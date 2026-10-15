# Software architecture

## Proposed namespace

```text
tools/a_dav/
    cli.py
    schemas.py
    search_log.py
    study_resolution.py
    object_verification.py
    registries.py
    endpoints.py
    timing.py
    assays.py
    overlap.py
    exposure.py
    admission.py
    matrices.py
    release.py
    reporting.py

tests/a_data_acquisition_validation/
docs/validation/A_DAV_*/
```

`tools/a_dav` owns acquisition and validation. Paper A scientific analysis remains in separate A namespaces. This avoids coupling identity/admission rules to model code.

## Proposed commands

```text
python -m tools.a_dav sources search-register
python -m tools.a_dav sources resolve-study
python -m tools.a_dav sources verify-object
python -m tools.a_dav patients build-registry
python -m tools.a_dav patients link-specimens
python -m tools.a_dav endpoints harmonize
python -m tools.a_dav timing harmonize
python -m tools.a_dav assays validate
python -m tools.a_dav overlap audit
python -m tools.a_dav admission evaluate
python -m tools.a_dav matrix build
python -m tools.a_dav matrix validate
python -m tools.a_dav release freeze
python -m tools.a_dav report build
```

These are proposed interfaces, not claims that commands exist.

## Stage contract

Every stage declares:

- input schema/version;
- output schema/version;
- configuration and defaults;
- deterministic ordering/tie rules;
- failure states and exit semantics;
- provenance and checksums;
- tests and real-source tracer;
- completion receipt.

## Data flow

```text
candidate packets
  -> study/publication/source registries
  -> private patient/treatment/specimen/assay/outcome registries
  -> overlap/exposure ledgers
  -> branch admission receipts
  -> materialized matrices
  -> matrix validation receipts
  -> split/freeze release bundle
```

Stages communicate through schema-validated objects, never undocumented filenames.

## Determinism

- sort outputs by stable canonical keys;
- preserve raw fields verbatim alongside derived fields;
- use versioned mapping rules;
- make specimen and follow-up selection row-order invariant;
- hash exact input bytes, config and code identity;
- write atomically to new version directories;
- never overwrite a released artifact.

## Resume/checkpointing

A stage may resume only when all input, code, config and schema hashes match its completion receipt. Partial downloads have distinct suffixes and cannot satisfy object verification. A stale or mismatched receipt invalidates the stage.

## Failure semantics

Expected data blockers produce a reason-coded incomplete receipt and nonzero command status appropriate to automation. Unexpected exceptions retain logs and never leave a false `COMPLETE` marker.

## Reporting

Public reports contain aggregate counts, gate states, limitations and hashes. Private reports may contain patient-level discrepancy lists under authorized storage. Report generation cannot alter registries or admissions.

## Implementation language

Python 3.11+ standard library is preferred for schema-independent plumbing; JSON Schema validation may use a pinned `jsonschema` release. R/Bioconductor belongs downstream where assay-specific statistical methods require it. Database storage may use SQLite/Parquet/relational tables, but canonical exports must remain schema-versioned and portable.
