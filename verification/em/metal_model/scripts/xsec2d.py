# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: 2D quasi-static filament solver for the per-unit-length R and L of a conductor cross-section
"""Per-unit-length loop impedance of a signal conductor over a ground, with the current inside both resolved.

Each conductor is cut into rectangular cells (filaments) that are fine at the surfaces and coarse inside.
The impedance matrix is R_i delta_ij + jw L_ij with L_ij = -(mu0 / 2 pi) <ln r>_ij.
<ln r> is the exact mean over both rectangles (the Hoer and Love kernel) for neighbouring cells and Gauss quadrature for distant ones.
All cells of one conductor share one voltage, and the conductors carry +I and -I.
This is the "volume" physics that a converged volume-metal EM solve would give, without its mesh cost.
Coordinates are in um.
"""
import math

import numpy as np

MU0 = 4e-7 * math.pi


def G(u, v):
    """Even, C2 kernel with d4G/du2dv2 = ln(u^2 + v^2) / 2 (the classical symmetric form)."""
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    r2 = u * u + v * v
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = np.where(u == 0, 0.0, u**3 * v * np.arctan(v / u)) / 6
        t2 = np.where(v == 0, 0.0, u * v**3 * np.arctan(u / v)) / 6
        lg = np.where(r2 == 0, 0.0, (6 * u * u * v * v - u**4 - v**4) / 48 * np.log(r2))
    return t1 + t2 - 25 * u * u * v * v / 48 + lg


def mean_lnr_exact(a, b):
    """Exact mean of ln r over rectangle a and rectangle b, rows (x0, x1, z0, z1)."""
    a = np.atleast_2d(a)
    b = np.atleast_2d(b)
    tot = 0.0
    for ia, ib, s in ((1, 0, 1), (0, 0, -1), (1, 1, -1), (0, 1, 1)):
        uu = a[:, ia] - b[:, ib]
        for ja, jb, t in ((3, 2, 1), (2, 2, -1), (3, 3, -1), (2, 3, 1)):
            vv = a[:, ja] - b[:, jb]
            tot = tot + s * t * G(uu, vv)
    area = (a[:, 1] - a[:, 0]) * (a[:, 3] - a[:, 2]) * (b[:, 1] - b[:, 0]) * (b[:, 3] - b[:, 2])
    return tot / area


def lnr_matrix(cells, near_factor=4.0, ngauss=3):
    """Mean ln r between every pair of cells (N x 4 array of x0, x1, z0, z1)."""
    xc = 0.5 * (cells[:, 0] + cells[:, 1])
    zc = 0.5 * (cells[:, 2] + cells[:, 3])
    dx = cells[:, 1] - cells[:, 0]
    dz = cells[:, 3] - cells[:, 2]
    g, w = np.polynomial.legendre.leggauss(ngauss)
    n = len(cells)
    M = np.zeros((n, n))
    for p, wp in zip(g, w):
        for q, wq in zip(g, w):
            xa = xc + p * dx / 2
            za = zc + q * dz / 2
            for r, wr in zip(g, w):
                for s, ws in zip(g, w):
                    xb = xc + r * dx / 2
                    zb = zc + s * dz / 2
                    d2 = np.subtract.outer(xa, xb) ** 2 + np.subtract.outer(za, zb) ** 2
                    np.fill_diagonal(d2, 1.0)
                    M += (wp * wq * wr * ws / 16) * 0.5 * np.log(d2)
    # quadrature is poor for touching cells, so near pairs and the diagonal get the exact value
    size = np.maximum(dx, dz)
    dist = np.hypot(np.subtract.outer(xc, xc), np.subtract.outer(zc, zc))
    near = dist < near_factor * np.maximum.outer(size, size)
    ii, jj = np.nonzero(near)
    M[ii, jj] = mean_lnr_exact(cells[ii], cells[jj])
    return M


def graded_edges(a, b, hmin, ratio, hmax):
    """Cell edges on [a, b], hmin at both ends, growing by ratio up to hmax, symmetric."""
    half = 0.5 * (b - a)
    sizes = []
    h = hmin
    while sum(sizes) < half:
        sizes.append(h)
        h = min(h * ratio, hmax)
    sizes = np.array(sizes) * half / sum(sizes)
    return a + np.concatenate([[0.0], np.cumsum(np.concatenate([sizes, sizes[::-1]]))])


def sized_edges(a, b, size_of_x):
    """Cell edges on [a, b], symmetric about the centre, size given as a function of |x - centre|."""
    c = 0.5 * (a + b)
    half = 0.5 * (b - a)
    sizes = []
    x = 0.0
    while x < half:
        h = size_of_x(x)
        sizes.append(h)
        x += h
    sizes = np.array(sizes) * half / sum(sizes)
    right = c + np.concatenate([[0.0], np.cumsum(sizes)])
    left = c - np.concatenate([[0.0], np.cumsum(sizes)])[::-1]
    return np.concatenate([left[:-1], right])


def rect_cells(xe, ze):
    X0, Z0 = np.meshgrid(xe[:-1], ze[:-1], indexing="ij")
    X1, Z1 = np.meshgrid(xe[1:], ze[1:], indexing="ij")
    return np.column_stack([X0.ravel(), X1.ravel(), Z0.ravel(), Z1.ravel()])


def loss_split(conductors, f):
    """Loop Z per metre and the share of the ohmic loss in each conductor."""
    cells = np.vstack([c[0] for c in conductors])
    sig = np.concatenate([np.full(len(c[0]), c[1]) for c in conductors])
    area = (cells[:, 1] - cells[:, 0]) * (cells[:, 3] - cells[:, 2]) * 1e-12
    R = 1.0 / (sig * area)
    L = -MU0 / (2 * math.pi) * lnr_matrix(cells)
    Z = np.diag(R) + 2j * math.pi * f * L
    P = np.zeros((len(cells), len(conductors)))
    k = 0
    for j, c in enumerate(conductors):
        P[k:k + len(c[0]), j] = 1.0
        k += len(c[0])
    ZiP = np.linalg.solve(Z, P)
    Y = P.T @ ZiP
    I = np.array([c[2] for c in conductors], complex)
    V = np.linalg.solve(Y, I)
    icell = ZiP @ V
    ploss = R * np.abs(icell) ** 2
    shares = [float(np.sum(ploss[P[:, j] > 0])) / float(np.sum(ploss)) for j in range(len(conductors))]
    return complex(V @ I.conj()), shares


def loop_impedance(conductors, f):
    """conductors: list of (cells N x 4 in um, sigma S/m, net current). Returns Z per metre."""
    cells = np.vstack([c[0] for c in conductors])
    sig = np.concatenate([np.full(len(c[0]), c[1]) for c in conductors])
    area = (cells[:, 1] - cells[:, 0]) * (cells[:, 3] - cells[:, 2]) * 1e-12
    L = -MU0 / (2 * math.pi) * lnr_matrix(cells)
    Z = np.diag(1.0 / (sig * area)) + 2j * math.pi * f * L
    P = np.zeros((len(cells), len(conductors)))
    k = 0
    for j, c in enumerate(conductors):
        P[k:k + len(c[0]), j] = 1.0
        k += len(c[0])
    Y = P.T @ np.linalg.solve(Z, P)
    I = np.array([c[2] for c in conductors], complex)
    V = np.linalg.solve(Y, I)
    # a single conductor returns its voltage, whose L carries an arbitrary constant (R is still valid)
    return complex(V @ I.conj()) if len(conductors) > 1 else complex(V[0])
