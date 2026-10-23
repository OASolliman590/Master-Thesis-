"""Independently verify the retained AIU synthetic receipts and preserved inputs."""
from pathlib import Path
import hashlib
import json
import re


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
OUTER = REPO.parents[1]
AIU = PACKET / "AIU_RECEIPTS"
FLAGS = ("analysis_ready", "source_admission", "statistical_release", "biological_analysis_executed")


def read(path):
    return json.loads(path.read_text())


def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    baseline = read(PACKET / "PRESERVATION_BASELINE.json")
    for item in baseline["files"]:
        path = OUTER / item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], item["path"]
    manifest = read(PACKET / "ALLOWLIST_MANIFEST.json")
    expected = {}
    for item in manifest["files"]:
        name = item["path"]
        source = PACKET / name if name == "runner.py" else REPO / name
        assert source.stat().st_size == item["size"] and sha(source) == item["sha256"], name
        expected[name] = item["sha256"]
    assert len(expected) == 44
    manifest_hash = sha(PACKET / "ALLOWLIST_MANIFEST.json")
    for item in read(PACKET / "COLLECTION.json")["files"]:
        path = AIU / item["path"]
        assert path.stat().st_size == item["size"] and sha(path) == item["sha256"], item["path"]
    status = read(AIU / "result/status.json")
    assert status["classification"] == "SYNTHETIC_ONLY" and status["status"] == "PASSED"
    assert status["target_environment_software_acceptance"] is True and status["failed_stage"] is None
    assert all(status[key] is False for key in (*FLAGS, "real_source_data_used", "frozen_specs_changed"))
    assert status["payload"] == {"files": expected, "manifest_sha256": manifest_hash}
    assert status["pid"] == int((AIU / "runner.pid").read_text())
    assert json.loads((AIU / "runner.stdout.log").read_text()) == status
    assert (AIU / "runner.stderr.log").read_text() == ""
    environment = status["environment"]
    assert environment["os"] == "Linux" and environment["python_version"] == "3.11.16"
    assert environment["installed_distributions"] == environment["public_requirements"]
    assert environment["installed_distributions"] == {"jsonschema": "4.26.0", "pytest": "9.1.1", "mypy": "1.18.2"}
    assert set(status["stages"]) == {"full_synthetic_tests", "fresh_demo", "resume_demo"}
    assert all(stage["exit_code"] == 0 for stage in status["stages"].values())
    assert re.search(r"\b255 passed in [0-9.]+s", (AIU / "result/process-tests.stdout.log").read_text())
    fresh = (AIU / "result/process-fresh.stdout.log").read_text().strip()
    assert fresh == (AIU / "result/process-resume.stdout.log").read_text().strip()
    summary = json.loads(fresh)
    assert set(summary) == {"classification", "stage", "status", "reasons", "bindings", *FLAGS}
    assert summary["classification"] == "SYNTHETIC_ONLY" and summary["status"] == "SYNTHETIC_READY"
    assert summary["stage"] == "workflow" and summary["reasons"] == []
    assert all(summary[key] is False for key in FLAGS)
    assert set(summary["bindings"]) == {"input_sha256", "config_sha256", "schemas_sha256", "code_sha256", "core_sha256", "output_sha256"}
    assert all(re.fullmatch(r"[a-f0-9]{64}", value) for value in summary["bindings"].values())
    assert hashlib.sha256(fresh.encode()).hexdigest() == status["safe_summary_sha256"]
    bundle = AIU / "result/synthetic-bundle"
    bundle_hashes = {path.name: sha(path) for path in bundle.iterdir()}
    assert bundle_hashes == status["fresh_bundle_sha256"]
    bundle_manifest = read(bundle / "manifest.json")
    assert all(bundle_manifest[key] is False for key in FLAGS)
    assert bundle_manifest["files"] == {name: value for name, value in bundle_hashes.items() if name != "manifest.json"}
    result = read(bundle / "result.json")
    assert all(result[key] is False for key in FLAGS)
    draft = read(bundle / "release_draft.json")
    assert draft["state"] == "READY_FOR_REVIEW" and draft["evidence_class"] == "SYNTHETIC"
    assert draft["software_gate"] == "PASS"
    assert draft["data_gate"] == draft["statistical_gate"] == draft["protected_set_gate"] == "NOT_RUN"
    assert draft["admitted_source_ids"] == []
    assert set(draft["blocked_reasons"]) == {"ACTUAL_SOURCE_REVIEW_NOT_RUN", "ACTUAL_STATISTICAL_REVIEW_NOT_RUN"}
    parent = read(AIU / "parent-resume.json")
    assert parent["exit_code"] == 0 and parent["before_sha256"] == parent["after_sha256"] == bundle_hashes
    assert parent["payload_sha256"] == {**expected, "ALLOWLIST_MANIFEST.json": manifest_hash}
    assert (AIU / "parent-resume.stdout.log").read_text().strip() == fresh
    assert (AIU / "parent-resume.stderr.log").read_text() == ""
    parent_types = read(AIU / "parent-review.json")
    assert parent_types["exit_code"] == 0
    assert parent_types["filesystem_probe"]["case_sensitive"] is True
    assert parent_types["filesystem_probe"]["symlink_supported"] is True
    assert "Success: no issues found in 15 source files" in (AIU / "parent-mypy.stdout.log").read_text()
    setup = read(AIU / "setup-status.json")
    assert setup["status"] == "PASSED" and setup["payload_files_verified"] == 45
    assert all(item["exit_code"] == 0 for item in setup["stages"])
    assert setup["shared_environment_modified"] is False
    for item in read(PACKET / "EVIDENCE_BINDINGS.json")["files"]:
        path = PACKET / item["path"]
        assert path.stat().st_size == item["size"] and sha(path) == item["sha256"], item["path"]
    return {"classification": "SYNTHETIC_ONLY", "status": "PASSED", "base_commit": manifest["base_commit"],
            "preserved_files_checked": len(baseline["files"]), "preserved_files_changed": 0,
            "payload_files_checked": 45, "aiu_synthetic_tests_passed": 255,
            "parent_target_typecheck_sources": 15, "parent_resume_unchanged": True,
            "target_environment_software_acceptance": True, "real_source_data_used": False,
            "frozen_specs_changed": False, **{flag: False for flag in FLAGS}}


if __name__ == "__main__":
    result = verify()
    (PACKET / "VERIFICATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
