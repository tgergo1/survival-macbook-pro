"""Single source of truth for the sled geometry. All values in millimetres.

Sled origin = front-left-bottom corner of the base plate; x = right,
y = towards the rear (hinge), z = up. build_sled.py and check_model.py both
read from here, so a dimension only ever lives in one place.
"""

# ------------------------------------------------------------------ envelope
W, D = 355.7, 248.1          # MacBook Pro 16" footprint (Apple's published size)
CORNER_R = 15.0              # plan-view corner radius of the plates (matches the Mac, see MAC)
WALL_T = 3.0                 # perimeter wall thickness

BASE_T = 2.5                 # 6061 base plate; heat pipes sit flush in grooves
PCB_T = 1.6
PCB_TOP = 8.4                # back of the chips-down boards
PCB_Z0 = PCB_TOP - PCB_T     # chip side of the boards (faces down)

# Above the boards: an MHF4 plug (1.2 mm mated) and two crossing layers of
# 1.13 mm micro-coax must fit under the top plate.
COAX_D = 1.13
COAX_R = COAX_D / 2
MHF4_RECEPT_H = 0.6          # MHF4 receptacle height on the PCB
MHF4_MATED_H = 1.2           # receptacle + plug, mated (Hirose/I-PEX spec ~1.2 mm max)
CABLE_GAP = 0.02             # modelling gap so stacked cables don't touch
Z_LOW = PCB_TOP + COAX_R + CABLE_GAP              # cables running along x
Z_HIGH = Z_LOW + COAX_D + 2 * CABLE_GAP           # cables running along y
TOP_CLEAR = 2.6              # PCB back -> underside of top plate: coax crossings + the USB flat-flex layer
TOP_Z0 = PCB_TOP + TOP_CLEAR # 11.0
TOP_Z1 = TOP_Z0 + 1.0        # 1 mm top plate
assert Z_HIGH + COAX_R < TOP_Z0, "coax crossings must clear the top plate"
assert PCB_TOP + MHF4_MATED_H < TOP_Z0

RAIL_T = 0.7                 # silicone pads the Mac's feet sit on
MAC_FOOT_T = 1.9             # measured: the Mac's rubber feet stand 1.9 mm proud (Apple side photo)
MAC_Z = TOP_Z1 + RAIL_T + MAC_FOOT_T

FOOT_H = 4.0                 # sled feet: 4 mm intake gap under the blower grille

# ------------------------------------------------------------------ RF edge
SMA_X = W                    # bulkheads on the right-hand wall
Z_SMA = 7.0                  # bulkhead centre height (hole Ø6.5 fits the 8.3 mm wall)
SMA_HOLE_R = 3.25            # 6.5 mm D-hole for the 1/4-36 barrel
SMA_HOLE_FLAT = 3.0          # D-flat 3.0 mm above the axis (anti-rotation)
SMA_INSIDE = 8.0             # flange + body + crimp ferrule behind the panel (parts.SMA)
SMA_FERRULE_X = W - WALL_T - SMA_INSIDE   # pigtail enters the ferrule here
CABLE_DESCENT_X = SMA_FERRULE_X - 7.5     # S-bend from Z_LOW down to Z_SMA (bend R > 5x coax OD)
BOARD_MAX_X = 336.0          # boards stay left of the cable descent zone
CORNER_R_CABLE = 5.0         # bend radius at each cable corner (>= 5x coax OD)

# ------------------------------------------------------------------ thermal
HP_W, HP_T = 6.0, 1.7        # flattened heat pipe section
PAD_T = 0.5                  # thermal pad between chip and pedestal
PAD_GAP = 0.05               # compression allowance

BLOWER = dict(x0=296.0, y0=182.0, size=52.0, h=6.5, r=5.0)   # 52 x 52 x 6.5 mm laptop blower
BLOWER_C = (BLOWER["x0"] + BLOWER["size"] / 2, BLOWER["y0"] + BLOWER["size"] / 2)
PLENUM = dict(x0=16.0, x1=BLOWER["x0"], y0=222.0, y1=233.0)    # blower -> fins duct
FINS = dict(x0=16.0, x1=294.0, y0=233.0, y1=D - WALL_T - 0.1, pitch=1.35, t=0.3)
SIDE_INTAKE = dict(y0=192.0, y1=232.0)                         # louvre in the right wall
EXHAUST = dict(x0=16.0, x1=294.0)                               # opening in the rear wall

