"""Design-rule check for model/osint_sled.blend. Exits non-zero on any failure.

usage: blender -b --factory-startup --python scripts/check_model.py

Checks
  1. No two parts interpenetrate (BVH triangle overlap): sled, thermal layer,
     boards, pigtails, top plate, every screw, washer, pin and spring, the
     mount and the MacBook's base. Each mesh is eroded by EPS along its normals
     first, so parts that merely touch (a board on its boss, a screw in its
     tapped hole, a liner against the Mac) are not reported. Screw shanks are
     modelled at the thread's minor diameter and tapped holes at the tap drill,
     so a screw that misses its hole is a collision.
  2. Everything inside the sled stays below the top plate and above the base.
  3. Heat pipes sit flush in the base plate.
  4. Every pedestal sits on a heat pipe, except ones marked plate-only.
  5. The five KrakenSDR pigtails are the same length within tolerance.
  6. Every screw engages at least MIN_ENGAGEMENT x d of thread in metal,
     measured on the geometry (not taken from the config).
  7. The Mac is held: every jaw liner, both rear stops and both pawls touch it.
  8. The Mac slides in and out from the front without hitting anything but
     the pawls (which it pushes down).
  9. Keep-out envelopes are clear: SMA nut driver and mating plug, USB-C plugs
     at the sled, plugs in the Mac's own ports, and the lid's swing.
"""
import itertools
import json
import math
import sys
from pathlib import Path

import bpy  # must be imported before bmesh/mathutils
import bmesh
import mathutils
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sled_config import (  # noqa: E402
    BASE_T, D, HEAT_PIPES, HP_W, KRAKEN_LENGTH_TOL, MIN_ENGAGEMENT, PEDESTALS, PEDESTALS_PLATE_ONLY, TOP_Z0,
)

ROOT = Path(__file__).resolve().parents[1]
MM = 0.001
EPS = 0.03  # mm
CHECKED = ["Sled chassis", "Thermal", "Boards", "RF pigtails", "Top plate", "Fasteners", "Mount"]
RF_PREFIXES = ("Pigtail", "MHF4", "SMA bulkhead")

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "model/osint_sled.blend"))
dg = bpy.context.evaluated_depsgraph_get()
failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL", msg)


def world_verts_tris(ob, with_normals=False):
    """World-space vertices, triangles and outward vertex normals (normals are
    recomputed per connected piece, so joined or imported meshes are safe)."""
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    ev.to_mesh_clear()
    bm.transform(ob.matrix_world)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.verts.index_update()
    verts = [v.co.copy() for v in bm.verts]
    normals = [v.normal.copy() for v in bm.verts]
    if ob.get("imported"):
        # imported (STEP-tessellated) meshes have no usable inside/outside:
        # shrink those about their own centre instead
        lo, hi = bounds(verts)
        c = (lo + hi) / 2
        normals = [mathutils.Vector([(v[i] - c[i]) / max((hi[i] - lo[i]) / 2, 1e-9) for i in range(3)]) for v in verts]
    tris = [tuple(l.vert.index for l in t) for t in bm.calc_loop_triangles()]
    bm.free()
    return (verts, tris, normals) if with_normals else (verts, tris)


def bounds(verts):
    lo = mathutils.Vector([min(v[i] for v in verts) for i in range(3)])
    hi = mathutils.Vector([max(v[i] for v in verts) for i in range(3)])
    return lo, hi


def shrunk_bvh(verts, tris, normals, offset=(0, 0, 0)):
    """Erode the mesh by EPS: every vertex moves EPS inwards along its normal,
    so touching surfaces separate while holes and slots get slightly bigger."""
    lo, hi = bounds(verts)
    o = mathutils.Vector(offset)
    sv = [v - n * (EPS * MM) + o for v, n in zip(verts, normals)]
    return BVHTree.FromPolygons(sv, tris), lo + o, hi + o


def tag(name):
    """Parts of one RF chain may touch and overlap (crimp, mated connectors)."""
    if name.startswith(RF_PREFIXES):
        return name[name.find("(") + 1:name.rfind(")")]
    return None


