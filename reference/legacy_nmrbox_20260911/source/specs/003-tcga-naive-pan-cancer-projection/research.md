# Research Notes: TCGA Treatment-Naive Pan-Cancer Projection (v1)

## Purpose

Lock the scientific and implementation decisions for TCGA projection as a dedicated post-discovery workstream.

## Locked Context

### Discovery-to-Projection Separation

- Discovery remains GEO-only (`R/NR`, `PRE/POST`, `TREATMENT_DELTA`) from the finalized 21-study cohort.
- TCGA is strictly projection and epidemiologic interpretation.
- No TCGA data enters discovery signature fitting.

### Why Treatment-Naive TCGA

- TCGA is largely pre-ICI era, so it is suitable for baseline biology projection.
- Main interpretation: prognostic and epidemiologic context of ICI-derived signatures in untreated tumors.
- It is not suitable for direct ICI responder/non-responder discovery.

## Locked GEO Coverage

- Melanoma: 8 cohorts
- NSCLC: 5 cohorts
- HNSCC: 4 cohorts
- HCC: 1 cohort
- RCC: 1 cohort
- Stomach adenocarcinoma: 1 cohort
- Glioblastoma: 1 cohort

Total cohorts in fixed GEO roster: 21.

## Locked TCGA Project Scope

- `TCGA-SKCM` (Melanoma)
- `TCGA-LUAD` and `TCGA-LUSC` (NSCLC alignment)
- `TCGA-HNSC` (HNSCC)
- `TCGA-LIHC` (HCC)
- `TCGA-KIRC`, `TCGA-KIRP` (RCC alignment)
- `TCGA-STAD` (Stomach adenocarcinoma)
- `TCGA-GBM` (Glioblastoma)
- `TCGA-PRAD` (comparative reference)

## Design Decisions

### Decision 1: Naive filtering is mandatory, not optional

- **Decision**: Primary analyses use only `naive_flag == 1`.
- **Why**: treatment history changes baseline interpretation and can confound signature-outcome links.

### Decision 2: Projection score definition remains fixed

- **Decision**: `signature_score = mean(up_genes) - mean(down_genes)`.
- **Why**: consistency with current pipeline implementation and previous evidence runs.

### Decision 3: Stratification defaults

- **Decision**: median split (`High`/`Low`) is primary; tertiles are sensitivity.
- **Why**: stable default with broad project comparability.

### Decision 4: Outcomes hierarchy

- **Decision**: OS is mandatory; PFS/DSS are optional when available and quality-checked.
- **Why**: OS availability is highest and most robust cross-project endpoint.

### Decision 5: Epidemiology interaction first, subgroup-only second

- **Decision**: use interaction models as primary evidence (`score * covariate`) rather than standalone subgroup slicing.
- **Why**: interaction terms directly test effect modification.

### Decision 6: Tiered validation is integral

- **Decision**: compare `GOLD`, `GOLD+SILVER`, and `ALL` signatures in TCGA.
- **Why**: tests whether replicated genes improve external projection utility.

### Decision 7: Data-gated execution status must be explicit

- **Decision**: stages with insufficient data emit `*_skipped.tsv` or status rows.
- **Why**: avoids silent failures and simplifies resume behavior.

## Covariate Families (v1 Priority)

- Demographics: age, sex, race, ethnicity
- Clinical: stage, grade, pathologic descriptors
- Exposures: smoking/alcohol fields where non-missing
- Molecular subtype: disease-specific markers where available

## Method Stack (v1)

- Projection scoring: Python (existing `tcga project` path)
- Survival modeling: R `survival`/`survminer` (existing `tcga_survival.R`)
- Interaction modeling: Python `statsmodels` or R Cox wrappers
- Pan-cancer synthesis: pooled TSV + forest plot utilities

## Non-Goals for v1

- Re-discovery of signatures in TCGA.
- Mixing treated and naive patients in primary analyses.
- Overfitting project-specific thresholds that break cross-cancer comparability.
- Claiming causal treatment response effects from non-ICI-era cohorts.

## Known Risks

- Incomplete treatment metadata across projects.
- Sparse exposure variables in some cancers.
- Subtype fields not uniformly available.
- Empty signatures from upstream discovery (projection blocked if no genes pass).

## Mitigation Strategy

- Standardized exclusion reasons in naive manifests.
- Per-project missingness summaries before modeling.
- Stage skip artifacts for underpowered analyses.
- Resume-friendly stage execution with preserved run-manifest lineage.
