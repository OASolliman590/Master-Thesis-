# B-G1: deterministic outcome-blind gene-set registry and coverage audit

**Paper:** B  
**Specification:** corrected B-KIT v0.2  
**Depends on:** B-P decision; `SECONDARY_PROGRAMS.md`; `EXPLORATORY_MODULES.md`; registry v0.2 and schema  
**May use:** synthetic, patient-free annotation fixtures  
**Must not do:** inspect CPC outcomes, score patients, select probes, fit a model, change `P`, freeze a program, download cohort matrices or invent mappings/weights

## Goal

Build a Python 3.11 standard-library-only module that validates the proposed registry, verifies normalized annotation manifests and produces deterministic, hash-attested registry and coverage tables. Completion means that every required annotation source was supplied and audited. Missing sources produce an explicit incomplete receipt and never a `COMPLETE.json` marker.

## Owned implementation paths

- `tools/b_gene_registry/`
- `tests/b_gene_registry/`
- `docs/validation/B_gene_registry/`

The implementer must not edit `specs/`, other tools/tests, dependency files or existing validation records. The parent owns specification and execution-manager updates.

## Command-line contract

```text
python -m tools.b_gene_registry build \
  --registry specs/B/gene_set_registry.proposed.json \
  --schema specs/B/gene_set_registry.schema.json \
  --annotation-manifest MANIFEST.json [--annotation-manifest MANIFEST.json ...] \
  --output OUTPUT_DIRECTORY
```

Only subcommand `build` is admitted. Inputs and output paths are explicit. No network, environment-dependent discovery or fallback files are allowed.

Exit codes:

- `0`: complete valid audit written with `COMPLETE.json`.
- `2`: usage/argument error or output path already exists.
- `3`: registry/schema/manifest/annotation validation failure, or required annotation source missing; a safely writable missing-source case emits `INCOMPLETE.json`.
- `4`: other input/output failure.

Write to a sibling temporary directory and atomically rename only after validation. Never overwrite an existing output path. Clean a temporary directory created by the current process on failure; never remove a caller-owned path.

## Registry validation

Validate the JSON against the supplied Draft 2020-12 schema without third-party packages. Because the schema is fixed and repository-owned, an exact contract validator is acceptable; it must reject unknown fields, missing required fields, invalid enum/const/type/pattern constraints, duplicate raw members and inconsistent null membership/hash states.

In addition:

1. Require the exact ordered primary membership `HLA-A,HLA-B,HLA-C,B2M,TAP1,TAP2,PSMB8,PSMB9`, `primary_unchanged=true` and `primary_membership_frozen=false`.
2. Recompute every non-null `membership_sha256` using the registry-declared byte contract and reject any mismatch. A null symbol list must have a null hash and unresolved membership; the converse is forbidden.
3. Require one unique program id; separate primary, planned-secondary and M0-M6 layers; never infer a score from membership.
4. Load alias and non-collapse rules from the registry. Apply exact, case-sensitive raw-token matching only. `MB21D1 -> CGAS`, `TMEM173 -> STING1`, `TAPBPR -> TAPBPL`; `TAPBP` and `TAPBPL` remain distinct.
5. Refuse unresolved directions, weights, scoring or predictors as numerical values. No coefficient, sign or patient-level output is part of B-G1.

## Normalized annotation manifest

Each repeated `--annotation-manifest` is UTF-8 JSON with exactly:

```json
{
  "schema_version": "B-G1-annotation-manifest-v1",
  "source_id": "tcga_gencode_v36",
  "source_status": "pinned",
  "canonicalization_authority": "source-specific authority and version",
  "identifier_namespace": "symbol_entrez_ensembl",
  "source_reference": "auditable local/source reference",
  "table_path": "relative/or/absolute/annotation.tsv",
  "table_sha256": "64 lowercase hex characters"
}
```

