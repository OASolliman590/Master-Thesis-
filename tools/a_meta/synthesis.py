"""Stratified random-effects synthesis for A-META effect tables."""
from __future__ import annotations

import csv
import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from .endpoint_definitions import endpoint_is_per_study_only, is_known_endpoint_definition
from .provenance import (
    preflight_effect_file,
    validate_effect_rows_provenance,
)
from .r_manifest import run_r_sanitised


SYNTHESIS_COLUMNS = (
    "unit_family", "unit", "endpoint_family", "endpoint_definition_id",
    "study", "patient_set_id", "n_R", "n_NR", "stratum_type", "stratum",
    "cancer", "drug_class_stratum", "stage", "k", "estimate", "se",
    "n_cancers", "n_studies",
    "ci_lb", "ci_ub", "tau2", "I2", "Q", "p", "fixed_estimate",
    "fixed_ci_lb", "fixed_ci_ub", "q", "label", "low_k", "status",
    "reason", "weighting",
)
SUBGROUP_COLUMNS = (
    "unit_family", "unit", "endpoint_family", "endpoint_definition_id", "moderator", "total_k",
    "n_levels", "F", "p", "status", "reason",
)
_STRATA = {"per_cancer", "per_drug_class", "across_cancers", "melanoma_cancer_drug"}
_LOW_K_CLASSES = {"ANTI_CTLA4", "DUAL_PD1_CTLA4"}


@dataclass(frozen=True)
class SynthesisResult:
    summaries: list[dict]
    subgroup_tests: list[dict]
    metadata: dict = field(default_factory=dict)
    r_manifest: dict | None = None


def synthesize(
    effects: Sequence[Mapping] | Path | str,
    stratum: str,
    *,
    output_dir: Path | str | None = None,
    runner=None,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
) -> SynthesisResult:
    """Pool per-study effects for one declared A-META synthesis stratum.

    `stratum` is `per_cancer`, `per_drug_class`, `across_cancers`, or
    `melanoma_cancer_drug`. All grouping retains unit family and endpoint family.
    """
    if stratum not in _STRATA:
        raise ValueError("Unknown synthesis stratum")
    if isinstance(effects, (str, Path)):
        preflight_effect_file(
            effects,
            allow_outcomes=allow_outcomes,
            provenance_manifest=provenance_manifest,
        )
    rows = _read_effects(effects)
    validate_effect_rows_provenance(
        effects,
        rows,
        allow_outcomes=allow_outcomes,
        provenance_manifest=provenance_manifest,
    )
    pooled_rows = [
        row for row in rows
        if not endpoint_is_per_study_only(row["endpoint_definition_id"], row["endpoint_family"])
    ]
    groups, effect_rows = _plan_groups(pooled_rows, stratum)
    subgroup_groups, subgroup_rows = _plan_subgroups(pooled_rows, stratum)
    per_study_summaries = _per_study_summaries(rows, stratum)
    if not groups:
        return SynthesisResult(
            summaries=per_study_summaries,
            subgroup_tests=[],
            metadata=_metadata(stratum),
        )

    run_dir = Path(output_dir) if output_dir is not None else _default_run_dir(rows, stratum)
    run_dir.mkdir(parents=True, exist_ok=True)
    group_path = run_dir / "groups.tsv"
    effect_path = run_dir / "meta_input.tsv"
    subgroup_path = run_dir / "subgroup_input.tsv"
    _write_tsv(group_path, groups, tuple(groups[0]))
    _write_tsv(
        effect_path,
        effect_rows,
        ("analysis_id", "study", "patient_set_id", "cancer", "cancer_components", "yi", "vi"),
    )
    _write_tsv(
        subgroup_path,
        subgroup_rows,
        ("test_id", "study", "patient_set_id", "stratum", "n_studies", "total_k", "yi", "vi"),
    )

    script = Path(__file__).resolve().parents[2] / "r/scripts/meta_rma.R"
    r_result = run_r_sanitised(
        script,
        {"groups": group_path, "effects": effect_path, "subgroups": subgroup_path},
        {"expected_outputs": ["meta.tsv", "subgroups.tsv"]},
        run_dir / "R",
        script_id="r/scripts/meta_rma.R",
        runner=runner,
    )
    fitted = _index_rows(_read_tsv(r_result.outputs["meta.tsv"]), "analysis_id")
    subgroup_fits = _index_rows(_read_tsv(r_result.outputs["subgroups.tsv"]), "test_id")
    effects_by_analysis: dict[str, list[dict]] = defaultdict(list)
    for effect in effect_rows:
        effects_by_analysis[effect["analysis_id"]].append(effect)
    summaries = list(per_study_summaries)
    for group in groups:
        fit = fitted.get(group["analysis_id"])
        group_effects = effects_by_analysis.get(group["analysis_id"], [])
        if group["unit_family"] == "gene" and _integer(fit.get("k"), default=0) == 2:
            summaries.extend(_gene_unpooled_rows(group, fit, group_effects))
        else:
            summaries.append(_summary(group, fit, group_effects))
    _apply_fdr(summaries)
    subgroup_tests = [
        _subgroup_result(group, subgroup_fits.get(group["test_id"]))
        for group in subgroup_groups
    ]
    summaries.sort(key=_summary_sort_key)
    subgroup_tests.sort(key=lambda row: (row["unit_family"], row["endpoint_family"], row["unit"], row["moderator"]))
    return SynthesisResult(
        summaries=summaries,
        subgroup_tests=subgroup_tests,
        metadata=_metadata(stratum),
        r_manifest=r_result.manifest,
    )


