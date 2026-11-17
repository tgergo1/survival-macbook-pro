"""Build the caseless OSINT sled in Blender (bpy 5.2 or later).

All geometry comes from sled_config.py (millimetres in code, converted to
metres for Blender). Sled origin = front-left-bottom corner of the base plate;
x = right, y = towards the rear (hinge), z = up. Standard parts (screws, SMA,
MHF4, USB-C, springs, pins) come from parts.py.

usage: blender -b --factory-startup --python scripts/build_sled.py
       (or: python scripts/build_sled.py with the bpy module installed)
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402  must be imported before bmesh/mathutils, which it provides
import bmesh  # noqa: E402
import mathutils  # noqa: E402

import parts  # noqa: E402
from geom import (MM, apply_tf, boolean, boolean_cut, cut_many, cyl, join, lathe, link, mat,  # noqa: E402
                  place, poly_curve, polyline_length, prism, rbox, rounded_rect, rounded_slab, set_stage,
                  smooth_by_angle)
from sled_config import (  # noqa: E402
    BASE_T, BLOWER, BLOWER_C, BOARDS, BOARD_MAX_X, BOSS_R, CABLE_DESCENT_X, CORNER_R,
    CORNER_R_CABLE, COAX_R, D, EXHAUST, FINS, FLANGE_T, FLANGE_W, FOOT_H, HACKRF, HACKRF_HOLES,
    HACKRF_KEEP_X, HEAT_PIPES, HOLE_INSET, HP_T, HP_W, JAWS, JAW_SCREWS, JAW_SCREW_X, JAW_T, LANES,
    LATCH, LID_KEEPOUT, LINER_T, MAC, MAC_FOOT_T, MAC_PLUG_LEN, MAC_PORTS, MAC_PORT_CZ, MAC_Z,
    MHF4_RECEPT_H, PAD_GAP, PAD_T, PCB_T, PCB_TOP, PCB_Z0, PEDESTALS, PLENUM, RAIL_T,
    REAR_RETURN, SIDE_INTAKE, SILICONE_RAILS, SMA_FERRULE_X, SMA_HOLE_FLAT, SMA_HOLE_R, TOP_SCREWS,
    TOP_Z0, TOP_Z1, USBC, USBC_PORTS, W, WALL_BOSS_R, WALL_T, Z_HIGH, Z_LOW, Z_SMA,
)

ROOT = Path(__file__).resolve().parents[1]
HACKRF_GLB = str(ROOT / "model/assets/hackrf-one.glb")
FLIPPER_GLB = str(ROOT / "model/assets/flipper-zero.glb")
OUT_BLEND = str(ROOT / "model/osint_sled.blend")
T = parts.THREAD

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


C_SLED = coll("Sled chassis")
C_THERMAL = coll("Thermal")
C_BOARDS = coll("Boards")
C_CABLES = coll("RF pigtails")
C_TOP = coll("Top plate")
C_FAST = coll("Fasteners")
C_MOUNT = coll("Mount")
C_MAC = coll("MacBook Pro 16")
C_EXT = coll("External cables")
C_KEEP = coll("Keep-out envelopes")
C_REF = coll("Reference - real assets")
C_STAGE = coll("Stage")
set_stage(C_STAGE)
C_KEEP.hide_render = True

# ---------------------------------------------------------------- materials
M = {
    "alu": mat("Aluminium 6061 bead-blasted", (0.62, 0.63, 0.65), 1.0, 0.36, bump=0.25, bump_scale=2500),
    "alu_mill": mat("Aluminium 6061 milled", (0.70, 0.71, 0.72), 1.0, 0.22, aniso=0.6),
    "alu_dark": mat("Anodised aluminium black", (0.018, 0.018, 0.02), 0.0, 0.55, bump=0.15, bump_scale=3000),
    "copper": mat("Copper heat pipe", (0.93, 0.52, 0.32), 1.0, 0.22),
    "pcb": mat("PCB soldermask", (0.012, 0.13, 0.055), 0.0, 0.35, coat=0.6, bump=0.08, bump_scale=600),
    "pcb_black": mat("PCB black", (0.02, 0.02, 0.025), 0.0, 0.35, coat=0.6, bump=0.08, bump_scale=600),
    "pcb_purple": mat("PCB purple", (0.18, 0.06, 0.28), 0.0, 0.35, coat=0.6, bump=0.08, bump_scale=600),
    "can": mat("Tin shield can", (0.80, 0.80, 0.80), 1.0, 0.28),
    "chip": mat("IC package", (0.03, 0.03, 0.03), 0.0, 0.55),
    "gold": mat("Gold plating", (1.0, 0.77, 0.34), 1.0, 0.2),
    "nickel": mat("Nickel plating", (0.75, 0.73, 0.70), 1.0, 0.25),
    "ptfe": mat("PTFE", (0.92, 0.92, 0.90), 0.0, 0.45),
    "coax": mat("Micro-coax 1.13", (0.15, 0.15, 0.16), 0.0, 0.6),
    "coax_kraken": mat("Micro-coax 1.13 phase-matched", (0.55, 0.12, 0.10), 0.0, 0.55),
    "rubber": mat("Rubber", (0.02, 0.02, 0.02), 0.0, 0.85),
    "silicone": mat("Silicone friction rail", (0.03, 0.03, 0.032), 0.0, 0.7),
    "tpu": mat("TPU 85A liner", (0.06, 0.06, 0.065), 0.0, 0.75),
    "pom": mat("POM (Delrin) pawl", (0.85, 0.85, 0.82), 0.0, 0.4),
    "plastic": mat("Blower plastic", (0.04, 0.04, 0.045), 0.0, 0.5),
    "pad": mat("Thermal pad", (0.55, 0.35, 0.65), 0.0, 0.7),
    "steel": mat("Stainless steel", (0.72, 0.72, 0.74), 1.0, 0.28),
    "screw": mat("Stainless A2 screw", (0.70, 0.70, 0.72), 1.0, 0.3),
    "spring": mat("Spring steel", (0.55, 0.56, 0.58), 1.0, 0.3),
    "window": mat("Polycarbonate window", (0.85, 0.9, 1.0), 0.0, 0.05, transmission=1.0),
    "mac": mat("MacBook space black", (0.028, 0.028, 0.032), 0.75, 0.32, bump=0.12, bump_scale=4000),
    "key": mat("Keycaps", (0.012, 0.012, 0.012), 0.0, 0.7),
    "glass": mat("Display bezel", (0.004, 0.004, 0.005), 0.0, 0.08, coat=1.0),
    "screen": mat("Display", (0.01, 0.012, 0.02), 0.0, 0.06, emission=(0.06, 0.13, 0.26)),
    "port": mat("Port interior", (0.01, 0.01, 0.01), 0.0, 0.8),
    "floor": mat("Floor", (0.30, 0.31, 0.32), 0.0, 0.55),
    "flipper": mat("Flipper Zero shell", (0.92, 0.92, 0.90), 0.0, 0.45),
    "keepout": mat("Keep-out", (1.0, 0.1, 0.1), 0.0, 0.5, alpha=0.3),
}


def screw(*a, **k):
    return parts.screw(*a, materials=M, stage=C_STAGE, **k)


def tap_hole(x, y, z_top, depth, size):
    """Cutter for a tapped hole (tap-drill diameter) going down from z_top."""
    return cyl("cut", x, y, z_top - depth / 2 + 0.05, T[size]["tap"] / 2, depth + 0.1, None, C_STAGE, verts=20)


def clr_hole(x, y, z0, z1, size):
    return cyl("cut", x, y, (z0 + z1) / 2, T[size]["clr"] / 2, z1 - z0 + 0.2, None, C_STAGE, verts=20)


def mirror_x(x):
    return W - x


# ================================================================ chassis
base = rbox("Base plate (6061, 2.5 mm)", 0, 0, 0, W, D, BASE_T, M["alu"], C_SLED, r=CORNER_R, bevel=0.4)
boolean_cut(base, rbox("cut", 188, 12, -1, 248, 54, BASE_T + 1, None, C_SLED, r=4))
rbox("Proxmark RF window (PC)", 188, 12, 0.2, 248, 54, BASE_T - 0.2, M["window"], C_SLED, r=4)

wall_z0, wall_z1 = BASE_T, TOP_Z0
walls = rbox("Side walls", 0, 0, wall_z0, W, D, wall_z1, M["alu"], C_SLED, r=CORNER_R, bevel=0.3)
boolean_cut(walls, rbox("cut", WALL_T, WALL_T, wall_z0 - 1, W - WALL_T, D - WALL_T, wall_z1 + 1, None, C_SLED, r=6))

# bosses inside the wall: top-plate screws, jaw screws (vertical) and latch screws (horizontal)
JAW_SCREW_PTS = []
for j in JAWS:
    x = JAW_SCREW_X if j["side"] == "L" else W - JAW_SCREW_X
    JAW_SCREW_PTS += [(j["name"], x, y) for y in JAW_SCREWS[j["name"]]]
LATCH_SCREW_PTS = []
for side in "LR":
    for (sx, sz) in LATCH["screws"]:
        LATCH_SCREW_PTS.append((side, sx if side == "L" else W - sx, sz))
bosses = [cyl("boss", x, y, (wall_z0 + wall_z1) / 2, WALL_BOSS_R, wall_z1 - wall_z0, None, C_STAGE, verts=24)
          for x, y in TOP_SCREWS + [(x, y) for _, x, y in JAW_SCREW_PTS]]
for _, x, z in LATCH_SCREW_PTS:
    bosses.append(cyl("boss", x, WALL_T + 1.75, z, WALL_BOSS_R, 3.5 + 0.2, None, C_STAGE, axis="Y", verts=24))
for b in bosses:
    apply_tf(b)
boolean(walls, join(bosses, "bosses"), op="UNION")

# rear exhaust behind the fin stack
boolean_cut(walls, rbox("cut", EXHAUST["x0"], D - 5, wall_z0 + 0.8, EXHAUST["x1"], D + 2, wall_z1 - 0.8, None, C_SLED))
# right-wall intake louvres feeding the blower's top inlet (works even on a soft surface)
slots = []
y = SIDE_INTAKE["y0"]
while y + 3 <= SIDE_INTAKE["y1"]:
    slots.append(rbox("cut", W - WALL_T - 1, y, wall_z0 + 1.0, W + 1, y + 3, wall_z1 - 1.0, None, C_SLED))
    y += 5
cut_many(walls, slots)


def d_hole(y, z):
    """6.5 mm SMA panel hole with an anti-rotation flat on top (local x = world -z)."""
    pts = []
    for k in range(40):
        a = 2 * math.pi * k / 40
        lx, ly = SMA_HOLE_R * math.cos(a), SMA_HOLE_R * math.sin(a)
        pts.append((max(lx, -SMA_HOLE_FLAT), ly))
    ob = prism("cut", pts, -1, WALL_T + 2, None, C_STAGE)
    place(ob, (W - WALL_T - 0.5, y, z), "+X")
    return ob


USBC_ZC = PCB_Z0 + PCB_T / 2
cuts = [d_hole(LANES[n], Z_SMA) for n in LANES]
cuts += [rbox("cut", -1, yc - USBC["w"] / 2 - 0.4, USBC_ZC - USBC["h"] / 2 - 0.4,
              WALL_T + 1, yc + USBC["w"] / 2 + 0.4, USBC_ZC + USBC["h"] / 2 + 0.4, None, C_STAGE, r=1.2)
         for _, yc in USBC_PORTS]
# tapped holes: top-plate screws (4 mm deep), jaw screws (4.5 mm), latch screws (horizontal, 5 mm)
cuts += [tap_hole(x, y, TOP_Z0, 4.0, "M2") for x, y in TOP_SCREWS]
cuts += [tap_hole(x, y, TOP_Z0, 4.5, "M2") for _, x, y in JAW_SCREW_PTS]
cuts += [cyl("cut", x, 2.5, z, T["M2"]["tap"] / 2, 5.2, None, C_STAGE, axis="Y", verts=20) for _, x, z in LATCH_SCREW_PTS]
cut_many(walls, cuts)

# exhaust deflector: turns the hot air down and away from the Mac's underside
defl = rbox("Exhaust deflector", EXHAUST["x0"] - 2, 0, -0.8, EXHAUST["x1"] + 2, 14, 0, M["alu"], C_SLED, bevel=0.2)
defl.location = (0, (D + 0.6) * MM, TOP_Z0 * MM)
defl.rotation_euler = (math.radians(-38), 0, 0)

# SMA bulkhead jacks on the right wall, one per RF lane
for name, y in LANES.items():
    parts.sma_bulkhead(f"SMA bulkhead ({name})", (W, y, Z_SMA), WALL_T, C_SLED, M, C_STAGE)

# blower intake grille through the base plate, plus taller feet for the intake gap
grille = []
bx, by = BLOWER_C
for gx in range(-3, 4):
    for gy in range(-3, 4):
        if gx * gx + gy * gy <= 10:
            grille.append(cyl("g", bx + gx * 4.4, by + gy * 4.4, BASE_T / 2, 1.6, BASE_T + 2, None, C_SLED, verts=12))
cut_many(base, grille)
for i, (x, y) in enumerate([(14, 14), (W - 14, 14), (14, D - 14), (W - 14, D - 14)]):
    f = lathe(f"Sled foot {i + 1}", [(0, -FOOT_H), (4.2, -FOOT_H), (5, -FOOT_H + 0.8), (5, 0), (0, 0)], M["rubber"], C_SLED, seg=32)
    f.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)))

# ================================================================ thermal
HP_Z = BASE_T - HP_T / 2
grooves = []
for name, pts in HEAT_PIPES:
    poly_curve(name, [(x, y, HP_Z) for x, y in pts], M["copper"], C_THERMAL, profile=(HP_W, HP_T))
    g = (HP_W + 0.2) / 2
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        assert xa == xb or ya == yb, f"{name}: heat pipe runs must be axis-aligned"
        grooves.append(rbox("cut", min(xa, xb) - g, min(ya, yb) - g, BASE_T - HP_T - 0.1,
                            max(xa, xb) + g, max(ya, yb) + g, BASE_T + 1, None, C_STAGE))
cut_many(base, grooves)

fin = rbox("Fin stack", FINS["x0"], FINS["y0"], BASE_T, FINS["x0"] + FINS["t"], FINS["y1"], TOP_Z0, M["alu_mill"], C_THERMAL)
arr = fin.modifiers.new("array", "ARRAY")
arr.use_relative_offset = False
arr.use_constant_offset = True
arr.constant_offset_displace = (FINS["pitch"] * MM, 0, 0)
arr.count = int((FINS["x1"] - FINS["x0"]) / FINS["pitch"])
plen = rbox("Plenum duct", PLENUM["x0"], PLENUM["y0"], BASE_T, PLENUM["x1"], PLENUM["y1"], TOP_Z0, M["alu"], C_THERMAL, bevel=0.3)
boolean_cut(plen, rbox("cut", PLENUM["x0"] + 1, PLENUM["y0"] + 1, BASE_T + 0.6,
                       PLENUM["x1"] + 1, PLENUM["y1"] + 1, TOP_Z0 - 0.6, None, C_THERMAL))

bx0, by0, bs = BLOWER["x0"], BLOWER["y0"], BLOWER["size"]
bh = rbox("Blower housing", bx0, by0, BASE_T, bx0 + bs, by0 + bs, BASE_T + BLOWER["h"], M["plastic"], C_THERMAL,
          r=BLOWER["r"], bevel=0.4)
bh_top = BASE_T + BLOWER["h"]
boolean_cut(bh, cyl("cut", bx, by, (BASE_T + bh_top) / 2, 18, BLOWER["h"] - 1.2, None, C_THERMAL, verts=64))
boolean_cut(bh, cyl("cut", bx, by, bh_top, 16, 3, None, C_THERMAL, verts=48))
boolean_cut(bh, cyl("cut", bx, by, BASE_T, 16, 3, None, C_THERMAL, verts=48))
boolean_cut(bh, rbox("cut", bx0 - 1, PLENUM["y0"] + 1, BASE_T + 0.6, bx, PLENUM["y1"] - 0.5,
                     bh_top - 0.6, None, C_THERMAL))
cyl("Blower impeller hub", bx, by, BASE_T + 4.8, 7, 2.4, M["plastic"], C_THERMAL, verts=32)
blades = []
for k in range(33):
    b = rbox(f"blade{k}", -0.25, 8, BASE_T + 1.0, 0.25, 15, BASE_T + 6.0, M["plastic"], C_THERMAL)
    b.rotation_euler = (0, 0, 2 * math.pi * k / 33 + 0.35)
    b.location = (bx * MM, by * MM, 0)
    apply_tf(b)
    blades.append(b)
join(blades, "Blower impeller blades")

# ================================================================ boards
UFL_POS = {}


def receptacle(name, x, y):
    UFL_POS[name] = (x, y)
    return parts.mhf4_receptacle(f"MHF4 receptacle ({name})", x, y, PCB_TOP, C_BOARDS, M)


def board_holes(spec):
    if "holes" in spec:
        return spec["holes"]
    x0, y0, x1, y1 = spec["rect"]
    i = HOLE_INSET
    return [(x0 + i, y0 + i), (x1 - i, y0 + i), (x0 + i, y1 - i), (x1 - i, y1 - i)]


def board(spec):
    """Chips-down board: PCB on top, packages hang below toward the plate."""
    name, (x0, y0, x1, y1) = spec["name"], spec["rect"]
    assert x1 <= BOARD_MAX_X, f"{name} intrudes on the cable descent zone"
    pcb = rbox(name + " PCB", x0, y0, PCB_Z0, x1, y1, PCB_TOP, M[spec.get("mat", "pcb")], C_BOARDS, r=1.5)
    cuts = [clr_hole(hx, hy, PCB_Z0, PCB_TOP, "M2") for hx, hy in board_holes(spec)]
    if name.startswith("Dock board"):       # notches for the mid-mount USB-C receptacles
        for _, yc in USBC_PORTS:
            cuts.append(rbox("cut", x0 - 1, yc - USBC["w"] / 2 - 0.2, PCB_Z0 - 1,
                             USBC["x0"] + parts.USBC_RCP["len"] + 0.2, yc + USBC["w"] / 2 + 0.2, PCB_TOP + 1, None, C_STAGE))
    cut_many(pcb, cuts)
    objs = [pcb]
    for (cx, cy, w, d, h) in spec.get("chips", ()):
        objs.append(rbox(name + " IC", cx - w / 2, cy - d / 2, PCB_Z0 - h, cx + w / 2, cy + d / 2, PCB_Z0, M["chip"], C_BOARDS, bevel=0.15))
    for (cx, cy, w, d, h) in spec.get("cans", ()):
        objs.append(rbox(name + " can", cx - w / 2, cy - d / 2, PCB_Z0 - h, cx + w / 2, cy + d / 2, PCB_Z0, M["can"], C_BOARDS, bevel=0.2))
    ob = join(objs, name)
    for cname, (ux, uy) in spec.get("ufl", {}).items():
        receptacle(cname, ux, uy)
    if name.startswith("Dock board"):
        for pname, yc in USBC_PORTS:
            parts.usbc_receptacle(f"USB-C receptacle ({pname})", (USBC["x0"], yc, USBC_ZC), C_BOARDS, M, C_STAGE)
    for k, (hx, hy) in enumerate(board_holes(spec)):
        screw("pan", "M2", 5, (hx, hy, PCB_TOP), "+Z", C_FAST, f"Screw M2x5 ({name} #{k + 1})", into="boss", grip=PCB_T)
    return ob


def pocket_wall(name, x0, y0, x1, y1, holes, size="M2", notches=(), tap_depth=4.0):
    """Milled wall under the board edge: with the board's ground plane on top it
    closes a shielded pocket around the chips (the RF lid is the PCB itself).
    Standoff bosses under the board's mounting holes are part of the wall."""
    ring = rbox(f"Pocket wall ({name})", x0 + 0.3, y0 + 0.3, BASE_T, x1 - 0.3, y1 - 0.3, PCB_Z0, M["alu_mill"], C_SLED, r=1.5)
    boolean_cut(ring, rbox("cut", x0 + 1.5, y0 + 1.5, BASE_T - 1, x1 - 1.5, y1 - 1.5, PCB_Z0 + 1, None, C_STAGE, r=0.8))
    bs = [cyl("boss", hx, hy, (BASE_T + PCB_Z0) / 2, BOSS_R + (0.3 if size == "M2.5" else 0), PCB_Z0 - BASE_T, None, C_STAGE, verts=24)
          for hx, hy in holes]
    for b in bs:
        apply_tf(b)
    boolean(ring, join(bs, "bosses"), op="UNION")
    cuts = [rbox("cut", *n[:2], BASE_T - 1, *n[2:], PCB_Z0 + 1, None, C_STAGE) for n in notches]
    cuts += [tap_hole(hx, hy, PCB_Z0, tap_depth, size) for hx, hy in holes]
    cut_many(ring, cuts)
    return ring


