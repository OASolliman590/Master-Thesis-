# Riaz: decisions before signing

26 October 2026, Cairo. Scope: GSE91061 × `A_BASELINE_BIO`. These are proposed dispositions from public-source review, not a signature or admission. Frozen specifications remain unchanged. No expression analysis or downloaded analysis code was run.

**Update:** the user subsequently approved baseline-only scope and author BOR on 26 October. See the [accepted scope decision](../decisions/RIAZ_BASELINE_BOR_20261026.md). QC remains proposed; this is not a signature.

## What the evidence settles

All 51 baseline specimens have source-supported patient joins. The count difference between GEO (109) and the harmonized resource (107) is confined to on-treatment material. Source clinical `NE` and GEO `UNK` both prevent an evaluable objective-response assignment; their raw meanings remain distinct. The paper supplies RECIST v1.1 and study biopsy windows, not individual collection dates. The remaining exclusion issue combines four script removals with a separate published PCA exclusion; the sources do not establish one universal eligibility set.

See the [identity evidence review](A_DAV_RIAZ_IDENTITY_REVIEW_20261026.md) and [clinical evidence review](A_DAV_RIAZ_CLINICAL_REVIEW_20261026.md). Primary sources are the [GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061), [author sample table](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/data/SampleTableCorrected.9.19.16.csv), [author clinical table](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/data/bms038_clinical_data.csv), [author script](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/rnaseq/TableS6.A.R), [pinned harmonized study](https://github.com/cBioPortal/datahub/tree/1da5c747e4fdb6125e46410e61842a786e134833/public/mel_iatlas_riaz_nivolumab_2017), and [original article methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC5685550/).

## All nine worksheet items

IDs below identify the original unsigned worksheet from 25 October. A software correction changes an item's ID when its evidence/category changes; it does not transfer any approval. Private source pointers remain in the runtime worksheet. In the 26 October regenerated worksheet, item 1 is `I-08aa8f17569763e659dd` (`AUTHOR_SAMPLE_CODE_IDENTITY_CONFLICT`) and item 2 is `I-7100fa20b853bdcd3895` (still missing; more specific pointer). The other seven IDs are unchanged. Both worksheets remain unsigned.

| # | Original item ID | Evidence and proposed disposition | Decision still needed |
| --- | --- | --- | --- |
| 1 | `I-2453aa9d06a739f6a39b` | On-treatment title has no full-name match, but a same specimen-code candidate has conflicting identity labels. Report the candidate conflict; do not join or correct it. | Keep outside the baseline population; retain unresolved for A.1. A shared code alone is not proof of physical specimen identity. |
| 2 | `I-14fe0075e4dfc68e92d1` | On-treatment specimen has no author-table match, including no matching specimen-code suffix. | Keep outside baseline; no guessed match or deletion from the raw source inventory. |
| 3 | `I-2c485e4f000382145ad3` | Two distinct on-treatment specimens share a patient/visit label. Metadata does not select which to keep. | Keep both source records; defer any longitudinal replicate selection. |
| 4 | `I-6e356c35dc2585083392` | Study protocol specifies on-treatment days 23–29. Individual collection days are not established by the reviewed metadata. | Baseline-only scope excludes On specimens. Do not fill each collection day with 29. |
| 5 | `I-0c01e94e1428c298b680` | On-treatment author NE versus GEO UNK. Preserve both labels and no binary response assignment. | Accept the vocabulary explanation while keeping this specimen outside baseline. |
| 6 | `I-0f3a9ce2c18297d65dcb` | Baseline author NE versus GEO UNK. Both prevent an evaluable ORR assignment. | Retain the source record; exclude from ORR-evaluable membership. |
| 7 | `I-47f3dec5f3e9b814f6da` | A second baseline author NE versus GEO UNK. Same handling, with its own source pointers. | Retain the source record; exclude from ORR-evaluable membership. |
| 8 | `I-8c1e8c687be8b58c5fbf` | Four removals in a particular author script lack a stated rationale there; the article separately reports one PCA exclusion. | Do not inherit the script's population blindly or force the published N. Approve an outcome-independent QC/eligibility policy before analytical inclusion, or explicitly scope a later exact reproduction. |
| 9 | `I-4f5ddbe4c0ec44c325eb` | GEO has 51 Pre/58 On; the harmonized resource has 51 Pre/56 On. This explains the count difference at branch level, not the reason for the omitted records. | Keep the harmonized resource as a cross-check; it cannot remove source-of-record specimens. |

The table is a recommendation based on the two evidence reviews, not nine recorded approvals. The 51 linked baseline specimens are not an analysis-ready denominator. The two baseline NE records mean at most 49 have evaluable source categories before QC, exclusion, assay, overlap and exposure rules. No analysis population was selected here.

## Decisions and current status

1. **Scope — approved:** continue `A_BASELINE_BIO` with pretreatment specimens only. Keep unresolved on-treatment identity, duplicate and actual-day questions visible for A.1. These are not prerequisites for baseline clinical joins.
2. **Outcome handling — approved:** use original author BOR with RECIST v1.1; preserve GEO corroborating labels; follow the frozen mapping (CR/PR responder, SD/PD nonresponder, NE/unknown unevaluable). This records the existing contract, not a new endpoint. Source-binding review and the worksheet signature remain outstanding.
3. **Exclusion/QC — proposed:** preserve all source-available baseline records now. The [QC proposal](A_DAV_RIAZ_QC_PROPOSAL_20261026.md) defines the pending technical rules and the choice between retained FPKM and TPM representations. Do not claim exact Table S6A reproduction or select samples to obtain N=45. Exact reproduction would require a separate, reconciled source population.

The first two choices no longer need to be asked again. They are not an instruction to mark V0–V8 PASS. V7 remains unapproved. Matrix suitability/representation, treatment/timing configuration, overlap and prior-use disposition remain separate required gates. The review must distinguish source availability from analytical eligibility. Current implementation results are recorded in the [accepted scope decision](../decisions/RIAZ_BASELINE_BOR_20261026.md).

## Earlier engineering verification, before the scope/BOR implementation

The parallel Luna chat implemented `tools/a_dav/review_prepare.py`: it takes an explicitly configured packet, discards stale dependencies and derived records, rebuilds metadata-stage results, and emits a matching unsigned worksheet. It selects no scientific policy and cannot approve admission or build a matrix. The reporting correction now exposes the same-code conflicting candidate without using it to establish identity. The real metadata rerun retains 51 baseline joins and nine source questions. Parent verification: 29 focused tests passed, with the opt-in real tracer skipped in that default run; the real tracer then passed separately. Strict mypy passed the three touched production modules with `--strict --follow-imports=silent --ignore-missing-imports --explicit-package-bases`. Astra accepted the bounded source and code review with no substantive finding; its two documentation corrections were applied. No repeat full-redesign review was started.

The parallel implementation chat `01a174e8-e111-75f3-9f7c-05ea872f360c` completed and was archived after review as requested. Work remains in this checkout, uncommitted.

The real preparation command was exercised on the newly generated, unmodified-policy packet. Registries passed; endpoints (`ENDPOINT_MAPPING_UNKNOWN`), timing (`INDEX_TREATMENT_UNRESOLVED`), assays (`ASSAY_POLICY_UNKNOWN`), overlap (`OVERLAP_POLICY_UNKNOWN`) and exposure (`EXPOSURE_POLICY_UNKNOWN`) remain blocked. This exposes missing evidence/policy configuration together; it does not infer that missing scientific facts are software defects. Some inputs can now be supported by the reviewed article, but the endpoint/QC population, measurement representation and prior-exposure/overlap dispositions still need explicit encoding and validation. No one has signed or admitted the cohort.

Updated private artifacts are under `.scratch/runtime/riaz_gse91061/ingestion-review-20261026/` and `review-prepared-20261026/`. The original 25 October worksheet is preserved. The prepared `reviewer_worksheet.json` is unsigned, and `SUMMARY.json` contains only stage status/reason codes. No raw source rows appear in this report.

The final step is to encode accepted source and policy decisions, regenerate the packet and matching worksheet, and review its remaining gates. Only the author or named supervisor supplies the real signature. No appointment search or two-reader rehearsal is needed for these public objects under the [approved public-reviewer amendment](../decisions/AMENDMENT_V7_PUBLIC_REVIEWER_20261025.md).
