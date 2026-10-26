"""Connected invented workflow invokes every real stage API."""
from copy import deepcopy

from tools.a_dav.demo import synthetic_workflow_packet
from tools.a_dav.workflow import run_workflow














def _evidence(**fields):
    return {'policy_version': 'invented-v1', 'source_locators': ['invented'],
            'rule': 'invented metadata rule',
            'record_refs': [{'table': 'patient_registry', 'key': 'patient_uid', 'value': 'p1'}], **fields}


def _admission_checks(result):
    stage = next(row for row in result['audit'] if row['stage'] == 'admission')
    return next(row['criteria'] for row in stage['checks'] if row['kind'] == 'admission_eligibility')












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


def test_refreshing_same_output_ancestor_invalidates_descendants(monkeypatch, tmp_path):
    import pytest
    from tools.a_dav import core, workflow
    from tools.a_dav.release import freeze_bundle
    packet = _connected_graph()
    original = core._file_hash
    monkeypatch.setattr(core, '_file_hash', lambda path: 'e' * 64 if path.name == 'endpoints.py' else original(path))
    old = packet['dependencies']['endpoints']
    fresh = workflow.map_endpoints(packet)
    assert fresh['status'] == 'READY'
    assert fresh['records']['endpoint'] == old['records']['endpoint']
    assert fresh['receipt_id'] != old['receipt_id']
    packet['dependencies']['endpoints'] = fresh
    for stage in ('admission', 'baseline'):
        with pytest.raises(core.DavError, match='DEPENDENCY_INVALID'):
            core.dependency(packet, stage, core.SchemaStore())
    assert workflow.build_public_report(packet)['status'] == 'FAIL'
    assert freeze_bundle(packet, tmp_path / 'stale')['status'] == 'FAIL'
    for function in (workflow.evaluate_admission, workflow.validate_split, workflow.build_baseline,
                     workflow.build_longitudinal, workflow.build_public_report):
        result = function(packet)
        assert result['status'] == 'READY', (result['stage'], result['reasons'])
        packet['records'] = result['records']
        packet['dependencies'][result['stage']] = result
    assert freeze_bundle(packet, tmp_path / 'rebuilt')['status'] == 'READY'


def test_legacy_runtime_and_demo_hash_changes_invalidate_receipts(monkeypatch, tmp_path):
    import pytest
    from tools.a_dav import core
    from tools.a_dav.release import freeze_bundle, verify_bundle
    packet = _connected_graph()
    target = tmp_path / 'runtime'
    frozen = freeze_bundle(packet, target)
    assert frozen['status'] == 'READY'
    original = core._file_hash
    for filename in ('search_log.py', 'study_resolution.py', 'object_verification.py', 'demo.py'):
        with monkeypatch.context() as patch:
            patch.setattr(core, '_file_hash', lambda path, filename=filename: 'f' * 64 if path.name == filename else original(path))
            with pytest.raises(core.DavError, match='CODE_BINDING_MISMATCH'):
                core.verify_result(frozen)
            with pytest.raises(core.DavError, match='CODE_BINDING_MISMATCH'):
                verify_bundle(target)







