# Numerical freeze and gene sets for Papers A and A-LONG (4 Nov 2026)

**Status: DRAFT, NOT SIGNED.** Nothing is frozen until the user signs. No responder or non-responder result exists on real data, and none will be computed until this is signed. All numbers below came from the signed specs or from gene availability only.

## What signing does

It fills `specs/A/NUMERICAL_FREEZE_REGISTER.tsv`, fixes the gene sets in this folder, and meets gates 1 and 2 of `specs/A/SPEC_v2.md` section 11. It does not unlock outcome analysis by itself: the remaining gates below still apply.

## Gene sets

Source: MSigDB release 2026.1.Hs, through the pinned `msigdbr` 26.1.1. Cite MSigDB and Liberzon 2015 for Hallmark.

| File | Sets | Use | SHA256 |
|---|---:|---|---|
| `hallmark_2026.1.Hs.gmt` | 50 | singscore pathways (formal), fgsea (descriptive) | `01f390fb123ac08c75874030233a4252122c9d7f97c1e173366b587438f57ad5` |
| `reactome_2026.1.Hs.gmt` | 1,839 | fgsea only (descriptive) | `4e1b4a6231ccb812985bffef6b9991bc54745c1b72bbcbcd2d132d5188b006bb` |

`HALLMARK_INTERFERON_GAMMA_RESPONSE` has 200 genes. Membership SHA256, by the registry's contract with genes in sorted order: `51d3b96ed77916fc7da2e2dfcde2fbdee4a8dc3f3a2c60f469050889bc4cf714`.

## Decisions needing the user's judgement

1. **Coverage rule for the Hallmark IFN-gamma panel.** Under the strict rule, all 200 genes are needed, and only 1 of 20 studies qualifies. At 90% or more (180 genes), 14 of 20 do. The other six are the four targeted or NanoString panels (65-85 genes) and two studies at 176-177. **Proposed:** this one panel uses the 90% rule in the main analysis, per study and per patient, scored as an unweighted mean like the other panels. The 90% rule stays a sensitivity for the other ten panels. Strict coverage is shown alongside for this panel.
2. **M5 and M6 genes.** The signed spec says these genes are counted separately from panels. **Proposed:** one family of their own, BH FDR 10%, per stratum and endpoint family, separate from the genome-wide gene family. They stay in the genome-wide family as well, as discovery, where their values are not reinterpreted.
3. **One seed everywhere: 20261102**, already signed for the A-P2 bootstrap. **Proposed** for all other random steps: A-P2 splits, fgsea, UMAP, Leiden and Paper B's bootstrap.
4. **Ridge solver.** The signed objective is mean logistic loss plus (0.1 / 2) × Σ β². **Proposed:** `glmnet` 5.2, `alpha = 0`, `lambda = 0.1`, `standardize = FALSE`, `intercept = TRUE`, `thresh = 1e-10`, `maxit = 1e6`. A test must confirm the coefficients against a direct optimiser on synthetic data.

## Register

| ID | Setting | Value | Status on signing | Source |
|---|---|---|---|---|
| N01 | A-P2 weights | IMvigor210 weight 1; development: equal cancer, equal study within cancer | FROZEN | Validation amendment 1, 4 |
| N02 | A-P2 test size | At least 10 patients per ORR class, otherwise descriptive. Actual counts come at the release step | FROZEN (rule) | Validation amendment 1 |
| N03 | Development folds | Leave one study family out; at least 3 families; at least 20 R and 20 NR per training set; 20 repeated 70/30 splits as sensitivity | FROZEN | Validation amendment 3, 4 |
| N04 | Scale | log2(TPM+1) | FROZEN | Validation amendment 2 |
| N05 | Feature filter | None: the 4 locked panels | SUPERSEDED | Validation amendment 2 |
| N06 | Penalty | Ridge, 0.1, no search | FROZEN | Validation amendment 2 |
| N07 | Solver | Decision 4 | FROZEN | This note |
| N08 | Bootstrap | 2,000 paired, outcome-stratified, 95% percentile, seed 20261102 | FROZEN | Validation amendment 1 |
| N09 | A-BIO statistics | Hedges g, escalc defaults; DESeq2 for integer counts, limma-trend otherwise; within-study batch as a covariate if recorded; BH FDR 10% per family, stratum and endpoint family; families: panels, M5/M6 genes, genome-wide genes, Hallmark pathways, fractions, `panel_coverage90` | FROZEN | Analysis modules; decision 2 |
| N10 | Meta-analysis | REML, modified Knapp-Hartung (`test = "adhoc"`), metafor 5.2-1; subgroup test at k of 10 or more | FROZEN | Analysis modules |
| N11 | Panels | 10 locked panels as registered, plus Hallmark IFN-gamma, 2026.1.Hs; unweighted; coverage per decision 1 | FROZEN | Registry v1; decision 1 |
| N12 | A-LONG windows | Registered per study after the roster check | OPEN | A.1 spec, section 9 |
| N13 | A-LONG inference | Set with N12 | OPEN | A.1 spec, section 9 |
| N14 | Handoff to B and C | Not needed for Paper A results | OPEN | Handoff spec |
| N15 | Cell composition | quanTIseq version and options | OPEN | Paper A gate 5 |
| N16 | Environment | `r/renv.lock` sha256 begins 8ccd9f41d6e3e50c; `envs/sc-analysis/requirements.lock` begins d82d0bc145f1f7ea; full hashes recorded on signing | FROZEN | This note |

## Code needed after signing

1. Set the seed in `fgsea_rank.R` and the single-cell embedding steps. No analysis script sets one today.
2. Add the M5/M6 family to synthesis.
3. Add the Hallmark IFN-gamma panel to the feature path with the rule in decision 1.
4. Make the frozen gene-set files the default input, with hashes checked.

## What this does not freeze

- Paper B's Tier 1-3 gene lists: their sources (CRI landscape, ImmPort, TISIDB) still have to be obtained and pinned.
- A-LONG windows, and quanTIseq (N12, N13, N15).
- The IMvigor210 prior-exposure audit (Paper A gate 3).
