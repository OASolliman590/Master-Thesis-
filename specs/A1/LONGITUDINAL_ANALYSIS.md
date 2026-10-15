# Longitudinal estimands and statistical implementation

## Contrast hierarchy

The central response-associated contrast is RESPONSE_TIME_INTERACTION: the R-minus-NR difference in within-patient change over a qualified baseline/follow-up window. BASELINE_R_NR and ON_R_NR are cross-sectional contrasts. DELTA_R and DELTA_NR are within-group changes; 'significant in R but not in NR' is not a test of their difference. Progression and genuinely post-treatment contrasts remain distinct. ARM_TIME_INTERACTION is allowed only with real comparative arms and a separately reviewed estimand. Dynamic prediction is not part of the current release.

## Two-timepoint continuous-expression route

For complete qualified pairs define d_gi=X_followup,gi−X_baseline,gi on the same declared assay scale. Fit d_gi=alpha_g+beta_g R_i+C_i gamma_g+epsilon_gi using a source-appropriate linear/limma model. beta_g is the direct response-associated differential change. Predeclared baseline covariates or timing deviations enter only when estimable and justified; do not select them by significance. Report group paired counts, interval, covariates, rank and residual degrees of freedom. A single response group supports its own delta but not the response-time interaction.

## Repeated-measures continuous/count-derived precision route

For multiple windows use a patient-aware model such as expression ~ response * window + prespecified_covariates + (1|patient), with an implementation that supports the required precision weights and degrees of freedom. For count-derived voom weights and complex repeated designs, evaluate the pinned variancePartition/dream workflow, including voomWithDreamWeights where required. limma duplicateCorrelation is a distinct limited correlation structure, not automatically equivalent to multiple random effects. Check convergence/singular fits, design rank and contrast estimability before returning estimates. Do not switch among models after inspecting favourable p-values; numerical/model selection is frozen first.

## Count model route and rank

For two-timepoint NB fixed-patient analysis use patient intercepts plus time and time×response, omitting the patient-constant response main effect. With one intercept per patient, an additional response main column is collinear. In formula terms, construct and verify the actual model matrix rather than blindly executing patient + response + time + response:time. The NB interaction is a log ratio of changes in modelled means, not the same estimand as the difference in mean log-transformed abundance. Store distinct effect_scale_id values and do not pool them by shared 'log2' labels. Imported estimated counts require their supported offset/length model.

For every route explicitly calculate rank, residual information, estimable contrasts and affected parameters. A rank-deficient design yields NONESTIMABLE_CONTRAST with a report, not an arbitrary dropped column that changes the question. Shared controls/baselines and multiple regimens require joint covariance or a model that preserves dependence.

## Synthesis

Estimate within originating study and compatible regimen/endpoint/window/assay first. At least two independently admitted families are required for a cross-study synthesis; this is not sufficient precision or manuscript evidence. Use the A-BIO compatible-scale REML/modified-KH proposal with the same explicit numerical freeze and small-k cautions. If one study contributes correlated windows/arms, preserve its covariance or report separate window-specific syntheses; do not inflate k. Cross-class/cancer/time moderators are individually gated by confounding, rank, independent information and precision. No post-result dropping of discordant studies.

## Biopsy selection and missingness

The main paired estimand applies to patients with eligible biopsies at both times, not automatically all treated patients. Report baseline clinical characteristics and available baseline molecular summaries of paired versus nonpaired patients only under the relevant data release, along with response/follow-up patterns and missing-biopsy reasons. Conditioning on future response and availability can select on clinical course. Do not assume missing at random. Inverse-probability weighting or missing-data models require measured selection predictors, positivity and explicit assumptions; they are optional sensitivity analyses, not automatic cures. Never impute an unobserved biopsy as no molecular change.

## Multiplicity and outputs

Freeze feature/programme families, window contrasts and multiplicity correction before fitting. Preserve full tested tables, nonsignificant and contradictory effects. Output estimate/SE/interval/effect scale, exact contrast and time definitions, patient/specimen/assay counts, covariates, same-lesion/platform composition, selection limitations, heterogeneity and estimability. longitudinal_support.tsv is observational evidence. No causal treatment effect, parallel-trends assumption, drug ranking or rate constant follows from the response interaction alone.
