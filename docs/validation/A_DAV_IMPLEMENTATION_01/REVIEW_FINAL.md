# Final independent whole-slice review

**Verdict: changes required — four P2 findings; zero P0/P1/P3.** The corrected original findings remain closed within their reviewed scopes. The four findings below are additional software integration defects, not missing external scientific evidence. They prevent an all-ticket synthetic-software completion claim at this snapshot.

Reviewed the 29-file final package against fixed base `9da3b1afaeba04aa9a8a29095c01574e8c87579c`, the current stage implementations and seven test files, reused T01–T03 API boundaries, original and corrective independent reviews, frozen tickets/relational/matrix/admission/reproduction contracts, integrated A/A1 decision and implementation plan. Independently checked every file in `final-review-inputs.json`: all 29 SHA-256 values match. The exact reviewed manifest is `.superpowers/implement/2026-10-23-dav-all/final-review-inputs.json`.

## F1 — P2: structured policy fields can override known contradictory evidence

Location: [admission.py:163](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/admission.py:163), generic `SUPPORTED` return at line 168; branch evaluation consumes this result at line 223.

For several named criteria, presence of required policy fields plus any existing record reference and a nonempty rule is enough for `SUPPORTED`. Their values are not reconciled with the already validated canonical records or dependency audit. This is more than leaving clinical truth to source reviewers: known machine-readable contradictions pass.

Two narrow connected reproductions both returned `SYNTHETIC_READY`, with all named admission criteria `SUPPORTED`:

- Set the invented demo branch to `A_P2_OUTER_VALIDATION`, provide a structured holdout policy for `s1`, and provide `lineage_no_training.analysis_lineage_id='invented-lineage'`. Change the existing exposure to `MODEL_TUNING`, the same lineage and `BLOCKS_UNTOUCHED_FOR_LINEAGE`. The exposure stage correctly retains response-associated use, but admission declares `lineage_no_training=SUPPORTED`.
- Set the demo branch to `PAIRED_MULTIOMICS`; name `sp1` and `sp2` as same-time/same-specimen, and declare modalities RNA/METHYLATION with assay IDs `a1`/`a2`. The actual records describe distinct specimens at days −2 and 10 and two RNA assays. Admission nevertheless declares `same_time_specimen` and `modality_gates` supported.

Required correction: evaluate each mechanically checkable criterion against the scoped normalized records and sealed audits, including current-lineage training exposure, exact referenced assays/modalities and specimen/timing relationships. Unknown external policy may remain `UNKNOWN`; generic record existence must not certify a policy contradicted by available evidence. Add connected negative regressions for both cases and positive cases for genuinely compatible policies. This affects T09 and downstream use of synthetic eligibility. Authority: `COHORT_ADMISSION_AND_RELEASE.md` named branch criteria and `MULTIOMICS_PAIRING_CONTRACT.md` analysis boundaries.

## F2 — P2: baseline ranking includes explicitly ineligible specimens

Location: [matrices.py:118](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/matrices.py:118).

The baseline candidate filter checks episode category/role but ignores `baseline_candidate_status` and biological compartment. Study-level admission only establishes that some suitable tumour baseline exists; it does not establish that the later ranked specimen is that eligible baseline.

Connected reproduction: in the invented demo set `sp1.baseline_candidate_status='NO'` and `sp1.biological_compartment='BLOOD'`. Convert `sp2` to a valid tumour baseline at day −1, with matching binding and timing policy. Keep the original ranks, which prefer `sp1`. The complete workflow returns `SYNTHETIC_READY` and baseline `('sp1','INCLUDED')`. The alternative valid tumour specimen permits admission, but the builder selects the explicitly ineligible blood specimen. This also affects the baseline side of longitudinal pairs because both builders use `_candidates`.

Required correction: enforce explicit candidate eligibility and the branch's compartment/specimen rule before ranking; preserve each rejection in the candidate audit. Do not create a new clinical default for branches whose specimen policy remains unknown. Regress `NO` and non-tumour candidates independently, and verify that the valid alternate candidate wins regardless of row order. Authority: `PATIENT_MATRIX_CONTRACT.md` baseline hierarchy and `COHORT_ADMISSION_AND_RELEASE.md` baseline branch requirements. Tickets T10–T11 remain incomplete until corrected.

## F3 — P2: materialized role and exposure assertions bypass the frozen ledgers

Location: [matrices.py:211](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/matrices.py:211), with missing reconciliation at [release.py:49](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/release.py:49).

