#!/bin/bash
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: the Palace runs of the metal-model study, stage by stage
# Usage: run_study.sh <setup|wpd|lines|bpf|report> ...   (run from a login shell in IIC-OSIC-TOOLS)
# Env: METAL_WORK (default /tmp/sparx_metal_model), NP (default 6), MESH_ONLY=1 to mesh without solving.
# Measured on 7 cores with NP 3 to 6: wpd about 45 min, lines about 3 h, bpf about 2 h, peak 8.4 GB (BPF).
set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../../.." && pwd)
export METAL_WORK=${METAL_WORK:-/tmp/sparx_metal_model}
export NP=${NP:-6}
W=$METAL_WORK
M5=23190000.0
BPF=$repo/verification/em/layout/sparx160_bpf.gds
BAND=150.4,155.2,160.0,164.8,169.6
case_() { bash "$here/run_case.sh" "$@"; }

for stage in "$@"; do
    case $stage in
    setup)
        python3 "$here/make_stackups.py" "$W/stackups"
        python3 "$here/gen_lines.py" "$W/lines" ;;
    wpd)
        # A: SPARX's model, P: PEC metals (radiation), B: TopMetal2 edges at 0.5 um
        case_ A_surf2 "{}"
        case_ P_pec "{}" "$W/stackups/SG13G2_nosub_pec.xml"
        case_ B_surf_tm2_0p5 '{"refined_cellsize_override": [["TopMetal2", 0.5]]}' ;;
    lines)
        # s2 at 125, 250 and 500 um serves both length pairs, so each case runs once
        for variant in s2/125/250/500 ext/250/500 r05/125/250 r05ext/125/250; do
            IFS=/ read -r v lengths <<< "$variant"
            for w in 2p5 7p2; do
                for L in ${lengths//\// }; do
                    extra="{}"
                    case $v in r05|r05ext) extra='{"refined_cellsize_override": [["TopMetal2", 0.5]]}' ;; esac
                    case $v in ext|r05ext) ext=$M5 ;; *) ext="" ;; esac
                    GDS=$W/lines/line_w${w}_l${L}.gds MM_EXTERNAL_SIGMA=$ext case_ "L_w${w}_l${L}_$v" "$extra"
                done
            done
        done ;;
    bpf)
        GDS=$BPF MM_FREQS_GHZ=160 case_ F_bpf_s2 "{}"
        GDS=$BPF MM_FREQS_GHZ=160 MM_EXTERNAL_SIGMA=$M5 case_ F_bpf_ext "{}"
        GDS=$BPF MM_FREQS_GHZ=160 case_ F_bpf_sig119 "{}" "$W/stackups/SG13G2_nosub_sig119.xml"
        GDS=$BPF MM_FREQS_GHZ=$BAND case_ G_bpf_s2_band "{}"
        GDS=$BPF MM_FREQS_GHZ=$BAND case_ G_bpf_sig119_band "{}" "$W/stackups/SG13G2_nosub_sig119.xml"
        GDS=$BPF MM_FREQS_GHZ=$BAND MM_EXTERNAL_SIGMA=$M5 case_ G_bpf_ext_tm2x1073_band "{}" \
            "$W/stackups/SG13G2_nosub_tm2x1073.xml" ;;
    report)
        python3 "$here/analyze_snp.py" "$W/runs/A_surf2" "$W/runs/B_surf_tm2_0p5" "$W/runs/P_pec"
        python3 "$here/compare_lines.py"
        python3 "$here/analyze_snp.py" "$W"/runs/F_bpf_* "$W"/runs/G_bpf_* ;;
    *)
        echo "unknown stage $stage"; exit 1 ;;
    esac
done
