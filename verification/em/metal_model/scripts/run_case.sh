#!/bin/bash
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: mesh one metal-model case with palace_sim.py and solve it with Palace
# Usage: run_case.sh <name> <extra settings json> [stackup]
# Env: METAL_WORK (work dir), GDS (default: the WPD of verification/em/layout), MM_FREQS_GHZ,
# MM_EXTERNAL_SIGMA, NP (Palace processes), MESH_ONLY=1 (stop after meshing). Run from a login shell.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../../.." && pwd)
W=${METAL_WORK:-/tmp/sparx_metal_model}
name=$1; extra=$2; stackup=${3:-SG13G2_nosub.xml}
R=$W/runs/$name
rm -rf "$R"; mkdir -p "$R"
export MM_RUN_DIR=$R MM_EXTRA="$extra" MM_FREQS_GHZ=${MM_FREQS_GHZ:-80,160,240}
command -v palace > /dev/null || { echo "palace not on PATH, run from a login shell"; exit 1; }
cd "$repo"
t0=$(date +%s)
python3 "$here/palace_point.py" verification/em/scripts/palace_sim.py \
    "${GDS:-$repo/verification/em/layout/sparx160_wpd.gds}" --f_center 160e9 \
    --signal_cross_section TM2 --ground_cross_section M5 --Z0 50 --stackup "$stackup" \
    > "$R/build.log" 2>&1 || { echo "$name BUILD FAILED"; exit 1; }
t1=$(date +%s)
[ "${MESH_ONLY:-0}" = 1 ] && { echo "$name build $((t1-t0)) s (mesh only)"; exit 0; }
cd "$R" && palace -np "${NP:-6}" config.json > "$R/palace.log" 2>&1 || { echo "$name PALACE FAILED"; exit 1; }
t2=$(date +%s)
echo "$name build $((t1-t0)) s, solve $((t2-t1)) s"