def edge_notches(ob, rect, band=1.8, margin=0.4):
    """Notches in a pocket wall wherever the real board has parts over the wall."""
    x0, y0, x1, y1 = rect
    cells = set()
    mw = ob.matrix_world
    for v in ob.data.vertices:
        w = mw @ v.co
        x, y, z = w.x / MM, w.y / MM, w.z / MM
        if z > PCB_Z0 - 0.02:
            continue
        for side, d, t in (("L", x - x0, y), ("R", x1 - x, y), ("B", y - y0, x), ("T", y1 - y, x)):
            if d < band:
                cells.add((side, math.floor(t)))
    out = []
    for side in "LRBT":
        ts = sorted(t for s, t in cells if s == side)
        runs = []
        for t in ts:
            if runs and t <= runs[-1][1] + 1:
                runs[-1][1] = t
            else:
                runs.append([t, t])
        for a, b in runs:
            a, b = a - margin, b + 1 + margin
            out.append({"L": (x0 - 1, a, x0 + band + 0.2, b), "R": (x1 - band - 0.2, a, x1 + 1, b),
                        "B": (a, y0 - 1, b, y0 + band + 0.2), "T": (a, y1 - band - 0.2, b, y1 + 1)}[side])
    print(f"pocket wall notches for {ob.name}: {len(out)}")
    return out


