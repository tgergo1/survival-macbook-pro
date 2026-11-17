"""Design-rule check for model/osint_sled.blend. Exits non-zero on any failure.

usage: python scripts/check_model.py

Checks
  1. No two parts of the sled interpenetrate (BVH triangle overlap). Each mesh
     is shrunk by EPS on every side first, so parts that merely touch (a board
     resting on its pocket wall, a pad on a pedestal) are not reported.
  2. Everything inside the sled stays below the top plate and above the base.
  3. Heat pipes sit flush in the base plate (no part of a pipe above it).
  4. Every pedestal sits on a heat pipe, except ones marked plate-only.
  5. The five KrakenSDR pigtails are the same length within tolerance.
"""
import itertools
import sys
from pathlib import Path

import bpy  # must be imported before mathutils
import mathutils
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sled_config import (  # noqa: E402
    BASE_T, HEAT_PIPES, HP_W, KRAKEN_LENGTH_TOL, PEDESTALS, PEDESTALS_PLATE_ONLY, TOP_Z0,
)

ROOT = Path(__file__).resolve().parents[1]
MM = 0.001
EPS = 0.03  # mm
CHECKED = ["Sled chassis", "Thermal", "Boards", "RF pigtails", "Top plate"]

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "model/osint_sled.blend"))
dg = bpy.context.evaluated_depsgraph_get()
failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL", msg)


def world_verts_tris(ob):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    me.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    ev.to_mesh_clear()
    return verts, tris


def shrunk_bvh(verts, tris):
    lo = mathutils.Vector([min(v[i] for v in verts) for i in range(3)])
    hi = mathutils.Vector([max(v[i] for v in verts) for i in range(3)])
    c = (lo + hi) / 2
    ext = hi - lo
    s = [max(0.0, 1 - 2 * EPS * MM / e) if e > 4 * EPS * MM else 1.0 for e in ext]
    sv = [mathutils.Vector((c.x + (v.x - c.x) * s[0], c.y + (v.y - c.y) * s[1], c.z + (v.z - c.z) * s[2])) for v in verts]
    return BVHTree.FromPolygons(sv, tris), lo, hi


def tag(name):
    """'Pigtail (Kraken CH0)' -> 'Kraken CH0': parts that belong to one RF chain may touch."""
    return name[name.find("(") + 1:name.rfind(")")] if "(" in name else None


objs = []
for cname in CHECKED:
    for ob in bpy.data.collections[cname].all_objects:
        if ob.type in {"MESH", "CURVE"} and not ob.hide_render:
            verts, tris = world_verts_tris(ob)
            if tris:
                bvh, lo, hi = shrunk_bvh(verts, tris)
                objs.append((ob.name, bvh, lo, hi))

# 1 + 2: collisions and envelope
for name, _, lo, hi in objs:
    in_sled = not name.startswith(("Top plate", "Rubber rail", "Sled foot", "SMA", "Exhaust deflector"))
    if in_sled and hi.z / MM > TOP_Z0 + 1e-3:
        fail(f"{name} reaches z={hi.z / MM:.2f} mm, above the top plate underside ({TOP_Z0} mm)")
n_pairs = 0
for (na, ba, la, ha), (nb, bb, lb, hb) in itertools.combinations(objs, 2):
    if any(la[i] > hb[i] or lb[i] > ha[i] for i in range(3)):
        continue
    ta, tb = tag(na), tag(nb)
    if ta and ta == tb:
        continue
    n_pairs += 1
    hits = ba.overlap(bb)
    if hits:
        fail(f"collision: {na}  <->  {nb}  ({len(hits)} triangle pairs)")
print(f"collision check: {len(objs)} parts, {n_pairs} close pairs tested")

# 3: heat pipes flush
for name, _, lo, hi in objs:
    if name.startswith("Heat pipe") and hi.z / MM > BASE_T + 1e-3:
        fail(f"{name} sticks out of the base plate (top at {hi.z / MM:.2f} mm)")

# 4: pedestals on heat pipes
def seg_hits_rect(p, q, rect, half_w):
    x0, y0, x1, y1 = rect
    for k in range(101):
        t = k / 100
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x0 - half_w <= x <= x1 + half_w and y0 - half_w <= y <= y1 + half_w:
            return True
    return False


for pname, *rect in PEDESTALS:
    on_pipe = any(seg_hits_rect(p, q, rect, -HP_W / 4) for _, pts in HEAT_PIPES for p, q in zip(pts, pts[1:]))
    if not on_pipe and pname not in PEDESTALS_PLATE_ONLY:
        fail(f"pedestal {pname} is not on a heat pipe")

# 5: KrakenSDR phase matching
lengths = dict(bpy.context.scene.get("pigtail_lengths_mm", {}))
kr = [v for k, v in lengths.items() if k.startswith("Kraken")]
if len(kr) != 5:
    fail("expected 5 KrakenSDR pigtails")
elif max(kr) - min(kr) > KRAKEN_LENGTH_TOL:
    fail(f"KrakenSDR pigtails differ by {max(kr) - min(kr):.2f} mm (tolerance {KRAKEN_LENGTH_TOL} mm)")
else:
    print(f"KrakenSDR pigtails: {min(kr):.1f}-{max(kr):.1f} mm (spread {max(kr) - min(kr):.2f} mm)")

if failures:
    print(f"\n{len(failures)} check(s) failed")
    sys.exit(1)
print("all checks passed")
