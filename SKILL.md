---
name: hardware-design
description: Design a 3D-printable part (mount, bracket, holder, enclosure) as parametric CadQuery code, prove it with digital checks and renders, publish a web design report with a 3D viewer (assembled + exploded) and a feedback layer where the user pins notes on the model, marks up pictures and uploads photos of real prints, then iterate revision by revision from their feedback rounds. Use when asked to design physical or 3D-printed hardware, or when a "Design feedback round N came in from the review page" message arrives.
---

# Printed-hardware design loop

You design with code; the user reviews on a web page and on real prints. Each revision is one pass of the
loop below and ends in a report, a commit and a short reply. The worked example (DGX Spark touchscreen mount,
Rev A to H, 21 notes over 7 rounds, two printed parts) is in `references/case-study-dgx-spark-mount.md`.

## Ground rules (what this user expects)

- **Simple and minimal.** Fewest printed parts, one unified look, nothing they did not ask for. They will strike
  out extras (a springy "click" edge added in one revision was removed in the next). Clean surfaces, rounded
  edges, one straight line where one will do; it must still look good with nothing mounted on it.
- **Don't ask for measurements.** Design from published data: spec sheets, vendor drawings and 3D models,
  standards, teardowns, reviews. Put the source next to each parameter. When the user volunteers a
  measurement, a photo or a print result, it wins: change the parameter and say so.
- **Quality first, step by step.** Take hard items one at a time, verify before replying, and never claim a
  check you did not run.
- **Notes arrive in any language,** often dictated Chinese. Translate faithfully, keep their intent, and
  restate it briefly in the report.
- **Messages can land mid-turn** (e.g. "also add an explode view"). Fold them into the same turn.
- **Honest about uncertainty.** Name what is assumed, what to check on the print, and the one parameter to
  tune if it is off (e.g. `BTN_GAP`; reprint only the small part).

## Project skeleton

```
cad/<part>.py   parameters (with sources) -> frames -> geometry -> exports/ (STEP, STL, 3MF per part)
cad/geom.py     shared helpers                        (templates/cad/geom.py)
cad/checks.py   digital checks -> exports/checks.json (templates/cad/checks_kit.py)
cad/render.py   PNG views, labelled sections, assembly.glb with an explode animation (templates/cad/render_kit.py)
cad/report.py   site/index.html from checks + renders + the NOTES table   (templates/report/report.py)
review/         feedback layer: server.py, feedback.js/.css, viewer.js, mount.yaml, smoke_test.py (templates/feedback)
feedback/       FEEDBACK.md, feedback.json, media/   (written by the feedback server)
notes/rev_X_plan.md   per revision: notes translated, decisions with numbers, log. Your memory across compactions
research/       datasheets, drawings and images you measured from
PLAN.md README.md
```

Quick start (`SKILL_DIR` = this skill's folder):

```sh
uv venv --python 3.11 .venv && uv pip install cadquery==2.8.0 pyvista trimesh pillow playwright
mkdir -p cad review exports renders feedback notes research
cp $SKILL_DIR/templates/cad/*.py cad/ && cp $SKILL_DIR/templates/report/report.py cad/
cp $SKILL_DIR/templates/feedback/* review/      # then edit review/mount.yaml (name, workdir, session, frame)
```

Write `cad/<part>.py` (with `build_part()` and `explode_offsets()`), a short `checks.py` and `render.py` on top
of the kits, then `myco serve <name> ./site` once and `myco serve apply review/mount.yaml` once. A private git
repo; one commit per revision. The kits were tested end to end on a toy bracket (model -> checks -> renders ->
GLB with explode -> report -> Explode in Chrome).

## The loop (one revision)

1. **Read** the brief or the round: `feedback/FEEDBACK.md`, and *look at* every image in `feedback/media/`
   (3D snapshots with the pin ringed, marked-up renders, photos of the real print).
2. **Plan** in `notes/rev_X_plan.md`: each note translated, what it really asks, decisions with numbers,
   published data found. Search the web for missing data (iPhone + case thickness, connector envelopes...).
3. **Model**: change parameters first, geometry second. Rebuild, then `isValid()` and one solid per part.
4. **Check** (`references/checks.md`): every collision is 0 except intended contacts (preloads, crush ribs),
   which are reported on their own. Add a check for whatever the note was about (tip-over, a button's
   stroke, a phone in the lane...).
5. **Render** (`references/renders-and-viewer.md`) and look at every image: a contact sheet, close-ups of the
   changed area, labelled cut sections for mechanisms, the assembled and exploded 3D view.
6. **Report** (`references/web-report.md`): bump `REV`; one NOTES row per note (round, number, the note,
   what the design does now); rewrite older answers the change supersedes; captions, checks table, "to
   confirm on the print". Screenshot the live page with Playwright to check the layout.
7. **Record**: README, PLAN.md section, the rev plan's log. Commit (message: what each note became,
   ends with the Co-Authored-By line) and push.
