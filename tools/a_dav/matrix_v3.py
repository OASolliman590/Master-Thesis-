"""Outcome-blind, reusable V3 structural and numeric matrix checks."""
from __future__ import annotations

import argparse
import csv
from collections.abc import Iterator
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, TextIO, cast

from .core import DavError, require
from .geo_soft import parse_geo_family_soft
from .ingest import validate_output_path
from .matrix_header import matrix_rows, transpose_sample_rows

_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _open_text(path: Path, compressed: bool | None = None) -> TextIO:
    if compressed if compressed is not None else path.suffix == ".gz":
        return cast(TextIO, gzip.open(path, "rt", encoding="utf-8", newline=""))
    return path.open("r", encoding="utf-8", newline="")


def _blocked_result(representation: str, reasons: list[str], counts: dict[str, int],
                    checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blocked = bool(reasons) or any(row.get("status") == "BLOCKED" for row in checks.values())
    return {"representation": representation, "status": "BLOCKED" if blocked else "PASS",
            "reasons": sorted(set(reasons)), "counts": counts, "checks": checks}


def validate_v3_matrix(
    matrix_path: Path,
    *,
    expected_sample_ids: set[str],
    pre_sample_ids: set[str],
    on_sample_ids: set[str],
    selected_sample_ids: set[str],
    expected_counts: dict[str, int],
    annotation_feature_ids: set[str] | None,
    annotation_evidence_status: str,
    feature_id_pattern: str,
    annotation_label: str,
    genome_build: str,
    representation: str,
    processing_documented: bool,
    certification_level: str,
    feature_identity_limit: str | None = None,
    delimiter: str | None = None,
    compressed: bool | None = None,
    orientation: str = "samples_as_columns",
    undocumented_fields: list[str] | None = None,
    source_format: str = "MATRIX_HEADER_CSV",
    auxiliary_columns: list[dict[str, Any]] | None = None,
    missing_policy: str = "BLOCK",
    excluded_feature_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate a complete delimited expression matrix without outcome inputs.

    Results contain counts and reason codes only; source identifiers and values are
    used transiently for matching and are never returned.
    """
    require(missing_policy in {"BLOCK", "EXCLUDE_FEATURE_IF_ANY_MISSING"}, "MATRIX_MISSING_POLICY_INVALID")
    require(orientation in {"samples_as_columns", "samples_as_rows"}, "MATRIX_ORIENTATION_INVALID")
    require(bool(representation), "V3_REPRESENTATION_REQUIRED")
    require(pre_sample_ids.isdisjoint(on_sample_ids), "V3_TIMEPOINT_OVERLAP")
    require(set(expected_counts) == {"full_header_columns", "baseline_selected", "on_selected"}
            and all(type(value) is int and value >= 0 for value in expected_counts.values()),
            "V3_EXPECTED_COUNTS_INVALID")
    require(annotation_evidence_status in {"PINNED_ANNOTATION", "DECLARED_ID_FORMAT_ONLY", "UNKNOWN"},
            "V3_ANNOTATION_EVIDENCE_STATUS_INVALID")
    reasons: list[str] = []
    checks: dict[str, dict[str, Any]] = {}
    counts = {"features": 0, "sample_columns": 0, "selected_pre_columns": 0,
              "source_on_inventory_columns": 0, "selected_on_columns": 0,
              "cells": 0, "missing_cells": 0,
              "nonnumeric_cells": 0, "nonfinite_cells": 0, "negative_cells": 0,
              "blank_feature_ids": 0, "duplicate_feature_ids": 0,
              "feature_identifier_system_incompatible": 0, "unmapped_features": 0,
              "row_width_mismatches": 0,
              "duplicate_profile_groups": 0, "quarantined_columns": 0}
    if missing_policy == "EXCLUDE_FEATURE_IF_ANY_MISSING":
        counts["excluded_missing_features"] = 0
    exclusions = {item['row']: item['identifier'] for item in (excluded_feature_rows or [])}
    if excluded_feature_rows is not None:
        counts['excluded_feature_rows'] = 0
    if not processing_documented or undocumented_fields:
        reasons.append("PROCESSING_DOCUMENTATION_INSUFFICIENT")

    matrix_delimiter = delimiter or ("\t" if matrix_path.name.endswith(".tsv") or
                                      matrix_path.name.endswith(".tsv.gz") else ",")
    feature_ids: set[str] = set()
    selected_indices: list[tuple[int, str]] = []
    column_profiles: dict[str, list[float | str]] = {}
    duplicate_groups: list[list[str]] = []
    numeric_bad = {"NONNUMERIC_VALUES_PRESENT", "NONFINITE_VALUES_PRESENT", "NEGATIVE_VALUES_PRESENT"}
    try:
        with matrix_rows(matrix_path, delimiter=matrix_delimiter,
                         compressed=compressed if compressed is not None else matrix_path.suffix == ".gz",
                         source_format=source_format) as reader:
            if orientation == "samples_as_rows":
                reader = iter(transpose_sample_rows(reader))
            header = next(reader, None)
            if header is None or len(header) < 2:
                reasons.append("MATRIX_HEADER_INVALID")
                header = []
            if auxiliary_columns:
                indexes = [entry.get('index') for entry in auxiliary_columns]
                if (orientation != 'samples_as_columns' or len(indexes) != len(set(indexes)) or
                    any(type(index) is not int or index <= 0 or index >= len(header) or
                        header[index] != entry.get('header') for index, entry in zip(indexes, auxiliary_columns))):
                    raise ValueError('AUXILIARY_COLUMN_INVALID')
                source_width = len(header)
                excluded = set(indexes)
                header = [value for index, value in enumerate(header) if index not in excluded]
                reader = iter(([value for index, value in enumerate(row) if index not in excluded]
                               if len(row) == source_width else [] for row in reader))
            sample_header = header[1:]
            counts["sample_columns"] = len(sample_header)
            header_unique = len(sample_header) == len(set(sample_header)) and all(x.strip() for x in sample_header)
            if not header_unique:
                reasons.append("SAMPLE_HEADER_DUPLICATE_OR_BLANK")
            if len(sample_header) != expected_counts["full_header_columns"]:
                reasons.append("FULL_HEADER_COUNT_MISMATCH")
            if set(sample_header) != expected_sample_ids:
                reasons.append("SAMPLE_HEADER_RECONCILIATION_FAILED")
            counts["selected_pre_columns"] = len(set(sample_header) & selected_sample_ids & pre_sample_ids)
            counts["source_on_inventory_columns"] = len(set(sample_header) & on_sample_ids)
            counts["selected_on_columns"] = len(set(sample_header) & selected_sample_ids & on_sample_ids)
            if pre_sample_ids - set(sample_header) or on_sample_ids - set(sample_header):
                reasons.append("SOURCE_SAMPLE_INVENTORY_INCOMPLETE")
            if not selected_sample_ids:
                reasons.append("EMPTY_BASELINE_SELECTION")
            if not selected_sample_ids.issubset(expected_sample_ids):
                reasons.append("SELECTED_SAMPLE_INVENTORY_MISMATCH")
            if counts["selected_pre_columns"] != expected_counts["baseline_selected"]:
                reasons.append("PRE_SELECTION_COUNT_MISMATCH")
                reasons.append("BASELINE_SELECTION_COUNT_MISMATCH")
            if counts["selected_on_columns"] != expected_counts["on_selected"]:
                reasons.append("ON_SELECTION_COUNT_MISMATCH")
            if len(selected_sample_ids) != counts["selected_pre_columns"] + counts["selected_on_columns"]:
                reasons.append("SELECTED_SAMPLE_INVENTORY_MISMATCH")

            selected_indices = [(i, sample) for i, sample in enumerate(sample_header)
                                if sample in selected_sample_ids]
            column_profiles = {sample: [] for _, sample in selected_indices}
            for row_number, row in enumerate(reader, 1):
                if len(row) != len(header):
                    reasons.append("MATRIX_ROW_WIDTH_MISMATCH")
                    counts["row_width_mismatches"] += 1
                    continue
                feature_id = row[0].strip()
                if row_number in exclusions:
                    if feature_id != exclusions[row_number]:
                        raise ValueError('EXCLUDED_ROW_MISMATCH')
                    counts['excluded_feature_rows'] += 1
                    counts['features'] += 1
                    continue
                if not feature_id:
                    reasons.append("FEATURE_ID_BLANK")
                    counts["blank_feature_ids"] += 1
                if feature_id in feature_ids:
                    reasons.append("FEATURE_ID_DUPLICATE")
                    counts["duplicate_feature_ids"] += 1
                feature_ids.add(feature_id)
                values = row[1:]
                counts["cells"] += len(values)
                feature_missing = any(not value.strip() or value.strip().upper() in {"NA", "N/A", "NULL"} for value in values)
                if feature_missing and missing_policy == "EXCLUDE_FEATURE_IF_ANY_MISSING":
                    counts["excluded_missing_features"] += 1
                for value in values:
                    if value.strip() == "" or value.strip().upper() in {"NA", "N/A", "NULL"}:
                        counts["missing_cells"] += 1
                        continue
                    try:
                        number = float(value)
                    except ValueError:
                        reasons.append("NONNUMERIC_VALUES_PRESENT")
                        counts["nonnumeric_cells"] += 1
                        continue
                    if not math.isfinite(number):
                        reasons.append("NONFINITE_VALUES_PRESENT")
                        counts["nonfinite_cells"] += 1
                    elif number < 0:
                        reasons.append("NEGATIVE_VALUES_PRESENT")
                        counts["negative_cells"] += 1
                for index, sample in selected_indices:
                    if feature_missing and missing_policy == "EXCLUDE_FEATURE_IF_ANY_MISSING":
                        continue
                    value = row[index + 1].strip()
                    if value == "" or value.upper() in {"NA", "N/A", "NULL"}:
                        column_profiles[sample].append("MISSING")
                    else:
                        try:
                            numeric_profile_value = float(value)
                        except ValueError:
                            column_profiles[sample].append(f"NONNUMERIC:{value}")
                        else:
                            column_profiles[sample].append(
                                numeric_profile_value if math.isfinite(numeric_profile_value)
                                else f"NONFINITE:{value}")
                counts["features"] += 1
            if not feature_ids:
                reasons.append("MATRIX_HAS_NO_FEATURE_ROWS")
            if excluded_feature_rows is not None and counts['excluded_feature_rows'] != len(exclusions):
                raise ValueError('EXCLUDED_ROW_MISMATCH')
            if counts["missing_cells"] and missing_policy == "BLOCK":
                reasons.append("MISSING_CELLS_PRESENT")
            if (missing_policy == "EXCLUDE_FEATURE_IF_ANY_MISSING" and
                    counts["features"] == counts["excluded_missing_features"] + counts.get('excluded_feature_rows', 0)):
                reasons.append("NO_FEATURES_REMAIN_AFTER_MISSING_EXCLUSION")
            try:
                identifier_pattern = re.compile(feature_id_pattern)
            except re.error:
                identifier_pattern = re.compile("(?!)")
                reasons.append("FEATURE_ID_PATTERN_INVALID")
            incompatible_ids = sum(identifier_pattern.fullmatch(feature_id) is None for feature_id in feature_ids)
            counts["feature_identifier_system_incompatible"] = incompatible_ids
            if incompatible_ids:
                reasons.append("FEATURE_IDENTIFIER_SYSTEM_INCOMPATIBLE")
            if annotation_evidence_status == "PINNED_ANNOTATION":
                if not annotation_feature_ids:
                    reasons.append("ANNOTATION_EVIDENCE_MISSING")
                else:
                    counts["unmapped_features"] = len(feature_ids - annotation_feature_ids)
            elif annotation_evidence_status == "UNKNOWN":
                reasons.append("FEATURE_IDENTITY_UNDOCUMENTED")
            else:
                if annotation_feature_ids:
                    reasons.append("UNEXPECTED_ANNOTATION_FOR_FORMAT_ONLY")
                if not feature_identity_limit:
                    reasons.append("FEATURE_IDENTITY_LIMIT_UNDECLARED")
            seen_profiles: dict[tuple[float | str, ...], list[str]] = defaultdict(list)
            for sample_id, column_profile in column_profiles.items():
                seen_profiles[tuple(column_profile)].append(sample_id)
            duplicate_groups = [sorted(ids) for ids in seen_profiles.values() if len(ids) > 1]
            counts["duplicate_profile_groups"] = len(duplicate_groups)
            counts["quarantined_columns"] = sum(len(ids) for ids in duplicate_groups)
    except (OSError, UnicodeError, csv.Error, StopIteration, ValueError):
        reasons.append("MATRIX_PARSE_FAILED")

    if not processing_documented or undocumented_fields:
        checks["documented_processing"] = {"status": "BLOCKED", "reason": "PROCESSING_DOCUMENTATION_INSUFFICIENT",
                                           "undocumented_fields": sorted(undocumented_fields or [])}
    else:
        checks["documented_processing"] = {"status": "PASS"}
    if counts["features"] == 0:
        reasons.extend(["MATRIX_HAS_NO_FEATURE_ROWS", "NO_NUMERIC_CELLS"])
    if counts["cells"] == 0:
        reasons.append("NO_NUMERIC_CELLS")
    blocked_reasons = {
        "dimensions_and_parse": {"MATRIX_PARSE_FAILED", "MATRIX_ROW_WIDTH_MISMATCH", "MATRIX_HEADER_INVALID", "MATRIX_HAS_NO_FEATURE_ROWS"},
        "sample_header": {"MATRIX_PARSE_FAILED", "MATRIX_HEADER_INVALID", "SAMPLE_HEADER_DUPLICATE_OR_BLANK", "SAMPLE_HEADER_RECONCILIATION_FAILED", "FULL_HEADER_COUNT_MISMATCH"},
        "selected_timepoints": {"MATRIX_PARSE_FAILED", "SOURCE_SAMPLE_INVENTORY_INCOMPLETE", "EMPTY_BASELINE_SELECTION", "SELECTED_SAMPLE_INVENTORY_MISMATCH", "PRE_SELECTION_COUNT_MISMATCH", "BASELINE_SELECTION_COUNT_MISMATCH", "ON_SELECTION_COUNT_MISMATCH"},
        "feature_identity": {"MATRIX_PARSE_FAILED", "MATRIX_HAS_NO_FEATURE_ROWS", "FEATURE_ID_BLANK", "FEATURE_ID_DUPLICATE", "FEATURE_ID_PATTERN_INVALID", "FEATURE_IDENTIFIER_SYSTEM_INCOMPATIBLE", "ANNOTATION_EVIDENCE_MISSING", "UNEXPECTED_ANNOTATION_FOR_FORMAT_ONLY", "FEATURE_IDENTITY_LIMIT_UNDECLARED", "FEATURE_IDENTITY_UNDOCUMENTED"},
        "numeric_validity": {"MATRIX_PARSE_FAILED", "MATRIX_HAS_NO_FEATURE_ROWS", "NO_NUMERIC_CELLS", "MISSING_CELLS_PRESENT", "NO_FEATURES_REMAIN_AFTER_MISSING_EXCLUSION", "NONNUMERIC_VALUES_PRESENT", "NONFINITE_VALUES_PRESENT", "NEGATIVE_VALUES_PRESENT"},
        "duplicate_profiles": {"MATRIX_PARSE_FAILED", "MATRIX_HAS_NO_FEATURE_ROWS"},
    }
    checks.update({
        "dimensions_and_parse": {"status": "BLOCKED" if blocked_reasons["dimensions_and_parse"] & set(reasons) else "PASS",
                                 "reasons": sorted(blocked_reasons["dimensions_and_parse"] & set(reasons)),
                                 "counts": {"features": counts["features"], "sample_columns": counts["sample_columns"],
                                            "cells": counts["cells"],
                                            "row_width_mismatches": counts["row_width_mismatches"]}},
        "sample_header": {"status": "BLOCKED" if blocked_reasons["sample_header"] & set(reasons) else "PASS",
                          "reasons": sorted(blocked_reasons["sample_header"] & set(reasons)),
                          "counts": {"observed_sample_columns": counts["sample_columns"],
                                     "inventory_sample_columns": len(expected_sample_ids),
                                     "expected_sample_columns": expected_counts["full_header_columns"]}},
        "selected_timepoints": {"status": "BLOCKED" if blocked_reasons["selected_timepoints"] & set(reasons) else "PASS",
                               "reasons": sorted(blocked_reasons["selected_timepoints"] & set(reasons)),
                               "counts": {"selected_pre_columns": counts["selected_pre_columns"],
                                          "source_on_inventory_columns": counts["source_on_inventory_columns"],
                                          "selected_on_columns": counts["selected_on_columns"],
                                          "expected_baseline_selected": expected_counts["baseline_selected"],
                                          "expected_on_selected": expected_counts["on_selected"]}},
        "feature_identity": {"status": "BLOCKED" if blocked_reasons["feature_identity"] & set(reasons) else "PASS",
                             "reasons": sorted(blocked_reasons["feature_identity"] & set(reasons)),
                             "counts": {"blank_feature_ids": counts["blank_feature_ids"],
                                        "duplicate_feature_ids": counts["duplicate_feature_ids"],
                                        "identifier_system_incompatible": counts["feature_identifier_system_incompatible"],
                                        "unmapped_features": counts["unmapped_features"]},
                             "annotation_evidence_status": annotation_evidence_status,
                             "annotation_label": annotation_label, "genome_build": genome_build,
                             "certification_level": certification_level, "limit": feature_identity_limit,
                             "unmapped_disposition": "RETAINED_COVERAGE_OUTCOME" if annotation_evidence_status == "PINNED_ANNOTATION" else None},
        "numeric_validity": {"status": "BLOCKED" if blocked_reasons["numeric_validity"] & set(reasons) else "PASS",
                             "reasons": sorted(blocked_reasons["numeric_validity"] & set(reasons)),
                             "counts": {"nonnumeric_cells": counts["nonnumeric_cells"],
                                        "nonfinite_cells": counts["nonfinite_cells"],
                                        "negative_cells": counts["negative_cells"],
                                        "missing_cells": counts["missing_cells"]}},
        "duplicate_profiles": {"status": "BLOCKED" if blocked_reasons["duplicate_profiles"] & set(reasons)
                               else "QUARANTINE" if counts["duplicate_profile_groups"] else "PASS",
                               "reasons": sorted(blocked_reasons["duplicate_profiles"] & set(reasons)),
                               "disposition": "QUARANTINE_KEEP" if counts["duplicate_profile_groups"]
                               else "NO_DUPLICATE_PROFILES",
                               "counts": {"duplicate_profile_groups": counts["duplicate_profile_groups"],
                                          "quarantined_columns": counts["quarantined_columns"]},
                               "groups": duplicate_groups},
    })
    if missing_policy == "EXCLUDE_FEATURE_IF_ANY_MISSING":
        checks["numeric_validity"]["missing_policy"] = missing_policy
        checks["numeric_validity"]["excluded_missing_features"] = counts["excluded_missing_features"]
    return _blocked_result(representation, reasons, counts, checks)


def run_v3_with_fallback(primary_path: Path, fallback_path: Path | None, *,
                         primary_arguments: dict[str, Any],
                         fallback_arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Run the declared primary and automatically validate its fallback if blocked."""
    primary = validate_v3_matrix(primary_path, **primary_arguments)
    require((fallback_path is None) == (fallback_arguments is None), "V3_FALLBACK_INVALID")
    if fallback_path is None:
        passed = primary["status"] == "PASS"
        return {"primary": primary, "fallback": None,
                "selected_representation": primary["representation"] if passed else None,
                "effective_primary": primary["representation"] if passed else None,
                "effective_sensitivity": None,
                "selection_reason": "PRIMARY_V3_PASSED" if passed else "PRIMARY_BLOCKED_NO_FALLBACK"}
    assert fallback_arguments is not None
    if primary["status"] == "PASS":
        return {"primary": primary, "fallback": None,
                "selected_representation": primary["representation"],
                "effective_primary": primary["representation"],
                "effective_sensitivity": fallback_arguments["representation"],
                "selection_reason": "PRIMARY_V3_PASSED"}
    fallback = validate_v3_matrix(fallback_path, **fallback_arguments)
    fallback_passed = fallback["status"] == "PASS"
    return {"primary": primary, "fallback": fallback,
            "selected_representation": fallback["representation"] if fallback_passed else None,
            "effective_primary": fallback["representation"] if fallback_passed else None,
            "effective_sensitivity": primary["representation"] if fallback_passed else None,
            "selection_reason": "PRIMARY_BLOCKED_FALLBACK_VALIDATED" if fallback_passed
            else "PRIMARY_AND_FALLBACK_BLOCKED"}


def patient_free_summary(results: dict[str, Any]) -> dict[str, Any]:
    """Return count-only results suitable for a non-private summary."""
    def one(result: dict[str, Any]) -> dict[str, Any]:
        return {"status": result["status"], "counts": result["counts"], "reasons": result["reasons"]}

    return {"effective_primary": results["effective_primary"],
            "effective_sensitivity": results["effective_sensitivity"],
            "selected_representation": results["selected_representation"],
            "selection_reason": results["selection_reason"],
            "primary": one(results["primary"]),
            "fallback": None if results["fallback"] is None else one(results["fallback"])}


def object_path_by_sha256(store_dir: Path, sha256: str) -> Path:
    """Resolve a content-addressed object without consulting names or locators."""
    require(bool(_SHA256.fullmatch(sha256)), "SOURCE_OBJECT_HASH_INVALID")
    path = store_dir / "objects" / sha256
    require(path.is_file(), "SOURCE_OBJECT_NOT_FOUND")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(digest == sha256, "SOURCE_OBJECT_HASH_MISMATCH")
    return path


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "V3_INPUT_INVALID")
    return cast(dict[str, Any], value)


def _run_geo_primary_only(store: Path, field_map: dict[str, Any], output: Path) -> int:
    """Run source-preserving V3 checks without reading endpoint labels."""
    from .ingest import _expression_bindings, _parse_source
    from .source_objects import SourceObject

    config = field_map['v3']
    role = config['primary_representation']
    geo_role = config['sample_inventory_source_role']
    metadata = field_map['source_objects'][role]
    geo_sha = field_map['source_objects'][geo_role]['sha256']
    source_sha = metadata['sha256']
    geo_path = object_path_by_sha256(store, geo_sha)
    source_path = object_path_by_sha256(store, source_sha)
    visit_key = field_map['geo']['characteristics'].get('visit')
    patient_key = field_map['geo']['characteristics'].get('patient')
    binding_rule = field_map.get('expression_column_map', {}).get(role, {})
    groups = binding_rule.get('characteristic_groups', {})
    require(all(entry.get('characteristic') == visit_key for entry in groups.values()),
            'V3_BINDING_CHARACTERISTIC_NOT_OUTCOME_BLIND')
    samples = parse_geo_family_soft(geo_path.read_bytes(),
                                    characteristic_keys={key for key in (visit_key, patient_key) if key})
    # The V3 inventory carries identity and visit fields only.
    inventory = [{'accession': sample['accession'], 'title': sample['title'],
                  'characteristics': [entry for entry in sample['characteristics']
                                      if entry['key'] in {visit_key, patient_key}]}
                 for sample in samples]
    source = SourceObject(source_sha, metadata['locator'], metadata['version'],
                          source_path.stat().st_size, '', source_path.read_bytes())
    representation = field_map['measurement_representations'][role]
    axis = _parse_source(source, {**metadata, 'orientation': representation.get('orientation', 'samples_as_columns')})
    items: list[dict[str, Any]] = []
    bindings = _expression_bindings(inventory, {role: axis}, {role: source}, field_map, items)
    expected = set(bindings.values())
    baseline_values = field_map['geo_ingest']['baseline_values']
    pre: set[str] = set()
    on: set[str] = set()
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    title_rule = re.compile(field_map['sample_identity']['title_regex'])
    identity = field_map['sample_identity']
    for sample in inventory:
        header = bindings.get((role, sample['accession']))
        if header is None:
            continue
        characteristics = {entry['key']: entry['value'] for entry in sample['characteristics']}
        visit = characteristics.get(visit_key)
        match = title_rule.match(sample['title'])
        if visit in baseline_values:
            pre.add(header)
            patient = characteristics.get(patient_key) or (match.group(identity['patient_group']) if match else None)
            if patient:
                letter = match.group(identity['lesion_group']) if match and identity.get('lesion_group') else ''
                grouped[patient].append((letter, header))
        elif visit:
            on.add(header)
    selected: set[str] = set()
    for entries in grouped.values():
        if len(entries) == 1:
            selected.add(entries[0][1])
        elif field_map['geo_ingest'].get('baseline_tie_rule') == 'LOWEST_LESION_LETTER':
            letters = [entry[0] for entry in entries]
            if all(re.fullmatch('[A-Z]', letter) for letter in letters) and len(set(letters)) == len(letters):
                selected.add(min(entries)[1])
    unknown = [name for name in ('unit', 'transform', 'platform', 'genome_build', 'feature_identifier_system')
               if not representation.get(name) or representation.get(name) == 'UNKNOWN']
    identity_evidence = dict(config.get('representation_identity', {}).get(role, {}))
    derived_declarations = representation.get('derived_facts', {})
    recomputed: dict[str, Any] = {}
    feature_evidence: dict[str, Any] = {}
    if derived_declarations:
        import gzip
        from .object_evidence import derive_file_evidence
        unit_declaration = derived_declarations.get('unit', {})
        raw_geo = geo_path.read_bytes()
        geo_content = gzip.decompress(raw_geo).decode('utf-8') if raw_geo.startswith(b'\x1f\x8b') else raw_geo.decode('utf-8')
        processing = [line for line in geo_content.splitlines() if line.startswith('!Sample_data_processing = ')]
        named_rsem = any('RSEM expected counts' in line for line in processing)
        rsem_locator = unit_declaration.get('source_locator') if named_rsem else None
        expected_rsem_locator = field_map['source_objects'][geo_role]['locator'] + '#!Sample_data_processing'
        if rsem_locator != expected_rsem_locator:
            rsem_locator = None
        is_filename_rule = unit_declaration.get('rule') == 'FILENAME_PLUS_NONCONTRADICTING_PAPER'
        filename_locator = unit_declaration.get('filename_locator') if is_filename_rule else None
        paper_locator = unit_declaration.get('paper_locator') if is_filename_rule else None
        if filename_locator != metadata['locator']:
            filename_locator = None
        recomputed = derive_file_evidence(source_path, source_sha256=source_sha, source_format=metadata['format'],
            delimiter=config.get('delimiters', {}).get(role, ','),
            compressed=config.get('compressed', {}).get(role, False),
            auxiliary_columns=representation.get('auxiliary_columns'), rsem_source=rsem_locator,
            filename_unit='FPKM' if is_filename_rule else None, filename_locator=filename_locator,
            paper_noncontradiction=paper_locator)
        for key in ('unit', 'transform', 'feature_identifier_system'):
            asserted = derived_declarations.get(key, {})
            observed = recomputed[key]
            if asserted.get('status') == 'DERIVED':
                keys = ('status', 'value', 'evidence_type', 'rule', 'source_sha256')
                if (any(asserted.get(k) != observed.get(k) for k in keys) or
                        representation.get(key) != observed.get('value')):
                    unknown.append('derived_evidence_conflict:' + key)
        feature_evidence = recomputed['feature_identifier_system']
        declared_feature = derived_declarations.get('feature_identifier_system', {})
        if (feature_evidence.get('status') == 'DERIVED' and declared_feature == feature_evidence and
                representation.get('feature_identifier_system') == feature_evidence.get('value')):
            patterns = {'ENSEMBL_GENE': r'ENSG\d{11}(?:\.\d+)?', 'ENTREZ_GENE': r'\d+',
                        'GENE_SYMBOL': r'[A-Z0-9][A-Za-z0-9.-]*'}
            identity_evidence = {'annotation_evidence_status': 'DECLARED_ID_FORMAT_ONLY',
                                 'identifier_pattern': patterns[feature_evidence['value']],
                                 'certification_level': 'DERIVED_FROM_OBJECT',
                                 'limit': 'Identifier format only; annotation release remains unresolved.'}
    identity_status = identity_evidence.get('annotation_evidence_status', 'UNKNOWN')
    annotation_ids = None
    annotation_role = identity_evidence.get('annotation_role')
    if annotation_role:
        annotation_sha = field_map['source_objects'][annotation_role]['sha256']
        annotation_path = object_path_by_sha256(store, annotation_sha)
        annotation_ids = _read_first_column(annotation_path, config['delimiters'][annotation_role],
                                            config['compressed'][annotation_role])
    source_format = metadata['format']
    delimiter = config.get('delimiters', {}).get(role, '\t' if source_format == 'MATRIX_HEADER_TSV' else ',')
    compressed = config.get('compressed', {}).get(role, False)
    args = {'expected_sample_ids': expected, 'pre_sample_ids': pre, 'on_sample_ids': on,
            'selected_sample_ids': selected, 'expected_counts': config['expected_counts'],
            'annotation_feature_ids': annotation_ids, 'annotation_evidence_status': identity_status,
            'feature_id_pattern': identity_evidence.get('identifier_pattern', '.*'), 'annotation_label': representation.get('annotation', 'UNKNOWN'),
            'genome_build': representation.get('genome_build', 'UNKNOWN'),
            'representation': role, 'processing_documented': config.get('documentation', {}).get(role, {}).get('status') == 'DOCUMENTED',
            'certification_level': identity_evidence.get('certification_level', 'UNKNOWN'),
            'feature_identity_limit': identity_evidence.get('limit'), 'orientation': representation.get('orientation', 'samples_as_columns'),
            'source_format': source_format, 'delimiter': delimiter, 'compressed': compressed,
            'undocumented_fields': unknown, 'auxiliary_columns': representation.get('auxiliary_columns'),
            'missing_policy': representation.get('missing_policy', 'BLOCK'),
            'excluded_feature_rows': recomputed.get('excluded_rows') if feature_evidence.get('rule') == 'GENE_SYMBOL_MAJORITY' else None}
    results = run_v3_with_fallback(source_path, None, primary_arguments=args, fallback_arguments=None)
    if recomputed:
        results['primary']['object_derived_evidence'] = recomputed
    output.mkdir(parents=True, exist_ok=True)
    receipt = {'schema_version': '1', 'checks_version': 'V3', 'checks': results,
               'source_sha256': {'primary': source_sha, 'sample_inventory': geo_sha},
               'qc_policy': config.get('qc_policy', {})}
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (output / 'SUMMARY.json').write_text(json.dumps(patient_free_summary(results), sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if results['primary']['status'] == 'PASS' else 2

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--field-map", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        field_map = _load_json(args.field_map)
        config = field_map["v3"]
        if "geo_ingest" in field_map and not config.get("fallback_representation"):
            return _run_geo_primary_only(args.store, field_map, validate_output_path(args.out))
        source_hashes = {role: row["sha256"] for role, row in field_map["source_objects"].items()}
        primary_role = config["primary_representation"]
        fallback_role = config.get("fallback_representation")
        inventory_role = config["sample_inventory_source_role"]
        inventory_path = object_path_by_sha256(args.store, source_hashes[inventory_role])
        samples = parse_geo_family_soft(inventory_path.read_bytes(),
                                        characteristic_keys={field_map["geo"]["characteristics"]["visit"]})
        sample_inventory: dict[str, dict[str, str]] = {}
        for sample in samples:
            characteristics = {item["key"]: item["value"] for item in sample["characteristics"]}
            title_match = re.search(field_map["sample_identity"]["title_regex"], sample["title"])
            visit_key = field_map["geo"]["characteristics"]["visit"]
            visit_group = field_map["sample_identity"]["visit_group"]
            visit = characteristics.get(visit_key) or (title_match.group(visit_group) if title_match else "")
            sample_inventory[sample["accession"]] = {"accession": sample["accession"],
                                                     "visit": visit, "title": sample["title"]}
        require(bool(sample_inventory), "V3_SAMPLE_INVENTORY_EMPTY")
        primary_id = config["header_key_by_role"][primary_role]
        fallback_id = config["header_key_by_role"][fallback_role] if fallback_role else None
        primary_expected = {row[primary_id] for row in sample_inventory.values()}
        fallback_expected = {row[fallback_id] for row in sample_inventory.values()} if fallback_id else set()
        pre = {row[primary_id] for row in sample_inventory.values() if row["visit"].lower() == "pre"}
        on = {row[primary_id] for row in sample_inventory.values() if row["visit"].lower() == "on"}
        fallback_pre = {row[fallback_id] for row in sample_inventory.values() if row["visit"].lower() == "pre"} if fallback_id else set()
        fallback_on = {row[fallback_id] for row in sample_inventory.values() if row["visit"].lower() == "on"} if fallback_id else set()
        primary_path = object_path_by_sha256(args.store, source_hashes[config["source_object_roles"]["primary"]])
        fallback_path = object_path_by_sha256(args.store, source_hashes[config["source_object_roles"]["fallback"]]) if fallback_role else None

        def representation_arguments(role: str, expected: set[str], pre_ids: set[str],
                                     on_ids: set[str], matrix_path: Path) -> dict[str, Any]:
            identity = config["representation_identity"][role]
            annotation_role = identity["annotation_role"]
            annotation_ids = None
            if annotation_role is not None:
                annotation_path = object_path_by_sha256(args.store, source_hashes[annotation_role])
                annotation_ids = _read_first_column(annotation_path, config["delimiters"][annotation_role],
                                                    config["compressed"][annotation_role])
            return {"expected_sample_ids": expected, "pre_sample_ids": pre_ids,
                    "on_sample_ids": on_ids, "selected_sample_ids": pre_ids,
                    "expected_counts": config["expected_counts"],
                    "annotation_feature_ids": annotation_ids,
                    "annotation_evidence_status": identity["annotation_evidence_status"],
                    "feature_id_pattern": identity["identifier_pattern"],
                    "annotation_label": field_map["measurement_representations"][role]["annotation"],
                    "orientation": field_map["measurement_representations"][role].get("orientation", "samples_as_columns"),
                    "genome_build": identity["genome_build"],
                    "certification_level": identity["certification_level"],
                    "feature_identity_limit": identity["limit"],
                    "representation": role,
                    "processing_documented": config["documentation"][role]["status"] == "DOCUMENTED",
                    "delimiter": config["delimiters"][role],
                    "compressed": config["compressed"][role],
                    "matrix_path": matrix_path}

        primary_args = representation_arguments(primary_role, primary_expected, pre, on, primary_path)
        fallback_args = (representation_arguments(fallback_role, fallback_expected, fallback_pre,
                                                 fallback_on, fallback_path)
                         if fallback_role and fallback_path else None)
        primary_args.pop("matrix_path")
        if fallback_args is not None:
            fallback_args.pop("matrix_path")
        results = run_v3_with_fallback(
            primary_path, fallback_path,
            primary_arguments=primary_args,
            fallback_arguments=fallback_args,
        )
        output = validate_output_path(args.out)
        output.mkdir(parents=True, exist_ok=True)
        receipt_sources = {"primary": source_hashes[config["source_object_roles"]["primary"]],
                           "sample_inventory": source_hashes[inventory_role]}
        if fallback_role:
            receipt_sources["fallback"] = source_hashes[config["source_object_roles"]["fallback"]]
        for identity in config["representation_identity"].values():
            annotation_role = identity["annotation_role"]
            if annotation_role is not None:
                receipt_sources["annotation_" + annotation_role] = source_hashes[annotation_role]
        receipt = {"schema_version": "1", "checks_version": "V3", "checks": results,
                   "source_sha256": receipt_sources,
                   "qc_policy": field_map["v3"].get("qc_policy", {})}
        (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        summary = patient_free_summary(results)
        (output / "SUMMARY.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except (DavError, KeyError, OSError, json.JSONDecodeError) as error:
        parser.error(str(error))
    return 0


def _read_first_column(path: Path, delimiter: str = "\t", compressed: bool | None = None) -> set[str]:
    result: set[str] = set()
    with _open_text(path, compressed) as handle:
        reader = csv.reader(handle, delimiter=delimiter, strict=True)
        next(reader, None)
        for row in reader:
            if row and row[0].strip():
                result.add(row[0].strip())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