for spec in BOARDS:
    board(spec)
    notches = []
    if spec["name"].startswith("Dock board"):
        notches = [(spec["rect"][0] - 1, yc - USBC["w"] / 2 - 0.5, spec["rect"][0] + 3, yc + USBC["w"] / 2 + 0.5)
                   for _, yc in USBC_PORTS]
    pocket_wall(spec["name"], *spec["rect"], board_holes(spec), notches=notches)

# HackRF One: real PCB from Great Scott Gadgets' KiCad design (open hardware),
# exported to STEP with KiCad 3D models, then to glTF.
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=HACKRF_GLB)
new = [o for o in bpy.data.objects if o not in before]
meshes = [o for o in new if o.type == "MESH"]
others = [o.name for o in new if o.type != "MESH"]
for o in meshes:  # bake the importer's Y-up conversion before dropping the empties
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw
keep = []
for o in meshes:  # drop the edge SMA jacks and micro-USB: replaced by MHF4 pigtails and the dock board
    xs = [(o.matrix_world @ mathutils.Vector(v)).x for v in o.bound_box]
    if min(xs) < HACKRF_KEEP_X[0] or max(xs) > HACKRF_KEEP_X[1]:
        bpy.data.objects.remove(o, do_unlink=True)
    else:
        keep.append(o)
