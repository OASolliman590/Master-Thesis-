import json
import urllib.parse

import pytest

from tools.a_discovery import core
from tools.a_discovery.core import Record


class Fixture:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.urls = []
    def get(self, url):
        self.urls.append(url)
        return next(self.responses).encode()


def test_esearch_pagination():
    c = Fixture([json.dumps({"esearchresult": {"count": "3", "idlist": ["1", "2"]}}), json.dumps({"esearchresult": {"count": "3", "idlist": ["3"]}})])
    assert core.NCBI(c).search_db("query", "gds", page_size=2) == ["1", "2", "3"]
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(c.urls[1]).query)["retstart"] == ["2"]


def test_geo_characteristics_and_listing():
    c = Fixture(['!Series_sample_id = GSM0000001\n!Series_sample_id = GSM0000002\n!Series_supplementary_file = ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE000nnn/GSE000001/suppl/GSE000001_counts.txt.gz\n', '!Sample_characteristics_ch1 = response: CR\n!Sample_characteristics_ch1 = response: PD\n', '<a href="GSE000001_counts.txt.gz">GSE000001_counts.txt.gz</a> 2026-01-01 00:00 123\n'])
    r = core.GEO(c).resolve("GSE000001")
    assert r.facts["sample_count"] == 2
    assert r.facts["characteristic_counts"] == {"response": {"CR": 1, "PD": 1}}
    assert r.objects[0]["size"] == 123
    assert "GSM000000" not in str(r.facts)


def test_ncbi_links_all_databases():
    replies = ['{"esearchresult":{"idlist":["1"]}}', '{"result":{"1":{"title":"Example"}}}', '{"linksets":[{"linksetdbs":[{"links":["2"]}]}]}', '{"result":{}}', '{"linksets":[{"linksetdbs":[{"links":["3"]}]}]}', '{"result":{}}', '{"linksets":[{"linksetdbs":[{"links":["4"]}]}]}']
    c = Fixture(replies)
    r = core.NCBI(c).resolve("GSE000001")
    assert r.facts["linked_uids"] == {"bioproject": ["2"], "sra": ["3"], "pubmed": ["4"]}


def test_ega_search_studies_and_datasets():
    c = Fixture(['{"response":{"result":[{"studyId":"EGAS000000"}]}}', '{"response":{"result":[{"datasetId":"EGAD000000"}]}}'])
    assert {x.identifier for x in core.EGA(c).search("example")} == {"EGAS000000", "EGAD000000"}


def test_dbgap_summary_and_pattern():
    c = Fixture(['{"esearchresult":{"idlist":["1"]}}', '{"result":{"1":{"title":"Fake study"}}}'])
    r = core.DbGaP(c).resolve("phs000000")
    assert r.facts["access"] == "CONTROLLED"
    assert r.facts["title"] == "Fake study"
    with pytest.raises(ValueError):
        core.DbGaP(c).resolve("phs-invalid")


def test_readiness_evidence_and_unknown():
    r = Record("GSE000001", "geo")
    assert core.readiness(r)[0] == "UNKNOWN"
    r.facts.update({"processed_matrix_public": True, "response_labels_repository": True})
    assert core.readiness(r)[0] == "R1"
    r.facts["response_labels_repository"] = False
    r.facts["response_labels_paper"] = True
    assert core.readiness(r)[0] == "R2"
    r.facts = {"access": "CONTROLLED"}
    assert core.readiness(r)[0] == "R3"
    r.facts = {"set_aside": True}
    assert core.readiness(r)[0] == "X"
    assert core.readiness(r)[1]


def test_class_lexicon_dual_ici_and_ezh2():
    r = Record("fake", "geo")
    r.add("title", "nivolumab and ipilimumab", "https://www.ncbi.nlm.nih.gov/", "title")
    assert "COMBINATION" not in core.packet(r, [], set())["design_implications"]
    r.facts["title"] = "nivolumab with tazemetostat"
    assert "COMBINATION" in core.packet(r, [], set())["design_implications"]


def test_inventory_draft_geo_and_lfs(tmp_path):
    from tools.a_dav.retrieval import load_plan
    rec = Record("GSE000001", "geo", objects=[
        {"file": "matrix.txt.gz", "url": "https://ftp.ncbi.nlm.nih.gov/geo/matrix.txt.gz", "size": 123, "published_hash": None, "hash_type": None, "version": "v1"},
        {"file": "data.txt", "url": "https://media.githubusercontent.com/media/cBioPortal/datahub/" + "a"*40 + "/public/fake/data.txt", "size": 456, "published_hash": "b"*64, "hash_type": "sha256", "version": "a"*40},
    ])
    p = core.packet(rec, [], set())
    assert p["object_inventory"] == rec.objects
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(p))
    out = tmp_path / "plan.json.draft"
    core.draft_plan(path, "fake", out)
    objects = load_plan(out)["objects"]
    assert objects[0]["expected_size"] == 123 and objects[0]["expected_sha256"] is None
    assert objects[1]["expected_size"] == 456 and objects[1]["expected_sha256"] == "b"*64


