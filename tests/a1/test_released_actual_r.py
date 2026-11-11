from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.a_meta.provenance import canonical_sha256
from tools.r_bridge import _r_environment


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXED_MEMBERSHIPS = Path(__file__).parent / "fixtures" / "a_long_fixed_memberships.json"
R_PROJECT = PROJECT_ROOT / "r"
RSCRIPT = shutil.which("Rscript")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tsv(path: Path, rows, columns):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _installed_r_runtime():
    expression = (
        'packages <- c("jsonlite", "BiocManager", "metafor"); '
        'versions <- vapply(packages, function(pkg) as.character(utils::packageVersion(pkg, lib.loc=renv::paths$library())), character(1)); '
        'cat(as.character(jsonlite::toJSON(list('
        'library=renv::paths$library(), library_root=Sys.getenv("RENV_PATHS_LIBRARY"), '
        'r_version=as.character(getRversion()), packages=as.list(versions)), auto_unbox=TRUE)))'
    )
    result = subprocess.run(
        [RSCRIPT, "--no-save", "--no-restore", "--no-site-file", "-e", expression],
        cwd=R_PROJECT,
        env=_r_environment(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout.splitlines()[-1])


def _stage_public_route(project: Path, memberships_path: Path):
    tools_dir = project / "tools"
    for package in ("tools", "a1", "a_meta", "r_bridge"):
        (tools_dir / package).mkdir(parents=True, exist_ok=True)
    for package in ("tools", "a1", "a_meta"):
        (tools_dir / package / "__init__.py").write_text("", encoding="utf-8")
    for name in ("analysis.py", "authorization.py"):
        shutil.copyfile(PROJECT_ROOT / "tools" / "a1" / name, tools_dir / "a1" / name)
    shutil.copyfile(PROJECT_ROOT / "tools" / "a_meta" / "provenance.py", tools_dir / "a_meta" / "provenance.py")
    shutil.copyfile(PROJECT_ROOT / "tools" / "r_bridge" / "__init__.py", tools_dir / "r_bridge" / "__init__.py")

    feature_stub = '''
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

def fixed_long_feature_memberships():
    data = json.loads(Path(os.environ["A_LONG_TEST_MEMBERSHIPS"]).read_text(encoding="utf-8"))
    payload = {key: data[key] for key in ("ap2_panels", "custom_panels", "m5m6_genes", "aliases")}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return SimpleNamespace(
        ap2_panels={key: tuple(value) for key, value in data["ap2_panels"].items()},
        custom_panels={key: tuple(value) for key, value in data["custom_panels"].items()},
        m5m6_genes=tuple(data["m5m6_genes"]),
        aliases=dict(data["aliases"]),
        membership_sha256=digest,
    )
'''.lstrip()
    (tools_dir / "a1" / "features.py").write_text(feature_stub, encoding="utf-8")

    r_project = project / "r"
    (r_project / "R").mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "r" / "R" / "a_long.R", r_project / "R" / "a_long.R")
    shutil.copyfile(PROJECT_ROOT / "r" / "R" / "bridge.R", r_project / "R" / "bridge.R")
    runtime = _installed_r_runtime()
    library = json.dumps(runtime["library"])
    library_root = json.dumps(runtime["library_root"])
    (r_project / ".Rprofile").write_text(
        f"Sys.setenv(RENV_PATHS_LIBRARY = {library_root})\n"
        f".libPaths(c({library}, .libPaths()))\n"
        'renv::load(project = Sys.getenv("RENV_PROJECT"), quiet = TRUE)\n',
        encoding="utf-8",
    )
    (r_project / ".Renviron").write_text("", encoding="utf-8")
    lock = {
        "R": {"Version": runtime["r_version"]},
        "Packages": {
            package: {"Package": package, "Version": version}
            for package, version in runtime["packages"].items()
        },
    }
    _write_json(r_project / "renv.lock", lock)
    cohorts = project / "docs" / "cohorts"
    decisions = project / "docs" / "decisions"
    scratch = project / ".scratch"
    for directory in (cohorts, decisions, scratch, project / "test-fixtures"):
        directory.mkdir(parents=True, exist_ok=True)
    (cohorts / "REGISTRY.tsv").write_text("cohort_id\ninvented-unrelated-registry-entry\n", encoding="utf-8")
    shutil.copyfile(FIXED_MEMBERSHIPS, memberships_path)
    return runtime


