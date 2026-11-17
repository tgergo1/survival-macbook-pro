"""Standard parts modelled from their published dimensions (millimetres):
ISO screws, washers and dowel pins, SMA bulkhead jacks, I-PEX MHF4 micro-coax
connectors, USB-C receptacles and plugs, compression springs.

Screw shanks are modelled at the thread's minor diameter and tapped holes at
the tap-drill diameter, so a screw sitting in its hole touches it but does not
overlap it. A screw that misses its hole therefore shows up as a collision in
check_model.py, and the check measures how much thread actually engages.
"""
import math

import bpy  # must be imported before mathutils
import mathutils

from geom import (MM, apply_tf, boolean, cyl, hexalobular, join, lathe, ngon, place, prism,
                  rbox, rounded_rect, helix, to_mesh)

# ISO 261 coarse threads: nominal d, pitch, minor d3, tap drill, ISO 273 medium clearance
THREAD = {
    "M1.6": dict(d=1.6, P=0.35, d3=1.221, tap=1.25, clr=1.8),
    "M2": dict(d=2.0, P=0.40, d3=1.567, tap=1.60, clr=2.4),
    "M2.5": dict(d=2.5, P=0.45, d3=2.013, tap=2.05, clr=2.9),
}
# ISO 14583 pan head, hexalobular (Torx) socket
PAN = {"M2": dict(dk=4.0, k=1.6, A=1.75, drive="T6"), "M2.5": dict(dk=5.0, k=2.0, A=2.40, drive="T8")}
# ISO 14581 countersunk head (90 deg), hexalobular socket
CSK = {"M2": dict(dk=3.8, k=1.2, A=1.75, drive="T6")}
# ISO 4762 socket head cap screw
SHCS = {"M2": dict(dk=3.8, k=2.0, s=1.5)}
# DIN 433 small washers: inner, outer, thickness
WASHER = {"M2": (2.2, 4.0, 0.3), "M2.5": (2.7, 5.0, 0.5)}

FASTENERS = []          # filled as screws are placed; stored in the .blend for the check
_PROTO = {}


def _screw_proto(kind, size, length, materials, stage):
    key = (kind, size, length)
    if key in _PROTO:
        return _PROTO[key]
    t = THREAD[size]
    r3 = t["d3"] / 2
    ch = min(0.3, r3 * 0.5)
    if kind == "pan":
        h = PAN[size]
        dk, k = h["dk"], h["k"]
        # domed pan head; bearing face at z = 0, shank down to -length
        prof = [(0, k), (dk * 0.32, k), (dk * 0.44, k * 0.86), (dk / 2, k * 0.42), (dk / 2, 0),
                (r3, 0), (r3, -length + ch), (r3 - ch, -length), (0, -length)]
        recess = (hexalobular(h["A"]), k - k * 0.6, k + 0.5)
    elif kind == "csk":
        h = CSK[size]
        dk, k = h["dk"], h["k"]
        # top flush at z = 0; ISO length includes the head
        hk = dk / 2 - t["d"] / 2 + 0.1          # 90 deg head
        prof = [(0, 0), (dk / 2, 0), (dk / 2, -0.1), (t["d"] / 2, -hk), (r3, -hk),
                (r3, -length + ch), (r3 - ch, -length), (0, -length)]
        recess = (hexalobular(h["A"]), -k * 0.75, 0.5)
    elif kind == "shcs":
        h = SHCS[size]
        dk, k = h["dk"], h["k"]
        prof = [(0, k), (dk / 2 - 0.2, k), (dk / 2, k - 0.2), (dk / 2, 0), (r3, 0),
                (r3, -length + ch), (r3 - ch, -length), (0, -length)]
        recess = (ngon(6, h["s"] / 2 / math.cos(math.pi / 6)), k - k * 0.6, k + 0.5)
    else:
        raise ValueError(kind)
    ob = lathe(f"proto {key}", prof, materials["screw"], stage, seg=32)
    poly, z0, z1 = recess
    boolean(ob, prism("recess", poly, z0, z1, None, stage))
    ob.hide_render = True
    ob.hide_viewport = True
    _PROTO[key] = ob
    return ob


