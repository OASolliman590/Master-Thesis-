# Benchmarks: Spec 026 — Analysis Design Contrast Registry

| Benchmark | Command | Target |
|---|---|---|
| Design build wall time | `time python3.13 -m src.pipeline.cli design build --sample-manifest configs/sample_manifest_curated.tsv --out /tmp/spec026_design` | < 10 seconds on curated manifest |
| Registry row count | `wc -l /tmp/spec026_design/analysis_contrast_registry.tsv` | Deterministic for a fixed manifest |
| Router dry-run safety | `python3.13 -m src.pipeline.cli router run --sample-manifest configs/sample_manifest_curated.tsv --analysis-registry /tmp/spec026_design/analysis_contrast_registry.tsv --analysis-membership /tmp/spec026_design/analysis_contrast_membership.tsv --dry-run --out /tmp/spec026_router` | Writes summary only; no DE/meta outputs |

