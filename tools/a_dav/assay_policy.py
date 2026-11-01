"""Derive assay measurement declarations from pinned V3 and field-map evidence."""
from __future__ import annotations


def provisional_feature_scope(value: str | None, provisional: bool) -> str | None:
    """Preserve the legacy validator's unknown state for a documented filtered universe."""
    if provisional and value == 'GENE_LEVEL_EXCLUDING_SNORNA':
        return 'UNKNOWN'
    return value

import re
import copy
import csv
from collections.abc import Iterator
import gzip
import hashlib
import math
from pathlib import Path
from typing import Any, cast


class AssayPolicyEvidenceError(ValueError):
    """Raised when evidence cannot support a required measurement declaration."""


def validate_feature_scope(representation: dict[str, Any], *, provisional: bool) -> str:
    scope = provisional_feature_scope(representation.get('feature_scope'), provisional)
    if provisional and not scope:
        scope = 'UNKNOWN'
    allowed = {'COMPLETE', 'TARGETED', 'COMPLETE_WITH_DOCUMENTED_EXCLUSIONS'}
    if provisional:
        allowed.add('UNKNOWN')
    if scope not in allowed:
        raise AssayPolicyEvidenceError('ASSAY_POLICY_EVIDENCE_MISSING:feature_scope')
    if scope == 'COMPLETE_WITH_DOCUMENTED_EXCLUSIONS':
        exclusions = representation.get('excluded_feature_classes')
        if (not isinstance(exclusions, list) or not exclusions or
                any(not isinstance(entry, dict) or
                    any(not isinstance(entry.get(k), str) or not entry[k].strip() or entry[k].strip().upper() == 'UNKNOWN'
                        for k in ('class', 'evidence')) for entry in exclusions)):
            raise AssayPolicyEvidenceError('ASSAY_POLICY_EVIDENCE_MISSING:excluded_feature_classes')
    return str(scope)


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_TRANSFORMS = {"NONE", "LOG2", "LN", "LOG10"}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AssayPolicyEvidenceError(code)


