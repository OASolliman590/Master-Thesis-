# Plan: Spec 010 — Stage 01 Intake (Assay & Response Contract)

## Architecture

Extract Stage 01 inference into `src/pipeline/modules/_01_dataset_intake/` (mirroring `_00_retrieval` from spec 009):

```
_01_dataset_intake/
  __init__.py            # public API: detect_assay_type, build_response_record, infer_timing, build_curation_report
  assay_detect.py        # FR-001/002/003 — file-content detector, builds on common/expression.py observers
  response_record.py     # FR-005/006 — response-definition record + provenance precedence
  timing.py              # FR-007 — timing provenance
  curation_report.py     # FR-008 — examiner-facing report
```

`cli.py` keeps the `intake` subcommands and adds `intake detect-assay-type`, `intake build-response-record`; each dispatches to the module. Legacy `_infer_input_class` stays in `cli.py` but is annotated as a hint feeding `assay_type_override`-eligible defaults only.

**Key principle:** this spec *freezes a contract* (the four new fields + three records). The behavioural consumers (Stage 06 transform routing, Stage 09 scoring) are implemented in their own specs against this frozen contract. That keeps the blast radius of spec 010 to intake.

## Milestones

- **M1 — Spec Kit Setup**: 6 files (this commit).
- **M2 — Tests-First**: failing unit tests for FR-001 (6 assay types + suspect), FR-006 precedence, FR-007 timing, FR-002 override; failing integration test against multi-cohort fixture + golden.
- **M3 — Assay detector**: implement `assay_detect.py`; `intake detect-assay-type`; emit `assay_detection.tsv`; wire `assay_type` into the sample manifest.
- **M4 — Response & timing records**: `response_record.py`, `timing.py`; precedence + SD-handling capture; manifest columns.
- **M5 — Curation report**: `curation_report.py`; `intake_curation_report.{md,tsv}`.
- **M6 — Module extraction + shrink**: move logic, verify ≥400-line `cli.py` reduction, all existing intake tests still green.
- **M7 — Reproducibility bundle + runbook**: FR-011, FR-012.
- **M8 — Sign-off**: SC-001..SC-007; CHANGELOG entry; status Draft→Active→Complete.

## Dependencies

- Upstream: Stage 00 (spec 009) outputs — series matrices + downloaded matrices. Assay detection reads the same files Stage 00 retrieved; coordinate the `detected_assay_type` ledger column noted in the spec 009 scientific note.
- Downstream blocked-on-this: Stage 06 (spec 015) and Stage 09 (spec 018) consume `assay_type`; Stage 07 (spec 016) consumes `response_definition_id` for the sensitivity analysis. Those specs MUST NOT start their behavioural changes until this contract is Active.
- Libraries: numpy/pandas only (no new deps for detection).

## Rollback

- The four manifest columns are **additive**; downstream stages read them with safe defaults during transition, so a partial rollout does not break the current full run.
- If detection proves unreliable on the real cohort set (SC-002 fails), fall back to `assay_type_override` for the affected cohorts (manual) while keeping the contract — detection becomes assist, not gate, for those cohorts; record in a migration note.
- Module extraction is behaviour-preserving; revert by re-pointing CLI dispatch to the in-`cli.py` helpers (kept until M6 sign-off).
- No results are overwritten: new records land in the run's Stage 01 output dir; the prior `results/spec_008` manifest is untouched.

## Constitutional Checks

- One spec per stage ✓ (Stage 01). Template 6 files ✓. Contracts frozen in `research.md` ✓. ≥1 unit test per public function + ≥1 integration test (FR-010) ✓. Reproducibility bundle (FR-011) ✓. CHANGELOG entry at sign-off ✓. Scientific-validity section present (`research.md` §5) ✓.
- Carry-forward from spec 009: reuse the failure-taxonomy enum style for `assay_type`/`label_provenance` vocabularies; reuse the reproducibility-bundle emitter.
