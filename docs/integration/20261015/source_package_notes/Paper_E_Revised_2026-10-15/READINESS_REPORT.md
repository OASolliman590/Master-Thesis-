# Revised Paper E readiness — 15 October 2026

## What was delivered

Two populated draft specifications: public-only `specs/E/` and optional last-stage `specs/E_LAST/`. The original experiment-dependent primary and implementation gates were replaced in active core files, not retained behind an optional-data note. The original v1 ZIP is unchanged.

| Layer | Actual state |
|---|---|
| Scope redesign | User-directed split specified |
| Scientific endpoint, lead, axis, concrete schedules/tolerances | Recommendations with explicit unresolved decisions; not silently approved |
| Core draft | Populated; E0–E7 packets and public-only completion profiles |
| Optional extension draft | Populated; dormant; X0–X5 only after actual core completion and data qualification |
| Source review | Bounded update: seven primary-source records plus one explicitly unverified novelty lead; no new numerical observations admitted |
| Parameters | 34 source/role coverage entries with unresolved numerical evidence; no new biological constants fitted |
| Local compatibility QA | 22 legacy schemas; 33 examples; 50 tests passed, 0 failures/errors/skips |
| V2 contract QA | 5 additional schemas; 7 synthetic examples; 42 tests passed, 0 failures/errors/skips |
| Capability logic | 4,096 combinations of 12 selected interacting flags checked; no probabilities assigned |
| Actual scientific core release | Not produced; E0–E7 production/scientific work remains |
| PBPK/QSP fits, real model held-out isolation, upstream parity, AIU tests | Not performed in this revision |
| Independent empirical/prospective/clinical validation | Not performed |
| Repository changes | No remote branch, commit, push, merge or PR; integrator-owned policy preserved |

There are **92 distinct local reference/compatibility test cases**. The 42 v2 tests are also distributed and rerun with the standalone optional package; those are repeated copies, not 42 additional independent cases or scientific evidence.

## Correct meaning of completion

The core is designed to finish without original biological data. It still needs recoverable public quantitative exposure and biological evidence, justified uncertainty, actual analyses and reviews. A scheduling analysis and a measurement-linked identifiability analysis are distinct accepted design profiles; a metadata-only catalogue or arbitrary simulation is incomplete. No journal-acceptance guarantee is made.

The extension requires the actual frozen, scientifically reviewed completed foundation plus permitted original generated/QC-admitted data. The synthetic `complete=true` example is not that foundation. Missing, partial, null, adverse or contradictory original results never block or overwrite the core; they control the extension's enabled modules and claims.

This redesign does not waive any university or biological-paper experimental obligation. It changes Paper E's dependency structure only.

## Traceability

Core and extension decision registers identify owners, evidence requirements and affected packets. QA receipts/logs state checks actually performed and not performed. MANIFEST.json and SHA256SUMS.txt bind payload files; archives are independently integrity-checked in the delivery receipt. The standalone bundles are checked with the other branch physically absent; this verifies contract-package independence, not real-fit scientific isolation.