class Part:
    def __init__(self, ob):
        self.ob = ob
        self.name = ob.name
        self.coll = ob.users_collection[0].name
        self.verts, self.tris, self.normals = world_verts_tris(ob, True)
        self.bvh, self.lo, self.hi = shrunk_bvh(self.verts, self.tris, self.normals)
        self.exact = BVHTree.FromPolygons(self.verts, self.tris)
        self.tag = tag(ob.name)


def collect(cnames, pred=lambda o: True):
    out = []
    for cname in cnames:
        for ob in bpy.data.collections[cname].all_objects:
            if ob.type in {"MESH", "CURVE"} and pred(ob):
                v, t = world_verts_tris(ob)
                if t:
                    out.append(Part(ob))
    return out


parts = collect(CHECKED)
mac = collect(["MacBook Pro 16"], lambda o: o.get("check"))
keepouts = collect(["Keep-out envelopes"])
print(f"loaded {len(parts)} parts, {len(mac)} Mac parts, {len(keepouts)} keep-out envelopes")


def boxes_apart(a, b):
    return any(a.lo[i] > b.hi[i] or b.lo[i] > a.hi[i] for i in range(3))


# 1: collisions
n_pairs = 0
for a, b in itertools.combinations(parts + mac, 2):
    if boxes_apart(a, b):
        continue
    if (a.tag and a.tag == b.tag) or (a in mac and b in mac):
        continue
    n_pairs += 1
    hits = a.bvh.overlap(b.bvh)
    if hits:
        fail(f"collision: {a.name}  <->  {b.name}  ({len(hits)} triangle pairs)")
print(f"1. collision check: {len(parts) + len(mac)} parts, {n_pairs} close pairs tested")

# 2: envelope (parts that live inside the sled)
OUTSIDE = ("Top plate", "Silicone rail", "Sled foot", "SMA bulkhead", "Exhaust deflector")
for p in parts:
    inside = p.coll in ("Sled chassis", "Thermal", "Boards", "RF pigtails") and not p.name.startswith(OUTSIDE)
    inside |= p.coll == "Fasteners" and ("HackRF" in p.name or "M2x5" in p.name)
    if inside and p.hi.z / MM > TOP_Z0 + 1e-3:
        fail(f"{p.name} reaches z={p.hi.z / MM:.2f} mm, above the top plate underside ({TOP_Z0} mm)")
    if inside and p.lo.z / MM < -1e-3:
        fail(f"{p.name} reaches below the base plate (z={p.lo.z / MM:.2f} mm)")
print("2. envelope check done")

# 3: heat pipes flush
for p in parts:
    if p.name.startswith("Heat pipe") and p.hi.z / MM > BASE_T + 1e-3:
        fail(f"{p.name} sticks out of the base plate (top at {p.hi.z / MM:.2f} mm)")


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
print("3-4. heat pipes and pedestals checked")

# 5: KrakenSDR phase matching
lengths = dict(bpy.context.scene.get("pigtail_lengths_mm", {}))
kr = [v for k, v in lengths.items() if k.startswith("Kraken")]
if len(kr) != 5:
    fail("expected 5 KrakenSDR pigtails")
elif max(kr) - min(kr) > KRAKEN_LENGTH_TOL:
    fail(f"KrakenSDR pigtails differ by {max(kr) - min(kr):.2f} mm (tolerance {KRAKEN_LENGTH_TOL} mm)")
else:
    print(f"5. KrakenSDR pigtails: {min(kr):.1f}-{max(kr):.1f} mm (spread {max(kr) - min(kr):.2f} mm)")


# 6: thread engagement, measured on the geometry
def inside(p, solid):
    if any(p[i] < solid.lo[i] - 1e-6 or p[i] > solid.hi[i] + 1e-6 for i in range(3)):
        return False
    loc, nrm, _, _ = solid.exact.find_nearest(p)
    return loc is not None and (loc - p).dot(nrm) > 0


