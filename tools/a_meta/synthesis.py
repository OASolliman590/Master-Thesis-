"""Stratified random-effects synthesis for A-META effect tables."""
from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from tools.r_bridge import run_r


SYNTHESIS_COLUMNS = (
    "unit_family", "unit", "endpoint_family", "stratum_type", "stratum",
    "cancer", "drug_class_stratum", "stage", "k", "estimate", "se",
    "ci_lb", "ci_ub", "tau2", "I2", "Q", "p", "fixed_estimate",
    "fixed_ci_lb", "fixed_ci_ub", "q", "label", "low_k", "status",
    "reason", "weighting",
)
SUBGROUP_COLUMNS = (
    "unit_family", "unit", "endpoint_family", "moderator", "total_k",
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
) -> SynthesisResult:
    """Pool per-study effects for one declared A-META synthesis stratum.

    `stratum` is `per_cancer`, `per_drug_class`, `across_cancers`, or
    `melanoma_cancer_drug`. All grouping retains unit family and endpoint family.
    """
    if stratum not in _STRATA:
        raise ValueError("Unknown synthesis stratum")
    rows = _read_effects(effects)
    if any(_is_locked_study(row.get("study", "")) for row in rows):
        raise ValueError("IMvigor210 is locked and cannot enter A-META synthesis")
    groups, effect_rows = _plan_groups(rows, stratum)
    subgroup_groups, subgroup_rows = _plan_subgroups(rows, stratum)
    if not groups:
        return SynthesisResult(
            summaries=[],
            subgroup_tests=[],
            metadata=_metadata(stratum),
        )

    run_dir = Path(output_dir) if output_dir is not None else _default_run_dir(rows, stratum)
    run_dir.mkdir(parents=True, exist_ok=True)
    group_path = run_dir / "groups.tsv"
    effect_path = run_dir / "meta_input.tsv"
    subgroup_path = run_dir / "subgroup_input.tsv"
    _write_tsv(group_path, groups, tuple(groups[0]))
    _write_tsv(effect_path, effect_rows, ("analysis_id", "study", "yi", "vi"))
    _write_tsv(subgroup_path, subgroup_rows, ("test_id", "study", "stratum", "yi", "vi"))

    script = Path(__file__).resolve().parents[2] / "r/scripts/meta_rma.R"
    r_result = run_r(
        script,
        {"groups": group_path, "effects": effect_path, "subgroups": subgroup_path},
        {"expected_outputs": ["meta.tsv", "subgroups.tsv"]},
        run_dir / "R",
        runner=runner,
    )
    fitted = _index_rows(_read_tsv(r_result.outputs["meta.tsv"]), "analysis_id")
    subgroup_fits = _index_rows(_read_tsv(r_result.outputs["subgroups.tsv"]), "test_id")
    summaries = [_summary(group, fitted.get(group["analysis_id"])) for group in groups]
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
        (row["unit_family"], row["unit"], row["endpoint_family"])
        for row in rows
    })
    specs: list[dict] = []
    if stratum == "per_cancer":
        for unit_family, unit, endpoint in identities:
            pairs = sorted({(row["cancer"], row["drug_class_stratum"]) for row in rows
                            if row["unit_family"] == unit_family and row["unit"] == unit
                            and row["endpoint_family"] == endpoint and row["drug_class_stratum"] == "ALL"
                            and row["cancer"] != "multi"})
            for cancer, drug_class in pairs:
                _add_direct_spec(specs, rows, unit_family, unit, endpoint,
                                 stratum_type="cancer", stratum_value=cancer,
                                 cancer=cancer, drug_class=drug_class, stage="direct")
    elif stratum == "per_drug_class":
        for unit_family, unit, endpoint in identities:
            classes = sorted({row["drug_class_stratum"] for row in rows
                              if row["unit_family"] == unit_family and row["unit"] == unit
                              and row["endpoint_family"] == endpoint
                              and row["drug_class_stratum"] != "ALL"})
            for drug_class in classes:
                _add_direct_spec(specs, rows, unit_family, unit, endpoint,
                                 stratum_type="drug_class", stratum_value=drug_class,
                                 cancer="ALL", drug_class=drug_class, stage="direct")
    elif stratum == "melanoma_cancer_drug":
        for unit_family, unit, endpoint in identities:
            classes = sorted({row["drug_class_stratum"] for row in rows
                              if row["unit_family"] == unit_family and row["unit"] == unit
                              and row["endpoint_family"] == endpoint
                              and row["cancer"] == "melanoma"
                              and row["drug_class_stratum"] != "ALL"})
            for drug_class in classes:
                _add_direct_spec(specs, rows, unit_family, unit, endpoint,
                                 stratum_type="cancer_drug", stratum_value=f"melanoma|{drug_class}",
                                 cancer="melanoma", drug_class=drug_class, stage="direct")
    else:
        for unit_family, unit, endpoint in identities:
            classes = sorted({row["drug_class_stratum"] for row in rows
                              if row["unit_family"] == unit_family and row["unit"] == unit
                              and row["endpoint_family"] == endpoint})
            for drug_class in classes:
                cancers = sorted({row["cancer"] for row in rows
                                  if row["unit_family"] == unit_family and row["unit"] == unit
                                  and row["endpoint_family"] == endpoint
                                  and row["drug_class_stratum"] == drug_class
                                  and row["cancer"] != "multi"})
                parent_key = ("across_cancers", unit_family, unit, endpoint, drug_class)
                for cancer in cancers:
                    _add_direct_spec(
                        specs, rows, unit_family, unit, endpoint,
                        stratum_type="cancer", stratum_value=cancer,
                        cancer=cancer, drug_class=drug_class, stage="within_cancer",
                        parent_key=parent_key, analysis_type="across_within",
                    )
                specs.append({
                    "analysis_key": parent_key,
                    "analysis_type": "across_cancers",
                    "stage": "across_cancers",
                    "parent_key": "",
                    "unit_family": unit_family,
                    "unit": unit,
                    "endpoint_family": endpoint,
                    "stratum_type": "across_cancers",
                    "stratum": drug_class,
                    "cancer": "ALL",
                    "drug_class_stratum": drug_class,
                    "weighting": "two-stage; REML with vi=1 per cancer and equal cancer weights in stage two",
                    "effects": [],
                })

    specs.sort(key=lambda group: (
        group["analysis_type"], group["unit_family"], group["unit"],
        group["endpoint_family"], group["stratum_type"], group["stratum"],
        group["cancer"], group["drug_class_stratum"],
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
        for effect in group["effects"]:
            study = effect["study"]
            if study in seen_studies:
                raise ValueError("A synthesis stratum contains more than one effect from a study")
            seen_studies.add(study)
            input_rows.append({
                "analysis_id": group["analysis_id"],
                "study": study,
                "yi": effect["g"],
                "vi": float(effect["se"]) ** 2,
            })
    return group_rows, input_rows


def _add_direct_spec(specs, rows, unit_family, unit, endpoint, *,
                     stratum_type, stratum_value, cancer, drug_class, stage,
                     parent_key=None, analysis_type="direct"):
    effects = [
        row for row in rows
        if row["unit_family"] == unit_family and row["unit"] == unit
        and row["endpoint_family"] == endpoint and row["drug_class_stratum"] == drug_class
        and (cancer == "ALL" or row["cancer"] == cancer)
        and _valid_effect(row)
    ]
    if cancer == "ALL":
        multi_studies = {row["study"] for row in effects if row["cancer"] == "multi"}
        effects = [row for row in effects if row["cancer"] == "multi" or row["study"] not in multi_studies]
    key = (analysis_type, unit_family, unit, endpoint, stratum_type, stratum_value,
           cancer, drug_class, stage)
    specs.append({
        "analysis_key": key,
        "analysis_type": analysis_type,
        "stage": stage,
        "parent_key": parent_key or "",
        "unit_family": unit_family,
        "unit": unit,
        "endpoint_family": endpoint,
        "stratum_type": stratum_type,
        "stratum": stratum_value,
        "cancer": cancer,
        "drug_class_stratum": drug_class,
        "weighting": "",
        "effects": effects,
    })


def _plan_subgroups(rows: list[dict], stratum: str) -> tuple[list[dict], list[dict]]:
    if stratum == "per_cancer":
        selected = [row for row in rows if row["drug_class_stratum"] == "ALL" and row["cancer"] != "multi"]
        moderator = "cancer"
    elif stratum == "melanoma_cancer_drug":
        selected = [row for row in rows if row["cancer"] == "melanoma" and row["drug_class_stratum"] != "ALL"]
        moderator = "drug_class"
    else:
        selected = [row for row in rows if row["drug_class_stratum"] != "ALL"]
        moderator = "drug_class"
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in selected:
        grouped[(row["unit_family"], row["unit"], row["endpoint_family"])].append(row)
    tests, input_rows = [], []
    for key in sorted(grouped):
        unit_family, unit, endpoint = key
        usable = [row for row in grouped[key] if _valid_effect(row)]
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
                    "stratum": level,
                    "yi": row["g"],
                    "vi": float(row["se"]) ** 2,
                })
    return tests, input_rows


