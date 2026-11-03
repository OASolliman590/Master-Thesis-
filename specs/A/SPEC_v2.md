# Paper A: consolidated specification v2.1, 3 Nov 2026

**Status: SIGNED by the user on 3 Nov 2026 ("I sign all three"), v2.1.** v2.1 (3 Nov) adds the cell-composition analysis (section 4.4), removes the RNA-derived composition adjustment from 4.3 and gives single-cell its own section (8), from the user's grilling answers recorded in `docs/wayfinding/SPEC_V2_1_20261103/MAP.md` and the evidence in `docs/research/SPEC_V2_1_EVIDENCE_20261103.md`. It consolidates, without changing, the signed decisions in force: RC2 (15 Oct), the immune-programme amendment (16 Oct), the integrated plan (29 Oct), simple mode (31 Oct), the validation amendment and its Addendum 1 (2 Nov), the A-BIO settings D4-D6 (2 Nov), the single-cell plan (2 Nov) and the acquisition close (2 Nov). Where the older files in `specs/A/` disagree with this document, this document and the dated amendments it cites prevail. The older files keep the full technical detail and are linked by section.

## 1. Question and products
**Question.** Which pretreatment immune-expression programmes are reproducibly associated with response to immune checkpoint inhibitors (ICI), how do they vary by cancer and regimen, and how well does one small frozen score discriminate response in an independent study compared with the cytolytic-activity score (CYT)?

**Products, in order of importance:**
1. **A-BIO (main biology result):** per-study response associations for the 11 locked immune panels, the individual checkpoint (M5) and epigenetic-regulator (M6) genes, and genome-wide differential expression. Synthesised per cancer, then across cancers.
2. **A-P2 (single formal primary):** paired AUROC difference, frozen 4-feature score minus CYT, on ORR in IMvigor210.
3. **A-P1 (endpoint sensitivity):** the same fixed score on the same patients under different response definitions.
4. **A-COMP (supporting):** estimated immune-cell composition (quanTIseq; CIBERSORTx secondary) related to response and to the panels, descriptive only.
5. **SC-1 (supporting):** where the panel genes are expressed, by cell type, in the Lin 2026 single-cell atlas.
6. **The frozen score's equation**, published with all parameters.

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
The unadjusted association is the common reference. A prespecified, estimable baseline clinical set is added where available. **v2.1: there is no RNA-derived composition adjustment.** An RNA-derived cell composition estimate is not an independent covariate for RNA outcomes; composition is described in 4.4 instead. If response cannot be separated from batch, the effect is reported as not estimable (for example GSE168204: 10 patients, 4 batches).

### 4.4 A-COMP: cell composition (v2.1, supporting)
- **Question:** how does estimated immune-cell composition relate to response, and how much does each locked programme track infiltration?
- **Cohorts (12):** the linear whole-transcriptome RNA-seq cohorts, with TPM rebuilt by the A-P2 routes: Riaz, Hugo, GSE168204, Liu, Gide, Van Allen, GSE135222, GSE176307 (Salmon TPM), Kim, GSE145996, GSE165278, GSE218989. Excluded: arrays (GSE67501, GSE122220, GSE111636), NanoString and targeted panels (GSE93157, GSE140901, GSE136961, GSE159067), Braun (log2, upper-quartile, ComBat; not linear TPM) and IMvigor210 (UNTOUCHED_FINAL_TEST).
- **Primary method: quanTIseq**, one pinned version shared with Paper B: TIL10 signature, `lsei` method (fractions of all cells, including "Other"), tumour mode on, mRNA-content scaling on; input is non-log TPM with gene symbols. Ten immune fractions plus "Other". The tool's authors note lower accuracy on pre-computed TPM than on its own FASTQ pipeline; this is stated as a limitation. Weak cell types (Tregs, B cells, M2) are flagged.
- **Secondary: CIBERSORTx**, LM22, relative mode (share of immune cells, not of the tumour), on the same 12 cohorts, only if the user registers; otherwise reported as "not run". quanTIseq and CIBERSORTx fractions answer different questions and are never compared as the same quantity.
- **Analyses:**
  1. *Response:* per-study Hedges g (R minus NR) for each fraction, within the ORR family first, then the other families; synthesised as in 4.1. Each fraction's association is also reported **as added value over CYT and the 18-gene GEP** within study (logistic model with the programme alone, then programme plus fraction; difference in AUROC with a paired bootstrap), because fractions and programmes form one immune axis (TIL10 shares only CD8A/CD8B with our gene sets, but the biology is shared).
  2. *Programmes:* within-study Spearman correlation of each fraction with each of the 11 panel scores and CYT, summarised across studies.
