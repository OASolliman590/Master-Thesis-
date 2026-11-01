# Novelty check for the four thesis claims (2026-10-29)

Literature check only. Nothing was downloaded, no code changed, no analysis run.

## How this was made

- **Source:** PubMed through NCBI E-utilities (`esearch` sorted by relevance, `esummary`, `efetch` abstracts), with requests at least 1 s apart. About 40 queries were run: 3–5 per claim, plus anchor-paper lookups. PMC full text was used only where an earlier session had already read it (the epigenetic + ICI trials in section 5 of `ICI_COHORT_SEARCH_EXPANDED_20261028.md`).
- **Verification:** every PMID below was checked against its PubMed title. "What they did" is taken from the abstract unless marked otherwise. Anything not confirmed from the abstract is marked **UNVERIFIED**.
- **Limits:**
  - PubMed relevance search is noisy in this area: many single-cancer "X-related gene signature" papers. Those were skimmed and are not listed one by one.
  - Preprints, bioRxiv-only work, conference abstracts and Google Scholar were not searched, so a recent preprint could overlap.
  - Verdicts are about published PubMed-indexed work up to October 2026.
- **Closeness scale:** **High** = does the same thing on overlapping data. **Medium** = the same idea with a different scope or method. **Low** = shares one ingredient.

---

## Claim 1. Endpoint sensitivity

*Meta-analysis of transcriptomic response signatures in ICI cohorts, testing whether conclusions change with the response definition (ORR CR/PR vs SD/PD, clinical benefit including durable SD, irRECIST), per study, pooled per cancer and pan-cancer.*

| PMID | Year | Paper | What they did | Closeness |
| --- | --- | --- | --- | --- |
| 33508232 | 2021 | Litchfield et al., Cell | Pan-cancer meta-analysis of more than 1,000 CPI-treated patients (exome + RNA, 7 tumour types). Uses **one standardised clinical-outcome criterion**; clonal TMB and CXCL9 were the top predictors. | Medium: same pooled design, but the endpoint is fixed, not varied |
| 36055464 | 2022 | Bareche et al., Ann Oncol | Computed TMB and **37 published gene-expression signatures** across pooled ICB cohorts (meta-analysis). | Medium–high: the closest signature meta-analysis. The abstract does not say whether the response definition was varied (**UNVERIFIED**; check the methods) |
| 38117502 | 2024 | Cancer Res (large meta-analysis) | 3,037 ICI-treated patients, 14 solid tumour types; signature meta-analysis (TMB, IFNG, PDCD1, macrophage–T-cell interaction). | Medium: same pooling, one endpoint |
| 35781709 | 2023 | Mol Carcinog | Re-evaluated **28 published expression signatures across 8 melanoma ICI cohorts** for reproducibility. | Medium: reproducibility across cohorts, not across endpoint definitions |
| 42399673 | 2026 | COMPASS, Nat Med | Pan-cancer transcriptomic foundation model, benchmarked against **22 methods across 16 ICI cohorts**. | Low–medium: benchmark of predictors, not of endpoints |
| 36095221 / 36049666 | 2022 / 2023 | ICBatlas; TIGER | Curated ICB transcriptome resources with response / non-response labels. | Low: resources; each fixes one response split |
| 35533926 | 2022 | "Deciphering radiological stable disease to ICIs", Ann Oncol | Systematic review of SD in ICI trials. Defined the SD subgroup whose survival matches responders (cut-points on best % change + PFS) and related SD vs response to TCGA proliferation expression. | **High on the concept** (SD is ambiguous and should be split); does not re-run signature meta-analysis under alternative endpoints |
| 30670497 | 2019 | CheckMate-010 irRECIST biomarker study, Clin Cancer Res | In nivolumab-treated ccRCC, compared biomarker associations (PD-L1, multiplex IF, **RNA-seq T-cell activation signatures**) under RECIST 1.1 vs irRECIST endpoints. | **High, but for one trial and one cancer**. The direct precedent for "the endpoint changes the biomarker conclusion" |
| 29182990 | 2018 | Eur J Cancer | RECIST 1.1 vs irRECIST vs iRECIST discordance in 160 NSCLC ICI patients (clinical only). | Low: endpoint discordance, no molecular data |
| 30127393 / 30127394 | 2018 | TIDE; IMPRES, Nat Med | Signature papers validated on cohorts with a single response split. | Low: they are among the signatures to be tested |

