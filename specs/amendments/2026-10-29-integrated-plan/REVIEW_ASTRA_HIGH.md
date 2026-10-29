# Astra (gpt-6-astra, high effort) statistical review, 29 Oct 2026

Read-only review of the first draft of AMENDMENT.md. Kept verbatim for the record.

**The amendment is not ready to freeze.** Its overall structure is workable, but the hierarchy, effect-size synthesis, endpoint-sensitivity analysis and B-V claims need correction. B-P should remain unchanged.

This is a read-only review of the requested documents and relevant local admission records. No network access was used and no files were changed. Section references below refer to [AMENDMENT.md](specs/amendments/2026-10-29-integrated-plan/AMENDMENT.md), unless another document is named.

The sample-size constraints are more restrictive than “a few hundred patients” suggests:

| Source | Realistic analytical availability | Consequence |
|---|---|---|
| GSE168204 | 10 admitted patients; SOURCE_BINARY clinical benefit; four sequencing batches; only two dual-ICI patients | Does not currently contribute to the ORR learner. Adjusted analysis is fragile; dual-ICI subgroup is descriptive. |
| Hugo | 26 admitted patients; ORR categories; author FPKM; no SD category in the signed mapping | One ORR study. DCR–ORR sensitivity is structurally zero without SD. FPKM admission does not satisfy A-P2’s TPM contract. |
| Riaz | 51 baseline patients pending admission; the local decision records two NE outcomes, leaving at most 49 ORR-evaluable before other exclusions | Would give at most 75 ORR patients across Hugo and Riaz, before compatibility and independence checks—not three eligible ORR development families. |
| IMvigor210 | 347 candidate baseline profiles; the local search table lists 298 category-labelled profiles, including 68 CR/PR | Potentially valuable, but neither 347 nor 298 is an admitted analytical denominator. |
| Liu | 122 candidate patients | Requires source-of-record, representation, endpoint and overlap admission. |
| Gide | 73 candidate baseline profiles | Requires patient/timepoint reconciliation and regimen-specific eligibility. The local search table’s response totals include more than 73 observations. |

Thus, **36 admitted patients do not constitute one interchangeable development sample**, and adding Riaz does not automatically make A-P2 feasible. A large candidate study also adds only one independent study family; it does not solve small-*k* synthesis.

**1. Is the proposed hierarchy sound?**

**HIGH — §1, “Proposed hierarchy,” “A-PANEL” and “A-P2.”**

The proposed gatekeeping is underspecified and changes the frozen hierarchy. “Each family has its own error control” does not define a gatekeeping procedure: it leaves unspecified whether all, any, or an omnibus set of panel hypotheses must reject, how alpha transfers, and what overall error rate is controlled. BH FDR within discovery families is not interchangeable with confirmatory familywise error control.

The scientific dependency is also unconvincing: a useful predictor need not show endpoint sensitivity, and biological associations remain informative when prediction fails. These are explicitly separate products in the frozen scientific-aim contract.

**Fix:** retain **A-P2 as the single conditional primary**, with its frozen paired AUROC-difference estimand and a two-sided 95% interval. Make A-PANEL and CYT-led A-P1 prespecified secondary analyses; use BH at 5% for explicitly enumerated exploratory programme families. Keep A-DE as discovery. Do not require significance in one branch before estimating another.

If the author instead wants biological confirmation as the primary, make an explicit prospective replacement specifying the exact programme contrast or global hypothesis, population and multiplicity procedure. “Eleven panels are confirmatory” is not a complete primary definition. Holm at familywise α=0.05 is a defensible default for a genuinely confirmatory panel family, but its relationship to other confirmatory claims must also be specified.

At current admission, A-P2 remains unavailable. That should be reported directly; it must not be replaced after results by the most favourable secondary.

**2. Is random-effects meta-analysis valid with k=1–3?**

**HIGH — §1, “A-DE,” meta-analysis and heterogeneity bullets.**

Two studies are the frozen **minimum for attempting synthesis**, not a threshold establishing reliable heterogeneity estimation or generalizability.

Recommended defaults:

| Independent compatible families | Recommended analysis |
|---|---|
| **k=1** | Report the study-specific effect and interval. No between-study τ², I² or future-study prediction claim. |
| **k=2** | Show both effects prominently. An explicitly tentative REML synthesis is permissible under the frozen modified Knapp–Hartung rule; report instability and nonestimability. |
| **k=3** | Same approach; heterogeneity remains poorly determined. Leave-one-study-out results are sensitivity descriptions, not convincing validation. |
| Larger k | Consider moderators only when independent study support and the design matrix justify them. Patient N cannot substitute for study-level replication. |

The frozen method is **modified Knapp–Hartung**, with variance inflation not below the conventional value and *t* degrees of freedom *k−1*. The draft’s generic “Hartung–Knapp when k is small” loses that safeguard. At k=2 and k=3, the corresponding two-sided 95% *t* critical values are approximately 12.71 and 4.30, illustrating the uncertainty.

**Fix:** restore that exact method, including convergence/failure rules. Default to **no prediction interval at k≤3**; report it as insufficiently supported rather than presenting a numerically obtainable interval as established transport. Do not fit cancer/regimen moderators when they are confounded with study or platform. A Bayesian sensitivity with declared heterogeneity priors is possible, but it does not manufacture replication.

**3. Can heterogeneous expression representations be pooled, and which effect size should be used?**

**HIGH — §1, “A-DE,” expression-model and effect-size bullets.**

Per-study analysis is appropriate. The proposed effect-size wording is not: **a log fold change is not a standardized effect**, and negative-binomial log-mean ratios, differences of log expression and Hedges’ *g* are different estimands.

The frozen A-BIO contract expressly prohibits pooling NB log-mean ratios with mean log-expression differences merely because both are log-scaled.

**Fix:**

- Keep the main synthesis within compatible `effect_scale_id` strata.
- For counts, use the declared count-model coefficient and its **unshrunk matching SE**, with appropriate library/composition normalization and offsets. A source library-size field alone is insufficient.
- For continuous measurements, use a declared transformation and limma contrast on that scale. Already logged values must not be logged again; normalized counts must not be treated as raw counts.
- Retain arrays as their own qualified measurement stratum.

For a separately preregistered cross-platform sensitivity, **unadjusted Hedges’ g on qualified continuous expression** is a reasonable default:

\[
g=J(n_R+n_{NR}-2)\frac{\bar x_R-\bar x_{NR}}{s_{\mathrm{pooled,within\ group}}}.
\]

Freeze the transformation, denominator, small-sample correction and sampling-variance method. Do not standardize raw counts or use a limma-moderated variance as though it were the ordinary pooled SD.

Hedges’ *g* measures separation relative to within-study variability; platform noise and population composition still affect it. It does not establish measurement equivalence. Adjusted standardized contrasts require a separate definition and must not be mixed indiscriminately with unadjusted *g*.

**4. Is A-DE feature selection circular for A-P2?**

**HIGH — §1, “A-DE” and “A-P2”; frozen `PREDICTION_ANALYSIS.md`, “Exact learning procedure.”**

Using the same development resource for discovery and model development is not intrinsically circular. **Selecting genes using all development outcomes before cross-validation is leakage into the held-out development folds.**

It also changes the frozen learner: A-P2 currently uses a prespecified common representation with fold-local filtering, not an automatically inherited list of significant A-DE genes.

**Fix — preferred default:** keep the products separate. A-DE produces biological evidence and the B/C handoff; A-P2 follows its existing feature and preprocessing contract.

If A-DE screening becomes part of the learner, explicitly amend the learning algorithm and repeat **the entire screening/meta-analysis procedure inside every inner and outer training partition**. Validation-study outcomes must never select genes. Freeze the selection threshold, maximum feature count and no-selected-genes behaviour before fitting.

An all-development gene list may be used to construct the final frozen model before a genuinely untouched external test, but development performance based on that globally selected list is not unbiased cross-validation. Report these two facts separately.

At present, the three-family grouped-development requirement is unmet for the ORR/measurement-compatible population. Even three families would establish only minimal fold feasibility, with particularly unstable inner tuning.

