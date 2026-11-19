# Paper A: baseline clinical covariates by development cohort (SPEC v2.1 section 4.3; A3 decision C)

**Date:** 19 Nov 2026. **Status:** research note. The adjustment set and rule in section 4 are **PROPOSED and unsigned**; nothing here changes `specs/A/SPEC_v2.md`, the numerical freeze register or the A3 decision sheet.

**Scope and what was read.** I read the 20 development cohorts in `docs/cohorts/REGISTRY.tsv` (IMvigor210 is excluded and was not touched) against these sources only:
- the primary papers' Methods and Results text;
- Table 1 row labels (aggregate tables only);
- supplementary table titles and legends;
- GEO series-level summaries (title, summary and design, via NCBI E-utilities `esummary`);
- cBioPortal clinical-attribute **name** lists (the `/clinical-attributes` endpoint, which returns names and no values).

No patient-level clinical table, expression matrix, response table or GEO sample record was downloaded or opened. Where a paper's full text could not be reached (publisher 403 or no PMC full text), the matrix says UNKNOWN; it does not guess.

**What "available" means here.** The variable is named as collected in the primary publication or its deposit. That does **not** establish per-patient completeness in the evaluable subset, the coding or the timing. Those belong to the outcome-free availability audit that the A3 sheet asks for (`docs/decisions/A3_DECISION_SHEET_PROPOSED_20261110.md`, section C).

Relation to the freeze register: N12–N15 are all `NOT_FROZEN`. N13 (A1 contrast covariates) and the A3 clinical set are separate decisions. This note can inform both but freezes neither.

---

## 1. Summary

1. **Few cohorts document covariates well.** Only 4 of the 20 document a usable baseline clinical set in public sources: Liu 2019, Van Allen 2015, GSE159067 (Foy 2022) and, more narrowly, Braun 2020. Riaz 2017 and Hugo 2016 document part of a set. The 9 small GEO-only or array/NanoString cohorts document almost nothing beyond regimen and specimen timing.
2. **Variables available in at least half the cohorts:** regimen or agent, specimen timing, and prior ICI exposure in the melanoma cohorts where it varies. No single clinical variable apart from these is documented in more than about 8 of the 20 cohorts. Age and sex are documented, or available through a harmonised secondary source, in about 10. LDH is documented in 4 (Liu, Van Allen, the linked MSKCC ipilimumab record for GSE165278, and partly Braun through the MSKCC risk score). ECOG is documented in 2 (Liu, GSE159067).
3. **Evidence on confounding.** Two kinds of covariate act on both immune expression and response, so they are true confounder candidates for a response-versus-expression contrast:
   - **Specimen site and timing:** lymph-node or other biopsy site, primary versus metastasis, archival interval.
   - **Prior therapy:** prior anti-CTLA-4, prior MAPK inhibitor, number of prior lines.

   Disease burden (LDH, M-stage, liver metastasis, IMDC/MSKCC, ECOG) is strongly prognostic for response. Its link to tumour immune expression is weaker, except liver metastasis. Age and sex have moderate evidence on both sides. PD-L1 IHC and TMB are tumour biomarkers that partly measure the same immune axis or lie on its causal path, so they should not be adjustment covariates.
4. **PROPOSED approach.** The unadjusted contrast stays primary. A per-study adjusted sensitivity is run only where the study has enough patients and the covariate is documented, well filled and varies. Covariates enter in a fixed priority order set before outcomes are seen. Under any reasonable threshold, at most about 8–10 studies would carry an adjusted estimate, so a cross-study "adjusted synthesis" would cover a different, smaller set of studies than the primary one.
5. **Still open.**
   - Full text could not be reached for 6 sources: GSE176307 (Rose 2021), Kim 2018, Gide 2019, Prat 2017 (GSE93157), Foy 2022 (EJC) and Braun Table S1 columns.
   - Two inclusion and overlap flags surfaced: GSE159067 includes ICI-plus-anti-KIR or anti-CTLA-4 trial patients, and GSE218989 includes previously reported Samsung Medical Center lung cases, so it may overlap GSE135222.

---

## 2. Availability matrix (development cohorts only)

**Codes:**
- **Y:** named as collected in a primary source.
- **P (partial):** one of the following applies:
  - documented only in a secondary or harmonised re-release (cBioPortal iAtlas, a later reanalysis), or a linked earlier release of the same cohort;
  - documented only in aggregate (Table 1) with no sign of a per-patient field;
  - documented for only part of the cohort.
- **N:** checked and not reported in the sources read.
- **U:** UNKNOWN, because the source exists but could not be read.
- **C:** constant by design (does not vary, so it cannot be adjusted for).
- **n/a:** not applicable to that cancer.

