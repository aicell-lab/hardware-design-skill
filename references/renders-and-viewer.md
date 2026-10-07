# Renders, the 3D model for the web, and the explode view

## Offscreen renders (PyVista / VTK, EGL)

`templates/cad/render_kit.py`: `mesh()`, `shot()`, `labels()`, `export_glb()`, `add_explode()`.

- A `scene()` list of (mesh, colour, lighting kwargs) per object: printed parts dark grey (#2b2d31), the
  removable part slightly lighter when shown apart, the host in a neutral tan, device black, cables white.
  The scene background matches the page (#f3f2ee).
- Standard set (1500 x 1050): oblique front (the user marks this one up most), close-up of the key area,
  operator view, side, rear, front left/right, part alone, part from below, small parts in their print pose,
  use cases (charging, cable storage as a cutaway), exploded still, labelled sections.
- **Look at every render** before shipping: build a contact sheet (4 x 3 thumbnails) and view it, then
  render close-ups of whatever changed. Views that look wrong are usually camera problems: a face parallel
  to the panel looks like a top face from above.
- Cut sections explain mechanisms better than any 3D view:
  - slice a **thin slab** (1 mm) so slits and gaps show the background instead of the far wall;
  - slice the second object just behind the first (1.2-2.2 mm) so the cut part draws in front of it;
  - parallel projection, set `camera.parallel_scale` (half the view height, mm) for a known scale;
  - add labels with leader lines (`labels(png, centre, right, up, scale, [(text, point_mm, (dx, dy))])`):
    44 px DejaVuSans in white boxes, then check they don't overlap or run off the edge.
- Keep the same image size for figures that share a grid, or the captions misalign.
- Small JPEG copies (~900 px, quality ~84) for chat cards; the chat proxy rejects large bodies.

## GLB for model-viewer

- One node and one material per object, **both named after the object** ("printed part", "screen frame",
  "DGX Spark", "phone"...). The feedback pins record `materialFromPoint().name`, so names must read well.
- glTF wants linear colours: convert sRGB hex to linear for `baseColorFactor`, or everything looks washed out.
- Transform mm, Z-up to m, Y-up: rotate -90 deg about X, scale 0.001. Model coordinates then map back to CAD
  as `[x*1000, -z*1000, y*1000]` (the feedback server does this).

## Explode view (assembled <-> exploded)

The user asked for an explode option "so all the parts can be individually seen and inspected" (their example
page used a custom WebGL viewer with per-part explode vectors and an eased toggle). With model-viewer:

1. **Offsets per object** (mm, world), each along the way the part goes on: the frame and then the device out
   of the panel along its normal (frame 55 mm, device 28 mm), the phone out of its lane (40 mm), the host
   down (60 mm). Cables and plugs stay with the body. Keep them in the model script (`explode_offsets()`).
2. **Bake them into the GLB** (`add_explode(glb, offsets)`): hang every part node under one `assembly` node
   that carries the mm-to-m / Z-to-Y matrix (animated nodes must not have a matrix), then add an animation
   named `explode` (0 -> 1 s, LINEAR) with a translation channel per moving part, 0 -> offset in mm (the
   parent's frame). Writing the GLB by hand: JSON chunk padded with spaces, BIN chunk padded with zeros,
   new bufferViews/accessors for the times (with min/max) and the vec3 outputs.
3. **Scrub it** from `viewer.js` (templates/feedback/viewer.js): on `load`, set `animationName = "explode"`,
   `play()`, and `pause()` ~150 ms later (pausing in the same tick leaves the clip unset and `currentTime`
   does nothing). Each frame ease `amount += (target - amount) * 0.12` and set
   `currentTime = amount * duration * 0.999`: **the clip loops, so `currentTime = duration` wraps to 0** and
   "exploded" shows the assembled pose.
4. A button "Explode / Assemble" at the viewer's **bottom left** (the feedback panel covers the top right).
5. Feedback pins follow their parts: `window.EXPLODE = {amount, offsets (glTF m)}`, `viewer.js` fires
   `fb-explode`; the widget moves each hotspot with `updateHotspot()` and stores new pins in the assembled
   pose (hit position minus the clicked part's offset x amount), so CAD coordinates stay true.
6. Test in a real browser: the button appears, `currentTime` ends near 0.999, the parts visibly move, a pin
   placed while exploded is stored at the assembled position and returns there on Assemble.
