# Numerical freeze and gene sets for Papers A and A-LONG (4 Nov 2026)

**Status: DRAFT 2, NOT SIGNED.** Nothing is frozen until the user signs. No responder or non-responder result exists on real data, and none will be computed until this is signed. All numbers here come from signed specs, gene availability or synthetic software checks. Evidence: `docs/research/NUMERICAL_FREEZE_EVIDENCE_20261104.md`. Decisions: `docs/wayfinding/NUMERICAL_FREEZE_20261104/MAP.md`.

**Correction to draft 1.** Draft 1 said only 1 of 20 studies has all 200 Hallmark IFN-gamma genes. That was wrong: the check missed the frozen RIGI/DDX58 alias and two old Ensembl IDs. The corrected figure is 9 of 20.

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

### 1. Coverage rule for Hallmark gene sets

Measured coverage of the 200 IFN-gamma genes, after identifiers:

| Group | Studies | Genes |
|---|---:|---|
| Complete | 9 | 200 |
| At least 180 | 5 (Riaz, Liu, Braun, Van Allen, GSE111636) | 191-198 |
| Below 180, whole transcriptome or array | 2 (GSE145996, GSE122220) | 176-177 |
| Targeted or NanoString | 4 | 65-85 |

No published threshold has evidence behind it, so 90% is a judgement, not a standard. Most tools silently use whatever genes are present.

**Proposed:**
- All 50 Hallmark sets, including IFN-gamma as the eleventh panel, use one rule: at least 90% of a set's members, fixed per study on the set of genes measured in that study, and a patient is scored only with all of those genes measured. For IFN-gamma that is at least 180 of 200.
- The ten short panels keep the strict rule, because each gene carries more weight there.
- **This overrides signed text:** panel-coverage amendment decisions 3 and 4, `specs/A/SPEC_v2.md` line 35, and analysis-modules lines 61 and 75, for Hallmark sets only. Strict results are shown beside them.
- Sensitivity: a fixed common-gene version of each set across included studies.
- The four targeted and NanoString studies are never pooled in Hallmark families. They are reported per study, under a custom name.
- Every result reports n_found and the missing genes.

**Alternative:** keep the strict rule with no override. Main IFN-gamma results then rest on 9 studies and lose Liu, Riaz, Van Allen and Braun. Other Hallmark sets also lose studies; the exact count needs the alias fix applied first.

**Identifier additions** (`gene_aliases_addendum.tsv`, on signing): `ENSG00000112096` SOD2 and `ENSG00000117289` TXNIP, and the existing RIGI/DDX58 alias applied to gene-set members. Remaining gaps were checked against NCBI synonyms and raw rows; none were recovered. Entrez-keyed studies were checked less fully.

### 2. M5 and M6 genes

One family of their own, BH FDR 10%, per stratum and endpoint family. Claims about these genes come only from this family. The same genes stay in the genome-wide family, flagged as discovery. Pooled at k of 3 or more, as for other genes. Power is low at small k, and this is stated before results. IHW is not used: 21 genes are too few.

### 3. Random numbers

Root seed 20261102. Each step has its own named stream, and generators are frozen with it:

| Stream | Seed |
|---|---:|
| `a_p2_bootstrap` (signed) | 20261102 |
| `a_p2_splits` | 20261103 |
| `fgsea` | 20261104 |
| `sc_embedding` (PCA, neighbours, UMAP, Leiden) | 20261105 |
| `b_bootstrap` | 20261106 |

R uses Mersenne-Twister, Inversion and Rejection. `fgsea`: `set.seed` immediately before each call, `nproc = 1`, keep `log2err`. Tested on synthetic data: same seed gives the same result, also at `nproc = 2`, and another seed differs. scanpy and Seurat already have fixed defaults; passing seeds explicitly makes that visible. Thread count is pinned to 1 for the neighbour graph, and embeddings are compared by tolerance. One second-seed check is reported for bootstrap and fgsea.

### 4. Ridge solver

```r
glmnet(x, y, family = "binomial", alpha = 0, lambda = 0.1,
       standardize = FALSE, intercept = TRUE,
       control = list(thresh = 1e-10, maxit = 1e6))
```

This matches the signed objective. Responder is the modelled class, and standardisation uses the sample SD (n - 1). The test checks KKT residuals and a direct optimiser on synthetic data, and fails above a tolerance of 1e-6. Result of a one-off synthetic run: see the map. No retry: any non-zero `jerr` stops the run.

### 5. Panels are named as custom expression features

All panels are scored as unweighted means and named "custom panel-expression features", as the validation amendment already does. `AYERS_GEP_18` is therefore not the published weighted GEP and is never called that. Effects describe expression direction only; no panel orientation is claimed. This authorises scoring where the registry says `registry_only_no_score_authorized`, for descriptive A-BIO use.

## Outside the register

- At signing: an external timestamped registration (OSF) carrying the commit hash.
- A dated deviation log, `DEVIATIONS.md`, in this folder.
- A prior-knowledge statement: gene availability and cohort-level response counts have been seen; no association with response has.

## Code needed after signing

1. Seed streams in `fgsea_rank.R` and the single-cell steps.
2. M5/M6 family in synthesis.
3. Hallmark coverage rule, per study, and the IFN-gamma panel in the feature path.
4. Addendum entries; aliases applied to gene-set members.
5. Frozen gene-set files as default input, hashes checked.
6. The ridge fit and its test.

## Still open

- IMvigor210 prior-exposure audit (Paper A gate 3).
- quanTIseq pin (N15), A-LONG windows (N12, N13), handoff (N14).
- Container digest: none is used; `renv.lock`, the Python lock and CPU are recorded instead.
- Paper B's Tier 1-3 gene lists, whose sources must still be obtained.
