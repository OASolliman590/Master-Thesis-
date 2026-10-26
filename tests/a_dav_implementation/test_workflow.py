"""Connected invented workflow invokes every real stage API."""
from copy import deepcopy

from tools.a_dav.demo import synthetic_workflow_packet
from tools.a_dav.workflow import run_workflow


def test_connected_workflow_includes_baseline_and_longitudinal_without_admission():
    packet = synthetic_workflow_packet()
    before = deepcopy(packet)
    result = run_workflow(packet)
    assert result['status'] == 'READY', [(x['stage'], x['status'], x['reasons']) for x in result['audit']]
    assert len(result['audit']) == 12
    assert result['records']['baseline'][0]['specimen_uid'] == 'sp1'
    assert result['records']['pair'][0]['followup_specimen_uid'] == 'sp2'
    assert result['records']['pair'][0]['inclusion_status'] == 'INCLUDED'
    assert result['records']['cohort_admission_receipt'][0]['admission_status'] == 'BLOCKED_UNKNOWN'
    assert result['source_admission'] is False
    assert result['biological_analysis_executed'] is False
    assert packet == before


def test_changed_bytes_block_every_downstream_view():
    packet = synthetic_workflow_packet()
    packet['config']['existing_seams']['source_payloads']['obj1'] = b'SYNTHETIC_ONLY\nchanged'.hex()
    result = run_workflow(packet)
    assert result['status'] == 'FAIL'
    assert result['reasons'] == ['SOURCE_BYTES_MISMATCH']
    assert 'baseline' not in result['records']
    assert 'pair' not in result['records']


def test_matrix_must_come_from_the_verified_complete_bytes():
    packet = synthetic_workflow_packet()
    packet['config']['assays']['matrices'][0]['values'][0][0] = 1
    result = run_workflow(packet)
    assert result['status'] == 'FAIL'
    assert result['reasons'] == ['MATRIX_BYTES_MISMATCH']
    assert 'baseline' not in result['records']


def test_missing_followup_stays_in_denominator():
    packet = synthetic_workflow_packet()
    packet['config']['longitudinal']['windows'][0].update(lower_day=11, upper_day=20)
    result = run_workflow(packet)
    assert result['status'] == 'READY'
    assert result['records']['pair'] == []
    stage = next(row for row in result['audit'] if row['stage'] == 'longitudinal')
    assert any(row['kind'] == 'PAIR_DENOMINATOR' and row['reason'] == 'NO_FOLLOWUP_IN_WINDOW'
               and row['patient_uid'] == 'p1' for row in stage['checks'])


def test_connected_freeze_fresh_resume_and_changed_input(tmp_path):
    from tools.a_dav.release import verify_bundle
    packet = synthetic_workflow_packet()
    target = tmp_path / 'invented-release'
    first = run_workflow(packet, target)
    assert first['status'] == 'READY', first['audit']
    assert verify_bundle(target)['statistical_release'] is False
    assert run_workflow(packet, target) == first
    old_bytes = {p.name: p.read_bytes() for p in target.iterdir()}
    changed = deepcopy(packet)
    changed['config']['longitudinal']['windows'][0]['upper_day'] = 19
    assert run_workflow(changed, target)['status'] == 'FAIL'
    assert {p.name: p.read_bytes() for p in target.iterdir()} == old_bytes


def test_connected_record_permutation_and_outcome_blind_selection():
    packet = synthetic_workflow_packet()
    first = run_workflow(packet)
    shuffled = deepcopy(packet)
    for rows in shuffled['records'].values():
        rows.reverse()
    assert run_workflow(shuffled) == first
    changed = deepcopy(packet)
    changed['records']['clinical_outcome'][0].update(raw_endpoint_label='invented-progressive',
        canonical_category='PD', orr_mapping=False, dcr_mapping=False)
    changed['config']['endpoints']['category_map'] = {'invented-progressive': 'PD'}
    result = run_workflow(changed)
    assert result['status'] == 'READY'
    assert result['records']['baseline'][0]['orr'] == 0
    assert result['records']['baseline'][0]['specimen_uid'] == first['records']['baseline'][0]['specimen_uid']
    assert result['records']['pair'][0]['followup_specimen_uid'] == first['records']['pair'][0]['followup_specimen_uid']


def _evidence(**fields):
    return {'policy_version': 'invented-v1', 'source_locators': ['invented'],
            'rule': 'invented metadata rule',
            'record_refs': [{'table': 'patient_registry', 'key': 'patient_uid', 'value': 'p1'}], **fields}


def _admission_checks(result):
    stage = next(row for row in result['audit'] if row['stage'] == 'admission')
    return next(row['criteria'] for row in stage['checks'] if row['kind'] == 'admission_eligibility')


