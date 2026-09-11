# Feature Specification: Patient-Granular Meta-Analysis and Epigenetic Immune-State Layer

**Feature Branch**: `007-patient-granular-meta-analysis-and-epigenetic-immune-state`
**Created**: 2026-05-08
**Status**: Draft
**Input**: Last full spec_006 evidence run (`results/full_pipeline_20260507_134734`) plus last9 preflight fixes — 21 PRE_RESPONSE cohorts analyzed in the last full run, 1 additional cohort (`gse289583_mcrc_regorafenib_ipilimumab_nivolumab`) ready pending full rerun, 33 tests passing, but (a) the manifest is sample-level only with no patient-level grouping; (b) Stage 06/07 form contrasts implicitly without an explicit comparison registry; (c) Stage 09 ssGSEA runs only an `IMMUNE_SCORE` proxy against HALLMARK + KEGG, missing C7_IMMUNESIGDB and an epigenetic-focused gene set layer; (d) per-patient clinical enrichment (drug, dose, stage, prior lines, biopsy site) is not captured.

## Context Lock

### Current Baseline (after spec_006 + last9 fix cycle)

- 30 cohorts ingested. 21 PRE_RESPONSE cohorts analyzed in the last full run, 1 additional cohort ready pending full rerun (`gse289583_mcrc_regorafenib_ipilimumab_nivolumab`), and 8 cohorts not PRE_RESPONSE-ready for scientific/design reasons (registry: `results/spec_006/blocked_datasets_registry.md`; current status: `results/spec_006/cohort_status_grouped.md`)
- Patient manifest v1 (`results/patient_manifest/patient_manifest_v1.tsv`) built manually outside the pipeline: 1,037 rows (1,027 real patients + 10 stubs), 312 R / 500 NR / 225 unknown, 67 longitudinal
- `cohort_input_table_all.tsv` is sample-level only and may be stale for recovered cohorts; current sample authority is `configs/sample_manifest_curated.tsv` plus `results/geo_tables/geo_tables_summary.tsv`. Neither provides patient-level aggregation or clinical enrichment beyond response/timing.
- Stage 06 (`cmd_de_run`) constructs the R-vs-NR contrast inline per cohort; the comparison itself is not a first-class artifact
- Stage 07 (`cmd_meta_run`) computes Fisher's combined p + random-effects but does not report I² heterogeneity, drug-class subgroups, or leave-one-cohort-out sensitivity
- Stage 09 (`cmd_immune_score`) only writes a single `IMMUNE_SCORE` proxy column — no real ssGSEA against MSigDB GMT files. `configs/immune_gene_sets_registry.tsv` registers HALLMARK + KEGG but the score function does not consume them
- T7 external drive holds the four MSigDB collections (HALLMARK, KEGG, REACTOME, C7_IMMUNESIGDB) at `/Volumes/T7/1-Epigenetics_MSc_Thesis/gene_sets/msigdb_layers_2026-03-24/`; only HALLMARK and KEGG are registered
- Stages 13 (TCIA overlay) and 14 (methylation integration) are stubs in the pipeline tree

### Why this cycle now

The pipeline is statistically correct at sample level but cannot answer patient-level scientific questions: "how many *patients* support each gene's effect?", "is the signal consistent across drug classes?", "do epigenetic regulators (PRC2, SWI/SNF, DNMT, retroelement sensing) drive the responder/non-responder split?". Spec_007 promotes patient_id to a first-class entity, makes comparisons explicit, hardens the meta-analysis statistics, and introduces a five-layer ICB-relevant gene set battery with a tumor-intrinsic + T-cell-intrinsic epigenetic layer.

## User Scenarios & Testing

### User Story 1 — Patient-level manifest is canonical (Priority: P1)

As the analysis owner, I need the patient manifest to be built by the pipeline (not hand-curated) and to be the source of truth for response and timing in downstream stages, so that no stage silently disagrees with another.

**Independent Test**: Running `cmd_intake_build_patient_manifest` produces `results/patient_manifest/patient_manifest.tsv` with one row per patient_uid, columns for response_label/response_source/timing presence flags, and Stage 03 (`cmd_manifest_build`) reads this file before falling back to `cohort_input_table_all.tsv`.

### User Story 2 — Patient clinical record (Priority: P1)

As the analysis owner, I need every patient row enriched with disease, ICB drug, dose, clinical stage, prior treatment lines, and biopsy site (where available) so that Stage 06/07 can stratify by drug class and Stage 10 can validate within clinically homogeneous strata.

**Independent Test**: `results/patient_manifest/patient_clinical_record.tsv` exists with ≥1 non-null clinical field for ≥80% of real (non-stub) patients.

### User Story 3 — Comparison registry as first-class artifact (Priority: P1)

