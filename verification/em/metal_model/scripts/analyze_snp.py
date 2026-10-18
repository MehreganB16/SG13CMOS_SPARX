#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: S-parameters and dissipated power per excitation, 1 - sum_i |S_ij|^2, from Palace port-S.csv
# Usage: analyze_snp.py <run dir> ...
import csv
import os
import sys

import numpy as np


def read_s(path):
    with open(path) as f:
        rows = [r for r in csv.reader(f) if r]
    head = [h.strip() for h in rows[0]]
    data = np.array([[float(x) for x in r] for r in rows[1:]])
    n = int(round(((len(head) - 1) / 2) ** 0.5))
    S = np.zeros((len(data), n, n), complex)
    for k, h in enumerate(head):
        if h.startswith("|S["):
            i, j = int(h[3]) - 1, int(h[6]) - 1
            mag = 10 ** (data[:, k] / 20)
            ph = np.deg2rad(data[:, k + 1])
            S[:, i, j] = mag * np.exp(1j * ph)
    return data[:, 0], S


def load(run):
    out = os.path.join(run, "output")
    return read_s(os.path.join(out, os.listdir(out)[0], "port-S.csv"))


def main():
    db = lambda x: 20 * np.log10(abs(x))
    print("%-24s %5s %8s %8s %8s %8s %8s %8s %8s" % ("run", "f", "S11 dB", "S21 dB", "S31 dB", "S23 dB", "D1 %", "D2 %", "D3 %"))
    for run in sys.argv[1:]:
        f, S = load(run)
        n = S.shape[1]
        for k in range(len(f)):
            s = S[k]
            D = 1 - np.sum(np.abs(s) ** 2, axis=0)
            cols = [db(s[0, 0]), db(s[1, 0])]
            cols += [db(s[2, 0]), db(s[1, 2])] if n > 2 else [float("nan")] * 2
            ds = [100 * D[j] if j < n else float("nan") for j in range(3)]
            print("%-24s %5.1f %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f" % (
                os.path.basename(run.rstrip("/")), f[k], *cols, *ds))


if __name__ == "__main__":
    main()
