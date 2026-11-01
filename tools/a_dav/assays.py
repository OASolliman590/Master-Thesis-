"""Validate only invented matrix structure, measurement declarations and coverage."""
from __future__ import annotations

import copy
import math
from typing import Any

from .core import SchemaStore, dependency, finish, require, stage_boundary

REASON_CODES = frozenset({"ASSAY_SCALE_UNKNOWN", "ASSAY_SCALE_CONFLICT", "MATRIX_STRUCTURE_CONFLICT", "DUPLICATE_HEADER", "DUPLICATE_FEATURE", "FEATURE_COLLISION", "FEATURE_UNIVERSE_UNKNOWN", "ASSAY_SOURCE_CONFLICT", "ASSAY_QC_FAILED", "ASSAY_QC_UNKNOWN", "ASSAY_MISSING_VALUES", "ASSAY_REPLICATE_UNKNOWN", "FEATURE_COVERAGE_INCOMPLETE", "ASSAY_POLICY_UNKNOWN", "ASSAY_PLATFORM_CONFLICT"})
_LANES = {"COUNTS": {"counts", "estimated_counts"}, "CONTINUOUS": {"TPM", "FPKM", "log_expression"}, "ARRAY": {"array_intensity", "log_array_intensity"}, "METHYLATION_BETA": {"beta"}, "METHYLATION_M": {"M"}}


