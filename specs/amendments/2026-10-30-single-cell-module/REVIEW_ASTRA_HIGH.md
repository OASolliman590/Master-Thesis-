# Astra (gpt-6-astra, high effort) review of the single-cell draft, 30 Oct 2026

Read-only review, kept verbatim.

**Recommendation: retain SC-1, make SC-3 conditional, and defer SC-2. The draft is sensible in scope but is not ready to freeze.** Its strongest contribution is showing which sampled cell types express the bulk programmes. It cannot establish that composition explains a response association or that prostate methylation acts within malignant cells.

This review used the requested local documents, project context and evidence records. No network access or file changes were made. The signed amendment controls; its archived Astra review explains the reasoning but reviews an earlier draft. The single-cell cohort-verification note cited in the draft is missing from this checkout, so actual eligible cohort sizes remain unverified.

**1. Should any single-cell analysis be confirmatory?**

**MEDIUM — “Role,” SC-1–SC-3: keep all three supporting or exploratory.**

The proposed hierarchy is appropriate. A-P2 and B-P retain their existing primary roles. SC-3 could eventually support an independently specified replication question, but this draft lacks a verified independent population, exact contrast, precision assessment and multiplicity plan. A matching direction alone is not confirmation.

**Fix/default:** describe SC-1 as *cell-type expression localization*, SC-2 as *composition sensitivity*, and SC-3 as *exploratory within-cell-type response association*. Different cancers, treatment regimens or sampling times provide transport evidence, not replication of the original clinical estimand. Record prior knowledge of published single-cell findings and patient overlap with bulk cohorts.

**HIGH — SC-1: “mostly malignant-cell or immune-cell” exceeds what these data necessarily identify.**

Expression within recovered cells does not establish their contribution to total tumour RNA. CD45 sorting excludes most malignant and stromal cells; even unsorted dissociation changes recovery across compartments. High expression per immune cell can coexist with a larger total contribution from abundant malignant cells.

**Fix/default:** report donor-aware expression distributions across the **sampled compartments**, without estimating their share of whole-tumour expression. For CD45-enriched sources, restrict conclusions to immune compartments and mark malignant/stromal expression **not assessed**, not absent. Quantitative whole-tumour attribution would require separately qualified abundance and RNA-content information.

**2. Which deconvolution approach avoids circularity, and can melanoma references transfer?**

**HIGH — SC-2: an independent reference does not eliminate circular adjustment.**

The reference can be independent while estimated fractions and the tested programme still use overlapping genes from the same bulk RNA sample. Adjusting for those fractions can remove programme signal mechanically. The draft’s question—whether the effect is “explained by composition”—also overstates the inference: attenuation can reflect measurement error, collinearity, mediation or reduced precision. This is explicitly cautioned against in [A’s cellular-context contract](specs/A/CELLULAR_AND_MULTIOMICS_CONTEXT.md:9).

**Fix/default:**

- Keep the original association as the main result. Compare unadjusted and adjusted estimates on **identical patients**, reporting effects, intervals and changes in sample eligibility.
- Freeze the reference, marker-selection rule and adjustment model without inspecting bulk response associations.
- Where feasible, exclude the frozen target-programme genes from deconvolution markers. Report the remaining marker coverage and identifiability. This reduces direct overlap; it does **not** establish independence.
- If exclusion leaves inadequate markers, omit that sensitivity rather than claiming circularity has been solved.
- For B-MX prediction, do not feed target-sample RNA-derived fractions into a model advertised as predicting RNA from methylation/non-RNA inputs. Keep them in a separately labelled explanatory sensitivity. Prefer qualified non-RNA purity measurements where available.
- Do not replace B-P’s frozen covariates or model with SC-2 outputs.

**MEDIUM — SC-2: the reference and method are unspecified.**

