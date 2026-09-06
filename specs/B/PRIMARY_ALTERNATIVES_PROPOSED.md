# Paper B primary alternatives — historical comparison after B-P selection

**Primary decision, 6 September 2026:** the user selected B-P external prediction improvement as the single primary. This file preserves the earlier alternatives analysis; B-R is historical, unexecuted and not a co-primary or automatic fallback. [Decision record](../../docs/decisions/B_PRIMARY_BP_20260906.md).

**Measurement evidence, 6 September 2026:** [verified source facts refining proposed platform, promoter and cellularity contracts](../../docs/research/B_MEASUREMENT_CHECKPOINT.md) refine shared gates. Annotation and measurement choices remain unselected.

**Source correction, 6 September 2026:** the CPC portal `WGS_BASED_PURITY_ESTIMATION` field matches original WGS/OncoScan SNP-call agreement, not tumour purity. It must not populate a purity covariate or count toward purity availability. Genuine cellularity alternatives require their own method/specimen/scale validation. [Verified correction](../../docs/research/B_PURITY_FIELD_CORRECTION.md). The original-study bridge supports 73 candidate patients at study-protocol level, with Qpure present in72; this is not final eligible N. See [specimen evidence](../../docs/research/B_SPECIMEN_RESOLUTION.md) and [updated novelty comparison](../../docs/research/B_NOVELTY_2026.md).

**Historical proposal snapshot, 6 September 2026.** The original local proposal is preserved under `planning/next_evidence`; this revision incorporated the independent statistical correction. The later B-P decision supersedes its undecided status without approving B-R inference or changing unresolved shared measurement gates.

**Historical comparison, not the current decision record.** This document used the predictive proposal and completed annotation audit to compare options. The drafting step made no scores or models. Statistical procedures below remain unexecuted proposals, not findings or claims that the cited biological papers validated these exact procedures.

The substantive choice is between **a model that transports useful predictive information** and **a molecular relationship that recurs in independent prostate specimens**. The latter reduces calibration and whole-transcriptome mapping dependencies. It does not make missing purity, ambiguous specimen pairing or inadequate external precision disappear.

## 1. Direct comparison

| Aspect | B-P: selected external-prediction primary | B-R: historical replicated-association alternative |
|---|---|---|
| Main question | Does promoter methylation improve prediction of a fixed antigen-presentation expression score beyond age, grade and purity in CPC-GENE, after fitting only in TCGA? | Is at least one predefined promoter–cognate immune-gene expression association present in the same direction in both TCGA and CPC-GENE after the predefined adjustments? |
| Primary target | External paired `Delta_R2=(SSE_baseline−SSE_extended)/SST` for two frozen ridge predictors. | Maximum directionally shared partial rank-correlation magnitude across a frozen gene family, with one multiplicity-controlled global replication test defined below. |
| Endpoint | Proposed eight-gene mean within-sample percentile-rank score over a frozen common gene universe U. | Eight separate cognate gene abundances form one prespecified hypothesis family; the proposed composite remains a secondary endpoint. |
| External use | Evaluate frozen predictions; no external fitting/recalibration. | Estimate each association independently within CPC. This is external association replication, explicitly not validation of a frozen prediction model. |
| Key extra requirement | Transport of the exact score scale, gene universe, covariates, model calibration and predictor relationships. | Comparable gene/probe measurement and covariate constructs; identical numeric expression calibration is unnecessary. |
| Strongest warranted positive claim | Adding the specified methylation measurements reduces external prediction error relative to the specified baseline in the eligible population. | The specified methylation/expression relationship recurs in independently recruited eligible prostate specimens under the stated adjustment models. |
| Neither can establish | Tumour-cell causal silencing, ICI benefit, drug efficacy, or a substitute for the registered wet lab. | Same limitations. |

Both alternatives retain the wider Paper B scope: immune-program association, broader TCGA discovery, within-prostate immune-state contrasts, signed locus/domain annotation, composition/CNA sensitivities, the secondary PRAD/LUAD contrast and the B-to-C molecular handoff. Selecting a primary changes which claim carries the manuscript; it does not approve deleting those modules.