| Cohort (n in registry) | Age | Sex | Stage / M-stage | LDH | Prior ICI | Prior lines / other prior tx | ECOG | Cancer-specific burden or risk | Specimen site | Specimen timing | Regimen / agent | TMB | PD-L1 IHC | Driver / subtype |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Riaz 2017 (49) | Y¹ | P² | Y¹ | U | Y³ | U | U | U | U | Y⁴ | C (nivolumab) | Y⁵ | Y¹ | P² |
| Hugo 2016 (26) | Y⁶ | Y⁶ | Y⁶ | N⁶ | U⁷ | Y⁶ (prior MAPKi) | N⁶ | N | P⁸ | Y⁶ | Y⁶ | Y⁶ | N | Y (WES) |
| GSE168204 (10) | U | U | U | U | U | U | U | U | P⁹ | Y⁹ | Y⁷ | N | N | U |
| Liu 2019 (102) | P¹⁰ | Y¹¹ | Y¹¹ | Y¹¹ | Y¹¹ | Y¹¹ | Y¹¹ | Y¹¹ (brain, liver/visceral, LN, lung, bone metastases) | Y¹¹ | Y¹¹ | Y¹¹ | Y¹¹ | N | Y¹¹ |
| Gide 2019 (73) | P² | P² | P² | U | P¹² | U | U | U | P² | Y⁷ | Y⁷ (arm) | N | U | U |
| Braun 2020 (181) | U¹³ | U¹³ | n/a (all advanced) | P (in MSKCC score) | U | Y¹³ | P (Karnofsky, in MSKCC score) | Y¹³ (MSKCC risk) | U¹³ | Y¹³ | C (nivolumab arm) | Y¹³ | U | Y (WES) |
| Van Allen 2015 (40) | Y¹⁴ | Y¹⁴ | Y¹⁴ | Y¹⁴ | n/a (ipilimumab is the index drug) | Y¹⁴ (prior lines; prior RAF inhibitor) | U | P | Y¹⁴ | P¹⁴ | Y¹⁴ | Y¹⁴ | N | Y¹⁴ |
| GSE135222, Jung 2019 (27) | U¹⁵ | U¹⁵ | U¹⁵ | n/a | U | U | U | U | U | P¹⁵ | Y (PD-1/PD-L1) | Y¹⁵ | U | U |
| GSE136961, Hwang 2020 (21) | Y¹⁶ | Y¹⁶ | Y¹⁶ | n/a | U | Y¹⁶ | U | Y¹⁶ (smoking, histology) | U | P¹⁶ | C (anti-PD-1) | Y¹⁶ | Y¹⁶ | Y¹⁶ (EGFR/ALK) |
| GSE176307, Rose 2021 (88) | P¹⁷ | P¹⁷ | U | U | U | U | U | U | P¹⁷ (archival primary or metastasis) | N¹⁷ | Y⁷ | P¹⁷ | U | U |
| Kim 2018 (45) | U | U | U | U | C (ICI-naive)⁷ | P¹⁸ (salvage setting) | U | Y¹⁸ (EBV, MSI-H) | U | Y⁷ | C (pembrolizumab) | Y¹⁸ | Y¹⁸ (CPS) | Y¹⁸ |
| GSE145996, Amato 2020 (10) | P¹⁹ | P¹⁹ | P¹⁹ (stage at diagnosis) | U | Y¹⁹ | U | U | U | U | Y⁷ | Y¹⁹ | Y¹⁹ | N | Y¹⁹ (BRAF, NRAS, NF1, subtype) |
| GSE165278, Nathanson 2017 (7) | P²⁰ | P²⁰ | P²⁰ | P²⁰ | U | U | U | U | P²⁰ | P²⁰ | C (ipilimumab) | Y²⁰ | N | P²⁰ (RAF/RAS) |
| GSE93157, Prat 2017 (65) | U | U | U | U | U | U | U | Y (tumour type)⁹ | U | P²¹ | Y (anti-PD-1)⁹ | N | U | U |
| GSE67501, Ascierto 2016 (11) | U | U | U | U | U | U | U | C (all PD-L1+) | Y⁷ (primary or metastasis) | Y⁷ (specimen–therapy interval) | C (nivolumab) | N | C (PD-L1+ by design)²² | U |
| GSE122220 (10, no publication) | N | N | N | N | N | N | N | N | N | Y⁹ (pre-treatment) | Y⁷ (8 anti-PD-1, 2 dual) | N | N | N |
| GSE140901, Hsu 2021 (24) | U²³ | U²³ | U²³ | n/a | U | Y²³ (prior systemic therapy) | U | Y²³ (macrovascular invasion; HBV) | Y²³ (liver vs lung metastasis, separate cohort) | Y²³ | Y²³ (single agent vs combination) | N | U | U |
| GSE111636 (11, no publication) | N | N | N | N | N | N | N | N | N | N | C (pembrolizumab) | N | N | N |
| GSE218989, Kang 2024 (355) | U²⁴ | U²⁴ | U²⁴ | n/a | U | U | U | Y²⁴ (LUAD/LUSC) | U | U⁷ | Y²⁴ (PD-1 or PD-L1) | N | U | U |
| GSE159067, Foy 2022 (102) | Y²⁵ | Y²⁵ | U | U | P²⁵ | Y²⁵ | Y²⁵ | Y²⁵ (subsite, HPV, smoking, alcohol) | U | Y⁹ | P²⁵ | N | P²⁵ (subset) | Y²⁵ (HPV) |

