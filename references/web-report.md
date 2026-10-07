# The web design report (`cad/report.py` -> `site/`)

One static page per project, regenerated every revision, served at a stable URL. Skeleton:
`templates/report/report.py`.

## How report.py works

- Constants: `REV = "Rev H"`; `FEEDBACK_MOUNT` (the myco process mount name of the feedback server);
  `IMAGES` (renders copied to `site/img/`).
- `NOTES`: one tuple per feedback note ever received, `(round, n, "the note in plain English", "answer
  template with {values}")`. The answer says what the design does **now**; when a later round supersedes an
  answer, rewrite it ("Superseded by #14: ...").
- `feedback_api()`: the feedback server's public URL from `myco serve list --json` (or `$FEEDBACK_API`).
- `build()`: copy images, downloads (3MF / STL / STEP per part, `checks.json`, `assembly.glb`) and the
  review scripts (`feedback.js`, `feedback.css`, `viewer.js`, hashed for cache busting); load
  `checks.json`; compute the values dict (dimensions from the built part's bounding box, mass = volume x 1.27
  g/cm3 x 0.85, numbers from checks, parameters formatted with `f"{x:g}"`); render the NOTES rows with the
  note's snapshot as thumbnail (`feedback.json` item `snap`, copied to `site/img/fb/`); `TEMPLATE.format(**v)`.
- The template is a Python format string: CSS and JS braces are doubled (`{{ }}`).

## Page outline (what the user scrolls through)

1. Header bar (project, rev, date), kicker, h1 (one sentence: what it is), lede, pills (parts count, no
   screws/glue, host not modified, material/no supports, prototype status).
2. Hero: the oblique render next to `<model-viewer src="files/assembly.glb" camera-controls auto-rotate>`
   with the Explode button and the "📍 Comment on 3D" button; a note on how to use both and the feedback
   panel.
3. Downloads per part (3MF primary, STL, STEP) and the checks JSON.
4. **Your feedback -> Rev X**: table of every note (thumbnail, #n, round, the note, the design now).
5. How it works: a 3-column grid of captioned figures (bold lead, then one or two sentences): the overall
   look, labelled sections of the mechanisms, use cases, the exploded still, the print pose of small parts.
6. Two columns: The parts (dimensions, mass, key numbers) / Designed from published data (each input and
   its source).
7. Two columns: Print + Assemble (+ how to remove) / Digital checks table + "To confirm on the first print".
8. More views; footer (tools, units, source in the git repo).
9. Scripts: `window.FEEDBACK_API`, `window.DESIGN_REV`, `window.EXPLODE = {amount, offsets}`, then
   `viewer.js` and `feedback.js` (defer).

## Serving and checking

- Static mount once: `myco serve <name> ./site`; its URL stays the same, so later revisions only re-run
  `report.py`. Add it to the session's links (`myco session link add <url> --label "Design report"`).
- After building, screenshot the live page with Playwright (system Chrome) at the feedback table, How it
  works and the checks: overflowing labels, misaligned grids and stale numbers show up there.
