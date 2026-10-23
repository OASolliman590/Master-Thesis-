"""Check the planning packet and preservation; never run source-review software."""
import ast
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


def digest(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_record(record):
    path = (OUTER / record["path"]).resolve()
    assert path.is_relative_to(OUTER), record["path"]
    assert path.stat().st_size == record["bytes"] and digest(path) == record["sha256"], record["path"]
    return path


def table(name):
    with (HERE / name).open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert rows and all(all(isinstance(value, str) and value for value in row.values()) for row in rows)
    return rows


def verify():
    binding = load(HERE / "BINDINGS.json")
    assert binding["document_kind"] == "SOURCE_REVIEW_PLAN_NOT_SOURCE_EVIDENCE"
    baseline_path = check_record(binding["prior_preservation_baseline"])
    protected = {item["path"]: item for item in load(baseline_path)["files"]}
    for item in binding["additional_protected_files"]:
        assert item["path"] not in protected
        protected[item["path"]] = item
    for item in list(protected.values()) + binding["input_documents"]:
        check_record(item)
    assert len(protected) == 2212
    assert binding["frozen_specs_edited"] is binding["runtime_edited"] is binding["real_source_objects_inspected"] is False
    state = load(HERE / "STATUS.json")
    assert state["classification"] == "PLANNING_ONLY"
    assert state["status"] == "PLAN_COMPLETE_SOURCE_REVIEW_NOT_RUN"
    assert state["base_commit"] == binding["base_commit"]
    assert state["source_candidate"] == "Prat-GSE93157" and state["branch_id"] == "A_BASELINE_BIO"
    assert state["canonical_study_id"] is state["canonical_publication_family_id"] is None
    assert state["inventory_kind"] == "EVIDENCE_REQUIREMENT_ROLES_NOT_VERIFIED_OBJECTS"
    assert state["source_object_completeness"] == "UNKNOWN" and state["reader_appointments"] == "UNASSIGNED"
    assert state["source_readiness"] == "BLOCKED_UNKNOWN"
    for key in ("two_reader_first_passes", "reader_authentication", "adjudication", "actual_private_export", "source_download", "form_walkthrough"):
        assert state[key] == "NOT_RUN", key
    for key in ("real_source_data_used", "analysis_ready", "source_admission", "statistical_release",
                "biological_analysis_executed", "frozen_specs_changed", "remote_job_started",
                "source_objects_inspected", "software_changes", "pushed"):
        assert state[key] is False, key
    inventory = table("INVENTORY_REQUIREMENTS.tsv")
    assert {row["requirement_id"] for row in inventory} == {f"IR{i:02d}" for i in range(1, 11)}
    assert len(inventory) == 10
    assert all(row["planning_state"] in {"NOT_REVERIFIED", "NOT_ESTABLISHED", "NOT_REASSESSED"} for row in inventory)
    assert all(row["artifact_class"] in {"SOURCE_OBJECT_REQUIREMENT", "AUTHORIZED_RECORD_REQUIREMENT"} for row in inventory)
    assert {item for row in inventory for item in row["evidence_ids"].split(",")} == {f"E{i:02d}" for i in range(1, 9)}
    questions = table("REVIEW_QUESTIONS.tsv")
    code = ast.parse((ROOT / "tools/a_dav/prat_review.py").read_text())
    question_node = next(node for node in code.body if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == "CURRENT_QUESTIONS" for target in node.targets))
    expected_questions = ast.literal_eval(question_node.value.args[0])
    assert len(questions) == 7 and {row["question_id"] for row in questions} == expected_questions
    dispositions = table("EVIDENCE_SOFTWARE_DISPOSITION.tsv")
    assert len(dispositions) == 10 and {row["evidence_id"] for row in dispositions} == {f"E{i:02d}" for i in range(1, 11)}
    assert {item for row in dispositions for item in row["procedure_gap_ids"].split(",") if item != "NONE"} == {f"P{i:02d}" for i in range(1, 9)}
    assert next(row for row in dispositions if row["evidence_id"] == "E09")["current_state"] == "DEFERRED_NAMED_METHOD_USE"
    assert next(row for row in dispositions if row["evidence_id"] == "E10")["current_state"] == "ADMISSION_AND_RELEASE_NOT_REQUESTED_OR_ESTABLISHED"
    assert state["software_status"] == "NO_NEW_DEFECT_ESTABLISHED"
    links = 0
    for path in HERE.glob("*.md"):
        text = path.read_text()
        assert not re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|https?://[^\s/]+:[^\s/@]+@", text)
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("https:", "http:")):
                continue
            assert (path.parent / target.split("#", 1)[0]).resolve().is_file(), (path.name, target)
            links += 1
    for item in load(HERE / "ARTIFACT_HASHES.json")["files"]:
        path = HERE / item["path"]
        assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], item["path"]
    return {"status": "PASS_PLANNING_AND_PRESERVATION_CHECKS_ONLY", "classification": "PLANNING_ONLY",
            "source_candidate": "Prat-GSE93157", "branch_id": "A_BASELINE_BIO",
            "preserved_files_checked": len(protected), "preserved_files_changed": 0,
            "input_documents_bound": len(binding["input_documents"]), "local_links_checked": links,
            "inventory_requirement_roles": len(inventory), "actual_object_inventory": "NOT_REVERIFIED",
            "review_questions": len(questions), "evidence_gaps_covered": 10, "procedure_gaps_covered": 8,
            "source_review": "NOT_RUN", "form_walkthrough": "NOT_RUN", "source_readiness": "BLOCKED_UNKNOWN",
            "new_software_defects_established": [], "runtime_tests_executed": [],
            "real_source_data_used": False, "biological_analysis_executed": False,
            "source_admission": False, "statistical_release": False, "frozen_specs_changed": False}


if __name__ == "__main__":
    report = verify()
    (HERE / "VERIFICATION.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
