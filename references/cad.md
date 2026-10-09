# Parametric CAD with CadQuery 2.8 / OCP 7.9

## Structure of the model script

- **Parameters first**, grouped by subject, each with a comment: what it controls and where the value comes
  from ("NVIDIA rear drawing, measured", "Waveshare 3D model", "measured on the Spark, round 6", "assumed:
  check on the first print"). Changing one value must regenerate everything (parts, checks, renders, page).
- **Derived placement next.** Derive positions so the things that must not move stay put. Example: the panel's
  bottom edge height (`PANEL_Z0`) is fixed because a charging plug must fit under it; the screen's
  position (`CASE_LIFT`) is derived from it, so moving the screen up the panel moves nothing else.
- **Frames.** A world frame anchored on the host device (here X right as the operator sees it, Y to the back,
  Z up, origin at the host's top front left corner). Local frames where a sub-assembly is simple:
  - the screen frame (u right, v up the glass, n out of it): `screen_frame(tilt)` returns U, V, N;
  - the lane frame (origin on the panel's bottom edge, x = world X, v up the panel, n out of it).
  Build each feature in its own frame, then place it with `to_world(shape, origin, U, V, N)` (a `gp_Trsf`).
- **Functions per feature** (`lane()`, `side_hook(side)`, `bezel()`, `screen_cuts()` returning (cuts, adds)),
  then `build_part()` assembles: body, minus cuts, plus adds, plus small features last.
- **Stand-ins** for everything not printed (host, screen, phone, plug, cable), used by checks and renders only.
  Give them realistic shapes where they touch the design (rounded case edges, the largest connector
  envelope, cable bend radius).
- `__main__`: build, print `isValid()`, solid count, volume, bounding box, key derived numbers, export.

## Smooth bodies from 2D profiles

- Draw the side profile as a closed polygon with a radius per corner (`rounded_wire_yz(pts, radii)`), extrude
  along X (`prism_x`). One profile gives the whole body a single, calm silhouette.
- Hollow it with the same polygon offset inward: `wire.offset2D(-inset, "intersection")`, so the wall stays
  `inset` thick all the way round, including concentric rounds.
- End plates (the body's ends, continuing down as side walls) are separate prisms of the same profile,
  filleted on their outer edges *before* the union.
- For printing rear-face down, the top-back round runs out at 45 deg into the rear face (a "teardrop"), and a
  hollow's inner front face is a 45 deg plane instead of a flat ceiling.

## Fillets: the main source of invalid solids

- Wrap risky fillets: `_try_fillet(wp, edges_fn, r, what)` tries, logs "skipped" on failure and returns the
  input. Then check `isValid()`; a fillet can "succeed" and still leave an invalid solid.
- Radius < half the thinnest wall at that edge (a 1.0 mm end fillet on a 1.6 mm lip invalidated the part;
  0.6 worked).
- Fillet edges before booleans create short edges next to them. Rounding the plan corners of a tongue after
  its tip edges were filleted (leaving 0.6 mm edges) failed: fillet the long edges only, or round first.
- Filleting across faces that came from a union of touching plates segfaulted OCC: fillet each plate, then union.
- To find what broke a part, build and validate each sub-feature on its own (lane, cuts, hooks...), then
  re-add them one at a time.

## Selectors that work

- One specific edge: `w.edges("|X").edges(cq.selectors.NearestToPointSelector((x, y, z)))`.
- Edges in a region: `cq.selectors.BoxSelector(p0, p1)` (matches by centre). Several regions: `sel_a + sel_b`.
- Faces: `faces("<X or >X")`, `faces(">Z")`.
- Workplane orientation: `"XY"` normal +Z, `"YZ"` normal +X, `"XZ"` normal **-Y** (a positive extrude goes
  toward -Y; set `origin=` and extrude the other way if needed).

## Other gotchas

- A polyline's pending wire is consumed by `extrude()`; reusing the same Workplane raises "No pending wires
  present". Keep the point list and rebuild `cq.Workplane(...).polyline(pts).close()` each time.
- Coplanar faces in a boolean: offset the cutter by 0.01 to 0.3 mm. Slots and holes: overshoot the cutter
  through the material.
- Rounded holes: `cq.Workplane("XZ", origin=c).placeSketch(cq.Sketch().rect(w, h).vertices().fillet(r)).extrude(d)`.
- Tapered features (ribs with a lead-in, bevel cutters): `cq.Solid.makeLoft([w1, w2], True)` with
  `cq.Wire.makePolygon(points, close=True)` wires of equal vertex count.
- Cables: a round tube swept along a polyline with filleted corners (`sweep_tube(points, r, bend_r)` in
  `geom.py`); corners need segments longer than the bend radius allows.
- After changing anything, confirm `len(part.solids().vals()) == 1`: a feature that doesn't touch the body
  becomes a loose second solid.
- `build_part()` can take a minute: pass the built part into checks instead of rebuilding per check, run long
  scripts with a timeout, and keep stdout (results) apart from stderr (warnings).

## Sizes you can't trust: check them against a photo

Vendor size drawings are often not to scale, and their labels can be plain wrong (a "60 mm deep" dock was ~105).
Before designing to a published size, check it against everything else you have: does it fit in the stated box
size, and is it consistent with the user's photo? To measure from a photo, pick the four corners of one flat
rectangular face and fit a pinhole camera with a phone's focal length (24-26 mm equivalent: f = image diagonal
in px x 24-26 / 43.3) using `scipy.optimize.least_squares`. That gives the face's aspect ratio reliably (residual
of a few px). Then set the scale from an object of known size in the same photo (the host). Points on rounded
or occluded edges give fits that are 30+ px off; leave them out.

When a size stays uncertain, design so it doesn't matter: a tray longer than any estimate with an open end, so
only one dimension sets a stop. Name that one parameter on the report as the thing to confirm.

## Exports

- Per printed part: STEP (for CAD users), STL (`tolerance=0.02, angularTolerance=0.1`) and 3MF.
- Export small parts in their print pose (the frame face down) so the slicer gets it right without thought.
- `exports/checks.json` from the checks; `renders/assembly.glb` for the web viewer.
