# Printing and mechanics: rules and formulas that held up

## Print orientation and overhangs

- Pick the orientation first, usually the biggest flat face on the bed (the mount printed rear face down;
  the frame face down). Every later feature is checked in that pose.
- Overhang check: tessellate, take the triangles whose normal points toward the bed more than 50 deg from
  vertical (allow ~2e-3 tolerance so exact 50 deg faces pass), skip faces on the bed, report the share of area.
  Aim for < 1% on the body: short ledges and small fillets only, no supports.
- Rounds that meet the bed face become teardrops (run out at 45 deg). Flat ceilings inside a hollow become
  45 deg planes.
- A feature whose end face points at the bed starts in mid-air (the tongue that stopped 5 mm short of the
  rear face): cut that end back at 45 deg in plan so each layer only steps out ~0.2 mm.
- Flexures, springs and snap arms must bend **in the layer plane**: the stress then runs along the extruded
  lines, not across layer bonds. With the body printed rear-face down (build axis Y), a finger along X bending
  sideways is good; a lip hinged at its base would peel layers.
- Small bridges (<= 3 mm) are fine; give the slicer short spans.
- PETG near warm electronics (heat deflection ~68-78 C); PLA softens ~55 C. 0.2 mm layers, **5 walls** so thin
  hooks, hinges and ribs are solid perimeters, ~20% gyroid infill, textured PEI or glue stick to release PETG.

## Clearances

| fit | per side |
|---|---|
| sliding drop-in (screen in a pocket, old design) | 0.3 mm |
| removable frame in its recess | 0.15 mm (0.05 on the side a press pushes it toward) |
| datum wall the part is pushed against | 0.05 mm |
| crush rib interference | 0.2 mm, with a 1 mm tapered lead-in at the entry |
| around a plug overmold / cable | >= 0.5 mm, 1 mm where the user's hand guides it |
| frame window round a device rim | 0.15 mm |

## Holding a device rigidly

- Solid floor under it (no gap): a touch then pushes into plastic, not into a spring. Springs behind a
  touchscreen "feel loose" to the user even at 0.3 mm travel.
- Datum walls on the side(s) the loads push toward (a side button press pushes the screen sideways; gravity
  pulls it down the slope). Crush ribs on the opposite walls push it onto the datums: no play, tolerant of
  print and vendor tolerances.
- Put ribs where the device has plain walls (not over buttons, ports, speaker grilles).
- Leave a push-out hole behind it for removal.
- The panel can meet the device at its own rim, so curved (2.5D) glass stands proud: looks tighter than a
  lip over the rim, and the gap around curved glass disappears.

## Flexure buttons (pressing a device's side buttons through 90 deg)

- A lever cut free by a U-slit, hinged on a thin skin under the face (0.6 mm), with a finger below the hinge:
  pressing the pad swings the finger's nose sideways into the button. Rotation at the stop
  `theta = nose_travel / (pivot height above the nose)`; pad travel = arm x theta; hinge strain
  = `t_hinge x theta / (2 x hinge length)` (keep ~1%).
- **Lost motion kills it.** Every play between the lever and the button eats travel: the device moving in its
  pocket, the frame moving in its recess. In the case study the user needed a 1 mm shim: device play 0.6 +
  frame play 0.3 mm. Fix the device against a datum on the side the press pushes toward, make the frame tight
  on that side, and set the nose's rest gap to ~0.
- The nose must lie within the button cap's outline (v and n), or the housing beside the cap stops it.
- A stop shelf under the pad tip limits the stroke. Keep one tuning parameter (`BTN_GAP`) on the small part.

## Snap-fit side walls and locking tongues

Wall as a cantilever: `k = 3 E I / L^3`, `I = b t^3 / 12` (b wall width, t thickness, L length).
Printed PETG: E ~ 1.8 GPa (vendor range 1.5-2.8), friction on anodised aluminium mu ~ 0.35 (0.25-0.45).

- Root strain at deflection d: `eps = 3 t d / (2 L^2)`. Repeated flexing <= ~1-1.5%; yield ~4%.
- Catch face at angle c from horizontal, wall force H:
  - seated pull-down `V = H_preload / tan c`;
  - pop-off (lift) `2 H_release (cos c + mu sin c) / (sin c - mu cos c)` (self-locking when the denominator <= 0);
  - push-on with a lead-in g from vertical: `2 H_release (tan g + mu) / (1 - mu tan g)`.
