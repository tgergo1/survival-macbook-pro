"""Single source of truth for the sled geometry. All values in millimetres.

Sled origin = front-left-bottom corner of the base plate; x = right,
y = towards the rear (hinge), z = up. build_sled.py and check_model.py both
read from here, so a dimension only ever lives in one place.
"""

# ------------------------------------------------------------------ envelope
W, D = 355.7, 248.1          # MacBook Pro 16" footprint (Apple's published size)
CORNER_R = 9.0               # plan-view corner radius of the plates
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
TOP_CLEAR = 2.4              # PCB back -> underside of top plate
TOP_Z0 = PCB_TOP + TOP_CLEAR # 10.8
TOP_Z1 = TOP_Z0 + 1.0        # 1 mm top plate
assert Z_HIGH + COAX_R < TOP_Z0, "coax crossings must clear the top plate"
assert PCB_TOP + MHF4_MATED_H < TOP_Z0

RAIL_T = 2.0                 # rubber rails the Mac sits on
MAC_FOOT_T = 0.6
MAC_Z = TOP_Z1 + RAIL_T + MAC_FOOT_T

FOOT_H = 4.0                 # sled feet: 4 mm intake gap under the blower grille

# ------------------------------------------------------------------ RF edge
SMA_X = W                    # bulkheads on the right-hand wall
Z_SMA = 7.0                  # bulkhead centre height (hole Ø6.5 fits the 8.3 mm wall)
SMA_HOLE_R = 3.25
CABLE_DESCENT_X = 346.0      # cables drop from Z_LOW to Z_SMA after this x
BOARD_MAX_X = 344.0          # boards stay left of the cable descent zone
CORNER_R_CABLE = 5.0         # bend radius at each cable corner (>= 5x coax OD)

# ------------------------------------------------------------------ thermal
HP_W, HP_T = 6.0, 1.7        # flattened heat pipe section
PAD_T = 0.5                  # thermal pad between chip and pedestal
PAD_GAP = 0.05               # compression allowance

BLOWER = dict(x0=296.0, y0=186.0, size=52.0, h=6.5, r=5.0)   # 52 x 52 x 6.5 mm laptop blower
BLOWER_C = (BLOWER["x0"] + BLOWER["size"] / 2, BLOWER["y0"] + BLOWER["size"] / 2)
PLENUM = dict(x0=12.0, x1=BLOWER["x0"], y0=222.0, y1=233.0)    # blower -> fins duct
FINS = dict(x0=12.0, x1=294.0, y0=233.0, y1=D - WALL_T - 0.1, pitch=1.35, t=0.3)
SIDE_INTAKE = dict(y0=192.0, y1=232.0)                         # louvre in the right wall
EXHAUST = dict(x0=12.0, x1=294.0)                               # opening in the rear wall

# Heat pipes run in grooves in the base plate (top flush with BASE_T), from
# the hot spots to the fin stack. Polylines in plan view.
HEAT_PIPES = [
    ("Heat pipe 1 (KrakenSDR bar)", [(150, 206), (28, 206), (28, 236.5), (170, 236.5)]),
    ("Heat pipe 2 (HackRF)", [(205, 169), (242, 169), (242, 243.5), (292, 243.5)]),
    ("Heat pipe 3 (Flipper One)", [(76, 78), (12, 78), (12, 243.5), (60, 243.5)]),
]

# ------------------------------------------------------------------ boards
# KrakenSDR: bare board modelled from the official enclosure drawing
# (167.2 x 104.5 mm body, 5 channels on 27.8 mm pitch).
KRAKEN_PITCH = 27.8
KX = [32.9 + i * KRAKEN_PITCH for i in range(5)]
KRAKEN_UFL_Y = 216.0