def screw(kind, size, length, at, axis, c, name, materials, stage, into=None, grip=0.0):
    """Place a screw. `at` is the bearing point (under the head; for
    countersunk screws the flush top surface) and `axis` points out of the
    head (the screw goes in along -axis). Records it for the check."""
    proto = _screw_proto(kind, size, length, materials, stage)
    ob = bpy.data.objects.new(name, proto.data.copy())
    c.objects.link(ob)
    place(ob, at, axis)
    std = {"pan": "ISO 14583", "csk": "ISO 14581", "shcs": "ISO 4762"}[kind]
    ob["standard"] = f"{std} {size}x{length}"
    FASTENERS.append(dict(name=name, size=size, kind=kind, length=length, at=list(at), axis=axis,
                          d=THREAD[size]["d"], tap=THREAD[size]["tap"], into=into or "", grip=grip))
    return ob


def washer(size, at, axis, c, name, materials):
    di, do, s = WASHER[size]
    ob = lathe(name, [(di / 2, 0), (do / 2, 0), (do / 2, s), (di / 2, s)], materials["screw"], c, seg=32, closed=True)
    place(ob, at, axis)
    ob["standard"] = f"DIN 433 {size}"
    return ob


def dowel(name, d, length, at, axis, c, material):
    """ISO 2338 parallel pin, centred on `at`."""
    ch = min(0.15, d * 0.15)
    ob = lathe(name, [(0, -length / 2), (d / 2 - ch, -length / 2), (d / 2, -length / 2 + ch),
                      (d / 2, length / 2 - ch), (d / 2 - ch, length / 2), (0, length / 2)], material, c, seg=20)
    place(ob, at, axis)
    ob["standard"] = f"ISO 2338 {d}x{length} m6"
    return ob


def spring(name, od, wire, z0, z1, turns, at_xy, c, material):
    """Compression spring along +Z between z0 and z1 (compressed length)."""
    ob = helix(name, od / 2 - wire / 2, wire / 2, z0, z1, turns, material, c)
    ob.location = (at_xy[0] * MM, at_xy[1] * MM, 0)
    ob = to_mesh(ob)
    apply_tf(ob)
    ob.name = name
    return ob


# ------------------------------------------------------------------ SMA bulkhead jack
# Rear-mount SMA female bulkhead for 1.13 mm micro-coax: 1/4-36 UNS barrel with
# a D-flat, 5/16" hex nut and internal-tooth lock washer outside the panel, a
# round flange against the inside of the panel, body and crimp ferrule inside.
SMA = dict(thread_od=6.35, pitch=25.4 / 36, flat=2.95, out_len=6.6, bore=4.2, pin=1.27,
           nut_af=25.4 * 5 / 16, nut_t=2.3, washer=(6.5, 8.6, 0.45),
           flange_r=3.4, flange_t=1.4, body_r=2.4, body_len=4.6, ferrule_r=1.05, ferrule_len=2.0)


def sma_inside_len():
    return SMA["flange_t"] + SMA["body_len"] + SMA["ferrule_len"]


