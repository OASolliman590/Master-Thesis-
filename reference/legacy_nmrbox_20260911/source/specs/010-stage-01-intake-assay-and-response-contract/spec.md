# Feature Specification: Stage 01 Intake — Assay-Type Contract, Response-Definition Record, and Timing Provenance

**Feature Branch**: `010-stage-01-intake-assay-and-response-contract`
**Created**: 2026-05-30
**Status**: Active (Round-3 implementation in place; final full-run sign-off pending)
**Input**: 2026-05-30 senior-scientist review (`docs/reviews/pipeline_scientific_review_2026-05-30.md`). This is the next spec in the per-stage hardening cycle, worked in **scientific-priority order** (user decision 2026-05-30). Stage 01 is the source of two cross-cutting S1/S2 flaws — **X1 (assay-type heterogeneity)** and **X2 (response-label heterogeneity)** — so it is both the sequential next spec and the highest-leverage scientific fix.

## Context Lock

Stage 01 (dataset intake) consumes the Stage 00 retrieval outputs (SOFT/series-matrix/runinfo + downloaded matrices) and curates the per-sample manifest that every downstream modelling stage reads: `input_class`, `response_label`, `timing_category`, `cancer_type`, `include_flag`, plus patient-level records (spec 007). All current logic lives in `src/pipeline/cli.py` (the `cmd_intake_*` family, L1655–2980, plus inference helpers L480–581); the module dir `src/pipeline/modules/01_dataset_intake/` holds only `patient_manifest.py` and `sample_allocation.py`.

**Current state (verified 2026-05-30):**

- `_infer_input_class` (cli.py L494) assigns the data type from **accession shape**, not file content: GEO⇒`processed_matrix`, SRP+GEO⇒`raw_counts`, SRP-only⇒`FASTQ`, etc. Nothing reads the actual matrix.
- Matrix scale is later re-**guessed** by a magnitude heuristic in every modelling stage (`is_log = max<50 and median<25`, e.g. `cmd_de_run` L4435, `cmd_immune_score` L6297).
- `_infer_response_label` (L510) assigns responder/non-responder from `sample_id` prefix heuristics (`^(cr|pr)\d+`, `^nr\d+`, `_r`/`_nr` suffixes); `_infer_response_from_text` (L523) adds RECIST-regex inference; **Stable Disease is always mapped to non_responder**. No record of each cohort's original endpoint or the rule actually applied.
- `_infer_timing_from_text` (L552) assigns pre/on/post by regex; PRE_RESPONSE membership depends entirely on this.

**Why this cycle:** these inferences are the upstream root of flaws that invalidate or misframe downstream results (DE model selection, meta pooling, mega ComBat-Seq, response-contrast composition). Fixing them here is a precondition for the Stage 06/07/09 cycles to be meaningful.

## User Scenarios & Testing

### User Story 1 — Every cohort carries a file-derived, override-able assay type (Priority: P1)

The thesis examiner asks: "For cohort X, is this a raw-count matrix or TPM? How does the pipeline know, and what happens if it's wrong?" Today the answer is "it guesses from the accession and again from magnitude."

**Why this priority**: X1 is the systemic S1 flaw; nothing downstream is defensible until assay type is declared and validated rather than guessed.

**Independent Test**: For a fixture set containing one raw-count, one TPM, one rlog/VST, and one microarray-intensity matrix, `intake detect-assay-type` assigns the correct `assay_type` to each from file content alone, and a manifest with a hand-set `assay_type_override` is honoured over detection.

**Acceptance Scenarios**:

1. **Given** a raw integer-count matrix, **When** detection runs, **Then** `assay_type=raw_counts`, `assay_evidence` records integer-ness + column-sum spread, `detection_confidence≥0.9`.
2. **Given** a TPM matrix (non-integer, columns≈1e6), **When** detection runs, **Then** `assay_type=tpm` and it is NOT eligible for count-model DE.
3. **Given** a matrix with negative values, **When** detection runs, **Then** `assay_type∈{rlog_vst, microarray_intensity, normalized_other}` (never `raw_counts`).
4. **Given** `assay_type_override=raw_counts` in the manifest, **When** detection runs and disagrees, **Then** the override wins and a `assay_type_override_conflict` row is logged.

### User Story 2 — Every response label has a provenance record (Priority: P1)

The examiner asks: "How is 'responder' defined in each cohort, and are those definitions comparable?"

**Why this priority**: X2 — cross-cohort outcome heterogeneity is the largest unmodeled confound in ICB meta-analysis.

**Independent Test**: `intake build-response-record` emits `response_definition.tsv` with one row per cohort capturing `original_endpoint`, `criteria_version`, `applied_rule`, `sd_handling`, and `label_provenance ∈ {curated, text_inferred, sampleid_inferred}`. Every `response_label` in the sample manifest links to a `response_definition_id`.