for n in others:
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
hack = join(keep, "HackRF One PCB (real KiCad design)")
hack["imported"] = True
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
link(hack, C_BOARDS)
me = hack.data
me.transform(mathutils.Matrix.Rotation(math.radians(90), 4, "X"))  # parts face -Z
xs = [v.co.x for v in me.vertices]
ys = [v.co.y for v in me.vertices]
zs = [v.co.z for v in me.vertices]
hw, hd = (max(xs) - min(xs)) / MM, (max(ys) - min(ys)) / MM
print(f"HackRF extents mm: {hw:.1f} {hd:.1f} {(max(zs) - min(zs)) / MM:.2f}")
me.transform(mathutils.Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -max(zs))))
hcx, hcy = HACKRF["center"]
hack.location = (hcx * MM, hcy * MM, PCB_TOP * MM)
# the STEP export fills the plated mounting holes with copper-layer faces; open them up
# (split the long tessellation triangles near each hole first, so the cut stays round)
bm = bmesh.new()
bm.from_mesh(me)
for _ in range(6):
    near = [e for e in bm.edges if e.calc_length() > 0.25 * MM and
            any(min(math.hypot(v.co.x / MM + hcx - hx, v.co.y / MM + hcy - hy) for v in e.verts) < 3.0
                for hx, hy in HACKRF_HOLES)]
    if not near:
        break
    bmesh.ops.subdivide_edges(bm, edges=near, cuts=1, use_grid_fill=False)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
