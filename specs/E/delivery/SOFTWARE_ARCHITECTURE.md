# Software architecture — one canonical simulator, isolated modes

Core mode `public_core` owns public retrieval/curation, exposure models, public PD, reduced QSP, set/ensemble inference, scenarios and release. Optional mode `experimental_last` consumes a completed version through a typed interface and writes new-version outputs. Core must neither import nor discover E_LAST automatically.

## Proposed owned paths in the thesis repository

```
tools/e_core/{cli,provenance,admission,events,pk,pd,qsp,observations,inference,ensembles,scenarios,release}.py
configs/e_core/              # schema-valid reviewed configs, no numerical defaults for unknowns
schemas/e_core/              # promoted reviewed schemas, version-pinned
registry/e_core/             # public object/study/parameter/role registries
runs/e_core/<run_id>/        # immutable manifests and outputs
releases/e_core/<release_id>/
tests/e_core/
```

These are target paths, not implemented production files in this bundle. Preserve the existing project style where it conflicts; record an integrator-reviewed mapping before coding. Do not restructure A–D to implement E.

Python is the natural integration candidate given the inspected repository scaffolding. The canonical ODE/inference backend must be selected after the upstream asset audit, with an openly executable path. The existing specification evaluates SciPy solve_ivp and OSP-based reconstruction. No new runtime version is asserted selected; pin actual versions/native dependencies and OS support after a reproducible smoke/parity test. A proprietary SimBiology dependency cannot be concealed in an 'open' pipeline. A native OSP source or a public independent ODE port must be classified by actual numerical parity.

## Interfaces

`admit_objects(manifest, policy) -> admitted_observations, exclusion_receipt`
`compile_events(event_table, context) -> ordered_events`
`simulate(model, parameter_state, context, events, observation_grid) -> state_and_observation_bundle`
`fit_or_constrain(observations, role_manifest, model_family) -> typed_uncertainty_state`
`evaluate_contrast(uncertainty_state, paired_schedules) -> sampled_or_certified_contrast_set`
`audit_release(release_manifest) -> level_specific_readiness_receipt`

Use explicit amount/concentration/time/cell units and versioned assay mappings. An unsupported context raises a named error, not a fallback to baseline. Inputs/config/code/environment and random seeds are hashed; cache keys include mode, source role, evidence-set definition, solver settings and structure. Resume revalidates hashes and atomic outputs.

Current executable deliverables are bounded specification/schema QA only (`qa/` and `qa_v2/`). No PK/QSP production module, real fitting, scientific release or AIU test is claimed.