# Heat pipes run in grooves in the base plate (top flush with BASE_T), from
# the hot spots to the fin stack. Polylines in plan view.
HEAT_PIPES = [
    ("Heat pipe 1 (KrakenSDR bar)", [(150, 206), (28, 206), (28, 236.5), (170, 236.5)]),
    ("Heat pipe 2 (HackRF)", [(205, 169), (242, 169), (242, 243.5), (292, 243.5)]),
    ("Heat pipe 3 (Flipper One)", [(76, 85), (16, 85), (16, 243.5), (60, 243.5)]),
]

# ------------------------------------------------------------------ boards
# KrakenSDR: bare board from KrakenRF's official enclosure drawing
# (github.com/krakenrf/krakensdr_docs, drawings/KrakenSDR.Enclosure.Drawing.NEW.png):
# 167.2 x 104.5 mm body; SMA centres at -57.5, -29.6, -1.7, +26.3, +54.2 mm from the
# centre line (CH4 ... CH0, a uniform 27.9 mm pitch); board screws on a
# 162.6 x 88.8 mm pattern, four per side (21.5 and 45.7 mm steps). The board is
# sized from that pattern with 3 mm edge margins.
KRAKEN_PITCH = 27.9
KRAKEN_RECT = (6.0, 122.0, 174.6, 216.8)
KRAKEN_CX = (KRAKEN_RECT[0] + KRAKEN_RECT[2]) / 2
KRAKEN_CY = (KRAKEN_RECT[1] + KRAKEN_RECT[3]) / 2
KX = [KRAKEN_CX + 54.2 - i * KRAKEN_PITCH for i in range(5)]     # CH0 (right) ... CH4 (left)
KRAKEN_UFL_Y = 213.0
KRAKEN_HOLES = [(KRAKEN_CX + sx * 81.3, KRAKEN_CY + dy) for sx in (-1, 1) for dy in (-44.4, -22.9, 22.8, 44.4)]

