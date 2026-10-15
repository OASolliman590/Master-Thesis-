# A-BIO: response-associated biological effects

## Inputs and release

Consume only A_BASELINE_BIO-admitted baseline rows, episode-linked outcomes, assay/source hashes and a frozen feature/programme registry. Exclude all reserved final-test families and related specimens before any response-associated gene exploration. Clinical curation may inspect outcomes; no atlas R/NR DEG list from reserved patients may enter discovery. A-BIO may run under its own statistical/data release even if independent A-P2 evaluation is unavailable.

## Study-specific model

The default estimand is the pretreatment R-minus-NR association within the originating study, declared cancer/regimen/endpoint and eligible assay stratum. A source with multiple regimens is stratified or modelled with an explicitly identifiable adjustment; it is not automatically split into independent studies. Retain all tested genes and all nonestimable flags.

For integer counts, use a qualified negative-binomial GLM with library normalization/offset and response coefficient: log(mu_gi)=offset_i+alpha_g+beta_g R_i+C_i gamma_g. Report beta_g/log(2) as NB_log_mean_ratio, its unshrunk model SE/interval and exact design; shrunken effects may be descriptive but cannot be mixed with unshrunk SEs. Estimated-count import requires the backend's documented offset/length route. For known continuous expression, fit source-scale linear models, preferably limma empirical Bayes for compatible designs, and report the R-minus-NR contrast and SE on that declared scale. Microarrays retain their own annotation/normalization stratum. Do not use ANOVA as an unexamined replacement for the contrast model.

Adjustment sets are source-specific and frozen before associations: retain an unadjusted association as the common reference, add an estimable prespecified baseline clinical set where available, and run composition adjustment separately. Covariates measured after treatment cannot be inserted as baseline confounders. Report missing covariates, rank, residual degrees of freedom, reference levels and exactly which patients enter each model. No stepwise p-value covariate selection. A smaller adjusted subset is not compared to the larger unadjusted set as though adjustment alone caused attenuation.

## Compatible-context synthesis

Start within cancer, compatible regimen/endpoint and effect_scale_id. One effect per independent originating family per declared contrast is the default; dependent arms/shared controls require within-study combination with covariance or a multivariate model. With at least two independent compatible effects, propose REML random effects with modified Knapp–Hartung uncertainty (variance inflation not below the conventional value) and t degrees of freedom k−1; freeze implementation/version before fitting. k=2 is a minimal synthesis condition, not convincing precision. Nonconvergence or nonestimable tau² yields a flagged forest table, not an undisclosed fixed-effect substitute. Report tau², interval, direction, leave-one-study-out influence and study/cancer support. Prediction intervals require adequate estimability and a specified method; do not print unstable intervals as established transfer. Cross-cancer pooling and moderator models are supporting analyses, conditional on full-rank context structure and sufficient independent information. A non-significant heterogeneity test is not proof of homogeneity.

Never combine NB log-mean ratios and mean log-expression differences just because both are log-scaled. Standardized effects are a separately preregistered sensitivity, with denominator and small-sample correction recorded. P-value aggregation or vote counting is descriptive only, not the primary synthesis. Robust variance estimation is not a remedy for too few independent clusters.

## Programmes and multiplicity

Use a versioned registry containing exact genes, identifiers, weights/direction, source and required coverage. Source-defined scores require their original implementation; simple custom programme averages are explicitly named custom scores. Learned programmes are development-only and stability-assessed across held-out development studies. Freeze scoring and effect_scale_id before final evaluation. Candidate domains include cytotoxicity, interferon, antigen presentation, recruitment, myeloid inflammation, immunosuppression, ECM/stroma and cell-cycle/stress; no canonical domain is required to appear.

Define gene-level and prespecified programme-level multiplicity families separately within each declared synthesis family; proposed BH FDR and confidence settings must be numerically released in NUMERICAL_FREEZE_REGISTER.tsv. Retain complete tested tables and unadjusted p-values alongside adjusted values; no cross-family cherry-picking. Replication is assessed by direction/uncertainty and independent context, not merely a pooled p-value.

## Outputs and acceptance

response_effects.tsv records feature, contrast, estimate, SE/interval, effect scale, source-study count, patient N, covariates, cancer/regimen support, heterogeneity, coverage and estimability. biological_context.tsv records cellular hypotheses and conflicting evidence separately. Null and contradictory programmes remain. The B/C handoff is frozen before final-test inspection and cannot be rewritten using test results.
