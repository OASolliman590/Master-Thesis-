from __future__ import annotations

import re
import shutil
import hashlib
from pathlib import Path
from typing import Any

import yaml

from ...common.io import read_tsv, write_tsv


DEFAULT_THRESHOLDS: dict[str, Any] = {
    "version": "signature_thresholds_v1",
    "signature_version": "responder_signature_v1",
    "require_common_effect_scale": True,
    "min_meta_cohorts": 2,
    "effect_column": "meta_effect_random",
    "standard_error_column": "meta_se_random",
    "fdr_column": "meta_fdr",
    "tiers": [
        {
            "name": "tier_1",
            "label": "core_wet_lab",
            "max_fdr": 0.05,
            "min_abs_effect": 1.0,
            "max_i2": 75,
            "role": "compact high-confidence wet-lab prioritization",
        },
        {
            "name": "tier_2",
            "label": "discovery",
            "max_fdr": 0.20,
            "min_abs_effect": 0.5,
            "max_i2": 85,
            "role": "broader immune biology discovery",
        },
        {
            "name": "tier_3",
            "label": "exploratory",
            "max_fdr": 0.50,
            "min_abs_effect": 0.3,
            "max_i2": None,
            "role": "sensitivity and appendix-level exploration",
        },
    ],
    "core_tiers": ["tier_1"],
}

LEGACY_SIGNATURE_FIELDS = [
    "analysis_id",
    "gene_id",
    "original_gene_id",
    "gene_symbol",
    "signature_direction",
    "meta_fdr",
    "direction_consistency",
    "signature_tier",
    "signature_variant",
]

REGISTRY_FIELDS = [
    "signature_id",
    "signature_version",
    "analysis_id",
    "analysis_family",
    "timing_label",
    "contrast_direction",
    "gene_id",
    "original_gene_id",
    "gene_symbol",
    "signature_direction",
    "effect",
    "standard_error",
    "meta_fdr",
    "n_cohorts_contributed",
    "n_patients_contributed",
    "direction_consistency",
    "heterogeneity_i2",
    "tau_squared",
    "evidence_tier",
    "evidence_tier_label",
    "module_id",
    "module_label",
    "signature_variant",
    "source_meta_path",
    "blocked_flag",
    "blocked_reason",
]

AUDIT_FIELDS = [
    "analysis_id",
    "status",
    "reason",
    "n_meta_rows",
    "n_selected_core",
    "n_selected_tiered",
    "min_meta_cohorts",
    "thresholds_version",
    "signature_version",
    "scale_columns_present",
    "source_meta_path",
]

MODULE_FIELDS = [
    "analysis_id",
    "signature_id",
    "gene_id",
    "gene_symbol",
    "module_id",
    "module_label",
    "assignment_rule",
]

LOCO_FIELDS = [
    "analysis_id",
    "fold_id",
    "holdout_cohort_id",
    "derivation_cohorts",
    "status",
    "reason",
]


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int_or_zero(value: str | None) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def load_thresholds(path: Path | None, *, min_meta_cohorts_override: int | None = None) -> dict[str, Any]:
    if path and path.exists():
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        cfg = {**DEFAULT_THRESHOLDS, **loaded}
    else:
        cfg = dict(DEFAULT_THRESHOLDS)
    if min_meta_cohorts_override is not None:
        cfg["min_meta_cohorts"] = max(1, int(min_meta_cohorts_override))
    return cfg


def _write_thresholds_copy(cfg: dict[str, Any], source: Path | None, out_path: Path) -> None:
    if source and source.exists():
        shutil.copyfile(source, out_path)
        return
    with out_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg, handle, sort_keys=False)


