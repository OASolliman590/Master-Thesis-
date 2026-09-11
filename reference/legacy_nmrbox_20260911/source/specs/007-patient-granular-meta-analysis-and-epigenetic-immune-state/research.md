# Research: Patient-Granular Meta-Analysis and Epigenetic Immune-State Layer

## Evidence Sources

- Last full pipeline run: `results/full_pipeline_20260507_134734`.
- Current cohort status: `results/spec_006/cohort_status_grouped.md`.
- Last9 recovery report: `results/spec_006/last9_fix_report.md`.
- Strict gene audit after recovery: `results/spec_006/gene_audit_after_last9_recovery`.
- Patient manifest prototype: `src/pipeline/spec_patient_manifest/build_patient_manifest.py`.
- Patient manifest v1 reference: `results/patient_manifest/patient_manifest_v1.tsv`.

## Baseline Findings

The current full-run evidence supports 21 analyzed PRE_RESPONSE cohort IDs. A subsequent recovery cycle made `gse289583_mcrc_regorafenib_ipilimumab_nivolumab` ready pending full rerun, giving a current preflight target of 22 analyzed cohort IDs. Eight cohorts remain not PRE_RESPONSE-ready due to design, assay type, or missing outcome labels.

The patient manifest prototype already demonstrates patient-level grouping and cohort-specific metadata correction. It is not yet exposed through the CLI, and its outputs are not authoritative for downstream stages.

## Patient Manifest Rationale

Patient-level analysis is required because sample count and patient count diverge in longitudinal cohorts. A per-sample manifest is sufficient for expression alignment but is not sufficient for reporting clinical support, longitudinal status, or patient-level response authority.

The patient manifest should:
- Collapse sample rows into stable `patient_uid` rows.
- Preserve sample-level timing through `pre_sample_ids`, `on_sample_ids`, and `post_sample_ids`.
- Expose `is_longitudinal` and `n_timepoints`.
- Make stubs explicit through `is_stub`.
- Produce a corrected sample annotation view for Stage 03 fallback.

## Comparison Registry Rationale

Current Stage 06 outputs are traceable by filename but do not expose a first-class comparison object. A registry makes the contrast explicit and allows Stage 07, reports, and thesis tables to reference a stable `comparison_id`.

The registry should be append-safe per run but uniqueness-checked for `(cohort_id, analysis_type, contrast_definition)`.

## Meta-Analysis Rationale

The pipeline already emits meta-analysis and leave-one-out artifacts in the last full run. Spec 007 should not duplicate that work loosely; it should formalize it:
- Add I2 to the primary meta summary.
- Join LOCO stability fields back into top-gene outputs.
- Add subgroup outputs by cancer type and drug class.

This makes the analysis more defensible against claims that one large cohort or one drug class dominates the signal.

## Immune-State Rationale

The current `IMMUNE_SCORE` proxy is useful as a lightweight continuity artifact but is not enough for the epigenetics thesis question. Real ssGSEA over selected ICB and epigenetic layers will let us test immune-state structure at sample level and summarize it by layer.

Layer design:
- Layer 1: compact ICB predictor sets.
- Layer 2: selected C7 exhaustion/dysfunction sets, not full C7.
- Layer 3: selected Hallmark immune/inflammation sets.
- Layer 4: custom tumor-intrinsic and T-cell-intrinsic epigenetic sets.
- Layer 5: HOPE_18 as standalone comparability layer.

## TCGA Projection Rationale

TCGA projection is a validation hook, not a replacement for ICB response evidence. It tests whether Layer 4 epigenetic scores align with immune subtype structure in larger tumor cohorts.

Minimum TCGA projects:
- SKCM
- BLCA
- HNSC
- LUAD
- KIRC

Minimum statistic:
- Kruskal-Wallis test of gene set score across Thorsson immune subtype labels.
- FDR correction across gene set by project tests.

## Key Risks

- Patient manifest may disagree with sample-level manifest. Mitigation: patient manifest wins only where resolvable and divergences are logged.
- ssGSEA dependencies may not be installed. Mitigation: detect backend availability and make Phase 5 dependency-gated.
- Custom epigenetic gene sets need literature signoff. Mitigation: keep Layer 4 GMT small, transparent, and version-controlled.
- Full-run target wording can drift. Mitigation: distinguish last full-run evidence from current preflight readiness in all docs.

