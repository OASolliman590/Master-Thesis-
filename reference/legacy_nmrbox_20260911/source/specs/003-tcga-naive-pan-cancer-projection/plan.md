# Implementation Plan: TCGA Treatment-Naive Pan-Cancer Projection (v1)

**Branch**: `003-tcga-naive-pan-cancer-projection` | **Date**: 2026-03-27 | **Spec**: `specs/003-tcga-naive-pan-cancer-projection/spec.md`  
**Input**: Feature specification from `specs/003-tcga-naive-pan-cancer-projection/spec.md`

## Summary

Build a TCGA projection workstream that keeps discovery frozen in GEO ICI cohorts and uses treatment-naive TCGA as an external epidemiologic and survival projection layer.

This spec extends existing TCGA scaffolding (map/project/survival) into a full pan-cancer module with:

1. GEO-to-TCGA cancer mapping for the final 21-study roster.
2. Explicit treatment-naive filtering.
3. Per-project signature projection and survival modeling.
4. Epidemiological interaction modeling (demographics, stage, exposures, subtype).
5. Cross-cancer synthesis and concordance-tier evaluation (`GOLD`, `GOLD+SILVER`, `ALL`).

## Technical Context

**Language/Version**: Python 3.11 + R 4.3+  
**Primary Dependencies**: pandas, numpy, scipy, statsmodels, lifelines (optional), R `survival`/`survminer`  
**Storage**: TSV + Markdown + PNG artifacts under `results/tcga_naive_projection/`  
**Testing**: pytest contract/integration + CLI smoke checks  
**Target Platform**: local workstation + T7-backed storage  
**Project Type**: CLI module extension in existing pipeline  
**Constraints**: no leakage from discovery cohorts, no TCGA treated patients in primary analyses, missingness in exposure fields, unequal project sample sizes

## Current Baseline (Already Implemented in Code)

Inherited from spec-002:

- `python -m pipeline.cli tcga map` emits `tcga_sample_map.tsv` with expression/survival URLs and local paths.
- `python -m pipeline.cli tcga project` scores patients from frozen signature and emits project survival inputs/stats.
- `scripts/tcga_survival.R` runs Cox PH + Kaplan-Meier outputs per project.
- `python -m pipeline.cli validate run` can integrate TCGA survival outputs into concordance-driven validation artifacts.

This spec does not replace these pieces; it matures them into treatment-naive, epidemiology-aware, pan-cancer execution.

## Constitution Check

Gates applied:

- **Frozen Discovery Gate**: GEO discovery signatures remain frozen; TCGA is projection-only.
- **Naive Filter Gate**: primary analyses must use treatment-naive patients only.
- **Traceability Gate**: every exclusion must be explicit (treated/missing RNA/missing survival).
- **Cross-Cancer Comparability Gate**: output schema must be project-consistent.
- **No-Hard-Fail Gate**: data-gated blocks produce status artifacts instead of silent breaks.

Gate status: **PASS**

## Project Structure

### Documentation (this feature)

```text
specs/003-tcga-naive-pan-cancer-projection/
|-- plan.md
|-- spec.md
|-- research.md
|-- quickstart.md
|-- contracts/
|   `-- io-contracts.md
`-- tasks.md
```

### Source Extensions (planned)

```text
src/pipeline/
|-- cli.py                           # add tcga naive subcommands or options
`-- modules/
    |-- 16_tcga_naive_clinical_pull/
    |-- 17_tcga_epidemiology_models/
    `-- 18_tcga_pan_cancer_summary/
```

### Artifact Roots (planned)

```text
results/tcga_naive_projection/
|-- mapping/
|-- manifests/
|-- projection/
|-- survival/
|-- epidemiology/
|-- concordance_tiers/
`-- reports/
```

## GEO-to-TCGA Scope (Locked)

GEO cancer groups from final 21-cohort roster:

- Melanoma (8 cohorts)
- NSCLC (5 cohorts)
- HNSCC (4 cohorts)
- HCC (1 cohort)
- RCC (1 cohort)
- Stomach adenocarcinoma (1 cohort)
- Glioblastoma (1 cohort)

TCGA projects in v1:

- `TCGA-SKCM`
- `TCGA-LUAD`
- `TCGA-LUSC`
- `TCGA-HNSC`
- `TCGA-LIHC`
- `TCGA-KIRC`
- `TCGA-KIRP`
- `TCGA-STAD`
- `TCGA-GBM`
- `TCGA-PRAD` (comparative reference project)

## Execution Architecture

### Phase 1: Mapping and Registry

- Build frozen GEO-to-TCGA mapping table.
- Build TCGA project registry with cancer alignment and analysis eligibility flags.

### Phase 2: Naive Manifests

- Pull/flatten project clinical metadata.
- Derive patient-level `naive_flag`.
- Emit exclusion-reason ledger.

### Phase 3: Projection and Survival

- Score signatures per patient (`mean(up) - mean(down)`).
- Run project-level OS (and PFS/DSS if available).
- Emit per-project stats and plots.

### Phase 4: Epidemiology Interactions

- Demographic interactions (age/sex/race where powered).
- Stage and exposure interactions (smoking, alcohol, etc. as available).
- Molecular subtype interactions where fields exist.

### Phase 5: Pan-Cancer Integration

- Forest table/plot across projects.
- Heterogeneity summary (`I2`, `Q` where computable).
- Concordance-tier comparison (`GOLD`, `GOLD+SILVER`, `ALL`).

## Delivery Strategy

1. Reuse existing `tcga map` + `tcga project` as stable base.
2. Add naive-filter manifest stage before projection.
3. Add epidemiology model stage after survival stats.
4. Add pan-cancer synthesis stage and final report wiring.
5. Keep resume-friendly behavior with explicit skipped/blocking artifacts.
