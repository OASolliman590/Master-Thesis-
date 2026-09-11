# Quickstart: ICI Discovery + Immune-State Interpretation (Spec-002)

This file defines stage order and spec-facing expectations. For copy/paste operational commands and troubleshooting, use `docs/USAGE.md`.

## Scope

Discovery authority:

- `../../02_data_inventory/core_discovery_cohorts_v1.tsv`

Primary implementation track:

- `PRE_RESPONSE` as default discovery contrast
- `TREATMENT_DELTA` and special cohort branches are supported via routing/manifest logic

## Stage Order

### 0) Retrieval and harmonization

```bash
python -m pipeline.cli retrieval run \
  --discovery-manifest ../../02_data_inventory/core_discovery_cohorts_v1.tsv \
  --out results/retrieval
```

Optional GEO typing package:

```bash
python -m pipeline.cli retrieval geo-full \
  --discovery-manifest configs/discovery_geo_focus.tsv \
  --out results/retrieval/downloads

python -m pipeline.cli retrieval geo-manifest \
  --discovery-manifest configs/discovery_geo_focus.tsv \
  --downloads-root results/retrieval/downloads \
  --out results/retrieval/geo_data_type_manifest.tsv
```

### 1) Intake, audit, and curated manifest

```bash
python -m pipeline.cli intake inspect \
  --retrieval-ledger results/retrieval/retrieval_ledger.tsv \
  --out results/dataset_intake

python -m pipeline.cli cohort audit \
  --candidate-roster configs/candidate_cohort_roster.tsv \
  --inventory ../../02_data_inventory/ici_cross_cancer_cohorts.tsv \
  --out results/cohort_audit

python -m pipeline.cli manifest build \
  --discovery-manifest ../../02_data_inventory/core_discovery_cohorts_v1.tsv \
  --retrieval-ledger results/retrieval/retrieval_ledger.tsv \
  --intake-record results/dataset_intake/dataset_inspection.tsv \
  --out configs/sample_manifest.tsv
```

Manual curation flow:

```bash
python -m pipeline.cli method inspect \
  --sample-manifest configs/sample_manifest.tsv \
  --out results/method_inspection

python -m pipeline.cli method curation-sheet \
  --discovery-manifest configs/discovery_geo_focus.tsv \
  --method-inspection results/method_inspection/cohort_method_inspection.tsv \
  --out results/manual_curation

python -m pipeline.cli method apply-curation \
  --sample-manifest configs/sample_manifest.tsv \
  --curation-sheet results/manual_curation/study_manual_curation.tsv \
  --out configs/sample_manifest_curated.tsv \
  --projection-out results/manual_curation/sample_manifest_projection.tsv \
  --audit-out results/manual_curation/curation_apply_audit.tsv
```

Gene-ID preflight gate (required before modeling):

```bash
python -m pipeline.cli intake gene-audit \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --gene-id-mapping configs/gene_id_mapping_human.tsv \
  --strict \
  --out results/gene_id_audit_preflight
```

### 2) RNA-seq routing and discovery

Recommended orchestrator:

```bash
python -m pipeline.cli router run \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --track ALL \
  --out results/<run_root>/router \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --count-method deseq2 \
  --gene-id-mapping configs/gene_id_mapping_human.tsv
```

Signature derivation:

```bash
python -m pipeline.cli signature derive \
  --contrast PRE_RESPONSE \
  --meta-dir results/<run_root>/router/meta_analysis/pre_response_only/PRE_RESPONSE \
  --out results/<run_root>/signature_sets
```

Visualization layer:

```bash
python -m pipeline.cli visualize run \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --de-dir results/<run_root>/router/within_cohort_de \
  --meta-dir results/<run_root>/router/meta_analysis/pre_response_only/PRE_RESPONSE \
  --immune-dir results/<run_root>/immune_state \
  --out results/<run_root>/visualizations
```

### 3) Immune-state interpretation

```bash
python -m pipeline.cli immune score \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --gene-set-registry configs/immune_gene_sets_registry.tsv \
  --out results/<run_root>/immune_state

python -m pipeline.cli immune effects \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --immune-dir results/<run_root>/immune_state \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --out results/<run_root>/immune_state
```

Layering policy:

- Stage 1 baseline: `HALLMARK`
- Stage 2 interpretability layer: `KEGG`
- Advance only after prespecified gates (consistency/stability/FDR)

### 4) Validation and TCGA hooks

```bash
python -m pipeline.cli validate run \
  --signature results/<run_root>/signature_sets/pre_response_signature_v1.tsv \
  --results-root results/<run_root> \
  --contrast PRE_RESPONSE \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --out results/<run_root>/validation
```

TCGA-specific execution is defined in `specs/003-tcga-naive-pan-cancer-projection/quickstart.md`.

### 5) Reporting

```bash
python -m pipeline.cli report build \
  --results-root results/<run_root> \
  --out results/<run_root>/reports
```

## Acceptance Check (Spec-002)

Minimum acceptance for an implementation run:

- Router executes requested tracks and emits route summary.
- Signature stage emits either a non-empty signature or explicit empty-signature status.
- Immune stage emits outputs or explicit blocking reason.
- Validation emits concordance and status artifacts.
- Report summarizes completed vs skipped/blocked stages.
