# Final corrective wave — F1–F4

Scope: shared DAV synthetic software only. Read `REVIEW_FINAL.md`, AGENTS/CONTEXT, execution progress, the frozen implementation plan, admission/matrix/relational/multi-omics contracts and prior Group A/C correction reports. Used the TDD skill at the already authorized public packet/result seams. No frozen specification, prior source file, preserved old runtime module, real/private/cached-source data, biology, network, install, remote execution, subagent or commit was changed/executed. Parent owns integration and acceptance.

## Changes and interfaces

### F1 — admission reconciles structured policy with canonical evidence

`admission._criterion` now receives the validated dependency graph and configuration so declarations can be compared with the sealed timing/assay/exposure/overlap audits. It checks current-lineage exposure for `lineage_no_training`; the untouched policy also retains prior-lineage exposure. Scoped patient/family/specimen/assay-source ledger rows are reconciled, rather than trusting any existing reference. Known response-associated exposure cannot support the no-training assertion. Evidence for another lineage cannot certify the current lineage.

Patient links resolve exact scoped specimens and verified patient identity. Same-specimen assertions compare actual specimen identities. Same-time assertions compare exact sealed relative days in a common explicitly evidenced episode; multiple possible contexts require an explicit episode. Paired-window policies reconcile the selected pre/follow-up contexts, timing categories, chronology and exact sealed window. No global specimen category overwrites an alternate evidenced episode context.

Modality gates resolve exact assay IDs, match their declared modalities and specimen selectors, and require each selected assay's sealed measurement gate. RNA vocabulary aliases remain one modality family; RNA/RNA_SEQ cannot masquerade as two modalities. A fully connected same-specimen RNA/methylation invented case succeeds using actual stage functions and complete invented source bytes.

Analogous machine-readable checks cover mapping versions, feature coverage, allowed assay unit/platform and compartment declarations, scoped specimen/episode/endpoint selectors, timing-policy versions, explicit comparative-arm assignments, independent-family references/known overlap and development-selection contradictions. The generic fields-plus-existing-reference fallback no longer returns SUPPORTED for unimplemented external model/contrast/clinical judgments; those remain UNKNOWN. All canonical admission drafts stay BLOCKED_UNKNOWN with no approved branches.

### F2 — eligibility precedes outcome-blind ranking

`matrices._candidates` excludes explicit baseline status NO, blocks unresolved baseline status, and enforces the named A_BASELINE_BIO/A_P2 tumour rule before rank selection. Other branches need an explicit `config.<matrix_stage>.baseline_compartments` policy; there is no global inferred compartment default. Rejection reasons (`BASELINE_INELIGIBLE`, `BASELINE_ELIGIBILITY_UNKNOWN`, `COMPARTMENT_INELIGIBLE`, `SPECIMEN_POLICY_UNKNOWN`) survive in candidate audit. The same filter supplies both baseline rows and the pre side of longitudinal pairs. Existing episode-specific timing keys and legitimate repeated contexts are preserved.

Connected independent NO and BLOOD mutations select the valid alternate specimen under both record orders. A direct unknown-branch policy test blocks until an explicit compartment policy is supplied.

### F3 — per-patient split and exposure materialization

Workflow order is now admission → split → baseline/longitudinal → public report. Matrix preparation requires validated `split` and `exposure` dependencies. Global `config.baseline.split_role` and `prior_exposure_status` are no longer authoritative inputs; the demo's old illustrative labels may remain but are ignored for materialization.

`exposure.patient_exposure_state(records, audit, patient, lineage)` is a shared metadata reconciliation helper. A string lineage restricts a no-training check to that lineage; None retains all applicable prior ledgers. Scope follows patient ID, family, that patient's specimens and their assay source objects. Response-associated use dominates a metadata label; clinical-only and unknown states remain distinct.

`validate_split` retains validated permanent assignments and emits a `PATIENT_LEDGER` audit per patient. Non-final split exposure states derive from the ledgers (clinical-only is UNKNOWN in the narrower split schema); final-test adjudication remains subject to all existing strict checks. Matrix role/exposure columns derive from the sealed assignment and per-patient audit. EXCLUDED roles cannot materialize included baseline or pair rows. Mixed patients in one family can retain DEVELOPMENT/EXCLUDED and different patient-specific exposure states without a global-label overwrite. All actual-untouched flags remain false.

