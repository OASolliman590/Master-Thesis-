# Group B implementation report

Scope: DAV-T08 (overlap/exposure), DAV-T09 (synthetic admission) and Prat P01–P08 protocol/checklist. New modules only; no frozen/source/control-output edits or reads, real data, acquisition, network, remote execution, installation, commits or subagents. The historical proposed procedure was read as documentation at `../paper-a-batch-pipeline/specs/source-evidence/2026-10-12-patient-semantics/CONTRACT_AUTHORING_PROCEDURE.md`, alongside the independent review and frozen DAV contracts.

## Outcome and limits

The APIs consume the core packet and preserve all incoming rows. Canonical entity assertions are never changed. Actual source admission, statistical release, analysis readiness and biological execution remain false. `SYNTHETIC_READY` denotes invented software simulation only.

Overlap produces protected transitive components across canonical containment, identical trial/publication IDs, repository-scoped accession aliases and frozen typed edges, including possible/unresolved edges. Cross-namespace raw labels are never equated. Explicit contradictory independence, invalid foreign nodes, malformed schemas and duplicate edge IDs fail. Absent review policy/evidence blocks.

Exposure preserves lineage-specific use. States are `METADATA_ONLY`, `CLINICAL_ONLY`, `RESPONSE_ASSOCIATED`, `UNKNOWN`; known clinical curation is retained separately from molecular association. Every supplied publication family must have explicit coverage. Another lineage or absent use never certifies untouched. `untouched_certified` is always false.

Admission verifies all six sealed upstream stages. Required exact sources cannot silently disappear. `STRUCTURAL_ONLY` sources may support simulation only with full hash/RETRIEVED and sealed current assay coverage for that exact source with measurement suitability PASS. Their canonical source status is unchanged. Frozen named branches have explicit requirement sets; named policies require domain fields and source locators, with reference ownership, endpoint/baseline, classes, freeze order, holdout, pair and compartment checks. Arbitrary PASS/name/hash or arbitrary existing-record/rule dictionaries do not qualify. Unknown requirements block; known contradictions fail. Every study with a supplied exact source receives a schema-valid `cohort_admission_receipt` draft, always `BLOCKED_UNKNOWN`, approved_branches empty, V0–V7 blocked. A study with no supplied source emits `admission_draft_unavailable` rather than inventing a source ID (frozen receipt requires a nonempty source_object_ids list). Parent approved that exception explicitly. Repeated identical drafts are retained once; collisions fail.

Prat validates complete invented bytes from content_hex against actual SHA256 and size, FULL_OBJECT basis, authored version or immutable capture, scoped required inventory, and common sealed basis. It requires the current baseline checklist, two distinct independent first passes sealed before comparison, policy lock before reader work, all assertion/authority/source/rule locators, preserved disagreements and current adjudications retaining both originals. Equal legacy table hashes do not resolve assertion disagreement. Missing second reader/seal/auth reference blocks; present tampering or stale basis fails. Canonical episode bindings supplied in a packet must retain same-person ownership. Narrow public output contains only fixed enums/reasons/hash bindings/false flags, no counts, identifiers, dates, free text or sidecars.

All actual Prat source completeness/custody, authenticated readers, actual independence and scientific adjudication remain `NOT_RUN`; canonical admission stays `BLOCKED_UNKNOWN`. E01–E10 are not closed by protocol simulation. The module checks protocol/reference structure; it does not establish scientific truth of supplied policies or actual human independence. Source-specific scientific policy defaults were not invented.

## Integration contract

All config dictionaries must be present before upstream seals. Dependencies bind equal complete config and normalized source snapshots. APIs are `validate_overlap`, `validate_exposure`, `evaluate_admission`, `review_prat_packet` with `(packet, *, schemas=None)`.

```python
config['overlap'] = {'review_complete': True}
config['exposure'] = {
    'analysis_lineage_id': 'invented-lineage', 'review_complete': True,
    'covered_subjects': [{'subject_type': 'STUDY_FAMILY', 'subject_id': 'f1'}],
    # optional comparator_training_set_ids: [...]
}
config['admission'] = {
    'required_source_object_ids': ['obj1'],
    'admission_version': 'invented-v1',  # optional synthetic draft default
    'branch_policies': {'A_BASELINE_BIO': {
        'baseline': {'policy_version': 'invented-v1', 'source_locators': ['invented']},
        'endpoint': {'policy_version': 'invented-v1', 'source_locators': ['invented'],
                     'endpoint_class': 'ORR'},
    }},
}
```

SOURCE_BINARY endpoint instead requires its explicit source_binary_definition; no relabeling into ORR. Other exact branch requirement names and required domain fields are in immutable `BRANCH_REQUIREMENTS` and `POLICY_FIELDS` module constants. Non-base policy evidence also uses explicit `rule` plus `record_refs:[{table,key,value}]`; references cannot cross study/patient ownership. This is supplied invented policy evidence, never authenticated source approval.