# chips/cans: (cx, cy, w, d, h) hanging below the PCB; ufl: connector names -> (x, y)
BOARDS = [
    dict(name="KrakenSDR (bare, from official drawing)", rect=KRAKEN_RECT, mat="pcb_black", holes=KRAKEN_HOLES,
         hole_washer=True,
         chips=[(88.5, 150, 9, 9, 1.0), (40, 140, 6, 6, 1.0), (140, 140, 5, 5, 1.0)],
         cans=[(x, 203, 21, 19, 3.4) for x in KX],
         ufl={f"Kraken CH{i}": (x, KRAKEN_UFL_Y) for i, x in enumerate(KX)}),
    dict(name="USB 2.0 hub (low-rate devices)", rect=(175, 114, 288, 134), holes=[(178, 117), (272, 117), (186, 131), (258, 131)],
         chips=[(205, 124, 7, 7, 0.9), (255, 124, 5, 5, 0.9)]),
    # Flipper One: bay sized from Flipper's official B.1 enclosure CAD (154.9 x 67.1 x 49.3 mm overall);
    # the mainboard itself is not published as a 3D file yet.
    dict(name="Flipper One (bay from official B.1 enclosure)", rect=(6, 56, 146, 118), mat="pcb_purple",
         holes=[(9, 59), (139, 58.6), (9, 115), (141, 95)],
         chips=[(71, 85, 15, 15, 1.2), (100, 77, 12, 10, 1.0), (100, 95, 12, 10, 1.0), (125, 72, 30, 22, 1.4)],
         ufl={"Flipper One LTE": (136, 100), "Flipper One GNSS": (126, 100), "Flipper One LTE div": (131, 113)}),
    # Airspy HF+ Discovery: board measured from RigPix's inside photos, scaled by the
    # ATSAM3U1C's 14 x 14 mm LQFP-100 body: about 58 x 42 mm, four ~3.2 mm corner holes
    # ~4.5 mm in, SMA on a short edge (fits the published 60 x 45 x 10 mm case).
    dict(name="Airspy HF+ Discovery (bare)", rect=(175, 64, 233, 106), hole_washer=True,
         holes=[(179.5, 68.5), (228.5, 68.5), (179.5, 101.5), (228.5, 101.5)],
         chips=[(216, 80, 14, 14, 1.4)], cans=[(196, 87, 26, 24, 2.0)], ufl={"Airspy HF+": (183, 85)}),
    dict(name="Wi-Fi adapter (bare)", rect=(240, 80, 310, 105),
         chips=[(270, 92, 8, 8, 0.9)], ufl={"Wi-Fi A": (305, 92.65), "Wi-Fi B": (300, 100)}),
    # Proxmark3 RDV4: 87 x 54 mm board (Lab401 spec)
    dict(name="Proxmark3 RDV4 (bare)", rect=(175, 6, 261, 60), mat="pcb_black",
         chips=[(205, 40, 14, 14, 1.4), (240, 40, 8, 8, 1.0)]),
    dict(name="Flipper Zero (bare-board bay)", rect=(264, 18, BOARD_MAX_X, 54), holes=[(267, 21), (333, 21), (267, 44), (333, 44)],
         chips=[(296, 36, 10, 10, 1.0), (326, 36, 6, 6, 1.0)], ufl={"Flipper Zero Sub-GHz": (272, 41)}),
    # BLE sniffer: Nordic nRF52840 Dongle (PCA10059), 46 x 15.24 mm; no mounting holes, held by a
    # VHB pad on its pocket wall. Its PCB antenna needs re-working to a pigtail inside the shielded sled.
    dict(name="BLE sniffer nRF52840 Dongle (PCA10059)", rect=(290, 121, BOARD_MAX_X, 136.24), holes=[],
         chips=[(316, 128.6, 7, 7, 0.9)], ufl={"BLE": (296, 128.6)}),
    # LoRa: RAKwireless RAK4631 core (nRF52840 + SX1262, 20 x 30 mm) on a RAK19003 mini base (35 x 30 mm)
    dict(name="LoRa node RAK4631 on RAK19003", rect=(301, 140, BOARD_MAX_X, 170),
         chips=[(318, 155, 20, 14, 2.0)], ufl={"LoRa": (326, 152)}),
    # Dock board: Thunderbolt device controller with PCIe out to two extra xHCI
    # controllers, so the HackRF and the KrakenSDR each get their own USB 2.0
    # root (480 Mbit/s each), plus the single-cable power path (see POWER):
    # EPR sink on the input, 48->28 V EPR source for the Mac's MagSafe, 48->5 V
    # buck for the sled, ideal-diode OR with the Mac's Thunderbolt port and one
    # load switch per board for load shedding.
    dict(name="Dock board (TB controller, 2x xHCI, power path)", rect=(4, 13, 150, 53),
         holes=[(11, 16), (147, 16), (11, 51), (140, 46)],
         chips=[(62, 25, 12, 12, 1.2), (98, 25, 7, 7, 0.9), (122, 25, 7, 7, 0.9), (138, 25, 6, 6, 1.0),
                (15, 20, 4, 4, 0.9),             # USB PD 3.1 EPR sink controller (input)
                (15, 34, 4, 4, 0.9),             # USB PD 3.1 EPR source controller (MagSafe out)
                (22, 46, 4, 4, 0.9),             # PD sink controller on the Thunderbolt port (Mac -> sled, 15 W)
                (34, 22, 7, 7, 3.0),             # 48 -> 5 V buck inductor
                (34, 33, 5, 5, 0.9),             # 48 -> 5 V buck controller
                (80, 44, 10, 10, 4.0),           # 48 -> 28 V buck inductor (140 W)
                (95, 44, 5, 6, 1.0),             # 48 -> 28 V buck MOSFETs
                (108, 44, 3, 3, 0.9),            # ideal-diode OR controller (5 V rail)
                (116, 44, 2, 2, 0.6), (121, 44, 2, 2, 0.6), (126, 44, 2, 2, 0.6),   # load switches
                (131, 44, 2, 2, 0.6), (116, 49, 2, 2, 0.6), (121, 49, 2, 2, 0.6),
                (126, 49, 2, 2, 0.6), (131, 49, 2, 2, 0.6)]),
]

