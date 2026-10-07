"""Build the web design report (site/) from the current model, checks and renders. Generic skeleton: fill in
PROJECT, IMAGES, NOTES and the page text; the structure, the feedback table, the 3D viewer with Explode and the
feedback layer are ready.

Expects: cad/<model>.py importable as M (with explode_offsets()), exports/checks.json, renders/*.png,
renders/assembly.glb, review/{feedback.js, feedback.css, viewer.js}, feedback/feedback.json (once notes exist).
Run:  python cad/report.py   -> site/index.html
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import model as M  # noqa: E402  (rename to your model script)

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PROJECT = "Project name"                  # header bar + <title>
REV = "Rev A"
FEEDBACK_MOUNT = "project-feedback"       # myco process mount running review/server.py (review/mount.yaml)
PARTS = ("part", "frame")                 # exports/<part>.{3mf,stl,step}
IMAGES = ("oblique_front", "section_a", "exploded", "part_alone", "side", "rear")

# Every feedback note and what the design does NOW: (round, n, "the note in plain English", "answer {values}").
# Rewrite an answer when a later round supersedes it ("Superseded by #14: ...").
NOTES = [
    # (1, 1, "The phone sits too close to the screen.", "Moved {gap} mm apart ..."),
]


def feedback_api():
    """Public URL of the feedback server: $FEEDBACK_API, else the myco mount of that name."""
    if os.environ.get("FEEDBACK_API"):
        return os.environ["FEEDBACK_API"].rstrip("/")
    try:
        mounts = json.loads(subprocess.run(["myco", "serve", "list", "--json"], capture_output=True, text=True,
                                           timeout=30).stdout)
        return next(m["url"].rstrip("/") for m in mounts if m["name"] == FEEDBACK_MOUNT)
    except Exception:  # noqa: BLE001
        return ""


def build():
    for d in ("img", "img/fb", "files"):
        (SITE / d).mkdir(parents=True, exist_ok=True)
    for f in IMAGES:
        shutil.copy(ROOT / "renders" / f"{f}.png", SITE / "img" / f"{f}.png")
    for part in PARTS:
        for ext in ("stl", "3mf", "step"):
            shutil.copy(ROOT / "exports" / f"{part}.{ext}", SITE / "files" / f"{part}.{ext}")
    shutil.copy(ROOT / "exports" / "checks.json", SITE / "files" / "checks.json")
    shutil.copy(ROOT / "renders" / "assembly.glb", SITE / "files" / "assembly.glb")
    h = hashlib.sha1()
    for f in ("feedback.js", "feedback.css", "viewer.js"):                     # cache-busting hash
        shutil.copy(ROOT / "review" / f, SITE / f)
        h.update((ROOT / "review" / f).read_bytes())

    ck = json.loads((ROOT / "exports" / "checks.json").read_text())
    v = dict(project=PROJECT, rev=REV, today=date.today().isoformat(), fb_api=feedback_api(), fbv=h.hexdigest()[:10],
             mass=round(ck["part_volume_cm3"] * 1.27 * 0.85),       # PETG, ~85% fill
             explode=json.dumps({k: [round(x / 1000, 5), round(z / 1000, 5), round(-y / 1000, 5)]   # glTF m, Y up
                                 for k, (x, y, z) in M.explode_offsets().items()}))
    # ... add every number the page shows, from ck (checks.json) and M (parameters), formatted f"{x:g}"

    snaps = {}
    try:
        snaps = {it["n"]: it.get("snap") for it in json.loads((ROOT / "feedback" / "feedback.json").read_text())["items"]}
    except (OSError, ValueError, KeyError):
        pass
    rows = []
    for rnd, n, note, answer in NOTES:
        src = ROOT / "feedback" / (snaps.get(n) or f"media/n{n}-3d.jpg")
        thumb = ""
        if src.exists():
            shutil.copy(src, SITE / "img" / "fb" / src.name)
            thumb = f'<img src="img/fb/{src.name}" alt="Note {n} snapshot">'
        rows.append(f'<tr><td>{thumb}</td><td><span class="n">#{n}</span> <span class="note">round {rnd}</span><br>'
                    f'{note}</td><td>{answer.format(**v)}</td></tr>')
    v["rows"] = "\n".join(rows) or '<tr><td></td><td colspan="2" class="note">No notes yet.</td></tr>'
    (SITE / "index.html").write_text(TEMPLATE.format(**v))
    return SITE / "index.html"


# Python format string: CSS/JS braces are doubled.
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{project} · {rev}</title>
<link rel="icon" href="data:,">
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>
<link rel="stylesheet" href="feedback.css?v={fbv}">
<style>
  :root {{ --ink:#1d1f22; --mute:#6b6f76; --line:#e4e2dd; --bg:#fbfaf7; --card:#ffffff; --acc:#2f6f73; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.6 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif; color:var(--ink); background:var(--bg); }}
  header {{ border-bottom:1px solid var(--line); background:var(--card); }}
  .bar {{ max-width:1040px; margin:0 auto; padding:10px 24px; display:flex; justify-content:space-between; font-size:12px; color:var(--mute); letter-spacing:.04em; }}
  main {{ max-width:1040px; margin:0 auto; padding:30px 24px 60px; }}
  .kicker {{ font-size:12px; letter-spacing:.09em; text-transform:uppercase; color:var(--acc); margin:0 0 6px; }}
  h1 {{ font-weight:400; font-size:34px; line-height:1.2; margin:0 0 8px; }}
  .lede {{ color:var(--mute); font-size:16px; max-width:780px; margin:0 0 14px; }}
  .pills span {{ display:inline-block; font-size:12px; padding:3px 10px; border:1px solid var(--line); border-radius:20px; color:var(--mute); margin:0 6px 6px 0; background:var(--card); }}
  h2 {{ font-weight:400; font-size:22px; margin:40px 0 12px; }}
  h3 {{ font-weight:600; font-size:14px; margin:18px 0 6px; }}
  .hero {{ display:grid; grid-template-columns:3fr 2fr; gap:14px; margin-top:20px; }}
  .hero img, model-viewer {{ width:100%; border-radius:12px; border:1px solid var(--line); background:#f3f2ee; }}
  model-viewer {{ height:100%; min-height:330px; }}
  model-viewer .mv-explode {{ position:absolute; left:10px; bottom:10px; padding:7px 12px; border:1px solid rgba(0,0,0,.08);
    border-radius:18px; background:rgba(255,255,255,.94); color:#1d1f22; font:600 12.5px/1 inherit; cursor:pointer;
    box-shadow:0 2px 8px rgba(0,0,0,.12); }}
  model-viewer .mv-explode.on {{ background:#1d1f22; color:#fff; }}
  model-viewer .mv-explode[hidden] {{ display:none; }}
  .grid3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
  .grid3 img {{ width:100%; border-radius:10px; border:1px solid var(--line); background:#f3f2ee; }}
  figure {{ margin:0; }} figcaption {{ font-size:12px; color:var(--mute); margin-top:5px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; background:var(--card); }}
  th, td {{ text-align:left; padding:8px 11px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ font-weight:600; color:var(--mute); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
  td:first-child {{ color:var(--mute); width:38%; }}
  .two {{ display:grid; grid-template-columns:1fr 1fr; gap:26px; }}
  ol, ul {{ padding-left:20px; margin:0; }} li {{ margin:5px 0; }}
  .note {{ font-size:13px; color:var(--mute); }}
  .dl a {{ display:inline-block; margin:0 8px 8px 0; padding:9px 14px; border:1px solid var(--acc); border-radius:8px; color:var(--acc); text-decoration:none; font-size:14px; background:var(--card); }}
  .dl a.primary {{ background:var(--acc); color:#fff; }}
  .ok {{ color:#2f7a4f; font-weight:600; }}
  code {{ font:13px ui-monospace,Menlo,monospace; background:rgba(0,0,0,.05); padding:1px 5px; border-radius:4px; }}
  footer {{ max-width:1040px; margin:0 auto; padding:0 24px 40px; font-size:12px; color:var(--mute); }}
  .fbt td:first-child {{ width:auto; }} .fbt img {{ width:120px; border-radius:6px; border:1px solid var(--line); display:block; }}
  .fbt td {{ font-size:13.5px; }} .fbt .n {{ font-weight:700; color:var(--acc); }}
  .dl b {{ display:inline-block; min-width:92px; font-size:13px; color:var(--mute); font-weight:600; }}
  @media (max-width:800px) {{ .hero, .two, .grid3 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header><div class="bar"><span>{project}</span><span>{rev} · {today}</span></div></header>
<main>
  <p class="kicker">Design report</p>
  <h1>One sentence: what it is and what it does.</h1>
  <p class="lede">Two or three sentences: what it holds, how it attaches, what stays hidden.</p>
  <div class="pills"><span>N printed parts</span><span>No screws, glue or bought parts</span><span>PETG, no supports</span><span>Prototype status</span></div>

  <div class="hero">
    <figure><img src="img/oblique_front.png" alt="Assembled"></figure>
    <model-viewer src="files/assembly.glb" alt="Interactive 3D view" camera-controls auto-rotate rotation-per-second="18deg"
      shadow-intensity="0.7" exposure="1.05" camera-orbit="-35deg 62deg auto" interaction-prompt="none"></model-viewer>
  </div>
  <p class="note">Right: drag to rotate, scroll to zoom; <b>Explode</b> lifts the parts apart the way they go together.
  <b>Feedback:</b> <b>📍 Comment on 3D</b> pins a note on the model, click any picture to mark it up, or open <b>💬 Feedback</b>
  (bottom right) to add photos of your hardware and send everything back for the next revision.</p>

  <div class="dl" style="margin-top:14px">
    <div><b>Part</b><a class="primary" href="files/part.3mf" download>3MF</a><a href="files/part.stl" download>STL</a><a href="files/part.step" download>STEP</a><a href="files/checks.json">Check results (JSON)</a></div>
  </div>

  <h2>Your feedback → {rev}</h2>
  <table class="fbt"><tr><th>Your view</th><th>Note</th><th>In the design now</th></tr>
  {rows}
  </table>

  <h2>How it works</h2>
  <div class="grid3">
    <figure><img src="img/section_a.png" alt="Section"><figcaption><b>Bold lead.</b> One or two sentences on what the labelled section shows.</figcaption></figure>
    <figure><img src="img/exploded.png" alt="Exploded"><figcaption><b>How it goes together.</b> Each part, in assembly order.</figcaption></figure>
    <figure><img src="img/part_alone.png" alt="The part"><figcaption><b>The printed part.</b> As printed, no supports.</figcaption></figure>
  </div>

  <div class="two">
    <section><h2>The parts</h2><table><tr><td>Part</td><td>W × D × H mm; PETG ≈{mass} g</td></tr></table></section>
    <section><h2>Designed from published data</h2><table><tr><td>Input</td><td>Value (source)</td></tr></table></section>
  </div>
  <div class="two">
    <section><h2>Print</h2><ol><li>Orientation, no supports.</li><li>PETG, 0.2 mm layers, 5 walls, 20% gyroid.</li></ol>
      <h2>Assemble</h2><ol><li>Step.</li></ol><p class="note"><b>Remove:</b> how.</p></section>
    <section><h2>Digital checks</h2><table><tr><th>Check</th><th>Result</th></tr><tr><td>Part vs everything</td><td><span class="ok">0 mm³</span></td></tr></table>
      <h3>To confirm on the first print</h3><ul class="note"><li>Each assumed number, and the parameter to tune.</li></ul></section>
  </div>
</main>
<footer>Built with CadQuery (parametric source), PyVista renders. Units mm.</footer>
<script>window.FEEDBACK_API = "{fb_api}"; window.DESIGN_REV = "{rev}"; window.EXPLODE = {{ "amount": 0, "offsets": {explode} }};</script>
<script src="viewer.js?v={fbv}" defer></script>
<script src="feedback.js?v={fbv}" defer></script>
</body>
</html>
"""

if __name__ == "__main__":
    print(build())