If this branch is retained, my recommended starting method for a multi-donor single-cell reference is **MuSiC**, subject to source and platform qualification. Its donor-aware approach is relevant here; it does not solve missing compartments or cancer mismatch. See the [primary MuSiC paper](https://doi.org/10.1038/s41467-018-08023-x) and [official implementation](https://github.com/xuranw/MuSiC). These are method references, not evidence that the proposed data are already compatible.

Freeze these construction rules:

- Use outcome-blind, preferably pretreatment references with donor identities and documented cell annotations.
- Retain donor-specific profiles; do not let donors with many captured cells dominate a pooled reference.
- Begin with broad compartments: T/NK, B, myeloid, fibroblast, endothelial and relevant epithelial/malignant populations.
- Require several independent donors supporting each retained compartment. **Five donors per major compartment is a pragmatic starting floor, preferably ten or more**, not a validated universal threshold.
- Use the documented input units and normalization. Batch-corrected embeddings, scaled residuals and arbitrary logged matrices are not interchangeable with expression inputs.
- Examine donor-held-out stability and reference-gene conditioning. Artificial mixtures can test reconstruction behaviour, but cannot validate real tumour fractions.
- State whether outputs estimate cell proportions or relative RNA contributions and what RNA-content assumptions support that interpretation.

**HIGH — SC-2 and its Paper B use: melanoma is not a default prostate reference.**

Malignant expression is lineage-specific; immune and stromal states also vary by tissue, treatment and disease stage. A melanoma reference can force unrepresented prostate expression into incorrect compartments.

**Fix/default:** use a cancer-matched, whole-tissue reference for each bulk cancer, including prostate. If none qualifies, omit quantitative deconvolution for that cancer. Cross-cancer transfer may be a separately labelled exploratory sensitivity for broad shared immune compartments, with matched-reference comparison where available. Never transfer melanoma malignant profiles as prostate malignant profiles.

A CD45-only reference cannot estimate whole-tumour immune abundance or tumour purity. At most, a separately qualified method may estimate composition **within the represented immune compartment**.

**3. Is SC-3 worthwhile with 10–30 patients? What minimum and test?**

**MEDIUM — SC-3 and “The unit is the patient”: worthwhile for estimation, but presently underspecified.**

Use the number of **unique eligible patients with usable data for the particular cell type**, not total study donors, biopsies or cells. Baseline restrictions, missing response labels and sparse cell types can substantially reduce that number.

Recommended pragmatic reporting rules:

| Eligible patients for a given cell-type contrast | Default |
|---|---|
| Fewer than 5 responders or 5 nonresponders | Patient-level plots and descriptive summaries; no formal response-test claim |
| At least 5 per group, but fewer than 10 in either group | Exploratory effect and interval; any test is explicitly fragile |
| At least 10 per group | Reasonable exploratory comparison, still insufficient by itself for confirmation |

These are proposed operating rules, **not power guarantees**. For orientation, with balanced groups, two-sided α=0.05 and 80% power, an optimistic normal approximation requires standardized differences of approximately **1.77, 1.25 and 1.02** for total N=10, 20 and 30. Small-sample testing, imbalance and multiplicity make the requirements larger.

**Fix/default method:**

1. Select one eligible pretreatment specimen per patient using a frozen timing/site rule. Keep on-treatment and paired-change analyses separate.
2. **Sum raw counts within patient × specimen × cell type, then normalize and calculate the frozen score.** Averaging cell scores is a different estimand and should not be called count pseudobulk.
3. For one continuous programme score, use a **two-sided Welch comparison of patient-level scores**, reporting the responder-minus-nonresponder mean difference and 95% interval.
4. For gene-level count contrasts, if separately needed, use **edgeR quasi-likelihood on patient pseudobulk counts**, with library normalization and an estimable design. This is optional scope, not required for SC-3.
5. Do not weight clinical replication by cell count. Set cell/library QC thresholds before looking at response; absent or inadequately sampled cell types yield missing scores, not zero scores.
6. Check response-by-batch, regimen and tissue-site support. If response is inseparable from batch, report the adjusted contrast as nonestimable rather than attempting to correct it away.

Patient-aware pseudobulk inference is supported by the [muscat study](https://doi.org/10.1038/s41467-020-19894-4); count-model implementation should follow the [official edgeR documentation](https://bioconductor.org/packages/edgeR).

A null or opposite-direction result must be shown. At these sizes, nonsignificance usually means uncertainty, not equivalence.

**4. Are there conflicts with the signed rules?**

The patient unit, supporting role and prohibition on count-level study merging are consistent. The main problems are incomplete inheritance of safeguards and the stronger SC-1/SC-2 interpretations identified above.

**HIGH — Rules and SC-2: final-test protection must explicitly cover every single-cell use.**

The draft names protected families for reference construction, but should bind SC-1 annotation, SC-3 comparisons and portal/atlas reuse to the same restriction.

**Fix/default:** explicitly exclude the entire **IMvigor210 overlap-connected family** from this module before its separately authorized final evaluation: all patients, arms, timepoints, modalities, derived expression signatures and reused atlas material. Do not use its molecular distributions to choose references, normalization, markers, cell types or coverage repairs—even with response labels hidden. Unknown atlas membership is unresolved provenance, not proof of independence. Necessary metadata-only curation remains governed by the existing barrier.

This follows the [signed amendment’s family protection](specs/amendments/2026-10-29-integrated-plan/AMENDMENT.md:11) and [validation contract](specs/A/VALIDATION_AND_SPLITS.md:5).

**HIGH — Rules: “one cohort is one study” can miscount independent evidence.**

Separate accessions or portal collections may contain overlapping patients; bulk and single-cell publications can share an originating study family. Keeping matrices separate does not establish independence.

**Fix/default:** assign study-family and patient-overlap identities through the shared registry. Analyse studies separately and label overlapping single-cell evidence as complementary measurement, not independent validation. Default to **no SC-3 meta-analysis**. If later justified, retain compatible endpoints/effect scales and the signed modified Knapp–Hartung rule for 2–3 independent studies, without prediction intervals.

**MEDIUM — Rules and SC-1: distinguish frozen biology from an executable scoring contract.**

A locked panel list does not automatically supply an admitted single-cell score. Nor should localization of frozen A-DE results feed back into A-P2 selection.

**Fix/default:** freeze the single-cell measurement contract separately: membership, signs, coefficients, units, normalization, coverage and missing-feature handling. Preserve the distinction between composite panels and individual M5/M6 genes. Localization of A-DE genes remains downstream annotation; any selection use would require its own prospective amendment and appropriate validation.

**5. Is the full module worth the effort within approximately 600 researcher-hours?**

**MEDIUM — Overall scope: three branches are disproportionate to their likely incremental evidence.**

The [data assessment](docs/integration/20261030-data-assessment/ASSESSMENT.md) identifies cancer diversity and completion of bulk analysis methods as major outstanding needs. Single-cell profiling does not add independent bulk response cohorts or close those gaps. SC-2 adds substantial reference qualification and interpretation work.

**Fix/default:** make SC-1 the committed module. Permit one SC-3 analysis only if an admitted source already has usable baseline labels, donor linkage and adequate group sizes. Defer custom SC-2. Use an explicit **30–40-hour planning cap** for source qualification and a complete SC-1 output; this is a recommended allocation, not an estimate based on completed work. If usable processed data and donor annotations are unavailable within that cap, report the limitation and return to the bulk core.

**Other design and statistical findings**

**MEDIUM — Candidate cohorts and admission: the evidence trail is incomplete.**

`docs/research/USER_LEADS_VERIFICATION_20261030.md` is absent. The named publications therefore do not establish admitted accessions, independent donors, response availability or usable baseline sample sizes.

**Fix/default:** require a compact admission table containing exact source objects, donor/specimen linkage, cancer, regimen, collection timing, sorting, measurement representation, eligible response counts, overlap and prior exposure. Keep candidates unadmitted until verified. Permit expression-localization-only admission without response labels; SC-3 requires them. V3 processing documentation alone does not close the [G01–G06 gates](specs/amendments/2026-10-16-immune-programmes/INTERFACES_AND_GATES.md:27).

**MEDIUM — SC-1 and Rules: cell annotation and technical contamination need explicit handling.**

Doublets and ambient RNA can create apparent cross-compartment expression. Calling every epithelial cell malignant is also unsafe. Defining a cell state using the same programme later compared across states can make localization partly tautological.

**Fix/default:** reuse documented author QC and broad annotations, audit doublet/ambient-RNA handling, and retain uncertain labels. Require source-supported malignant assignments; otherwise report “epithelial/putative malignant.” Avoid defining clusters using the target programme and then treating programme enrichment as independent evidence. Summarize normalized patient-level profiles with donors contributing equally; show donor support and variability alongside aggregate heatmaps.

**MEDIUM — SC-3: “descriptive” does not specify multiplicity or prevent selective reporting.**

Eleven panel entries multiplied by cell types, endpoints and visits can create many comparisons; M5/M6 may add individual-gene hypotheses.

**Fix/default:** restrict optional SC-3 to one endpoint, baseline samples and a small biological set of programme–cell-type contrasts fixed before outcomes. Report every planned contrast. If p-values are used, apply **BH FDR at 5% across the declared exploratory family**, including the actual individual-gene tests. Use two-sided tests even when checking an expected direction.

**HIGH — Paper B rule: the joint-assay exception can imply too much.**

The sentence “scRNA has no methylation, unless…” should not imply that adding joint measurements establishes epigenetic silencing. Matched molecular association still does not identify a causal mechanism; unpaired computational integration is not measured pairing.

**Fix/default:** state that SC-1 provides localization and SC-2 provides composition sensitivity only. Separately admitted joint assays may support cell-resolved methylation–expression association, with their own coverage and statistical design. Preserve “association supported,” “inconclusive” and “not measured/not estimable”; causal silencing or restoration requires additional evidence.

**(a) Recommended minimal version**

Implement SC-1 using one qualified, donor-resolved, unsorted prostate tumour reference and, only if inexpensive, one qualified reference matching Paper A’s main development cancer. Use existing processed data and documented broad cell annotations; generate one donor-aware expression-localization figure and a coverage/provenance table for the locked programmes and frozen A-DE genes. Keep sorted datasets restricted to their sampled compartments, distinguish malignant from uncertain epithelial labels, and make no whole-tumour fraction or methylation-mechanism claims. Add a small baseline SC-3 analysis only when verified patient counts and labels satisfy its frozen feasibility rules. Defer custom deconvolution, leave A-P2 and B-P unchanged, and exclude IMvigor210’s entire protected family throughout.

**(b) Plain summary**

- Keep single-cell work small and supporting.
- Count patients, not cells or biopsies.
- Sorted immune cells cannot describe the whole tumour.
- Ten to thirty patients mainly reveal large differences.
- RNA-based adjustment cannot prove composition explains an effect.
- Melanoma references do not automatically transfer to prostate.
- Keep IMvigor210 untouched and both primary analyses unchanged.