def _plan_groups(rows: list[dict], stratum: str) -> tuple[list[dict], list[dict]]:
    identities = sorted({
        (row["unit_family"], row["unit"], row["endpoint_family"], row["endpoint_definition_id"])
        for row in rows
    })
    specs: list[dict] = []
    if stratum == "per_cancer":
        for unit_family, unit, endpoint, definition_id in identities:
            pairs = sorted({(row["cancer"], row["drug_class_stratum"]) for row in rows
                            if row["unit_family"] == unit_family and row["unit"] == unit
                            and row["endpoint_family"] == endpoint
                            and row["endpoint_definition_id"] == definition_id
                            and row["drug_class_stratum"] == "ALL"
                            and row["cancer"] != "multi"})
            for cancer, drug_class in pairs:
                _add_direct_spec(specs, rows, unit_family, unit, endpoint, definition_id,
                                 stratum_type="cancer", stratum_value=cancer,
                                 cancer=cancer, drug_class=drug_class, stage="within_cancer")
    elif stratum == "per_drug_class":
        for unit_family, unit, endpoint, definition_id in identities:
            classes = sorted({row["drug_class_stratum"] for row in rows
                              if row["unit_family"] == unit_family and row["unit"] == unit
                              and row["endpoint_family"] == endpoint
                              and row["endpoint_definition_id"] == definition_id
                              and row["drug_class_stratum"] != "ALL"})
            for drug_class in classes:
                _add_direct_spec(specs, rows, unit_family, unit, endpoint, definition_id,
                                 stratum_type="drug_class", stratum_value=drug_class,
                                 cancer="ALL", drug_class=drug_class, stage="per_drug_class")
    elif stratum == "melanoma_cancer_drug":
        for unit_family, unit, endpoint, definition_id in identities:
            classes = sorted({row["drug_class_stratum"] for row in rows
                              if row["unit_family"] == unit_family and row["unit"] == unit
                              and row["endpoint_family"] == endpoint
                              and row["endpoint_definition_id"] == definition_id
                              and row["cancer"] == "melanoma"
                              and row["drug_class_stratum"] != "ALL"})
            for drug_class in classes:
                _add_direct_spec(specs, rows, unit_family, unit, endpoint, definition_id,
                                 stratum_type="cancer_drug", stratum_value=f"melanoma|{drug_class}",
                                 cancer="melanoma", drug_class=drug_class, stage="melanoma_cancer_drug")
    else:
        for unit_family, unit, endpoint, definition_id in identities:
            classes = sorted({row["drug_class_stratum"] for row in rows
                              if row["unit_family"] == unit_family and row["unit"] == unit
                              and row["endpoint_family"] == endpoint
                              and row["endpoint_definition_id"] == definition_id})
            for drug_class in classes:
                cancers = sorted({row["cancer"] for row in rows
                                  if row["unit_family"] == unit_family and row["unit"] == unit
                                  and row["endpoint_family"] == endpoint
                                  and row["endpoint_definition_id"] == definition_id
                                  and row["drug_class_stratum"] == drug_class
                                  and row["cancer"] != "multi"})
                parent_key = ("across_cancers", unit_family, unit, endpoint, definition_id, drug_class)
                for cancer in cancers:
                    _add_direct_spec(
                        specs, rows, unit_family, unit, endpoint, definition_id,
                        stratum_type="cancer", stratum_value=cancer,
                        cancer=cancer, drug_class=drug_class, stage="stage1_within_cancer",
                        parent_key=parent_key, analysis_type="across_within",
                    )
                specs.append({
                    "analysis_key": parent_key,
                    "analysis_type": "across_cancers",
                    "stage": "stage2_across_cancers",
                    "parent_key": "",
                    "unit_family": unit_family,
                    "unit": unit,
                    "endpoint_family": endpoint,
                    "endpoint_definition_id": definition_id,
                    "stratum_type": "across_cancers",
                    "stratum": drug_class,
                    "cancer": "ALL",
                    "drug_class_stratum": drug_class,
                    "weighting": "two-stage; REML uses real cancer variances with equal metafor weights (unweighted cancer mean)",
                    "effects": [],
                })

    specs.sort(key=lambda group: (
        group["analysis_type"], group["unit_family"], group["unit"],
        group["endpoint_family"], group["stratum_type"], group["stratum"],
        group["endpoint_definition_id"], group["cancer"], group["drug_class_stratum"],
    ))
    key_to_id = {group["analysis_key"]: f"A{index:05d}" for index, group in enumerate(specs, 1)}
    for group in specs:
        group["analysis_id"] = key_to_id[group["analysis_key"]]
        group["parent_id"] = key_to_id.get(group["parent_key"], "") if group.get("parent_key") else ""
        group["min_k"] = 3 if group["unit_family"] == "gene" else 2
        group["requires_fit"] = "true"
        group["weighting"] = group.get("weighting") or "inverse-variance random effects across studies"

    group_rows = []
    input_rows = []
    for group in specs:
        group_rows.append({key: value for key, value in group.items()
                           if key not in {"analysis_key", "parent_key", "effects"}})
        seen_studies = set()
        seen_patient_sets = set()
        for effect in group["effects"]:
            study = effect["study"]
            if study in seen_studies:
                raise ValueError("A synthesis stratum contains more than one effect from a study")
            seen_studies.add(study)
            patient_set_id = effect["patient_set_id"]
            if patient_set_id in seen_patient_sets:
                raise ValueError("A synthesis stratum contains a patient set more than once")
            seen_patient_sets.add(patient_set_id)
            input_rows.append({
                "analysis_id": group["analysis_id"],
                "study": study,
                "patient_set_id": patient_set_id,
                "cancer": effect["cancer"],
                "cancer_components": effect.get("cancer_components", effect["cancer"]),
                "n_R": effect.get("n_R", ""),
                "n_NR": effect.get("n_NR", ""),
                "yi": effect["g"],
                "vi": float(effect["se"]) ** 2,
            })
    return group_rows, input_rows


