"""Build the caseless OSINT sled in Blender (bpy 5.3).

All geometry comes from sled_config.py (millimetres in code, converted to
metres for Blender). Sled origin = front-left-bottom corner of the base plate;
x = right, y = towards the rear (hinge), z = up.

usage: python scripts/build_sled.py      # writes model/osint_sled.blend
"""
import math
from pathlib import Path

import bpy  # must be imported before bmesh/mathutils, which it provides
import bmesh
import mathutils

from sled_config import (
    BASE_T, BLOWER, BLOWER_C, BOARDS, BOARD_MAX_X, CABLE_DESCENT_X, CORNER_R,
    CORNER_R_CABLE, COAX_R, D, EXHAUST, FINS, FOOT_H, HACKRF, HACKRF_KEEP_X,
    HEAT_PIPES, HP_T, HP_W, LANES, MAC_FOOT_T, MAC_Z, MHF4_MATED_H,
    MHF4_RECEPT_H, PAD_GAP, PAD_T, PCB_T, PCB_TOP, PCB_Z0, PEDESTALS, PLENUM,
    RAIL_T, SIDE_INTAKE, SMA_HOLE_R, TOP_Z0, TOP_Z1, USBC, USBC_PORTS, W, WALL_T,
    Z_HIGH, Z_LOW, Z_SMA,
)

ROOT = Path(__file__).resolve().parents[1]
HACKRF_GLB = str(ROOT / "model/assets/hackrf-one.glb")
FLIPPER_GLB = str(ROOT / "model/assets/flipper-zero.glb")
OUT_BLEND = str(ROOT / "model/osint_sled.blend")
MM = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"


# ---------------------------------------------------------------- helpers
def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


C_SLED = coll("Sled chassis")
C_THERMAL = coll("Thermal")
C_BOARDS = coll("Boards")
C_CABLES = coll("RF pigtails")
C_TOP = coll("Top plate")
C_MAC = coll("MacBook Pro 16")
C_REF = coll("Reference - real assets")
C_STAGE = coll("Stage")