### Sources behind each code (superscripts)

1. Riaz et al., *Cell* 2017 (PMID 29033130, PMC5685550). Methods give median age and M-stage at study entry, with stage unknown for some patients. PD-L1 IHC used clone 28-8. Supplementary **Table S2 "Clinical Characteristics"** (title only).
2. cBioPortal iAtlas harmonised studies (attribute names only):
   - `mel_iatlas_riaz_nivolumab_2017`: AGE_AT_DIAGNOSIS, SEX, RACE, CLINICAL_STAGE, PRIOR_ICI_RX, TISSUE_SUBTYPE.
   - `mel_iatlas_gide_2019`: AGE_AT_DIAGNOSIS, SEX, CLINICAL_STAGE, BIOPSY_SITE.

   These are a secondary re-release. "Age at diagnosis" is not age at ICI start.
3. Riaz design strata Ipi-naive and Ipi-progressed (Cell 2017). The repo already binds prior ipilimumab to the author Cohort field (`docs/decisions/RIAZ_SIGNATURE_20261029.md`).
4. Pre- and on-therapy design (Cell 2017, GEO GSE91061 summary).
5. WES mutation load (Riaz Table S1, Table S4).
6. cBioPortal `mel_ucla_2016` attribute names: AGE_AT_DIAGNOSIS, SEX, M_STAGE, PREVIOUS_MAPKI, BIOPSY_TIME, PRIMARY_SITE, TREATMENT, TMB_NONSYNONYMOUS. LDH and ECOG are not in the list. The Hugo 2016 text discusses prior MAPKi failure as a candidate negative factor.
7. `docs/cohorts/REGISTRY.tsv` caveats, as already recorded by the project:
   - Hugo: "prior ICI unknown".
   - GSE145996: prior ipilimumab recorded from Amato Table S1.
   - GSE67501: primary/metastasis and specimen interval retained.
   - GSE122220: regimen split.
   - Kim: ICI-naive, biopsy within 42 days.
   - GSE176307: five agents.
   - GSE218989: SOFT does not document specimen timing.
   - GSE168204: regimen mix.
8. iAtlas `mel_iatlas_hugo_ucla_2016` lists BIOPSY_SITE. In the primary-derived `mel_ucla_2016`, PRIMARY_SITE is a sample attribute whose meaning (lesion site versus primary tumour site) is not verified.
9. GEO series summaries:
   - GSE168204 (Du et al., *Nat Commun* 2021, PMID 34654806) says the authors "investigated the effect of biopsy sites" and has pre- and on-treatment samples.
   - GSE93157 covers three cancers treated with anti-PD-1.
   - GSE122220 states pre-treatment samples only.
   - GSE159067 says specimens came from clinical-trial patients.
10. Liu et al., *Nat Med* 2019 (PMID 31792460, PMC6898788). Methods say "Age, stage and ECOG performance status were documented before the first application of anti-PD1". Age is not a Table 1 row and not in the cBioPortal attribute list, so it is P.
11. Liu 2019 sources:
    - **Table 1 rows:** drug, sex, stage (unresectable III, M1a–M1c), active brain metastases, elevated LDH (with an Unknown category), ECOG (with Unknown), primary type (cutaneous, occult, acral, mucosal), line of anti-PD-1 therapy, previous ipilimumab.
    - **cBioPortal `mel_dfci_2019` attributes:** BIOPSY_SITE, BIOPSY_CONTEXT, LDH_ELEVATED, TX_START_LDH, TX_START_ECOG, M_STAGE, PRIOR_CTLA4, NUM_PRIOR_THERAPIES, PRIOR_MAPK_TX, LIVER_VISC_MET, LN_MET, MET_BRAIN, MET_BONE, LUNG_MET, STEROIDS_GT_10MG_DAILY, PRIMARY_TYPE, TMB_NONSYNONYMOUS.
    - **Methods:** LDH within 28 days of first dose.
