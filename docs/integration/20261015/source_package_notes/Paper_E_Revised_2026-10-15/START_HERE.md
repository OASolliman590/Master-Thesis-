# Paper E — two-track revision, 15 October 2026

**Latest scope:** complete a public-data-only computational Paper E without any required original biological experiment. Preserve PBPK/PKPD, reduced QSP and virtual-population/scenario layers. Implement a separate optional experimental integration only after the full computational foundation has passed its release gates and compatible measurements actually exist.

## Two deliverables, one-way dependency

| Package | Purpose | Completion dependency |
|---|---|---|
| `specs/E/` — PUBLIC CORE v2 | Public-evidence-constrained exposure, immune-priming/QSP and schedule robustness or quantitative non-identifiability | Admissible public evidence, completed analysis, reproducibility and scientific review; **no local wet-lab data** |
| `specs/E_LAST/` — OPTIONAL LAST-STAGE EXTENSION | Integrate qualifying original data into a new version; evaluate frozen predictions and/or recalibrate only permitted modules | Accepted E-core foundation release **and** generated/QC-admitted data **and** applicable approvals; never a prerequisite for core completion |

The core is not retrospectively described as experimentally validated. The old surface-HLA prospective prediction endpoint moves to the optional extension; it is not a hidden core gate. This does not remove biological requirements from the university thesis or the separate biological paper.

## Read now

1. `specs/E/SCIENTIFIC_APPRAISAL.md` and `CORE_COMPLETION_CONTRACT.md`.
2. `specs/E/inference/PRIMARY_ESTIMAND_AND_ANALYSIS.md` and `PUBLIC_DATA_SUFFICIENCY_AND_FALLBACKS.md`.
3. `specs/E/delivery/CODEX_IMPLEMENTATION_PROMPT.md`.
4. Read `specs/E_LAST/START_HERE.md` only to understand the future interface; do not implement its adapters while core work remains active.

## Boundaries

No new source measurement was fitted; no original experiment was generated; no model was scientifically validated in this revision. Source leads are not admitted datasets. Tests exercise specification/schema/readiness contracts only. No remote branch, commit or PR was created. The integrator owns repository integration.

**Completable without original data is not completable without evidence.** An evidence-adequate scheduling analysis and a rigorous quantitative non-identifiability analysis are different permitted core profiles. A source catalogue alone is not a completed PBPK–QSP paper. See the explicit fail states.
