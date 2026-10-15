# Paper C implementation tickets

Tickets are ordered release gates. A later ticket may not infer completion of an earlier scientific gate from software success.

## C-T00 — Historical reuse and repository reconciliation

**Deliverable:** classified inventory of existing C code, metadata audits, NMRbox recovery and source objects: `reuse_unchanged`, `adapt`, `replace`, `obsolete`, `missing`, `synthetic_only`, `real_metadata_validated`.

**Acceptance:** every reused component has path, commit/hash, tests, data exposure and known limitation. No pipeline is copied wholesale.

## C-T01 — B-to-C query contract validator

**Deliverable:** schema/CLI validating `Q_E` and `Q_M`, quotas, direction, provenance, leakage fields and deterministic hashes.

**Tests:** missing fields, duplicate genes, invalid directions, quota mismatch, insufficient methylation genes, prior-outcome leakage, hash instability.

**Gate:** fictional fixtures only until B release.

## C-T02 — Compound identity and universe release

**Deliverable:** canonical parent/salt/alias/structure/mechanism registry and frozen universe manifest.

**Tests:** fuzzy-name collision, salt/parent separation, duplicate BRD IDs, multi-target compound, unknown structure, conflicting regulatory status.

## C-T03 — Source admission adapters

**Deliverable:** one adapter and admission receipt per independent source, with exact intervention/control/replicate/unit mapping.

**Tests:** shared controls, technical replicates, missing dose units, unresolved row joins, mirror duplicates, incomplete feature universe.

## C-T04 — LINCS matrix adapter and WTCS parity

**Deliverable:** hash-checked GCTX/metadata adapter and scorer matching the pinned reference.

**Tests:** all fixtures in `SCORER_CONTRACT.md`, release overlap and full-universe ranking.

**Gate:** no real biological scoring until parity is independently reviewed.

## C-T05 — Sample-level query scorer and limma engine

**Deliverable:** pinned directional rank scoring, programme aggregation, `D_i`, source-specific design matrices and `delta[s,j]` outputs.

**Tests:** paired/unpaired designs, blocks, shared controls, query coverage, one-sided programmes, null and opposite effects, technical-replicate collapse.

## C-T06 — Synthetic end-to-end workflow

**Deliverable:** fictional B handoff → fictional C2 signatures → fictional independent study → evidence matrix → figures/handoff.

**Acceptance:** deterministic fresh and resume runs; all outputs labelled synthetic; biology validation false.

## C-T07 — Tiny permitted real-data smoke

**Deliverable:** bounded I/O/ID/coverage smoke on an admitted public object without inspecting effects for endpoint choice.

**Acceptance:** exact source hash, command, object counts and no biological conclusion.

## C-T08 — Biological configuration freeze

**Deliverable:** approved query hashes, universe, source/contrast list, scorer versions, multiplicity, seed and environment lock.

**Gate:** explicit user/scientific release required.

## C-T09 — C2 discovery execution and interpretation freeze

**Deliverable:** context-specific scores, C1 calibration, coverage and frozen candidate interpretations.

**Acceptance:** no independent validation outcomes opened; no class claim unless identifiability passes.

## C-T10 — Independent measured primary and validation

**Deliverable:** source-specific `delta`, `delta_s`, `Delta_Q`, component effects, programme sensitivities and disagreement table.

**Acceptance:** biological units and exclusions trace to admitted source receipts; nulls retained.

## C-T11 — Context, mechanism, viability and PK append

**Deliverable:** native-scale evidence records with contradictions and missingness; no opaque total score.

## C-T12 — Figures, manuscript tables and wet-lab handoff

**Deliverable:** four reproducible figures, source tables, evidence tiers/Pareto set and prospective experimental packets.

**Acceptance:** every panel has source/unit/N/uncertainty/claim ceiling; no prediction fills missing measured validation.
