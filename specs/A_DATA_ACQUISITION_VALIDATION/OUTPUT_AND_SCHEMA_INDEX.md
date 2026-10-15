# Shared output and schema authority index

## Existing normalized records (preserved)

schemas/study_registry.schema.json; publication_family.schema.json; source_record.schema.json; patient_registry.schema.json; treatment_exposure.schema.json; specimen_registry.schema.json; assay_registry.schema.json; clinical_outcome.schema.json; overlap_edge.schema.json. Existing receipt schemas are cohort_admission_receipt, matrix_build_receipt and validation_receipt. Their raw field names remain authoritative. Patient-level data_classification and private storage rules are not relaxed.

## Integration additions

schemas/treatment_episode.schema.json and episode_binding.schema.json connect existing component/specimen/outcome records without duplicating patients. prior_exposure_record.schema.json represents study/object/field use and its information boundary. materialized_matrix.schema.json defines seven $defs: baseline, timepoint, pair, endpoint, coverage, split and membership. A/PATIENT_MATRIX_SCHEMA.json and SOURCE_RECORD_SCHEMA.json are reference aliases, not alternate schema owners. release_contract.schema.json records branch-scoped dependencies and freezes with an explicit blocked state.

## Required outputs

search_log.tsv; study_registry.tsv; publication_family_registry.tsv; source_objects.jsonl (records follow source_record.schema.json); study_alias_crosswalk.tsv; private patient/treatment/specimen/assay/outcome registries; episode_registry.jsonl; episode_bindings.jsonl; overlap_edges.tsv; prior_exposure_ledger.tsv; branch_admission_registry.tsv; patient_matrix_build_receipt.json; split_registry.tsv; feature_coverage.tsv; source_gap_register.tsv; baseline_patient_matrix.tsv; patient_timepoint_long.tsv; longitudinal_pair_matrix.tsv; endpoint_matrix.tsv; analysis_membership.tsv. Each table's row grain and privacy are defined in PATIENT_DATA_MODEL and matrices/ contracts. Shared templates are header-only until real curation occurs; no placeholder patients are invented.

## Serialization rules

UTF-8 TSV; exact column strings; explicit schema version in the build receipt; null serialized as an unambiguous declared token, never empty-string-versus-zero guessing. JSON examples are explicitly SYNTHETIC_ONLY and never mixed with real registry records. IDs remain strings. Dates use documented event anchors/precision; no manufactured exact day. Object SHA-256 is lowercase 64 hex and must be checked against bytes. Sort materialized outputs by declared stable keys before hashing.

Source-level candidate/coverage tables may be public. Patient records, aliases, episode bindings, split membership and full predictions remain private by default. Public counts require source terms and aggregate disclosure review. A source metadata record is not an admission receipt, and a valid schema is not clinical evidence.
