# Implementation reconciliation

## Three-way comparison

The reconciliation covers:

1. historical repository `OASolliman590/epigenetic-ici-priming-thesis`;
2. source-only NMRbox recovery `reference/legacy_nmrbox_20260911/`;
3. current Paper A specification and merged repository state.

The machine-readable table is `implementation_reconciliation.tsv`.

## Evidence status

The NMRbox archive contains source/spec/configuration files and selected tests but deliberately excludes source data, patient/sample manifests, matrices, results, logs and runtime environments. It can establish code history, not historical scientific admission or reproducibility.

The current repository has stronger scientific contracts and source-specific reports, but no merged Paper A acquisition implementation under `tools/`.

## Reuse classes

### Adapt after characterization

- GEO/SRA retrieval and metadata helpers;
- HTTP/checksum/atomic-write patterns;
- run-manifest conventions;
- header/alias inspection helpers;
- gene-ID mapping utilities;
- report-bundle patterns;
- selected synthetic failure cases.

### Replace

- historical global patient manifest;
- endpoint normalization that collapses SD and PD;
- global include flag;
- treatment-delta resolver;
- last-row follow-up selection;
- missing-to-zero harmonization;
- default assay-to-model routing;
- source rules that assert baseline timing without source evidence.

### Preserve as historical evidence only

- 47-row roster and previous inclusion flags;
- old output counts and checked tasks;
- historical biological results not reproducible from the archive;
- tests whose expected values encode obsolete endpoint or timing semantics.

## Confirmed incompatibilities

| Finding | Evidence | Disposition |
|---|---|---|
| missing values converted to zero | recovered `harmonize.py` calls `fillna(0.0)` | prohibit and replace |
| SD/PD collapsed | historical patient response normalizer | replace with endpoint instances |
| on/post pooled | historical delta resolver | replace with time ontology |
| row-order-dependent follow-up | one dictionary value overwritten per patient | replace; add invariance test |
| multiple specimens overwritten | historical pre/after maps | preserve all specimens |
| inconsistent include semantics | pretreatment path differs from delta path | branch memberships replace global flag |
| broad model fallback | non-count/non-excluded assays route to one backend | DAV emits suitability only; fail closed |
| scale heuristics | assay detector relies partly on value magnitude | retain only as secondary anomaly check |

## Migration rule

Historical archives remain immutable. Reused functions are copied or reimplemented under new ownership with characterization tests and an explicit migration receipt. No historical output is grandfathered as a current admission receipt.

## Known but unverified risks

The following remain `UNKNOWN` until characterization tests run:

- response conflicts accepted by some execution paths;
- accession aliases double-counted in old runs;
- resume behavior under interrupted downloads;
- gene-ID collisions across annotation versions;
- approximate immune scores mislabeled in old generated reports.

Do not report these as fixed or currently present without reproduction.