doomed = [f for f in bm.faces
          if any(math.hypot(v.co.x / MM + hcx - hx, v.co.y / MM + hcy - hy) < 1.25 for v in f.verts for hx, hy in HACKRF_HOLES)
          or any(math.hypot(f.calc_center_median().x / MM + hcx - hx, f.calc_center_median().y / MM + hcy - hy) < 1.25
                 for hx, hy in HACKRF_HOLES)]
bmesh.ops.delete(bm, geom=doomed, context="FACES")
bm.to_mesh(me)
bm.free()
print(f"HackRF: opened {len(HACKRF_HOLES)} mounting holes ({len(doomed)} faces)")
ref_h = hack.copy()
ref_h.data = hack.data.copy()
C_REF.objects.link(ref_h)
ref_h.name = "HackRF One PCB (real, reference view)"
ref_h.rotation_mode = "XYZ"
ref_h.rotation_euler = (math.pi, 0, 0)
ref_h.location = (-150 * MM, 120 * MM, -0.4 * MM)
for cname, (ux, uy) in HACKRF["ufl"].items():
    receptacle(cname, ux, uy)
bpy.context.view_layer.update()
hrect = (hcx - hw / 2, hcy - hd / 2, hcx + hw / 2, hcy + hd / 2)
pocket_wall("HackRF", *hrect, HACKRF_HOLES, notches=edge_notches(hack, hrect))
for k, (hx, hy) in enumerate(HACKRF_HOLES):
    ws = parts.WASHER["M2"][2]      # HackRF holes are 2.75 mm: M2 with a DIN 433 washer
    parts.washer("M2", (hx, hy, PCB_TOP), "+Z", C_FAST, f"Washer DIN 433 M2 (HackRF #{k + 1})", M)
    screw("pan", "M2", 5, (hx, hy, PCB_TOP + ws), "+Z", C_FAST, f"Screw M2x5 (HackRF #{k + 1})",
          into="boss", grip=PCB_T + ws)

# aluminium pedestals under the hottest chips, sized to each chip's measured depth
bpy.context.view_layer.update()
board_objs = [o for o in C_BOARDS.objects if o.type == "MESH"]
for pname, x0, y0, x1, y1 in PEDESTALS:
    lo = 1e9
    for o in board_objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            w = mw @ v.co
            if x0 * MM <= w.x <= x1 * MM and y0 * MM <= w.y <= y1 * MM:
                lo = min(lo, w.z / MM)
    if lo > 1e8:
        raise SystemExit(f"pedestal {pname}: no board above it")
    pad_top = lo - PAD_GAP
    ped_top = pad_top - PAD_T
    if ped_top > BASE_T + 0.2:
        rbox(f"Pedestal ({pname})", x0, y0, BASE_T, x1, y1, ped_top, M["alu_mill"], C_THERMAL, bevel=0.2)
    rbox(f"Thermal pad ({pname})", x0 + 0.5, y0 + 0.5, max(ped_top, BASE_T), x1 - 0.5, y1 - 0.5, pad_top, M["pad"], C_THERMAL)
    print(f"pedestal {pname}: chip bottom {lo:.2f} mm")

# ================================================================ RF pigtails
Z_PLUG = PCB_TOP + MHF4_RECEPT_H + COAX_R + 0.02   # cable leaves the plug above the receptacle


def route(ux, uy, lane):
    """Run along y on the upper layer, one bend, then along x on the lower
    layer, then an S-bend down into the SMA's crimp ferrule."""
    pts = [(ux, uy, Z_PLUG)]
    if abs(lane - uy) > 1e-6:
        s = 1 if lane > uy else -1
        R = CORNER_R_CABLE
        assert abs(lane - uy) >= R + 3, f"lane {lane} too close to connector at y={uy}"
        pts += [(ux, uy + s * 3, Z_HIGH), (ux, lane - s * R, Z_HIGH)]
        cx, cy = ux + R, lane - s * R
        n = 8
        for k in range(1, n + 1):
            a = math.pi - s * (math.pi / 2) * k / n
            z = Z_HIGH + (Z_LOW - Z_HIGH) * k / n
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a), z))
        direction = (0, s)
    else:
        pts += [(ux + 1.5, uy, Z_PLUG), (ux + 4, uy, Z_LOW)]
        direction = (1, 0)
    n = 10
    for k in range(n + 1):
        t = k / n
        x = CABLE_DESCENT_X + (SMA_FERRULE_X - CABLE_DESCENT_X) * t
        pts.append((x, lane, Z_LOW + (Z_SMA - Z_LOW) * (1 - math.cos(math.pi * t)) / 2))
    return pts, direction


lengths = {}
for cname, lane in LANES.items():
    ux, uy = UFL_POS[cname]
    pts, direction = route(ux, uy, lane)
    lengths[cname] = polyline_length(pts)
    kraken = cname.startswith("Kraken")
    poly_curve(f"Pigtail ({cname})", pts, M["coax_kraken" if kraken else "coax"], C_CABLES, radius=COAX_R)
    parts.mhf4_plug(f"MHF4 plug ({cname})", ux, uy, PCB_TOP, direction, C_CABLES, M)
