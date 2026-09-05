# Independent COMBAT source/format review

Reviewed 6 September 2026. Read the three audit scripts and root's `REPORT.md`; independently parsed the retained XLSX ZIP/XML with the Python standard library and Decimal arithmetic, rather than executing the author's openpyxl audit helper. No expression matrices were downloaded again, altered, normalized or scored. Original article pages and official RSEM documentation were also inspected.

## Conclusion and material findings

The reported identifier and assay-scale calculations are correct. Direct pmeTPM admission remains unsupported. Candidate clinical-ID equality and approximate numerical agreement do not establish final-regimen response labels.

1. **Add the published RNA subset gate.** JCI Figure 3 uses 15 paired RNA subjects, whereas the subsequent COMBAT publication reports 12 paired RNA subjects (six responders and six nonresponders). The actual public workbook contains 15. The latter publication says all 12 received both treatments, but all six responders had responded before nivolumab. Thus neither membership of the published 12 nor final-regimen flags can be assigned to the public 15 without a source-linked selection crosswalk. The published eligibility explanation is not a sample-level exclusion manifest. [COMBAT results, paired RNA analysis](https://www.nature.com/articles/s41467-023-44514-2), Figure 4 and preceding Results paragraphs.

2. **Name, but do not repair, the clinical discrepancy.** Under the expressly provisional `subjectid` versus `Pt #` join, subject 20 has GEO PSA change `3.52` at both visits, hence 352%, whereas the original source workbook's `Supplemental Figure 1!B34` is 353% (`A34=20`). The difference is one percentage point and fails the 0.51-point rounding tolerance. No inspected source explains whether this is rounding from different upstream precision, transcription, an updated calculation, or another cause. Do not choose one explanation or overwrite either value. Subject 1 is the sole half-point difference: -88% in GEO versus -88.5% in the workbook. Thirteen matches are exact; one differs by 0.5 and one by 1 percentage point. [Original publication source workbook](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-023-44514-2/MediaObjects/41467_2023_44514_MOESM4_ESM.xlsx), cited worksheet; [GSE229555](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE229555).

These are additions to the evidence/gates, not a recommendation to select or change an endpoint.

## Independent numerical checks

| Property | Independent result | Agreement |
|---|---:|---|
| Gene rows / distinct gene labels | 26,467 / 26,467 | Exact |
| Expression columns | 30 | Exact |
| Matrix headers versus GEO titles | Exact set equality; 30 distinct titles | Exact |
| Subjects / complete Pretx-C4D1 pairs | 15 / 15 | Exact |
| Invalid / negative entries | 0 / 0 | Exact |
| Noninteger entries | 64,612 | Exact |
| Minimum / maximum column sum | 1,306,624.91 / 40,876,909.09 | Exact to source precision |
| Columns exceeding one million | 30 | Exact |
| Baseline PSA50 catalogue flags | YES 7 / NO 8 | Exact |
| Baseline radiographic catalogue flags | YES 4 / NO 11 | Exact |
| Candidate clinical-ID matches | 15 / 15 | Exact, not authoritative |
| Candidate fraction-times-100 agreement within 0.51 percentage points | 14 / 15 | Exact |

These are format, numerical-scale and metadata comparisons, not biological effect estimates. The source feature-presence report is not evidence that any immune score is valid on this assay scale.

## Assay interpretation

Official RSEM documentation distinguishes `expected_count`, `TPM`, and posterior-mean `pme_TPM`. TPM totals one million across transcripts; gene abundance sums the constituent transcript abundances. A nonduplicated subset of nonnegative gene TPM values cannot exceed the complete total. Therefore the observed totals contradict an unmodified standard gene-level TPM/pmeTPM table, far beyond ordinary rounding error. This does **not** uniquely identify the actual values as counts. [RSEM output documentation](https://deweylab.github.io/RSEM/rsem-calculate-expression.html#output).

The GEO filename and worksheet identify expected counts; the sample metadata instead describes pmeTPM. The later article's RNAseq Methods explicitly describe RSEM gene read-count estimates followed by DESeq2 normalization and log2 transformation. This strengthens the proposed count interpretation while leaving the exact deposited export unknown. The workbook has no effective-length information. Scaling its columns to one million would not establish TPM; neither expected counts nor their normalization can silently replace a frozen TPM input contract. [COMBAT RNAseq Methods](https://www.nature.com/articles/s41467-023-44514-2); [GEO source workbook](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE229nnn/GSE229555/suppl/GSE229555_FinalExpectedCounts_COMBAT_RNAseq_MatchedPairs.xlsx).

## Timing and independence

JCI Figure 3 and its adjacent Results define response on C4D1 after three BAT cycles, using PSA decline or tumor-volume decrease. Its Methods place paired biopsies before treatment and after three BAT monotherapy cycles, before the concurrent nivolumab phase. Therefore the original BAT comparison cannot validate post-nivolumab response. [JCI162396, Figure 3 and Methods](https://www.jci.org/articles/view/162396).

The later publication describes the same trial, separates responses arising before and after nivolumab, and places the second biopsy before nivolumab begins. Its confirmation-based trial endpoint is not automatically equivalent to the GEO binary fields. Shared trial/publication aliases must not become independent cohorts. The 14/15 candidate numerical comparison supports further mapping investigation; it proves neither identity nor final endpoint timing. [COMBAT trial report](https://www.nature.com/articles/s41467-023-44514-2).

## Provenance and review limits

Independently recomputed input hashes agree with the supplied audit: expression workbook `8c60d0b0e9c9be30bd04d5e54a3cad9d129f4373aad9ea46348429a6baf7627f` (4,202,331 bytes); GEO sample metadata `6ffe453038d0e8e4faf6749f736c429b0f91fbdc03cd70c1ef1182aa3daea81e`; clinical source workbook `c8f0521cfb2c4ff8d70c873da4bdb75c129e99b63e89660a7b40fb21b46245a8`.

The scripts correctly label the clinical join provisional. Their openpyxl audit visits cell values and does not impute units or endpoints. The initial data-preview helper exposes a few matrix rows locally; no untouched test-set claim follows from this review. No authoritative 15-to-12 subset mapping, original sample-level quantification export, effective-length object, or final-regimen endpoint map was established. No canonical files, source workbooks, model code or clinical flags were edited.
