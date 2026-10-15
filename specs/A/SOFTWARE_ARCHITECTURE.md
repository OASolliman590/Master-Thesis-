# Software architecture and stage contracts

## Ownership

The shared acquisition package owns tools/a_dav and private normalized records. A analysis adapters should live under tools/a_analysis (proposed, not currently implemented); A1 under tools/a1_analysis. One accountable integrator owns shared contracts and Git integration. Implementers receive bounded packets; no two writers edit the identity store concurrently. AIU is the principal scientific execution environment; optional local/Colab tracers must execute the same versioned code, not an alternate pipeline.

## Dataflow

source discovery → immutable objects → normalized records/episode bindings → overlap/exposure → branch admission → matrix build/coverage → split protection → branch statistical release → A-BIO or A-PRED/A-P1 → immutable handoff/evaluation → reports. All arrows require schema/config/code/input hashes and a completion receipt. Acquisition does not compute response-associated effects. Analysis code cannot override an admission failure or silently construct its own patient list.

## Proposed command interface, NOT existing executables

`python -m tools.a_dav inventory|resolve|validate|materialize|release --config ...`
`python -m tools.a_analysis bio|develop|freeze|evaluate|endpoint-sensitivity|report --release ...`
`python -m tools.a1_analysis pair-audit|estimate|synthesize|report --release ...`

These names define future CLI behavior; do not claim they run until the corresponding migration ticket is implemented and tested. Public configurations contain logical storage roots only. Credentials and actual private paths remain environment-managed. stdout reports stage/status/receipt, not patient IDs. A nonzero status accompanies blocked required gates; no 'success with empty output' shortcut.

## Reproducibility and restart

Pin Python/R and packages with a lock/container digest after a small compatibility test, including reticulate/import/solver signatures where used. Record locale, timezone, RNG, BLAS/thread settings and platform. A stage writes temporary outputs, verifies checksums/schema/counts, atomically promotes files, then writes its completion receipt. Resume is valid only when input, schema, config, code and environment identities match; a receipt from another version invalidates downstream stages. Never hash a partial retrieval as the completed source object.

## Legacy migration

Inventory first; compare historical GitHub, NMRbox and active candidates by SHA-256/Git blob plus normalized function-body AST where languages permit. Keep exact bytes separately from semantic comparisons. Ports receive new tests before behavior changes; archived source is read-only. No historical test count is reported current. IMPLEMENTATION_RECONCILIATION.md and migration tickets decide reuse/adapt/replace rather than rebuilding by preference.

## Scientific separation

Model coefficients, effect estimates, programme definitions and candidate-release tables are separate typed outputs. Serialized model loading must reject incompatible dependency versions/untrusted formats. No notebook state or undocumented cache is part of a release. Public plotting code reads permitted aggregate outputs; patient predictions remain in controlled private storage unless explicit terms permit release.
