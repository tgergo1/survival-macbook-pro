"""Mesh helpers shared by build_sled.py and parts.py. Inputs in millimetres,
Blender data in metres."""
import math

import bpy  # must be imported before bmesh/mathutils, which it provides
import bmesh
import mathutils

MM = 0.001
_STAGE = {}


def set_stage(c):
    """Collection for hidden helper objects (bevel profiles)."""
    _STAGE["c"] = c


def mat(name, rgb, metal=0.0, rough=0.5, alpha=1.0, transmission=0.0, emission=None,
        aniso=0.0, coat=0.0, bump=0.0, bump_scale=800.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
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
    if aniso:
        p.inputs["Anisotropic"].default_value = aniso
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.08
    if bump:
        # fine noise bump: bead blast, anodising or soldermask texture
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 6.0
        bmp = nt.nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        bmp.inputs["Distance"].default_value = 0.00002
        nt.links.new(tex.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
        # small roughness variation reads as a real machined/anodised surface
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough * 0.85
        mr.inputs["To Max"].default_value = rough * 1.15
        nt.links.new(tex.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], p.inputs["Roughness"])
    return m


def link(obj, c):
    for uc in obj.users_collection:
        uc.objects.unlink(obj)
    c.objects.link(obj)
    return obj


def mesh_obj(name, bm, material, c):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
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
    smooth_by_angle(ob)
    return ob


def smooth_by_angle(ob, deg=35.0):
    """Smooth shading on curved faces, sharp edges kept (rounded corners render round)."""
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(deg))


def cyl(name, x, y, z, r, h, material, c, axis="Z", verts=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r * MM, radius2=r * MM, depth=h * MM)
    ob = mesh_obj(name, bm, material, c)
    smooth_by_angle(ob)
    ob.location = (x * MM, y * MM, z * MM)
    if axis == "X":
        ob.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y":
        ob.rotation_euler = (math.pi / 2, 0, 0)
    return ob


def apply_tf(ob):
    """Bake location/rotation into the mesh."""
    m = ob.matrix_basis.copy() if ob.parent is None else ob.matrix_world.copy()
    ob.data.transform(m)
    ob.matrix_basis = mathutils.Matrix.Identity(4)
    return ob


def boolean(target, cutter, op="DIFFERENCE", keep=False):
    md = target.modifiers.new("cut", "BOOLEAN")
    md.operation = op
    md.object = cutter
    md.solver = "EXACT"
    md.use_self = True
    bpy.context.view_layer.objects.active = target
    with bpy.context.temp_override(object=target):
        bpy.ops.object.modifier_move_to_index(modifier=md.name, index=0)
        bpy.ops.object.modifier_apply(modifier=md.name)
    if not keep:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def boolean_cut(target, cutter):
    return boolean(target, cutter)


def join(objs, name):
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        objs[0].name = name
        objs[0].data.name = name
        return objs[0]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def cut_many(target, cutters):
    """One boolean with all cutters joined (much faster than one per cutter)."""
    cutters = [c for c in cutters if c is not None]
    if not cutters:
        return target
    for c in cutters:
        apply_tf(c)
        for md in list(c.modifiers):
            c.modifiers.remove(md)
    return boolean(target, join(cutters, "cutters") if len(cutters) > 1 else cutters[0])


def rect_profile(name, w, h):
    pc = bpy.data.curves.new(name + "_profile", "CURVE")
    ps = pc.splines.new("POLY")
    ps.points.add(3)
    for p, (a, b) in zip(ps.points, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]):
        p.co = (a * MM, b * MM, 0, 1)
    ps.use_cyclic_u = True
    prof = bpy.data.objects.new(name + "_profile", pc)
    _STAGE["c"].objects.link(prof)
    prof.hide_render = True
    prof.hide_viewport = True
    return prof


def poly_curve(name, pts, material, c, radius=None, profile=None, res=3):
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
        cu.bevel_resolution = res
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    c.objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob


def polyline_length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def lathe(name, prof, material, c, seg=32, closed=False):
    """Solid of revolution about local Z. prof = [(r, z), ...] in mm, from the
    axis back to the axis (open chain), or any loop with closed=True."""
    bm = bmesh.new()
    vs = [bm.verts.new((r * MM, 0, z * MM)) for r, z in prof]
    es = [bm.edges.new((a, b)) for a, b in zip(vs, vs[1:])]
    if closed:
        es.append(bm.edges.new((vs[-1], vs[0])))
    bmesh.ops.spin(bm, geom=vs + es, angle=2 * math.pi, steps=seg, axis=(0, 0, 1), cent=(0, 0, 0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, material, c)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def prism(name, poly, z0, z1, material, c):
    """Vertical prism from a plan polygon [(x, y), ...] in mm."""
    bm = bmesh.new()
    bot = [bm.verts.new((x * MM, y * MM, z0 * MM)) for x, y in poly]
    top = [bm.verts.new((x * MM, y * MM, z1 * MM)) for x, y in poly]
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, material, c)
    smooth_by_angle(ob)
    return ob


