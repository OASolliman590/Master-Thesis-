# Tasks: Patient-Granular Meta-Analysis and Epigenetic Immune-State Layer

**Input**: `spec.md`, `plan.md`, `research.md`, `quickstart.md`, `contracts/io-contracts.md`

## Phase 0: Spec Kit Initialization

- [x] T001 Create complete Spec 007 kit files.
- [x] T002 Patch baseline/count inconsistencies in `spec.md`.
- [x] T003 Validate current baseline paths exist: latest full run, patient manifest v1, strict gene audit, and Spec 006 status reports.

## Phase 1: Patient Manifest Promotion

- [x] T004 Review `src/pipeline/spec_patient_manifest/build_patient_manifest.py` and identify production module boundary.
- [x] T005 Add `src/pipeline/modules/01_dataset_intake/patient_manifest.py` or equivalent production wrapper.
- [x] T006 Add CLI command `intake build-patient-manifest`.
- [x] T007 Emit `results/patient_manifest/patient_manifest.tsv`.
- [x] T008 Emit `results/patient_manifest/sample_annotations_corrected.tsv`.
- [x] T009 Emit `results/patient_manifest/patient_clinical_record.tsv`.
- [x] T010 Emit validation report comparing new patient manifest to `patient_manifest_v1.tsv`.
- [x] T011 Add unit tests for patient UID generation, timing aggregation, longitudinal flags, and gse67501 override.

## Phase 2: Manifest Authority

- [x] T012 Locate `cmd_manifest_build` authority path and current fallback behavior.
- [x] T013 Add optional/default patient manifest input to manifest build.
- [x] T014 Make patient manifest response/timing values win when resolvable.
- [x] T015 Write `results/manifest_build/divergences.tsv` for disagreements.
- [x] T016 Add tests for patient-manifest override and fallback behavior.

## Phase 3: Comparison Registry

- [x] T017 Add comparison ID helper.
- [x] T018 Add registry writer for Stage 06 DE runs.
- [x] T019 Add duplicate guard for `(cohort_id, analysis_type, contrast_definition)`.
- [x] T020 Add `comparison_id` to DE output rows or metadata.
- [x] T021 Add unit tests for registry uniqueness and ID stability.

## Phase 4: Meta-Analysis Hardening

- [x] T022 Inspect existing `cmd_meta_run`, `meta_leave_one_out.tsv`, and `meta_leave_one_out_summary.tsv` behavior.
- [x] T023 Add per-gene I2 to primary meta output.
- [x] T024 Add cancer-type subgroup meta outputs.
- [x] T025 Add drug-class subgroup meta outputs.
- [x] T026 Join LOCO stability fields into `meta_summary.tsv` for top genes.
- [x] T027 Add tests for I2 calculation and subgroup output shape.

## Phase 5: Five-Layer Immune-State Scoring

- [x] T028 Confirm ssGSEA backend availability (`gseapy` or equivalent).
- [x] T029 Create Layer 4 GMT files under `inputs/gene_sets/epigenetic_layer/`.
- [x] T030 Update `configs/immune_gene_sets_registry.tsv` with Layers 1-5.
- [x] T031 Implement real ssGSEA scoring path while retaining deprecated `IMMUNE_SCORE` proxy.
- [x] T032 Emit `results/immune_state/ssgsea_scores.tsv`.
- [x] T033 Emit `results/immune_state/layer_summary.tsv`.
- [x] T034 Add tests with a small expression/gene-set fixture.

## Phase 6: TCGA Projection Hook

- [x] T035 Define required TCGA expression and Thorsson subtype input contracts.
- [x] T036 Add TCGA projection command or extend existing Stage 12 command.
- [x] T037 Score Layer 4 gene sets on TCGA projects.
- [x] T038 Run Kruskal-Wallis tests and FDR correction.
- [x] T039 Emit `results/tcga_projection/epigenetic_layer_tcga_validation.tsv`.
- [x] T040 Add a fixture-level test for projection statistics.

## Phase 7: Deprecation and Documentation

- [x] T041 Mark `src/pipeline/modules/13_tcia_overlay/__init__.py` as deprecated.
- [x] T042 Confirm Stage 14 remains deferred with no functional changes.
- [x] T043 Update pipeline documentation/report notes for patient-level and immune-state artifacts.

## Phase 8: Verification

- [x] T044 Run `python -m pytest tests/ -q`.
- [x] T045 Run `intake build-patient-manifest`.
- [x] T046 Run strict gene audit.
- [x] T047 Move `gse289583_hgnc_symbol_counts.tsv.gz` to T7 if write approval is available and update expression manifests.
- [x] T048 Run full pipeline with Spec 007 path enabled.
- [x] T049 Verify full-run target: 22 PRE_RESPONSE analyzed cohort IDs unless a separate recovery cycle adds more.
- [x] T050 Write `results/spec_007/spec_007_execution_report.md`.
