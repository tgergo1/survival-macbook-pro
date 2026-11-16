"""Build the caseless OSINT sled in Blender (bpy 5.3). Units: millimetres in
code, converted to metres. Sled origin = front-left-bottom corner;
x = right, y = towards the rear (hinge), z = up."""
import math
import sys
import bpy  # noqa: must load before bmesh
import bmesh
import bpy
import mathutils

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HACKRF_GLB = str(ROOT / "model/assets/hackrf-one.glb")
FLIPPER_GLB = str(ROOT / "model/assets/flipper-zero.glb")
OUT_BLEND = str(ROOT / "model/osint_sled.blend")

MM = 0.001
W, D = 355.7, 248.1          # MacBook Pro 16" footprint
BASE_T = 2.5                 # base plate
PCB_TOP = 8.4                # back of chips-down boards
TOP_Z0, TOP_Z1 = 9.8, 10.8   # 1 mm top plate
RAIL_T = 2.0
MAC_Z = TOP_Z1 + RAIL_T + 0.6

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
    "can": mat("Tin shield can", (0.80, 0.80, 0.80), 1.0, 0.28),
    "chip": mat("IC package", (0.03, 0.03, 0.03), 0.0, 0.55),
    "gold": mat("Gold SMA", (1.0, 0.77, 0.34), 1.0, 0.22),
    "coax": mat("Micro-coax 1.13", (0.15, 0.15, 0.16), 0.0, 0.6),
    "rubber": mat("Rubber", (0.02, 0.02, 0.02), 0.0, 0.85),
    "plastic": mat("Blower plastic", (0.04, 0.04, 0.045), 0.0, 0.5),
    "pad": mat("Thermal pad", (0.55, 0.35, 0.65), 0.0, 0.7),
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


def curve_path(name, pts, radius, material, c, profile_rect=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x * MM, y * MM, z * MM, 1)
    if profile_rect:
        w, h = profile_rect
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
        cu.bevel_mode = "OBJECT"
        cu.bevel_object = prof
    else:
        cu.bevel_depth = radius * MM
        cu.bevel_resolution = 3
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    c.objects.link(ob)
    ob.data.materials.append(material)
    return ob


def smooth_cable(name, pts, c):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.bezier_points, pts):
        p.co = (x * MM, y * MM, z * MM)
        p.handle_left_type = p.handle_right_type = "AUTO"
    cu.bevel_depth = 0.56 * MM
    cu.bevel_resolution = 2
    ob = bpy.data.objects.new(name, cu)
    c.objects.link(ob)
    ob.data.materials.append(M["coax"])
    return ob


# ---------------------------------------------------------------- chassis
base = rbox("Base plate (6061, 2.5 mm)", 0, 0, 0, W, D, BASE_T, M["alu"], C_SLED, r=9, bevel=0.4)
# Proxmark read window through the base plate
win_cut = rbox("cut", 188, 12, -1, 248, 54, BASE_T + 1, None, C_SLED, r=4)
boolean_cut(base, win_cut)
rbox("Proxmark RF window (PC)", 188, 12, 0.2, 248, 54, BASE_T - 0.2, M["window"], C_SLED, r=4)

# perimeter walls (rear edge left open behind the fin stack = exhaust)
wall_h0, wall_h1 = BASE_T, TOP_Z0
outer = rbox("Side walls", 0, 0, wall_h0, W, D, wall_h1, M["alu"], C_SLED, r=9, bevel=0.3)
inner = rbox("cut", 3, 3, wall_h0 - 1, W - 3, D - 3, wall_h1 + 1, None, C_SLED, r=6)
boolean_cut(outer, inner)
exhaust = rbox("cut", 8, D - 5, wall_h0 + 0.8, 298, D + 2, wall_h1 - 0.8, None, C_SLED)
boolean_cut(outer, exhaust)

# rubber rails the MacBook rests on
for i, x in enumerate((24, W - 36)):
    rbox(f"Rubber rail {i + 1}", x, 18, TOP_Z1, x + 12, D - 18, TOP_Z1 + RAIL_T, M["rubber"], C_TOP, bevel=0.5)

