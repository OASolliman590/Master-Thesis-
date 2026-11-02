# Astra (gpt-6-astra, high) review of the score-level rescue option, 2 Nov 2026

Read-only review, kept verbatim except that absolute paths were made repository-relative.

**VERDICT:** Retain TPM-only A-P2 as primary; permit score-level standardisation as a prespecified sensitivity, with exact CYT retained and GSE176307 excluded until complete panel coverage is established.

**ANSWERS**

**Q1. Statistically acceptable, and which should be primary?**

**Acceptable as a different, cohort-relative prediction procedure; it does not establish measurement equivalence.** It could become primary through an explicit redesign, but I recommend against replacing the signed primary merely to increase patient numbers.

Score standardisation removes positive affine differences in a *completed feature*. It cannot generally undo gene-specific ComBat adjustments, different pseudocount effects or sample-specific normalisation. Those operations can change panel rankings and relationships.

**Frozen default:** TPM-only primary; expanded-cohort standardisation sensitivity. The five-family primary remains valid, explicitly testing joint study-and-cancer transfer to bladder. **GSE176307 also lacks CGAS**, independently blocking the proposed four-feature rescue under the complete-coverage rule. See the [measurement decision](docs/decisions/A_P2_MEASUREMENT_20261102.md).

**Q2. What is lost, and is it acceptable?**

The procedure discards between-study feature means **and variances**, including genuine biology. Patients become high or low *relative to their own cohort*. Different response mixtures, tumour purity, tissue sampling and clinical selection change those reference distributions even without accessing outcomes. Small studies produce unstable SDs; near-zero SDs can amplify noise.

For a frozen linear score, subtracting feature means changes only its within-cohort intercept; dividing features by different SDs can change patient rankings. Consequently, adding other patients to the reference cohort can change an existing patient’s prediction.

**Frozen default:** accept these limitations for a cohort-relative sensitivity, without claims of harmonised biological units, calibrated probabilities or standalone patient deployment.

**Q3. Can IMvigor210 remain “untouched”?**

**Its outcomes can remain untouched; its expression distribution is being used to adapt the prediction procedure.** This is a transductive, cohort-adaptive external evaluation, not evaluation of a wholly training-derived transform.

Freeze beforehand the reference-population eligibility, four feature definitions, SD convention, zero-variance handling and adaptation algorithm. Compute its moments without outcomes, record them, then unlock outcomes. Apply the same cohort-adaptive rule to each held-out development study.

**Frozen default:** the primary uses development-derived means/SDs. Label the sensitivity **“external, outcome-blinded cohort-adaptive evaluation”**, with exposure-audit qualification. Keep its external comparison descriptive. Any later interval must distinguish conditioning on the realised reference moments from resampling and re-estimating the adaptation.

**Q4. Is the proposed CYT handling valid?**

**No, not as the signed TPM/no-offset CYT comparator.** Three distinctions matter:

- For positive abundances, averaging **unshifted** logarithms equals the logarithm of their geometric mean. With `log2(1+x)`, it instead ranks \(\sqrt{(1+x_{\mathrm{GZMA}})(1+x_{\mathrm{PRF1}})}\), which need not preserve no-offset CYT rankings.
- Upper-quartile abundance and TPM can differ by patient-specific factors; monotonicity on one scale does not establish identical rankings on the other.
- Gene/batch-specific ComBat adjustments can change rankings. Fixed gene-wise median subtraction alone would preserve the corresponding log-score ranking, but sample-wise centring/scaling need not. “Approximately rank-equivalent” is an unverified empirical claim.

**Frozen default:** compute exact CYT only where the signed measurement contract permits it. Braun may train the **sensitivity learner** if all four features qualify; report its learner AUROC without a CYT difference. GSE176307 cannot currently train that learner because CGAS is missing. Do not substitute available-gene averaging. Keep CYT-paired summaries restricted to their explicitly identified compatible cohorts.

**Q5. Is there a simpler rescue within the signed rules?**

**No demonstrated route recovers both cancers, but bladder has an overlooked source lead.** The local audit records a separate official `GSE176307_salmon_tpm_gene.matrix.tsv.gz`, with a sample-name key. Thus “only centred values exist” is too strong: the centred matrix is the currently selected representation.

The [local source audit](docs/research/A_source_admission_176307/REPORT.md) inspected the TPM header, not its complete values or gene coverage. It records 92 assay columns, two unmatched identifiers and a duplicate-patient issue. The [official TPM object](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE176nnn/GSE176307/suppl/GSE176307_salmon_tpm_gene.matrix.tsv.gz) is a recorded locator, not a newly verified download.

**Frozen default:** prioritise qualification of that existing TPM representation before changing the model. Admit only verified, deduplicated patients with complete panels and valid CYT inputs. No verified compatible Braun source is established; standardisation, ranks or renaming cannot recover TPM. Both cohorts remain usable in appropriate A-BIO analyses.

**DESIGN TO FREEZE**

- **Primary:** signed four-feature TPM learner; currently five development families. IMvigor210 paired AUROC difference versus exact CYT remains the single formal primary.
- Preserve complete panel membership, fixed ridge penalty 0.1 on mean logistic loss, unpenalised intercept, equal patient weights and no tuning.
- Preserve primary leave-one-family-out development and 20 stratified 70/30 within-study sensitivity repeats, with training-only primary preprocessing and study-specific evaluation.
- **Additional sensitivity:** standardise completed panel features within each eligible study; include Braun conditionally, but exclude the currently loaded GSE176307 representation.
- For this additional sensitivity, held-out studies use their own outcome-blinded moments; 70/30 splits use each study’s training-split moments. Freeze sample SD (`n−1`); zero/nonfinite SD makes that fit/evaluation unavailable.
- Document deposited preprocessing. Split-local standardisation cannot undo ComBat or other preprocessing already estimated using the complete source cohort.
- Report exact CYT comparisons only where computable; separate learner-only results and their denominators. Freeze both equations before external evaluation; never select the primary from external performance.
- Retain the signed primary bootstrap and exposure audit. Report the adaptive external sensitivity descriptively; assess the existing GSE176307 TPM route before final roster lock.

**WHAT CHANGES IN THE SIGNED AMENDMENT**

- Add an explicitly secondary mixed-representation, cohort-adaptive procedure and its exception to training-only preprocessing.
- Separate learner eligibility from CYT-comparison eligibility **for that sensitivity only**.
- Specify reference populations, scaling failures, reporting denominators and deposited-preprocessing limitations.
- Correct the GSE176307 source-availability statement and retain its unresolved coverage/identity gates.
- Leave the primary estimand, learner, exact CYT definition and final-test protection unchanged.
