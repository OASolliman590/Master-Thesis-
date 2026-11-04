"""Within-study Hedges-g effects for A-META feature tables."""
from __future__ import annotations

import math
import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from statistics import mean, stdev
from types import SimpleNamespace

from tools.a_cohorts.view import normalise_drug_class
from tools.a_scoring import endpoint_label
from .endpoint_definitions import endpoint_definition_id
from .provenance import validate_effect_input_provenance


EFFECT_COLUMNS = (
    "unit_family",
    "unit",
    "study",
    "cancer",
    "cancer_components",
    "drug_class_stratum",
    "endpoint_family",
    "endpoint_definition_id",
    "patient_set_id",
    "n_R",
    "n_NR",
    "mean_R",
    "mean_NR",
    "sd_R",
    "sd_NR",
    "g",
    "se",
    "status",
    "reason",
)
_UNIT_FAMILIES = {"gene", "panel", "pathway", "fraction"}


def study_effects(
    view,
    features,
    family: str | Sequence[str],
    *,
    by_drug_class: bool = True,
    allow_outcomes: bool = False,
    provenance_manifest=None,
) -> list[dict]:
    """Estimate Hedges g (responders minus non-responders) within a cohort.

    `features` may be a FeatureTable or long rows with `patient_row`, `unit`,
    and `value` columns. `patient_row` is the zero-based row in the validated
    CohortView; no patient or sample identifiers are needed.
    """
    validate_effect_input_provenance(
        view,
        features,
        allow_outcomes=allow_outcomes,
        provenance_manifest=provenance_manifest,
    )
    cohort_id = str(getattr(view.metadata, "cohort_id", ""))
    feature_cohort = getattr(features, "cohort_id", None)
    if feature_cohort and feature_cohort != cohort_id:
        raise ValueError("Feature table cohort does not match the cohort view")
    unit_family = _unit_family(features)
    clinical_rows = list(view.clinical_rows)
    feature_values = _feature_vectors(features, len(clinical_rows))

    families = _endpoint_families(view, family)
    results = []
    for endpoint_family in families:
        patients = [_patient_context(view, row, index) for index, row in enumerate(clinical_rows)]
        definition_ids = [
            endpoint_definition_id(
                cohort_id,
                endpoint_family,
                row.get("endpoint_definition", ""),
            )
            for row in clinical_rows
        ]
        for definition_id in sorted(set(definition_ids)):
            definition_indices = [
                index for index, value in enumerate(definition_ids) if value == definition_id
            ]
            definition_rows = [clinical_rows[index] for index in definition_indices]
            local_view = SimpleNamespace(metadata=view.metadata, clinical_rows=definition_rows)
            local_labels, _ = endpoint_label(local_view, endpoint_family)
            labels = [None] * len(clinical_rows)
            for index, label in zip(definition_indices, local_labels):
                labels[index] = label
            if len(local_labels) != len(definition_indices):
                raise ValueError("Endpoint labels do not align with cohort rows")

            cancer_groups = sorted({patients[index]["cancer"] for index in definition_indices})
            if getattr(view.metadata, "cancer", None) == "multi":
                cancer_groups.append("multi")
            for cancer in cancer_groups:
                cancer_indices = (
                    definition_indices if cancer == "multi"
                    else [i for i in definition_indices if patients[i]["cancer"] == cancer]
                )
                drug_classes = sorted({patients[i]["drug_class"] for i in cancer_indices
                                       if patients[i]["drug_class"] != "OTHER_EXCLUDED"})
                strata = [("ALL", cancer_indices)]
                if by_drug_class:
                    strata.extend(
                        (drug_class, [i for i in cancer_indices if patients[i]["drug_class"] == drug_class])
                        for drug_class in drug_classes
                    )

                for stratum, patient_indices in strata:
                    included_indices = [i for i in patient_indices
                                        if patients[i]["drug_class"] != "OTHER_EXCLUDED"]
                    subset_view = SimpleNamespace(
                        metadata=view.metadata,
                        clinical_rows=[clinical_rows[i] for i in included_indices],
                    )
                    _, stratum_excluded = endpoint_label(subset_view, endpoint_family)
                    for unit, values in feature_values.items():
                        results.append(_effect_row(
                            view=view,
                            unit_family=unit_family,
                            unit=unit,
                            cancer=cancer,
                            stratum=stratum,
                            endpoint_family=endpoint_family,
                            endpoint_definition_id=definition_id,
                            labels=labels,
                            values=values,
                            patient_indices=included_indices,
                            excluded=stratum_excluded,
                            coverage=_coverage_for(features, unit),
                            clinical_rows=clinical_rows,
                            cancer_components=sorted({patients[i]["cancer"] for i in included_indices}),
                        ))
    return results