# right-side SMA bulkheads (U.FL pigtails land here)
BULK_Y = [16 + i * 16 for i in range(11)]
for i, y in enumerate(BULK_Y):
    zc = (wall_h0 + wall_h1) / 2
    cyl(f"SMA bulkhead {i + 1}", W + 3.5, y, zc, 3.15, 9, M["gold"], C_SLED, axis="X")
    cyl(f"SMA nut {i + 1}", W + 1.0, y, zc, 4.4, 2.0, M["gold"], C_SLED, axis="X", verts=6)

# blower intake grille through the base plate, plus feet for the intake gap
grille = []
for gx in range(-3, 4):
    for gy in range(-3, 4):
        if gx * gx + gy * gy <= 10:
            grille.append(cyl("g", 326 + gx * 4.4, 212 + gy * 4.4, BASE_T / 2, 1.6, BASE_T + 2, M["alu"], C_SLED, verts=12))
boolean_cut(base, join(grille, "grille"))
for i, (x, y) in enumerate([(14, 14), (W - 14, 14), (14, D - 14), (W - 14, D - 14)]):
    cyl(f"Sled foot {i + 1}", x, y, -1.0, 5, 2.0, M["rubber"], C_SLED, verts=32)

# ---------------------------------------------------------------- thermal
# flattened 6 x 1.7 mm heat pipes set into grooves, top flush with the plate
HP = [
    ("Heat pipe 1 (KrakenSDR)", [(88, 160, 0), (88, 239, 0), (292, 239, 0)]),
    ("Heat pipe 2 (HackRF)", [(235, 175, 0), (235, 231, 0), (292, 231, 0)]),
    ("Heat pipe 3 (Flipper One)", [(76, 78, 0), (12, 78, 0), (12, 243, 0), (60, 243, 0)]),
]
for name, pts in HP:
    pts = [(x, y, BASE_T - 0.3) for x, y, _ in pts]
    curve_path(name, pts, 0, M["copper"], C_THERMAL, profile_rect=(6, 1.7))

# fin stack along the rear edge
fin = rbox("Fin stack", 8, 234, BASE_T, 8.3, D - 1.5, TOP_Z0, M["alu"], C_THERMAL)
arr = fin.modifiers.new("array", "ARRAY")
arr.use_relative_offset = False
arr.use_constant_offset = True
arr.constant_offset_displace = (1.35 * MM, 0, 0)
arr.count = int((298 - 8) / 1.35)
# plenum duct from blower to fins
plen = rbox("Plenum duct", 8, 223, BASE_T, 300, 234, TOP_Z0, M["alu"], C_THERMAL, bevel=0.3)
plen_in = rbox("cut", 9, 224, BASE_T + 0.6, 301, 233, TOP_Z0 - 0.6, None, C_THERMAL)
boolean_cut(plen, plen_in)

# laptop-style blower, 52 x 52 x 6.5 mm
bh = rbox("Blower housing", 300, 186, BASE_T, 352, 238, BASE_T + 6.5, M["plastic"], C_THERMAL, r=14, bevel=0.4)
hole = cyl("cut", 326, 212, BASE_T + 6.5, 16, 3, M["plastic"], C_THERMAL, verts=48)
boolean_cut(bh, hole)
hub = cyl("Blower impeller hub", 326, 212, BASE_T + 4.8, 7, 2.4, M["plastic"], C_THERMAL, verts=32)
blades = []
for k in range(33):
    a = 2 * math.pi * k / 33
    b = rbox(f"blade{k}", -0.25, 8, BASE_T + 1.0, 0.25, 15, BASE_T + 6.0, M["plastic"], C_THERMAL)
    b.rotation_euler = (0, 0, a + 0.35)
    b.location = (326 * MM, 212 * MM, 0)
    blades.append(b)
join(blades, "Blower impeller blades")

# ---------------------------------------------------------------- boards
PCB_T = 1.6
PCB_Z0 = PCB_TOP - PCB_T


def board(name, x0, y0, x1, y1, material=None, chips=(), cans=(), ufl=()):
    """Chips-down board: PCB on top, packages hang below toward the plate."""
    parts = [rbox(name + " PCB", x0, y0, PCB_Z0, x1, y1, PCB_TOP, material or M["pcb"], C_BOARDS, r=1.5)]
    for (cx, cy, w, d, h) in chips:
        parts.append(rbox(name + " IC", cx - w / 2, cy - d / 2, PCB_Z0 - h, cx + w / 2, cy + d / 2, PCB_Z0, M["chip"], C_BOARDS, bevel=0.15))
    for (cx, cy, w, d, h) in cans:
        parts.append(rbox(name + " can", cx - w / 2, cy - d / 2, PCB_Z0 - h, cx + w / 2, cy + d / 2, PCB_Z0, M["can"], C_BOARDS, bevel=0.2))
    for (ux, uy) in ufl:
        parts.append(rbox(name + " U.FL", ux - 1.5, uy - 1.5, PCB_TOP, ux + 1.5, uy + 1.5, PCB_TOP + 1.25, M["gold"], C_BOARDS))
    return join(parts, name)


