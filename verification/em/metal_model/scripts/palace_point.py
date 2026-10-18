#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: run verification/em/scripts/palace_sim.py with extra gds2palace settings and a point solve
"""Build one Palace model through the repo's own palace_sim.py, changed only where the metal-model study needs it.

    MM_RUN_DIR         output directory (config.json, mesh, output/), nothing is written into the repo
    MM_FREQS_GHZ       comma-separated point frequencies, replacing the 0.5 to 1.5 f_center sweep
    MM_EXTRA           JSON dict merged into palace_sim.py's settings, e.g. refined_cellsize_override
    MM_EXTERNAL_SIGMA  conductivity (S/m) of the surface metal whose faces get "External": true

Usage: palace_point.py <palace_sim.py> <palace_sim.py arguments ...>
"""
import json
import os
import runpy
import sys

import gds2palace
from gds2palace import simulation_setup, utilities

run_dir = os.environ["MM_RUN_DIR"]
freqs = [float(f) for f in os.environ["MM_FREQS_GHZ"].split(",")]
extra = json.loads(os.environ.get("MM_EXTRA", "{}"))
external = os.environ.get("MM_EXTERNAL_SIGMA")
print("gds2palace module:", gds2palace.__file__)
print("extra settings:   ", extra)
print("point solve GHz:  ", freqs)

orig_create_palace = simulation_setup.create_palace


def create_sim_path(script_path, model_basename, dirname=None):
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def create_palace(excite_ports, settings):
    settings.update(extra)
    settings["sim_path"] = run_dir
    config_name, data_dir = orig_create_palace(excite_ports, settings)
    with open(config_name) as f:
        cfg = json.load(f)
    cfg["Solver"]["Driven"] = {
        "Samples": [{"Type": "Point", "Freq": freqs, "SaveStep": 0}],
        "AdaptiveTol": 0.0,
    }
    # Palace's thickness correction uses t/2 per face unless External is set, then t (one-sided)
    if external:
        n = 0
        for bc in cfg["Boundaries"].get("Conductivity", []):
            if abs(bc["Conductivity"] - float(external)) < 1.0:
                bc["External"] = True
                n += 1
        assert n > 0, "no Conductivity boundary with sigma " + external
        print("External set on", n, "boundaries")
    with open(config_name, "w") as f:
        json.dump(cfg, f, indent=2)
    print("config:", config_name)
    return config_name, data_dir


utilities.create_sim_path = create_sim_path
simulation_setup.create_palace = create_palace
script = sys.argv[1]
sys.argv = [script] + sys.argv[2:]
runpy.run_path(script, run_name="__main__")