def _add_direct_spec(specs, rows, unit_family, unit, endpoint, definition_id, *,
                     stratum_type, stratum_value, cancer, drug_class, stage,
                     parent_key=None, analysis_type="direct"):
    effects = [
        row for row in rows
        if row["unit_family"] == unit_family and row["unit"] == unit
        and row["endpoint_family"] == endpoint
        and row["endpoint_definition_id"] == definition_id
        and row["drug_class_stratum"] == drug_class
        and (cancer == "ALL" or row["cancer"] == cancer)
        and _valid_effect(row)
    ]
    if cancer == "ALL":
        effects = _one_effect_per_study(effects, prefer_aggregate=True)
    else:
        effects = _one_effect_per_study(effects, prefer_aggregate=False)
    key = (analysis_type, unit_family, unit, endpoint, definition_id, stratum_type, stratum_value,
           cancer, drug_class, stage)
    specs.append({
        "analysis_key": key,
        "analysis_type": analysis_type,
        "stage": stage,
        "parent_key": parent_key or "",
        "unit_family": unit_family,
        "unit": unit,
        "endpoint_family": endpoint,
        "endpoint_definition_id": definition_id,
        "stratum_type": stratum_type,
        "stratum": stratum_value,
        "cancer": cancer,
        "drug_class_stratum": drug_class,
        "weighting": "",
        "effects": effects,
    })


