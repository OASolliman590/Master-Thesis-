# Independent B TCGA cellularity source review

6 September 2026. Read `audit.py`, `summary.json`, `retrieval.json`, the retained 901,812-byte public TSV, and canonical `docs/research/B_paired_prostate/summary.json`. Independently joined hyphen-separated barcode components rather than running the audit script. No downloads, molecular matrices, outcome analyses or canonical edits.

## Result

No material counting or barcode-join error found. The retained result is **469 called primary sample-vials from 469 candidate cases**, not a final eligible analysis population and not proof of matching DNA/RNA/methylation aliquots.

| Check | Independently verified count |
|---|---:|
| Candidate cases / primary sample-vials | 497 / 501 |
| Case-linked source rows / unique cases | 486 / 485 |
| Case-linked primary / metastatic source rows | 485 / 1 |
| Matching candidate primary sample-vials | 485 |
| Matching called primary sample-vials / cases | 469 / 469 |
| Matching rows with blank status and all three relevant numeric fields blank | 16 |
| Candidate cases without any table row | 12 |
| Candidate cases without called primary row | 28 |
| Candidate sample-vials without any matching row / without called matching row | 16 / 32 |

All 486 case-linked rows satisfy the full aliquot-barcode syntax. The one extra sample is type `06`, excluded by the primary-vial intersection. The retained 485 vial-linked rows are all type `01`, unique by both case and vial. The 470 case-linked called rows include the metastatic row and must not be described as 470 called primary samples. Case-only matching happens to leave the same 469 unique called cases here because the metastatic case already has a called primary, but this does not justify using a case-only join in production.

## Field and missingness checks

All 469 called primary rows have finite numeric `purity`, `ploidy`, and `Cancer DNA fraction`. Ranges are 0.16–1.00, 1.79–4.39, and 0.16–1.00, respectively. **Purity and Cancer DNA fraction differ in the stored values of 215 of these rows** despite sharing a range; this is a schema/value distinction, not a biological association calculation. The proposed cellular-fraction covariate must use the correctly documented `purity` field, not silently substitute `Cancer DNA fraction`. Their biological distinction is covered in the original [ABSOLUTE methods](https://doi.org/10.1038/nbt.2203) and the separate `planning/next_evidence/B_cellularity_methods/REPORT.md`.

The 16 empty-status candidate rows also have blank purity, ploidy and Cancer DNA fraction. Blank status does not identify a specific ABSOLUTE failure class, low cellularity, zero purity, or absence of cancer. The 12 cases absent from this table are a separate missingness category. Neither missing category may be recoded as zero or imputed from unrelated samples.

The complete table contains 10,786 rows with statuses called 9,847; blank 144; legacy_call 558; snp_call 56; maf_call 146; legacy_maf_call 35. Its full aliquot-barcode subset contains 9,991 rows, 9,929 cases and 9,991 vials; 795 rows lack the checked full-barcode form. The summary's overall unique-case/vial counts describe that valid-form subset, not all possible alternative identifiers. This does not affect the PRAD candidate join, where every source row has a full barcode. An accepted-status policy for other cohorts is not automatically established by this PRAD audit.

## Provenance and remaining gate

The retained file SHA-256 matches `retrieval.json`: `f430a975433d82e0098d7405619d4f12a0c765fcd97e7d63cc9b1de7f2d763cd`. Candidate metadata SHA-256 matches the audit: `2a47ccd1777d85ff8c792a4f3360c4391c9171ca214395f499e0a7148a102777`. Source pointers identify the [GDC publication resource](https://gdc.cancer.gov/about-data/publications/PanCan-CellOfOrigin) and its [download object](https://api.gdc.cancer.gov/data/4f277128-f793-4354-a13d-30cc7fe9f6b5); no renewed source retrieval was performed.

Barcode hierarchy is handled correctly: three components identify the case, four the sample-vial, and additional components carry portion/analyte/plate/centre information. A full barcode on the purity row does not establish an exact molecular-aliquot join when the candidate manifest contains only case/vial identifiers. Preserve this linkage limit, source-call status and missingness in any later eligibility manifest. The qpure/ABSOLUTE comparability and specimen-policy gates remain separate from these successful source-field checks. B-P and B-R remain proposed.