for cname, L in lengths.items():
    print(f"pigtail {cname:18s} {L:6.1f} mm")
scene["pigtail_lengths_mm"] = {k: round(v, 2) for k, v in lengths.items()}

# ================================================================ top plate
top = rbox("Top plate (1 mm, grounded shield)", 0, 0, TOP_Z0, W, D, TOP_Z1, M["alu_dark"], C_TOP, r=CORNER_R, bevel=0.3)
cut_many(top, [clr_hole(x, y, TOP_Z0, TOP_Z1, "M2") for x, y in TOP_SCREWS + [(x, y) for _, x, y in JAW_SCREW_PTS]])
for k, (x, y) in enumerate(TOP_SCREWS):
    screw("pan", "M2", 4, (x, y, TOP_Z1), "+Z", C_FAST, f"Screw M2x4 (top plate #{k + 1})", into="wall boss", grip=1.0)
for i, (xa, xb) in enumerate(SILICONE_RAILS):
    rbox(f"Silicone rail {i + 1}", xa, 12, TOP_Z1, xb, D - 12, TOP_Z1 + RAIL_T, M["silicone"], C_TOP, bevel=0.6)

# ================================================================ mount: jaws, rear stops, front latches
JAW_Z1 = {}


def jaw(j):
    """One side jaw: web outside the Mac's side, flange on the top plate (under
    the Mac's edge), TPU liner, and for the rear jaws a corner return that
    stops the Mac sliding back."""
    left = j["side"] == "L"
    sx = (lambda x: x) if left else mirror_x
    z1 = MAC_Z + j["top"]
    JAW_Z1[j["name"]] = z1
    y0, y1 = j["y0"], j["y1"]
    yo = y1 + (LINER_T + JAW_T if j["rear"] else 0)
    xa, xb = sorted((sx(-LINER_T - JAW_T), sx(-LINER_T)))
    objs = [rbox("web", xa, y0, TOP_Z0, xb, yo, z1, M["alu_dark"], C_STAGE)]
    fa, fb = sorted((sx(-LINER_T - JAW_T), sx(FLANGE_W)))
    objs.append(rbox("flange", fa, y0, TOP_Z1, fb, y1 if not j["rear"] else D - CORNER_R * 0.4, TOP_Z1 + FLANGE_T, M["alu_dark"], C_STAGE, r=0.8))
    if j["rear"]:
        ra, rb = sorted((sx(-LINER_T - JAW_T), sx(REAR_RETURN)))
        objs.append(rbox("return", ra, D + LINER_T, TOP_Z1, rb, D + LINER_T + JAW_T, z1, M["alu_dark"], C_STAGE))
    for o in objs:
        apply_tf(o)
    body = objs[0]
    for o in objs[1:]:
        boolean(body, o, op="UNION")
    body.name = j["name"] + " (6061, black anodised)"
    link(body, C_MOUNT)
    # countersunk holes for the screws (ISO 14581 M2, 90 deg)
    cuts = []
    for y in JAW_SCREWS[j["name"]]:
        x = sx(JAW_SCREW_X)
        c = lathe("cut", [(0, TOP_Z1 + FLANGE_T + 0.5), (2.4, TOP_Z1 + FLANGE_T + 0.5), (2.0, TOP_Z1 + FLANGE_T),
                          (T["M2"]["clr"] / 2, TOP_Z1 + FLANGE_T - (2.0 - T["M2"]["clr"] / 2)),
                          (T["M2"]["clr"] / 2, TOP_Z1 - 0.5), (0, TOP_Z1 - 0.5)], None, C_STAGE, seg=24)
        c.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)))
        cuts.append(c)
    cut_many(body, cuts)
    bev = body.modifiers.new("bevel", "BEVEL")
    bev.width = 0.25 * MM
    bev.limit_method = "ANGLE"
    # TPU liner on the inside of the web (and of the rear return)
    la, lb = sorted((sx(-LINER_T), sx(0)))
    liner = [rbox(j["name"] + " liner", la, y0 + 0.5, TOP_Z1 + FLANGE_T, lb, y1, z1 - 0.3, M["tpu"], C_MOUNT)]
    if j["rear"]:
        ra, rb = sorted((sx(MAC["r_plan"] - 2.0), sx(REAR_RETURN - 0.5)))
        liner.append(rbox("rear liner", ra, D, TOP_Z1 + 0.3, rb, D + LINER_T, z1 - 0.3, M["tpu"], C_MOUNT))
    join(liner, j["name"] + " TPU liner")
    for k, y in enumerate(JAW_SCREWS[j["name"]]):
        screw("csk", "M2", 6, (sx(JAW_SCREW_X), y, TOP_Z1 + FLANGE_T), "+Z", C_FAST,
              f"Screw M2x6 countersunk ({j['name']} #{k + 1})", into="wall boss", grip=FLANGE_T + 1.0)


for j in JAWS:
    jaw(j)

LATCH_TOP = MAC_Z - MAC_FOOT_T - 0.4       # the Mac's feet slide over the latch block
PAWL_TOP = MAC_Z + LATCH["pawl_up"]
PAWL_H = 9.0


