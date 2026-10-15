# Scientific-core completion contract

Core completion is a reviewed analysis release, not publication acceptance and not clinical validation. The release must identify its profile and the evidence level of every model output.

## Required in either complete profile

- A named compound, checkpoint axis, biological context, primary contrast and context of use approved for that release.
- Original-study-resolved public numerical exposure evidence, an independently held-out exposure evaluation or a clearly justified external benchmark not used to develop the relevant version, and at least one usable measured biological constraint relevant to the prostate question.
- Runnable E1, E2 and E3 components or their reduced mathematically justified equivalents; QSP/ensemble execution cannot be omitted because original experiments are absent.
- No real input from internal unpublished project experiments. Private project documents may guide governance but are not numeric core evidence. Any empirically influential A–D handoff must meet the public-data/release policy or remain contextual and excluded from calibration.
- Data roles frozen before fitting; original-study/publication-family and prior model-training overlap audited. Development, public evaluation and source reproduction remain distinct.
- An identifiable calibrated subset or an explicit non-identifiability analysis; separate measurement, parameter, structural, transfer and numerical uncertainty.
- Completed baselines, fair schedule accounting, source-to-figure provenance, reproducibility, access/privacy checks and scientific/integrator review.

## C-SCHEDULING additions

Admitted public temporal PD and functional constraints, plus a relevant checkpoint-specific functional constraint or an explicitly justified transferable checkpoint model with its evidence receipt. The admissible set must be nonempty. Report primary contrast bounds with numerical search adequacy, alternative model structures and assumption sensitivity. Calibration of one layer never validates the composite human prediction. Full independent schedule evaluation is **not** assumed; its presence or absence is a separate validation field.

## C-IDENTIFIABILITY additions

A quantitative certificate tied to admitted observations: an algebraic equivalence class, a profile/likelihood region showing unresolved timing, or at least two well-resolved parameterisations/structures consistent with all development constraints that give incompatible schedule conclusions. An arbitrary toy example alone is insufficient. Show which observables break the ambiguity and how uncertainty propagates through all three layers. A certified unbounded/undetermined contrast can be the result; do not replace it with an arbitrary finite range.

Profile selection is made from evidence coverage before ranking results are seen. Failure to obtain a favourable contrast is never a reason to change profiles. Switching after a genuine data-access/identifiability discovery needs a dated amendment and retention of prior runs.

## Explicit non-gates

Local biological data generated, local instrument configured, local reagent received, prospective internal experiment completed, D completed, and biological manuscript accepted are **not** core gates. Core completion must be unchanged when any internal-data directory is removed, altered or denied access.

## Release receipt

Use `schemas_v2/core_release.schema.json`. It records evidence/profile, E0–E7 status, exact artifact hashes, reviewer references, all unvalidated claims and the absence of internal-data dependency. `complete=true` is allowed only after provenance and referenced artifacts are checked by the actual production auditor. The supplied readiness checker evaluates declared contract flags; it does not inspect a server, certify a scientist or validate biology.
