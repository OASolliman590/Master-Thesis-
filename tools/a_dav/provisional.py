"""Non-admissible structural previews of unsigned source proposals."""
from __future__ import annotations

from typing import Any


def add_v3_blocker_item(packet: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    import copy
    result = copy.deepcopy(packet)
    check = receipt.get('checks', {}).get('primary', {})
    if check.get('status') == 'BLOCKED':
        items = result.setdefault('config', {}).setdefault('admission', {}).setdefault('ingestion_worksheet', [])
        if isinstance(items, dict):
            items = items['items']
        items.append({'category':'V3_REVIEW_REQUIRED','status':'BLOCKED_UNKNOWN',
                      'evidence_pointers':[{'role':'V3','sha256':receipt.get('source_sha256', {}).get('primary')}],
                      'context':{'reasons':check.get('reasons', [])}})
    return result


def v3_limitations(receipt: dict[str, Any]) -> dict[str, str]:
    primary = receipt.get('checks', {}).get('primary', {})
    return {key: primary[key] for key in ('processing_limitation', 'processing_acceptance_evidence')
            if isinstance(primary.get(key), str)}


def add_v3_exclusion_item(packet: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """Carry object-derived excluded feature rows into the unsigned worksheet."""
    import copy
    result = copy.deepcopy(packet)
    evidence = receipt.get('checks', {}).get('primary', {}).get('object_derived_evidence', {})
    rows, fact = evidence.get('excluded_rows', []), evidence.get('excluded_rows_evidence', {})
    if rows and fact.get('evidence_type') == 'DERIVED_FROM_OBJECT' and fact.get('rule') == 'NONSTANDARD_ROWS_EXCLUDED':
        items = result['config']['admission']['ingestion_worksheet']
        if isinstance(items, dict):
            items = items['items']
        items.append({'category':'FEATURE_ROWS_EXCLUDED','status':'BLOCKED_UNKNOWN',
                      'evidence_pointers':[{'rule':'NONSTANDARD_ROWS_EXCLUDED','sha256':fact['source_sha256']}],
                      'context':{'count':len(rows),'excluded_rows':copy.deepcopy(rows),
                                 'evidence_type':'DERIVED_FROM_OBJECT','rule':'NONSTANDARD_ROWS_EXCLUDED'}})
    return result


def cbio_preview_blockers(field_map: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    """Keep an unsigned cBioPortal preview blocked until its role and V3 are settled."""
    reasons: list[str] = []
    role = field_map.get('decision_config', {}).get('preview', {}).get('split_policy')
    if field_map.get('decision_config', {}).get('preview', {}).get('author_endpoint_join') == 'UNRESOLVED':
        reasons.append('AUTHOR_ENDPOINT_JOIN_UNRESOLVED')
    if field_map.get('decision_config', {}).get('representation_restrictions', {}).get('development_only') and role != 'DEVELOPMENT':
        reasons.append('DEVELOPMENT_ONLY_REPRESENTATION')
    if role not in {'DEVELOPMENT', 'FINAL_TEST'}:
        reasons.append('SPLIT_NOT_FROZEN')
    check = receipt.get('checks', {}).get('primary', {})
    if check.get('status') != 'PASS':
        reasons.extend('V3_BLOCKED:'+str(reason) for reason in check.get('reasons', ['V3_NOT_PASSED']))
    return reasons


def preview_split_role(packet: dict[str, Any], field_map: dict[str, Any]) -> str:
    role = packet.get('config', {}).get('split', {}).get('policy', {}).get('permanent_role')
    if role is None and ('geo_ingest' in field_map or 'cbio_ingest' in field_map):
        role = field_map.get('decision_config', {}).get('preview', {}).get('split_policy')
    if not isinstance(role, str) or not role or role == 'UNKNOWN':
        raise ValueError('SPLIT_NOT_FROZEN')
    return role


def provisional_patient_rows(records: dict[str, Any], source_id: str, role: str, *,
                             nonbaseline_visit_values: list[str] | None = None,
                             exclude_without_assay: bool = False) -> dict[str, Any]:
    """Build a provisional patient view; fail on unresolved selection or endpoint joins."""
    if role == 'UNKNOWN' or not role:
        raise ValueError('SPLIT_NOT_FROZEN')
    rows = []
    not_applicable = 0
    seen: set[str] = set()
    for patient in records.get('patient_registry', []):
        uid = patient['patient_uid']
        if uid in seen:
            raise ValueError('MATRIX_GRAIN_DUPLICATE')
        seen.add(uid)
        patient_specimens = [s for s in records.get('specimen_registry', []) if s['patient_uid'] == uid]
        if (nonbaseline_visit_values and patient_specimens and
                all(s.get('timing_raw_text') in nonbaseline_visit_values for s in patient_specimens)):
            not_applicable += 1
            continue
        specimens = [s for s in patient_specimens if s['patient_uid'] == uid
                     and s.get('canonical_timing_category') == 'PRE_INDEX_BASELINE'
                     and s.get('biological_compartment') == 'TUMOUR'
                     and s.get('baseline_candidate_status') == 'YES']
        assays = [(s, a) for s in specimens for a in records.get('assay_registry', [])
                  if a['specimen_uid'] == s['specimen_uid'] and a.get('source_object_id') == source_id]
        if exclude_without_assay and len(specimens) == 1 and not assays:
            not_applicable += 1
            continue
        if len(assays) != 1:
            raise ValueError('BASELINE_SELECTION_AMBIGUOUS')
        outcomes = [o for o in records.get('clinical_outcome', []) if o['patient_uid'] == uid]
        episodes = [e for e in records.get('treatment_episode', []) if e['patient_uid'] == uid]
        classes = [o.get('endpoint_class') for o in outcomes]
        if len(classes) != len(set(classes)) or len(episodes) != 1:
            raise ValueError('UNRESOLVED_IDENTIFIER')
        specimen, assay = assays[0]
        def evaluability(outcome: dict[str, Any]) -> str:
            status = outcome.get('evaluability', 'UNKNOWN')
            category = outcome.get('canonical_category'); endpoint_class = outcome.get('endpoint_class')
            raw = outcome.get('raw_endpoint_label')
            if endpoint_class in {'TUMOUR_RESPONSE', 'SOURCE_BINARY'}:
                if not isinstance(raw, str) or not raw.strip() or category in {None, 'UNKNOWN', 'UNK'}:
                    return 'UNKNOWN'
                if category == 'NE':
                    return 'NOT_EVALUABLE'
                if ((endpoint_class == 'TUMOUR_RESPONSE' and category in {'CR', 'PR', 'SD', 'PD'}) or
                    (endpoint_class == 'SOURCE_BINARY' and category in {'SOURCE_POSITIVE', 'SOURCE_NEGATIVE'})):
                    return 'EVALUABLE'
                return 'UNKNOWN'
            return str(status)
        outcome = next((o for o in outcomes if o.get('endpoint_class') == 'TUMOUR_RESPONSE'),
                       outcomes[0] if outcomes else {})
        status = evaluability(outcome)
        included = status == 'EVALUABLE' and role != 'EXCLUDED'
        result_row = {'patient_uid': uid, 'study_id': patient['study_id'],
                     'specimen_uid': specimen['specimen_uid'], 'assay_uid': assay['assay_uid'],
                     'expression_column': assay['matrix_header'], 'raw_response': outcome.get('raw_endpoint_label'),
                     'canonical_category': outcome.get('canonical_category'), 'endpoint_evaluability': status,
                     'inclusion_status': 'INCLUDED' if included else 'EXCLUDED',
                     'exclusion_reason': None if included else 'ENDPOINT_NOT_EVALUABLE',
                     'split_role': role, 'prior_ici': episodes[0].get('prior_ici', 'UNKNOWN'),
                     'flags': []}
        if len(outcomes) > 1:
            result_row['endpoint_evaluability_by_class'] = {o['endpoint_class']: evaluability(o) for o in outcomes}
        rows.append(result_row)
    return {'status': 'PROVISIONAL', 'admission_status': 'PROVISIONAL_PENDING_SIGNATURE',
            'releasable': False, 'rows': rows, 'not_applicable_patients': not_applicable}


def apply_historical_flags(rows: list[dict[str, Any]], records: dict[str, Any],
                           items: list[dict[str, Any]], *, outlier_source_id: str,
                           patient_regex: str | None = None, patient_group: int = 1) -> None:
    """Annotate source-evidenced historical exclusions without changing membership."""
    exclusions = {pointer['record'] for item in items
                  if item.get('category') == 'AUTHOR_EXCLUSION_POLICY_UNRESOLVED'
                  for pointer in item.get('evidence_pointers', [])
                  if isinstance(pointer, dict) and isinstance(pointer.get('record'), str)}
    import re
    exclusion_patients = {match.group(patient_group) for value in exclusions
                          if patient_regex and (match := re.match(patient_regex, value))}
    patients = {row['patient_uid']: row for row in records.get('patient_registry', [])}
    specimens: dict[str, set[str]] = {}
    for specimen in records.get('specimen_registry', []):
        specimens.setdefault(specimen['patient_uid'], set()).update(specimen.get('raw_sample_aliases', []))
    for row in rows:
        patient = patients[row['patient_uid']]
        if patient.get('source_patient_id') == outlier_source_id:
            row['flags'].append('PAPER_PCA_OUTLIER')
        if (specimens.get(row['patient_uid'], set()) & exclusions or
                patient.get('source_patient_id') in exclusion_patients):
            row['flags'].append('AUTHOR_SCRIPT_EXCLUSION')


def apply_declared_historical_flags(rows: list[dict[str, Any]], packet: dict[str, Any],
                                    field_map: dict[str, Any], policy: dict[str, Any]) -> None:
    """Apply a declared historical flag, if this cohort has such evidence."""
    import re
    from pathlib import Path
    evidence = policy.get('pca_flag_evidence')
    if evidence is None and ('geo_ingest' in field_map or 'cbio_ingest' in field_map):
        return
    if not isinstance(evidence, dict):
        raise ValueError('HISTORICAL_FLAG_EVIDENCE_MISSING')
    document = Path(evidence['document'])
    if document.is_absolute() or '..' in document.parts:
        raise ValueError('HISTORICAL_FLAG_EVIDENCE_MISSING')
    found = re.findall(evidence['patient_id_regex'], document.read_text(encoding='utf-8'), re.IGNORECASE)
    if len(found) != 1 or not isinstance(found[0], str):
        raise ValueError('HISTORICAL_FLAG_EVIDENCE_MISSING')
    items = packet['config']['admission'].get('ingestion_worksheet', [])
    if isinstance(items, dict):
        items = items.get('items', [])
    identity = field_map['sample_identity']
    apply_historical_flags(rows, packet['records'], items, outlier_source_id=found[0],
                           patient_regex=identity['title_regex'], patient_group=identity['patient_group'])

def write_provisional_products(rows: list[dict[str, Any]], store: Any, source_hash: str, output: Any, *,
                               delimiter: str, compressed: bool,
                               orientation: str = "samples_as_columns",
                               source_format: str = "MATRIX_HEADER_CSV",
                               missing_policy: str = "BLOCK",
                               excluded_feature_rows: list[dict[str, Any]] | None = None,
                               auxiliary_columns: list[dict[str, Any]] | None = None,
                               allow_external_out: bool = False) -> dict[str, Any]:
    """Write a non-releasable preview with explicit pending admission checks."""
    import csv
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from .expression_materialization import materialize_expression
    from .ingest import validate_output_path

    folder = validate_output_path(Path(output), allow_external_out=allow_external_out)
    folder.mkdir(parents=True, exist_ok=False)
    expression = materialize_expression(Path(store), source_hash, rows, folder / 'expression.provisional.tsv',
                                        delimiter=delimiter, compressed=compressed, orientation=orientation, source_format=source_format,
                                        missing_policy=missing_policy, auxiliary_columns=auxiliary_columns,
                                        excluded_feature_rows=excluded_feature_rows,
                                        allow_external_out=allow_external_out)
    names = ['patient_uid', 'study_id', 'specimen_uid', 'assay_uid', 'expression_column', 'raw_response',
             'canonical_category', 'endpoint_evaluability', 'inclusion_status', 'exclusion_reason',
             'split_role', 'prior_ici', 'flags']
    with (folder / 'patients.provisional.tsv').open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=names, delimiter='\t', extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, 'flags': '|'.join(row.get('flags', []))})
    import hashlib
    expression['patient_table_sha256'] = hashlib.sha256((folder / 'patients.provisional.tsv').read_bytes()).hexdigest()
    evaluability = {state: sum(row.get('endpoint_evaluability') == state for row in rows)
                    for state in ('EVALUABLE', 'NOT_EVALUABLE', 'UNKNOWN')}
    counts = {'gene_count': expression['gene_count'], 'expression_patient_count': expression['patient_count'],
              'retained_patient_count': len(rows), 'evaluability': evaluability,
              'specimen_count':len({r['specimen_uid'] for r in rows if r.get('specimen_uid')}),
              'assay_count':len({r['assay_uid'] for r in rows if r.get('assay_uid')}),
              'missing_cells': expression['missing_count'],
              'excluded_missing_gene_count': expression['excluded_missing_gene_count'],
              'excluded_feature_row_count': expression['excluded_feature_row_count'],
              'paper_pca_outlier_flags': sum('PAPER_PCA_OUTLIER' in row.get('flags', []) for row in rows),
              'author_script_exclusion_flags': sum('AUTHOR_SCRIPT_EXCLUSION' in row.get('flags', []) for row in rows)}
    checks = {'MATRIX_GRAIN_DUPLICATE': {'count': len(rows) - len({row['patient_uid'] for row in rows})},
              'UNRESOLVED_IDENTIFIER': {'status': 'NOT_RUN', 'count': None}, 'UNADMITTED_SOURCE': {'count': len(rows)},
              'BASELINE_SELECTION_AMBIGUOUS': {'status': 'NOT_RUN', 'count': None},
              'ENDPOINT_NOT_EVALUABLE': {'count': evaluability['NOT_EVALUABLE'] + evaluability['UNKNOWN']},
              'ASSAY_UNSUPPORTED': {'status': 'NOT_RUN', 'count': None}, 'FEATURE_COVERAGE_FAILED': {'status': 'NOT_RUN', 'count': None},
              'SPLIT_NOT_FROZEN': {'count': len(rows)}, 'HASH_OR_VERSION_MISMATCH': {'count': 0}}
    result = {'status':'PROVISIONAL', 'admission_status':'PROVISIONAL_PENDING_SIGNATURE',
              'releasable':False, 'counts':counts, 'checks':checks,
              'build_utc':datetime.now(timezone.utc).isoformat(), 'hashes':expression}
    (folder / 'PROVISIONAL.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


def provisional_matrix_record(result: dict[str, Any], worksheet: dict[str, Any], *, branch: str,
                              matrix_version: str, split_version: str) -> dict[str, Any]:
    """Describe a preview without creating a schema-valid admission or release receipt."""
    import hashlib
    from pathlib import Path
    from .core import digest
    counts = result['counts']
    code_hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                   for name in ('provisional.py', 'expression_materialization.py')}
    return {'status':'PROVISIONAL','test_status':'NOT_RUN','validation_status':'PROVISIONAL_PENDING_SIGNATURE',
            'releasable':False,'matrix_id':'provisional-baseline-expression','branch_id':branch,
            'schema_version':'1.1.0','build_version':matrix_version,'split_version':split_version,
            'source_admission_receipt_ids':[], 'patient_count':counts['retained_patient_count'],
            'specimen_count':counts.get('specimen_count'),'assay_count':counts.get('assay_count'),
            'class_counts':counts['evaluability'],'timepoint_counts':{'PRE_INDEX_BASELINE':counts['retained_patient_count']},
            'excluded_records':{'ENDPOINT_NOT_EVALUABLE':counts['evaluability']['NOT_EVALUABLE']},
            'duplicate_checks':result['checks'].get('MATRIX_GRAIN_DUPLICATE'),
            'overlap_checks':{'status':'PROVISIONAL_PENDING_SIGNATURE'},
            'feature_coverage':{'gene_count':counts['gene_count']},
            'missingness':{'cells':counts['missing_cells'], 'excluded_missing_gene_count':counts.get('excluded_missing_gene_count', 0)},
            'input_hashes':[result['hashes']['source_sha256']],
            'output_hash':digest({'expression':result['hashes']['output_sha256'],
                                  'patients':result['hashes'].get('patient_table_sha256')}),
            'code_hash':digest(code_hashes),'code_hashes':code_hashes,
            'config_hash':worksheet['context']['config_hash'], 'worksheet_context_hash':worksheet['context_hash'],
            'build_utc':result['build_utc']}


def run_provisional(packet: dict[str, Any], field_map: dict[str, Any], store: Any, output: Any, *,
                    worksheet: dict[str, Any] | None = None,
                    v3_receipt: dict[str, Any] | None = None,
                    allow_external_out: bool = False) -> dict[str, Any]:
    """Run real stages and a separate non-admissible preview without signing anything."""
    if field_map.get('decision_config', {}).get('family_protection', {}).get('status') == 'UNTOUCHED_FINAL_TEST':
        raise ValueError('UNTOUCHED_FINAL_TEST_PROTECTED')
    if field_map.get('decision_config', {}).get('representation_restrictions', {}).get('development_only'):
        declared = field_map.get('decision_config', {}).get('preview', {}).get('split_policy')
        packet_role = packet.get('config', {}).get('split', {}).get('policy', {}).get('permanent_role')
        if declared != 'DEVELOPMENT' or packet_role not in (None, 'DEVELOPMENT'):
            raise ValueError('DEVELOPMENT_ONLY_REPRESENTATION')
    import copy
    import json
    import re
    from pathlib import Path
    from .admission import evaluate_admission
    from .assays import validate_assays
    from .core import SchemaStore
    from .endpoints import map_endpoints
    from .exposure import validate_exposure
    from .matrices import build_baseline
    from .overlap import validate_overlap
    from .registries import build_registries
    from .release import validate_split
    from .timing import validate_timing
    from .worksheet import build_worksheet

    if worksheet is not None and ('signature' in worksheet or worksheet.get('review_status') == 'SIGNED'):
        raise ValueError('PROVISIONAL_WORKSHEET_MUST_BE_UNSIGNED')
    unsigned = build_worksheet(packet)
    if worksheet is not None and worksheet.get('context_hash') != unsigned['context_hash']:
        raise ValueError('WORKSHEET_CONTEXT_MISMATCH')
    current = copy.deepcopy(packet)
    current['dependencies'] = {}
    schemas = SchemaStore()
    statuses = []
    stages = (build_registries, map_endpoints, validate_timing, validate_assays, validate_overlap, validate_exposure)
    for stage in stages:
        result = stage(current, schemas=schemas)
        statuses.append({'stage':result['stage'],'status':result['status'],'reasons':result['reasons']})
        if result['status'] == 'READY':
            current['records'] = result['records']
            current['dependencies'][result['stage']] = result
    admission = evaluate_admission(current, reviewer_worksheet=unsigned, worksheet_context_packet=packet,
                                   schemas=schemas)
    statuses.append({'stage':'admission','status':'PROVISIONAL_PENDING_SIGNATURE','reasons':admission['reasons']})
    for stage in (validate_split, build_baseline):
        result = stage(current, schemas=schemas)
        statuses.append({'stage':result['stage'],'status':result['status'],'reasons':result['reasons']})
    matrices = packet['config']['assays']['matrices']
    if len(matrices) != 1:
        raise ValueError('ASSAY_UNSUPPORTED')
    matrix = matrices[0]
    source_hash = matrix['source_sha256']
    source_id = matrix['source_object_id']
    matching_roles = [role for role, obj in field_map['source_objects'].items() if obj.get('sha256') == source_hash]
    if len(matching_roles) != 1:
        raise ValueError('HASH_OR_VERSION_MISMATCH')
    role = matching_roles[0]
    role_name = preview_split_role(packet, field_map)
    result_rows = provisional_patient_rows(packet['records'], source_id, role_name,
        nonbaseline_visit_values=(field_map.get('geo_ingest', {}).get('nonbaseline_visit_values') or
                                  (field_map.get('cbio_ingest', {}).get('nonbaseline_values', []) +
                                   field_map.get('cbio_ingest', {}).get('excluded_visit_values', []))),
        exclude_without_assay=field_map.get('decision_config', {}).get('preview', {}).get('exclude_without_assay', False))
    policy = packet['config'].get('materialization', {})
    apply_declared_historical_flags(result_rows['rows'], packet, field_map, policy)
    folder = Path(output)
    result = write_provisional_products(result_rows['rows'], store, source_hash, folder / 'table',
                                        delimiter=field_map['v3']['delimiters'][role],
                                        compressed=field_map['v3']['compressed'][role],
                                        orientation=field_map.get('measurement_representations', {}).get(role, {}).get('orientation', 'samples_as_columns'),
                                        source_format=field_map['source_objects'][role].get('format', 'MATRIX_HEADER_CSV'),
                                        missing_policy=field_map['measurement_representations'][role].get('missing_policy', 'BLOCK'),
                                        excluded_feature_rows=(v3_receipt or {}).get('checks', {}).get('primary', {}).get('object_derived_evidence', {}).get('excluded_rows'),
                                        auxiliary_columns=field_map['measurement_representations'][role].get('auxiliary_columns'),
                                        allow_external_out=allow_external_out)
    result['stages'] = statuses
    if v3_receipt is not None:
        result['representation_limitations'] = v3_limitations(v3_receipt)
        result['checks'] = audit_provisional_contract(result_rows['rows'], packet['records'], result,
                                                       v3_receipt, field_map)
        record = provisional_matrix_record(result, unsigned, branch=packet['branch_id'],
                                           matrix_version=policy.get('version', 'PROVISIONAL'),
                                           split_version=packet['config'].get('split', {}).get('version', 'PROVISIONAL_PENDING_CONFIRMATION'))
        record['representation_limitations'] = v3_limitations(v3_receipt)
        (folder / 'provisional_matrix_record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    (folder / 'PROVISIONAL.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    (folder / 'reviewer_worksheet.unsigned.json').write_text(json.dumps(unsigned, indent=2, sort_keys=True) + '\n')
    return result


def audit_provisional_contract(rows: list[dict[str, Any]], records: dict[str, Any],
                               report: dict[str, Any], v3: dict[str, Any],
                               field_map: dict[str, Any]) -> dict[str, Any]:
    """Count structural failures while retaining signature-dependent checks as pending."""
    patients = {r['patient_uid'] for r in records.get('patient_registry', [])}
    specimens = {r['specimen_uid']:r for r in records.get('specimen_registry', [])}
    assays = {r['assay_uid']:r for r in records.get('assay_registry', [])}
    source_sha = report['hashes']['source_sha256']
    sources = [r for r in records.get('source_record', []) if r.get('sha256') == source_sha]
    source_id = sources[0]['source_object_id'] if len(sources) == 1 else None
    unresolved = 0
    ambiguous = 0
    for row in rows:
        uid = row.get('patient_uid')
        specimen = specimens.get(row.get('specimen_uid'), {})
        assay = assays.get(row.get('assay_uid'), {})
        if (uid not in patients or specimen.get('patient_uid') != uid or
                assay.get('specimen_uid') != row.get('specimen_uid') or
                assay.get('source_object_id') != source_id or
                assay.get('matrix_header') != row.get('expression_column')):
            unresolved += 1
        candidates = [s for s in specimens.values() if s.get('patient_uid') == uid
                      and s.get('canonical_timing_category') == 'PRE_INDEX_BASELINE'
                      and s.get('biological_compartment') == 'TUMOUR'
                      and s.get('baseline_candidate_status') == 'YES']
        choices = [a for s in candidates for a in assays.values()
                   if a.get('specimen_uid') == s['specimen_uid'] and a.get('source_object_id') == source_id]
        if len(choices) != 1:
            ambiguous += 1
    role = v3.get('checks', {}).get('effective_primary')
    roles = field_map.get('v3', {}).get('source_object_roles', {})
    key = next((key for key, value in roles.items() if value == role), None)
    v3_rep = v3.get('checks', {}).get(key, {})
    hashes = v3.get('source_sha256', {})
    declared = field_map.get('source_objects', {}).get(role, {})
    hash_mismatch = int(len(sources) != 1 or hashes.get(key) != source_sha or declared.get('sha256') != source_sha)
    stage_assays_ready = any(s.get('stage') == 'assays' and s.get('status') == 'READY' for s in report.get('stages', []))
    unsuitable = int(not stage_assays_ready or v3_rep.get('status') != 'PASS')
    feature_counts = v3_rep.get('counts', {})
    representation = field_map.get('measurement_representations', {}).get(role, {})
    excluded = feature_counts.get('excluded_missing_features', 0)
    excluded_rows = feature_counts.get('excluded_feature_rows', 0)
    total = feature_counts.get('features')
    valid_exclusion = (type(total) is int and type(excluded) is int and 0 <= excluded <= total
                       and report['counts'].get('excluded_missing_gene_count', 0) == excluded
                       and report['counts'].get('excluded_feature_row_count', 0) == excluded_rows
                       and (excluded == 0 or representation.get('missing_policy') == 'EXCLUDE_FEATURE_IF_ANY_MISSING'))
    feature_error = int(v3_rep.get('checks', {}).get('feature_identity', {}).get('status') != 'PASS'
                        or not valid_exclusion or total - excluded - excluded_rows != report['counts']['gene_count']
                        or representation.get('feature_scope') != 'COMPLETE')
    patient_ids = [r.get('patient_uid') for r in rows]
    status = 'PROVISIONAL_STRUCTURAL_CHECK'
    return {'MATRIX_GRAIN_DUPLICATE':{'count':len(rows)-len(set(patient_ids)), 'status':status},
            'UNRESOLVED_IDENTIFIER':{'count':unresolved, 'status':status},
            'UNADMITTED_SOURCE':{'count':len(rows), 'status':'PENDING_SIGNATURE'},
            'BASELINE_SELECTION_AMBIGUOUS':{'count':ambiguous, 'status':status},
            'ENDPOINT_NOT_EVALUABLE':{'count':sum(r.get('endpoint_evaluability') != 'EVALUABLE' for r in rows), 'status':status},
            'ASSAY_UNSUPPORTED':{'count':unsuitable, 'status':status},
            'FEATURE_COVERAGE_FAILED':{'count':feature_error, 'status':status},
            'SPLIT_NOT_FROZEN':{'count':None, 'status':'PENDING_SIGNATURE'},
            'HASH_OR_VERSION_MISMATCH':{'count':hash_mismatch, 'status':status}}
