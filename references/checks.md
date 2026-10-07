# Digital checks (`cad/checks.py` -> `exports/checks.json`)

The report reads every number from `checks.json`; never copy numbers by hand. Helpers:
`templates/cad/checks_kit.py`.

## Collisions

- Exact B-rep intersection volume between the part and every other object: host, device, plug, cable,
  phone envelopes, the second printed part. Report `0 mm3` or the boxes of what overlaps
  (`[xmin, xmax, ymin, ymax, zmin, zmax]` per solid), so you can see *where*.
- Intended contacts get their own key: `"part_vs_host_mm3 (intended: hook preload)"`, `"case_vs_part_mm3
  (intended: crush ribs)"`. Also check "outside the intended features = 0": intersect with the intended
  features alone and subtract.
- User-side objects as envelopes over their range: phones at the thinnest that should click and the
  thickest that should fit, the largest standard plug plus its bend, a longer cable wound N turns round the
  storage pegs, a button cap model.

## Assembly paths

- Move the inserted part along its insertion path and check at each step (`dn = 20, 10, 4, 1, 0` mm out of
  the pocket): only the intended features may touch on the way in.
- Removable parts in their fitted position against everything (frame vs body, screen, plug, cable, host).

## Mechanisms

- Turn a lever through its stroke (`0, 0.5, 1 x theta_stop`) and measure how far the nose pushes into the
  button (geometry, not a linear estimate: the first linear estimate was wrong). Bisect the angle where it
  touches and where it reaches the switch travel; convert to pad travel. Check the lever against everything
  else at the stop.
- Springs, ribs, fingers: stiffness, force at the working deflection, root strain.

## Print orientation

- Overhang share (> 50 deg) for each part in its print pose; list a sample of the offending locations so you
  can find them (a new feature that starts mid-air shows up here).

## Load cases the user cares about

- Clip: wall stiffness, seated pull-down, push-on / spread force, hold or pop-off, strain.
- Tip-over: the press at the leaning object's top that tips the mount, and the whole host (see
  `print-and-mechanics.md`); compare with the previous revision when that was the complaint.
- Slide: press force to slide the mount on the host.

## Habits

- Build the part once and pass it to the checks (a full build takes ~1 min).
- Re-run the checks after every geometry change, before rendering and before writing the reply.
- When a check fails, find the overlap's box, then build sub-features on their own to see which one causes
  it (a concave 0.4 mm fillet under a phone's sharp edge showed as two thin strips).
