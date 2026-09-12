"""Execute explicit fictional contracts; never derive a score from a gene registry.

The first implementation deliberately supports only synthetic measurement tests.
Published secondary models and real nominations require their own qualified
contracts and executors; no generic switch releases real biological analyses.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from tools.b_prediction.w5_bundle import load_w5_bundle
from tools.b_workflow.io import (
    PipelineFailure, atomic_write_json, atomic_write_tsv, canonical_json_bytes,
    json_no_dups, publish_directory, read_tsv, sha256_bytes, sha256_file,
    utc_stamp, verify_published_stage,
)

SCOPE = "synthetic-software-w1-w8"
LABEL = "SYNTHETIC FIXTURE ONLY. No biological or clinical validation."
NAMED = {"AYERS_GEP_18", "HALLMARK_INTERFERON_GAMMA_RESPONSE", "HOPE_18"}


def fail(reason: str) -> None:
    raise PipelineFailure(f"stage=W8 reason={reason}", 3, "W8")


def exact(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"contract-fields:{label}")


def finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def validate_contract(contract: dict[str, Any]) -> None:
    """Fail closed for unknown fields, names, implicit weights and scales."""
    if not isinstance(contract, dict):
        fail("contract-not-object")
    if contract.get("status") == "blocked":
        exact(contract, {"id", "status", "reason"}, "blocked")
        if not isinstance(contract["id"], str) or not isinstance(contract["reason"], str) or not contract["reason"].strip():
            fail("blocked-reason-required")
        return
    exact(contract, {"id", "status", "scope", "cohort", "members", "scale", "input_columns",
                     "method", "missingness", "output_semantics"}, "enabled")
    if contract["id"] != "FICTIONAL_SIGNED_TPM_DIFFERENCE_V1" or contract["status"] != "frozen-fixture":
        fail("only-fictional-frozen-executor-available")
    fixed = {"scope": "synthetic-fixture-only", "cohort": "TCGA-SYN", "scale": "tpm_unstranded",
             "input_columns": ["patient_id", "cohort", "stable_gene_id", "value", "abundance_type", "synthetic"],
             "method": "signed-weighted-sum", "missingness": "undefined-if-any-member-missing",
             "output_semantics": "fictional-signed-expression-value-not-immune-activation"}
    if any(contract[key] != value for key, value in fixed.items()):
        fail("unsupported-fictional-score-contract")
    members = contract["members"]
    if not isinstance(members, list) or not members:
        fail("members-required")
    seen = set()
    for member in members:
        exact(member, {"gene", "direction", "weight"}, "member")
        gene = member["gene"]
        if not isinstance(gene, str) or not gene.startswith("SYN:") or gene in seen:
            fail("fictional-membership-invalid")
        if type(member["direction"]) is not int or member["direction"] not in (-1, 1) or not finite(member["weight"]) or member["weight"] <= 0:
            fail("explicit-signed-positive-weight-required")
        seen.add(gene)


def validate_handoff(contract: dict[str, Any]) -> None:
    exact(contract, {"id", "status", "scope", "source_cohort", "source_stage", "source_table",
                     "selection", "uses_external_outcomes", "membership_source", "scale", "genes",
                     "reference_value", "contrast", "uncertainty", "missingness", "biological_context", "alternative_explanations"}, "handoff")
    fixed = {"id": "FICTIONAL_TCGA_QUERY_V1", "status": "frozen-fixture", "scope": "synthetic-fixture-only",
             "source_cohort": "TCGA-SYN", "source_stage": "W3", "source_table": "expression.tsv",
             "selection": "all-predeclared-members-no-ranking", "uses_external_outcomes": False,
             "membership_source": "independent-fictional-contract", "scale": "tpm_unstranded",
             "contrast": "mean-minus-fixed-fictional-reference", "uncertainty": "not-estimated-fixture-only",
             "missingness": "available-finite-patients-per-gene-undefined-if-none"}
    if any(contract[key] != value or (key == "uses_external_outcomes" and contract[key] is not False)
           for key, value in fixed.items()):
        fail("handoff-must-be-independent-tcga-only-outcome-blind-fixture")
    genes = contract["genes"]
    if not isinstance(genes, list) or not genes or any(not isinstance(g, str) or not g.startswith("SYN:") for g in genes) or len(set(genes)) != len(genes):
        fail("handoff-fictional-membership-required")
    if not finite(contract["reference_value"]) or not isinstance(contract["biological_context"], str) or not contract["biological_context"].strip():
        fail("handoff-reference-context-required")
    if not isinstance(contract["alternative_explanations"], list) or not contract["alternative_explanations"] or any(not isinstance(x, str) or not x.strip() for x in contract["alternative_explanations"]):
        fail("handoff-alternative-explanations-required")


def validate_config(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    exact(config, {"policy_label", "registry_path", "registry_sha256", "contracts", "c_handoff"}, "w8")
    if config["policy_label"] != "synthetic-fixture-only":
        fail("fixture-policy-required")
    if not isinstance(config["registry_path"], str):
        fail("registry-path-required")
    path = (repo_root / config["registry_path"]).resolve()
    if not path.is_relative_to(repo_root.resolve()) or not path.is_file() or sha256_file(path) != config["registry_sha256"]:
        fail("registry-pin-mismatch")
    registry = json_no_dups(path.read_bytes())
    if registry.get("schema_version") != "B-gene-set-registry-proposed-v0.2" or registry.get("status") != "proposed_not_frozen":
        fail("unsupported-registry")
    contracts = config["contracts"]
    if not isinstance(contracts, list) or not contracts:
        fail("contracts-required")
    for contract in contracts:
        validate_contract(contract)
    ids = [c["id"] for c in contracts]
    if len(set(ids)) != len(ids) or not NAMED.issubset(ids):
        fail("duplicate-or-missing-named-contract")
    if not any(c["status"] == "frozen-fixture" for c in contracts) or not any(c["status"] == "blocked" for c in contracts):
        fail("enabled-and-blocked-fixture-required")
    validate_handoff(config["c_handoff"])
    return registry


def verify_publication(path: Path, stage: str, *, identity: str, config_hash: str) -> dict[str, Any]:
    """Exact declared payloads, manifest agreement and publication identities."""
    if path.with_name(path.name + ".work").exists():
        fail(f"parent-work-present:{stage}")
    # Validate paths before generic hash verification can open any declared file.
    checksum_path = path / "checksums.json"
    if not checksum_path.is_file():
        fail(f"parent-missing-checksums:{stage}")
    checks = json_no_dups(checksum_path.read_bytes())
    artifacts = checks.get("artifact_hashes")
    if not isinstance(artifacts, dict) or not artifacts:
        fail(f"parent-payload-index:{stage}")
    for rel, digest in artifacts.items():
        if stage == "W3" and rel == "checksums.json" and digest is None:
            continue  # Historical W3 schema self-placeholder; COMPLETE pins its bytes.
        if not isinstance(rel, str) or "\\" in rel or not (path / rel).resolve().is_relative_to(path.resolve()) or rel in {"COMPLETE.json", "checksums.json", "manifest.json"}:
            fail(f"unsafe-parent-payload:{stage}")
        if not isinstance(digest, str) or len(digest) != 64:
            fail(f"parent-payload-hash:{stage}")
    actual = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    if actual != set(artifacts) | {"COMPLETE.json", "checksums.json", "manifest.json"}:
        fail(f"parent-undeclared-or-missing-payload:{stage}")
    ok, reason = verify_published_stage(path, stage)
    if not ok:
        fail(f"parent-publication-invalid:{stage}:{reason}")
    manifest = json_no_dups((path / "manifest.json").read_bytes())
    complete = json_no_dups((path / "COMPLETE.json").read_bytes())
    expected_manifest = dict(checks)
    if stage in {"W3", "W5", "W6"}:
        expected_manifest["artifact_hashes"] = {**artifacts, "checksums.json": sha256_file(checksum_path)}
    if any(manifest.get(k) != v for k, v in expected_manifest.items()):
        fail(f"parent-manifest-disagreement:{stage}")
    for record in (checks, manifest, complete):
        if stage == "W8" and (record.get("completion_scope") != SCOPE or record.get("pipeline_complete") is not True or record.get("biological_validation") is not False):
            fail("invalid-software-completion-scope")
        if record.get("synthetic") is not True or record.get("stage") != stage or record.get("code_identity_sha256") != identity:
            fail(f"parent-identity-mismatch:{stage}")
        if record.get("parent_hashes", {}).get("config") != config_hash:
            fail(f"parent-config-mismatch:{stage}")
    if complete.get("parent_hashes") != checks.get("parent_hashes"):
        fail(f"parent-links-disagree:{stage}")
    return checks


def expression_rows(path: Path) -> list[dict[str, str]]:
    header, raw = read_tsv(path)
    required = {"patient_id", "cohort", "stable_gene_id", "symbol", "value", "abundance_type", "synthetic"}
    if len(set(header)) != len(header) or not required.issubset(header):
        fail("expression-schema")
    rows = [dict(zip(header, r)) for r in raw]
    if any(r["synthetic"] != "true" for r in rows):
        fail("non-synthetic-expression")
    return rows


def tcga_values(rows: list[dict[str, str]]) -> dict[str, dict[str, float | None]]:
    values: dict[str, dict[str, float | None]] = {}
    for row in rows:
        if row["cohort"] != "TCGA-SYN":
            continue
        patient, gene = row["patient_id"], row["stable_gene_id"]
        if not patient.startswith("TCGA-") or row["abundance_type"] != "tpm_unstranded":
            fail("tcga-expression-identity-or-scale")
        target = values.setdefault(patient, {})
        if gene in target:
            fail("duplicate-patient-gene")
        try:
            value = None if row["value"] == "NA" else float(row["value"])
        except ValueError:
            fail("invalid-expression-value")
        if value is not None and (not finite(value) or value < 0):
            fail("invalid-tpm")
        target[gene] = value
    if not values:
        fail("no-tcga-fixture-patients")
    return values


def score_contract(contract: dict[str, Any], values: dict[str, dict[str, float | None]]) -> list[list[Any]]:
    validate_contract(contract)
    if contract["status"] == "blocked":
        return []
    results = []
    for patient, genes in sorted(values.items()):
        missing = [m["gene"] for m in contract["members"] if genes.get(m["gene"]) is None]
        value = None if missing else sum(genes[m["gene"]] * m["direction"] * m["weight"] for m in contract["members"])
        if value is not None and not finite(value):
            fail("score-overflow")
        results.append([contract["id"], patient, "TCGA-SYN", value,
                        "undefined" if missing else "defined", "missing-member" if missing else "",
                        contract["scale"], True])
    return results


def handoff_rows(contract: dict[str, Any], values: dict[str, dict[str, float | None]]) -> list[list[Any]]:
    validate_handoff(contract)
    results = []
    for gene in contract["genes"]:
        finite_values = [row[gene] for row in values.values() if row.get(gene) is not None]
        effect = sum(finite_values) / len(finite_values) - contract["reference_value"] if finite_values else None
        sign = "undefined" if effect is None else "negative" if effect < 0 else "positive" if effect > 0 else "zero"
        results.append([gene, "TCGA-SYN", len(finite_values), len(values) - len(finite_values), effect, sign,
                        None, None, contract["uncertainty"], contract["contrast"], contract["biological_context"],
                        " | ".join(contract["alternative_explanations"]), "fictional-not-biological-nomination", True])
    return results


def run_secondary(config: dict[str, Any], *, repo_root: Path, run_dir: Path, stage_dir: Path,
                  parent_hashes: dict[str, str], code_identity: str, interpreter: str) -> dict[str, Any]:
    registry = validate_config(config["w8"], repo_root)
    publications = {}
    for stage in ("W3", "W5", "W6", "W7"):
        publications[stage] = verify_publication(run_dir / stage, stage, identity=code_identity, config_hash=config["_config_sha256"])
        if parent_hashes.get(f"parent:{stage}") != sha256_file(run_dir / stage / "checksums.json"):
            fail(f"requested-parent-mismatch:{stage}")
        if publications[stage]["parent_hashes"].get("plan") != parent_hashes.get("plan"):
            fail(f"parent-plan-mismatch:{stage}")
    for child, parents in (("W6", ["W5"]), ("W7", ["W3", "W5", "W6"])):
        for parent in parents:
            if publications[child]["parent_hashes"].get(f"parent:{parent}") != parent_hashes[f"parent:{parent}"]:
                fail(f"cross-stage-link-mismatch:{child}:{parent}")
    load_w5_bundle(run_dir / "W5" / "bundle", expected_code_identity=code_identity)
    if publications["W6"]["bundle_sha256"] != publications["W5"]["bundle_sha256"] or publications["W6"]["final_feature_state_sha256"] != publications["W5"]["final_feature_state_sha256"]:
        fail("w5-w6-frozen-state-link")
    rows = expression_rows(run_dir / "W3" / "expression.tsv")
    values = tcga_values(rows)
    work = stage_dir.with_name(stage_dir.name + ".work")
    if work.exists() or stage_dir.exists():
        fail("output-already-exists")
    work.mkdir(parents=True)
    policy = config["w8"]
    atomic_write_json(work / "frozen_fixture_contracts.json", policy)
    statuses, blocked, scores = [], [], []
    for contract in policy["contracts"]:
        computed = score_contract(contract, values)
        scores.extend(computed)
        statuses.append([contract["id"], contract["status"], len(computed), contract.get("reason", "fictional-measurement-only-no-predictive-model"), True])
        if contract["status"] == "blocked":
            blocked.append([contract["id"], contract["reason"], True])
    for module, reason in (("MethylCIBERSORT", "official-reference-platform-qc-statistical-contract-unqualified"),
                           ("LUAD", "comparison-scale-cohort-contract-unqualified"),
                           ("approved-immunotherapy-targets", "regulatory-cutoff-categories-source-evidence-unfrozen")):
        statuses.append([module, "blocked", 0, reason, True])
        blocked.append([module, reason, True])
    atomic_write_tsv(work / "module_status.tsv", ["module", "status", "n_results", "reason", "synthetic"], statuses)
    atomic_write_tsv(work / "blocked_reasons.tsv", ["module", "reason", "synthetic"], blocked)
    atomic_write_tsv(work / "module_results.tsv", ["module", "patient_id", "cohort", "value", "status", "reason", "scale", "synthetic"], scores)
    measured = {r["symbol"] for r in rows if r["cohort"] == "TCGA-SYN" and r["value"] != "NA"}
    context = []
    modules = [p for p in registry["programs"] if p["id"].startswith(tuple(f"M{i}" for i in range(7)))]
    if len(modules) != 7:
        fail("registry-m0-m6-required")
    for program in modules:
        for gene in program["raw_gene_symbols"]:
            context.append([program["id"], gene, gene in measured, "proposed-symbol-fixture-coverage-only-not-platform-qualification", "not-scored", True])
    atomic_write_tsv(work / "registry_context.tsv", ["module", "raw_gene_symbol", "measured_in_tcga_fixture", "coverage_scope", "score_status", "synthetic"], context)
    # No invented drug, target, authority, approval or indication rows.
    atomic_write_tsv(work / "approval_evidence_targets.tsv", ["drug", "authority", "source", "approval_date", "indication", "modality", "target", "canonical_gene", "mechanism_direction", "cell_context", "assay_coverage", "disposition"], [])
    atomic_write_tsv(work / "paper_c_handoff.tsv", ["gene", "cohort", "n_finite", "n_missing", "effect", "sign", "ci_low", "ci_high", "uncertainty_status", "contrast", "biological_context", "alternative_explanations", "nomination_status", "synthetic"], handoff_rows(policy["c_handoff"], values))
    atomic_write_json(work / "handoff_provenance.json", {"synthetic": True, "contract_sha256": sha256_bytes(canonical_json_bytes(policy["c_handoff"])),
                      "expression_sha256": sha256_file(run_dir / "W3" / "expression.tsv"), "source_cohort": "TCGA-SYN",
                      "external_outcomes_used_for_selection": False, "selection": "all-predeclared-members-no-ranking",
                      "scope": "fictional-software-contract-not-real-paper-c-release"})
    artifact_hashes = {p.name: sha256_file(p) for p in work.iterdir() if p.is_file()}
    checks = {"schema_version": "B-W8-manifest-v1", "stage": "W8", "synthetic": True, "synthetic_label": LABEL,
              "parent_hashes": parent_hashes, "code_identity_sha256": code_identity, "interpreter": interpreter,
              "registry_sha256": policy["registry_sha256"], "artifact_hashes": artifact_hashes,
              "pipeline_complete": True, "completion_scope": SCOPE, "biological_validation": False,
              "named_secondary_models_complete": False, "broader_immune_barrier_framework_complete": False}
    atomic_write_json(work / "checksums.json", checks)
    atomic_write_json(work / "manifest.json", {**checks, "created_utc": utc_stamp()})
    atomic_write_json(work / "COMPLETE.json", {"stage": "W8", "status": "complete", "synthetic": True,
                      "checksums_sha256": sha256_file(work / "checksums.json"), "manifest_sha256": sha256_file(work / "manifest.json"),
                      "parent_hashes": parent_hashes, "code_identity_sha256": code_identity,
                      "pipeline_complete": True, "completion_scope": SCOPE, "biological_validation": False})
    publish_directory(work, stage_dir)
    return checks
