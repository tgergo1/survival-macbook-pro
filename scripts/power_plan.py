"""One-cable power plan: how the dock board shares the charger between the
sled and the Mac, and what it sheds when there is not enough.

usage: python3 scripts/power_plan.py      (also run as check 10 by check_model.py)

For each charger size in POWER["chargers_w"] the dock:
  1. powers the whole sled from the 48 -> 5 V buck,
  2. offers the Mac the biggest USB PD contract that still fits under the
     charger's rating minus headroom (28 V EPR only from a >= 140 W charger),
  3. if even the sled alone does not fit, sheds boards in POWER["shed_order"].
With no charger, the Mac's Thunderbolt port (15 W) back-feeds the sled and the
dock sheds boards until the rest fits.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sled_config import POWER, POWER_W  # noqa: E402


def plan(charger_w, p=POWER, loads=POWER_W):
    loads = dict(loads)
    shed = []
    if charger_w == 0:
        budget = p["mac_tb_source_w"] * p["eff_backfeed"]
        for name in p["shed_order"]:
            if sum(loads.values()) <= budget:
                break
            shed.append(name)
            loads.pop(name)
        sled = sum(loads.values())
        return dict(charger=0, source="Mac battery (Thunderbolt back-feed)", mac_contract=None, mac_w=0.0,
                    sled_w=sled, input_w=sled / p["eff_backfeed"], limit_w=p["mac_tb_source_w"], shed=shed,
                    ok=sled <= budget)
    limit = charger_w * (1 - p["headroom"])
    while True:
        sled = sum(loads.values())
        avail = limit - p["overhead_w"] - sled / p["eff_5v"]
        if avail >= 0 or not [n for n in p["shed_order"] if n in loads]:
            break
        name = next(n for n in p["shed_order"] if n in loads)
        shed.append(name)
        loads.pop(name)
    contract = None
    for v in p["mac_voltages"]:             # highest voltage first; current set to what fits
        if v > 20 and charger_w < 140:
            continue                        # EPR 28 V only when the input is EPR too
        amax = 5.0 if v >= 20 else 3.0
        a = min(amax, int(avail * p["eff_mac"] / v * 20) / 20)    # PD current steps of 50 mA
        if a >= 1.0:
            contract = (v, a)
            break
    mac_w = min(contract[0] * contract[1], p["mac_max_w"]) if contract else 0.0
    input_w = p["overhead_w"] + sled / p["eff_5v"] + mac_w / p["eff_mac"]
    return dict(charger=charger_w, source=f"{charger_w} W USB-C PD charger", mac_contract=contract, mac_w=mac_w,
                sled_w=sled, input_w=input_w, limit_w=limit, shed=shed, ok=input_w <= limit + 1e-9)


def problems():
    """Design rules for the power path; returns a list of failure messages."""
    out = []
    full = plan(max(POWER["chargers_w"]))
    if full["shed"] or full["mac_w"] < POWER["mac_max_w"]:
        out.append(f"a {full['charger']} W charger should run everything and charge the Mac at "
                   f"{POWER['mac_max_w']:.0f} W, got {full['mac_w']:.0f} W, shed {full['shed']}")
    for c in POWER["chargers_w"]:
        r = plan(c)
        if not r["ok"]:
            out.append(f"{r['source']}: draws {r['input_w']:.1f} W, limit {r['limit_w']:.1f} W")
    bat = plan(0)
    if not bat["ok"]:
        out.append("on the Mac's battery the sled cannot be shed below the Thunderbolt port's 15 W")
    return out


def table():
    rows = []
    for c in POWER["chargers_w"]:
        r = plan(c)
        con = f"{r['mac_contract'][0]} V {r['mac_contract'][1]:g} A" if r["mac_contract"] else "-"
        rows.append(f"  {r['source']:38s} Mac {r['mac_w']:5.0f} W ({con:9s})  sled {r['sled_w']:4.1f} W  "
                    f"draw {r['input_w']:5.1f}/{r['limit_w']:5.1f} W  shed: {', '.join(r['shed']) or 'nothing'}")
    return "\n".join(rows)


if __name__ == "__main__":
    print(table())
    errs = problems()
    for e in errs:
        print("FAIL", e)
    sys.exit(1 if errs else 0)
