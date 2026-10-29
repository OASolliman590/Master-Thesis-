# Signature gene sets: source verification (2026-10-28)

Draft JSON files are in `tools/a_analysis/gene_sets/drafts/`. That directory did not exist before this work. The existing gene-set files are in `tools/a_analysis/genes/` (`cyt.json`, `cd274.json`, `cxcl9_cd8a.json`), and the drafts follow their schema: `id`, `version`, `source_pmid`, `source_doi`, `genes[{symbol, entrez}]`. The drafts add these fields: `source_pmcid`, `verification_status`, `scoring_method`, `source_location`, and notes.

No source gives NCBI Entrez Gene IDs. Every `entrez` field is `null` with `entrez_status: "to be mapped"`. Gene symbols are copied as printed in the source. Current-HGNC checks are still pending. Where the source prints a protein alias, the alias is kept in `symbol_as_printed`.

Retrieval methods:
- NCBI efetch PMC full-text XML, where PMC has a body.
- PubMed MCP for IDs and metadata.
- WebFetch of the PMC HTML page and jci.org for Ayers 2017, because its PMC XML has no body text.

No supplementary data files (xlsx) were downloaded.

## Summary table

| Signature | Genes confirmed / published size | Source (PMID; DOI; PMCID) | Exact location | Scoring (original paper) | Status |
|---|---|---|---|---|---|
| IFN-γ 6-gene | 0 / 6 | Ayers 2017 JCI (28650338; 10.1172/JCI91190; PMC5531419) | Table 2, image only | Mean of log10 normalized expression | UNVERIFIED |
| Expanded immune 18-gene | 0 / 18 | Ayers 2017 (as above) | Table 2, image only | Mean of log10 normalized expression | UNVERIFIED |
| T cell-inflamed GEP | 18 / 18 | Cristescu 2018 Science (30309915; 10.1126/science.aar3593; PMC6718162) | Materials and methods, "Gene expression (RNA) profiling: NanoString methodology" | Weighted sum of housekeeping-normalized log10 expression; weights not published in text | VERIFIED (membership); weights null |
| CYT | 2 / 2 (GZMA, PRF1) | Rooney 2015 Cell (25594174; 10.1016/j.cell.2014.12.033; PMC4856474) | Experimental Procedures, "Cytolytic activity and other cell type-specific signatures"; Fig. 1A legend | Geometric mean of TPM (+0.01 offset) | VERIFIED |
| MHC class II (HLA, 13 genes) | 13 / 13 | Liu 2019 Nat Med (31792460; 10.1038/s41591-019-0654-5; PMC6898788) | Methods, "GSEA and ssGSEA" | ssGSEA, rank normalization; median split | VERIFIED |
| Pan-F-TBRS (stromal) | 0 / not stated in text | Mariathasan 2018 Nature (29443960; 10.1038/nature25501; PMC6028240) | Supplementary Table S8 (xlsx, not read) | "Average expression"; details in Supplementary Methods (not reached) | UNVERIFIED |
| IMPRES | 9 of 15 pairs (direction for 5); 9 genes | Auslander 2018 Nat Med (30127394; 10.1038/s41591-018-0157-9; PMC6693632) | Results (Fig. 3C paragraph); full list in Supp. Table 2 (docx, 403) and Fig. 3C (image) | Count of satisfied pairs, 0-15; rescaled when genes are missing | UNVERIFIED |
| TIDE (reference needs only) | 5 CTL markers (CD8A, CD8B, GZMA, GZMB, PRF1) | Jiang 2018 Nat Med (30127393; 10.1038/s41591-018-0136-1; PMC6487502) | Results and Methods, "Statistical analysis", "Performance comparison on predicting ICB response" | Pearson correlation with the dysfunction signature (CTL-high) or exclusion signature (CTL-low), scaled by TCGA SD | VERIFIED (requirements) |

## Per-signature notes

**IFN-γ 6-gene and expanded immune 18-gene (Ayers 2017).** The final gene lists appear only in Table 2, "IFN-γ and expanded immune gene signatures". PMC and jci.org both serve that table as a JPEG; neither has table text. The text does name the parent sets:
- **IFN-γ 6-gene.** Its parent is the 10-gene "preliminary IFN-γ" set: IFNG, STAT1, CCR5, CXCL9, CXCL10, CXCL11, IDO1, PRF1, GZMA, HLA-DRA.
- **Expanded immune 18-gene.** Its parent is the 28-gene preliminary set. Only 16 of its 28 genes are named by symbol.

Both parent lists are stored as `parent_set` with a caution flag. They must not be used as the final signatures. To close this gap, read the Table 2 image by eye.

**T cell-inflamed GEP.** Membership is quoted verbatim from Cristescu 2018 (PMC XML, paragraph P38):
CCL5, CD27, CD274, CD276, CD8A, CMKLR1, CXCL9, CXCR6, HLA-DQA1, HLA-DRB1, HLA-E, IDO1, LAG3, NKG7, PDCD1LG2, PSMB10, STAT1, TIGIT.

