# Primary evidence and implementation documentation

## Source discipline

These references support the specified methods and known-study boundaries. They are not an admitted cohort roster, complete systematic search or verification of all source-specific patient joins. The approved user handoff and pinned repository evidence govern architectural decisions. Source-dependent implementation/version/weights/assay settings still require the admission and numerical-freeze records. Public URLs are locators; complete downloaded objects require their own version/hash/terms.

| ID | Original source or official documentation | Use in this kit |
|---|---|---|
| S01 | Rooney et al. Molecular and genetic properties of tumors associated with local immune cytolytic activity. Cell 2015. https://doi.org/10.1016/j.cell.2014.12.033 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC4856474/ | CYT reference; the specific TPM/no-pseudocount contract is the project-selected implementation, not a claim that every published assay uses that identical preprocessing |
| S02 | Ayers et al. IFN-gamma-related mRNA profile predicts clinical response to PD-1 blockade. JCI 2017. https://www.jci.org/articles/view/91190 | Exact published GEP and original cohort/model context; source-correct implementation required |
| S03 | Jiang et al. Signatures of T cell dysfunction and exclusion predict cancer immunotherapy response. Nature Medicine 2018. https://www.nature.com/articles/s41591-018-0136-1 | TIDE original method; no homemade approximation |
| S04 | Generalizable AI predicts immunotherapy outcomes across cancers and treatments. Nature Medicine 2026. https://www.nature.com/articles/s41591-026-04502-7 | COMPASS closest-study and model/source-overlap audit; primary article inspected 15 October 2026 |
| S05 | Sun et al. Systematic Assessment of Transcriptomic Biomarkers for Immune Checkpoint Blockade Response in Cancer Immunotherapy. Cancers 2021. https://doi.org/10.3390/cancers13071639 | Existing benchmark landscape; not a new contribution merely to compare scores |
| S06 | Riaz et al. Tumor and Microenvironment Evolution during Immunotherapy with Nivolumab. Cell 2017. https://doi.org/10.1016/j.cell.2017.09.028 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC5685550/ | Original longitudinal context and prior-ipilimumab distinction; patient/window admission remains separate |
| S07 | Love et al. Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. Genome Biology 2014. https://doi.org/10.1186/s13059-014-0550-8 ; https://bioconductor.org/packages/DESeq2/ | Count-aware model and documented import/offset requirements |
| S08 | Ritchie et al. limma powers differential expression analyses for RNA-sequencing and microarray studies. NAR 2015. https://doi.org/10.1093/nar/gkv007 ; https://bioconductor.org/packages/limma/ | Source-appropriate linear models and contrasts |
| S09 | variancePartition official package and dream documentation. https://bioconductor.org/packages/release/bioc/html/variancePartition.html ; https://gabrielhoffman.github.io/variancePartition/ | Qualified repeated-measures implementation, weights and rank/correlation requirements |
| S10 | scikit-learn LogisticRegression official API. https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html | Pin actual compatible elastic-net/SAGA API; do not assume a historical parameter signature |
| S11 | metafor official reference. https://wviechtb.github.io/metafor/reference/rma.uni.html | REML and Knapp-Hartung implementation proposal; exact modification, version and small-k behavior need statistical freeze |
| S12 | JSON Schema Draft 2020-12. https://json-schema.org/draft/2020-12 | Record schemas and offline reference-resolution contract; not relational or clinical validation |
| S13 | NCBI GEO official repository. https://www.ncbi.nlm.nih.gov/geo/ | Original accession and object metadata; catalogue aliases are not independent cohorts |

## Verified repository lineage

The acquisition review head inspected was 58ac943acbe8c981c7c8c269103c602b4425bd50, draft PR #9. Its original exported artifact came from commit 293130281db0a827cda0e975aec3b823403df68f; artifact 11966788962 SHA-256 is 17b987192b2ea8ac080ae748bcb58618c1a181efb9a88d672756a4b8b12fa169. Full original A and DAV subtrees are preserved under reference. Prior source-admission reports and historical counts remain historical/source-candidate evidence, not new admission.

## Explicit remaining literature gaps

The exact requested Kang benchmark and Luo endpoint-definition references must be resolved from the preserved bibliography/original publications before attributing specific results to them. The bounded current update did not establish a complete 2025–2026 longitudinal/multi-omics census or comparator implementation audit. These remain named methods/search tickets, not fabricated citations. No first-study claim is authorized. The final A1 manuscript gate requires a fresh complete closest-study comparison; source acquisition and contract implementation need not wait for a positive novelty verdict.
