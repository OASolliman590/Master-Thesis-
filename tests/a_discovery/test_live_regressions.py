import csv
import io
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tools.a_discovery import core


class Fixtures:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.urls = []
        self.requests = []
    def get(self, url):
        self.urls.append(url)
        return next(self.payloads).encode()


def test_geo_uses_separate_brief_text_views():
    c = Fixtures(['!Series_title = Synthetic\n!Series_sample_id = GSM0000001\n', '!Sample_characteristics_ch1 = response: CR\n'])
    r = core.GEO(c).resolve('GSE0000001')
    assert r.facts['characteristic_counts']['response'] == {'CR': 1}
    assert [parse_qs(urlsplit(u).query)['targ'][0] for u in c.urls] == ['self', 'gsm']
    assert all(parse_qs(urlsplit(u).query)['form'] == ['text'] for u in c.urls)


def test_challenge_aborts_and_persists_packet_and_receipt(tmp_path, monkeypatch):
    c = Fixtures(['<!DOCTYPE html><html><title>reCAPTCHA</title></html>'])
    monkeypatch.setattr(core, 'SCRATCH', tmp_path)
    record = core.resolve_lead(core.GEO(c), 'GSE0000001', c)
    assert record.status == 'BLOCKED_BY_CHALLENGE'
    assert len(c.urls) == 1
    core.save_packets(tmp_path / 'run', [(record, [])], c)
    packet = json.loads((tmp_path / 'run/packets/GSE0000001.json').read_text())
    receipt = json.loads((tmp_path / 'run/receipt.json').read_text())
    assert packet['status'] == receipt['status'] == 'BLOCKED_BY_CHALLENGE'


def test_no_false_overlap_for_same_candidate():
    r = core.Record('GSE0000001', 'geo')
    p = core.packet(r, [], {'GSE0000001': 'Family fake'})
    assert p['suspected_overlap'] == 'UNKNOWN'
    r.facts['pubmed_id'] = ['10000001']
    r.locators['pubmed_id'] = 'https://www.ncbi.nlm.nih.gov/geo/#pubmed'
    p = core.packet(r, [], {'PMID:10000001': 'Family fake'})
    assert p['suspected_overlap']['family'] == 'Family fake'
    assert p['suspected_overlap']['shared_identifier'] == 'PMID:10000001'


def test_fastq_filters_strategy_and_reports_all_totals(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'SCRATCH', tmp_path)
    text = ('run_accession\tsample_accession\tlibrary_strategy\tlibrary_layout\tinstrument_model\tfastq_bytes\tfastq_md5\tfastq_ftp\n'
            'ERR0000001\tSAMN0000001\tRNA-Seq\tSINGLE\tFake\t10\t' + 'a'*32 + '\tftp.sra.ebi.ac.uk/fake/rna.fastq.gz\n'
            'ERR0000002\tSAMN0000002\tWXS\tSINGLE\tFake\t20\t' + 'b'*32 + '\tftp.sra.ebi.ac.uk/fake/wxs.fastq.gz\n')
    c = Fixtures([text])
    core.save_fastq('PRJEB00000', tmp_path, c)
    stats = json.loads((tmp_path / 'fastq/PRJEB00000.size.json').read_text())
    assert stats['total_bytes'] == 10
    assert stats['per_strategy']['WXS']['total_bytes'] == 20
    assert len(list(csv.DictReader((tmp_path / 'samplesheet.nfcore.csv').open()))) == 1


