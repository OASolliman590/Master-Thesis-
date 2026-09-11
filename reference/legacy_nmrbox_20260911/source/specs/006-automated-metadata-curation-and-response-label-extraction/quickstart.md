# Quickstart: Automated Metadata Curation and Response Label Extraction

## Prerequisites

- T7 external drive mounted at `/Volumes/T7/`
- 30 GEO cohort folders under `/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30/`
- Each cohort folder contains `*_family.soft.gz`
- Current working manifest: `configs/sample_manifest_curated.tsv` (1097 rows, 30 cohorts)
- Python 3.11+ with pandas, numpy

## Phase 1: Extract Characteristics

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"

python -m pipeline.cli intake extract-characteristics \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --out results/spec_006
```

Expected outputs:
- `results/spec_006/characteristics_extracted_long.tsv` (all characteristics in long format)
- `results/spec_006/characteristics_extracted_wide.tsv` (one column per characteristic key)
- `results/spec_006/characteristic_key_inventory.tsv` (unique keys per cohort)

## Phase 2: Apply Response Mappings

```bash
python -m pipeline.cli intake apply-characteristics-mapping \
  --characteristics results/spec_006/characteristics_extracted_long.tsv \
  --response-mapping configs/response_label_mapping.tsv \
  --timing-mapping configs/timing_label_mapping.tsv \
  --out results/spec_006
```

Expected outputs:
- `results/spec_006/response_labels_mapped.tsv`
- `results/spec_006/unmapped_values_review.tsv`

## Phase 3: Extract Expression Aliases

```bash
python -m pipeline.cli intake extract-expression-aliases \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --out results/spec_006
```

Expected output:
- `results/spec_006/expression_aliases.tsv`

## Phase 4: Rebuild Manifest

```bash
python -m pipeline.cli intake merge-extracted-metadata \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --response-labels results/spec_006/response_labels_mapped.tsv \
  --expression-aliases results/spec_006/expression_aliases.tsv \
  --out configs/sample_manifest_curated.tsv
```

## Phase 5: Re-run Pipeline

```bash
export DOWNLOADS_ROOT="/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30"
export SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
export EXPRESSION_MANIFEST="results/geo_tables/geo_tables_summary.tsv"
bash run_full_pipeline.sh
```

## Verification

Check the pipeline summary for:
- `pre_response_only: analyzed >= 8`
- `signature_status: non_empty_signature`
- Signature file has >= 2 genes
