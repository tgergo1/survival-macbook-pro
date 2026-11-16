"""Render views of out/osint_sled.blend.
usage: python render_views.py <view> <quality: draft|final>"""
import os
import sys
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[1]
view, quality = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "model/osint_sled.blend"))
scene = bpy.context.scene
MM = 0.001
W, D = 355.7, 248.1


def col(name):
    return bpy.data.collections[name]


def hide(name, state=True):
    col(name).hide_render = state


def shift(name, dz):
    for o in col(name).objects:
        if o.parent is None:
            o.location.z += dz * MM


def camera(loc, target, lens=50, ortho=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.005
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    cam.location = loc
    d = mathutils.Vector(target) - mathutils.Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam


ctr = (W / 2 * MM, D / 2 * MM, 0.012)
hide("Reference - real assets")

if view == "hero":
    camera((0.56, -0.30, 0.16), (0.20, 0.10, 0.03), lens=42)
elif view == "exploded":
    hide("MacBook Pro 16")
    for o in col("Top plate").objects:
        o.location.z += 120 * MM
        o.location.y += 270 * MM
    shift("Boards", 55)
    shift("RF pigtails", 55)
    camera((-0.06, -0.50, 0.52), (0.18, 0.20, 0.05), lens=34)
elif view == "layout":
    hide("MacBook Pro 16")
    hide("Top plate")
    camera((W / 2 * MM, D / 2 * MM, 0.8), (W / 2 * MM, D / 2 * MM, 0), ortho=0.40)
elif view == "thermal":
    hide("MacBook Pro 16")
    hide("Top plate")
    hide("Boards")
    hide("RF pigtails")
    camera((0.56, 0.52, 0.30), (0.17, 0.11, 0.0), lens=44)
elif view == "reference":
    for c in bpy.data.collections:
        if c.name not in ("Reference - real assets", "Stage"):
            hide(c.name)
    hide("Reference - real assets", False)
    camera((-0.105, -0.10, 0.25), (-0.105, 0.115, 0.0), lens=40)

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24 if quality == "draft" else 64
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.resolution_x = 960 if quality == "draft" else 1600
scene.render.resolution_y = 600 if quality == "draft" else 1000
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = float(os.environ.get("EXPO", "-2.5"))
scene.render.filepath = str(ROOT / f"renders/render_{view}{'_draft' if quality == 'draft' else ''}.png")
bpy.ops.render.render(write_still=True)
print("wrote", scene.render.filepath)