HACKRF = dict(center=(235, 177.5), ufl={"HackRF": (235, 213)})
HACKRF_KEEP_X = (0.0595, 0.1805)   # metres in the imported glTF: drops edge SMAs + micro-USB

# USB-C receptacles on the left wall (mid-mount, centred in the dock PCB)
USBC_PORTS = [("USB-C PD 3.1 in (the one cable, up to 240 W)", 20.0),
              ("USB-C EPR out to MagSafe 3 (up to 140 W)", 33.5),
              ("Thunderbolt to Mac (data, 15 W back-feed)", 46.5)]
USBC = dict(x0=0.3, w=8.94, h=3.26)     # opening 0.3 mm behind the wall face

# Pedestals: (name, x0, y0, x1, y1). Heights come from the measured chip depth.
KRAKEN_BAR = ("KrakenSDR isothermal bar", min(KX) - 11.5, 192, max(KX) + 11.5, 214)
PEDESTALS = [
    KRAKEN_BAR,                                   # one bar under all 5 tuner cans
    ("Flipper One SoC", 63, 77, 79, 93),
    ("HackRF CPLD/MCU", 196, 160, 214, 178),
    ("HackRF RF front end", 232, 168, 252, 188),
    ("Dock TB controller", 55, 18, 69, 32),       # spreads into the base plate
    ("Dock 28 V buck MOSFETs", 92, 41, 98, 47),   # about 4 W at 140 W out
]
PEDESTALS_PLATE_ONLY = {"Dock TB controller", "Dock 28 V buck MOSFETs"}     # allowed without a heat pipe

# ------------------------------------------------------------------ RF routing
# Each pigtail runs along y first (upper layer, Z_HIGH), turns once, then runs
# along x (lower layer, Z_LOW) to its bulkhead. Distinct x for every y-run and
# distinct y for every x-run means crossings are always one layer over the other.
# KrakenSDR lanes step by the channel pitch, so all 5 coherent channels have
# exactly the same Manhattan length (phase matched by construction).
KRAKEN_LANE0 = 50.8         # CH0 (rightmost on the board) takes the lowest lane
LANES = {f"Kraken CH{i}": KRAKEN_LANE0 + i * KRAKEN_PITCH for i in range(5)}
LANES.update({               # the others sit halfway between the Kraken lanes
    "LoRa": 176.3,
    "HackRF": 148.45,
    "Airspy HF+": 120.55,
    "Wi-Fi A": 92.65,
    "Flipper One LTE": 64.75,
    "Flipper One GNSS": 36.8,
})
# Four more SMA bulkheads on the front wall, right of the Proxmark (x of each):
# each pigtail runs along x on the lower layer, bends once, then along -y on
# the upper layer and drops into the bulkhead.
FRONT_LANES = {
    "Flipper Zero Sub-GHz": 272.0,
    "BLE": 286.0,
    "Wi-Fi B": 300.0,
    "Flipper One LTE div": 314.0,
}
FRONT_DESCENT_Y = 18.5       # S-bend down into the front bulkheads starts here
KRAKEN_LENGTH_TOL = 0.5      # mm, max spread across the 5 Kraken pigtails

# ------------------------------------------------------------------ power budget (estimates)
POWER_W = {
    "KrakenSDR (5 tuners, onboard hub)": 11.0,
    "Flipper One (est., LTE active)": 5.0,
    "Dock board (TB controller, 2x xHCI, hub)": 4.0,
    "HackRF (RX)": 2.5,
    "Wi-Fi adapter": 2.0,
    "Airspy HF+ Discovery": 1.0,
    "Blower (PWM)": 1.0,
    "Proxmark3 RDV4": 0.8,
    "Flipper Zero": 0.3,
    "LoRa node (RX)": 0.2,
    "BLE sniffer": 0.1,
}

