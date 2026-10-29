"""Local-only source ingestion proposals for declared cohort field maps."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .assays import validate_assays
from .core import SchemaStore
from .delimited import DelimitedTable, read_delimited_table
from .endpoints import map_endpoints
from .field_maps import FieldMapError, load_field_map
from .geo_soft import parse_geo_family_soft
from .matrix_header import parse_matrix_header
from .registries import build_registries
from .source_objects import ContentAddressedStore, SourceObject, SourceObjectError
from .timing import validate_timing
from .xlsx import read_numeric_xlsx


REPO_ROOT = Path(__file__).resolve().parents[2]
FIELD_MAP_ROOT = Path(__file__).with_name("field_maps")


class IngestError(ValueError):
    """Safe command boundary error."""


def validate_output_path(output: Path, *, allow_external_out: bool = False) -> Path:
    candidate = Path(output).absolute()
    if any(parent.is_symlink() for parent in (candidate, *candidate.parents)):
        raise IngestError("OUTPUT_PATH_UNSAFE")
    resolved = candidate.resolve(strict=False)
    runtime_root = (REPO_ROOT / ".scratch" / "runtime").resolve(strict=False)
    try:
        resolved.relative_to(runtime_root)
        allowed_runtime = resolved != runtime_root
    except ValueError:
        allowed_runtime = False
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve())
        inside_repo = True
    except ValueError:
        relative = Path()
        inside_repo = False
    if not allowed_runtime:
        if not allow_external_out or inside_repo:
            raise IngestError("OUTPUT_PATH_NOT_ALLOWED")
    if inside_repo:
        try:
            tracked = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
                check=True, capture_output=True, text=False,
            ).stdout.split(b"\0")
        except (OSError, subprocess.CalledProcessError):
            raise IngestError("TRACKED_PATH_CHECK_FAILED") from None
        relative_text = relative.as_posix().rstrip("/")
        for raw_path in tracked:
            if not raw_path:
                continue
            tracked_path = raw_path.decode("utf-8", errors="strict")
            if (tracked_path == relative_text or tracked_path.startswith(relative_text + "/")
                    or relative_text.startswith(tracked_path + "/")):
                raise IngestError("OUTPUT_PATH_TRACKED")
    return resolved


def _item(items: list[dict[str, Any]], category: str, pointers: list[dict[str, str]],
          context: dict[str, Any] | None = None) -> None:
    row: dict[str, Any] = {"category": category, "status": "BLOCKED_UNKNOWN",
                            "evidence_pointers": pointers}
    if context:
        row["context"] = context
    items.append(row)


def _parse_source(source: SourceObject, object_map: dict[str, Any]) -> Any:
    source_format = object_map["format"]
    if source_format == "GEO_FAMILY_SOFT":
        return parse_geo_family_soft(source.bytes)
    if source_format in {"DELIMITED_CSV", "DELIMITED_TSV"}:
        delimiter = "," if source_format == "DELIMITED_CSV" else "\t"
        raw = source.bytes
        comment_prefix = object_map.get("comment_prefix", object_map.get("header_comment_prefix"))
        if comment_prefix:
            try:
                lines = raw.decode("utf-8-sig").splitlines(keepends=True)
            except UnicodeError:
                raise IngestError("SOURCE_OBJECT_PARSE_INVALID") from None
            raw = "".join(line for line in lines if not line.lstrip().startswith(comment_prefix)).encode("utf-8")
        return read_delimited_table(raw, delimiter=delimiter)
    if source_format in {"MATRIX_HEADER_CSV", "MATRIX_HEADER_TSV"}:
        delimiter = "," if source_format == "MATRIX_HEADER_CSV" else "\t"
        return parse_matrix_header(source.bytes, delimiter=delimiter,
                                   allow_empty=object_map.get("header_allow_empty", False),
                                   orientation=object_map.get("orientation", "samples_as_columns"))
    if source_format == "XLSX_NUMERIC":
        return read_numeric_xlsx(source.bytes)[0]
    if source_format in {"TEXT_UTF8", "SCRIPT_R"}:
        if len(source.bytes) > 8 * 1024 * 1024:
            raise IngestError("SOURCE_OBJECT_PARSE_INVALID")
        try:
            return source.bytes.decode("utf-8-sig")
        except UnicodeError:
            raise IngestError("SOURCE_OBJECT_PARSE_INVALID") from None
    raise IngestError("FIELD_MAP_FORMAT_INVALID")


def _normalize_sample_name(value: str, rule: dict[str, str], bam_suffix: str) -> str:
    sample = value.removesuffix(bam_suffix)
    return re.sub(rule["regex"], rule["replacement"], sample)


def _sample_code_group(value: str, sample_cfg: dict[str, Any]) -> str | None:
    """Return a declared grouping token for candidate discovery, never identity."""
    grouping = sample_cfg.get("sample_code_group")
    if not isinstance(grouping, dict):
        return None
    normalized = _normalize_sample_name(value, sample_cfg["sample_name_rule"], sample_cfg["bam_suffix"])
    match = re.match(grouping["regex"], normalized)
    group = grouping["capture_group"]
    return match.group(group) if match is not None and group <= match.re.groups else None


def _table_value(table: DelimitedTable, position: int, row: tuple[str, ...]) -> str | None:
    return row[position] if 0 <= position < len(row) else None


def _locator(value: str) -> list[dict[str, str]]:
    return [{"kind": "source_object", "value": value}]


def _source_repository(locator: str) -> str:
    match = re.match(r"https?://([^/]+)", locator)
    return match.group(1) if match else "UNKNOWN"


def _source_object_id(cohort: str, role: str) -> str:
    return f"SOURCE:{cohort}:{role}"


def _expression_bindings(soft: list[dict[str, Any]], parsed: dict[str, Any],
                         sources: dict[str, SourceObject], field_map: dict[str, Any],
                         items: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    bindings: dict[tuple[str, str], str] = {}
    for role, representation in field_map.get('measurement_representations', {}).items():
        if not isinstance(representation, dict):
            continue
        rules = field_map.get('expression_column_map', {})
        rule = rules.get(role)
        headers = parsed.get(role)
        if not isinstance(rule, dict) or rule.get('method') == 'UNRESOLVED':
            _item(items, 'EXPRESSION_BINDING_RULE_UNRESOLVED', [{'role': role}])
            continue
        if not isinstance(headers, tuple) or role not in sources:
            _item(items, 'EXPRESSION_BINDING_UNRESOLVED', [{'role': role}])
            continue
        method = rule['method']
        if rule.get('review_required', False):
            _item(items, 'EXPRESSION_BINDING_RULE_REVIEW_REQUIRED', [{'role': role}])
        crosswalk: dict[str, list[str]] = {}
        if method == 'CROSSWALK':
            cross_role = rule['source_role']
            table = parsed.get(cross_role)
            metadata = field_map['source_objects'].get(cross_role, {})
            if not isinstance(table, DelimitedTable) or cross_role not in sources or not metadata.get('sha256') or sources[cross_role].sha256 != metadata['sha256']:
                _item(items, 'EXPRESSION_CROSSWALK_UNAVAILABLE', [{'role': cross_role}])
                continue
            try:
                mi = table.headers.index(rule['matrix_column'])
                gi = table.headers.index(rule['geo_column'])
            except ValueError:
                _item(items, 'EXPRESSION_CROSSWALK_UNAVAILABLE', [{'role': cross_role}])
                continue
            if table.headers.count(rule['matrix_column']) != 1 or table.headers.count(rule['geo_column']) != 1:
                _item(items, 'EXPRESSION_CROSSWALK_UNAVAILABLE', [{'role': cross_role}])
                continue
            for row in table.rows:
                crosswalk.setdefault(row[mi], []).append(row[gi])
        header_pattern = re.compile(rule['header_regex']) if method == 'REGEX' else None
        title_pattern = re.compile(rule['title_regex']) if method == 'REGEX' else None
        def match_key(pattern: re.Pattern[str] | None, value: str) -> tuple[tuple[str, str], ...] | None:
            match = pattern.fullmatch(value) if pattern else None
            if match is None or not match.groupdict() or any(value is None for value in match.groupdict().values()):
                return None
            groups = match.groupdict()
            for name, value in groups.items():
                for change in rule.get('normalizations', []):
                    value = re.sub(change['regex'], change['replacement'], value)
                groups[name] = value
            return tuple(sorted(groups.items()))
        matches: dict[str, list[str]] = {}
        header_counts = Counter(headers)
        for sample in soft:
            candidates: list[str] = []
            for header in headers:
                if not header:
                    continue
                if method == 'TITLE':
                    matched = header == sample['title']
                elif method == 'ACCESSION':
                    matched = header == sample['accession']
                elif method == 'REGEX':
                    a, b = match_key(header_pattern, header), match_key(title_pattern, sample['title'])
                    header_groups = dict(a) if a is not None else {}
                    allowed_groups = rule.get('characteristic_groups', {})
                    characteristics_match = True
                    for group, declaration in allowed_groups.items():
                        token = header_groups.pop(group, None)
                        characteristic_values = {entry['value'] for entry in sample['characteristics']
                                                 if entry['key'] == declaration['characteristic']}
                        expected_value = declaration['values'].get(token)
                        if expected_value is None or characteristic_values != {expected_value}:
                            characteristics_match = False
                    matched = a is not None and b is not None and characteristics_match and tuple(sorted(header_groups.items())) == b
                elif method == 'CROSSWALK':
                    values = crosswalk.get(header, [])
                    matched = sample[rule['geo_key']] in values
                    if matched and len(values) != 1:
                        _item(items, 'EXPRESSION_BINDING_AMBIGUOUS', [{'role': role, 'record': sample['accession']}, {'role': rule['source_role']}])
                        continue
                else:
                    matched = False
                if matched:
                    candidates.append(header)
            matches[sample['accession']] = candidates
        used = Counter(header for candidates in matches.values() for header in candidates)
        for sample in soft:
            candidates = matches[sample['accession']]
            if len(candidates) == 1 and header_counts[candidates[0]] == 1 and used[candidates[0]] == 1:
                bindings[(role, sample['accession'])] = candidates[0]
            else:
                visit_key = field_map.get('geo', {}).get('characteristics', {}).get('visit')
                visits = {entry['value'] for entry in sample.get('characteristics', []) if entry['key'] == visit_key}
                baseline_values = field_map.get('geo_ingest', {}).get('baseline_values', [])
                if (not candidates and rule.get('nonbaseline_unmatched') == 'NOT_APPLICABLE'
                        and len(visits) == 1 and next(iter(visits)) not in baseline_values):
                    continue
                category = 'EXPRESSION_BINDING_AMBIGUOUS' if candidates else 'EXPRESSION_BINDING_UNRESOLVED'
                _item(items, category, [{'role': role, 'record': sample['accession']}])
    return bindings


def _geo_records(tables: dict[str, list[dict[str, Any]]], soft: list[dict[str, Any]],
                 parsed: dict[str, Any], sources: dict[str, SourceObject],
                 field_map: dict[str, Any], items: list[dict[str, Any]]) -> None:
    cfg = field_map['geo_ingest']
    identity = field_map['sample_identity']
    characteristics = field_map['geo']['characteristics']
    study_id = 'STUDY:' + field_map['cohort']
    locator = field_map['source_objects']['geo_family_soft']['locator']
    title_re = re.compile(identity['title_regex']) if identity.get('title_regex') else None
    bindings = _expression_bindings(soft, parsed, sources, field_map, items)
    grouped: dict[str, list[tuple[dict[str, Any], str, str | None]]] = {}
    treatment_declaration = field_map.get('treatment_proposal', {})
    if treatment_declaration.get('agent_interpretation') == 'CLASS':
        _item(items, 'TREATMENT_DRUG_IDENTITY_UNKNOWN', [{'role': 'geo_family_soft',
              'field': treatment_declaration['agent_field']}])
    if cfg.get('baseline_by_cohort'):
        _item(items, 'COHORT_BASELINE_TIMING_UNVERIFIED', [{'role': 'geo_family_soft', 'field': 'sample timing'}])
    for sample in soft:
        values: dict[str, list[str]] = {}
        for entry in sample['characteristics']:
            values.setdefault(entry['key'], []).append(entry['value'])
        def characteristic(key: str | None) -> str | None:
            matches = values.get(key or '', [])
            return matches[0] if len(set(matches)) == 1 and matches else None
        match = title_re.match(sample['title']) if title_re else None
        patient = characteristic(characteristics.get('patient'))
        title_patient = match.group(identity['patient_group']) if match and identity.get('patient_group') else None
        if patient and title_patient and patient != title_patient:
            _item(items, 'GEO_PATIENT_IDENTITY_CONFLICT', [{'role': 'geo_family_soft', 'record': sample['accession']}])
            continue
        patient = patient or title_patient
        if not patient or cfg.get('patient_mapping_unverified', False):
            _item(items, 'GEO_PATIENT_IDENTITY_UNRESOLVED', [{'role': 'geo_family_soft', 'record': sample['accession'], 'field': 'title'}])
            continue
        visit = characteristic(characteristics.get('visit'))
        if visit is None and match and identity.get('visit_group'):
            visit = match.group(identity['visit_group'])
        if visit is None and cfg.get('baseline_by_cohort'):
            visit = 'COHORT_BASELINE'
        if visit is None:
            _item(items, 'GEO_VISIT_CHARACTERISTIC_UNKNOWN', [{'role': 'geo_family_soft', 'record': sample['accession']}])
            visit = 'UNKNOWN'
        response = characteristic(characteristics.get('response'))
        grouped.setdefault(patient, []).append((sample, visit, response))
    for patient, entries in sorted(grouped.items()):
        uid = f"{study_id}:PATIENT:{hashlib.sha256(patient.encode('utf-8')).hexdigest()}"
        tables['patient_registry'].append({'data_classification': 'PRIVATE_PATIENT_LEVEL', 'patient_uid': uid,
            'study_id': study_id, 'source_patient_id': patient, 'patient_identity_confidence': 'UNRESOLVED',
            'prior_ici': 'UNKNOWN', 'prior_radiotherapy': 'UNKNOWN', 'treatment_naive_status': 'UNKNOWN',
            'inclusion_state': 'CANDIDATE', 'source_locators': _locator(locator)})
        treatment = field_map.get('treatment_proposal')
        if isinstance(treatment, dict):
            if treatment['agent_source'] == 'GEO_CHARACTERISTIC':
                agents = {item['value'] for sample, _, _ in entries for item in sample['characteristics']
                          if item['key'] == treatment['agent_field'] and item['value'].strip()}
                agent = next(iter(agents)) if len(agents) == 1 else 'UNKNOWN'
                if len(agents) != 1:
                    _item(items, 'TREATMENT_AGENT_UNRESOLVED', [{'role': 'geo_family_soft',
                          'field': treatment['agent_field'], 'record': entries[0][0]['accession']}])
            else:
                agent = treatment['agent_value']
            treatment_class = treatment['pharmacological_class']
            if treatment.get('agent_interpretation') == 'CLASS':
                treatment_class, agent = agent, 'UNKNOWN'
            episode_id, exposure_id = uid + ':index', uid + ':exposure'
            tables['treatment_episode'].append({'schema_version': '1.1.0',
                'data_classification': 'PRIVATE_PATIENT_LEVEL', 'treatment_episode_id': episode_id,
                'patient_uid': uid, 'study_id': study_id, 'regimen_id': treatment['regimen_id'],
                'index_event': treatment['index_event'], 'start_day': None, 'stop_day': None,
                'timing_precision': 'UNKNOWN', 'prior_ici': 'UNKNOWN', 'episode_status': 'BLOCKED_UNKNOWN',
                'component_exposure_ids': [exposure_id], 'source_locators': [treatment['source_locator']]})
            tables['treatment_exposure'].append({'data_classification': 'PRIVATE_PATIENT_LEVEL',
                'treatment_exposure_id': exposure_id, 'patient_uid': uid, 'regimen_id': treatment['regimen_id'],
                'agent': agent, 'pharmacological_class': treatment_class,
                'sequence': 'INDEX', 'line_of_therapy': 'UNKNOWN', 'prior_ici': 'UNKNOWN',
                'certainty': 'UNRESOLVED', 'source_locators': _locator(treatment['source_locator'])})
        baseline_entries = [entry for entry in entries if entry[1] in cfg['baseline_values'] or entry[1] == 'COHORT_BASELINE']
        selected_baseline = baseline_entries
        if len(baseline_entries) > 1 and cfg.get('baseline_tie_rule') == 'LEXICOGRAPHIC_ACCESSION':
            selected_baseline = [min(baseline_entries, key=lambda entry: entry[0]['accession'])]
        elif len(baseline_entries) > 1 and cfg.get('baseline_tie_rule') == 'LOWEST_LESION_LETTER':
            lesion_group = identity.get('lesion_group')
            matches = [(title_re.fullmatch(entry[0]['title']) if title_re else None, entry)
                       for entry in baseline_entries]
            letters = [match.group(lesion_group) if match and lesion_group else None for match, _ in matches]
            if all(letter and re.fullmatch('[A-Z]', letter) for letter in letters) and len(set(letters)) == len(letters):
                selected_baseline = [min(zip(letters, baseline_entries), key=lambda pair: pair[0] or '')[1]]
            else:
                _item(items, 'BASELINE_LESION_TIE_UNRESOLVED', [{'role': 'geo_family_soft', 'rule': 'lesion letter'}])
                selected_baseline = []
        if len(baseline_entries) > 1 and len(selected_baseline) != 1:
            _item(items, 'DUPLICATE_GEO_PATIENT_VISIT', [{'role': 'geo_family_soft', 'rule': 'patient+baseline'}],
                  {'duplicate_record_count': len(baseline_entries), 'tie_rule': cfg.get('baseline_tie_rule')})
        for sample, visit, response in entries:
            accession = sample['accession']
            is_baseline = (sample, visit, response) in selected_baseline
            pointer = f"sha256:{sources['geo_family_soft'].sha256}#sample={accession}" if 'geo_family_soft' in sources else locator + '#sample=' + accession
            specimen_uid = f'{study_id}:SPECIMEN:{accession}'
            compartment_cfg = field_map.get('biological_compartment', {})
            field = compartment_cfg.get('source_name_field')
            raw_compartment = sample.get(field) if isinstance(field, str) else None
            if raw_compartment is None and isinstance(field, str):
                candidates = {entry['value'] for entry in sample['characteristics'] if entry['key'] == field}
                raw_compartment = next(iter(candidates)) if len(candidates) == 1 else None
            compartment_map = compartment_cfg.get('source_name_map', {})
            normalized_map = {key.strip().lower(): value for key, value in compartment_map.items()}
            compartment = normalized_map.get(raw_compartment.strip().lower(), 'UNKNOWN') if isinstance(raw_compartment, str) else 'UNKNOWN'
            tables['specimen_registry'].append({'data_classification': 'PRIVATE_PATIENT_LEVEL',
                'specimen_uid': specimen_uid, 'patient_uid': uid, 'raw_sample_aliases': [accession, sample['title']],
                'timing_raw_text': visit, 'canonical_timing_category': 'PRE_INDEX_BASELINE' if (sample, visit, response) in baseline_entries else 'UNKNOWN',
                'tissue_type': '', 'biological_compartment': compartment, 'scheduled_or_clinically_indicated': 'UNKNOWN',
                'baseline_candidate_status': ('YES' if is_baseline else 'UNKNOWN'
                    if visit == 'UNKNOWN' or ((sample, visit, response) in baseline_entries and not selected_baseline) else 'NO'),
                'longitudinal_pair_status': 'UNKNOWN', 'source_locators': _locator(pointer)})
            for role, representation in field_map.get('measurement_representations', {}).items():
                headers, source = parsed.get(role), sources.get(role)
                if not isinstance(representation, dict) or not isinstance(headers, tuple) or source is None:
                    continue
                header = bindings.get((role, accession))
                if header is None:
                    continue
                tables['assay_registry'].append({'data_classification': 'PRIVATE_PATIENT_LEVEL',
                    'assay_uid': f'{study_id}:ASSAY:{role}:{accession}', 'specimen_uid': specimen_uid,
                    'source_sample_id': accession, 'source_object_id': _source_object_id(field_map['cohort'], role),
                    'modality': 'RNA_SEQ', 'platform': representation.get('platform', ''),
                    'measurement_unit': representation.get('unit', ''), 'genome_build': representation.get('genome_build'),
                    'feature_annotation': representation.get('annotation'), 'transform': representation.get('transform'),
                    'matrix_header': header, 'qc_status': 'NOT_EVALUATED', 'replicate_status': 'UNKNOWN',
                    'branch_suitability': [], 'source_locators': _locator(f"sha256:{source.sha256}#{'row' if representation.get('orientation') == 'samples_as_rows' else 'column'}={header}")})
        if not baseline_entries:
            continue
        responses = {response for _, _, response in baseline_entries if response is not None}
        if cfg['response_source'] != 'geo_family_soft':
            _item(items, 'RESPONSE_SOURCE_NOT_AVAILABLE', [{'role': cfg['response_source']}])
            continue
        if len(responses) != 1:
            _item(items, 'GEO_RESPONSE_UNRESOLVED', [{'role': 'geo_family_soft', 'field': characteristics.get('response', '')}])
            continue
        raw = next(iter(responses))
        category = cfg['response_map'].get(raw, 'UNKNOWN')
        if category == 'UNKNOWN' and raw not in cfg['response_map']:
            _item(items, 'GEO_RESPONSE_VALUE_UNKNOWN', [{'role': 'geo_family_soft', 'field': characteristics.get('response', '')}])
        tables['clinical_outcome'].append({'data_classification': 'PRIVATE_PATIENT_LEVEL',
            'outcome_id': f'{uid}:BOR', 'patient_uid': uid, 'raw_endpoint_label': raw,
            'endpoint_class': cfg['endpoint_class'], 'assessment_criteria': cfg.get('assessment_criteria', ''),
            'best_overall_response': category if category in {'CR', 'PR', 'SD', 'PD', 'NE'} else 'UNKNOWN',
            'canonical_category': category, 'evaluability': 'UNKNOWN', 'mapping_rule_version': 'field-map',
            'mapping_confidence': 'UNRESOLVED', 'discrepancy_status': 'UNRESOLVED', 'source_locators': _locator(locator)})


def build_canonical_records(parsed: dict[str, Any], sources: dict[str, SourceObject],
                           field_map: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Map clean source joins into frozen entity tables, leaving judgments unresolved."""
    tables: dict[str, list[dict[str, Any]]] = {name: [] for name in (
        "study_registry", "publication_family", "source_record", "patient_registry",
        "specimen_registry", "clinical_outcome", "treatment_episode", "treatment_exposure",
        "episode_binding", "assay_registry", "overlap_edge", "prior_exposure_record")}
    cohort = field_map["cohort"]
    study_id = f"STUDY:{cohort}"
    family_id = f"PUBLICATION_FAMILY:{cohort}"
    publication_id = f"PUBLICATION:{cohort}"
    role_cfgs = field_map["source_objects"]
    source_ids = {role: _source_object_id(cohort, role) for role in role_cfgs}
    object_locators = [metadata["locator"] for metadata in role_cfgs.values()]
    study_record = {
        "study_id": study_id, "publication_family_id": family_id, "study_title": cohort,
        "cancer_type": field_map.get("cancer_type", ""), "study_design": "",
        "candidate_paper_branches": [field_map["branch_id"]], "study_status": "CANDIDATE",
        "source_locators": [pointer for locator in object_locators for pointer in _locator(locator)],
    }
    if "study_class" in field_map:
        study_record["study_class"] = field_map["study_class"]
    tables["study_registry"].append(study_record)
    tables["publication_family"].append({
        "publication_family_id": family_id, "study_id": study_id,
        "publication_id": publication_id, "publication_role": "OTHER",
        "independence_status": "UNRESOLVED",
        "source_locators": [pointer for locator in object_locators for pointer in _locator(locator)],
    })
    for role, metadata in role_cfgs.items():
        source = sources.get(role)
        locator = source.locator if source is not None else metadata["locator"]
        source_record = {
            "source_object_id": source_ids[role], "study_id": study_id,
            "publication_family_id": family_id, "repository": _source_repository(locator),
            "object_url": locator, "access_route": "PUBLIC_DIRECT",
            "object_type": metadata["format"], "exact_file_name": locator.rsplit("/", 1)[-1],
            "source_version": source.version if source else metadata["version"],
            "retrieval_utc": source.retrieved_at if source else None,
            "byte_size": source.byte_size if source else None,
            "sha256": source.sha256 if source else metadata["sha256"],
            "hash_scope": "FULL_OBJECT" if source else "NOT_RETRIEVED",
            "patient_sample_crosswalk": "AVAILABLE_UNVERIFIED",
            "redistribution_status": "UNKNOWN",
            "retrieval_status": "RETRIEVED" if source else "NOT_ATTEMPTED",
            "validation_status": "STRUCTURAL_ONLY" if source else "NOT_VALIDATED",
            "source_locators": _locator(locator),
        }
        representation = field_map.get("measurement_representations", {}).get(role)
        if representation:
            source_record.update({
                "modality": "RNA_SEQ", "genome_build": representation.get("genome_build"),
                "feature_identifier_system": representation.get("annotation"),
                "measurement_unit": representation.get("unit"),
                "transform": representation.get("transform"),
                "platform": representation.get("platform"),
            })
        if metadata.get("role") == "harmonized_cross_check":
            source_record["notes"] = "Harmonized resource; cross-check only."
        tables["source_record"].append(source_record)

    soft = parsed.get("geo_family_soft")
    if not isinstance(soft, list):
        return tables
    if "geo_ingest" in field_map:
        _geo_records(tables, soft, parsed, sources, field_map, items)
        return tables
    sample_table = parsed.get("author_sample_table")
    clinical_table = parsed.get("author_clinical_table")
    sample_cfg = field_map["author_sample_table"]
    clinical_cfg = field_map["author_clinical_table"]
    compartment_cfg = field_map.get("biological_compartment", {})
    sample_matches: dict[str, list[tuple[str, ...]]] = {}
    sample_code_matches: dict[str, list[tuple[str, ...]]] = {}
    if isinstance(sample_table, DelimitedTable):
        for row in sample_table.rows:
            sample_name = _table_value(sample_table, sample_cfg["sample_name_column"], row)
            if sample_name:
                key = _normalize_sample_name(sample_name, sample_cfg["sample_name_rule"], sample_cfg["bam_suffix"])
                sample_matches.setdefault(key, []).append(row)
                sample_code = _sample_code_group(sample_name, sample_cfg)
                if sample_code:
                    sample_code_matches.setdefault(sample_code, []).append(row)
    clinical_matches: dict[str, list[tuple[str, ...]]] = {}
    clinical_bor_position = clinical_cohort_position = -1
    if isinstance(clinical_table, DelimitedTable):
        try:
            clinical_bor_position = clinical_table.headers.index(clinical_cfg["bor_column"])
            clinical_cohort_position = clinical_table.headers.index(clinical_cfg["cohort_column"])
            for row in clinical_table.rows:
                patient_id = _table_value(clinical_table, clinical_cfg["patient_column"], row)
                if patient_id:
                    clinical_matches.setdefault(patient_id, []).append(row)
        except (KeyError, ValueError):
            _item(items, "CLINICAL_TABLE_COLUMNS_UNKNOWN", [])
    title_matcher = re.compile(field_map["sample_identity"]["title_regex"])
    parsed_samples: list[tuple[dict[str, Any], str, str, tuple[str, ...] | None, tuple[str, ...] | None]] = []
    patient_visits: Counter[tuple[str, str]] = Counter()
    clinical_unknown_reported: set[str] = set()
    for sample in soft:
        match = title_matcher.match(sample["title"])
        if match is None:
            continue
        patient_id = match.group(field_map["sample_identity"]["patient_group"])
        visit = match.group(field_map["sample_identity"]["visit_group"])
        patient_visits[(patient_id, visit)] += 1
        visit_key = field_map["geo"]["characteristics"]["visit"]
        visit_values = [entry["value"] for entry in sample["characteristics"]
                        if entry["key"] == visit_key]
        if len(set(visit_values)) != 1:
            _item(items, "GEO_VISIT_CHARACTERISTIC_UNKNOWN", [
                {"role": "geo_family_soft", "record": sample["accession"], "field": visit_key}])
            continue
        if visit_values[0] != visit:
            _item(items, "TITLE_CHARACTERISTIC_VISIT_DISAGREEMENT", [
                {"role": "geo_family_soft", "record": sample["accession"], "field": "title"},
                {"role": "geo_family_soft", "record": sample["accession"], "field": visit_key}],
                {"title_visit": visit, "characteristic_visit": visit_values[0]})
            continue
        key = _normalize_sample_name(sample["title"], sample_cfg["sample_name_rule"], sample_cfg["bam_suffix"])
        author_rows = sample_matches.get(key, [])
        author_row = author_rows[0] if len(author_rows) == 1 else None
        author_patient = _table_value(sample_table, sample_cfg["patient_column"], author_row) if isinstance(sample_table, DelimitedTable) and author_row else None
        clean_author_link = author_patient == patient_id
        if len(author_rows) != 1:
            if not author_rows:
                sample_code = _sample_code_group(sample["title"], sample_cfg)
                candidates = sample_code_matches.get(sample_code, []) if sample_code else []
                conflicts = []
                if isinstance(sample_table, DelimitedTable):
                    for candidate in candidates:
                        candidate_name = _table_value(sample_table, sample_cfg["sample_name_column"], candidate)
                        candidate_patient = _table_value(sample_table, sample_cfg["patient_column"], candidate)
                        candidate_match = (title_matcher.match(_normalize_sample_name(
                            candidate_name, sample_cfg["sample_name_rule"], sample_cfg["bam_suffix"]))
                            if candidate_name else None)
                        prefix_conflict = candidate_match is not None and (
                            candidate_match.group(field_map["sample_identity"]["patient_group"]) != patient_id
                            or candidate_match.group(field_map["sample_identity"]["visit_group"]) != visit)
                        patient_conflict = bool(candidate_patient and candidate_patient != patient_id)
                        if prefix_conflict or patient_conflict:
                            conflicts.append(candidate)
                pointers = [
                    {"role": "geo_family_soft", "record": sample["accession"], "field": "title"},
                    {"role": "author_sample_table", "field": "BamName", "rule": "sample_code_group"},
                    {"role": "author_sample_table", "field": "PatientID"},
                ]
                if conflicts:
                    _item(items, "AUTHOR_SAMPLE_CODE_IDENTITY_CONFLICT", pointers,
                          {"candidate_count": len(candidates),
                           "conflicting_candidate_count": len(conflicts)})
                elif candidates:
                    _item(items, "AUTHOR_SAMPLE_CODE_CANDIDATE_UNRESOLVED", pointers,
                          {"candidate_count": len(candidates)})
                else:
                    _item(items, "AUTHOR_SAMPLE_ROW_MISSING", pointers)
            else:
                _item(items, "AUTHOR_SAMPLE_NAME_AMBIGUOUS",
                      [{"role": "geo_family_soft", "record": sample["accession"], "field": "title"},
                       {"role": "author_sample_table", "field": "BamName"}])
        elif not clean_author_link:
            _item(items, "AUTHOR_SAMPLE_NAME_PATIENT_CONFLICT",
                  [{"role": "geo_family_soft", "record": sample["accession"], "field": "title"},
                   {"role": "author_sample_table", "field": "PatientID versus BamName"}],
                  {"geo_patient": patient_id, "author_patient_label": author_patient})
        clinical_rows = clinical_matches.get(patient_id, [])
        clinical_row = clinical_rows[0] if len(clinical_rows) == 1 else None
        if visit == "Pre" and len(clinical_rows) != 1 and patient_id not in clinical_unknown_reported:
            _item(items, "CLINICAL_SOURCE_ROW_MISSING" if not clinical_rows else "CLINICAL_SOURCE_DUPLICATE_PATIENT",
                  [{"role": "author_clinical_table", "field": "PatientID", "patient": patient_id}])
            clinical_unknown_reported.add(patient_id)
        parsed_samples.append((sample, patient_id, visit, author_row if clean_author_link else None,
                               clinical_row if clean_author_link else None))
    for (patient_id, visit), count in sorted(patient_visits.items()):
        if count > 1:
            _item(items, "DUPLICATE_GEO_PATIENT_VISIT", [
                {"role": "geo_family_soft", "rule": "patient+visit", "visit": visit}],
                {"duplicate_record_count": count})
    on_treatment_count = sum(visit == "On" for _, _, visit, _, _ in parsed_samples)
    if on_treatment_count:
        _item(items, "ON_TREATMENT_WINDOW_UNRESOLVED", [
            {"role": "geo_family_soft", "field": visit_key}],
            {"source_label": "On", "specimen_count": on_treatment_count})
    # GEO titles and a unique, matching author sample row are the structural identity evidence.
    for patient_id in sorted({entry[1] for entry in parsed_samples}):
        linked = any(entry[1] == patient_id and entry[3] is not None
                     for entry in parsed_samples)
        locator = next((entry[0] for entry in parsed_samples if entry[1] == patient_id), None)
        if locator is None:
            continue
        source_values = [field_map["source_objects"]["geo_family_soft"]["locator"]]
        if linked:
            source_values.extend([
                field_map["source_objects"]["author_sample_table"]["locator"],
            ])
        patient_clinical_row = next((entry[4] for entry in parsed_samples
                                     if entry[1] == patient_id and entry[4] is not None), None)
        if linked and patient_clinical_row is not None:
            source_values.append(field_map["source_objects"]["author_clinical_table"]["locator"])
        if not linked:
            continue
        clinical_cohort = (_table_value(clinical_table, clinical_cohort_position, patient_clinical_row)
                           if isinstance(clinical_table, DelimitedTable) and patient_clinical_row is not None
                           else None)
        prior_ipilimumab = field_map.get("treatment", {}).get("prior_ipilimumab_by_cohort", {}).get(clinical_cohort)
        prior_ici = "YES" if prior_ipilimumab is True else "NO" if prior_ipilimumab is False else "UNKNOWN"
        tables["patient_registry"].append({
            "data_classification": "PRIVATE_PATIENT_LEVEL",
            "patient_uid": f"{study_id}:{patient_id}", "study_id": study_id,
            "source_patient_id": patient_id, "patient_identity_confidence": "VERIFIED" if linked else "UNRESOLVED",
            **({"cancer": field_map["cancer_type"]} if field_map.get("cancer_type") else {}),
            "prior_ici": prior_ici, "prior_radiotherapy": "UNKNOWN", "treatment_naive_status": "UNKNOWN",
            "inclusion_state": "CANDIDATE",
            "source_locators": [pointer for value in source_values for pointer in _locator(value)],
        })
    outcome_patients: set[str] = set()
    for sample, patient_id, visit, author_row, clinical_row in parsed_samples:
        accession, title = sample["accession"], sample["title"]
        patient_uid = f"{study_id}:{patient_id}"
        source_locator = f"sha256:{sources['geo_family_soft'].sha256}#sample={accession}" if "geo_family_soft" in sources else field_map["source_objects"]["geo_family_soft"]["locator"] + "#sample=" + accession
        source_pointer = _locator(source_locator)
        if author_row is None:
            continue
        specimen_uid = f"{study_id}:SPECIMEN:{accession}"
        clinical_locator = field_map["source_objects"]["author_clinical_table"]["locator"]
        aliases = [accession, title]
        source_name_field = compartment_cfg.get("source_name_field")
        source_name = sample.get(source_name_field) if isinstance(source_name_field, str) else None
        compartment_map = compartment_cfg.get("source_name_map", {})
        biological_compartment = (compartment_map.get(source_name.strip().lower(), "UNKNOWN")
                                  if isinstance(source_name, str) and isinstance(compartment_map, dict)
                                  else "UNKNOWN")
        tables["specimen_registry"].append({
            "data_classification": "PRIVATE_PATIENT_LEVEL",
            "specimen_uid": specimen_uid, "patient_uid": patient_uid, "raw_sample_aliases": aliases,
            "timing_raw_text": visit,
            "canonical_timing_category": "PRE_INDEX_BASELINE" if visit == "Pre" else "UNKNOWN",
            "tissue_type": "",
            "biological_compartment": biological_compartment,
            "scheduled_or_clinically_indicated": "UNKNOWN",
            "baseline_candidate_status": "YES" if visit == "Pre" else "NO",
            "longitudinal_pair_status": "UNKNOWN",
            "source_locators": source_pointer,
        })
        if clinical_row is None:
            continue
        bor = _table_value(clinical_table, clinical_bor_position, clinical_row) if isinstance(clinical_table, DelimitedTable) else None
        characteristics = {entry["key"]: entry["value"] for entry in sample["characteristics"]}
        geo_response = characteristics.get(field_map["geo"]["characteristics"]["response"])
        source_labels = field_map.get("labels", {}).get("source_of_record_bor", {})
        geo_labels = field_map.get("labels", {}).get("geo_response", {})
        if bor and geo_response and source_labels.get(bor) != geo_labels.get(geo_response):
            _item(items, "OUTCOME_LABEL_DISAGREEMENT", [
                {"role": "author_clinical_table", "record": patient_id, "field": "BOR"},
                {"role": "geo_family_soft", "record": accession, "field": "response"}],
                {"source_of_record_bor": bor, "corroborating_label": geo_response})
        sample_bor = (_table_value(sample_table, sample_cfg["response_positions"]["bor"], author_row)
                      if isinstance(sample_table, DelimitedTable) else None)
        if sample_bor and bor and sample_bor != bor:
            _item(items, "AUTHOR_SAMPLE_TABLE_CROSSCHECK_DISAGREEMENT", [
                {"role": "author_sample_table", "record": accession, "field": "BOR"},
                {"role": "author_clinical_table", "record": patient_id, "field": "BOR"}],
                {"author_sample_table_bor": sample_bor, "source_of_record_bor": bor})
        if visit == "Pre" and bor and patient_id not in outcome_patients:
            canonical_category = bor if bor in {"CR", "PR", "SD", "PD", "NE"} else "UNKNOWN"
            tables["clinical_outcome"].append({
                "data_classification": "PRIVATE_PATIENT_LEVEL",
                "outcome_id": f"{patient_uid}:BOR", "patient_uid": patient_uid,
                "raw_endpoint_label": bor, "endpoint_class": "TUMOUR_RESPONSE",
                "assessment_criteria": "", "best_overall_response": bor if bor in {"CR", "PR", "SD", "PD", "NE"} else "UNKNOWN",
                "canonical_category": canonical_category, "evaluability": "NOT_EVALUABLE" if bor == "NE" else "UNKNOWN",
                "mapping_rule_version": "field-map", "mapping_confidence": "UNRESOLVED",
                "discrepancy_status": "UNRESOLVED", "source_locators": _locator(clinical_locator),
            })
            outcome_patients.add(patient_id)
        for role, representation in field_map.get("measurement_representations", {}).items():
            if not isinstance(representation, dict):
                continue
            headers = parsed.get(role)
            source = sources.get(role)
            if not isinstance(headers, tuple) or source is None:
                continue
            sample_header = accession if accession in headers else title if title in headers else None
            if sample_header is None:
                continue
            source_obj_id = source_ids[role]
            tables["assay_registry"].append({
                "data_classification": "PRIVATE_PATIENT_LEVEL",
                "assay_uid": f"{study_id}:ASSAY:{role}:{accession}", "specimen_uid": specimen_uid,
                "source_sample_id": sample_header, "source_object_id": source_obj_id,
                "modality": "RNA_SEQ", "platform": representation.get("platform", ""), "measurement_unit": representation.get("unit", ""),
                "genome_build": representation.get("genome_build"),
                "feature_annotation": representation.get("annotation"),
                "transform": representation.get("transform"), "matrix_header": sample_header,
                "qc_status": "NOT_EVALUATED", "replicate_status": "UNKNOWN", "branch_suitability": [],
                "source_locators": _locator(f"sha256:{source.sha256}#column={sample_header}"),
            })
    return tables


