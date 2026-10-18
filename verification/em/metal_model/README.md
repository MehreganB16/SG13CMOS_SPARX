# Surface Versus Volume Metal in the Palace EM Flow

How a conductor is modelled decides the loss an EM solve reports.
`gds2palace` offers two models, a surface model (its default) and a volume model (`filled_metals`).
This document explains the difference, records the check of 2026-10-17/18 that compared SPARX's surface-model results with volume physics, and says why SPARX stays on the surface model for now.

## Summary

- All SPARX EM solves (BLC, WPD, BPF, six-port core) use the surface model.
- A volume solve that resolves the skin depth does not fit the 14 GB host the check ran on: the skin depth in TopMetal2 is 0.23 µm at 160 GHz, which needs about 6 to 9 million unknowns for the WPD alone.
- Instead, Palace's surface results were compared with a 2D volume reference of the same microstrip cross-section, on straight lines, on the WPD and on the BPF.
- On SPARX's mesh, the 2.5 µm WPD arms match volume physics within 1 %. The 7.2 µm 50 Ohm lines (BPF, feeds) read 6 to 14 % too lossy over 80 to 240 GHz.
- The BPF passband would improve by about 0.5 dB (0.52 dB at the best point, 0.56 dB on average, ±0.1 dB) with volume physics. That is at the 0.5 dB threshold set for switching, and in the conservative direction.
- Decision: stay on the surface model. The committed losses are slightly pessimistic, not optimistic. [When to revisit](#when-to-revisit-and-switch-to-volume) lists what would change that, first among them the skin-layer volume model of gds2palace 0.9.0.

## Skin depth decides which model is right

At high frequency the current in a conductor crowds into a layer of one skin depth below the surface:

$$\delta = \frac{1}{\sqrt{\pi f \mu_0 \sigma}}$$

With the conductivities of `SG13G2_nosub.xml`, that is 3.3 µm / √(f in GHz) for Metal2 to Metal5 (2.319e7 S/m), 3.0 µm for TopMetal1 (2.78e7 S/m) and 2.9 µm for TopMetal2 (3.03e7 S/m).
What matters is the metal thickness t in skin depths, and the width w against t:

| SG13G2 metal, t | 2.4 GHz | 20 GHz | 80 GHz | 160 GHz | 240 GHz |
|---|---:|---:|---:|---:|---:|
| Metal2 to Metal5, 0.49 µm | 0.23 | 0.66 | 1.33 | 1.88 | 2.30 |
| TopMetal1, 2.0 µm | 1.0 | 3.0 | 5.9 | 8.4 | 10.3 |
| TopMetal2, 3.0 µm | 1.6 | 4.6 | 9.3 | 13.1 | 16.1 |

SPARX's signal metal TopMetal2 is 9 to 16 skin depths thick in its band, but its ground metal Metal5 is only 1.3 to 2.3.

## The surface model

`gds2palace` meshes no metal interior by default.
Each metal polygon becomes a hollow shell, and every face of the shell, sidewalls included, gets a Palace `Conductivity` boundary with the metal's conductivity and `Thickness` = t.
Palace turns that into a surface impedance, the ratio of the tangential electric to the tangential magnetic field on the face.
For a face of a conductor much thicker than the skin depth it is the Leontovich impedance:

$$Z_s = \frac{1+j}{\sigma \delta}$$

`Thickness` activates Palace's finite-thickness correction.
Palace's schema describes the flag `External` as "Whether this boundary is on the exterior of the computational domain. Relevant for the thickness correction.", and `gds2palace` never sets it, so it is false.
With `External` false each face gets the impedance of a slab of half the thickness, the case of a metal carrying current on both faces:

$$Z_s = \frac{1+j}{\sigma \delta} \coth\left(\frac{(1+j)\,t}{2\delta}\right)$$

With `External` true the full thickness is used, the case of a slab with field on one face only:

$$Z_s = \frac{1+j}{\sigma \delta} \coth\left(\frac{(1+j)\,t}{\delta}\right)$$

Palace's results in the check below match these two forms: the shift between them predicts the shift Palace shows when `External` is set to within 0.7 % of the line loss.
Both reduce to the Leontovich impedance once t is several skin depths.

What the surface model gets right:

- Any conductor much thicker than the skin depth with dimensions large against it: the current lives in the skin, and the surface impedance is the standard model for it.
- Capacitance, coupling, Z0 and phase, which depend on the field outside the metal.
- A thin metal (t much smaller than δ) that carries current on both faces: top and bottom face together give the correct sheet resistance 1/(σ t).

What it gets wrong:

- **Sidewalls of thin metal.** The sidewalls get the same thin-sheet impedance as top and bottom, so a thin strip conducts as if it were w + t wide and its R reads w / (w + t) too low.
- **Ground planes one to two skin depths thick.** A wide ground plane under a line carries the return current on its top face only, so the one-sided formula is the physical one. Palace's default (two-sided, half thickness) gives that face a higher resistance: 1.63 times at 80 GHz, 1.22 times at 160 GHz and 1.02 times at 240 GHz for SPARX's Metal5, and twice when t is much smaller than δ. The gds2palace 0.9.0 changelog states the same limit: thin conductors that carry current on one face only, such as a ground plane under a line, get up to twice their real loss.
- **Corners and narrow traces.** The surface impedance assumes a locally flat surface. Near the edges of a strip that is only a few skin depths wide, the current enters from two sides, which the model does not see. Narrow thick traces then read low.
- **Internal inductance at t ≈ δ**, which moves L by about 1 % on a coil and by 6.6 % per unit length on a hairpin of 7.5 µm lines (OpenBLAU's study below).

## The volume model

With `filled_metals` true, `gds2palace` meshes each metal as a solid domain with the bulk conductivity, and Palace solves the current inside it.
Since gds2palace 0.8.0 the face boundaries are dropped in this mode (0.5.2 still wrote them, and they had to be deleted from `config.json`).
The volume model has no thickness or corner approximation, but the mesh inside the metal has to resolve the skin depth.
OpenBLAU's TopMetal1 study converged with 2 µm cells at a skin depth of 1.93 µm, element order 2.

Things to know before using it:

- `filled_metals` is one switch for every metal (checked in gds2palace 0.8.0). A microstrip model therefore also fills its ground plane, whose skin depth is about as small as the signal metal's.
- `refined_cellsize_override` sets the cell size at a layer's polygon edges. The gmsh size field then grows by about 1 µm per µm of distance, so the centre of a w-wide face gets about cell + w/2. Fine cells across a whole face need a mesh control that gds2palace does not offer.
- Vias are volumes in both models, with σ_xy a tenth of σ_z so that merged via arrays carry little lateral current. A merged array also has more area than its cuts, which `fill_factor_correction` compensates. SPARX's drivers do not merge vias (`merge_polygon_size = 0`), so that does not apply here.

gds2palace 0.9.0 (changelog of 2026-10-15) replaces `filled_metals` with `conductor_model`: `'surface'` (the default, unchanged), `'solve_inside'` (the former `filled_metals = True`) and `'solve_inside_skin'`, new.
`'solve_inside_skin'` splits each conductor into thin layers at 0.4 and 1 skin depth (at the highest frequency) below all its faces plus a core, while the cells along the surface stay at `refined_cellsize`.
Layers thinner than 4 skin depths get no skin layers.
The changelog reports it within 2 to 3 % of a converged reference for the peak Q of TopMetal1 and TopMetal2 coils at a 2 µm mesh, where `'surface'` reads 18 to 30 % high, at 1.5 to 3.5 times the run time of `'surface'`.
It also removes `z_thickness_factor`.
The image this check ran on carries gds2palace 0.8.0, so none of this was used here.

## What other designs found

Two coil studies in the same open toolchain show how much the choice can matter at lower frequency:

- [OpenBLAU](https://github.com/iic-jku/OpenBLAU), DCO tank coil, 7.5 µm TopMetal1 on SG13CMOS5L at 2.5 GHz (t ≈ δ): volume metal moves R by +2.7 %, L by +1.0 % and Q by -1.7 % (`macros/dco_core/doc/dco_ind_filled_metal.md`). On the coarse-tune MOM capacitor the surface model reads the ESR at 0.53 times its value (`macros/dco_core/doc/coarsetune_cap_esr.md`).
- [SG13G2 AMS chip template](https://github.com/iic-jku/ihp-sg13g2-ams-chip-template), branch `add-rf-macro`, 20 GHz VCO coil with 4 µm traces on TopMetal2 and TopMetal1 (t/δ 4.6): volume metal raises R by 28 % and takes Q from 16.5 to 13.0 (`macros/vco/README.md`). There the surface run used 3 µm cells, so mesh and model are not fully separated.

The common thread is narrow traces about as thick as they are wide, and metals of about one skin depth.
SPARX has both: 2.5 µm wide arms on 3 µm TopMetal2, and a 0.49 µm Metal5 ground.

## What SPARX uses

- `palace_sim.py` and `six_port_core_palace_sim.py`: surface metal (no `filled_metals`), `External` unset, `refined_cellsize` 2 µm, element order 2, `SG13G2_nosub.xml`, no via merging.
- The committed `config.json` files of BLC, WPD, BPF and core carry a `Conductivity` boundary with `Thickness` for every metal: TopMetal2 3.0 µm at 3.03e7 S/m, Metal5 0.49 µm at 2.319e7 S/m, plus Metal1 to Metal4 and TopMetal1 in the core.
- The loss figures of the transmission-line study in IHP-GDSFactory-Addon (`evaluation/palace_sim.py`) are surface metal too.

## The check of 2026-10-17/18

### Why not a volume solve

A volume solve that resolves 0.23 µm in TopMetal2 needs cells of about 0.35 µm through all of its 1186 µm² by 3 µm in the WPD. By estimate that is 1 to 1.4 million tetrahedra, or 6 to 9 million unknowns at order 2.
The Metal5 plane under it would be filled as well.
The host had 14 GB and 7 cores, and the largest solve of this check (the BPF, 765 k unknowns) peaked at 8.4 GB.
An under-resolved volume solve spreads the current too deep into the metal and reads R too low, which would have pointed the wrong way.

### Method

1. **2D volume reference.** A quasi-static filament solve of the cross-section, TopMetal2 strip over a 60 µm Metal5 strip, gap 5.65 µm (`scripts/xsec2d.py`). The cells are graded from δ/4 at the surfaces, and the mutual inductance between two rectangles is computed exactly. It reproduces OpenBLAU's TopMetal1 hairpin reference (1.0997 against 1.100 times DC paired, 1.0435 against 1.044 alone) and is converged: a finer mesh moves R′ by 0.16 % at most. For a quasi-TEM line the current distribution is set by the magnetic field, which the dielectric does not change, so a 2D magneto-quasi-static solve gives the conductor loss.
2. **Palace straight lines.** TopMetal2 lines 2.5 µm and 7.2 µm wide over the same 60 µm Metal5 strip, 125, 250 and 500 µm long, ports as in the add-on's line structures. The propagation constant comes from two lengths (eigenvalues of ABCD₂ ABCD₁⁻¹), which cancels the port launches. The line loss is compared with the 2D result at the same Zc = ωL′/β.
3. **Palace WPD and BPF**, the committed `verification/em/layout/` GDS, at 80, 160 and 240 GHz (WPD) and 150 to 170 GHz (BPF).
4. **Variants**, each changing one thing against SPARX's model (`s2`):
    - `ext`: `External` true on the Metal5 faces (the one-sided formula).
    - `r05`: TopMetal2 edges refined to 0.5 µm.
    - `r05ext`: both.
    - PEC metals (WPD), for the radiation share of the dissipation.
    - Conductivities raised to emulate volume physics on the BPF (below).

All runs used the stock image `hpretl/iic-osic-tools:2026.10` (gds2palace 0.8.0, Palace v0.18.1-226, PDK `a49358cc`), point solves, element order 2, the repo's own `palace_sim.py`.
`scripts/` holds every script, `results/` every table quoted here.

### 2D reference

| Line | Ground share of the loss | R′ at 80 / 160 / 240 GHz | L′ at 160 GHz |
|---|---:|---|---:|
| 2.5 µm | 18 % | 15.40 / 21.23 / 25.93 Ω/mm | 0.458 pH/µm |
| 7.2 µm | 27 % | 9.54 / 13.26 / 16.32 Ω/mm | 0.335 pH/µm |
| 12.5 µm | 34 % | 7.19 / 10.00 / 12.34 Ω/mm | 0.263 pH/µm |

A 100 µm wide ground instead of 60 µm lowers R′ by 0.9 to 3.1 %, more for wider lines. The Palace lines use the same 60 µm, so the comparison below is like for like.

### Lines: Palace against the reference

Line loss of Palace divided by line loss of the 2D reference at 80 / 160 / 240 GHz (`results/lines_compare.txt`):

| Variant | 2.5 µm (WPD arms) | 7.2 µm (BPF, 50 Ohm lines) |
|---|---|---|
| `s2`, SPARX's model, 250/500 µm | 1.007 / 1.007 / 1.000 | 1.139 / 1.103 / 1.070 |
| `s2`, 125/250 µm | 0.997 / 0.988 / 0.990 | 1.130 / 1.081 / 1.063 |
| `ext`, one-sided Metal5, 250/500 µm | 0.889 / 0.963 / 0.994 | 0.958 / 1.037 / 1.061 |
| `r05`, TopMetal2 edges 0.5 µm, 125/250 µm | 0.966 / 0.945 / 0.939 | 1.088 / 1.026 / 1.001 |
| `r05ext`, both, 125/250 µm | 0.851 / 0.902 / 0.932 | 0.910 / 0.961 / 0.992 |

The two length pairs agree within 1 to 2 %, which is the resolution of this comparison.

### What moves the loss

- **The Metal5 thickness correction reads the ground high.** `ext` lowers Palace's line loss by 0.118 / 0.044 / 0.006 of the reference (2.5 µm) and 0.181 / 0.066 / 0.009 (7.2 µm). The ground share of the 2D loss times the ratio of the two formulas predicts 0.112 / 0.038 / 0.004 and 0.176 / 0.059 / 0.006. The flag accounts for the shift, so the mechanism is the two-sided thickness formula on a ground plane that carries current on one face.
- **SPARX's 2 µm mesh reads 2 to 6 % high.** Refining the TopMetal2 edges to 0.5 µm lowers the loss of the lines by 3 to 6 % and the dissipation of the WPD from 6.9 / 8.0 / 8.7 % to 6.7 / 7.7 / 8.2 %.
- **The refined surface model reads narrow strips low.** With both corrections, the 2.5 µm line still reads 7 to 15 % below the reference. With the ground part taken as exact, that is 8 to 18 % of the strip loss, largest at 80 GHz where the skin depth is largest against the 2.5 µm width. The 7.2 µm line reads 1 to 9 % low.
- **Radiation is negligible.** With PEC metals the WPD dissipates 0.06 / 0.18 / 0.33 % against 6.9 / 8.0 / 8.7 % with real metals (`results/wpd.txt`).

On SPARX's mesh the three errors cancel for the 2.5 µm arms and add up for the 7.2 µm lines.

### WPD

On SPARX's model the WPD at 160 GHz has S11 -44.0 dB, S21 -3.37 dB and dissipates 8.0 % (0.36 dB), the same as the full adaptive sweep on the current GDS (the committed WPD result predates the port move of `914c021`, see `ToDo.md`).
Most of its loss is in the 2.5 µm arms, whose line loss on SPARX's mesh matches volume physics within 1 %, so the metal model changes nothing measurable for the WPD.

### BPF

The BPF is built from 7.2 µm lines, so its loss follows the 7.2 µm row.
SPARX's model reproduces the committed `sparx160_bpf.s2p` within 0.013 dB at the five passband points.
Volume physics was emulated in two ways on SPARX's mesh: both conductivities raised by 1.092², the measured line-loss excess at 160 GHz, and the cleaner Metal5 `External` with only TopMetal2 raised by 1.073 for the remaining strip excess (`results/bpf.txt`):

| f (GHz) | S21, SPARX's model | S21, σ x 1.19 | S21, `External` + TopMetal2 σ x 1.073 |
|---:|---:|---:|---:|
| 150.4 | -12.749 dB | -12.142 dB | -12.087 dB |
| 155.2 | -10.709 dB | -10.162 dB | -10.065 dB |
| 160.0 | -10.008 dB | -9.294 dB | -9.493 dB |
| 164.8 | -10.746 dB | -10.146 dB | -10.275 dB |
| 169.6 | -11.086 dB | -10.248 dB | -10.558 dB |
| best point | -10.008 dB | -9.294 dB (+0.71) | -9.493 dB (+0.52) |
| mean | -11.060 dB | -10.398 dB (+0.66) | -10.495 dB (+0.56) |

Raising both conductivities over-corrects: Palace's Metal5 term falls faster with σ than the strip term (by 1.165 against 1.092 at 160 GHz), about 2 % too much line loss removed.
The second emulation is the better estimate, ±0.1 dB from the spread of the two length pairs.
The BPF is mismatched at 160 GHz (S11 -6.1 dB) and dissipates 65 % of the incident power, so S21 reacts to small loss changes.
`External` on Metal5 alone gives +0.32 dB.

## Decision: stay on the surface model for now

The criterion set before the check was to switch to volume metal if the BPF loss moved by more than about 0.5 dB.
It moves by 0.52 dB at the best point and 0.56 dB on average, ±0.1 dB, at the threshold.
SPARX stays on the surface model because:

- **The error is conservative.** Volume physics makes the BPF and the 50 Ohm lines less lossy. The committed results understate the receiver's performance, they do not overstate it.
- **The WPD is right as it is**, within 1 %.
- **A volume solve cannot run on the hosts available** with the gds2palace 0.8.0 of the current image. It needs several times their memory, and a coarse one reads too low. The skin-layer model of 0.9.0 is untried.
- **No cheaper model is closer everywhere.** `External` on Metal5 alone brings the 7.2 µm lines to 0.96 / 1.04 / 1.06 but the 2.5 µm arms to 0.89 / 0.96 / 0.99. Refining TopMetal2 as well reads both widths low.
- **Switching touches everything downstream.** All four EM results, the snp2le fits (including the accepted WPD passivity), the testbenches, the documentation numbers and the paper figures would change together.

What the committed numbers mean until then: the BPF is about 0.5 dB too lossy in its passband, the 50 Ohm lines 6 to 14 % (80 to 240 GHz), the WPD is within 1 %.

## When to revisit and switch to volume

A future revision should switch, or repeat this check, when one of these holds:

- Measured insertion loss of the receiver or a test structure disagrees with the EM by more than the 0.5 dB found here.
- An image with gds2palace 0.9.0 or later is available. Its `'solve_inside_skin'` meshes the skin layer without isotropic cells of a skin depth, at a reported 1.5 to 3.5 times the surface run time, which may put a volume solve of the WPD and BPF within reach of a 14 GB host. It is the first thing to try: rerun the BPF with it and compare with the table above.
- A host with enough memory for the plain volume model is available. At the memory per unknown of these runs (8.4 GB for 765 k), the WPD's 6 to 9 million unknowns need about 70 to 100 GB, and the seven-port core far more.
- The design moves to narrower lines, thinner metals or a lower frequency, where the surface model's errors grow (see the coil results above).
- Absolute loss within 0.5 dB becomes a requirement, for example for a link budget or a journal comparison with a commercial solver.

Switching means `conductor_model = 'solve_inside_skin'` (gds2palace 0.9.0 or later) or `filled_metals` true with a mesh that resolves δ inside the metals in both drivers, and then all four EM targets, the fits, the benches and the documentation numbers in one change.
A smaller step is `External` true on the Metal5 boundaries, which removes the ground-plane error at no cost, but it is only worth taking together with a finer TopMetal2 mesh and a check like this one, because on its own it moves the 2.5 µm arms low at 80 GHz.

## Reproduce

Inside IIC-OSIC-TOOLS 2026.10 or later, from a login shell (`palace` must be on the path):

```sh
cd verification/em/metal_model/scripts
python3 xsec_run.py                    # 2D reference: kernel checks, OpenBLAU reference, R' and L' (about 10 min)
python3 xsec_split.py                  # strip and ground share of the 2D loss
export METAL_WORK=/tmp/sparx_metal_model NP=6
bash run_study.sh setup                # stackup variants and line GDS into $METAL_WORK
bash run_study.sh wpd lines bpf        # all Palace runs, about 6 h on 7 cores, peak 8.4 GB (BPF)
bash run_study.sh report               # the WPD, line and BPF tables
python3 compare_bpf.py                 # the BPF passband table
```

`MESH_ONLY=1 bash run_study.sh setup wpd lines bpf` meshes every case without solving, in about 5 minutes.
Nothing is written into the repo: the runs go to `$METAL_WORK/runs/<case>/`.

| File | What it does |
|---|---|
| `scripts/xsec2d.py` | 2D filament solver: graded rectangular cells, exact rectangle mutual inductance, loop R′ and L′, loss share per conductor |
| `scripts/xsec_geom.py` | SPARX cross-section (TopMetal2 over Metal5, stackup z ranges) and the two 2D mesh levels |
| `scripts/xsec_run.py`, `scripts/xsec_split.py` | validation and the 2D results, the loss split |
| `scripts/palace_point.py` | runs `verification/em/scripts/palace_sim.py` with extra gds2palace settings, a point solve and optional `External`, writing only to the run directory |
| `scripts/run_case.sh`, `scripts/run_study.sh` | one case, and every case of the check stage by stage |
| `scripts/make_stackups.py`, `scripts/gen_lines.py` | the stackup variants (PEC, conductivity scaled) and the straight-line GDS |
| `scripts/analyze_snp.py`, `scripts/line_extract.py`, `scripts/compare_lines.py`, `scripts/compare_bpf.py` | S-parameters and dissipation, two-length extraction, the line and BPF comparisons |
| `results/` | the outputs quoted above |

## Limits of this check

- TopMetal2 was refined in one step (2 to 0.5 µm). The Metal5 plane under the lines stays at the mesh the TopMetal2 refinement grows into, about 6 to 8 µm, so the split between strip and ground errors is inferred, not measured.
- The 2D reference uses a 60 µm ground strip and no coupled lines. The BPF's coupled sections and bends are covered only through the 7.2 µm line ratio.
- The two emulations of volume physics change conductivities, which also changes the surface reactance slightly. Their spread is part of the ±0.1 dB.
- The six-port core and the BLC were not solved. The BLC's branches are 7.2 µm and 12.5 µm wide, with a larger ground share than the 2.5 µm arms, so its loss is probably pessimistic too.
