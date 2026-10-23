"""Verify readiness documentation and preservation without source access."""
import csv
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTER = ROOT.parents[1]


def load(path):
    return json.loads(path.read_text())


def checked(record):
    path = (OUTER / record["path"]).resolve()
    assert path.is_relative_to(OUTER) and path.is_file()
    raw = path.read_bytes()
    assert len(raw) == record["bytes"] and hashlib.sha256(raw).hexdigest() == record["sha256"], record["path"]
    return path


def verify():
    binding = load(HERE / "BINDINGS.json")
    assert binding["document_kind"] == "READINESS_CHECK_NOT_ACCESS_APPROVAL"
    plan = load(checked(binding["prior_plan_bindings"]))
    baseline = load(checked(plan["prior_preservation_baseline"]))
    preserved = baseline["files"] + plan["additional_protected_files"] + binding["additional_protected_files"]
    assert len(preserved) == 2226 and len({r["path"] for r in preserved}) == 2226
    for record in preserved + binding["input_documents"]:
        checked(record)
    state = load(HERE / "STATUS.json")
    assert state["classification"] == "DOCUMENT_METADATA_CHECK_ONLY"
    assert state["check_status"] == "COMPLETE_WITH_MISSING_APPROVAL_EVIDENCE"
    assert state["source_candidate"] == "Prat-GSE93157" and state["branch_id"] == "A_BASELINE_BIO"
    assert state["source_review_readiness"] == "BLOCKED_UNKNOWN"
    assert state["custody_authority"] == state["custodian_appointment"] == "NOT_ESTABLISHED"
    assert state["first_reader_appointment"] == state["second_reader_appointment"] == "UNASSIGNED_IN_CHECKED_RECORDS"
    assert state["access_route"] == "UNKNOWN" and state["approval_references"] == "UNKNOWN_TO_USER_NOT_ESTABLISHED_IN_CHECKED_RECORDS"
    for key in ("actual_reader_authentication", "form_walkthrough", "private_source_review", "actual_private_export"):
        assert state[key] == "NOT_RUN", key
    for key in ("approval_instruments_examined", "missing_approvals_are_software_defects", "runtime_changed",
                "approval_or_appointment_issued", "messages_to_other_people_sent", "real_source_data_used",
                "biological_analysis_executed", "analysis_ready", "source_admission", "statistical_release",
                "frozen_specs_changed", "remote_job_started", "pushed"):
        assert state[key] is False, key
    assert state["new_software_defects_established"] == []
    with (HERE / "READINESS_CHECKLIST.tsv").open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert {r["check_id"] for r in rows} == {"C01", "C02", "C03", "R01", "R02", "R03", "R04", "R05", "P01", "P02", "P03", "P04", "T01"}
    assert len(rows) == 13 and all(all(r.values()) for r in rows)
    assert all(r["state"] in {"NOT_ESTABLISHED", "UNASSIGNED_IN_CHECKED_RECORDS"} for r in rows if r["stage"] == "S0")
    assert all(r["category"] != "SOFTWARE_DEFECT" for r in rows)
    search = load(HERE / "SEARCH_SCOPE.json")
    assert search["source_objects_opened"] is search["private_authorization_records_exported"] is False
    assert len(search["connected_searches"]) == 4 and "No global absence claim" in search["limits"]
    links = 0
    for path in HERE.iterdir():
        if not path.is_file():
            continue
        text = path.read_text()
        assert not re.search(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----|https?://[^\s/]+:[^\s/@]+@|[?&](?:access_token|X-Amz-Signature)=", text, re.I)
        assert all(line.rstrip() == line for line in text.splitlines()), path.name
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("http:", "https:")):
                    continue
                assert (HERE / target.split("#", 1)[0]).resolve().is_file(), target
                links += 1
    for record in load(HERE / "ARTIFACT_HASHES.json")["files"]:
        path = HERE / record["path"]
        raw = path.read_bytes()
        assert len(raw) == record["bytes"] and hashlib.sha256(raw).hexdigest() == record["sha256"], path.name
    return {"status": "PASS_DOCUMENT_AND_PRESERVATION_CHECKS_ONLY",
            "source_review_readiness": "BLOCKED_UNKNOWN", "approval_authentication": "NOT_RUN",
            "preserved_files_checked": len(preserved), "preserved_files_changed": 0,
            "readiness_requirements_checked": len(rows), "local_links_checked": links,
            "new_software_defects_established": [], "frozen_specs_changed": False,
            "real_source_data_used": False, "biological_analysis_executed": False,
            "source_admission": False, "statistical_release": False, "remote_job_started": False}


if __name__ == "__main__":
    result = verify()
    (HERE / "VERIFICATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
