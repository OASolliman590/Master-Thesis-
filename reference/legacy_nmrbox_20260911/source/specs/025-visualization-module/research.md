# Research: Spec 025 — Visualization Module

## 1. Current-State Audit (2026-05-30)
- `src/pipeline/qc_plots.py`: `plot_library_size_boxplot`, `plot_gene_detection_barplot`, `plot_pca`, `plot_sample_distance_heatmap`, `calculate_housekeeping_stability`, `calculate_cooks_distance`, `calculate_variance_partition` — solid, reused by `cmd_qc_run`.
- `cmd_visualize_run` (cli.py L5239): cohort-level expression plots.
- `cmd_meta_run` (cli.py L4977): forest plots emitted **inline** (top-50 FDR<0.05 genes).
- No registry, no manifest, no scientific-caption guarantee. Figures are stage side-effects.

## 2. Figure catalogue + source mapping (frozen contract)

| figure_id | inputs (stage output) | type | scientific_note |
|---|---|---|---|
| qc_library_size | Stage 05 qc_metrics | boxplot | library-size distribution per cohort |
| qc_pca_response | Stage 05 / expression | PCA | colored by response; within-cohort |
| batch_global_pca | Stage 05 global_batch_assessment | PCA | cohort vs response variance |
| variance_partition | Stage 05 variance_partition.tsv | bar | fraction variance by factor |
| volcano_<cohort> | Stage 06 DE tsv (harmonized) | volcano | per-cohort DE; model_class in caption |
| forest_<gene> | Stage 07 meta_effects (corrected) | forest | inverse-variance pooled, harmonized scale |
| signature_heatmap | Stage 08 signature + expression | heatmap | signature genes × samples |
| ssgsea_layer_<L> | Stage 09 ssgsea (GSVA) | violin/box R vs NR | real ssGSEA enrichment, per layer |
| tcga_km_<project> | Stage 12 (continuous-Cox) | KM + HR | **prognostic (TCGA not ICB-treated)** |
| tcga_thorsson_<set> | Stage 12 Layer-4 vs Thorsson | assoc bar | descriptive subtype association |
| concordance_tiers | Stage 10 | bar | **cross-method robustness, not validation** |

## 3. Scientific Validity
The module's scientific job is **labeling discipline**: every figure ships a `scientific_note` enforcing the corrected framing (D5 mediator caveat on composition plots; D6 prognostic-not-predictive on TCGA; robustness-not-validation on concordance). A figure that would assert an unsupported claim must be relabeled or withheld.

## 4. References
qc_plots.py provenance; matplotlib Agg for headless determinism; forest-plot convention (effect ± 95% CI, pooled diamond).
