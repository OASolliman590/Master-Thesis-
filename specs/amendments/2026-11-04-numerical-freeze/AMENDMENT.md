# Numerical freeze and gene sets for Papers A and A-LONG (4 Nov 2026)

**Status: DRAFT 3 (5 Nov 2026), NOT SIGNED.** Nothing is frozen until the user signs. No responder or non-responder result exists on real data, and none will be computed until this is signed. All numbers here come from signed specs, gene availability or synthetic software checks. Evidence: `docs/research/NUMERICAL_FREEZE_EVIDENCE_20261104.md`. Decisions: `docs/wayfinding/NUMERICAL_FREEZE_20261104/MAP.md`. Deviations: `DEVIATIONS.md`.

**Changes from draft 2.**
- Strict coverage stays the main rule. Draft 2's 90% override is withdrawn, so no signed coverage text changes.
- IFN-gamma coverage is corrected to 8 of 20 complete studies. Draft 1 said 1 and draft 2 said 9, and both were wrong. Draft 2's 9 assumed a TXNIP mapping with no support.
- The TXNIP identifier proposal is withdrawn. Ensembl lists `ENSG00000117289` as retired at release 75 with no replacement.
- Families, sampling, analysis settings, custom methods and the environment record are now fully specified.

## What signing does

It fills `specs/A/NUMERICAL_FREEZE_REGISTER.tsv` from `NUMERICAL_FREEZE_REGISTER.proposed.tsv`, fixes the gene sets in this folder, and meets gates 1 and 2 of `specs/A/SPEC_v2.md` section 11. It does not unlock outcome analysis: see "Still open".

## Gene sets

MSigDB 2026.1.Hs, through the pinned `msigdbr` 26.1.1. This is deliberately not the latest release (2026.2): the package pin is tied to 2026.1. The hashes below are the authority, because `msigdbr` fetches its data at run time. Attribution: `NOTICE.md`.

| File | Sets | Use | SHA256 |
|---|---:|---|---|
| `hallmark_2026.1.Hs.gmt` | 50 | singscore pathways (formal), fgsea (descriptive) | `01f390fb123ac08c75874030233a4252122c9d7f97c1e173366b587438f57ad5` |
| `reactome_2026.1.Hs.gmt` | 1,839 | fgsea only (descriptive) | `4e1b4a6231ccb812985bffef6b9991bc54745c1b72bbcbcd2d132d5188b006bb` |

`HALLMARK_INTERFERON_GAMMA_RESPONSE`: 200 genes, membership SHA256 `51d3b96ed77916fc7da2e2dfcde2fbdee4a8dc3f3a2c60f469050889bc4cf714`.

## Decisions

### 1. Coverage rule: strict main, 90% and common-gene sensitivities

**Scope: A-BIO only.** A-LONG keeps its complete-coverage rule (`specs/A1/SPEC_v2.md`, section 4) and its own multiplicity rules. A-P2 is unchanged.

**Rule.** The main result for every panel and all 50 Hallmark sets needs complete coverage after aliases and identifier additions. This is the signed rule, and only the main result supports a claim.

**"Measured"** means a valid observed value in that study's matrix. Zero counts as measured. Each study has one fixed gene subset per set, and a patient missing any gene in that subset gets no score. Scores never average over a different gene list for each patient.

**Evidence** (patient-free, all from the audit tables below):

| Check | Result |
|---|---|
| IFN-gamma, 20 studies | 8 complete, 14 at 90% or more |
| IFN-gamma, A-P2 baseline studies | melanoma 2 of 5 complete, 5 of 5 at 90%; bladder 1 of 1; gastric 1 of 1 |
| All 50 sets, studies complete | 2 to 13, median 9 |
| All 50 sets, studies at 90% or more | 13 to 16 |
| Drop each other study's missing genes | median correlation at least 0.998 for every set |
| Common genes only | median correlation at least 0.974 (mean), 0.940 (singscore) |
| Worst single comparison | -0.07 (singscore, KRAS signaling DN) |
| Targeted gene subsets | 39 of 50 sets below 0.90 median by both methods |