def test_ena_hash_metadata_stays_out_of_draft(tmp_path):
    c = Fixture(['run_accession\tfastq_bytes\tfastq_md5\tfastq_ftp\nERR0000001\t12\t' + 'c'*32 + '\tftp.sra.ebi.ac.uk/vol1/ERR0000001.fastq.gz\n'])
    r = core.ENA(c).resolve("PRJEB00000")
    assert r.objects[0]["published_hash"] == "c"*32
    assert r.objects[0]["hash_type"] == "md5"
    p = tmp_path / "packet.json"
    p.write_text(json.dumps(core.packet(r, [], set())))
    with pytest.raises(ValueError):
        core.draft_plan(p, "fake", tmp_path / "plan.draft")


def test_ncbi_resolves_linked_uids_to_accessions():
    c = Fixture([
        '{"esearchresult":{"idlist":["1"]}}',
        '{"result":{"1":{"title":"Fake"}}}',
        '{"linksets":[{"linksetdbs":[{"links":["2"]}]}]}',
        '{"result":{"2":{"project_acc":"PRJEB00000"}}}',
        '{"linksets":[{"linksetdbs":[{"links":["3"]}]}]}',
        json.dumps({'result': {'3': {'expxml': '<Study acc="SRP000000"/>'}}}),
        '{"linksets":[{"linksetdbs":[{"links":["4"]}]}]}',
    ])
    r = core.NCBI(c).resolve("GSE000001")
    assert r.facts["linked_accessions"] == {"bioproject": ["PRJEB00000"], "sra": ["SRP000000"], "pubmed": ["4"]}


def test_retry_after_header_is_respected(monkeypatch):
    import urllib.error
    sleeps = []
    monkeypatch.setattr(core.time, "sleep", sleeps.append)
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'{}'
    class Opener:
        count = 0
        def open(self, req, timeout):
            self.count += 1
            if self.count == 1:
                raise urllib.error.HTTPError(req.full_url, 429, "rate limit", {"Retry-After": "7"}, None)
            return Response()
    monkeypatch.setattr(core.urllib.request, "build_opener", lambda *args: Opener())
    core.Client().get("https://www.ebi.ac.uk/test")
    assert sleeps == [7]


def test_geo_inventory_to_packet_to_fetch_draft(tmp_path, monkeypatch):
    from tools.a_dav.retrieval import load_plan
    monkeypatch.setattr(core, "SCRATCH", tmp_path)
    c = Fixture(['!Series_title = Synthetic\n!Series_supplementary_file = ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE000nnn/GSE000001/suppl/GSE000001_matrix.txt.gz\n', '', '<a href="GSE000001_matrix.txt.gz">GSE000001_matrix.txt.gz</a> 2026-01-01 00:00 123\n'])
    c.requests = []
    rec = core.GEO(c).resolve("GSE000001")
    out = tmp_path / "discovery"
    core.save_packets(out, [(rec, ["q1"])], c)
    p = out / "packets/GSE000001.json"
    assert json.loads(p.read_text())["object_inventory"][0]["size"] == 123
    plan = tmp_path / "plan.draft"
    core.draft_plan(p, "synthetic", plan)
    assert load_plan(plan)["objects"][0]["expected_size"] == 123


def test_no_run_accession_in_git_bound_draft_from_allowed_ena_host(tmp_path):
    p = tmp_path / "packet.json"
    p.write_text(json.dumps({"object_inventory": [{"file": "ERR0000001.fastq.gz", "url": "https://ftp.sra.ebi.ac.uk/vol1/ERR0000001.fastq.gz", "size": 12, "published_hash": "c" * 32, "hash_type": "md5"}]}))
    with pytest.raises(ValueError):
        core.draft_plan(p, "fake", tmp_path / "x.draft")


def test_overlap_matches_linked_accession():
    r = Record("GSE000001", "ncbi")
    r.facts["linked_accessions"] = {"bioproject": ["PRJEB00000"]}
    assert "POSSIBLE_OVERLAP" in core.packet(r, [], {"PRJEB00000": "Fake family"})["design_implications"]
