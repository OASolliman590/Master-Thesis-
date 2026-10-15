# Released-foundation interface

Require a `core_release.json` validated against the v2 schema and accompanied by:

| Artifact | Required content | Verification |
|---|---|---|
| Model manifest | Structure IDs/equations, parameter IDs/units/support, assay mappings, contexts and limiting cases | Hash + schema + review receipt |
| Evidence manifest | Original public sources, observation roles, fitted/fixed/prior/hypothesis labels, dependencies/overlap | Data lineage and immutable IDs |
| Uncertainty object | Posterior draws with diagnostics, constrained ensembles or set/profile representation | Type must match claims; no hidden point-estimate substitution |
| Scenario manifest | Dose/events/global horizon/comparison class and primary contrast | Same definitions or explicit adaptation version |
| Executable adapter contract | Inputs/events/contexts/observations, solver version/settings, deterministic fixtures | Clean replay and fresh relevant tests |
| Release/claims receipt | C-SCHEDULING or C-IDENTIFIABILITY, all unvalidated levels, review and E0–E7 completion | Hashes and actual artifact existence, not a boolean alone |

Proposed language-independent interfaces:

```
simulate(context_id, model_id, parameter_state, event_table, observation_request) -> prediction_bundle
observe(prediction_bundle, assay_mapping_version) -> assay_scale_predictions
read_uncertainty(release_id) -> typed_parameter_samples_or_constraint_set
```

The production implementation may use the core's canonical open ODE stack; do not fork a second simulator. No hidden automatic imputation of unsupported experimental conditions. A public-nominal-culture model and a human-systemic model use different context IDs and mappings.

Before comparing measurements, define baseline conditioning, units, reagent/formulation identity, culture/recognition compatibility and which parameters may adapt. A different lead drug requires a new drug module/evidence decision; it is not merely a different concentration input. A different cell model normally requires a new biological context. Core uncertainty is propagated, not discarded.