Reduced sets usually track the full score, but not always, and a correlation does not show they measure the same thing. That supports a sensitivity analysis, not a change to the main rule. No published threshold has evidence behind it, so 90% is a judgement. Coverage counts are not k: k also depends on endpoint and stratum eligibility, and is reported with each result.

**Cost of this rule, stated before results.** Main IFN-gamma results lose Riaz, Liu, Van Allen, Braun, GSE135222 and GSE111636. Those studies appear only in the sensitivity families.

**Common-gene sets.** The study universe is the 16 non-targeted signed development studies. For each set, take the studies with at least 90% coverage (13 to 16 studies), then intersect their available members. Memberships are fixed once, here, and are not recomputed after endpoint or stratum exclusions. They are listed and hashed in `docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv`. They hold 27 to 189 genes. A membership below 10 genes would not be scored; none is. A study enters only with every common gene measured.

**Identifier additions** (`gene_aliases_addendum.tsv`, on signing): the 23 mappings in `docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv`, each a one-to-one match in the local GTF, including `ENSG00000112096` SOD2. The RIGI/DDX58 alias is applied to gene-set members. Other gaps stay gaps. GSE145996's comma-joined rows, such as `HLA-A,HLA-G,HLA-H`, are never split, because each row mixes several genes.

**Audit tables** (SHA256):

| File | SHA256 |
|---|---|
| `docs/cohorts/HALLMARK_COVERAGE.tsv` | `8247abfd23a57135fd228afbeda6886ffd54e1ab037e818f8a2d058510a5baac` |
| `docs/cohorts/HALLMARK_IDENTIFIER_AUDIT.tsv` | `43137b13a9ae1c30eff2cfc2941337df3aad2b2b1ff10e42ba7f6af35fd3b2ce` |
| `docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv` | `7f90583f0548cafecd57a3a059c087ea9d3b945867e09262fec3c23e13287d84` |
| `docs/cohorts/HALLMARK_BRIDGING.tsv` | `d37a27bd18a8f9ca2c96531ef8e046588e4270a6c8b6143bd3eed3686d19d53d` |
| `docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv` | `1ce5611a406b98d96016eed697ccaf2642df847ca0907fc7f877da65b9d53e51` |

### 2. Families

BH FDR 10% runs separately within each family, stratum and endpoint family. Families overlap, so each FDR statement holds for its own family only. **There is no manuscript-wide FDR guarantee.** Results are presented in the order of this table, not by best family.

| Family | Units | Score | Coverage | Studies | Role |
|---|---|---|---|---|---|
| `panel` | 11 custom panels | unweighted mean | complete | any platform | supports claims |
| `m5m6_gene` | 21 M5 and M6 genes | gene on study scale | gene measured | any platform, including targeted | only source of claims about these genes |
| `gene` | all genes | gene on study scale | gene measured | whole transcriptome and arrays only | discovery; M5/M6 rows flagged, never claimed |
| `pathway` | 50 Hallmark sets | singscore | complete | non-targeted | supports claims |
| `panel_coverage90` | 11 custom panels | mean of fixed study subset | at least 90% | any platform | sensitivity |
| `pathway_coverage90` | 50 Hallmark sets | singscore on fixed study subset | at least 90% | non-targeted | sensitivity |
| `pathway_common` | 50 Hallmark sets | singscore on common genes | all common genes | non-targeted | sensitivity |
| `targeted_subset` | Hallmark subsets | mean | as measured | 4 targeted studies | per study; no pooling, no FDR |

- This resolves `panel_coverage90` as eleven panels. IFN-gamma's main result is now strict, so the two no longer duplicate each other.
- Genes pool at k of 3 or more in `m5m6_gene` and `gene`. A gene can have a different k in each, so the two are separate effect identities.
- Keeping M5 and M6 in `gene` is a choice, not a reporting need. Power is low at small k, and this is stated before results.
- Sensitivity families never support a claim alone. Disagreement with the main result is reported.
- IHW is not used: 21 genes are too few. `fraction` (A-COMP) waits for the quanTIseq pin.

### 3. Random numbers

