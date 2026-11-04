# Standard bulk analysis

`tools.a_bulk` runs one bulk expression dataset at a time. It passes TSV inputs to the pinned R project through `tools.r_bridge`; it does not combine expression matrices across studies.

## CLI

```text
python -m tools.a_bulk qc --cohort liu2019 --paper A
python -m tools.a_bulk pca --cohort liu2019 --paper A
python -m tools.a_bulk panels --cohort liu2019 --paper A
```

Response-associated stages (`de`, `gsea`, `all`) require `--allow-outcomes` for real cohorts. PCA includes response colouring only when that flag is set. While the signed numerical register and Hallmark membership remain unfrozen, run only outcome-free stages on real cohorts; outcome stages are exercised on synthetic fixtures. GSEA accepts a local GMT file, requires `--gene-set-id-type` (`symbol` or `entrez`), and never downloads or selects a gene-set collection. The declared GMT namespace must match the DE ranking namespace. Enrichment stops if fewer than 10 unique ranking identifiers overlap GMT membership by default; `--min-gene-set-overlap` can set a different predeclared floor. `membership_overlap.tsv` reports overlap counts and fractions per gene set.

The results root is selected by `--results`, then `THESIS_RESULTS`, then a `results/` sibling beside the repository. The dataset layout is:

```text
<results>/<A|B>/<dataset>/{qc,pca,de,gsea,scores}/
```

Each stage has a module `manifest.json` plus its `bridge/` R outputs and R manifest. Hashed sample-metadata inputs and patient-level tables stay under that dataset's results folder. The dataset-root `summary.json` contains aggregate counts, QC, outlier and PCA variance summaries without sample-level rows. Its provenance uses relative script/manifest identifiers and hashes only; imported stage summaries are checked against the current dataset identity and input hashes. Mismatched summaries are excluded with a reason, and outcome-stage summaries are not read by an outcome-free action without the guard.

## Analysis contract

- QC reports count library sizes or non-count column totals and medians, detected features, zero/missing fractions, sample correlations, and descriptive outlier flags. PC1, PC2, PC1/PC2 distance, and count log2 library depth use median plus three scaled MADs (1.4826 × MAD) with a near-zero MAD tolerance; non-count totals and medians are not treated as library depth. Flags never exclude samples.
- PCA uses blind DESeq2 VST for integer counts and the dataset's declared log scale otherwise. Linear inputs are transformed with `log2(x + 1)`. The default top-variance feature count is 2,000. PCA covariate plots are emitted for recorded batch, platform, biopsy site and drug class; response is conditional on `--allow-outcomes`.
- DE uses DESeq2 for declared linear integer counts, otherwise limma-trend. Linear non-count inputs use `log2(x + 1)`; declared log2 and log2p1 inputs stay on their supplied scale. An `other` transform is retained for outcome-free QC/PCA but DE fails closed because a log2 fold-change scale cannot be established.
- DE designs include a recorded within-study batch only when it has at least two levels and is estimable with response. Excluded endpoint rows and reason counts are recorded. DESeq2 fold changes are unshrunk; both engines report standard errors, statistics, p-values and BH q-values.
- fgsea ranks by the DE statistic. Its GMT membership is an explicit file input; Hallmark membership is not frozen here.
- Panel scores use the signed 11 panel memberships from the shared scoring registry and require complete panel coverage. Counts use log2(TPM + 1) when a complete gene-length TPM route is available, otherwise log2(CPM + 1) using the full count library. Log-scale data stay on their source scale. CYT is `sqrt(TPM_GZMA × TPM_PRF1)` only for verified linear TPM with both genes present; otherwise it is reported unavailable. Spearman correlations are computed within that dataset only.

Paper B can use `BulkDataset` or `adapt_view()` with a cohort-view-like object. The adapter must provide an expression TSV with feature IDs in column one and sample IDs in the remaining columns, one aligned clinical row per sample, typed platform/unit/transform/feature-ID metadata, a declared DE engine, endpoint families, and a sample identity field. Its source/representation and specimen gates remain owned by the future B loader.

## Method references

- Love MI, Huber W, Anders S. Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. *Genome Biology*. 2014;15:550. [doi:10.1186/s13059-014-0550-8](https://doi.org/10.1186/s13059-014-0550-8). Official package documentation: [DESeq2 on Bioconductor](https://bioconductor.org/packages/DESeq2/).
- Ritchie ME, Phipson B, Wu D, et al. limma powers differential expression analyses for RNA-sequencing and microarray studies. *Nucleic Acids Research*. 2015;43:e47. [doi:10.1093/nar/gkv007](https://doi.org/10.1093/nar/gkv007). Official package documentation: [limma on Bioconductor](https://bioconductor.org/packages/limma/).
- Sergushichev A. An algorithm for fast preranked gene set enrichment analysis using cumulative statistic calculation. *bioRxiv*. 2016. [doi:10.1101/060012](https://doi.org/10.1101/060012). Official package documentation: [fgsea on Bioconductor](https://bioconductor.org/packages/fgsea/).
