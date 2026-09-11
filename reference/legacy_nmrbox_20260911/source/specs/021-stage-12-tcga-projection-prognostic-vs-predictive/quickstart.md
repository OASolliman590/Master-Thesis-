# Quickstart: Spec 021 — Stage 12 TCGA Projection

```bash
python -m pipeline.cli tcga project \
  --signature results/signature/pre_response_signature_v1.tsv \
  --tcga-map results/tcga/tcga_project_map.tsv \
  --thorsson-subtypes inputs/tcga/thorsson_subtypes.tsv \
  --gene-set-registry configs/immune_gene_sets_registry.tsv \
  --out results/spec_021_tcga
```

## Expected outputs
- `<PROJECT>_score_input.tsv` with `signature_score` + `signature_score_z`
- `<PROJECT>_survival_stats.tsv` with `model_covariates`
- `thorsson_layer4/epigenetic_layer_tcga_validation.tsv` (optional path)
- `tcga_projection_status.tsv`