Baseline rows copy one global `config.baseline.split_role` and `prior_exposure_status`; split validation later checks assignment integrity without reconciling these materialized assertions. A single patient's authoritative assignment can therefore disagree with the analysis-facing row while every stage and the public report succeeds.

Connected reproduction: change only `config.split.assignments[0].permanent_role` to `EXCLUDED` in the invented demo. Observed workflow `SYNTHETIC_READY`, baseline `split_role='DEVELOPMENT'`, `inclusion_status='INCLUDED'`, and split `permanent_role='EXCLUDED'`. F1's outer-validation reproduction also retains baseline `prior_exposure_status='METADATA_ONLY'` despite its response-associated exposure record.

Required correction: derive materialized role/exposure fields per patient from the applicable validated assignments/ledger decisions, or explicitly reconcile them before report/freeze and fail on contradictions. A study-wide or global config label is insufficient for mixed assignments. The stage order may need to reflect that the baseline contract consumes a frozen split. Add an end-to-end disagreement regression and a valid mixed-patient assignment case. Authority: `matrices/BASELINE_PATIENT_MATRIX.md` frozen split invariant, `PATIENT_MATRIX_CONTRACT.md` matrix flow, and `RELATIONAL_INVARIANTS.md` permanent-role rule. Tickets T10/T12/T14 are affected.

## F4 — P2: refreshed upstream receipts do not invalidate stale descendants

Location: [core.py:214](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/core.py:214), especially lines 219–222.

`dependency` verifies the dependency's own current module/core hash, config and canonical/owned output tables. It does not verify that the dependency consumed the currently supplied upstream receipt identities. `input_sha256` seals an opaque historical input, but that historical dependency graph is not retained or reconciled. Once a changed upstream module is rerun, old downstream results with unchanged own code/config/entities are accepted alongside the new upstream receipt.

Narrow reproduction used actual stage APIs to build the demo through `public_report`. Without editing any file, monkeypatch only the core file-hash reader for `endpoints.py` to simulate a new code version, rerun only `map_endpoints`, and replace the endpoint dependency with that fresh result. The endpoint receipt ID changes. Leave the old admission, baseline, longitudinal, split and report receipts in place. Every check in `FREEZE_DEPENDENCIES` succeeds, and `build_public_report` returns `SYNTHETIC_READY`. Old admission and baseline receipt IDs are unchanged. No forged `finish` output was used. The monkeypatch is an explicitly simulated code-version change, not a real code edit or source-evidence claim.

The same incomplete code-provenance model also omits reused runtime dependencies: `core.py:28` maps `existing_seams` only to `workflow.py`, and `finish` binds that module plus `core.py`. The invoked `search_log.py`, `study_resolution.py` and `object_verification.py` bytes are not bound in the receipt or verified by the freeze manifest; `demo.py`, named by the reproduction command, is likewise absent from the code binding. Static inspection confirms that changing one of these files can leave an old result verifiable even before refreshing any ancestor. This is a companion F4 defect, not a fifth finding. The parent independently raised the same reused-runtime omission. Correct it with an explicit current runtime-code manifest or dependency-code hashes without editing the preserved legacy modules.

Required correction: seal the relevant upstream receipt IDs (and reused runtime code closure where applicable) into each result, then recursively or topologically verify that lineage against the current graph. A rerun of an affected ancestor must force dependent stages to rerun even when the output table happens to be identical. Add a regression that refreshes only the changed ancestor and rejects stale descendants, followed by a successful full affected rebuild. Authority: `REPRODUCE_AND_READINESS.md` resume/rebuild rules and the implementation plan's stale-descendant requirement. Core/T14 completion is blocked by this gap.

## Executed reproduction details

Interpreter: `/private/tmp/thesis-adav05-20261020/bin/python -B`, repository root as CWD. These were five targeted invented scenarios (two for F1, one each for F2–F4), not suite reruns. F1–F3 used `synthetic_workflow_packet()` followed by `run_workflow(packet)` with these mutations:

