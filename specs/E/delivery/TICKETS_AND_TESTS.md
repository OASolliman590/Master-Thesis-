# E0–E7 bounded implementation packets

**All commands below are target acceptance interfaces, not production tools implemented in this bundle.** Each ticket uses TDD and requires a scientific/data gate before real fitting. Packet completion is not inferred from historical logs.

## E0 — Public source admission and feasibility
**Owned paths:** `tools/e_core/provenance.py; tools/e_core/admission.py; registry/e_core/`.
**Schemas:** source_access, source_object, study, publication_family, observation, parameter_evidence; evidence_profile v2.
**Dependencies:** none.
**Data tracer:** Original S001/S004/V201 object → study family → actual extracted observation → permissible role; no table admitted merely by citation.
**Bounded sub-tickets:** resolve and cache objects; preserve access failures; curate units/denominators; choose evidence profile before ranking.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_public_only.py tests/e_core/test_sources.py tests/e_core/test_units.py tests/e_core/test_roles.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_public_only.py tests/e_core/test_sources.py tests/e_core/test_units.py tests/e_core/test_roles.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** public manifest rejects internal/unknown origins; figure predictions cannot enter observations; duplicate studies/shared controls retained as dependencies; absent numerical biology emits C-INCOMPLETE.
**Failure states:** unknown access, no biological units, mixed analyte, empty public quantitative foundation.
**Reviewers:** data steward + pharmacometric and immunology source reviewers.

## E1 — Lead and upstream reconstruction
**Owned paths:** `tools/e_core/pk.py; registry/e_core/model_assets/`.
**Schemas:** compound, formulation, model_asset, parameter_evidence; evidence_profile v2.
**Dependencies:** E0 decision release.
**Data tracer:** Verified upstream equations/parameter table → explicit missing inputs → open replay/port plan
**Bounded sub-tickets:** compare leads on recoverability not simulation results; recover source equations/assets; select canonical backend; establish exact/partial/new reuse category.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_model_assets.py tests/e_core/test_formulation.py tests/e_core/test_upstream_parity.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_model_assets.py tests/e_core/test_formulation.py tests/e_core/test_upstream_parity.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** unpublished/request-only dependency is blocked or removed transparently; chosen lead has complete identity; no false numerical parity.
**Failure states:** inaccessible required asset, licence conflict, unresolved drug identity.
**Reviewers:** pharmacometric reviewer + software reproducer.

## E2 — Systemic exposure and independent evaluation
**Owned paths:** `tools/e_core/events.py; tools/e_core/pk.py; tests/e_core/`.
**Schemas:** dosing_event, observation, run, validation_receipt.
**Dependencies:** E1 plus admitted independent PK role.
**Data tracer:** Public PK study/dose/history → amount equations → predicted original-analyte scale → independent source error
**Bounded sub-tickets:** implement PK/PBPK and parsimonious comparator; validate amount/event accounting; freeze and evaluate independent exposure object.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_pk_mass_balance.py tests/e_core/test_events.py tests/e_core/test_pk_holdout.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_pk_mass_balance.py tests/e_core/test_events.py tests/e_core/test_pk_holdout.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** amount/concentration and CL/F errors rejected; infusion/time-origin correct; no downstream tumour fit retunes fixed PK; evaluation is original-study independent.
**Failure states:** mass imbalance, missing dose history, unresolvable independence.
**Reviewers:** pharmacometric reviewer + numerical analyst.

## E3 — Public target/priming PD and recovery constraints
**Owned paths:** `tools/e_core/pd.py; tools/e_core/observations.py`.
**Schemas:** observation, assay_result, parameter_evidence, role_assignment.
**Dependencies:** E2 uncertainty interface plus public PD admission.
**Data tracer:** Source exposure/withdrawal and assay → mapped state/likelihood → identifiable rate/amplitude set
**Bounded sub-tickets:** implement minimal direct/delay/turnover candidates; distinguish endpoints from trajectories; profile recovery and remove unsupported hidden states.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_pd_identifiability.py tests/e_core/test_observation_models.py tests/e_core/test_washout.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_pd_identifiability.py tests/e_core/test_observation_models.py tests/e_core/test_washout.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** single endpoint cannot silently release unique recovery; carryover distinguished; qPCR/flow/WB scales not absolute counts; adverse response allowed.
**Failure states:** unidentified parameter presented as measured, unsupported context transfer.
**Reviewers:** PD modeller + assay expert/statistician.

