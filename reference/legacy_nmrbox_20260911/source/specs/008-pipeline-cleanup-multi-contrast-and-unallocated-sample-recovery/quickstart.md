# Quickstart: Spec 008

Run from repository root:

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"
```

## Build Allocation Audit

```bash
python -m pipeline.cli intake build-sample-allocation \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --out results/spec_008
```

Expected outputs:

- `results/spec_008/sample_allocation_matrix.tsv`
- `results/spec_008/cohort_allocation_summary.tsv`
- `results/spec_008/unallocated_samples.tsv`
- `results/spec_008/allocation_audit.md`
- `results/spec_008/reproducibility/commands.sh`
- `results/spec_008/reproducibility/environment.yml`
- `results/spec_008/reproducibility/checksums.sha256`

## Multi-Contrast Dry Run

```bash
python -m pipeline.cli router run \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --track ALL \
  --contrasts PRE_RESPONSE,POST_RESPONSE,ON_RESPONSE,TREATMENT_DELTA \
  --out results/spec_008/router_dry_run \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --dry-run
```

## Tests

```bash
python -m pytest tests/ -q
```

