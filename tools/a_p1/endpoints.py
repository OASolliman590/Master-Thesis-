"""Fixed-score ORR/DCR comparisons for source-supported O/SD/PD categories."""

from __future__ import annotations

import math
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence


_CATEGORIES = ("O", "SD", "PD")
SCORE_MAPPING_VERSION = "CYT_SQRT_TPM_GZMA_TIMES_PRF1_V1"
SCORE_FORMULA = "sqrt(TPM_GZMA * TPM_PRF1)"
ENDPOINT_MAPPING_VERSION = "A_P1_ORR_DCR_CRPR_SD_PD_V1"
REQUIRED_FIELDS = (
    "study_id",
    "cancer",
    "patient_key",
    "specimen_key",
    "index_episode_id",
    "is_index_specimen",
    "expression_episode_id",
    "outcome_episode_id",
    "response_category",
    "source_criteria",
    "evaluation_window",
    "TPM_GZMA",
    "TPM_PRF1",
)


def cyt_score(tpm_gzma: object, tpm_prf1: object) -> float | None:
    """Return the fixed CYT score from unlogged TPM; missing genes stay missing."""
    values = (_parse_tpm(tpm_gzma), _parse_tpm(tpm_prf1))
    if any(value is None for value in values):
        return None
    gzma, prf1 = (float(value) for value in values)
    return math.sqrt(gzma * prf1)


def source_category(response: object) -> str | None:
    """Map only explicit CR, PR, SD or PD source categories to O/SD/PD."""
    token = str(response or "").strip().upper()
    return {"CR": "O", "PR": "O", "SD": "SD", "PD": "PD"}.get(token)


def summarize_records(records: Sequence[Mapping[str, object]]) -> dict:
    """Summarize one fixed CYT score against source-supported categories."""
    return _summarize_records(records)[0]


