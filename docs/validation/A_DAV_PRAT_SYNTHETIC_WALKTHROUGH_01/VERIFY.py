"""Verify invented reader artifacts and preservation, without source access."""
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


def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(record):
    path = (OUTER / record["path"]).resolve()
    assert path.is_relative_to(OUTER)
    assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], record["path"]
    return path


def verify():
    binding = load(HERE / "BINDINGS.json")
    readiness = load(check(binding["prior_readiness_bindings"]))
    plan = load(check(readiness["prior_plan_bindings"]))
    baseline = load(check(plan["prior_preservation_baseline"]))
    protected = baseline["files"] + plan["additional_protected_files"] + readiness["additional_protected_files"] + binding["additional_protected_files"]
    assert len(protected) == len({r["path"] for r in protected}) == 2237
    for record in protected + binding["input_documents"]:
        check(record)
    lock = load(HERE / "BASIS_LOCK.json")
    assert lock["sequence"] == 1 and lock["base_commit"] == binding["base_commit"]
    assert lock["policy_locked_before_reader_dispatch"] is True
    for name, expected in lock["files_sha256"].items():
        assert sha(HERE / name) == expected, name
    book, form = load(HERE / "CASEBOOK_V1.json"), load(HERE / "FORM_V1.json")
    assert book["classification"] == form["classification"] == "SYNTHETIC_ONLY"
    with (ROOT / "docs/evidence/A_DAV_PRAT_SOURCE_REVIEW_PLAN_01/REVIEW_QUESTIONS.tsv").open() as f:
        questions = {row["question_id"] for row in csv.DictReader(f, delimiter="\t")}
    assert {q["question_id"] for q in form["questions"]} == questions and len(questions) == 7
    cases = {case["case_id"]: case for case in book["cases"]}
    assert set(cases) == {"INV-C01", "INV-C02", "INV-C03"}
    dispatch, opening = load(HERE / "DISPATCH.json"), load(HERE / "COMPARISON_OPEN.json")
    assert [r["sequence"] for r in dispatch["reader_dispatches"]] == [2, 3]
    assert all(r["fork_turns"] == "none" for r in dispatch["reader_dispatches"])
    assert opening["sequence"] == 4 and opening["both_seals_present_before_parent_read"] is True
    passes = []
    for directory, label in (("reader_a", "SYN-READER-A"), ("reader_b", "SYN-READER-B")):
        relative = directory + "/first_pass.json"
        path = HERE / relative
        seal = load(HERE / directory / "seal.json")
        assert seal["first_pass_path"] == relative and seal["sha256"] == sha(path)
        assert seal["byte_size"] == path.stat().st_size and seal["reader_label"] == label
        assert seal["seal_kind"] == "INVENTED_FORM_PILOT_NOT_AUTHENTICATED_SOURCE_REVIEW"
        row = next(r for r in opening["passes"] if r["path"] == relative)
        assert row["sha256"] == sha(path) and row["bytes"] == path.stat().st_size
        reader = load(path)
        assert reader["classification"] == "SYNTHETIC_ONLY" and reader["reader_label"] == label
        assert reader["peer_material_seen"] is reader["real_source_data_used"] is False
        for field, file in (("casebook_sha256", "CASEBOOK_V1.json"), ("form_sha256", "FORM_V1.json"), ("policy_sha256", "POLICY_V1.json")):
            assert reader[field] == lock["files_sha256"][file]
        assert {c["case_id"] for c in reader["cases"]} == set(cases) and len(reader["cases"]) == 3
        grouped = {}
        for case in reader["cases"]:
            source = cases[case["case_id"]]
            lines = {line["line_id"] for line in source["lines"]}
            assert len(case["assertions"]) == 7 and {a["question_id"] for a in case["assertions"]} == questions
            for assertion in case["assertions"]:
                assert set(assertion) == set(form["required_per_assertion"])
                assert assertion["object_id"] == source["object_id"]
                assert assertion["disposition"] in form["dispositions"]
                assert isinstance(assertion["line_ids"], list) and set(assertion["line_ids"]) <= lines
                assert assertion["assertion"] and assertion["reason"]
                assert bool(assertion["line_ids"]) == (assertion["disposition"] != "NOT_IN_INSPECTED_OBJECTS")
                grouped[(case["case_id"], assertion["question_id"])] = assertion
        passes.append(grouped)
    comparison = load(HERE / "COMPARISON.json")
    assert comparison["sequence"] == 5 and comparison["first_pass_bindings"] == opening["passes"]
    assert len(comparison["rows"]) == comparison["paired_question_assessments"] == 21
    assert {(r["case_id"], r["question_id"]) for r in comparison["rows"]} == set(passes[0])
    for row in comparison["rows"]:
        key = row["case_id"], row["question_id"]
        a, b = passes[0][key], passes[1][key]
        assert row["reader_a_disposition"] == a["disposition"] == row["reader_b_disposition"] == b["disposition"]
        assert row["exact_assertion_equal"] == (a == b)
        assert row["source_locators_equal"] == (a["line_ids"] == b["line_ids"])
        assert row["parent_rationale"] and row["actual_source_adjudication"] == "NOT_RUN"
    run = load(HERE / "PROTOCOL_TEST_RUN.json")
    assert run["exit_code"] == 0 and "33 passed" in (HERE / run["stdout_log"]).read_text()
    assert (HERE / run["stderr_log"]).read_text() == ""
    state = load(HERE / "STATUS.json")
    assert state["classification"] == "SYNTHETIC_ONLY" and state["synthetic_form_walkthrough"] == "COMPLETE"
    assert state["source_readiness"] == "BLOCKED_UNKNOWN"
    assert state["actual_source_custody_approval"] == state["actual_reader_appointments"] == "PENDING_NOT_ESTABLISHED"
    for field in ("actual_appointed_reader_familiarization", "actual_reader_authentication", "actual_source_review", "actual_source_adjudication", "actual_private_export"):
        assert state[field] == "NOT_RUN", field
    for field in ("runtime_changed", "frozen_specs_changed", "real_source_data_used", "analysis_ready", "source_admission", "statistical_release", "biological_analysis_executed", "remote_job_started", "pushed"):
        assert state[field] is False, field
    assert state["new_software_defects_established"] == []
    assert state["form_clarifications"] == "DOCUMENTED_NOT_REPILOTED"
    links = 0
    for path in HERE.glob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
            if target.startswith(("http:", "https:")):
                continue
            assert (HERE / target.split("#", 1)[0]).resolve().is_file(), target
            links += 1
    for record in load(HERE / "ARTIFACT_HASHES.json")["files"]:
        path = HERE / record["path"]
        assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], record["path"]
    return {"status": "PASS_SYNTHETIC_WALKTHROUGH_AND_PRESERVATION_CHECKS_ONLY", "classification": "SYNTHETIC_ONLY",
            "invented_cases": 3, "sealed_synthetic_passes": 2, "paired_question_assessments": 21,
            "existing_protocol_tests_passed": 33, "local_links_checked": links,
            "preserved_files_checked": len(protected), "preserved_files_changed": 0,
            "source_readiness": "BLOCKED_UNKNOWN", "actual_source_authentication": "NOT_RUN",
            "real_source_data_used": False, "biological_analysis_executed": False,
            "frozen_specs_changed": False, "source_admission": False, "statistical_release": False}


if __name__ == "__main__":
    report = verify()
    (HERE / "VERIFICATION.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
