# A-P2 measurement compatibility check, 2 Nov 2026

Section 3 of the signed `specs/amendments/2026-11-02-paper-a-validation/AMENDMENT.md` requires a TPM-compatible representation and complete coverage of the four learner panels (46 genes) plus GZMA and PRF1 for CYT. This records what each candidate cohort actually holds. The checks covered scale and gene identifiers only; no expression-response relationship was examined.

| Cohort | What the loaded file holds | Panel coverage | A-P2 status |
| --- | --- | --- | --- |
| liu2019 | TPM (each sample sums to about 1,000,000 over 20,838 genes) | complete with aliases (TMEM173, RIGI) | **eligible** |
| riaz_gse91061 | author FPKM, Entrez gene IDs (22,187) | needs an Entrez-to-symbol map | **eligible** via FPKM→TPM over the full feature set |
| hugo_gse78220 | author FPKM (25,263 genes) | complete with aliases (MB21D1, TMEM173, DDX58) | **eligible** via FPKM→TPM |
| vanallen2015 | FPKM-like values, Entrez gene IDs (21,935) | needs an Entrez-to-symbol map | **eligible** via FPKM→TPM; "RPKM/FPKM unclear" stays a caveat |
| kim2018 | recount3 approximate counts, GENCODE v26 (63,856 genes) | Ensembl IDs; mapped through the pinned GENCODE v26 annotation | **eligible** via recount3 counts ÷ gene length (annotation `human.gene_sums.G026.gtf.gz` already pinned) |
| gide2019 | iAtlas log2 upper-quartile (signed 1 Nov rule) | complete | **not eligible as loaded**; eligible for the 60 recount3 runs only if the user accepts the proposed run-to-patient crosswalk (13 PRE runs still unlinked) |
| braun2020 | log2 upper-quartile, ComBat-corrected (Supplementary Table S4A is the only expression table; raw RNA is controlled-access) | complete with aliases | **not eligible**: no TPM route; stays in A-BIO |
| gse176307 | log2(1+x), median-centred (values about -2 to +2) | missing CGAS | **not eligible**; stays in A-BIO |
| gse145996 | FPKM, merged loci (HLA-A with HLA-G/H; HLA-B with HLA-C), TAP1 and PSMB8 absent, GZMB duplicated | incomplete antigen-presentation panel | **not eligible** (complete coverage required); stays in A-BIO |

## Result
- **Eligible now: 5 study families, 4 melanoma and 1 gastric:** Liu, Riaz, Hugo, Van Allen and Kim, with 84 responders and 177 non-responders (ORR-evaluable baseline).
- The amendment's minimums are met: at least 3 families, and every leave-one-out training set has at least 20 responders and 20 non-responders.
- **Gide** would add a sixth melanoma family (up to 60 patients) if its crosswalk is accepted.
- **Consequence:** kidney and bladder are not represented in A-P2 training. IMvigor210 (bladder) therefore tests transfer to a cancer absent from training, and the primary result must say so.

## Needed before scoring (implementation, frozen tables)
1. A pinned Entrez-to-symbol map for Riaz and Van Allen (for example NCBI `Homo_sapiens.gene_info` at a fixed date).
2. A frozen alias table: MB21D1→CGAS, TMEM173→STING1, DDX58↔RIGI. Any other panel alias needs a recorded entry.
3. FPKM→TPM as TPM_g = 10^6 × FPKM_g / Σ_h FPKM_h over each sample's complete feature set (`specs/A/ASSAY_PROCESSING_CONTRACT.md`).
4. recount3 counts→TPM using the G026 `bp_length`, as recount3 documents.