# ------------------------------------------------------------------ MacBook Pro 16"
# Apple publishes the envelope (355.7 x 248.1 x 16.8 mm, 16-inch 2021 and later)
# but no dimensioned drawing. The rest is MEASURED from Apple's own straight-on
# photos (scale set by the published width and depth; see docs/mac_measurements.md):
#   underside: support.apple.com/100572 (bottom case service guide), 0.219 mm/px,
#              width/depth scales agree to 0.1 %
#   sides:     support.apple.com/111901 (tech specs port images), 0.267 mm/px
# Accuracy is about +-0.5 mm (one or two pixels); check against your own Mac.
MAC = dict(
    W=W, D=D, H=16.8,            # published
    base_h=12.6, lid_h=4.0,      # measured: lid/base seam in the side photo
    r_plan=15.0,                 # measured: plan corner radius 16.0 front, 13.9 rear (bottom photo)
    r_bot=2.5,                   # estimate: bottom edge fillet
    r_top=1.2,                   # estimate: top deck edge fillet
    foot_d=19.0, foot_inset=(26.2, 26.7),   # measured: 4 round feet, centres 26.2 mm from the sides, 26.4/27.0 mm from front/rear
    mass_kg=2.14,                # published (M4 Pro)
)
# Bottom-case screws (measured): x 10.0/10.3 and 119.0/119.6 mm from each side,
# 10.4 mm from the front (4 short) and 10.8 mm from the rear (4 long), heads ~3.3 mm.
MAC_BOTTOM_SCREWS = [(10.3, 10.4), (119.3, 10.4), (W - 119.3, 10.4), (W - 10.3, 10.4),
                     (10.3, D - 10.8), (119.3, D - 10.8), (W - 119.3, D - 10.8), (W - 10.3, D - 10.8)]
# Side intake vents on the underside edge (measured): 25.5 to 150.5 mm from the front, both sides.
MAC_VENTS = dict(y0=25.5, y1=150.5)
# Side ports (measured centres, mm from the FRONT edge): (name, side, y, opening w x h, mating plug overmould w x h).
# Overmould sizes are typical values for each connector type.
MAC_PORTS = [
    ("MagSafe 3", "L", 212.5, (9.6, 3.0), (12.0, 5.0)),
    ("Thunderbolt 4 L1", "L", 193.8, (8.9, 3.2), (12.2, 6.5)),
    ("Thunderbolt 4 L2", "L", 178.8, (8.9, 3.2), (12.2, 6.5)),
    ("Headphone", "L", 166.0, (3.6, 3.6), (7.0, 7.0)),
    ("HDMI", "R", 212.3, (14.4, 4.6), (21.0, 10.5)),
    ("Thunderbolt 4 R", "R", 193.8, (8.9, 3.2), (12.2, 6.5)),
    ("SDXC", "R", 169.2, (24.0, 2.2), (24.0, 2.1)),
]
MAC_PORT_CZ = 8.4                 # measured: port centres above the Mac's bottom face
MAC_PLUG_LEN = 40.0               # plug + strain relief sticking out of the side
# Lid swing (estimate): when open, the display's lower edge drops behind the
# base's rear face. Keep this box clear: up to 8 mm behind the rear face, from
# 5 mm above the Mac's bottom face upward.
LID_KEEPOUT = dict(dy=8.0, z_above_bottom=5.0)

# ------------------------------------------------------------------ mount (Mac to sled)
# Slide-in cradle: the Mac slides in from the front between four TPU-lined side
# jaws, stops against two rear corner stops and is locked by two spring pawls
# that pop up in front of its front face. Lift is held by the jaws' clamp
# friction (the MacBook has no undercut that could be hooked without covering
# a port, a vent or the lid's path).
JAW_T = 2.5                  # 6061 jaw web, black anodised
LINER_T = 0.8                # TPU 85A liner, free thickness
LINER_SQUEEZE = 0.15         # interference per side: the jaws sit 0.15 mm closer than the free liner needs,
                             # so the liners are compressed and clamp the Mac (modelled as overlap)