@pytest.mark.skipif(not os.getenv('A_DISCOVERY_REPLAY_DIR'), reason='recorded response replay is opt-in')
def test_recorded_geo_cbio_and_fastq_replay(tmp_path, monkeypatch):
    folder = Path(os.environ['A_DISCOVERY_REPLAY_DIR'])
    if not folder.is_dir():
        pytest.skip('recorded response directory is absent')
    monkeypatch.setattr(core, 'SCRATCH', tmp_path)
    geo_self = next(folder.glob('geo_*_self.txt'))
    identifier = geo_self.name.removeprefix('geo_').removesuffix('_self.txt')
    c = Fixtures([geo_self.read_text(), next(folder.glob('geo_*_gsm.txt')).read_text(), next(folder.glob('geo_*_suppl_listing.html')).read_text()])
    geo = core.GEO(c).resolve(identifier)
    assert geo.facts['title'] and geo.facts['sample_count'] > 0 and geo.facts['platform_id']
    assert geo.facts['pubmed_id'] and geo.facts['characteristic_counts'] and geo.objects
    assert geo.objects[0]['size_display']
    blocked = core.resolve_lead(core.GEO(Fixtures([next(folder.glob('geo_*_wrongparam.html')).read_text()])), identifier, Fixtures([]))
    assert blocked.status == 'BLOCKED_BY_CHALLENGE'
    study_data = next(data for data in (json.loads(p.read_text()) for p in folder.glob('cbio_*.json')) if isinstance(data, dict) and 'studyId' in data)
    study = study_data['studyId']
    entries = json.loads(next(folder.glob('github_*_contents.json')).read_text())
    pointer = next(folder.glob('github_*_lfs_pointer.txt')).read_text()
    pointer_name = next(e['name'] for e in entries if e['name'].startswith('data_mrna_seq_expression.') and e['size'] == len(pointer.encode()))
    class PortalFixture:
        requests = []
        def get(self, address):
            if '/commits/HEAD' in address: return json.dumps({'sha': 'a'*40}).encode()
            if 'api.github.com' in address: return json.dumps(entries).encode()
            if 'raw.githubusercontent.com' in address:
                return pointer.encode() if address.endswith('/' + pointer_name) else b'not a pointer'
            if address.endswith('/clinical-attributes'): return next(folder.glob('cbio_*_clinical-attributes.json')).read_bytes()
            if address.endswith('/molecular-profiles'): return next(folder.glob('cbio_*_molecular-profiles.json')).read_bytes()
            return json.dumps(study_data).encode()
    portal = core.CBioPortal(PortalFixture()).resolve('cbioportal:' + study)
    assert portal.facts['name'] and portal.facts['pmid'] and portal.facts['cancerTypeId']
    assert portal.facts['clinical_attributes'] and portal.facts['molecular_profiles']
    assert any(x.get('hash_type') == 'sha256' for x in portal.objects)
    ena_file = next(folder.glob('ena_*.tsv'))
    project = ena_file.stem.removeprefix('ena_')
    rows = list(csv.DictReader(io.StringIO(ena_file.read_text()), delimiter='\t'))
    expected = [r for r in rows if r['library_strategy'] == 'RNA-Seq']
    client = Fixtures([ena_file.read_text()])
    core.save_fastq(project, tmp_path / 'ena', client)
    stats = json.loads((tmp_path / 'ena/fastq' / (project + '.size.json')).read_text())
    assert stats['selected_run_count'] == len(expected) == 34
    assert stats['total_bytes'] == sum(sum(int(x) for x in r['fastq_bytes'].split(';')) for r in expected)


def test_alternate_fastq_strategy(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'SCRATCH', tmp_path)
    text = ('run_accession\tsample_accession\tlibrary_strategy\tlibrary_layout\tinstrument_model\tfastq_bytes\tfastq_md5\tfastq_ftp\n'
            'ERR0000001\tSAMN0000001\tRNA-Seq\tSINGLE\tFake\t10\t' + 'a'*32 + '\tftp.sra.ebi.ac.uk/fake/rna.fastq.gz\n'
            'ERR0000002\tSAMN0000002\tWXS\tSINGLE\tFake\t20\t' + 'b'*32 + '\tftp.sra.ebi.ac.uk/fake/wxs.fastq.gz\n')
    core.save_fastq('PRJEB00000', tmp_path, Fixtures([text]), 'WXS')
    stats = json.loads((tmp_path / 'fastq/PRJEB00000.size.json').read_text())
    assert stats['total_bytes'] == 20 and stats['selected_run_count'] == 1


def test_html_on_json_endpoint_is_blocked_without_parsing():
    client = Fixtures(['<html><body>Service unavailable</body></html>'])
    result = core.resolve_lead(core.CBioPortal(client), 'cbioportal:fake', client)
    assert result.status == 'BLOCKED_BY_CHALLENGE'
    assert len(client.urls) == 1


def test_transport_challenge_is_recorded_without_retry(monkeypatch):
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'<html><title>reCAPTCHA</title></html>'
    class Opener:
        count = 0
        def open(self, req, timeout):
            self.count += 1
            return Response()
    opener = Opener()
    monkeypatch.setattr(core.urllib.request, 'build_opener', lambda *args: opener)
    client = core.Client()
    result = core.resolve_lead(core.GEO(client), 'GSE0000001', client)
    assert result.status == 'BLOCKED_BY_CHALLENGE'
    assert client.requests[0]['outcome'] == 'BLOCKED_BY_CHALLENGE'
    assert core.receipt(client)['status'] == 'BLOCKED_BY_CHALLENGE'
    assert opener.count == 1


def test_overlap_matches_cbio_pmid_to_named_family():
    record = core.Record('cbioportal:fake', 'cbioportal')
    record.add('pmid', '10000001', 'https://www.cbioportal.org/api/studies/fake', 'pmid')
    result = core.packet(record, [], {'PMID:10000001': 'Fake family'})
    assert result['suspected_overlap'] == {'family': 'Fake family', 'shared_identifier': 'PMID:10000001'}