**Verdict: PARTLY DONE.** Signature meta-analyses exist (Litchfield, Bareche, the 2024 Cancer Res study, the melanoma reproducibility paper, COMPASS), and the "SD is ambiguous" and "irRECIST changes biomarker associations" points are each published (35533926 for SD; 30670497 for irRECIST, in one ccRCC trial).

**Still new:** No paper found re-runs the same signature meta-analysis **systematically across response definitions** (ORR vs clinical benefit vs irRECIST) and reports how often significance, effect direction or ranking flips, per study, per cancer and pan-cancer. That makes endpoint choice the object of study, not a fixed input. Keep two caveats:
- Check Bareche 2022's methods first (UNVERIFIED whether they ran a sensitivity analysis on the endpoint).
- irRECIST labels exist for very few public cohorts, so that arm will be thin.

---

## Claim 2. The chain (ICI response genes → TCGA methylation control via multi-omics → pre-registered test in epigenetic drug + ICI trials)

### Link 1: response genes from ICI cohorts (genome-wide DE + pre-specified immune panels)

| PMID | Year | Paper | What they did | Closeness |
| --- | --- | --- | --- | --- |
| 33508232, 36055464, 38117502 | 2021–2024 | (see claim 1) | Response genes and signatures from pooled ICI cohorts | **High**: this link is well done |
| 28650338 | 2017 | Ayers et al., J Clin Invest | IFN-γ-related mRNA profile predicts PD-1 response | High for the IFN-γ panel |
| 30309915 | 2018 | Cristescu et al., Science | Pan-tumour TMB + T-cell-inflamed GEP for pembrolizumab | High for the inflamed GEP |

**Link 1 verdict: ALREADY DONE** as a stand-alone step. It is only the input to the chain.

### Link 2: methylation control of those genes in TCGA via multi-omics integration

| PMID | Year | Paper | What they did | Closeness |
| --- | --- | --- | --- | --- |
| 29628290 | 2018 | Thorsson et al., Immunity (Immune Landscape of Cancer) | TCGA pan-cancer immune subtypes (C1–C6) from expression, with regulatory and epigenetic correlates. Regulator methylation was reported as part of the analysis (from memory; **UNVERIFIED** in the abstract) | Medium: TCGA immune landscape, not ICI-response genes, not MOFA/DIABLO |
| 31537801 | 2019 | Jung et al., Nat Commun | Global methylation loss in partially methylated domains represses immunomodulatory genes and correlates with immune evasion, independent of TMB. Validated in lung and melanoma ICI cohorts. | **High on the biology** (methylation → immune evasion → ICI resistance); does not start from ICI-derived response genes or use factor-model integration |
| 30355485 | 2018 | Saghafinia et al., Cell Rep | Pan-cancer landscape of aberrant DNA methylation in TCGA (title verified; immune content **UNVERIFIED**) | Low–medium |
| 28714863 | 2017 | Jeschke et al., J Clin Invest (MeTIL) | Methylation-based immune (TIL) signature across cancers | Medium: methylation as an immune readout |
| 31202362 | 2019 | Adv Cancer Res | CpG markers whose methylation tracks GZMA, PRF1, PDCD1 and CTLA4 expression across TCGA cancers | Medium |
| 38566132 | 2024 | Genome Med | Conserved methylation signatures (NMF on 2,465 TCGA profiles) associated with the tumour immune microenvironment and ICI response | **Medium–high**: TCGA methylation linked to ICI response, but the direction is methylation-first, not response-genes-first, and NMF, not MOFA/DIABLO |
| 30100403 | 2018 | EPIMMUNE, Lancet Respir Med | Methylation signature predicting anti-PD-1 benefit in NSCLC | Medium: methylation predicts ICI response directly |
| 34281986 | 2021 | J Immunother Cancer | Methylation deconvolution classifier predicting ICI response in melanoma | Medium |
| 41545302 | 2026 | J Immunother Cancer | **MOFA2** on plasma cfDNA methylation + EV-miRNA in 79 ICI-treated NSCLC | Medium on method: MOFA with methylation in an ICI setting, but liquid biopsy, not TCGA tissue |
| 36050516 | 2022 | Commun Biol | HLA class I loss in prostate cancer tied to DNA methylation and H3K27me3; reversed by DNMT/HDAC inhibition | High for one gene family (also relevant to claim 3) |

