# B-G2: deterministic annotation-normalization preparation

**Paper:** B
**Specification:** [ANNOTATION_NORMALIZATION.md](../ANNOTATION_NORMALIZATION.md); [annotation_normalization.proposed.json](../annotation_normalization.proposed.json); [annotation_normalization.schema.json](../annotation_normalization.schema.json)
**Depends on:** B-P decision; corrected B-KIT v0.2; released B-G1 consumer contract; measurement/expression-platform evidence already in-repo
**May use:** synthetic, patient-free identifier fixtures
**Must not do:** implement in this specification turn (this ticket is the later coding brief); download or process real source databases in Git; inspect patient/sample/expression values; run cohort analyses; calculate scores; fit models; freeze `P`/`U`/`Q`; update external applications; mutate the B-G1 registry or schema

## Goal

Build a later Python 3.11 **standard-library-only** module that reads a freeze-identified public source through a patient-free identifier-only parser boundary and writes the B-G1 five-column uncompressed UTF-8 TSV plus a `B-G1-annotation-manifest-v1` file. Completion for a source means: freeze receipt present, bytes verified, deterministic table hashed, manifest `source_status=pinned` only after that receipt. Missing freeze or failed validation produces an explicit failure/incomplete receipt and never a pinned B-G1 manifest.

This ticket is **implementation-ready**. No tool or tests are written by the specification kit itself.

## Owned implementation paths (later)

- `tools/b_annotation_normalize/`
- `tests/b_annotation_normalize/`
- `docs/validation/B_annotation_normalize/`

The implementer must not edit `specs/` except if the parent later directs a contract fix, and must not edit other tools/tests, dependency files, registries, decision records, or evidence artifacts. The parent owns specification and execution-manager updates.

## Separation of work

| Lane | In scope for B-G2 | Out of scope |
|---|---|---|
| (a) Public annotation / identifier metadata | Headers, gene/probeset IDs, source symbol/Entrez/Ensembl maps, version/hash provenance, B-G1 tables | Patient columns, expression magnitudes, detection-p, methylation, clinical covariates |
| (b) Later real-cohort feature construction | None | `U` freeze, ranks, promoter `Q`, specimen maps, B-I2 features, scores, models |

Historical source availability is not redistribution permission. Do not copy v18 databases, GSE matrices, or GDC tables into Git.

## Command-line contract

```text
python -m tools.b_annotation_normalize prepare \
  --plan specs/B/annotation_normalization.proposed.json \
  --schema specs/B/annotation_normalization.schema.json \
  --source-id SOURCE_ID \
  --freeze-receipt FREEZE_RECEIPT.json \
  --input ROLE=INPUT_PATH [--input ROLE=INPUT_PATH ...] \
  --output OUTPUT_DIRECTORY
```

Optional later subcommand for fixtures only:

```text
python -m tools.b_annotation_normalize validate-table \
  --purpose synthetic_test \
  --table ANNOTATION.tsv \
  --source-id SOURCE_ID \
  --output OUTPUT_DIRECTORY
```

Only `prepare` and `validate-table` are admitted. Inputs and output paths are explicit. No network, environment-dependent discovery, or fallback files. `prepare` is source-freeze mode only. `validate-table` is synthetic validation only and never writes a B-G1 manifest or `COMPLETE.json`.

`SOURCE_ID` must be exactly one of `tcga_gencode_v36`, `gse107299_processed`, `historical_v18_maps`.

Exit codes:

- `0`: valid new output written. For `prepare`, this means the exact receipt has `purpose=source_freeze`, `pin_authorized=true`, all plan/schema/input hashes match, and the pinned B-G1 manifest plus `COMPLETE.json` were written. For `validate-table`, this means only a synthetic `VALIDATED.json` receipt was written.
- `2`: usage/argument error or output path already exists.
- `3`: plan/schema/freeze/input/annotation validation failure; TAPBP/TAPBPL collapse; hash mismatch; missing freeze; patient/value columns; suffix-repair attempt. A safely writable case emits `FAILURE.json` or `INCOMPLETE.json`.
- `4`: other input/output failure.

Write to a sibling temporary directory and atomically rename only after validation. Never overwrite an existing output path. Clean a temporary directory created by the current process on failure; never remove a caller-owned path.

## Freeze receipt (blocking for pinned)