12. Du et al. 2021 (PMC8519947) re-tabulates Gide: of the anti-PD-1 monotherapy patients, a subset had prior anti-CTLA-4 (Supplementary Data 1b). This is a secondary source. Gide's own Table S1 could not be read (publisher 403).
13. Braun et al., *Nat Med* 2020 (PMID 32472114, PMC7499153).
    - Supplementary **Table S1 "Clinical and immune phenotype data for the CheckMate cohorts"** (title only).
    - The text names, as multivariable covariates, "MSKCC risk group, lines of therapy (≤1 or ≥2), or timing of sample collection (days before beginning trial therapy)".
    - Tissue was "mostly archival", taken before anti-angiogenic therapy.
    - Age, sex and primary-versus-metastasis columns are not confirmed from a legend, so they are U.
14. Van Allen et al., *Science* 2015 (PMID 26359337, PMC5054517).
    - The text tests "patient age, gender, tumor histology, primary tumor site, number of therapies received before ipilimumab, and lactate dehydrogenase levels at initiation of ipilimumab" (table S3), and controls "for prior RAF inhibitor treatment and M class".
    - cBioPortal `skcm_dfci_2015` attributes: AGE, SEX, M_STAGE, SERUM_LACTATE_DEHYDROGENASE, TUMOR_SITE, TUMOR_STAGE, TUMOR_SAMPLE_HISTOLOGY, PRIMARY_SITE, DOSAGE, TMB_NONSYNONYMOUS.
    - Specimen timing is P because "pretreatment" is stated at cohort level.
15. Jung et al., *Nat Commun* 2019 (PMID 31537801, PMC6753140).
    - The SMC cohort's clinical data sit in Supplementary Table 3. Its columns are not described in the text, so they are U.
    - Mutation burden enters the authors' multivariable models.
    - Tumours were "obtained before anti-PD1/PD-L1 treatment", either FFPE or fresh.
16. Hwang et al., *Sci Rep* 2020 (PMID 31959763, PMC6971301).
    - **Table 1 "Baseline clinical characteristics" rows:** age, gender, histology, smoking status, stage (IIIB/IV), PD-L1 expression, EGFR mutation and ALK fusion, prior systemic therapy lines.
    - TMB and TILs are also reported.
    - Table 1 is aggregated by DCB/NDB. The heatmap figure shows PD-L1, smoking, histology, TIL and TMB per patient.
    - The authors note that "Intervening treatments were administered to 14% of patients after biopsy was taken", so specimen timing is P.
17. Rose et al., *BJC* 2021 (PMID 34294892).
    - The abstract says "Clinical annotation for demographics and cancer outcomes, as well as somatic DNA and RNA sequencing".
    - The repo's earlier source check (`docs/research/A_source_admission_176307/REPORT.md`) records archival FFPE from primary or metastatic sites, and no patient-level specimen-to-ICI interval.
    - The full text and Table 1 were not reachable in this pass (PMC and publisher both blocked automated access).
18. Kim et al., *Nat Med* 2018 (PMID 30013197).
    - From the abstract and the indexed summaries: PD-L1 CPS is available for most patients, plus EBV status, MSI-H status and WES-based TMB.
    - Pembrolizumab was given as salvage treatment.
    - Table 1 (age, sex, ECOG, Lauren) was not reachable.
19. Amato et al., *Cancers* 2020 (PMID 32708981, PMC7409244).
    - **Table 1 rows (52-patient WES cohort):** sex, age, BRAF/NRAS/NF1, nivolumab or pembrolizumab, melanoma subtype, stage at diagnosis.
    - Per-patient Table S1 is cited for prior ipilimumab (registry).
    - The 10-patient RNA subset's completeness is unknown.
20. GSE165278's labels come from the Nathanson et al. 2017 clinical table (PMID 27956380, PMC5253347; Online Data File 1). The registry already notes that this is the same MSKCC ipilimumab cohort as Snyder 2014.
    - cBioPortal `skcm_mskcc_2014` attributes: AGE, SEX, M_STAGE, SERUM_LACTATE_DEHYDROGENASE, TUMOR_SITE, SIMPLIFIED_TUMOR_SITE, BIOPSY_TIME, RAF_RAS_STATUS, TMB_NONSYNONYMOUS.
    - These are P because they come from a linked release, not the pinned Nathanson table.
21. Prat et al., *Cancer Res* 2017. Repo notes (`docs/research/A_DAV_PRAT_PUBLIC_GAPS_02.md`) record a "Sample data" passage on biopsy timing categories. The Table 1 and Table S1 columns were not read.
22. Ascierto et al., *Cancer Immunol Res* 2016 (PMID 27491898, PMC5584610). All specimens are PD-L1+ (≥5% tumour cells, clone 5H1). Patient characteristics are in Supplementary Table S1 (title per text; columns U).
23. Hsu et al., *Liver Cancer* 2021 (PMID 34414122), publisher full text.
    - The text names macrovascular invasion, prior systemic therapy, sampling-to-ICI interval, single-agent versus combination ICI, HBV status, and liver primary versus lung metastasis.
    - Cohort characteristics are in Supplementary Tables 2–3 (not read).
    - The authors' own rule: "clinicopathological characteristics present in more than 20% of a given cohort were included in multivariate analyses".
    - Age, sex, Child-Pugh, BCLC, AFP and ECOG are not mentioned in the text.
