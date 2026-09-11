# Research: Spec 011 — Stage 02 Cohort Audit

## 1. Audit Problem
Stage 02 originally reported cohort health but did not consistently enforce high-stakes exclusions. Round-2 data inspection and D0/D1 decisions require deterministic gating.

## 2. Locked Policy
- Exclude duplicate alias row for `gse126044` (retain one canonical cohort in denominator).
- Exclude `gse165278` from PRE-response analysis due to missing responder arm.
- Exclude `methylation_beta` and `unreadable` assay classes from RNA-seq DE/meta tracks.
- Mark low-confidence / manual-confirmation cases as `needs_curation`.

## 3. Contract
`cohort_audit.tsv` must provide machine-readable gating keys:
- `audit_status` (`ready`, `excluded`, `needs_curation`, `hold`)
- `include_decision`
- `reason`

These are consumed by manifest build and govern downstream inclusion.

## 4. Scientific Validity
This stage prevents denominator inflation and assay-mixing bias before DE/meta, preserving interpretability of pooled estimates and signature derivation.