def mat(name, rgb, metal=0.0, rough=0.5, alpha=1.0, transmission=0.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    if transmission:
        p.inputs["Transmission Weight"].default_value = transmission
        p.inputs["IOR"].default_value = 1.5
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = 1.0
    return m


M = {
    "alu": mat("Aluminium 6061", (0.60, 0.61, 0.63), 1.0, 0.42),
    "alu_dark": mat("Anodised aluminium", (0.10, 0.10, 0.11), 0.7, 0.45),
    "copper": mat("Copper heat pipe", (0.93, 0.52, 0.32), 1.0, 0.22),
    "pcb": mat("PCB soldermask", (0.012, 0.13, 0.055), 0.0, 0.45),
    "pcb_black": mat("PCB black", (0.02, 0.02, 0.025), 0.0, 0.4),
    "pcb_purple": mat("PCB purple", (0.18, 0.06, 0.28), 0.0, 0.45),
    "pcb_blue": mat("PCB blue", (0.02, 0.06, 0.22), 0.0, 0.45),
    "can": mat("Tin shield can", (0.80, 0.80, 0.80), 1.0, 0.28),
    "chip": mat("IC package", (0.03, 0.03, 0.03), 0.0, 0.55),
    "gold": mat("Gold SMA", (1.0, 0.77, 0.34), 1.0, 0.22),
    "coax": mat("Micro-coax 1.13", (0.15, 0.15, 0.16), 0.0, 0.6),
    "coax_kraken": mat("Micro-coax 1.13 phase-matched", (0.55, 0.12, 0.10), 0.0, 0.55),
    "rubber": mat("Rubber", (0.02, 0.02, 0.02), 0.0, 0.85),
    "plastic": mat("Blower plastic", (0.04, 0.04, 0.045), 0.0, 0.5),
    "pad": mat("Thermal pad", (0.55, 0.35, 0.65), 0.0, 0.7),
    "steel": mat("USB-C shell", (0.75, 0.75, 0.77), 1.0, 0.3),
    "window": mat("Polycarbonate window", (0.85, 0.9, 1.0), 0.0, 0.05, transmission=1.0),
    "mac": mat("MacBook space black", (0.035, 0.035, 0.04), 0.35, 0.42),
    "key": mat("Keycaps", (0.012, 0.012, 0.012), 0.0, 0.75),
    "glass": mat("Display bezel", (0.004, 0.004, 0.005), 0.0, 0.35),
    "screen": mat("Display", (0.01, 0.012, 0.02), 0.0, 0.06, emission=(0.10, 0.22, 0.42)),
    "floor": mat("Floor", (0.30, 0.31, 0.32), 0.0, 0.65),
    "flipper": mat("Flipper Zero shell", (0.92, 0.92, 0.90), 0.0, 0.45),
}


def link(obj, c):
    for uc in obj.users_collection:
        uc.objects.unlink(obj)
    c.objects.link(obj)
    return obj


def mesh_obj(name, bm, material, c):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def rbox(name, x0, y0, z0, x1, y1, z1, material, c, r=0.0, bevel=0.0, seg=6):
    """Box in mm with optional vertical-corner radius r and edge bevel."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = (x0 if v.co.x < 0 else x1) * MM
        v.co.y = (y0 if v.co.y < 0 else y1) * MM
        v.co.z = (z0 if v.co.z < 0 else z1) * MM
    if r > 0:
        vert_edges = [e for e in bm.edges
                      if abs(e.verts[0].co.x - e.verts[1].co.x) < 1e-9
                      and abs(e.verts[0].co.y - e.verts[1].co.y) < 1e-9]
        bmesh.ops.bevel(bm, geom=vert_edges, offset=r * MM, segments=seg,
                        affect="EDGES", profile=0.5)
    ob = mesh_obj(name, bm, material, c)
    if bevel > 0:
        md = ob.modifiers.new("bevel", "BEVEL")
        md.width = bevel * MM
        md.segments = 2
        md.limit_method = "ANGLE"
    for p in ob.data.polygons:
        p.use_smooth = False
    return ob


def cyl(name, x, y, z, r, h, material, c, axis="Z", verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r * MM, depth=h * MM,
                                        location=(x * MM, y * MM, z * MM))
    ob = bpy.context.active_object
    ob.name = name
    if axis == "X":
        ob.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y":
        ob.rotation_euler = (math.pi / 2, 0, 0)
    if material:
        ob.data.materials.append(material)
    return link(ob, c)


def boolean_cut(target, cutter):
    md = target.modifiers.new("cut", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.object = cutter
    md.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def rect_profile(name, w, h):
    pc = bpy.data.curves.new(name + "_profile", "CURVE")
    ps = pc.splines.new("POLY")
    ps.points.add(3)
    for p, (a, b) in zip(ps.points, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]):
        p.co = (a * MM, b * MM, 0, 1)
    ps.use_cyclic_u = True
    prof = bpy.data.objects.new(name + "_profile", pc)
    C_STAGE.objects.link(prof)
    prof.hide_render = True
    prof.hide_viewport = True
    return prof


def poly_curve(name, pts, material, c, radius=None, profile=None):
    """POLY curve through pts (mm). Round section (radius) or rectangular (profile=(w, h))."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x * MM, y * MM, z * MM, 1)
    if profile:
        cu.bevel_mode = "OBJECT"
        cu.bevel_object = rect_profile(name, *profile)
    else:
        cu.bevel_depth = radius * MM
        cu.bevel_resolution = 3
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    c.objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob


def polyline_length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


# ---------------------------------------------------------------- chassis
base = rbox("Base plate (6061, 2.5 mm)", 0, 0, 0, W, D, BASE_T, M["alu"], C_SLED, r=CORNER_R, bevel=0.4)
# Proxmark read window through the base plate
win_cut = rbox("cut", 188, 12, -1, 248, 54, BASE_T + 1, None, C_SLED, r=4)
boolean_cut(base, win_cut)
rbox("Proxmark RF window (PC)", 188, 12, 0.2, 248, 54, BASE_T - 0.2, M["window"], C_SLED, r=4)

# perimeter walls
wall_z0, wall_z1 = BASE_T, TOP_Z0
walls = rbox("Side walls", 0, 0, wall_z0, W, D, wall_z1, M["alu"], C_SLED, r=CORNER_R, bevel=0.3)
boolean_cut(walls, rbox("cut", WALL_T, WALL_T, wall_z0 - 1, W - WALL_T, D - WALL_T, wall_z1 + 1, None, C_SLED, r=6))
# rear exhaust behind the fin stack
boolean_cut(walls, rbox("cut", EXHAUST["x0"], D - 5, wall_z0 + 0.8, EXHAUST["x1"], D + 2, wall_z1 - 0.8, None, C_SLED))
# right-wall intake louvres feeding the blower's top inlet (works even on a soft surface)
slots = []
y = SIDE_INTAKE["y0"]
while y + 3 <= SIDE_INTAKE["y1"]:
    slots.append(rbox("cut", W - WALL_T - 1, y, wall_z0 + 1.0, W + 1, y + 3, wall_z1 - 1.0, None, C_SLED))
    y += 5
boolean_cut(walls, join(slots, "louvres"))
# SMA bulkhead holes (right wall) and USB-C openings (left wall)
holes = [cyl("cut", W - WALL_T / 2, LANES[n], Z_SMA, SMA_HOLE_R, WALL_T + 2, None, C_SLED, axis="X")
         for n in LANES]
boolean_cut(walls, join(holes, "sma holes"))
USBC_ZC = PCB_Z0 + PCB_T / 2
ports = [rbox("cut", -1, yc - USBC["w"] / 2 - 0.4, USBC_ZC - USBC["h"] / 2 - 0.4,
              WALL_T + 1, yc + USBC["w"] / 2 + 0.4, USBC_ZC + USBC["h"] / 2 + 0.4, None, C_SLED, r=1.2)
         for _, yc in USBC_PORTS]
boolean_cut(walls, join(ports, "usb-c openings"))

# exhaust deflector: turns the hot air down and away from the Mac's underside
defl = rbox("Exhaust deflector", EXHAUST["x0"] - 2, 0, -0.8, EXHAUST["x1"] + 2, 14, 0, M["alu"], C_SLED, bevel=0.2)
defl.location = (0, (D + 0.6) * MM, TOP_Z0 * MM)
defl.rotation_euler = (math.radians(-38), 0, 0)

# rubber rails the MacBook rests on
for i, x in enumerate((24, W - 36)):
    rbox(f"Rubber rail {i + 1}", x, 18, TOP_Z1, x + 12, D - 18, TOP_Z1 + RAIL_T, M["rubber"], C_TOP, bevel=0.5)

# right-side SMA bulkheads, one per RF lane; the pigtail crimps onto the inner end
SMA_IN_X = W - WALL_T - 0.5
for name, y in LANES.items():
    cyl(f"SMA bulkhead ({name})", (SMA_IN_X + W + 6.5) / 2, y, Z_SMA, 3.15, W + 6.5 - SMA_IN_X, M["gold"], C_SLED, axis="X")
    cyl(f"SMA nut ({name})", W + 1.0, y, Z_SMA, 4.4, 2.0, M["gold"], C_SLED, axis="X", verts=6)

# blower intake grille through the base plate, plus taller feet for the intake gap
grille = []
bx, by = BLOWER_C
for gx in range(-3, 4):
    for gy in range(-3, 4):
        if gx * gx + gy * gy <= 10:
            grille.append(cyl("g", bx + gx * 4.4, by + gy * 4.4, BASE_T / 2, 1.6, BASE_T + 2, None, C_SLED, verts=12))
boolean_cut(base, join(grille, "grille"))
for i, (x, y) in enumerate([(14, 14), (W - 14, 14), (14, D - 14), (W - 14, D - 14)]):
    cyl(f"Sled foot {i + 1}", x, y, -FOOT_H / 2, 5, FOOT_H, M["rubber"], C_SLED, verts=32)

# ---------------------------------------------------------------- thermal
# flattened heat pipes in grooves, top flush with the base plate
HP_Z = BASE_T - HP_T / 2
for name, pts in HEAT_PIPES:
    p3 = [(x, y, HP_Z) for x, y in pts]
    pipe = poly_curve(name, p3, M["copper"], C_THERMAL, profile=(HP_W, HP_T))
    # groove: one milled slot per straight run (the pipes only make 90-degree bends)
    g = (HP_W + 0.2) / 2
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        assert xa == xb or ya == yb, f"{name}: heat pipe runs must be axis-aligned"
        boolean_cut(base, rbox("cut", min(xa, xb) - g, min(ya, yb) - g, BASE_T - HP_T - 0.1,
                               max(xa, xb) + g, max(ya, yb) + g, BASE_T + 1, None, C_THERMAL))

# fin stack along the rear edge, fed by the plenum
fin = rbox("Fin stack", FINS["x0"], FINS["y0"], BASE_T, FINS["x0"] + FINS["t"], FINS["y1"], TOP_Z0, M["alu"], C_THERMAL)
arr = fin.modifiers.new("array", "ARRAY")
arr.use_relative_offset = False
arr.use_constant_offset = True
arr.constant_offset_displace = (FINS["pitch"] * MM, 0, 0)
arr.count = int((FINS["x1"] - FINS["x0"]) / FINS["pitch"])
# plenum duct: closed front/top/bottom, open to the fins (rear) and to the blower (right)
plen = rbox("Plenum duct", PLENUM["x0"], PLENUM["y0"], BASE_T, PLENUM["x1"], PLENUM["y1"], TOP_Z0, M["alu"], C_THERMAL, bevel=0.3)
boolean_cut(plen, rbox("cut", PLENUM["x0"] + 1, PLENUM["y0"] + 1, BASE_T + 0.6,
                       PLENUM["x1"] + 1, PLENUM["y1"] + 1, TOP_Z0 - 0.6, None, C_THERMAL))

# laptop-style blower: bottom inlet over the grille, top inlet fed by the side louvres,
# outlet on its left face into the plenum
bx0, by0, bs = BLOWER["x0"], BLOWER["y0"], BLOWER["size"]
bh = rbox("Blower housing", bx0, by0, BASE_T, bx0 + bs, by0 + bs, BASE_T + BLOWER["h"], M["plastic"], C_THERMAL,
          r=BLOWER["r"], bevel=0.4)
bh_top = BASE_T + BLOWER["h"]
boolean_cut(bh, cyl("cut", bx, by, (BASE_T + bh_top) / 2, 18, BLOWER["h"] - 1.2, None, C_THERMAL, verts=64))  # scroll cavity
boolean_cut(bh, cyl("cut", bx, by, bh_top, 16, 3, None, C_THERMAL, verts=48))     # top inlet
boolean_cut(bh, cyl("cut", bx, by, BASE_T, 16, 3, None, C_THERMAL, verts=48))     # bottom inlet
boolean_cut(bh, rbox("cut", bx0 - 1, PLENUM["y0"] + 1, BASE_T + 0.6, bx, PLENUM["y1"] - 0.5,
                     bh_top - 0.6, None, C_THERMAL))                                 # outlet
cyl("Blower impeller hub", bx, by, BASE_T + 4.8, 7, 2.4, M["plastic"], C_THERMAL, verts=32)
blades = []
for k in range(33):
    b = rbox(f"blade{k}", -0.25, 8, BASE_T + 1.0, 0.25, 15, BASE_T + 6.0, M["plastic"], C_THERMAL)
    b.rotation_euler = (0, 0, 2 * math.pi * k / 33 + 0.35)
    b.location = (bx * MM, by * MM, 0)
    blades.append(b)
join(blades, "Blower impeller blades")

# ---------------------------------------------------------------- boards
UFL_POS = {}


def receptacle(name, x, y):
    UFL_POS[name] = (x, y)
    return rbox(f"MHF4 receptacle ({name})", x - 1, y - 1, PCB_TOP, x + 1, y + 1, PCB_TOP + MHF4_RECEPT_H, M["gold"], C_BOARDS)


def board(spec):
    """Chips-down board: PCB on top, packages hang below toward the plate."""
    name, (x0, y0, x1, y1) = spec["name"], spec["rect"]
    assert x1 <= BOARD_MAX_X, f"{name} intrudes on the cable descent zone"
    parts = [rbox(name + " PCB", x0, y0, PCB_Z0, x1, y1, PCB_TOP, M[spec.get("mat", "pcb")], C_BOARDS, r=1.5)]
    for (cx, cy, w, d, h) in spec.get("chips", ()):
        parts.append(rbox(name + " IC", cx - w / 2, cy - d / 2, PCB_Z0 - h, cx + w / 2, cy + d / 2, PCB_Z0, M["chip"], C_BOARDS, bevel=0.15))
    for (cx, cy, w, d, h) in spec.get("cans", ()):
        parts.append(rbox(name + " can", cx - w / 2, cy - d / 2, PCB_Z0 - h, cx + w / 2, cy + d / 2, PCB_Z0, M["can"], C_BOARDS, bevel=0.2))
    for cname, (ux, uy) in spec.get("ufl", {}).items():
        parts.append(receptacle(cname, ux, uy))
    if name.startswith("Dock board"):
        for pname, yc in USBC_PORTS:
            parts.append(rbox(name + " " + pname, USBC["x0"], yc - USBC["w"] / 2, USBC_ZC - USBC["h"] / 2,
                              USBC["x1"], yc + USBC["w"] / 2, USBC_ZC + USBC["h"] / 2, M["steel"], C_BOARDS, r=1.2))
    return join(parts, name)


def pocket_wall(name, x0, y0, x1, y1, notches=()):
    """Milled wall under the board edge: with the board's ground plane on top it
    closes a shielded pocket around the chips (the RF lid is the PCB itself)."""
    ring = rbox(f"Pocket wall ({name})", x0 + 0.3, y0 + 0.3, BASE_T, x1 - 0.3, y1 - 0.3, PCB_Z0, M["alu"], C_SLED, r=1.5)
    boolean_cut(ring, rbox("cut", x0 + 1.5, y0 + 1.5, BASE_T - 1, x1 - 1.5, y1 - 1.5, PCB_Z0 + 1, None, C_SLED, r=0.8))
    for (nx0, ny0, nx1, ny1) in notches:
        boolean_cut(ring, rbox("cut", nx0, ny0, BASE_T - 1, nx1, ny1, PCB_Z0 + 1, None, C_SLED))
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
    pocket_wall(spec["name"], *spec["rect"], notches=notches)

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
# drop the edge SMA jacks and micro-USB: replaced by MHF4 pigtails and the dock board
keep = []
for o in meshes:
    xs = [(o.matrix_world @ mathutils.Vector(v)).x for v in o.bound_box]
    if min(xs) < HACKRF_KEEP_X[0] or max(xs) > HACKRF_KEEP_X[1]:
        bpy.data.objects.remove(o, do_unlink=True)
    else:
        keep.append(o)
for n in others:
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
hack = join(keep, "HackRF One PCB (real KiCad design)")
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
link(hack, C_BOARDS)
# board is in the XZ plane with parts toward -Y: rotate so parts face -Z
me = hack.data
me.transform(mathutils.Matrix.Rotation(math.radians(90), 4, "X"))
xs = [v.co.x for v in me.vertices]
ys = [v.co.y for v in me.vertices]
zs = [v.co.z for v in me.vertices]
hw, hd = (max(xs) - min(xs)) / MM, (max(ys) - min(ys)) / MM
print(f"HackRF extents mm: {hw:.1f} {hd:.1f} {(max(zs) - min(zs)) / MM:.2f}")
me.transform(mathutils.Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -max(zs))))
hcx, hcy = HACKRF["center"]
hack.location = (hcx * MM, hcy * MM, PCB_TOP * MM)
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
pocket_wall("HackRF", *hrect, notches=edge_notches(hack, hrect))

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
        rbox(f"Pedestal ({pname})", x0, y0, BASE_T, x1, y1, ped_top, M["alu"], C_THERMAL, bevel=0.2)
    rbox(f"Thermal pad ({pname})", x0 + 0.5, y0 + 0.5, max(ped_top, BASE_T), x1 - 0.5, y1 - 0.5, pad_top, M["pad"], C_THERMAL)
    print(f"pedestal {pname}: chip bottom {lo:.2f} mm")

