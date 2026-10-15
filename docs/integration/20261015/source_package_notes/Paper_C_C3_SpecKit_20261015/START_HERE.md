# Paper C C3 Specification Kit

**Package date:** 15 October 2026  
**Repository:** `OASolliman590/Master-Thesis-`  
**Source branch:** `review/paper-c-scientific-revision-20261015`  
**Source commit:** `9f9bece797d904cd59f8a1c285f809e892040086`  
**Draft pull request:** `#10`

## Approved framework

- C3 is the Paper C evidence-based experimental-prioritisation framework.
- A bounded C2 perturbation screen is the discovery engine.
- The C1 decitabine/entinostat/tazemetostat common-condition anchor is secondary calibration.
- The paired independent-measured `Q_M` versus `Q_E` endpoint is the proposed primary.

## Reading order

1. `docs/decisions/C_FRAMEWORK_20261015.md`
2. `docs/research/C_SCIENTIFIC_REVISION_20261015.md`
3. `specs/C/revision_20261015/README.md`
4. `specs/C/revision_20261015/ANALYSIS_CONTRACT.md`
5. `specs/C/revision_20261015/QUERY_HANDOFF.md`
6. `specs/C/revision_20261015/DATA_SOURCE_CONTRACT.md`
7. `specs/C/revision_20261015/SCORER_CONTRACT.md`
8. `specs/C/revision_20261015/VALIDATION_ARCHITECTURE.md`
9. `specs/C/revision_20261015/SOFTWARE_ARCHITECTURE.md`
10. `specs/C/revision_20261015/tickets/IMPLEMENTATION_TICKETS.md`

## Primary endpoint status

The paired endpoint is scientifically proposed but is not yet released for biological execution. It remains gated by the frozen B-to-C handoff, source admission, query fairness and coverage, source-specific contrast freeze, scorer parity, and a later explicit analysis release.

## Verification boundary

The included validation audit reports 10 specification/schema tests passed. That validates internal contract consistency only; it does not establish biological validity, candidate superiority, immune restoration, ICI sensitisation or clinical benefit.