Overlap/exposure require `registries`. Admission requires `registries,endpoints,timing,assays,overlap,exposure`. Propagate actual endpoint and coverage views into packet records before admission, as the connected test does.

Audit rows:

- overlap_component: nodes[{node_type,node_id}], protection (`RELATED`/`POTENTIAL_OR_UNKNOWN`), independence_certified=false.
- exposure_decision: subject_type,subject_id,analysis_lineage_id,state,untouched_certified=false.
- admission_eligibility: study_id,branch_id,eligibility (`SYNTHETIC_READY`/`BLOCKED_UNKNOWN`/`FAIL`), criteria{name:`SUPPORTED`/`UNKNOWN`/`CONTRADICTED`}, actual_source_review=`NOT_RUN`.
- admission_draft_unavailable: study_id,reason=`REQUIRED_SOURCE_MISSING`.
- prat_protocol: software_protocol,actual_source_evidence=`NOT_RUN`,actual_reader_authentication=`NOT_RUN`,canonical_admission=`BLOCKED_UNKNOWN`,legacy_reconstruction_equal,basis_sha256,first_pass_sha256,checklist P01–P08.
- assertion_disagreement: question_id,first_assertion,second_assertion,first_pass_sha256,adjudication,basis_sha256. Private audit only.

Prat configuration: full self-contained invented example is `tests/a_dav_implementation/test_group_b_protocol.py::prat()`. Keys are manifest, required_object_ids, inventory_scope, basis, questions, repeat_policy, policy_locked_order, selection_inputs, comparison_order, readers, adjudications, current_contract_sha256, export_schema_version=`prat-narrow-v1`, extra_artifacts=[]. Basis binds manifest/version/inventory scope/required IDs/branch/schemas/questions/repeat policy/executor/auditor/rule-language. Each reader seal hashes its whole dictionary excluding seal_sha256. Public helper is `public_prat_summary(result)`.

## Focused verification and retained history