def _model_policy(decision_ref):
    return {
        "status": "ACCEPTED",
        "decision_ref": decision_ref,
        "delta_method_id": "lm_change_response_covariates_v1",
        "ancova_method_id": "lm_on_response_baseline_covariates_sensitivity_v1",
        "repeated_method_id": "lmerTest_lme4_response_window_random_intercept_v1",
        "randomized_arm_method_id": "lm_randomized_arm_change_contrast_v1",
        "meta_method_id": "metafor_REML_modified_KH_v1",
        "df_method_id": "residual_t_and_Satterthwaite_v1",
        "covariates": [],
        "repeated_windows": ["baseline", "on"],
        "min_repeated_patients": 4,
        "min_per_response_group": 2,
        "min_meta_k_pool": 4,
        "confidence_level": 0.95,
        "fdr_scope_id": "predeclared_panel_families_v1",
        "repeated_selection_mode": "complete_declared_windows",
        "min_per_randomized_arm": 2,
        "panel_family_members": None,
        "m5m6_family_members": [],
        "fdr_denominator_policy": None,
        "source_overlap_contract_sha256": None,
        "same_lesion_sensitivity_method_id": "lm_change_response_covariates_same_lesion_sensitivity_v1",
        "exact_day_sensitivity_method_id": "lm_change_response_covariates_exact_day_sensitivity_v1",
        "tighter_timing_sensitivity_method_id": "lm_change_response_covariates_tighter_timing_sensitivity_v1",
        "sensitivity_modes": [],
        "tighter_timing_max_deviation_days": None,
    }


def _feature_metadata(memberships):
    metadata = {}
    metadata.update({
        f"AP2:{panel}": {
            "unit_family": "panel",
            "feature_method_id": "A_LONG_AP2_LOG2_TPM_PLUS1_FIXED_PANEL_MEAN",
            "analysis_method_id": "lm_change_response_covariates_v1",
            "endpoint_id": "invented-response-endpoint",
            "regimen_id": "invented-ici-regimen",
            "window_id": "invented-scheduled-window",
            "assay_id": "invented-qualified-tpm-assay",
            "effect_scale_id": "LOG2_TPMPLUS1_PANEL_MEAN_CHANGE",
            "panel_family": "A_P2",
            "multiplicity_family_id": "A_P2_PANELS",
        }
        for panel in memberships["ap2_panels"]
    })
    metadata["CYT"] = {
        "unit_family": "comparator",
        "feature_method_id": "A_LONG_AP2_CYT_GZMA_PRF1_GEOMETRIC_MEAN",
        "analysis_method_id": "lm_change_response_covariates_v1",
        "endpoint_id": "invented-response-endpoint",
        "regimen_id": "invented-ici-regimen",
        "window_id": "invented-scheduled-window",
        "assay_id": "invented-qualified-tpm-assay",
        "effect_scale_id": "TPM_GEOMETRIC_MEAN_GZMA_PRF1_CHANGE",
        "panel_family": "CYT",
        "multiplicity_family_id": "CYT_SINGLETON",
    }
    metadata.update({
        f"CUSTOM:{panel}": {
            "unit_family": "custom_panel",
            "feature_method_id": "A_LONG_STRICT_CUSTOM_PANEL_MEAN_SOURCE_SCALE",
            "analysis_method_id": "lm_change_response_covariates_v1",
            "endpoint_id": "invented-response-endpoint",
            "regimen_id": "invented-ici-regimen",
            "window_id": "invented-scheduled-window",
            "assay_id": "invented-qualified-tpm-assay",
            "effect_scale_id": "SOURCE_SCALE_PANEL_MEAN:rnaseq:tpm:linear_CHANGE",
            "panel_family": "A_LONG_CUSTOM",
            "multiplicity_family_id": "A_LONG_CUSTOM_PANELS",
        }
        for panel in memberships["custom_panels"]
    })
    metadata.update({
        f"M5M6:{gene}": {
            "unit_family": "m5m6_gene",
            "feature_method_id": "A_LONG_M5M6_INDIVIDUAL_GENE_SOURCE_SCALE",
            "analysis_method_id": "lm_change_response_covariates_v1",
            "endpoint_id": "invented-response-endpoint",
            "regimen_id": "invented-ici-regimen",
            "window_id": "invented-scheduled-window",
            "assay_id": "invented-qualified-tpm-assay",
            "effect_scale_id": "SOURCE_SCALE_INDIVIDUAL_GENE:rnaseq:tpm:linear_CHANGE",
            "panel_family": "M5M6",
            "multiplicity_family_id": "M5M6_GENES",
        }
        for gene in memberships["m5m6_genes"]
    })
    return metadata


