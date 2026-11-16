"""Add standard KiCad 3D models to the HackRF One footprints (the GSG library
footprints ship without model references), so a STEP export shows components."""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
M = "${KICAD7_3DMODEL_DIR}/"

def passive(size, ref):
    metric = {"0402": "1005", "0603": "1608", "0805": "2012"}[size]
    if ref.startswith("R"):
        return f"Resistor_SMD.3dshapes/R_{size}_{metric}Metric.step"
    if ref.startswith(("L", "FB")):
        return f"Inductor_SMD.3dshapes/L_{size}_{metric}Metric.step"
    return f"Capacitor_SMD.3dshapes/C_{size}_{metric}Metric.step"

FIXED = {
    "SOT23-3": "Package_TO_SOT_SMD.3dshapes/SOT-23.step",
    "GSG-SOT363": "Package_TO_SOT_SMD.3dshapes/SOT-363_SC-70-6.step",
    "SKY13350-385LF": "Package_TO_SOT_SMD.3dshapes/SOT-363_SC-70-6.step",
    "GSG-SKY13317-373LF": "Package_TO_SOT_SMD.3dshapes/SOT-363_SC-70-6.step",
    "GSG-SMA-73251-2120": "Connector_Coaxial.3dshapes/SMA_Molex_73251-1153_EdgeMount_Horizontal.step",
    "GSG-USB-MICROB-FCI-10103592-EXT": "Connector_USB.3dshapes/USB_Micro-B_Molex_47346-0001.step",
    "GSG-QFN48-7": "Package_DFN_QFN.3dshapes/QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm.step",
    "GSG-QFN48-6": "Package_DFN_QFN.3dshapes/QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm.step",
    "GSG-QFN32": "Package_DFN_QFN.3dshapes/QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm.step",
    "GSG-QFN20-4": "Package_DFN_QFN.3dshapes/QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm.step",
    "GSG-LQFP144": "Package_QFP.3dshapes/LQFP-144_20x20mm_P0.5mm.step",
    "GSG-VQ100": "Package_QFP.3dshapes/TQFP-100_14x14mm_P0.5mm.step",
    "GSG-SOIC8-208": "Package_SO.3dshapes/SOIC-8_5.275x5.275mm_P1.27mm.step",
    "GSG-XTAL3.2x2.5mm": "Crystal.3dshapes/Crystal_SMD_3225-4Pin_3.2x2.5mm.step",
    "LTST-S220": "LED_SMD.3dshapes/LED_0805_2012Metric.step",
    "GSG-LP0603": "Inductor_SMD.3dshapes/L_0603_1608Metric.step",
}

out, name, ref, added = [], None, "", 0
for line in open(src, encoding="utf-8"):
    m = re.match(r'  \(footprint "([^"]+)"', line)
    if m:
        name, ref = m.group(1).split(":")[-1], ""
    r = re.search(r'\(fp_text reference "([^"]+)"', line)
    if name and r:
        ref = r.group(1)
    if name and line.rstrip("\n") == "  )":
        model = None
        p = re.match(r"GSG-(0402|0603|0805)$", name)
        if p:
            model = passive(p.group(1), ref)
        elif name in FIXED:
            model = FIXED[name]
        if model:
            out.append(f'    (model "{M}{model}" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n')
            added += 1
        name = None
    out.append(line)
open(dst, "w", encoding="utf-8").writelines(out)
print("models added:", added)