**Acceptance Scenarios**:

1. **Given** a cohort with curated RECIST BOR, **When** the record builds, **Then** `label_provenance=curated` and `applied_rule="CR/PR=R; SD/PD=NR"` is explicit.
2. **Given** a cohort labelled only via `sample_id` prefix, **When** the record builds, **Then** `label_provenance=sampleid_inferred` and the cohort is flagged `needs_manual_confirmation=true`.
3. **Given** a cohort whose authors defined response as durable clinical benefit (SD≥6mo = benefit), **When** the record builds, **Then** `sd_handling` captures the divergence from the default SD⇒NR rule, enabling the Stage 07 sensitivity analysis.

### User Story 3 — Stage 01 is a real Python module (Priority: P2)

**Independent Test**: `python -c "from pipeline.modules._01_dataset_intake import detect_assay_type, build_response_record, infer_timing"` succeeds; CLI dispatches to it; existing intake tests still pass.

### Edge Cases

- A matrix that is part-integer (counts with a few imputed fractional values) — confidence drops, `assay_type=raw_counts_suspect`, flagged for review, not silently passed.
- A cohort with mixed assay types across samples (rare, e.g. merged submissions) — must split or flag, never average.
- A cohort with no response metadata at all — `response_label=unknown`, excluded from response contrasts, recorded with reason (not dropped silently).
- `sample_id` prefix heuristic disagreeing with text inference — record both, prefer text, flag conflict.
- log-scale microarray vs linear-scale: detection must distinguish (negatives ⇒ log/intensity).

## Requirements

### Functional Requirements

> **Empirically validated (data_inspection_2026-05-30.md):** the detector prototype (`scripts/inspect_assay_types.py`) ran on all 30 real cohort matrices. Findings that tighten the rules below: (a) **16/30 cohorts' `source_type_selected` is wrong or unverifiable**; (b) a **methylation β-value matrix (gse222934, 758k rows, 0–1) is mislabeled `raw_counts`** — must be a distinct, RNA-blocked class; (c) **log-scale matrices without negatives** (log2-TPM gse207422, gse100797) are misread as count-suspect — need a max-value rule; (d) **constant column sums** (`colsum_cv≈0`) reliably indicate already-normalized; (e) **4 series-matrix files are unreadable** by the loader and must be a typed failure, not silent-empty.

- **FR-001**: A file-content **assay-type detector** MUST classify each cohort's primary expression matrix into `assay_type ∈ {raw_counts, tpm, fpkm, rlog_vst, log_normalized, microarray_intensity, normalized_other, raw_counts_suspect, methylation_beta, unreadable}` using deterministic evidence: integer-ness fraction, presence of negatives, per-column sum distribution (≈1e6 for TPM; `cv≈0`⇒normalized), value range (`max<~25`⇒log even without negatives), bounded-[0,1]-with-huge-row-count⇒`methylation_beta`, and (if available) the series-matrix `!Sample_data_processing` text. Magnitude alone MUST NOT be the sole basis.
- **FR-001a**: `methylation_beta` and `unreadable` MUST be **hard-excluded from RNA-seq modelling** (Stage 06/07/09) with a typed reason, never silently coerced or zero-contributed. The unreadable series-matrix loader bug (`_read_series_matrix_table`, 4 cohorts incl. gse202069) MUST be flagged here and assigned to the Stage 00/04 fix (it gates the TREATMENT_DELTA arm).
- **FR-002**: The detector MUST emit `assay_detection.tsv` (`cohort_id`, `assay_type`, `detection_confidence`, `assay_evidence`, `n_genes`, `n_samples`, `source_file`) and MUST honour a manifest `assay_type_override` column, logging conflicts.
- **FR-003**: `input_class` (the legacy accession-shape field) MUST be retained for compatibility but MUST NOT be the input to any modelling decision; modelling stages consume `assay_type`. `_infer_input_class` is reclassified as a hint only.
- **FR-004**: The modelling stages' magnitude heuristic (`is_log`) MUST be replaced by an `assay_type`-driven transform decision (documented mapping assay_type → {count-model | log2 | as-is}). (Implemented in the Stage 06/09 specs; **this spec freezes the contract and field** they consume.)
- **FR-005**: A **response-definition record** (`response_definition.tsv`) MUST be emitted, one row per cohort: `response_definition_id`, `cohort_id`, `original_endpoint`, `criteria_version`, `applied_rule`, `sd_handling`, `label_provenance`, `needs_manual_confirmation`. Every sample's `response_label` MUST carry the `response_definition_id`.
- **FR-006 (REVISED per data_inspection_2026-05-30.md):** the live manifest's labels are **already curated** (`manual_curation_sheet_applied`, `characteristics_mapping`) — the sample-id-prefix path is not actually in use. So the priority is **capturing each cohort's original endpoint definition + flagging cross-cohort definition heterogeneity** (durable-clinical-benefit vs RECIST BOR vs PFS vs CR/NR/SD — all present in the real data), feeding the Stage-07 sensitivity analysis (D3). `_infer_response_label` is still demoted to a flagged last-resort fallback, but is not the main concern. **gse165278 (0 responders) MUST be marked DE-ineligible for PRE_RESPONSE; the gse126044 GEO+SRA duplicate MUST be deduplicated.**
- **FR-007**: A **timing-provenance record** MUST capture how `timing_category` (pre/on/post) was assigned per sample (`timing_provenance ∈ {curated, text_inferred, default_pre}`), because PRE_RESPONSE membership depends on it.
- **FR-008**: An intake **curation report** (`intake_curation_report.md` + `.tsv`) MUST summarise, per cohort: assay_type + confidence, response provenance mix, timing provenance mix, and a count of `needs_manual_confirmation` samples — the examiner-facing "what was inferred vs curated" view.
- **FR-009**: Stage 01 logic MUST be extracted into `src/pipeline/modules/_01_dataset_intake/` (detector, response-record, timing); CLI commands preserved and dispatching to the module. `cli.py` Stage 01 surface MUST shrink by ≥ 400 lines (verified by `wc -l`).
- **FR-010**: Unit tests MUST cover: assay detection for all 6 types + suspect, override precedence, response-provenance precedence (curated > text > sampleid), SD-handling capture, timing provenance, empty-metadata cohort. Integration test MUST run intake on a multi-cohort fixture and produce manifest + the three new records with a committed golden file.
- **FR-011**: A reproducibility bundle (`commands.sh`, `environment.yml`, `checksums.sha256` over the manifest + three records) MUST be emitted into the run's `reproducibility/` dir.
- **FR-012**: A runbook `docs/runbooks/stage_01_intake.md` MUST cover invocation, the assay-type and response-definition contracts, and how to supply curated overrides.

