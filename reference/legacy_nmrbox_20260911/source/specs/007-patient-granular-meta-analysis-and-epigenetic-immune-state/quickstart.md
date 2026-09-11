# Quickstart: Patient-Granular Meta-Analysis and Epigenetic Immune-State Layer

## Working Directory

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"
```

## Baseline Checks

```bash
python -m pytest tests/ -q
```

```bash
python -m pipeline.cli intake gene-audit \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --out results/spec_007/preflight_gene_audit \
  --strict
```

Expected current preflight:
- Tests pass: 33 baseline tests.
- Strict gene audit target: 22 pass / 0 fail.

## Phase 1 Target Command

After `intake build-patient-manifest` is implemented:

```bash
python -m pipeline.cli intake build-patient-manifest \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --cohort-input-table results/geo_tables/cohort_input_table_all.tsv \
  --out results/patient_manifest
```

Expected outputs:
- `results/patient_manifest/patient_manifest.tsv`
- `results/patient_manifest/sample_annotations_corrected.tsv`
- `results/patient_manifest/patient_clinical_record.tsv`
- `results/patient_manifest/patient_manifest_validation.tsv`

## Phase 3 Target Check

After comparison registry is implemented, a DE run should produce:

```bash
results/spec_007/comparison_registry.tsv
```

Registry must contain no duplicate `(cohort_id, analysis_type, contrast_definition)` rows.

## Phase 5 Target Check

After ssGSEA is implemented:

```bash
python -m pipeline.cli immune score \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --gene-set-registry configs/immune_gene_sets_registry.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --out results/immune_state
```

Expected outputs:
- `results/immune_state/ssgsea_scores.tsv`
- `results/immune_state/layer_summary.tsv`

## Full Pipeline Verification

Before the full rerun, move the temporary GSE289583 cleaned matrix to T7 if write approval is available:

```bash
mkdir -p /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/recovered_expression/spec_006
cp results/spec_006/recovered_expression/gse289583_hgnc_symbol_counts.tsv.gz \
  /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/recovered_expression/spec_006/
```

Then update `results/geo_tables/geo_tables_summary.tsv` and `results/geo_tables/cohort_input_table_all.tsv` so GSE289583 points to the T7 copy.

Run:

```bash
export DOWNLOADS_ROOT="/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30"
export SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
export EXPRESSION_MANIFEST="results/geo_tables/geo_tables_summary.tsv"
bash run_full_pipeline.sh
```

Expected current target:
- 22 PRE_RESPONSE analyzed cohort IDs.
- 0 executed blockers.
- Spec 007 artifacts present if the spec flag/path is implemented.