def test_outer_validation_reconciles_current_lineage_training():
    packet = synthetic_workflow_packet()
    packet['branch_id'] = 'A_P2_OUTER_VALIDATION'
    policy = deepcopy(packet['config']['admission']['branch_policies']['A_BASELINE_BIO'])
    policy.update(originating_study_holdout=_evidence(held_out_study_ids=['s1'], training_study_ids=[]),
                  lineage_no_training=_evidence(analysis_lineage_id='invented-lineage'))
    packet['config']['admission']['branch_policies'][packet['branch_id']] = policy
    good = run_workflow(packet)
    assert good['status'] == 'READY', good['audit']
    packet['records']['prior_exposure_record'][0].update(use='MODEL_TUNING', fields_accessed=['response'],
        independence_implication='BLOCKS_UNTOUCHED_FOR_LINEAGE')
    bad = run_workflow(packet)
    assert bad['status'] == 'FAIL'
    assert _admission_checks(bad)['lineage_no_training'] == 'CONTRADICTED'


def test_multiomics_reconciles_exact_specimens_times_and_assays():
    packet = synthetic_workflow_packet()
    packet['branch_id'] = 'PAIRED_MULTIOMICS'
    policy = {'patient_link': _evidence(specimen_uids=['sp1', 'sp2']),
              'same_time_specimen': _evidence(specimen_uids=['sp1', 'sp2'], same_time=True, same_specimen=True),
              'modality_gates': _evidence(modalities=['RNA', 'METHYLATION'], assay_uids=['a1', 'a2'])}
    packet['config']['admission']['branch_policies'][packet['branch_id']] = policy
    bad = run_workflow(packet)
    assert bad['status'] == 'FAIL'
    checks = _admission_checks(bad)
    assert checks['same_time_specimen'] == checks['modality_gates'] == 'CONTRADICTED'
    # Correct declarations preserve the actual different-time relationship; two RNA
    # assays still cannot constitute the named paired multi-omics branch.
    policy['same_time_specimen'].update(same_time=False, same_specimen=False)
    checks = _admission_checks(run_workflow(packet))
    assert checks['same_time_specimen'] == 'SUPPORTED'
    assert checks['modality_gates'] == 'CONTRADICTED'


def test_baseline_rejects_explicit_no_and_wrong_compartment_before_ranking():
    for change, reason in [({'baseline_candidate_status': 'NO'}, 'BASELINE_INELIGIBLE'),
                           ({'biological_compartment': 'BLOOD'}, 'COMPARTMENT_INELIGIBLE')]:
        packet = synthetic_workflow_packet()
        packet['records']['specimen_registry'][0].update(change)
        packet['records']['specimen_registry'][1].update(canonical_timing_category='PRE_INDEX_BASELINE',
            collection_date_or_day='-1', days_from_index_start=-1, baseline_candidate_status='YES')
        for binding in packet['records']['episode_binding']:
            if binding['subject_id'] == 'sp2': binding['role'] = 'PRE_INDEX_BASELINE'
        packet['config']['timing']['specimens']['sp2'].update(relative_day=-1,
            canonical_category='PRE_INDEX_BASELINE', window_id='invented-pre')
        first = run_workflow(packet)
        assert first['status'] == 'READY', first['audit']
        assert first['records']['baseline'][0]['specimen_uid'] == 'sp2'
        baseline = next(row for row in first['audit'] if row['stage'] == 'baseline')
        assert any(row.get('specimen_uid') == 'sp1' and row.get('reason') == reason for row in baseline['checks'])
        for rows in packet['records'].values(): rows.reverse()
        assert run_workflow(packet) == first


def test_materialized_roles_and_exposure_follow_patient_ledgers():
    packet = synthetic_workflow_packet()
    packet['config']['split']['assignments'][0]['permanent_role'] = 'EXCLUDED'
    result = run_workflow(packet)
    assert result['status'] == 'READY', result['audit']
    row = result['records']['baseline'][0]
    assert row['split_role'] == 'EXCLUDED'
    assert row['inclusion_status'] == 'EXCLUDED'
    assert row['exclusion_reason'] == 'PATIENT_EXCLUDED'
    packet = synthetic_workflow_packet()
    packet['records']['prior_exposure_record'][0].update(use='MODEL_TUNING', fields_accessed=['response'],
        independence_implication='BLOCKS_UNTOUCHED_FOR_LINEAGE')
    result = run_workflow(packet)
    assert result['status'] == 'READY', result['audit']
    assert result['records']['baseline'][0]['prior_exposure_status'] == 'RESPONSE_ASSOCIATED'
    assert result['records']['split'][0]['prior_exposure_state'] == 'RESPONSE_ASSOCIATED'