As the analysis owner, I need each Stage 06 DE run to be backed by a row in a comparison registry (comparison_id, analysis_type, cohort_id, cancer_type, drug_class, n_A, n_B, contrast_definition) so that meta-analysis and reports cite comparisons by ID rather than re-deriving them.

**Independent Test**: `results/spec_007/comparison_registry.tsv` exists with one row per Stage 06 contrast, and Stage 07 outputs reference `comparison_id`.

### User Story 4 — Hardened meta-analysis (Priority: P2)

As the analysis owner, I need Stage 07 to report I² heterogeneity, cancer-type and drug-class subgroup results, and leave-one-cohort-out sensitivity per top gene, so that I can defend each meta-analysis claim against a single dominant cohort or off-class study.

**Independent Test**: `results/meta_analysis/meta_summary.tsv` includes `i2`, `subgroup_*`, and `loco_max_delta_padj` columns; the top-50 gene table is reproduced under each subgroup.

### User Story 5 — Five-layer immune gene set battery (Priority: P2)

As the analysis owner, I need Stage 09 to score each sample against five layers: (L1) ICB predictors, (L2) C7 exhaustion subset, (L3) selected Hallmark, (L4) custom epigenetic — both tumor-intrinsic and T-cell-intrinsic, (L5) HOPE_18, so that the immune-state output supports the epigenetics thesis question directly.

**Independent Test**: `results/immune_state/ssgsea_scores.tsv` contains one column per gene set across all five layers, populated by real ssGSEA (not the proxy), for every QC-pass sample.

### User Story 6 — TCGA validation hook (Priority: P2)

As the analysis owner, I need Stage 12 to project the Layer 4 epigenetic gene set scores onto TCGA (SKCM, BLCA, HNSC, LUAD, KIRC) and report set-vs-immune-subtype association (Thorsson 2018 immune subtype calls) so that the epigenetic claim can be triangulated outside the ICB cohorts.

**Independent Test**: `results/tcga_projection/epigenetic_layer_tcga_validation.tsv` exists with one row per (gene_set × tcga_project × immune_subtype) and a Kruskal–Wallis statistic.

## Requirements

### Functional Requirements — Patient Manifest (Stage 01)

- **FR-001**: The system MUST add `cmd_intake_build_patient_manifest` to the pipeline CLI. Logic must be the same as the prototype at `src/pipeline/spec_patient_manifest/build_patient_manifest.py`, promoted into `src/pipeline/modules/01_dataset_intake/`.
- **FR-002**: The output MUST be `results/patient_manifest/patient_manifest.tsv` with columns: `patient_uid`, `patient_id_raw`, `cohort_id`, `cancer_type`, `therapy_agent`, `response_label`, `response_source`, `has_pre`, `has_on`, `has_post`, `n_timepoints`, `is_longitudinal`, `is_stub`, `pre_sample_ids`, `on_sample_ids`, `post_sample_ids`, `unknown_sample_ids`.
- **FR-003**: The system MUST also produce `results/patient_manifest/sample_annotations_corrected.tsv` (sample-level corrected view) and `results/patient_manifest/patient_clinical_record.tsv` (clinical enrichment).
- **FR-004**: `patient_clinical_record.tsv` MUST contain at minimum: `patient_uid`, `cancer_type`, `clinical_stage`, `icb_drug`, `icb_drug_class` (PD1/PDL1/CTLA4/COMBO), `prior_treatment_lines`, `biopsy_site`, `dose_schedule`, `source_field`. Fields not parseable MUST be `unknown`, never blank.
- **FR-005**: Cohort-specific parsers (gse91061, gse96619, gse106128, gse207422, gse195832, gse115821, gse210287, gse159067, gse93157, gse67501) MUST be retained; gse67501 parser MUST override the global table annotation (response is mislabeled there).

### Functional Requirements — Manifest Authority (Stage 03)

- **FR-006**: `cmd_manifest_build` MUST consult `patient_manifest.tsv` as the authoritative source for response and timing before falling back to `cohort_input_table_all.tsv`.
- **FR-007**: When a sample's response label or timing differs between patient_manifest and the global table, the patient_manifest value MUST win and the divergence MUST be logged to `results/manifest_build/divergences.tsv`.

### Functional Requirements — Comparison Registry (Stage 06)

- **FR-008**: Before any DE call, `cmd_de_run` MUST write a row to `results/spec_007/comparison_registry.tsv` with: `comparison_id`, `analysis_type` (PRE_RESPONSE | TREATMENT_DELTA), `cohort_id`, `cancer_type`, `drug_class`, `contrast_definition` (e.g., `responder_vs_non_responder@pre`), `n_group_A`, `n_group_B`, `n_genes_tested`, `software` (DESeq2 | limma_voom), `created_at`.
- **FR-009**: Each Stage 06 output file MUST embed `comparison_id` in its filename or header so it can be joined back.
- **FR-010**: The comparison registry MUST forbid duplicate `(cohort_id, analysis_type, contrast_definition)` rows in a single run.