**5. Are B-MX’s supervised labels and methylation labels defensible?**

**HIGH — §3, “B-MX,” methods bullet.**

A panel-score tertile is circular **if the predictor blocks include the RNA measurements used to calculate that score**. DIABLO could recover the constructed label without demonstrating methylation-related information. Dividing a continuous score into tertiles also discards information and introduces arbitrary cutoffs.

**Fix:** make continuous programme expression the default molecular target. Predict it from methylation and separately justified non-RNA modalities, excluding the target-defining RNA block. Use nested patient-level validation, with all feature selection, scaling, component selection and tuning confined to training partitions. Compare against a simple covariate baseline and methylation-only model.

MOFA+ may remain exploratory, but factor interpretation and factor selection using the same data are not independent validation. For survival/BCR, use a censoring-aware model—such as penalized Cox regression where appropriate—not an ordinary DIABLO event/no-event classification that ignores follow-up. Freeze the endpoint and assess event counts first.

**HIGH — §3, “B-MX,” “methylation-associated or not” bullet.**

Association plus factor loading does not establish methylation control. Factor loading is not independent corroboration when fitted to the same RNA/methylation data, and absence of significance does not establish absence of association.

**Fix:** replace the binary label with:

- **Association supported**, with direction, effect and uncertainty;
- **Inconclusive**;
- **Not estimable or not measured**.

Use direct, prespecified per-cancer models as the default: expression versus a frozen promoter methylation aggregate, with an estimable adjustment set, including source-qualified purity and relevant CNA/composition sensitivities. Report effects on an interpretable methylation scale, for example per 0.1 increase in mean beta. Control BH FDR at 5% across the declared gene–cancer testing family, or declare separate cancer families without claiming pooled FDR control.

Test the full frozen A-derived universe; do not select genes by MOFA loadings and then report ordinary association p-values as if selection had not occurred. Factor loadings should be descriptive support. Preserve positive and negative associations. Use “methylation-associated,” never “methylation-controlled,” without stronger evidence.

**6. Is B-V adequately powered at 9–18 pairs, and are one-sided tests acceptable?**

**MEDIUM — §3, “B-V,” item 1 and gene-set testing bullet.**

These samples support estimation and detection of **large, coherent changes**, not a general validation of the chain.

For orientation, let \(d_z\) be mean within-patient change divided by the SD of changes. An optimistic normal approximation for 80% power gives:

| Complete pairs | One-sided α=0.05 | Two-sided α=0.05 |
|---|---:|---:|
| 9 | \(d_z\approx0.83\) | \(d_z\approx0.93\) |
| 18 | \(d_z\approx0.59\) | \(d_z\approx0.66\) |

These are **hypothetical planning values**, not observed effects or exact small-sample power. Finite-sample *t* testing, multiplicity, missing pairs and noisy measurement increase the required effects. Testing 11 directional predictions with a Bonferroni planning threshold raises the optimistic requirements to approximately 1.15 and 0.81, respectively.

The local cohort note also lists only **seven RNA pairs** for the urothelial study and nine RNA versus eleven methylation pairs for the ovarian study. The intersection with both modalities could be smaller. Eighteen C1D1 samples must not be assumed to mean eighteen usable pairs before linkage and QC.

**Fix:** prespecify a small number of biologically justified, signed programme summaries. Compute one change per patient and test across patients—not across genes as independent replicates. A paired *t* test is a reasonable default under approximately normal changes; prespecify a robust sensitivity. An exact sign-flip test requires a symmetry/exchangeability justification and is not automatically a randomized-treatment test.

A one-sided test is acceptable only with a frozen, defensible direction, score, time window and population. Use Holm correction across the confirmatory prediction family, and report two-sided 95% intervals and opposite-direction findings regardless of the directional test.

If “RNA rises **and** methylation falls” is one conjunctive prediction, require both components to pass an intersection–union test. RNA-only and methylation-only cohorts cannot individually validate that joint prediction.

**7. What conflicts with frozen rules?**

