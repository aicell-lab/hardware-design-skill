"""Feedback API for the design report: 3D pins, image mark-ups, reference photos and notes.

Everything lands in ../feedback/ so the design agent can read it straight from the project:
  feedback.json   all notes (source of truth)
  FEEDBACK.md     readable digest, regenerated on every change
  media/          3D view snapshots (pin marked), marked-up images, reference photos (JPEG, <= 1600 px)

"Send" stamps the unsent notes with the next round number and messages the design session
(`myco session send`). Run by the myco process mount in review/mount.yaml. Stdlib + Pillow.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("FEEDBACK_DIR", ROOT / "feedback"))
MEDIA = DATA / "media"
SITE = ROOT / "site"
PORT = int(os.environ.get("PORT", "8790"))
NOTIFY = os.environ.get("FEEDBACK_NOTIFY_SESSION", "")   # myco session that gets the "round N" message
CAD_FRAME = os.environ.get("FEEDBACK_CAD_FRAME",             # how to read the X/Y/Z of 3D notes (FEEDBACK.md header)
                           "CAD frame for 3D notes: the model script's world frame, mm (glTF Y-up converted back to Z-up).")
MAX_BODY = 25 * 1024 * 1024
MAX_PX = 1600
ACCENT = (232, 80, 40)
LOCK = threading.Lock()
_last_send = 0.0


# ----------------------------------------------------------------------------- storage
def load():
    try:
        return json.loads((DATA / "feedback.json").read_text())
    except FileNotFoundError:
        return {"next": 1, "rounds": [], "items": []}


def save(db):
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = DATA / "feedback.json.tmp"
    tmp.write_text(json.dumps(db, indent=1))
    tmp.replace(DATA / "feedback.json")
    (DATA / "FEEDBACK.md").write_text(digest(db))


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- images
def decode_image(data_url):
    m = re.match(r"data:image/(?:png|jpeg|webp);base64,(.+)$", data_url or "", re.S)
    if not m:
        raise ValueError("expected a base64 PNG/JPEG data URL")
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(base64.b64decode(m.group(1)))))
    im = im.convert("RGB")                      # re-encoding also drops EXIF (GPS etc.)
    im.thumbnail((MAX_PX, MAX_PX))
    return im


def save_jpeg(im, name):
    MEDIA.mkdir(parents=True, exist_ok=True)
    im.save(MEDIA / name, "JPEG", quality=85)
    return f"media/{name}"


def source_path(ref):
    """Image a mark-up refers to: a report image (img/...) or an uploaded photo (media/...)."""
    if re.fullmatch(r"img/[\w.-]+\.(png|jpg)", ref or ""):
        return SITE / ref
    if re.fullmatch(r"media/[\w.-]+\.jpg", ref or ""):
        return DATA / ref
    raise ValueError("unknown image")


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def badge(draw, x, y, n, W):
    r = max(13, W // 55)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=ACCENT, outline=(255, 255, 255), width=max(2, r // 6))
    draw.text((x, y), str(n), fill=(255, 255, 255), font=font(int(r * 1.15)), anchor="mm")


def mark_up(item):
    """The marked image the agent reads: the source image with the box/point and its number drawn on."""
    im = Image.open(source_path(item["image"])).convert("RGB")
    im.thumbnail((MAX_PX, MAX_PX))
    W, H = im.size
    d = ImageDraw.Draw(im)
    x, y, w, h = item["x"] * W, item["y"] * H, item.get("w", 0) * W, item.get("h", 0) * H
    lw = max(3, W // 280)
    if w > 3 and h > 3:
        d.rectangle([x, y, x + w, y + h], outline=ACCENT, width=lw)
        badge(d, x, y, item["n"], W)
    else:
        r = max(16, W // 45)
        d.ellipse([x - r, y - r, x + r, y + r], outline=ACCENT, width=lw)
        badge(d, x + r, y - r, item["n"], W)
    return im


# ----------------------------------------------------------------------------- notes
def gltf_to_cad(p):
    """Viewer (glTF: metres, Y up, front +Z) -> CAD frame (mm: X right, Y rearward, Z up)."""
    return [round(p[0] * 1000, 1), round(-p[2] * 1000, 1), round(p[1] * 1000, 1)]


def create(db, body):
    kind = body.get("type")
    if kind not in ("3d", "image", "photo", "note"):
        raise ValueError("unknown note type")
    n = db["next"]
    it = {"n": n, "type": kind, "text": str(body.get("text", "")).strip()[:4000],
          "author": str(body.get("author", "")).strip()[:60], "rev": str(body.get("rev", ""))[:20],
          "created": now(), "round": None}
    if kind == "3d":
        it["pos"] = [float(v) for v in body["pos"]][:3]
        it["normal"] = [round(float(v), 3) for v in body.get("normal", [0, 0, 0])][:3]
        it["cad_mm"] = gltf_to_cad(it["pos"])
        it["object"] = str(body.get("object", ""))[:40]
        it["camera"] = {k: str(v)[:80] for k, v in (body.get("camera") or {}).items() if k in ("orbit", "target", "fov")}
        if body.get("snapshot"):
            it["snap"] = save_jpeg(decode_image(body["snapshot"]), f"n{n}-3d.jpg")
    elif kind == "image":
        it["image"] = str(body["image"])
        source_path(it["image"])
        for k in ("x", "y", "w", "h"):
            it[k] = round(min(1.0, max(0.0, float(body.get(k, 0)))), 4)
        it["snap"] = save_jpeg(mark_up(it), f"n{n}-mark.jpg")
    elif kind == "photo":
        it["snap"] = save_jpeg(decode_image(body["photo"]), f"n{n}-photo.jpg")
    db["items"].append(it)
    db["next"] = n + 1
    return it


def find(db, n):
    for it in db["items"]:
        if it["n"] == n:
            return it
    raise KeyError(n)


def stamp_round(db):
    """Stamp the unsent notes with the next round number. Returns (result, message for the design session)."""
    global _last_send
    todo = [it for it in db["items"] if it["round"] is None]
    if not todo:
        return {"round": None, "count": 0, "notified": False, "detail": "nothing new to send"}, None
    if time.time() - _last_send < 20:
        raise ValueError("just sent; try again in a few seconds")
    _last_send = time.time()
    rnd = len(db["rounds"]) + 1
    for it in todo:
        it["round"] = rnd
    kinds = {k: sum(1 for it in todo if it["type"] == k) for k in ("3d", "image", "photo", "note")}
    db["rounds"].append({"round": rnd, "sent": now(), "count": len(todo), "kinds": kinds, "notified": False})
    parts = [f"{kinds['3d']} on the 3D model", f"{kinds['image']} image mark-ups", f"{kinds['photo']} photos",
             f"{kinds['note']} general notes"]
    msg = (f"Design feedback round {rnd} came in from the review page: {len(todo)} notes "
           f"({', '.join(p for p in parts if not p.startswith('0 '))}). Notes and images: "
           f"{DATA / 'FEEDBACK.md'} (data: feedback.json, media/). Please use them for the next design revision.")
    return {"round": rnd, "count": len(todo), "notified": False, "detail": ""}, msg


def notify(msg):
    if not NOTIFY:
        return False, "notifications off"
    myco = shutil.which("myco") or str(Path.home() / ".local/bin/myco")
    try:
        r = subprocess.run([myco, "session", "send", NOTIFY, msg], capture_output=True, text=True, timeout=40)
        return r.returncode == 0, (r.stdout + r.stderr).strip()[-300:]
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ----------------------------------------------------------------------------- digest
KIND = {"3d": "3D model", "image": "Image mark-up", "photo": "Reference photo", "note": "Note"}


def entry(it):
    head = f"### #{it['n']} · {KIND[it['type']]}"
    if it["type"] == "3d":
        x, y, z = it["cad_mm"]
        head += f" · {it.get('object') or 'model'} at X {x}, Y {y}, Z {z} mm"
    elif it["type"] == "image":
        box = it["w"] > 0.004 and it["h"] > 0.004
        where = (f"box {it['x']:.0%},{it['y']:.0%} size {it['w']:.0%}×{it['h']:.0%}" if box
                 else f"point {it['x']:.0%},{it['y']:.0%}")
        head += f" · `{it['image']}` · {where}"
    quote = "\n".join("> " + line for line in (it["text"] or "(no text)").splitlines())
    meta = " · ".join(p for p in (it.get("author"), it["created"][:16].replace("T", " "), it.get("rev")) if p)
    out = [head, quote, "", meta]
    if it.get("snap"):
        out.append(f"![#{it['n']}]({it['snap']})")
    return "\n".join(out) + "\n"


def digest(db):
    lines = ["# Design feedback", "",
             "From the design report's feedback panel. Newest round first; images in `media/` "
             "(3D snapshots have the pin marked, mark-ups have the box or point drawn).",
             CAD_FRAME, ""]
    unsent = [it for it in db["items"] if it["round"] is None]
    if unsent:
        lines += [f"## Not sent yet ({len(unsent)})", ""] + [entry(it) for it in unsent]
    for r in reversed(db["rounds"]):
        its = [it for it in db["items"] if it["round"] == r["round"]]
        lines += [f"## Round {r['round']} · sent {r['sent'][:16].replace('T', ' ')} · {len(its)} notes", ""]
        lines += [entry(it) for it in its]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "feedback/1"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")

    def _send(self, code, body=b"", ctype="application/json", extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode())

    def _body(self):
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():   # the tunnel streams bodies
            buf = bytearray()
            while True:
                size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    self.rfile.readline()
                    break
                buf += self.rfile.read(size)
                self.rfile.readline()
                if len(buf) > MAX_BODY:
                    raise ValueError("too large")
            raw = bytes(buf)
        else:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("too large")
            raw = self.rfile.read(n)
        return json.loads(raw or b"{}")

    def _route(self, fn):
        try:
            fn()
        except (ValueError, KeyError, TypeError) as e:
            self._json({"error": str(e) or e.__class__.__name__}, 400)
        except Exception as e:  # noqa: BLE001
            self._json({"error": f"server error: {e}"}, 500)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/api/health"):
            myco = shutil.which("myco") or str(Path.home() / ".local/bin/myco")
            return self._json({"ok": True, "notify": bool(NOTIFY), "myco": os.access(myco, os.X_OK)})
        if path == "/api/items":
            with LOCK:
                return self._json(load())
        m = re.fullmatch(r"/media/([\w.-]+\.jpg)", path)
        if m and (MEDIA / m.group(1)).is_file():
            return self._send(200, (MEDIA / m.group(1)).read_bytes(), "image/jpeg",
                              [("Cache-Control", "public, max-age=86400")])
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]

        def run():
            if path not in ("/api/items", "/api/send"):
                return self._json({"error": "not found"}, 404)
            body = self._body()
            with LOCK:
                db = load()
                if path == "/api/items":
                    it = create(db, body)
                    save(db)
                    return self._json(it, 201)
                res, msg = stamp_round(db)
                save(db)
            if msg:                                   # message the design session outside the lock
                res["notified"], res["detail"] = notify(msg)
                with LOCK:
                    db = load()
                    db["rounds"][-1]["notified"] = res["notified"]
                    save(db)
            self._json(res)
        self._route(run)

    def do_PUT(self):
        def run():
            n = int(self.path.split("?")[0].rsplit("/", 1)[-1])
            body = self._body()
            with LOCK:
                db = load()
                it = find(db, n)
                if it["round"] is not None:
                    raise ValueError("already sent")
                it["text"] = str(body.get("text", "")).strip()[:4000]
                save(db)
            self._json(it)
        self._route(run)

    def do_DELETE(self):
        def run():
            n = int(self.path.split("?")[0].rsplit("/", 1)[-1])
            with LOCK:
                db = load()
                it = find(db, n)
                if it["round"] is not None:
                    raise ValueError("already sent")
                db["items"].remove(it)
                if it.get("snap"):
                    (DATA / it["snap"]).unlink(missing_ok=True)
                save(db)
            self._json({"deleted": n})
        self._route(run)


if __name__ == "__main__":
    print(f"feedback server on 127.0.0.1:{PORT}, data in {DATA}, notify={NOTIFY or 'off'}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