def derive_assay_policy_metadata(field_map: dict[str, Any], receipt: dict[str, Any],
                                 assays: list[dict[str, Any]]) -> dict[str, Any]:
    """Join receipt checks to declared representations without inferring values.

    This returns measurement metadata only. A caller must provide a supported
    transform and platform before it can create an assays-stage policy.
    """
    _require(receipt.get("checks_version") == "V3", "V3_RECEIPT_REQUIRED")
    checks = receipt.get("checks")
    hashes = receipt.get("source_sha256")
    v3_config = field_map.get("v3")
    if not isinstance(v3_config, dict):
        raise AssayPolicyEvidenceError("FIELD_MAP_V3_CONFIG_MISSING")
    source_roles = v3_config.get("source_object_roles")
    representations = field_map.get("measurement_representations")
    source_objects = field_map.get("source_objects")
    if not isinstance(checks, dict) or not isinstance(hashes, dict):
        raise AssayPolicyEvidenceError("V3_RECEIPT_INVALID")
    if not all(isinstance(value, dict) for value in (source_roles, representations, source_objects)):
        raise AssayPolicyEvidenceError("FIELD_MAP_REPRESENTATIONS_INVALID")
    source_roles = cast(dict[str, Any], source_roles)
    representations = cast(dict[str, Any], representations)
    source_objects = cast(dict[str, Any], source_objects)
    primary_role = source_roles.get("primary")
    fallback_role = source_roles.get("fallback")
    if not isinstance(primary_role, str) or (fallback_role is not None and
            (not isinstance(fallback_role, str) or primary_role == fallback_role)):
        raise AssayPolicyEvidenceError("FIELD_MAP_REPRESENTATIONS_INVALID")
    role_to_receipt: dict[str, tuple[str, str]] = {primary_role: ("primary", "primary")}
    if isinstance(fallback_role, str):
        role_to_receipt[fallback_role] = ("fallback", "fallback")
    effective_primary = checks.get("effective_primary")
    effective_sensitivity = checks.get("effective_sensitivity")
    if effective_primary is None and checks.get("primary", {}).get("status") == "BLOCKED":
        raise AssayPolicyEvidenceError("V3_EFFECTIVE_PRIMARY_NOT_PASS")
    if not (isinstance(effective_primary, str) and effective_primary in role_to_receipt and
            (effective_sensitivity is None if fallback_role is None else
             isinstance(effective_sensitivity, str) and effective_sensitivity in role_to_receipt
             and effective_primary != effective_sensitivity)):
        raise AssayPolicyEvidenceError("V3_EFFECTIVE_REPRESENTATIONS_INVALID")
    primary_receipt_key = role_to_receipt[effective_primary][0]
    _require(checks[primary_receipt_key].get("status") == "PASS", "V3_EFFECTIVE_PRIMARY_NOT_PASS")

    role = effective_primary
    receipt_key, hash_key = role_to_receipt[role]
    declaration = representations.get(role)
    source = source_objects.get(role)
    if not isinstance(declaration, dict) or not isinstance(source, dict):
        raise AssayPolicyEvidenceError(f"FIELD_MAP_REPRESENTATION_MISSING:{role}")
    expected_hash = source.get("sha256")
    _require(isinstance(expected_hash, str) and _SHA256.fullmatch(expected_hash) is not None and
             hashes.get(hash_key) == expected_hash, f"V3_SOURCE_HASH_MISMATCH:{role}")
    v3_check = checks[receipt_key]
    _require(v3_check.get("representation") == role, f"V3_REPRESENTATION_MISMATCH:{role}")
    identity = v3_check.get("checks", {}).get("feature_identity", {})
    _require(identity.get("status") == "PASS", f"V3_FEATURE_IDENTITY_NOT_PASS:{role}")
    certification = identity.get("certification_level")
    _require(isinstance(certification, str) and bool(certification),
             f"V3_FEATURE_IDENTITY_CERTIFICATION_MISSING:{role}")

    unit = declaration.get("unit")
    if not isinstance(unit, str) or not unit:
        raise AssayPolicyEvidenceError(f"ASSAY_POLICY_EVIDENCE_MISSING:unit:{role}")
    transform = declaration.get("transform")
    if not isinstance(transform, str) or transform not in _TRANSFORMS:
        raise AssayPolicyEvidenceError(f"ASSAY_POLICY_EVIDENCE_MISSING:transform:{role}")
    modality = declaration.get("modality")
    if not isinstance(modality, str) or not modality:
        candidates = {row.get("modality") for row in assays if row.get("source_role") == role
                      and isinstance(row.get("modality"), str) and row.get("modality")}
        _require(len(candidates) == 1, f"ASSAY_POLICY_EVIDENCE_MISSING:modality:{role}")
        modality = cast(str, next(iter(candidates)))
    platform = declaration.get("platform")
    if not isinstance(platform, str) or not platform:
        candidates = {row.get("platform") for row in assays if row.get("source_role") == role
                      and isinstance(row.get("platform"), str) and row.get("platform")}
        _require(len(candidates) == 1, f"ASSAY_POLICY_EVIDENCE_MISSING:platform:{role}")
        platform = cast(str, next(iter(candidates)))
    derived = {role: {
        "source_sha256": expected_hash,
        "unit": unit,
        "transform": transform,
        "genome_build": declaration.get("genome_build"),
        "annotation": declaration.get("annotation"),
        "feature_identity_certification": certification,
        "modality": modality,
        "platform": platform,
    }}
    return {"effective_primary": effective_primary,
            "effective_sensitivity": effective_sensitivity,
            "representations": derived}


