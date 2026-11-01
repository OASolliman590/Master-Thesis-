# Thesis data repository

Start with `.scratch/runtime/data_repository/cohorts.tsv`. It lists each cohort's status, table dimensions, approval status and file locations. Open `catalog.sqlite` in a SQLite viewer for the same information alongside the source inventory. All paths in the catalogue are relative to the repository root.

From the repository root, build the available local tables and refresh the catalogue:

```sh
../envs/dav-pipeline/bin/python -m tools.a_cohorts build
```

This uses existing pinned local files. It does not download or analyse data. A failure in one cohort does not stop the others. To check one existing table:

```sh
../envs/dav-pipeline/bin/python -m tools.a_cohorts validate --cohort riaz_gse91061
```

Each prepared cohort has `.scratch/runtime/<cohort>/simple/` containing:

- `expression.tsv`: source feature rows × patient columns, with a leading feature identifier column.
- `clinical.tsv`: one row per patient, in exactly the same order as the expression columns. Original endpoint categories, provenance and unknowns are retained.
- `caveats.md`: what is still uncertain, including duplicate features or unverified timing.
- `manifest.json`: source/output hashes, dimensions and approval status.

“Table ready” means those files passed their integrity and alignment checks. It does not authorize analysis. The four admitted cohorts retain their admissions; new exports remain `PENDING_BATCH_REVIEW`. Duplicate source features are preserved, so row counts can exceed unique gene counts. A pending table is not automatically a verified pretreatment cohort. Survival fields marked UNKNOWN have not been extracted or verified in this export.

For example, inspect the catalogue without reading any patient rows:

```python
import sqlite3

with sqlite3.connect('.scratch/runtime/data_repository/catalog.sqlite') as db:
    rows = db.execute('''
        SELECT cohort_id, table_status, genes, patients, expression_path
        FROM cohorts
    ''').fetchall()
```

For a selected cohort, read its expression and clinical files separately in R or Python. Clinical `patient_id` matches the expression header after its first column. Preserve the recorded scale; do not pool raw matrices across studies. IMvigor210 is locked and is never opened by this loader.

## What is included

`REGISTRY.tsv` is the study-level cohort roster. `RESOURCES.tsv` keeps the other discussed repositories, combination cohorts, Paper B/C references and unsigned single-cell leads visible. Listing a source does not mean its patient files have been acquired or its eligibility verified. Paper B production files remain separate and unchanged.

`ICBATLAS_INDEX.tsv` imports only study and processing metadata from the provided ICBatlas parse; `ICBATLAS_PROVENANCE.json` records hashes and the unresolved publisher-file provenance. Its 25 study records and 25 processing records are explicitly **unjoined**: raw study names differ between tables, and one accession can describe more than one study subset. These records are discovery leads, not patient counts, patient tables or validated cohort identities. Response summaries, drug scores and the reconstructed website extracts are not imported.

The previous simple exports are retained in private `simple-before-20261031/` folders for recovery. They are not linked as current tables. Source files and admitted products are preserved.
