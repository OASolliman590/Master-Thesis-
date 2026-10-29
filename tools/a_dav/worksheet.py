"""Build and consume branch-scoped source reviewer worksheets."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, cast

from .core import DavError, ENTITY_TABLES, canonical_bytes, digest, require

GATE_QUESTIONS = {
    "V0": "Was this candidate discovered from a recorded query or source locator?",
    "V1": "Are the originating study, publication family, and aliases resolved?",
    "V2": "Is each exact source object, version, access route, and complete-byte hash verified?",
    "V3": "Are measurement modality, platform, unit, transform, feature IDs, and structure understood?",
    "V4": "Are sample-to-patient and sample-to-specimen links supported, with replicates resolved?",
    "V5": "Are endpoint, treatment, and collection timing supported by source evidence?",
    "V6": "Are overlap and prior exposure reviewed and dispositioned?",
    "V7": "Does the evidence support admission to this named branch?",
    "V8": "Has the branch matrix been built, tested, and structurally validated?",
}
DECISIONS = frozenset({"PASS", "FAIL", "BLOCKED_UNKNOWN", "NOT_APPLICABLE", "SUPERSEDED"})
SIGNATURE_DERIVED_RECORD_FIELDS = frozenset({"reviewer", "review_date", "reviewed_utc"})


def _context_entity_records(records: dict[str, Any]) -> dict[str, list[Any]]:
    """Hash reviewed facts without binding them to the signer's identity or date."""
    context_records: dict[str, list[Any]] = {}
    for table in sorted(ENTITY_TABLES):
        normalized = []
        for value in records.get(table, []):
            if isinstance(value, dict):
                row = copy.deepcopy(value)
                for field in SIGNATURE_DERIVED_RECORD_FIELDS:
                    row.pop(field, None)
                normalized.append(row)
            else:
                normalized.append(copy.deepcopy(value))
        context_records[table] = sorted(normalized, key=canonical_bytes)
    return context_records


def _ingestion_items(packet: dict[str, Any]) -> list[dict[str, Any]]:
    value = packet.get("config", {}).get("admission", {}).get("ingestion_worksheet", [])
    if isinstance(value, dict):
        value = value.get("items", [])
    require(isinstance(value, list), "WORKSHEET_INPUT_INVALID")
    items = []
    occurrences: dict[str, int] = {}
    for row in value:
        require(isinstance(row, dict) and isinstance(row.get("category"), str), "WORKSHEET_INPUT_INVALID")
        pointers = row.get("evidence_pointers", [])
        require(isinstance(pointers, list) and all(isinstance(pointer, dict) for pointer in pointers),
                "WORKSHEET_INPUT_INVALID")
        status = row.get("status", "BLOCKED_UNKNOWN")
        require(status in DECISIONS, "WORKSHEET_INPUT_INVALID")
        item = {"kind": "ingestion", "category": row["category"], "question": row["category"].replace("_", " ").lower(),
                "status": status, "evidence_pointers": pointers}
        if "context" in row:
            item["context"] = row["context"]
        base_id = digest(item)
        occurrence = occurrences.get(base_id, 0)
        occurrences[base_id] = occurrence + 1
        item["item_id"] = "I-" + digest({"item": base_id, "occurrence": occurrence})[:20]
        items.append(item)
    return items


