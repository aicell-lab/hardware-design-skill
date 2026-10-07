# hardware-design: a Claude Code skill for 3D-printed hardware

A Claude Code skill for designing 3D-printable parts
(mounts, brackets, holders, enclosures) together with a person who reviews them on the web and on real prints.

The agent models the part as parametric CadQuery code, proves it with digital checks (collisions, insertion
paths, print-pose overhangs, clip, lever and tip-over maths) and renders, and publishes a design report: a web
page with a 3D viewer (assembled and **exploded**), labelled cut sections, downloads (3MF / STL / STEP) and a
**feedback layer**. On that page the reviewer pins notes on the 3D model, marks up pictures, uploads photos of
the real print and presses *Send*. The agent gets a "feedback round N" message and turns it into the next
revision, answering every note by number.

It grew out of a real project, a touchscreen-and-phone mount for an NVIDIA DGX Spark: 8 revisions, 21 notes
in 7 rounds, two of them after printing it and trying it on the hardware. The lessons are in
`references/case-study-dgx-spark-mount.md`.

## Install

```sh
git clone https://github.com/aicell-lab/hardware-design-skill ~/.claude/skills/hardware-design
```

Claude Code picks it up as the `hardware-design` skill (ask for a printable part, or send a feedback round).

## What's inside

| path | what |
|---|---|
| `SKILL.md` | the loop, how the agent and the reviewer work together, the reply format, design rules that held up |
| `references/cad.md` | CadQuery/OCC practice: frames, 2D profiles, fillets that break solids, selectors, exports |
| `references/print-and-mechanics.md` | print orientation and overhangs, clearances, rigid seats and datums, flexure buttons and lost motion, snap-fit and tip-over formulas, connectors |
| `references/checks.md` | the digital checks and how to report them |
| `references/renders-and-viewer.md` | offscreen renders, labelled sections, GLB for the web, the explode animation |
| `references/web-report.md` | the report generator and the page outline |
| `references/feedback-loop.md` | pins, mark-ups, photos, rounds; the feedback server on myco; testing with Playwright |
| `references/case-study-dgx-spark-mount.md` | revisions and lessons from the DGX Spark mount |
| `templates/cad/` | `geom.py`, `render_kit.py`, `checks_kit.py` |
| `templates/report/report.py` | report generator skeleton |
| `templates/feedback/` | feedback server, widget, explode control, myco mount spec, browser smoke test |

## Requirements

Python 3.11, `cadquery==2.8.0`, `pyvista`, `trimesh`, `pillow`, `playwright` (driving a system Chrome).
Hosting and the session messages use the `myco` CLI (static and process mounts, `myco session send`); any
static host plus a small Python server works too.
