"""Verify exact software/receipt bytes and preservation without running source code."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTER = ROOT.parent.parent


def verify() -> dict[str, object]:
    baseline = json.loads((HERE / "PRESERVATION_BASELINE.json").read_text())
    for row in baseline["files"]:
        path = (OUTER / row["path"]).resolve()
        assert path.is_relative_to(OUTER), row["path"]
        raw = path.read_bytes()
        assert len(raw) == row["bytes"], row["path"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], row["path"]
    binding = json.loads((HERE / "IMPLEMENTATION_BINDINGS.json").read_text())
    assert binding["classification"] == "SYNTHETIC_ONLY"
    for flag in ("real_source_data_used", "analysis_ready", "source_admission",
                 "statistical_release", "biological_analysis_executed", "frozen_specs_changed"):
        assert binding[flag] is False, flag
    assert binding["real_source_tracers"] == "NOT_RUN"
    assert binding["authenticated_source_review"] == "NOT_RUN"
    for row in binding["files"]:
        path = (ROOT / row["path"]).resolve()
        assert path.is_relative_to(ROOT), row["path"]
        raw = path.read_bytes()
        assert len(raw) == row["bytes"], row["path"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], row["path"]
    acceptance = json.loads((HERE / "ACCEPTANCE.json").read_text())
    assert {row["ticket"] for row in acceptance["tickets"]} == {f"DAV-T{i:02d}" for i in range(1, 15)}
    assert all(row["actual_source_acceptance"] == "NOT_RUN" for row in acceptance["tickets"])
    assert acceptance["tests"]["exit_code"] == 0
    assert acceptance["typecheck"]["exit_code"] == 0
    return {"classification": "SYNTHETIC_ONLY", "preserved_files": len(baseline["files"]),
            "bound_files": len(binding["files"]), "status": "VERIFIED_SOFTWARE_RECEIPTS_ONLY"}


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