MAC_WIDTH_TOL = 0.2          # estimate: total width tolerance of the Mac; worst case leaves 0.05 mm squeeze per side
FLANGE_T = 1.2               # jaw flange on the top plate, under the Mac's edge (1.4 mm air gap left)
FLANGE_W = 6.0               # flange reaches this far in under the Mac
JAWS = [   # side, y0, y1, top above the Mac's bottom face, rear corner return
    dict(name="Jaw FL", side="L", y0=8.0, y1=25.0, top=7.0, rear=False),    # ends before the side intake vents
    dict(name="Jaw FR", side="R", y0=12.0, y1=25.0, top=7.0, rear=False),
    dict(name="Jaw RL", side="L", y0=200.0, y1=D, top=3.0, rear=True),
    dict(name="Jaw RR", side="R", y0=220.0, y1=D, top=3.0, rear=True),
]
REAR_RETURN = 28.0           # rear stop wraps 28 mm in from each side (about 14 mm of contact past the corner radius)
JAW_SCREWS = {"Jaw FL": (10.0,),     # one screw: the dock's USB-C ports fill the wall behind
               "Jaw FR": (15.0, 22.0), "Jaw RL": (206.0, 238.0), "Jaw RR": (233.0, 241.0)}
JAW_SCREW_X = 4.0            # countersunk screws through the flange, top plate and into the wall boss
LATCH = dict(x0=15.5, x1=30.5, y0=-6.5, z0=0.5,            # block in front of the sled's front wall (left; mirrored)
             pawl_x=(19.5, 24.5), pawl_y=(-3.0, 0.0), pawl_up=2.5,  # pawl rises 2.5 mm above the Mac's bottom face
             pin_z=10.0, spring=dict(od=2.6, wire=0.3, turns=7),
             screws=((18.0, 5.0), (27.5, 5.0)))          # (x, z) of the two M2 screws into the front wall
SILICONE_RAILS = [(16.0, 42.0), (W - 42.0, W - 16.0)]       # x ranges; the Mac's feet sit on these

# ------------------------------------------------------------------ fasteners
WALL_BOSS_R = 2.0            # bosses milled inside the perimeter wall, tapped M2
TOP_SCREWS = [               # ISO 14583 M2x4 pan head through the top plate into wall bosses
    (4.0, 100.0), (4.0, 150.0),
    (60.0, 4.0), (120.0, 4.0), (172.0, 4.0), (222.0, 4.0), (293.0, 4.0),
    (W - 4.0, 57.75), (W - 4.0, 113.2), (W - 4.0, 141.1), (W - 4.0, 170.0),
]
BOSS_R = 2.2                 # board standoff bosses (milled), tapped M2 / M2.5
HOLE_INSET = 3.0             # default board hole inset from each corner
# HackRF One mounting holes, measured from the KiCad board in the model (world mm)
HACKRF_HOLES = [(178.78, 142.13), (291.26, 142.15), (291.22, 212.86), (180.49, 210.71)]
MIN_ENGAGEMENT = 1.5         # x nominal diameter of thread engaged in aluminium