**HIGH — §1, “A-DE,” pan-cancer synthesis.**

An ordinary inverse-variance random-effects model with cancer moderators does **not** automatically implement equal cancer weights. More fundamentally, RC2’s equal-cancer/equal-study rule defines A-P2’s finite-roster estimand; it is not a generic random-effects specification for A-DE.

**Fix:** retain the exact A-P2 weights and required-source failure rule. For A-DE, separately define whether the target is an average over the observed study collection or a random-effects population mean. If an equal-cancer biological summary is wanted, write its explicit marginal contrast and covariance calculation on a common effect scale. Do not call regression software’s default pooled coefficient “equal cancer weighted.”

**HIGH — §1, opening population statement and “A-P2”; §2; §3, “B-V.”**

Restricting discovery to DEVELOPMENT rows is necessary but insufficient. Protection applies to the **entire overlap-connected originating family**, including related arms, longitudinal material and modalities.

**Fix:** add an explicit inheritance clause for `VALIDATION_AND_SPLITS.md`. If the ICI-only arm of GSE343570 or IMmotion150 is reserved for final testing, its related arm/timepoint analyses cannot inform development before the authorized evaluation release. Either assign the family to development or preserve its protection across A, A.1, B and C.

**MEDIUM — §1, endpoint separation.**

The wording correctly separates ORR and SOURCE_BINARY, but SOURCE_BINARY is a provenance category, not one common clinical endpoint. Different duration requirements, assessment criteria and follow-up rules remain different estimands.

**Fix:** freeze endpoint-specific eligibility and compatibility rules. Do not pool distinct clinical-benefit definitions under one binary heading. Retain RECIST/irRECIST provenance; unknown durability is not nonresponse.

**MEDIUM — §0, production/cohort decisions; §3, B-V; §4.**

Parallel A/B production and placing combination-cohort corroboration in B are prospective changes to earlier rules, not statistical errors in themselves. The latest recorded user scope takes precedence. However, the amendment currently cites a decision that still assigns all-combination cohorts outside A/B, while saying ICI-plus-non-ICI cohorts are excluded from “response analyses” despite the proposed B-V response interaction.

**Fix:** explicitly enumerate the superseded process/scope clauses. Define B-V and randomized arm comparisons as named exceptions; keep combinations excluded from baseline ICI-only response synthesis. State that parallel production does not remove shared dependency freezes, protected-family boundaries or release gates. No reversal of the recorded user decisions is needed.

**Other statistical and design findings**

**8. HIGH — §1, “A-P1-wide”: endpoint sensitivity is not a count of significance flips.**

“Significant under ORR, nonsignificant under DCR” does not establish a difference between endpoints. Selecting top genes under ORR also preferentially selects strong ORR estimates, making subsequent attenuation under another endpoint partly a selection effect.

**Fix:** use fixed-score paired endpoint contrasts on identical patients. For CYT and locked programme scores, estimate the change in AUROC with joint patient resampling, retaining original response categories and recomputing both endpoints together. Keep the frozen O/SD/PD decomposition. AUROC itself has no positive/negative sign; define direction using AUC−0.5 or a separately specified expression contrast.

Treat significance/rank flips as descriptive. Keep top-A-DE-gene sensitivity exploratory unless assessed in independent eligible patients. The current 10-patient binary cohort cannot reconstruct SD categories, and Hugo supplies no informative DCR–ORR contrast without SD.

**9. HIGH — §1, “A-DE,” covariates: the 10-patient design can be nearly saturated or confounded.**

Four batches require three indicators. Adding response and two drug-class indicators to an intercept leaves at most three residual degrees of freedom in ten patients, even before further covariates—and the design may not be full rank. Empirical-Bayes shrinkage does not repair treatment/response–batch confounding.

**Fix:** inspect response-by-batch-by-regimen support and matrix rank before fitting. Retain the frozen unadjusted reference, clearly labelled potentially confounded. Fit only an identifiable prespecified adjusted model and report residual degrees of freedom and patient changes. If response is inseparable from batch, mark the adjusted response contrast nonestimable. Do not merge batches because it improves significance. Keep the two dual-ICI patients descriptive.

