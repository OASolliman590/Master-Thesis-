# Analysis Pipeline Repo

This repository hosts the implementation workspace for the thesis analysis engine.

## Source of Truth

- Canonical usage/run commands: `docs/USAGE.md`
- Specs:
  - `specs/002-ici-discovery-meta-pipeline/`
  - `specs/003-tcga-naive-pan-cancer-projection/`
  - `specs/007-patient-granular-meta-analysis-and-epigenetic-immune-state/`
- Runtime artifacts:
  - `results/` (stage outputs)
  - `logs/` (run manifests/logs)
  - `reports/` (rendered summaries)

## Current Module Status

- RNA-seq routing + DE/meta/signature pipeline: implemented
- Gene-ID preflight audit + canonicalization gates: implemented (`intake gene-audit`, strict in `router run`)
- Immune-state scoring/effects: implemented (data-gated by gene-set paths/CIBERSORTx availability)
- Validation concordance and tier flow: implemented
- TCGA mapping/projection: implemented (data-gated by local TCGA files and non-empty signature)
- TCGA naive epidemiology + pan-cancer synthesis: implemented
- Patient-level manifest and comparison registry: implemented (Spec 007)
- Layered immune-state scoring: implemented (Spec 007 ssGSEA-style gene-set scores)
- Sample allocation audit: implemented (Spec 008; every sample is assigned to PRE/POST/ON/UNALLOCATED)
- Multi-contrast router entry point: implemented and dry-run validated (Spec 008 `router run --contrasts`)
- Shared contrast resolver: implemented (`src/pipeline/common/contrast_resolver.py`)
- Unallocated-sample curation templates: implemented (Spec 008)
- TREATMENT_DELTA pair audit: implemented (Spec 008)
- TCIA overlay: deprecated in Spec 007 and not registered as an active CLI workflow
- Methylation integration: deferred beyond Spec 008
- Report builder: implemented

Operational blocked/skipped states are expected when prerequisites are missing and are surfaced in status tables plus `pipeline_summary.md`.

## Current Pipeline Status

Updated: 2026-05-18

The current active checkpoint is `results/spec_008`. It is a cleanup/routing checkpoint, not a completed full multi-contrast DE/meta/signature execution.

Validated Spec 008 outputs:

| Area | Current result |
|---|---:|
| Sample allocation rows | 1314 |
| Allocated samples | 1120 |
| Unallocated samples | 194 |
| Unallocated curation-template cohorts | 13 |
| Router dry-run routed cohorts | 30 |
| Router dry-run analyzed cohorts | 0 |
| TREATMENT_DELTA audited pairs | 1266 |
| TREATMENT_DELTA eligible cohorts | 3 |
| Latest Spec 008 tests | 49 passed |

Contrast summary:

| Contrast | Sample memberships | Case | Control | Cohorts with membership | DE-eligible cohorts |
|---|---:|---:|---:|---:|---:|
| PRE_RESPONSE | 1040 | 402 | 638 | 23 | 22 |
| POST_RESPONSE | 74 | 27 | 47 | 5 | 5 |
| ON_RESPONSE | 6 | 4 | 2 | 1 | 1 |
| TREATMENT_DELTA | 86 | 36 | 50 | 3 | 3 |

Key files:

- `results/spec_008/spec_008_execution_report.md`
- `results/spec_008/reports/pipeline_summary.md`
- `results/spec_008/reports/multi_contrast_summary.tsv`
- `results/spec_008/router_dry_run/route_execution_summary.tsv`
- `results/spec_008/router_dry_run/cohort_readiness_status.tsv`
- `results/spec_008/sample_allocation_matrix.tsv`
- `results/spec_008/unallocated_samples.tsv`
- `results/spec_008/curation_templates/unallocated_curation_template_index.tsv`
- `results/spec_008/treatment_delta_pair_audit.tsv`
- `results/spec_008/treatment_delta_pair_summary.tsv`

Known caveats:

- Full multi-contrast DE/meta/signature execution is still pending.
- `results/spec_008/router_dry_run` proves routing only; it intentionally reports `executed=false`.
- Unallocated samples require evidence-backed response/timing curation before inclusion in response contrasts.
- Strict signature/meta gates remain underpowered in small slices unless additional discovery-ready cohorts are added or thresholds are explicitly approved.
- Heavy execution should only be run after confirming expression manifests, mounted download roots, and gene-ID compatibility.

## Repository Layout

- `src/`, `pipeline/`, `scripts/`, `tests/`, `configs/`, `inputs/`: code and execution layer
- `docs/`: authored documentation and runbooks
- `reports/`: report artifacts for active analyses
- `results/`, `logs/`, `work/`: runtime outputs and intermediates

## Quick Entry

Run from repository root:

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"
python -m pipeline.cli --help
```

Common run paths:

- Full RNA-seq orchestration: `bash run_full_pipeline.sh`
- Evidence resume: `bash scripts/run_evidence_resume.sh <run_root>`
- TCGA naive resume: `bash scripts/run_tcga_naive_resume.sh <run_root> <signature_tsv> <concordance_tsv>`
- Rebuild current Spec 008 report: `python -m pipeline.cli report build --results-root results/spec_008 --out results/spec_008/reports`
- Re-run low-risk multi-contrast dry-run:

```bash
python -m pipeline.cli router run \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --contrasts PRE_RESPONSE,POST_RESPONSE,ON_RESPONSE,TREATMENT_DELTA \
  --include-excluded \
  --dry-run \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --out results/spec_008/router_dry_run
```

For full commands, prerequisites, outputs, and troubleshooting use `docs/USAGE.md`.

## Notes

- Discovery and validation cohort authority files remain under `../02_data_inventory/`.
- Non-standard cohorts can be routed to dedicated roles (for example comparative multi-omics or tumor-vs-adjacent) via curated manifest fields.
