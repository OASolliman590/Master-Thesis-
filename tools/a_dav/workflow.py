"""Connected synthetic DAV stages; no network, source inspection or analysis."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.a_dav.core import DavError, SchemaStore, finish, require, stage_boundary, verification_run
from tools.a_dav.search_log import validate_search_log
from tools.a_dav.study_resolution import resolve
from tools.a_dav.registries import build_registries
from tools.a_dav.endpoints import map_endpoints
from tools.a_dav.timing import validate_timing
from tools.a_dav.assays import validate_assays
from tools.a_dav.overlap import validate_overlap
from tools.a_dav.exposure import validate_exposure
from tools.a_dav.admission import evaluate_admission
from tools.a_dav.matrices import build_baseline, build_longitudinal
from tools.a_dav.release import validate_split, freeze_bundle
from tools.a_dav.reporting import build_public_report

REASON_CODES = frozenset({"DISCOVERY_INCOMPLETE", "CONTEXT_MISMATCH", "SOURCE_BYTES_MISMATCH",
                          "SOURCE_OBJECT_INCOMPLETE", "EXISTING_API_REJECTED", "MATRIX_BYTES_MISMATCH"})
MATRIX_PAYLOAD_FIELDS = ("headers", "features", "values", "unit", "transform", "annotation", "platform", "modality")


@stage_boundary("existing_seams")
def run_existing_seams(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    """Reuse T01–03 against provided invented catalogue packets and complete bytes."""
    assert schemas is not None
    config = packet["config"].get("existing_seams")
    require(isinstance(config, dict), "MISSING_ASSERTION", blocked=True)
    try:
        runs = validate_search_log(config["search_runs"])
        require(bool(runs), "MISSING_ASSERTION", blocked=True)
        require(all(run["completion_status"] == "COMPLETE" for run in runs),
                "DISCOVERY_INCOMPLETE", blocked=True)
        queries = {run["query_id"] for run in runs}
        study_schema = json.loads((schemas.root / "study_registry.schema.json").read_text())
        publication_schema = json.loads((schemas.root / "publication_family.schema.json").read_text())
        resolved = resolve(config["candidate_packets"], config["resolution_decision"], queries,  # type: ignore[no-untyped-call]
                           study_schema, publication_schema)
        proposed = {row["study_id"]: row for row in packet["records"].get("study_registry", [])}
        actual = {row["study_id"]: row for row in resolved["study_records"]}
        require(bool(actual) and actual == proposed, "CONTEXT_MISMATCH")
        require(sorted(resolved["publication_records"], key=lambda row: row["publication_id"]) ==
                sorted(packet["records"].get("publication_family", []), key=lambda row: row["publication_id"]),
                "CONTEXT_MISMATCH")
        sources = packet["records"].get("source_record", [])
        require(bool(sources), "SOURCE_OBJECT_INCOMPLETE", blocked=True)
        payloads = config["source_payloads"]
        require(set(payloads) == {row["source_object_id"] for row in sources}, "CONTEXT_MISMATCH")
        for source in sources:
            require(source["study_id"] in actual and
                    source["publication_family_id"] == actual[source["study_id"]]["publication_family_id"],
                    "CONTEXT_MISMATCH")
            encoded = payloads[source["source_object_id"]]
            require(isinstance(encoded, str) and len(encoded) <= 2 * 1024 * 1024, "MALFORMED_INPUT")
            content = bytes.fromhex(encoded)
            marker = packet["classification"].encode("ascii") + b"\n"
            require(content.startswith(marker), "SYNTHETIC_ONLY_REQUIRED")
            require(source.get("hash_scope") == "FULL_OBJECT" and source.get("retrieval_status") == "RETRIEVED",
                    "SOURCE_OBJECT_INCOMPLETE", blocked=True)
            require(source.get("sha256") == hashlib.sha256(content).hexdigest() and
                    source.get("byte_size") == len(content), "SOURCE_BYTES_MISMATCH")
            matrices = [m for m in packet["config"].get("assays", {}).get("matrices", [])
                        if m.get("source_object_id") == source["source_object_id"]]
            if matrices:
                require(len(matrices) == 1, "MATRIX_BYTES_MISMATCH")
                parsed = json.loads(content.removeprefix(marker))
                expected = {key: matrices[0][key] for key in MATRIX_PAYLOAD_FIELDS}
                require(parsed == {"assay_matrix": expected}, "MATRIX_BYTES_MISMATCH")
    except DavError:
        raise
    except (ValueError, KeyError, TypeError):
        raise DavError("EXISTING_API_REJECTED") from None
    return finish("existing_seams", packet, copy.deepcopy(packet["records"]),
                  audit=[{"ticket": "DAV-T01", "scope": "INVENTED_DISCOVERY"},
                         {"ticket": "DAV-T02", "scope": "INVENTED_RESOLUTION"},
                         {"ticket": "DAV-T03", "scope": "INVENTED_COMPLETE_BYTES"}], schemas=schemas)


@stage_boundary("workflow")
def run_workflow(packet: dict[str, Any], destination: Path | None = None, *,
                 schemas: SchemaStore | None = None) -> dict[str, Any]:
    """Run the connected synthetic DAG, stopping before any blocked descendant.

    Existing dependency claims are discarded. Every receipt used here comes from
    an actual stage invocation in this run. Freeze writes only on explicit Path.
    """
    assert schemas is not None
    with verification_run():
        current = copy.deepcopy(packet)
        current["dependencies"] = {}
        audit: list[dict[str, Any]] = []
        functions = (run_existing_seams, build_registries, map_endpoints, validate_timing, validate_assays,
                     validate_overlap, validate_exposure, evaluate_admission, validate_split, build_baseline,
                     build_longitudinal, build_public_report)
        for function in functions:
            result = function(current, schemas=schemas)
            audit.append({"stage": result["stage"], "status": result["status"],
                          "reasons": result["reasons"], "receipt_id": result["receipt_id"],
                          "checks": result["audit"]})
            current["records"] = result["records"]
            if result["status"] != "READY":
                return finish("workflow", current, current["records"], status=result["status"],
                              reasons=result["reasons"], audit=audit, schemas=schemas)
            current["dependencies"][result["stage"]] = result
        if destination is not None:
            result = freeze_bundle(current, destination, schemas=schemas)
            audit.append({"stage": result["stage"], "status": result["status"],
                          "reasons": result["reasons"], "receipt_id": result["receipt_id"]})
            return finish("workflow", current, result["records"], status=result["status"],
                          reasons=result["reasons"], audit=audit, schemas=schemas)
        return finish("workflow", current, current["records"], audit=audit, schemas=schemas)