# ------------------------------------------------------------------ bolting the sled to the Mac
# Four of the Mac's eight P5 pentalobe bottom-case screws (four 9.1 mm and four
# 5 mm on the 2021 16", per iFixit) are replaced by STUD SCREWS: the same thread,
# the same thread length and the same under-head shape as the stock screw they
# replace, so nothing goes deeper into the Mac than before. Instead of a
# pentalobe head, each has a 4 mm stainless body that bridges the 2.6 mm gap to
# the sled's top plate and carries an M2 female thread. An M2 countersunk screw
# from under the sled, through a column milled in the base, pulls the stud down
# onto the top plate. Screw positions are measured from Apple's underside photo;
# check them (and the thread) against your own Mac before machining.
MAC_STUDS = [  # (x, y) of the four corner screws, measured from Apple's bottom-case photo
    (10.3, 10.4), (W - 10.3, 10.4), (10.3, D - 10.8), (W - 10.3, D - 10.8),
]
STUD = dict(body_d=4.0, flats=3.5, thread_depth=2.4)
# The stock bottom-case screws are SHOULDER screws: a flat countersunk head, a
# smooth shoulder and a short thread at the tip. Measured from Apple's part
# photos (support.apple.com/100570, 923-06866 front / 923-06867 rear), scaled
# to iFixit's 5 mm and 9.1 mm lengths: head ~2.7 mm, shoulder ~2.0 mm, thread
# ~1.75 mm major at ~0.37 mm pitch (so about M1.7 x 0.35, not a common metric
# size), ~2.2 mm of thread. The stud copies these exactly (it is only the head
# end that changes), so check one stock screw with a caliper and thread gauge.
STOCK_SCREW = {
    "front": dict(length=5.0, head_d=2.7, head_h=0.9, shoulder_d=2.0, shoulder_len=1.7, thread_d=1.75, thread_len=2.2,
                  pitch=0.37, apple_part="923-06866 (silver) / 923-06868 (space gray)"),
    "rear": dict(length=9.1, head_d=2.7, head_h=0.85, shoulder_d=2.0, shoulder_len=5.95, thread_d=1.75, thread_len=2.3,
                 pitch=0.37, apple_part="923-06867 (silver) / 923-06869 (space gray)"),
}
COLUMN_R = 2.5               # solid column milled in the base under each stud, M2 clearance through it
STUD_BOLT_LEN = 14           # M2x14 countersunk (ISO 14581 / ISO 10642 style), from under the base
STUD_BOLT_RECESS = 0.4       # head 0.4 mm up a counterbore in the base's underside
SLED_FEET = [(26.0, 14.0), (W - 26.0, 14.0), (26.0, D - 14.0), (W - 26.0, D - 14.0)]
MIN_ENGAGEMENT_STEEL = 1.0   # x d, thread engaged in a stainless female thread

# ------------------------------------------------------------------ one-cable power
# One USB-C PD 3.1 charger plugs into the sled. The dock board takes up to
# 240 W (48 V, 5 A EPR), runs the sled from a 48 -> 5 V buck and feeds the Mac
# through a 48 -> 28 V EPR source into Apple's USB-C to MagSafe 3 cable (the
# 16" charges at 140 W only over MagSafe on 2021-22 models; Thunderbolt ports
# cap at 100 W). The Thunderbolt jumper carries data, and with no charger it
# back-feeds the sled from the Mac (Apple's ports source 15 W), with load
# shedding. The dock re-advertises the Mac's power whenever the sled's load or
# the charger changes, so the charger is never overdrawn.
POWER = dict(
    eff_5v=0.92,             # 48 -> 5 V buck (estimate)
    eff_mac=0.97,            # 48 -> 28/20 V buck to the Mac (estimate)
    overhead_w=1.0,          # PD controllers, OR-ing, quiescent
    headroom=0.10,           # keep 10 % of the charger's rating unused
    mac_max_w=140.0,         # 16" MacBook Pro over MagSafe 3
    mac_tb_source_w=15.0,    # what a Mac Thunderbolt port supplies (5 V 3 A)
    eff_backfeed=0.95,       # Mac's 5 V -> sled 5 V rail (OR-ing and switch losses)
    # fixed PD source voltages the dock can offer the Mac, current set in 50 mA steps;
    # 28 V (EPR) only from a >= 140 W charger
    mac_voltages=[28, 20, 15, 9, 5],
    chargers_w=[240, 140, 100, 65, 0],
    # shed in this order when the budget is short (first = first to go)
    shed_order=["KrakenSDR (5 tuners, onboard hub)", "Flipper One (est., LTE active)", "HackRF (RX)",
                "Wi-Fi adapter", "Airspy HF+ Discovery", "Proxmark3 RDV4"],
)