def _summary(group: Mapping, fit: Mapping | None) -> dict:
    unit_family = group["unit_family"]
    min_k = int(group["min_k"])
    study_effects = []
    # Effect rows are not retained in the group TSV. The R result supplies k
    # and the requested fit status for all groups, including single-study rows.
    if fit is None:
        k = 0
    else:
        k = _integer(fit.get("k"), default=0)
    label = _label(k)
    status = str(fit.get("status", "not_estimable")) if fit else "not_estimable"
    reason = str(fit.get("reason", "no_estimable_studies")) if fit else "no_estimable_studies"
    if unit_family == "gene" and 0 < k < 3 and k > 1:
        label = "tentative_k2" if k == 2 else "standard"
        status = "not_pooled"
        reason = "gene_pooling_requires_k>=3"
    result = {
        "unit_family": unit_family,
        "unit": group["unit"],
        "endpoint_family": group["endpoint_family"],
        "stratum_type": group["stratum_type"],
        "stratum": group["stratum"],
        "cancer": group["cancer"],
        "drug_class_stratum": group["drug_class_stratum"],
        "stage": group["stage"],
        "k": k,
        "estimate": _float(fit.get("estimate")) if fit else None,
        "se": _float(fit.get("se")) if fit else None,
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
    if unit_family == "gene" and 0 < k < 3:
        result["estimate"] = None
        result["se"] = None
        result["ci_lb"] = None
        result["ci_ub"] = None
        result["tau2"] = None
        result["I2"] = None
        result["Q"] = None
        result["p"] = None
        result["fixed_estimate"] = None
        result["fixed_ci_lb"] = None
        result["fixed_ci_ub"] = None
    return result


def _subgroup_result(group: Mapping, fit: Mapping | None) -> dict:
    return {
        "unit_family": group["unit_family"],
        "unit": group["unit"],
        "endpoint_family": group["endpoint_family"],
        "moderator": group["moderator"],
        "total_k": group["total_k"],
        "n_levels": group["n_levels"],
        "F": _float(fit.get("F")) if fit else None,
        "p": _float(fit.get("p")) if fit else None,
        "status": str(fit.get("status")) if fit and fit.get("status") else group["status"],
        "reason": str(fit.get("reason", "")) if fit else group["reason"],
    }


def _apply_fdr(summaries: list[dict]) -> None:
    families: dict[tuple, list[dict]] = defaultdict(list)
    for row in summaries:
        is_pooled = row["status"] == "pooled" and row["p"] is not None
        if row["unit_family"] == "gene" and row["k"] < 3:
            is_pooled = False
        if is_pooled:
            key = (
                row["unit_family"], row["stratum_type"], row["stratum"],
                row["endpoint_family"], row["cancer"], row["drug_class_stratum"],
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
                "endpoint_family", "g", "se", "status"}
    if rows and not required.issubset(rows[0]):
        raise ValueError("Effect table is missing required A-META columns")
    result = []
    for raw in rows:
        row = dict(raw)
        for field in ("g", "se"):
            row[field] = _float(row.get(field))
        for field in ("unit_family", "unit", "study", "cancer", "drug_class_stratum", "endpoint_family", "status"):
            row[field] = str(row.get(field, "")).strip()
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
            "with equal weight per cancer (vi=1) in stage two."
        ),
        "fdr_method": "Benjamini-Hochberg",
        "fdr_threshold": 0.10,
        "fdr_scope": "unit_family x stratum x endpoint_family; pooled units only",
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


def _is_locked_study(value) -> bool:
    token = re.sub(r"[^a-z0-9]", "", str(value).casefold())
    return "imvigor210" in token


def _summary_sort_key(row):
    return (
        row["stratum_type"], row["stratum"], row["unit_family"], row["endpoint_family"], row["unit"], row["stage"]
    )