## 2. Exact proposed B-R estimand

For this concrete comparison only, let the fixed candidate family be

`G={HLA-A,HLA-B,HLA-C,B2M,TAP1,TAP2,PSMB8,PSMB9}`, with `m=8`.

These genes are a proposed literature-informed family, not an accepted primary signature. If the user prefers a different biological family, its membership and resulting multiplicity must be frozen before the external association analysis. There is no outcome-based gene replacement.

For each cohort `c` separately, in its prespecified eligible patient population:

- `X_cg`: mean promoter beta for gene g using the frozen common probe list and coverage rule.
- `E_cg`: the unambiguously mapped cognate gene's measured abundance on the native gene-level expression platform.
- `R(X_cg)` and `R(E_cg)`: within-cohort midrank percentiles, `(midrank−1)/(n_c−1)`. Ties receive mean ranks. These are ranks **across eligible patients for one gene**, unlike B-P's ranks across genes within one patient.
- `Z_c`: the prespecified adjustment design below.
- Residuals `u_cg` and `v_cg`: population linear-projection residuals of the two percentile variables on `Z_c`. Define `rho_cg=Corr(u_cg,v_cg)`. For a population definition, use the cohort-eligible mid-distribution H(t)=P(T<t)+0.5 P(T=t), then its population linear projections. The empirical estimator uses cohort-specific midranks and ordinary least-squares projections. Its affine rank convention with an intercept preserves the partial correlation; the inferential method must account for the estimated ranks.

This is an explicitly defined **covariate-adjusted rank association**, not a nonparametric proof of conditional independence. Linear covariate adjustment may leave residual confounding or miss nonlinear effects.

Define the shared directional association for each gene as

`gamma_g = max{min(rho_TCGA,g, rho_CPC,g), min(−rho_TCGA,g, −rho_CPC,g)}`,

and the single primary population estimand as

`Gamma = max_{g in G} gamma_g`.

For concordant nonzero correlations, `gamma_g` is the smaller absolute correlation across cohorts; opposite directions yield a negative value, and a zero association in either cohort yields no positive replicated signal. The primary scientific hypothesis is **`Gamma>0`: at least one fixed gene has a same-direction association in both cohorts**. This is a concrete global hypothesis, not permission to call all eight genes replicated.

Report the full 8-by-2 table of correlations and intervals, `Gamma_hat`, and the primary global p-value. A positive result means at least one relationship replicated; if only one does, the title/abstract must say so. The family maximum can overstate the magnitude of the strongest signal through selection, so it must not replace the unselected per-gene estimates.

## 3. Unit, eligibility and adjustment

The independent unit is a **patient with one source-verified paired RNA/methylation tumour specimen or focus**, within the source cohort's actual disease setting. No metastatic/ICI-treated target population is inferred from these primary-prostate samples. Preserve case, specimen, focus, aliquot, GSM and reanalysis origin in the linkage manifest.

Use the current B specimen policy: verify biological identity first, apply assay QC, then a deterministic source-ID tie-break among genuinely equivalent eligible specimens. Average only proven technical replicates under a fixed rule. Unresolved different foci cannot be averaged or paired by patient-code resemblance. The 300 old reanalysis links are provenance, not new replication cohorts.

Proposed primary `Z_c` includes an intercept, age in years, Gleason categories <=6/7/>=8 and same-specimen non-RNA tumour purity on [0,1]. Include fixed indicators for independently documented expression assay/platform groups when more than one occurs within that cohort, with a frozen reference level; this requires actual provenance, not an invented batch label. Both X and E projections use the same Z. Report design-matrix rank, covariate support and residual degrees of freedom; non-identifiable designs do not yield an eligible primary estimate.

The **constructs and categories must match**, but coefficients are fitted separately. Different purity algorithms need evidence that they measure a sufficiently comparable construct and a sensitivity analysis restricted to a verified common method where feasible. Separate fitting reduces the need for identical covariate calibration; it does not remove measurement-error confounding. Gene-level copy number remains a mechanistic sensitivity requiring same-specimen data. Its absence prohibits an independence-from-CNA claim.