`--freeze-receipt` is UTF-8 JSON with **exactly** these top-level keys: `schema_version`, `purpose`, `source_id`, `pin_authorized`, `plan_sha256`, `schema_sha256`, `inputs`, `reviewer_id`, `reviewer_identity`, `reviewed_utc`, `notes`. Unknown keys fail. Required values are `schema_version=B-G2-source-freeze-receipt-v1`, `purpose=source_freeze`, `pin_authorized=true`, one of the three exact source IDs, lowercase 64-hex hashes of the exact approved plan and schema bytes, non-empty parent reviewer identity fields, a UTC review timestamp and non-empty rationale. The future standard-library tool validates this explicit known contract; it does not claim to implement a general JSON Schema engine.

Each ordered `inputs` element has **exactly**: `role`, `object_name`, `byte_count`, `sha256`, `retrieved_utc`, `exact_url`, `access_class`, `completeness`, `redistribution`, `committed_path`. `byte_count` is positive; `sha256` is lowercase 64-hex; the URL is credential-free; `access_class` is `public` for this ticket; `redistribution` is `not_adjudicated` unless a later reviewed contract says otherwise; and `committed_path` is JSON null in repository-bound receipts. No private absolute path is allowed.

Receipt input roles and order are exact:

| `source_id` | Required ordered `inputs` roles | CLI cardinality |
|---|---|---:|
| `tcga_gencode_v36` | `tcga_gencode_v36` | 1 |
| `gse107299_processed` | `gse107299_processed` | 1 |
| `historical_v18_maps` | `hta20`, then `hugene20st` | 2 |

Each repeatable `--input ROLE=PATH` must match the receipt element at the same index. Missing, extra, duplicate, reordered or role-mismatched inputs fail before parsing; each path's byte count and SHA-256 must match its descriptor.

The B-G1 `source_reference` is rendered exactly as `B-G2|{source_id}|source_freeze|{plan_sha256}|{schema_sha256}|{role1}:{sha256_1}[,{roleN}:{sha256_N}]|{reviewed_utc}`, using receipt order and no URL or path. This is deterministic and credential-free.

Absent, false or synthetic authorization makes `prepare` exit `3` with only `INCOMPLETE.json` or `FAILURE.json`. Synthetic fixtures use only `validate-table --purpose synthetic_test`; that command writes `VALIDATED.json` and can never emit a B-G1 manifest or `COMPLETE.json`.

## Input handling by source

### `tcga_gencode_v36`

Exactly one `--input tcga_gencode_v36=PATH`. Local uncompressed UTF-8 TSV. First non-empty comment must be `# gene-model: GENCODE v36` (leading `# ` plus `gene-model: GENCODE v36` as already parsed by B-F1). Header must equal the nine STAR fields. Exclude the four `N_` summary `gene_id` values. Extract `gene_id` and `gene_name` only. Refuse gzip. Verify input bytes against the same-index receipt descriptor before parsing.

### `gse107299_processed`

Exactly one `--input gse107299_processed=PATH`. Accept either (i) the compressed object whose SHA-256 matches `09d866ce89adb7122879354a523ae0c1fdac03572c555a2d647b64a35c342f2b` when the receipt names that exact compressed object, or (ii) a patient-free identifier-only TSV with the seven exact annotation fields and its **own** receipt hash. Never treat a prefix hash as the full-object hash. When the compressed matrix is admitted, stream rows and retain only the first seven annotation fields; never parse later fields as identifiers or retain their values. Synthetic fixtures must not be cut from real patient matrices.

### `historical_v18_maps`

Exactly two inputs in order: `--input hta20=PATH --input hugene20st=PATH`. Each is its hashed `*_18.0.0.tar.gz` package, or an already extracted SQLite member explicitly named and hashed by the corresponding receipt descriptor. Read-only SQLite (`mode=ro`). Do not install R packages. Emit platform-qualified `raw_id` `{hta20|hugene20st}:{probe_id}`. Retain `_at`. Do not fill NULL Entrez from GPL19803 description bytes even if those bytes are present.

## Output layout

On success, `OUTPUT_DIRECTORY` contains:

