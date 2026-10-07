"""Browser smoke test of the feedback widget: Playwright driving the system Chrome (software WebGL).

Object names: SMOKE_HOST / SMOKE_PART env vars (defaults "host", "printed part").
Run it against a COPY of site/ whose FEEDBACK_API points at a scratch server, never the live one:
  FEEDBACK_DIR=/tmp/fbdata PORT=8791 .venv/bin/python review/server.py &
  cp -r site /tmp/site_test   # then set window.FEEDBACK_API = "http://127.0.0.1:8791" in its index.html
  (cd /tmp/site_test && python3 -m http.server 8792 &)
  .venv/bin/python review/smoke_test.py http://127.0.0.1:8792/ /tmp/fb_shots
"""
from __future__ import annotations

import io
import json
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8792/"
HOST = os.environ.get("SMOKE_HOST", "host")             # object names in assembly.glb (= material names)
PART = os.environ.get("SMOKE_PART", "printed part")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/fb_shots")
OUT.mkdir(parents=True, exist_ok=True)

FIND = """([name, HOST]) => { const mv = document.querySelector('model-viewer'), r = mv.getBoundingClientRect();
  for (let fy = 0.25; fy < 0.95; fy += 0.025) for (let fx = 0.2; fx < 0.85; fx += 0.025) {
    const x = r.left + fx * r.width, y = r.top + fy * r.height, hit = mv.positionAndNormalFromPoint(x, y);
    if (hit && mv.materialFromPoint(x, y)?.name === name && (name !== HOST || hit.normal.y > 0.9))
      return {x, y, pos: [hit.position.x, hit.position.y, hit.position.z]}; }
  return null; }"""


def shot(page, name):
    im = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    im.thumbnail((1000, 1000))
    im.save(OUT / f"{name}.jpg", quality=68)


def note(page, text):
    page.wait_for_selector(".fb-pop textarea")
    page.fill(".fb-pop textarea", text)
    page.click(".fb-pop .fb-primary")
    page.wait_for_selector(".fb-pop", state="detached")


def main():
    photo = OUT / "test_photo.jpg"
    im = Image.new("RGB", (3200, 2400), (205, 200, 190))
    ImageDraw.Draw(im).rectangle([900, 700, 2300, 1700], fill=(30, 30, 32))
    im.save(photo, quality=90)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                    args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("dialog", lambda d: d.accept())
        page.goto(URL)
        page.wait_for_function("document.querySelector('model-viewer')?.loaded", timeout=90000)
        api = page.evaluate("window.FEEDBACK_API")
        assert "127.0.0.1" in api or "localhost" in api, f"refusing to test against a live server: {api}"

        # 3D: full-screen pin mode, one pin on the host's top, one on the printed part
        page.click(".fb-mvbtn")
        page.wait_for_timeout(1500)
        top = page.evaluate(FIND, [HOST, HOST])
        page.mouse.click(top["x"], top["y"])
        page.wait_for_selector(".fb-pop textarea")
        shot(page, "1_pin_popover")
        note(page, "Test pin on the host's top")
        part = page.evaluate(FIND, [PART, HOST])
        page.mouse.click(part["x"], part["y"])
        note(page, "Test pin on the printed part")
        page.wait_for_function("document.querySelectorAll('model-viewer .fb-pin:not(.temp)').length === 2")
        shot(page, "2_pins")
        page.click(".fb-bar .fb-primary")                 # Done -> back to the page, panel opens

        # picture mark-up: drag a box on the hero render, then a point
        page.click("main figure .fb-wrap")
        layer = page.locator(".fb-layer").bounding_box()
        page.mouse.move(layer["x"] + layer["width"] * 0.35, layer["y"] + layer["height"] * 0.45)
        page.mouse.down()
        page.mouse.move(layer["x"] + layer["width"] * 0.5, layer["y"] + layer["height"] * 0.6, steps=8)
        page.mouse.up()
        note(page, "Test box")
        page.mouse.click(layer["x"] + layer["width"] * 0.7, layer["y"] + layer["height"] * 0.3)
        note(page, "Test point")
        page.wait_for_function("document.querySelectorAll('.fb-layer .fb-dot, .fb-layer .fb-box').length === 2")
        shot(page, "3_markup")
        page.click(".fb-lbbar .fb-primary")

        # photo, note, edit, delete, send
        page.set_input_files(".fb-panel input[type=file]", str(photo))
        note(page, "Test photo of the real hardware")
        page.click(".fb-tools button:nth-child(3)")
        note(page, "Test general note")
        page.click(".fb-item[data-n='6'] .fb-acts button[title=Edit]")
        page.wait_for_selector(".fb-pop textarea")
        page.fill(".fb-pop textarea", "Test general note (edited)")
        page.click(".fb-pop .fb-primary")
        page.wait_for_selector(".fb-pop", state="detached")
        page.click(".fb-item[data-n='4'] .fb-acts button[title=Delete]")
        page.wait_for_function("!document.querySelector(\".fb-item[data-n='4']\")")
        shot(page, "4_panel")
        page.click(".fb-send")
        page.wait_for_function("document.querySelector('.fb-status').textContent.includes('round 1')", timeout=30000)
        status = page.inner_text(".fb-status")
        shot(page, "5_sent")

        # phone-sized screen: panel as a bottom sheet
        m = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        m.goto(URL)
        m.wait_for_selector(".fb-fab")
        m.tap(".fb-fab")
        m.wait_for_selector(".fb-item")
        shot(m, "6_mobile_panel")
        browser.close()

    db = json.loads(urllib.request.urlopen(f"{api}/api/items").read())
    print("status:", status)
    print("errors:", errors or "none")
    print("host top hit (viewer m):", [round(v, 4) for v in top["pos"]])
    for it in db["items"]:
        print(it["n"], it["type"], it.get("object", ""), it.get("cad_mm", ""), it.get("snap", ""), it["round"], it["text"])


if __name__ == "__main__":
    main()