**10. MEDIUM — §1, “A-PANEL”: eleven registry entries are not necessarily eleven hypotheses.**

M5 consists of separate candidate genes and M6 of regulator expression; they do not automatically constitute two coherent composite scores. Registry membership alone also does not establish a validated scoring method.

**Fix:** freeze the actual hypothesis list: composite programmes, individual M5 genes and individual M6 regulators, including endpoint/context contrasts. Count all tested hypotheses in the appropriate correction. Freeze membership, direction, coverage and missing-feature handling. Retain the explicit custom name for the unweighted Ayers-derived score. Do not average regulators with different functions into a generic activation score.

**11. MEDIUM — §1, “A-DE,” intersection universe.**

A global intersection that includes targeted assays can reduce “genome-wide discovery” to a small immune panel. Changing the intersection across endpoints or sensitivity runs can also make ranking changes reflect coverage rather than endpoint choice.

**Fix:** define a genome-wide assay roster separately from targeted-panel analyses. Freeze an outcome-independent common universe within each compatible synthesis stratum. Endpoint comparisons must use the same gene universe and patients. Report excluded coverage and effective study support per gene.

**12. MEDIUM — §3, “B-MX,” layers and gene universe.**

TCGA project size is not the number of patients with matched RNA, methylation, miRNA, RPPA and ATAC. RPPA/ATAC coverage and specimen matching can substantially reduce N. Moreover, genes do not map one-to-one onto miRNAs, proteins, CpGs or accessible regions.

**Fix:** make matched RNA–methylation the core. Report patient/specimen counts and missingness for every modality intersection. Add modalities only through explicit mappings and adequate coverage; do not require a complete five-omics intersection by default. Freeze block scaling, feature mappings, factor/component tuning and missing-data handling.

If A-DE yields no FDR discoveries, retain the prespecified panel/regulator universe and report that result. Do not relax A’s threshold to populate B-MX.

**13. HIGH — §3, “Prostate transfer”: “which programmes are low” lacks a reference.**

Low relative to what—other PRAD tumours, normal prostate, or ICI responders in other cancers? These are distinct contrasts. Cross-cancer score differences may reflect lineage, platform, disease stage and cellular composition rather than an immune deficit.

**Fix:** define the reference population and measurement scale before analysis. Default to continuous within-PRAD associations; use a prespecified matched normal or external reference only for a separately justified deficit contrast. Do not infer clinical ICI responsiveness from TCGA scores.