For the concrete primary proposal, use one complete eligible patient set per cohort for all eight genes, all required aggregates and Z, fixed before any association is calculated. This keeps the eight estimands tied to the same cohort target population. Gene-specific complete-case analyses can be labelled secondary; they cannot quietly replace the primary population. An undefined/constant gene or empty promoter set prevents this exact family from being fully executable and triggers a recorded amendment, not outcome-guided omission.

Original clinical mapping supplies **114 candidate codes, including73 with stronger original-study support and Qpure present in72 of those73**, before specimen/QC checks; none is an accepted N. The alternative therefore does not inherit all 210 metadata-paired codes as its adjusted validation sample. If comparable purity remains unavailable, an unadjusted or age/grade-only primary would be a *separate material choice with weaker claims*, not an automatic fallback.

## 4. Measurement, platform and missingness contract

Freeze gene-ID mapping, annotation build/transcript policy, promoter definition, mask, probe membership and aggregation before viewing CPC associations. Common probe availability can be checked from assay metadata. Eligibility based on finite values/detection p-values is allowed only under previously specified QC rules and an access log; effects and signs cannot choose probes.

The current B 95% TCGA probe-coverage and 80% specimen aggregate-coverage thresholds remain proposals, not accepted defaults. If retained, use TCGA methylation-only QC to freeze final eligible probe lists before CPC analysis and apply the same lists externally. Require at least one retained probe per gene. Different probes contributing to individual means can change what the aggregate measures; report contributing-probe counts and a prespecified complete-probe sensitivity rather than treating variable coverage as harmless.

