"""Explicit cancer/study weighted means of within-study A-P1 estimands."""

from __future__ import annotations

import math
from collections.abc import Mapping

from tools.a_meta.provenance import is_locked_study

from .provenance import is_known_real_identity


def synthesize_studies(
    studies: Mapping[str, Mapping[str, object]],
    contract: Mapping[str, object] | None,
    *,
    data_classification: str,
) -> dict:
    """Weight within-study AUCs using a declared A-P1 roster and weights."""
    if contract is None:
        return _missing_setting()
    if data_classification not in {"synthetic", "real"}:
        raise ValueError("Synthesis requires an explicit data classification")
    decision_status = str(contract.get("decision_status", "")).upper()
    if data_classification == "real" and decision_status != "SIGNED":
        return _missing_setting("The real synthesis contract is not signed.")
    if data_classification == "synthetic" and decision_status != "INVENTED_FIXTURE":
        raise ValueError("Synthetic synthesis weights must be labelled as an invented fixture")
    if data_classification == "real":
        if not contract.get("prospectively_declared"):
            return _missing_setting("The real collection was not declared prospectively.")
        if not str(contract.get("decision_id", "")).strip():
            return _missing_setting("The signed synthesis decision ID is missing.")

    collection_id = str(contract.get("collection_id", "")).strip()
    roster = contract.get("studies")
    if not collection_id or not isinstance(roster, list) or not roster:
        raise ValueError("Synthesis requires a collection ID and explicit study roster")

    entries: dict[str, dict] = {}
    cancer_weights: dict[str, float] = {}
    within_cancer_weights: dict[str, list[float]] = {}
    for raw in roster:
        if not isinstance(raw, Mapping):
            raise ValueError("Synthesis study entries must be objects")
        study = str(raw.get("study_id", "")).strip()
        cancer = str(raw.get("cancer", "")).strip()
        if not study or not cancer or study in entries:
            raise ValueError("Synthesis roster requires unique study and cancer IDs")
        if data_classification == "synthetic" and (
            is_locked_study(study) or is_known_real_identity(study)
        ):
            raise ValueError("Synthetic synthesis cannot name a protected or known real cohort")
        cancer_weight = _weight(raw.get("cancer_weight"), "cancer_weight")
        study_weight = _weight(raw.get("study_weight"), "study_weight")
        prior = cancer_weights.setdefault(cancer, cancer_weight)
        if not math.isclose(prior, cancer_weight, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("A cancer must have one explicit cancer weight")
        within_cancer_weights.setdefault(cancer, []).append(study_weight)
        entries[study] = {
            "cancer": cancer,
            "cancer_weight": cancer_weight,
            "study_weight": study_weight,
            "effective_weight": cancer_weight * study_weight,
        }
    if set(entries) != set(studies):
        raise ValueError("Declared A-P1 synthesis roster does not match the input studies")
    if not math.isclose(sum(cancer_weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Explicit cancer weights must sum to one")
    if any(not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-12)
           for weights in within_cancer_weights.values()):
        raise ValueError("Explicit within-cancer study weights must sum to one")
    for study, entry in entries.items():
        result_cancer = studies[study].get("cancer")
        if result_cancer is not None and str(result_cancer) != entry["cancer"]:
            raise ValueError("Declared synthesis cancer does not match the study result")

    noninformative = sorted(
        study for study, result in studies.items() if result.get("informative") is not True
    )
    positively_weighted_noninformative = [
        study for study in noninformative if entries[study]["effective_weight"] > 0.0
    ]
    if positively_weighted_noninformative:
        return {
            "status": "not_estimable_noninformative_studies_in_declared_roster",
            "collection_id": collection_id,
            "analysis_identity": "A_P1_EXPLICIT_CANCER_STUDY_WEIGHTED_WITHIN_STUDY_MEANS_V1",
            "noninformative_studies": positively_weighted_noninformative,
            "unassigned_weight": sum(
                entries[study]["effective_weight"] for study in positively_weighted_noninformative
            ),
            "cross_study_pooled_auc": None,
            "interval": None,
            "interval_status": "not_available_for_noninformative_roster",
        }

    effective_weights = {
        study: entries[study]["effective_weight"]
        for study in sorted(entries)
        if studies[study].get("informative") is True
    }
    if not math.isclose(sum(effective_weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Explicit effective cancer/study weights must sum to one")
    auc_orr = sum(effective_weights[study] * float(studies[study]["auc_orr"])
                  for study in effective_weights)
    auc_dcr = sum(effective_weights[study] * float(studies[study]["auc_dcr"])
                  for study in effective_weights)
    delta = sum(effective_weights[study] * float(studies[study]["delta"])
                for study in effective_weights)
    decomposition_verified = math.isclose(
        auc_dcr - auc_orr, delta, rel_tol=0.0, abs_tol=1e-12
    )
    if not decomposition_verified:
        raise ArithmeticError("Weighted within-study endpoint identity failed")
    return {
        "status": "estimated_synthetic_fixture" if data_classification == "synthetic" else "estimated",
        "collection_id": collection_id,
        "analysis_identity": "A_P1_EXPLICIT_CANCER_STUDY_WEIGHTED_WITHIN_STUDY_MEANS_V1",
        "n_studies": len(effective_weights),
        "n_cancers": len({entries[study]["cancer"] for study in effective_weights}),
        "weighting": effective_weights,
        "excluded_noninformative_studies": noninformative,
        "weighted_mean_within_study_auc_orr": auc_orr,
        "weighted_mean_within_study_auc_dcr": auc_dcr,
        "weighted_mean_within_study_delta": delta,
        "decomposition_verified": decomposition_verified,
        "cross_study_pooled_auc": None,
        "interval": None,
        "interval_status": "awaiting_joint_patient_bootstrap",
        "synthetic_scope": (
            "invented weighting fixture; not a biological estimate"
            if data_classification == "synthetic" else None
        ),
        "real_release_requirement": (
            "A signed prospective A-P1 collection roster and explicit cancer/study weights "
            "are still required before real synthesis."
            if data_classification == "synthetic" else None
        ),
    }


def _weight(value: object, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Synthesis requires an explicit numeric {field}") from error
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"Synthesis {field} must be finite and nonnegative")
    return parsed


def _missing_setting(reason: str | None = None) -> dict:
    return {
        "status": "blocked_missing_signed_synthesis_setting",
        "release_requirement": (
            "A signed prospective A-P1 collection roster and explicit cancer/study weights "
            "are required for real synthesis."
        ),
        "reason": reason,
        "cross_study_pooled_auc": None,
        "interval": None,
    }