def latch(side):
    """Spring pawl latch in front of the sled's front wall. The pawl rises in
    front of the Mac's front face; press it down to slide the Mac out."""
    L = LATCH
    sx = (lambda x: x) if side == "L" else mirror_x
    tag = "front left" if side == "L" else "front right"
    xa, xb = sorted((sx(L["x0"]), sx(L["x1"])))
    block = rbox(f"Latch block ({tag}) (6061, black anodised)", xa, L["y0"], L["z0"], xb, 0, LATCH_TOP, M["alu_dark"], C_MOUNT, r=0.6)
    pa, pb = sorted((sx(L["pawl_x"][0]), sx(L["pawl_x"][1])))
    pya, pyb = L["pawl_y"]
    pcx = (pa + pb) / 2
    pcy = (pya + pyb) / 2
    cuts = [rbox("cut", pa - 0.05, pya - 0.05, 1.0, pb + 0.05, 0.5, LATCH_TOP + 1, None, C_STAGE)]   # pawl pocket
    cuts.append(cyl("cut", pcx, pcy, L["pin_z"], 0.5, 10.0, None, C_STAGE, axis="X", verts=16))      # pin bore
    for (sxx, sz) in L["screws"]:
        x = sx(sxx)
        cuts.append(cyl("cut", x, L["y0"] + 1.0, sz, 2.1, 2.4, None, C_STAGE, axis="Y", verts=24))   # counterbore
        cuts.append(cyl("cut", x, (L["y0"] + 2.2) / 2, sz, T["M2"]["clr"] / 2, -L["y0"] - 2.2 + 0.4, None, C_STAGE, axis="Y", verts=20))
    cut_many(block, cuts)
    # pawl (POM): vertical locking face towards the Mac, entry ramp towards the front
    z_bot = PAWL_TOP - PAWL_H
    pawl = rbox(f"Latch pawl ({tag}) (POM)", pa, pya, z_bot, pb, pyb, PAWL_TOP, M["pom"], C_STAGE)
    ramp = prism("cut", [(pya - 1, PAWL_TOP - 3.4), (pya + 2.0, PAWL_TOP + 0.01), (pya - 1, PAWL_TOP + 2)], pa - 1, pb + 1, None, C_STAGE)
    # prism() extrudes along z; map (u, v, w) -> (x=w, y=u, z=v) to extrude the (y, z) wedge along x
    ramp.data.transform(mathutils.Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    slot = rbox("cut", pa - 1, pcy - 0.525, z_bot + 1.6, pb + 1, pcy + 0.525, z_bot + 6.2, None, C_STAGE)
    cut_many(pawl, [ramp, slot])
    link(pawl, C_MOUNT)
    parts.dowel(f"Latch pin ({tag})", 1.0, 8.0, (pcx, pcy, L["pin_z"]), "+X", C_MOUNT, M["steel"])
    sp = L["spring"]
    parts.spring(f"Latch spring ({tag})", sp["od"], sp["wire"], 1.0, z_bot, sp["turns"], (pcx, pcy), C_MOUNT, M["spring"])
    for k, (sxx, sz) in enumerate(L["screws"]):
        screw("shcs", "M2", 8, (sx(sxx), L["y0"] + 2.2, sz), "-Y", C_FAST,
              f"Screw M2x8 socket head (latch {tag} #{k + 1})", into="front wall + boss", grip=-L["y0"] - 2.2)


latch("L")
latch("R")

# ================================================================ MacBook Pro 16
BASE_H, LID_H = MAC["base_h"], MAC["lid_h"]
mac = rounded_slab("MacBook base", 0, 0, W, D, MAC_Z, MAC_Z + BASE_H, MAC["r_plan"], MAC["r_bot"], MAC["r_top"], M["mac"], C_MAC)
port_cuts = []
for pname, side, py, (pw, ph), _ in MAC_PORTS:
    x = 0 if side == "L" else W
    c = prism("cut", rounded_rect(-pw / 2, -ph / 2, pw / 2, ph / 2, min(ph, pw) / 2 - 1e-3, 6), -0.5, 7.0, None, C_STAGE)
    place(c, (x, py, MAC_Z + MAC_PORT_CZ), "+X" if side == "L" else "-X", spin=math.pi / 2)
    port_cuts.append(c)
cut_many(mac, port_cuts)
for pname, side, py, (pw, ph), _ in MAC_PORTS:          # dark port interiors
    x = 0 if side == "L" else W
    c = prism(f"Mac port {pname}", rounded_rect(-pw / 2, -ph / 2, pw / 2, ph / 2, min(ph, pw) / 2 - 1e-3, 6), 6.0, 7.0, M["port"], C_MAC)
    place(c, (x, py, MAC_Z + MAC_PORT_CZ), "+X" if side == "L" else "-X", spin=math.pi / 2)
kb_z = MAC_Z + BASE_H
rbox("Keyboard well", 40, 128, kb_z - 0.6, W - 40, D - 14, kb_z + 0.01, M["key"], C_MAC, r=2)
keys = []
y = D - 22
for n, kh in [(14, 16.0), (14, 18.0), (13, 18.0), (12, 18.0), (11, 18.0), (9, 13.0)]:
    pitch = (W - 84) / n
    for k in range(n):
        x = 42 + k * pitch
        keys.append(rbox("k", x + 1, y - kh + 2, kb_z - 0.6, x + pitch - 1, y, kb_z + 0.5, M["key"], C_MAC, bevel=0.4))
    y -= kh + 2
join(keys, "Keycaps")
rbox("Trackpad", W / 2 - 80, 14, kb_z - 0.05, W / 2 + 80, 112, kb_z + 0.02, M["mac"], C_MAC, r=4)
for i, xx in enumerate((14, W - 14 - 22)):     # speaker grilles beside the keyboard
    rbox(f"Speaker grille {i + 1}", xx, 130, kb_z - 0.02, xx + 22, D - 18, kb_z + 0.005, M["key"], C_MAC, r=2)
hinge = bpy.data.objects.new("Lid hinge", None)
C_MAC.objects.link(hinge)
hinge.location = (0, D * MM, kb_z * MM)
lid = rounded_slab("MacBook lid", 0, 0, W, D, 0, LID_H, MAC["r_plan"], 1.0, 1.5, M["mac"], C_MAC)
glass = rbox("Display glass", 3, 3, -0.02, W - 3, D - 3, 0.3, M["glass"], C_MAC, r=8)
panel = rbox("Display panel", 7, 8, -0.04, W - 7, D - 6, 0.0, M["screen"], C_MAC, r=6)
for o in (lid, glass, panel):
    o.location = (0, -D * MM, 0)
    o.parent = hinge
hinge.rotation_euler = (math.radians(-108), 0, 0)
fi_x, fi_y = MAC["foot_inset"]
for i, (x, y) in enumerate([(fi_x, fi_y), (W - fi_x, fi_y), (fi_x, D - fi_y), (W - fi_x, D - fi_y)]):
    r = MAC["foot_d"] / 2
    f = lathe(f"Mac foot {i + 1}", [(0, MAC_Z - MAC_FOOT_T), (r - 0.4, MAC_Z - MAC_FOOT_T), (r, MAC_Z - MAC_FOOT_T + 0.3),
                                    (r, MAC_Z + 0.2), (0, MAC_Z + 0.2)], M["rubber"], C_MAC, seg=40)
    f.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)))