def _summarize_records(
    records: Sequence[Mapping[str, object]],
) -> tuple[dict, dict[str, list[dict]], dict[str, list[dict]]]:
    if not records:
        raise ValueError("A-P1 requires at least one input row")
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    study_metadata: dict[str, dict[str, str]] = {}
    row_counts: Counter[str] = Counter()
    specimen_bindings: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for raw in records:
        row = {name: raw.get(name) for name in REQUIRED_FIELDS}
        missing = [
            name for name in REQUIRED_FIELDS
            if row[name] is None and name not in {
                "specimen_key", "index_episode_id", "is_index_specimen",
                "expression_episode_id", "outcome_episode_id", "response_category",
                "TPM_GZMA", "TPM_PRF1",
            }
        ]
        if missing:
            raise ValueError("A-P1 input is missing a required selected field")
        study = _required_text(row["study_id"], "study_id")
        cancer = _required_text(row["cancer"], "cancer")
        patient = _required_text(row["patient_key"], "patient_key")
        metadata = {
            "cancer": cancer,
            "source_criteria": _required_text(row["source_criteria"], "source_criteria"),
            "evaluation_window": _required_text(row["evaluation_window"], "evaluation_window"),
        }
        previous = study_metadata.setdefault(study, metadata)
        if previous != metadata:
            raise ValueError("Study cancer, source criteria and window must be consistent")
        specimen = _text(row["specimen_key"])
        if specimen:
            binding = (
                patient,
                _text(row["index_episode_id"]),
                _text(row["expression_episode_id"]),
                _text(row["outcome_episode_id"]),
            )
            previous_binding = specimen_bindings.setdefault((study, specimen), binding)
            if previous_binding != binding:
                raise ValueError(
                    "A study-wide specimen-to-patient/episode binding is ambiguous"
                )
        grouped.setdefault((study, patient), []).append(row)
        row_counts[study] += 1

    accepted_by_study: dict[str, list[dict]] = {study: [] for study in study_metadata}
    endpoint_eligible_by_study: dict[str, list[dict]] = {
        study: [] for study in study_metadata
    }
    exclusions_by_study: dict[str, Counter[str]] = {
        study: Counter() for study in study_metadata
    }
    non_index_by_study: Counter[str] = Counter()
    for (study, _patient), patient_rows in sorted(
        grouped.items(), key=lambda item: (_utf8(item[0][0]), _utf8(item[0][1]))
    ):
        specimen_keys = [_text(row["specimen_key"]) for row in patient_rows]
        if any(not specimen_key for specimen_key in specimen_keys):
            exclusions_by_study[study]["SPECIMEN_KEY_MISSING"] += 1
            continue
        if len(specimen_keys) != len(set(specimen_keys)):
            exclusions_by_study[study]["DUPLICATE_SPECIMEN_ROW"] += 1
            continue
        flags = [_index_flag(row["is_index_specimen"]) for row in patient_rows]
        selected = [row for row, flag in zip(patient_rows, flags) if flag is True]
        non_index_by_study[study] += len(patient_rows) - len(selected)
        if any(flag is None for flag in flags) or len(selected) != 1:
            exclusions_by_study[study]["INDEX_SPECIMEN_NOT_UNIQUE"] += 1
            continue
        row = selected[0]
        episode_values = {_text(value) for value in (item["index_episode_id"] for item in patient_rows)}
        if len(episode_values) != 1:
            exclusions_by_study[study]["INDEX_EPISODE_DECLARATION_MISMATCH"] += 1
            continue
        index_episode = _text(row["index_episode_id"])
        if (
            not index_episode
            or _text(row["expression_episode_id"]) != index_episode
            or _text(row["outcome_episode_id"]) != index_episode
        ):
            exclusions_by_study[study]["INDEX_EPISODE_MISMATCH"] += 1
            continue
        category = source_category(row["response_category"])
        if category is None:
            exclusions_by_study[study]["UNKNOWN_OR_NE_CATEGORY"] += 1
            continue
        endpoint_patient = {
            "patient_key": _text(row["patient_key"]),
            "index_episode_id": index_episode,
            "category": category,
        }
        endpoint_eligible_by_study[study].append(endpoint_patient)
        score = cyt_score(row["TPM_GZMA"], row["TPM_PRF1"])
        if score is None:
            exclusions_by_study[study]["MISSING_CYT_GENE"] += 1
            continue
        accepted_by_study[study].append({**endpoint_patient, "score": score})

    study_results: dict[str, dict] = {}
    all_scores = []
    total_exclusions: Counter[str] = Counter()
    for study in sorted(study_metadata, key=_utf8):
        patients = sorted(accepted_by_study[study], key=lambda row: _utf8(row["patient_key"]))
        if patients:
            metrics = category_metrics(
                [row["score"] for row in patients],
                [row["category"] for row in patients],
            )
        else:
            metrics = _empty_metrics()
        excluded = dict(sorted(exclusions_by_study[study].items()))
        total_exclusions.update(exclusions_by_study[study])
        metadata = study_metadata[study]
        score_hash = _score_hash(study, patients)
        all_scores.extend((study, row) for row in patients)
        study_results[study] = {
            "study_id": study,
            **metadata,
            "patient_n": len({key[1] for key in grouped if key[0] == study}),
            "specimen_row_n": row_counts[study],
            "non_index_specimen_rows": non_index_by_study[study],
            "eligible_n": len(patients),
            "category_episode_eligible_n": len(endpoint_eligible_by_study[study]),
            **metrics,
            "exclusions": excluded,
            "score_hash_sha256": score_hash,
            "score_formula": SCORE_FORMULA,
            "score_mapping_version": SCORE_MAPPING_VERSION,
            "endpoint_mapping_version": ENDPOINT_MAPPING_VERSION,
        }
    summary = {
        "analysis_id": "A_P1_CYT_FIXED_SCORE_ENDPOINT_SENSITIVITY_V1",
        "score_mapping_version": SCORE_MAPPING_VERSION,
        "score_formula": SCORE_FORMULA,
        "endpoint_mapping_version": ENDPOINT_MAPPING_VERSION,
        "patient_n": sum(len({key[1] for key in grouped if key[0] == study}) for study in study_metadata),
        "eligible_n": sum(len(rows) for rows in accepted_by_study.values()),
        "category_episode_eligible_n": sum(
            len(rows) for rows in endpoint_eligible_by_study.values()
        ),
        "exclusions": dict(sorted(total_exclusions.items())),
        "score_hash_sha256": _score_hash_all(all_scores),
        "studies": study_results,
        "synthesis": {
            "status": "blocked_missing_signed_synthesis_setting",
            "release_requirement": (
                "A signed prospective A-P1 collection roster and explicit cancer/study weights "
                "are required for real synthesis."
            ),
        },
        "learned_score_secondary": {
            "status": "unavailable_not_supplied",
            "reason": "A frozen equation and disjoint prediction provenance were not supplied.",
        },
    }
    return summary, accepted_by_study, endpoint_eligible_by_study


