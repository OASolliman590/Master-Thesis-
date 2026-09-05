# A proposed statistical contract

Status: proposed endpoint choice; no score computed. CYT is selected for a transparent assayable anchor, not because it is known to perform best. The published two-gene concept is from Rooney et al., Cell2015, DOI10.1016/j.cell.2014.12.033; the exact input-scale and analysis choices below are this protocol's proposals.

## Unresolved primary choice

Two competing primary designs remain proposed: (A-P1) fixed-CYT endpoint sensitivity below, and (A-P2) external incremental discrimination of a discovered responder signature in DISCOVERY.md. Exactly one must be selected before confirmatory scoring; the other remains a declared secondary analysis. Full discovery and prostate transport remain in scope as conditional modules, not cancelled because A-P1 is specified first. No primary approval is inferred from this draft.

## A-P1: proposed fixed-CYT primary endpoint

Patient score s_i = sqrt(TPM_GZMA,i × TPM_PRF1,i), with nonnegative TPM and both genes present. Zero abundance is a valid zero; missing is not zero. Higher score predicts the positive outcome without post-hoc sign flips. For a labelled cohort j, AUC_j(s,Y) is the mean over positive–negative patient pairs of I(s_positive>s_negative)+0.5 I(equal).

Delta_j = AUC_j(s,Y_DCR) − AUC_j(s,Y_ORR), computed on exactly the same baseline patient set. ORR means CR/PR positive, SD/PD negative; DCR means CR/PR/SD positive, PD negative. This is the effect of changing the outcome definition on discrimination, not a causal treatment effect and not evidence DCR is a better label.

For K eligible cancers, with J_k eligible independently sourced cohorts in cancer k:

Delta_primary = (1/K) Σ_k [(1/J_k) Σ_j Delta_j].

The A-P1 primary cohort set requires at least one O (CR/PR/PRCR), one SD and one PD patient, plus all DATA.md eligibility gates. This is mathematical estimability, not adequate precision. Freeze source-study membership and numeric weights after metadata/assay admission and before score–outcome analysis. Weights sum to one and are independent of measured performance. The estimand concerns this finite cohort collection, not all cancers. If only one cancer qualifies, do not call the result cross-cancer. A separately frozen all-cohort sensitivity additionally includes eligible O/PD cohorts with no SD, whose Delta is structurally zero; recompute and archive that sensitivity's own weights before scoring.

If a frozen cohort later fails parsing, pairing or score coverage, the primary aggregate is incomplete/nonestimable: do not drop it and renormalize. Repair a factual import error with an audit trail or prospectively amend the manifest, disclosing prior exposure. Any reduced-set result is separately labelled sensitivity and cannot replace the frozen primary result.

To distinguish endpoint composition from score separation, report nO,nS,nP and the pairwise category concordances A_OS,A_OP,A_SP, with half credit for ties. Algebraically, AUC_ORR=(nS A_OS+nP A_OP)/(nS+nP), and AUC_DCR=(nO A_OP+nS A_SP)/(nO+nS). Consequently Delta can change with category proportions even when those concordances do not. These components are descriptive interpretation, not extra primary tests.

Primary hypothesis is two-sided Delta_primary=0. One primary contrast needs no across-signature multiplicity correction. Estimate a 95% interval; do not label overlap with zero proof of equivalence. A directional hypothesis or material-effect bound may only be added before scoring with its rationale documented.

## Uncertainty, replication and precision

