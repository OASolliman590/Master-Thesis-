"""Strict A-LONG feature scoring on explicitly declared expression scales."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from tools.a_scoring.core import DEFAULT_PANELS, cyt, log2p1, panel_scores, panel_definitions
from tools.a_meta.provenance import canonical_sha256
from tools.a1.authorization import is_released_inputs


@dataclass(frozen=True)
class LongFeatureMemberships:
    ap2_panels: dict[str, tuple[str, ...]]
    custom_panels: dict[str, tuple[str, ...]]
    m5m6_genes: tuple[str, ...]
    aliases: dict[str, str]
    membership_sha256: str


@dataclass(frozen=True)
class FeatureScores:
    sample_keys: tuple[str, ...]
    values_by_unit: dict[str, tuple[float | None, ...]]
    coverage_by_unit: dict[str, dict]
    method_id_by_unit: dict[str, str]
    effect_scale_by_unit: dict[str, str]
    metadata: dict = field(default_factory=dict)


def build_pair_analysis_rows(
    released_inputs,
    *,
    policy: Mapping,
    allow_outcomes: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Join selected outcome-free pairs, fixed features, and released endpoint rows."""
    if allow_outcomes is not True:
        raise PermissionError("A-LONG pair-to-analysis requires allow_outcomes=True")
    if not is_released_inputs(
        released_inputs,
        release_scope="N13_FEATURE_JOIN",
        operation="pair_to_analysis",
    ):
        raise PermissionError("Pair-to-analysis requires validated N13_FEATURE_JOIN inputs")
    if canonical_sha256(dict(policy)) != released_inputs.authorization.record.get("policy_sha256"):
        raise PermissionError("Pair-to-analysis policy differs from the approved user-release hash")
    fixed = validate_feature_join_policy(policy)
    tables = released_inputs.tables
    if set(tables) != {"pairs", "expression", "endpoint"}:
        raise ValueError("Pair-to-analysis requires exactly pairs, expression, and endpoint sources")
    bindings = released_inputs.manifest["scope_bindings"]
    if bindings["feature_membership_sha256"] != fixed.membership_sha256:
        raise PermissionError("Released feature membership does not match the fixed A-LONG contract")
    if bindings["pair_manifest_sha256"] != released_inputs.authorization.source_sha256["pairs"]:
        raise PermissionError("Pair source hash does not match the N13 pair-manifest binding")
    if bindings["representation_sha256"] != canonical_sha256(policy["representation"]):
        raise PermissionError("Released representation does not match the N13 feature-join binding")
    return _build_pair_analysis_rows_after_policy_check(released_inputs, policy, fixed)


def validate_feature_join_policy(policy: Mapping) -> LongFeatureMemberships:
    """Preflight fixed membership, unit identities, and explicit scale declarations."""
    required_policy = {
        "analysis_method_id", "assay_id", "covariates", "endpoint_id",
        "regimen_id", "representation", "source_scale", "tpm_qualified",
        "tpm_route", "unit_identities", "window_id",
    }
    if not isinstance(policy, Mapping) or set(policy) != required_policy:
        raise ValueError("Pair-to-analysis policy must declare every feature and identity field exactly")
    fixed = fixed_long_feature_memberships()
    representation = policy["representation"]
    platform, unit, transform = _representation(representation)
    representation_id = f"{platform}:{unit}:{transform}"
    if policy["source_scale"] != representation_id:
        raise ValueError("Pair-to-analysis source scale does not match its representation")
    if not isinstance(policy["covariates"], list) or len(set(policy["covariates"])) != len(policy["covariates"]):
        raise ValueError("Pair-to-analysis covariates must be explicit and unique")
    if any(not isinstance(policy[name], str) or not policy[name].strip() for name in (
        "analysis_method_id", "assay_id", "endpoint_id", "regimen_id", "window_id",
    )):
        raise ValueError("Pair-to-analysis identities must be explicit and non-empty")
    if not isinstance(policy["tpm_qualified"], bool):
        raise ValueError("TPM route qualification must be an explicit boolean")
    if policy["tpm_qualified"] and (platform, unit, transform) != ("rnaseq", "tpm", "linear"):
        raise ValueError("TPM qualification cannot relabel a different representation")
    if policy["tpm_qualified"] and not isinstance(policy["tpm_route"], str):
        raise ValueError("Qualified TPM requires an explicit route identity")

    expected_units = {
        *(f"AP2:{panel}" for panel in fixed.ap2_panels), "CYT",
        *(f"CUSTOM:{panel}" for panel in fixed.custom_panels),
        *(f"M5M6:{gene}" for gene in fixed.m5m6_genes),
    }
    identities = policy["unit_identities"]
    if not isinstance(identities, Mapping) or set(identities) != expected_units:
        raise ValueError("Pair-to-analysis identity policy must cover every fixed A-LONG unit exactly")
    expected_identity = {}
    expected_identity.update({
        f"AP2:{panel}": {
            "unit_family": "panel", "panel_family": "A_P2", "multiplicity_family_id": "A_P2_PANELS",
        }
        for panel in fixed.ap2_panels
    })
    expected_identity["CYT"] = {
        "unit_family": "comparator", "panel_family": "CYT", "multiplicity_family_id": "CYT_SINGLETON",
    }
    expected_identity.update({
        f"CUSTOM:{panel}": {
            "unit_family": "custom_panel", "panel_family": "A_LONG_CUSTOM",
            "multiplicity_family_id": "A_LONG_CUSTOM_PANELS",
        }
        for panel in fixed.custom_panels
    })
    expected_identity.update({
        f"M5M6:{gene}": {
            "unit_family": "m5m6_gene", "panel_family": "M5M6", "multiplicity_family_id": "M5M6_GENES",
        }
        for gene in fixed.m5m6_genes
    })
    if {unit: dict(identity) for unit, identity in identities.items()} != expected_identity:
        raise ValueError("Production A-LONG unit identities must match their fixed feature namespaces")
    return fixed