# ---------------------------------------------------------------- RF pigtails
Z_PLUG = PCB_TOP + MHF4_RECEPT_H + COAX_R + 0.02   # cable leaves the plug above the receptacle


def route(ux, uy, lane):
    """Run along y on the upper layer, one bend, then along x on the lower layer."""
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
    else:
        pts += [(ux + 1.5, uy, Z_PLUG), (ux + 4, uy, Z_LOW)]
    pts += [(CABLE_DESCENT_X, lane, Z_LOW), (SMA_IN_X, lane, Z_SMA)]
    return pts


lengths = {}
for cname, lane in LANES.items():
    ux, uy = UFL_POS[cname]
    pts = route(ux, uy, lane)
    lengths[cname] = polyline_length(pts)
    kraken = cname.startswith("Kraken")
    poly_curve(f"Pigtail ({cname})", pts, M["coax_kraken" if kraken else "coax"], C_CABLES, radius=COAX_R)
    rbox(f"MHF4 plug ({cname})", ux - 1, uy - 1, PCB_TOP + MHF4_RECEPT_H, ux + 1, uy + 1, PCB_TOP + MHF4_MATED_H,
         M["gold"], C_CABLES)
for cname, L in lengths.items():
    print(f"pigtail {cname:18s} {L:6.1f} mm")