def _plan_subgroups(rows: list[dict], stratum: str) -> tuple[list[dict], list[dict]]:
    if stratum == "per_cancer":
        selected = [row for row in rows if row["drug_class_stratum"] == "ALL"]
        moderator = "cancer"
    elif stratum == "melanoma_cancer_drug":
        selected = [row for row in rows if row["cancer"] == "melanoma" and row["drug_class_stratum"] != "ALL"]
        moderator = "drug_class"
    else:
        selected = [row for row in rows if row["drug_class_stratum"] != "ALL"]
        moderator = "drug_class"
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in selected:
        grouped[(row["unit_family"], row["unit"], row["endpoint_family"],
                 row["endpoint_definition_id"])].append(row)
    tests, input_rows = [], []
    for key in sorted(grouped):
        unit_family, unit, endpoint, definition_id = key
        candidates = [row for row in grouped[key] if _valid_effect(row)]
        # Every moderator fit is a per-study analysis. Keep one aggregate
        # effect when present; otherwise require one cancer-specific row.
        usable = _one_effect_per_study(candidates, prefer_aggregate=True)
        _assert_unique_patient_sets(usable, "A subgroup test")
        n_studies = len({row["study"] for row in usable})
        levels = sorted({row["cancer"] if moderator == "cancer" else row["drug_class_stratum"]
                         for row in usable})
        test_id = f"T{len(tests) + 1:05d}"
        reason = ""
        status = "pending"
        if n_studies < 10:
            status, reason = "not_tested", "total_k<10"
        elif len(levels) < 2:
            status, reason = "not_tested", "fewer_than_two_strata"
        tests.append({
            "test_id": test_id,
            "unit_family": unit_family,
            "unit": unit,
            "endpoint_family": endpoint,
            "endpoint_definition_id": definition_id,
            "moderator": moderator,
            "total_k": n_studies,
            "n_levels": len(levels),
            "status": status,
            "reason": reason,
        })
        if status == "pending":
            for row in usable:
                level = row["cancer"] if moderator == "cancer" else row["drug_class_stratum"]
                input_rows.append({
                    "test_id": test_id,
                    "study": row["study"],
                    "patient_set_id": row["patient_set_id"],
                    "stratum": level,
                    "n_studies": n_studies,
                    "total_k": len(usable),
                    "yi": row["g"],
                    "vi": float(row["se"]) ** 2,
                })
    return tests, input_rows


