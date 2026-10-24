"""Check the clarified synthetic rehearsal and preserved artifacts only."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTER = ROOT.parents[1]
PRIOR = HERE.parent / "A_DAV_PRAT_SYNTHETIC_WALKTHROUGH_01"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(record):
    path = (OUTER / record["path"]).resolve()
    assert path.is_relative_to(OUTER)
    assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], record["path"]
    return path


def preserved_files(binding):
    records = []
    while True:
        records.extend(binding.get("additional_protected_files", []))
        if "prior_preservation_baseline" in binding:
            records.extend(load(checked(binding["prior_preservation_baseline"]))["files"])
            return records
        keys = [key for key in ("prior_walkthrough_bindings", "prior_readiness_bindings", "prior_plan_bindings") if key in binding]
        assert len(keys) == 1
        binding = load(checked(binding[keys[0]]))


def verify():
    binding = load(HERE / "BINDINGS.json")
    protected = preserved_files(binding)
    assert len(protected) == len({r["path"] for r in protected}) == 2260
    for record in protected + binding["input_documents"]:
        checked(record)
    lock, form = load(HERE / "BASIS_LOCK.json"), load(HERE / "FORM_V2.json")
    book, policy = load(HERE / "CASEBOOK_V1.json"), load(HERE / "POLICY_V1.json")
    assert lock["sequence"] == 1 and lock["policy_and_form_locked_before_dispatch"] is True
    assert lock["base_commit"] == binding["base_commit"]
    for name, value in lock["files_sha256"].items():
        assert sha(HERE / name) == value, name
    for name in ("CASEBOOK_V1.json", "POLICY_V1.json"):
        assert (HERE / name).read_bytes() == (PRIOR / name).read_bytes()
    assert form["version"] == "form-v2" and form["questions"] == load(PRIOR / "FORM_V1.json")["questions"]
    assert form["classification"] == book["classification"] == policy["classification"] == "SYNTHETIC_ONLY"
    questions = {q["question_id"] for q in form["questions"]}
    cases = {c["case_id"]: c for c in book["cases"]}
    assert len(questions) == 7 and set(cases) == {"INV-C01", "INV-C02", "INV-C03"}
    dispatch, opening = load(HERE / "DISPATCH.json"), load(HERE / "COMPARISON_OPEN.json")
    assert [r["sequence"] for r in dispatch["reader_dispatches"]] == [2, 3]
    assert all(r["fork_turns"] == "none" for r in dispatch["reader_dispatches"])
    assert dispatch["prior_passes_provided_to_readers"] is False
    assert opening["sequence"] == 4 and opening["both_seals_present_before_parent_read"] is True
    readers = []
    absent = 0
    for directory, label in (("reader_a", "SYN-V2-A"), ("reader_b", "SYN-V2-B")):
        relative = directory + "/first_pass.json"
        path = HERE / relative
        seal, reader = load(HERE / directory / "seal.json"), load(path)
        assert seal["first_pass_path"] == relative and seal["sha256"] == sha(path)
        assert seal["byte_size"] == path.stat().st_size and seal["reader_label"] == label
        assert seal["seal_kind"] == "CLARIFIED_FORM_REHEARSAL_NOT_AUTHENTICATED_SOURCE_REVIEW"
        entry = next(r for r in opening["passes"] if r["path"] == relative)
        assert entry["sha256"] == sha(path) and entry["bytes"] == path.stat().st_size
        assert set(form["required_top_level"]) <= set(reader)
        assert reader["reader_label"] == label and reader["classification"] == "SYNTHETIC_ONLY"
        assert reader["peer_material_seen"] is reader["real_source_data_used"] is False
        assert reader["actual_source_approval"] == "PENDING_NOT_ESTABLISHED" and reader["actual_reader_authentication"] == "NOT_RUN"
        for field, file in (("casebook_sha256", "CASEBOOK_V1.json"), ("form_sha256", "FORM_V2.json"), ("policy_sha256", "POLICY_V1.json")):
            assert reader[field] == lock["files_sha256"][file]
        assert len(reader["cases"]) == 3 and {c["case_id"] for c in reader["cases"]} == set(cases)
        grouped = {}
        for case in reader["cases"]:
            source = cases[case["case_id"]]
            lines = {line["line_id"] for line in source["lines"]}
            assert len(case["assertions"]) == 7 and {a["question_id"] for a in case["assertions"]} == questions
            for assertion in case["assertions"]:
                assert set(assertion) == set(form["required_per_assertion"])
                assert assertion["object_id"] == source["object_id"] and assertion["disposition"] in form["dispositions"]
                assert set(assertion["line_ids"]) <= lines and assertion["assertion"] and assertion["reason"]
                assert assertion["support_scope"] and isinstance(assertion["remaining_gaps"], list) and assertion["remaining_gaps"]
                assert assertion["subclaims"]
                for claim in assertion["subclaims"]:
                    assert set(claim) == set(form["subclaim_fields"])
                    assert claim["kind"] in form["subclaim_kinds"] and claim["text"] and set(claim["line_ids"]) <= lines
                if assertion["disposition"] == "NOT_IN_INSPECTED_OBJECTS":
                    expected = {"INV-C01": "A5", "INV-C02": "B5", "INV-C03": "C4"}[case["case_id"]]
                    assert expected in assertion["line_ids"]
                    assert any(c["kind"] == "SCOPED_ABSENCE" and expected in c["line_ids"] for c in assertion["subclaims"])
                    absent += 1
                grouped[(case["case_id"], assertion["question_id"])] = assertion
        for key in (("INV-C01", "identity"), ("INV-C02", "episode_bindings")):
            assert {"CASE_FACT", "UNSUPPORTED_PROPOSAL"} <= {c["kind"] for c in grouped[key]["subclaims"]}
        assert {"HYPOTHETICAL_ALTERNATIVE", "UNRESOLVED_GAP"} <= {c["kind"] for c in grouped[("INV-C03", "episode_bindings")]["subclaims"]}
        assert grouped[("INV-C03", "episode_bindings")]["disposition"] == "UNRESOLVED"
        assert any("header" in gap.lower() for gap in grouped[("INV-C02", "patient_specimen_assay")]["remaining_gaps"])
        readers.append(grouped)
    assert absent == 26
    comparison = load(HERE / "COMPARISON.json")
    assert comparison["sequence"] == 5 and comparison["first_pass_bindings"] == opening["passes"]
    assert len(comparison["rows"]) == 21 and {(r["case_id"], r["question_id"]) for r in comparison["rows"]} == set(readers[0])
    different = []
    for row in comparison["rows"]:
        key = row["case_id"], row["question_id"]
        a, b = readers[0][key], readers[1][key]
        assert row["reader_a_disposition"] == a["disposition"] and row["reader_b_disposition"] == b["disposition"]
        assert row["same_disposition"] == (a["disposition"] == b["disposition"])
        assert row["exact_record_equal"] == (a == b)
        assert row["parent_rationale"] and row["actual_source_adjudication"] == "NOT_RUN"
        if not row["same_disposition"]:
            different.append(key)
            assert row["parent_review"] == "CODING_SCOPE_DIFFERENCE_RETAINED"
    assert different == [("INV-C02", "endpoint")]
    assert comparison["same_disposition_pairs"] == 20 and comparison["different_disposition_pairs"] == 1
    assert {r["clarification_id"] for r in comparison["clarification_checks"]} == {"F1", "F2", "F3", "F4"}
    prior_test = load(PRIOR / "PROTOCOL_TEST_RUN.json")
    assert prior_test["exit_code"] == 0 and "33 passed" in (PRIOR / prior_test["stdout_log"]).read_text()
    state = load(HERE / "STATUS.json")
    assert state["classification"] == "SYNTHETIC_ONLY" and state["synthetic_form_rehearsal"] == "COMPLETE"
    assert state["source_readiness"] == "BLOCKED_UNKNOWN"
    assert state["actual_source_approval"] == state["actual_reader_appointments"] == "PENDING_NOT_ESTABLISHED"
    for field in ("actual_appointed_reader_familiarization", "actual_reader_authentication", "actual_source_review", "actual_source_adjudication", "actual_private_export"):
        assert state[field] == "NOT_RUN", field
    for field in ("runtime_changed", "frozen_specs_changed", "real_source_data_used", "analysis_ready", "source_admission", "statistical_release", "biological_analysis_executed", "remote_job_started", "pushed"):
        assert state[field] is False, field
    assert state["new_software_defects_established"] == []
    for record in load(HERE / "ARTIFACT_HASHES.json")["files"]:
        path = HERE / record["path"]
        assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], record["path"]
    links = 0
    for path in HERE.glob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
            if target.startswith(("http:", "https:")):
                continue
            assert (HERE / target.split("#", 1)[0]).resolve().is_file(), target
            links += 1
    return {"status": "PASS_SYNTHETIC_REHEARSAL_AND_PRESERVATION_CHECKS_ONLY", "form_version": "form-v2",
            "sealed_synthetic_passes": 2, "paired_questions": 21, "same_disposition_pairs": 20,
            "retained_coding_differences": 1, "explicit_absence_citations": absent,
            "preserved_files_checked": len(protected), "preserved_files_changed": 0, "local_links_checked": links,
            "runtime_tests_this_rehearsal": "NOT_RERUN", "prior_protocol_tests_retained": 33,
            "source_readiness": "BLOCKED_UNKNOWN", "real_source_data_used": False,
            "frozen_specs_changed": False, "biological_analysis_executed": False,
            "source_admission": False, "statistical_release": False}


if __name__ == "__main__":
    result = verify()
    (HERE / "VERIFICATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