AXIS = {"+Z": (0, 0, 1), "-Z": (0, 0, -1), "+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0)}
metal = [p for p in parts if p.coll in ("Sled chassis", "Mount") and not p.name.startswith(("Sled foot", "Proxmark", "SMA"))]
fasteners = json.loads(bpy.context.scene["fasteners"])
worst = None
per_type = {}
for f in fasteners:
    ax = mathutils.Vector(AXIS[f["axis"]])
    at = mathutils.Vector(f["at"])
    perp1 = ax.orthogonal().normalized()
    perp2 = ax.cross(perp1)
    r = f["tap"] / 2 + 0.15
    tip = at - ax * f["length"]                # ISO length: under the head, or overall for countersunk
    step = 0.1
    engaged = 0.0
    s = 0.3                                   # skip the chamfer at the tip
    started = False
    while s < f["length"]:
        c = tip + ax * s
        n_in = 0
        for k in range(6):
            a = 2 * math.pi * k / 6
            q = (c + (perp1 * math.cos(a) + perp2 * math.sin(a)) * r) * MM
            if any(inside(q, m) for m in metal):
                n_in += 1
        if n_in >= 5:
            engaged += step
            started = True
        elif started:
            break
        s += step
    engaged += 0.3 if started else 0.0
    need = MIN_ENGAGEMENT * f["d"]
    if worst is None or engaged / need < worst[1] / worst[2]:
        worst = (f["name"], engaged, need)
    key = f'{f["kind"]} {f["size"]}x{f["length"]}'
    per_type.setdefault(key, []).append(engaged)
    if engaged + 1e-6 < need:
        fail(f"{f['name']}: {engaged:.1f} mm of thread engaged, needs {need:.1f} mm ({MIN_ENGAGEMENT} x d)")
print(f"6. thread engagement: {len(fasteners)} screws, tightest {worst[0]} with {worst[1]:.1f} mm (needs {worst[2]:.1f})")
for key, es in sorted(per_type.items()):
    print(f"     {key:14s} x{len(es):3d}  engaged {min(es):.1f}-{max(es):.1f} mm")


# 7: the Mac is held
def min_dist(a, b):
    """Smallest distance from a's vertices to b's surface (mm)."""
    best = 1e9
    for v in a.verts:
        loc, _, _, d = b.exact.find_nearest(v)
        if loc is not None:
            best = min(best, d / MM)
    return best


mac_base = next(m for m in mac if m.name.startswith("MacBook base"))
holders = [p for p in parts if p.coll == "Mount" and ("liner" in p.name or "pawl" in p.name)]
for h in holders:
    d = min_dist(h, mac_base)
    if d > 0.05:
        fail(f"{h.name} does not touch the Mac (gap {d:.2f} mm)")
print(f"7. Mac held: {len(holders)} liners and pawls checked for contact")

# 8: insertion path (slide the Mac forward out of the cradle, then back)
static = [p for p in parts if p.coll in ("Mount", "Top plate", "Fasteners", "Sled chassis") and "pawl" not in p.name]
movers = [(m, m.verts, m.tris, m.normals) for m in mac]
y = 0.0
hits8 = set()
while y <= D + 10:
    for m, verts, tris, normals in movers:
        bvh, lo, hi = shrunk_bvh(verts, tris, normals, (0, -y * MM, 0))
        for s in static:
            if any(lo[i] > s.hi[i] or s.lo[i] > hi[i] for i in range(3)):
                continue
            if bvh.overlap(s.bvh):
                hits8.add((m.name, s.name, round(y, 1)))
    y += 2.0
for mname, sname, yy in sorted(hits8)[:20]:
    fail(f"sliding the Mac out: {mname} hits {sname} {yy} mm forward")
print(f"8. insertion path: Mac slid {D + 10:.0f} mm forward in 2 mm steps, {len(hits8)} hits")

# 9: keep-out envelopes
for k in keepouts:
    own = tag(k.name.replace("Keep-out SMA access", "SMA bulkhead"))
    for p in parts + mac:
        if boxes_apart(k, p):
            continue
        if own and p.tag == own:
            continue
        if p in mac and ("Mac plug" in k.name or "lid" in k.name):
            continue
        if k.bvh.overlap(p.bvh):
            fail(f"{p.name} is inside {k.name}")
print(f"9. keep-out envelopes: {len(keepouts)} checked")

if failures:
    print(f"\n{len(failures)} check(s) failed")
    sys.exit(1)
print("all checks passed")