“HLA class I loss” also needs a measurement definition. Low RNA expression is not HLA-LOH, mutation, deletion or protein loss. Use the published HLA-I study as a biological benchmark, not a guaranteed positive result. The local novelty note cites the [primary HLA-I study](https://pubmed.ncbi.nlm.nih.gov/36050516/).

**14. HIGH — §3, “B-V,” item 1: the proposed comparisons do not generally identify an epigenetic-drug effect.**

The ovarian, urothelial and METADUR follow-up samples occur after exposure to both drugs. Their changes cannot isolate the epigenetic component. Entinostat’s lead-in separates it temporally from ICI, but an uncontrolled before–after comparison still cannot exclude time, biopsy-site, composition or selection effects.

**Fix:** distinguish:

- **Change during an epigenetic-only lead-in**;
- **Change during combination treatment**;
- **Randomized incremental treatment effect**.

Prespecify biopsy timing/site and attrition reporting. Use the first two as measured corroboration with explicit attribution limits.

Also separate drug-class hypotheses. HDAC inhibition does not imply obligatory CpG demethylation. For DNMT inhibitors, test qualified promoter hypomethylation separately from transcriptional restoration. Freeze gene-specific desired directions: stromal exclusion genes and negative response-associated genes should not all be predicted to rise. The frozen B analysis already preserves alternative domain-level mechanisms, supported by [Guo et al.](https://doi.org/10.1016/j.cell.2023.05.028).

**15. HIGH — §2 and §3, “B-V,” item 2: randomization alone does not validate every molecular contrast.**

A baseline arm difference is not a treatment effect. Response-stratified comparisons can condition on a post-randomization variable, and analysis restricted to patients with follow-up biopsies can lose randomization’s protection.

The local cohort note reports approximately **33 baseline transcriptomes**, with 15 putative PR outcomes, and only **21 paired biopsies: 10 versus 11**. These are the relevant candidate denominators—not all 45 trial patients or all expression columns.

**Fix:** for molecular arm effects, default to follow-up score ANCOVA adjusting for baseline score and applicable randomization strata, with a declared missing-biopsy estimand and sensitivity analysis. Verify randomization and endpoint provenance before causal wording.

For response effect modification, prespecify **one continuous baseline score**, treatment, and their interaction. Firth logistic regression with a profile penalized-likelihood interval is a reasonable sparse-data default. Do not dichotomize the score or screen 11 interactions. Keep this exploratory: a null interaction at this N is not evidence of no effect modification, and the interaction is not itself the trial’s average treatment benefit.

**16. MEDIUM — §3, “B-V,” opening sentence: prospective registration is not untouched replication.**

The novelty review already discusses published positive and negative trial findings. Freezing a new gene set before opening patient-level matrices is useful, but does not erase knowledge of published results.

**Fix:** register the analysis prospectively from this point, disclose known trial results and distinguish metadata/publication exposure from patient-level molecular exposure. Call this an externally specified secondary analysis of existing trials unless the stronger independence claim is demonstrably justified. Do not select cohorts or directions based on known favourable findings.

**17. MEDIUM — §3, “B-P unchanged”: preserve its measurement and validation isolation.**

B-MX must not use TCGA exploration to revise B-P’s endpoint, promoter construction, covariates or analysis after performance inspection. Candidate CPC-GENE counts also overstate the presently plausible adjusted validation sample: the frozen record identifies 114 code matches, 73 stronger assay bridges and 72 with Qpure before remaining gates—not 210 eligible patients.

**Fix:** freeze B-P’s P/U/Q, specimen, purity and preprocessing contracts separately. Preserve TCGA-only fitting and untouched CPC-GENE evaluation. Plan precision for the actual eligible external population and paired prediction errors. Positive B-MX or B-V findings cannot replace a null or unavailable B-P.

**18. LOW — §1, “A-EQ”; supporting novelty note, Claims 2–4.**

Equation export is reproducibility, not an additional validation result. Weighted logistic outputs need not be calibrated response probabilities. Similarly, “no paper found” in a bounded literature search does not establish novelty, and adding MOFA/DIABLO does not establish a new biological inference.

**Fix:** export the complete transformation and linear predictor, clearly distinguishing score from calibrated probability. Omit symbolic regression by default at this sample size; if retained, treat it as another development algorithm subject to the same nested-selection rules. Describe novelty as a proposed contribution pending the unresolved comparisons. Retain PK/PD as future work.

**(a) Recommended Paper A hierarchy.** Keep A-P2 as the single formal primary, conditional on an adequate set of independent ORR-compatible development families and a protected, sufficiently precise external-test roster; otherwise report it unavailable. Present locked programme associations as the principal prespecified biological secondary product, followed by CYT-led paired endpoint sensitivity and its locked-panel extension. Keep genome-wide A-DE as FDR-controlled discovery and top-discovery-gene endpoint analyses exploratory unless independently evaluated. A-EQ is the reproducibility export of the same frozen predictor. Biological reporting should proceed under its own release without depending on predictive success; none of these branches should become primary because another branch is null.

**(b) Plain-language summary**

- The plan is workable, but it is not ready to freeze.
- The admitted cohorts cannot yet support the proposed prediction study.
- Different response definitions cannot be combined just to increase sample size.
- Two or three studies give weak evidence about consistency across settings.
- Gene selection must happen inside model-training folds.
- Methylation associations do not prove that methylation controls a gene.
- Nine to eighteen pairs mainly detect large changes; negative findings will often be inconclusive.
- Most combination biopsies cannot isolate the epigenetic drug’s effect.
- Keep one primary question, protect independent tests, and report secondary findings honestly.