8. **Reply** (below), `myco session notify "<rev> is ready: ..."`.

When the user says "looks good, I'll print it", reply with a print and fit checklist only.

## Reply format

- First line: what this revision answers, the live URL, checks pass, the commit.
- An artifact card: `outputs/dgx_rev_X.html`, a 2-4 image grid (small JPEGs, ~900 px, under 200 KB in total)
  with one-line captions per note. Use `<artifact src="outputs/....html" title="..." />`.
- Then per note, by number, in plain words: what changed, with the key numbers (mm, N, %).
- "For the print": what to reprint (often only the body or only the frame), how to fit or remove it, what to
  check, which parameter to tune.
- Cite web sources as markdown links when you used a web search.

## Design rules that held up

| topic | rule |
|---|---|
| print orientation | Decide it first (big flat face on the bed). Overhang check: faces > 50 deg from vertical in print pose. A feature starting mid-air (an end face facing the bed) needs a 45 deg chamfer in plan. Flexures and springs bend *in the layer plane*. |
| clearances | 0.3 mm/side sliding fit, 0.15 frame in recess, 0.05 datum, 0.2 crush-rib interference, 0.5 mm min around plugs. |
| holding a device | Rigid seat: solid floor, solid datum wall on the side the load pushes toward, crush ribs opposite. No springs behind a touch surface: they feel loose. |
| actuation | Count lost motion: every bit of play between a lever and its target eats travel (case 0.6 + frame 0.3 mm = the user's 1 mm shim). Keep the pusher inside the target's outline so the housing can't stop it. |
| clips on a device | Use the real edge height (measure or derive), preload small (0.5 mm) or the walls splay visibly, catch angle sets pull-down vs pop-off. If the user wants it locked, reach a tongue well under the edge and fit by spreading the walls. |
| stability | When something leans or overhangs, compute where the CG sits vs the tipping edge and the press force that tips it (a 40 deg phone's CG sat right over the host's rear edge: 2 N tipped the Rev F mount). |
| cables | Model the largest standard plug envelope (USB-C overmold 12.35 x 6.5 x 16 mm) and its bend; leave holes (closed, rounded) not gaps if the user asks; storage pegs long enough for 4-5 turns. |
| material | PETG for anything near warm electronics (PLA softens ~55 C); 5 walls so hooks, hinges and ribs are solid perimeters. |

Details and formulas: `references/print-and-mechanics.md`.

## Gotchas index

- CadQuery/OCC (fillets that kill solids, pending wires, selectors, coplanar booleans): `references/cad.md`.
- GLB for the web (sRGB to linear, names = pin labels, explode animation that loops back to 0 at its end,
  play before pause): `references/renders-and-viewer.md`.
- myco (static vs process mounts, re-apply = new URL, `command` not `args`, kill by port): `references/feedback-loop.md`.
- Testing the page: Playwright with the system Chrome (`executable_path="/usr/bin/google-chrome"`, swiftshader),
  a scratch feedback server + a copy of `site/`; never post test notes to the live server.

## Files in this skill

- `references/`: cad, print-and-mechanics, checks, renders-and-viewer, web-report, feedback-loop, case study.
- `templates/feedback/`: the review layer (server, widget, explode control, mount spec, smoke test). Copy to
  `review/`, then set the names, the port and the session to notify.
- `templates/cad/`: `geom.py` (frames, rounded profiles, sweeps, booleans), `render_kit.py` (offscreen shots,
  sections, labels, contact sheets, GLB with explode), `checks_kit.py` (interference, overhangs in any print
  pose, cantilever, clip, tip-over and slide maths).
- `templates/report/report.py`: the report generator (page outline, NOTES table, 3D viewer with Explode,
  feedback layer hooks), ready to fill in.