### Key Entities

- **Sample manifest** (output, extended): adds `assay_type`, `assay_type_override`, `response_definition_id`, `timing_provenance`. Existing columns frozen.
- **Assay detection record** (`assay_detection.tsv`): one row per cohort. Schema frozen in `research.md` §2.
- **Response-definition record** (`response_definition.tsv`): one row per cohort. Schema frozen in `research.md` §3.
- **Timing-provenance**: per-sample column + summary in the curation report.
- **Intake curation report**: examiner-facing markdown + machine TSV.

## Success Criteria

- **SC-001**: FR-001–FR-012 acceptance scenarios pass automated tests.
- **SC-002**: For the committed cohort set, ≥ 95% of cohorts receive an `assay_type` with `detection_confidence ≥ 0.8`; the remainder are flagged, none silently defaulted.
- **SC-003**: Every `response_label != unknown` links to a `response_definition_id`; ≥ 1 cohort exercises non-default `sd_handling`.
- **SC-004**: Re-running the full pipeline with `assay_type`-driven routing (Stage 06/09) reproduces or *corrects* prior DE results; any cohort whose model class changes is listed in a migration note (expected: cohorts previously mis-routed to the t-test that are actually counts now run DESeq2, and vice versa).
- **SC-005**: `cli.py` Stage 01 surface drops by ≥ 400 lines.
- **SC-006**: Test count grows by ≥ 10.
- **SC-007**: Runbook lets an examiner inspect any cohort's assay + response provenance in < 5 minutes.

## Implementation Notes (Round 3)
- Assay detection contract is implemented in `src/pipeline/modules/_01_dataset_intake/assay_detect.py` and exercised by Stage-01 unit/integration tests.
- Hard-exclusion gates for `methylation_beta` / `unreadable`, `gse126044` dedup, and `gse165278` drop are implemented and covered by tests.
- Response-definition and timing-provenance records plus curation report outputs are implemented and documented in the Stage-01 runbook.
- Final SC-004/SC-002/SC-003 real-run confirmation remains pending by design because this cycle explicitly avoids mutating committed `results/` without user approval.

## Out Of Scope

- Implementing the new `assay_type`-driven DE/scoring transforms themselves — those land in Stage 06 (spec 015) and Stage 09 (spec 018). This spec **freezes the contract** only.
- Real FASTQ→counts quantification for SRA-only cohorts (Stage 04, spec 013).
- Tumor-purity/composition estimation (Stage 09 / X3).
- Re-curating every cohort's clinical labels by hand — this spec builds the *record and provenance machinery* and flags what needs curation; the curation itself is a data task tracked separately.