def _summary(group: Mapping, fit: Mapping | None, input_effects: Sequence[Mapping] = ()) -> dict:
    unit_family = group["unit_family"]
    # Effect rows are not retained in the group TSV. The R result supplies k
    # and the requested fit status for all groups, including single-study rows.
    if fit is None:
        k = 0
    else:
        k = _integer(fit.get("k"), default=0)
    label = _label(k)
    status = str(fit.get("status", "not_estimable")) if fit else "not_estimable"
    reason = str(fit.get("reason", "no_estimable_studies")) if fit else "no_estimable_studies"
    if group["stage"] == "stage2_across_cancers" and k == 1:
        label = "single_cancer"
        status = "single_cancer"
        reason = "one cancer contributes; no cross-cancer pooling"
    if unit_family == "gene" and 1 < k < 3:
        label = "tentative_k2" if k == 2 else "standard"
        status = "not_pooled"
        reason = "gene_pooling_requires_k>=3"
    result = {
        "unit_family": unit_family,
        "unit": group["unit"],
        "endpoint_family": group["endpoint_family"],
        "endpoint_definition_id": group["endpoint_definition_id"],
        "study": "",
        "patient_set_id": "",
        "n_R": None,
        "n_NR": None,
        "stratum_type": group["stratum_type"],
        "stratum": group["stratum"],
        "cancer": group["cancer"],
        "drug_class_stratum": group["drug_class_stratum"],
        "stage": group["stage"],
        "k": k,
        "estimate": _float(fit.get("estimate")) if fit else None,
        "se": _float(fit.get("se")) if fit else None,
        "n_cancers": _integer(fit.get("n_cancers"), default=0) if fit else 0,
        "n_studies": _integer(fit.get("n_studies"), default=0) if fit else 0,
        "ci_lb": _float(fit.get("ci_lb")) if fit else None,
        "ci_ub": _float(fit.get("ci_ub")) if fit else None,
        "tau2": _float(fit.get("tau2")) if fit else None,
        "I2": _float(fit.get("I2")) if fit else None,
        "Q": _float(fit.get("Q")) if fit else None,
        "p": _float(fit.get("p")) if fit else None,
        "fixed_estimate": _float(fit.get("fixed_estimate")) if fit else None,
        "fixed_ci_lb": _float(fit.get("fixed_ci_lb")) if fit else None,
        "fixed_ci_ub": _float(fit.get("fixed_ci_ub")) if fit else None,
        "q": None,
        "label": label,
        "low_k": group["drug_class_stratum"] in _LOW_K_CLASSES and k <= 3,
        "status": status,
        "reason": reason,
        "weighting": group["weighting"],
    }
    if label == "single_study" and result["estimate"] is None and fit:
        # A single effect is passed through by meta_rma.R with its normal CI.
        result["status"] = "not_estimable"
        result["reason"] = "single_study_has_no_estimable_effect"
    if k == 1 and len(input_effects) == 1:
        single = input_effects[0]
        result["study"] = single["study"]
        result["patient_set_id"] = single["patient_set_id"]
        result["n_R"] = single.get("n_R")
        result["n_NR"] = single.get("n_NR")
    return result


def _gene_unpooled_rows(group: Mapping, fit: Mapping | None, input_effects: Sequence[Mapping]) -> list[dict]:
    base = _summary(group, fit)
    if not input_effects:
        return [base]
    results = []
    for effect in input_effects:
        yi = float(effect["yi"])
        standard_error = math.sqrt(float(effect["vi"]))
        row = dict(base)
        row.update({
            "study": effect["study"],
            "patient_set_id": effect["patient_set_id"],
            "n_R": effect.get("n_R"),
            "n_NR": effect.get("n_NR"),
            "stage": "per_study",
            "estimate": yi,
            "se": standard_error,
            "ci_lb": yi - 1.96 * standard_error,
            "ci_ub": yi + 1.96 * standard_error,
            "tau2": None,
            "I2": None,
            "Q": None,
            "p": None,
            "fixed_estimate": None,
            "fixed_ci_lb": None,
            "fixed_ci_ub": None,
            "q": None,
            "label": _label(_integer(fit.get("k"), default=0)) if fit else "not_estimable",
            "status": "not_pooled",
            "reason": "gene_pooling_requires_k>=3; per-study effect retained",
            "weighting": "not pooled; gene synthesis requires k>=3",
        })
        results.append(row)
    return results