def _common_scale_status(rows: list[dict[str, str]]) -> tuple[bool, str, str]:
    if not rows:
        return True, "empty_meta", ""
    row0 = rows[0]
    present = [
        col
        for col in (
            "effect_scale_status",
            "effect_scale",
            "meta_effect_scale",
            "common_effect_scale",
            "assay_scale_contract",
        )
        if col in row0
    ]
    if not present:
        return False, "missing_common_scale_provenance", ""

    accepted_scale_values = {
        "common_log2",
        "common_log2_response_logfc",
        "log2",
        "log2_response_logfc",
        "log2_effect",
    }
    accepted_status_values = {
        "common_scale",
        "common_log2",
        "common_scale_log2",
        "verified_common_scale",
    }
    bool_values = {"true", "1", "yes", "y"}

    for row in rows:
        if "effect_scale_status" in row and row.get("effect_scale_status", "").strip().lower() not in accepted_status_values:
            return False, "mixed_or_unverified_effect_scale", ",".join(present)
        scale_val = (row.get("effect_scale") or row.get("meta_effect_scale") or "").strip().lower()
        if ("effect_scale" in row or "meta_effect_scale" in row) and scale_val not in accepted_scale_values:
            return False, "mixed_or_unverified_effect_scale", ",".join(present)
        if "common_effect_scale" in row and row.get("common_effect_scale", "").strip().lower() not in bool_values:
            return False, "mixed_or_unverified_effect_scale", ",".join(present)
        if "assay_scale_contract" in row:
            contract = row.get("assay_scale_contract", "").strip().lower()
            if contract and "common" not in contract and "log2" not in contract:
                return False, "mixed_or_unverified_effect_scale", ",".join(present)
    return True, "common_scale_verified", ",".join(present)


def _analysis_labels(analysis_id: str) -> tuple[str, str, str]:
    upper = analysis_id.upper()
    if "PRE" in upper:
        timing = "pre-treatment"
    elif "ON" in upper:
        timing = "on-treatment"
    elif "POST" in upper:
        timing = "post-treatment"
    elif "DELTA" in upper:
        timing = "paired-delta"
    else:
        timing = "unknown"

    family = upper.split("__", 1)[0]
    if family.endswith("_TREATMENT"):
        family = family.replace("_TREATMENT", "")
    contrast_direction = "responder_vs_non_responder"
    return family, timing, contrast_direction


def _load_module_rules(path: Path | None) -> list[dict[str, str]]:
    if path and path.exists():
        rows = read_tsv(path)
    else:
        rows = [
            {
                "module_id": "other",
                "module_label": "Other or unassigned",
                "priority": "999",
                "gene_symbol_regex": ".*",
                "gene_id_regex": "",
                "notes": "Fallback assignment.",
            }
        ]
    return sorted(rows, key=lambda r: _int_or_zero(r.get("priority", "999")))


def _assign_module(row: dict[str, str], rules: list[dict[str, str]]) -> tuple[str, str, str]:
    gene_symbol = (row.get("gene_symbol") or "").strip().upper()
    gene_id = (row.get("gene_id") or "").strip().upper()
    for rule in rules:
        symbol_re = (rule.get("gene_symbol_regex") or "").strip()
        gene_id_re = (rule.get("gene_id_regex") or "").strip()
        symbol_match = bool(symbol_re and re.search(symbol_re, gene_symbol, flags=re.IGNORECASE))
        id_match = bool(gene_id_re and re.search(gene_id_re, gene_id, flags=re.IGNORECASE))
        if symbol_match or id_match:
            return (
                rule.get("module_id", "other"),
                rule.get("module_label", "Other or unassigned"),
                symbol_re or gene_id_re or "fallback",
            )
    return "other", "Other or unassigned", "fallback"