### Functional Requirements — Hardened Meta-Analysis (Stage 07)

- **FR-011**: `cmd_meta_run` MUST compute and emit per-gene `i2` (Higgins-Thompson heterogeneity statistic) alongside Fisher's combined p and random-effects estimates.
- **FR-012**: `cmd_meta_run` MUST produce subgroup analyses: by `cancer_type` and by `drug_class`. Each subgroup output MUST be a separate TSV under `results/meta_analysis/subgroups/`.
- **FR-013**: For the top 50 genes by primary meta-p, `cmd_meta_run` MUST run leave-one-cohort-out sensitivity and report `loco_max_delta_padj` (max change in -log10(padj) when any single cohort is dropped).
- **FR-014**: Genes whose top-50 ranking is destroyed (`loco_max_delta_padj` exceeds threshold τ=2.0 by default, configurable) MUST be flagged in `meta_summary.tsv` with a `loco_unstable=true` column.

### Functional Requirements — Five-Layer Gene Set Battery (Stage 09)

- **FR-015**: `configs/immune_gene_sets_registry.tsv` MUST register all five layers and point to T7 paths where applicable:
  - **Layer 1 — ICB predictors**: T_CELL_INFLAMED_GEP_18 (Ayers 2017), HOPE_18, IFNG_signature, CYT_score (Rooney 2015)
  - **Layer 2 — C7_IMMUNESIGDB exhaustion subset**: hand-picked exhaustion/dysfunction signatures from C7 (≤30 sets)
  - **Layer 3 — Hallmark selected (10)**: HALLMARK_INTERFERON_GAMMA_RESPONSE, HALLMARK_INTERFERON_ALPHA_RESPONSE, HALLMARK_TNFA_SIGNALING_VIA_NFKB, HALLMARK_INFLAMMATORY_RESPONSE, HALLMARK_IL6_JAK_STAT3_SIGNALING, HALLMARK_ALLOGRAFT_REJECTION, HALLMARK_COMPLEMENT, HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION, HALLMARK_TGF_BETA_SIGNALING, HALLMARK_HYPOXIA
  - **Layer 4 — Custom epigenetic (tumor-intrinsic + T-cell-intrinsic)**: see FR-016
  - **Layer 5 — HOPE_18 standalone** (kept separate for direct comparability with prior literature)
- **FR-016**: Layer 4 MUST consist of these custom GMT entries, written under `inputs/gene_sets/epigenetic_layer/`:
  - **Tumor-intrinsic**: `PRC2_IMMUNE_TARGETS` (EZH2, EED, SUZ12 + curated H3K27me3 immune target genes), `SWI_SNF_ICB` (ARID1A, SMARCA4, SMARCB1, ARID2, PBRM1), `DNMT_IMMUNE_LOCI` (DNMT1, DNMT3A, DNMT3B + methylation-silenced immune loci), `HISTONE_WRITERS_ICB` (KMT2A, KMT2C, KMT2D, SETD2, NSD1, NSD2), `EPIGENETIC_CHECKPOINT` (EZH2, HDAC1, HDAC2, DNMT1 + their checkpoint targets CD274, IDO1, HLA-A/B/C), `RETROELEMENT_SENSING` (SETDB1, TRIM28, MAVS, STING1, CGAS, ZBP1, ADAR)
  - **T-cell-intrinsic**: `T_CELL_EXHAUSTION_EPIGENETIC` (TOX, NR4A1, NR4A2, NR4A3, BATF, IRF4 + EZH2/DNMT3A in T cells), `T_CELL_MEMORY_EPIGENETIC` (TCF7, LEF1, BACH2, FOXO1 + memory-associated chromatin regulators)
- **FR-017**: `cmd_immune_score` MUST be replaced (or extended) to run real ssGSEA (e.g., via `gseapy.ssgsea` or rpy2 + `GSVA`) against every registered layer; the proxy `IMMUNE_SCORE` column MUST be retained for backward compatibility but flagged deprecated.
- **FR-018**: `results/immune_state/ssgsea_scores.tsv` MUST contain one column per registered gene set across all 5 layers, with rows for every QC-pass sample. A `results/immune_state/layer_summary.tsv` MUST aggregate per-layer mean scores per sample.

### Functional Requirements — TCGA Validation (Stage 12)

- **FR-019**: `cmd_tcga_projection` MUST project Layer 4 (epigenetic) gene set scores onto TCGA-SKCM, TCGA-BLCA, TCGA-HNSC, TCGA-LUAD, and TCGA-KIRC at minimum.
- **FR-020**: For each (gene_set × tcga_project) pair, the system MUST compute a Kruskal–Wallis statistic against Thorsson 2018 immune subtype calls (C1–C6) and write to `results/tcga_projection/epigenetic_layer_tcga_validation.tsv` with `gene_set, tcga_project, n_patients, kw_statistic, p_value, fdr`.