def _subgroup_result(group: Mapping, fit: Mapping | None) -> dict:
    return {
        "unit_family": group["unit_family"],
        "unit": group["unit"],
        "endpoint_family": group["endpoint_family"],
        "endpoint_definition_id": group["endpoint_definition_id"],
        "moderator": group["moderator"],
        "total_k": group["total_k"],
        "n_levels": group["n_levels"],
        "F": _float(fit.get("F")) if fit else None,
        "p": _float(fit.get("p")) if fit else None,
        "status": str(fit.get("status")) if fit and fit.get("status") else group["status"],
        "reason": str(fit.get("reason", "")) if fit else group["reason"],
    }


def _one_effect_per_study(rows: Sequence[Mapping], *, prefer_aggregate: bool) -> list[dict]:
    by_study: dict[str, list[dict]] = defaultdict(list)
    for raw in rows:
        by_study[str(raw["study"])].append(dict(raw))
    selected = []
    for study in sorted(by_study):
        candidates = by_study[study]
        aggregates = [row for row in candidates if row["cancer"] == "multi"]
        if prefer_aggregate and aggregates:
            if len(aggregates) != 1:
                raise ValueError("A study has duplicate multi-cancer aggregate effects")
            selected.append(aggregates[0])
            continue
        cancer_specific = [row for row in candidates if row["cancer"] != "multi"]
        if len(cancer_specific) == 1:
            selected.append(cancer_specific[0])
            continue
        if not cancer_specific and len(candidates) == 1:
            selected.append(candidates[0])
            continue
        raise ValueError(
            f"Study {study!r} has multiple cancer-specific effects but no selected aggregate"
        )
    _assert_unique_patient_sets(selected, "A synthesis stratum")
    return selected


def _assert_unique_patient_sets(rows: Sequence[Mapping], context: str) -> None:
    seen = set()
    by_study: dict[str, list[Mapping]] = defaultdict(list)
    for row in rows:
        if not _valid_effect(row):
            continue
        study = str(row.get("study", ""))
        for previous in by_study[study]:
            if _cancer_component_overlap(previous, row):
                raise ValueError(
                    f"{context} contains an aggregate and overlapping cancer-component effect for study {study!r}"
                )
        by_study[study].append(row)
        patient_set_id = str(row.get("patient_set_id", ""))
        if not patient_set_id:
            raise ValueError(f"{context} requires a patient_set_id for every effect")
        if patient_set_id in seen:
            raise ValueError(f"{context} contains a patient set more than once")
        seen.add(patient_set_id)


def _cancer_component_overlap(left: Mapping, right: Mapping) -> bool:
    """Detect a same-study aggregate/component overlap even when hashes differ."""
    if str(left.get("study", "")) != str(right.get("study", "")):
        return False
    left_cancer = str(left.get("cancer", "")).strip().casefold()
    right_cancer = str(right.get("cancer", "")).strip().casefold()
    left_components = _component_set(left)
    right_components = _component_set(right)
    if left_cancer == "multi" and right_cancer == "multi":
        return not left_components or not right_components or bool(left_components & right_components)
    if left_cancer == "multi":
        return not left_components or right_cancer in left_components
    if right_cancer == "multi":
        return not right_components or left_cancer in right_components
    return False


def _component_set(row: Mapping) -> set[str]:
    components = {
        component.strip().casefold()
        for component in str(row.get("cancer_components", "")).split(",")
        if component.strip()
    }
    if not components and str(row.get("cancer", "")).strip().casefold() != "multi":
        components.add(str(row.get("cancer", "")).strip().casefold())
    return components


