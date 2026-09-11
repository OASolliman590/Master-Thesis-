# Research: Spec 010 — Stage 01 Intake (Assay & Response Contract)

Companion to `spec.md`. Current-state audit, frozen I/O contracts, and the scientific-validity section that the per-stage template requires.

## 1. Current-State Audit (verified 2026-05-30)

### 1.1 Where the code lives

- Inference helpers in `cli.py`: `_canonical_timing` (L480), `_canonical_response` (L487), `_infer_input_class` (L494), `_infer_response_label` (L510), `_infer_response_from_text` (L523), `_infer_timing_from_text` (L552), `_metadata_relevance_class` (L572).
- Intake commands in `cli.py`: `cmd_intake_inspect` (L1655), `cmd_intake_build_geo_tables` (L1792), `cmd_intake_build_geo_sample_manifest` (L2065), `cmd_intake_analyze_geo_series_matrix` (L1089), `cmd_intake_extract_characteristics` (L2573), `cmd_intake_apply_characteristics_mapping` (L2693), `cmd_intake_merge_extracted_metadata` (L2832), `cmd_intake_build_patient_manifest` (L2941), `cmd_intake_build_sample_allocation` (L2959).
- Partial module: `src/pipeline/modules/01_dataset_intake/{patient_manifest.py, sample_allocation.py}` (spec 007/008). The dir name uses a leading digit — the extracted package MUST be importable, so use `_01_dataset_intake` (matching the `_00_retrieval` convention from spec 009).
- `common/expression.py::load_expression_matrix` / `_coerce_expression_table` is where assay evidence (integer-ness, negatives, column sums) is observable; the detector should build on it without duplicating parsing.

### 1.2 What works

- Series-matrix parsing, characteristics extraction, alias mapping, patient manifest (spec 007), sample allocation (spec 008) are functional and tested (`tests/unit/test_spec006_metadata_intake.py`, `test_intake_*`, `test_spec007_patient_manifest.py`, `test_spec008_sample_allocation.py`).

### 1.3 Gaps to close (from the 2026-05-30 review)

- **X1**: assay type inferred from accession (`_infer_input_class`), scale re-guessed by magnitude. No file-derived `assay_type`. → FR-001/002/003.
- **X2**: response label heuristic + uniform SD⇒NR; no per-cohort definition record. → FR-005/006.
- Timing inference fragile, undocumented provenance; drives PRE_RESPONSE membership. → FR-007.
- No examiner-facing "inferred vs curated" view. → FR-008.

### 1.4 Existing test inventory for Stage 01

`test_spec006_metadata_intake.py`, `test_metadata_inference_rules.py`, `test_intake_build_geo_tables.py`, `test_intake_build_geo_sample_manifest.py`, `test_intake_analyze_geo_series_matrix.py`, `test_spec007_patient_manifest.py`, `test_spec008_sample_allocation.py`, `test_accession_split.py`. New tests (FR-010) extend, do not replace, these.

## 2. I/O Contract — Assay detection (FROZEN)

`assay_detection.tsv`, one row per cohort:

| column | type | notes |
|---|---|---|
| cohort_id | str | |
| assay_type | enum | raw_counts, tpm, fpkm, rlog_vst, microarray_intensity, normalized_other, raw_counts_suspect |
| detection_confidence | float [0,1] | |
| assay_evidence | str | `;`-joined tuples, e.g. `integer_frac=0.99;has_negative=false;colsum_cv=0.12;median=8.0` |
| n_genes | int | |
| n_samples | int | |
| source_file | path | the matrix inspected |
| assay_type_override | str | empty unless set in manifest |
| override_applied | bool | |

**Detection rules (deterministic, documented):**
- `has_negative=true` ⇒ never `raw_counts`; if `value_range` small and centered ⇒ `rlog_vst`; else `microarray_intensity`.
- `integer_frac ≥ 0.98` and `min ≥ 0` ⇒ `raw_counts` (confidence from integer_frac and colsum spread).
- `0.5 ≤ integer_frac < 0.98` ⇒ `raw_counts_suspect` (flag).
- non-integer, `min ≥ 0`, per-column sums ≈ 1e6 (within tolerance) ⇒ `tpm`.
- non-integer, `min ≥ 0`, not TPM-summing ⇒ `fpkm` if data-processing text says FPKM/RPKM else `normalized_other`.
- series-matrix `!Sample_data_processing` text, when present, raises/overrides confidence.

## 3. I/O Contract — Response definition (FROZEN)

`response_definition.tsv`, one row per cohort:

| column | notes |
|---|---|
| response_definition_id | `rdef_` + sha1(cohort_id|applied_rule)[:12] |
| cohort_id | |
| original_endpoint | e.g. `RECIST 1.1 BOR`, `irRECIST`, `durable_clinical_benefit`, `unknown` |
| criteria_version | free text / version |
| applied_rule | explicit, e.g. `CR/PR=R; SD/PD=NR` |
| sd_handling | `SD=NR` (default) \| `SD=benefit_if_durable` \| `SD=excluded` \| `unknown` |
| label_provenance | curated \| text_inferred \| sampleid_inferred |
| needs_manual_confirmation | bool |
| n_responder | int |
| n_non_responder | int |
| n_unknown | int |

Precedence (FR-006): `curated` (manifest-supplied) > `text_inferred` (`_infer_response_from_text`) > `sampleid_inferred` (`_infer_response_label`). Any cohort whose final labels rest on `sampleid_inferred` is `needs_manual_confirmation=true`.

## 4. Sample manifest additions (FROZEN)

Added columns (existing columns unchanged): `assay_type`, `assay_type_override`, `response_definition_id`, `timing_provenance`. Downstream stages (06/07/09) read `assay_type` and `response_definition_id`.

## 5. Scientific Validity

### 5.1 Why assay type is load-bearing
DESeq2/edgeR/ComBat-Seq assume non-negative integer counts with an NB mean–variance relationship; limma-voom assumes counts→logCPM with mean-variance weights; limma (classic) assumes normalized/log intensities. Feeding the wrong data type produces invalid dispersion estimates and invalid p-values (counts), or destroys the mean-variance modelling (TPM/microarray into NB). A *declared, validated* assay type is the precondition for correct model selection in Stage 06/09.

### 5.2 Why response definition is load-bearing
A meta-analysis pools per-cohort effects under the assumption they estimate the same contrast. If "responder" means RECIST CR/PR in one cohort and durable-clinical-benefit (incl. SD≥6mo) in another, the pooled effect is a blur of two estimands. Recording `original_endpoint` + `applied_rule` + `sd_handling` makes the heterogeneity explicit and enables a Stage 07 sensitivity analysis under harmonised definitions. This does not, by itself, harmonise the labels — it makes the divergence auditable, which is the defensible minimum.

### 5.3 What this spec does NOT change scientifically
It does not re-curate clinical outcomes, does not implement the new transforms (Stage 06/09), and does not change which samples are *currently* included — it changes what is *recorded and gated on*. The behavioural change (model re-routing) is realised in Stage 06/09 against the contract frozen here.

### 5.4 Reproducibility-as-science
The curation report + three records make "show me how cohort X's samples were classified" answerable from committed artifacts, not from re-reading inference code — a defense requirement.

## 6. References
- Love, Huber, Anders 2014 (DESeq2); Robinson et al. 2010 (edgeR); Law et al. 2014 (voom); Ritchie et al. 2015 (limma); Zhang et al. 2020 (ComBat-Seq) — all assume specific data types, motivating §5.1.
- Eisenhauer et al. 2009 (RECIST 1.1); Seymour et al. 2017 (iRECIST) — motivating the response-definition record (§5.2).
