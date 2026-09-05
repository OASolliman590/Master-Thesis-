# Paper B novelty update: final Arbet et al. publication

6 September 2026. **Bounded primary-source comparison; neither B-P nor B-R is selected, cancelled or scientifically frozen.** Final abstract/publication identity and publisher supplement catalogue were accessible. The final main PDF and supplement bodies were not retrieved: direct publisher retrieval returned HTTP 403, and the indexed page states that the main content is PDF-only. The parent found no cached final PDF/Table 3. No supplement, model object or matrix was downloaded; no patient-level or eight-gene effect table was inspected. Exact final-method claims therefore remain limited below.

## Confirmed final publication and scope

The correct current citation is Arbet et al., *The Landscape of Prostate Tumour Methylation*, **Cancer Discovery**, online 17 June 2026, DOI **10.1158/2159-8290.CD-25-0761**, PMID **42307031**. Its abstract reports **3,001 methylomes**, **884 samples with DNA and/or RNA multiomics**, four subtypes and predictors for 15 clinico-molecular features. The 884 are not necessarily 884 fully matched methylation/RNA/CNA specimens. [Final PubMed record](https://pubmed.ncbi.nlm.nih.gov/42307031/).

The final publisher catalogue identifies RNA–methylation–CNA correlation analyses, hypoxia associations, feature-selection/model comparisons, cohort-stratified model performance and multiomic biochemical-recurrence modelling. **Purity is already examined:** Supplementary Information 1 explicitly concerns race/ancestry/purity associations. This does not establish which final primary regressions adjusted for purity. Table 3 is the dataset inventory; Table 7 combines outcome annotations and model feature-importance content. These descriptions establish analysis scope, not the exact equations, gene results or specimen overlap. [Final publisher page, Supplementary data](https://aacrjournals.org/cancerdiscovery/article/doi/10.1158/2159-8290.CD-25-0761/785858/The-Landscape-of-Prostate-Tumour-MethylationThe).

## What the official software actually documents

The accessible [PrCaMethy reference site](https://uclahs-cds.github.io/package-PrCaMethy/reference/index.html) identifies **version 1.1.0**. Its [official tutorial, dated 17 October 2025](https://uclahs-cds.github.io/package-PrCaMethy/articles/Introduction.html), lists these 15 prediction targets:

- Age; ISUP grade; T category; categorical PSA.
- Copy-number loss in CHD1, NKX3-1, PTEN, CDKN1B, RB1, CDH1 and TP53; MYC copy-number gain.
- Log-transformed SNV density, percentage genome altered, and TMPRSS2–ERG fusion.

No antigen-presentation expression score or individual HLA-A/B/C, B2M, TAP1/2, PSMB8/9 expression target appears in that documented target list. That is a bounded list comparison, **not evidence that these genes were absent from genome-wide association analyses or model inputs**. The tutorial defines gene methylation using median promoter-CpG-island beta values. It still calls the manuscript forthcoming; its correspondence to the final accepted model objects/splits is unverified.

The [public source repository](https://github.com/uclahs-cds/package-PrCaMethy) provides R source, models/data, tests and a GPL-2 licence. I did not install it, inspect trained model coefficients/importance, or establish that it reproduces every analysis in the final article. It is a documented implementation/comparator candidate, not a validated replacement for our pipeline.

## Cohort overlap and remaining factual gaps

The predecessor manuscript identifies TCGA and ICGC PRAD-CA among its cohorts. This is **preprint evidence only**, and its publication version history contains materially different cohort totals. Do not promote predecessor sample counts, splitting rules or association formulas to final-study facts. [Predecessor PMC record](https://pmc.ncbi.nlm.nih.gov/articles/PMC11844408/), [PubMed's explicit update link](https://pubmed.ncbi.nlm.nih.gov/39990314/).

Consequently, substantial overlap with our intended TCGA/CPC substrate must be anticipated and audited, but **exact final CPC-GENE accessions, patient identifiers, RNA/methylation pairing and allocation to train/test remain unverified here**. The same named cohort is not proof that every planned patient was included. A new paper DOI is not a new independent cohort. Reusing public patients is permissible for a distinct analysis; it does not create independent confirmation of findings selected from those same patients in this predecessor/final study.

## Closest-study comparison and defensible proposed contribution

| Proposed alternative | Overlap that cannot be claimed as new | Potential additional answer — conditional design inference |
|---|---|---|
| **B-P: external incremental prediction** | Predicting prostate clinical/molecular features from methylation; integrating methylation with other variables; applying methylation models to held-out patients are established by the competitor's scope. | Does a **fixed APM expression program** receive incremental externally transported information from its promoter methylation beyond the identical age/grade/non-RNA-purity baseline? Frozen TCGA fitting, untouched CPC evaluation, paired external Delta_R2, calibration and precision are the specific proposed answer. Its distinction from the documented 15 targets is real; its novelty against the final complete analyses remains to be verified. |
| **B-R: replicated adjusted association** | Broad prostate methylation–RNA association, CNA relationships, gene-specific regulation and examining purity are already inside the competing study's scope. Eight selected correlations or a smaller promoter definition alone offer weak differentiation. | A predeclared eight-gene family with **same-direction replication under matched adjustment and measurement definitions**, rank-aware inference, familywise error control and explicit uncertainty may answer whether an APM relationship survives these restrictions. The contribution must come from that biological/measurement answer and its limits, not presenting standard IUT/Bonferroni machinery as new methodology. |

These are proposed questions, not promised positive findings. B-R may produce only targeted confirmation of an already reported relationship; B-P may expose failure of transport or negligible incremental information. Neither outcome alone determines publishability. A credible manuscript needs the exact competing estimands/results boundary established without choosing favourable genes after reading their effects.

## Concrete charter changes and reopening gate

1. Update the closest-study citation to the final DOI, preserving the preprint as version/access provenance. Remove claims that methylation–expression integration, predictive modelling, promoter aggregation or purity consideration are absent from prior prostate work.
2. Label the proposed distinction as **APM-specific adjusted replication** or **APM-specific incremental transport**, according to the eventual user-approved primary. Retain both options now. Keep malignant-cell origin and causal silencing outside the bulk-data claim.
3. Obtain the final PDF's methods, Table 3 inventory and a **target/feature-name-only** extract of relevant model metadata through an accessible original source. Required fields: association measure/model, promoter aggregation, covariate set including purity/CNA, train/test selection unit, cohort membership and identifiers/accessions. Do not open gene effect/importance rows to make the primary choice. A method-only auditor may inspect workbook sheet names and approved identifier columns under a recorded access rule.
4. Audit whether any borrowed annotation/features/model objects were learned using CPC outcomes. A pretrained PrCaMethy output is not automatically an independent baseline or an APM predictor. Freeze our gene/probe choices without competitor effect-guided selection and retain the existing historical-access ledger.

**Prior-access record:** this search exposed published abstract claims, supplement captions, earlier-version narrative/model-performance snippets and the official tutorial's example outputs. No eight-gene association signs/effects were deliberately inspected or used to choose an endpoint. Supplementary Tables 4/6/7 result bodies and model weights remain uninspected. This is a completed bounded novelty audit with a final-method/inventory access limitation, not a completed scientific novelty clearance.
