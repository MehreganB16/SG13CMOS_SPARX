#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: two-length extraction of gamma = alpha + j beta from two Palace line runs
# The eigenvalues of ABCD2 inv(ABCD1) are exp(+-gamma dL), which cancels the port launches common to both lines.
# Usage: line_extract.py <run dir L1> <L1 um> <run dir L2> <L2 um>
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_snp import load  # noqa: E402

Z0 = 50.0


def abcd(S):
    s11, s12, s21, s22 = S[0, 0], S[0, 1], S[1, 0], S[1, 1]
    A = ((1 + s11) * (1 - s22) + s12 * s21) / (2 * s21)
    B = Z0 * ((1 + s11) * (1 + s22) - s12 * s21) / (2 * s21)
    C = ((1 - s11) * (1 - s22) - s12 * s21) / (2 * s21) / Z0
    D = ((1 - s11) * (1 + s22) + s12 * s21) / (2 * s21)
    return np.array([[A, B], [C, D]])


def gamma(r1, l1, r2, l2):
    """{f GHz: gamma per metre} of the added length l2 - l1 (um)."""
    f1, S1 = load(r1)
    f2, S2 = load(r2)
    assert np.allclose(f1, f2)
    dl = (l2 - l1) * 1e-6
    out = {}
    for k, f in enumerate(f1):
        lam = np.linalg.eigvals(abcd(S2[k]) @ np.linalg.inv(abcd(S1[k])))
        out[float(f)] = -np.log(lam[np.argmin(np.abs(lam))]) / dl   # the decaying root, exp(-gamma dl)
    return out


if __name__ == "__main__":
    r1, l1, r2, l2 = sys.argv[1], float(sys.argv[2]), sys.argv[3], float(sys.argv[4])
    print("%6s %12s %10s %10s" % ("f GHz", "alpha dB/mm", "alpha Np/m", "beta rad/m"))
    for f, g in gamma(r1, l1, r2, l2).items():
        print("%6.0f %12.4f %10.3f %10.2f" % (f, g.real * 8.685889638e-3, g.real, g.imag))