The new audit provides an executable annotation candidate: pinned GENCODE v36 hg38 mappings and the complete 202209 Zhou mask. Under an **inspection-only** +/-1.5 kb window around any matching protein-coding TSS, unmasked candidates number 3/8/12/14/83/75/82/126 for HLA-A/HLA-B/HLA-C/B2M/TAP1/TAP2/PSMB8/PSMB9. These are not CPC-confirmed usable features and are not the manufacturer TSS200/TSS1500 definition currently proposed in B. Choosing between these definitions must be explicit. [Annotation audit summary](../../docs/research/POST_M1_EVIDENCE.md), [Zhou et al., DOI 10.1093/nar/gkw967](https://pmc.ncbi.nlm.nih.gov/articles/PMC5389466/).

B-R uses each gene's abundance directly and therefore does **not require a common whole-transcriptome scoring universe U for its primary**. It still requires correct gene-specific array mapping, HLA specificity and meaningful variation. Within-cohort ranks tolerate monotone scale differences; they do not remove array-probe bias, assay noise, processing differences or specimen-composition effects. Preserve TCGA SeSAMe and CPC dasen processing provenance. No joint ComBat or cross-cohort quantile harmonization is needed for this proposed primary.

Native missing beta remains missing, never zero. No primary aggregate or covariate imputation is proposed. Report exclusions by cohort, platform, reason and patient characteristics; complete-case association applies to the resulting eligible population. Missing-not-at-random bias remains possible. Existing public gene-row coverage is not proof of sample-level measurement quality. [GSE107298](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107298), [GSE107299](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107299), [GDC methylation documentation](https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Methylation_Pipeline/).

## 5. One replication test, multiplicity and uncertainty

For each gene and cohort, the candidate rank regression is `R(E)=a+b R(X)+Z_nonintercept eta+error`. Its slope has the same sign and zero as the partial correlation when both residual variances are positive, but is not the correlation magnitude used in Gamma. Export the two separately.

**Correction after independent statistical review:** the earlier HC3 plus residual-df Student-t proposal is withdrawn from this candidate. Empirical-rank uncertainty requires specifically justified inference; ordinary sandwich/leverage corrections do not supply that justification. Chetverikov and Wilhelm derive rank-aware inference including covariates and ties. The documented `csranks` 1.3.0 `lmranks` method is a candidate, with explicit midrank `omega=0.5`, complete-case filtering before ranks, and its documented asymptotic inference rather than an invented residual-df t rule. No package installation, runtime validation, one-sided implementation or finite-sample calibration has passed. Those gates must close before the component p-values below are used. This correction does not select B-R over B-P. [Primary methods preprint](https://arxiv.org/abs/2310.15512), [official package documentation](https://danielwilhelm.github.io/R-CS-ranks/reference/lmranks.html), [independent review](../../docs/reviews/B_ASSOCIATION_STATISTICAL_REVIEW.md).

For each gene `g` and direction `s` in {positive, negative}, calculate one-sided p-values `p_TCGA,g,s` and `p_CPC,g,s` for association in that direction. Define

```text
p_rep,g,s = max(p_TCGA,g,s, p_CPC,g,s)
p_global = min(1, 2*m * min_over_g,s(p_rep,g,s))
```

Reject the single primary null at `p_global<=0.05`. The maximum is an intersection–union test: both cohorts must support the specified direction. The factor `2*m=16` Bonferroni adjustment covers eight genes and both directions, including a direction discovered in TCGA. This is conservative and does not require independent gene tests; it prevents choosing whichever methylation sign looks desirable. Its validity depends on valid component p-values and prespecified eligibility/analysis. Do not substitute nominal significance in one cohort plus a matching external sign.

Report individual adjusted directional replication p-values, all cohort estimates, and both directions. Do not claim BH-FDR control from this Bonferroni procedure. Broader exploratory gene/probe tests form separately frozen families with their own multiplicity rules; they cannot borrow this primary family's error control.

For descriptive effect uncertainty, propose 2,000 patient bootstrap resamples independently within each cohort, recomputing ranks and adjustment fits, with PCG64 seed 20260906, percentile 2.5%/97.5% quantiles using the linear quantile convention. These are **pointwise**, not simultaneous or selection-adjusted intervals and do not decide primary replication. Keep rank-deficient or constant-variable bootstrap draws as invalid, report their fraction, and do not hide them by silently redrawing until success. The handling threshold for unstable interval estimation must be frozen before execution. If a confidence bound for selected `Gamma` is required, add a reviewed simultaneous-inference design before analysis rather than interpreting the maximum of pointwise intervals as one.

Before committing to the primary, set a meaningful minimum shared association magnitude and a desired precision target from scientific/design reasoning; no such target or adequate power has yet been established. This requirement remains even though the exact zero-association null above is specified.

## 6. Validation, nulls and broader thesis scope

CPC-GENE is one independent validation cohort only after recruitment/reuse and specimen provenance are checked. Old/expanded GEO series and cBioPortal copies are not extra cohorts. Freeze the complete B-R analysis before computing external associations. TCGA may supply independently declared discovery modules, but post-CPC changes create a new exploratory version.

Interpret outcomes literally:

- A positive global test supports at least one directionally replicated association within this family and these adjusted populations. It does not show every gene is regulated, that methylation is causal, or that an intervention will restore immunity.
- No replication plus valid gene-specific intervals can constrain each named relationship. A family-wide claim that no shared effect reaches a chosen meaningful magnitude needs a separately justified simultaneous bound or equivalence-style test; the proposed pointwise intervals do not establish that claim for Gamma.
- No replication with wide intervals is inconclusive. Failure in the small or noisy external set is not proof of no biology.
- Opposite directions are heterogeneity requiring assay, composition and biological explanation; they are not repaired by dropping the inconvenient cohort or redefining “silenced.”

Keep positive and negative associations, and retain the Guo hypomethylated-domain mechanism as a competing explanation rather than forcing universal promoter hypermethylation. Sparse 450K domain overlap remains an annotation/proxy, not a new whole-genome PMD call. [Guo et al., Cell 2023, DOI 10.1016/j.cell.2023.05.028](https://doi.org/10.1016/j.cell.2023.05.028).

The eight genes' pathway membership is supported by structural, transporter, B2M-loss and immunoproteasome studies summarized in the annotation audit; their expression composite is not itself a validated clinical assay. Retain the composite as a prespecified secondary program analysis if its U/mapping gates close. Single-sample scoring precedent does not prove cross-platform invariance of this custom program. [Foroutan et al., 2018, DOI 10.1186/s12859-018-2435-4](https://doi.org/10.1186/s12859-018-2435-4), [Kincaid et al., 2012, DOI 10.1038/ni.2203](https://pmc.ncbi.nlm.nih.gov/articles/PMC3262888/).

## 7. B-to-C handoff under either primary

Retain the **TCGA-discovery-only signed disease query** contract. Its selection universe, expression contrast, orientation, effect thresholds, multiplicity and query-size sensitivity must be frozen separately before C drug scoring. The primary eight-gene association test is not automatically a sufficiently large or bidirectional LINCS query.

Export gene ID, assay/annotation version, expression-contrast direction and effect, methylation direction and effect, quality/coverage flags, cell-origin evidence and discovery-selection provenance. A methylation association sign is not the disease expression sign: hypermethylation with negative expression association does not alone demonstrate that the gene is downregulated in the defined immune-cold state. C query UP/DOWN must derive from the prespecified measured expression contrast.

CPC validation may annotate the frozen query's evidence later, with its exact test family stated. It cannot choose genes, reverse directions, reorder candidates or replace the query used in a completed drug screen. If B yields no confirmed association, C can proceed only under its already defined hypothesis-generation/alternative-input contract, with the missing B confirmation visible; it cannot label that input externally validated. Preserve the wider genome-scale discovery and all agreed C data sources regardless of which B primary is selected.

## 8. Four-month tradeoff and concrete decision gates

| Gate/work package | B-P | B-R |
|---|---|---|
| Same-specimen pairing, duplicates and true independence | Required | Required |
| Frozen promoter annotation/mask and actual CPC QC coverage | Required | Required |
| Age/grade/purity linkage and acceptable final precision | Required | Required; does not recover all 210 cases by design |
| Common whole-transcriptome U and cross-platform composite measurement | Required for primary | Optional secondary module; eight gene-specific mappings still required |
| Comparable absolute score scale and external model calibration | Central dependency | Replaced by within-cohort association measurement assumptions |
| Nested model tuning, training-only preprocessing and locked prediction artifacts | Required | Not needed for the primary; broader discovery models remain separately specified |
| Multiple-gene replicability and small-sample association inference | Secondary in current proposal | Central dependency; multiplicity reduces sensitivity |
| Strongest connection to thesis | A transportable molecular predictor if successful | Recurrent patient-level regulatory associations feeding pharmacological hypotheses |

At the preselection checkpoint, B-R offered a smaller primary implementation and fewer transport assumptions. It still faced the same biological data bottleneck and could not guarantee a publishable result. That planning comparison is retained as decision provenance; current work follows selected B-P while resolving its specimen/annotation/covariate/precision gates.

The historical B-R path would have retained a four-figure structure around cohort accountability, association estimates, locked external replication and the B-to-C bridge. The selected B-P path retains its external prediction figure. A negative/null B-P result does not authorize switching the primary to B-R or whichever secondary result looks favourable.

**Recorded outcome:** B-P is selected because the principal contribution will test transportable predictive improvement. Shared specimen, annotation, covariate and precision gates still block the biological run. B-R stays available only as historical decision provenance or a separately amended future analysis.

## Inference boundaries added by review

B-R would have permitted independently fitted CPC nuisance coefficients/slopes after a frozen association contract; selected B-P prohibits external refitting of the predictive model. These are different validation designs. Any future promotion of B-R would require a new explicit decision and coordinated amendments to ANALYSIS, validation, schemas, eligibility and preregistration before fitting anything.

The 2,000 descriptive bootstrap resamples are not automatically enough for primary tail probabilities near 0.003125. Recompute ranks and projections per patient resample, preserve invalid draws and define when no interval is issued. Predefine covariates/platform effects and precision/calibration requirements without inspecting external association signs. The statistical review is a required part of this proposal.