def _derive_rows(
    rows: list[dict[str, str]],
    *,
    analysis_id: str,
    source_meta_path: Path,
    thresholds: dict[str, Any],
    module_rules: list[dict[str, str]],
    signature_variant: str,
) -> list[dict[str, str]]:
    analysis_family, timing_label, contrast_direction = _analysis_labels(analysis_id)
    min_meta_cohorts = int(thresholds.get("min_meta_cohorts", 2))
    effect_col = str(thresholds.get("effect_column", "meta_effect_random"))
    se_col = str(thresholds.get("standard_error_column", "meta_se_random"))
    fdr_col = str(thresholds.get("fdr_column", "meta_fdr"))
    signature_version = str(thresholds.get("signature_version", "responder_signature_v1"))
    tiers = thresholds.get("tiers", [])
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    for tier in tiers:
        tier_name = str(tier.get("name", "tier"))
        tier_label = str(tier.get("label", tier_name))
        max_fdr = float(tier.get("max_fdr", 1.0))
        min_abs_effect = float(tier.get("min_abs_effect", 0.0))
        max_i2 = tier.get("max_i2")
        max_i2_float = float(max_i2) if max_i2 is not None else None
        for row in rows:
            gene_id = row.get("gene_id", "")
            if not gene_id or gene_id in seen:
                continue
            effect = _float_or_none(row.get(effect_col) or row.get("meta_effect_random") or row.get("meta_effect"))
            fdr = _float_or_none(row.get(fdr_col) or row.get("meta_fdr"))
            if effect is None or fdr is None:
                continue
            n_cohorts = _int_or_zero(row.get("n_cohorts_contributed"))
            i2 = _float_or_none(row.get("heterogeneity_i2") or row.get("i2"))
            if n_cohorts < min_meta_cohorts:
                continue
            if max_i2_float is not None and i2 is not None and i2 > max_i2_float:
                continue
            if fdr > max_fdr or abs(effect) < min_abs_effect:
                continue

            module_id, module_label, _assignment_rule = _assign_module(row, module_rules)
            signature_direction = "up" if effect > 0 else "down"
            signature_id = f"{analysis_id}__{signature_version}__{tier_name}__{gene_id}"
            selected.append(
                {
                    "signature_id": signature_id,
                    "signature_version": signature_version,
                    "analysis_id": analysis_id,
                    "analysis_family": analysis_family,
                    "timing_label": timing_label,
                    "contrast_direction": contrast_direction,
                    "gene_id": gene_id,
                    "original_gene_id": row.get("original_gene_id", gene_id),
                    "gene_symbol": row.get("gene_symbol", ""),
                    "signature_direction": signature_direction,
                    "effect": f"{effect:.6g}",
                    "standard_error": row.get(se_col, row.get("meta_se_random", "")),
                    "meta_fdr": f"{fdr:.6g}",
                    "n_cohorts_contributed": row.get("n_cohorts_contributed", ""),
                    "n_patients_contributed": row.get("n_patients_contributed", ""),
                    "direction_consistency": row.get("direction_consistency", ""),
                    "heterogeneity_i2": row.get("heterogeneity_i2", row.get("i2", "")),
                    "tau_squared": row.get("tau_squared", ""),
                    "evidence_tier": tier_name,
                    "evidence_tier_label": tier_label,
                    "module_id": module_id,
                    "module_label": module_label,
                    "signature_variant": signature_variant,
                    "source_meta_path": str(source_meta_path),
                    "blocked_flag": "false",
                    "blocked_reason": "",
                }
            )
            seen.add(gene_id)
    return selected


def _legacy_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "analysis_id": row["analysis_id"],
            "gene_id": row["gene_id"],
            "original_gene_id": row["original_gene_id"],
            "gene_symbol": row["gene_symbol"],
            "signature_direction": row["signature_direction"],
            "meta_fdr": row["meta_fdr"],
            "direction_consistency": row["direction_consistency"],
            "signature_tier": row["evidence_tier"],
            "signature_variant": row["signature_variant"],
        }
        for row in rows
    ]