def star(n, r_out, r_in, rot=0.0):
    pts = []
    for k in range(2 * n):
        r = r_out if k % 2 == 0 else r_in
        a = rot + math.pi * k / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def ngon(n, r, rot=0.0):
    return [(r * math.cos(rot + 2 * math.pi * k / n), r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def hexalobular(a_dia, n=48):
    """Torx-style 6-lobe outline (smooth), A = point-to-point size."""
    pts = []
    ro, ri = a_dia / 2, a_dia / 2 * 0.72
    for k in range(n):
        t = 2 * math.pi * k / n
        r = ri + (ro - ri) * (0.5 + 0.5 * math.cos(6 * t)) ** 1.6
        pts.append((r * math.cos(t), r * math.sin(t)))
    return pts


AXES = {
    "+Z": mathutils.Matrix.Identity(3),
    "-Z": mathutils.Matrix.Rotation(math.pi, 3, "X"),
    "+X": mathutils.Matrix.Rotation(math.pi / 2, 3, "Y"),
    "-X": mathutils.Matrix.Rotation(-math.pi / 2, 3, "Y"),
    "+Y": mathutils.Matrix.Rotation(-math.pi / 2, 3, "X"),
    "-Y": mathutils.Matrix.Rotation(math.pi / 2, 3, "X"),
}


def place(ob, at, axis="+Z", spin=0.0):
    """Bake: local +Z -> axis, local origin -> at (mm)."""
    m = AXES[axis].to_4x4() @ mathutils.Matrix.Rotation(spin, 4, "Z")
    m.translation = mathutils.Vector(at) * MM
    ob.data.transform(m)
    return ob


def rounded_rect(x0, y0, x1, y1, r, seg=8):
    """Plan outline, counter-clockwise, r clamped to the half-size."""
    r = min(r, (x1 - x0) / 2 - 1e-6, (y1 - y0) / 2 - 1e-6)
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rounded_slab(name, x0, y0, x1, y1, z0, z1, r_plan, r_bot, r_top, material, c, seg=10, eseg=6):
    """Slab with rounded plan corners and filleted bottom and top edges
    (a laptop body). Lofted from stacked rounded-rect loops."""
    loops = []
    for k in range(eseg + 1):              # bottom fillet, from the flat bottom up
        a = math.pi / 2 * k / eseg
        inset = r_bot * (1 - math.sin(a))
        loops.append((inset, z0 + r_bot * (1 - math.cos(a))))
    for k in range(eseg + 1):              # top fillet, up to the flat top
        a = math.pi / 2 * k / eseg
        inset = r_top * (1 - math.cos(a))
        loops.append((inset, z1 - r_top + r_top * math.sin(a)))
    bm = bmesh.new()
    rings = []
    for inset, z in loops:
        pts = rounded_rect(x0 + inset, y0 + inset, x1 - inset, y1 - inset, max(r_plan - inset, 0.5), seg)
        rings.append([bm.verts.new((x * MM, y * MM, z * MM)) for x, y in pts])
    n = len(rings[0])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    for ra, rb in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, material, c)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def helix(name, r, wire_r, z0, z1, turns, material, c, closed_ends=True):
    """Compression spring along +Z, centred on the origin axis."""
    pts = []
    n = int(turns * 24)
    for k in range(n + 1):
        t = k / n
        a = 2 * math.pi * turns * t
        # closed (ground) ends: flatten pitch in the first and last turn
        if closed_ends:
            edge = 1 / turns
            if t < edge:
                zz = wire_r + (t / edge) * wire_r * 2
            elif t > 1 - edge:
                zz = (z1 - z0) - wire_r - ((1 - t) / edge) * wire_r * 2
            else:
                zz = wire_r * 3 + (t - edge) / (1 - 2 * edge) * ((z1 - z0) - 6 * wire_r)
        else:
            zz = wire_r + t * ((z1 - z0) - 2 * wire_r)
        pts.append((r * math.cos(a), r * math.sin(a), z0 + zz))
    return poly_curve(name, pts, material, c, radius=wire_r, res=2)


def to_mesh(ob):
    """Convert a curve object to a mesh in place (for joining and booleans)."""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    return bpy.context.view_layer.objects.active
