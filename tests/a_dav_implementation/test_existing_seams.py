"""Existing discovery, resolution and object APIs with invented inputs only."""
from copy import deepcopy


from tools.a_dav.workflow import run_existing_seams
from tools.a_dav.demo import synthetic_context


def test_existing_discovery_resolution_and_whole_object_context_connect():
    packet = synthetic_context()
    before = deepcopy(packet)
    result = run_existing_seams(packet)
    assert result['status'] == 'READY'
    assert {row['ticket'] for row in result['audit']} == {'DAV-T01', 'DAV-T02', 'DAV-T03'}
    assert result['source_admission'] is False
    assert result['records']['source_record'][0]['sha256'] == packet['records']['source_record'][0]['sha256']
    assert packet == before


def test_changed_complete_bytes_fail_despite_well_shaped_hash():
    packet = synthetic_context()
    packet['config']['existing_seams']['source_payloads']['obj1'] = b'SYNTHETIC_ONLY\nchanged'.hex()
    result = run_existing_seams(packet)
    assert result['status'] == 'FAIL'
    assert result['reasons'] == ['SOURCE_BYTES_MISMATCH']


def test_incomplete_search_does_not_become_a_source_pass():
    packet = synthetic_context()
    packet['config']['existing_seams']['search_runs'][0]['completion_status'] = 'INCOMPLETE'
    packet['config']['existing_seams']['search_runs'][0]['pages'][0]['count'] = 2
    result = run_existing_seams(packet)
    assert result['status'] == 'BLOCKED_UNKNOWN'
    assert result['source_admission'] is False
