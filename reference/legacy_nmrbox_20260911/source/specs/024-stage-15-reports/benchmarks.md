# Benchmarks: Spec 024 - Stage 15 Reports

## Runtime

Expected report build runtime is seconds, not minutes. It reads TSV/Markdown metadata and figure manifests only.

| Benchmark | Command | Target |
|---|---|---:|
| focused unit tests | `python3.13 -m pytest -q tests/unit/test_tcga_naive_contracts.py::test_report_build_summarizes_claim_boundaries_and_figure_manifests` | < 5 s |
| reviewed-root report build | `python3.13 -m src.pipeline.cli report build ...` | < 30 s |

## Correctness Checks

- `report_claim_boundaries.tsv` has rows for TCGA projection, cross-method concordance, and signature status.
- `figure_manifest_summary.tsv` reports all supplied figure manifests.
- TCGA caption lint failures are zero.
- Concordance caption lint failures are zero.
- `evidence_readiness_status.tsv` includes a visualization row when `--figure-root` is supplied.

## Scientific Checks

- No report text should say TCGA validates ICB response.
- No report text should call nested LOCO external validation.
- Missing external validation must remain visible.