def _per_study_summaries(rows: Sequence[Mapping], stratum: str) -> list[dict]:
    per_study = [
        dict(row) for row in rows
        if endpoint_is_per_study_only(row["endpoint_definition_id"], row["endpoint_family"])
    ]
    if stratum == "per_cancer":
        selected = [row for row in per_study if row["drug_class_stratum"] == "ALL" and row["cancer"] != "multi"]
        stratum_type = "cancer"
    elif stratum == "melanoma_cancer_drug":
        selected = [row for row in per_study if row["cancer"] == "melanoma" and row["drug_class_stratum"] != "ALL"]
        stratum_type = "cancer_drug"
    elif stratum == "per_drug_class":
        selected = [row for row in per_study if row["drug_class_stratum"] != "ALL"]
        stratum_type = "drug_class"
    else:
        selected = [row for row in per_study if row["drug_class_stratum"] != "ALL"]
        stratum_type = "across_cancers"

    if stratum in {"per_drug_class", "across_cancers"}:
        buckets: dict[tuple, list[dict]] = defaultdict(list)
        for row in selected:
            key = (
                row["unit_family"], row["unit"], row["endpoint_family"],
                row["endpoint_definition_id"], row["drug_class_stratum"],
            )
            buckets[key].append(row)
        selected = [
            effect
            for bucket in buckets.values()
            for effect in _one_effect_per_study(bucket, prefer_aggregate=True)
        ]
    else:
        _assert_unique_patient_sets(selected, "Per-study-only synthesis output")

    summaries = []
    for effect in selected:
        g = effect.get("g") if effect.get("status") == "ok" else None
        se = effect.get("se") if effect.get("status") == "ok" else None
        study = str(effect["study"])
        cancer = str(effect["cancer"])
        drug_class = str(effect["drug_class_stratum"])
        stratum_value = (
            cancer if stratum_type == "cancer"
            else f"{cancer}|{drug_class}" if stratum_type == "cancer_drug"
            else drug_class if stratum_type == "drug_class"
            else drug_class
        )
        reason = "source-defined endpoint is reported per study only"
        if effect.get("reason"):
            reason = f"{reason}; {effect['reason']}"
        summaries.append({
            "unit_family": effect["unit_family"],
            "unit": effect["unit"],
            "endpoint_family": effect["endpoint_family"],
            "endpoint_definition_id": effect["endpoint_definition_id"],
            "study": study,
            "patient_set_id": effect["patient_set_id"],
            "n_R": effect.get("n_R"),
            "n_NR": effect.get("n_NR"),
            "stratum_type": stratum_type,
            "stratum": stratum_value,
            "cancer": cancer,
            "drug_class_stratum": drug_class,
            "stage": "per_study",
            "k": 1,
            "estimate": g,
            "se": se,
            "n_cancers": len([value for value in str(effect.get("cancer_components", "")).split(",") if value]),
            "n_studies": 1,
            "ci_lb": g - 1.96 * se if g is not None and se is not None else None,
            "ci_ub": g + 1.96 * se if g is not None and se is not None else None,
            "tau2": None,
            "I2": None,
            "Q": None,
            "p": None,
            "fixed_estimate": None,
            "fixed_ci_lb": None,
            "fixed_ci_ub": None,
            "q": None,
            "label": "per_study_only",
            "low_k": drug_class in _LOW_K_CLASSES,
            "status": "per_study_only",
            "reason": reason,
            "weighting": "not pooled; source-defined endpoint reported by study",
        })
    return summaries


def _apply_fdr(summaries: list[dict]) -> None:
    families: dict[tuple, list[dict]] = defaultdict(list)
    for row in summaries:
        is_pooled = row["status"] == "pooled" and row["p"] is not None
        if row["unit_family"] == "gene" and row["k"] < 3:
            is_pooled = False
        if is_pooled:
            key = (
                row["unit_family"], row["stratum_type"], row["stratum"],
                row["endpoint_family"], row["endpoint_definition_id"],
                row["cancer"], row["drug_class_stratum"],
                row["stage"],
            )
            families[key].append(row)
    for family_rows in families.values():
        p_values = [row["p"] for row in family_rows]
        q_values = _bh(p_values)
        for row, q_value in zip(family_rows, q_values):
            row["q"] = q_value