def sma_bulkhead(name, at, wall_t, c, materials, stage):
    """`at` = centre of the hole on the panel's outer face; axis +X (outwards)."""
    s = SMA
    r = s["thread_od"] / 2
    rr = r - 0.42
    prof = [(s["bore"] / 2, s["out_len"]), (r - 0.15, s["out_len"]), (r, s["out_len"] - 0.15)]
    z = s["out_len"] - 0.4
    while z > s["nut_t"] + s["washer"][2] + 0.3:     # thread crests (rings) on the exposed barrel
        prof += [(r, z), (rr, z - s["pitch"] / 2)]
        z -= s["pitch"]
    prof += [(r, z), (r, -wall_t), (s["bore"] / 2, -wall_t)]
    barrel = lathe(name + " barrel", prof, materials["gold"], c, seg=36, closed=True)
    # D-flat (world +z side = local -x)
    boolean(barrel, rbox("cut", -r - 1, -r - 1, -wall_t - 0.1, -s["flat"], r + 1, s["out_len"] + 0.1, None, stage))
    ptfe = lathe(name + " PTFE", [(0, s["out_len"] - 0.05), (s["bore"] / 2, s["out_len"] - 0.05),
                                  (s["bore"] / 2, -wall_t), (0, -wall_t)], materials["ptfe"], c, seg=24)
    pin = lathe(name + " contact", [(0, s["out_len"] - 0.02), (s["pin"] / 2, s["out_len"] - 0.02),
                                    (s["pin"] / 2, s["out_len"] - 2.0), (0, s["out_len"] - 2.0)], materials["gold"], c, seg=16)
    boolean(pin, cyl("cut", 0, 0, s["out_len"], 0.3, 2.0, None, stage))     # socket bore
    wi, wo, wt = s["washer"]
    lw = lathe(name + " lock washer", [(wi / 2, 0), (wo / 2, 0), (wo / 2, wt), (wi / 2, wt)],
               materials["nickel"], c, seg=12, closed=True)
    nut = prism(name + " nut", ngon(6, s["nut_af"] / 2 / math.cos(math.pi / 6), math.pi / 6),
                wt, wt + s["nut_t"], materials["gold"], c)
    boolean(nut, cyl("cut", 0, 0, wt + s["nut_t"] / 2, r, s["nut_t"] + 1, None, stage, verts=36))
    nut.modifiers.new("chamfer", "BEVEL").width = 0.25 * MM
    zi = -wall_t
    inner = lathe(name + " body", [
        (s["bore"] / 2 - 0.6, zi), (s["flange_r"], zi), (s["flange_r"], zi - s["flange_t"]),
        (s["body_r"], zi - s["flange_t"]), (s["body_r"], zi - s["flange_t"] - s["body_len"]),
        (s["ferrule_r"], zi - s["flange_t"] - s["body_len"]),
        (s["ferrule_r"], zi - sma_inside_len()), (0, zi - sma_inside_len()), (0, zi + 0.0)],
        materials["gold"], c, seg=32)
    ob = join([barrel, ptfe, pin, lw, nut, inner], name)
    place(ob, at, "+X", spin=0.0)
    return ob


# ------------------------------------------------------------------ I-PEX MHF4
MHF4 = dict(base=2.0, base_t=0.15, ring_od=1.6, ring_id=1.25, h=0.6, mated=1.2, plug_od=2.0)


def mhf4_receptacle(name, x, y, z, c, materials):
    m = MHF4
    base = rbox(name + " base", x - m["base"] / 2, y - m["base"] / 2, z, x + m["base"] / 2, y + m["base"] / 2,
                z + m["base_t"], materials["gold"], c, r=0.2)
    ring = lathe(name + " ring", [(m["ring_id"] / 2, z + m["base_t"]), (m["ring_od"] / 2, z + m["base_t"]),
                                  (m["ring_od"] / 2, z + m["h"]), (m["ring_id"] / 2, z + m["h"])],
                 materials["gold"], c, seg=24, closed=True)
    ring.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)))
    ins = lathe(name + " insulator", [(0, z + m["h"] - 0.1), (m["ring_id"] / 2, z + m["h"] - 0.1),
                                      (m["ring_id"] / 2, z + m["base_t"]), (0, z + m["base_t"])], materials["ptfe"], c, seg=16)
    ins.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)))
    return join([base, ring, ins], name)


def mhf4_plug(name, x, y, z, direction, c, materials):
    """Mated plug: cap over the receptacle ring plus the crimp tail towards
    the cable exit (unit vector in plan)."""
    m = MHF4
    cap = lathe(name + " cap", [(0, z + m["mated"]), (m["plug_od"] / 2, z + m["mated"]),
                                (m["plug_od"] / 2, z + m["base_t"] + 0.05), (m["ring_od"] / 2, z + m["base_t"] + 0.05),
                                (m["ring_od"] / 2, z + m["h"]), (0, z + m["h"])], materials["gold"], c, seg=28)
    cap.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)))
    dx, dy = direction
    tail = rbox(name + " tail", -0.55, 0.6, z + m["h"] + 0.02, 0.55, 2.0, z + m["mated"], materials["gold"], c)
    ang = math.atan2(dy, dx) - math.pi / 2
    tail.data.transform(mathutils.Matrix.Translation((x * MM, y * MM, 0)) @ mathutils.Matrix.Rotation(ang, 4, "Z"))
    return join([cap, tail], name)