def build_worksheet(packet: dict[str, Any]) -> dict[str, Any]:
    """Create unsigned questions bound to one study, branch, configuration, and source set."""
    require(isinstance(packet, dict) and isinstance(packet.get("records"), dict), "WORKSHEET_INPUT_INVALID")
    branch = packet.get("branch_id")
    require(isinstance(branch, str) and bool(branch), "WORKSHEET_INPUT_INVALID")
    config = packet.get("config", {})
    require(isinstance(config, dict), "WORKSHEET_INPUT_INVALID")
    config = cast(dict[str, Any], config)
    sources = sorted(({
        "source_object_id": source.get("source_object_id"),
        "sha256": source.get("sha256"),
        "access_route": source.get("access_route", source.get("access_status")),
        "exact_file_name": source.get("exact_file_name"),
        "source_locators": source.get("source_locators", []),
        "source_version": source.get("source_version"),
    } for source in packet["records"].get("source_record", [])), key=lambda row: str(row["source_object_id"]))
    studies = packet["records"].get("study_registry", [])
    study_ids = sorted({row.get("study_id") for row in studies if isinstance(row.get("study_id"), str)})
    require(len(study_ids) == 1, "WORKSHEET_STUDY_AMBIGUOUS")
    ingestion = _ingestion_items(packet)
    items = list(ingestion)
    admission = config.get("admission", {})
    prefill = admission.get("worksheet_prefill", {}) if isinstance(admission, dict) else {}
    require(isinstance(prefill, dict), "WORKSHEET_PREFILL_INVALID")
    default_status = prefill.get("default_status", "BLOCKED_UNKNOWN")
    require(default_status in DECISIONS, "WORKSHEET_PREFILL_INVALID")
    source_prefill = prefill.get("source_items", {})
    gate_prefill = prefill.get("gates", {})
    require(isinstance(source_prefill, dict) and isinstance(gate_prefill, dict), "WORKSHEET_PREFILL_INVALID")
    gate_tables = {
        "V0": ("source_record",), "V1": ("study_registry", "publication_family"),
        "V2": ("source_record",), "V3": ("assay_registry",),
        "V4": ("patient_registry", "specimen_registry"),
        "V5": ("clinical_outcome", "treatment_episode", "episode_binding"),
        "V6": ("overlap_edge", "prior_exposure_record"),
        "V7": ("source_record",), "V8": ("matrix_build_receipt",),
    }
    for gate, question in GATE_QUESTIONS.items():
        evidence: list[dict[str, Any]] = []
        for table in gate_tables[gate]:
            rows = packet["records"].get(table, [])
            locators = [locator for row in rows for locator in row.get("source_locators", [])]
            evidence.extend({"table": table, "locator": locator} for locator in locators)
            if not locators:
                evidence.append({"table": table})
        row = {"kind": "gate", "gate": gate, "question": question, "evidence_pointers": evidence}
        row["item_id"] = gate
        items.append(row)
    for item in items:
        decisions = gate_prefill if item.get("kind") == "gate" else source_prefill
        key = item.get("gate") if item.get("kind") == "gate" else item.get("category")
        value = decisions.get(key, {}) if isinstance(key, str) else {}
        require(isinstance(value, dict), "WORKSHEET_PREFILL_INVALID")
        status = value.get("status", default_status)
        require(status in DECISIONS, "WORKSHEET_PREFILL_INVALID")
        pointers = item["evidence_pointers"] + value.get("evidence_pointers", [])
        require(isinstance(pointers, list) and all(isinstance(pointer, dict) for pointer in pointers),
                "WORKSHEET_PREFILL_INVALID")
        pointers = list({canonical_bytes(pointer): pointer for pointer in pointers}.values())
        decision = value.get("decision", "Awaiting reviewer disposition.")
        require(isinstance(decision, str) and decision.strip(), "WORKSHEET_PREFILL_INVALID")
        item["prefilled_decision"] = {"status": status, "decision": decision,
                                      "evidence_pointers": pointers}
    bound_config = copy.deepcopy(config)
    if isinstance(bound_config, dict) and isinstance(bound_config.get("admission"), dict):
        bound_config["admission"].pop("reviewer_worksheet", None)
        bound_config["admission"].pop("worksheet_created_utc", None)
    context = {
        "study_id": study_ids[0], "branch_id": branch,
        "config_hash": digest(bound_config), "sources": sources,
        "entity_records_hash": digest(_context_entity_records(packet["records"])),
        "ingestion_items_hash": digest(ingestion),
    }
    context_hash = digest(context)
    created = config.get("admission", {}).get("worksheet_created_utc")
    if not isinstance(created, str) or not created:
        created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {"schema_version": "1", "worksheet_id": "worksheet-" + context_hash[:24],
            "created_utc": created, "context": context, "context_hash": context_hash,
            "items": items, "review_status": "UNSIGNED", "reviewer_name": "", "review_date": "",
            "signature_placeholder": "Awaiting the user's named reviewer and actual sign-off."}


