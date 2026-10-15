# Reproduction and readiness

## Readiness checklist

A branch reaches R9 only when all applicable items are complete:

- search version frozen and every prior queue row disposed;
- original study/publication family resolved;
- exact source objects retrieved and completely hashed;
- patient/treatment/specimen/assay/outcome registries validated;
- endpoint and timing rules reviewed;
- overlap and prior exposure resolved;
- branch admission receipt approved;
- matrix built under a frozen schema/config;
- structural and feature-coverage validation passed;
- split role and independence freeze approved;
- public/private release boundaries checked;
- fresh reproduction and resume/checkpoint tests passed;
- source-specific scientific reviewer signed;
- execution environment validated.

## Reproduction bundle

```text
release_manifest.json
commands.sh
environment lock or container digest
schema versions
config files and hashes
source object registry snapshot
admission receipt IDs
private patient membership hash
split version
matrix hashes
validation receipts
public aggregate report
```

Restricted source paths and patient records remain outside the public bundle.

## Fresh build

A fresh build starts from an empty output directory and verifies every source/input hash. It must not depend on undocumented cache state.

## Resume

A resume performs no work only when all completion-receipt identities match. Modified inputs, code, configuration or schemas invalidate the affected and downstream stages.

## Environment validation

Record operating system, Python/R versions, package lock, locale/timezone, filesystem assumptions and remote execution identity. Deferred AIU or other remote checks remain explicitly pending and are never reported as passed.

## Release labels

Allowed release labels include:

- `specification-review`;
- `synthetic-software`;
- `real-source-structural-validation`;
- `branch-data-release`;
- `scientific-analysis-release`.

A lower label cannot be described using a higher one. Passing this Spec Kit’s structural tests is `specification-review`, not Paper A data validation.

## Rebuild triggers

Rebuild/review is mandatory after:

- source object replacement;
- endpoint or timing mapping change;
- specimen-selection rule change;
- annotation/feature-universe change;
- overlap/exposure discovery;
- split-role change;
- code/config/schema change.

## Readiness report

The report lists each branch separately. A source can be R9 for baseline biology and R4 for longitudinal progression. No global analysis-ready flag is produced.
