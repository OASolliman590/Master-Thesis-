# Shared A/A1 integration amendment — 15 October 2026

## Preserve the existing authority

The canonical DAV package was retrieved from the actual completed export of draft PR #9, head 58ac943acbe8c981c7c8c269103c602b4425bd50. Its twelve registry/receipt schemas, source-derived protocol crosswalk, implementation reconciliation, matrix definitions and bounded DAV tickets remain authoritative. The older staged e477c680 snapshot is not the current state. New A/A1 files are consumers, not duplicate registries. Existing schema IDs/fields and raw records are preserved; this amendment adds explicit relational contracts and executable consumer schemas.

## Episode binding gap and extension

The inherited clinical_outcome and treatment_exposure schemas have patient/regimen fields but no explicit treatment_episode_id. Do not replace them with incompatible duplicates. Add treatment_episode.schema.json and episode_binding.schema.json in this same schema directory. An episode is one patient × actual treatment interval/sequence context. A binding associates an existing exposure component, specimen or outcome with an episode and role, with source evidence. Branch admission now requires a source-supported binding for each selected outcome and each baseline/follow-up specimen/exposure. Binding uniqueness/foreign keys are relational validators, not proved by JSON syntax. No response from one episode may label another by default.

## Consumer contract additions

materialized_matrix.schema.json defines machine-checkable baseline, timepoint-long, pair, endpoint, feature-coverage, split and analysis-membership records. A's schema files are reference aliases only. release_contract.schema.json describes branch-specific source/statistical/software gates without asserting they passed. prior_exposure_record.schema.json provides structured use/field/lineage distinctions. The inherited normalized schemas remain the storage authority; materialized rows are views with source/build receipts.

## Gate refinements

Retain DAV's at-least-two-independent-families minimal cross-study A1 condition; it is not a precision/publication guarantee. One qualified family can support its own limited analysis. Protect reserved patients and related assays across A-BIO/A-PRED/A1. Metadata-only/clinical endpoint curation is distinguished from molecular–outcome/model exposure. Unknown exposure cannot be certified untouched. Missing A-P2 final-test data blocks its independent-test evaluation, not separately admitted A-BIO, CYT A-P1 or A1.

A branch can be released against a prospectively declared bounded source universe without asserting the entire global search is complete; required frozen sources cannot subsequently disappear. Keep a source-universe version in every release. Search completion requires actual pagination/export coverage, queue dispositions, original-source review, overlap reconciliation and a dated update. The old 'two quiet pages' rule is superseded, not silently erased.

## Migration and validation

No patient rows are generated here. Existing consumers gain the new episode-binding joins and materialized schema validation through migration tickets, with old data left immutable. Test unknown bindings, sequential regimens, outcome mismatch, identifier collisions, pair row-order invariance, source failure and private-output filtering. Structural/schema tests do not prove patient linkage or source admission. The current release remains specification-review until actual software/data/statistical receipts exist.