# KrakenSDR: bare board modelled from the official enclosure drawing
# (167.2 x 104.5 mm body, 5 channels on 27.8 mm pitch).
KX = [32.9, 60.7, 88.5, 116.3, 144.1]
board("KrakenSDR (bare, from official drawing)", 6, 120, 171, 220, M["pcb_black"],
      chips=[(88.5, 150, 9, 9, 1.0), (40, 140, 6, 6, 1.0), (140, 140, 5, 5, 1.0)],
      cans=[(x, 206, 21, 19, 3.4) for x in KX],
      ufl=[(x, 216) for x in KX])
board("USB hub (soldered flex)", 175, 114, 295, 134, chips=[(205, 124, 7, 7, 0.9), (255, 124, 5, 5, 0.9)])
board("Flipper One (bay placeholder, board TBD)", 6, 45, 146, 110, M["pcb_purple"],
      chips=[(71, 77, 15, 15, 1.2), (100, 77, 12, 10, 1.0), (100, 95, 12, 10, 1.0), (125, 60, 30, 22, 1.4)],
      ufl=[(138, 100), (138, 90)])
board("Airspy HF+ Discovery (bare)", 175, 64, 230, 104, chips=[(202, 84, 7, 7, 0.9)], cans=[(190, 84, 14, 16, 2.0)], ufl=[(226, 96)])
board("Wi-Fi adapter (bare)", 240, 80, 310, 105, chips=[(270, 92, 8, 8, 0.9)], ufl=[(305, 92)])
board("Proxmark3 RDV4 (bare)", 175, 6, 261, 60, M["pcb_black"], chips=[(205, 40, 14, 14, 1.4), (240, 40, 8, 8, 1.0)])
board("Flipper Zero (bare-board bay)", 264, 10, 350, 46, chips=[(300, 28, 10, 10, 1.0), (330, 28, 6, 6, 1.0)])
board("BLE sniffer nRF52840", 304, 120, 350, 138, chips=[(320, 129, 7, 7, 0.9)])
board("LoRa node nRF52840 + SX1262", 312, 150, 342, 173, chips=[(327, 161, 8, 8, 0.9)], ufl=[(338, 168)])

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
# drop the edge SMA jacks and micro-USB: replaced by U.FL pigtails and soldered flex
keep = []
for o in meshes:
    xs = [(o.matrix_world @ mathutils.Vector(v)).x for v in o.bound_box]
    if min(xs) < 0.0595 or max(xs) > 0.1805:
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
# board is in the XZ plane with parts toward -Y: rotate so parts face -Z,
me = hack.data
rot = mathutils.Matrix.Rotation(math.radians(90), 4, "X")
me.transform(rot)
xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
print("HackRF extents mm:", round((max(xs) - min(xs)) * 1000, 1), round((max(ys) - min(ys)) * 1000, 1), round((max(zs) - min(zs)) * 1000, 2))
me.transform(mathutils.Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -max(zs))))
hack.location = (235 * MM, 177.5 * MM, PCB_TOP * MM)
ref_h = hack.copy(); ref_h.data = hack.data.copy(); C_REF.objects.link(ref_h)
ref_h.name = "HackRF One PCB (real, reference view)"
ref_h.rotation_mode = "XYZ"
ref_h.rotation_euler = (math.pi, 0, 0)
ref_h.location = (-150 * MM, 120 * MM, -0.4 * MM)
rbox("HackRF U.FL", 233.5, 213.5, PCB_TOP, 236.5, 216.5, PCB_TOP + 1.25, M["gold"], C_BOARDS)

