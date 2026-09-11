# Implementation Plan: Patient-Granular Meta-Analysis and Epigenetic Immune-State Layer

## Baseline Lock

- Last completed full evidence run: `results/full_pipeline_20260507_134734`.
- Last full run analyzed 21 PRE_RESPONSE cohort IDs with 0 executed blockers.
- Current preflight state has 1 additional ready-pending cohort: `gse289583_mcrc_regorafenib_ipilimumab_nivolumab`.
- Current target for the next full rerun is 22 PRE_RESPONSE analyzed cohort IDs.
- Patient manifest prototype exists at `src/pipeline/spec_patient_manifest/build_patient_manifest.py`.
- Patient manifest v1 exists at `results/patient_manifest/patient_manifest_v1.tsv`: 1,037 rows, 1,027 real patients, 10 stubs, 312 responder, 500 non_responder, 225 unknown, 67 longitudinal.
- Strict gene audit after last9 recovery passes 22 cohorts: `results/spec_006/gene_audit_after_last9_recovery`.

## Implementation Strategy

Spec 007 should be implemented in slices. The first slice should make patient identity and comparison provenance explicit while preserving all Spec 006 outputs. The second slice should harden meta-analysis. The third slice should add real gene-set scoring. The TCGA projection should be isolated behind its own command and treated as a late slice because it depends on external validation inputs.

## Phase 0: Kit and Baseline Normalization

- Complete the spec kit files.
- Correct baseline counts and distinguish last full-run evidence from preflight readiness.
- Lock I/O contracts before implementation.
- Preserve current Spec 006 reports as evidence references.

## Phase 1: Patient Manifest Promotion

Goal: promote the existing patient manifest prototype into the CLI and make patient-level artifacts reproducible.

Primary work:
- Move or wrap `src/pipeline/spec_patient_manifest/build_patient_manifest.py` into production module space.
- Add `intake build-patient-manifest` CLI command.
- Emit `patient_manifest.tsv`, `sample_annotations_corrected.tsv`, and `patient_clinical_record.tsv`.
- Keep `patient_manifest_v1.tsv` as validation reference, not runtime authority.

Expected outputs:
- `results/patient_manifest/patient_manifest.tsv`
- `results/patient_manifest/sample_annotations_corrected.tsv`
- `results/patient_manifest/patient_clinical_record.tsv`
- `results/patient_manifest/patient_manifest_validation.tsv`

## Phase 2: Manifest Authority

Goal: make Stage 03 consume patient-level authority without breaking sample-level fallback.

Primary work:
- Add optional patient manifest argument or default lookup.
- Resolve response/timing from patient manifest when available.
- Write divergence log where patient manifest disagrees with sample-level table.
- Preserve fallback behavior for one-sample or unresolved cohorts.

Expected outputs:
- `results/manifest_build/divergences.tsv`
- Updated curated sample manifest, if Stage 03 rebuild is invoked.

## Phase 3: Comparison Registry

Goal: make every Stage 06 contrast a first-class artifact.

Primary work:
- Create comparison ID generator.
- Add registry row writing before or during each DE run.
- Include `comparison_id` in DE output rows or metadata columns.
- Guard duplicate `(cohort_id, analysis_type, contrast_definition)` rows.

Expected outputs:
- `results/spec_007/comparison_registry.tsv`
- DE rows with `comparison_id`

## Phase 4: Meta-Analysis Hardening

Goal: make Stage 07 more defensible for thesis claims.

Primary work:
- Compute per-gene I2.
- Add cancer-type subgroup meta-analysis.
- Add drug-class subgroup meta-analysis.
- Integrate leave-one-cohort-out summary into primary meta summary for top genes.

Expected outputs:
- `results/meta_analysis/meta_summary.tsv`
- `results/meta_analysis/subgroups/by_cancer_type/*.tsv`
- `results/meta_analysis/subgroups/by_drug_class/*.tsv`
- LOCO columns in primary summary.

## Phase 5: Five-Layer Immune-State Scoring

Goal: replace the proxy-only immune score with real ssGSEA while retaining backward compatibility.

Primary work:
- Register Layer 1, Layer 2, Layer 3, Layer 4, and Layer 5 gene sets.
- Add small custom Layer 4 GMT files under `inputs/gene_sets/epigenetic_layer/`.
- Implement real ssGSEA command path using available local dependencies.
- Retain `IMMUNE_SCORE` proxy with deprecated method label.

Expected outputs:
- `inputs/gene_sets/epigenetic_layer/*.gmt`
- Updated `configs/immune_gene_sets_registry.tsv`
- `results/immune_state/ssgsea_scores.tsv`
- `results/immune_state/layer_summary.tsv`

## Phase 6: TCGA Projection Hook

Goal: add a reproducible command for Layer 4 projection onto TCGA immune subtype labels.

Primary work:
- Define required TCGA expression and Thorsson subtype inputs.
- Add `tcga projection` command or extend existing TCGA command.
- Score Layer 4 gene sets.
- Run Kruskal-Wallis tests and FDR correction by project.

Expected outputs:
- `results/tcga_projection/epigenetic_layer_tcga_validation.tsv`

## Phase 7: Full Verification Run

Goal: prove Spec 007 does not regress Spec 006 and produces the new artifacts.

Verification:
- `python -m pytest tests/ -q`
- `intake build-patient-manifest`
- `intake gene-audit --strict`
- Full pipeline rerun with Spec 007 flag or equivalent configured path
- Confirm target: 22 PRE_RESPONSE analyzed cohort IDs unless new cohort recovery happens in a separate cycle.

## Dependency Notes

- T7 must be mounted for full run and MSigDB layer access.
- `gse289583_hgnc_symbol_counts.tsv.gz` is currently repo-local under `results/spec_006/recovered_expression/`; move to T7 before full rerun when write escalation is available.
- `gseapy` or an equivalent ssGSEA backend must be available before Phase 5. If not present, Phase 5 begins with dependency decision and installation notes.

