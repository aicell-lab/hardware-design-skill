# The feedback loop: how the user annotates and how it reaches you

Templates: `templates/feedback/` (copy to `review/`). Stdlib + Pillow server, vanilla JS widget on top of
`<model-viewer>`.

## What the user does on the page

- **📍 Comment on 3D**: the viewer goes full screen, they click the model and type a note. Saved: the hit
  position (glTF metres, converted to CAD mm by the server), the clicked object's name, the camera, and a
  snapshot JPEG with the spot ringed.
- **Mark up any picture**: click an image -> lightbox; click = point, drag = box, then a note. Saved with the
  image path and the mark's position in %; the server draws the mark onto a copy in `media/`.
- **💬 Feedback panel** (bottom right): photos of the real hardware (drag-drop, paste or pick; downscaled
  to 1600 px JPEG in the browser, EXIF stripped), general notes, edit and delete.
- **Send N notes to Claude**: stamps the unsent notes as round N and messages the design session.

## What reaches you

- A message: `Design feedback round N came in from the review page: K notes (a on the 3D model, b image
  mark-ups, c photos). Notes and images: <project>/feedback/FEEDBACK.md (data: feedback.json, media/).`
- `feedback/FEEDBACK.md`, rounds newest first:
  `### #14 · 3D model · screen glass at X 106.7, Y 115.7, Z 32.6 mm`, the note, date and revision, the image.
- `feedback.json` (source of truth) and `media/` (n14-3d.jpg, n18-mark.jpg, n20-photo.jpg...).
- Read the note *and* the image: the pin or box says which feature; photos often carry the real fix (a paper
  shim beside the screen showed exactly which play to remove).

## Server (review/server.py)

- Endpoints: `GET /api/health`, `GET/POST /api/items`, `PATCH/DELETE /api/items/<n>`, `POST /api/send`.
- Env: `FEEDBACK_DIR` (default `<project>/feedback`), `PORT`, `FEEDBACK_NOTIFY_SESSION` (the myco session
  that gets the round message; `myco session send <id> "..."`).
- Writes `FEEDBACK.md` on every change; JPEGs only, <= 1600 px; the request body cap is generous but the
  hypha proxy rejects ~10 MB bodies, so keep images small.
- Must decode `Transfer-Encoding: chunked` (the tunnel streams bodies).

## Hosting with myco

- The report: a **static** mount (`myco serve <name> ./site`), stable URL.
- The server: a **process** mount (`review/mount.yaml`, `myco serve apply review/mount.yaml`) with
  `wake_on_request: true`, `idle_timeout_sec: 1800`, `warmup_path: /api/health`. Gotchas:
  - `command` runs through `sh -c`; an `args:` list is silently dropped: put the whole command line in
    `command`.
  - **Re-applying a mount issues a new URL** (and revokes the old one): apply once, then rebuild the report
    so the page points at it. To load new server code, stop the process; the next request restarts it.
  - The proxy sets `Access-Control-Allow-Origin: *` itself, so the static page can call the other mount.
  - Cloudflare answers 403 to Python-urllib's default User-Agent on hypha.run; use curl or a browser.
  - Never `pkill -f` a pattern that also appears in your own command line (it kills your shell); stop
    servers by port (`ss -ltnp | grep :8793` -> kill the pid).

## Revisions and pins

- `window.DESIGN_REV` stamps new notes; the widget hides sent pins and marks from older revisions, so the
  page starts clean each revision.
- Pins live in the assembled pose; with the explode view they move with their part (see
  `renders-and-viewer.md`).

## Testing the widget (never against the live server)

```sh
FEEDBACK_DIR=/tmp/fbdata PORT=8791 .venv/bin/python review/server.py &
cp -r site /tmp/site_test   # set window.FEEDBACK_API = "http://127.0.0.1:8791" in its index.html
(cd /tmp/site_test && python3 -m http.server 8792 &)
.venv/bin/python review/smoke_test.py http://127.0.0.1:8792/ /tmp/fb_shots
```

Playwright with the system Chrome, no browser download:
`p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-angle=swiftshader",
"--enable-unsafe-swiftshader", "--no-sandbox"])`. Wait for `document.querySelector('model-viewer').loaded`.
Find a clickable point on an object by scanning `positionAndNormalFromPoint` + `materialFromPoint`. Stop the
scratch servers by port afterwards.