# ------------------------------------------------------------------ USB-C
# USB Type-C receptacle (mid-mount) and plug, from the USB-IF Type-C spec:
# receptacle shell 8.94 x 3.26 outside, 8.34 x 2.56 opening; tongue 6.69 x 0.70;
# plug shell 8.25 x 2.40.
USBC_RCP = dict(w=8.94, h=3.26, wi=8.34, hi=2.56, len=7.35, tongue_w=6.69, tongue_t=0.70, tongue_len=4.45)
USBC_PLUG = dict(w=8.25, h=2.40, len=6.65, om_w=12.2, om_h=6.5, om_len=21.0, cable_r=2.1)


def usbc_receptacle(name, at, c, materials, stage):
    """`at` = centre of the opening; the opening faces -X."""
    u = USBC_RCP
    shell = prism(name + " shell", rounded_rect(-u["w"] / 2, -u["h"] / 2, u["w"] / 2, u["h"] / 2, u["h"] / 2 - 1e-3, 8),
                  0, u["len"], materials["steel"], c)
    boolean(shell, prism("cut", rounded_rect(-u["wi"] / 2, -u["hi"] / 2, u["wi"] / 2, u["hi"] / 2, u["hi"] / 2 - 1e-3, 8),
                         -0.1, u["len"] - 0.6, None, stage))
    tongue = rbox(name + " tongue", -u["tongue_w"] / 2, -u["tongue_t"] / 2, u["len"] - 0.6 - u["tongue_len"],
                  u["tongue_w"] / 2, u["tongue_t"] / 2, u["len"] - 0.6, materials["chip"], c, bevel=0.1)
    pins = []
    for k in range(12):
        px = -u["tongue_w"] / 2 + 0.6 + k * 0.5
        for sgn in (-1, 1):
            pins.append(rbox("pin", px - 0.12, sgn * u["tongue_t"] / 2 - (0.02 if sgn > 0 else 0),
                             u["len"] - 0.6 - u["tongue_len"] + 0.4, px + 0.12,
                             sgn * u["tongue_t"] / 2 + (0.0 if sgn > 0 else 0.02), u["len"] - 1.2, materials["gold"], c))
    ob = join([shell, tongue] + pins, name)
    place(ob, at, "+X", spin=math.pi / 2)
    return ob


def usbc_plug(name, at, axis, c, materials, stage, cable_pts=None):
    """Plug fully inserted: `at` = centre of the receptacle opening, `axis` =
    direction the cable leaves in. Returns plug (shell + overmould) and cable."""
    u = USBC_PLUG
    shell = prism(name + " shell", rounded_rect(-u["w"] / 2, -u["h"] / 2, u["w"] / 2, u["h"] / 2, u["h"] / 2 - 1e-3, 8),
                  -6.2, u["len"] - 6.2, materials["steel"], c)
    om = prism(name + " overmould", rounded_rect(-u["om_w"] / 2, -u["om_h"] / 2, u["om_w"] / 2, u["om_h"] / 2, 2.4, 8),
               u["len"] - 6.2, u["len"] - 6.2 + u["om_len"], materials["rubber"], c)
    om.modifiers.new("soft", "BEVEL").width = 0.8 * MM
    om.modifiers["soft"].segments = 3
    relief = lathe(name + " strain relief", [(0, u["len"] - 6.2 + u["om_len"] - 0.5), (u["cable_r"] + 0.6, u["len"] - 6.2 + u["om_len"] - 0.5),
                                             (u["cable_r"] + 0.2, u["len"] - 6.2 + u["om_len"] + 6),
                                             (0, u["len"] - 6.2 + u["om_len"] + 6)], materials["rubber"], c, seg=24)
    ob = join([shell, om, relief], name)
    place(ob, at, axis, spin=math.pi / 2)
    return ob


# ------------------------------------------------------------------ helpers for envelopes
def envelope_cyl(name, at, axis, r, length, c, material):
    ob = lathe(name, [(0, 0), (r, 0), (r, length), (0, length)], material, c, seg=24)
    place(ob, at, axis)
    ob.hide_render = True
    return ob
