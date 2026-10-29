# Riaz GSE91061 × A_BASELINE_BIO: QC, expression, binding, timing and overlap decisions

**Status:** decided by the user in chat on 26 Oct 2026 (grilling round, Q1–Q5). These decisions apply only to this branch. They do not admit the cohort, sign the worksheet or authorize analysis. The frozen specs are unchanged.

1. **QC rules.** `docs/research/A_DAV_RIAZ_QC_PROPOSAL_20261026.md` is approved as written:
   - Identity is checked at two levels: the full 109-column header, then the 51 selected `Pre` columns, with no `On` columns.
   - Values must be finite and non-negative, and a missing value must be distinguishable from a measured zero.
   - Profiles that look like duplicates are quarantined, not removed.
   - QC is done without looking at response labels.
   - There are no numeric thresholds.
   - The paper's Pt3 PCA outlier and the four exclusions in `TableS6.A.R` are kept as historical flags only. They are not automatic exclusions.
2. **Expression representation.** The primary representation is NCBI GRCh38.p13 TPM (`GSE91061_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz` plus the GRCh38.p13 annotation). This choice is conditional:
   - If V3 cannot tie the unit, transform, gene grain and annotation to documented NCBI processing, the branch falls back automatically to the author's hg19 FPKM, and the user is told.
   - Whichever representation is not primary stays pinned as a separate sensitivity representation.
   - Nothing converts between the two.
3. **Treatment–response binding.** Each baseline patient is bound to one index episode: nivolumab monotherapy in trial CA209-038.
   - Author BOR is the response assessed in that episode.
   - The author Cohort value (NIV3-NAIVE / NIV3-PROG) becomes the `prior_ici` (prior ipilimumab) attribute, not a separate episode.
   - Evidence comes from the article's methods and the author clinical table at commit `137111c`.
   - The binding becomes VERIFIED only when the named reviewer signs.
4. **Timing.** The index treatment is the start of nivolumab. A `Pre` specimen counts as baseline because the source labels it pretreatment. The collection day is recorded as not reported and is never inferred from the protocol window.
5. **Overlap and prior use.**
   - Riaz vs Hugo: no shared GSM, SRA or BioSample identifiers. Whether patients at the site level are independent is UNKNOWN. This does not block single-cohort A_BASELINE_BIO, but it must be resolved before any joint train/test split.
   - Prior project exposure is METADATA_ONLY: no expression results have been seen.

**Signer.** The user (thesis author) or the named supervisor signs under the V7 public-reviewer amendment. The name and role have not been provided yet. Do not fill in a name until the user supplies it with the actual sign-off.
