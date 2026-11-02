# Paper A: consolidated specification v2, 3 Nov 2026

**Status: DRAFT v2 for debate review and signature.** It consolidates, without changing, the signed decisions in force: RC2 (15 Oct), the immune-programme amendment (16 Oct), the integrated plan (29 Oct), simple mode (31 Oct), the validation amendment and its Addendum 1 (2 Nov), the A-BIO settings D4-D6 (2 Nov), the single-cell plan (2 Nov) and the acquisition close (2 Nov). Where the older files in `specs/A/` disagree with this document, this document and the dated amendments it cites prevail. The older files keep the full technical detail and are linked by section.

## 1. Question and products
**Question.** Which pretreatment immune-expression programmes are reproducibly associated with response to immune checkpoint inhibitors (ICI), how do they vary by cancer and regimen, and how well does one small frozen score discriminate response in an independent study compared with the cytolytic-activity score (CYT)?

**Products, in order of importance:**
1. **A-BIO (main biology result):** per-study response associations for the 11 locked immune panels, the individual checkpoint (M5) and epigenetic-regulator (M6) genes, and genome-wide differential expression. Synthesised per cancer, then across cancers.
2. **A-P2 (single formal primary):** paired AUROC difference, frozen 4-feature score minus CYT, on ORR in IMvigor210.
3. **A-P1 (endpoint sensitivity):** the same fixed score on the same patients under different response definitions.
4. **SC-1 (supporting):** where the panel genes are expressed, by cell type, in the Lin 2026 single-cell atlas.
5. **The frozen score's equation**, published with all parameters.

## 2. Data (frozen at the acquisition close, `docs/decisions/A_ACQUISITION_CLOSED_20261102.md`)
- **20 development cohorts, 1,257 patients** (`docs/cohorts/REGISTRY.tsv`): melanoma (Riaz, Hugo, Liu, Gide, Van Allen, GSE168204, GSE145996, GSE165278, GSE122220, plus part of GSE93157), lung (GSE135222, GSE136961, GSE218989), kidney (Braun nivolumab arm, GSE67501), head and neck (GSE159067), bladder (GSE176307, GSE111636), gastric (Kim), liver (GSE140901) and the three-cancer NanoString GSE93157.
- **Locked final test:** IMvigor210 (bladder, anti-PD-L1, about 298 ORR-evaluable), UNTOUCHED_FINAL_TEST, refused in code.
- **Inclusion rules:**
  - ICI monotherapy or dual ICI; combinations with non-ICI drugs are excluded (mixed studies contribute their ICI-only arm).
  - One pre-treatment specimen per patient.
  - Unknown response is never counted as non-response.
- **Representations:** RNA-seq counts, TPM, FPKM, log-scale and array/NanoString values, each kept on its own scale. Raw expression is never merged across studies.