# ------------------------------------------------------------------ left-side bridge (replaces both jumper cables)
BRIDGE = dict(
    x0=-5.6, x1=-0.3,                  # 5.3 mm thick, 0.3 mm off the sled wall and the Mac's side
    y0=26.6, y1=220.0,                 # from just behind the charger port to just past the MagSafe port
    z_low=(2.5, 12.2),                 # runs under the Mac's side intake vents, clear of their air path
    step_y=(152.0, 160.0),             # steps up after the vents end (150.5 mm)
    z_high=(17.8, 27.2),               # above the rear jaw (MAC_Z + 3.0) up to the top of the Mac's base
    windows=["Headphone", "Thunderbolt 4 L1"],
    screw_y=(70.0, 130.0), screw_z=5.0, cbore_x=-3.4,   # two M2x8 socket screws into the left wall
)

# ------------------------------------------------------------------ USB wiring: flat flex under the top plate
# Every board gets USB 2.0 over a 6-way, 0.5 mm-pitch FFC (VBUS, D+, D-, 3 x GND),
# 3.5 mm wide and 0.1 mm thick, bonded to the underside of the top plate. Runs
# along x sit on the upper FFC layer and runs along y on the lower one, so
# crossings never stack on one layer. At each end the FFC drops into a 0.9 mm-high
# 0.5 mm-pitch back-flip FPC connector on the board's back.
FFC = dict(w=3.5, t=0.1, conn=(6.0, 4.0, 0.9), drop=4.0)
FFC_ROUTES = [   # name, plan polyline (first point = upstream connector, last = downstream connector)
    ("Dock -> KrakenSDR", [(25, 22), (25, 128)]),
    ("Dock -> HackRF", [(45, 22), (45, 150), (186, 150)]),
    ("Dock -> USB hub", [(65, 22), (65, 124), (180, 124)]),
    ("Hub -> Airspy HF+", [(195, 128), (195, 88)]),
    ("Hub -> Flipper One", [(207, 128), (207, 74), (16, 74)]),
    ("Hub -> Proxmark3", [(219, 128), (219, 20)]),
    ("Hub -> LoRa", [(231, 128), (231, 158), (305, 158)]),
    ("Hub -> Wi-Fi", [(250, 128), (250, 88)]),
    ("Hub -> Flipper Zero", [(267, 128), (267, 32)]),
    ("Hub -> BLE dongle", [(280, 128), (300, 128)]),
]

# ------------------------------------------------------------------ antennas (what plugs into each SMA)
# type: whip = folding dipole on an SMA hinge, length in mm; cable = SMA plug and a coax
# run leaving the sled (to an array, a loop or a roof antenna); patch = active GNSS puck on a cable
ANTENNAS = {
    **{f"Kraken CH{i}": ("cable", "KrakenTenna set: 5 length-matched RG58 runs to the array") for i in range(5)},
    "HackRF": ("whip", 200.0, "Great Scott Gadgets ANT500 telescopic, 75 MHz-1 GHz (collapsed)"),
    "Airspy HF+": ("cable", "HF loop or long wire (e.g. YouLoop) on a coax run"),
    "Wi-Fi A": ("whip", 108.0, "2.4/5 GHz dual-band dipole"),
    "Wi-Fi B": ("whip", 108.0, "2.4/5 GHz dual-band dipole (second MIMO chain)"),
    "BLE": ("whip", 108.0, "2.4 GHz dipole"),
    "Flipper One LTE": ("whip", 190.0, "LTE wideband dipole, main"),
    "Flipper One LTE div": ("whip", 190.0, "LTE wideband dipole, diversity"),
    "Flipper One GNSS": ("patch", "active GNSS patch on 3 m RG174"),
    "LoRa": ("whip", 170.0, "868/915 MHz dipole"),
    "Flipper Zero Sub-GHz": ("whip", 190.0, "433 MHz dipole (CC1101, 300-928 MHz)"),
}
# second polycarbonate window, under the Flipper Zero's NFC / 125 kHz coils
FZ_WINDOW = (272.0, 28.0, 318.0, 50.0)
