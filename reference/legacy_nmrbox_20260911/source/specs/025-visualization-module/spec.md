# Feature Specification: Visualization Module — Thesis-Grade Figure Generation

**Feature Branch**: `025-visualization-module`
**Created**: 2026-05-30
**Status**: Active (implementation cycle complete under no-results-mutation policy; corrected-output figure regeneration/sign-off pending approval)
**Input**: Round-2 Step 6. A dedicated, contract-driven visualization module producing the figures the thesis defense needs, fed by the corrected stage outputs (specs 010/015/016/018/021). Consolidates today's scattered plotting (`qc_plots.py`, `cmd_visualize_run` L5239, forest plots inline in `cmd_meta_run` L4977).

## Context Lock

Plotting currently lives in three disconnected places: `src/pipeline/qc_plots.py` (QC figures), `cmd_visualize_run` (cohort-level expression plots), and inline forest-plot code inside `cmd_meta_run`. There is no single module, no figure-contract registry, and no guarantee that a figure reflects the *corrected* science (e.g. forest plots currently visualize the heterogeneous-effect meta; TCGA plots show median-split survival labeled as validation). This module centralizes figure generation behind explicit contracts so every thesis figure is reproducible and scientifically labeled.

## User Scenarios & Testing

### User Story 1 — One command regenerates every thesis figure (Priority: P1)
The examiner asks "regenerate Figure 3 from the committed results." Today figures are emitted as side effects of various stages.
**Independent Test**: `pipeline viz build --results-root <run> --out figures/` regenerates the full figure set from committed stage outputs, deterministically (same inputs → same files, modulo timestamp).

### User Story 2 — Figures carry the corrected scientific framing (Priority: P1)
**Independent Test**: TCGA survival figures are titled "prognostic (TCGA, not ICB-treated)"; concordance figures say "cross-method robustness," not "validation"; forest plots note the assay-harmonized effect. No figure asserts a claim the corrected pipeline does not support.

### Edge Cases
- A stage output is missing/blocked → the figure is skipped with a placeholder + reason, never a crash.
- A cohort with <2 samples per arm → omitted from per-cohort figures with a logged note.
- Headless/CI environment → `matplotlib Agg` backend, no display dependency.

## Requirements

### Functional Requirements
- **FR-001**: A `viz` CLI group MUST build all figures from a `--results-root`, writing to `--out` with a `figure_manifest.tsv` (figure_id → source files, caption, scientific_note).
- **FR-002**: A **figure-contract registry** MUST define each figure: `figure_id`, inputs (which stage output TSVs), plot type, grouping/coloring, and the **scientific caption/label** required (e.g. prognostic-not-predictive).
- **FR-003**: The module MUST consolidate existing plots: per-cohort QC (library size, gene detection, PCA-by-response, sample-distance heatmap, housekeeping), global batch/PCA + variance-partition, volcano (per-cohort DE), forest (meta top genes), signature heatmaps, ssGSEA layer plots (per-layer score distributions R vs NR), TCGA survival KM + subtype-association plots.
- **FR-004**: Figures MUST consume the **corrected** outputs: harmonized-effect meta (spec 016) for forests; real GSVA scores (spec 018) for ssGSEA layer plots; continuous-Cox/prognostic framing (spec 021) for TCGA.
- **FR-005**: Every figure MUST embed (in `figure_manifest.tsv` and as a caption sidecar) a one-line `scientific_note` stating what the figure does and does not show (e.g. "TCGA prognostic association; not ICB-predictive").
- **FR-006**: Deterministic + headless: `Agg` backend, fixed color palettes, sorted inputs, no wall-clock in pixels.
- **FR-007**: The module MUST live in `src/pipeline/modules/_viz/` (or `_15_reports`-adjacent) and the inline forest-plot code in `cmd_meta_run` MUST be moved here (Stage 07 calls the module, not vice versa).
- **FR-008**: Unit tests per figure builder (renders without error on a fixture); integration test builds the full set on a committed mini-run and checks `figure_manifest.tsv` completeness.
- **FR-009**: A reproducibility bundle + a `docs/runbooks/visualization.md` mapping each thesis figure number to its `figure_id` + command.

### Key Entities
- **Figure-contract registry**: `configs/figure_registry.tsv` — one row per figure.
- **Figure manifest** (output): `figures/figure_manifest.tsv`.
- **Caption sidecars**: `figures/<figure_id>.caption.txt`.

## Success Criteria
- **SC-001**: `viz build` regenerates the full set deterministically from committed results.
- **SC-002**: Every figure has a `scientific_note`; no figure mislabels prognostic-vs-predictive or robustness-vs-validation.
- **SC-003**: Forest/ssGSEA/TCGA figures read the corrected (spec 016/018/021) outputs, not legacy ones.
- **SC-004**: Inline plotting removed from `cmd_meta_run`; one module owns figures.
- **SC-005**: Full set builds headless in CI on a fixture; ≥1 test per builder.

## Implementation Notes (Round 3)
- `viz build` command, figure-contract registry loader, scientific-note lint, caption sidecars, and reproducibility bundle are implemented.
- Contract tests cover manifest emission and TCGA/concordance framing lint behavior.
- Forest plotting has been extracted from inline Stage-07 code into `_viz` (`src/pipeline/modules/_viz/forest.py`) and invoked from `cmd_meta_run`.

## Out Of Scope
- Interactive dashboards / web viz.
- Designing the underlying analyses (owned by their stage specs); this module *renders* their outputs.
- Publication typesetting (figure assembly into panels is a manual thesis step; this emits the component figures).