def materialize_primary_assay_policy(packet: dict[str, Any], field_map: dict[str, Any],
                                     receipt: dict[str, Any], store_root: Path, *,
                                     provisional: bool = False) -> dict[str, Any]:
    """Build an in-memory primary assay view from the receipt and pinned source bytes."""
    records = packet.get("records")
    if not isinstance(records, dict):
        raise AssayPolicyEvidenceError("ASSAY_PACKET_RECORDS_INVALID")
    assay_rows = records.get("assay_registry")
    source_rows = records.get("source_record")
    if not isinstance(assay_rows, list) or not isinstance(source_rows, list):
        raise AssayPolicyEvidenceError("ASSAY_PACKET_REGISTRIES_INVALID")
    assay_metadata = derive_assay_policy_metadata(field_map, receipt, assay_rows)
    role = assay_metadata["effective_primary"]
    metadata = assay_metadata["representations"][role]
    object_hash = metadata["source_sha256"]
    matching_sources = [row for row in source_rows if row.get("sha256") == object_hash]
    if len(matching_sources) != 1:
        raise AssayPolicyEvidenceError("ASSAY_SOURCE_RECORD_AMBIGUOUS")
    source_record = copy.deepcopy(matching_sources[0])
    source_object_id = source_record.get("source_object_id")
    if not isinstance(source_object_id, str) or not source_object_id:
        raise AssayPolicyEvidenceError("ASSAY_SOURCE_OBJECT_ID_MISSING")
    primary_assays = [copy.deepcopy(row) for row in assay_rows
                      if row.get("source_object_id") == source_object_id]
    if not primary_assays:
        raise AssayPolicyEvidenceError("ASSAY_PRIMARY_ROWS_MISSING")
    specimen_counts: dict[str, int] = {}
    declared_suitability = (field_map.get('proposal_generation', {}).get('stage_config', {})
                            .get('materialization', {}).get('assay_suitability'))
    if declared_suitability is not None:
        _require(declared_suitability in {'BASELINE_DE', 'BASELINE_SCORING', 'PREDICTION_DEVELOPMENT',
                                          'OUTER_VALIDATION', 'FINAL_TEST', 'LONGITUDINAL'},
                 'ASSAY_SUITABILITY_INVALID')
    for assay in primary_assays:
        specimen_uid = assay.get("specimen_uid")
        if not isinstance(specimen_uid, str) or not specimen_uid:
            raise AssayPolicyEvidenceError("ASSAY_SPECIMEN_ID_MISSING")
        specimen_counts[specimen_uid] = specimen_counts.get(specimen_uid, 0) + 1
    if any(count != 1 for count in specimen_counts.values()):
        raise AssayPolicyEvidenceError("ASSAY_REPLICATE_STATUS_UNRESOLVED")

    v3_config = field_map["v3"]
    object_config = field_map["source_objects"][role]
    if object_config.get("format") not in {"MATRIX_HEADER_CSV", "MATRIX_HEADER_TSV", "XLSX_NUMERIC"}:
        raise AssayPolicyEvidenceError("ASSAY_MATRIX_FORMAT_UNSUPPORTED")
    delimiter_value = v3_config["delimiters"][role]
    if delimiter_value not in {",", "\t"}:
        raise AssayPolicyEvidenceError("ASSAY_MATRIX_DELIMITER_UNSUPPORTED")
    delimiter_name = "COMMA" if delimiter_value == "," else "TAB"
    compressed = v3_config["compressed"][role]
    matrix_path = store_root / "objects" / object_hash
    if not matrix_path.is_file():
        matrix_path = store_root / object_hash
    if not matrix_path.is_file():
        raise AssayPolicyEvidenceError("ASSAY_SOURCE_OBJECT_MISSING")
    hasher = hashlib.sha256()
    with matrix_path.open("rb") as binary_source:
        for chunk in iter(lambda: binary_source.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != object_hash:
        raise AssayPolicyEvidenceError("ASSAY_SOURCE_HASH_MISMATCH")

    headers_by_name = {row.get("matrix_header"): row for row in primary_assays}
    selected_headers = list(headers_by_name)
    if any(not isinstance(header, str) or not header for header in selected_headers):
        raise AssayPolicyEvidenceError("ASSAY_SELECTED_HEADER_INVALID")
    if len(selected_headers) != len(set(selected_headers)):
        raise AssayPolicyEvidenceError("ASSAY_SELECTED_HEADER_DUPLICATE")
    features: list[str] = []
    seen_features: set[str] = set()
    values: list[list[float | None]] = []
    receipt_key = next(key for key, value in v3_config['source_object_roles'].items() if value == role)
    exclusion_rows = receipt['checks'][receipt_key].get('object_derived_evidence', {}).get('excluded_rows', [])
    excluded = {item['row']: item['identifier'] for item in exclusion_rows}
    if len(excluded) != len(exclusion_rows):
        raise AssayPolicyEvidenceError('ASSAY_MATRIX_FEATURE_ID_INVALID')
    excluded_seen = 0
    from .matrix_header import matrix_rows
    with matrix_rows(matrix_path, delimiter=delimiter_value, compressed=compressed,
                     source_format=object_config["format"]) as reader:
        orientation = field_map["measurement_representations"][role].get("orientation", "samples_as_columns")
        if orientation == "samples_as_rows":
            from .matrix_header import transpose_sample_rows
            try:
                reader = iter(transpose_sample_rows(reader))
            except ValueError:
                raise AssayPolicyEvidenceError("ASSAY_MATRIX_ROW_WIDTH_INVALID") from None
        elif orientation != "samples_as_columns":
            raise AssayPolicyEvidenceError("ASSAY_MATRIX_FORMAT_UNSUPPORTED")
        header = next(reader, None)
        if header is None or len(header) < 2:
            raise AssayPolicyEvidenceError("ASSAY_MATRIX_HEADER_INVALID")
        auxiliary = field_map['measurement_representations'][role].get('auxiliary_columns', [])
        indexes = {item['index'] for item in auxiliary}
        if any(index <= 0 or index >= len(header) or header[index] != item['header'] for item in auxiliary for index in [item['index']]):
            raise AssayPolicyEvidenceError('ASSAY_MATRIX_HEADER_INVALID')
        if len([value for index, value in enumerate(header) if index not in indexes]) != len(set(value for index, value in enumerate(header) if index not in indexes)):
            raise AssayPolicyEvidenceError('ASSAY_MATRIX_HEADER_INVALID')
        source_headers = header[1:]
        if not set(selected_headers).issubset(source_headers):
            raise AssayPolicyEvidenceError("ASSAY_SELECTED_HEADER_NOT_FOUND")
        selected_indices = [source_headers.index(value) for value in selected_headers]
        for row_number, row in enumerate(reader, 1):
            if len(row) != len(header):
                raise AssayPolicyEvidenceError("ASSAY_MATRIX_ROW_WIDTH_INVALID")
            feature = row[0].strip()
            if row_number in excluded:
                if feature != excluded[row_number]:
                    raise AssayPolicyEvidenceError('ASSAY_MATRIX_FEATURE_ID_INVALID')
                excluded_seen += 1
                continue
            if field_map['measurement_representations'][role].get('missing_policy') == 'EXCLUDE_FEATURE_IF_ANY_MISSING':
                if any(not value.strip() or value.strip().upper() in {'NA', 'N/A', 'NULL'} for index, value in enumerate(row) if index > 0 and index not in indexes):
                    continue
            if not feature or feature in seen_features:
                raise AssayPolicyEvidenceError("ASSAY_MATRIX_FEATURE_ID_INVALID")
            features.append(feature)
            seen_features.add(feature)
            values_row: list[float | None] = []
            for index in selected_indices:
                raw = row[index + 1].strip()
                if not raw or raw.upper() in {"NA", "N/A", "NULL"}:
                    values_row.append(None)
                    continue
                try:
                    number = float(raw)
                except ValueError:
                    raise AssayPolicyEvidenceError("ASSAY_MATRIX_NONNUMERIC_VALUE") from None
                if not math.isfinite(number) or number < 0:
                    raise AssayPolicyEvidenceError("ASSAY_MATRIX_NUMERIC_VALUE_INVALID")
                values_row.append(number)
            values.append(values_row)
    if not features or excluded_seen != len(excluded):
        raise AssayPolicyEvidenceError("ASSAY_MATRIX_FEATURES_EMPTY")

    representation = field_map["measurement_representations"][role]
    normalization = representation.get("normalization")
    if provisional and not normalization:
        normalization = 'UNKNOWN'
    if not isinstance(normalization, str) or not normalization:
        raise AssayPolicyEvidenceError(f"ASSAY_POLICY_EVIDENCE_MISSING:normalization:{role}")
    try:
        feature_scope = validate_feature_scope(representation, provisional=provisional)
    except AssayPolicyEvidenceError as error:
        raise AssayPolicyEvidenceError(f'{error}:{role}') from None
    unit = metadata["unit"]
    unit = {'READ_COUNTS': 'counts', 'RSEM expected counts': 'estimated_counts'}.get(unit, unit)
    lane = ('COUNTS' if unit in {'counts', 'estimated_counts'} else
            'CONTINUOUS' if unit in {"TPM", "FPKM", "log_expression"} else None)
    if provisional and lane is None:
        lane = 'UNKNOWN'
    if lane is None:
        raise AssayPolicyEvidenceError(f"ASSAY_POLICY_EVIDENCE_MISSING:lane:{role}")

    for assay in primary_assays:
        assay.update({"platform": metadata["platform"], "modality": metadata["modality"],
                      "measurement_unit": unit, "transform": metadata["transform"],
                      "feature_annotation": metadata["annotation"], "genome_build": metadata["genome_build"],
                      "qc_status": "PASS", "replicate_status": "PRIMARY"})
        if declared_suitability is not None:
            assay['branch_suitability'] = [declared_suitability]
    source_record.update({"platform": metadata["platform"], "modality": metadata["modality"],
                          "measurement_unit": unit, "transform": metadata["transform"],
                          "feature_identifier_system": metadata["annotation"],
                          "normalisation": normalization})
    matrix = {
        "source_object_id": source_object_id, "source_sha256": object_hash,
        "headers": selected_headers, "features": features, "values": values,
        "unit": unit, "transform": metadata["transform"], "annotation": metadata["annotation"],
        "feature_universe": features, "feature_map": {feature: feature for feature in features},
        "feature_scope": feature_scope, "normalization": normalization, "lane": lane,
        "source_locator": f"sha256:{object_hash}", "replicate_policy": "PRESERVE",
        "missingness_policy": "PRESERVE", "delimiter": delimiter_name, "encoding": "UTF-8",
        "platform": metadata["platform"], "modality": metadata["modality"],
    }
    if feature_scope == 'COMPLETE_WITH_DOCUMENTED_EXCLUSIONS':
        matrix['excluded_feature_classes'] = copy.deepcopy(representation['excluded_feature_classes'])
    if lane == 'COUNTS':
        if any(value is None for row in values for value in row):
            raise AssayPolicyEvidenceError('ASSAY_MATRIX_MISSING_COUNTS')
        matrix['library_properties'] = {
            header: {'library_size': math.fsum(cast(float, row[index]) for row in values),
                     'source_locator': f'sha256:{object_hash}', 'evidence_type': 'DERIVED_FROM_OBJECT',
                     'rule': 'COLUMN_SUM_LIBRARY_SIZE'}
            for index, header in enumerate(selected_headers)}
        if unit == 'estimated_counts':
            matrix['quantifier'] = 'RSEM'
            matrix['estimated_count_structure'] = 'gene-level RSEM expected counts'
    result = copy.deepcopy(packet)
    result_records = result["records"]
    result_records["source_record"] = [source_record if row.get("source_object_id") == source_object_id else row
                                        for row in result_records["source_record"]]
    result_records["assay_registry"] = primary_assays
    result_config = result.setdefault("config", {})
    result_config["assays"] = {"required_features": features, "matrices": [matrix]}
    return result