**Link 2 verdict: PARTLY DONE.** That methylation controls immune and antigen-presentation genes and associates with ICI resistance is established (Jung 2019, MeTIL, 38566132, 36050516). **Still new:** starting from the ICI-response gene set and using MOFA+ / DIABLO with methylation + RNA + miRNA + RPPA across TCGA to assign each response gene a methylation-controlled vs not label. No paper found does this with that direction and those methods.

### Link 3: test in epigenetic drug + ICI trials (before vs after the drug)

| PMID | Year | Paper | What they did | Closeness |
| --- | --- | --- | --- | --- |
| 26317466 / 26317465 | 2015 | Chiappinelli; Roulois, Cell | DNMTi → dsRNA/ERV → interferon response ("viral mimicry"); predicts better ICI response (preclinical; Chiappinelli also used melanoma ICI data) | Mechanistic basis for the viral-mimicry panel |
| 29195073 | 2017 | Topper et al., Cell | Low-dose DNMTi + HDACi: IFN and antigen-presentation programme, reversal of immune evasion (NSCLC models) | Mechanistic basis |
| 35671108 | 2022 | Chen/Matei et al., J Clin Invest | Guadecitabine + pembrolizumab in ovarian cancer; before/after methylome + RNA in tumour biopsies (GSE188249/GSE186825) | **High for the data**: the before/after analysis exists for this trial, but it was descriptive, not a pre-registered test of TCGA-derived genes |
| 36928921 | 2023 | Clin Cancer Res | Guadecitabine + atezolizumab in urothelial cancer; no tumour hypomethylation or viral-mimicry induction after 2 cycles (GSE222934) | High for the data; a published **negative** result to anticipate |
| 39532835 | 2024 | Baretti et al., Nat Commun | Entinostat lead-in then + nivolumab in PDAC; RNA at baseline, after the lead-in, and on combination (GSE248014) | High for the data (descriptive) |
| 37739939 | 2023 | NIBIT-M4, Nat Commun | Guadecitabine + ipilimumab melanoma; integrated multi-omics at 5 years | High for the data (descriptive) |
| 40091844 | 2025 | J Clin Invest | 5-azacitidine + durvalumab + tremelimumab in HNSCC; paired biopsies, IFN-γ signature and CD274 rise in 3 of 8 | Medium–high (controlled data) |

**Link 3 verdict: PARTLY DONE.** Before/after transcriptomes of epigenetic drug + ICI trials have been analysed by their own authors, descriptively and trial by trial. **Still new:** a pre-registered, directional test of an externally derived gene set (from links 1–2) across several such trials. No paper found pre-registers a TCGA-derived, methylation-controlled response set and tests it in these trials.

### Full chain

**Verdict: NOVEL as a whole.** No paper found connects (1) ICI-response genes → (2) TCGA multi-omics methylation control → (3) a pre-registered test in epigenetic drug + ICI trials. Each link has close neighbours (Jung 2019 and 38566132 for link 2; the trial papers for link 3), so the novelty is the end-to-end chain and the pre-registration, not any single link. Be ready for the urothelial negative result (36928921) and for small public trial n (section 5 of the cohort note).

---

## Claim 3. Prostate: transferring responder programmes from other cancers' ICI cohorts to TCGA-PRAD methylation and expression

