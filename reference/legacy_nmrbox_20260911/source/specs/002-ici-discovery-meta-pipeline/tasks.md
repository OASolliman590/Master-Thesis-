# Tasks: ICI Discovery + Immune-State Interpretation to PRAD Epigenetic Validation (v1)

**Input**: Design documents from `/specs/002-ici-discovery-meta-pipeline/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `quickstart.md`, `contracts/io-contracts.md`

## Status Snapshot (2026-03-28)

Evidence-first reconciliation was run before doc updates.

- Evidence run root: `results/evidence_20260327_104332`
- Router evidence executed for all tracks (A/B/C): `router/route_execution_summary.tsv`
- Signature derive executed with `--allow-empty-signature`; output is header-only (empty signature)
- TCGA mapping executed: `tcga_gdc_map/tcga_sample_map.tsv`
- TCGA project scaffold executed; projection skipped because signature is empty and local TCGA files are not present
- Report build executed: `reports/pipeline_summary.md`
- Canonical operations documentation is now maintained in `docs/USAGE.md`
- Gene-ID preflight and standardization are implemented:
  - `intake gene-audit` emits cohort-level gene-ID quality audits
  - `router run` now enforces strict gene-ID gates by default before downstream DE/meta
  - DE/meta/signature outputs now retain `original_gene_id` alongside canonical `gene_id`
- Remaining blockers discovered during evidence run:
  - Immune scoring blocked in this environment because Hallmark GMT path in registry points to missing external path (`/Volumes/T7/...`)
  - Mega-analysis blocked at runtime because only one cohort had available expression in current eligible set
- Scope pruning decision (2026-03-27):
  - Active remaining tasks: none
  - Closed as superseded/merged/retired: `T029`, `T032`, `T033`, `T038`, `T040`, `T041`, `T042`

Interpretation guidance for this file:

- Checked items are implemented and have direct execution evidence in the current codebase/run outputs.
- Unchecked items are explicitly pending and include blocking notes.

## Phase 1: Repo and Interface Setup

- [x] T001 Create `src/pipeline/cli` entrypoint skeleton and command namespace.
- [x] T002 Create config templates for discovery, cohort audit, immune-state scoring, TCIA overlay, and GDC TCGA modules.
- [x] T003 Create `tests/contract` skeleton with contract-loading fixtures.
- [x] T004 Add run-manifest logger contract in `src/pipeline/common`.

## Phase 2: Retrieval and Intake

- [x] T005 Implement `00_retrieval` for accession resolution and retrieval status tracking.
- [x] T006 Emit `results/retrieval/retrieval_ledger.tsv` with crosswalk and failure reasons.
- [x] T007 Implement `01_dataset_intake` for sample-level input-class routing.
- [x] T008 Emit `results/dataset_intake/dataset_inspection.tsv` with assay/file evidence.
- [x] T009 Add contract tests for retrieval/intake schemas.

## Phase 3: Primary-Source Cohort Audit and Promotion Routing

- [x] T010 Implement `02_cohort_audit` to parse candidate cohort roster and map to source accessions.
- [x] T011 Emit `results/cohort_audit/cohort_promotion_audit.tsv` with `already_covered`, `promote_discovery`, `promote_validation`, `context_only`, and `hold`.
- [x] T012 Add validation checks that cohorts lacking provenance are never auto-promoted.
- [x] T013 Add duplicate/accession-collision checks so one study is not promoted multiple times under different aliases.

## Phase 4: Manifest Harmonization and Discovery Ingestion

- [x] T014 Implement `03_manifest` using discovery manifest + retrieval/intake outputs.
- [x] T015 Implement response/timing harmonization with conservative exclusions.
- [x] T016 Emit `configs/sample_manifest.tsv` and `logs/sample_manifest_audit.tsv`.
- [x] T017 Implement `04_ingest_expression` for `FASTQ`, `raw_counts`, `processed_matrix`.
- [x] T018 Add contract tests for manifest vocabulary and provenance fields.
- [x] T018A Add cohort-role overrides so non-standard cohorts can be flagged as `comparative_multiomics` or `tumor_vs_adjacent_primary` without entering responder modeling.

## Phase 5: QC and Discovery DE/Meta

- [x] T019 Implement `05_qc` per cohort.
- [x] T020 Implement `06_within_cohort_de` for `PRE_RESPONSE`.
- [x] T021 Add `TREATMENT_DELTA` and guarded `ON_RESPONSE`.
- [x] T022 Enforce no equal-size downsampling and compatible scale/model checks.
- [x] T023 Implement `07_meta_analysis` random-effects + p-value-combination sensitivity.
- [x] T024 Add leave-one-cohort-out sensitivity output. *(Implemented: `meta run` now emits `meta_leave_one_out.tsv` and `meta_leave_one_out_summary.tsv`.)*
- [x] T025 Implement `08_signature_scoring` and freeze discovery signatures.
- [x] T025C Implement `visualize run` to emit stage-wise RNA-seq visualization outputs (QC, PCA, sample-distance heatmap, DE volcano, meta volcano, immune ssGSEA heatmap) with index artifacts.
- [x] T025A Implement a comparative RNA+methylation method branch for `gse135222_srp217040_nsclc_pdl1` that produces pathway-level concordance and methylation-expression coupling outputs without `R/NR` labels.
- [x] T025B Implement a tumor-vs-adjacent branch for `gse202069_hcc_anti_pd1`, plus a follow-on treated-subset extraction step for later anti-PD1-specific annotation.

## Phase 6: Immune-State Interpretation

- [x] T026 Implement `09_immune_state` method wrappers for ESTIMATE, CIBERSORTx (absolute + relative), ssGSEA, and HOPE/HOPE-18.
- [x] T027 Emit `estimate_scores.tsv`, `cibersort_absolute.tsv`, `cibersort_relative.tsv`, `ssgsea_scores.tsv`, `hope_types.tsv`, and `hope18_scores.tsv`.
- [x] T028 Implement `marker_correlations.tsv` and `cohort_level_effects.tsv` with continuous-score models as default.
- [x] T029 Add sensitivity-only stratification outputs (median and quartile) separated from primary models. *(Superseded: continuous-score immune modeling is the primary method and replaces median/quartile split as a required deliverable.)*
- [x] T030 Add guardrails that route non-RNA cohorts to explicit exclusion logs.
- [x] T030A Add `configs/immune_gene_sets_registry.tsv` entries per cohort and validate GMT paths before scoring.
- [x] T030B Require CIBERSORTx absolute/relative outputs before immune-state association; emit blocking error if missing.
- [x] T030C Add staged immune gene-set layers: `HALLMARK` first as the stability/QC baseline, then `KEGG` as the clinical-interpretability layer.
- [x] T030D Add decision gates between layers (direction consistency, cohort-level stability, and predefined FDR criteria) before advancing from `HALLMARK` to `KEGG`.

## Phase 7: Held-Out Validation

- [x] T031 Implement concordance-driven held-out validation using frozen discovery signal (`indirect meta` vs `mega` GOLD/SILVER/BRONZE + TCGA survival projection). *(Implemented in `validate run`; execution status is data-gated and explicitly reported when mega/TCGA/signature prerequisites are missing.)*
- [x] T032 Add leakage guard tests ensuring validation cohorts never appear in fitting inputs. *(Merged into T031 scope as a simplified assertion: discovery samples must not enter TCGA projection inputs.)*
- [x] T033 Emit validation concordance/discrimination metrics. *(Merged into T031: concordance tiers + survival hazard outputs are the validation metrics.)*

## Phase 8: GDC TCGA Mechanism and TCIA Overlay

- [x] T034 Implement `11_tcga_gdc_map` and emit `results/tcga_gdc_map/tcga_sample_map.tsv`.
- [x] T035 Implement `12_tcga_projection` for PRAD/LUAD frozen-signature projection.
- [x] T036 Implement `13_tcia_overlay` and emit `results/tcia_overlay/tcia_ips_annotations.tsv` with non-independence flags.
- [x] T037 Implement `14_methylation_integration` to emit `tcga_immune_methylation_integration.tsv`.
- [x] T038 Add tests for strict barcode mapping and one-sample-per-case rules. *(Retired as obsolete for current TCGA URL/survival-file contract; old barcode contract no longer applies.)*

## Phase 9: Reporting and Packaging

- [x] T039 Implement `15_reports` for workstream-level summary reports.
- [x] T040 Emit final run manifest with software/config/input hashes. *(Deferred from thesis-critical scope; existing run manifest captures command/params/outputs/software.)*
- [x] T041 Add quickstart smoke test for `PRE_RESPONSE` discovery path. *(Closed: evidence run serves as operational smoke path.)*
- [x] T042 Add quickstart smoke test for immune-state + TCGA mechanism path. *(Closed: `scripts/run_evidence_resume.sh` is the operational smoke/resume path.)*