def _module_assignment_rows(rows: list[dict[str, str]], rules: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        _module_id, _module_label, assignment_rule = _assign_module(row, rules)
        out.append(
            {
                "analysis_id": row["analysis_id"],
                "signature_id": row["signature_id"],
                "gene_id": row["gene_id"],
                "gene_symbol": row["gene_symbol"],
                "module_id": row["module_id"],
                "module_label": row["module_label"],
                "assignment_rule": assignment_rule,
            }
        )
    return out


def _loco_rows(analysis_id: str, comparison_registry: Path | None) -> list[dict[str, str]]:
    if not comparison_registry or not comparison_registry.exists():
        return [
            {
                "analysis_id": analysis_id,
                "fold_id": "blocked_no_comparison_registry",
                "holdout_cohort_id": "",
                "derivation_cohorts": "",
                "status": "blocked",
                "reason": "comparison_registry_unavailable",
            }
        ]
    cohorts = sorted(
        {
            row.get("cohort_id", "")
            for row in read_tsv(comparison_registry)
            if row.get("analysis_id", "") == analysis_id and row.get("cohort_id", "")
        }
    )
    if len(cohorts) < 2:
        return [
            {
                "analysis_id": analysis_id,
                "fold_id": "blocked_insufficient_cohorts",
                "holdout_cohort_id": cohorts[0] if cohorts else "",
                "derivation_cohorts": ",".join(cohorts),
                "status": "blocked",
                "reason": "need_at_least_two_cohorts_for_loco",
            }
        ]
    out = []
    for idx, holdout in enumerate(cohorts, start=1):
        derivation = [cohort for cohort in cohorts if cohort != holdout]
        out.append(
            {
                "analysis_id": analysis_id,
                "fold_id": f"loco_{idx:03d}",
                "holdout_cohort_id": holdout,
                "derivation_cohorts": ",".join(derivation),
                "status": "planned",
                "reason": "leave_one_cohort_out_derivation_plan",
            }
        )
    return out


def _write_checksums(paths: list[Path], out_dir: Path) -> Path:
    repro_dir = out_dir / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)
    checksum_path = repro_dir / "checksums.sha256"
    rows = []
    for path in sorted({p for p in paths if p.exists()}):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}\t{path.relative_to(out_dir)}")
    checksum_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return checksum_path


