import json
from pathlib import Path

import pytest

from tools.a_dav.ingest import IngestError, run_ingest, validate_output_path


def test_ingest_writes_private_canonical_tables_and_unsigned_review_worksheet_for_missing_objects(tmp_path, monkeypatch):
    field_map_path = Path("tools/a_dav/field_maps/riaz_gse91061.json")
    field_map = json.loads(field_map_path.read_text())
    for source in field_map["source_objects"].values():
        source["sha256"] = None
    map_root = tmp_path / "field_maps"
    map_root.mkdir()
    (map_root / "riaz_gse91061.json").write_text(json.dumps(field_map))
    import tools.a_dav.ingest as ingest
    monkeypatch.setattr(ingest, "FIELD_MAP_ROOT", map_root)

    result = run_ingest("riaz_gse91061", "A_BASELINE_BIO", tmp_path / "ingest",
                        tmp_path / "out", allow_external_out=True)
    assert result["packet"]["classification"] == "PRIVATE_PATIENT_LEVEL"
    from tools.a_dav.core import ENTITY_TABLES
    assert set(result["packet"]["records"]) == ENTITY_TABLES
    assert not any(key.endswith("_proposals") for key in result["packet"]["records"])
    assert result["worksheet_status"] == "UNSIGNED"
    assert result["summary"]["counts"]["geo_samples"] == 0
    assert all(value is None for value in result["summary"]["object_hashes"].values())
    assert (tmp_path / "out/records/ingestion_packet.json").is_file()
    assert (tmp_path / "out/records/stage_statuses.json").is_file()
    assert (tmp_path / "out/worksheet.json").is_file()
    summary = (tmp_path / "out/SUMMARY.md").read_text()
    assert "Pt" not in summary
    assert "GSM" not in summary
    assert "SOURCE_OBJECT_HASH_UNPINNED" in summary
    assert all(item["kind"] in {"gate", "ingestion"} for item in result["worksheet"]["items"])
    assert len([item for item in result["worksheet"]["items"] if item["kind"] == "gate"]) == 9


def test_ingestion_worksheet_is_bound_before_registry_receipt(tmp_path, monkeypatch):
    field_map_path = Path("tools/a_dav/field_maps/riaz_gse91061.json")
    field_map = json.loads(field_map_path.read_text())
    for source in field_map["source_objects"].values():
        source["sha256"] = None
    map_root = tmp_path / "field_maps"
    map_root.mkdir()
    (map_root / "riaz_gse91061.json").write_text(json.dumps(field_map))
    import tools.a_dav.ingest as ingest
    from tools.a_dav.core import SchemaStore, dependency, finish

    monkeypatch.setattr(ingest, "FIELD_MAP_ROOT", map_root)

    def registry_receipt(packet, *, schemas=None):
        return finish("registries", packet, packet["records"], schemas=schemas)

    monkeypatch.setattr(ingest, "build_registries", registry_receipt)
    result = ingest.run_ingest("riaz_gse91061", "A_BASELINE_BIO", tmp_path / "ingest",
                               tmp_path / "out", allow_external_out=True)
    packet = result["packet"]
    assert packet["dependencies"]["registries"]["bindings"]["config_sha256"]
    assert dependency(packet, "registries", SchemaStore())["status"] == "READY"


def test_output_policy_requires_runtime_or_explicit_external_path(tmp_path):
    with pytest.raises(IngestError, match="OUTPUT_PATH_NOT_ALLOWED"):
        validate_output_path(tmp_path / "private-output")
    assert validate_output_path(tmp_path / "private-output", allow_external_out=True) == tmp_path / "private-output"


def test_output_policy_refuses_paths_inside_the_repository_even_with_external_flag():
    from tools.a_dav.ingest import REPO_ROOT
    with pytest.raises(IngestError, match="OUTPUT_PATH_NOT_ALLOWED"):
        validate_output_path(REPO_ROOT / "untracked-private-output", allow_external_out=True)


def test_output_policy_checks_git_tracked_descendants_in_runtime(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import tools.a_dav.ingest as ingest

    monkeypatch.setattr(ingest.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        stdout=b".scratch/runtime/private-run/packet.json\0"))
    with pytest.raises(IngestError, match="OUTPUT_PATH_TRACKED"):
        validate_output_path(ingest.REPO_ROOT / ".scratch/runtime/private-run")
