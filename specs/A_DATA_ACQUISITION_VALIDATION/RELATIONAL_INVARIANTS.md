# Cross-table invariants beyond JSON Schema

JSON record validity is necessary, not sufficient. Admission must execute these relational checks against private normalized tables and save a validation receipt with exact failures and counts.

## Keys and evidence

Primary keys are unique and strings remain byte-preserving aliases. Foreign keys resolve to exactly one authorized record; duplicate publication/accession aliases are edges, not duplicate patients. Every admitted source object has complete-byte SHA-256, version/retrieval/terms, declared unit/processing and verified matrix/header linkage. Patient, specimen and assay counts are independently computed. No patient identifiers or restricted paths enter public Git; pseudonyms are still patient-level records under the default private policy.

## Episode integrity

Each analysis-selected exposure component, specimen and outcome has an episode_binding of the appropriate role with source evidence. subject patient equals episode patient. Component sequence and specimen timing refer to the same index episode; outcome assessment belongs to that episode. A specimen may legitimately serve as an end-of-prior/start-of-next context only through separate explicitly evidenced bindings; no global one-patient-one-response assumption. Unknown bindings block the relevant row. Regimen IDs alone do not resolve sequential episodes.

## Materialized views

One baseline patient per branch unless a separately specified multilevel design exists. Pair rows have the same patient/episode on both sides; selected assays belong to selected specimens; follow-up obeys the source-specific window and exposure rule; assay scales/platforms are compatible or explicitly admitted. Multiple windows preserve dependence. Sorting/permutation cannot change deterministic selections. Missing follow-up is represented in the audit denominator with a reason, not fabricated in a pair row.

## Endpoints and splits

Raw outcomes are immutable. Canonical ORR/DCR agrees with source-supported category/criteria and episode; PSA/pathology/DCB/survival cannot acquire ORR labels by a shortcut. Conflicting source assertions block until adjudicated. Each patient/family has one permanent development/final-test role; nested fold assignments are scoped separately. Overlap-connected or unresolved potentially overlapping families cannot cross protected boundaries. Related A1/multi-omics specimens inherit reservation. Metadata curation and molecular–outcome exposure are distinct ledger uses; unknown exposure cannot pass untouched-test certification.

## Receipts and cardinality

A source-admission receipt's patient/assay/class counts must equal the actual branch rows, not publication totals. Every required source in a frozen release must be present and pass; missing source yields INCOMPLETE_REQUIRED_SOURCE. SHA-256s must match bytes, not just format. A reviewer string is not proof of a real signature: validate reviewer identity, actual review date and referenced evidence in the authorized review system. Matrix/config/schema/code/exposure/split changes invalidate the dependent receipt. No self-issued synthetic fixture is a clinical admission.

## Test evidence classes

Schema fixtures test record syntax/enums/conditional requirements. Relational synthetic tests test joins, counts, rank/logic and leakage barriers. Real-source tracers test only retrieved formats/mappings explicitly examined. Full clinical validation requires actual source bytes, private joins, reviewer adjudication and reproduction. Never promote one evidence class to another.
