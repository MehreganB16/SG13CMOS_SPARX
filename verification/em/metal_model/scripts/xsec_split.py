#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: share of the 2D volume loss in the TopMetal2 strip and the Metal5 ground
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xsec2d as X  # noqa: E402
from xsec_geom import S_M5, S_TM2, microstrip  # noqa: E402

print("%6s %5s %10s %8s %8s" % ("w", "f", "R' ohm/mm", "strip %", "ground %"))
for w in (2.5, 7.2, 12.5):
    strip, gnd = microstrip(w, 60.0, 240e9, "base")
    for f in (80e9, 160e9, 240e9):
        z, sh = X.loss_split([(strip, S_TM2, 1.0), (gnd, S_M5, -1.0)], f)
        print("%6.2f %5.0f %10.4f %8.1f %8.1f" % (w, f / 1e9, z.real / 1e3, 100 * sh[0], 100 * sh[1]))