def _bh(values: Sequence[float]) -> list[float]:
    count = len(values)
    order = sorted(range(count), key=lambda index: (values[index], index))
    adjusted = [0.0] * count
    running = 1.0
    for reverse_rank in range(count - 1, -1, -1):
        index = order[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, float(values[index]) * count / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def _read_effects(effects) -> list[dict]:
    if isinstance(effects, (str, Path)):
        with Path(effects).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
    else:
        rows = [dict(row) for row in effects]
    required = {"unit_family", "unit", "study", "cancer", "drug_class_stratum",
                "endpoint_family", "endpoint_definition_id", "patient_set_id",
                "g", "se", "status"}
    if rows and not required.issubset(rows[0]):
        raise ValueError("Effect table is missing required A-META columns")
    result = []
    for raw in rows:
        row = dict(raw)
        for field in ("g", "se"):
            row[field] = _float(row.get(field))
        for field in (
            "unit_family", "unit", "study", "cancer", "drug_class_stratum",
            "endpoint_family", "endpoint_definition_id", "patient_set_id", "status",
        ):
            row[field] = str(row.get(field, "")).strip()
        if not is_known_endpoint_definition(row["endpoint_definition_id"], row["endpoint_family"]):
            raise ValueError("Effect table contains an unmapped endpoint_definition_id")
        result.append(row)
    return result


def _valid_effect(row: Mapping) -> bool:
    return row.get("status") == "ok" and row.get("g") is not None and row.get("se") is not None and row["se"] > 0


def _label(k: int) -> str:
    if k == 1:
        return "single_study"
    if k == 2:
        return "tentative_k2"
    if k >= 3:
        return "standard"
    return "not_estimable"


def _metadata(stratum: str) -> dict:
    return {
        "stratum_definition": stratum,
        "random_effects": "metafor::rma(method='REML', test='adhoc')",
        "fixed_effect_sensitivity": "metafor::rma(method='FE')",
        "cross_cancer_weighting": (
            "Two-stage: random-effects pool within each cancer, then pool cancer estimates "
            "with an equal-weight cancer mean; stage-two REML retains each cancer estimate's "
            "sampling variance and uses equal metafor weights."
        ),
        "row_selection": {
            "cancer_strata": "use cancer-specific rows; multi-cancer aggregate rows are excluded",
            "all-cancer-drug-strata": "prefer one multi-cancer aggregate per study; otherwise require one cancer-specific row",
            "cancer-subgroup-test": "prefer one multi-cancer aggregate per study; otherwise require one cancer-specific row",
            "subgroup_duplicate_patient_sets": "refuse duplicate patient-set hashes before fitting",
        },
        "fdr_method": "Benjamini-Hochberg",
        "fdr_threshold": 0.10,
        "fdr_scope": "unit_family x stratum x endpoint_family x endpoint_definition_id; pooled units only",
        "gene_pool_minimum_k": 3,
        "subgroup_test_minimum_k": 10,
        "prediction_interval": "not computed for tentative_k2",
    }


def _default_run_dir(rows, stratum) -> Path:
    digest = hashlib.sha256(repr((stratum, rows)).encode("utf-8")).hexdigest()[:12]
    return Path("/private/tmp") / f"a-meta-{stratum}-{digest}"


def _write_tsv(path: Path, rows: Sequence[Mapping], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _index_rows(rows: Sequence[Mapping], key: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        value = str(row.get(key, ""))
        if not value or value in result:
            raise ValueError("R synthesis output has a missing or duplicate analysis key")
        result[value] = dict(row)
    return result


def _float(value):
    if value is None or (isinstance(value, str) and value.strip().casefold() in {"", "na", "nan"}):
        return None
    try:
        parsed = float(value)
    except (ValueError, TypeError):
        return None
    return parsed if math.isfinite(parsed) else None


def _integer(value, default=0):
    parsed = _float(value)
    return int(parsed) if parsed is not None else default


def _summary_sort_key(row):
    return (
        row["stratum_type"], row["stratum"], row["unit_family"], row["endpoint_family"],
        row["endpoint_definition_id"], row["unit"], row["stage"], row["study"],
    )
