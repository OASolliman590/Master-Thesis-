# SC-3 source-derived release interface

The default command accepts only hash-matched invented fixtures. A future source-derived run requires both explicit opt-in and a user-release record bound to the input provenance manifest, clinical and expression hashes, exact cohort set, source-family mapping, resolution statuses, operation, outcome-field set, and a decision identity/path/SHA256. IMvigor210 and ingestion-packet paths remain refused in every mode.

After a separate user release has been recorded, the one-command form is:

```sh
python -m tools.sc.sc3_cli \
  --clinical /path/to/clinical.tsv \
  --expression /path/to/expression.tsv \
  --provenance /path/to/source_manifest.json \
  --release-record /path/to/approved_sc3_release.json \
  --allow-outcomes \
  --output-dir /path/to/new_sc3_output
```

No approved record is included here. This unsigned template is documentation only; it cannot authorize execution:

```json
{
  "record_type": "sc3_user_release_v1",
  "record_status": "PENDING_USER_APPROVAL",
  "real_authorization": false,
  "release_scope": "SC3_REAL_OUTCOME_ACCESS",
  "operation": "sc3-analysis",
  "input_manifest_sha256": "<exact SHA256>",
  "input_sha256": {
    "clinical": "<exact SHA256>",
    "expression": "<exact SHA256>"
  },
  "cohorts": ["<exact cohort IDs>"],
  "source_family_by_cohort": {"<cohort ID>": "<verified source family>"},
  "source_resolution_status": "<must be resolved>",
  "overlap_resolution_status": "<must be resolved>",
  "metric_resolution_status": "<must be resolved>",
  "outcome_fields": ["endpoint_family", "outcome_label", "response", "response_metric"],
  "decision": {
    "identity": "<decision file stem>",
    "path": "docs/decisions/<decision file>.md",
    "sha256": "<exact decision-file SHA256>"
  }
}
```

The input provenance must use producer `tools.sc.sc3_source_provenance`, kind `sc3_input`, classification `real`, and exact hashes for both payloads. Unknown cohort/source mappings and unresolved overlap or metric status stop the run. Outcome values are read only after the opt-in, decision hash, manifest/input hashes, and named cohort/source identities pass.

Tests use a separate temporary test-only record status and explicit fixture registry/decision roots. Those fixtures remain classified as `source_derived_test_fixture`; they are not user approvals and cannot be supplied through the CLI.