def _known_items(field_map: dict[str, Any], items: list[dict[str, Any]], counts: dict[str, int],
                 parsed: dict[str, Any]) -> None:
    code = parsed.get("author_analysis_code")
    if isinstance(code, str):
        if re.search(r"(?i)PCA.{0,80}outlier|outlier.{0,80}PCA", code):
            _item(items, "PCA_OUTLIER_STATUS_UNRESOLVED", [
                {"role": "author_analysis_code", "field": "PCA outlier statement"}])
        exclusion_code = ""
        for line_number, line in enumerate(code.splitlines()):
            if re.search(r"(?i)exclude\s+4\s+samples", line):
                exclusion_code = "\n".join(code.splitlines()[line_number:line_number + 5])
                break
        excluded = set(re.findall(r"\bPt\d+_Pre\b", exclusion_code))
        if excluded:
            _item(items, "AUTHOR_EXCLUSION_POLICY_UNRESOLVED", [
                {"role": "author_analysis_code", "field": "explicit baseline exclusions",
                 "locator": field_map["source_objects"]["author_analysis_code"]["locator"],
                 "record": record} for record in sorted(excluded)],
                {"excluded_sample_count": len(excluded)})
    for cross_check in field_map.get("harmonized_cross_checks", []):
        observed: int | None = None
        resource_role = cross_check.get("sample_role")
        candidates = [resource_role] if resource_role else [
            role for role in parsed if role.startswith("cbioportal") and "sample" in role]
        for role in candidates:
            table = parsed.get(role)
            if isinstance(table, DelimitedTable):
                observed = len(table.rows)
                break
        if observed is None:
            continue
        expected = cross_check.get("expected_sample_count")
        # A matching cross-check is evidence, not a reviewer question. Surface only
        # a discrepancy that is present in the inspected source object counts.
        if observed == counts["geo_samples"]:
            continue
        _item(items, "HARMONIZED_SAMPLE_COUNT_CROSSCHECK", [
            {"role": role, "resource": cross_check["resource"], "use": "CROSS_CHECK_ONLY"}],
            {"geo_samples": counts["geo_samples"], "harmonized_samples": observed,
             "field_map_expected_samples": expected})