24. Kang et al., *Nat Commun* 2024 (PMID 38744958, PMC11094150).
    - The cohort is lung adenocarcinoma and squamous carcinoma treated with PD-1 or PD-L1 inhibitors, "including previously reported cases", from Samsung Medical Center.
    - "Clinical information … collected from electronic medical records"; response by RECIST 1.1.
    - Clinical data are in Supplementary Data 8 (columns not described beyond OS/PFS).
    - Note: the GEO deposit uses a source "Responder/Non-responder" field; see the registry.
25. Foy et al., *Data in Brief* 2022 (PMID 36111282, PMC9467865).
    - **Table 2 rows for the CLB-IHN cohort (n = 102):** age, gender, smoking history, alcohol consumption, disease site, HPV status (with Unknown), ECOG PS, number of previous lines of systemic treatment, best response.
    - PD-L1 TPS and CPS are available in a subset.
    - The article states that "the complete set of gene expression profiles and associated clinical information" was submitted to GEO.
    - Regimen is P because the cohort was treated "with PD-1/PD-L1 antibodies alone or in combination with an anti-KIR or an anti-CTLA4 antibody". See still open, item 3.

### Column totals

These are counts of Y, plus P in brackets, across the 20 cohorts. They are rough, because P mixes secondary, linked and aggregate-only sources.

| Covariate | Y | +P |
|---|---|---|
| Age | 5 | +5 |
| Sex | 5 | +5 |
| Stage / M-stage | 5 | +3 |
| LDH | 2 | +2 |
| Prior ICI (where it can vary) | 3 | +2 |
| Prior lines / other prior therapy | 7 | +1 |
| ECOG | 2 | +1 |
| Specimen site | 4 | +5 |
| Specimen timing | 12 | +5 |
| Regimen / agent | most (constant in 7) | |
| TMB | 10 | +1 |
| PD-L1 | 3 | +1 |

---

## 3. Evidence on confounding: which baseline covariates act on both response and immune expression

In section 4.1 the contrast is the expression score compared between responders and non-responders, as Hedges g. A covariate confounds this association only if it is related to **both** response and the pre-treatment immune score, and it is not itself a consequence of the immune state.