scene["pigtail_lengths_mm"] = {k: round(v, 2) for k, v in lengths.items()}

# ---------------------------------------------------------------- top plate
rbox("Top plate (1 mm, grounded shield)", 0, 0, TOP_Z0, W, D, TOP_Z1, M["alu_dark"], C_TOP, r=CORNER_R, bevel=0.3)

# ---------------------------------------------------------------- MacBook Pro 16 (Apple's published dimensions)
BASE_H, LID_H = 10.6, 6.2
rbox("MacBook base", 0, 0, MAC_Z, W, D, MAC_Z + BASE_H, M["mac"], C_MAC, r=11, bevel=1.2)
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
hinge = bpy.data.objects.new("Lid hinge", None)
C_MAC.objects.link(hinge)
hinge.location = (0, D * MM, kb_z * MM)
lid = rbox("MacBook lid", 0, 0, 0, W, D, LID_H, M["mac"], C_MAC, r=11, bevel=1.2)
glass = rbox("Display glass", 4, 4, -0.02, W - 4, D - 4, 0.3, M["glass"], C_MAC, r=8)
panel = rbox("Display panel", 9, 14, -0.04, W - 9, D - 6, 0.0, M["screen"], C_MAC, r=4)
for o in (lid, glass, panel):
    o.location = (0, -D * MM, 0)
    o.parent = hinge
hinge.rotation_euler = (math.radians(-108), 0, 0)
for i, (x, y) in enumerate([(30, 30), (W - 30, 30), (30, D - 30), (W - 30, D - 30)]):
    rbox(f"Mac foot {i}", x - 6, y - 6, MAC_Z - MAC_FOOT_T, x + 6, y + 6, MAC_Z, M["rubber"], C_MAC, r=5)

# ---------------------------------------------------------------- reference: real downloaded assets
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

# ---------------------------------------------------------------- stage
bpy.ops.mesh.primitive_plane_add(size=4, location=(W / 2 * MM, D / 2 * MM, -FOOT_H * MM))
floor = link(bpy.context.active_object, C_STAGE)
floor.name = "Floor"
floor.data.materials.append(M["floor"])

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes["Background"]
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

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("saved", OUT_BLEND)
