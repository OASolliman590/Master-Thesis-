# Quickstart: Spec 010 — Stage 01 Intake (Assay & Response Contract)

## TL;DR

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"

# Detect assay type per cohort from file content (X1 fix):
python -m pipeline.cli intake detect-assay-type \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --out results/spec_010

# Build the response-definition record (X2 fix):
python -m pipeline.cli intake build-response-record \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --out results/spec_010
```

## What you get

- `results/spec_010/assay_detection.tsv` — one row per cohort: `assay_type`, `detection_confidence`, `assay_evidence`.
- `results/spec_010/response_definition.tsv` — one row per cohort: `original_endpoint`, `applied_rule`, `sd_handling`, `label_provenance`, `needs_manual_confirmation`.
- Extended `sample_manifest` with `assay_type`, `assay_type_override`, `response_definition_id`, `timing_provenance`.
- `results/spec_010/intake_curation_report.md` — examiner-facing "inferred vs curated" view.
- `results/spec_010/reproducibility/` — `commands.sh`, `environment.yml`, `checksums.sha256`.

## How to read the contract

- **assay_type drives modelling.** A cohort with `assay_type=raw_counts` is eligible for DESeq2/edgeR or limma-voom (Stage 06) and ComBat-Seq (mega); `tpm`/`fpkm`/`normalized_other` route to **limma-trend/limma** (NOT voom — voom needs counts); `microarray_intensity` routes to classic limma. `input_class` is now only a hint.
- **response_definition_id makes labels auditable.** Trace any `response_label` back to its cohort's `applied_rule` and `sd_handling`. Cohorts with `needs_manual_confirmation=true` rest on sample-id heuristics — curate before trusting.

## How to supply curated overrides

Add columns to the sample manifest before running:
- `assay_type_override` — set per cohort to force the assay type (detection logs the conflict but obeys the override).
- curated `response_label` + a cohort-level `original_endpoint` / `sd_handling` — these take precedence over text and sample-id inference.

## How to verify it does not change current results yet

This spec freezes a contract; behavioural re-routing lands in Stage 06/09 specs. To confirm intake is additive:

```bash
# The new columns are added; existing columns are unchanged:
diff <(cut -f1-N old_manifest.tsv) <(cut -f1-N results/spec_010/sample_manifest.tsv)   # expect empty for the legacy columns
```

The SC-004 migration note (`results/spec_010/assay_model_migration_note.md`) lists which cohorts *would* change model class once Stage 06 consumes `assay_type` — review it before running the Stage 06 cycle.

## How to run only the tests for Stage 01

```bash
pytest tests/unit/test_intake_* tests/unit/test_spec006_metadata_intake.py \
       tests/unit/test_stage_01_*  -q
```

## Where to look next
- Review findings driving this spec: `docs/reviews/pipeline_scientific_review_2026-05-30.md` (X1, X2).
- Downstream consumers: spec 015 (Stage 06 DE — assay-driven model routing), spec 018 (Stage 09 — real ssGSEA), spec 016 (Stage 07 — response-definition sensitivity analysis).
