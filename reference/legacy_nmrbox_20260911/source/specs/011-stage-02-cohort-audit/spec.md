# Feature Specification: Stage 02 — Cohort Audit

**Feature Branch**: `011-stage-02-cohort-audit`
**Created**: 2026-05-30
**Status**: Complete (implementation + tests landed in Round 3)
**Scientific-priority rank**: supporting (gates inclusion). Severity S3 / S2.
**Input**: 2026-05-30 review §"Stage 02".

## Context Lock
`cmd_cohort_audit` (cli.py L2980). Produces cohort-level audit/inclusion signals consumed by manifest build.

## Findings addressed
- **02 (S2):** verify the audit actually *blocks* data-type-/label-inconsistent cohorts rather than only reporting. With spec 010 adding `assay_type` + `response_definition`/provenance, the audit should gate on `detection_confidence` and `needs_manual_confirmation`.

## Draft Functional Requirements
- **FR-001**: Audit MUST consume spec-010 `assay_detection.tsv` and `response_definition.tsv` and flag cohorts with low assay confidence or sampleid-only labels as `audit_status=needs_curation`.
- **FR-001a (from data_inspection_2026-05-30.md):** Audit MUST enforce concrete exclusions confirmed in the real data: **drop gse165278** (0 responders → no PRE case arm), **deduplicate gse126044** (entered twice as GEO `gse126044_nsclc_pd1` + SRA `gse126044_srp183455`, identical 5R/11NR — double-counts in meta), and **exclude `methylation_beta`/`unreadable` cohorts** from the RNA-seq tracks. Effective primary PRE_RESPONSE denominator = **21 unique cohorts**.
- **FR-002**: Inclusion decisions MUST be explicit and machine-readable (`include_decision`, `reason`), and downstream stages MUST honour them (verify they do).
- **FR-003**: Extract to `_02_cohort_audit`; tests; reproducibility bundle; runbook.

## Out Of Scope
- The detection/record machinery itself (spec 010).

## Implementation Notes (Round 3)
- `cmd_cohort_audit` now consumes Stage-01 assay/response records when provided and hard-gates:
  - duplicate `gse126044` alias rows,
  - `gse165278` no-responder cohort,
  - `methylation_beta` / `unreadable` assay classes.
- Audit outputs are explicit and machine-readable via `audit_status`, `include_decision`, and `reason`.
- Stage-02 gating is validated by unit coverage in `tests/unit/test_audit_and_manifest_rules.py`.
