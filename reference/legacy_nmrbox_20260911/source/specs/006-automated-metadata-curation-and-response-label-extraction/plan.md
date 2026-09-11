# Implementation Plan: Automated Metadata Curation and Response Label Extraction

## Approach Summary

Parse GEO SOFT `characteristics_ch1` fields from the 30 locally-downloaded SOFT files on T7 into a structured table, apply per-cohort response-label and timing mappings, extend expression alias coverage, rebuild the sample manifest, and re-run the pipeline.

**No new external tool dependencies required.** The SOFT files are already downloaded. `getGeoMetadata` (R) is available as a supplementary source but not needed for the primary extraction path — Python parsing of local SOFT files is sufficient and avoids adding an R dependency.

## Tool Assessment

| Tool | Role | Status |
|------|------|--------|
| Local SOFT parsing (Python) | Primary: parse characteristics_ch1 from downloaded .soft.gz files | **Primary path** |
| extract-geo-metadata (Python) | Supplementary: MINiML XML extraction | Already run (Spec-005); no additional response data found |
| getGeoMetadata (R) | Optional: supplementary HTTP-based extraction | Deferred — only needed if local parsing misses data |

## Phase 0: Spec Kit Initialization

- T001: Create all 6 spec-kit files under `specs/006-automated-metadata-curation-and-response-label-extraction/`.

## Phase 1: Comprehensive Characteristics Extraction

**Goal**: Parse ALL `characteristics_ch1` key-value pairs from SOFT files into a flat, structured table.

- T002: Write `intake extract-characteristics` CLI command that:
  - Reads each cohort's `_family.soft.gz` file from T7
  - Parses `^SAMPLE` blocks and extracts all `!Sample_characteristics_ch1` entries
  - Splits on `:` to get key-value pairs
  - Also extracts `!Sample_title`, `!Sample_source_name_ch1`, `!Sample_description`
  - Outputs a flat TSV: `cohort_id | sample_id | char_key | char_value` (long format)
  - Also outputs a wide-format TSV with one column per unique characteristic key

- T003: Run extraction on all 30 cohorts. Verify >=12 cohorts have response-related characteristic keys.

- T004: Produce a characteristic key inventory: unique keys per cohort, frequency, and response/timing relevance classification.

**Output**: `results/spec_006/characteristics_extracted_long.tsv`, `results/spec_006/characteristics_extracted_wide.tsv`, `results/spec_006/characteristic_key_inventory.tsv`

## Phase 2: Response Label Mapping

**Goal**: Map heterogeneous GEO response values to pipeline-standard labels.

- T005: Create `configs/response_label_mapping.tsv` with columns:
  - `cohort_id` (or `DEFAULT`)
  - `source_field` (the characteristic key name, e.g., `response`, `recist`, `best response on immunotherapy (recist)`)
  - `source_value` (the raw GEO value, e.g., `PD`, `PR`, `CR`, `SD`, `NR`, `response`, `no_response`)
  - `pipeline_label` (the target: `responder`, `non_responder`, `unknown`)
  - `notes` (reasoning)

  Standard RECIST mapping (DEFAULT):
  - CR (complete response) → responder
  - PR (partial response) → responder
  - SD (stable disease) → non_responder
  - PD (progressive disease) → non_responder

  Cohort-specific overrides where needed (e.g., GSE67501 uses `response`/`no_response`).

- T006: Create `configs/timing_label_mapping.tsv` with columns:
  - `cohort_id` (or `DEFAULT`)
  - `source_field` (e.g., `visit (pre or on treatment)`, `sample.timepoint`, `treatment status`)
  - `source_value` (e.g., `Pre`, `On`, `baseline`, `pre-treatment`)
  - `pipeline_label` (`pre_treatment`, `on_treatment`, `post_treatment`, `unknown`)

- T007: Write `intake apply-characteristics-mapping` CLI command that:
  - Reads the extracted characteristics (T002 output)
  - Applies response_label_mapping.tsv and timing_label_mapping.tsv
  - Outputs a mapped TSV: `cohort_id | sample_id | response_label | timing_category | mapping_source`
  - Reports unmapped values for manual review

**Output**: `results/spec_006/response_labels_mapped.tsv`, `results/spec_006/unmapped_values_review.tsv`

## Phase 3: Expression Alias Extraction

**Goal**: Build GSM → expression column mappings for all cohorts.

- T008: Write `intake extract-expression-aliases` CLI command that:
  - For each cohort, reads `!Sample_title` from SOFT
  - Loads the expression matrix and compares title-derived aliases to column names
  - Handles known transformations (strip `RNA-seq_` prefix, append `.baseline`, etc.)
  - Outputs: `cohort_id | sample_id | expression_sample_alias | match_status`
  - Falls back to exact title match, then partial match, then reports unmapped

- T009: Run alias extraction for all 30 cohorts. Verify coverage >=95% for cohorts with non-GSM columns.

- T010: For cohorts where aliases can't be derived from SOFT title (e.g., complex studies), check supplementary metadata files (like GSE207422_metadata.xlsx) for sample ID mappings.

