"""Verify this synthetic training rule and document preservation; no source input."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTER = ROOT.parents[1]
STATES = {"SUPPORTED", "UNRESOLVED", "CONFLICTING", "NOT_IN_INSPECTED_OBJECTS"}


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def checked(record):
    path = OUTER / record["path"]
    assert path.resolve().is_relative_to(OUTER) and not path.is_symlink()
    raw = path.read_bytes()
    assert len(raw) == record["bytes"], record["path"]
    assert hashlib.sha256(raw).hexdigest() == record["sha256"], record["path"]
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


def summarize(meaning, assessment):
    if meaning not in STATES or assessment not in STATES:
        raise ValueError("Unknown training disposition")
    if "CONFLICTING" in (meaning, assessment):
        return "CONFLICTING"
    if meaning == assessment == "SUPPORTED":
        return "SUPPORTED"
    if meaning == assessment == "NOT_IN_INSPECTED_OBJECTS":
        return "NOT_IN_INSPECTED_OBJECTS"
    return "UNRESOLVED"


def exercise(form, examples):
    assert examples["classification"] == "SYNTHETIC_ONLY"
    assert examples["expected_actual_use_authorized"] is False
    cases = examples["cases"]
    assert len(cases) == len({c["case_id"] for c in cases}) == 8
    rule = form["endpoint_rule"]
    results = []
    for case in cases:
        components = {key: case[key] for key in ("meaning_disposition", "assessment_disposition", "episode_link_disposition")}
        assert all(value in STATES for value in components.values())
        summary = summarize(components["meaning_disposition"], components["assessment_disposition"])
        complete = all(value == "SUPPORTED" for value in components.values())
        assert summary == case["expected_summary"], case["case_id"]
        assert complete is case["expected_components_supported"], case["case_id"]
        components.update(summary_scope=rule["summary_scope"], episode_question_reference="episode_bindings", actual_use_authorized=False)
        assert set(components) == set(rule["required_endpoint_fields"])
        results.append({"case_id": case["case_id"], "endpoint_disposition": summary, "endpoint_components": components, "all_three_training_components_supported": complete, "check": "PASSED"})
    for invalid in ("", "ADMITTED"):
        try:
            summarize(invalid, "SUPPORTED")
        except ValueError:
            pass
        else:
            raise AssertionError("Unknown disposition accepted")
    return {"classification": "SYNTHETIC_ONLY", "scope": "LOCAL_TRAINING_COMPONENT_RULE_ONLY", "cases_passed": len(results), "actual_use_authorized": False, "real_source_data_used": False, "biological_analysis_run": False, "cases": results}


def verify():
    bindings = load(HERE / "BINDINGS.json")
    protected = preserved_files(bindings)
    assert len(protected) == len({r["path"] for r in protected}) == 2280
    for record in protected + bindings["input_documents"]:
        checked(record)
    form = load(HERE / "FORM_V3.json")
    prior = load(HERE.parent / "A_DAV_PRAT_SYNTHETIC_WALKTHROUGH_02/FORM_V2.json")
    assert form["classification"] == "SYNTHETIC_ONLY" and form["version"] == "form-v3"
    assert form["questions"] == prior["questions"] and len(form["questions"]) == 7
    for key in ("required_per_assertion", "required_top_level", "subclaim_fields", "subclaim_kinds"):
        assert form[key] == prior[key], key
    rule = form["endpoint_rule"]
    assert set(rule["allowed_component_dispositions"]) == STATES
    assert rule["summary_scope"] == "NATIVE_ENDPOINT_MEANING_AND_ASSESSMENT"
    assert rule["episode_question_reference"] == "episode_bindings" and rule["actual_use_authorized"] is False
    results = exercise(form, load(HERE / "TRAINING_EXAMPLES.json"))
    assert results == load(HERE / "SCOPE_CHECK_RESULTS.json")
    status = load(HERE / "STATUS.json")
    assert status["training_endpoint_scope"] == "SETTLED" and status["source_readiness"] == "BLOCKED_UNKNOWN"
    for key in ("actual_source_approval", "actual_reader_appointments"):
        assert status[key] == "PENDING_NOT_ESTABLISHED"
    for key in ("frozen_specs_changed", "runtime_changed", "real_source_data_used", "biological_analysis_run", "source_admitted", "pushed"):
        assert status[key] is False
    hashes = load(HERE / "ARTIFACT_HASHES.json")["files"]
    expected = {p.name for p in HERE.iterdir() if p.is_file()} - {"ARTIFACT_HASHES.json", "VERIFICATION.json"}
    assert {Path(r["path"]).name for r in hashes} == expected and len(hashes) == len(expected)
    for record in hashes:
        assert checked(record).parent == HERE
    for path in HERE.glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" not in target:
                assert (path.parent / target.split("#")[0]).exists(), (path.name, target)
    report = {"status": "PASSED", "classification": "SYNTHETIC_ONLY", "training_boundary_cases_passed": results["cases_passed"], "protected_prior_files_unchanged": len(protected), "bound_input_documents": len(bindings["input_documents"]), "current_packet_files_hash_checked": len(hashes), "original_seven_question_texts_unchanged": True, "actual_source_review": "NOT_RUN", "actual_use_authorized": False, "runtime_tests_current": "NOT_RERUN_RUNTIME_UNCHANGED", "real_source_data_used": False, "biological_analysis_run": False}
    write(HERE / "VERIFICATION.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
