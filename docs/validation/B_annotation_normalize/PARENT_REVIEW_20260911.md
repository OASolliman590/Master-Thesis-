# B-G2 parent implementation review

**Reviewed:** 11 September 2026
**Disposition:** parent-accepted local synthetic software checkpoint; AIU Python 3.11 portability pending
**Base before implementation:** `7d4d2017b8b937b0fd77d73d026f231760364779`

This receipt covers the Python standard-library B-G2 annotation-normalization implementation and patient-free acceptance tests. It does not record a real source freeze, normalized biological export, annotation coverage result, program score, model, cohort analysis or scientific release.

## Delegation disposition

Grok CLI 1.0.13 was available, but the delegate relay failed its version preflight before dispatch. A direct workspace-sandbox launch then failed while creating Grok's own authentication/session state outside the repository; no Grok session or repository edit was created. The requested host escalation was rejected because it would have exceeded the approved workspace-write boundary. The Sol parent therefore implemented and reviewed the bounded ticket directly. Spark was not used.

## Implemented boundary

- `prepare` binds the exact approved plan/schema bytes, an exact `B-G2-source-freeze-receipt-v1`, ordered input roles, byte counts and SHA-256 values before parsing.
- Source-specific parsers cover uncompressed TCGA GENCODE-v36 STAR identifiers, the GSE107299 seven-field identifier boundary or the exact approved compressed object, and platform-qualified read-only v18 SQLite/package inputs.
- Outputs are deterministic B-G1 five-column annotation tables, exact pinned manifests, provenance/checksum receipts, conflict/HLA/unmapped sidecars and a completion marker written last through atomic directory promotion.
- `validate-table --purpose synthetic_test` emits only `VALIDATED.json` and cannot emit a manifest or completion marker.
- Exact aliases are applied while `TAPBP` remains distinct from `TAPBPL`. Patient/value columns, invented Ensembl identifiers, suffix repair, wrong hashes/roles, unknown fields, malformed encodings, duplicate exact rows and output replacement fail closed.

## Parent review findings closed

The parent tightened the initial implementation so the admitted compressed GSE path iterates decompressed rows without retaining matrix values, extracted v18 databases require the correct chip-specific object name, a receipt cannot carry a path-like object name, observed input hashes survive hash-failure receipts, the GENCODE comment must precede the TCGA header, and an empty production export cannot be pinned. Tests independently verify B-G1 consumption, output/checksum links and byte-identical reruns.

## Exact reviewed hashes

```text
42301c3899de2323668341bad65124ef8e2a2c68940213babc44825068dedd3b  tools/b_annotation_normalize/__init__.py
99794f44782a8806c1518f4fa0384d78b55c95f1d208d099d1e5a04763fbd058  tools/b_annotation_normalize/__main__.py
fd2484549b9142c0644212a09f752cbf78b24404341c7db33c09cc26d58ef9d9  tests/b_annotation_normalize/test_b_annotation_normalize.py
8d0b20c1284820d2510ab5d9f79cbba3f6af611b8e27cbb075448bbb7e60beec  specs/B/annotation_normalization.proposed.json
7be7fcc433c326e002a44478ec3c0213d858ee4c0a7dcb0c9463edef558e6820  specs/B/annotation_normalization.schema.json
```

## Gates

Local interpreter: Python 3.12.10.

```text
python -m py_compile tools/b_annotation_normalize/__init__.py tools/b_annotation_normalize/__main__.py tests/b_annotation_normalize/test_b_annotation_normalize.py
python -m unittest discover -s tests/b_annotation_normalize -v
python -m json.tool specs/B/annotation_normalization.proposed.json
python -m json.tool specs/B/annotation_normalization.schema.json
```

All commands exited 0. The B-G2 suite passed **16 tests**. A final combined synthetic Paper B run passed **66 tests in 33.175 seconds**, with eight pre-existing environment-dependent skips in the unchanged suites.

AIU connectivity reached Python 3.11.16, but the private-code transfer was blocked before egress. No remote test ran; see [AIU_PENDING_20260911.md](AIU_PENDING_20260911.md).

## Scientific disposition

The software checkpoint is accepted locally. All three plan sources remain `pending_normalized_export`; no real freeze receipt was supplied and no real B-G1 manifest is claimed. `P`, `U`, `Q`, specimen/covariate policy, measurement specificity, cross-platform transport and every cohort/scoring/model gate remain unchanged.