@stage_boundary("assays")
def validate_assays(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    assert schemas is not None
    dependency(packet, "registries", schemas)
    records = copy.deepcopy(packet["records"])
    cfg = packet["config"].get("assays", {})
    matrices = cfg.get("matrices", [])
    require(bool(matrices), "ASSAY_POLICY_UNKNOWN", blocked=True)
    assays = records.get("assay_registry", [])
    for assay in assays:
        require(assay["qc_status"] != "FAIL", "ASSAY_QC_FAILED")
    sources = {s["source_object_id"]: s for s in records.get("source_record", [])}
    specimens = {s["specimen_uid"]: s for s in records.get("specimen_registry", [])}
    patients = {p["patient_uid"]: p for p in records.get("patient_registry", [])}
    matrix_by_object: dict[str, dict[str, Any]] = {}
    for matrix in matrices:
        object_id = matrix["source_object_id"]
        require(object_id not in matrix_by_object, "MATRIX_STRUCTURE_CONFLICT")
        matrix_by_object[object_id] = matrix
        require(object_id in sources and matrix.get("source_sha256") == sources[object_id].get("sha256") and sources[object_id].get("hash_scope") == "FULL_OBJECT", "ASSAY_SOURCE_CONFLICT")
        headers = matrix.get("headers", [])
        features = matrix.get("features", [])
        values = matrix.get("values", [])
        require(isinstance(headers, list) and bool(headers) and all(isinstance(h, str) and bool(h) for h in headers), "MATRIX_STRUCTURE_CONFLICT")
        require(len(headers) == len(set(headers)), "DUPLICATE_HEADER")
        require(isinstance(features, list) and bool(features) and all(isinstance(f, str) and bool(f) for f in features), "MATRIX_STRUCTURE_CONFLICT")
        require(len(features) == len(set(features)), "DUPLICATE_FEATURE")
        require(isinstance(values, list) and len(values) == len(features) and all(isinstance(row, list) and len(row) == len(headers) for row in values), "MATRIX_STRUCTURE_CONFLICT")
        require(all(v is None or type(v) in {int, float} and math.isfinite(v) for row in values for v in row), "MATRIX_STRUCTURE_CONFLICT")
        unit = matrix.get("unit")
        lane = matrix.get("lane")
        require(lane in _LANES and unit in set().union(*_LANES.values()), "ASSAY_SCALE_UNKNOWN", blocked=True)
        require(unit in _LANES[lane], "ASSAY_SCALE_CONFLICT")
        transform = matrix.get("transform")
        require(transform in {"NONE", "LOG2", "LN", "LOG10"}, "ASSAY_SCALE_UNKNOWN", blocked=True)
        if lane == "COUNTS":
            require(transform == "NONE" and matrix.get("normalization") == "NONE", "ASSAY_SCALE_CONFLICT")
        if unit in {"log_expression", "log_array_intensity"}:
            require(transform != "NONE", "ASSAY_SCALE_CONFLICT")
        if lane == "METHYLATION_BETA":
            require(transform == "NONE", "ASSAY_SCALE_CONFLICT")
        present_values = [v for row in values for v in row if v is not None]
        if transform == "NONE" and lane != "METHYLATION_M":
            require(all(v >= 0 for v in present_values), "ASSAY_SCALE_CONFLICT")
        if unit == "estimated_counts":
            require(bool(matrix.get("quantifier")) and bool(matrix.get("estimated_count_structure")), "ASSAY_POLICY_UNKNOWN", blocked=True)
        if unit == "counts":
            require(all(float(v).is_integer() for v in present_values), "ASSAY_SCALE_CONFLICT")
        if lane == "METHYLATION_BETA":
            require(all(0 <= v <= 1 for v in present_values), "ASSAY_SCALE_CONFLICT")
        for field, source_field in (("unit", "measurement_unit"), ("transform", "transform"), ("normalization", "normalisation")):
            if sources[object_id].get(source_field) is not None:
                require(matrix.get(field) == sources[object_id][source_field], "ASSAY_SCALE_CONFLICT")
        selected = [a for a in assays if a["source_object_id"] == object_id]
        require({a["matrix_header"] for a in selected} == set(headers) and len(selected) == len(headers), "ASSAY_SOURCE_CONFLICT")
        require(bool(matrix.get("modality")) and bool(matrix.get("platform")), "ASSAY_POLICY_UNKNOWN", blocked=True)
        require(matrix.get("delimiter") in {"TAB", "COMMA"} and matrix.get("encoding") == "UTF-8" and matrix.get("source_locator"), "ASSAY_POLICY_UNKNOWN", blocked=True)
        require(matrix.get("missingness_policy") == "PRESERVE", "ASSAY_POLICY_UNKNOWN", blocked=True)
        require(matrix.get("replicate_policy") == "PRESERVE", "ASSAY_REPLICATE_UNKNOWN", blocked=True)
        from .assay_policy import validate_feature_scope, AssayPolicyEvidenceError
        try:
            validate_feature_scope(matrix, provisional=False)
        except AssayPolicyEvidenceError:
            require(False, "FEATURE_UNIVERSE_UNKNOWN", blocked=True)
        universe = matrix.get("feature_universe")
        require(isinstance(universe, list) and bool(universe), "FEATURE_UNIVERSE_UNKNOWN", blocked=True)
        require(len(universe) == len(set(universe)) and set(features) == set(universe), "FEATURE_UNIVERSE_UNKNOWN")
        fmap = matrix.get("feature_map", {})
        require(set(fmap) == set(features) and all(isinstance(v, str) and v for v in fmap.values()), "FEATURE_UNIVERSE_UNKNOWN", blocked=True)
        require(len(set(fmap.values())) == len(fmap), "FEATURE_COLLISION")
        require(bool(matrix.get("annotation")) and bool(matrix.get("normalization")), "ASSAY_POLICY_UNKNOWN", blocked=True)
        if lane == "COUNTS":
            library_properties = matrix.get("library_properties", {})
            require(set(library_properties) == set(headers), "ASSAY_POLICY_UNKNOWN", blocked=True)
            for header in headers:
                library = library_properties[header]
                require(type(library.get("library_size")) in {int, float} and library["library_size"] > 0 and bool(library.get("source_locator")), "ASSAY_POLICY_UNKNOWN", blocked=True)
        if lane == "ARRAY":
            require(all(matrix.get(k) for k in ("platform", "annotation", "preprocessing", "probe_to_gene_policy", "batch_structure")), "ASSAY_POLICY_UNKNOWN", blocked=True)
        if lane.startswith("METHYLATION"):
            require(all(matrix.get(k) for k in ("platform", "genome_build", "detection_p_provenance", "probe_filter_policy", "snp_policy", "cross_reactive_policy", "sex_chromosome_policy")), "ASSAY_POLICY_UNKNOWN", blocked=True)
        for assay in selected:
            require(assay["measurement_unit"] == unit and assay.get("transform") == transform, "ASSAY_SCALE_CONFLICT")
            require(assay.get("feature_annotation") == matrix["annotation"], "ASSAY_PLATFORM_CONFLICT")
            require(matrix["platform"] == assay["platform"] and matrix["modality"] == assay["modality"], "ASSAY_PLATFORM_CONFLICT")
            require(assay["modality"] in ({"METHYLATION", "DNA_METHYLATION"} if lane.startswith("METHYLATION") else {"RNA", "RNA_SEQ", "BULK_RNA", "TRANSCRIPTOMICS", "MICROARRAY", "TARGETED_RNA"}), "ASSAY_PLATFORM_CONFLICT")
            for key in ("platform", "modality"):
                if sources[object_id].get(key) is not None:
                    require(sources[object_id][key] == matrix[key], "ASSAY_PLATFORM_CONFLICT")
            require(assay["source_sample_id"] in specimens[assay["specimen_uid"]]["raw_sample_aliases"], "ASSAY_SOURCE_CONFLICT")
            require(assay["qc_status"] != "FAIL", "ASSAY_QC_FAILED")
    require(set(matrix_by_object) == {a["source_object_id"] for a in assays}, "ASSAY_SOURCE_CONFLICT")
    required = cfg.get("required_features")
    require(isinstance(required, list) and bool(required) and len(required) == len(set(required)), "ASSAY_POLICY_UNKNOWN", blocked=True)
    coverage: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    reasons: set[str] = set()
    profiles: dict[tuple[Any, ...], list[str]] = {}
    for assay in assays:
        matrix = matrix_by_object[assay["source_object_id"]]
        column = matrix["headers"].index(assay["matrix_header"])
        profile = tuple(row[column] for row in matrix["values"])
        profile_key = (assay["measurement_unit"], matrix["annotation"], tuple(matrix["features"]), profile)
        profiles.setdefault(profile_key, []).append(assay["assay_uid"])
        available = {matrix["feature_map"][feature] for feature, value in zip(matrix["features"], profile) if value is not None}
        missing = set(required) - available
        nulls = sum(v is None for v in profile)
        zeros = sum(v == 0 for v in profile if v is not None)
        if nulls:
            reasons.add("ASSAY_MISSING_VALUES")
        if missing:
            reasons.add("FEATURE_COVERAGE_INCOMPLETE")
        if assay["qc_status"] != "PASS":
            reasons.add("ASSAY_QC_UNKNOWN")
        if assay.get("replicate_status", "UNKNOWN") == "UNKNOWN":
            reasons.add("ASSAY_REPLICATE_UNKNOWN")
        specimen = specimens[assay["specimen_uid"]]
        row = {"row_type": "COVERAGE", "schema_version": "1.1.0", "study_id": patients[specimen["patient_uid"]]["study_id"], "assay_uid": assay["assay_uid"], "branch_id": packet["branch_id"], "required_genes": sorted(required), "present_genes": sorted(set(required) & available), "missing_genes": sorted(missing), "ambiguous_genes": [], "annotation_version": matrix["annotation"], "expression_unit": assay["measurement_unit"], "measurement_suitability": "PASS" if not nulls and assay["qc_status"] == "PASS" else "UNKNOWN", "scoring_suitability": "PASS" if not missing and not nulls and assay["qc_status"] == "PASS" else "FAIL", "de_suitability": "PASS" if matrix["feature_scope"] in {"COMPLETE", "COMPLETE_WITH_DOCUMENTED_EXCLUSIONS"} and matrix["lane"] in {"COUNTS", "CONTINUOUS", "ARRAY"} and not nulls and assay["qc_status"] == "PASS" else "FAIL", "final_test_suitability": "UNKNOWN", "source_object_id": assay["source_object_id"]}
        schemas.validate("coverage", row)
        coverage.append(row)
        audit.append({"check": "MATRIX_COLUMN_VALIDATED", "assay_uid": assay["assay_uid"], "source_object_id": assay["source_object_id"], "feature_count": len(profile), "missing_value_count": nulls, "zero_value_count": zeros, "feature_scope": matrix["feature_scope"], "replicate_status": assay.get("replicate_status", "UNKNOWN")})
    for ids in profiles.values():
        if len(ids) > 1:
            audit.append({"check": "IDENTICAL_PROFILE_RETAINED", "assay_uids": sorted(ids)})
    records["coverage"] = coverage
    return finish("assays", packet, records, status="BLOCKED_UNKNOWN" if reasons else "READY", reasons=reasons, audit=audit, schemas=schemas)
