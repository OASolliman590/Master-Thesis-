"""Existing discovery, resolution and object APIs with invented inputs only."""
from copy import deepcopy
import hashlib

import pytest

from tools.a_dav.workflow import run_existing_seams
from tools.a_dav.demo import synthetic_context


def test_existing_discovery_resolution_and_whole_object_context_connect():
    packet = synthetic_context()
    before = deepcopy(packet)
    result = run_existing_seams(packet)
    assert result['status'] == 'SYNTHETIC_READY'
    assert {row['ticket'] for row in result['audit']} == {'DAV-T01', 'DAV-T02', 'DAV-T03'}
    assert result['source_admission'] is False
    assert result['records']['source_record'][0]['sha256'] == packet['records']['source_record'][0]['sha256']
    assert packet == before


def test_injected_object_transport_resumes_and_publishes_immutable_bytes(tmp_path):
    from tools.a_dav.object_verification import atomic_retrieve
    content = b'SYNTHETIC_ONLY\ninvented object\n'
    destination = tmp_path / 'invented-object.bin'
    calls = []

    def transport(url, headers):
        calls.append(headers)
        if len(calls) == 1:
            return {'status': 200, 'headers': {'Content-Length': str(len(content)), 'ETag': 'invented-v1'},
                    'body': content[:8], 'interrupted': True}
        return {'status': 206, 'headers': {'Content-Length': str(len(content) - 8),
                'Content-Range': f'bytes 8-{len(content)-1}/{len(content)}', 'ETag': 'invented-v1'},
                'body': content[8:]}

    args = ('https://raw.githubusercontent.com/synthetic/example/invented.bin', destination,
            'SYN-OBJECT', transport, lambda: 1792713600)
    with pytest.raises(ValueError, match='incomplete'):
        atomic_retrieve(*args, expected_sha256=hashlib.sha256(content).hexdigest())
    assert not destination.exists()
    receipt = atomic_retrieve(*args, expected_sha256=hashlib.sha256(content).hexdigest())
    assert calls[1] == {'Range': 'bytes=8-', 'If-Range': 'invented-v1'}
    assert destination.read_bytes() == content
    assert receipt['partial_full_status'] == 'FULL_VERIFIED'
    assert receipt['validation_status'] == 'STRUCTURAL_ONLY'
    with pytest.raises(ValueError, match='replace'):
        atomic_retrieve(*args)
    assert len(calls) == 2


def test_bad_source_checksum_never_publishes_destination(tmp_path):
    from tools.a_dav.object_verification import atomic_retrieve
    target = tmp_path / 'invented-object.bin'
    with pytest.raises(ValueError, match='SHA-256'):
        atomic_retrieve('https://raw.githubusercontent.com/synthetic/example/invented.bin',
                        target, 'SYN-OBJECT', lambda *_: {'status': 200,
                        'headers': {'Content-Length': '3'}, 'body': b'bad'},
                        lambda: 1792713600, expected_sha256='a' * 64)
    assert not target.exists()
    assert not list(tmp_path.iterdir())


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