def validate_signed_worksheet(packet: dict[str, Any], worksheet: dict[str, Any]) -> dict[str, Any]:
    """Validate signature fields, exact worksheet binding, and a complete decision set."""
    expected = build_worksheet(packet)
    for key in ("worksheet_id", "context", "context_hash", "items"):
        require(worksheet.get(key) == expected.get(key), "WORKSHEET_CONTEXT_MISMATCH")
    signature = worksheet.get("signature")
    decisions = worksheet.get("decisions")
    require(isinstance(signature, dict), "WORKSHEET_UNSIGNED", blocked=True)
    signature = cast(dict[str, Any], signature)
    reviewer = signature.get("reviewer_name")
    review_date = signature.get("review_date")
    require(isinstance(reviewer, str) and reviewer.strip() and isinstance(review_date, str),
            "WORKSHEET_UNSIGNED", blocked=True)
    reviewer = cast(str, reviewer)
    review_date = cast(str, review_date)
    try:
        date.fromisoformat(review_date)
    except ValueError:
        raise DavError("WORKSHEET_UNSIGNED", blocked=True) from None
    decision_status = {row.get("item_id"): row.get("status") for row in decisions
                       if isinstance(row, dict)} if isinstance(decisions, list) else {}
    for row in packet["records"].get("episode_binding", []):
        if isinstance(row, dict) and row.get("binding_status") == "VERIFIED":
            require(row.get("reviewer") == reviewer.strip() and row.get("reviewed_utc") == review_date,
                    "WORKSHEET_SIGNATURE_RECORD_MISMATCH")
    if decision_status.get("V6") == "PASS":
        for row in packet["records"].get("overlap_edge", []):
            if isinstance(row, dict):
                record_reviewer, record_date = row.get("reviewer"), row.get("review_date")
                if record_reviewer not in (None, "") or record_date not in (None, ""):
                    require(record_reviewer == reviewer.strip() and record_date == review_date,
                            "WORKSHEET_SIGNATURE_RECORD_MISMATCH")
        for row in packet["records"].get("prior_exposure_record", []):
            if isinstance(row, dict):
                record_reviewer = row.get("reviewer")
                if record_reviewer not in (None, ""):
                    require(record_reviewer == reviewer.strip(), "WORKSHEET_SIGNATURE_RECORD_MISMATCH")
    public_routes = {"PUBLIC_DIRECT", "PUBLIC_LANDING"}
    public_only = bool(packet["records"].get("source_record")) and all(
        row.get("access_route") in public_routes for row in packet["records"].get("source_record", []))
    if not public_only:
        for name, date_key in (("source_reviewer_name", "source_review_date"),
                               ("integrator_name", "integration_date")):
            require(isinstance(signature.get(name), str) and signature[name].strip()
                    and isinstance(signature.get(date_key), str), "CONTROLLED_REVIEWERS_REQUIRED", blocked=True)
            try:
                date.fromisoformat(signature[date_key])
            except ValueError:
                raise DavError("CONTROLLED_REVIEWERS_REQUIRED", blocked=True) from None
    require(isinstance(decisions, list), "WORKSHEET_PARTIAL", blocked=True)
    decisions = cast(list[dict[str, Any]], decisions)
    require(all(isinstance(row, dict) for row in decisions), "WORKSHEET_CONTRADICTION")
    ids = [row.get("item_id") for row in decisions if isinstance(row, dict)]
    expected_ids = [row["item_id"] for row in expected["items"]]
    require(len(ids) == len(set(ids)), "WORKSHEET_CONTRADICTION")
    require(set(ids) == set(expected_ids), "WORKSHEET_PARTIAL", blocked=True)
    result: dict[str, Any] = {}
    for decision in decisions:
        status = decision.get("status")
        require(status in DECISIONS, "WORKSHEET_CONTRADICTION")
        if status in {"NOT_APPLICABLE", "SUPERSEDED"}:
            require(isinstance(decision.get("rationale"), str) and decision["rationale"].strip(),
                    "WORKSHEET_CONTRADICTION")
        result[decision["item_id"]] = status
    require(all(isinstance(row, dict) and isinstance(row.get("rationale", ""), str) for row in decisions),
            "WORKSHEET_CONTRADICTION")
    return {"reviewer_name": reviewer.strip(), "review_date": review_date,
            "source_reviewer_name": signature.get("source_reviewer_name", reviewer.strip()),
            "integrator_name": signature.get("integrator_name", reviewer.strip()),
            "signer_identity_status": "SELF_REPORTED",
            "decisions": result}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise DavError("WORKSHEET_FILE_INVALID") from None
    require(isinstance(value, dict), "WORKSHEET_FILE_INVALID")
    return cast(dict[str, Any], value)


def read_worksheet(path: Path) -> dict[str, Any]:
    """Read an unsigned or signed worksheet JSON document."""
    return _load_json(path)


def _safe_output_path(path: Path, *, allow_external_out: bool = False) -> Path:
    # Reuse ingestion's output boundary at call time to avoid an import cycle.
    from .ingest import IngestError, validate_output_path
    try:
        return validate_output_path(path, allow_external_out=allow_external_out)
    except IngestError as error:
        raise DavError(str(error)) from None


def write_worksheet(packet: dict[str, Any], path: Path, *, allow_external_out: bool = False) -> dict[str, Any]:
    """Build and persist the unsigned reviewer worksheet."""
    worksheet = build_worksheet(packet)
    output = _safe_output_path(path, allow_external_out=allow_external_out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(worksheet, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return worksheet


def worksheet_status(packet: dict[str, Any], worksheet: dict[str, Any]) -> str:
    """Return the review state without upgrading unsigned or partial input."""
    if worksheet.get("context_hash") != build_worksheet(packet).get("context_hash"):
        return "CONTEXT_MISMATCH"
    try:
        validate_signed_worksheet(packet, worksheet)
    except DavError as error:
        if error.code == "WORKSHEET_UNSIGNED":
            return "UNSIGNED"
        if error.code in {"WORKSHEET_PARTIAL", "CONTROLLED_REVIEWERS_REQUIRED"}:
            return "PARTIAL"
        return "CONTRADICTED"
    statuses = {row["status"] for row in worksheet["decisions"]}
    if "FAIL" in statuses:
        return "FAIL"
    if "BLOCKED_UNKNOWN" in statuses:
        return "BLOCKED_UNKNOWN"
    return "SIGNED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("--packet", required=True, type=Path)
    write.add_argument("--out", required=True, type=Path)
    admit = sub.add_parser("ingest-signed")
    admit.add_argument("--packet", required=True, type=Path)
    admit.add_argument("--worksheet", required=True, type=Path)
    admit.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        packet = _load_json(args.packet)
        if args.command == "write":
            result = write_worksheet(packet, args.out)
        else:
            _safe_output_path(args.out)
            result = read_worksheet(args.worksheet)
            validate_signed_worksheet(packet, result)
            from .admission import evaluate_admission
            result = evaluate_admission(packet, reviewer_worksheet=result)
        if args.command != "write":
            output = _safe_output_path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except DavError as error:
        parser.error(error.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