- Preload: 0.5 mm. At 1.0 mm the walls visibly splay outward.
- The real edge height decides everything: the user measured 46.0 mm where the drawing suggested 45.5. With
  0.5 mm error a shallow hook never engages.
- A ramped hook needs height: a 2.2 mm hook with a 50 deg lead-in already filled the ~4.5 mm under the edge.
  For a *locked* clip, use a tongue reaching well under the edge (8 mm, under a flat underside), 2 mm thick
  and clear of the desk, plus a short catch at the edge for the pull-down. Fit by spreading the walls by hand
  (8.5 mm, ~18 N, 1.15% strain) or sliding it on from behind.
- Rear returns (tapered tabs behind the rear corners) stop forward sliding without visible hooks.

## Stability (anything leaning or overhanging)

- Press force F square to a 40 deg panel at point P tips the assembly backward about the host's rear edge Q
  when `F (cos t (P_y - Q_y) + sin t (P_z - Q_z))` exceeds the stabilising moments
  `sum W_i (Q_y - y_i)` + clip hold x arm. Compute it for the mount on the host and for the whole host.
- A phone on a 40 deg stand is long: its CG sat right over the host's rear edge, so the Rev F hooks
  (pop-off ~9 N) let a 2 N press at the phone's top tip everything back. Locked clips fixed the mount; the
  whole host still tips at ~6 N (fine for 0.5-1 N taps).
- Sliding under a press: `F_slip = (mu W + 2 mu V) / (sin t - mu cos t)`.

## Phones, plugs and cables

- Lane depth for "an iPhone in a silicone case": iPhone 16-18 are 7.8-8.75 mm; a silicone case adds ~2.4-2.6
  mm (walls ~1.6, the front edge ~1 mm above the glass) -> 11.4 mm deep. A low edge (1.8 x 1.8 mm) right at
  the phone hides only the case's rim.
- Charging: largest USB-C overmold 12.35 x 6.5 x 16 mm plus room to bend; a closed rounded hole through the
  shelf under the port (the user preferred a hole to a gap in the edge).
- Device cable: plug + tight bend (5 mm) into a channel, a drop slot into the hollow, out through a rounded
  rear arch to the host port. Spare length winds onto two pegs (30 mm long ~ 5 turns of a 4.6 mm cable) with
  flared tips printed at 45 deg.

## Reading dimensions off published drawings

- Scale by a known overall dimension in pixels (e.g. 150 mm wide = 1725 px), then read heights, insets,
  radii. Record the result and the image in `research/` with the scale you used.
- Reviews and teardowns fill gaps (cased phone thickness, removable pads, rounded bottoms).
- Mark every assumed number "assumed: check on the first print" and list it in the report's "to confirm".

## Cables you have to store (stiff leads)

- A stiff lead wants bends of R 25 mm or more. A U-turn in a vertical plane needs 2R (50 mm) of height. If that
  height isn't there, climb sideways instead: turn 90 degrees in plan, then rise gently along the run.
- Store slack as ONE big loop round the edge of a shallow layer (a lead's diameter plus a few mm). A stiff loop
  presses outward against the fences and stays put without clips, and the middle stays open for air.
- Model the lead as a swept tube with a polyline and filleted corners (`geom.sweep_tube`). Each segment must be at
  least the sum of its neighbours' tangent lengths (R tan(angle/2)), or the sweep fails with "null magnitude" or
  "MakeSolid". A small grid search over one or two waypoints finds the most compact route that still sweeps.
- A straight plug into a rear-facing port always leaves a tail of plug length plus R behind the box. Say so, and
  name the bought fix (a 90-degree plug) rather than hiding it.

## Merging a finished part into a new one

When a new part should absorb an earlier, proven one (here a clip-on mount and a base became one chassis):
- Vendor the old model file unchanged into the new project.
- Build the new part as a union of the old part's pieces, minus its attachment features, plus the new ones.
- Keep the old part's print pose, and design every new feature to run along the build direction.
- Then check what that pose does to the new geometry. A plate that ends mid-air when printed must be extended down
  to the bed.
