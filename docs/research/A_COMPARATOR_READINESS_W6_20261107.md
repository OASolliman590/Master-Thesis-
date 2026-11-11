# Paper A comparator readiness, W6

**Status: implementation qualification only.** This report does not admit a comparator, evaluate outcomes, validate biology, or complete the deferred real A-P2 rebuild. Synthetic checks demonstrate software behavior only.

The patient-free registry is [A_COMPARATOR_READINESS_W6_20261107.tsv](A_COMPARATOR_READINESS_W6_20261107.tsv). It records source URLs, identities where verified, source-family exposure, measurement and missingness policy, implementation state, blockers, and any command that can be run later. `python -m tools.a_comparators readiness` prints the short status view.

## Selected comparator: CYT

The fixed rule is `sqrt(TPM_GZMA * TPM_PRF1)`, with higher values in the cytolytic direction, no pseudocount, and no learned coefficient. The source paper describes CYT from GZMA and PRF1 TPM; the Paper A registry and assay contract fix the unlogged, no-offset rule for this product ([Rooney et al.](https://pubmed.ncbi.nlm.nih.gov/25594174/), [comparator contract](../../specs/A/COMPARATOR_REGISTRY.md), [assay contract](../../specs/A/ASSAY_PROCESSING_CONTRACT.md)).

The new adapter reuses `tools/a_scoring.cyt` and `tools/a_scoring.resolve`. It accepts only a linear RNA-seq TPM representation, refuses duplicate or ambiguous required symbols and invalid abundance, leaves a sample unscorable when either required value is missing, and preserves input sample-column order. It performs no normalization. Its precondition is that the caller supplied full-source TPM already qualified through the accepted A-P2 preparation route; the adapter cannot certify source completeness on its own.

The existing A-P2 route is the qualification path for source TPM. The user's latest decision defers its real rebuild, so this work has no fresh source identity or real qualification receipt. CYT is selected and its score rule is available, but its real source gate remains pending. No real expression or outcome source was read or run.

## Method readiness

| Method | Readiness | Specific blocker |
|---|---|---|
| CYT | Existing scorer reused; source qualification pending | Real A-P2 rebuild is deferred. |
| Constant/intercept baseline | Sanity baseline only | No comparator outcome command is available here; do not compute AUC when either class is absent. |
| Lin 2026, 59 genes | Blocked | Exact final membership/rule and 19-cohort roster are not verified. The final article reports a 59-gene signature tested across 19 cohorts, which does not identify the exact roster or executable scoring rule ([Lin et al.](https://pubmed.ncbi.nlm.nih.gov/42679812/)). |
| Subramanian 2023 | Blocked | GSVA and cohort-level clustering are described, but a standalone single-sample assignment rule and its exact inputs are not verified. The author release describes enrichment results and cluster-generating code ([Dryad release](https://datadryad.org/dataset/doi:10.5061/dryad.v41ns1s11)); official [GSVA documentation](https://bioconductor.org/packages/release/bioc/html/GSVA.html) describes the package's sample-wise enrichment role but does not establish this publication's exact gene-set version or clustering assignment rule. |
| PredictIO, Bareche 2022 | Blocked | Original launchers disagree on membership threshold; exact membership, locked-version GSVA equivalence, and licence/access are unresolved. The original repository remains the cited source; no later package is substituted ([Bareche et al.](https://pubmed.ncbi.nlm.nih.gov/36055464/), [original repository](https://github.com/bhklab/PredictIO)). The current official [GSVA documentation](https://bioconductor.org/packages/release/bioc/html/GSVA.html) does not resolve the locked-version equivalence. |
| Ayers final T-cell-inflamed GEP | Blocked | The final weighted 18-gene score uses housekeeping-normalized log10 counts and elastic-net coefficients. Its exact coefficient and normalization bundle is not qualified. It is not `CUSTOM_MEAN_AYERS_GEP_18` ([Ayers et al.](https://www.jci.org/articles/view/91190)). |
| TIDE | Blocked | No qualified local code/version, reference bundle, licence, subtype handling, or missing-feature policy. The primary method uses pre-treatment RNA-seq or NanoString data ([Jiang et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC6487502/)). |
| TIS | Blocked | Exact assay identity, coefficients, normalization, licence/access, and missing policy are unresolved. TIS is kept distinct from the Ayers GEP ([primary TIS report](https://jitc.bmj.com/content/6/1/63)). |
| COMPASS 2026 | Blocked | Final/preprint feature identity, input order/reference resources, and checkpoint identity remain unresolved ([Shen et al.](https://pubmed.ncbi.nlm.nih.gov/42399673/)). |
| Clinical-only | Blocked | Shared covariate sets and missingness rules await a signed decision. |

The registry includes no placeholder implementation for a blocked method. The only executable command in this package reports readiness; no outcome or AUC calculation was added. The constant score remains labelled as a sanity baseline. Any later outcome evaluation must use the accepted A-P2/A-META route on invented data and keep the same prospectively eligible patient rows for every compared score. This package does not select a convenience subset or implement a second statistics layer.

## Prior source-family use

The registry marks Subramanian, TIDE, and COMPASS source-family use as confirmed where the primary-source audit identifies a matching family. These labels say only that a publication analysed a source family. Patient intersection, individual-model training, tuning, and checkpoint-specific exposure remain `UNVERIFIED`. Lin's final 19-cohort list is unavailable. The newer PredictIO, Ayers, TIS, and CYT exposure fields remain `UNVERIFIED`; absence from an inspected source is not independence.

The Subramanian source-family record is also summarized in [RESOURCES.tsv](../cohorts/RESOURCES.tsv). The primary TIDE article names Riaz and Hugo and cites the Van Allen and Prat studies; the additional source audit resolves the Prat publication to `gse93157`. The COMPASS final article's cohort audit confirms Riaz, Hugo, Liu, Van Allen, Kim, Gide, Rose, and IMvigor210 at the source-family level. None of these records establish patient overlap or training membership for each executable model.

## Test boundary

Tests use invented numeric matrices and invented synthetic manifests. They check formula outputs, unit and mapping failures, missing-value propagation, conditional refusal, and the existing A-META early locks. An A-META effects check feeds shuffled invented feature rows by row index and confirms expected summaries and one shared eligible-row identity across both scores. The lock checks patch the source loader and assert it is not called. These tests do not open real source tables or validate biology. No `--allow-outcomes` option is passed.
