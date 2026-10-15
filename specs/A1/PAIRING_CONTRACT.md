# Pair construction and repeated specimens

## Deterministic algorithm

1. Join specimen and assay to patient and source-supported index episode through the shared bindings. Check raw aliases, exact object columns and overlap edges before considering timing.
2. Select an eligible baseline using the outcome-independent source-specific baseline hierarchy. Store all rejected candidates and reasons; do not silently overwrite them.
3. Enumerate follow-ups satisfying the declared contrast/window and exposure components. Reject progression/regimen-change/after-stop specimens from a scheduled on-treatment contrast unless explicitly allowed by that contract.
4. Apply the frozen hierarchy: timing relevance within the window, qualified compartment/assay, prespecified same-lesion preference, then a stable opaque tie-breaker. Record exact day distance and ambiguity. Never select 'last row', maximum response, best assay effect or most favourable score.
5. Preserve all windows for an approved repeated-measures model or one deterministic pair per specified window. Multiple follow-ups cannot overwrite a dictionary value keyed only by patient.
6. Verify patient/episode/endpoint consistency, platform/unit/annotation compatibility, pair quality and protected-set status. Materialize pairs and a missing-follow-up audit with counts and receipts.

## Lesions, assays and technical replicates

Same lesion is preferred only where the source-specific design supports it; a different-lesion pair is not automatically invalid but must be explicitly admitted and labelled, with a same-lesion sensitivity if estimable. Tissue/compartment change is a distinct contrast. Sequencing repeats from the same specimen are technical replicates, not additional timepoints or patients. Combination of counts requires a documented technical-replicate model; otherwise select the qualified assay with a fixed policy. Never average incompatible transformations/platforms.

## Dependency accounting

Shared baseline across two windows induces dependent changes. The analysis must use a patient-aware repeated model or a joint study-level covariance, not treat each pair as independent. A patient exposed to sequential regimens remains one patient; episodes may be modelled jointly only under an explicitly approved nested structure. Cross-publication duplicates are resolved before cohort-level synthesis.

## Required validation

Row permutation must leave the selected pair IDs and output hash unchanged after canonical sorting. Tests cover two follow-ups in one window, equal-day ties, multiple lesions, repeated sequencing, unknown/exact timing contradiction, baseline after a prior drug, regimen switch, absent endpoint, pair crossing patient IDs, mismatched platform and protected final-test patients. Missing pairs stay in the flow as excluded/blocked with reasons. A successful pair parser is not a response-time analysis release.
