# Paper B proposed specification kit

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1, 2026-09-05.** This kit specifies the intended analysis; no model, external validation or biological conclusion has been implemented. Primary choices require independent scientific review.

## Question and thesis role

Does promoter methylation add externally reproducible information about a fixed antigen-presentation expression program beyond prespecified clinical and tumour-purity covariates in prostate cancer? Develop the model in TCGA-PRAD and test it once in a distinct CPC-GENE cohort. The primary result is an external change in predictive R-squared, not a clinical ICI-response prediction or causal-silencing test.

B is the central patient molecular chapter. It retains the registered PRAD/LUAD contrast as a secondary tissue comparison and a frozen, discovery-only signed handoff to C. Neither the contrast nor expression–methylation anticorrelation proves that a tumour cell is epigenetically silenced. Wet-lab requirements remain separate; this kit contains no experimental procedures.

## Novelty and counterexamples

| Closest source | What already exists | Proposed contribution |
|---|---|---|
| [MethylCIBERSORT](https://www.nature.com/articles/s41467-018-05570-1), DOI 10.1038/s41467-018-05570-1 | Methylation-derived tumour composition/immune patterns | Independent prediction of a defined prostate molecular program with explicit composition limits; not a generic methylation immune score. |
| [The Landscape of Prostate Tumour Methylation](https://pmc.ncbi.nlm.nih.gov/articles/PMC11844408/) | Broad prostate methylation heterogeneity and regulatory relationships | A narrowly specified external immune-program estimand and transparent incremental information beyond shared covariates. Exact overlap with the final selected data must be audited. |
| [Guo et al., Cell 2023](https://doi.org/10.1016/j.cell.2023.05.028) | Immune-gene repression associated with hypomethylated domains in prostate cancer | Explicitly distinguish promoter association from domain-level mechanisms and preserve both directions. Rediscovering methylation-associated immune repression alone is insufficient novelty. |

Proposed hypothesis: external delta-R-squared is positive. A null/negative result is scientifically valid. The study may establish predictive transport on the declared molecular scale; it cannot establish independence from every unmeasured covariate, cellular causality or ICI sensitisation. A conditional standalone manuscript decision follows the actual evidence and closest-study comparison, not the presence of a spec.

## Current evidence changing feasibility

The verified metadata route is **497 TCGA cases** and **210 CPC-GENE patient-code pairs**, before specimen reconciliation/QC. Actual header checks support the paired code coverage. External clinical linkage currently reaches only **73/210 candidate patient codes** and still requires focus/identity confirmation. Gene-level external copy number is not established. A later complete AIU expression audit verified all eight proposed genes as unique gene-ID rows, each finite in all 213 samples (24,598 feature rows; 32,357,821 compressed bytes). No expression matrix or Y score was retained. The common TCGA/CPC annotation universe, promoter coverage and cross-platform scale remain unresolved. Therefore the adjusted primary endpoint is conditional; 210 cannot be advertised as its final validation N. See DATA_AND_SOURCES and canonical B evidence reports.

## Requirements and kit map

Research users must be able to inspect source-specific patient/sample counts, trace reanalyses, reproduce ranks and promoter mappings, distinguish prediction from mechanism, see negative associations, audit held-out outcome access, and reconstruct the C handoff without using CPC-GENE outcomes.

| GOAL deliverable | Document |
|---|---|
| 1 Scope, thesis mapping, novelty, claims | README |
| 2 Coverage/manifest/mapping/real evidence | DATA_AND_SOURCES.md; SOURCE_MANIFEST.json |
| 3 Exact proposed primary analysis | ANALYSIS.md |
| 4 Validation/leakage boundaries | VALIDATION_AND_FIGURES.md |
| 5 Four figures | VALIDATION_AND_FIGURES.md |
| 6 Preregistration, ledger, glossary, citations | PREREGISTRATION_AND_LEDGER.md |
| 7 Architecture, environment, schemas | SOFTWARE_CONTRACT.md |
| 8 Tickets | TICKETS_AND_TESTS.md |
| 9 Tests | TICKETS_AND_TESTS.md |
| 10 Reproduction/readiness | REPRODUCE_AND_READINESS.md |

**Proceed criteria:** all source/scale/covariate/precision/review gates pass. **Narrow proposal:** explicitly restrict external inference to a verified covariate-complete subset if sufficiently precise and scientifically representative; do not pretend that decision is already accepted. **Combine proposal:** if B supplies credible associations but C lacks independent standalone differentiation, consider an integrated chapter/manuscript. **Defer an analysis:** when its mandatory covariates or independent data remain missing; continue unaffected design work. None of these recommendations cancels B without user acceptance.