## E4 — Reduced QSP and functional constraints
**Owned paths:** `tools/e_core/qsp.py; tools/e_core/observations.py`.
**Schemas:** observation, model_asset, parameter_evidence, scenario.
**Dependencies:** E3 interface plus public biological constraints.
**Data tracer:** Qualified published target-specific/antibody endpoint → minimal killing terms → context-specific constraint set
**Bounded sub-tickets:** implement tumour/immune/direct-toxicity separation and checkpoint observer; test unsupported mechanisms as hypotheses, not measurements.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_qsp_limits.py tests/e_core/test_checkpoint.py tests/e_core/test_contexts.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_qsp_limits.py tests/e_core/test_checkpoint.py tests/e_core/test_contexts.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** no immune cells means no immune killing; no blockade term from unqualified assay; no lymph-node culture trafficking; positivity/event limits hold.
**Failure states:** mixed viability interpreted as tumour killing, incompatible assay/context, duplicated binding clearance.
**Reviewers:** immunologist + numerical modeller.

## E5 — Public holdouts and prediction identifiability
**Owned paths:** `tools/e_core/inference.py; tools/e_core/release.py`.
**Schemas:** role_assignment, validation_receipt, run; core_release v2.
**Dependencies:** E2–E4 relevant models/data, predeclared primary.
**Data tracer:** Public holdout observation or evidence equivalence class → frozen predictions/profiles → metric or certificate
**Bounded sub-tickets:** run fair baselines; assess structural/practical and contrast identifiability; independently evaluate available layers; freeze selected profile.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_independent_groups.py tests/e_core/test_contrast_profile.py tests/e_core/test_validation_isolation.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_independent_groups.py tests/e_core/test_contrast_profile.py tests/e_core/test_validation_isolation.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** mutating held-out outcomes leaves development unchanged; unknown training overlap is not independent; counterexamples fit actual constraints; no claimed proof from failed optimiser.
**Failure states:** leakage, post-outcome endpoint switch, unjustified finite bounds.
**Reviewers:** statistician + independent model reviewer.

## E6 — Ensembles, fixed schedules and robustness
**Owned paths:** `tools/e_core/ensembles.py; tools/e_core/scenarios.py`.
**Schemas:** population, vpop_target, scenario, dosing_event, run; evidence_profile v2.
**Dependencies:** E5 accepted uncertainty/contrast contract; no local data dependency.
**Data tracer:** Public constraint/target → set or weighted ensemble → paired events → primary contrast/uncertainty
**Bounded sub-tickets:** generate correctly typed ensemble; compare fixed primary and secondary schedules; optional optimisation held out from ensemble/structure checks.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_ensemble_types.py tests/e_core/test_schedule_fairness.py tests/e_core/test_weights.py tests/e_core/test_structure_sensitivity.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_ensemble_types.py tests/e_core/test_schedule_fairness.py tests/e_core/test_weights.py tests/e_core/test_structure_sensitivity.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** ESS and correlations reported; ensemble frequency not patient probability; equal amount not automatically equal AUC; no advantage from hidden lead-in/horizon; sampled extrema labelled.
**Failure states:** unjustified weights/prevalence, dose imbalance, empty feasible set, false global robustness.
**Reviewers:** statistician + pharmacologist.

## E7 — Reproduction, manuscript and foundation release
**Owned paths:** `tools/e_core/release.py; releases/e_core/; E figures/tables`.
**Schemas:** run, handoff, validation_receipt; core_release v2.
**Dependencies:** All core E0–E6 gates and selected complete profile.
**Data tracer:** Every figure/claim → run hash → public observation/constraint → original study and actual N
**Bounded sub-tickets:** replay clean environment; audit claims/privacy/rights; create evidence-linked figures; publish immutable foundation with no internal dependencies.

- [ ] Write the named failing tests for the acceptance behaviours below.
- [ ] Run `python -m pytest tests/e_core/test_core_without_extension.py tests/e_core/test_release_integrity.py tests/e_core/test_figures.py tests/e_core/test_resume.py -q`; confirm failure is the missing intended behaviour, not a broken test import.
- [ ] Implement only this packet’s reviewed interfaces and minimum necessary behaviour.
- [ ] Run `python -m pytest tests/e_core/test_core_without_extension.py tests/e_core/test_release_integrity.py tests/e_core/test_figures.py tests/e_core/test_resume.py -q` and the affected regression; retain commands, input hashes, passes/failures/skips.
- [ ] Produce a packet receipt and request the named review; the integrator owns any commit/push.

**Acceptance assertions:** whole core works with E_LAST/internal storage absent; referenced hashes verified; only completed levels certified; final package declares unvalidated functions and human limits.
**Failure states:** missing evidence, restricted leakage, generic source list called completed paper, unreviewed science.
**Reviewers:** integrator + independent reproducer + scientific lead.
