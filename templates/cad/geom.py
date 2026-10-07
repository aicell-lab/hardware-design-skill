"""Small geometry helpers shared by the mount, checks and renders (CadQuery 2.8 / OCP 7.9)."""
from __future__ import annotations

import math

import cadquery as cq
import numpy as np


def rrect_prism(w, h, t, r, centered=True):
    """Rounded-rectangle prism in local XY, extruded +Z by t. Origin at centre of the bottom face."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3)
    sk = cq.Sketch().rect(w, h)
    if r > 0:
        sk = sk.vertices().fillet(r)
    wp = cq.Workplane("XY").placeSketch(sk).extrude(t)
    if not centered:
        wp = wp.translate((w / 2, h / 2, 0))
    return wp


def rrect_frustum(w, h, r, z0, grow, z1):
    """Ruled loft from a w x h rounded rectangle at z0 to one `grow` larger per side at z1 (bevel cutter)."""
    def wire(w_, h_, r_, z):
        return rrect_prism(w_, h_, 1.0, r_).faces("<Z").val().outerWire().translate(cq.Vector(0, 0, z))
    return cq.Workplane().add(cq.Solid.makeLoft([wire(w, h, r, z0), wire(w + 2 * grow, h + 2 * grow, r + grow, z1)],
                                                True))


def rounded_wire_yz(pts, radii, x=0.0):
    """Closed convex (y, z) polygon at X = x, corner i rounded to radii[i] (0 = sharp), as a cq.Wire."""
    P = [np.asarray(p, float) for p in pts]
    n = len(P)
    corners = []                                   # (arc start, arc mid or None, arc end) per vertex
    for i in range(n):
        p, a, b = P[i], P[i - 1], P[(i + 1) % n]
        if radii[i] <= 0:
            corners.append((p, None, p))
            continue
        da, db = (a - p) / np.linalg.norm(a - p), (b - p) / np.linalg.norm(b - p)
        th = math.acos(max(-1.0, min(1.0, float(np.dot(da, db)))))
        d = radii[i] / math.tan(th / 2)
        bis = (da + db) / np.linalg.norm(da + db)
        corners.append((p + da * d, p + bis * (radii[i] / math.sin(th / 2) - radii[i]), p + db * d))
    wp = cq.Workplane("YZ", origin=(x, 0, 0)).moveTo(*corners[0][2])
    cur = corners[0][2]
    for i in list(range(1, n)) + [0]:
        t1, mid, t2 = corners[i]
        if np.linalg.norm(t1 - cur) > 1e-6:
            wp = wp.lineTo(*t1)
        if mid is not None:
            wp = wp.threePointArc(tuple(mid), tuple(t2))
        cur = t2
    return wp.close().val()


def prism_x(wire, x0, x1):
    """Extrude a wire lying in a YZ plane along X from x0 to x1."""
    w = wire.translate(cq.Vector(x0 - wire.Center().x, 0, 0))
    return cq.Workplane().add(cq.Solid.extrudeLinear(cq.Face.makeFromWires(w), cq.Vector(x1 - x0, 0, 0)))


def loft_x(wire_a, wire_b):
    """Ruled loft between two section wires (same edge count) lying in YZ planes."""
    return cq.Workplane().add(cq.Solid.makeLoft([wire_a, wire_b], True))


def rounded_prism_yz(pts, radii, x0, x1):
    """Closed convex (y, z) polygon, corner i rounded to radii[i] (0 = sharp), extruded along X from x0 to x1."""
    return prism_x(rounded_wire_yz(pts, radii), x0, x1)




def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def frame_matrix(origin, u, v, n):
    """4x4 matrix mapping local (x=u, y=v, z=n) to world."""
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = u, v, n, origin
    return m


def to_world(shape_or_wp, origin, u, v, n):
    """Place a local-frame solid into the world using an orthonormal frame (rigid motion)."""
    from OCP.gp import gp_Trsf

    shape = shape_or_wp.val() if isinstance(shape_or_wp, cq.Workplane) else shape_or_wp
    tr = gp_Trsf()
    tr.SetValues(float(u[0]), float(v[0]), float(n[0]), float(origin[0]),
                 float(u[1]), float(v[1]), float(n[1]), float(origin[1]),
                 float(u[2]), float(v[2]), float(n[2]), float(origin[2]))
    return shape.moved(cq.Location(tr))


def screen_frame(tilt_deg):
    """Screen-local axes in world: u right, v up-the-glass (UI up), n out of the glass."""
    t = math.radians(tilt_deg)
    u = np.array([1.0, 0.0, 0.0])
    v = np.array([0.0, math.cos(t), math.sin(t)])
    n = np.array([0.0, -math.sin(t), math.cos(t)])
    return u, v, n


def solid(x):
    if isinstance(x, cq.Workplane):
        vals = [v for v in x.vals() if isinstance(v, cq.Shape)]
        return vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
    return x


def volume(x):
    s = solid(x)
    return s.Volume() if s is not None else 0.0


def common_volume(a, b):
    """Volume of the intersection of two solids (0 when they only touch)."""
    sa, sb = solid(a), solid(b)
    try:
        inter = sa.intersect(sb)
        return inter.Volume()
    except Exception:
        return float("nan")


def min_distance(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape

    d = BRepExtrema_DistShapeShape(solid(a).wrapped, solid(b).wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


def bbox(x):
    bb = solid(x).BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def sweep_tube(points, radius, bend_radius):
    """Round tube along a polyline with filleted corners (bend_radius at each vertex).

    Returns (solid, centreline_wire, min_bend_radius_used)."""
    pts = [np.asarray(p, float) for p in points]
    # build a path of straight segments + arcs (fillet corners in 3D)
    edges = []
    cur = pts[0]
    min_r = math.inf
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d1 = (b - a) / np.linalg.norm(b - a)
        d2 = (c - b) / np.linalg.norm(c - b)
        ang = math.acos(max(-1.0, min(1.0, float(np.dot(d1, d2)))))
        if ang < 1e-6:
            continue
        tlen = bend_radius * math.tan(ang / 2)
        p1 = b - d1 * tlen
        p2 = b + d2 * tlen
        # arc midpoint
        bis = (d2 - d1)
        bis /= np.linalg.norm(bis)
        centre = b + bis * (bend_radius / math.cos(ang / 2))
        mid = centre + ((b - centre) / np.linalg.norm(b - centre)) * bend_radius
        if np.linalg.norm(p1 - cur) > 1e-6:
            edges.append(cq.Edge.makeLine(cq.Vector(*cur), cq.Vector(*p1)))
        edges.append(cq.Edge.makeThreePointArc(cq.Vector(*p1), cq.Vector(*mid), cq.Vector(*p2)))
        cur = p2
        min_r = min(min_r, bend_radius)
    if np.linalg.norm(pts[-1] - cur) > 1e-6:
        edges.append(cq.Edge.makeLine(cq.Vector(*cur), cq.Vector(*pts[-1])))
    wire = cq.Wire.assembleEdges(edges)
    d0 = (pts[1] - pts[0]) / np.linalg.norm(pts[1] - pts[0])
    circ = cq.Wire.makeCircle(radius, cq.Vector(*pts[0]), cq.Vector(*d0))
    tube = cq.Solid.sweep(circ, [], wire, makeSolid=True, isFrenet=False, transitionMode="round")
    return tube, wire, min_r
