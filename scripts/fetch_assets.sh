#!/usr/bin/env bash
# Rebuild model/assets/*.glb from the original open-hardware sources.
# Needs: git, KiCad 7 (kicad-cli + kicad-packages3d), Python 3.13 with
# `pip install bpy==5.3.0 cascadio`.
set -euo pipefail
cd "$(dirname "$0")/.."
WORK=build/sources
mkdir -p "$WORK" model/assets

# 1. HackRF One PCB (Great Scott Gadgets, CERN-OHL-P-2.0)
if [ ! -d "$WORK/hackrf" ]; then
  git clone --depth 1 --filter=blob:none --sparse https://github.com/greatscottgadgets/hackrf.git "$WORK/hackrf"
  git -C "$WORK/hackrf" sparse-checkout set hardware/hackrf-one
fi
# 2. Flipper Zero body (Flipper Devices, GPL-3.0)
[ -d "$WORK/flipperzero-3d-models" ] || \
  git clone --depth 1 https://github.com/flipperdevices/flipperzero-3d-models.git "$WORK/flipperzero-3d-models"

# GSG footprints carry no 3D models: add matching standard KiCad models, then export STEP
rm -rf "$WORK/hackrf-patched" && cp -r "$WORK/hackrf/hardware/hackrf-one" "$WORK/hackrf-patched"
python3 scripts/patch_hackrf_models.py "$WORK/hackrf/hardware/hackrf-one/hackrf-one.kicad_pcb" \
  "$WORK/hackrf-patched/hackrf-one.kicad_pcb"
export KICAD7_3DMODEL_DIR=${KICAD7_3DMODEL_DIR:-/usr/share/kicad/3dmodels}
kicad-cli pcb export step --subst-models -f -o "$WORK/hackrf-one.step" "$WORK/hackrf-patched/hackrf-one.kicad_pcb"

# 3. Flipper One B.1 enclosure (Flipper Devices, CERN-OHL-P-2.0)
mkdir -p "$WORK/flipperone"
curl -sfL -o "$WORK/flipperone/f1.stp" "https://raw.githubusercontent.com/flipperdevices/flipperone-mechanics/dev/CURRENT/B.1/Flipper%20One%20(B.1).stp"

# STEP -> glTF binary for Blender
python3 -I -c "
import cascadio
cascadio.step_to_glb('$WORK/hackrf-one.step', 'model/assets/hackrf-one.glb', tol_linear=0.05, tol_angular=0.5)
cascadio.step_to_glb('$WORK/flipperzero-3d-models/flipper-zero/body-3d/flipper-zero-body-3d.stp', 'model/assets/flipper-zero.glb', tol_linear=0.05, tol_angular=0.5)
cascadio.step_to_glb('$WORK/flipperone/f1.stp', 'model/assets/flipper-one.glb', tol_linear=0.05, tol_angular=0.5)
"
echo "assets written to model/assets/"