def category_metrics(scores: Sequence[float], categories: Sequence[str]) -> dict:
    """Compute both endpoint AUCs and their category-composition decomposition."""
    if len(scores) != len(categories) or not scores:
        raise ValueError("Scores and O/SD/PD categories must be non-empty and aligned")
    parsed_scores = [float(score) for score in scores]
    parsed_categories = [str(category) for category in categories]
    if any(not math.isfinite(score) for score in parsed_scores):
        raise ValueError("AUC scores must be finite")
    if any(category not in _CATEGORIES for category in parsed_categories):
        raise ValueError("Only source-supported O, SD and PD categories are estimable")

    counts = Counter(parsed_categories)
    groups = {
        category: [score for score, label in zip(parsed_scores, parsed_categories)
                   if label == category]
        for category in _CATEGORIES
    }
    pairwise = {
        "O_SD": _pairwise_auc(groups["O"], groups["SD"]),
        "O_PD": _pairwise_auc(groups["O"], groups["PD"]),
        "SD_PD": _pairwise_auc(groups["SD"], groups["PD"]),
    }
    auc_orr = _auc(
        groups["O"], groups["SD"] + groups["PD"]
    )
    auc_dcr = _auc(
        groups["O"] + groups["SD"], groups["PD"]
    )

    auc_orr_decomposed = _weighted_decomposition(
        ((counts["SD"], pairwise["O_SD"]),
         (counts["PD"], pairwise["O_PD"])),
        counts["SD"] + counts["PD"],
    )
    auc_dcr_decomposed = _weighted_decomposition(
        ((counts["O"], pairwise["O_PD"]),
         (counts["SD"], pairwise["SD_PD"])),
        counts["O"] + counts["SD"],
    )
    decomposition_verified = _same_optional(auc_orr, auc_orr_decomposed) and _same_optional(
        auc_dcr, auc_dcr_decomposed
    )
    if auc_orr is not None and auc_orr_decomposed is not None:
        _assert_identity(auc_orr, auc_orr_decomposed)
    if auc_dcr is not None and auc_dcr_decomposed is not None:
        _assert_identity(auc_dcr, auc_dcr_decomposed)

    if counts["O"] and counts["SD"] and counts["PD"]:
        status = "informative"
        informative = True
        nonestimability_reason = None
    elif counts["O"] and counts["PD"] and counts["SD"] == 0:
        status = "structurally_zero_no_sd"
        informative = False
        nonestimability_reason = "no_sd_structural_zero_excluded_from_informative_set"
    elif not counts["O"] or not counts["PD"]:
        status = "nonestimable_missing_o_or_pd"
        informative = False
        missing = [category for category in ("O", "PD") if counts[category] == 0]
        nonestimability_reason = "missing_" + "_and_".join(category.lower() for category in missing)
    else:
        status = "nonestimable_incomplete_categories"
        informative = False
        nonestimability_reason = "incomplete_source_supported_category_counts"

    delta = None if auc_orr is None or auc_dcr is None else auc_dcr - auc_orr
    category_total = sum(counts.values())
    fractions = {
        category: (counts[category] / category_total if category_total else None)
        for category in _CATEGORIES
    }
    return {
        "n": category_total,
        "category_counts": {category: counts[category] for category in _CATEGORIES},
        "category_fractions": fractions,
        "auc_orr": auc_orr,
        "auc_dcr": auc_dcr,
        "delta": delta,
        "pairwise_auc": pairwise,
        "auc_orr_decomposed": auc_orr_decomposed,
        "auc_dcr_decomposed": auc_dcr_decomposed,
        "decomposition_verified": decomposition_verified,
        "status": status,
        "informative": informative,
        "nonestimability_reason": nonestimability_reason,
    }