def _build_pair_analysis_rows_after_policy_check(released_inputs, policy, fixed):
    """Implementation helper kept below the pre-read policy boundary."""
    tables = released_inputs.tables
    representation = policy["representation"]

    pairs = tables["pairs"]
    expression = tables["expression"]
    endpoints = tables["endpoint"]
    pair_columns = {
        "study_id", "patient_id", "pair_id", "selected", "pre_specimen_id", "on_specimen_id",
        "pre_assay_id", "on_assay_id", "endpoint_id", "regimen_id", "window_id",
        "same_lesion", "pre_day_precision", "on_day_precision", "pre_day_numeric", "on_day_numeric",
        "day_distance_to_target", "pair_day_distance", "timing_ambiguity",
        "source_family_id", "overlap_receipt_id", "overlap_status", "admission_receipt",
        "pre_source_locator", "on_source_locator", "pre_source_confidence", "on_source_confidence",
        "pre_annotation_id", "on_annotation_id", "pre_measurement_comparability_id",
        "on_measurement_comparability_id", "pre_day_origin", "on_day_origin",
    }
    if not pairs or any(not pair_columns <= row.keys() for row in pairs):
        raise ValueError("Pair source lacks selected-pair, admission, or overlap receipt fields")
    if not expression or any(not {"study_id", "sample_id", "assay_id", "gene_id", "value"} <= row.keys() for row in expression):
        raise ValueError("Expression source must name study, selected specimen, assay, gene, and value fields")
    if any(not {
        "study_id", "patient_id", "endpoint_id", "response", *policy["covariates"]
    } <= row.keys() for row in endpoints):
        raise ValueError("Endpoint source lacks the released class or prespecified covariate fields")
    if any(str(row["endpoint_id"]) != policy["endpoint_id"] for row in endpoints):
        raise ValueError("Endpoint source identity differs from the explicitly released endpoint")
    selected_pairs = [pair for pair in pairs if str(pair["selected"]).casefold() in {"true", "1", "yes"}]
    if not selected_pairs:
        raise ValueError("Pair-to-analysis has no selected pairs in the released window")
    if any(str(pair["window_id"]) != policy["window_id"] for pair in selected_pairs):
        raise ValueError("Pair-to-analysis input mixes windows outside the exact released window")
    if any(str(pair["endpoint_id"]) != policy["endpoint_id"] for pair in selected_pairs):
        raise ValueError("Pair-to-analysis endpoint binding does not match the released policy")
    if any(str(pair["regimen_id"]) != policy["regimen_id"] for pair in selected_pairs):
        raise ValueError("Pair-to-analysis regimen identity does not match the released policy")
    if any(not str(pair[name]).strip() for pair in selected_pairs for name in (
        "pre_assay_id", "on_assay_id", "admission_receipt", "pre_source_locator", "on_source_locator",
        "pre_source_confidence", "on_source_confidence", "pre_annotation_id", "on_annotation_id",
        "pre_measurement_comparability_id", "on_measurement_comparability_id",
    )):
        raise ValueError("Pair-to-analysis requires selected assay and source/admission provenance")

    endpoint_by_patient = {}
    for row in endpoints:
        key = (str(row["study_id"]), str(row["patient_id"]))
        if key in endpoint_by_patient:
            raise ValueError("Endpoint source contains multiple rows for one released patient")
        response = str(row.get("response") or "").strip()
        if response not in {"", "R", "NR"}:
            raise ValueError("Released response field must be R, NR, or missing")
        endpoint_by_patient[key] = row

    sample_keys = sorted({
        _expression_sample_key(str(pair["study_id"]), str(pair[specimen]), str(pair[assay]))
        for pair in selected_pairs
        for specimen, assay in (("pre_specimen_id", "pre_assay_id"), ("on_specimen_id", "on_assay_id"))
    })
    symbols = sorted({str(row["gene_id"]) for row in expression})
    values = {}
    for row in expression:
        if str(row["study_id"]) not in released_inputs.manifest["cohort_ids"]:
            raise ValueError("Expression source has a study outside the released cohort set")
        key = (str(row["study_id"]), str(row["sample_id"]), str(row["assay_id"]), str(row["gene_id"]))
        if key in values:
            raise ValueError("Expression source repeats a study/specimen/assay/gene measurement")
        values[key] = row["value"] if row["value"] != "" else None
    matrix = [
        [
            values.get((*json.loads(sample), gene))
            for sample in sample_keys
        ]
        for gene in symbols
    ]
    scores = score_long_features(
        symbols,
        sample_keys,
        matrix,
        representation=representation,
        source_scale=policy["source_scale"],
        tpm_route=policy["tpm_route"],
        tpm_qualified=bool(policy["tpm_qualified"]),
    )
    unit_identities = policy["unit_identities"]
    expected_units = set(scores.values_by_unit)
    if not isinstance(unit_identities, Mapping) or set(unit_identities) != expected_units:
        raise ValueError("Pair-to-analysis identity policy must cover every fixed A-LONG unit exactly")
    for unit, identity in unit_identities.items():
        if not isinstance(identity, Mapping) or set(identity) != {
            "unit_family", "panel_family", "multiplicity_family_id",
        } or any(not str(value).strip() for value in identity.values()):
            raise ValueError(f"Pair-to-analysis family identity is incomplete for {unit}")

    index = {sample: position for position, sample in enumerate(sample_keys)}
    output = []
    for pair in selected_pairs:
        study_id = str(pair["study_id"])
        patient_id = str(pair["patient_id"])
        endpoint = endpoint_by_patient.get((study_id, patient_id), {})
        for unit in sorted(expected_units):
            identity = unit_identities[unit]
            row = {
                "study_id": study_id,
                "patient_key": patient_id,
                "pair_id": str(pair["pair_id"]),
                "unit": unit,
                "pre_value": scores.values_by_unit[unit][index[_expression_sample_key(
                    study_id, str(pair["pre_specimen_id"]), str(pair["pre_assay_id"])
                )]],
                "on_value": scores.values_by_unit[unit][index[_expression_sample_key(
                    study_id, str(pair["on_specimen_id"]), str(pair["on_assay_id"])
                )]],
                "response": str(endpoint.get("response") or ""),
                "unit_family": str(identity["unit_family"]),
                "feature_method_id": scores.method_id_by_unit[unit],
                "analysis_method_id": str(policy["analysis_method_id"]),
                "endpoint_id": str(pair["endpoint_id"]),
                "regimen_id": str(pair["regimen_id"]),
                "window_id": str(pair["window_id"]),
                "assay_id": str(policy["assay_id"]),
                "effect_scale_id": scores.effect_scale_by_unit[unit],
                "panel_family": str(identity["panel_family"]),
                "multiplicity_family_id": str(identity["multiplicity_family_id"]),
                "source_family_id": str(pair["source_family_id"]),
                "overlap_receipt_id": str(pair["overlap_receipt_id"]),
                "overlap_status": str(pair["overlap_status"]),
                "same_lesion": str(pair["same_lesion"]),
                "pre_day_precision": str(pair["pre_day_precision"]),
                "on_day_precision": str(pair["on_day_precision"]),
                "pre_day_numeric": str(pair["pre_day_numeric"]),
                "on_day_numeric": str(pair["on_day_numeric"]),
                "day_distance_to_target": str(pair["day_distance_to_target"]),
                "pair_day_distance": str(pair["pair_day_distance"]),
                "timing_ambiguity": str(pair["timing_ambiguity"]),
            }
            for covariate in policy["covariates"]:
                row[covariate] = endpoint.get(covariate, "")
            output.append(row)
    output.sort(key=lambda row: (row["unit"], row["study_id"], row["patient_key"], row["pair_id"]))
    coverage = []
    for unit in sorted(expected_units):
        item = scores.coverage_by_unit[unit]
        coverage.append({
            "unit": unit,
            "feature_method_id": scores.method_id_by_unit[unit],
            "effect_scale_id": scores.effect_scale_by_unit[unit],
            "complete_samples": item["complete_samples"],
            "sample_count": item["sample_count"],
            "complete": item["complete"],
            "missing_members": ",".join(item["missing"]),
        })
    return output, coverage


