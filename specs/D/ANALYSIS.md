# D proposed statistical contract

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** The formula is fixed as a proposal; the compatible prostate dataset, full ordered gene space, transform, independent-unit structure and precision target remain unresolved. These must be settled before preregistration and inference.

## Primary estimand

Target population: the finite set of eligible, independently measured prostate cell-context responses to **checkpoint-supported chemical drug–dose labels**, at the compatible documented collection duration. The task is context transfer for represented treatments, not discovery of effects for categorical labels absent from the checkpoint.

Let D be the frozen eligible drug set; C_d the unique eligible condition set for drug d (dose × prostate context × collection duration); R_c the independently assigned biological replicate units for condition c; and G the complete, frozen, ordered checkpoint gene-output space. A technical well is not automatically a biological replicate. Let T be the exact documented checkpoint-compatible expression transform, applied without fitting to held-out responses. Its identity and parameters must be recovered at G2; `int_counts=false` alone is insufficient.

For each biological replicate r and gene g, `mu_crg` is the arithmetic mean of T-expression across measured cells in that replicate. `mu_0crg` is the arithmetic mean of corresponding control-replicate means, giving each independent matched control replicate equal weight. Control membership is fixed by the study design and is stored explicitly. Observed change is `delta_crg = mu_crg - mu_0crg`.

The State prediction uses the exact matched control-replicate identities defining `mu_0crg`. Run prediction on each control replicate separately; compute its predicted treated cell mean and basal cell mean, then average both across those replicates with the same equal-replicate weights used for the observed control term. Their difference is `S_crg`. Do not pool unequal cell counts and thereby alter the control mixture between truth and prediction. The sealed manifest fixes these identities/weights; an upstream interface that cannot preserve them fails compatibility. No observed treated expression enters inference. A single declared inference seed, 42, defines the primary prediction; alternative-seed variability is secondary computational uncertainty.

**One primary comparator:** supported-drug–dose–duration mean response in other auditable transition-training contexts. For the exact label and duration of c, let K_c be eligible non-test training contexts; each context's change is the equal-replicate mean measured treated–matched-control difference. Define `B_cg = (1/|K_c|) sum_k mean_r(delta_train,krg)`. Neither prostate test response nor validation/test checkpoint rows enter B. Empty K_c blocks that condition; it cannot silently switch to no-change or a neighbouring dose. A primary test with no remaining eligible conditions cannot run.

For model m in {B,S}, define `L_m(cr) = (1/|G|) sum_g (delta_crg - m_crg)^2`, taking `B_crg=B_cg`. The single primary endpoint is:

`theta = (1/|D|) sum_d [ (1/|C_d|) sum_c [ (1/|R_c|) sum_r {L_B(cr) - L_S(cr)} ] ]`.

Positive theta favours State. Units are squared units of T-expression. Genes receive equal weight; each drug receives equal weight, then conditions within a drug and biological replicates within a condition receive equal weight. Cell counts never determine condition weights. Report both constituent losses alongside the gain. No test-derived per-gene standardisation, inverse-variance weighting, percentage conversion or effect-size-selected feature subset changes this estimand.

## Hypothesis, uncertainty and precision

Proposed primary question: whether the benchmark estimate supports `theta > 0`. It is a comparative accuracy estimand, not a claim that each drug is accurate. One primary endpoint means no primary endpoint multiplicity adjustment. Secondary inferential families, if activated, use BH FDR 0.05 within a preregistered family; report unadjusted effect estimates and adjusted values together. FDR controls only the specified family, not undisclosed analyses.

The finite-benchmark point estimate is defined once valid data exist. Population uncertainty is **not** solved by resampling cells. Before freeze, map independent experiments, shared controls, donors and plates; identify the highest independent assignment blocks. Proposed interval method is 2,000 paired hierarchical bootstrap draws: retain paired State/baseline errors, resample drug clusters for an expressly defined drug-population interpretation, and resample independent experiment blocks within sampled drugs while keeping shared-control-linked observations together. The actual design may require crossed-block handling; if the selected dataset does not support this hierarchy, the inference design must be amended before outcomes. Do not publish this interval under an incompatible structure.

No numeric precision or minimum-drug target is asserted now. G5 requires a supervisor/reviewer-visible smallest scientifically meaningful gain `delta_min`, desired interval half-width `h_target` and variance/cluster assumptions from independent development or replicate evidence. Run the precision assessment on that design before test access. If it cannot support the intended interpretation, report a finite-benchmark descriptive analysis or propose narrowing; neither is automatically an accepted replacement for D.

## Inclusion, covariates and missingness

Include only verified human prostate contexts with measured per-cell expression, provenance, valid biological units, matched untreated/basal controls, exact drug mapping and compatible exposure metadata. Required feature ordering/transform, baseline training effects and overlap status must pass first. Exclude technical QC failures using source-supported criteria fixed without test-response effect magnitudes; no deletion for a null or unexpected response.

Unknown labels, controls, transformations, timings, identity and overlap are distinct machine-readable ineligibility reasons. Missing outcomes are not imputed; missing mandatory metadata makes the affected condition pending/ineligible, with denominators disclosed. Record every candidate before exclusions and keep a full attrition table. A failed model output after eligibility is a model/run failure, not retrospective data exclusion: retain it in coverage accounting, withhold complete-benchmark theta and repair/review before rerun.

The primary analysis has no fitted clinical or purity covariates. Context, dose, duration, study, plate and replicate define eligibility, control pairing and grouping. Read-depth/cell-quality effects must be handled by the checkpoint-compatible preprocessing contract or prespecified sensitivity analyses, never by fitting to the test outcome. The model and baseline receive equivalent permitted training information; extra baseline tuning uses development data only.

## Secondary/exploratory endpoints

Prespecified secondary: no-change baseline; global training-average baseline; independently tuned ridge/nearest-neighbour comparator if valid training inputs exist; repeat-seed variability; paired observed-replicate reproducibility; error by drug/context and effect magnitude. A fixed immune-program subset may examine biological relevance only after B/C handoff provenance and feature coverage are frozen. No outcome-selected rescue panel or redefinition of the primary feature space. Bulk/L1000 rank concordance, if separately justified, is exploratory external transfer and cannot replace theta's native-expression benchmark.
