# Integrated A/A1 Spec Kit review record — 15 October 2026

## Review scope and evidence

This is the accountable integrator's specification review, not an independent scientific/clinical review. The uploaded decision handoff is applied without reopening the six architectural choices. The live acquisition head 58ac943acbe8c981c7c8c269103c602b4425bd50 and draft PR #9 were inspected; its completed downloadable export was retrieved and its SHA-256 matched 17b987192b2ea8ac080ae748bcb58618c1a181efb9a88d672756a4b8b12fa169. The earlier staged e477c680 snapshot is historical. No real patient population, legacy analysis or AIU job was executed here.

## Material corrections from the appraisal

A-P1 is CYT-led, not learned-score-led. A1 is an active full workstream, not operationally deferred 'thesis-only' work. It is planned for prespecification rather than already preregistered. Missing independent A-P2 test data blocks that claim only. Equal cancer/equal study weighting remains selected. Protocol discussion is drafted, not institutionally accepted. An explicit shared episode-binding extension addresses the absent episode field in inherited outcome/exposure schemas without duplicating the normalized store.

## Reconciliation of existing work

The entire original A tree and original DAV tree are retained by exact Git tree references in reference/specs_A_before_20261015 and reference/specs_A_DAV_before_20261015. Current A entry points route to new populated contracts. DAV normalized schemas/tickets/crosswalk/reconciliation are inherited, with a dated additive interface amendment. PR #6's biological/longitudinal ambitions are incorporated only where compatible; its existence does not authorize a second manuscript, generic POST pooling or treatment NMA. PR #9 is inherited by ancestry, not automatically merged. No issue is closed.

## Scientific consistency review

A-BIO effects are separate from predictor coefficients and can survive a null A-P2. Fixed-score A-P1 holds score/patients constant and includes category-composition algebra. A-P2 bootstrap keeps both scores paired and the finite roster/weights fixed, with conditional uncertainty distinguished from retraining/new-study uncertainty. A1 tests the interaction directly and rejects the patient-fixed-effect/response-main-effect rank alias. Incompatible effect scales and treatment/endpoint windows are not silently pooled. COMBAT's BAT-before-nivolumab interval and untreated PRAD claim limits are explicit. Optional modalities/moderators/publication gates do not create global deadlocks.

## Verification ceiling

The package's actual executed verification is recorded in docs/validation/A_A1_SPEC_KIT_20261015/ after the tests run. Structural/schema/synthetic algebra checks are not application implementation, source admission, real biological validation or external scientific review. Numerical settings, source objects/patients/paired N, precise windows, comparator code/weights/licences, historical three-way runtime tests, environment and final-test lineage remain gates.

## Draft PR review requirements

Review canonical files rather than only this memo. Confirm schema references, branch-specific state logic, historical preservation, no private data, exact statistical estimands, no premature numeric freeze and a bounded Codex packet. Retain draft status and no automatic merge. Do not close #1/#7 or claim #6/#9 acceptance criteria completed by copying documents. Independent statistical/source-specific review remains required before production execution.
