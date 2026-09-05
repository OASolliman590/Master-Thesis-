# Paper A: clinical transfer and endpoint evidence audit

Checked 2026-09-05. Research only; no production analysis. All new artifacts are in `planning/next_evidence/A_clinical_transfer/`; the canonical repository was not modified during this task.

## Findings that change the proposed paper

1. **Do not claim that prostate ICI transcriptomes do not exist.** A published pembrolizumab/enzalutamide study contains pretreatment prostate transcriptomics, but this audit has not located a downloadable complete matrix with linked labels for that cohort. A different prostate trial, COMBAT, has demonstrably public processed transcriptomics and sample-level response fields. Its sequential BAT/nivolumab design prevents interpreting overall response as the effect of ICI alone.
2. **Response-label harmonization is already a published contribution.** Kang2023 explicitly harmonized response using response categories and six-month PFS. Stable-disease responder definitions with external validation also precede us. A generic harmonization-plus-benchmark manuscript would overlap substantially.
3. A possible remaining contribution is **quantifying endpoint-definition sensitivity on exactly the same patients and scores**, with provenance, censoring-aware endpoint eligibility, independent replication, and an explicit audit of how apparent transportability changes. This is a candidate gap, not a verified 'first'.

## Closest primary studies and resources

| Primary source and date | Verified overlap | Consequence for our novelty |
|---|---|---|
| Kang et al., *Cancers*,2023-08-14. DOI [10.3390/cancers15164094](https://doi.org/10.3390/cancers15164094). Full XML inspected.|29 analysis datasets from16 accessible studies,39 biomarker sets/48 scoring measurements, broad response/survival benchmark. Their methods explicitly discuss RECIST/irRECIST, PFS and mixed definitions, then apply a combined response/PFS rule.|Neither a large score comparison nor response harmonization alone is new. Dataset partitions also must not be counted as independent studies.|
| Luo et al., *Annals of Oncology*, online2022-05-06. DOI [10.1016/j.annonc.2022.04.450](https://doi.org/10.1016/j.annonc.2022.04.450). [Primary full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10001430/).|Studied heterogeneity within RECIST stable disease. Proposed PFS>6 months plus no tumour growth as an SD-responder definition, with external NSCLC trial validation.|Do not claim discovery that SD is heterogeneous or all SD means benefit. Their more restrictive SD rule requires tumour-change and follow-up fields, not merely a categorical label.|
| Yang et al., *Cancer Immunology Research*,2022. DOI [10.1158/2326-6066.CIR-22-0249](https://doi.org/10.1158/2326-6066.CIR-22-0249). [Author-hosted primary paper](https://guolab.wchscu.cn/static/ICBatlas/ICBatlas.pdf).|ICBatlas organizes transcriptomic/clinical ICB data and response/treatment contrasts across studies.|A larger reusable download collection does not by itself distinguish the thesis. Atlas labels still require original-study provenance.|
| Liang et al., posted2026-04-07, **preprint**, [arXiv2604.05478](https://arxiv.org/abs/2604.05478).|Independent-cohort benchmark of nine bulk/single-cell predictors; reports limited generalisability.|'Existing models fail externally' is already a directly competing question. Keep peer-review status explicit.|
| Hashim et al., posted2026-04-01, **preprint**, DOI [10.48550/arXiv.2604.00739](https://doi.org/10.48550/arXiv.2604.00739).|BioCOMPASS evaluates leave-cohort-, cancer-type- and treatment-out schemes. [Original repository](https://github.com/hashimsayed0/BioCOMPASS/blob/main/README.md).|Those split schemes are validity controls, not a novel method by themselves.|

The Kang wording for its combined rule needs careful implementation review: it describes responders through CR/PR/SD and PFS>6 months, and nonresponders through PD or SD with PFS<6 months. Boundary handling at exactly six months, short censored follow-up, and the scope of the PFS condition must be checked against original code/tables before reproducing its labels. This audit inspected the published prose; it did not verify the executable implementation. [Kang primary source](https://pmc.ncbi.nlm.nih.gov/articles/PMC10452274/).

## Actual prostate data coverage

### COMBAT: public and usable for a qualified question

The original trial report is Markowski et al., *Nature Communications*,2024-01-02, DOI [10.1038/s41467-023-44514-2](https://doi.org/10.1038/s41467-023-44514-2). Patients received three cycles of BAT before nivolumab was added. Its gene-expression response grouping uses confirmed PSA50 or objective response, and most responses occurred during BAT monotherapy. The paper provides processed RNA in GSE229555 while raw RNA is unavailable publicly. Thus it supports exploration of response to the **sequential regimen**, not attribution of response to PD-1 blockade.

Actual samples-only GEO metadata retrieved here:

| Unit/field | Verified value |
|---|---|
| GEO accession |[GSE229555](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE229555), public2023-04-12|
| Assay records |30|
| Unique `subjectid` values |15|
| `time point` |15 `Pretx`;15 `C4D1`|
| Pretx `psa50 response` |7 YES;8 NO|
| Pretx `radiographic response` |4 YES;11 NO|
| Other source fields |`change in psa from baseline`, `change in tumor volume from baseline`, `batch`, `subjectid`|
| Biopsy compartment |Laser-capture tumour-enriched regions; not unbiased whole-TME sampling|
| Processing annotation |RSEM/STAR, hg38; metadata describes pmeTPM|
| Processed matrix listing |`GSE229555_FinalExpectedCounts_COMBAT_RNAseq_MatchedPairs.xlsx`, approximately4MB; not downloaded in this audit|

A filename saying expected counts and metadata saying pmeTPM are not interchangeable. Inspect workbook headers/values and author methods before choosing a scoring transform. The GEO labels also need temporal reconciliation: they must not silently inherit final-trial response interpretation if originally derived for the BAT-only analysis. The earlier biological publication concerns BAT response: Sena et al., *JCI*,2022, DOI [10.1172/JCI162396](https://doi.org/10.1172/JCI162396).

The40,029-byte original COMBAT source workbook was downloaded and its XML inspected. It contains sheets with `Pt #`, `Best PSA @ C4D1`, `Best PSA on Nivolumab`, `subjectID`, `clinical response`, `PT ID`, `Objective RESPONSE`, `PSA RESPONSE`, `Confirmed PSA50 Response`, and response-time columns. The inventory preserves cell coordinates so missing cells do not shift columns. These are candidate mapping/timing sources; a complete validated join to the15 transcriptomic patients was not performed. Do not derive RECIST CR/PR/SD/PD from a YES/NO field or numeric shrinkage alone: new lesions and other criteria matter.

### Guan: clinical prostate transcriptomics exists; full reuse is unresolved

Guan et al., *Nature*, published2022-03-23, DOI [10.1038/s41586-022-04522-6](https://doi.org/10.1038/s41586-022-04522-6), reports pretreatment metastatic biopsies before pembrolizumab in men progressing on enzalutamide. The single-cell cohort has eight patients (three responders/five nonresponders);16 other patients have bulk RNA. Response was sustained PSA decline>25%, not RECIST objective response. The public data-availability statement promises GEO deposition without an accession and directs additional trial data to author request. Source figure workbooks exist, but no complete reusable expression-plus-label package was verified here.

A2025 mechanistic reanalysis uses the same cohort, so it is not independent replication. [Chesner et al., DOI10.1158/2159-8290.CD-24-0559](https://doi.org/10.1158/2159-8290.CD-24-0559). A2026 AR/immune pan-cancer paper cites the same source and offers a [Code Ocean capsule](https://codeocean.com/capsule/7694890/tree/v3); its contents could not be inspected through the web tool. Availability remains unresolved, not disproven. [Original2026 article](https://aacrjournals.org/cancerrescommun/article/6/1/17/771449/Elevated-Tumor-Associated-Androgen-Receptor).

### CheckMate650: molecular resource, not verified clinical RNA test set

Sharma et al., *Nature Communications*,2026-05-08, DOI [10.1038/s41467-026-72242-w](https://doi.org/10.1038/s41467-026-72242-w), offers public CODEX spatial proteomics through [Zenodo](https://zenodo.org/doi/10.5281/zenodo.17652425); clinical access is subject to the BMS/Vivli process. Its TCGA-PRAD RNA analysis concerns survival in a separate dataset. It does not turn untreated TCGA patients into a prostate ICI response-validation cohort. No open trial bulk-RNA/response package was established in this audit.

**Search conclusion:** prostate ICI-related transcriptomic data exists, and public COMBAT RNA/response metadata is confirmed. An adequately sized, independent, directly downloadable prostate cohort with the same objective-response endpoint and a suitable regimen for our intended transfer claim has **not yet been secured**. This is a bounded search result, not proof of universal absence.

## Non-prostate endpoint coverage: what the current records really permit

Existing original-source metadata in `planning/feasibility` was re-inspected:

- GSE91061 has explicit `visit (pre or on treatment)` and `response` categories. These permit baseline selection and CR/PR versus SD/PD comparisons, subject to patient deduplication and unknown-label exclusions.
- GSE176307 has `io.response`, `io.therapy`, `pfs`, `progressed`, and treatment duration. Verify biopsy timing and clinical definitions before admission. Censored follow-up must stay distinct from progression.
- GSE126044 exposes binary `patient response` and pretreatment status; those fields alone cannot reconstruct which patients had SD.
- GSE135222 exposes `progression-free survival (pfs)` and `pfs.time` rather than categorical best response. It cannot enter a CR/PR/SD/PD contrast without additional primary annotations.

Sources: [GSE91061](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061), [GSE176307](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176307), [GSE126044](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE126044), [GSE135222](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135222). No '1,300 eligible independent patients' count was established.

## One exact proposed estimand

**Design recommendation, not a reported finding or agreed endpoint replacement:** retain the narrow endpoint-sensitivity question. Use fixed CYT, defined as the geometric mean of nonnegative TPM expression of **GZMA and PRF1**, higher score predicting response, with ties awarded one-half. Require both genes; do not swap in a successful score after results. The two-gene basis originates in [Rooney et al., Cell2015, DOI10.1016/j.cell.2014.12.033](https://doi.org/10.1016/j.cell.2014.12.033); selecting TPM as the required input is our implementation choice.

For each eligible cohort j, compute on **exactly the same baseline patients**:

`Delta_j = AUROC(CYT, Y_DCR) - AUROC(CYT, Y_ORR)`

where `Y_ORR=1` for CR/PR and0 for SD/PD; `Y_DCR=1` for CR/PR/SD and0 for PD. Missing/unevaluable responses are excluded from both. These are two different clinical endpoints; neither defines treatment benefit perfectly. DCR is not six-month durable clinical benefit.

Primary programme summary: equal-weight average of `Delta_j` within each represented cancer, followed by equal-weight average across represented cancers. This defines a finite, prespecified cohort collection estimand and prevents one large melanoma cohort determining the result. Eligibility requires evaluable positive/negative classes under both definitions and at least one SD patient; sparse groups remain visible with uncertainty and cannot become strong evidence by pooling cells or repeated biopsies.

Validation: freeze scoring, mapping and eligible cohorts before scoring; paired patient bootstrap within cohorts retains each patient's two endpoint labels together. Report each cancer/cohort estimate, patient counts, confidence intervals, and leave-cohort/cancer-out summary sensitivity. With a fixed score there is no fitted classifier and therefore no honest claim of 'nested model cross-validation'. Any secondary trained model must separately use patient-disjoint nested training, hold out whole cohorts/cancers, and fit transformations only within training. No label-derived feature selection may see holdouts.

This metric measures dependence of discrimination on endpoint definition, not improvement caused by harmonization. A follow-up durable-benefit comparison is secondary and requires sufficient event/censoring/time data; the Luo SD criterion additionally requires tumour-change measurements. Do not impute clinical endpoints merely to increase sample count. [Official iRECIST guidance](https://recist.eortc.org/irecist/) further shows why confirmed/unconfirmed progression cannot be collapsed without the required observation history.

**Prostate alternative:** if a suitable directly labelled prostate cohort becomes available, add a locked, regimen-specific external AUROC for its own documented endpoint, separately from the primary paired ORR/DCR estimand. For current COMBAT this can at most be an exploratory sequential-regimen test after temporal label validation. If access/endpoint matching remains unresolved, finish the cross-cancer endpoint analysis and present PRAD scoring only as molecular transport characterization. Do not call immune-phenotype agreement or untreated PRAD survival 'clinical ICI validation'.

## Proceed decision and remaining gates

Proceed only with a **narrow, conditional Paper A**. Its distinct contribution must be demonstrated by the matched-patient endpoint comparison and a reusable provenance/error audit beyond prior harmonization. If the audit leaves only a few informative SD cases or largely recapitulates the existing papers, combine it with the thesis methods/B rather than promise a separate publication.

Open gates:

1. Inspect actual original biomarker implementations and all candidate cohort clinical supplements; resolve response criteria, timepoints, repeated patients and six-month boundaries.
2. Identify additional informative cohorts with recoverable SD and sufficient events. Current binary-only datasets cannot automatically supply this.
3. Inspect GSE229555 matrix units/headers and validate its15 patient joins and exact outcome timing against both publications/source workbook.
4. Resolve Guan bulk/scRNA public package and Code Ocean contents through documented access; do not send author requests without user authorization.
5. Exclude original signature-development cohorts from purported independent validations; the same trial reused in multiple papers is one source cohort.
6. Record all later additions and protocol deviations; no prostate access delay should silently change clinical endpoints or convert phenotype into clinical validation.

Artifacts: [COMBAT metadata summary](A_clinical_transfer/COMBAT_metadata_summary.json), [source workbook inventory](A_clinical_transfer/COMBAT_source_inventory.json), original `GSE229555_gsm.soft`, `COMBAT_source.xlsx`, two primary article XMLs, and request/provenance scripts. The family metadata request exceeded its5MB cap and the Guan EuropePMC XML endpoint returned404; both failures are recorded. A smaller samples-only GEO request succeeded. No production scoring, fitted model, inferential result or canonical-repo mutation occurred.
