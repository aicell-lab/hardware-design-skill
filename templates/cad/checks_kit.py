"""Checks kit: collisions, overhangs in the print pose, and the small mechanics formulas used for clips,
springs, levers and stability. Generic; the project's checks.py composes these and writes checks.json.

Units: mm, N, MPa. Printed PETG: E ~ 1800 MPa, mu on anodised aluminium ~ 0.35 (0.25-0.45).
"""
from __future__ import annotations

import math

import numpy as np

E_PETG = 1800.0


# ------------------------------------------------------------------ collisions
def vol(a, b):
    """Exact intersection volume of two CadQuery objects (0 when they only touch; nan if OCC fails)."""
    try:
        sa = a.val() if hasattr(a, "val") else a
        sb = b.val() if hasattr(b, "val") else b
        return sa.intersect(sb).Volume()
    except Exception:  # noqa: BLE001
        return float("nan")


def boxes(shape):
    """Bounding boxes [xmin, xmax, ymin, ymax, zmin, zmax] of each solid in an intersection: *where* it overlaps."""
    s = shape.val() if hasattr(shape, "val") else shape
    return [[round(v, 1) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]
            for b in (so.BoundingBox() for so in s.Solids())]


def outside(a, b, intended):
    """Overlap of a and b that is NOT inside the intended features (should be 0)."""
    return vol(a, b) - vol(a, intended)


# ------------------------------------------------------------------ printing
def overhangs(shape, up=(0.0, 0.0, 1.0), max_angle=50.0, tol=2e-3):
    """Area facing the bed more than max_angle from vertical, with the part in its print pose given by `up`
    (the build direction in the shape's frame; e.g. (0, -1, 0) when the rear face, max Y, lies on the bed).
    Returns (bad area mm2, total area mm2, centres of the bad triangles)."""
    s = shape.val() if hasattr(shape, "val") else shape
    vs, tris = s.tessellate(0.05, 0.2)
    V, T = np.array([[p.x, p.y, p.z] for p in vs]), np.array(tris)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    n = np.cross(b - a, c - a)
    area = np.linalg.norm(n, axis=1) / 2
    up = np.asarray(up, float) / np.linalg.norm(up)
    nz = (n @ up) / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    h = ((a + b + c) / 3) @ up
    bad = (nz < -math.cos(math.radians(90 - max_angle)) - tol) & (h > (V @ up).min() + 0.3)   # skip the bed
    return float(area[bad].sum()), float(area.sum()), ((a + b + c) / 3)[bad]


# ------------------------------------------------------------------ cantilevers (walls, fingers, leaf springs)
def cantilever_k(b, t, L, E=E_PETG):
    """Tip stiffness (N/mm) of a rectangular cantilever: width b, thickness t (bending), length L."""
    return 3 * E * (b * t ** 3 / 12) / L ** 3


def root_strain(t, d, L):
    """Root strain (fraction) at tip deflection d. Keep <= ~0.01-0.015 for repeated flexing of PETG."""
    return 3 * t * d / (2 * L ** 2)


# ------------------------------------------------------------------ clips
def clip(k, preload, release, catch_deg, lead_deg=None, mu=0.35, walls=2):
    """Side-wall snap clip. preload: wall still flexed when seated; release: total flex as the catch clears.
    Returns pull-down when seated, lift to pop off (inf = self-locking), push-on force (if a lead-in)."""
    c = math.radians(catch_deg)
    den = math.sin(c) - mu * math.cos(c)
    out = dict(pull_down=walls * k * preload / math.tan(c),
               pop_off=walls * k * release * (math.cos(c) + mu * math.sin(c)) / den if den > 0 else math.inf)
    if lead_deg is not None:
        g = math.radians(lead_deg)
        out["push_on"] = walls * k * release * (math.tan(g) + mu) / (1 - mu * math.tan(g))
    return out


# ------------------------------------------------------------------ stability
def tip_press(press_pt, panel_deg, pivot, weights, hold=0.0, hold_y=None):
    """Press force (N), square to a panel tilted panel_deg, at press_pt (y, z) that tips the assembly backward
    about pivot (y, z). weights = [(W N, y of its CG)]; hold = clip force resisting lift at y = hold_y."""
    s, c = math.sin(math.radians(panel_deg)), math.cos(math.radians(panel_deg))
    stab = sum(W * (pivot[0] - y) for W, y in weights) + (hold * (pivot[0] - hold_y) if hold else 0.0)
    arm = c * (press_pt[0] - pivot[0]) + s * (press_pt[1] - pivot[1])
    return stab / arm if arm > 0 else math.inf


def slide_press(weight, pull_down, panel_deg, mu=0.35):
    """Press force square to the panel that slides the mount backward on the host (no pads)."""
    t = math.radians(panel_deg)
    den = math.sin(t) - mu * math.cos(t)
    return (mu * weight + mu * pull_down) / den if den > 0 else math.inf