### F4 — dependency lineage and actual runtime closure

Core defines the static `UPSTREAMS` DAG. Each receipt adds `bindings.upstream_receipt_ids` containing only present direct prerequisites, never incidental self/future receipts in a resume packet. Actual stage entry points continue to enforce mandatory dependencies; finish-sealed invented upstream fixtures remain possible for isolated unit boundaries. A registries invocation supplied with an existing-seams receipt now validates it before use.

`dependency` recursively verifies prerequisite receipt identities, code/config/schema/entity/output seals and current graph membership, with cycle protection and per-call memoization. Missing ancestors remain DEPENDENCY_MISSING/BLOCKED_UNKNOWN; replaced/stale identities fail DEPENDENCY_INVALID. Refreshing endpoints with identical endpoint rows but a changed code hash now forces admission/split/matrix/report descendants to rebuild. Full affected rebuild then freezes successfully.

Each receipt also adds `bindings.runtime_sha256`, an exact static filename/hash manifest. Pure stages bind their own module and core. Existing seams additionally bind preserved `__init__.py`, `search_log.py`, `study_resolution.py`, and `object_verification.py`. Workflow/freeze bind the full new runtime, those preserved modules and demo.py. `verify_result` requires the exact current manifest; bundle verification recursively checks the graph and runtime. This is change detection, never authentication. Workflow results seal the graph actually executed, including on safe failure. Malformed dependency values still produce sealed, verifiable failures without echoing input.

## Test fixture maintenance

`test_group_c.seal` now builds invented receipts in DAG order, creates explicit frozen split fixtures and patient-ledger audits, and rebuilds affected synthetic descendants after a test deliberately replaces an upstream audit. It does not reseal intentional stale/tamper tests. Existing leakage, adjudication, unknown timing, multi-context, source coverage, privacy and freeze negative assertions remain meaningful and passed.

Changed product modules: core.py, registries.py, admission.py, exposure.py, matrices.py, release.py, workflow.py. Changed tests: test_core.py, test_group_c.py, test_workflow.py. All other new modules and the four preserved runtime files were left unedited.

## Commands and evidence

All pytest commands ran from the isolated worktree using this exact prefix:

```text
/private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -q -p no:cacheprovider
```

All log paths below are relative to `.superpowers/implement/2026-10-23-dav-all/`. Original RED and failed-attempt logs are preserved.

| Log | Test selection after prefix | Result |
|---|---|---|
| final-fix-F1-red.log | test_workflow.py -k 'outer_validation_reconciles or multiomics_reconciles' | 2 failed: both false eligibility repros |
| final-fix-F1-green.log | same selection | 2 passed |
| final-fix-F2-red.log | test_workflow.py -k baseline_rejects | 1 failed: ineligible specimen selected |
| final-fix-F2-green.log | same selection | 1 passed, independently checks NO and BLOOD plus permutations |
| final-fix-F3-red.log | test_workflow.py -k 'materialized_roles or mixed_patient' | 2 failed: global roles overwrite patient assignments |
| final-fix-F3-green.log | same selection | 2 passed, role/exposure derivation |
| final-fix-F4-red.log | test_workflow.py -k 'refreshing_same or legacy_runtime' | 2 failed; ancestor-refresh RED is valid, second freeze case was contaminated by a concurrent live code edit and is not used as runtime-closure RED evidence |
| final-fix-F4-runtime-red-isolated.log | isolated software copy, pre-final core snapshot, test_workflow.py -k legacy_runtime | 1 failed at expected missing code-hash rejection after successful freeze; definitive runtime-closure RED |
| final-fix-F4-green-attempt1.log | test_workflow.py -k 'refreshing_same or legacy_runtime' | 2 passed, stale descendants and legacy/demo changes detected |
| final-fix-F1-compatible.log | test_workflow.py -k 'compatible_same or external_policy' | 2 passed, real-stage compatible multi-omics and unknown external policy |
| final-fix-F1-window-red.log | test_workflow.py -k window_policy_cannot | 1 failed: known window contradiction was UNKNOWN |
| final-fix-metadata-green.log | test_workflow.py -k 'window_policy_cannot or mixed_patient or compatible_same or external_policy' | 4 passed |
| final-fix-group-c-attempt1.log | test_group_c.py | 40 passed, 1 failed: missing-ancestor diagnostic precedence; fixed missing to preserve DEPENDENCY_MISSING/BLOCKED_UNKNOWN |
| final-fix-affected-final.log | test_core.py test_group_b_graph_admission.py test_group_c.py test_workflow.py test_existing_seams.py | 116 passed in 214.73s; affected files only, not the complete seven-file synthetic suite |
| final-fix-F1-modality-alias-red.log | test_workflow.py -k compatible_same | 1 failed: RNA/RNA_SEQ was incorrectly treated as two modalities |
| final-fix-F1-final-green.log | test_workflow.py -k 'outer_validation_reconciles or multiomics_reconciles or compatible_same or external_policy or window_policy_cannot' | 5 passed, 11 deselected in 30.37s |

