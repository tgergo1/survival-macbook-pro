# Board measurements

How the bare boards without published PCB files were sized. Sources are the makers' own drawings where they exist, or inside photos scaled by a part of known size.

## KrakenSDR

Source: KrakenRF's official enclosure drawing, `drawings/KrakenSDR.Enclosure.Drawing.NEW.png` in [krakenrf/krakensdr_docs](https://github.com/krakenrf/krakensdr_docs). It is also in the [KrakenSDR datasheet](https://github.com/krakenrf/krakensdr_docs/blob/main/paper_manual/KrakenSDR%20Datasheet.pdf).

| Feature | From the drawing | In the model |
|---|---|---|
| Body | 167.2 × 104.5 × 21.5 mm (113.5 deep with the SMAs) | |
| SMA centres | −57.5, −29.6, −1.7, +26.3, +54.2 mm from the centre line (CH4 … CH0) | uniform 27.9 mm pitch; MHF4 receptacles at the same x |
| Channel LEDs | 9.2 mm left of each SMA | |
| Board screws | 162.6 × 88.8 mm pattern, four per side (21.5 and 45.7 mm steps), "3 mm × 12" screws | 8 holes; M2 with DIN 433 washers into bosses |
| USB-C (power, data) | −62.9 and −32.0 mm from the centre line | handled by the USB flat-flex instead |
| Board | not stated | 168.6 × 94.8 mm: the screw pattern plus 3 mm margins |

The five Kraken pigtails stay phase-matched with the corrected 27.9 mm pitch: each is 360.7 mm.

## Airspy HF+ Discovery

Source: [RigPix](https://rigpix.com/miscrx/airspy_hfplusdiscovery.htm) inside photos (top and bottom of the board). Scale: the bottom side's Microchip ATSAM3U1C in its 14 × 14 mm LQFP-100 body, 194 px across, so about 0.072 mm/px. The photo is slightly oblique.

| Feature | Measured | In the model |
|---|---|---|
| Board | about 58 × 42 mm | 58 × 42 mm (fits Airspy's published 60 × 45 × 10 mm case) |
| Mounting holes | 4 corner holes, about 3.2 mm, about 4.5 mm in | M2 with DIN 433 washers |
| SMA | on a short edge | MHF4 receptacle near that edge |
| RF section | one large shield can | 26 × 24 mm can |

## Wi-Fi adapter

A generic MediaTek MT7612U dual-band 2 × 2 adapter, for example the ALFA AWUS036ACM (FCC ID 2AB877612). Its FCC internal photos would size it, but the FCC mirrors (fcc.report, fccid.io) and the FCC's own exhibit server all refused automated access. It stays a 70 × 25 mm placeholder with two MHF4 outputs (both MIMO chains).

## Flipper One

Flipper's Altium 365 space has the Flipper One debug probe and an SDIO-JTAG adapter, but not the mainboard (checked 2026-11-17). The bay is sized from the official B.1 enclosure STEP ([flipperone-mechanics](https://github.com/flipperdevices/flipperone-mechanics), 154.9 × 67.1 × 49.3 mm).

## Others

| Board | Source | Size |
|---|---|---|
| Proxmark3 RDV4 | Lab401 spec | 87 × 54 mm |
| nRF52840 Dongle (PCA10059) | Nordic / distributors | 46 × 15.24 mm |
| RAK4631 + RAK19003 | RAKwireless datasheets | 20 × 30 mm core on a 35 × 30 mm base |
| HackRF One | Great Scott Gadgets KiCad files | real board |