for o in C_MAC.objects:
    if o.type == "MESH" and o.name.startswith(("MacBook base", "Mac foot")):
        o["check"] = True          # parts of the Mac that take part in the fit check

# ================================================================ external cables (renders) and keep-out envelopes
tb_y = USBC_PORTS[1][1]
parts.usbc_plug("USB-C plug (sled Thunderbolt)", (USBC["x0"], tb_y, USBC_ZC), "-X", C_EXT, M, C_STAGE)
mac_tb = next(p for p in MAC_PORTS if p[0] == "Thunderbolt 4 L2")
parts.usbc_plug("USB-C plug (Mac Thunderbolt)", (0, mac_tb[2], MAC_Z + MAC_PORT_CZ), "-X", C_EXT, M, C_STAGE)
x_om = USBC["x0"] - (parts.USBC_PLUG["len"] - 6.2) - parts.USBC_PLUG["om_len"] - 5.5
x_om2 = -(parts.USBC_PLUG["len"] - 6.2) - parts.USBC_PLUG["om_len"] - 5.5
zc2 = MAC_Z + MAC_PORT_CZ
cable = [(x_om, tb_y, USBC_ZC), (x_om - 10, tb_y, USBC_ZC), (x_om - 26, tb_y + 22, USBC_ZC + 1),
         (x_om - 32, (tb_y + mac_tb[2]) / 2, (USBC_ZC + zc2) / 2),
         (x_om2 - 26, mac_tb[2] - 22, zc2 - 1), (x_om2 - 10, mac_tb[2], zc2), (x_om2, mac_tb[2], zc2)]
cu = poly_curve("Thunderbolt cable (sled to Mac)", cable, M["rubber"], C_EXT, radius=parts.USBC_PLUG["cable_r"], res=4)
cu.data.splines[0].type = "NURBS"
cu.data.splines[0].use_endpoint_u = True
cu.data.splines[0].order_u = 4
cu.data.resolution_u = 24

for name, y in LANES.items():         # nut driver / mating SMA plug around every bulkhead
    parts.envelope_cyl(f"Keep-out SMA access ({name})", (W + 0.6, y, Z_SMA), "+X", 5.6, 22.0, C_KEEP, M["keepout"])
for pname, yc in USBC_PORTS:          # USB-C plug overmould at the sled's ports
    rbox(f"Keep-out USB-C plug ({pname})", -30, yc - 6.3, USBC_ZC - 3.4, -0.2, yc + 6.3, USBC_ZC + 3.4, M["keepout"], C_KEEP)
for pname, side, py, _, (ow, oh) in MAC_PORTS:   # plugs in the Mac's own ports
    xa, xb = (-MAC_PLUG_LEN, -0.05) if side == "L" else (W + 0.05, W + MAC_PLUG_LEN)
    cz = MAC_Z + MAC_PORT_CZ
    rbox(f"Keep-out Mac plug ({pname})", xa, py - ow / 2, cz - oh / 2, xb, py + ow / 2, cz + oh / 2, M["keepout"], C_KEEP)
rbox("Keep-out lid swing", 0, D + 0.05, MAC_Z + LID_KEEPOUT["z_above_bottom"], W, D + LID_KEEPOUT["dy"], MAC_Z + 40,
     M["keepout"], C_KEEP)
for o in C_KEEP.objects:
    o.display_type = "WIRE"

# ================================================================ reference: real downloaded assets
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=FLIPPER_GLB)
fz = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
for o in fz:
    link(o, C_REF)
    o.data.materials.clear()
    o.data.materials.append(M["flipper"])
fz_obj = fz[0]
fz_obj.name = "Flipper Zero body (official model, donor device)"
bpy.context.view_layer.update()
fzb = [fz_obj.matrix_world @ mathutils.Vector(v) for v in fz_obj.bound_box]
fz_obj.location.x += -60 * MM - min(v.x for v in fzb)
fz_obj.location.y += 70 * MM - min(v.y for v in fzb)
fz_obj.location.z += -2 * MM - min(v.z for v in fzb)

# ================================================================ stage
cyl("Floor", W / 2, D / 2, -FOOT_H - 0.5, 2500, 1.0, M["floor"], C_STAGE, verts=64)
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.55, 0.57, 0.60, 1)
bg.inputs["Strength"].default_value = 0.35


def area(name, loc, size, energy, target):
    lt = bpy.data.lights.new(name, "AREA")
    lt.size = size
    lt.energy = energy
    o = bpy.data.objects.new(name, lt)
    C_STAGE.objects.link(o)
    o.location = loc
    d = mathutils.Vector(target) - mathutils.Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


ctr = (W / 2 * MM, D / 2 * MM, 0.01)
area("Key light", (-0.35, -0.55, 0.75), 0.8, 140, ctr)
area("Fill light", (0.75, -0.35, 0.45), 1.0, 60, ctr)
area("Rim light", (0.2, 0.9, 0.6), 0.6, 110, ctr)

# helper objects left over from booleans
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.name.split(".")[0] in ("cut", "boss", "bosses", "cutters", "g", "louvres", "web",
                                                    "flange", "return", "rear liner"):
        bpy.data.objects.remove(o, do_unlink=True)

# booleans add edges that are not marked sharp yet: redo the smoothing on the final meshes
for o in bpy.data.objects:
    if o.type == "MESH" and not o.get("imported") and o.data.users == 1:
        smooth_by_angle(o)

scene["fasteners"] = json.dumps(parts.FASTENERS)
scene["mount"] = json.dumps(dict(jaw_top={k: round(v, 3) for k, v in JAW_Z1.items()}, latch_top=LATCH_TOP, pawl_top=PAWL_TOP))
print(f"fasteners: {len(parts.FASTENERS)} screws")
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("saved", OUT_BLEND)
