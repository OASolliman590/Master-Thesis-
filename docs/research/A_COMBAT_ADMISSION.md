# COMBAT source admission: assay scale and outcome timing

Checked 6 September 2026 (Cairo). Source/format audit, not analysis or endpoint approval. Canonical A-P1/A-P2 and the separate prostate transport branch are preserved.

## Decision-changing evidence

The actual GEO workbook resolves the sample-header gate: 30 expression columns exactly equal the 30 GEO sample titles, with 15 distinct subjects each represented at Pretx and C4D1. Both proposed CYT genes have one row and finite nonnegative values for all 30 profiles. This establishes feature presence, not a valid score.

The assay-scale gate fails for direct use as standard pmeTPM. GEO labels the values pmeTPM, while its linked file and worksheet identify expected counts. Complete structural inspection found 26,467 unique gene labels, no invalid or negative cells, and column sums ranging from 1,306,624.91 to 40,876,909.09. Every column exceeds one million. This is inconsistent with an unmodified nonduplicated gene-level TPM/pmeTPM table. Expected counts are the leading source-supported interpretation, but the exact export has not been proven. Do not silently rename the values, divide by column totals and call them TPM, or apply a frozen TPM-trained model. The workbook supplies no effective-length columns.

Official RSEM documentation distinguishes expected counts from TPM and posterior-mean TPM; gene abundances sum their constituent transcript abundances. This supports the scale contradiction, not a complete reconstruction of the author's quantification. [RSEM output documentation](https://deweylab.github.io/RSEM/rsem-calculate-expression.html#output), fields `expected_count`, `TPM`, `pme_TPM` and `sample_name.genes.results`.

## Clinical timeline and mapping

Sena's original BAT study defines Figure 3 response at C4D1, after three BAT cycles. Its transcriptomic comparison is therefore not proof of response following nivolumab. [JCI162396](https://www.jci.org/articles/view/162396), Results “AR activity determines response to BAT,” Figure 3A–E and legend; DOI10.1172/JCI162396, 2022.

The later COMBAT trial starts nivolumab at C4D1 and distinguishes responses occurring before and after its addition. Its overall confirmed PSA50 endpoint must not be inferred from the earlier BAT response flag. The source workbook contains separate C4D1 and nivolumab PSA columns. Its RNA methods describe RSEM read-count estimates followed by DESeq2 normalization, strengthening the count interpretation. Its paired RNA analysis uses 12 patients (six responders, all responding before nivolumab, and six nonresponders), whereas GEO provides 15 pairs. The 12-subject analysis cannot silently inherit all 15 public subjects without a selection crosswalk. [Markowski2024](https://www.nature.com/articles/s41467-023-44514-2), Results, Figures 1–2 and RNA-sequencing Methods; DOI10.1038/s41467-023-44514-2. [Original source workbook](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-023-44514-2/MediaObjects/41467_2023_44514_MOESM4_ESM.xlsx), “Supplemental Figure 1.”

An explicitly provisional join of GEO `subjectid` to the source workbook's `Pt #` gives 15 candidate matches. Direct numerical equality fails for all 15 because the fields use fraction versus percentage conventions. Multiplying the GEO change by100 gives 14/15 agreements within0.51 percentage points (a rounding check, not a biological threshold). Independent XML/Decimal review identifies the remaining difference as 352% versus353%; no source-supported correction is established. Numeric agreement alone does not prove an authoritative clinical-ID map, response confirmation or final-regimen timing. No patient IDs were reassigned by searching for a matching response value.

Baseline GEO flags remain PSA50 YES7/NO8 and radiographic YES4/NO11. These are catalogue field counts, not a newly validated endpoint. The source-based timing evidence makes it unsafe to promote them to final-regimen labels. A final-regimen analysis requires an explicit source-linked endpoint table; otherwise the proposed final-regimen branch remains unavailable. BAT-only characterization would be a separately recorded design choice, not a silent replacement.

## Evidence ledger

| ID | Question | Answer class and evidence | Effect / status |
|---|---|---|---|
| A-COMBAT-01 | Do actual matrix columns join to GEO? | Verified fact: exact 30-title set equality, no duplicate titles, 15 paired visit units; `A_COMBAT_admission/audit_summary.json`, expression and join fields | Header/feature-presence gate closed; biological eligibility not closed |
| A-COMBAT-02 | Can this workbook be scored directly as pmeTPM? | Verified metadata contradiction plus arithmetic evidence; inference that expected counts are likely, exact export unknown | Reject direct TPM admission; do not fabricate a conversion |
| A-COMBAT-03 | Do public flags prove final BAT/nivolumab response? | Unknown; JCI locates original BAT response at C4D1, trial starts nivolumab then | Final-regimen mapping remains gated |
| A-COMBAT-04 | Is the clinical subject join authoritative? | Candidate map only; 14/15 rounded PSA-change agreement, one unresolved | Do not inherit final endpoint labels from numeric-ID resemblance |
| A-COMBAT-05 | Is prostate ICI clinical validation now established? | No: assay-scale and clinical-join gates remain; sequential exposure and tumour-enriched sampling limit interpretation | Retain conditional branch; no performance calculation or independent-ICI claim |

Source/retrieval dates and hashes are in `A_COMBAT_admission/retrieval.json`, the retained outer `workbook_initial.json` and `A_COMBAT_admission/audit_summary.json`. Original GEO samples-only metadata is the prior audit's 12 April2023 source snapshot; current series metadata was retrieved during this check. The source workbook is the prior hash-verified original publication download.

## Artifacts, reproduction and exposure

The inspected expression workbook is 4,202,331 bytes, SHA256 `8c60d0b0e9c9be30bd04d5e54a3cad9d129f4373aad9ea46348429a6baf7627f`. [Original GEO file](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE229nnn/GSE229555/suppl/GSE229555_FinalExpectedCounts_COMBAT_RNAseq_MatchedPairs.xlsx). Public retrieval does not establish permission for redistribution; retain it outside Git/Notion. Publish only small aggregate evidence and retrieval instructions.

Scripts are `planning/audit_combat_admission.py`, `planning/inspect_combat_workbook.py` and `planning/verify_combat_join.py`. They are audit helpers, not production workflow. The first two refuse to overwrite downloaded inputs. The verifier reuses those files and the original samples-only metadata/clinical workbook and writes the aggregate audit summary. Runtime: bundled Python with openpyxl, no dependency installation. No expression normalization, immune score, drug effect, classifier or clinical association was computed. Reading original articles exposed their published findings; this is not an untouched prospective test-set claim. The local initial preview contains a few unrelated expression rows and stays outside Git.

Independent review is complete in `A_COMBAT_admission/REVIEW.md`; its subset and clinical-discrepancy findings are incorporated. The canonical A DATA/TRANSPORT/PREREGISTRATION documents now retain the exact sample join, scale contradiction and outcome timing gate, with both proposed primaries preserved. A TRANSPORT also reflects the prior CPC correction: that portal field is SNP-call agreement, not purity.
