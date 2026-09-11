# Feature Specification: TCGA Treatment-Naive Pan-Cancer Projection (v1)

**Feature Branch**: `003-tcga-naive-pan-cancer-projection`  
**Created**: 2026-03-27  
**Status**: Draft  
**Input**: User direction to project ICI-discovery signatures from 21 GEO cohorts onto treatment-naive TCGA cohorts, then derive epidemiological and survival insights across matched cancer types.

## Context Lock

### GEO Discovery Cohort Structure (Fixed Input)

- Total GEO cohorts: 21
- Cancer groups represented:
  - Melanoma (8)
  - NSCLC (5)
  - HNSCC (4)
  - HCC (1)
  - RCC (1)
  - Stomach adenocarcinoma (1)
  - Glioblastoma (1)

### TCGA Projection Project Scope (v1)

- `TCGA-SKCM`
- `TCGA-LUAD`
- `TCGA-LUSC`
- `TCGA-HNSC`
- `TCGA-LIHC`
- `TCGA-KIRC`
- `TCGA-KIRP`
- `TCGA-STAD`
- `TCGA-GBM`
- `TCGA-PRAD` (comparative reference)

### Current Implementation Baseline

Already available in current codebase:

- `tcga map` (URL/local-path manifest)
- `tcga project` (signature scoring + per-project survival input/stats)
- `tcga_survival.R` (Cox PH + Kaplan-Meier)

This spec extends that baseline with treatment-naive filtering, epidemiological interaction modeling, and pan-cancer synthesis.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build GEO-to-TCGA cancer coverage map (Priority: P1)

As the analysis owner, I need an auditable map from the 21 GEO cohorts to matched TCGA projects so projection is biologically aligned by cancer context.

**Independent Test**: Generate `geo_tcga_cancer_mapping.tsv` with GEO cohort IDs, source cancer type, matched TCGA projects, and rationale.

### User Story 2 - Retrieve and filter TCGA to treatment-naive patients (Priority: P1)

As the analysis owner, I need TCGA expression and clinical records filtered to treatment-naive patients so projected signal reflects baseline tumor biology.

**Independent Test**: For each selected TCGA project, emit a patient manifest with `naive_flag`, treatment metadata, and sample-level RNA eligibility.

### User Story 3 - Project frozen GEO signatures into TCGA and run survival analysis (Priority: P1)

As the analysis owner, I need per-project signature scoring and survival modeling so I can quantify prognostic signal in independent treatment-naive cohorts.

**Independent Test**: Emit project-level score tables, Cox/KM outputs, and a pan-cancer hazard-ratio summary table.

### User Story 4 - Quantify epidemiological interaction effects (Priority: P1)

As the analysis owner, I need multivariable and interaction models (age, sex, race, stage, exposures, subtype where available) so I can report when signature prognostic value is context-dependent.

**Independent Test**: Emit `tcga_epidemiology_interactions.tsv` with model terms, interaction coefficients, and corrected p-values.

### User Story 5 - Validate concordance tier utility in TCGA (Priority: P2)

As the analysis owner, I need GOLD/SILVER/BRONZE tier-specific projection performance so I can test whether replicated genes outperform weakly supported genes in external data.

**Independent Test**: Emit per-tier score/survival comparison outputs and statistical comparison summary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST map all 21 GEO cohorts into canonical cancer-type groups before selecting TCGA projects.
- **FR-002**: The system MUST support the following TCGA project set in v1 scope: `SKCM`, `LUAD`, `LUSC`, `HNSC`, `LIHC`, `KIRC`, `KIRP`, `STAD`, `GBM`, `PRAD`.
- **FR-003**: The system MUST ingest TCGA RNA + clinical data and derive a patient-level `naive_flag` from treatment history fields.
- **FR-004**: The system MUST exclude non-naive patients from primary projection analyses and log exclusions with reasons.
- **FR-005**: The system MUST harmonize gene identifiers between GEO-derived signatures and TCGA expression matrices.
- **FR-006**: The system MUST score each patient as `mean(up_genes) - mean(down_genes)` for each active signature definition.
- **FR-007**: The system MUST support score stratification as median split by default, with optional tertiles for sensitivity.
- **FR-008**: The system MUST run project-level Cox PH and Kaplan-Meier analyses for OS; PFS/DSS where fields are available.
- **FR-009**: The system MUST emit one pan-cancer forest summary table of hazard ratios and heterogeneity statistics.
- **FR-010**: The system MUST run epidemiological interaction models for predefined covariate families (demographics, exposures, stage, molecular subtype).
- **FR-011**: The system MUST emit model diagnostics and explicit missingness notes for each interaction model.
- **FR-012**: The system MUST evaluate tiered signatures (`GOLD`, `GOLD+SILVER`, `ALL`) and compare prognostic performance.
- **FR-013**: The system MUST preserve leakage controls (no discovery sample contamination in TCGA projection inputs).
- **FR-014**: The system MUST emit run-manifest provenance for each stage (inputs, params, software versions, outputs).
- **FR-015**: The system MUST separate execution status from scientific signal status (for example, data-gated blocked stages should produce explicit status artifacts, not hard-fail).

### Key Entities *(include if feature involves data)*

- **GEO-TCGA Mapping Record**: GEO cohort, cancer group, matched TCGA project, mapping confidence.
- **TCGA Naive Patient Manifest**: case/sample IDs, RNA availability, treatment history flags, naive status.
- **TCGA Clinical Flat Table**: harmonized demographics, stage, outcomes, exposures, subtype markers.
- **TCGA Signature Score Record**: per-patient signature score + stratum assignment.
- **TCGA Survival Model Record**: per-project Cox/KM summary statistics and diagnostics.
- **Epidemiological Interaction Record**: interaction term effect size, uncertainty, p/FDR, model context.
- **Tier Validation Record**: comparative performance by GOLD/SILVER/BRONZE-derived score sets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A complete GEO-to-TCGA mapping artifact is generated for all 21 GEO cohorts.
- **SC-002**: Naive-only TCGA patient manifests are generated for all in-scope projects with exclusion accounting.
- **SC-003**: Signature projection + survival outputs are generated for all projects with sufficient data.
- **SC-004**: Pan-cancer HR forest summary is produced with project-level effect sizes and heterogeneity.
- **SC-005**: At least one epidemiological interaction model family is executed per project where covariates are available.
- **SC-006**: Tier-based validation artifacts are generated and rank relative performance of tier definitions.
- **SC-007**: All blocked/missing-data scenarios produce explicit status rows and do not break end-to-end reporting.