def _pairwise_auc(positive: Sequence[float], negative: Sequence[float]) -> float | None:
    if not positive or not negative:
        return None
    wins = sum(
        1.0 if case > control else 0.5 if case == control else 0.0
        for case in positive
        for control in negative
    )
    return wins / (len(positive) * len(negative))


def _parse_tpm(value: object) -> float | None:
    if value is None or (
        isinstance(value, str) and value.strip().casefold() in {"", "na", "nan", "null"}
    ):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("CYT requires numeric unlogged TPM values") from error
    if math.isnan(parsed):
        return None
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError("CYT TPM values must be finite and nonnegative")
    return parsed


def _auc(positive: Sequence[float], negative: Sequence[float]) -> float | None:
    return _pairwise_auc(positive, negative)


def _weighted_decomposition(
    weighted_values: Sequence[tuple[int, float | None]], denominator: int
) -> float | None:
    if denominator == 0:
        return None
    if any(weight and value is None for weight, value in weighted_values):
        return None
    return sum(weight * float(value) for weight, value in weighted_values if weight) / denominator


def _empty_metrics() -> dict:
    return {
        "n": 0,
        "category_counts": {category: 0 for category in _CATEGORIES},
        "category_fractions": {category: None for category in _CATEGORIES},
        "auc_orr": None,
        "auc_dcr": None,
        "delta": None,
        "pairwise_auc": {"O_SD": None, "O_PD": None, "SD_PD": None},
        "auc_orr_decomposed": None,
        "auc_dcr_decomposed": None,
        "decomposition_verified": None,
        "status": "nonestimable_no_eligible_patients",
        "informative": False,
        "nonestimability_reason": "no_eligible_scored_source_supported_categories",
    }


def _index_flag(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    token = str(value).strip().casefold()
    if token in {"true", "1"}:
        return True
    if token in {"false", "0"}:
        return False
    return None


def _required_text(value: object, field: str) -> str:
    result = _text(value)
    if not result:
        raise ValueError(f"A-P1 input has an empty required {field}")
    return result


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _utf8(value: object) -> bytes:
    return _text(value).encode("utf-8")


def _score_hash(study: str, patients: Sequence[Mapping[str, object]]) -> str:
    payload = {
        "score_mapping_version": SCORE_MAPPING_VERSION,
        "study": study,
        "scores": [
            [row["patient_key"], row["index_episode_id"], format(float(row["score"]), ".17g")]
            for row in patients
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _score_hash_all(rows: Sequence[tuple[str, Mapping[str, object]]]) -> str:
    payload = {
        "score_mapping_version": SCORE_MAPPING_VERSION,
        "scores": [
            [study, row["patient_key"], row["index_episode_id"], format(float(row["score"]), ".17g")]
            for study, row in sorted(
                rows,
                key=lambda item: (_utf8(item[0]), _utf8(item[1]["patient_key"])),
            )
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _same_optional(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def _assert_identity(left: float, right: float) -> None:
    if not math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12):
        raise ArithmeticError("Category-composition AUC identity failed")