Each test filename above is under `tests/a_dav_implementation/`. The isolated runtime-closure RED copied only local Python runtime files, frozen schemas and the new test file into a temporary software directory, then replaced the copied core with `pre-final-fix/core.py.snapshot`; no preserved runtime or source data was edited.

The 116-test run preceded only the final admission modality-alias guard and typing-only variable rename. The final five selected F1 tests verify those last edits; parent owns the next complete integration run. Group A and Prat protocol full files were not rerun here.

Strict offline typecheck:

```text
UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --explicit-package-bases --ignore-missing-imports --follow-imports=silent tools/a_dav/core.py tools/a_dav/admission.py tools/a_dav/exposure.py tools/a_dav/matrices.py tools/a_dav/release.py tools/a_dav/workflow.py tools/a_dav/registries.py
```

`final-fix-mypy-attempt1.log` and `final-fix-mypy-final.log` retain earlier type failures (narrowing and local variable-name collisions). `final-fix-mypy-green.log`: **Success: no issues found in 7 source files**.

## Current hashes and remaining boundaries

Exact SHA-256 values for all fourteen new modules, four preserved runtime files and three changed tests are in `final-fix-hashes.json`; changed-file values are also listed below. No actual source admission, authenticated independent review, target-environment acceptance or scientific/statistical acceptance was performed. All four actual flags remain false, canonical admission/build drafts blocked, and release drafts READY_FOR_REVIEW with actual gates NOT_RUN. No known unresolved F1–F4 software reproduction remains; final independent re-review and parent integration are pending.

- `tools/a_dav/core.py`: `0bef3e9fe31bc8a962caa312f7dda4e4ebfe84d647c251498791097ec8e37642`
- `tools/a_dav/registries.py`: `ca0aa09d28c121a7a2c5b48338ecb803739b744f82dfd07160d4cf62821dd103`
- `tools/a_dav/exposure.py`: `5c94d89cb48d698162d0a3dede02a112b4c007240f5c9acb3aaeb973c2847f0f`
- `tools/a_dav/admission.py`: `ae57181dd1ced267e34f6d0728e9056dd9a4191afede2d3a08db460ff1c2b1a8`
- `tools/a_dav/matrices.py`: `81fe81908d9b7e8f8207a9e9771341b7b9d74d257013fab36d0e43f9b674bd5e`
- `tools/a_dav/release.py`: `2dbd66eb25dbbf155f380d2f70b77fbab391c90db49c2e94e0b92191fcb826de`
- `tools/a_dav/workflow.py`: `8f6ae141f8b46336f54218b4e4b380da16fc26c0dd2b06acd4c6d26f2a248cb0`
- `tests/a_dav_implementation/test_core.py`: `7f8cb6cca5cd13f22db52939d065c337bf174416cb99424693c3febc201682a9`
- `tests/a_dav_implementation/test_group_c.py`: `8a9804c34b20aaaa69ba37dbb6109022136139fa601a94a278e5866b9cd4bbfc`
- `tests/a_dav_implementation/test_workflow.py`: `d6d8bf383c65fb5315792d28fff7f53111cb37f625dd426fe8a150ac00ccf974`