Resample patients with replacement within each source cohort and canonical response stratum O/SD/PD, retaining each observed stratum count. O combines CR, PR and source-combined PRCR; use these same three strata regardless of source reporting granularity. Keep both labels and the score together and recompute every cohort/cancer mean with the original frozen weights. Proposed interval is the percentile interval at probabilities0.025/0.975, using NumPy `quantile(method="linear")`. Use2,000 replicates and a recorded PCG64 seed proposed as20260905; assess numerical stability on synthetic precision scenarios before freeze. These numerical values are proposals, not literature-derived thresholds. [NumPy2.4 quantile API](https://numpy.org/doc/2.4/reference/generated/numpy.quantile.html), checked5 September2026.

This interval targets uncertainty conditional on observed category composition. An undefined stratum-bootstrap AUC in an admitted O/SD/PD cohort is an implementation/data failure and invalidates the interval. No numerical p-value is specified; report the signed estimate and95% percentile interval against the proposed two-sided zero hypothesis, without calling overlap equivalence. The unstratified sensitivity resamples patients within cohort without fixing categories. If any replicate makes any frozen cohort AUC undefined, report the invalid fraction and mark that sensitivity interval nonestimable; do not discard those replicates, impute zero, or renormalize cohort weights. Report the valid replicate distribution descriptively only if clearly labelled conditional-on-validity, not as the unconditional95% interval.

Show each cohort and cancer estimate, category counts and intervals. Leave-one-cohort/cancer-out summaries assess influence on the fixed-score meta-summary; they are not classifier cross-validation. Independent replication means a separate originating study with the same locked score/mapping, not a second release or repeated biopsy. Label same-cancer, comparable-regimen replication separately from cross-cancer/regimen transport. A melanoma-to-urothelial comparison changes several contexts simultaneously and cannot identify which caused disagreement. Within-cancer reproducibility requires qualifying separate studies of that cancer; its availability is not established. Reconcile exposure and trial overlap before designating replication sets.

A current metadata ceiling of49 labelled baseline GSE91061 patients and89 labelled GSE176307 records does not prove power. Only16 and4 records respectively are labelled SD, and the latter cohort's timing/deduplication remains open. Before readiness, calculate anticipated interval widths using actual admitted category counts and a documented range of plausible score separations; simulated data are precision scenarios, never evidence of biology. Record achieved precision after analysis without promising statistical significance. The material precision target remains a scientific decision; no invented minimum N is accepted.

## Covariates and secondary analyses

Primary AUC is marginal within each cohort, with cancer-balanced aggregation. Do not pool cohort-normalized expressions into a universal classifier. Record tumour type, treatment/line, prior ICI exposure, biopsy site, sequencing platform and assessable clinical covariates. Conditional discrimination/regression is secondary and only when covariates and sample sizes permit; do not adjust for post-treatment intermediates.

Secondary fixed signature panel: IFN-gamma/TIS and other documented scores after source implementation, required genes, units and development-cohort overlap are verified. Freeze explicit score IDs/versions, genes/weights/direction, source implementation, eligible cohort set, estimand and test method in `secondary_registry` before running A03. No unnamed "other scores" may enter a confirmatory family. For secondary endpoint-sensitivity tests, use the same paired Delta contrast per frozen signature; list any additional duration/clinical endpoint tests as separate named families. Panel identity and source-correct secondary test methods remain admission gates, not permission to choose winners from data. For each frozen family with M tests, keep M fixed; enter computational p=1 for nonestimable tests solely in the BH calculation while publishing their biological estimate/p-value as null with a reason. Do not present that placeholder as observed evidence. Report all M entries. TIDE server output is not interchangeable with a locally approximated expression average.

Durable benefit is a separate endpoint requiring follow-up, progression and the source's exact duration/boundary definitions. PSA decline, RECIST response and survival are not substitutes. Do not combine binary-only datasets into the primary by guessing SD.

The retained discovery branch is specified in DISCOVERY.md with a competing primary choice, regularised learner, training-only processing, cohort-held-out validation, uncertainty and a versioned B/C handoff. Its execution is conditional on admitted data and reviewed design, not on positive CYT results. No deep model is specified.

## Prostate claim boundary

Untreated PRAD score distributions, gene coverage and association with independently motivated immune/composition measures characterize molecular transport only. Comparing two RNA-derived scores with overlapping genes is circular corroboration unless explicitly quantified. COMBAT has a sequential regimen and a small enriched-biopsy subset; final-trial responses cannot be attributed to nivolumab from this design. Any prostate clinical analysis reports its own documented endpoint and regimen, independently from Delta_primary.

TRANSPORT.md defines cohort-specific admissibility and exact molecular/clinical transport statistics. No untreated PRAD statistic is a substitute for clinical response validation.
