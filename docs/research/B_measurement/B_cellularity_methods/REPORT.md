# B-E4: cellularity estimands and cross-cohort use

6 September 2026. Methods/field QC only. **B-P and B-R remain proposed.** No patient outcome, methylation association, prediction, numerical harmonization or purity conversion was computed. The root's current GDC sample/aliquot linkage audit is separate.

## Original methods: similar labels do not establish the same measurement

**qpure.** The paper calls its target tumour cellularity, but calibrates its regression using mixtures of cancer-cell-line DNA and matched normal DNA. It selects normal-heterozygous SNPs in tumour single-copy-loss regions, estimates separation of B-allele-frequency clusters, and predicts cellularity from the calibration curve. Therefore its direct calibration is DNA admixture; a general ploidy-adjusted cell-count fraction is not demonstrated. The authors discuss ploidy and heterogeneity as confounders and use mixture modelling to mitigate their influence; this is not explicit joint estimation of cellular fraction and genome-wide ploidy. Low-content samples have poorly separated/unimodal clusters and a nonlinear calibration below approximately 20%. Paired normal data and usable BAF/log-R measurements are required. **Inference:** inadequate informative LOH or erroneous loss/cluster identification can undermine identifiability; a nonmissing output is not proof of accuracy. [Song et al. 2012](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0045835), Model Generation steps 1–4, Results on d-score, and Discussion. Do not relabel every qpure estimate as an exact DNA-mass fraction either: it remains a model-based cellularity estimate with DNA-mixture calibration.

**ABSOLUTE.** Its purity parameter alpha is cancer-cell fraction, estimated jointly with malignant-cell ploidy tau from relative copy-number profiles; somatic mutation allele fractions may supply additional information. Its mixture has average ploidy `D = alpha*tau + 2*(1-alpha)`. Consequently cancer DNA fraction is `alpha*tau/D`, not generally alpha. The method supports total or allele-specific copy ratios; LOH is informative but not a universal required event. Ambiguous purity/ploidy solutions are resolved using cancer-karyotype models. The paper distinguishes called, non-aberrant, insufficient-purity and polygenomic results. Low purity, absent informative somatic copy changes and heterogeneous profiles therefore affect callability; complete cases can be a selected population. [Carter et al. 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC4383288/), Results “Inference of sample purity and ploidy,” Figure 1/equation 1, Figure 3 and Online Methods; DOI [10.1038/nbt.2203](https://doi.org/10.1038/nbt.2203). This formula describes the model distinction; it is not authorization to transform Fraser values.

## Exact Fraser source field and scale

The original supplement page 3 defines `Qpure Cellularity` as an estimate from matched blood/tumour SNP-array profiles. Its separate `ASCAT Cellularity`, `ASCAT Ploidy`, pathological cellularity and LUMP fields must retain their own meanings. The supplement does not document an additional conversion of qpure into ABSOLUTE-compatible cancer-cell fraction. [Fraser supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnature20788/MediaObjects/41586_2017_BFnature20788_MOESM323_ESM.pdf), page 3; reference 8 on page 19 cites Song.

Actual cached Supplementary Table 1: `Sheet1`, column **K**, header **Qpure Cellularity**. Across 284 rows there are **214 numeric entries and 70 literal `NA` entries**; numeric range **0.12–1.00**, all 214 values at most one. Cells use `GENERAL` format, not Excel percentage formatting. Operationally the deposited field is on a **0–1 fractional scale**, not 0–100; dividing it by 100 would corrupt the recorded values. This is whole-table field QC, not an eligible-patient count. Source: [original supplementary tables archive](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnature20788/MediaObjects/41586_2017_BFnature20788_MOESM324_ESM.zip), retained `Fraser2017_Table01.xlsx`.

## Consequences for the two proposed B contracts

These are design inferences, not comparative-validation findings supplied by the papers.

| Contract | What the sources permit | What remains unjustified |
|---|---|---|
| B-P: frozen TCGA predictors evaluated in CPC-GENE | Identify an actual non-RNA-derived CPC covariate and preserve its native units and provenance. | Treating an ABSOLUTE-trained purity coefficient as transferable to qpure solely because both range from zero to one. Training-fold standardization changes units, not biological calibration or measurement error. No external distribution matching, rank matching, coefficient refit or ploidy-based correction is automatically allowed. |
| B-R: independent within-cohort adjusted associations | A proposed amended contract could name ABSOLUTE and qpure as distinct cohort-specific nuisance measurements, with independently fitted adjustment coefficients. It would test replication under these specified measured-covariate adjustments. | Claiming both cohorts condition on the same perfectly measured cellular fraction, or that independently fitting nuisance terms eliminates residual cell-composition confounding. Method-dependent measurement error can change residual associations. This is not a workaround for missingness or poor specimen linkage. |

A scalar cellularity estimate also does not identify immune versus stromal fractions, malignant-cell methylation, or malignant-cell expression. Consequently either design needs its existing limits on cell-origin and causality claims.

Before freeze, the contract needs named estimators/versions and field meanings; same-specimen or explicitly accepted specimen-policy linkage; valid-call and missingness rules; and a justified strategy for differing measurement methods. A bridge dataset measuring both methods on the same specimens, or a common independently justified measurement, could inform comparability. Neither was established here. Mere correlation, source-wide range similarity, or selecting the adjustment giving stronger methylation results would not establish calibration. No primary was selected, omitted or weakened during this audit.

## Question/answer ledger

| Question | Answer class | Evidence / specification impact |
|---|---|---|
| Is Fraser column K genuine cellularity rather than SNP agreement? | Verified source definition | Supplement page 3 and original header; the distinct WGSvsOS agreement field remains excluded. |
| Is the deposited qpure scale 0–100? | Verified field QC: no | Range, number formats and missing tokens above; retain original fractions. |
| Are qpure and ABSOLUTE proven interchangeable? | Unresolved; no affirmative evidence | Original method comparison above; B-E4 comparability gate remains open. |
| Does qpure handle ploidy exactly like ABSOLUTE? | Verified methodological distinction | Cluster-mixture mitigation versus explicit joint purity/ploidy inference; do not infer equal estimands from labels. |
| Can B-R proceed with different nuisance measurements? | Proposed conditional design only | Needs an explicit amended adjustment target and sensitivity/claim limits; it is not already approved. |
| Do field presence or successful calls establish unbiased eligibility? | No; methodological inference | Preserve callability/missingness and specimen-linkage audit; no final N asserted. |

## Provenance and boundaries

Fraser files were reused, not downloaded: `Fraser2017_Table01.xlsx`, 38,116 bytes, SHA-256 `9e1921e2667e5bf78e040557d7a2e68ab4770fdd42ea6679ba489bcd65a2b7a6`; supplement PDF, 4,470,341 bytes, SHA-256 `db2e84e39f6869065501eeda656ff0afcc5fbbbf10357d6c95c62e7bc6f8adbe`. Both are under `planning/next_evidence/B_specimen_resolution/`. Read supplement text with bundled pypdf and only qpure field/header/range/missingness with bundled openpyxl. No dependency changes.

Original qpure text was accessible through the browser research tool. Direct ABSOLUTE Nature/PMC pages were intermittently unavailable; the browser tool's indexed original PMC full-text result exposed the relevant equations and Methods/Results, and those primary-source passages were used. An attempted Europe PMC fullTextXML request returned HTTP 404; no successful new source-file payload or patient matrix was retained. No author contact, tool execution, estimator rerun, causal analysis or canonical repository edit occurred. No credentials were read or copied.