## 3. Endpoints (D5)
Three families, never pooled across families:
1. **ORR:** CR/PR versus SD/PD (RECIST or the source's stated criteria); the main family.
2. **Clinical benefit:** each definition tagged separately (for example SD ≥ 6 months, DCB/NDB, PFS > 24 weeks).
3. **Source-defined binary labels** without a stated clinical definition (GSE218989, GSE111636, GSE168204): reported per study only.

## 4. A-BIO: response associations
### 4.1 Locked panels (D4)
- **Panels** (`specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json`): P_ANTIGEN_PRESENTATION, AYERS_GEP_18, HALLMARK_INTERFERON_GAMMA_RESPONSE (membership to be frozen before use), HOPE_18, M0-M6. CYT is the comparator, not a panel.
- **Score:** the frozen panel definition, computed on each study's own log-scale expression. A study enters a panel only with complete gene coverage after the frozen alias table.
- **Effect:** Hedges g (small-sample-corrected standardised mean difference), responders minus non-responders, within each study and endpoint family, with a 95% interval.
- **Synthesis:**
  - Per cancer, then across cancers, with REML random effects and modified Knapp–Hartung intervals.
  - 1 study is reported alone. 2-3 studies are combined tentatively, with no prediction interval. Patient numbers never replace study numbers.
  - The cross-cancer weighting is stated.
- **Multiplicity:** composite panel scores form one family, and individual M5 and M6 genes are counted separately. The numerical familywise rule is set in the numerical freeze register before outcomes are examined.

### 4.2 Genome-wide differential expression (D6, discovery only)
- **Integer counts:** negative-binomial GLM (DESeq2 or edgeR, chosen once), library offset, unshrunk log2 fold change with SE.
- **Log-scale and array data:** limma on the source scale, with the moderated t.
- **Synthesis:** only within the same effect type. Cross-type summaries are a labelled sensitivity.
- **Multiplicity:** Benjamini–Hochberg FDR 10% within each declared synthesis family. Full tables are kept, with unadjusted p-values.
- Targeted panels contribute to 4.1 only. Genome-wide lists never feed the A-P2 learner.

### 4.3 Adjustment and confounding
The unadjusted association is the common reference. A prespecified, estimable baseline clinical set is added where available. Composition adjustment is a separate sensitivity. If response cannot be separated from batch, the effect is reported as not estimable (for example GSE168204: 10 patients, 4 batches).

## 5. A-P2: the frozen predictor (validation amendment, 2 Nov)
- **Estimand:** paired difference in ORR AUROC, frozen learned score minus CYT, among eligible pretreatment IMvigor210 patients (weight 1; the claim is bladder-specific).
- **Features (4):** for each patient, the unweighted mean of log2(TPM+1) over all genes of P_ANTIGEN_PRESENTATION (8), M2_CYTOTOXICITY (12), M3_VIRAL_MIMICRY (13) and M4_EXCLUSION (13). M2 contains GZMA and PRF1, so the score partly overlaps CYT, and this is stated with every result.
- **Model:**
  - Logistic regression with an L2 penalty: mean logistic loss + (0.1/2) Σβ², with an unpenalised intercept.
  - Features standardised with training means and SDs only.
  - Equal patient weights, no class weighting, no interactions, no study or cancer indicators, no tuning.
- **CYT:** sqrt(TPM_GZMA × TPM_PRF1), no offset.
- **Inputs (built):** `python -m tools.a_p2 build`, 7 TPM families with 408 patients (139 responders, 269 non-responders). Liu 102, GSE176307 87, Gide 60, Riaz 49, Kim 45, Van Allen 39, Hugo 26. Routes and checks are in `docs/decisions/A_P2_MEASUREMENT_20261102.md`.
- **Development evaluation (INTERNAL_EXTERNAL):**
  - **Main:** leave one study family out. Study-specific paired AUROC differences, then equal-cancer and equal-study averages. Single-study cancers (gastric, bladder) are labelled as study-and-cancer transfer.
  - **Sensitivity:** 20 repeated, response-stratified 70/30 splits within studies. Only studies with at least 10 responders and 10 non-responders are evaluated. AUROCs are computed within studies and then averaged. The result is called a validation-setting contrast, not optimism.
  - **Cohort-adaptive sensitivity (Addendum 1):** completed features standardised within each study. Braun enters if all features qualify, with a learner AUROC but no CYT difference.
- **Final model:** fitted on all 408 development patients. Its equation (feature definitions, training means and SDs, coefficients, intercept) is recorded and published, and then evaluated once on IMvigor210.
- **Inference:** 2,000 paired, outcome-stratified bootstrap resamples, 95% percentile interval, seed 20261102. The formal comparison needs at least 10 patients per ORR class; an interval spanning zero is inconclusive.
- **Minimums:** at least 3 development families, and every leave-one-out training set needs at least 20 responders and 20 non-responders; otherwise A-P2 is reported as unavailable.

## 6. A-P1: endpoint sensitivity
CYT is fixed, on identical category-evaluable patients: the AUROC under the clinical-benefit definition minus the AUROC under ORR. It is decomposed by response-category composition (`specs/A/ENDPOINT_SENSITIVITY.md`), then repeated for the locked panels. It is reported as a paired difference, never as "significant here, not there".

## 7. Comparators
CYT is the formal comparator. Supporting comparators are admitted only with their exact published scoring rules, evaluated on a frozen common eligible population, and labelled with any prior exposure to our cohorts:
- Lin 2026, 59 genes;
- Subramanian 2023, angio-immune subtypes;
- PredictIO (Bareche 2022) and published signatures where implementable.

## 8. SC-1 (single-cell plan, 2 Nov)
- **Data:** the Lin 2026 atlas (Zenodo, CC BY 4.0; 1.5 million cells, 245 patients). 13 cohorts in 6 cancers qualify (breast, head and neck, melanoma, colorectal, liver, basal cell carcinoma).
- **Method:**
  - Broad compartments; summed raw UMI counts per patient and compartment.
  - NA below 15 cells or 5,000 UMIs; a compartment is shown only with at least 5 donors.
  - log2(CPM+1) on the full library.
  - Low-copy genes are tagged below the detection limit, never "absent".
- **Output:** one figure and one provenance table, under a 10-hour cap.

## 9. Claims
**Can claim:** context-specific association of programmes with response; reproducibility or contradiction across studies; how one frozen compact score discriminates ORR compared with CYT in IMvigor210, with conditional uncertainty; development performance under labelled validation settings.

**Cannot claim:** causal ICI effects or mechanisms; pan-cancer independent validation; calibrated probabilities; clinical readiness; that a coefficient is a target; prostate ICI response.

## 10. Technical implementation
| Step | Tool | Status |
| --- | --- | --- |
| Cohort loading | `python -m tools.a_cohorts load --cohort <id>` → `.scratch/runtime/<c>/simple/` | done for 20 cohorts |
| A-P2 inputs | `python -m tools.a_p2 build` → `.scratch/runtime/a_p2/inputs/` | done (408 patients) |
| A-BIO panel effects and meta-analysis | to build (`tools/a_bio`), per-study Hedges g + REML/Knapp–Hartung (R metafor or Python statsmodels, chosen once) | not started |
| Genome-wide DE | DESeq2/edgeR and limma (R, pinned Bioconductor) | not started |
| A-P2 development and final evaluation | to build (`tools/a_p2` fit/evaluate) | not started; final test needs a release step |
| SC-1 | R qs2/SeuratObject, pseudobulk | atlas qualified, not started |
All outputs stay under `.scratch/` (git-ignored); Git holds code, specs and patient-free results only.

## 11. Open gates before analysis
1. Freeze the Hallmark IFN-gamma panel membership.
2. Freeze the numerical register entries: panel multiplicity rule, DE software choice, bootstrap seeds.
3. Audit IMvigor210 prior exposure for comparators.
4. Release step for the final test (only after the model equation is frozen).
