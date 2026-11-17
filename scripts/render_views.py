"""Render a view of model/osint_sled.blend with Cycles (GPU when available).

usage: blender -b --factory-startup --python scripts/render_views.py -- <view> <draft|final>
views: hero | hero_left | exploded | layout | thermal | latch | rear_stop | sma | fasteners | reference

The studio HDRI (Poly Haven, CC0) is downloaded to build/hdri on first use.
Set EXPO to override the exposure."""
import os
import sys
import urllib.request
from pathlib import Path

import bpy  # must be imported before mathutils
import mathutils

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sled_config import D, LANES, MAC_Z, W, Z_SMA  # noqa: E402

VIEWS = ("hero", "hero_left", "insert", "exploded", "layout", "thermal", "latch", "rear_stop", "sma", "fasteners", "reference")
ROOT = Path(__file__).resolve().parents[1]
HDRI = ROOT / "build/hdri/studio_small_09_2k.hdr"
HDRI_URL = "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/studio_small_09_2k.hdr"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
view, quality = args[0], args[1]
if view not in VIEWS or quality not in ("draft", "final"):
    raise SystemExit(__doc__)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "model/osint_sled.blend"))
scene = bpy.context.scene
MM = 0.001


def col(name):
    return bpy.data.collections[name]


def hide(name, state=True):
    col(name).hide_render = state


def move(obs, dx=0.0, dy=0.0, dz=0.0):
    for o in obs:
        if o.parent is None:
            o.location += mathutils.Vector((dx, dy, dz)) * MM


def objs(cname, prefix=None, contains=None):
    return [o for o in col(cname).objects
            if (prefix is None or o.name.startswith(prefix)) and (contains is None or contains in o.name)]


def camera(loc, target, lens=50, ortho=None, fstop=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.002
    cd.sensor_width = 36
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    cam.location = [v * MM for v in loc]
    t = mathutils.Vector(target) * MM
    d = t - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if fstop:
        cd.dof.use_dof = True
        cd.dof.focus_distance = d.length
        cd.dof.aperture_fstop = fstop
    scene.camera = cam


# ---------------------------------------------------------------- environment: studio HDRI + softboxes
if not HDRI.exists():
    HDRI.parent.mkdir(parents=True, exist_ok=True)
    print("downloading", HDRI_URL)
    urllib.request.urlretrieve(HDRI_URL, HDRI)
nt = scene.world.node_tree
bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(str(HDRI))
mapping = nt.nodes.new("ShaderNodeMapping")
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping.inputs["Rotation"].default_value = (0, 0, float(os.environ.get("HDRI_ROT", "1.9")))
nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9
for name, e in (("Key light", 60), ("Fill light", 18), ("Rim light", 70)):
    bpy.data.objects[name].data.energy = e
# seamless studio floor
fl = bpy.data.materials["Floor"]
p = next(n for n in fl.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
p.inputs["Base Color"].default_value = (0.42, 0.43, 0.44, 1)
p.inputs["Roughness"].default_value = 0.45

hide("Reference - real assets")
hide("Keep-out envelopes")

if view == "hero":
    camera((520, -300, 165), (225, 95, 22), lens=45, fstop=5.6)
elif view == "hero_left":
    camera((-230, -150, 120), (40, 90, 14), lens=50, fstop=5.6)
elif view == "insert":
    hide("External cables")
    move(col("MacBook Pro 16").objects, dy=-120)
    for o in col("Mount").objects:          # the Mac's underside holds the pawls down
        if "pawl" in o.name:
            o.location.z -= 3.6 * MM
    bpy.data.objects["Lid hinge"].rotation_euler = (0, 0, 0)    # lid closed
    camera((540, 560, 330), (185, 140, 8), lens=42, fstop=8)
elif view == "exploded":
    hide("MacBook Pro 16")
    hide("External cables")
    move(col("Top plate").objects, dz=110)
    move(col("Mount").objects, dz=150)
    for o in col("Mount").objects:
        if "Latch" in o.name:
            o.location.z -= 150 * MM
            o.location.y -= 40 * MM
    for o in col("Fasteners").objects:
        if "top plate" in o.name:
            o.location.z += 128 * MM
        elif "countersunk" in o.name:
            o.location.z += 168 * MM
        elif "latch" in o.name:
            o.location.y -= 62 * MM
        else:
            o.location.z += 72 * MM
    move(col("Boards").objects, dz=55)
    move(col("RF pigtails").objects, dz=55)
    camera((-30, -400, 420), (180, 160, 70), lens=34)
elif view == "layout":
    hide("MacBook Pro 16")
    hide("Top plate")
    hide("Mount")
    hide("External cables")
    for o in col("Fasteners").objects:
        if "top plate" in o.name or "countersunk" in o.name:
            o.hide_render = True
    camera((W / 2, D / 2, 800), (W / 2, D / 2, 0), ortho=0.40)
elif view == "thermal":
    for c in ("MacBook Pro 16", "Top plate", "Boards", "RF pigtails", "Mount", "External cables", "Fasteners"):
        hide(c)
    camera((560, 520, 300), (170, 110, 0), lens=44)
elif view == "latch":
    hide("External cables")
    camera((-45, -95, 62), (18, 0, 12), lens=70, fstop=8)
elif view == "rear_stop":
    bpy.data.objects["Lid hinge"].rotation_euler = (0, 0, 0)    # lid closed
    camera((W + 110, D + 105, 80), (W - 12, D - 8, MAC_Z), lens=70, fstop=11)
elif view == "sma":
    hide("External cables")
    mid = (LANES["Kraken CH2"] + LANES["Airspy HF+"]) / 2
    camera((W + 85, mid - 95, 42), (W + 2, mid + 8, Z_SMA + 2), lens=70, fstop=6.3)
elif view == "fasteners":
    for c in ("MacBook Pro 16", "Top plate", "Mount", "External cables"):
        hide(c)
    for o in col("Fasteners").objects:
        if "top plate" in o.name or "countersunk" in o.name:
            o.hide_render = True
    camera((318, 112, 34), (291.2, 142.2, 9), lens=90, fstop=11)
elif view == "reference":
    for c in bpy.data.collections:
        if c.name not in ("Reference - real assets", "Stage"):
            hide(c.name)
    hide("Reference - real assets", False)
    camera((-105, -100, 250), (-105, 115, 0), lens=40)

scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("METAL", "OPTIX", "CUDA", "HIP"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = "GPU"
                print("rendering on", dev_type)
                break
        except TypeError:
            continue
except KeyError:
    pass
scene.cycles.samples = 48 if quality == "draft" else 512
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.01
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 10
scene.cycles.glossy_bounces = 6
scene.cycles.transmission_bounces = 8
scene.render.resolution_x = 1200 if quality == "draft" else 2400
scene.render.resolution_y = 750 if quality == "draft" else 1500
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = float(os.environ.get("EXPO", "-0.6"))
scene.render.filepath = str(ROOT / f"renders/render_{view}{'_draft' if quality == 'draft' else ''}.png")
bpy.ops.render.render(write_still=True)
print("wrote", scene.render.filepath)