def _endpoint_families(view, family: str | Sequence[str]) -> tuple[str, ...]:
    if isinstance(family, str):
        if family.casefold() == "all":
            families = tuple(view.metadata.endpoint_families)
        else:
            families = (family,)
    else:
        families = tuple(family)
    if not families or len(set(families)) != len(families):
        raise ValueError("At least one unique endpoint family is required")
    allowed = {"orr", "clinical_benefit", "source_label"}
    if any(item not in allowed for item in families):
        raise ValueError("Unknown endpoint family")
    declared = set(view.metadata.endpoint_families)
    if not set(families).issubset(declared):
        raise ValueError("Endpoint family is not declared by this cohort")
    return families


def _unit_family(features) -> str:
    value = getattr(features, "unit_family", None)
    if value is None and isinstance(features, Mapping):
        value = features.get("unit_family")
    if value is None and hasattr(features, "values_by_unit"):
        value = "gene"
    if value is None:
        rows = _records(features)
        families = {row.get("unit_family") for row in rows if row.get("unit_family")}
        value = next(iter(families)) if len(families) == 1 else "gene"
    if value not in _UNIT_FAMILIES:
        raise ValueError("Feature table has an unsupported unit family")
    return str(value)


def _feature_vectors(features, n_patients: int) -> dict[str, Sequence[float | None]]:
    if hasattr(features, "values_by_unit"):
        values = features.values_by_unit
        if any(len(vector) != n_patients for vector in values.values()):
            raise ValueError("Feature vectors do not align with cohort-view rows")
        return {str(unit): vector for unit, vector in values.items()}
    feature_values: dict[str, dict[int, float | None]] = defaultdict(dict)
    for row in _records(features):
        patient_row = _patient_row(row)
        unit = str(row.get("unit", "")).strip()
        if not unit:
            raise ValueError("Feature table contains an empty unit")
        if patient_row in feature_values[unit]:
            raise ValueError("Feature table contains a duplicate patient-row/unit pair")
        if patient_row >= n_patients:
            raise ValueError("Feature table row index is outside the cohort")
        feature_values[unit][patient_row] = _value(row.get("value"))
    return {
        unit: [feature_values[unit].get(index) for index in range(n_patients)]
        for unit in feature_values
    }


def _records(features) -> list[Mapping]:
    if hasattr(features, "records"):
        rows = list(features.records)
    elif isinstance(features, Mapping):
        rows = list(features.get("records", ()))
    else:
        rows = list(features)
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("Feature table rows must be mappings")
    return rows


