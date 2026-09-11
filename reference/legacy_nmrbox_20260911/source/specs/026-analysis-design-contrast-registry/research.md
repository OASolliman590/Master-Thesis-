# Research: Spec 026 — Analysis Design Contrast Registry

## Decision 1: Design layer before execution

The study design is no longer inferred from router tracks. A new `design build` command materializes analysis intent first, and execution stages consume the resulting `analysis_id` records incrementally.

## Decision 2: Co-equal families with distinct interpretation

The thesis may inspect all analysis axes as co-equal discovery families. Scientific labels still prevent over-claiming:

- PRE is predictive baseline biology.
- ON is early pharmacodynamic biology.
- POST is a post-treatment response-state association.
- DELTA is paired treatment-induced change.
- Drug/cancer/pan-ICB families are moderator or discovery views.

## Decision 3: Timing and pairing are hard boundaries

PRE, ON, and POST response contrasts are separate cross-sectional analyses. DELTA requires paired pre plus after-treatment samples and is split into pre-to-on and pre-to-post candidates where possible.

## Decision 4: Preserve raw labels

Collapsed drug and cancer groups are necessary for feasible analysis, but raw `therapy_class`, `therapy_agent`, and `cancer_type` remain in every design output so downstream tables can explain exactly what was pooled.

## Decision 5: ICI combinations are explicit

Any ICI-containing combination regimen is represented as both `DRUG_STRATIFIED_RESPONSE__*__ICI_COMBINATION` and the dedicated `ICI_COMBINATION_RESPONSE` family. The dedicated family makes the thesis question visible without hiding it inside the generic drug-stratified catalogue.

## Decision 6: Blocked rows are scientific metadata

An infeasible analysis is a result of the study design audit, not an invisible absence. Registry rows therefore carry `feasibility_status=blocked` and `blocker_reason`.