def derive_signature_outputs(
    *,
    analysis_id: str,
    meta_dir: Path,
    out_dir: Path,
    thresholds_path: Path | None = None,
    module_rules_path: Path | None = None,
    comparison_registry_path: Path | None = None,
    min_meta_cohorts: int | None = None,
    allow_empty_signature: bool = False,
    composition_adjusted_meta_dir: Path | None = None,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = meta_dir / "meta_effects.tsv"
    if not meta_path.exists():
        raise RuntimeError(f"Missing meta-effects file for signature derivation: {meta_path}")

    thresholds = load_thresholds(thresholds_path, min_meta_cohorts_override=min_meta_cohorts)
    module_rules = _load_module_rules(module_rules_path)
    rows = read_tsv(meta_path)
    if not rows and not allow_empty_signature:
        raise RuntimeError(
            f"Meta-effects file is empty for {analysis_id}: {meta_path}. "
            "Refusing to emit an empty signature."
        )

    thresholds_copy = out_dir / "signature_thresholds.yaml"
    _write_thresholds_copy(thresholds, thresholds_path, thresholds_copy)

    scale_ok, scale_reason, scale_cols = _common_scale_status(rows)
    registry_path = out_dir / "signature_registry.tsv"
    core_path = out_dir / "responder_signature_core.tsv"
    tiered_path = out_dir / "responder_signature_tiered.tsv"
    audit_path = out_dir / "signature_derivation_audit.tsv"
    module_path = out_dir / "signature_module_assignment.tsv"
    loco_path = out_dir / "signature_loco_derivation_manifest.tsv"
    legacy_path = out_dir / f"{analysis_id.lower()}_signature_v1.tsv"
    outputs = [registry_path, core_path, tiered_path, audit_path, thresholds_copy, module_path, loco_path, legacy_path]

    if thresholds.get("require_common_effect_scale", True) and not scale_ok:
        write_tsv(registry_path, fieldnames=REGISTRY_FIELDS, rows=[])
        write_tsv(core_path, fieldnames=REGISTRY_FIELDS, rows=[])
        write_tsv(tiered_path, fieldnames=REGISTRY_FIELDS, rows=[])
        write_tsv(module_path, fieldnames=MODULE_FIELDS, rows=[])
        write_tsv(loco_path, fieldnames=LOCO_FIELDS, rows=_loco_rows(analysis_id, comparison_registry_path))
        write_tsv(legacy_path, fieldnames=LEGACY_SIGNATURE_FIELDS, rows=[])
        write_tsv(
            audit_path,
            fieldnames=AUDIT_FIELDS,
            rows=[
                {
                    "analysis_id": analysis_id,
                    "status": "blocked",
                    "reason": scale_reason,
                    "n_meta_rows": str(len(rows)),
                    "n_selected_core": "0",
                    "n_selected_tiered": "0",
                    "min_meta_cohorts": str(thresholds.get("min_meta_cohorts", "")),
                    "thresholds_version": str(thresholds.get("version", "")),
                    "signature_version": str(thresholds.get("signature_version", "")),
                    "scale_columns_present": scale_cols,
                    "source_meta_path": str(meta_path),
                }
            ],
        )
        outputs.append(_write_checksums(outputs, out_dir))
        return outputs

    tiered_rows = _derive_rows(
        rows,
        analysis_id=analysis_id,
        source_meta_path=meta_path,
        thresholds=thresholds,
        module_rules=module_rules,
        signature_variant="composition_unadjusted_primary",
    )
    core_tiers = set(thresholds.get("core_tiers", ["tier_1"]))
    core_rows = [row for row in tiered_rows if row["evidence_tier"] in core_tiers]
    if not tiered_rows and not allow_empty_signature:
        raise RuntimeError(
            f"No signature genes passed any threshold tier with "
            f"n_cohorts_contributed>={thresholds.get('min_meta_cohorts')} for {analysis_id}. "
            "Use --allow-empty-signature to override."
        )

    write_tsv(registry_path, fieldnames=REGISTRY_FIELDS, rows=tiered_rows)
    write_tsv(core_path, fieldnames=REGISTRY_FIELDS, rows=core_rows)
    write_tsv(tiered_path, fieldnames=REGISTRY_FIELDS, rows=tiered_rows)
    write_tsv(module_path, fieldnames=MODULE_FIELDS, rows=_module_assignment_rows(tiered_rows, module_rules))
    write_tsv(loco_path, fieldnames=LOCO_FIELDS, rows=_loco_rows(analysis_id, comparison_registry_path))
    write_tsv(legacy_path, fieldnames=LEGACY_SIGNATURE_FIELDS, rows=_legacy_rows(tiered_rows))
    write_tsv(
        audit_path,
        fieldnames=AUDIT_FIELDS,
        rows=[
            {
                "analysis_id": analysis_id,
                "status": "completed",
                "reason": scale_reason,
                "n_meta_rows": str(len(rows)),
                "n_selected_core": str(len(core_rows)),
                "n_selected_tiered": str(len(tiered_rows)),
                "min_meta_cohorts": str(thresholds.get("min_meta_cohorts", "")),
                "thresholds_version": str(thresholds.get("version", "")),
                "signature_version": str(thresholds.get("signature_version", "")),
                "scale_columns_present": scale_cols,
                "source_meta_path": str(meta_path),
            }
        ],
    )

    if composition_adjusted_meta_dir:
        adjusted_path = composition_adjusted_meta_dir / "meta_effects.tsv"
        if not adjusted_path.exists():
            raise RuntimeError(
                "Requested composition-adjusted secondary signature, but missing "
                f"meta-effects file: {adjusted_path}"
            )
        adjusted_rows_raw = read_tsv(adjusted_path)
        adjusted_ok, adjusted_reason, _adjusted_cols = _common_scale_status(adjusted_rows_raw)
        if thresholds.get("require_common_effect_scale", True) and not adjusted_ok:
            raise RuntimeError(
                "Composition-adjusted secondary signature is blocked by common-scale guard: "
                f"{adjusted_reason}"
            )
        adjusted_rows = _derive_rows(
            adjusted_rows_raw,
            analysis_id=analysis_id,
            source_meta_path=adjusted_path,
            thresholds=thresholds,
            module_rules=module_rules,
            signature_variant="composition_adjusted_secondary",
        )
        adjusted_out = out_dir / f"{analysis_id.lower()}_signature_composition_adjusted_secondary.tsv"
        write_tsv(adjusted_out, fieldnames=LEGACY_SIGNATURE_FIELDS, rows=_legacy_rows(adjusted_rows))
        outputs.append(adjusted_out)

    outputs.append(_write_checksums(outputs, out_dir))
    return outputs
