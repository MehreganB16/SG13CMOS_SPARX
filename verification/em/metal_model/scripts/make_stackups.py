#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: write the SG13G2_nosub.xml variants of the metal-model study into the work directory
"""Variants of the PDK's SG13G2_nosub.xml, each changed in one place:

    SG13G2_nosub_pec.xml       TopMetal2 and Metal5 as PEC, for the radiation share of the dissipation
    SG13G2_nosub_sig119.xml    both conductivities x 1.092^2, the measured line-loss excess of the 2 um mesh
    SG13G2_nosub_tm2x1073.xml  TopMetal2 conductivity x 1.073, the strip part of that excess alone

Usage: make_stackups.py <output dir>
"""
import os
import re
import sys

out = sys.argv[1]
palace = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"], "libs.tech", "palace")
src = next(p for p in (os.path.join(palace, "XML_stackup", "legacy", "SG13G2_nosub.xml"),
                       os.path.join(palace, "workflow", "SG13G2_nosub.xml")) if os.path.exists(p))
print("source:", src)
base = open(src).read()
SIGMA = {"Metal5": 23190000.0, "TopMetal2": 30300000.0}


def scaled(text, factors):
    for name, k in factors.items():
        old = '<Material Name="%s" Type="Conductor" Conductivity="%.1f"' % (name, SIGMA[name])
        assert text.count(old) == 1, name
        text = text.replace(old, '<Material Name="%s" Type="Conductor" Conductivity="%.1f"' % (name, SIGMA[name] * k))
    return text


def pec(text):
    for name in ("Metal5", "TopMetal2"):
        text, n = re.subn(r'(<Layer Name="%s" [^>]*Material=")%s(")' % (name, name), r"\g<1>PEC\g<2>", text)
        assert n == 1, name
    return text


os.makedirs(out, exist_ok=True)
for fname, text in (("SG13G2_nosub_pec.xml", pec(base)),
                    ("SG13G2_nosub_sig119.xml", scaled(base, {"Metal5": 1.092**2, "TopMetal2": 1.092**2})),
                    ("SG13G2_nosub_tm2x1073.xml", scaled(base, {"TopMetal2": 1.073}))):
    with open(os.path.join(out, fname), "w") as f:
        f.write(text)
    print("wrote", fname)