| Covariate | Effect on ICI response (primary evidence) | Effect on tumour immune expression | Role for A |
|---|---|---|---|
| **Specimen site** (lymph node vs other; primary vs metastasis; liver lesion) | Liu 2019: lymph-node metastasis independently predicted non-progression in the ipilimumab-pretreated subgroup (PMID 31792460). Tumeh 2017: liver metastasis associated with lower ORR and PFS on pembrolizumab in melanoma and NSCLC (PMID 28411193). | Lymph-node specimens carry resident lymphocytes, which mechanically raise T-cell and IFN scores. Du 2021 tested biopsy-site effects on signature performance (PMID 34654806, GEO summary). Yu 2021: liver metastases drive macrophage-mediated systemic CD8 T-cell loss (PMID 33398162). Hsu 2021: lung-metastatic HCC had higher exhausted-CD8 signature than liver primaries (PMID 34414122). | **Strong confounder candidate.** Highest priority where it is documented. |
| **Prior anti-CTLA-4 (prior ICI)** | Riaz 2017: associations of mutation load, TCR and immune features with response differ between ipilimumab-naive and ipilimumab-progressed patients (PMID 29033130). Liu 2019: previous ipilimumab changes which predictors work (interaction P = 0.004 and 0.018), though response rates were similar (PMID 31792460). | Prior ipilimumab remodels the tumour T-cell repertoire and infiltrate (Riaz 2017; Liu 2019). | **Confounder and effect modifier.** Adjust, or stratify where both levels are present. The spec already keeps anti-CTLA-4 as a separate drug-class stratum. |
| **Prior MAPKi / prior lines / prior chemotherapy** | Hugo 2016: prior MAPKi failure is a candidate negative factor, and MAPKi induces the IPRIM resistance signature (PMID 26997480). Braun 2020 used lines of therapy as a covariate (PMID 32472114). | MAPKi induces mesenchymal and angiogenic transcription (Hugo 2016). Alkylating chemotherapy leaves mutational signatures (Liu 2019). Archival specimens taken before intervening therapy may not reflect the tumour at ICI start (Braun 2020; Hwang 2020). | **Confounder candidate.** Coding differs by cancer. |
| **Specimen-to-ICI interval / archival status** | Not a response predictor in itself. | Braun 2020: the immune state "may have further evolved prior to PD-1 blockade" in archival tissue. The registry already records intervals for GSE67501 and Kim. | Measurement-validity covariate. Best handled by eligibility (the existing one-baseline-specimen rule) plus a sensitivity analysis, not by regression. |
| **LDH / tumour burden** | Diem 2016: elevated baseline LDH predicts shorter OS on anti-PD-1 (PMID 26794281). Weide 2016: LDH and metastatic pattern were independent pembrolizumab prognostic factors in 616 patients (PMID 27185375). LDH defines M-category suffixes in AJCC 8th edition (Gershenwald 2017, PMID 29028110). ESMO melanoma guideline lists LDH as a key prognostic factor (Michielin 2019, PMID 31566661). Liu 2019: LDH below the median independently predicted non-progression. | Indirect link: hypoxia and lactate are immunosuppressive. Direct evidence that LDH shifts bulk immune scores is weak in the sources read. | **Mainly a prognostic or precision covariate.** Adjusting can improve precision but is not clearly needed to remove bias. Second tier. |
| **M-stage / visceral or liver / brain metastasis** | Tumeh 2017 and Yu 2021 (liver). Liu 2019 Table 1 (brain metastases). Weide 2016 (metastasis beyond soft tissue and lung). | Liver metastasis: yes (Yu 2021). The others are unclear. | Second tier, ideally coded as liver metastasis (yes or no) where available. |
| **ECOG performance status** | Urothelial: ECOG, liver metastasis and LDH are among five prognostic factors on PD-L1 inhibitors (Sonpavde 2020, PMID 32552295). Pre-ICI urothelial prognosis uses ECOG, haemoglobin and liver metastasis (Bellmunt 2010, PMID 20231682). Kidney: Karnofsky is part of the MSKCC and IMDC risk scores (Heng 2009, PMID 19826129). | No direct evidence that it shifts tumour immune expression. | Prognostic. Second tier. Rarely documented here (2 cohorts). |
| **Kidney risk group (MSKCC/IMDC)** | CheckMate 025 reports nivolumab benefit across MSKCC risk groups (Motzer 2015, PMID 26406148). Braun 2020 used MSKCC risk as a covariate. Heng 2009 defines IMDC. | Braun 2020 reports genomic and immune features by MSKCC risk group (section heading). | **Braun-specific covariate.** Documented. |
| **Age** | Kugel 2018: older melanoma patients respond better to anti-PD-1, with age-related differences in intratumoural CD8 and Treg cells (PMID 29898988). | Same study: intratumoural Treg and CD8 composition varies with age. | **Confounder candidate**, weak to moderate, but cheap (1 df) and often documented. |
| **Sex** | Conforti 2018 meta-analysis of RCTs: ICI survival benefit is larger in men than in women (PMID 29778737). This is a treatment-effect modifier in RCTs, not a within-arm response predictor. | Sex differences in immunity are well known, but bulk-tumour immune-score evidence was not in the sources read. | Weak. Third tier. |
| **Baseline steroids** | Arbour 2018: ≥10 mg prednisone at ICI start was associated with worse outcomes in NSCLC (PMID 30125216). | Systemic immunosuppression. | Documented only in Liu (STEROIDS_GT_10MG_DAILY). Sensitivity only. |
| **PD-L1 IHC** | Predicts response in NSCLC (Reck 2016, PMID 27718847) and gastric cancer (Fuchs 2018, PMID 29543932; Kim 2018). | IFN-γ induces PD-L1, so PD-L1 IHC partly measures the same inflamed-tumour axis as the panels. Ascierto 2016 calls it a "surrogate marker for an immune-reactive TME". | **Do not adjust.** Adjusting would partly remove the signal being measured. Report it descriptively or as a named sensitivity only. |
| **TMB / MSI / EBV** | Rizvi 2015, NSCLC (PMID 25765070). Kim 2018: EBV and MSI-H in gastric cancer. | TMB, MSI and EBV are upstream causes of infiltration, so they are common causes, not mediators. | Biologically a confounder. But it is a tumour-genomic covariate, adjusting would answer a different question ("immune expression beyond TMB"), and it is DNA-derived and missing in most non-WES cohorts. **Named sensitivity analysis, not the main set.** |
| **Tumour purity / RNA-derived composition** | — | Purity strongly confounds bulk immune expression (Aran 2015, PMID 26634437). | **Excluded by SPEC v2.1 section 4.3** for RNA outcomes. Composition is described in section 4.4. Not reopened here. |

