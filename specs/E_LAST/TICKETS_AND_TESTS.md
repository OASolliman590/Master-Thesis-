# E_LAST implementation packets — only after core release

These are future production targets. X2 calibration, X3 retrospective evaluation and X4 prospective testing are role-specific branches; none can be relabelled another. X4 may follow the unchanged foundation directly if its context/assay mapping qualifies.

## X0 — Foundation and data admission
Owned paths: `tools/e_last/admission.py; registry/e_last/`.
Schemas: core_release; capability_snapshot; observation/event/experiment compatibility schemas.
Depends on: completed E0–E7 + integrator release.
Tracer: actual original raw object → permissions/QC/identity/unit group → capability snapshot.

- [ ] Write failing tests for each assertion below.
- [ ] Run `python -m pytest tests/e_last/test_activation.py tests/e_last/test_permissions.py tests/e_last/test_identity.py -q` and verify expected missing-behaviour failures.
- [ ] Implement one authorised adapter/module using the canonical core simulator.
- [ ] Run `python -m pytest tests/e_last/test_activation.py tests/e_last/test_permissions.py tests/e_last/test_identity.py -q` and core noninterference regression; record all passes/failures/skips.
- [ ] Produce versioned packet and data-role receipts; integrator reviews before any commit.

Acceptance: missing data defers only E_LAST; incomplete foundation blocks activation; unknown/failed QC cannot admit data.
Failure: missing foundation/data/permission/QC/identity/context/role or invalid prediction independence stops the affected branch; it does not invalidate core completion.
Review: data steward + integrator.

## X1 — Assay/context adapter and module selection
Owned paths: `tools/e_last/mapping.py; configs/e_last/`.
Schemas: capability_snapshot; assay_result; parameter_evidence.
Depends on: X0 authorised data.
Tracer: qualified assay with known scale → state mapping → enabled modules.

- [ ] Write failing tests for each assertion below.
- [ ] Run `python -m pytest tests/e_last/test_capabilities.py tests/e_last/test_context_adapter.py tests/e_last/test_mixed_signal.py -q` and verify expected missing-behaviour failures.
- [ ] Implement one authorised adapter/module using the canonical core simulator.
- [ ] Run `python -m pytest tests/e_last/test_capabilities.py tests/e_last/test_context_adapter.py tests/e_last/test_mixed_signal.py -q` and core noninterference regression; record all passes/failures/skips.
- [ ] Produce versioned packet and data-role receipts; integrator reviews before any commit.

Acceptance: single endpoint cannot enable recovery; different drug blocks direct validation; general killing cannot imply checkpoint function.
Failure: missing foundation/data/permission/QC/identity/context/role or invalid prediction independence stops the affected branch; it does not invalidate core completion.
Review: assay expert + immunology reviewer.

## X2 — Original-data calibration of a new version
Owned paths: `tools/e_last/calibrate.py; runs/e_last/`.
Schemas: role_assignment; run; parameter_evidence; extension_activation.
Depends on: X1 + explicit calibration role and parameter decision.
Tracer: admitted independent experiments → likelihood → new-version uncertainty.

- [ ] Write failing tests for each assertion below.
- [ ] Run `python -m pytest tests/e_last/test_biological_units.py tests/e_last/test_fit_roles.py tests/e_last/test_frozen_core.py -q` and verify expected missing-behaviour failures.
- [ ] Implement one authorised adapter/module using the canonical core simulator.
- [ ] Run `python -m pytest tests/e_last/test_biological_units.py tests/e_last/test_fit_roles.py tests/e_last/test_frozen_core.py -q` and core noninterference regression; record all passes/failures/skips.
- [ ] Produce versioned packet and data-role receipts; integrator reviews before any commit.

Acceptance: wells/timepoints not treated as donors; original core hashes unchanged; unknown variance not invented.
Failure: missing foundation/data/permission/QC/identity/context/role or invalid prediction independence stops the affected branch; it does not invalidate core completion.
Review: statistician + pharmacometric reviewer.

## X3 — Independent retrospective comparison
Owned paths: `tools/e_last/evaluate.py`.
Schemas: role_assignment; validation_receipt; run.
Depends on: X1 plus genuinely unused independent retrospective role.
Tracer: frozen pre-evaluation model → unused observations → assay-scale error.

- [ ] Write failing tests for each assertion below.
- [ ] Run `python -m pytest tests/e_last/test_retrospective.py tests/e_last/test_holdout_isolation.py -q` and verify expected missing-behaviour failures.
- [ ] Implement one authorised adapter/module using the canonical core simulator.
- [ ] Run `python -m pytest tests/e_last/test_retrospective.py tests/e_last/test_holdout_isolation.py -q` and core noninterference regression; record all passes/failures/skips.
- [ ] Produce versioned packet and data-role receipts; integrator reviews before any commit.

Acceptance: past outcomes cannot be renamed prospective; test mutations do not change development; control/donor overlap handled.
Failure: missing foundation/data/permission/QC/identity/context/role or invalid prediction independence stops the affected branch; it does not invalidate core completion.
Review: independent model reviewer.

## X4 — Prospective freeze and challenge
Owned paths: `tools/e_last/predict.py; tools/e_last/evaluate.py`.
Schemas: prospective_prediction; capability_snapshot; validation_receipt.
Depends on: X1/X2 as selected + independent future design + pre-outcome freeze.
Tracer: signed/versioned prediction artifact → future experiment → QC → locked metric.

- [ ] Write failing tests for each assertion below.
- [ ] Run `python -m pytest tests/e_last/test_prediction_receipt.py tests/e_last/test_prospective_order.py tests/e_last/test_prediction_failure.py -q` and verify expected missing-behaviour failures.
- [ ] Implement one authorised adapter/module using the canonical core simulator.
- [ ] Run `python -m pytest tests/e_last/test_prediction_receipt.py tests/e_last/test_prospective_order.py tests/e_last/test_prediction_failure.py -q` and core noninterference regression; record all passes/failures/skips.
- [ ] Produce versioned packet and data-role receipts; integrator reviews before any commit.

Acceptance: changed receipts fail; predictions scored before update; null/adverse signs do not block admission; new update needs new future validation.
Failure: missing foundation/data/permission/QC/identity/context/role or invalid prediction independence stops the affected branch; it does not invalidate core completion.
Review: scientific lead + independent data/time witness.

## X5 — Extension population/claims/release
Owned paths: `tools/e_last/release.py; releases/e_last/`.
Schemas: population; vpop_target; handoff; extension_activation.
Depends on: completed selected X path, not all paths mandatory.
Tracer: enabled branch → actual new evidence/model version → figure/claim receipt.

- [ ] Write failing tests for each assertion below.
- [ ] Run `python -m pytest tests/e_last/test_extension_release.py tests/e_last/test_publication_overlap.py tests/e_last/test_privacy.py -q` and verify expected missing-behaviour failures.
- [ ] Implement one authorised adapter/module using the canonical core simulator.
- [ ] Run `python -m pytest tests/e_last/test_extension_release.py tests/e_last/test_publication_overlap.py tests/e_last/test_privacy.py -q` and core noninterference regression; record all passes/failures/skips.
- [ ] Produce versioned packet and data-role receipts; integrator reviews before any commit.

Acceptance: limited capability clearly labelled; no donor-to-patient relabelling; no duplicated independent experiment; core remains immutable.
Failure: missing foundation/data/permission/QC/identity/context/role or invalid prediction independence stops the affected branch; it does not invalidate core completion.
Review: integrator + scientific lead/data steward.
