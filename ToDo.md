## ToDo List

- [ ] top-level LVS: see [issue](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1041) for `Rmetal`: @simi1505
- [ ] WPD EM result: the committed `sparx160_wpd` Palace run (2026-07-29) predates `914c021`, which moved the port 2 and 3 markers to the output edges of the arms (same metal). Re-solve with `make sim-wpd-em`, refit the WPD models, rerun the WPD and composed-core benches and update the documentation numbers. On the current GDS at 160 GHz S21 is -3.37 dB instead of -4.42 dB and S11 -44.0 dB instead of -19.9 dB, and the fit is passive (largest singular value 0.999)