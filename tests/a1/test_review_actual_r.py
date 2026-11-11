from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.a1.test_released_actual_r import (
    FIXED_MEMBERSHIPS,
    RSCRIPT,
    _stage_public_route,
)


def _instrument_payload_read_sentinel(project: Path):
    script = project / "r" / "R" / "a_long.R"
    source = script.read_text(encoding="utf-8")
    marker = 'if (identical(mode, "fit_two_timepoint")) {'
    marker_index = source.rfind(marker)
    assert marker_index >= 0
    wrapper = '''
.read_authorized_table_original <- .read_authorized_table
.read_authorized_table <- function(path, fields) {
  requested <- unlist(fields, use.names = FALSE)
  if (any(requested %in% c("response", "pre_value", "on_value", "estimate", "se", "ci_lb", "ci_ub", "p_value"))) {
    stop("TEST_ONLY_OUTCOME_READ_REACHED")
  }
  .read_authorized_table_original(path, fields)
}
'''.lstrip()
    script.write_text(
        source[:marker_index] + wrapper + "\n" + source[marker_index:],
        encoding="utf-8",
    )


def _run_staged_probe(project: Path, memberships_path: Path, name: str, source: str):
    runner = project / f"TEST_ONLY_{name}.py"
    runner.write_text(source.lstrip(), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project)
    env["A_LONG_TEST_MEMBERSHIPS"] = str(memberships_path)
    result = subprocess.run(
        [sys.executable, str(runner)], cwd=project, env=env,
        capture_output=True, text=True, timeout=180, check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
@pytest.mark.parametrize(
    ("actual_study", "registry_study", "expected"),
    [
        ("IMVIGOR-210", "invented-unrelated-registry-entry", "protected, registered, or outside"),
        ("invented-registered-real-fixture", "invented-registered-real-fixture", "protected, registered, or outside"),
    ],
)
def test_direct_r_synthetic_boundary_checks_manifest_and_payload_identity_before_model_read(
    tmp_path, actual_study, registry_study, expected
):
    project = tmp_path / "TEST_ONLY_direct_r_identity_project"
    project.mkdir()
    memberships_path = tmp_path / "TEST_ONLY_fixed_memberships.json"
    _stage_public_route(project, memberships_path)
    registry = project / "docs" / "cohorts" / "REGISTRY.tsv"
    registry.write_text(f"cohort_id\n{registry_study}\n", encoding="utf-8")

    runner = project / "TEST_ONLY_direct_r_identity_probe.py"
    runner.write_text(
        '''
import hashlib
import json
from pathlib import Path
from tools.a1 import analysis
from tools.r_bridge import RScriptError, run_r

root = Path.cwd()
scratch = root / ".scratch"
payload = scratch / "TEST_ONLY_model_payload.tsv"
columns = [
    "study_id", "patient_key", "pair_id", "unit", "response", "pre_value", "on_value",
    "unit_family", "feature_method_id", "analysis_method_id", "endpoint_id", "regimen_id",
    "window_id", "assay_id", "effect_scale_id", "panel_family", "multiplicity_family_id",
    "source_family_id", "overlap_receipt_id", "overlap_status", "Tumor_Shrinkage",
]
payload.write_text(
    "\\t".join(columns) + "\\n" +
    "\\t".join([
        __ACTUAL_STUDY__, "invented-person", "invented-pair", "invented-panel", "R", "1", "2",
        "panel", "fixture-score-v1", "lm_change_response_covariates_v1", "invented-endpoint",
        "invented-ici-only", "invented-window", "invented-assay", "invented-log2-scale",
        "fixture-panels", "fixture-family", "invented-source-family", "" + "a" * 64,
        "DISJOINT_VERIFIED", "TEST_ONLY_OUTCOME_SENTINEL",
    ]) + "\\n",
    encoding="utf-8",
)
manifest_path = scratch / "TEST_ONLY_synthetic_manifest.json"
manifest = analysis._write_synthetic_r_manifest(
    manifest_path,
    kind="a_long_analysis_input",
    source_paths={"design": payload},
    cohorts=["invented-synthetic-claim"],
    identity_fields={"design": ["study_id"]},
)
boundary = {
    "data_classification": "synthetic",
    "manifest_kind": "a_long_analysis_input",
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    "cohorts": ["invented-synthetic-claim"],
    "source_inputs": ["design"],
    "input_sha256": {"design": hashlib.sha256(payload.read_bytes()).hexdigest()},
    "input_fields": {"design": columns[:-1]},
    "identity_fields": manifest["identity_fields"],
    "policy_sha256": "b" * 64,
    "retention_dir": str(scratch / "TEST_ONLY_retention"),
}
config = {
    "mode": "fit_two_timepoint",
    "expected_outputs": ["effects.tsv", "within_group_deltas.tsv", "model_support.tsv"],
    "covariates": [],
    "confidence_level": 0.95,
    "min_per_response_group": 2,
    "sensitivity_modes": [],
    "tighter_timing_max_deviation_days": None,
    "policy_status": "TEST_ONLY",
    "method_ids": {
        "delta": "lm_change_response_covariates_v1",
        "ancova": "lm_on_response_baseline_covariates_sensitivity_v1",
        "df": "residual_t_and_Satterthwaite_v1",
        "same_lesion_sensitivity": "fixture-same-lesion",
        "exact_day_sensitivity": "fixture-exact-day",
        "tighter_timing_sensitivity": "fixture-tighter-timing",
    },
    "identities": {"invented-panel": {"study": "invented-synthetic-claim", "patient_set_id": "fixture"}},
    "analysis_family": "observational_response",
    "boundary": boundary,
}
try:
    run_r(
        root / "r" / "R" / "a_long.R",
        {"design": payload, "provenance_manifest": manifest_path},
        config,
        scratch / "TEST_ONLY_output" / "R",
        retention_dir=scratch / "TEST_ONLY_retention",
    )
except RScriptError as error:
    message = str(error)
    assert __EXPECTED__ in message, message
    assert "TEST_ONLY_OUTCOME_SENTINEL" not in message
    assert "missing an authorized named field" not in message
else:
    raise AssertionError("Direct R accepted a synthetic payload with an unapproved study identity")
'''.replace("__ACTUAL_STUDY__", repr(actual_study)).replace("__EXPECTED__", repr(expected)).lstrip(),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project)
    env["A_LONG_TEST_MEMBERSHIPS"] = str(memberships_path)
    result = subprocess.run(
        [sys.executable, str(runner)],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_direct_r_rejects_synthetic_payload_changed_after_its_manifest_hash(tmp_path):
    project = tmp_path / "TEST_ONLY_direct_r_hash_project"
    project.mkdir()
    memberships_path = tmp_path / "TEST_ONLY_fixed_memberships_hash.json"
    _stage_public_route(project, memberships_path)
    runner = project / "TEST_ONLY_direct_r_hash_probe.py"
    runner.write_text(
        '''
import hashlib
from pathlib import Path
from tools.a1 import analysis
from tools.r_bridge import RScriptError, run_r

root = Path.cwd()
scratch = root / ".scratch"
payload = scratch / "TEST_ONLY_payload.tsv"
columns = ["study_id", "patient_key", "unit", "response", "pre_value", "on_value"]
initial = ["fixture-study", "invented-person", "fixture-unit", "NR", "1", "2"]
changed = ["fixture-study", "TEST_ONLY_CHANGED_AFTER_MANIFEST", "fixture-unit", "NR", "1", "2"]
payload.write_text("\\t".join(columns) + "\\n" + "\\t".join(initial) + "\\n", encoding="utf-8")
manifest_path = scratch / "TEST_ONLY_manifest.json"
manifest = analysis._write_synthetic_r_manifest(
    manifest_path, kind="a_long_analysis_input", source_paths={"design": payload},
    cohorts=["fixture-study"], identity_fields={"design": ["study_id"]},
)
payload.write_text("\\t".join(columns) + "\\n" + "\\t".join(changed) + "\\n", encoding="utf-8")
config = {
    "mode": "fit_two_timepoint", "expected_outputs": ["effects.tsv", "within_group_deltas.tsv", "model_support.tsv"],
    "boundary": {
        "data_classification": "synthetic", "manifest_kind": "a_long_analysis_input",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cohorts": ["fixture-study"], "source_inputs": ["design"],
        "input_sha256": {"design": hashlib.sha256(payload.read_bytes()).hexdigest()},
        "input_fields": {"design": columns},
        "identity_fields": manifest["identity_fields"], "policy_sha256": "c" * 64,
        "retention_dir": str(scratch / "TEST_ONLY_retention"),
    },
}
try:
    run_r(
        root / "r" / "R" / "a_long.R",
        {"design": payload, "provenance_manifest": manifest_path}, config,
        scratch / "TEST_ONLY_hash_output" / "R", retention_dir=scratch / "TEST_ONLY_retention",
    )
except RScriptError as error:
    assert "synthetic source hash mismatch" in str(error), str(error)
else:
    raise AssertionError("Direct R accepted changed synthetic payload contents")
'''.lstrip(),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project)
    env["A_LONG_TEST_MEMBERSHIPS"] = str(memberships_path)
    result = subprocess.run(
        [sys.executable, str(runner)],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_direct_r_synthetic_model_requires_canonical_study_id_with_alias_present(tmp_path):
    project = tmp_path / "TEST_ONLY_canonical_study_id_project"
    project.mkdir()
    memberships_path = tmp_path / "TEST_ONLY_canonical_study_id_memberships.json"
    _stage_public_route(project, memberships_path)
    _instrument_payload_read_sentinel(project)

    _run_staged_probe(project, memberships_path, "canonical_study_id_probe", '''
import hashlib
from pathlib import Path
from tools.a1 import analysis
from tools.r_bridge import RScriptError, run_r

root = Path.cwd()
scratch = root / ".scratch"
(root / "docs" / "cohorts" / "REGISTRY.tsv").write_text(
    "cohort_id\\ninvented-registered-real-fixture\\n", encoding="utf-8"
)
payload = scratch / "neutral_model_name.tsv"
columns = ["study_id", "study", "patient_key", "unit", "response", "pre_value", "on_value"]
values = ["invented-registered-real-fixture", "invented-synthetic-claim", "invented-person", "invented-panel", "R", "1", "2"]
payload.write_text("\\t".join(columns) + "\\n" + "\\t".join(values) + "\\n", encoding="utf-8")
manifest_path = scratch / "TEST_ONLY_alias_manifest.json"
manifest = analysis._write_synthetic_r_manifest(
    manifest_path, kind="a_long_analysis_input", source_paths={"design": payload},
    cohorts=["invented-synthetic-claim"], identity_fields={"design": ["study"]},
)
boundary = {
    "data_classification": "synthetic", "manifest_kind": "a_long_analysis_input",
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    "cohorts": ["invented-synthetic-claim"], "source_inputs": ["design"],
    "input_sha256": {"design": hashlib.sha256(payload.read_bytes()).hexdigest()},
    "input_fields": {"design": columns}, "identity_fields": manifest["identity_fields"],
    "policy_sha256": "f" * 64, "retention_dir": str(scratch / "TEST_ONLY_retention"),
}
config = {
    "mode": "fit_two_timepoint",
    "expected_outputs": ["effects.tsv", "within_group_deltas.tsv", "model_support.tsv"],
    "covariates": [], "confidence_level": 0.95, "min_per_response_group": 2,
    "sensitivity_modes": [], "tighter_timing_max_deviation_days": None,
    "policy_status": "TEST_ONLY", "analysis_family": "observational_response",
    "method_ids": {
        "delta": "lm_change_response_covariates_v1",
        "ancova": "lm_on_response_baseline_covariates_sensitivity_v1",
        "df": "residual_t_and_Satterthwaite_v1",
        "same_lesion_sensitivity": "fixture-same-lesion",
        "exact_day_sensitivity": "fixture-exact-day",
        "tighter_timing_sensitivity": "fixture-tighter-timing",
    },
    "identities": {"invented-panel": {"study": "invented-synthetic-claim", "patient_set_id": "TEST_ONLY"}},
    "boundary": boundary,
}
try:
    run_r(
        root / "r" / "R" / "a_long.R",
        {"design": payload, "provenance_manifest": manifest_path}, config,
        scratch / "TEST_ONLY_output" / "R", retention_dir=scratch / "TEST_ONLY_retention",
    )
except RScriptError as error:
    message = str(error)
    assert "Synthetic A-LONG identity roles do not match mode" in message, message
    assert "TEST_ONLY_OUTCOME_READ_REACHED" not in message
else:
    raise AssertionError("Direct R accepted an unbound study alias instead of canonical study_id")
''')


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_direct_r_synthetic_model_rejects_unbound_design_before_outcome_read(tmp_path):
    project = tmp_path / "TEST_ONLY_unbound_design_project"
    project.mkdir()
    memberships_path = tmp_path / "TEST_ONLY_unbound_memberships.json"
    _stage_public_route(project, memberships_path)
    _instrument_payload_read_sentinel(project)

    _run_staged_probe(project, memberships_path, "unbound_design_probe", '''
import hashlib
from pathlib import Path
from tools.a1 import analysis
from tools.r_bridge import RScriptError, run_r

root = Path.cwd()
scratch = root / ".scratch"
(root / "docs" / "cohorts" / "REGISTRY.tsv").write_text(
    "cohort_id\\ninvented-registered-real-fixture\\n", encoding="utf-8"
)
groups = scratch / "TEST_ONLY_groups.tsv"
groups.write_text("analysis_group_id\\ninvented-group\\n", encoding="utf-8")
design = scratch / "neutral_design_name.tsv"
columns = ["study_id", "patient_key", "pair_id", "unit", "response", "pre_value", "on_value"]
design.write_text(
    "\\t".join(columns) + "\\n" +
    "\\t".join(["invented-registered-real-fixture", "invented-person", "invented-pair", "invented-panel", "R", "1", "2"]) + "\\n",
    encoding="utf-8",
)
manifest_path = scratch / "TEST_ONLY_groups_manifest.json"
manifest = analysis._write_synthetic_r_manifest(
    manifest_path, kind="a_long_analysis_input", source_paths={"groups": groups},
    cohorts=["invented-synthetic-study"], identity_fields={"groups": ["analysis_group_id"]},
)
boundary = {
    "data_classification": "synthetic", "manifest_kind": "a_long_analysis_input",
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    "cohorts": ["invented-synthetic-study"], "source_inputs": ["groups"],
    "input_sha256": {"groups": hashlib.sha256(groups.read_bytes()).hexdigest()},
    "input_fields": {"groups": ["analysis_group_id"], "design": columns},
    "identity_fields": manifest["identity_fields"], "policy_sha256": "d" * 64,
    "retention_dir": str(scratch / "TEST_ONLY_retention"),
}
config = {
    "mode": "fit_two_timepoint",
    "expected_outputs": ["effects.tsv", "within_group_deltas.tsv", "model_support.tsv"],
    "covariates": [], "confidence_level": 0.95, "min_per_response_group": 2,
    "sensitivity_modes": [], "tighter_timing_max_deviation_days": None,
    "policy_status": "TEST_ONLY", "analysis_family": "observational_response",
    "method_ids": {
        "delta": "lm_change_response_covariates_v1",
        "ancova": "lm_on_response_baseline_covariates_sensitivity_v1",
        "df": "residual_t_and_Satterthwaite_v1",
        "same_lesion_sensitivity": "fixture-same-lesion",
        "exact_day_sensitivity": "fixture-exact-day",
        "tighter_timing_sensitivity": "fixture-tighter-timing",
    },
    "identities": {"invented-panel": {"study": "invented-synthetic-study", "patient_set_id": "TEST_ONLY"}},
    "boundary": boundary,
}
try:
    run_r(
        root / "r" / "R" / "a_long.R",
        {"groups": groups, "design": design, "provenance_manifest": manifest_path},
        config, scratch / "TEST_ONLY_output" / "R", retention_dir=scratch / "TEST_ONLY_retention",
    )
except RScriptError as error:
    message = str(error)
    assert "Synthetic A-LONG request input roles do not match mode" in message, message
    assert "TEST_ONLY_OUTCOME_READ_REACHED" not in message
else:
    raise AssertionError("Direct R accepted an unbound design input")
''')


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_direct_r_synthetic_synthesis_rejects_wrong_effect_identity_role_before_outcome_read(tmp_path):
    project = tmp_path / "TEST_ONLY_wrong_synthesis_identity_project"
    project.mkdir()
    memberships_path = tmp_path / "TEST_ONLY_wrong_synthesis_memberships.json"
    _stage_public_route(project, memberships_path)
    _instrument_payload_read_sentinel(project)

    _run_staged_probe(project, memberships_path, "wrong_effect_role_probe", '''
import hashlib
from pathlib import Path
from tools.a1 import analysis
from tools.r_bridge import RScriptError, run_r

root = Path.cwd()
scratch = root / ".scratch"
effects = scratch / "neutral_effect_name.tsv"
effect_columns = ["study", "study_a", "study_b", "analysis_group_id", "estimate", "se", "ci_lb", "ci_ub", "p_value"]
effects.write_text(
    "\\t".join(effect_columns) + "\\n" +
    "\\t".join(["invented-study-a", "invented-study-a", "invented-study-b", "invented-family", "TEST_ONLY_OUTCOME_SENTINEL", "0.2", "0", "1", "0.01"]) + "\\n",
    encoding="utf-8",
)
overlap = scratch / "TEST_ONLY_overlap.tsv"
overlap_columns = ["study_a", "study_b", "source_family_a", "source_family_b", "overlap_status", "receipt_sha256"]
overlap.write_text("\\t".join(overlap_columns) + "\\n", encoding="utf-8")
groups = scratch / "TEST_ONLY_groups.tsv"
group_columns = ["analysis_group_id", "preflight_reason", "k", "n_input", "n_excluded", "independence_status"]
groups.write_text(
    "\\t".join(group_columns) + "\\n" +
    "\\t".join(["invented-family", "fixture nonestimable", "0", "1", "1", "UNRESOLVED"]) + "\\n",
    encoding="utf-8",
)
paths = {"effects": effects, "overlap_receipts": overlap, "groups": groups}
manifest_path = scratch / "TEST_ONLY_synthesis_manifest.json"
manifest = analysis._write_synthetic_r_manifest(
    manifest_path, kind="a_long_synthesis_input", source_paths=paths,
    cohorts=["invented-study-a", "invented-study-b"],
    identity_fields={
        "effects": ["study_a", "study_b"],
        "overlap_receipts": ["study_a", "study_b"],
        "groups": ["analysis_group_id"],
    },
)
hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
field_map = {
    "effects": effect_columns, "overlap_receipts": overlap_columns, "groups": group_columns,
}
boundary = {
    "data_classification": "synthetic", "manifest_kind": "a_long_synthesis_input",
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    "cohorts": ["invented-study-a", "invented-study-b"],
    "source_inputs": ["effects", "overlap_receipts", "groups"],
    "input_sha256": hashes, "input_fields": field_map,
    "identity_fields": manifest["identity_fields"], "policy_sha256": "e" * 64,
    "retention_dir": str(scratch / "TEST_ONLY_retention"),
}
config = {
    "mode": "synthesize", "expected_outputs": ["synthesis.tsv"],
    "method_id": "metafor_REML_modified_KH_v1", "confidence_level": 0.95,
    "minimum_k_for_pooling": 4, "policy_status": "TEST_ONLY", "boundary": boundary,
}
try:
    run_r(
        root / "r" / "R" / "a_long.R",
        {**paths, "provenance_manifest": manifest_path}, config,
        scratch / "TEST_ONLY_output" / "R", retention_dir=scratch / "TEST_ONLY_retention",
    )
except RScriptError as error:
    message = str(error)
    assert "Synthetic A-LONG identity roles do not match mode" in message, message
    assert "TEST_ONLY_OUTCOME_READ_REACHED" not in message
else:
    raise AssertionError("Direct R accepted effects bound only to overlap study fields")
''')
