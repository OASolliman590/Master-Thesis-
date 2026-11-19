# quanTIseq pin for A-COMP (Paper A section 4.4; shared with Paper B)

Research note, read 19 Nov 2026. Docs and source were read only; nothing was installed or run, and no project data was touched. It answers SPEC_v2 section 11 item 5 ("Pin the quanTIseq version and options"). It checks the proposed N15 pin in `docs/decisions/A_COMP_N15_PROPOSED_20261106.md` and the constants in `tools/a_comp/core.py` against primary sources.

## Summary: recommended pin

| Item | Pin |
|---|---|
| Engine | Bioconductor `quantiseqr` **1.20.0**, Bioconductor **3.23** (release since 29 Apr 2026, R 4.6). Source commit `a948291c8d6b2a3262655ad2e4c52e1573ae55e4` ("bump ... prior to creation of RELEASE_3_23 branch", 28 Apr 2026). [Bioc page][bioc-rel], [release list][bioc-rel-ann], [commit][qr-commit] |
| Solver dependency | `limSolve` (`lsei`), imported by quantiseqr. [Bioc page][bioc-rel] |
| Reference files | Packaged `inst/extdata` at that commit. SHA-256 recomputed today **matches all five hashes** in the N15 proposal and `core.py` (TIL10_signature, TIL10_mRNA_scaling, TIL10_rmgenes, TIL10_TCGA_aberrant_immune_genes, HGNC_genenames_20170418). [extdata at commit][qr-extdata] |
| Optional wrapper | `immunedeconv` **2.1.4** (GitHub tag v2.1.4, 14 May 2026, commit `e625e6c2...`; not on Bioconductor). [releases][id-rel] |

Recommended call, direct to the engine:

```r
quantiseqr::run_quantiseq(
  expression_data  = tpm,          # genes x samples, non-log TPM, HGNC symbols as rownames
  signature_matrix = "TIL10",
  is_arraydata     = FALSE,
  is_tumordata     = TRUE,         # NOT the default in quantiseqr; must be explicit
  scale_mRNA       = TRUE,
  method           = "lsei",
  rm_genes         = "default",    # same as NULL for RNA-seq; explicit for the record
  return_se        = FALSE
)
```

Equivalent call through the wrapper (the form used in the N15 proposal):

```r
immunedeconv::deconvolute(tpm, "quantiseq",
  tumor = TRUE, arrays = FALSE, scale_mrna = TRUE, method = "lsei")
```

Both reach the same `quantiseqr::run_quantiseq` code. [immunedeconv wrapper source][id-src] The wrapper adds two things to keep in mind. First, it renames output rows: quanTIseq's `Other` becomes **`uncharacterized cell`**. [mapping xlsx][id-map] Second, its own `rmgenes` argument is a separate pre-filter and does not replace quantiseqr's `rm_genes`. My recommendation is to call `quantiseqr` directly, because that removes one dependency layer and the label remapping. If the N15 wrapper is kept, pass `method = "lsei"` explicitly and map `uncharacterized cell` back to `Other` (see "Still open").

Known defect in the pinned version: if lsei returns all-zero immune fractions for a sample, 1.20.0 divides by zero during mRNA rescaling and returns NaN. This was fixed in quantiseqr **1.21.3** (devel, 17 Nov 2026) and in the original pipeline (13–16 Nov 2026). [NEWS][qr-news], [quantiseqr fix][qr-commits], [original fix][orig-fix] For the pin, keep 1.20.0, which is the current release, and add a guard: any sample with a NaN fraction is reported and excluded, not imputed.

## 1. Implementations and versions

