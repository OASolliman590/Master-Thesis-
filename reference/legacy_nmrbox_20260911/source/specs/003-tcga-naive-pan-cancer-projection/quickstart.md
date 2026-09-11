# Quickstart: TCGA Treatment-Naive Pan-Cancer Projection (Spec-003)

This file defines spec-facing stage order for TCGA-naive projection. For operational command recipes and troubleshooting, use `docs/USAGE.md`.

## Scope

Run TCGA projection as a post-discovery layer using a frozen GEO signature and treatment-naive filtering.

## Prerequisites

- Non-empty signature file:
  - `results/<run_root>/signature_sets/pre_response_signature_v1.tsv`
- Curated sample manifest:
  - `configs/sample_manifest_curated.tsv`
- TCGA project registry:
  - `configs/tcga_naive_project_registry.tsv`

## Stage Order

### 1) Build TCGA URL/local-path map

```bash
python -m pipeline.cli tcga map \
  --projects TCGA-SKCM TCGA-LUAD TCGA-LUSC TCGA-HNSC TCGA-LIHC TCGA-KIRC TCGA-KIRP TCGA-STAD TCGA-GBM TCGA-PRAD \
  --out results/tcga_naive_projection/mapping
```

Expected artifact:

- `results/tcga_naive_projection/mapping/tcga_sample_map.tsv`

### 2) Build GEO-to-TCGA mapping

```bash
python -m pipeline.cli tcga naive-map \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --project-registry configs/tcga_naive_project_registry.tsv \
  --out results/tcga_naive_projection/mapping
```

### 3) Build naive manifest and clinical flat table

```bash
python -m pipeline.cli tcga naive-manifest \
  --tcga-map results/tcga_naive_projection/mapping/tcga_sample_map.tsv \
  --out results/tcga_naive_projection/manifests
```

Expected artifacts:

- `tcga_naive_patient_manifest.tsv`
- `tcga_clinical_flat.tsv`
- `tcga_naive_manifest_status.tsv`

### 4) Build tier signatures from concordance

```bash
python -m pipeline.cli tcga tier-validate \
  --concordance results/<run_root>/validation/validation_concordance.tsv \
  --survival-dir results/tcga_naive_projection/projection \
  --signature results/<run_root>/signature_sets/pre_response_signature_v1.tsv \
  --out results/tcga_naive_projection/concordance_tiers
```

### 5) Run naive-filtered projection and survival

```bash
python -m pipeline.cli tcga project \
  --signature results/<run_root>/signature_sets/pre_response_signature_v1.tsv \
  --tcga-map results/tcga_naive_projection/mapping/tcga_sample_map.tsv \
  --naive-manifest results/tcga_naive_projection/manifests/tcga_naive_patient_manifest.tsv \
  --tier-signatures-dir results/tcga_naive_projection/concordance_tiers \
  --out results/tcga_naive_projection/projection
```

Status artifact:

- `results/tcga_naive_projection/projection/tcga_projection_status.tsv`

### 6) Run epidemiology interaction models

```bash
python -m pipeline.cli tcga epi-model \
  --score-dir results/tcga_naive_projection/projection \
  --naive-manifest results/tcga_naive_projection/manifests/tcga_naive_patient_manifest.tsv \
  --clinical-flat results/tcga_naive_projection/manifests/tcga_clinical_flat.tsv \
  --out results/tcga_naive_projection/epidemiology
```

### 7) Build pan-cancer synthesis

```bash
python -m pipeline.cli tcga pan-cancer \
  --survival-dir results/tcga_naive_projection/projection \
  --epi-dir results/tcga_naive_projection/epidemiology \
  --project-registry configs/tcga_naive_project_registry.tsv \
  --out results/tcga_naive_projection/reports
```

Expected artifacts:

- `tcga_pan_cancer_survival_summary.tsv`
- `tcga_pan_cancer_heterogeneity.tsv`
- `tcga_pan_cancer_status.tsv`

### 8) Final report

```bash
python -m pipeline.cli report build \
  --results-root results/tcga_naive_projection \
  --out results/tcga_naive_projection/reports
```

### 9) Resume interrupted runs

```bash
bash scripts/run_tcga_naive_resume.sh \
  results/tcga_naive_projection \
  results/<run_root>/signature_sets/pre_response_signature_v1.tsv \
  results/<run_root>/validation/validation_concordance.tsv
```

## Acceptance Check (Spec-003)

Minimum acceptance for an implementation run:

- Naive manifest is generated with explicit inclusion/exclusion status.
- Projection status table is emitted with completed vs skipped/blocked projects.
- Epidemiology interaction table is emitted (or explicit blocked status if underpowered).
- Pan-cancer summary artifacts are emitted (or status table explains data gating).
- Report includes TCGA-naive section with stage outcomes.