| PMID | Year | Paper | What they did | Closeness |
| --- | --- | --- | --- | --- |
| 36050516 | 2022 | Commun Biol | HLA-I loss in prostate cancer via DNA methylation and H3K27me3, reversible with DNMT/HDAC inhibitors; proposed as a reason ICB fails in prostate cancer | **Medium–high**: same question (why prostate cancer is cold) and the same epigenetic angle, but one gene family, no transfer of responder programmes |
| 33589522 | 2021 | J Immunother Cancer | NSD2/WHSC1 (H3K36 methyltransferase) regulates immune infiltration in prostate cancer (TCGA-PRAD + ChIP-seq) | Medium: epigenetic regulator → cold prostate |
| 42303814 | 2026 | Nat Biomed Eng | Restored MHC-I in prostate cancer (SPSB1 3'UTR) to sensitise to ICT in mice | Low–medium: mechanism, no transfer |
| 29628290 | 2018 | Thorsson, Immunity | PRAD sits mostly in the immunologically quiet / lymphocyte-depleted subtypes (from memory; **UNVERIFIED** in the abstract) | Low–medium: descriptive context |
| many (e.g. 35222640, 37600770, 40355680) | 2022–2025 | Single-cancer PRAD papers | Build a PRAD-specific "immune / X-related signature" and predict immunotherapy response with TIDE scores | Low: the reverse direction (PRAD-derived signature, TIDE as a proxy), no transfer from real ICI responders |
| 39190534 | 2024 | AMADEUS, J Exp Med | Pan-tumour nivolumab ± ipilimumab with multi-omic response signatures (prostate inclusion **UNVERIFIED**) | Low–medium: possible source of cross-cancer responder programmes |

**Verdict: NOVEL** (with an established background). Published work explains cold prostate cancer gene-by-gene (HLA-I, NSD2, MHC-I) or derives PRAD-only signatures scored with TIDE. No paper found trains or derives responder programmes in other cancers' ICI cohorts and transfers them to TCGA-PRAD expression **and methylation** to explain which programme is missing and whether it is epigenetically silenced. Position it against 36050516; that paper's HLA-I result is a natural positive control.

---

## Claim 4. Equation: an ICI-response predictor as an explicit equation for PK/PD or tumour-growth models

| PMID | Year | Paper | What they did | Closeness |
| --- | --- | --- | --- | --- |
| 38831056 | 2024 | LORIS, Nat Cancer | **Six-feature logistic regression** (clinical, pathologic, genomic incl. TMB; no expression) on 2,881 ICB patients; an explicit, monotonic response-probability score across 18 tumour types | **High on the "explicit equation" part**; not built as a PK/PD covariate and has no transcriptomic or epigenetic terms |
| 30127394 | 2018 | IMPRES, Nat Med | Score from 15 pairwise gene-expression comparisons (a closed-form rule) | Medium: explicit transcriptomic rule, no PK/PD use |
| 33792207 | 2021 | CPT Pharmacometrics Syst Pharmacol | **LASSO on high-dimensional omics → covariates in a tumour growth inhibition (TGI) model**; a two-step ML + pharmacometric approach (not ICI-specific per the abstract) | **High on method**: the omics-to-TGI-covariate pipeline exists; the ICI response-signature version does not |
| 34270868 | 2021 | CPT Pharmacometrics Syst Pharmacol | TGI–OS models across 10 atezolizumab trials (6,699 patients); baseline covariates (clinical/lab) by backward elimination | Medium: ICI TGI models with clinical covariates, no gene-expression covariate |
| 33280255 | 2021 | CPT Pharmacometrics Syst Pharmacol | ML (LASSO, boosting) for TGI–OS in OAK (atezolizumab) | Medium |
| 31721173 | 2020 | Clin Pharmacol Ther | Random-forest **cytokine signature** linked to nivolumab clearance and OS | Medium: omics → PK covariate, but blood cytokines, not tumour transcriptome |
| 32426472 / 34749885 | 2020 / 2021 | Sci Adv; eLife (Butner et al.) | Mechanistic ODE model of ICI response with interpretable parameters (growth rate, immune infiltration, therapy amplification), fitted to CT data | Medium: explicit tumour–immune equations; the infiltration parameter is not driven by a gene signature |
| 38861365 | 2024 | Cancer Res | Spatial QSP virtual trial informed by clinical spatial multi-omics (HCC) | Medium: omics feeding a mechanistic ICI model |
| 37328961 | 2023 | CPT Pharmacometrics Syst Pharmacol | TGI model for ICI-treated melanoma from real-world data, with covariate screening | Low–medium |

Symbolic regression: no ICI-response or oncology PK/PD paper found (the query returned only general methods papers, e.g. 31617228, 36690644).

**Verdict: PARTLY DONE.** Explicit sparse ICI scores exist (LORIS, IMPRES), and omics-derived covariates in TGI models exist methodologically (33792207). **Still new:**
- (a) an equation derived from **tumour transcriptomic / epigenetic response programmes** (not TMB or clinical features), written so that it plugs into a TGI or PK/PD model as a covariate on a named parameter (for example the kill rate or the immune term in a Butner-type model);
- (b) symbolic regression for this purpose, which appears unpublished.

State the claim as "transcriptomic predictor → covariate equation", since "explicit ICI predictor" alone is taken by LORIS.

---

## Summary table

| Claim | Verdict | Closest prior work (PMID) | What would still be new |
| --- | --- | --- | --- |
| 1. Endpoint sensitivity | PARTLY DONE | 36055464, 33508232, 35533926, 30670497 | Systematic re-run of a signature meta-analysis across ORR / clinical benefit / irRECIST, reporting flip rates per study, per cancer, pan-cancer |
| 2. Chain (full) | NOVEL as a whole | Link 2: 31537801, 38566132; Link 3: 35671108, 36928921, 39532835 | The end-to-end chain plus a pre-registered test in epigenetic drug + ICI trials; MOFA+/DIABLO on ICI-derived genes |
| 2a. Link 1 alone | ALREADY DONE | 33508232, 36055464, 28650338 | Nothing (it is the input) |
| 2b. Link 2 alone | PARTLY DONE | 31537801, 38566132, 28714863 | ICI-response-gene-first direction; factor-model integration with 4 omics layers |
| 2c. Link 3 alone | PARTLY DONE | 35671108, 36928921, 39532835, 37739939 | Pre-registered directional test of an external gene set across trials |
| 3. Prostate transfer | NOVEL | 36050516, 33589522 | Transfer of responder programmes from other cancers' ICI cohorts to PRAD expression + methylation |
| 4. Equation | PARTLY DONE | 38831056, 33792207, 34270868, 32426472 | Transcriptomic / epigenetic predictor written as a TGI/PK-PD covariate; symbolic regression |

## Plain summary

1. **Endpoint sensitivity is partly done.** Signature meta-analyses exist (Litchfield 2021, Bareche 2022), and two papers show that SD handling (35533926) and irRECIST (30670497, one ccRCC trial) change conclusions. A systematic, multi-cohort endpoint-sensitivity analysis was not found. Check Bareche's methods before claiming it.
2. **The chain is novel as a whole, not link by link.** Response genes are well established. Methylation control of immune genes is established (Jung 2019, MeTIL, 38566132). Epigenetic drug + ICI trial transcriptomes have been analysed descriptively by their own authors. No paper strings them together with a pre-registered test.
3. **Prostate transfer is novel.** Prior work explains cold prostate cancer gene by gene (HLA-I methylation 36050516, NSD2) or with PRAD-only signatures scored by TIDE, not by transferring real ICI responder programmes.
4. **The equation claim is partly done.** LORIS (2024) is already an explicit six-feature ICI equation, and omics → TGI-covariate pipelines exist (33792207). The new part is a transcriptomic or epigenetic predictor built as a PK/PD covariate, plus symbolic regression.
5. **Caveats:** PubMed only, no preprints. Items marked UNVERIFIED (Bareche's endpoint handling, Thorsson's PRAD and methylation details, AMADEUS prostate inclusion) should be checked in full text before writing the thesis claims.

## Addendum, 30 Oct 2026: Lin et al., Cancer Cell 2026 (closest new neighbour for Paper A)
Lin Z, …, Becker JC, Aran D. "Tumor immune microenvironment remodeling predicts response to checkpoint inhibitor therapy." Cancer Cell 44(9):1847–1861.e6, 2026. PMID 42679812, doi:10.1016/j.ccell.2026.08.007. Read from the PubMed abstract only; the full text is not yet read.
- **What it did:**
  - built a longitudinal scRNA-seq atlas: 441 samples, 241 patients, 10 cancer types;
  - defined 77 immune and stromal subtypes and 4 conserved TIME subtypes;
  - found that about 40% of tumours shift state on therapy, and the transition predicts outcome better than the baseline state;
  - derived a **59-gene signature that predicted response and survival in 1,383 baseline tumours across 19 independent bulk cohorts**.
- **Effect on the claims:**
  - **Claim 1/A-P2 (a bulk predictor across cohorts):** this is now a strong 2026 neighbour. Our distinct parts remain endpoint sensitivity (the same estimate under ORR versus clinical benefit), the locked-panel structure, and the protected untouched final test.
  - **A.1 (on-treatment change):** directly supported; the transition matters more than baseline.
  - **The chain (Claim 2) and prostate (Claim 3):** not addressed by this paper; still novel as a whole.
- **Action items:**
  - add the 59-gene signature to the comparator registry if its genes and weights are published;
  - record which of its 19 validation cohorts overlap ours. If IMvigor210 is among them, it is PREVIOUSLY_INSPECTED for that comparator: still fair as a test for our learner, but the comparator's IMvigor210 performance is not unbiased;
  - check whether the atlas is public, as a possible SC-1 reference.
