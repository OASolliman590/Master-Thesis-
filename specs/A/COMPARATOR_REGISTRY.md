# Comparator admission registry

## Selected anchor: CYT

ID CYT_Rooney_TPM_v1; source DOI 10.1016/j.cell.2014.12.033; features GZMA and PRF1; unlogged nonnegative gene TPM; score sqrt(GZMA×PRF1); higher indicates greater cytolytic activity; no pseudocount or learned coefficient. Unique identifiers, both finite measured values and supported full-source normalization are required. Record exact annotation, upstream unit/conversion and implementation hash. Missing is unscorable, not zero. The mathematical definition is selected; a tested source parser/implementation bundle is still required. CYT is not itself evidence of observed prostate response.

## Conditional supporting methods

| Method | Required admission evidence | Current role |
|---|---|---|
| IFN-gamma / T-cell-inflamed GEP, Ayers et al. | Exact published gene set, coefficients, platform-specific normalization, direction and original training populations | Conditional supporting comparator; no substitute average |
| TIDE | Source-correct local code/version, expression/reference inputs, licence, subtype handling and overlap audit | Conditional; a web-service-only result or homemade approximation is not released |
| TIS | Resolve exact assay/implementation, coefficients/normalization and licence; distinguish overlapping names from GEP | Conditional, not assumed interchangeable |
| COMPASS (2026) | Original model/repository/version, feature representation and reference resources; training/test-family overlap and operational access | Conditional current-method comparator; not a mandatory blocker for CYT primary |
| Clinical-only model | Shared baseline covariates, missingness/representativeness and training-only fitting under the same folds | Additional prespecified model, not retrospectively convenient adjustment |
| Constant/intercept-only | Constant ranking gives 0.5 only when both classes exist; probabilities reflect the declared training population | Sanity baseline, not a competitive mechanistic method |

Each registry entry must include exact source URLs, immutable code/weights hashes, measurement suitability, gene coverage, missing-feature policy, direction, reference/training families, licence, access, admission reviewer and blocked reason. UNKNOWN weights or normalization block the named method. Do not reuse a convenient but differently normalized implementation under a published name.

## Fair evaluation

The primary compares the frozen learned score and qualified CYT on identical preselected patients. Supporting method comparisons use a separately frozen common eligible set and report its selection; do not declare superiority from different convenience subsets. Do not flip score direction after seeing labels or repair absent features using test outcomes. AUC improvement against CYT is not evidence of conditional information beyond CYT. A nested model comparison adding features to CYT requires its own learning/evaluation design. Audit published-method overlap independently for each comparator; 'independent of our training' does not prove independent of theirs.