def _expression_sample_key(study_id: str, specimen_id: str, assay_id: str) -> str:
    return json.dumps((study_id, specimen_id, assay_id), separators=(",", ":"), ensure_ascii=True)


def fixed_long_feature_memberships() -> LongFeatureMemberships:
    """Load the frozen A-P2/A-BIO membership contract through its public APIs."""
    from tools.a_meta import features as meta_features
    from tools.a_meta.frozen import read_frozen_aliases

    aliases = read_frozen_aliases()
    ap2 = panel_definitions(DEFAULT_PANELS)
    custom = meta_features._panel_definitions(meta_features.AVAILABLE_PANEL_IDS)
    m5m6_raw = meta_features._m5m6_gene_units()
    canonical = lambda gene: aliases.get(gene, gene)
    ap2 = {name: tuple(canonical(gene) for gene in members) for name, members in ap2.items()}
    custom = {name: tuple(canonical(gene) for gene in members) for name, members in custom.items()}
    m5m6 = tuple(sorted({canonical(gene) for gene in m5m6_raw}))
    if len(ap2) != 4 or len(custom) != 11 or len(m5m6) != 21:
        raise ValueError("Fixed A-LONG membership contract must contain 4, 11, and 21 units")
    if any(len(members) != len(set(members)) for members in (*ap2.values(), *custom.values())):
        raise ValueError("Frozen aliases collapse a fixed panel membership")
    membership = {
        "ap2_panels": {key: list(ap2[key]) for key in sorted(ap2)},
        "custom_panels": {key: list(custom[key]) for key in sorted(custom)},
        "m5m6_genes": list(m5m6),
        "aliases": dict(sorted(aliases.items())),
    }
    digest = hashlib.sha256(
        json.dumps(membership, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return LongFeatureMemberships(ap2, custom, m5m6, aliases, digest)


def score_long_features(
    feature_ids: Sequence[str],
    sample_keys: Sequence[str],
    matrix: Sequence[Sequence[float | None]],
    *,
    representation: Mapping[str, str],
    source_scale: str,
    ap2_panels: Mapping[str, Sequence[str]] | None = None,
    custom_panels: Mapping[str, Sequence[str]] | None = None,
    m5m6_genes: Sequence[str] | None = None,
    aliases: Mapping[str, str] | None = None,
    tpm_route: str | None = None,
    tpm_qualified: bool = False,
    fixture_only: bool = False,
) -> FeatureScores:
    """Score fixed feature units, keeping panel namespaces and scales distinct.

    Production calls resolve membership and aliases through the frozen source
    APIs. Injected memberships are accepted only by the fixture-only helper path.
    """
    if not isinstance(representation, Mapping):
        raise ValueError("An explicit measurement representation is required")
    platform, unit, transform = _representation(representation)
    representation_id = f"{platform}:{unit}:{transform}"
    if source_scale != representation_id:
        raise ValueError("Declared source scale does not match the expression representation")
    if platform == "rnaseq" and unit == "counts" and transform == "linear":
        raise ValueError("Raw count scoring requires the unavailable voom/dream precision route")
    is_qualified_tpm = platform == "rnaseq" and unit == "tpm" and transform == "linear"
    if is_qualified_tpm and (not tpm_qualified or not tpm_route):
        raise ValueError("The linear RNA-seq TPM route requires explicit qualification and route identity")

    if fixture_only:
        if ap2_panels is None or custom_panels is None or m5m6_genes is None:
            raise ValueError("Fixture-only membership injection requires all fixed-unit definitions")
        fixed = LongFeatureMemberships(
            {name: tuple(members) for name, members in ap2_panels.items()},
            {name: tuple(members) for name, members in custom_panels.items()},
            tuple(m5m6_genes),
            dict(aliases or {}),
            "fixture_only",
        )
    else:
        fixed = fixed_long_feature_memberships()
        if any(value is not None for value in (ap2_panels, custom_panels, m5m6_genes, aliases)):
            supplied = (
                {key: tuple(value) for key, value in (ap2_panels or {}).items()},
                {key: tuple(value) for key, value in (custom_panels or {}).items()},
                tuple(m5m6_genes or ()),
                dict(aliases or {}),
            )
            expected = (
                fixed.ap2_panels, fixed.custom_panels, fixed.m5m6_genes, fixed.aliases,
            )
            if supplied != expected:
                raise ValueError("Production scoring cannot override frozen A-LONG memberships or aliases")
    if set(fixed.ap2_panels) != set(DEFAULT_PANELS) or len(fixed.ap2_panels) != 4:
        raise ValueError("A-LONG requires the four fixed A-P2 panels")
    if len(fixed.custom_panels) != 11:
        raise ValueError("A-LONG requires eleven strict-coverage custom panels")
    if len(fixed.m5m6_genes) != 21 or len(set(fixed.m5m6_genes)) != 21:
        raise ValueError("A-LONG requires the 21 fixed, alias-resolved M5/M6 genes")

    symbols_in = tuple(str(value).strip() for value in feature_ids)
    samples = tuple(str(value).strip() for value in sample_keys)
    if not symbols_in or not samples or any(not value for value in (*symbols_in, *samples)):
        raise ValueError("Feature and sample identifiers must be non-empty")
    symbols = tuple(fixed.aliases.get(value, value) for value in symbols_in)
    if len(set(symbols)) != len(symbols) or len(set(samples)) != len(samples):
        raise ValueError("Resolved feature and sample identifiers must be unique")
    if len(matrix) != len(symbols) or any(len(row) != len(samples) for row in matrix):
        raise ValueError("Expression matrix must align to feature and sample identifiers")
    values: list[list[float | None]] = []
    for row in matrix:
        normalized = []
        for item in row:
            if item is None or item == "":
                normalized.append(None)
                continue
            number = float(item)
            if not math.isfinite(number):
                raise ValueError("Expression values must be finite or missing")
            if is_qualified_tpm and number < 0:
                raise ValueError("TPM values must be non-negative")
            normalized.append(number)
        values.append(normalized)

    raw_by_sample = [
        {symbol: values[row][sample] for row, symbol in enumerate(symbols)}
        for sample in range(len(samples))
    ]
    output: dict[str, tuple[float | None, ...]] = {}
    coverage: dict[str, dict] = {}
    method_ids: dict[str, str] = {}
    scales: dict[str, str] = {}

    # Namespaces make overlaps between A-P2 and the eleven A-LONG custom
    # panels non-destructive and keep method/effect identities distinct.
    if is_qualified_tpm:
        per_sample_panel_values = []
        per_sample_cyt_values = []
        for sample_values in raw_by_sample:
            present = {gene: value for gene, value in sample_values.items() if value is not None}
            if present:
                logged_values = log2p1(
                    [[value] for value in present.values()],
                    {"platform": platform, "unit": unit, "transform": transform},
                )
                logged = dict(zip(present, (row[0] for row in logged_values)))
            else:
                logged = {}
            scores, _ = panel_scores(logged, fixed.ap2_panels, require_complete=True)
            per_sample_panel_values.append(scores)
            if "GZMA" in present and "PRF1" in present:
                per_sample_cyt_values.append(cyt(present["GZMA"], present["PRF1"]))
            else:
                per_sample_cyt_values.append(None)
        for panel, members in fixed.ap2_panels.items():
            key = f"AP2:{panel}"
            output[key] = tuple(row[panel] for row in per_sample_panel_values)
            coverage[key] = _coverage(members, raw_by_sample)
            method_ids[key] = "A_LONG_AP2_LOG2_TPM_PLUS1_FIXED_PANEL_MEAN"
            scales[key] = "LOG2_TPMPLUS1_PANEL_MEAN"
        output["CYT"] = tuple(per_sample_cyt_values)
        coverage["CYT"] = _coverage(("GZMA", "PRF1"), raw_by_sample)
        method_ids["CYT"] = "A_LONG_AP2_CYT_GZMA_PRF1_GEOMETRIC_MEAN"
        scales["CYT"] = "TPM_GEOMETRIC_MEAN_GZMA_PRF1"
    else:
        for panel, members in fixed.ap2_panels.items():
            key = f"AP2:{panel}"
            output[key] = tuple(None for _ in samples)
            coverage[key] = _coverage(members, raw_by_sample)
            coverage[key]["reason"] = "qualified_linear_rnaseq_tpm_route_required"
            method_ids[key] = "A_LONG_AP2_LOG2_TPM_PLUS1_FIXED_PANEL_MEAN"
            scales[key] = "LOG2_TPMPLUS1_PANEL_MEAN"
        output["CYT"] = tuple(None for _ in samples)
        coverage["CYT"] = _coverage(("GZMA", "PRF1"), raw_by_sample)
        coverage["CYT"]["reason"] = "qualified_linear_rnaseq_tpm_route_required"
        method_ids["CYT"] = "A_LONG_AP2_CYT_GZMA_PRF1_GEOMETRIC_MEAN"
        scales["CYT"] = "TPM_GEOMETRIC_MEAN_GZMA_PRF1"

    for name, members in fixed.custom_panels.items():
        key = f"CUSTOM:{name}"
        unit_values = []
        per_sample_missing = []
        for sample_values in raw_by_sample:
            present = {gene: value for gene, value in sample_values.items() if value is not None}
            scores, details = panel_scores(present, {name: members}, require_complete=True)
            unit_values.append(scores[name])
            per_sample_missing.append(tuple(details[name]["missing"]))
        output[key] = tuple(unit_values)
        coverage[key] = _coverage(members, raw_by_sample)
        coverage[key]["per_sample_missing"] = tuple(per_sample_missing)
        method_ids[key] = "A_LONG_STRICT_CUSTOM_PANEL_MEAN_SOURCE_SCALE"
        scales[key] = f"SOURCE_SCALE_PANEL_MEAN:{representation_id}"

    for gene in fixed.m5m6_genes:
        key = f"M5M6:{gene}"
        output[key] = tuple(row.get(gene) for row in raw_by_sample)
        missing_count = sum(row.get(gene) is None for row in raw_by_sample)
        coverage[key] = {
            "members": (gene,),
            "missing": (gene,) if missing_count else (),
            "complete": not missing_count,
            "complete_samples": len(samples) - missing_count,
            "sample_count": len(samples),
            "per_sample_missing": tuple(() if row.get(gene) is not None else (gene,) for row in raw_by_sample),
        }
        method_ids[key] = "A_LONG_M5M6_INDIVIDUAL_GENE_SOURCE_SCALE"
        scales[key] = f"SOURCE_SCALE_INDIVIDUAL_GENE:{representation_id}"

    return FeatureScores(
        sample_keys=samples,
        values_by_unit=output,
        coverage_by_unit=coverage,
        method_id_by_unit=method_ids,
        effect_scale_by_unit=scales,
        metadata={
            "representation": {"platform": platform, "unit": unit, "transform": transform},
            "source_scale_id": representation_id,
            "tpm_route": tpm_route if is_qualified_tpm else None,
            "membership_sha256": fixed.membership_sha256,
            "data_classification": "invented_fixture" if fixture_only else "source_contract",
        },
    )


def _representation(value: Mapping[str, str]) -> tuple[str, str, str]:
    required = {"platform", "unit", "transform"}
    if set(value) != required:
        raise ValueError("Representation must contain exactly platform, unit, and transform")
    platform, unit, transform = (str(value[key]).strip().casefold() for key in ("platform", "unit", "transform"))
    if not platform or not unit or not transform:
        raise ValueError("Representation fields must be non-empty")
    if transform not in {"linear", "log2", "log2_normalised", "log2_cpm", "identity"}:
        raise ValueError("Unsupported declared transform; no conversion rule is registered")
    return platform, unit, transform


def _coverage(members, sample_values):
    missing_by_sample = [
        tuple(gene for gene in members if gene not in row or row[gene] is None)
        for row in sample_values
    ]
    return {
        "members": tuple(members),
        "missing": tuple(sorted({gene for missing in missing_by_sample for gene in missing})),
        "complete": all(not missing for missing in missing_by_sample),
        "complete_samples": sum(not missing for missing in missing_by_sample),
        "sample_count": len(sample_values),
        "per_sample_missing": tuple(missing_by_sample),
    }
