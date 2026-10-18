# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: SPARX TopMetal2-over-Metal5 microstrip cross-section and its two 2D mesh levels
import math

import numpy as np

import xsec2d as X

# conductivities and z ranges of SG13G2_nosub.xml (PDK libs.tech/palace)
S_TM2, S_M5 = 30.3e6, 23.19e6
T_TM2, T_M5, GAP = 3.0, 0.49, 11.2303 - 5.58
# cells: strip hmin = skin depth at f_res / hmin_div growing by ratio up to hmax, ground nz_g uniform layers
# and laterally h0_g near the strip, growing by slope_g per um up to hmax_g
LEVELS = {
    "base": dict(hmin_div=4.0, ratio=1.3, hmax=0.4, nz_g=10, h0_g=0.15, slope_g=0.15, hmax_g=3.0),
    "fine": dict(hmin_div=6.0, ratio=1.2, hmax=0.25, nz_g=14, h0_g=0.1, slope_g=0.1, hmax_g=2.0),
}


def delta_um(f, sigma):
    return 1e6 / math.sqrt(math.pi * f * X.MU0 * sigma)


def microstrip(w, wg, f_res, lev):
    """Cells of a w-wide TopMetal2 strip over a wg-wide Metal5 ground, resolved for f_res."""
    p = LEVELS[lev]
    hmin = delta_um(f_res, S_TM2) / p["hmin_div"]
    xs = X.graded_edges(-w / 2, w / 2, hmin, p["ratio"], p["hmax"])
    zs = X.graded_edges(T_M5 + GAP, T_M5 + GAP + T_TM2, hmin, p["ratio"], p["hmax"])
    strip = X.rect_cells(xs, zs)
    edge = w / 2 + 1.0
    xg = X.sized_edges(-wg / 2, wg / 2,
                       lambda x: min(p["hmax_g"], p["h0_g"] + p["slope_g"] * max(0.0, x - edge)))
    zg = np.linspace(0.0, T_M5, p["nz_g"] + 1)
    gnd = X.rect_cells(xg, zg)
    return strip, gnd
