#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Palace two-length line loss against the 2D volume reference, per width, variant and frequency
# alpha_2D = R'_2D / (2 Zc) with Zc = w L'_2D / beta_Palace, so alpha_P / alpha_2D = R'_P / R'_2D.
# Usage: compare_lines.py (reads $METAL_WORK/runs, default /tmp/sparx_metal_model)
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from line_extract import gamma  # noqa: E402

W = os.environ.get("METAL_WORK", "/tmp/sparx_metal_model")
# 2D volume reference from xsec_run.py, base mesh, 60 um ground: f GHz -> (R' ohm/mm, L' pH/um)
REF = {
    "2p5": {80: (15.4039, 0.46521), 160: (21.2322, 0.45786), 240: (25.9329, 0.45429)},
    "7p2": {80: (9.5424, 0.33924), 160: (13.2591, 0.33475), 240: (16.3185, 0.33248)},
}
# (variant, short length, long length) in the order of results/lines_compare.txt
PAIRS = (("s2", 250, 500), ("ext", 250, 500), ("s2", 125, 250), ("r05", 125, 250), ("r05ext", 125, 250))


def finished(run):
    log = os.path.join(run, "palace.log")
    return os.path.exists(log) and "Disk IO" in open(log).read()


print("%-4s %-11s %4s %10s %10s %8s %8s %8s" % ("w", "variant", "f", "aP dB/mm", "a2D dB/mm", "aP/a2D", "beta/k0", "Zc ohm"))
for w in REF:
    for variant, l1, l2 in PAIRS:
        r1 = os.path.join(W, "runs", "L_w%s_l%d_%s" % (w, l1, variant))
        r2 = os.path.join(W, "runs", "L_w%s_l%d_%s" % (w, l2, variant))
        if not (finished(r1) and finished(r2)):
            continue
        for f, g in sorted(gamma(r1, l1, r2, l2).items()):
            rp, lp = REF[w][int(round(f))]
            om = 2 * math.pi * f * 1e9
            zc = om * lp * 1e-6 / g.imag
            a2d = rp * 1e3 / (2 * zc)
            print("%-4s %-11s %4.0f %10.4f %10.4f %8.3f %8.4f %8.2f" % (
                w, "%s/%d" % (variant, l1), f, g.real * 8.685889638e-3, a2d * 8.685889638e-3, g.real / a2d,
                g.imag / (om / 299792458.0), zc))
