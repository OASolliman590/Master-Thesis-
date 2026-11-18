"""Invented strings only."""

from tools.gate.privacy import scan_paths, scan_text


def test_allows_study_accessions_and_relative_paths():
    text = "Data from GSE176307 and PRJEB23709; outputs under .scratch/runtime/a_p2/."
    assert scan_text("doc.md", text) == []


def test_refuses_private_path_sample_ids_and_keys():
    # Assembled at run time so this file itself passes the scan.
    text = "\n".join([
        "see /" + "Users/someone/notes",
        "sample " + "GSM" + "0000001 and run " + "SRR" + "0000001",
        "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
    ])
    kinds = sorted({hit.kind for hit in scan_text("doc.md", text)})
    assert kinds == ["credential", "private path", "sample or run accession"]


def test_refuses_ingestion_packet_by_name(tmp_path):
    packet = tmp_path / "x" / "ingestion_packet.json"
    packet.parent.mkdir()
    packet.write_text("{}")
    hits = scan_paths(tmp_path, ["x/ingestion_packet.json"])
    assert [h.kind for h in hits] == ["forbidden file"]
