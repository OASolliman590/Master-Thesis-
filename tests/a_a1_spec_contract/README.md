# Integrated specification tests — not the clinical pipeline

Run from repository/export root:

```sh
python -m pip install -r tests/a_a1_spec_contract/requirements.txt
python -m unittest discover -s tests/a_a1_spec_contract -v
```

Tests exercise actual document/schema files, offline references, synthetic invalid records, release-state guards, exact historical source preservation, TSV shape and fixed-score algebra. They do not implement the planned biological pipeline or establish source/patient admission, final-test independence or real-data results. Synthetic fixtures are named SYNTH and never persisted as patient records.

The initial inherited-only package lacked the new A/A1 contracts and episode-binding schema. The final checks validate these authored artifacts. This is document/schema verification, not a claim of a full application TDD cycle or freshly reproduced legacy bugs. The separately attempted repository-wide test result and environment are reported independently; a focused pass does not turn a failed/missing full suite green.
