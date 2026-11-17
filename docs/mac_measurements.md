# MacBook Pro 16" measurements

Apple publishes only the envelope of the 16" MacBook Pro (355.7 × 248.1 × 16.8 mm). It publishes no dimensioned drawing: its [dimensional drawings page](https://developer.apple.com/accessories/dimensional-drawings/) lists only the MacBook Neo. Everything else in `MAC`, `MAC_BOTTOM_SCREWS`, `MAC_STUDS`, `MAC_VENTS` and `MAC_PORTS` in `scripts/sled_config.py` was measured from Apple's own straight-on product photos. Each photo was scaled to the published envelope.

## Sources

| Photo | Where | Resolution | Scale |
|---|---|---|---|
| Underside, all 8 bottom-case screws marked | [MacBook Pro (16-inch, 2021) Bottom Case service guide](https://support.apple.com/100572), `RP1795_BC_Screws_Remove2.png` | 1760 × 1174 | 0.2190 mm/px from the width, 0.2188 mm/px from the depth (they agree to 0.1 %, so the photo is orthographic) |
| Left and right sides with the ports labelled | [MacBook Pro (16-inch, 2021) Tech Specs](https://support.apple.com/111901), `111902_sp854portimage1.png` and `…image2.png` | 931 × 190 | 0.2671 mm/px from the depth |

The photos are Apple's and are not stored in this repo. The outline edges, screw heads, feet and vent slots were found by thresholding the pixel brightness and taking the centroids of the dark regions (a few lines of numpy run inside Blender). Corner radii come from a least-squares circle fit to the outline. Expect about ±0.5 mm (one or two pixels).

## Results

Positions are in sled coordinates: x from the Mac's left side, y from its front edge.

| Feature | Measured | Notes |
|---|---|---|
| Bottom-case screws, front (4 short) | x = 10.2, 119.3, 235.4 (= 355.7 − 120.3), 345.0 (= 355.7 − 10.7); y = 10.1 to 10.7 | heads about 3.3 mm across |
| Bottom-case screws, rear (4 long) | x = 9.9, 119.0, 235.9, 345.7; y = 236.7 to 237.7 (10.4 to 11.4 from the rear) | |
| Model uses | x = 10.3 and 119.3 from each side; y = 10.4 front, D − 10.8 rear | the corner four carry the stud screws |
| Feet | Ø 19.0 to 19.5 mm (dark rubber), bright rim Ø 20 to 21.5 mm; centres 26.1 to 26.4 mm from the sides, 26.3 to 26.4 mm from the front, 26.7 to 27.3 mm from the rear | |
| Foot height | 1.9 mm proud of the underside | side photo |
| Plan corner radius (underside) | 16.0 mm front, 13.9 mm rear | model uses 15 mm |
| Side intake vents | slots on the underside edge, 1.0 to 2.7 mm in from each side, 25.5 to 150.5 mm from the front | both sides |
| Lid / base seam | 12.6 mm above the underside | side photo |
| Port centres | 8.4 mm above the underside | side photo |
| Left ports (from the front) | MagSafe 3 212.5, Thunderbolt 193.8 and 178.8, headphone 166.0 | |
| Right ports (from the front) | HDMI 212.3, Thunderbolt 193.8, SDXC 169.2 | |

## Bottom-case screws

Apple's [service guide](https://support.apple.com/100572) lists four short screws at the front and four long ones at the rear. [iFixit](https://www.ifixit.com/Guide/MacBook+Pro+16-Inch+2021+Antenna+Bar+Replacement/150596) gives their lengths as 5 mm and 9.1 mm. Apple's [screw page](https://support.apple.com/100570) shows a side photo of each: 923-06866/923-06868 (front) and 923-06867/923-06869 (rear). The [iFixit screw set](https://www.ifixit.com/products/macbook-pro-16-a2485-a2780-a2991-lower-case-screw-set) photo shows the same shapes. They are **shoulder screws**: a flat countersunk P5 pentalobe head, a smooth shoulder, then a short thread at the tip.

I measured Apple's two part photos along the screw axis (principal axis of the silhouette) and scaled them to the iFixit lengths. The thread pitch comes from the period of the crest pattern (FFT of the silhouette edge).

| | Front (5 mm) | Rear (9.1 mm) |
|---|---|---|
| Head (countersunk) | Ø 2.7, 0.9 high | Ø 2.7, 0.85 high |
| Shoulder | Ø 2.0 × 1.7 | Ø 2.0 × 5.95 |
| Thread | Ø 1.75 major × 2.2 | Ø 1.75 major × 2.3 |
| Pitch | 0.37 to 0.38 | 0.37 to 0.38 |

Both screws agree. The thread is about **M1.7 × 0.35** (JIS), not a common metric size. The photos are small (200 px) and taken at a slight angle, so treat these as ±0.1 mm on diameters and ±0.03 mm on pitch. **Check one screw with a caliper and a thread gauge before ordering the studs.** No source found gives Apple's thread specification.

Each stud copies the head seat, shoulder and thread of the screw it replaces (`STOCK_SCREW` in `sled_config.py`), so it reaches exactly as deep into the Mac as the stock screw.