All resampling indices are drawn in R, under Mersenne-Twister, Inversion and Rejection. Python draws no random numbers, except scanpy through its `random_state` argument. A step that has one task uses its stream seed directly. A step with many tasks uses `seed = strtoi(first 7 hex digits of SHA256("<stream seed>|<task id>"), 16L)`.

| Stream | Seed | Task id |
|---|---:|---|
| `a_p2_bootstrap` (signed) | 20261102 | one task |
| `a_p2_splits` | 20261103 | `<study>|rep<01-20>` |
| `fgsea` | 20261104 | `<dataset>|<endpoint>|<collection>` |
| `sc_embedding` (PCA, neighbours, UMAP, Leiden) | 20261105 | `<atlas>` |
| `b_bootstrap` | 20261106 | set by Paper B's own contract |
| `second_check` | 20261107 | `<stream>` |
| `a_p1_bootstrap` | 20261108 | one task |

- **Order:** rows are sorted by study, then patient key in C locale, before any draw. Strata run R then NR, or O, SD, PD.
- **Bootstrap:** the seed is set once. Replicates run 1 to 2,000 in order, each using `sample.int` with replacement within each stratum.
- **Splits (20 repeats):** within each study and response class, permute with `sample.int(n)`. The first `floor(0.7 n + 0.5)` patients train and the rest test.
- **Receipts:** assignments stay in `results/`, and the manifest records their hash.
- **fgsea:** `set.seed` immediately before each call, `nproc = 1`, keep `log2err`.
- **Single cell:** the neighbour graph uses one thread.
- **Second check:** bootstrap and fgsea run once more under `second_check`. It is reported only: bootstrap interval ends beyond 0.01 AUROC, or any fgsea BH decision that flips, are flagged. It never replaces the main result, and nothing is rerun because of it.
- **No seed needed:** leave-one-family-out folds, singscore with `tiesMethod = "min"`, unshrunk DESeq2, limma-trend and `prcomp`.

### 4. Bootstrap contracts

| | A-P2 (N08) | A-P1 (N08B, new proposal) |
|---|---|---|
| Estimand | paired delta AUROC | delta between ORR and DCR AUROC |
| Strata | binary ORR class | original O, SD, PD category |
| Resample | patients, with both scores | patients, with fixed score and category; both AUCs from the same resample |
| Repetitions and interval | 2,000; 95% percentile (signed) | 2,000; 95% percentile |
| Reading | conditions on the fitted model and test cohort | conditions on category counts |

### 5. Ridge solver

```r
glmnet(x, y, family = "binomial", alpha = 0, lambda = 0.1,
       standardize = FALSE, intercept = TRUE,
       control = list(thresh = 1e-10, maxit = 1e6))
```

This matches the signed objective. Responder is the modelled class, and standardisation uses the sample SD (n - 1). The test checks KKT residuals and a direct optimiser on synthetic data, and fails above 1e-6. Receipt: `docs/validation/NUMERICAL_FREEZE_CHECKS.md` (jerr 0, direct-fit difference 2.28e-7, KKT 2.19e-9). This is a software check, not biological validation. No retry: any non-zero `jerr` stops the run.

### 6. Analysis settings

| Step | Frozen setting |
|---|---|
| singscore | `rankGenes(tiesMethod = "min")`; `simpleScore(upSet, knownDirection = TRUE)`, default centring; no down set; background is every gene in the study's matrix after collapse |
| DESeq2 | keep genes with non-zero total count; `independentFiltering = FALSE`; package defaults for Cook's outliers; unshrunk log2FC |
| limma | `lmFit`, then `eBayes(trend = TRUE)`, `robust = FALSE`; no gene filter |
| Design | `~ [recorded within-study batch] + response`; not full rank means not estimable |
| fgsea | `fgseaMultilevel`, `minSize = 15`, `maxSize = 500`, `eps = 0`, other arguments default; ranked on the DE statistic, ties by gene symbol, missing statistics dropped |
| Adjustment | unadjusted only |

**Clinical adjustment is deferred.** `specs/A/SPEC_v2.md` section 4.3 asks for a prespecified baseline clinical set. No such set is frozen here. Adjusted models stay locked until a separate signed note fixes each study's set from covariate availability alone, and sets rules for missing covariates.

