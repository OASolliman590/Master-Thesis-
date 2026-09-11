# Quickstart: Cohort Bulk Ingestion and Manifest Reconciliation (Spec-005)

Run from repository root:

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"
```

## 1) Build reconciliation assets (Phase 1 + 2 seed)

```bash
python3.13 scripts/spec_005_prepare_manifests.py \
  --reconciled-tsv /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30/cohorts_source_geo_merged30_reconciled.tsv \
  --discovery-in configs/discovery_geo_focus.tsv \
  --routing-in configs/geo_input_routing_manifest.tsv \
  --sample-manifest-curated configs/sample_manifest_curated.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --ledger-out configs/cohort_id_reconciliation_ledger.tsv \
  --discovery-out configs/discovery_geo_focus.tsv \
  --routing-out configs/geo_input_routing_manifest.tsv \
  --alias-root results/spec_005/downloads_alias
```

## 2) Rebuild GEO intake tables for all 30 cohorts

```bash
python -m pipeline.cli intake build-geo-tables \
  --discovery-manifest configs/discovery_geo_focus.tsv \
  --downloads-root results/spec_005/downloads_alias \
  --routing-manifest configs/geo_input_routing_manifest.tsv \
  --out results/geo_tables
```

## 3) Inject `downloads_folder` into geo-tables summary

```bash
python3.13 scripts/spec_005_attach_downloads_folder.py \
  --geo-summary results/geo_tables/geo_tables_summary.tsv \
  --ledger configs/cohort_id_reconciliation_ledger.tsv \
  --out results/geo_tables/geo_tables_summary.tsv
```

## 4) Rebuild GEO sample manifests + preflight

```bash
python -m pipeline.cli intake build-geo-sample-manifest \
  --cohort-input-table results/geo_tables/cohort_input_table_all.tsv \
  --out configs/sample_manifest_geo_all.tsv \
  --ready-out configs/sample_manifest_geo_ready.tsv

python -m pipeline.cli intake gene-audit \
  --sample-manifest configs/sample_manifest_geo_all.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --gene-id-mapping configs/gene_id_mapping_human.tsv \
  --strict \
  --out results/spec_005/gene_audit_full30

python -m pipeline.cli method inspect \
  --sample-manifest configs/sample_manifest_geo_all.tsv \
  --out results/spec_005/method_inspection_full30

python -m pipeline.cli method curation-sheet \
  --discovery-manifest configs/discovery_geo_focus.tsv \
  --method-inspection results/spec_005/method_inspection_full30/cohort_method_inspection.tsv \
  --out results/spec_005/manual_curation_full30
```

## 5) Supplementary metadata (optional but recommended)

```bash
python3.13 scripts/spec_005_merge_supplementary_metadata.py \
  --sample-manifest configs/sample_manifest_geo_all.tsv \
  --out results/spec_005/supplementary_metadata_merged.tsv
```

## 6) Final curation application + verification run

```bash
python -m pipeline.cli method apply-curation \
  --sample-manifest configs/sample_manifest_geo_all.tsv \
  --curation-sheet results/spec_005/study_manual_curation_filled.tsv \
  --out configs/sample_manifest_curated.tsv \
  --projection-out configs/projection_manifest.tsv

export DOWNLOADS_ROOT="/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30"
export SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
export EXPRESSION_MANIFEST="results/geo_tables/geo_tables_summary.tsv"
bash run_full_pipeline.sh
```

## 7) Post-run report

```bash
python3.13 scripts/spec_005_write_reconciliation_report.py \
  --ledger configs/cohort_id_reconciliation_ledger.tsv \
  --geo-summary results/geo_tables/geo_tables_summary.tsv \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --inspection results/spec_005/method_inspection_full30/cohort_method_inspection.tsv \
  --out results/spec_005/ingestion_reconciliation_report.md
```