- `annotation.tsv` — B-G1 five-column table, stable sort, LF, UTF-8 no BOM
- `MANIFEST.json` — B-G1 annotation manifest; `source_status=pinned` only with freeze authorization
- `checksums.json` — exact-byte SHA-256 of plan, schema, freeze receipt, every ordered input, `annotation.tsv`, sidecars; do not hash `checksums.json` into itself
- `PROVENANCE.json` — parser boundary, namespace, authority/date, row counts, evidence class
- `CONFLICTS.tsv`, `HLA_CAUTION.tsv`, `UNMAPPED.tsv` — may be empty except header
- `COMPLETE.json` only when pinned and valid

JSON outputs use sorted keys, compact separators, UTF-8, `ensure_ascii=false`, one final LF.

On incomplete/failure, emit only `INCOMPLETE.json` or `FAILURE.json` in a newly created directory (plus stderr diagnostics). Do not emit a pinned manifest or `COMPLETE.json`. `validate-table` success emits only `VALIDATED.json`; it never shares the production success layout.

## Deterministic gates

1. Validate the explicit plan contract represented by the B-G2 schema, including unknown-field rejection; a Python 3.11 standard-library implementation performs the documented structural checks directly rather than claiming a generic Draft 2020-12 validator.
2. Require plan `schema_version=B-G2-annotation-normalization-proposed-v1` and source order `tcga_gencode_v36`, `gse107299_processed`, `historical_v18_maps`.
3. Load alias and non-collapse rules from the plan (copied from the registry, not edited there). Exact case-sensitive matching: `MB21D1→CGAS`, `TMEM173→STING1`, `TAPBPR→TAPBPL`; `TAPBP` remains distinct from `TAPBPL`.
4. Verify receipt purpose/authorization, exact plan/schema hashes, ordered input roles/cardinality and every input byte count/hash before parsing.
5. Apply the source recipe; never choose among candidates by expression, coverage, outcome, effect, or convenience.
6. Enforce B-G1 cell rules for `mapped` / `ambiguous` / `unmapped`.
7. Stable row order; exact-byte SHA-256.
8. Refuse patient/value/sample/expression columns.
9. Two independent identical `prepare` runs are byte-identical in scientific outputs.

## Negative and adversarial cases (later tests)

Tests must create only patient-free tiny fixtures and discriminate at least:

1. Valid synthetic `validate-table --purpose synthetic_test` for each `source_id`, exact expected order/hash receipt, and proof that it emits neither a B-G1 manifest nor `COMPLETE.json`.
2. Missing receipt, `purpose=synthetic_test` or `pin_authorized=false` makes `prepare` exit `3` and never yields `source_status=pinned`.
3. Wrong input SHA-256; gzip supplied where uncompressed is required; prefix hash used as full-object hash.
4. Unknown fields in plan, freeze, or B-G1 manifest.
5. Patient/value/sample/expression columns; NUL; CR-only; malformed UTF-8; empty `raw_id`; duplicate exact rows.
6. STAR `N_` rows classified as genes; missing GENCODE v36 comment; abundance used to pick a mapping.
7. GSE patient columns parsed; `_at` appended to `GeneID`; Ensembl invented.
8. v18 suffix stripping filling `101928749_at`; unqualified `raw_id`; HTA and HuGene collapsed into one row; 24,937 exported as `U`.
9. `TAPBP` collapsed into `TAPBPL`; aliases not applied; HLA rows dropped for “caution”.
10. Existing output path refused without mutation; byte-identical reruns; no network.
11. Altered plan/schema hash; missing/extra/reordered/duplicate input role; wrong v18 order; descriptor byte-count/hash mismatch; unknown receipt or input-descriptor field.

## Parent gates (when implemented)

```text
python -m py_compile tools/b_annotation_normalize/__init__.py tools/b_annotation_normalize/__main__.py tests/b_annotation_normalize/test_b_annotation_normalize.py
python -m unittest discover -s tests/b_annotation_normalize -v
python -m json.tool specs/B/annotation_normalization.proposed.json
python -m json.tool specs/B/annotation_normalization.schema.json
```

The parent reviews all code and tests, reruns gates independently, and records the actual receipt. Implementers do not commit or push.

## Scientific boundary

B-P remains the selected primary. B-G2 cannot freeze `P` or `U`, define `Q`, score a program, select genes, view CPC outcomes, prove measurement specificity, establish cross-platform transport, or release a biological analysis. The existing registry field `required_coverage_sources[].annotation_status` and this plan's `sources[].source_status` both remain `pending_normalized_export`; only a later parent-approved B-G1 manifest may carry `source_status=pinned`. This ticket does not change either pending status by being written.
