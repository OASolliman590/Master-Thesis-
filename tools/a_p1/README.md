# Paper A A-P1

A-P1 compares the fixed CYT score on the same index-episode patients under two source-supported response definitions: ORR (CR/PR vs SD/PD) and DCR (CR/PR/SD vs PD). It reports both within-study AUCs, `delta = AUC(DCR) - AUC(ORR)`, pairwise A(O,SD), A(O,PD), and A(SD,PD), category counts and fractions, exclusions, and score and mapping hashes. A fixed higher score is favorable; pairwise ties receive half credit. The score is exactly `sqrt(TPM_GZMA * TPM_PRF1)` on qualified, uniquely mapped, unlogged TPM. Zero is retained and missing genes are excluded.

The [original CYT study](https://pubmed.ncbi.nlm.nih.gov/25594174/) motivates the GZMA/PRF1 expression measure. Endpoint and eligibility behavior follows [`specs/A/ENDPOINT_SENSITIVITY.md`](../../specs/A/ENDPOINT_SENSITIVITY.md). Invented examples exercise software behavior and make no biological claim.

## Invented demonstration

Run the two-study synthetic demonstration with the pinned R 4.6.1 and Bioconductor 3.23 project runtime:

```sh
python -m tools.a_p1 demo --out results/a_p1_demo
```

The output has clearly labelled invented studies and weights, per-study intervals, and weighted collection intervals. Collection estimates are declared weighted means of within-study AUCs; cross-study pooled AUC is never calculated. Real synthesis remains unavailable until a prospectively declared roster and cancer/study weight contract are signed. The spec's proposed default is not promoted to a decision.

## Joint bootstrap

The principal score uses 2,000 patient resamples under `a_p1_bootstrap` (seed 20261108). R sets the root seed once for the complete task. For every replicate it iterates studies in UTF-8 radix order, then score series in UTF-8 radix order; within each study and series it samples the O, SD, and PD strata in that order, with patients ordered by UTF-8 radix patient key. Each draw stays inside its study, score series, and original category. CYT and an optional learned score use their own eligible rows while sharing the one task and streams; both endpoint AUCs use the same resampled rows within each score analysis.

The 95% percentile intervals condition on the original O/SD/PD category counts within each study and score analysis. They do not include category-composition uncertainty. One derived `second_check` stream reports interval-end differences over 0.01 and never replaces or retries the main result. Assignment receipts and artifact hashes are included in output provenance. The R helper's expected order is checked against a direct `sample.int` implementation.

No-SD results are labelled as structural-zero sensitivities and are outside the informative set. A declared collection that assigns positive weight to a noninformative study is reported as nonestimable; weights are not silently removed or renormalized. Missing O or PD makes the endpoint contrast explicitly nonestimable.

## Inputs and release gates

The `analyze` CLI and Python interface require hash-bound provenance. TSV input reads only these exact fields: `study_id`, `cancer`, `patient_key`, `specimen_key`, `index_episode_id`, `is_index_specimen`, `expression_episode_id`, `outcome_episode_id`, `response_category`, `source_criteria`, `evaluation_window`, `TPM_GZMA`, and `TPM_PRF1`. `CR`, `PR`, `SD`, and `PD` are mapped to O/SD/PD. Unknown and NE categories are excluded. Binary R/NR labels cannot supply SD. Specimen and episode bindings are validated study-wide before grouping.

The `--allow-outcomes` option exists for a future explicitly released route. It was never passed in this task. Without release provenance, real-cohort analyses refuse before payload access. Protected paths and ingestion-packet paths are refused before opening. Synthetic provenance is explicit and hash-bound, and known real or protected cohort identities cannot be labelled synthetic.

An optional learned-score secondary accepts one frozen equation with a prediction payload hash, score hash, score mapping version, endpoint mapping version, and provenance for source, fitting, tuning, feature-selection, and prediction patients. Prediction patients must be disjoint from those used in fitting or selection. Learned eligibility is evaluated independently of CYT gene availability. Outer-fold scores and endpoint-specific refitting are not supported.

The signed A-P1 scope also requires endpoint sensitivity for locked panels. A-P1-specific panel score definitions, fixed directions, and qualification rules have not been released; this unresolved gate is recorded in [`docs/decisions/A_P1_PANEL_SCORING_PENDING_20261106.md`](../../docs/decisions/A_P1_PANEL_SCORING_PENDING_20261106.md). No A-BIO panel means are copied into A-P1.

The hash-keyed `.a_p1_work/` subdirectory beneath the chosen output directory retains the selected R input and private bridge execution artifacts. It is generated output, not a source or result for version control. Shared `run_r` and `run_r_sanitised` keep their existing cleanup behavior unless callers explicitly supply `retention_dir`.

## Sources

- [R `sample` / `sample.int` documentation](https://stat.ethz.ch/R-manual/R-devel/library/base/html/sample.html)
- [R `quantile` documentation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/quantile.html)
