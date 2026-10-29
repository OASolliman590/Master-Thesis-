# Backlog


- The new DAV virtual environment cannot import the sibling legacy `batchqual` package: 40 pre-existing legacy-bridge tests fail with `ModuleNotFoundError`. Round 1 coordinator reproduced the same baseline. Resolve environment packaging separately; preserve the legacy bridge and report this gate honestly.

- The installed debate-review preflight fails before either configured reviewer starts: both relays reject their output directories as already existing. Repair the review tool separately; no debate review is claimed for this redesign. The requested Astra review remains the code review path.

- The opt-in historical inventory test compares the current queue-reconciliation test file with its A-DAV-04 byte-size/hash receipt. Moving evidence tests changes that file, so the historical comparison fails. Preserve the historical receipt; decide separately how historical snapshot checks should select their original source revision.

- Strengthen the outcome-blind V3 path by excluding response characteristics from the inventory parser and add a test that detects key access. Deferred by the bounded Riaz V3 integrity fix.

- Move the visit literals (`Pre` and `On`) from `matrix_v3.py` into the field map per ADR-0002. Deferred by the bounded Riaz V3 integrity fix.

- Reconcile GSE176307 expression row identifiers and sample-by-feature orientation with GEO specimens before expression binding; retain the source object and unresolved timing and duplicate-profile questions.
