# Paper B kit amendment: exploratory modules and extra data types

Decision date: 7 September 2026. Integration date: 10 September 2026. Status: USER-REQUESTED SCOPE AMENDMENT; proposed and not frozen; not a real-cohort release; not a change to the selected B-P estimand.

This corrected v0.2 amendment is based on commit `a0eb7dbfa5beb2d64aa147f6c3d0ba44255a5e4c` and incorporates the user-supplied `B_kit_amendment_20260907.zip` (SHA-256 `28260ec713cef24805bca19b42d514f3ba70a5e9c4501b214daa233c62671058`). Archive instructions were reviewed as proposed content, not executed as authority. The parent reconciled them with the canonical Paper B specification before integration.

## What remains unchanged

- The selected primary estimand remains B-P: TCGA-PRAD development and one no-refit CPC-GENE `Delta_R2` comparison of frozen baseline and extended ridge models.
- Proposed primary membership remains `P = {HLA-A, HLA-B, HLA-C, B2M, TAP1, TAP2, PSMB8, PSMB9}`. It is unchanged by this amendment but is still proposed and unfrozen.
- Primary candidate predictors remain the eight promoter aggregates of `P`; B-P1 and B-F1 engineering contracts are unchanged.
- Universe `U`, promoter set `Q`, specimen policy, purity comparability, measurement sources, minimum effect and precision remain unresolved gates.
- Historical June/July PAN ICI responder lists remain excluded from primary and confirmatory outcomes.
- No CPC-GENE outcome, association or performance value may select membership, mappings, scoring, predictors or promotion status.

## What this amendment adds

1. A proposed, machine-checkable registry for the three planned secondary programs and exploratory modules M0-M6.
2. Explicit identifier, provenance, membership-hash and unresolved-scoring fields so absence of evidence cannot be interpreted as a frozen score.
3. Proposed extra data types for later sensitivities and secondary contrasts, each with an allowed-use and claim ceiling.
4. Ticket B-G1: an outcome-blind registry and annotation-coverage audit before any B-I5 module scoring.

The module definitions live in [EXPLORATORY_MODULES.md](../../specs/B/EXPLORATORY_MODULES.md). The normative machine-readable proposal is [gene_set_registry.proposed.json](../../specs/B/gene_set_registry.proposed.json), validated against [gene_set_registry.schema.json](../../specs/B/gene_set_registry.schema.json). B-G1 may audit the proposal but cannot freeze it.

## Corrections made during integration

- `P` is described as unchanged, not frozen.
- Official Hallmark IFN-gamma membership remains unresolved until its 200-gene source bytes and release are pinned; no mini-panel may substitute.
- `MB21D1 -> CGAS`, `TMEM173 -> STING1`, and `TAPBPR -> TAPBPL` are explicit canonicalization rules. `TAPBP` and `TAPBPL` are distinct loci and must never be collapsed.
- M1 is registry-only until its directions and scoring are frozen; optional promoter candidates remain out of the primary predictor set.
- M5 is a checkpoint-candidate panel. A gene becomes an approved-immunotherapy target only through a separate drug/authority/date/indication evidence table.
- M6 is named epigenetic regulators because it mixes writers, erasers and other regulators.
- Thorsson immune subtype is expression-derived/integrative context, not orthogonal validation of an expression program.
- Extra data types are admitted only as proposed, unfrozen inputs. No availability, comparability or biological inference is implied.

## Outcome-access state and effects

The amendment was prepared without using CPC-GENE outcome values. Historical CPC header, identifier and coverage inspections documented before this amendment do not constitute outcome-score access and were not used to select these programs. This amendment changes specification scope only: it adds no patient result, no model fit, no frozen score, no primary gene, no primary predictor and no external application update.

## Claim ceiling

Admission is not evidence that a program is measurable on both platforms, that promoter probes exist, that ranks transport, that checkpoint genes correspond to an approved label, or that epigenetic priming plus immunotherapy is clinically applicable. A later freeze requires pinned source bytes, canonical identifiers, coverage, signs or weights, missing-member rules, scoring, predictor status, population, multiplicity and a signed outcome-access lock.
