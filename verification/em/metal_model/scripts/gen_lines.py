#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: straight TopMetal2 lines over a 60 um Metal5 strip with Palace port markers, for two-length extraction
# Drawn like the IHP-GDSFactory-Addon t-line structures: 0.1 um markers on 201/202 at the line ends.
# Usage: gen_lines.py <output dir>
import os
import sys

import gdspy

out = sys.argv[1]
WG = 60.0
os.makedirs(out, exist_ok=True)
for w in (2.5, 7.2):
    for L in (125, 250, 500):
        name = "line_w%s_l%d" % (str(w).replace(".", "p"), L)
        lib = gdspy.GdsLibrary(unit=1e-6, precision=1e-9)
        c = lib.new_cell(name)
        c.add(gdspy.Rectangle((0, -w / 2), (L, w / 2), layer=134, datatype=0))
        c.add(gdspy.Rectangle((0, -WG / 2), (L, WG / 2), layer=67, datatype=0))
        c.add(gdspy.Rectangle((0, -w / 2), (0.1, w / 2), layer=201, datatype=0))
        c.add(gdspy.Rectangle((L - 0.1, -w / 2), (L, w / 2), layer=202, datatype=0))
        lib.write_gds(os.path.join(out, name + ".gds"))
        print(name)