**Small-sample methods evidence.** Each extra parameter costs precision, and logistic models need roughly 10 or more events per variable to avoid bias, although that threshold is not universal (Peduzzi 1996, PMID 8970487; van Smeden 2016, PMID 27881078). Firth's correction handles separation (Heinze 2002, PMID 12210625). The A contrast is a mean difference, which can be estimated from a linear model with response plus covariates. Unlike an odds ratio, a mean difference is **collapsible**, so in principle adjusted and unadjusted g on the same patients estimate comparable quantities, as long as the standardising SD is fixed. With n ≤ 30, though, even 1–2 covariates noticeably widen the interval.

---

## 4. PROPOSED minimal estimable adjustment set and rule (for the user's decision; NOT SIGNED)

Proposed ID: `A3_CLIN_MINIMAL_V0_PROPOSED`. It follows the A3 sheet's suggested missingness and no-imputation stance and does not replace it.

### 4.1 Estimand and model (proposed)
- **Primary stays unadjusted**, unchanged.
- **Adjusted sensitivity, per study:** a linear model with the panel score as the outcome, response (R versus NR) as the term of interest, and the covariates for that study. The adjusted g is the response coefficient divided by the same pooled within-group SD used for the unadjusted g in that study, with Hedges' small-sample correction. Any technical-batch term already required stays in.
- The unadjusted g is always re-reported **on the same complete-case patients**, so a change in population can be told apart from an adjustment effect.

### 4.2 Which studies may carry an adjusted estimate (proposed)
- **Eligible:** n_evaluable ≥ 30 **and** the smaller response group ≥ 8.
- **Not eligible** (unadjusted only, stated in the table): Hugo, GSE168204, GSE135222, GSE136961, GSE145996, GSE165278, GSE67501, GSE122220, GSE140901, GSE111636.
- **Potentially eligible, using registry n:** Riaz, Liu, Gide, Braun, Van Allen, GSE176307, Kim, GSE93157, GSE218989, GSE159067. The smaller-group check needs response counts, so it waits for the release step.
- **Covariate budget:** at most floor(n_evaluable / 15) covariate degrees of freedom, and never more than 3. For Riaz (49) that is 3, Van Allen (40) 2, Kim (45) 3. Categories are collapsed to binary, and age is linear per decade.

### 4.3 Which covariates may enter, per study (proposed)

A covariate enters only if **all** of the following hold, and only in the priority order below until the budget is used up:
1. It is **Y** in the matrix above. P-from-secondary-source counts only after the user accepts that source.
2. It is measured **before the first ICI dose** (or at the specimen) and is not derived from the response, from RNA or from the outcome.
3. **Availability ≥ 90 %** of the study's evaluable patients. This is computed outcome-free in the A3 availability table.
4. It **varies**: the smaller category has ≥ 10 % of patients and ≥ 5 patients.
5. **Estimable with the response contrast:** no empty response × covariate cell, and the model is not rank-deficient. This step needs the outcome, so under the current lock it is run mechanically at the release step. If a covariate fails, it is dropped and the next one in priority order is tried. Terms are never dropped after looking at the effect estimate.

**Fixed priority order (cross-cancer):**

| Rank | Covariate | Coding notes |
|---|---|---|
| 1 | Prior ICI exposure | Where it varies, e.g. prior anti-CTLA-4 in Riaz, Liu, Gide. Unknown history is not "naive". |
| 2 | Specimen site | Lymph node vs other; or primary vs metastasis; liver lesion where coded. |
| 3 | Cancer-specific burden or risk, one variable | Melanoma: LDH elevated (> ULN), else M1c+ vs lower. Kidney: MSKCC/IMDC intermediate-or-poor vs favourable. Urothelial: liver metastasis or ECOG ≥ 1. HNSCC: ECOG ≥ 1. Lung: ECOG ≥ 1, else none. Gastric: none (EBV and MSI are excluded as biomarkers). |
| 4 | Number of prior systemic lines | 0 vs ≥ 1; or prior MAPKi in BRAF-mutant melanoma. |
| 5 | Age | Linear, per 10 years, at ICI start. Age at diagnosis is accepted only with a flag. |
| 6 | Sex | |

**Never in the set:** PD-L1 IHC, TMB, MSI, EBV, RNA-derived composition or purity, anything post-baseline, anything outcome-selected. PD-L1 and TMB may form a separately named sensitivity in the cohorts that document them.

### 4.4 Missing data (proposed)
- Complete cases for the chosen set.
- No imputation and no missing-indicator category. Missing-indicator coding is biased outside randomised trials, and imputation would require using the outcome in the imputation model.
- If complete-case loss is more than 10 %, report the adjusted result as "population-changed" next to its same-patient unadjusted twin.

### 4.5 Synthesis (proposed)
- Adjusted estimates are reported **per study**.
- A cross-study "adjusted" pool is formed only if at least 4 studies carry adjusted estimates in the same endpoint family and cancer stratum. It is labelled a sensitivity, with its own same-study unadjusted pool beside it.
- Adjusted and unadjusted g are never mixed in one pool.

