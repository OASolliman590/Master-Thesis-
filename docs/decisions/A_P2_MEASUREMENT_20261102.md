# A-P2 measurement compatibility check, 2 Nov 2026

Section 3 of the signed `specs/amendments/2026-11-02-paper-a-validation/AMENDMENT.md` requires a TPM-compatible representation and complete coverage of the four learner panels (46 genes) plus GZMA and PRF1 for CYT. This records what each candidate cohort actually holds. The checks covered scale and gene identifiers only; no expression-response relationship was examined.

| Cohort | What the loaded file holds | Panel coverage | A-P2 status |
| --- | --- | --- | --- |
| liu2019 | TPM (each sample sums to about 1,000,000 over 20,838 genes) | complete with aliases (TMEM173, RIGI) | **eligible** |
| riaz_gse91061 | author FPKM, Entrez gene IDs (22,187) | needs an Entrez-to-symbol map | **eligible** via FPKM→TPM over the full feature set |
| hugo_gse78220 | author FPKM (25,263 genes) | complete with aliases (MB21D1, TMEM173, DDX58) | **eligible** via FPKM→TPM |
| vanallen2015 | FPKM-like values, Entrez gene IDs (21,935) | needs an Entrez-to-symbol map | **eligible** via FPKM→TPM; "RPKM/FPKM unclear" stays a caveat |
| kim2018 | recount3 approximate counts, GENCODE v26 (63,856 genes) | Ensembl IDs; mapped through the pinned GENCODE v26 annotation | **eligible** via recount3 counts ÷ gene length (annotation `human.gene_sums.G026.gtf.gz` already pinned) |
| gide2019 | recount3 approximate counts, GENCODE v26, for 60 PRE runs; iAtlas log2 upper-quartile for all 73 (biology only) | complete | **eligible for 60 patients**: the run-to-patient crosswalk was accepted on 2 Nov after an outcome-blind sex check (see below); 13 PRE runs stay unlinked and use iAtlas for biology only |
| braun2020 | log2 upper-quartile, ComBat-corrected (Supplementary Table S4A is the only expression table; raw RNA is controlled-access) | complete with aliases | **not eligible**: no TPM route; stays in A-BIO |
| gse176307 | **official Salmon TPM** (`GSE176307_salmon_tpm_gene.matrix.tsv.gz`, GEO 2023 replacement file, pinned in `tools/a_dav/fetch_plans/gse176307_tpm.json`): 58,387 genes × 92 assays, every sample sums to exactly 1,000,000, no negatives. The previously loaded file is the log2(1+x) median-centred matrix | complete, with aliases MB21D1 and TMEM173; each gene appears once | **eligible** (found by Astra's rescue review): the 92 TPM columns are 90 keyed assays plus 2 unkeyed columns (excluded). The 90 keyed assays belong to 89 key patients (one has two assays, resolved by the lowest RS ID). 88 of the 89 key patients match a GEO title (key `BACI###` = last token of the title); the one key patient without a GEO record is not used |
| gse145996 | FPKM, merged loci (HLA-A with HLA-G/H; HLA-B with HLA-C), TAP1 and PSMB8 absent, GZMB duplicated | incomplete antigen-presentation panel | **not eligible** (complete coverage required); stays in A-BIO |

## Result
- **Eligible now: 6 study families, 4 melanoma, 1 gastric and 1 bladder:** Liu, Riaz, Hugo, Van Allen, Kim and GSE176307 (via its Salmon TPM file), with 100 responders and 248 non-responders (ORR-evaluable baseline), plus Gide's 60 linked patients (class counts to be taken by the loader).
- The amendment's minimums are met: at least 3 families, and every leave-one-out training set has at least 20 responders and 20 non-responders.
- **Gide** joins as a seventh family (melanoma, 60 patients) through the accepted crosswalk. Seven families in all.
- **Consequence:** bladder is now represented in training (GSE176307), so IMvigor210 tests transfer to a new bladder study rather than to an unseen cancer. Kidney is still absent from primary training; Braun enters only the cohort-adaptive sensitivity (see the addendum in the validation amendment).

## Needed before scoring (implementation, frozen tables)
0. Loader branches for the GSE176307 TPM file and the Gide recount3 crosswalk (60 PRE runs). For GSE176307: a branch, joined through the name key, with the duplicate-assay rule frozen before any outcome look.
1. A pinned Entrez-to-symbol map for Riaz and Van Allen (for example NCBI `Homo_sapiens.gene_info` at a fixed date).
2. A frozen alias table: MB21D1→CGAS, TMEM173→STING1, DDX58↔RIGI. Any other panel alias needs a recorded entry.
3. FPKM→TPM as TPM_g = 10^6 × FPKM_g / Σ_h FPKM_h over each sample's complete feature set (`specs/A/ASSAY_PROCESSING_CONTRACT.md`).
4. recount3 counts→TPM using the G026 `bp_length`, as recount3 documents.

## Gide crosswalk check (2 Nov 2026; user decision "verify, then accept")
- The title-rule crosswalk links 60 of 73 PRE runs to cBioPortal patients. Each linked run's sex was inferred from its own recount3 counts (summed CPM of RPS4Y1, DDX3Y, KDM5D, UTY, EIF1AY and ZFY; XIST recorded) and compared with cBioPortal SEX. No response or outcome field was used.
- **Result: 60 of 60 agree** (21 female, 39 male). Recorded women have Y-gene expression of 0.2-6.5 CPM, recorded men 214-2,961 CPM, a clean separation. Three male runs also show high XIST, noted as a sample caveat.
- **Accepted** for the 60 PRE runs. Limitation: a sex check cannot detect a swap between two patients of the same sex. The 14 matched EDT (on-treatment) runs are not accepted here; they belong to A.1.

## Built inputs (2 Nov 2026, `python -m tools.a_p2 build`)
`tools/a_p2` writes `.scratch/runtime/a_p2/inputs/` (features.tsv, coverage.tsv, manifest.json; git-ignored). It does no model fitting and no feature-by-response summaries.

| Cohort | Final N | R | NR | TPM route |
| --- | ---: | ---: | ---: | --- |
| liu2019 | 102 | 41 | 61 | author TPM |
| gse176307 | 87 | 16 | 71 | official Salmon TPM (1 unknown ORR excluded) |
| gide2019 | 60 | 39 | 21 | recount3 counts → TPM (accepted crosswalk; 13 without a join excluded) |
| riaz_gse91061 | 49 | 10 | 39 | author FPKM → TPM |
| kim2018 | 45 | 12 | 33 | recount3 counts → TPM |
| vanallen2015 | 39 | 7 | 32 | author FPKM-like → TPM (study-level pretreatment, PMC5054517; 1 unknown ORR excluded) |
| hugo_gse78220 | 26 | 14 | 12 | author FPKM → TPM |
| **Total** | **408** | **139** | **269** | 7 families: 5 melanoma, 1 gastric, 1 bladder |

- recount3 gene length: column 6 (GTF score) of the pinned G026 gene annotation, which is recount3's bp_length. The TPM denominator uses primary-assembly genes only (5,637 alternate or unplaced rows dropped per cohort). Every converted sample sums to 1,000,000.
- No missing or negative feature values and no duplicate patients; 40 tests pass.
