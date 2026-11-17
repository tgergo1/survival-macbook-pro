# Survival MacBook Pro: caseless OSINT sled

A ~12 mm machined-aluminium sled that sits under a 16" MacBook Pro and holds a full RF/SIGINT kit as **bare boards, chips facing down into shielded pockets and onto heat-piped pedestals**: KrakenSDR, HackRF, Airspy HF+, Flipper One, Flipper Zero, Proxmark3, Wi-Fi, BLE and LoRa. All 11 antenna ports come out on one edge as SMA bulkheads, and one Thunderbolt cable plus one USB-C PD charger connect it to the Mac. The Mac slides into a cradle on top of the sled and locks in place with two spring pawls.

![Assembled: MacBook Pro 16 on the sled](renders/render_hero.png)

> **Status: concept model.** Nothing here has been built or tested. Board geometry is real where open-hardware files exist; everything else is modelled from published dimensions or is a sized placeholder (see [Geometry sources](#geometry-sources)). Every screw, connector and mount part is modelled from its standard or datasheet dimensions. `scripts/check_model.py` verifies the model is physically consistent: no parts collide, every screw lands in its tapped hole with enough thread engaged, the Mac is held and slides in and out freely, the ports, SMA nuts and lid have room, and the KrakenSDR cables are phase matched. It does not verify that the electronics work. The MacBook's foot, port and edge-radius positions are estimates, because Apple publishes no dimensioned drawing of the 16" MacBook Pro (see [MacBook mount](#macbook-mount)).

---

## Renders

### Seen from the left: the Thunderbolt loop from the sled's dock port to the Mac
![Left side with the Thunderbolt cable](renders/render_hero_left.png)

### Sliding the Mac in (lid closed): rear jaws and corner stops, silicone rails, top-plate screws
![Mac partly inserted](renders/render_insert.png)

### Front latch, rear corner stop, SMA bulkheads and a HackRF mounting screw
| | |
|---|---|
| ![Front latch](renders/render_latch.png) | ![Rear corner stop](renders/render_rear_stop.png) |
| ![SMA bulkheads](renders/render_sma.png) | ![HackRF screw, washer and boss](renders/render_fasteners.png) |

### Exploded: base plate with pocket walls and thermal layer, boards with RF pigtails and their screws, top plate and its screws, jaws and latches
![Exploded view](renders/render_exploded.png)

### Top view with the top plate removed
Rear edge (hinge side) is at the top, the SMA bulkheads are on the right and the USB-C ports on the left. The red pigtails are the five phase-matched KrakenSDR cables.
![Top-down layout](renders/render_layout.png)

| Position | Board |
|---|---|
| Rear-left, black | KrakenSDR, 5-channel coherent receiver |
| Rear-centre, green | HackRF (real KiCad PCB) |
| Rear-right | Laptop-style blower (bottom and side intakes) |
| Along the rear edge | Plenum, fin stack and exhaust deflector |
| Middle-left, purple | Flipper One bay (Linux host, M.2 LTE + GNSS modem) |
| Middle | USB 2.0 hub for low-rate devices, Airspy HF+ Discovery, Wi-Fi adapter |
| Right column | BLE sniffer (nRF52840), LoRa node |
| Front-left | Dock board: Thunderbolt controller, 2 extra xHCI controllers, USB-C PD input, 5 V buck |
| Front | Proxmark3 RDV4 (black, over the RF window), Flipper Zero bare-board bay |

### Thermal layer: pocket walls, heat pipes, pedestals, blower, plenum and fin stack
![Thermal layer](renders/render_thermal.png)

### Real downloaded assets
On the left is the HackRF PCB built from Great Scott Gadgets' KiCad design, with 311 components given standard KiCad 3D models. On the right is the official Flipper Zero body model.
![Reference assets](renders/render_reference.png)

---

## Stack-up

| Layer | Thickness | Notes |
|---|---|---|
| MacBook Pro 16" | 16.8 mm | Apple's published 355.7 × 248.1 × 16.8 mm |
| Mac feet + silicone rails | 0.6 + 2.0 mm | Leaves an air gap for the Mac's own intake; the jaw flanges (1.2 mm) sit in this gap at the edges |
| Top plate | 1.0 mm | Anodised aluminium, grounded, sealed (no openings) |
| Cable zone | 2.4 mm | MHF4 connectors (1.2 mm mated) and two crossing layers of 1.13 mm micro-coax |
| Boards | 1.6 mm | Chips-down; PCB back at 8.4 mm |
| Pocket zone | 4.3 mm | Shield cans and ICs inside milled pocket walls, on pedestals |
| Base plate | 2.5 mm | 6061 with grooves for flush heat pipes; window for the Proxmark |
| Sled feet | 4.0 mm | Intake gap under the blower grille |
| **Sled** | **11.8 mm** (+4 mm feet) | |
| **Total with the Mac** | **≈ 35 mm** | |

Every dimension lives in [`scripts/sled_config.py`](scripts/sled_config.py).

## How it fits together

- **Chips-down boards in shielded pockets.** Every board mounts upside down on a milled aluminium wall that runs under its edge. The board's ground plane closes the pocket, so each de-cased radio gets its own shielded compartment. Where the real HackRF has parts at its edge, the wall is notched automatically around them.
- **Pedestals on heat pipes.** Shield cans and hot ICs press onto aluminium pedestals through 0.5 mm thermal pads. `build_sled.py` sizes each pedestal from the actual chip depth it measures in the model. The KrakenSDR's five tuner cans share **one isothermal bar**, so all five tuners sit at the same temperature (temperature differences between tuners cause phase drift).
- **Heat path.** Three flattened 6 × 1.7 mm heat pipes sit flush in base-plate grooves: KrakenSDR bar, both HackRF hot spots, and the Flipper One SoC. They carry heat to a fin stack along the rear edge. A 52 × 52 × 6.5 mm blower draws air through a grille in the base plate (4 mm feet) and through louvres in the right-hand wall (so it still breathes on a lap or a soft surface). It blows through an open plenum into the fins. An angled deflector turns the exhaust down and away from the underside of the Mac.
- **RF routing.** All RF runs on MHF4 pigtails (1.2 mm mated height, so they fit under the top plate) to 11 rear-mount SMA bulkhead jacks on the right edge. Each pigtail runs along y on an upper layer, makes one 5 mm-radius bend, then runs along x on a lower layer, and finishes with an S-bend down into the jack's crimp ferrule. No two cables share a lane, so every crossing is one cable over another and never through it. Board mounting screws are placed so that no cable runs over a screw head.
- **Phase-matched KrakenSDR.** The KrakenSDR's bulkheads are spaced at the same 27.8 mm pitch as its channels. Because of that, all five Kraken pigtails have exactly the same routed length (364.1 mm in the current model, MHF4 plug to SMA crimp ferrule) with no slack loops. Order them as a phase-matched set.
- **USB with enough bandwidth.** One USB 2.0 bus carries 480 Mbit/s, but the HackRF alone can use about 320 Mbit/s and the KrakenSDR about 200 Mbit/s. The dock board therefore uses a Thunderbolt device controller with a PCIe downstream (Intel JHL7440 class) feeding two extra xHCI controllers, so each of these gets a USB root of its own:

  | USB root | Devices |
  |---|---|
  | xHCI A (PCIe) | HackRF |
  | xHCI B (PCIe) | KrakenSDR (through its own onboard hub) |
  | TB controller's built-in xHCI → USB 2.0 hub | Airspy HF+, Wi-Fi, Flipper One, Flipper Zero, Proxmark3, BLE sniffer, LoRa node |

  Check that the chosen xHCI controllers have macOS driver support before committing to a part.
- **Power.** A USB-C PD input on the left edge takes up to 140 W. About 28 W runs the sled through a 5 V / 8 A buck, and the dock passes the rest to the Mac over the Thunderbolt cable (up to about 96 W, like a Thunderbolt dock). So on a desk it is one charger and one cable to the Mac.
- **Everything runs headless.** The Flipper Zero, Flipper One and Proxmark run from the Mac: no screens, no batteries. The Proxmark reads cards through a polycarbonate window in the base plate.

## MacBook mount

The Mac slides in from the front and is held on all sides without covering a port, a vent or the lid's path:

| Part | What it does |
|---|---|
| 4 side jaws (6061, black anodised) | A web outside the Mac's side and a 1.2 mm flange on the top plate, under the Mac's edge. Each is screwed down with two ISO 14581 M2×6 countersunk screws through the flange and the top plate into a boss in the sled wall. A 0.8 mm TPU 85A liner on the inside touches the Mac (about 0.15 mm squeeze takes up Apple's width tolerance). The front jaws rise 7 mm up the Mac's side. Near the ports, the rear jaws rise only 3 mm, below the lowest plug overmould. |
| 2 rear corner stops | Returns on the rear jaws that wrap 22 mm around each rear corner, 3 mm high. They stop the Mac sliding back and stay below the path of the lid's lower edge. |
| 2 front latches | A POM pawl in an anodised block in front of each front corner, pushed up 2.5 mm above the Mac's bottom face by a compression spring (Ø2.6 × 0.3 mm wire) and kept in by a Ø1 × 8 mm ISO 2338 pin running in a slot in the pawl. The entry ramp faces forward: the Mac's underside pushes the pawl down as it slides in, and the pawl snaps up in front of the Mac's front face. To take the Mac out, press both pawls down and slide it forward. Each block is held by two ISO 4762 M2×8 screws into the sled's front wall. |
| 2 silicone rails | The Mac's feet sit on these (2 mm), leaving an air gap for its own intake. |

With the mount, the sled's outline grows to 362.3 × 257.9 mm (jaws 3.3 mm per side, latches 6.5 mm at the front, corner stops 3.3 mm at the back).

**What holds the Mac down.** Nothing hooks over it: the MacBook Pro has no undercut that a clip could catch without covering a port, a vent or the lid's path. Lift is held by the jaws' clamping friction. Sideways, forward and backward movement is held positively by the jaws, the corner stops and the pawls. If you need a positive hold-down, the next step is keyhole studs in place of some of the bottom-case screws, but that needs the real screw positions and thread depth from a measured Mac.

**Real MacBook Pro dimensions.** Apple publishes only the envelope (355.7 × 248.1 × 16.8 mm). It has no dimensioned drawing for the 16" model: its [dimensional drawings page](https://developer.apple.com/accessories/dimensional-drawings/) currently lists only the MacBook Neo. The plan-view corner radius, the edge fillets, the foot positions and the port positions in `MAC` and `MAC_PORTS` in `sled_config.py` are therefore **estimates**. Measure your Mac, update those values, rebuild, and run the check before cutting metal. The check then re-verifies the fit against the new numbers.

## Fasteners and connectors

| Part | Standard | Qty | Where |
|---|---|---|---|
| M2×5 pan head, Torx T6 | ISO 14583, A2 | 42 | Every board into its standoff bosses (3.1 to 3.4 mm of thread engaged) |
| M2×4 pan head, Torx T6 | ISO 14583, A2 | 11 | Top plate into the wall bosses (3.0 mm engaged) |
| M2×6 countersunk, Torx T6 | ISO 14581, A2 | 8 | Jaws through the top plate into the wall bosses (3.8 mm engaged) |
| M2×8 socket head | ISO 4762, A2 | 4 | Latch blocks into the front wall and a boss behind it (3.7 mm engaged) |
| M2 washer | DIN 433 | 4 | HackRF (its mounting holes are 2.75 mm) |
| Ø1 × 8 parallel pin | ISO 2338 m6 | 2 | Latch pawl retainers |
| SMA jack, rear-mount bulkhead, for 1.13 mm coax | 1/4-36 UNS, 5/16" nut, D-flat | 11 | Right wall, 6.5 mm D-holes |
| MHF4 receptacle and plug | I-PEX MHF4 (0.6 mm / 1.2 mm mated) | 11 | Board RF ports |
| USB Type-C receptacle, mid-mount | USB Type-C spec | 2 | Dock board: PD in, Thunderbolt to Mac |

All screws thread into tapped holes in 6061: milled bosses inside the perimeter wall and standoff bosses that are part of each pocket wall. Every screw is modelled with its real head, its drive recess and a shank at the thread's minor diameter. Every hole is modelled at its tap-drill or ISO 273 clearance size. The check measures thread engagement on the geometry and needs at least 1.5 × d in aluminium.

### Power budget (estimates)

| Load | W |
|---|---|
| KrakenSDR (5 tuners, onboard hub) | 11.0 |
| Flipper One (estimate, LTE active) | 5.0 |
| Dock board (TB controller, 2× xHCI, hub) | 4.0 |
| HackRF (RX) | 2.5 |
| Wi-Fi adapter | 2.0 |
| Airspy HF+ Discovery | 1.0 |
| Blower (PWM) | 1.0 |
| Proxmark3 RDV4 | 0.8 |
| Flipper Zero | 0.3 |
| LoRa node (RX) | 0.2 |
| BLE sniffer | 0.1 |
| **Total** | **≈ 28** |

These are planning numbers, not measurements. Measure each board before sizing the buck.

## Geometry sources

| Part | Source of geometry | Fidelity |
|---|---|---|
| HackRF | [greatscottgadgets/hackrf](https://github.com/greatscottgadgets/hackrf) `hardware/hackrf-one` KiCad PCB → STEP → glTF | **Real board.** HackRF Pro board files aren't in the repo, so the HackRF One PCB stands in (same 120 × 75 mm outline). The GSG footprints carry no 3D models, so `patch_hackrf_models.py` maps them to standard KiCad models. Edge SMA jacks and micro-USB are removed. |
| Flipper Zero | [flipperdevices/flipperzero-3d-models](https://github.com/flipperdevices/flipperzero-3d-models) body STEP | **Real body**, shown for reference only. Flipper doesn't publish the internals; the sled has a sized bare-board bay. |
| KrakenSDR | Official enclosure drawing (167.2 × 104.5 mm body, 5 channels on ~27.8 mm pitch) | Bare board and shield cans approximated from those dimensions. |
| Flipper One | Announced specs (155 × 67 × 40 mm cased, still preliminary) | Placeholder bay, 140 × 65 mm. |
| Airspy HF+ Discovery | Published case size 60 × 45 × 10 mm | Approximated bare board. |
| Dock board, Proxmark3 RDV4, Wi-Fi, nRF52840 BLE, LoRa, USB hub | Typical module sizes | Placeholders. |
| MacBook Pro 16" | Apple's published envelope; edge radii, feet and ports estimated | Body with filleted edges and port openings, keyboard and lid. |
| Screws, washers, pins | ISO 14583, ISO 14581, ISO 4762, DIN 433, ISO 2338 | Modelled from the standards' dimension tables. |
| SMA, MHF4, USB-C | SMA bulkhead datasheet dimensions, I-PEX MHF4, USB Type-C specification | Modelled from published dimensions. |

## Repository layout

```
model/osint_sled.blend         Blender scene (collections: chassis, thermal, boards, pigtails, top plate, fasteners,
                               mount, Mac, external cables, keep-out envelopes, reference)
model/assets/hackrf-one.glb    HackRF PCB with components (from the KiCad design)
model/assets/flipper-zero.glb  Flipper Zero body (official model)
renders/                       Cycles renders used above
scripts/sled_config.py         Every dimension, board, lane and pedestal in one place
scripts/build_sled.py          Builds the whole scene from sled_config.py
scripts/parts.py               Standard parts: ISO screws, washers, pins, SMA, MHF4, USB-C, springs
scripts/geom.py                Mesh helpers (boxes, lathe, prisms, booleans, filleted slabs)
scripts/check_model.py         Design-rule check: collisions, thread engagement, Mac fit and insertion,
                               keep-outs, heat pipes, Kraken phase matching
scripts/render_views.py        Renders a view (Cycles, studio HDRI): hero | hero_left | insert | exploded |
                               layout | thermal | latch | rear_stop | sma | fasteners | reference
scripts/fetch_assets.sh        Re-downloads the sources and regenerates model/assets/
scripts/patch_hackrf_models.py Adds standard KiCad 3D models to the HackRF footprints
```

## Rebuild

Large files (`.blend`, `.glb`, renders) are stored with Git LFS: run `git lfs install` once before cloning.

With Blender 5.2 or later (macOS path shown):

```bash
B=/Applications/Blender.app/Contents/MacOS/Blender
# optional: regenerate the glTF assets (needs KiCad 7 + kicad-packages3d)
./scripts/fetch_assets.sh
$B -b --factory-startup --python scripts/build_sled.py                       # writes model/osint_sled.blend
$B -b --factory-startup --python scripts/check_model.py                      # must print "all checks passed"
$B -b --factory-startup --python scripts/render_views.py -- hero final       # or any view above; draft for previews
```

The first render downloads the studio HDRI (Poly Haven, CC0) to `build/hdri/`. The scripts also run with the `bpy` module from PyPI (`python scripts/build_sled.py`).

To edit it by hand, open `model/osint_sled.blend`. To change the design, edit `sled_config.py`, rebuild and re-run the check.

## Engineering caveats

- **The KrakenSDR's case does real work.** Its aluminium case is both a heatsink and a shield, and tuner temperature swings cause phase drift that ruins direction finding. The sled replaces it with a shielded pocket, a shared isothermal bar on its own heat pipe, and a PWM-controlled blower to hold the temperature steady. The pigtails are equal length by construction; the KrakenSDR's own calibration still has to run after warm-up.
- **De-casing voids warranties**, and every radio's shielding now depends on its pocket wall and a good ground contact along the board edge (use conductive gasket or fingerstock on the wall tops).
- **Thunderbolt and xHCI parts are not yet chosen.** The topology above is the requirement; part selection, macOS driver support and PD pass-through behaviour still need checking against datasheets.
- **Transmit.** Keep the HackRF's hardware TX-disable on while the receivers are listening. Transmitting without a licence, and acting on intercepted communications, is illegal in most jurisdictions.
- **Flipper One** isn't in mass production yet, and its published dimensions may change.
- **MacBook dimensions beyond the envelope are estimates.** See [MacBook mount](#macbook-mount). The jaw heights near the ports assume plug overmoulds start at least 3.3 mm above the Mac's bottom face.
- **Board-to-dock USB wiring is not modelled yet.** The boards need USB links to the dock board (an FFC under the top plate is the likely route). The cable zone above the boards is already full of coax crossings, so adding the FFC will probably take about 0.2 mm more height.

## Credits and licences

The original design files and scripts in this repository are released under the [MIT licence](LICENSE). The repo also bundles third-party geometry, which stays under its own licence:

- **HackRF One hardware** © Great Scott Gadgets, [CERN-OHL-P-2.0](https://github.com/greatscottgadgets/hackrf/blob/master/hardware/hackrf-one/LICENSE). It is in `model/assets/hackrf-one.glb` and the `.blend`.
- **Flipper Zero 3D models** © Flipper Devices, [GPL-3.0](https://github.com/flipperdevices/flipperzero-3d-models/blob/master/LICENSE). It is in `model/assets/flipper-zero.glb` and the `.blend`.
- **KiCad 3D component models**, [CC-BY-SA 4.0 with the KiCad libraries exception](https://www.kicad.org/libraries/license/). These are embedded in the HackRF asset.
- KrakenSDR dimensions come from KrakenRF's published drawing. The drawing itself is not included.
- The studio HDRI used for the renders (`studio_small_09`) is from [Poly Haven](https://polyhaven.com), CC0. It is downloaded at render time and not stored in the repo.