def test_mixed_patient_assignments_materialize_separately():
    packet = synthetic_workflow_packet()
    # A second invented patient shares the family, but is explicitly excluded.
    mapping = {'p1': 'p2', 'sp1': 'sp3', 'sp2': 'sp4', 'a1': 'a3', 'a2': 'a4',
               'e1': 'e2', 'o1': 'o2', 'x1': 'x2', 'bp1': 'bp2', 'bsp1': 'bsp3',
               'bsp2': 'bsp4', 'bo1': 'bo2', 'bx1': 'bx2', 'sample-001': 'sample-003',
               'sample-002': 'sample-004', '001': '002', '0001': '0002'}
    def replace(value):
        if isinstance(value, dict): return {mapping.get(k, k): replace(v) for k, v in value.items()}
        if isinstance(value, list): return [replace(v) for v in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    for table in ('patient_registry', 'specimen_registry', 'assay_registry', 'treatment_episode',
                  'treatment_exposure', 'episode_binding', 'clinical_outcome'):
        packet['records'][table] += replace(deepcopy(packet['records'][table]))
    packet['config']['timing']['episode_order'].append('e2')
    packet['config']['timing']['specimens'].update(replace(deepcopy(packet['config']['timing']['specimens'])))
    packet['config']['endpoints']['source_priority'].append('o2')
    matrix = packet['config']['assays']['matrices'][0]
    matrix['headers'] += ['sample-003', 'sample-004']
    for values in matrix['values']: values += list(values)
    matrix['library_properties'].update(replace(deepcopy(matrix['library_properties'])))
    for stage in ('baseline', 'longitudinal'):
        for key in ('specimen_rank', 'assay_rank'):
            packet['config'][stage][key].update(replace(deepcopy(packet['config'][stage][key])))
    other = replace(deepcopy(packet['config']['split']['assignments'][0]))
    other['permanent_role'] = 'EXCLUDED'
    packet['config']['split']['assignments'].append(other)
    exposure = deepcopy(packet['records']['prior_exposure_record'][0])
    exposure.update(exposure_id='patient-use', subject_type='PATIENT_SET', subject_id='p2',
                    use='MODEL_TUNING', fields_accessed=['response'],
                    independence_implication='BLOCKS_UNTOUCHED_FOR_LINEAGE')
    packet['records']['prior_exposure_record'].append(exposure)
    _refresh_invented_matrix_bytes(packet)
    result = run_workflow(packet)
    assert result['status'] == 'READY', result['audit']
    assert [(r['patient_uid'], r['split_role'], r['inclusion_status']) for r in
            sorted(result['records']['baseline'], key=lambda r: r['patient_uid'])] == [
                ('p1', 'DEVELOPMENT', 'INCLUDED'), ('p2', 'EXCLUDED', 'EXCLUDED')]
    assert {r['patient_uid']: r['prior_exposure_status'] for r in result['records']['baseline']} == {
        'p1': 'METADATA_ONLY', 'p2': 'RESPONSE_ASSOCIATED'}


def _refresh_invented_matrix_bytes(packet):
    import hashlib
    from tools.a_dav.core import canonical_bytes
    from tools.a_dav.workflow import MATRIX_PAYLOAD_FIELDS
    for matrix in packet['config']['assays']['matrices']:
        content = b'SYNTHETIC_ONLY\n' + canonical_bytes({'assay_matrix': {k: matrix[k] for k in MATRIX_PAYLOAD_FIELDS}})
        sha = hashlib.sha256(content).hexdigest()
        source = next(r for r in packet['records']['source_record'] if r['source_object_id'] == matrix['source_object_id'])
        source.update(sha256=sha, byte_size=len(content))
        matrix['source_sha256'] = sha
        packet['config']['registries']['source_hashes'][matrix['source_object_id']] = sha
        packet['config']['existing_seams']['source_payloads'][matrix['source_object_id']] = content.hex()


def _connected_graph(packet=None, stop_after=None):
    from tools.a_dav import workflow
    packet = synthetic_workflow_packet() if packet is None else packet
    functions = (workflow.run_existing_seams, workflow.build_registries, workflow.map_endpoints,
                 workflow.validate_timing, workflow.validate_assays, workflow.validate_overlap,
                 workflow.validate_exposure, workflow.evaluate_admission, workflow.validate_split,
                 workflow.build_baseline, workflow.build_longitudinal, workflow.build_public_report)
    for function in functions:
        result = function(packet)
        assert result['status'] == 'READY', (result['stage'], result['reasons'])
        packet['records'] = result['records']
        packet['dependencies'][result['stage']] = result
        if result['stage'] == stop_after: break
    return packet







def test_compatible_same_specimen_multiomics_uses_actual_assay_gates():
    packet = synthetic_workflow_packet()
    packet['branch_id'] = 'PAIRED_MULTIOMICS'
    source = deepcopy(packet['records']['source_record'][0])
    source.update(source_object_id='obj2', exact_file_name='invented-methylation.tsv')
    packet['records']['source_record'].append(source)
    for publication in [packet['records']['publication_family'][0],
                        packet['config']['existing_seams']['resolution_decision']['publications'][0]]:
        publication['source_object_ids'] = ['obj1', 'obj2']
    assay = deepcopy(packet['records']['assay_registry'][0])
    assay.update(assay_uid='a3', source_object_id='obj2', modality='METHYLATION',
                 measurement_unit='beta', branch_suitability=['METHYLATION'])
    packet['records']['assay_registry'].append(assay)
    matrix = deepcopy(packet['config']['assays']['matrices'][0])
    matrix.update(source_object_id='obj2', headers=['sample-001'], values=[[0.2], [0.4]],
                  modality='METHYLATION', unit='beta', lane='METHYLATION_BETA',
                  genome_build='invented', detection_p_provenance='invented',
                  probe_filter_policy='invented', snp_policy='invented',
                  cross_reactive_policy='invented', sex_chromosome_policy='invented')
    packet['config']['assays']['matrices'].append(matrix)
    packet['config']['admission']['required_source_object_ids'].append('obj2')
    _refresh_invented_matrix_bytes(packet)
    packet['config']['admission']['branch_policies']['PAIRED_MULTIOMICS'] = {
        'patient_link': _evidence(specimen_uids=['sp1', 'sp1']),
        'same_time_specimen': _evidence(specimen_uids=['sp1', 'sp1'], same_time=True, same_specimen=True),
        'modality_gates': _evidence(modalities=['RNA', 'METHYLATION'], assay_uids=['a1', 'a3'])}
    graph = _connected_graph(packet, stop_after='admission')
    admission = graph['dependencies']['admission']
    assert admission['status'] == 'READY'
    assert admission['audit'][0]['criteria'] == {'patient_link': 'SUPPORTED',
        'same_time_specimen': 'SUPPORTED', 'modality_gates': 'SUPPORTED'}
    assert admission['source_admission'] is False
    # Two RNA vocabulary aliases are still one modality, even when both exact
    # assay declarations and source bytes use their corresponding alias.
    packet['records']['assay_registry'][-1].update(modality='RNA_SEQ', measurement_unit='counts',
                                                 branch_suitability=['BASELINE_DE'])
    matrix.update(modality='RNA_SEQ', unit='counts', lane='COUNTS', values=[[2], [4]],
                  library_properties={'sample-001': {'library_size': 6, 'source_locator': 'invented'}})
    packet['config']['admission']['branch_policies']['PAIRED_MULTIOMICS']['modality_gates']['modalities'] = ['RNA', 'RNA_SEQ']
    _refresh_invented_matrix_bytes(packet)
    rejected = run_workflow(packet)
    assert rejected['status'] == 'FAIL'
    assert _admission_checks(rejected)['modality_gates'] == 'CONTRADICTED'


def test_external_policy_fields_and_reference_do_not_certify_unknown_rule():
    packet = synthetic_workflow_packet()
    packet['branch_id'] = 'A1_RESPONSE_TIME_INTERACTION'
    packet['config']['admission']['branch_policies'][packet['branch_id']] = {
        'repeated_observations': _evidence(specimen_uids=['sp1', 'sp2']),
        'response_groups': _evidence(endpoint_id='invented', group_definition='invented'),
        'time_model': _evidence(model_id='invented', variables=['time']),
        'missing_followup_audit': _evidence(candidate_specimen_uids=['sp1', 'sp2'], dispositions=['invented'])}
    result = run_workflow(packet)
    assert _admission_checks(result)['time_model'] == 'UNKNOWN'
    assert result['status'] != 'READY'


def test_window_policy_cannot_override_sealed_timing_window():
    packet = synthetic_workflow_packet()
    packet['branch_id'] = 'A1_ON_R_NR'
    policy = deepcopy(packet['config']['admission']['branch_policies']['A_BASELINE_BIO'])
    policy.update(on_window=_evidence(baseline_specimen_uid='sp1', followup_specimen_uid='sp2',
                                     window_id='invented-wrong'),
                  no_treatment_change=_evidence(specimen_uids=['sp1', 'sp2']))
    packet['config']['admission']['branch_policies'][packet['branch_id']] = policy
    result = run_workflow(packet)
    assert result['status'] == 'FAIL'
    assert _admission_checks(result)['on_window'] == 'CONTRADICTED'