### 7. Panels are custom expression features

All eleven are unweighted means with their own method IDs. Permitted use: per-study Hedges g and pooling in the `panel` and `panel_coverage90` families, for A-BIO only. This supersedes the listed registry status for that use only.

| Method ID | Registry status superseded for A-BIO |
|---|---|
| `CUSTOM_MEAN_P_ANTIGEN_PRESENTATION` | `controlled_by_ANALYSIS_md_not_frozen_by_registry` |
| `CUSTOM_MEAN_AYERS_GEP_18` | no score released |
| `CUSTOM_MEAN_HALLMARK_INTERFERON_GAMMA_RESPONSE` | `blocked_until_official_release_membership_and_method_are_frozen` |
| `CUSTOM_MEAN_HOPE_18` | no validated composite established |
| `CUSTOM_MEAN_M0_EXTRA_ANTIGEN_PRESENTATION` | `registry_only_no_score_authorized` |
| `CUSTOM_MEAN_M1_MOBILITY` | `registry_only_no_score_authorized` |
| `CUSTOM_MEAN_M2_CYTOTOXICITY` | `registry_only_no_score_authorized` |
| `CUSTOM_MEAN_M3_VIRAL_MIMICRY` | `registry_only_no_score_authorized` |
| `CUSTOM_MEAN_M4_EXCLUSION` | `registry_only_no_score_authorized` |
| `CUSTOM_MEAN_M5_CHECKPOINT_CANDIDATES` | `registry_and_locus_audit_only_no_score_authorized` |
| `CUSTOM_MEAN_M6_EPIGENETIC_REGULATORS` | `context_registry_only_no_score_authorized` |

Published-score restrictions stay. `AYERS_GEP_18` here is not the published weighted GEP, and HOPE_18 is not a validated composite. Effects describe expression direction only. No sign flips are added and no panel orientation is claimed. A-P2 and A-LONG use panels under their own signed text.

### 8. Environment

**Configuration frozen; production verification pending.** The AIU smoke gate stays open.

| Item | Value |
|---|---|
| `r/renv.lock` | `8ccd9f41d6e3e50cd0690202e1f1e3f442702f9439baf398687c26dc8d96f7bc` |
| `envs/sc-analysis/requirements.lock` | `d82d0bc145f1f7ea5495b6af7ac0129a4544c82e37b0db969457fee30b0eb965` |
| Software | R 4.6.1, Bioconductor 3.23 |
| Container | none |
| CPU | Intel Core i9-9880H, recorded in every manifest |
| Threads | 1 for fgsea and the neighbour graph |

## Outside the register

- At signing: an external timestamped registration (OSF) carrying the commit hash.
- `DEVIATIONS.md` in this folder, already started.
- A prior-knowledge statement: gene availability and cohort-level response counts have been seen; no association with response has. One audit run loaded the GSE176307 outcome section into memory and printed only field names and counts (`DEVIATIONS.md`).

## Code needed after signing

1. Seed streams, sampling and receipts in the resampling, `fgsea_rank.R` and single-cell steps.
2. New families, with a platform guard on `gene` (`tools/a_meta/features.py:118`).
3. Fixed per-study subsets in place of per-patient averaging (`tools/a_meta/features.py:445`), and the IFN-gamma panel in the feature path.
4. Addendum entries; aliases and Hallmark targets applied on the pathway route.
5. Frozen gene-set files as default input, hashes checked; fgsea limits of 15 and 500 in place of 1 and 5,000 (`tools/a_bulk/core.py:495`).
6. Common-gene memberships as input, hashes checked.
7. The ridge fit and its test.
8. Custom method IDs in outputs.

## Still open

- The full prior-exposure gate of `specs/A/SPEC_v2.md` section 11 item 3: IMvigor210 and development cohorts, including the 19 cohorts of the Lin 2026 signature validation. Signing does not narrow it.
- quanTIseq pin (N15), A-LONG windows (N12, N13), handoff (N14).
- Clinical adjustment sets (decision 6).
- AIU smoke (decision 8).
- Paper B's Tier 1-3 gene lists, whose sources must still be obtained.