def _write_release(root: Path, *, scope: str, operation: str, policy, manifest_path: Path,
                   source_paths, cohorts, permitted_fields, bindings, name: str):
    decision_dir = root / "docs" / "decisions"
    decision = decision_dir / f"TEST_ONLY_{name.upper()}.md"
    decision.write_text("TEST ONLY invented release fixture; not a user decision.\n", encoding="utf-8")
    record = {
        "record_type": "a_long_user_release_v1",
        "record_status": "APPROVED",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "release_scope": scope,
        "operation": operation,
        "policy_sha256": canonical_sha256(policy),
        "input_manifest_sha256": _sha256(manifest_path),
        "source_sha256": {source: _sha256(path) for source, path in source_paths.items()},
        "cohorts": sorted(cohorts),
        "permitted_fields": sorted(permitted_fields),
        **bindings,
        "decision": {
            "identity": decision.stem,
            "path": f"docs/decisions/{decision.name}",
            "sha256": _sha256(decision),
        },
    }
    record_path = root / ".scratch" / f"TEST_ONLY_{name}_release.json"
    _write_json(record_path, record)
    return record_path


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_released_model_and_effect_to_synthesis_round_trip_through_actual_r(tmp_path):
    project = tmp_path / "invented-released-r-project"
    memberships_path = project / "test-fixtures" / "fixed-memberships.json"
    project.mkdir()
    (project / "test-fixtures").mkdir()
    runtime = _stage_public_route(project, memberships_path)
    assert runtime["r_version"] == "4.6.1"
    memberships = json.loads(memberships_path.read_text(encoding="utf-8"))
    units = _feature_metadata(memberships)
    assert len(units) == 37
    assert len(memberships["ap2_panels"]) == 4
    assert len(memberships["custom_panels"]) == 11
    assert len(memberships["m5m6_genes"]) == 21

    study = "invented-released-r-cohort"
    model_decision = "TEST_ONLY_TWO_TIMEPOINT"
    model_policy = _model_policy(model_decision)
    design_columns = [
        "study_id", "patient_key", "pair_id", "unit", "response", "pre_value", "on_value",
        "unit_family", "feature_method_id", "analysis_method_id", "endpoint_id", "regimen_id",
        "window_id", "assay_id", "effect_scale_id", "panel_family", "multiplicity_family_id",
        "source_family_id", "overlap_receipt_id", "overlap_status",
    ]
    deltas = [("NR", 0.0), ("NR", 2.0), ("NR", 0.0), ("NR", 2.0),
              ("R", 2.0), ("R", 4.0), ("R", 2.0), ("R", 4.0)]
    source_family = "invented-source-family-e2e"
    receipt_id = hashlib.sha256(b"invented A-LONG source relation receipt").hexdigest()
    design_rows = []
    for unit, identity in units.items():
        for index, (response, delta) in enumerate(deltas, start=1):
            design_rows.append({
                "study_id": study,
                "patient_key": f"invented-person-{index}",
                "pair_id": f"invented-pair-{index}",
                "unit": unit,
                "response": response,
                "pre_value": 10.0,
                "on_value": 10.0 + delta,
                **identity,
                "source_family_id": source_family,
                "overlap_receipt_id": receipt_id,
                "overlap_status": "DISJOINT_VERIFIED",
            })
    scratch = project / ".scratch"
    design_path = scratch / "TEST_ONLY_model_design.tsv"
    _write_tsv(design_path, design_rows, design_columns)
    model_manifest_path = scratch / "TEST_ONLY_model_manifest.json"
    model_fields = [f"design:{column}" for column in design_columns]
    model_bindings = {
        "ancova_method_id": model_policy["ancova_method_id"],
        "covariate_contract_sha256": canonical_sha256(model_policy["covariates"]),
        "delta_method_id": model_policy["delta_method_id"],
    }
    model_manifest = {
        "schema": "a_long_release_input_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": [study],
        "source_files": {"design": design_path.name},
        "field_maps": {"design": {column: column for column in design_columns}},
        "identity_fields": {"design": ["study_id", "patient_key"]},
        "permitted_fields": model_fields,
        "scope_bindings": model_bindings,
    }
    _write_json(model_manifest_path, model_manifest)
    model_record_path = _write_release(
        project,
        scope="N13_TWO_TIMEPOINT",
        operation="fit_two_timepoint",
        policy=model_policy,
        manifest_path=model_manifest_path,
        source_paths={"design": design_path},
        cohorts=[study],
        permitted_fields=model_fields,
        bindings=model_bindings,
        name="two_timepoint",
    )
    model_policy_path = scratch / "TEST_ONLY_model_policy.json"
    _write_json(model_policy_path, model_policy)

    runner_path = project / "run_invented_released_routes.py"
    runner_path.write_text(
        '''
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from tools.a_meta.provenance import canonical_sha256
from tools.a1.analysis import (
    model_effects_for_synthesis, run_released_analysis, run_released_synthesis,
    validate_n13_policy_payload,
)
from tools.a1.authorization import read_released_inputs
import tools.a1.analysis as analysis_module
from tools.r_bridge import RScriptError

root = Path.cwd()
scratch = root / ".scratch"
model_manifest_path, model_record_path, model_policy_path = map(Path, sys.argv[1:4])
model_policy = json.loads(model_policy_path.read_text(encoding="utf-8"))
model_bindings = {
    "ancova_method_id": model_policy["ancova_method_id"],
    "covariate_contract_sha256": canonical_sha256(model_policy["covariates"]),
    "delta_method_id": model_policy["delta_method_id"],
}
model_inputs = read_released_inputs(
    model_manifest_path, model_record_path,
    release_scope="N13_TWO_TIMEPOINT", operation="fit_two_timepoint",
    policy_sha256=canonical_sha256(model_policy),
    expected_scope_bindings=model_bindings,
    output_paths={"product": scratch / "TEST_ONLY_model_output", "retention": scratch / "TEST_ONLY_model_retention"},
    allow_outcomes=True,
)
model_result = run_released_analysis(
    "two-timepoint", released_inputs=model_inputs, policy_payload=model_policy,
    output_dir=scratch / "TEST_ONLY_model_output",
    retention_dir=scratch / "TEST_ONLY_model_retention",
    allow_outcomes=True,
)
target = next(row for row in model_result.effects if row["unit"] == "AP2:M2_CYTOTOXICITY" and row["model"] == "delta_primary")
assert target["status"] == "ESTIMABLE"
assert float(target["estimate"]) == 2.0
assert math.isclose(float(target["se"]), math.sqrt(2.0 / 3.0), rel_tol=1e-7, abs_tol=1e-7)
assert int(target["n_R"]) == 4 and int(target["n_NR"]) == 4 and int(target["df"]) == 6
assert target["study"] == "invented-released-r-cohort"
assert len(target["patient_set_id"]) == 64 and len(target["source_family_id"]) > 0
assert model_result.paths["longitudinal_support"].is_file()
model_bridge = json.loads(model_result.paths["r_manifest"].read_text(encoding="utf-8"))
model_release_sha = hashlib.sha256(model_record_path.read_bytes()).hexdigest()
assert model_bridge["config"]["boundary"]["release_record_sha256"] == model_release_sha

def expect_direct_r_refusal(name, patch_config, expected_message):
    original_run_r = analysis_module.run_r
    def patched_run_r(script, inputs, config, output, *, runner=None, retention_dir=None):
        changed_config = json.loads(json.dumps(config))
        patch_config(changed_config, inputs)
        return original_run_r(
            script, inputs, changed_config, output,
            runner=runner, retention_dir=retention_dir,
        )
    analysis_module.run_r = patched_run_r
    try:
        run_released_analysis(
            "two-timepoint", released_inputs=model_inputs, policy_payload=model_policy,
            output_dir=scratch / ("TEST_ONLY_" + name + "_output"),
            retention_dir=scratch / ("TEST_ONLY_" + name + "_retention"),
            allow_outcomes=True,
        )
    except RScriptError as error:
        assert expected_message in str(error), str(error)
    else:
        raise AssertionError("Direct R accepted the invented tampered " + name + " boundary")
    finally:
        analysis_module.run_r = original_run_r

def patch_n12_scope(config, _inputs):
    config["boundary"]["release_scope"] = "N12_PAIRING"
    config["boundary"]["operation"] = "pair"

def patch_policy_projection(config, _inputs):
    config["covariates"] = ["invented_unauthorized_covariate"]

def patch_derived_source(config, inputs):
    design_path = Path(inputs["design"])
    with design_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\\t")
        columns = reader.fieldnames
        rows = list(reader)
    rows[0]["on_value"] = "999"
    with design_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\\t", lineterminator="\\n")
        writer.writeheader()
        writer.writerows(rows)
    config["boundary"]["input_sha256"]["design"] = hashlib.sha256(design_path.read_bytes()).hexdigest()

expect_direct_r_refusal("n12_scope", patch_n12_scope, "mode, N13 scope, and operation do not match")
expect_direct_r_refusal("policy_projection", patch_policy_projection, "executable setting differs from the approved policy")
expect_direct_r_refusal("derived_source", patch_derived_source, "derived model values do not match the authorized source contents")

effects = model_effects_for_synthesis([model_result])
effect_columns = list(effects[0])
effects_path = scratch / "TEST_ONLY_model_effects_for_synthesis.tsv"
with effects_path.open("x", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=effect_columns, delimiter="\\t", lineterminator="\\n")
    writer.writeheader()
    writer.writerows(effects)
overlap_path = scratch / "TEST_ONLY_empty_overlap_receipts.tsv"
overlap_columns = ["study_a", "study_b", "source_family_a", "source_family_b", "overlap_status", "receipt_sha256"]
overlap_path.write_text("\\t".join(overlap_columns) + "\\n", encoding="utf-8")

synthesis_policy = dict(model_policy)
synthesis_policy["decision_ref"] = "TEST_ONLY_SYNTHESIS"
synthesis_policy.update({
    "panel_family_members": {
        "A_P2_PANELS": [unit for unit in (row["unit"] for row in effects) if unit.startswith("AP2:")],
        "A_LONG_CUSTOM_PANELS": [unit for unit in (row["unit"] for row in effects) if unit.startswith("CUSTOM:")],
    },
    "m5m6_family_members": [unit for unit in (row["unit"] for row in effects) if unit.startswith("M5M6:")],
    "fdr_denominator_policy": "all_predeclared_members_missing_as_p1_v1",
    "source_overlap_contract_sha256": hashlib.sha256(b"invented pairwise source-overlap contract").hexdigest(),
})
validate_n13_policy_payload(synthesis_policy, route="synthesis")
synthesis_bindings = {
    "meta_method_id": synthesis_policy["meta_method_id"],
    "multiplicity_contract_sha256": canonical_sha256({
        "panel_family_members": synthesis_policy["panel_family_members"],
        "m5m6_family_members": synthesis_policy["m5m6_family_members"],
        "fdr_denominator_policy": synthesis_policy["fdr_denominator_policy"],
    }),
    "source_overlap_contract_sha256": synthesis_policy["source_overlap_contract_sha256"],
}
synthesis_manifest_path = scratch / "TEST_ONLY_synthesis_manifest.json"
synthesis_fields = [f"effects:{field}" for field in effect_columns]
synthesis_fields += [f"overlap_receipts:{field}" for field in overlap_columns]
synthesis_manifest = {
    "schema": "a_long_release_input_manifest_v1",
    "data_classification": "PRIVATE_PATIENT_LEVEL",
    "cohort_ids": ["invented-released-r-cohort"],
    "source_files": {"effects": effects_path.name, "overlap_receipts": overlap_path.name},
    "field_maps": {
        "effects": {field: field for field in effect_columns},
        "overlap_receipts": {field: field for field in overlap_columns},
    },
    "identity_fields": {
        "effects": ["study", "source_family_id"],
        "overlap_receipts": ["study_a", "study_b", "source_family_a", "source_family_b"],
    },
    "permitted_fields": sorted(synthesis_fields),
    "scope_bindings": synthesis_bindings,
}
synthesis_manifest_bytes = json.dumps(synthesis_manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
synthesis_manifest_path.write_bytes(synthesis_manifest_bytes + b"\\n")
synthesis_decision = root / "docs" / "decisions" / "TEST_ONLY_SYNTHESIS.md"
synthesis_decision.write_text("TEST ONLY invented synthesis release fixture; not a user decision.\\n", encoding="utf-8")
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
synthesis_record = {
    "record_type": "a_long_user_release_v1",
    "record_status": "APPROVED",
    "data_classification": "PRIVATE_PATIENT_LEVEL",
    "release_scope": "N13_SYNTHESIS",
    "operation": "synthesize_effects",
    "policy_sha256": canonical_sha256(synthesis_policy),
    "input_manifest_sha256": hashlib.sha256(synthesis_manifest_bytes + b"\\n").hexdigest(),
    "source_sha256": {"effects": sha(effects_path), "overlap_receipts": sha(overlap_path)},
    "cohorts": ["invented-released-r-cohort"],
    "permitted_fields": sorted(synthesis_fields),
    **synthesis_bindings,
    "decision": {
        "identity": synthesis_decision.stem,
        "path": "docs/decisions/TEST_ONLY_SYNTHESIS.md",
        "sha256": sha(synthesis_decision),
    },
}
synthesis_record_path = scratch / "TEST_ONLY_synthesis_release.json"
synthesis_record_path.write_text(json.dumps(synthesis_record, sort_keys=True, separators=(",", ":")) + "\\n", encoding="utf-8")
synthesis_policy_path = scratch / "TEST_ONLY_synthesis_policy.json"
synthesis_policy_path.write_text(json.dumps(synthesis_policy, sort_keys=True, separators=(",", ":")) + "\\n", encoding="utf-8")
synthesis_inputs = read_released_inputs(
    synthesis_manifest_path, synthesis_record_path,
    release_scope="N13_SYNTHESIS", operation="synthesize_effects",
    policy_sha256=canonical_sha256(synthesis_policy),
    expected_scope_bindings=synthesis_bindings,
    output_paths={"product": scratch / "TEST_ONLY_synthesis_output", "retention": scratch / "TEST_ONLY_synthesis_retention"},
    allow_outcomes=True,
)
synthesis_result = run_released_synthesis(
    released_inputs=synthesis_inputs, policy_payload=synthesis_policy,
    output_dir=scratch / "TEST_ONLY_synthesis_output",
    retention_dir=scratch / "TEST_ONLY_synthesis_retention",
    allow_outcomes=True,
)
synthesized = next(row for row in synthesis_result.effects if row["unit"] == "AP2:M2_CYTOTOXICITY")
assert synthesized["status"] == "single_study" and int(synthesized["k"]) == 1
assert float(synthesized["estimate"]) == 2.0
assert math.isclose(float(synthesized["se"]), math.sqrt(2.0 / 3.0), rel_tol=1e-7, abs_tol=1e-7)
assert synthesized["analysis_method_id"] == target["analysis_method_id"]
assert synthesized["effect_scale_id"] == target["effect_scale_id"]
synthesis_bridge = json.loads(synthesis_result.paths["r_manifest"].read_text(encoding="utf-8"))
assert synthesis_bridge["config"]["boundary"]["release_record_sha256"] == hashlib.sha256(synthesis_record_path.read_bytes()).hexdigest()
print(json.dumps({
    "model_beta": float(target["estimate"]),
    "model_se": float(target["se"]),
    "model_df": int(target["df"]),
    "model_groups": [int(target["n_R"]), int(target["n_NR"])],
    "synthesis_estimate": float(synthesized["estimate"]),
    "synthesis_se": float(synthesized["se"]),
    "synthesis_k": int(synthesized["k"]),
    "model_record_receipt": model_release_sha,
    "synthesis_record_receipt": hashlib.sha256(synthesis_record_path.read_bytes()).hexdigest(),
    "retained_model_longitudinal_support": model_result.paths["longitudinal_support"].is_file(),
}, sort_keys=True))
'''.lstrip(),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project)
    env["A_LONG_TEST_MEMBERSHIPS"] = str(memberships_path)
    result = subprocess.run(
        [sys.executable, str(runner_path), str(model_manifest_path), str(model_record_path), str(model_policy_path)],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.splitlines()[-1])
    assert report["model_beta"] == pytest.approx(2.0, abs=1e-8)
    assert report["model_se"] == pytest.approx((2.0 / 3.0) ** 0.5, abs=1e-7)
    assert report["model_df"] == 6
    assert report["model_groups"] == [4, 4]
    assert report["synthesis_estimate"] == pytest.approx(2.0, abs=1e-8)
    assert report["synthesis_se"] == pytest.approx((2.0 / 3.0) ** 0.5, abs=1e-7)
    assert report["synthesis_k"] == 1
    assert len(report["model_record_receipt"]) == 64
    assert len(report["synthesis_record_receipt"]) == 64
    assert report["retained_model_longitudinal_support"] is True

