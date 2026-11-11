# A-COMP N15 quanTIseq pin proposal

**Status: PROPOSED; unsigned.** This document does not close N15 and does not authorize a real cohort run. The direct user instruction remains synthetic-only implementation, with real A-P2 reconstruction, cohort input access, and expression/outcome joins deferred or locked.

The implementation should refuse any real run while this proposal remains unsigned. A real deconvolution also requires a matching R preflight report and a validated, full-source input manifest before it opens the TPM matrix. Outcome-linked A-COMP analyses have separate open scientific gates listed below.

## Proposed pin contract

```json
{
  "pin_id": "N15",
  "status": "PROPOSED",
  "signature": null,
  "software": {
    "r": "4.6.1",
    "bioconductor": "3.23",
    "packages": {
      "immunedeconv": "2.1.4",
      "quantiseqr": "1.20.0",
      "limSolve": "2.0.3"
    },
    "immunedeconv_source_commit": "e625e6c28ed14a30f9f40f159925cc9f0df4fa49",
    "quantiseqr_source_commit": "a948291c8d6b2a3262655ad2e4c52e1573ae55e4"
  },
  "reference_files": {
    "TIL10_signature.txt": "76aababc370c143705ee895f094a45eb168b87b10f30783bdcedbe4c4c0fecf9",
    "TIL10_mRNA_scaling.txt": "c7fa748a99c8f3e377924a7b35bed3000243966ee42beab7efac444940eecbd2",
    "TIL10_rmgenes.txt": "b05906748450b71d1a7b912ba3e351e2614052d99c2ba0670ff66510bac886f4",
    "TIL10_TCGA_aberrant_immune_genes.txt": "5182b9441fd03119da12a83ad932b9053cf73c62edc4028d55360ca3ad347fc3",
    "HGNC_genenames_20170418.txt.gz": "7bc6bd20dc57a696ca22dc603ef7f046c45e3e72ab591cea8857268dfb4f6b7e"
  },
  "method": {
    "wrapper": "immunedeconv::deconvolute",
    "method": "quantiseq",
    "signature_matrix": "TIL10",
    "native_method": "lsei",
    "tumor": true,
    "arrays": false,
    "scale_mrna": true,
    "rmgenes": null,
    "rm_genes": null,
    "rna_rm_genes_behavior": "packaged default noisy-gene removal",
    "tumor_exclusions": "packaged aberrant immune-gene list"
  },
  "input_policy": {
    "cohorts": [
      "riaz_gse91061",
      "hugo_gse78220",
      "gse168204",
      "liu2019",
      "gide2019",
      "vanallen2015",
      "gse135222",
      "gse176307",
      "kim2018",
      "gse145996",
      "gse165278",
      "gse218989"
    ],
    "platform": "RNA-seq",
    "unit": "TPM",
    "transform": "unlogged linear",
    "feature_id": "HGNC gene symbol",
    "full_source": true,
    "arrays": false,
    "protected_final_test": "refuse",
    "other_platforms": "refuse"
  },
  "coverage_qc": {
    "coverage_denominator": "TIL10 signature genes with nonzero weight for that cell type",
    "coverage_before_exclusions": "input-symbol overlap before package RNA and tumour exclusions",
    "coverage_after_exclusions": "input-symbol overlap after packaged RNA default and tumour aberrant-gene exclusions",
    "post_exclusion_coverage_floor": 0.9,
    "coverage_floor_source": "project proposal; not a quanTIseq default",
    "coverage_floor_action": "refuse the cohort if any required type is below the floor; report each type's before/after counts and status",
    "fraction_types": [
      "B cell",
      "Macrophage M1",
      "Macrophage M2",
      "Monocyte",
      "Neutrophil",
      "NK cell",
      "T cell CD4+ (non-regulatory)",
      "T cell CD8+",
      "T cell regulatory (Tregs)",
      "Myeloid dendritic cell",
      "Other"
    ],
    "fraction_range": "[-1e-6, 1 + 1e-6]",
    "fraction_range_tolerance": 0.000001,
    "fraction_sum_tolerance": 0.000001,
    "fraction_sum_rule": "all ten immune fractions plus Other sum to one within tolerance",
    "renormalize": false,
    "weak_types": ["T cell regulatory (Tregs)", "B cell", "Macrophage M2"],
    "coverage_source_note": "quantiseqr reports signature coverage but sets no numeric minimum; 90% is a project proposal"
  },
  "analysis_limits": {
    "pool_raw_fractions_across_studies": false,
    "use_single_cell_reference": false,
    "pseudobulk_benchmark": false,
    "rna_outcome_adjustment": false,
    "a_p2_features_or_outcome_adjustment": false,
    "cibersortx": "not run",
    "precomputed_tpm_limitation": "state that quanTIseq authors report lower accuracy on precomputed TPM than on their FASTQ workflow",
    "claim_language": "descriptive/supporting association only; never explains or causes"
  },
  "attribution_and_license": {
    "method_citation": "Finotello et al. Genome Medicine 2019;11:34. doi:10.1186/s13073-019-0638-6",
    "quantiseqr": "Marini and Finotello; Bioconductor quantiseqr 1.20.0; GPL-3",
    "immunedeconv": "Tomic et al.; immunedeconv 2.1.4; GPL-2-or-later",
    "limSolve": "locked dependency, version 2.0.3; retain its package license metadata in the R provenance",
    "redistribution": "call installed packages and cite sources; do not copy package implementation or redistribute cohort data"
  },
  "references": {
    "quantiseqr_api": "https://federicomarini.github.io/quantiseqr/reference/run_quantiseq.html",
    "quantiseqr_bioconductor": "https://bioconductor.org/packages/release/bioc/html/quantiseqr.html",
    "immunedeconv_pinned_wrapper": "https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/R/immune_deconvolution_methods.R",
    "quantiseqr_pinned_source": "https://github.com/bioc/quantiseqr/blob/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/R/quantiseqr.R",
    "quantiseqr_pinned_reference_files": "https://github.com/bioc/quantiseqr/tree/a948291c8d6b2a3262655ad2e4/inst/extdata",
    "immunedeconv_pinned_license": "https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/LICENSE"
  },
  "contract_sha256": "c5016e4a82e8959bdf07db736dea747f099f8999e78ef61c06348c1a9a108432"
}
```