def run_ingest(cohort: str, branch: str, store_path: Path, output: Path, *,
               allow_external_out: bool = False) -> dict[str, Any]:
    output_path = validate_output_path(output, allow_external_out=allow_external_out)
    field_map_path = FIELD_MAP_ROOT / f"{cohort}.json"
    try:
        field_map = load_field_map(field_map_path)
    except FieldMapError as error:
        raise IngestError(str(error)) from None
    if field_map.get("status") == "PARKED":
        raise IngestError("Cohort is PARKED: " + field_map["parked_reason"])
    if branch != field_map["branch_id"]:
        raise IngestError("COHORT_BRANCH_MISMATCH")
    items: list[dict[str, Any]] = []
    sources: dict[str, SourceObject] = {}
    parsed: dict[str, Any] = {}
    source_hashes: dict[str, str | None] = {}
    for role, metadata in field_map["source_objects"].items():
        sha = metadata["sha256"]
        source_hashes[role] = sha
        if sha is None:
            _item(items, "SOURCE_OBJECT_HASH_UNPINNED", [{"role": role,
                  "locator": metadata["locator"], "version": metadata["version"]}])
            continue
        try:
            source = ContentAddressedStore(store_path).read(sha)
        except SourceObjectError as error:
            _item(items, str(error), [{"role": role, "sha256": sha,
                  "locator": metadata["locator"]}])
            continue
        sources[role] = source
        if role == "ncbi_annotation_grch38":
            continue
        try:
            representation = field_map.get("measurement_representations", {}).get(role, {})
            orientation = representation.get("orientation", "samples_as_columns") if isinstance(representation, dict) else "samples_as_columns"
            parsed[role] = _parse_source(source, {**metadata, "orientation": orientation})
        except (ValueError, KeyError, TypeError):
            _item(items, "SOURCE_OBJECT_PARSE_INVALID", [{"role": role, "sha256": sha,
                  "locator": source.locator}])
    records = build_canonical_records(parsed, sources, field_map, items)
    geo_samples = parsed.get("geo_family_soft")
    if "geo_ingest" in field_map:
        specimens = records["specimen_registry"]
        counts = {
            "geo_samples": len(geo_samples) if isinstance(geo_samples, list) else 0,
            "pre_samples": sum(row["baseline_candidate_status"] == "YES" for row in specimens),
            "on_samples": 0,
            "unique_patients": len(records["patient_registry"]),
            "baseline_samples_linked_to_patient": sum(row["baseline_candidate_status"] == "YES" for row in specimens),
        }
    else:
        title_matcher = re.compile(field_map["sample_identity"]["title_regex"])
        title_rows = [match for sample in (geo_samples if isinstance(geo_samples, list) else [])
                      if (match := title_matcher.match(sample["title"])) is not None]
        counts = {
            "geo_samples": len(geo_samples) if isinstance(geo_samples, list) else 0,
            "pre_samples": sum(match.group(field_map["sample_identity"]["visit_group"]) == "Pre" for match in title_rows),
            "on_samples": sum(match.group(field_map["sample_identity"]["visit_group"]) == "On" for match in title_rows),
            "unique_patients": len({match.group(field_map["sample_identity"]["patient_group"]) for match in title_rows}),
            "baseline_samples_linked_to_patient": sum(row.get("timing_raw_text") == "Pre" for row in records["specimen_registry"]),
        }
    _known_items(field_map, items, counts, parsed)
    records_config = {
        "study_ids": [row["study_id"] for row in records["study_registry"]],
        "source_hashes": {row["source_object_id"]: row["sha256"] for row in records["source_record"]},
        "source_roles": {role: _source_object_id(cohort, role)
                         for role in field_map["source_objects"]},
    }
    raw_worksheet = {"classification": "PRIVATE_PATIENT_LEVEL",
                     "status": "BLOCKED_UNKNOWN" if items else "READY", "items": items}
    packet: dict[str, Any] = {
        "classification": "PRIVATE_PATIENT_LEVEL", "branch_id": branch,
        "records": records,
        "config": {"registries": records_config,
                   "ingestion_validation": {
                       "sha256_verified_roles": sorted(sources),
                       "parsed_source_roles": sorted(parsed),
                       **({"endpoint_definition": field_map.get("decision_config", {}).get("endpoint", {}).get("source_binary_definition")}
                          if isinstance(field_map.get("decision_config"), dict) and field_map.get("geo_ingest", {}).get("endpoint_class") == "SOURCE_BINARY" else {}),
                       "adapter_by_role": {role: field_map["source_objects"][role]["format"]
                                           for role in parsed},
                   },
                   "admission": {"ingestion_worksheet": raw_worksheet,
                                 "worksheet_prefill": field_map.get("worksheet_prefill", {})}},
        "schema_hashes": SchemaStore().hashes,
        "dependencies": {},
    }
    stages = (build_registries, map_endpoints, validate_timing, validate_assays)
    stage_statuses: dict[str, str] = {}
    for stage in stages:
        result = stage(packet)
        stage_statuses[result["stage"]] = result["status"]
        packet["records"] = result["records"]
        if result["status"] != "READY":
            break
        packet["dependencies"][result["stage"]] = result
    output_path.mkdir(parents=True, exist_ok=True)
    from .worksheet import worksheet_status, write_worksheet
    worksheet = write_worksheet(packet, output_path / "worksheet.json",
                                allow_external_out=allow_external_out)
    review_status = worksheet_status(packet, worksheet)
    records_dir = output_path / "records"
    records_dir.mkdir(exist_ok=True)
    (records_dir / "ingestion_packet.json").write_text(
        json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (records_dir / "stage_statuses.json").write_text(
        json.dumps(stage_statuses, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    categories = dict(sorted(Counter(item["category"] for item in items).items()))
    summary = {
        "classification": "PRIVATE_PATIENT_LEVEL", "cohort": cohort, "branch_id": branch,
        "counts": counts, "worksheet_item_count": len(worksheet["items"]),
        "source_issue_count": len(items), "worksheet_status": review_status,
        "worksheet_categories": categories,
        "object_hashes": source_hashes, "stage_statuses": stage_statuses,
    }
    summary_text = ("# Ingestion summary\n\n" +
        f"- Cohort: `{cohort}`\n- Branch: `{branch}`\n" +
        f"- GEO samples: {counts['geo_samples']} (Pre {counts['pre_samples']}, On {counts['on_samples']})\n" +
        f"- Title-derived unique patients: {counts['unique_patients']}\n" +
        f"- Baseline samples linked to patients: {counts['baseline_samples_linked_to_patient']}\n" +
        f"- Reviewer worksheet status: `{review_status}`\n" +
        f"- Reviewer worksheet items: {len(worksheet['items'])} (source issues: {len(items)})\n\n## Worksheet categories\n\n" +
        ("\n".join(f"- `{category}`: {count}" for category, count in categories.items()) or "- None") +
        "\n\n## Source object hashes\n\n" +
        "\n".join(f"- `{role}`: `{sha or 'null'}`" for role, sha in sorted(source_hashes.items())) + "\n")
    (output_path / "SUMMARY.md").write_text(summary_text, encoding="utf-8")
    return {"packet": packet, "worksheet": worksheet, "worksheet_status": review_status,
            "summary": summary,
            "output": output_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-external-out", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_ingest(args.cohort, args.branch, args.store, args.out,
                            allow_external_out=args.allow_external_out)
    except IngestError as error:
        parser.error(str(error))
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
