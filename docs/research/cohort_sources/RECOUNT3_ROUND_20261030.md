# Paper A recount3 and batch-3 continuation, 30 October 2026

**Status: blocked, because GSE176307 has a changed worksheet item requiring the user’s review.** Cohort work stopped after the difference was detected. No signature was created or transferred; no cohort was admitted by this round. Paper B and frozen RC2 files were not edited. No downloads, scoring, response analysis, model fitting, commit, push or merge occurred.

Authority: `docs/decisions/PAPER_A_CONTINUATION_20261030.md`, the signed integrated amendment, and the decided source-strategy amendment. The user confirmed that the Kim main paper and Rose paper/supplements have not yet been supplied.

## Finished preparation

`tools/a_dav/recount3.py` converts the five pinned local recount3 objects into a private approximate-count table and minimal identity inventory. It implements `compute_read_counts(round=TRUE)`: coverage divided by each run’s average mapped length, rounded to nearest integer with ties to even. The raw QC column is `star.average_mapped_length`; the package prefixes it with `recount_qc.`. It does not use AUC scaling, calculate scores or select an analysis method. Megadepth’s version remains undocumented.

Official method: [recount3 transform_counts.R](https://github.com/LieberInstitute/recount3/blob/devel/R/transform_counts.R), read as source text; the method evidence is also recorded in BATCH3_EVIDENCE section A. The linked branch is mutable, so it is not described as a commit pin. Local source objects, fetch plans and derived tables are hash-bound in each private PROVENANCE.json.

All four complete tables have 63,856 versioned GENCODE v26 gene identifiers, exactly matching the pinned G026 annotation. No symbol conversion, gene collapsing, outcome-based filtering or raw-count-model eligibility is inferred.

| Cohort | Complete gene × run table | Patient preparation |
| --- | ---: | --- |
| gide2019 | 63,856 × 91 | No accepted patient mapping |
| kim2018 | 63,856 × 45 | Patient response and timing unavailable |
| riaz_gse91061 | 63,856 × 109 | 63,856 × 49 sensitivity candidate; matrix checks PASS; unsigned |
| hugo_gse78220 | 63,856 × 28 | 63,856 × 26 sensitivity candidate; matrix checks PASS; unsigned |

Products: `.scratch/runtime/<cohort>/recount3-reviewed-20261030/` contains counts.tsv, sample_inventory.tsv and PROVENANCE.json. Riaz and Hugo additionally have baseline_candidate.tsv, proposed_run_patient_map.tsv and matrix_v3.json. Their patient membership is inherited from the existing admitted tables using exact GEO accession links; admitted primary matrices and signatures are unchanged. These are unsigned preparation products: canonical recount3 field-map/admission wiring and signature review are still pending.

**Gide identity blocker:** a proposed title rule translates the treatment prefix, numeric token and PRE/EDT suffix into cBioPortal labels. It matches only 74 of 91 source runs: 60 of 73 PRE and 14 of 18 EDT. Thirteen PRE and four EDT are unmatched. The rule was not adopted, unmatched samples were not silently discarded, and no patient matrix was published. A private unaccepted mapping is retained for source review. A verified source crosswalk is required before rebuilding Gide’s patient table and worksheet. The old iAtlas processing exception/signature does not authorize this new representation.

**Kim:** 45 tumour-labelled runs were converted; they are not asserted to be 45 eligible patients. Per-patient response, biopsy timing and traceable clinical identity remain blocked. No new PDF extraction was possible.

## Batch-3 V3 and suggested answers

All five V3 runs were executed against the pinned local objects. Receipts are `.scratch/runtime/<cohort>/v3-pinned-20261030/receipt.json`. No suggested exception clears a V3 blocker.

| Cohort | Source features × sample columns | Status and plain blocker |
| --- | ---: | --- |
| Braun | 43,893 × 181 | blocked: baseline timing not accepted; duplicate/mixed feature identifiers; reference, annotation and platform gaps. UQ=1000 → log2 → ComBat across four batches → +21 is now pinned. |
| Van Allen | 21,935 × 40 | blocked: unresolved RPKM/FPKM scale and processing; duplicate feature identifiers; baseline and endpoint review. |
| GSE135222 | 57,820 × 27 | blocked: Supplementary Table 3 join is only suggested; timing, mixed feature IDs and scale documentation unresolved. |
| GSE136961 | 393 × 21 | blocked: D/N response mapping is only suggested; study-wide timing and feature/scale review remain; five extra raw-count columns remain unassigned. |
| GSE176307 | 16,383 × 89 | blocked: deposited scale and negative values, 518-gene discrepancy, sample reconciliation, timing and response-source review. |

Unsigned worksheets are `.scratch/runtime/<cohort>/worksheet-pinned-20261030/WORKSHEET.md` and reviewer_worksheet.unsigned.json. Braun, Van Allen, GSE135222 and GSE136961 retain the same questions, item identifiers and evidence contexts (21, 21, 45 and 42 items). Only the explicitly requested SUGGESTED answers and their source pointers changed; all remain BLOCKED_UNKNOWN. No acceptance of those suggestions is inferred.

## Difference requiring the user’s review

GSE176307 still has 20 items, but the V3 item has changed:

| Before | After |
| --- | --- |
| V3 item `I-ba0c8a2df0f8da1c6013` | V3 item `I-992018b5b53bfa639f8e` |
| Seven unresolved V3 reasons | Same seven reasons, plus `NEGATIVE_VALUES_PRESENT` |
| Field map treated the BACI file as median-centered | Exact deposited transform is UNKNOWN; the published statement about other analyses is insufficient |
| BLOCKED_UNKNOWN | BLOCKED_UNKNOWN |

V3 counted 722,111 negative cells out of 1,458,087. This is a numeric validity/scale check only, with no response comparison. Negative values are not automatically bad; a verified transform could explain them. The issue is the unsupported permission to accept them. The full private difference is `.scratch/runtime/gse176307/worksheet-pinned-20261030/WORKSHEET_DIFF.json`. Further cohort work stopped here.

## One independent code review

One read-only review of the adapter, tests and recount3 fetch plans found one P2 issue: source hashes alone did not bind a bundle to its named cohort. A regression test reproduced cross-cohort relabelling; the adapter now enforces the four authorized cohort/project paths before source reads. That test failed before the fix and passed afterwards. Eighteen adapter tests pass. No second review round was run. The changed module passes mypy.

## Validation

- Final main suite: **625 passed, 3 skipped** (`tests/a_dav_ingest tests/a_dav_implementation tests/a_discovery`), rerun by the primary agent after the review fix.
- Legacy/identity plus DAV contracts: **1,190 passed, 40 failed**. All failures are the existing `tests/a_dav/test_legacy_bridge.py` missing `batchqual` dependency. This command includes ten DAV contract tests.
- Historical evidence with `DAV_EVIDENCE=1`: **24 passed, 1 failed**. Existing inventory-byte mismatch in `test_r4_inventory_rows_match_the_current_bytes_and_hashes`; no historical evidence was rewritten to force a pass.
- A/A.1 plus DAV contracts: **48 passed, 77 subtests passed**; these overlap the ten DAV tests above.
- verify_integration: PASS; 696 manifest hashes, 697 Git hashes, 94 schemas, 16 examples, 38 links, zero failures.
- Fresh Riaz real-source tracer: **1 passed**, fresh basetemp.
- Changed module mypy: **no issues**. No claim that the historical repository-wide mypy errors were fixed.

Private logs and reproduction scripts are in `.scratch/runtime/paper-a-round-20261030/`. The skipped initial evidence invocation was replaced by the enabled run; it is not counted as a pass.

## Still required

1. User review of the changed Rose V3 item before resuming cohort work.
2. Kim and Rose primary PDFs/supplements; an authoritative Gide run-to-clinical-patient crosswalk.
3. User decisions on the four suggested batch-3 rules and remaining timing/feature/processing issues; suggestions alone do not resolve them.
4. Finish canonical recount3 representation wiring and prepare fresh cohort worksheets after the blockers are resolved, then obtain actual user signatures. No signature is requested for an incomplete or inconsistent table.
5. Commit only if the user later requests it.