def _patient_row(row: Mapping) -> int:
    try:
        index = int(row["patient_row"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Feature table requires an integer patient_row") from None
    if index < 0 or str(row["patient_row"]).strip() != str(index):
        raise ValueError("Feature table patient_row must be a non-negative integer")
    return index


def _value(value) -> float | None:
    if value is None or (isinstance(value, str) and value.strip().casefold() in {"", "na", "nan"}):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError("Feature values must be numeric or missing") from None
    if not math.isfinite(parsed):
        raise ValueError("Feature values must be finite or missing")
    return parsed


def _patient_context(view, row: Mapping, index: int) -> dict[str, str]:
    metadata = view.metadata
    cancer = row.get("cancer_normalised") if getattr(metadata, "cancer", None) == "multi" else metadata.cancer
    if not cancer:
        raise ValueError("Multi-cancer cohort row has no normalised cancer")
    raw_drug = row.get("drug_class_normalised")
    if raw_drug is None:
        raw_drug = normalise_drug_class(row.get("drug_class", ""))
    drug_class = str(raw_drug)
    if drug_class not in {"ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4", "OTHER_EXCLUDED"}:
        raise ValueError("Cohort row has an uncontrolled normalised drug class")
    return {"cancer": str(cancer), "drug_class": drug_class, "patient_row": str(index)}


def _coverage_for(features, unit: str) -> Mapping | None:
    coverage = getattr(features, "coverage", None)
    if coverage is None and isinstance(features, Mapping):
        coverage = features.get("coverage")
    if isinstance(coverage, Mapping):
        return coverage.get(unit)
    if isinstance(coverage, Sequence):
        return next((row for row in coverage if row.get("unit") == unit), None)
    return None


def _effect_row(*, view, unit_family, unit, cancer, stratum, endpoint_family,
                endpoint_definition_id, labels, values, patient_indices, excluded,
                coverage, clinical_rows, cancer_components) -> dict:
    response_values: list[float] = []
    nonresponse_values: list[float] = []
    missing_values = 0
    for index in patient_indices:
        label = labels[index]
        if label not in (0, 1):
            continue
        value = values[index] if index < len(values) else None
        if value is None:
            missing_values += 1
            continue
        (response_values if label == 1 else nonresponse_values).append(value)

    n_r, n_nr = len(response_values), len(nonresponse_values)
    mean_r = mean(response_values) if response_values else None
    mean_nr = mean(nonresponse_values) if nonresponse_values else None
    sd_r = stdev(response_values) if n_r >= 2 else None
    sd_nr = stdev(nonresponse_values) if n_nr >= 2 else None
    reasons = [f"{name}={count}" for name, count in sorted(excluded.items()) if count]
    if missing_values:
        reasons.append(f"feature_missing={missing_values}")

    coverage_complete = coverage is None or coverage.get("complete", True)
    if not coverage_complete:
        reasons.append("incomplete_feature_coverage")
    if n_r < 2:
        reasons.append("n_R<2")
    if n_nr < 2:
        reasons.append("n_NR<2")

    g = se = None
    patient_tokens = []
    status = "NA"
    if coverage_complete and n_r >= 2 and n_nr >= 2:
        pooled_variance = (
            (n_r - 1) * sd_r ** 2 + (n_nr - 1) * sd_nr ** 2
        ) / (n_r + n_nr - 2)
        if pooled_variance == 0:
            reasons.append("pooled_sd_zero")
        else:
            pooled_sd = math.sqrt(pooled_variance)
            d = (mean_r - mean_nr) / pooled_sd
            degrees_of_freedom = n_r + n_nr - 2
            correction = math.exp(
                math.lgamma(degrees_of_freedom / 2.0)
                - 0.5 * math.log(degrees_of_freedom / 2.0)
                - math.lgamma((degrees_of_freedom - 1.0) / 2.0)
            )
            g = correction * d
            variance = (n_r + n_nr) / (n_r * n_nr) + g ** 2 / (2.0 * (n_r + n_nr))
            se = math.sqrt(variance)
            status = "ok"

    for index in patient_indices:
        if labels[index] not in (0, 1) or values[index] is None:
            continue
        row = clinical_rows[index]
        patient_tokens.append("\x1f".join((
            str(row.get("patient_id", "")),
            str(row.get("sample_id", "")),
            str(index),
        )))
    patient_set_id = hashlib.sha256(
        "\x1e".join(sorted(patient_tokens)).encode("utf-8")
    ).hexdigest()

    return {
        "unit_family": unit_family,
        "unit": unit,
        "study": view.metadata.cohort_id,
        "cancer": cancer,
        "cancer_components": ",".join(cancer_components),
        "drug_class_stratum": stratum,
        "endpoint_family": endpoint_family,
        "endpoint_definition_id": endpoint_definition_id,
        "patient_set_id": patient_set_id,
        "n_R": n_r,
        "n_NR": n_nr,
        "mean_R": mean_r,
        "mean_NR": mean_nr,
        "sd_R": sd_r,
        "sd_NR": sd_nr,
        "g": g,
        "se": se,
        "status": status,
        "reason": ";".join(reasons),
    }