Ayers 2017 shows the GEP genes only in the Figure 4 heatmap image. In its text it names only CD276, as the one gene that is not positively associated with outcome. Ayers states that the weights are penalized logistic regression coefficients but does not print them. `weights` is therefore null. The Cristescu supplementary PDF may contain the weights; it was not reachable because PMC showed a browser check.

**CYT.** Confirms the existing `genes/cyt.json`. That file cites PMID 37627121, a secondary paper, rather than Rooney 2015.

**MHC class II: choice.** Liu 2019 was picked over the two suggested options:
- **Ayers 2017** has no standalone MHC-II signature.
- **Johnson 2016** (PMID 26822383, PMC4740184) defines MHC-II status by HLA-DR immunohistochemistry (>5% of SOX10+ tumour membranes). Its only transcript list is a 159-gene CCLE differential set held in a supplementary data file.

Liu 2019 is an anti-PD-1 melanoma cohort paper that prints a fixed 13-gene HLA class II list in Methods. It cites both Johnson 2016 and Rodig 2018 for the MHC-II rationale, and it reports MHC-II expression as its best transcriptomic predictor.

**Stromal score.** Neither option has a gene list in accessible text:
- **Pan-F-TBRS:** membership is in Supplementary Table S8 (xlsx data file). The scoring method is in the Supplementary Information PDF; PMC showed a browser check and nature.com redirected to a login.
- **IPRES (Hugo 2016, PMID 26997480, PMC4808437):** a co-enrichment of 26 gene sets, scored by GSVA and taken as the average z-score with a 0.35 cutoff. The set names are in Figure 2D and Table S2 (xlsx). The text names only the four sets that were excluded in the cross-cohort comparison: JAEGER_METASTASIS_UP, YE_METASTATIC_LIVER_CANCER, KARAKAS_TGFB1_SIGNALING, JEON_SMAD6_TARGETS_DN.

Pan-F-TBRS was drafted because it is a single gene list. It is marked UNVERIFIED with `genes: []`.

**IMPRES.** The text confirms these pairs:
- **Direction stated** (the first gene higher means better response): CD40>PD-1, CD40>PD-L1, CD40>CD80, CD40>CD28, CD27>PD-1.
- **Direction not stated:** CD28/CD86, PD1/OX40L, CD86/OX40L, CD86/CD200.

HVEM, CD276, TIM-3 and VISTA are named as IMPRES nodes, but their partners are not given. The remaining 6 pairs are in Supp. Table 2 and Figure 3C, which were not readable here. Mapping aliases to HGNC symbols still needs checking: PD-1 to PDCD1, PDL-1 to CD274, OX40L to TNFSF4.

There is a publisher correction (PMID 30333558, PMC9639231). It fixes only a GEO URL (GSE100351 to GSE115821).

**TIDE.** The score needs these external references, all from the authors (tide.dfci.harvard.edu):
- **Dysfunction signature:** genome-wide, built from Cox-PH interaction z-scores averaged over 5 ICB-naive cohorts.
- **Exclusion signature:** genome-wide, built from GEO profiles of CAFs, MDSCs and M2 TAMs.
- **Scaling constants:** TCGA standard deviations used to normalize the two correlations.

Input data are quantile-normalized, then mean-centred per gene. CTL-high means all 5 CTL markers are above the dataset average.

## Discrepancies between papers

1. **Two different 18-gene sets.** The "expanded immune 18-gene" signature and the "18-gene T cell-inflamed GEP" are not the same set. Ayers says so explicitly in Methods, "Statistics". Do not merge them.
2. **GEP gene names.** Cristescu prints "TIGTT", a typo for TIGIT. Ayers names no GEP genes in text except CD276.
3. **GEP and expanded-immune scoring.** Ayers scores the expanded immune set as an unweighted mean of quantile-normalized log10 values. The GEP is a weighted sum of housekeeping-normalized log10 values with 11 housekeeping genes, in both Ayers and Cristescu.
4. **CYT across papers.** Rooney defines CYT as the geometric mean in TPM. TIDE's CTL level is a different measure: the arithmetic average of 5 markers (CD8A, CD8B, GZMA, GZMB, PRF1).
5. **Typo in Liu 2019.** The Results text lists "HLA-DOB and HLA-DOB". The Methods list (HLA-DOA and HLA-DOB) is the authoritative membership.
6. **Existing `genes/cyt.json`.** It cites a secondary source (PMID 37627121), not Rooney 2015.

## Open items

- Read the Ayers Table 2 image by eye to get the 6-gene and 18-gene lists.
- Get IMPRES Supp. Table 2 and Pan-F-TBRS Supp. Table S8 if downloading those files is approved.
- Map all symbols to Entrez IDs with an HGNC/NCBI lookup. In particular, check that CMKLR1 is still the current HGNC symbol.