### 4.6 What this would likely give (from the matrix only, no outcomes)

| Study | Likely adjustment set |
|---|---|
| Liu | prior CTLA-4, biopsy site, LDH (3 df) |
| Riaz | prior ipilimumab, M-stage or LDH if documented, age (≤ 3) |
| Van Allen | biopsy site, LDH, prior lines (2–3) |
| Braun | MSKCC risk, prior lines, sample timing or site if documented (3) |
| GSE159067 | ECOG, prior lines, age (3); also see the regimen issue in still open |
| Gide | prior CTLA-4 and biopsy site, only if the iAtlas and Du sources are accepted |
| Kim, GSE176307, GSE93157, GSE218989 | Most likely unadjusted only, unless the unread Table 1s show per-patient fields |

So roughly 5–7 adjusted studies, all melanoma, kidney or HNSCC. The cross-cancer adjusted synthesis would therefore be thinner than the primary one and mostly melanoma.

### 4.7 Trade-offs for the decision

| Choice | Option A (proposed) | Alternative | Trade-off |
|---|---|---|---|
| Availability threshold | ≥ 90 % | ≥ 80 % | 80 % adds a few covariates (e.g. LDH with an Unknown category in Liu), but complete-case loss can change the population. 90 % keeps adjusted and unadjusted samples nearly the same. |
| Study-size gate | n ≥ 30 and smaller group ≥ 8 | Any n with ≥ 1 covariate | Small-n adjustment mostly adds noise. Ascierto, Amato and Nathanson-sized studies (7–11) cannot support even 1 df without high variance. |
| Common versus study-specific set | Study-specific set from a fixed priority list | One common set (e.g. age + sex everywhere) | A common set is cleaner to synthesise, but age and sex are the weakest confounders and are absent from about half the cohorts. A study-specific set is closer to the confounding evidence but has heterogeneous estimands. |
| Prior ICI | Adjust | Stratify (spec already splits drug class) | Stratifying halves small studies. Adjusting assumes a common effect across strata, which Riaz and Liu suggest may not hold. A reasonable compromise: adjust in the main sensitivity, and report the interaction descriptively only in Liu (largest). |
| PD-L1 / TMB | Exclude from main set | Include | Including them conditions on part of the immune axis being measured (PD-L1) or on a DNA cause the panel partly reflects (TMB). It answers "expression beyond biomarker", which is a different question. |
| Secondary sources (iAtlas, Du 2021, linked Snyder record) | Do not count until accepted | Count as Y | Accepting them widens Riaz, Gide and GSE165278 coverage, but they add identity and harmonisation risk. The registry already flags the run-to-patient identity problem for Gide. |

---

## 5. Still open

1. **Unread primary sources.** Table 1 or supplementary columns are still needed for:
   - Gide 2019 (Table S1), Kim 2018 (Table 1), Rose 2021 (Table 1; GEO characteristics not inspected by design), Prat 2017 (Table 1 / S1), Foy 2022 EJC (the primary GSE159067 paper; the Data-in-Brief companion was read), Braun 2020 (Table S1 column names), Jung 2019 (Supplementary Table 3 columns), Kang 2024 (Supplementary Data 8 columns), Hsu 2021 (Supplementary Tables 2–3).

   These were blocked by publisher 403s or have no PMC full text. Each is resolved by an outcome-free header read in the A3 availability audit.
2. **Per-patient completeness, coding and timing** (e.g. LDH within 28 days in Liu; age at diagnosis versus at ICI start in iAtlas and Hugo) belong to the outcome-free A3 availability table and are not settled here.
3. **GSE159067 regimen.** Foy 2022 says the CLB-IHN cohort was treated with PD-1/PD-L1 antibodies "alone or in combination with an anti-KIR or an anti-CTLA4 antibody". ICI-plus-anti-KIR is not ICI monotherapy or dual ICI under section 2. The registry entry does not record this split. This is an inclusion question for the user, separate from adjustment.
4. **GSE218989 versus GSE135222 overlap.** Both come from Samsung Medical Center lung cohorts. Kang 2024 says its cohort includes "previously reported cases". This should be checked under the A-P2 patient-overlap rule (15 Nov amendment) before both enter synthesis.
5. **GSE111636 and GSE122220** have no linked publication. Unless the depositors are contacted, they will remain unadjusted only.
6. **Decisions for the user:**
   - (a) accept or amend `A3_CLIN_MINIMAL_V0_PROPOSED`, including the thresholds in 4.2–4.4;
   - (b) whether secondary or linked sources count;
   - (c) whether PD-L1 and TMB get a named sensitivity;
   - (d) whether N13 (A1) should reuse this priority list.