## Interpretation and scope

- The version and SHA256 values above match the installed locked packages and five package reference files. They are software provenance, not a cohort analysis or a fresh A-P2 rebuild.
- The wrapper routes its `tumor`, `arrays`, and `scale_mrna` options to `quantiseqr::run_quantiseq`. Its own `method` argument selects the wrapper method, so the native `lsei` value is verified from the locked `quantiseqr` default and recorded in every run receipt. The code refuses if that default changes.
- `rm_genes = NULL` uses quanTIseq's packaged RNA default-removal list. Tumour mode also removes the packaged tumour-aberrant list. The effective lists are loaded from the pinned reference files and reflected in coverage counts.
- The 90% post-exclusion coverage floor and `1e-6` fraction tolerances are proposed project QC rules. The package documentation sets no coverage minimum. Values are checked as returned; the implementation never renormalizes fractions.
- Coverage is reported per cell type before and after the effective exclusions, with unavailable types and the weak Treg, B-cell, and M2 estimates flagged. The accepted output has ten immune fractions plus `Other`, whose package label is `uncharacterized cell`.
- No raw fractions are pooled across studies. No single-cell-derived reference or pseudobulk benchmark is used. No estimated fraction is an RNA outcome covariate or an A-P2 feature. CIBERSORTx remains **not run**.

## Other A-COMP choices still open

N15 does not settle the incremental AUROC bootstrap. The signed numerical freeze has no A-COMP stream, refit/evaluation rule, or task identifier. The code therefore demonstrates a separately named synthetic-only, conditional-on-full-fit bootstrap with invented data and an R-only draw receipt; it does not reuse A-P2 or A-P1 streams. Real incremental AUROC remains refused until the user fixes the stream and refit/evaluation contract.

The signed text names an eighteen-gene GEP but does not supply the published weighted coefficients and housekeeping-normalization contract. `AYERS_GEP_18` custom mean scores are used only under their custom method IDs for panel correlation. The synthetic incremental-AUROC demonstration uses a distinct, explicitly invented weighted score and never calls it the published GEP. Real incremental AUROC remains refused until the published weighting and normalization are sourced and pinned.

No signature, approval, gate closure, or release is recorded here.