### Functional Requirements — Stages Out of Scope

- **FR-021**: Stage 13 (TCIA overlay) is dropped from spec_007. The directory `src/pipeline/modules/13_tcia_overlay/` MUST be marked `# DEPRECATED` in its `__init__.py` and excluded from CLI registration.
- **FR-022**: Stage 14 (methylation integration) is deferred. The directory remains in the tree but no functional changes are part of this spec. A follow-on spec (`spec_008_methylation_integration`) is the intended home.

### Non-Functional Requirements

- **NFR-001**: All new artifacts MUST be reproducible from `run_full_pipeline.sh` with the spec_007 flag set.
- **NFR-002**: Test coverage MUST add at least one unit test per new CLI command and one integration test that runs the patient manifest → comparison registry → meta-analysis chain on a 3-cohort fixture.
- **NFR-003**: All gene set GMT files for Layer 4 MUST be checked into `inputs/gene_sets/epigenetic_layer/` (small files, version-controlled). Layers 1–3 and 5 may live on T7.
- **NFR-004**: Backward compatibility: spec_006 outputs MUST remain readable; the new patient manifest MUST not break Stage 04+ when a cohort lacks patient-level resolution (fall back to one-row-per-sample treated as one patient).

## Key Entities

- **patient_uid**: stable identifier, format `<cohort_id>::<patient_id_raw>` after normalization. The unit of analysis for meta-analysis weighting (n_patients per cohort).
- **comparison_id**: stable identifier, format `<cohort_id>__<analysis_type>__<contrast>` (e.g., `gse91061_melanoma_pd1__PRE_RESPONSE__R_vs_NR`). First-class object referenced by Stage 06/07 outputs.
- **gene_set_layer**: enum `L1_ICB_PREDICTOR | L2_C7_EXHAUSTION | L3_HALLMARK | L4_EPIGENETIC | L5_HOPE_18`. Drives the layer_summary aggregation.

## Out of Scope

- New cohort intake (handled by F1 stub-fix follow-on, not this spec)
- gse135222 PFS-based response derivation (one-line config change, tracked separately under `results/spec_006/`)
- Methylation array integration beyond TCGA validation hooks (deferred to spec_008)
- TCIA imaging overlay (dropped)

## Success Criteria

1. Pipeline produces `patient_manifest.tsv` with ≥1,020 real patient rows (matching v1 hand-curated manifest within ±0.5%).
2. `comparison_registry.tsv` has one row per Stage 06 DE run, no duplicates, and every Stage 07 output references at least one comparison_id.
3. `meta_summary.tsv` includes I², subgroup, and LOCO columns for the top 50 genes; ≥40 of the top 50 retain padj < 0.05 under leave-one-cohort-out (target — not a hard requirement).
4. `ssgsea_scores.tsv` has columns for every Layer 1–5 set across every QC-pass sample, computed by real ssGSEA.
5. `epigenetic_layer_tcga_validation.tsv` shows ≥3 gene sets with FDR < 0.1 vs Thorsson immune subtype in at least one TCGA project.
6. Tests: 33 baseline + ≥6 new = 39 minimum, all passing.
7. Full pipeline rerun completes end-to-end with the 21 cohorts from `results/full_pipeline_20260507_134734` plus the ready-pending `gse289583_mcrc_regorafenib_ipilimumab_nivolumab` cohort (target: 22 PRE_RESPONSE analyzed cohort IDs unless additional cohorts are separately recovered).

## Risks and Mitigations

- **Risk**: ssGSEA over 5,219 C7 sets is computationally expensive. **Mitigation**: Layer 2 is a hand-picked exhaustion subset (≤30 sets), not the full C7.
- **Risk**: Custom epigenetic gene sets are not externally validated. **Mitigation**: TCGA validation (FR-019/020) provides external triangulation; gene lists are curated from PRC2/SWI-SNF/DNMT primary literature.
- **Risk**: Patient manifest divergences from existing global table may break Stage 04+. **Mitigation**: NFR-004 fallback; divergences logged for human review (FR-007).
- **Risk**: I² and LOCO multiply runtime. **Mitigation**: LOCO is restricted to top-50 genes only; I² is per-gene but cheap.

## Acceptance

This spec is accepted when:
- All FRs implemented and tested
- Success criteria 1–7 met on a full pipeline rerun
- Spec author (thesis researcher) signs off on the epigenetic layer gene lists after literature review
- Output reports are reviewable as-is for thesis chapters on (a) ICB response meta-analysis and (b) epigenetic regulation of immune state