| Implementation | Version (read 19 Nov 2026) | Status | How it runs quanTIseq |
|---|---|---|---|
| `quantiseqr` (Bioconductor) | 1.20.0 in release 3.23; 1.21.3 in devel 3.24 | Maintained; authors Federico Marini (cre) and Francesca Finotello (quanTIseq first author) | Native R port of the deconvolution module: `run_quantiseq()`. [release page][bioc-rel], [devel page][bioc-dev] |
| `immunedeconv` (omnideconv, GitHub/bioconda) | 2.1.4 (14 May 2026); previous 2.1.3 (Oct 2023) | Maintained | `deconvolute(..., "quantiseq")` → `deconvolute_quantiseq()` → `quantiseqr::run_quantiseq(is_arraydata = arrays, is_tumordata = tumor, scale_mRNA = scale_mrna, ...)`; `deconvolute()` defaults `tumor = TRUE, arrays = FALSE, scale_mrna = TRUE`. [source][id-src], [releases][id-rel], [docs][id-docs] |
| Original quanTIseq pipeline (icbi-lab, `quanTIseq_pipeline.sh`, Docker/Singularity) | Last tag v2.0.0 (20 Jan 2020); master updated 16 Nov 2026 (zero-division fix) | Docs dated 25 Feb 2019 | Full FASTQ → TPM → deconvolution pipeline; `--pipelinestart=decon` runs the deconvolution module only on a TPM file. [docs][icbi-doc], [repo][orig-repo] |

**Which implementation do the authors recommend now?** None of the sources I read makes an explicit current recommendation of one implementation. What the sources do show:
- The original docs present the Docker/Singularity pipeline as the tool. [icbi-doc]
- The quantiseqr vignette is co-authored by Finotello. It describes quantiseqr as "streamlining your workflow around the quanTIseq method" and refers to the pipeline docs for method details. [vignette][vig]
- immunedeconv has no deconvolution code of its own for quanTIseq: it calls quantiseqr. [id-src]
- The Finotello 2019 paper recommends the full pipeline when raw reads are available, to avoid missing signature genes and mismatched normalisation. [Finotello 2019][fin]

For pre-computed TPM, all three routes run the same deconvolution module. **Recommended pin: `quantiseqr` 1.20.0, Bioconductor 3.23, R 4.6.x.** It is the only implementation with a versioned, archived release tied to a Bioconductor release, and it is the maintained code path that immunedeconv itself uses. The N15 proposal's R 4.6.1 fits Bioconductor 3.23, which requires R 4.6. [bioc-rel-ann]

## 2. Function arguments and what each does

Source: the `run_quantiseq` roxygen docs and body at the pinned commit. [qr-src] Page-level behaviour is confirmed by the vignette [vig] and the original pipeline docs [icbi-doc].

| Signed option | Argument | Default in quantiseqr 1.20.0 | What it does (per docs/source) |
|---|---|---|---|
| TIL10 | `signature_matrix = "TIL10"` | `"TIL10"` | The only signature supported: "At the moment, only the original `TIL10` signature can be selected". [qr-src] The vignette FAQ says the same. [vig] TIL10 has 170 genes and 10 immune cell types. [fin] |
| lsei | `method = "lsei"` | `"lsei"` | Constrained least squares via `limSolve::lsei`. Fractions are kept non-negative and their sum is kept at or below 1 (G/H constraints), and `Other = max(0, 1 − sum)` is appended. [qr-helpers] Alternatives `hampel`/`huber`/`bisquare` (robust regression) do not estimate "other". The original docs say "We recommend using the "lsei" method." [icbi-doc] With lsei only, a Treg heuristic runs: for samples with Tregs < 0.02, Tregs are averaged with a fit that leaves out CD4, and CD4 is reduced to match. Fractions are then renormalised to sum to 1. [qr-src] |
| Tumour mode | `is_tumordata = TRUE` | **`FALSE`** | Removes the signature genes in `TIL10_TCGA_aberrant_immune_genes.txt` (genes with log2(TPM+1) > 11 in TCGA, which can be over-expressed by tumour cells through aberrant demethylation or duplication). [fin], [qr-src] The vignette's tumour example logs "Removing 15 genes with high expression in tumors". [vig] Original docs: "We highly recommend setting "--tumor=TRUE" when analyzing tumor data." [icbi-doc] Because quantiseqr defaults to FALSE and immunedeconv defaults to TRUE, the value must be set explicitly. |
| mRNA scaling | `scale_mRNA = TRUE` | `TRUE` | Divides the estimated fractions by cell-type-specific mRNA content factors (`TIL10_mRNA_scaling.txt`) and rescales them to the pre-scaling total. [qr-helpers] Vignette: for real RNA-seq this "should always set to TRUE". [vig] Original docs: "We highly recommend using the default setting." [icbi-doc] |
| RNA-seq input | `is_arraydata = FALSE` | `FALSE` | If TRUE, quantile normalisation is applied and `rm_genes` is set to "none". For RNA-seq it must be FALSE. [qr-src], [qr-helpers] |
| Noisy-gene removal | `rm_genes = NULL` → `"default"` | `"default"` for RNA-seq | Drops `TIL10_rmgenes.txt` (genes noisy in RNA-seq). The vignette logs "Removing 17 noisy genes". [qr-src], [vig] Original docs advise "default" for RNA-seq. [icbi-doc] |
| is_tpm | none | — | **No `is_tpm` argument exists** in quantiseqr or the immunedeconv wrapper. [qr-src], [id-src] TPM is a documented input requirement, not a switch. Integer input triggers only a warning. [qr-src] |