- **Rules:** fractions are compared within cohort only, never across platforms or cohorts on a raw scale; nothing pooled. Descriptive and supporting: never a response predictor, never an A-P2 input, never a covariate for RNA outcomes. Multiplicity: BH FDR 10% within each fraction family. Wording: "composition is associated with response", never "explains" or "causes".
- **Not single-cell deconvolution:** quanTIseq and LM22 use their own fixed published signatures, not our single-cell data, so this does not reopen the cut SC-2 (single-cell plan, 2 Nov). No pseudobulk benchmark is run; published benchmarks are cited.
- **Prior exposure:** Finotello 2019 analysed GSE91061 (Riaz) with quanTIseq; this is cited, and the Riaz result is not counted as independent of that report.

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

## 8. Single-cell: SC-1 (signed single-cell plan, 2 Nov)
- **Role:** descriptive support only. It shows where locked genes are expressed in sampled cells. It never tests response, never selects or changes bulk features, never touches IMvigor210, and is not used for deconvolution. Cut permanently: SC-2 (single-cell deconvolution), SC-3 (single-cell response testing), single-cell A.1, spatial data.
- **Data (on the SSD, Gate 0 passed):** the Lin 2026 atlas (Zenodo 10.5281/zenodo.19586163, CC BY 4.0; 1,498,487 cells, 245 patients, 17 source cohorts; raw integer UMI counts in two layers; 16 broad cell types including copy-number-confirmed malignant cells). Stored in the runtime area `lin2026_atlas/`, pinned by hash. 13 cohorts in 6 cancers qualify (breast 3 cohorts/75 patients, head and neck 3/44, melanoma 2/34, colorectal 2/24, liver 2/11, basal cell carcinoma 1/10). Not qualifying: lung and TNBC_Zhang (chemotherapy combinations), kidney (no baseline ICI-only sample), prostate (shown in Paper B only).
- **Method:**
  - Broad compartments; summed raw UMI counts per patient and compartment.
  - NA below 15 cells or 5,000 UMIs; a compartment is shown only with at least 5 donors.
  - log2(CPM+1) on the full library.
  - Low-copy genes are tagged below the detection limit, never "absent".
- **What is shown:** the 11 locked panels and individual M5/M6 genes, later the top A-BIO genes by a fixed rule (discordant ones kept). Each cancer and source study is its own panel; nothing pooled across studies. Missing tumour cells are "not assessed".
- **Overlap:** head and neck cohorts are checked against bulk GSE159067; overlap is reported as non-independent. The Lin 2026 59-gene signature was validated on 19 baseline bulk cohorts; which ones is to be audited (gate 3).
- **Output:** one figure (cancer and study panels × broad compartments) and one provenance and coverage table, under a 10-hour cap.

## 9. Claims
**Can claim:** context-specific association of programmes with response; reproducibility or contradiction across studies; how one frozen compact score discriminates ORR compared with CYT in IMvigor210, with conditional uncertainty; development performance under labelled validation settings. Descriptive composition–response and composition–programme associations (A-COMP).

**Cannot claim:** causal ICI effects or mechanisms; pan-cancer independent validation; calibrated probabilities; clinical readiness; that a coefficient is a target; prostate ICI response; that a cell fraction explains a programme or a response.

## 10. Technical implementation
| Step | Tool | Status |
| --- | --- | --- |
| Cohort loading | `python -m tools.a_cohorts load --cohort <id>` → `.scratch/runtime/<c>/simple/` | done for 20 cohorts |
| A-P2 inputs | `python -m tools.a_p2 build` → `.scratch/runtime/a_p2/inputs/` | done (408 patients) |
| A-BIO panel effects and meta-analysis | to build (`tools/a_bio`), per-study Hedges g + REML/Knapp–Hartung (R metafor or Python statsmodels, chosen once) | not started |
| Genome-wide DE | DESeq2/edgeR and limma (R, pinned Bioconductor) | not started |
| A-P2 development and final evaluation | to build (`tools/a_p2` fit/evaluate) | not started; final test needs a release step |
| A-COMP | quanTIseq (pinned, R or container) on A-P2 TPM; CIBERSORTx LM22 (web/Docker, after registration) | not started |
| SC-1 | R qs2/SeuratObject, pseudobulk | atlas qualified, not started |
All outputs stay under `.scratch/` (git-ignored); Git holds code, specs and patient-free results only.

## 11. Open gates before analysis
1. Freeze the Hallmark IFN-gamma panel membership.
2. Freeze the numerical register entries: panel multiplicity rule, DE software choice, bootstrap seeds.
3. Audit IMvigor210 and development-cohort prior exposure for comparators, including the 19 cohorts of the Lin 2026 signature validation.
4. Release step for the final test (only after the model equation is frozen).
5. Pin the quanTIseq version and options (shared with Paper B); CIBERSORTx needs the user's registration.

## 12. Budget
A-COMP adds about 15 researcher-hours (quanTIseq 12; CIBERSORTx 3).
