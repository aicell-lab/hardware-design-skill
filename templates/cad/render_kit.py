"""Render kit: offscreen PNGs (PyVista/VTK), labelled sections, contact sheets, and the web viewer's GLB with an
'explode' animation. Generic; the project's render.py builds its scene and calls these.

    objs = [("printed part", part_wp, "#2b2d31", 0.7), ("host", host_wp, "#c8b48b", 0.45), ...]
    shot(scene(objs), OUT / "oblique.png", [(-90, -330, 300), (75, 133, 56), (0, 0, 1)])
    export_glb(objs, OUT / "assembly.glb", explode={"screen frame": [0, -35, 42], "host": [0, 0, -60]})
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

pv.OFF_SCREEN = True
BG = "#f3f2ee"                                       # matches the report page


def mesh(shape, tol=0.04):
    """CadQuery Workplane/Shape -> PolyData."""
    s = shape.val() if hasattr(shape, "val") else shape
    vs, tris = s.tessellate(tol, 0.15)
    return pv.PolyData(np.array([[p.x, p.y, p.z] for p in vs]), np.hstack([[3, *t] for t in tris]))


def scene(objs):
    """[(name, shape, hex colour, roughness)] -> render items [(mesh, colour, lighting kwargs)]."""
    return [(mesh(s), c, dict(specular=0.3 if r > 0.5 else 0.6, specular_power=20, diffuse=0.85)) for _n, s, c, r in objs]


def shot(items, path, cam, size=(1500, 1050), zoom=1.0, parallel=False, scale=None):
    """One PNG. cam = [eye, focus, up]. parallel + scale (half the view height, mm) for sections."""
    p = pv.Plotter(off_screen=True, window_size=size, lighting="none")
    p.set_background(BG)
    for m, c, kw in items:
        p.add_mesh(m, color=c, smooth_shading=True, **kw) if c else p.add_mesh(m, smooth_shading=True, **kw)
    p.add_light(pv.Light(position=(-250, -350, 450), focal_point=(80, 90, 0), intensity=0.85, light_type="scene light"))
    p.add_light(pv.Light(position=(400, -100, 250), focal_point=(80, 90, 0), intensity=0.35, light_type="scene light"))
    p.add_light(pv.Light(position=(100, 450, 300), focal_point=(80, 90, 0), intensity=0.3, light_type="scene light"))
    p.add_light(pv.Light(light_type="headlight", intensity=0.25))
    p.enable_anti_aliasing("ssaa")
    p.camera_position = cam
    if parallel:
        p.enable_parallel_projection()
    if scale:
        p.camera.parallel_scale = scale
    else:
        p.camera.zoom(zoom)
    p.screenshot(str(path))
    p.close()
    return Path(path)


def section(cam_dir, centre, up, scale, items, path, size=(1500, 1050)):
    """Flat cut view: camera along cam_dir (unit) through centre, parallel projection, half-height `scale` mm.
    Slice the objects into thin slabs (1 mm) yourself so slits show the background."""
    centre, cam_dir = np.asarray(centre, float), np.asarray(cam_dir, float)
    return shot(items, path, [tuple(centre - 300 * cam_dir), tuple(centre), tuple(up)], size, parallel=True, scale=scale)


def labels(path, centre, right, up, scale, items, size=(1500, 1050), font=44):
    """Labels with leader lines on a parallel-projection render: items = [(text, point mm, (dx, dy) px)]. The
    label sits at point + (dx, dy); dx < 0 right-aligns it. Check the result for overlaps and clipping."""
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", font)
    except OSError:
        f = ImageFont.load_default()
    k = size[1] / (2 * scale)
    centre, right, up = (np.asarray(v, float) for v in (centre, right, up))
    for text, pt, (dx, dy) in items:
        q = np.asarray(pt, float) - centre
        x, y = size[0] / 2 + k * float(q @ right), size[1] / 2 - k * float(q @ up)
        tx, ty, anchor = x + dx, y + dy, "lm" if dx >= 0 else "rm"
        d.line([(x, y), (tx, ty)], fill=(200, 70, 40), width=3)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(200, 70, 40))
        bb = d.textbbox((tx, ty), text, font=f, anchor=anchor)
        d.rectangle([bb[0] - 8, bb[1] - 6, bb[2] + 8, bb[3] + 6], fill=(255, 255, 255), outline=(200, 70, 40), width=2)
        d.text((tx, ty), text, fill=(30, 30, 34), font=f, anchor=anchor)
    im.save(path)


def contact_sheet(paths, out, cols=4, w=600):
    """Thumbnails of many renders in one JPEG, to look at them all at once."""
    ims = [Image.open(p).convert("RGB") for p in paths]
    ims = [im.resize((w, int(im.height * w / im.width))) for im in ims]
    h = max(im.height for im in ims)
    sheet = Image.new("RGB", (w * cols, h * ((len(ims) + cols - 1) // cols)), "white")
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(out, quality=85)
    return out


def export_glb(objs, path, explode=None):
    """Coloured glTF for model-viewer. One node + one material per object, both named after it (the feedback
    pins record the material name). mm -> m, Z-up -> Y-up. explode = {name: [dx, dy, dz] mm}: adds the
    'explode' animation (see add_explode)."""
    import trimesh
    from trimesh.transformations import rotation_matrix
    from trimesh.visual.material import PBRMaterial

    sc = trimesh.Scene()
    for name, shape, col, rough in objs:
        s = shape.val() if hasattr(shape, "val") else shape
        vs, tris = s.tessellate(0.05, 0.2)
        m = trimesh.Trimesh(np.array([[q.x, q.y, q.z] for q in vs]), np.array(tris), process=False)
        srgb = [int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]     # glTF wants linear
        m.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(name=name, baseColorFactor=lin + [1.0],
                                                                       metallicFactor=0.0, roughnessFactor=rough))
        sc.add_geometry(m, node_name=name, geom_name=name)
    sc.apply_transform(rotation_matrix(-np.pi / 2, [1, 0, 0]) @ np.diag([1e-3] * 3 + [1]))
    glb = sc.export(file_type="glb", include_normals=True)
    Path(path).write_bytes(add_explode(glb, explode) if explode else glb)
    return Path(path)


def add_explode(glb, offsets):
    """Hang every part under one 'assembly' node carrying the mm -> m, Z-up -> Y-up matrix (animated nodes must
    not have a matrix), and add an 'explode' animation (0 -> 1 s, LINEAR) moving each listed part by its offset
    (mm, in the assembly's frame). Scrub it with model-viewer's currentTime (templates/feedback/viewer.js)."""
    jl = struct.unpack("<I", glb[12:16])[0]
    j = json.loads(glb[20:20 + jl])
    bl = struct.unpack("<I", glb[20 + jl:24 + jl])[0]
    binary = bytearray(glb[28 + jl:28 + jl + bl])
    parts = list(range(len(j["nodes"])))
    matrix = j["nodes"][0]["matrix"]
    for n in j["nodes"]:
        n.pop("matrix", None)
    j["nodes"].append({"name": "assembly", "matrix": matrix, "children": parts})
    j["scenes"][j.get("scene", 0)]["nodes"] = [len(j["nodes"]) - 1]

    def accessor(data, count, kind, lo=None, hi=None):
        binary.extend(b"\0" * (-len(binary) % 4))
        j["bufferViews"].append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data)})
        binary.extend(data)
        acc = {"bufferView": len(j["bufferViews"]) - 1, "componentType": 5126, "count": count, "type": kind}
        if lo is not None:
            acc.update(min=lo, max=hi)
        j["accessors"].append(acc)
        return len(j["accessors"]) - 1
    times = accessor(struct.pack("<2f", 0.0, 1.0), 2, "SCALAR", [0.0], [1.0])
    samplers, channels = [], []
    for i in parts:
        d = offsets.get(j["nodes"][i]["name"])
        if d:
            samplers.append({"input": times, "output": accessor(struct.pack("<6f", 0, 0, 0, *d), 2, "VEC3"),
                             "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": i, "path": "translation"}})
    j["animations"] = [{"name": "explode", "samplers": samplers, "channels": channels}]
    binary.extend(b"\0" * (-len(binary) % 4))
    j["buffers"][0]["byteLength"] = len(binary)
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(js) + len(binary)) + struct.pack("<I4s", len(js), b"JSON") + js
            + struct.pack("<I4s", len(binary), b"BIN\0") + bytes(binary))


def explode_for_page(offsets_mm):
    """The same offsets in glTF metres (Y-up), for window.EXPLODE.offsets on the report page."""
    return {k: [round(x / 1000, 5), round(z / 1000, 5), round(-y / 1000, 5)] for k, (x, y, z) in offsets_mm.items()}