Final command (exit 0):

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -p no:cacheprovider tests/a_dav_implementation/test_group_b_protocol.py tests/a_dav_implementation/test_group_b_graph_admission.py
62 passed in 10.21s
```

Final strict typecheck (exit 0):

```text
UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --ignore-missing-imports --follow-imports=silent --explicit-package-bases tools/a_dav/overlap.py tools/a_dav/exposure.py tools/a_dav/admission.py tools/a_dav/prat_review.py
Success: no issues found in 4 source files
```

No full suite was run by this worker. Parent owns full integration, independent review, regression and publication. Tests use real public APIs; most unit upstream fixtures are sealed invented results permitted by the brief, while the structural-source tracer invokes all six actual upstream APIs and propagates their real outputs.

RED logs retain actual failures, all exit 1:

| Log | Exact pytest selection after the common prefix above | Result | Interpretation |
|---|---|---|---|
| group-b-red-01.log | test_group_b_protocol.py | 15 failed | Required modules absent; initial public-API RED. |
| group-b-red-02.log | test_group_b_graph_admission.py | 3 failed, 26 passed | Initial broader graph/admission checks; ordering/reseal fixture mistakes plus A_P2_OUTER_VALIDATION returned FAIL during concurrent active edits (the log does not identify its fixed reason); final current branch parametrization passes. |
| group-b-red-03.log | both B files, two successive -k expressions (last effective: `legacy_questions or scoped_object`) | 2 failed, 47 deselected | Missing current checklist and required inventory checks. |
| group-b-red-04.log | graph_admission, -k `all_families or present_failure or wrong_study` | 3 failed, 29 deselected | Omitted family coverage, known source failure and cross-study policy refs. |
| group-b-red-05.log | protocol, -k `inventory_scope or auth_reference` | 2 failed, 18 deselected | Unbound scope and missing auth-reference distinction. |
| group-b-red-06.log | graph_admission, -k `structural_source` | 1 failed, 32 deselected | Registry prerequisite rejected STRUCTURAL_ONLY; parent-authorized Group A fix. |
| group-b-red-07.log | both B files, -k `canonical_episode_binding or arbitrary_existing` | 2 failed, 53 deselected | Cross-person canonical binding and generic branch-policy shortcut. |
| group-b-red-08.log | graph_admission, -k `structural_source` | 1 failed, 33 deselected | All real upstream APIs ready; admission rejected unchanged STRUCTURAL_ONLY source. |
| group-b-red-09.log | both B files, -k `shared_publication or repository_accession or known_clinical or same_draft or changed_required_inventory` | 5 failed, 55 deselected | Alias protection, clinical-use state, duplicate drafts and inventory sealing. |
| group-b-red-10.log | protocol, -k `missing_second or missing_seal` | 2 failed, 22 deselected | Missing evidence was wrongly FAIL; now BLOCKED_UNKNOWN. |

Retained intermediate files named green are historical attempts, not all passing: green-01 had 1 failed/14 passed (missing locator also created a retained disagreement; assertion corrected to expect both fixed reasons), green-03 had 17 passed, green-04 had 2 failed/30 passed (the test compared canonical row order and accidentally included a prior registry seal when resealing a permutation; corrected to compare complete row content and reseal a fresh dependency packet). Final green supersedes those attempts. Shared SchemaStore reuse reduced repeated schema parsing in tests; public API behavior was unchanged by that fixture optimization.

## Final file SHA256

```text
9d02db5c0453812e9ab0947799f319a9a0b2cc8629394c1bf41206a9b325d6ba  tools/a_dav/overlap.py
b8c7844ec9f2009e8fcb60e12be06356a53864ae50ce80e36e29f4dde68e78fe  tools/a_dav/exposure.py
245f1092d5a51dc0bbccfc929fc4a3e19a3c87c7ffed78aa4abbc1f3a747647a  tools/a_dav/admission.py
# Prat module/test hashes appended below after final missing-evidence distinction.
```

```text
e311611115b5081bf5d61e38cdf286ff50a0fd618470a7344b2418fc32cabed5  tools/a_dav/prat_review.py
646cfe35f388922e4cc354a33bee0891d65bba60b029eef277aad0b2eca6cd82  tests/a_dav_implementation/test_group_b_protocol.py
3451e225b92099cc137f7548b5480eac1527b66b903896ff1a461e011fbf56e5  tests/a_dav_implementation/test_group_b_graph_admission.py
```


## Independent-review fix round 1

Read `docs/validation/A_DAV_IMPLEMENTATION_01/REVIEW_STANDARDS.md` (B findings 2–3) and `REVIEW_SPEC.md` (S5; P07/S7 does not reject legitimate multiple bindings in this module). Reproduced both B defects before edits, including freshly resealed manifests to distinguish missing evidence from stale signatures.

Admission now keeps source and criterion reasons/failure state per study and aggregates them only after computing that study's eligibility. Batch-wide missing-source/config status remains aggregate; known source failures also appear in their owning study. A supported study remains SYNTHETIC_READY in its private simulation audit when another supplied study lacks baseline/outcomes, is non-ICI, or has a known source failure. The overall result still blocks/fails as appropriate. Three regression cases reverse every normalized table and require identical complete results and the independently specified per-study states.

Prat now derives an available-verified authority set only after complete-byte hash/size checks. Every ID in required_object_ids must belong to that set irrespective of its per-object optional flag. Assertions may cite only that set, so a missing/unavailable/uninspected/superseded optional object cannot support an assertion. Fresh common-basis/reader seals never substitute for unavailable bytes. Optional unavailable objects with no assertion reference remain permitted. All actual evidence/authentication/admission flags retain their previous blocked/false states.

RED command (exit 1), log group-b-review-r1-red.log:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -p no:cacheprovider tests/a_dav_implementation/test_group_b_protocol.py tests/a_dav_implementation/test_group_b_graph_admission.py -k 'test_review_'
11 failed, 1 passed, 62 deselected in 3.49s
```

GREEN command (exit 0), log group-b-review-r1-green.log:

```text
PYTHONDONTWRITEBYTECODE=1 /private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -p no:cacheprovider tests/a_dav_implementation/test_group_b_protocol.py tests/a_dav_implementation/test_group_b_graph_admission.py
74 passed in 5.68s
```

Strict mypy (exit 0), log group-b-review-r1-mypy.log:

```text
UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --ignore-missing-imports --follow-imports=silent --explicit-package-bases tools/a_dav/overlap.py tools/a_dav/exposure.py tools/a_dav/admission.py tools/a_dav/prat_review.py
Success: no issues found in 4 source files
```

No full suite, commits, network, source/control-output reads or subagents. Only admission.py, prat_review.py and the two owned B test files changed in this round. Config and public/audit field shapes are unchanged. Round-1 current hashes supersede the earlier hashes for changed files:

```text
9d02db5c0453812e9ab0947799f319a9a0b2cc8629394c1bf41206a9b325d6ba  tools/a_dav/overlap.py
b8c7844ec9f2009e8fcb60e12be06356a53864ae50ce80e36e29f4dde68e78fe  tools/a_dav/exposure.py
0f5e36164a846b80e6e72e5a00b9203dacab8756181527447fbec275380dd093  tools/a_dav/admission.py
28938f74b953920823f784ab781834115cf62d30890499d577f0d2b244b2a181  tools/a_dav/prat_review.py
db2baebe3c893c38ad5f82b8ba2a3e9619e25442814f61cb3958e9fd94af58b1  tests/a_dav_implementation/test_group_b_protocol.py
d56405e72084c8bd6c6ae50ad40ca863e138ab35feb5f57fe391c8e49376cff6  tests/a_dav_implementation/test_group_b_graph_admission.py
```
