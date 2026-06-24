# NAPOLI 8cgk / 6UQ-3003 Trajectory Simulation Notes

## Source Reconciliation

The shared NAPOLI result endpoint identifies the analyzed system as PDB `8cgk`,
ligand `6UQ-3003`, ligand chain `a`, interacting macromolecular chains `a l`.
The pre-existing local `frame_1/` folder is a different export named
`8FZA_optimized` with ligand `PRF 101 A`, so the synthetic trajectory in this
folder was generated from the online job JSON saved as `../napoli_job_1687.json`.

## Key Biological Signals From Frame 1

- Ligand burial is substantial but not complete: ligand BSA is 775.70 A2,
  corresponding to 46.61% of the unbound ligand ASA.
- The interface is mixed RNA/protein. RNA chain `a` supplies most contacts around
  residues 2469-2482 and 2529-2536, while protein chain `l` contributes a basic
  patch involving ARG50, ARG51, ARG55, and ARG59.
- Contact chemistry is dominated by polar vdW and CH-O/N contacts, with a smaller
  but important H-bond network. Only one CH-pi contact is present, from ARG51 to a
  6UQ ring, and no salt bridge, water-mediated, metal-mediated, cation-pi,
  anion-pi, halogen-pi, or pi-pi contacts were reported in the source job.
- The highest-burial residues in the source frame are ARG51:l, A2471:a,
  A2469:a, C2480:a, G2470:a, and G2535:a. These are treated as the trajectory
  core and therefore fluctuate less than peripheral proximal-only residues.
- Starred contacts are below the sum of the relevant van der Waals radii in
  NAPOLI's display. They highlight close contacts; in a development dataset they
  are useful for testing close-contact persistence and transient steric alarms.

## Synthetic Trajectory Design

Frames 2-10 were generated with a deterministic seed (`60423003`) by perturbing
the observed atom-pair distances and angles. Each contact receives correlated
motion from a global ligand breathing term, a residue term, a ligand-atom term,
and a small deterministic noise component. Marginal contacts can cross NAPOLI-like
thresholds and disappear; no new atom pairs or interaction classes are invented.

ASA/BSA values are recomputed from weighted active-contact scores, so frames with
more close polar/H-bond contacts show slightly greater ligand and residue burial.
This is intentionally plausible NAPOLI-style data, not a substitute for MD.

## Frame-Level Range

- Specific interaction count range: 81-98
- Ligand BSA range: 770.85-792.94 A2
- Ligand BSA percent range: 46.32-47.65%

## Most Persistent / Buried Residues

- ARG51:l present in 10/10 frames, mean BSA 56.19 A2; H-bond frames 0, CH-O/N frames 10, polar vdW frames 10.
- A2469:a present in 10/10 frames, mean BSA 55.26 A2; H-bond frames 10, CH-O/N frames 10, polar vdW frames 10.
- A2471:a present in 10/10 frames, mean BSA 54.39 A2; H-bond frames 10, CH-O/N frames 10, polar vdW frames 10.
- C2480:a present in 10/10 frames, mean BSA 49.06 A2; H-bond frames 10, CH-O/N frames 10, polar vdW frames 10.
- G2535:a present in 10/10 frames, mean BSA 45.08 A2; H-bond frames 10, CH-O/N frames 10, polar vdW frames 10.
- G2470:a present in 10/10 frames, mean BSA 44.23 A2; H-bond frames 10, CH-O/N frames 10, polar vdW frames 10.
- U2479:a present in 10/10 frames, mean BSA 39.82 A2; H-bond frames 0, CH-O/N frames 10, polar vdW frames 10.
- G2536:a present in 10/10 frames, mean BSA 34.70 A2; H-bond frames 10, CH-O/N frames 10, polar vdW frames 8.

## Files

- `frame_01` is the canonical NAPOLI job frame extracted from the JSON.
- `frame_02` through `frame_10` are synthetic trajectory-like frames.
- `trajectory_summary.csv` gives per-frame interaction and BSA counts.
- `residue_persistence.csv` gives residue-level persistence and mean BSA.
- `simulation_manifest.json` records thresholds, seed, and assumptions.
