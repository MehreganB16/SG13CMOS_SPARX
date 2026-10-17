// SPDX-FileCopyrightText: 2026 The SPARX Team
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Description: Quarto pre-render script, copies the testbench figures the documentation shows into fig/sim/.

// The figures stay committed in one place, testbenches/xschem/plot_simulations/figures/, and are copied
// before every render, so the site always shows the current results. Quarto bundles Deno, so this needs no extra tool.

const project = Deno.env.get("QUARTO_PROJECT_DIR") ?? ".";
const src = `${project}/../testbenches/xschem/plot_simulations/figures`;
const dst = `${project}/fig/sim`;

const figures = [
  "sparx_core_le_tb_acsp_vacask.png",
  "sparx_powdet_sbd_pss_sweep.png",
  "sparx_powdet_sbd_nf.png",
  "sparx_powdet_sbd_nf_lo_compare.png",
  "sparx_top_le_rx_m1_pex.png",
  "sparx_top_le_nf_m1_pex.png",
];

Deno.mkdirSync(dst, { recursive: true });
for (const name of figures) {
  // a missing figure throws and stops the render, rather than publishing a page with a broken image
  Deno.copyFileSync(`${src}/${name}`, `${dst}/${name}`);
}
