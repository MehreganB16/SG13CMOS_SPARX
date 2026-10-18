#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: validate xsec2d.py, then solve R' and L' of the SPARX microstrip cross-sections
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xsec2d as X  # noqa: E402
from xsec_geom import S_M5, S_TM2, T_M5, T_TM2, GAP, delta_um, microstrip  # noqa: E402

# ---------------------------------------------------------------- 1. kernel checks
print("== kernel checks")
sq = np.array([[0.0, 1.0, 0.0, 1.0]])
print("square self mean ln r: %.6f   ln(0.447049) = %.6f" % (X.mean_lnr_exact(sq, sq)[0], math.log(0.447049)))


def brute(a, b, n=40):
    g, w = np.polynomial.legendre.leggauss(n)
    xa = 0.5 * (a[0] + a[1]) + g * (a[1] - a[0]) / 2
    za = 0.5 * (a[2] + a[3]) + g * (a[3] - a[2]) / 2
    xb = 0.5 * (b[0] + b[1]) + g * (b[1] - b[0]) / 2
    zb = 0.5 * (b[2] + b[3]) + g * (b[3] - b[2]) / 2
    W = np.einsum("i,j,k,l->ijkl", w, w, w, w) / 16
    d2 = (xa[:, None, None, None] - xb[None, None, :, None]) ** 2 + (za[None, :, None, None] - zb[None, None, None, :]) ** 2
    return float(np.sum(W * 0.5 * np.log(d2)))


for a, b, what in (
    ([0, 0.2, 0, 0.05], [0.2, 0.3, 0, 0.1], "adjacent, different sizes"),
    ([0, 0.2, 0, 0.05], [0.25, 0.45, 0.3, 0.35], "near, separated"),
    ([0, 0.2, 0, 0.05], [-0.1, 0.3, 0.05, 0.1], "stacked, overlapping in x"),
):
    e = X.mean_lnr_exact(np.array([a], float), np.array([b], float))[0]
    print("%-28s exact %.6f  quadrature %.6f" % (what, e, brute(a, b)))
# a rectangle's self term cannot be checked by quadrature (ln 0), so against GMD = 0.2235 (a + b)
r = np.array([[0.0, 0.4, 0.0, 0.1]])
print("self, aspect 4               exact %.6f  0.2235 (a + b) %.6f" % (X.mean_lnr_exact(r, r)[0], math.log(0.2235 * 0.5)))

# ---------------------------------------------------------------- 2. OpenBLAU's TopMetal1 hairpin reference
print("== OpenBLAU reference: 7.5 x 2 um TopMetal1 legs, 3.9 um apart, 2.44 GHz (1.100x DC paired, 1.044x alone)")
s1 = 27.8e6
xe1 = X.graded_edges(0.0, 7.5, 0.05, 1.3, 0.3)
ze1 = X.graded_edges(0.0, 2.0, 0.05, 1.3, 0.3)
bar1 = X.rect_cells(xe1, ze1)
bar2 = bar1.copy()
bar2[:, :2] += 7.5 + 3.9
rdc = 1 / (s1 * 7.5e-6 * 2e-6)
zp = X.loop_impedance([(bar1, s1, 1.0), (bar2, s1, -1.0)], 2.44e9)
zi = X.loop_impedance([(bar1, s1, 1.0)], 2.44e9)
print("paired: R/Rdc per leg %.4f   alone: %.4f" % (zp.real / 2 / rdc, zi.real / rdc))

# ---------------------------------------------------------------- 3. SPARX microstrip
FREQS = [80e9, 160e9, 240e9]
print("== SPARX microstrip, TopMetal2 %.2f um over Metal5 %.2f um, gap %.4f um" % (T_TM2, T_M5, GAP))
print("   skin depth TM2 %s um, M5 %s um at %s GHz" % (
    ", ".join("%.3f" % delta_um(f, S_TM2) for f in FREQS),
    ", ".join("%.3f" % delta_um(f, S_M5) for f in FREQS), ", ".join("%g" % (f / 1e9) for f in FREQS)))
print("%-5s %6s %5s %6s %10s %10s %10s %10s %8s" % ("level", "w", "wg", "cells", "f GHz", "R' ohm/mm", "L' pH/um", "R'dc", "R'/R'dc"))
for lev in ("base", "fine"):
    for wg in (60.0, 100.0):
        for w in (2.5, 7.2, 12.5):
            if lev == "fine" and wg == 100.0:
                continue
            strip, gnd = microstrip(w, wg, max(FREQS), lev)
            rdc = (1 / (S_TM2 * w * T_TM2) + 1 / (S_M5 * wg * T_M5)) * 1e12 / 1e3   # ohm/mm
            t0 = time.time()
            for f in FREQS:
                z = X.loop_impedance([(strip, S_TM2, 1.0), (gnd, S_M5, -1.0)], f)
                print("%-5s %6.2f %5.0f %6d %10.0f %10.4f %10.5f %10.4f %8.3f" % (
                    lev, w, wg, len(strip) + len(gnd), f / 1e9, z.real / 1e3, z.imag / (2 * math.pi * f) * 1e6,
                    rdc, z.real / 1e3 / rdc))
            print("      (%.0f s)" % (time.time() - t0))
            sys.stdout.flush()