# aluminium pedestals under the hottest chips, sized to each chip's real depth
PEDESTALS = [  # KrakenSDR tuner/ADC cans, Flipper One SoC, HackRF FPGA/ADC area
    *[(x - 11, 196, x + 11, 216) for x in KX],
    (63, 69, 79, 85), (196, 160, 214, 178), (232, 168, 252, 188),
]
bpy.context.view_layer.update()
board_objs = [o for o in C_BOARDS.objects if o.type == "MESH"]
for i, (x0, y0, x1, y1) in enumerate(PEDESTALS):
    lo = 1e9
    for o in board_objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            w = mw @ v.co
            if x0 * MM <= w.x <= x1 * MM and y0 * MM <= w.y <= y1 * MM:
                lo = min(lo, w.z / MM)
    if lo > 1e8:
        continue
    pad_top = lo - 0.05
    ped_top = pad_top - 0.5
    if ped_top > BASE_T + 0.2:
        rbox(f"Pedestal {i + 1}", x0, y0, BASE_T, x1, y1, ped_top, M["alu"], C_THERMAL, bevel=0.2)
    rbox(f"Thermal pad {i + 1}", x0 + 0.5, y0 + 0.5, max(ped_top, BASE_T), x1 - 0.5, y1 - 0.5, pad_top, M["pad"], C_THERMAL)
    print(f"pedestal {i + 1}: chip bottom {lo:.2f} mm")

# ---------------------------------------------------------------- RF pigtails
UFL = [(x, 216) for x in KX] + [(235, 215), (226, 96), (305, 92), (338, 168), (138, 100), (138, 90)]
UFL.sort(key=lambda p: p[1])
for i, ((ux, uy), by) in enumerate(zip(UFL, BULK_Y)):
    zc = (wall_h0 + wall_h1) / 2
    zr = PCB_TOP + 0.75
    pts = [(ux, uy, PCB_TOP + 1.25), (ux + 4, uy + (by - uy) * 0.15, zr), ((ux + 330) / 2, (uy + by) / 2, zr), (338, by, zr - 0.4), (W - 4, by, zc)]
    smooth_cable(f"Pigtail {i + 1}", pts, C_CABLES)

# ---------------------------------------------------------------- top plate
top = rbox("Top plate (1 mm, grounded shield)", 0, 0, TOP_Z0, W, D, TOP_Z1, M["alu_dark"], C_TOP, r=9, bevel=0.3)
# sealed top: the blower breathes through a grille in the base plate instead

# ---------------------------------------------------------------- MacBook Pro 16 (modelled from Apple's published dimensions)
BASE_H, LID_H = 10.6, 6.2
mac = []
mac.append(rbox("MacBook base", 0, 0, MAC_Z, W, D, MAC_Z + BASE_H, M["mac"], C_MAC, r=11, bevel=1.2))
kb_z = MAC_Z + BASE_H
mac.append(rbox("Keyboard well", 40, 128, kb_z - 0.6, W - 40, D - 14, kb_z + 0.01, M["key"], C_MAC, r=2))
keys = []
rows = [(14, 16.0), (14, 18.0), (13, 18.0), (12, 18.0), (11, 18.0), (9, 13.0)]
y = D - 22
for n, kh in rows:
    pitch = (W - 84) / n
    for k in range(n):
        x = 42 + k * pitch
        keys.append(rbox("k", x + 1, y - kh + 2, kb_z - 0.6, x + pitch - 1, y, kb_z + 0.5, M["key"], C_MAC, bevel=0.4))
    y -= kh + 2
join(keys, "Keycaps")
mac.append(rbox("Trackpad", W / 2 - 80, 14, kb_z - 0.05, W / 2 + 80, 112, kb_z + 0.02, M["mac"], C_MAC, r=4))
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
mac_feet = [rbox(f"Mac foot {i}", x - 6, y - 6, MAC_Z - 0.6, x + 6, y + 6, MAC_Z, M["rubber"], C_MAC, r=5)
            for i, (x, y) in enumerate([(30, 30), (W - 30, 30), (30, D - 30), (W - 30, D - 30)])]

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
bpy.ops.mesh.primitive_plane_add(size=4, location=(W / 2 * MM, D / 2 * MM, -2.0 * MM))
floor = link(bpy.context.active_object, C_STAGE)
floor.name = "Floor"
floor.data.materials.append(M["floor"])

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.55, 0.57, 0.60, 1)
bg.inputs["Strength"].default_value = 0.35


def area(name, loc, size, energy, target):
    l = bpy.data.lights.new(name, "AREA")
    l.size = size
    l.energy = energy
    o = bpy.data.objects.new(name, l)
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