No other keys are allowed. `source_id` must occur once and be declared in `required_coverage_sources`. `source_status` must equal `pinned`; the other text fields must be non-empty. Resolve a relative `table_path` against the manifest directory. Verify exact annotation bytes before parsing.

The annotation table is an uncompressed UTF-8 TSV with exactly this header and no additional columns:

```text
raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status
```

Every subsequent record has exactly five fields. `mapping_status` is `mapped`, `ambiguous` or `unmapped`. A mapped record has a non-empty canonical symbol and at least one non-empty Entrez/Ensembl identifier; an unmapped record has empty canonical/identifier fields. Ambiguous records retain the source-provided candidates without automatic resolution. Reject NULs, malformed UTF-8, CR-only records, empty `raw_id`, duplicate exact rows and any patient/value/sample/expression column. Multiple distinct rows for a symbol are retained and reported as duplicate/ambiguous coverage, not silently collapsed.

## Required outputs

All TSV files use LF newlines, UTF-8 without BOM, the specified header order, escaped JSON where necessary and lexical row order defined below. JSON uses sorted keys, compact separators, UTF-8, `ensure_ascii=false` and one final LF. Every hash is SHA-256 of exact local bytes.

For a complete audit, output:

- `registry_rows.tsv` and `registry_rows.json`: one row for every non-null raw program token, ordered by program order then member order. Fields: program index/id/layer; member index; raw symbol; canonical symbol after registry aliasing; alias-applied flag; overlap with canonical `P`; membership/direction/weights/scoring/predictor status. Null-membership programs appear in JSON metadata and not as invented rows.
- `coverage.tsv` and `coverage.json`: one row for every registry row times every required source in registry order. Fields include program/member identity, source id, canonical symbol, presence boolean, matching annotation row count, duplicate flag, aggregate mapping status, and sorted unique raw/Entrez/Ensembl identifiers. Absence means annotation absence only, never a biological negative.
- `checksums.json`: registry/schema/manifest/table exact-byte hashes plus all emitted table hashes. Do not hash `checksums.json` into itself.
- `COMPLETE.json`: schema/version, `status=complete`, deterministic counts, ordered required source ids and the SHA-256 of `checksums.json`.

If one or more required sources are missing, perform registry and supplied-manifest validation, then output only `INCOMPLETE.json` in a newly created output directory. It contains `status=incomplete_missing_annotations`, ordered required/supplied/missing source ids, and exact-byte hashes of the registry, schema and supplied manifests/tables. Do not emit coverage tables or `COMPLETE.json`. Exit `3`.

## Acceptance tests

Tests must create only patient-free tiny fixtures and discriminate at least:

1. A valid complete build and exact expected row counts/order.
2. Any alteration or reordering of the eight primary genes.
3. Duplicate program ids or raw members; null/hash inconsistency; wrong membership hash.
4. Exact aliases for `MB21D1`, `TMEM173`, `TAPBPR`, plus proof that `TAPBP` remains distinct from `TAPBPL`.
5. Correct present, absent, duplicate and ambiguous coverage without biological interpretation.
6. A missing expected source creates only `INCOMPLETE.json`, exits `3` and never creates `COMPLETE.json`.
7. Unknown/duplicate source ids, wrong manifest/table hash, path error, unknown fields and non-pinned source status.
8. Rejection of patient/value/sample/expression columns and malformed annotation records.
9. Byte-identical outputs from independent identical builds and an existing-output refusal with no mutation.
10. No invented weights, scoring, model fitting, patient/cohort data or external access.

## Parent gates

```text
python -m py_compile tools/b_gene_registry/__init__.py tools/b_gene_registry/__main__.py tests/b_gene_registry/test_b_gene_registry.py
python -m unittest discover -s tests/b_gene_registry -v
python -m json.tool specs/B/gene_set_registry.proposed.json
python -m json.tool specs/B/gene_set_registry.schema.json
```

The parent reviews all code and tests, reruns gates independently and records the actual receipt. Grok does not commit or push.
