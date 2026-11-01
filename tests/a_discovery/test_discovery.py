"""Offline metadata fixtures, containing only invented accessions."""
import json
import urllib.error

import pytest

from tools.a_discovery import core


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return next(self.responses).encode()


def test_ncbi_fixture():
    c = FakeClient(['{"esearchresult":{"idlist":["1"]}}', '{"result":{"1":{"title":"Example"}}}', '{"linksets":[]}', '{"linksets":[]}', '{"linksets":[]}'])
    r = core.NCBI(c).resolve("GSE0000001")
    assert r.facts["title"] == "Example"
    assert "esummary" in r.locators["title"]


def test_geo_fixture():
    c = FakeClient(['!Series_title = Example\n!Series_sample_id = GSM0000001\n!Series_platform_id = GPL00001\n', ''])
    r = core.GEO(c).resolve("GSE0000001")
    assert r.facts["sample_count"] == 1
    assert "GSM0000001" not in str(r.facts)


def test_ena_fixture():
    c = FakeClient(['run_accession\tlibrary_strategy\nERR0000001\tRNA-Seq\n'])
    r = core.ENA(c).resolve("PRJEB00000")
    assert r.facts["run_count"] == 1
    assert "ERR0000001" not in str(r.facts)


def test_cbioportal_fixture():
    c = FakeClient(['{"name":"Example"}', '[{"clinicalAttributeId":"RESPONSE"}]', '[]', '{"sha":"' + 'a' * 40 + '"}', '[{"type":"file","name":"data.txt"}]'])
    r = core.CBioPortal(c).resolve("cbioportal:fake_study")
    assert r.facts["clinical_attributes"] == ["RESPONSE"]
    assert r.facts["datahub_commit"] == "a" * 40


def test_biostudies_fixture():
    c = FakeClient(['{"title":"Example","section":{"files":[{"path":"metadata.txt"}]}}'])
    assert core.BioStudies(c).resolve("E-MTAB-0000").facts["file_names"] == ["metadata.txt"]


def test_ega_fixture():
    c = FakeClient(['{"title":"Example","datasets":["EGAD000000"]}'])
    assert core.EGA(c).resolve("EGAS000000").facts["access"] == "CONTROLLED"


def test_dbgap_fixture():
    c = FakeClient(['{"esearchresult":{"idlist":[]}}'])
    assert core.DbGaP(c).resolve("phs000000").facts["access"] == "CONTROLLED"


def test_europepmc_fixture():
    c = FakeClient(['{"resultList":{"result":[{"title":"Example","isOpenAccess":"Y"}]}}'])
    assert core.EuropePMC(c).resolve("pmid:000000").facts["isOpenAccess"] == "Y"


def test_unknown_combination_and_overlap():
    r = core.Record("GSE0000001", "geo")
    r.add("title", "Nivolumab and entinostat", "https://www.ncbi.nlm.nih.gov/", "title")
    p = core.packet(r, [], {"GSE0000001"})
    assert p["endpoint_evidence"] == "UNKNOWN"
    assert set(p["design_implications"]) == {"COMBINATION"}
    r.facts["title"] = "Nivolumab and ipilimumab"
    assert "COMBINATION" not in core.packet(r, [], set())["design_implications"]


def test_host_refusal_and_private_output(tmp_path):
    for address in ("http://www.ebi.ac.uk/a", "https://evil.example/", "https://www.ebi.ac.uk@evil.example/"):
        with pytest.raises(ValueError):
            core.Client().get(address)
    with pytest.raises(ValueError):
        core.require_scratch(tmp_path)


def test_draft_plan_hashes_and_no_overwrite(tmp_path):
    from tools.a_dav.retrieval import load_plan
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({"source_object_candidates": [{"url": "https://raw.githubusercontent.com/example/file", "version": "a" * 40, "expected_size": 12, "expected_sha256": "b" * 64, "expected_md5": "c" * 32}]}))
    out = tmp_path / "plan.json.draft"
    core.draft_plan(packet, "fake", out)
    item = load_plan(out)["objects"][0]
    assert item["expected_sha256"] == "b" * 64
    assert "expected_md5" not in item
    with pytest.raises(FileExistsError):
        core.draft_plan(packet, "fake", out)


def test_no_sample_accession_in_plan(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({"source_object_candidates": [{"url": "https://example.org/ERR0000001.fastq.gz", "version": "1", "expected_size": 12}]}))
    with pytest.raises(ValueError):
        core.draft_plan(packet, "fake", tmp_path / "x.draft")


def test_retry_and_ncbi_rate_limit(monkeypatch):
    sleeps = []
    monkeypatch.setattr(core.time, "sleep", sleeps.append)
    monkeypatch.setattr(core.time, "monotonic", lambda: 1.0)
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
                raise urllib.error.HTTPError(req.full_url, 503, "error", {}, None)
            return Response()
    opener = Opener()
    monkeypatch.setattr(core.urllib.request, "build_opener", lambda *args: opener)
    c = core.Client(last_ncbi=1.0)
    assert c.get("https://eutils.ncbi.nlm.nih.gov/test") == b'{}'
    assert sleeps == [0.34, 1, 0.34]
    assert [x["status"] for x in c.requests] == [503, 200]


@pytest.mark.skipif(__import__("os").environ.get("A_DISCOVERY_LIVE") != "1", reason="live test is opt-in")
def test_live_smoke():
    assert core.EuropePMC(core.Client()).search("immunotherapy")