```python
from copy import deepcopy
from tools.a_dav.demo import synthetic_workflow_packet
from tools.a_dav.workflow import run_workflow

evidence = {
    'policy_version': 'invented-v1', 'source_locators': ['invented'],
    'rule': 'invented metadata rule',
    'record_refs': [{'table': 'patient_registry', 'key': 'patient_uid', 'value': 'p1'}],
}

# F1a: exact-lineage model tuning cannot support no-training.
p = synthetic_workflow_packet()
p['branch_id'] = 'A_P2_OUTER_VALIDATION'
policy = deepcopy(p['config']['admission']['branch_policies']['A_BASELINE_BIO'])
policy['originating_study_holdout'] = {
    **evidence, 'held_out_study_ids': ['s1'], 'training_study_ids': []}
policy['lineage_no_training'] = {**evidence, 'analysis_lineage_id': 'invented-lineage'}
p['config']['admission']['branch_policies'][p['branch_id']] = policy
p['records']['prior_exposure_record'][0].update(
    use='MODEL_TUNING', fields_accessed=['response'],
    independence_implication='BLOCKS_UNTOUCHED_FOR_LINEAGE')
r = run_workflow(p)  # observed SYNTHETIC_READY

# F1b: declarations contradict the actual specimen and assay records.
p = synthetic_workflow_packet()
p['branch_id'] = 'PAIRED_MULTIOMICS'
p['config']['admission']['branch_policies'][p['branch_id']] = {
    'patient_link': {**evidence, 'specimen_uids': ['sp1', 'sp2']},
    'same_time_specimen': {**evidence, 'specimen_uids': ['sp1', 'sp2'],
                          'same_time': True, 'same_specimen': True},
    'modality_gates': {**evidence, 'modalities': ['RNA', 'METHYLATION'],
                      'assay_uids': ['a1', 'a2']},
}
r = run_workflow(p)  # observed SYNTHETIC_READY

# F2: an eligible alternate cannot authorize selection of an ineligible row.
p = synthetic_workflow_packet()
p['records']['specimen_registry'][0].update(
    baseline_candidate_status='NO', biological_compartment='BLOOD')
p['records']['specimen_registry'][1].update(
    canonical_timing_category='PRE_INDEX_BASELINE', collection_date_or_day='-1',
    days_from_index_start=-1, baseline_candidate_status='YES')
for binding in p['records']['episode_binding']:
    if binding['subject_id'] == 'sp2':
        binding['role'] = 'PRE_INDEX_BASELINE'
p['config']['timing']['specimens']['sp2'].update(
    relative_day=-1, canonical_category='PRE_INDEX_BASELINE', window_id='invented-pre')
r = run_workflow(p)  # observed INCLUDED sp1

# F3: one explicit assignment mutation creates incompatible permanent roles.
p = synthetic_workflow_packet()
p['config']['split']['assignments'][0]['permanent_role'] = 'EXCLUDED'
r = run_workflow(p)  # observed SYNTHETIC_READY with baseline DEVELOPMENT
```

F4 executed each function in the workflow's stage order through `build_public_report`, updating `p['records']` and `p['dependencies'][result['stage']]` after each successful invocation. Then:

```python
from tools.a_dav import core
from tools.a_dav.endpoints import map_endpoints
from tools.a_dav.release import FREEZE_DEPENDENCIES
from tools.a_dav.reporting import build_public_report

original = core._file_hash
try:
    core._file_hash = lambda path: 'e' * 64 if path.name == 'endpoints.py' else original(path)
    fresh = map_endpoints(p)
    p['records'] = fresh['records']
    p['dependencies']['endpoints'] = fresh
    for stage in FREEZE_DEPENDENCIES:
        core.dependency(p, stage, core.SchemaStore())  # all incorrectly accepted
    assert build_public_report(p)['status'] == 'SYNTHETIC_READY'
finally:
    core._file_hash = original
```

## Completion and claim limits

The implementation consistently keeps actual readiness/admission/release/analysis flags false and canonical drafts blocked. The original chronology, required-object, study-order, malformed-failure, coverage-consumption, source-binary, adjudication, missing-pair, reporting and specimen-context corrections are present. Public allowlists and the stricter Prat count-free boundary remain appropriate.

T01–T08 and T13 have no additional finding from this final pass; this is bounded review evidence, not a claim that every possible case is proven. T09–T12 and T14 require the corrections above before the complete synthetic slice can be accepted. The parent reports 11 connected/existing-seam tests passed, strict mypy clean for all 14 new modules, and a fresh/resume copied-runtime demonstration; those are parent verification, not independently repeated here. The parent full affected synthetic suite was still running when these findings were prepared.

No full suite, network/install, real/private/cached source fixture read, biological computation, commit, subagent or product edit occurred in this review. Only this report was written. Actual source review, authenticated independent review, target-environment acceptance and scientific/statistical acceptance remain `NOT_RUN`. E01–E10 retain their documented external evidence states; none of F1–F4 may be reclassified as an external-evidence gap.