# chips/cans: (cx, cy, w, d, h) hanging below the PCB; ufl: connector names -> (x, y)
BOARDS = [
    dict(name="KrakenSDR (bare, from official drawing)", rect=(6, 120, 171, 220), mat="pcb_black",
         chips=[(88.5, 150, 9, 9, 1.0), (40, 140, 6, 6, 1.0), (140, 140, 5, 5, 1.0)],
         cans=[(x, 206, 21, 19, 3.4) for x in KX],
         ufl={f"Kraken CH{i}": (x, KRAKEN_UFL_Y) for i, x in enumerate(KX)}),
    dict(name="USB 2.0 hub (low-rate devices)", rect=(175, 114, 295, 134),
         chips=[(205, 124, 7, 7, 0.9), (255, 124, 5, 5, 0.9)]),
    dict(name="Flipper One (bay placeholder, board TBD)", rect=(6, 45, 146, 110), mat="pcb_purple",
         chips=[(71, 77, 15, 15, 1.2), (100, 77, 12, 10, 1.0), (100, 95, 12, 10, 1.0), (125, 60, 30, 22, 1.4)],
         ufl={"Flipper One LTE": (136, 100), "Flipper One GNSS": (126, 100)}),
    dict(name="Airspy HF+ Discovery (bare)", rect=(175, 64, 230, 104),
         chips=[(202, 84, 7, 7, 0.9)], cans=[(190, 84, 14, 16, 2.0)], ufl={"Airspy HF+": (226, 96)}),
    dict(name="Wi-Fi adapter (bare)", rect=(240, 80, 310, 105),
         chips=[(270, 92, 8, 8, 0.9)], ufl={"Wi-Fi": (305, 92)}),
    dict(name="Proxmark3 RDV4 (bare)", rect=(175, 6, 261, 60), mat="pcb_black",
         chips=[(205, 40, 14, 14, 1.4), (240, 40, 8, 8, 1.0)]),
    dict(name="Flipper Zero (bare-board bay)", rect=(264, 10, BOARD_MAX_X, 46),
         chips=[(296, 28, 10, 10, 1.0), (326, 28, 6, 6, 1.0)]),
    dict(name="BLE sniffer nRF52840", rect=(300, 120, BOARD_MAX_X, 138),
         chips=[(318, 129, 7, 7, 0.9)]),
    dict(name="LoRa node nRF52840 + SX1262", rect=(312, 150, 342, 173),
         chips=[(327, 161, 8, 8, 0.9)], ufl={"LoRa": (338, 168)}),
    # Dock board: Thunderbolt device controller with PCIe out to two extra xHCI
    # controllers, so the HackRF and the KrakenSDR each get their own USB 2.0
    # root (480 Mbit/s each), plus USB-C PD input and the 5 V buck.
    dict(name="Dock board (TB controller, 2x xHCI, PD, 5 V buck)", rect=(8, 8, 150, 42),
         chips=[(62, 25, 12, 12, 1.2), (98, 25, 7, 7, 0.9), (122, 25, 7, 7, 0.9),
                (28, 30, 5, 5, 0.9), (40, 14, 7, 7, 3.0), (138, 25, 6, 6, 1.0)]),
]

HACKRF = dict(center=(235, 177.5), ufl={"HackRF": (235, 213)})
HACKRF_KEEP_X = (0.0595, 0.1805)   # metres in the imported glTF: drops edge SMAs + micro-USB

# USB-C receptacles on the left wall (mid-mount, centred in the dock PCB)
USBC_PORTS = [("USB-C PD in (up to 140 W)", 16.5), ("Thunderbolt / USB4 to Mac", 33.5)]
USBC = dict(x0=1.5, x1=11.5, w=8.94, h=3.26)

# Pedestals: (name, x0, y0, x1, y1). Heights come from the measured chip depth.
KRAKEN_BAR = ("KrakenSDR isothermal bar", KX[0] - 11.5, 196, KX[-1] + 11.5, 216)
PEDESTALS = [
    KRAKEN_BAR,                                   # one bar under all 5 tuner cans
    ("Flipper One SoC", 63, 69, 79, 85),
    ("HackRF CPLD/MCU", 196, 160, 214, 178),
    ("HackRF RF front end", 232, 168, 252, 188),
    ("Dock TB controller", 55, 18, 69, 32),       # spreads into the base plate
]
PEDESTALS_PLATE_ONLY = {"Dock TB controller"}     # allowed without a heat pipe

# ------------------------------------------------------------------ RF routing
# Each pigtail runs along y first (upper layer, Z_HIGH), turns once, then runs
# along x (lower layer, Z_LOW) to its bulkhead. Distinct x for every y-run and
# distinct y for every x-run means crossings are always one layer over the other.
# KrakenSDR lanes step by the channel pitch, so all 5 coherent channels have
# exactly the same Manhattan length (phase matched by construction).
KRAKEN_LANE0 = 162.0
LANES = {f"Kraken CH{i}": KRAKEN_LANE0 - i * KRAKEN_PITCH for i in range(5)}
LANES.update({
    "LoRa": 178.0,
    "HackRF": 148.0,
    "Airspy HF+": 120.0,
    "Wi-Fi": 92.0,
    "Flipper One LTE": 64.7,
    "Flipper One GNSS": 36.8,
})
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
