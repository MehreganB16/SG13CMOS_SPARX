#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: BPF passband S21 on SPARX's surface model against the two emulations of volume physics
# Usage: compare_bpf.py (reads $METAL_WORK/runs, default /tmp/sparx_metal_model)
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_snp import load  # noqa: E402

W = os.environ.get("METAL_WORK", "/tmp/sparx_metal_model")
RUNS = (("SPARX surface", "G_bpf_s2_band"), ("sigma x 1.19", "G_bpf_sig119_band"),
        ("ext + TM2 x 1.073", "G_bpf_ext_tm2x1073_band"))
db = lambda x: 20 * np.log10(np.abs(x))
data = {k: load(os.path.join(W, "runs", r)) for k, r in RUNS}
f = data[RUNS[0][0]][0]
s21 = {k: db(data[k][1][:, 1, 0]) for k, _ in RUNS}
print("%6s" % "f GHz" + "".join("%20s" % k for k, _ in RUNS))
for i, ff in enumerate(f):
    print("%6.1f" % ff + "".join("%20.3f" % s21[k][i] for k, _ in RUNS))
ref = s21[RUNS[0][0]]
for k, _ in RUNS:
    print("%-18s best %.3f dB (%+.3f), mean %.3f dB (%+.3f)" % (
        k, s21[k].max(), s21[k].max() - ref.max(), s21[k].mean(), s21[k].mean() - ref.mean()))