Other processing in `fixMixture()` that the pin has to account for: [qr-helpers]
1. `mapGenes()` re-annotates symbols to the packaged HGNC table of **18 Apr 2017**. It maps previous symbols and synonyms to the approved symbol, drops withdrawn and unknown symbols, and takes the **median** across duplicate symbols.
2. If `max(matrix) < 50`, the data are assumed to be log2 and are exponentiated (`2^x`). Input that is actually log-scaled but has a maximum of 50 or more is not detected.
3. Each sample is renormalised to sum to 1e6 over the genes that remain after re-annotation. The genes present in the input therefore affect the scale, which is why the full gene set (not a subset) has to be supplied.

## 3. Input requirements and limits

- **Units:** gene-level TPM on a non-log scale. "Expression data should _not_ be provided in logarithmic scale." [qr-src] The pipeline docs require "non-log scale" too. [icbi-doc] Counts and other formats only trigger a warning, and the vignette FAQ says that "is not the recommended way". [vig]
- **Gene IDs:** HGNC symbols as rownames. Other identifiers must be converted beforehand, for example with `AnnotationDbi::mapIds`. [vig] Internally, symbols are reconciled to **HGNC as of 18 Apr 2017** (`HGNC_genenames_20170418.txt.gz`). [qr-helpers] Finotello 2019 likewise re-annotated to HGNC symbols "downloaded on April 2017". [fin] The practical consequence is that a symbol approved after April 2017 is unknown to the table and is dropped. A signature gene renamed since 2017 reaches the signature only if the old symbol is present in the input or appears as a previous symbol or synonym in the 2017 table. This matters only for TIL10 genes, so coverage should be checked after `mapGenes`.
- **Missing signature genes:** missing genes are silently left out. Deconvolution uses `intersect(signature, mixture)`. [qr-helpers] The function stops only when **zero** genes match and warns when fewer than **10%** are found. [qr-helpers] It logs "Signature genes found in data set: x/y (%)". [qr-src] **The authors publish no tolerable missing fraction.** The vignette examples show 97.83% and 100% coverage, but these are examples, not thresholds. [vig] The 90% post-exclusion floor in N15 is therefore correctly labelled "project proposal; not a quanTIseq default".
- **Lower accuracy on pre-computed TPM (authors' statements):** Finotello 2019 says pre-computed matrices can go straight to the deconvolution module, "although particular care must be taken" with pre-processing and signature-gene annotation. It also says the full pipeline exists to "avoid issues arising from missing signature genes and different data-normalization procedures" by building the mixture matrix the same way as the signature. [fin] The explicit "might show lower accuracy on pre-computed expression data" sentence in the paper refers to **microarray** validation sets (missing signature genes, different dynamic range). [fin] Sturm 2019, with Finotello as co-author, ran the deconvolution module alone and acknowledged "that the full quanTIseq pipeline can, in principle, provide higher performance". [sturm] SPEC_v2 4.4's limitation sentence is supported. For precise wording, cite Finotello 2019 for "particular care / missing genes" and Sturm 2019 for "full pipeline can provide higher performance".
- **Weak cell types:**
  - Finotello 2019 tumour IHC/IF validation: "Tregs, B cells, and M2 macrophages showed a lower agreement" (positive but non-significant correlations), partly attributed to small n and limited range. CD8 T cells were robust (r = 0.74–0.86). [fin] This is the source for the SPEC's weak list.
  - Sturm 2019 benchmark: across methods, poor separation of regulatory and non-regulatory CD4 T cells and poor dendritic-cell estimation. quanTIseq showed a high background prediction for macrophages/monocytes, driven by genes shared with CAFs, and spillover from pDCs to B cells, because TIL10 models myeloid DCs only. [sturm] Note that Sturm's guideline table still rates quanTIseq "++" for Tregs and CD8. The Treg weakness is therefore a validation-cohort finding from Finotello 2019, not a benchmark-wide consensus.
  - Flagging Tregs, B cells and M2 (as in `core.py` `WEAK_CELL_TYPES`) is supported. Adding dendritic cells and monocytes/macrophages (background) as a secondary caution is supported by Sturm 2019.

## 4. Licences

| Implementation | Licence | Source |
|---|---|---|
| quantiseqr | GPL-3 | Bioconductor page and DESCRIPTION. [bioc-rel] The GitHub repo is detected as GPL-3.0. [qr-repo] |
| immunedeconv | GPL-2 or later (DESCRIPTION: "GPL-2 + file LICENSE"; the LICENSE file text is GPL v2 "or (at your option) any later version") | [id-desc], [id-license] The README separately calls immunedeconv "free (BSD)" and lists quanTIseq as BSD. That conflicts with its own DESCRIPTION/LICENSE, so the DESCRIPTION/LICENSE files should be treated as authoritative. [id-readme] |
| Original quanTIseq pipeline | BSD 3-Clause per the docs. Third-party tools in the container have their own licences. GitHub detects no licence file in the repo. | [icbi-doc], [orig-repo] |

None of the three has a non-commercial restriction, unlike CIBERSORT and EPIC. [id-readme]

## Still open

1. **Wrapper or direct call.** N15 names `immunedeconv::deconvolute` as the wrapper, and that requires (a) explicit `method = "lsei"` in the record and (b) mapping `uncharacterized cell` back to `Other`, because `core.py` `FRACTION_CELL_TYPES` expects `Other` and the immunedeconv mapping emits `uncharacterized cell`. [id-map] A direct `quantiseqr::run_quantiseq` call avoids both. This is the user's decision at N15 signature.
2. **NaN guard for the 1.20.0 zero-division defect** (fixed in 1.21.3). Proposed: report and exclude NaN samples, and do not move to devel. Re-check when Bioconductor 3.24 is released. As of 19 Nov 2026 the release page still shows 3.23.
3. **HGNC 2017 drift.** After `mapGenes`, check per-cohort coverage of the ~138 TIL10 genes left after noisy and tumour removal (170 − 17 − 15 in the vignette's tumour example). Check also whether any lost gene is a renamed symbol that the 2017 table cannot map. The coverage check should run after re-annotation, not on raw input symbols.
4. **Auto-unlog heuristic (`max < 50`).** The input manifest should assert non-log TPM upstream and not rely on the package's detection.
5. **Paper B array mode.** B-SPEC mentions CPC-GENE in "array mode". That is `is_arraydata = TRUE`, which quantile-normalises and disables noisy-gene removal. It falls outside the A pin's `arrays = false` and needs its own option record under the same version.
6. **Explicit current recommendation from the authors** between quantiseqr and the Docker pipeline was not found. If wanted, ask the maintainers or check the Methods in Enzymology chapter (Plattner, Finotello, Rieder 2020), which I did not read here.

## Sources (all read 19 Nov 2026)

- [bioc-rel]: https://bioconductor.org/packages/release/bioc/html/quantiseqr.html (quantiseqr 1.20.0, Bioconductor 3.23, GPL-3)
- [bioc-dev]: https://bioconductor.org/packages/devel/bioc/html/quantiseqr.html (1.21.3, Bioconductor 3.24 devel)
- [bioc-rel-ann]: https://bioconductor.org/about/release-announcements/ (3.23 on 29 Apr 2026, R 4.6)
- [vig]: https://bioconductor.org/packages/3.23/bioc/vignettes/quantiseqr/inst/doc/using_quantiseqr.html
- [qr-src]: https://github.com/federicomarini/quantiseqr/blob/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/R/quantiseqr.R
- [qr-helpers]: https://github.com/federicomarini/quantiseqr/blob/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/R/quantiseqr_helpers.R
- [qr-extdata]: https://github.com/federicomarini/quantiseqr/tree/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/inst/extdata
- [qr-commit]: https://github.com/federicomarini/quantiseqr/commit/a948291c8d6b2a3262655ad2e4c52e1573ae55e4
- [qr-commits]: https://github.com/federicomarini/quantiseqr/commits/devel (fix commits 948f4af8, 406a7e8a; merged 1bc02b04, 17 Nov 2026)
- [qr-news]: https://github.com/federicomarini/quantiseqr/blob/devel/NEWS.md
- [qr-repo]: https://github.com/federicomarini/quantiseqr
- [id-rel]: https://github.com/omnideconv/immunedeconv/releases
- [id-src]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/R/immune_deconvolution_methods.R
- [id-map]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/inst/extdata/cell_type_mapping.xlsx
- [id-desc]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/DESCRIPTION
- [id-license]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/LICENSE
- [id-readme]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/README.md
- [id-docs]: https://omnideconv.org/immunedeconv/ (shows 2.1.4)
- [icbi-doc]: https://icbi.i-med.ac.at/software/quantiseq/doc/ (pipeline docs, dated 25 Feb 2019)
- [orig-repo]: https://github.com/icbi-lab/quanTIseq
- [orig-fix]: https://github.com/icbi-lab/quanTIseq/commit/e40f1e47499316fe9fc19793491f515b280a270f
- [fin]: Finotello F et al. Genome Medicine 2019;11:34. https://doi.org/10.1186/s13073-019-0638-6 (full text via PubMed Central PMC6534875)
- [sturm]: Sturm G et al. Bioinformatics 2019;35(14):i436–i445. https://doi.org/10.1093/bioinformatics/btz363 (full text via PubMed Central PMC6612828)

[bioc-rel]: https://bioconductor.org/packages/release/bioc/html/quantiseqr.html
[bioc-dev]: https://bioconductor.org/packages/devel/bioc/html/quantiseqr.html
[bioc-rel-ann]: https://bioconductor.org/about/release-announcements/
[vig]: https://bioconductor.org/packages/3.23/bioc/vignettes/quantiseqr/inst/doc/using_quantiseqr.html
[qr-src]: https://github.com/federicomarini/quantiseqr/blob/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/R/quantiseqr.R
[qr-helpers]: https://github.com/federicomarini/quantiseqr/blob/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/R/quantiseqr_helpers.R
[qr-extdata]: https://github.com/federicomarini/quantiseqr/tree/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/inst/extdata
[qr-commit]: https://github.com/federicomarini/quantiseqr/commit/a948291c8d6b2a3262655ad2e4c52e1573ae55e4
[qr-commits]: https://github.com/federicomarini/quantiseqr/commits/devel
[qr-news]: https://github.com/federicomarini/quantiseqr/blob/devel/NEWS.md
[qr-repo]: https://github.com/federicomarini/quantiseqr
[id-rel]: https://github.com/omnideconv/immunedeconv/releases
[id-src]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/R/immune_deconvolution_methods.R
[id-map]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/inst/extdata/cell_type_mapping.xlsx
[id-desc]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/DESCRIPTION
[id-license]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/LICENSE
[id-readme]: https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/README.md
[id-docs]: https://omnideconv.org/immunedeconv/
[icbi-doc]: https://icbi.i-med.ac.at/software/quantiseq/doc/
[orig-repo]: https://github.com/icbi-lab/quanTIseq
[orig-fix]: https://github.com/icbi-lab/quanTIseq/commit/e40f1e47499316fe9fc19793491f515b280a270f
[fin]: https://doi.org/10.1186/s13073-019-0638-6
[sturm]: https://doi.org/10.1093/bioinformatics/btz363