**Output**: `results/spec_006/expression_aliases.tsv`

## Phase 4: Manifest Rebuild

**Goal**: Merge all extracted data into the sample manifest and re-curate.

- T011: Write `intake merge-extracted-metadata` CLI command that:
  - Reads current `configs/sample_manifest_curated.tsv`
  - Merges response labels from T007 output (only for samples where `response_label` is currently `unknown`)
  - Merges timing from T007 output (only where `timing_category` is currently `unknown`)
  - Merges expression aliases from T009 output (only where `expression_sample_alias` is currently empty)
  - Sets `include_flag=true` for samples that now have response_label != unknown AND appropriate timing
  - Does NOT override existing manually curated labels
  - Outputs updated manifest

- T012: Apply DE eligibility rules: for each cohort, check if it has >=2 responders AND >=2 non_responders with pre-treatment timing. Report per-cohort eligibility.

- T013: Update `results/geo_tables/geo_tables_summary.tsv` `primary_expression_file` for cohorts where the series_matrix is empty but supplementary files exist (like gse91061 has `GSE91061_BMS038109Sample.hg19KnownGene.raw.csv.gz`).

**Output**: Updated `configs/sample_manifest_curated.tsv`, `results/spec_006/de_eligibility_report.tsv`

## Phase 5: Verification Evidence Run

- T014: Run `pytest tests/` to verify no regressions.
- T015: Re-run the full pipeline with the updated manifest.
- T016: Verify success criteria:
  - >=8 DE-eligible PRE_RESPONSE cohorts
  - >=5 meta-eligible cohorts
  - Signature with >=2 genes
  - Existing curated cohorts not regressed
- T017: Produce `results/spec_006/curation_reconciliation_report.md` documenting:
  - Per-cohort extraction coverage
  - Response label mapping decisions
  - DE eligibility changes
  - Signature improvement
  - Remaining gaps requiring manual publication review

## Phase 6: Optional getGeoMetadata Integration

Only needed if Phase 1-5 leaves significant gaps.

- T018: If >=5 cohorts still lack response labels after Phase 5, install getGeoMetadata (R) and run supplementary extraction for those cohorts.
- T019: Merge getGeoMetadata output with existing extracted data and repeat Phase 4-5.

## Cohort-by-Cohort Extraction Forecast

| Cohort | Samples | Response Field in SOFT | Expected Pipeline Label | DE Eligible? |
|--------|---------|----------------------|------------------------|--------------|
| gse91061_melanoma_pd1 | 109 | `response: PD/PR/CR/SD` | Yes (RECIST) | Yes (with timing filter for pre-treatment) |
| gse159067_hnscc_pd1_pdl1 | 102 | `best response on immunotherapy (recist): PD/PR/CR/SD` | Yes (RECIST) | Likely (need timing check) |
| gse106128_melanoma_dcs | 47 | `dth response` | Needs investigation | Maybe |
| gse207422_nsclc_pd1 | 39 | `pathologic_response` | Needs value inspection | Maybe |
| gse100797_melanoma_act | 25 | `recist` + `tumor.response` + timing | Yes (RECIST) | Yes |
| gse210287_hnscc_pdl1 | 22 | `response` + timing | Yes | Yes |
| gse93157_nsclc_pd1 | 65 | `response` | Yes | Need NR samples |
| gse67501_rcc_pd1 | 11 | explicit R/NR | Yes | Yes |
| gse115821_melanoma_ctla4_pd1 | 37 | `response` + timing | Already curated | Already done |
| gse126044_nsclc_pd1 | 16 | `patient response` + timing | Already curated | Already done |
| gse78220_melanoma_pd1 | 28 | `anti-pd-1 response` | Already curated | Already done |

**Conservative estimate**: 6-8 newly DE-eligible cohorts, bringing total to 8-11.

## Code Changes Required

1. **New CLI commands** (3):
   - `intake extract-characteristics` (Phase 1)
   - `intake apply-characteristics-mapping` (Phase 2)
   - `intake extract-expression-aliases` (Phase 3)
   - `intake merge-extracted-metadata` (Phase 4)

2. **New config files** (2):
   - `configs/response_label_mapping.tsv`
   - `configs/timing_label_mapping.tsv`

3. **Updated data files**:
   - `configs/sample_manifest_curated.tsv` (more rows with include_flag=true)
   - `results/geo_tables/geo_tables_summary.tsv` (expression file fixes for more cohorts)

4. **No changes to existing pipeline stages** — all fixes are in the intake/curation layer.

## Risk Assessment

- **Low risk**: Parsing characteristics_ch1 from SOFT files is well-understood; the data is already downloaded
- **Medium risk**: Some cohorts may have ambiguous response labels (e.g., `dth response` for GSE106128 — needs value inspection)
- **Low risk**: Expression alias mapping may not cover 100% of samples; fallback to manual mapping for edge cases
- **Blocked**: ~8 cohorts have no response data in SOFT at all (GSE135222, GSE145996, GSE195832, GSE202069, GSE235910, GSE96619, etc.) — these require publication-level manual curation (out of scope for this spec, would be Spec-007)
