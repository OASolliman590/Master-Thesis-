# Tasks: TCGA Treatment-Naive Pan-Cancer Projection (v1)

**Input**: Design documents from `/specs/003-tcga-naive-pan-cancer-projection/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `quickstart.md`, `contracts/io-contracts.md`

## Status Snapshot (2026-03-28)

Baseline inherited from spec-002:

- `tcga map` exists and emits URL/local-path manifest.
- `tcga project` exists and emits per-project survival inputs/stats.
- `tcga_survival.R` exists (Cox + KM).
- `validate run` can summarize TCGA survival outputs in concordance context.
- `tcga naive-map` and `tcga naive-manifest` now exist for mapping + naive filtering scaffolds.
- `tcga epi-model`, `tcga pan-cancer`, and `tcga tier-validate` are implemented and wired into resume flow.
- Canonical operational runbook is maintained in `docs/USAGE.md`.

Current runtime caveat:

- Execution can still be data-gated (empty signature, missing local TCGA files, or insufficient powered cohorts), but these conditions are surfaced in status artifacts rather than hard failures.

## Phase 0: Spec Kit Initialization

- [x] T001 Create `specs/003-tcga-naive-pan-cancer-projection/spec.md`.
- [x] T002 Create `specs/003-tcga-naive-pan-cancer-projection/plan.md`.
- [x] T003 Create `specs/003-tcga-naive-pan-cancer-projection/research.md`.
- [x] T004 Create `specs/003-tcga-naive-pan-cancer-projection/quickstart.md`.
- [x] T005 Create `specs/003-tcga-naive-pan-cancer-projection/contracts/io-contracts.md`.
- [x] T006 Create `specs/003-tcga-naive-pan-cancer-projection/tasks.md`.

## Phase 1: Mapping and Registry

- [x] T007 Build `configs/tcga_naive_project_registry.tsv` covering SKCM/LUAD/LUSC/HNSC/LIHC/KIRC/KIRP/STAD/GBM/PRAD. *(Seed file created.)*
- [x] T008 Implement GEO-to-TCGA mapping builder and emit `geo_tcga_cancer_mapping.tsv`. *(`tcga naive-map` implemented and emits mapping + summary artifacts.)*
- [x] T009 Add mapping contract tests (required columns + allowed vocabularies). *(`tests/unit/test_tcga_naive_contracts.py::test_tcga_naive_map_contract_columns_and_vocab`)*

## Phase 2: Naive Filtering Data Layer

- [x] T010 Implement TCGA clinical flatten stage and emit `tcga_clinical_flat.tsv`. *(`tcga naive-manifest` implemented.)*
- [x] T011 Implement treatment-naive derivation rules and emit `tcga_naive_patient_manifest.tsv`. *(`v1_keyword_heuristic` rules implemented.)*
- [x] T012 Add exclusion reason taxonomy (`treated`, `missing_treatment`, `missing_rna`, `missing_survival`, `other`). *(Primary reasons implemented in manifest/status outputs.)*
- [x] T013 Add contract tests for naive manifest and clinical flat table. *(`tests/unit/test_tcga_naive_contracts.py::test_tcga_naive_manifest_contract_columns_and_vocab`)*

## Phase 3: Projection and Survival Hardening

- [x] T014 Extend projection stage to consume naive manifest and enforce `include_primary_projection == 1`. *(`tcga project` now accepts `--naive-manifest` and filters accordingly.)*
- [x] T015 Emit `score_input.tsv` with tier labels (`ALL`, `GOLD_SILVER`, `GOLD`). *(Tier-aware score inputs now emitted by `tcga project`.)*
- [x] T016 Extend survival stats to include endpoint/tier fields consistently. *(Projection rewrites stats with normalized contract fields.)*
- [x] T017 Add status artifacts for blocked/skipped project runs. *(`tcga_projection_status.tsv` emitted.)*

## Phase 4: Epidemiological Interaction Modeling

- [x] T018 Implement epidemiology model stage for `signature_score * covariate` interaction terms. *(`tcga epi-model` implemented with interaction-model scaffold and status-safe execution.)*
- [x] T019 Add covariate-family routing (demographic, stage, exposure, molecular subtype). *(Implemented in covariate-family routing table.)*
- [x] T020 Emit `tcga_epidemiology_interactions.tsv` with FDR-corrected interaction p-values. *(Implemented with BH-FDR over successful model rows.)*
- [x] T021 Add model diagnostics and missingness summaries per project. *(Companion diagnostics/status artifacts emitted.)*

## Phase 5: Pan-Cancer Synthesis

- [x] T022 Implement pan-cancer survival summary table (`tcga_pan_cancer_survival_summary.tsv`). *(`tcga pan-cancer` implemented.)*
- [x] T023 Implement heterogeneity summary (`tcga_pan_cancer_heterogeneity.tsv`). *(Random-effects heterogeneity scaffold implemented with explicit blocked statuses.)*
- [x] T024 Add pan-cancer forest plot generation. *(Forest plot generation implemented when valid HR rows exist.)*

## Phase 6: Concordance Tier Evaluation

- [x] T025 Build tier-specific signatures from `validation_concordance.tsv` (`GOLD`, `GOLD+SILVER`, `ALL`). *(`tcga tier-validate` emits tier signature files.)*
- [x] T026 Run tier projection loops and emit `tier_performance_summary.tsv`. *(Tier summary scaffold implemented with data-gated status rows.)*
- [x] T027 Add statistical comparison of tier performance across projects. *(Mann-Whitney comparison scaffold implemented with blocked-safe output.)*

## Phase 7: Reporting and QA

- [x] T028 Add TCGA naive projection section to report builder. *(`cmd_report_build` now summarizes TCGA naive status/table artifacts.)*
- [x] T029 Add integration smoke test for a two-project run (e.g., `TCGA-SKCM`, `TCGA-LUAD`). *(`tests/integration/test_tcga_two_project_smoke.py`)*
- [x] T030 Add end-to-end resume command for interrupted TCGA naive runs. *(`scripts/run_tcga_naive_resume.sh`)*
- [x] T031 Update `CHANGELOG.md` with spec-003 implementation milestones.

## Completion Definition

Spec-003 is considered implementation-complete when:

- naive-only manifests are produced and used in primary projection,
- epidemiology interaction outputs are generated for at least one covariate family per powered project,
- pan-cancer summary/heterogeneity artifacts exist,
- tier comparison outputs are produced,
- and reporting clearly separates completed vs skipped/blocked stages.
