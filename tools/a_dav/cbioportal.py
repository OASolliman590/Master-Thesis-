"""Read pinned cBioPortal clinical and profile metadata without adjudicating identity."""
from __future__ import annotations

from typing import Any

from .delimited import read_delimited_table


def verified_author_links(author: dict[str, list[dict[str, str]]], patients: list[dict[str, str]],
                          samples: list[dict[str, str]]) -> dict[str, Any]:
    """Link unique, fully agreeing pairs only when both have documented RNA."""
    import re
    from collections import defaultdict
    keys: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for arm, prefix in (('mono', 'PD'), ('dual', 'iP')):
        for row in author.get(arm, []):
            n = row.get('Patient no.', '').strip()
            keys[(prefix, int(n) if n.isdigit() else -1)].append(row)
    source: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for patient in patients:
        match = re.fullmatch(r'(PD|iP)([0-9]+)', patient.get('PATIENT_ID', ''))
        if match:
            source[(match.group(1), int(match.group(2)))].append(patient)
    result: dict[str, Any] = {'links': {}, 'matched_linked': 0, 'matched_without_rna': 0,
        'unmatched_without_rna': 0, 'unmatched_with_rna': 0, 'rna_unknown': 0, 'ambiguous_or_disagree': 0}
    for key, rows in keys.items():
        candidates = source.get(key, [])
        if len(rows) != 1 or len(candidates) > 1 or key[1] < 0:
            result['ambiguous_or_disagree'] += len(rows)
            continue
        row = rows[0]; rna = row.get('RNA Sequencing', '').strip()
        if not rna:
            result['rna_unknown'] += 1
            continue
        if not candidates:
            result['unmatched_without_rna' if rna == '-' else 'unmatched_with_rna'] += 1
            continue
        if rna == '-':
            result['matched_without_rna'] += 1
            continue
        patient = candidates[0]; pid = patient.get('PATIENT_ID', '')
        sample_rows = [sample for sample in samples if sample.get('PATIENT_ID') == pid]
        check = verify_author_arm_number_join({'mono' if key[0] == 'PD' else 'dual': [row]}, [patient], sample_rows)
        if not check['adopted']:
            result['ambiguous_or_disagree'] += 1
            continue
        result['links'][pid] = row
        result['matched_linked'] += 1
    return result


def verify_author_arm_number_join(author: dict[str, list[dict[str, str]]],
                                  patients: list[dict[str, str]],
                                  samples: list[dict[str, str]]) -> dict[str, Any]:
    """Compare every proposed pair; return aggregates only and adopt nothing on conflict.

    PFS agrees within 0.5 months using 30.4375 days/month. Missing or conflicting
    values count as unresolved and prevent adoption.
    """
    import re
    from collections import defaultdict
    groups: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for arm, prefix in (('mono', 'PD'), ('dual', 'iP')):
        for row in author.get(arm, []):
            number = row.get('Patient no.', '').strip()
            if number.isdigit():
                groups[(prefix, int(number))].append(row)
            else:
                groups[(prefix, -1)].append(row)
    source: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    responses: dict[str, set[str]] = defaultdict(set)
    for row in patients:
        match = re.fullmatch(r'(PD|iP)([0-9]+)', row.get('PATIENT_ID', ''))
        if match:
            source[(match.group(1), int(match.group(2)))].append(row)
        else:
            source[('INVALID', -1)].append(row)
    for row in samples:
        responses[row.get('PATIENT_ID', '')].add(row.get('RESPONSE', '').strip())
    sex = {'F': 'female', 'M': 'male', 'Female': 'female', 'Male': 'male'}
    drug = {'Pembrolizumab': 'pembrolizumab', 'Pembro': 'pembrolizumab', 'Nivolumab': 'nivolumab',
            'Ipilimumab + Pembrolizumab': 'ipilimumab pembrolizumab',
            'Ipilimumab Pembrolizumab': 'ipilimumab pembrolizumab',
            'Ipilimumab + Nivolumab': 'ipilimumab nivolumab', 'Ipilimumab Nivolumab': 'ipilimumab nivolumab'}
    response = {'CR': 'CR', 'PR': 'PR', 'SD': 'SD', 'PD': 'PD', 'NE': 'NE',
                'Complete Response': 'CR', 'Partial Response': 'PR', 'Stable Disease': 'SD',
                'Progressive Disease': 'PD'}
    counts = {key: {'agree': 0, 'disagree': 0, 'unresolved': 0} for key in ('sex', 'age', 'drug', 'response', 'pfs')}
    matched = 0
    unmatched_author = sum(len(rows) for key, rows in groups.items() if key not in source)
    unmatched_cbio = sum(len(rows) for key, rows in source.items() if key not in groups)
    ambiguous = sum(len(groups[key]) + len(source[key]) for key in groups.keys() & source.keys()
                    if len(groups[key]) != 1 or len(source[key]) != 1 or key[1] < 0)
    for key in groups.keys() & source.keys():
        if len(groups[key]) != 1 or len(source[key]) != 1 or key[1] < 0:
            continue
        a, b = groups[key][0], source[key][0]
        matched += 1
        raw_responses = responses.get(b.get('PATIENT_ID', ''), set())
        vals = {
            'sex': (sex.get(a.get('Sex', '').strip()), sex.get(b.get('SEX', '').strip())),
            'drug': (drug.get(a.get('Treatment', '').strip()), drug.get(b.get('ICI_RX', '').strip())),
            'response': (response.get(a.get('Best RECIST response', '').strip()),
                         response.get(next(iter(raw_responses))) if len(raw_responses) == 1 else None),
        }
        for field, (left, right) in vals.items():
            outcome = 'unresolved' if left is None or right is None else 'agree' if left == right else 'disagree'
            counts[field][outcome] += 1
        for field, left, right, tolerance in (
                ('age', a.get('Age (Years)', ''), b.get('AGE_AT_DIAGNOSIS', ''), 0.0),
                ('pfs', a.get('Progression Free Survival (Days)', ''), b.get('PFS_MONTHS', ''), 0.5)):
            try:
                import math
                x, y = float(left), float(right)
                if not math.isfinite(x) or not math.isfinite(y) or x < 0 or y < 0:
                    raise ValueError
                if field == 'pfs':
                    x /= 30.4375
                outcome = 'agree' if abs(x - y) <= tolerance else 'disagree'
            except (ValueError, TypeError):
                outcome = 'unresolved'
            counts[field][outcome] += 1
    adopted = (matched > 0 and unmatched_author == unmatched_cbio == ambiguous == 0 and
               all(value['disagree'] == value['unresolved'] == 0 for value in counts.values()))
    return {'adopted': adopted, 'matched': matched, 'unmatched_author': unmatched_author,
            'unmatched_cbio': unmatched_cbio, 'ambiguous_rows': ambiguous, 'fields': counts,
            'pfs_days_per_month': 30.4375, 'pfs_tolerance_months': 0.5}


def clinical_benefit(response: str, pfs_days: str, progressed: str) -> str:
    """Map an author's clinical-benefit definition without inferring missing facts."""
    import math
    if response in {'CR', 'PR'}:
        return 'SOURCE_POSITIVE'
    if response == 'PD':
        return 'SOURCE_NEGATIVE'
    if response != 'SD':
        return 'UNKNOWN'
    try:
        days = float(pfs_days)
    except ValueError:
        return 'UNKNOWN'
    if not math.isfinite(days) or days < 0:
        return 'UNKNOWN'
    if days <= 182.5:
        return 'SOURCE_NEGATIVE'
    return 'SOURCE_POSITIVE' if progressed.strip().lower() == 'no' else 'UNKNOWN'


def author_outcomes(row: dict[str, str]) -> dict[str, str]:
    raw = row.get('Best RECIST response', '').strip()
    orr = raw if raw in {'CR', 'PR', 'SD', 'PD', 'NE'} else 'UNKNOWN'
    return {'orr': orr, 'clinical_benefit': clinical_benefit(
        orr, row.get('Progression Free Survival (Days)', ''), row.get('Progressed', ''))}


def apply_author_endpoint_records(tables: dict[str, list[dict[str, Any]]],
                                  links: dict[str, dict[str, str]], locators: dict[str, str]) -> None:
    """Keep ORR and clinical benefit as distinct source outcomes for verified links."""
    for patient in tables['patient_registry']:
        pid = patient.get('source_patient_id')
        if pid not in links or pid not in locators:
            continue
        row = links[pid]; categories = author_outcomes(row); uid = patient['patient_uid']
        outcome = next((x for x in tables['clinical_outcome'] if x['patient_uid'] == uid
                        and x.get('endpoint_class', 'TUMOUR_RESPONSE') == 'TUMOUR_RESPONSE'), None)
        if outcome is None:
            continue
        locator = [{'kind': 'source_object', 'value': locators[pid]}]
        outcome.update({'raw_endpoint_label': row.get('Best RECIST response', '').strip(),
                        'canonical_category': categories['orr'], 'best_overall_response': categories['orr'],
                        'assessment_criteria': 'RECIST 1.1', 'source_locators': locator})
        tables['clinical_outcome'].append({'data_classification': 'PRIVATE_PATIENT_LEVEL',
            'outcome_id': uid + ':CLINICAL_BENEFIT', 'patient_uid': uid,
            'raw_endpoint_label': ('RECIST=' + row.get('Best RECIST response', '').strip() +
                '; PFS_DAYS=' + row.get('Progression Free Survival (Days)', '').strip() +
                '; PROGRESSED=' + row.get('Progressed', '').strip()),
            'endpoint_class': 'SOURCE_BINARY', 'assessment_criteria': 'RECIST 1.1 clinical benefit',
            'best_overall_response': 'UNKNOWN', 'canonical_category': categories['clinical_benefit'],
            'evaluability': 'UNKNOWN', 'mapping_rule_version': 'field-map',
            'mapping_confidence': 'UNRESOLVED', 'discrepancy_status': 'UNRESOLVED', 'source_locators': locator})


def read_meta(raw: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.decode('utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition(':')
        key = key.strip()
        if not sep or not key or key in result:
            raise ValueError('CBIOPORTAL_META_INVALID')
        result[key] = value.strip()
    return result


def read_clinical(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode('utf-8-sig')
    data = ''.join(line for line in text.splitlines(keepends=True) if not line.startswith('#'))
    table = read_delimited_table(data.encode(), delimiter='\t')
    if len(set(table.headers)) != len(table.headers):
        raise ValueError('CBIOPORTAL_DUPLICATE_FIELD')
    return [dict(zip(table.headers, row)) for row in table.rows]


def read_inventory(raw: bytes, fields: list[str]) -> list[dict[str, str]]:
    """Project only the declared identity and timing columns for outcome-blind V3."""
    import csv
    import io
    text = raw.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(''.join(line for line in text.splitlines(keepends=True)
                                              if not line.startswith('#'))), delimiter='\t')
    if not reader.fieldnames or not set(fields) <= set(reader.fieldnames):
        raise ValueError('CBIOPORTAL_INVENTORY_FIELDS_MISSING')
    return [{field: row[field] for field in fields} for row in reader]


def read_workbook_inventory(path: Any, sheet_name: str, header_row: int,
                            fields: list[str]) -> list[dict[str, str]]:
    """Read only identity, visit and cohort fields from a named clinical sheet."""
    from .xlsx import iter_xlsx_sheet
    head_rows = iter_xlsx_sheet(path, sheet_name)
    for _ in range(header_row - 1):
        next(head_rows)
    header = next(head_rows)
    if any(header.count(field) != 1 for field in fields):
        raise ValueError('CBIOPORTAL_INVENTORY_FIELDS_MISSING')
    indexes = {field: header.index(field) for field in fields}
    rows = iter_xlsx_sheet(path, sheet_name, selected_columns={i + 1 for i in indexes.values()})
    for _ in range(header_row):
        next(rows)
    return [{field: row[index] if index < len(row) else '' for field, index in indexes.items()} for row in rows]


def crosscheck_by_patient(source: list[dict[str, str]], author: list[dict[str, str]],
                          patient_field: str, source_field: str, author_field: str) -> dict[str, int]:
    """Count exact source-label concordance without changing either source."""
    author_index: dict[str, list[dict[str, str]]] = {}
    for row in author:
        author_index.setdefault(row.get(patient_field, ''), []).append(row)
    result = {'matched_patients':0, 'agree':0, 'different':0, 'unmatched':0}
    for row in source:
        candidates = author_index.get(row.get(patient_field, ''), [])
        if len(candidates) != 1 or not row.get(patient_field):
            result['unmatched'] += 1
            continue
        result['matched_patients'] += 1
        result['agree' if row.get(source_field) == candidates[0].get(author_field) else 'different'] += 1
    return result


def response_corroboration(primary: list[dict[str, str]], corroborating: list[dict[str, str]],
                           patient_field: str, primary_field: str, corroborating_field: str) -> list[dict[str, str | None]]:
    """Preserve both source labels, using only a unique exact patient key."""
    index: dict[str, list[dict[str, str]]] = {}
    for row in corroborating:
        index.setdefault(row.get(patient_field, ''), []).append(row)
    output: list[dict[str, str | None]] = []
    for row in primary:
        pid = row.get(patient_field, '')
        candidates = index.get(pid, []) if pid else []
        output.append({'patient_id':pid, 'primary':row.get(primary_field),
                       'corroborating':candidates[0].get(corroborating_field) if len(candidates) == 1 else None})
    return output


def join_samples(patients: list[dict[str, str]], samples: list[dict[str, str]],
                 matrix_headers: list[str], config: dict[str, Any]) -> dict[str, Any]:
    patient_field, sample_field = config['patient_id'], config['sample_id']
    indexed: dict[str, list[dict[str, str]]] = {}
    for patient in patients:
        indexed.setdefault(patient.get(patient_field, ''), []).append(patient)
    matrix_counts = {header: matrix_headers.count(header) for header in set(matrix_headers)}
    sample_counts = {sample: sum(row.get(sample_field) == sample for row in samples)
                     for sample in {row.get(sample_field, '') for row in samples}}
    output, items = [], []
    unresolved_columns = sum(count for header, count in matrix_counts.items()
                             if count != 1 or sample_counts.get(header) != 1)
    if unresolved_columns:
        items.append({'category':'MATRIX_COLUMN_UNMAPPED_OR_AMBIGUOUS', 'context':{'column_count':unresolved_columns}})
    for sample in samples:
        sid, pid = sample.get(sample_field, ''), sample.get(patient_field, '')
        matches = indexed.get(pid, [])
        if not pid or len(matches) != 1 or not sid or sample_counts[sid] != 1:
            items.append({'category':'PATIENT_JOIN_UNRESOLVED'})
        patient = matches[0] if len(matches) == 1 else {}
        if matrix_counts.get(sid) != 1:
            items.append({'category':'EXPRESSION_SAMPLE_UNMATCHED'})
        def field(name: str) -> str:
            key = config.get(name)
            return sample.get(key, patient.get(key, '')) if isinstance(key, str) else ''
        visit = field('visit_field')
        output.append({'patient_id':pid,'sample_id':sid,'baseline':visit in config['baseline_values'],
                       'visit':visit,'response':field('response_field'),'drug':field('drug_field'),
                       'prior_ici':field('prior_ici_field'),'expression_linked':bool(pid and sid and len(matches) == 1 and sample_counts[sid] == 1 and matrix_counts.get(sid) == 1),
                       'identity_confidence':'UNRESOLVED'})
    return {'samples':output,'items':items}


def build_records(tables: dict[str, list[dict[str, Any]]], parsed: dict[str, Any],
                  sources: dict[str, Any], field_map: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """Create unreviewed source assertions from explicit clinical and matrix joins."""
    import hashlib
    cfg = field_map['cbio_ingest']; cohort = field_map['cohort']; study = 'STUDY:' + cohort
    patient_rows, sample_rows = parsed.get(cfg['patient_role']), parsed.get(cfg['sample_role'])
    header = parsed.get(cfg['matrix_role'])
    if not isinstance(patient_rows, list) or not isinstance(sample_rows, list) or not isinstance(header, tuple):
        items.append({'category':'CBIOPORTAL_SOURCE_UNAVAILABLE','evidence_pointers':[],'status':'BLOCKED_UNKNOWN'})
        return
    auxiliary = {item['index'] for item in field_map.get('measurement_representations', {}).get(cfg['matrix_role'], {}).get('auxiliary_columns', [])}
    matrix_headers = [value for index, value in enumerate(header) if index > 0 and index not in auxiliary]
    selection = cfg.get('cohort_filter')
    if isinstance(selection, dict):
        field, allowed = selection.get('field'), selection.get('allowed_values', [])
        if not isinstance(field, str) or not isinstance(allowed, list) or not allowed:
            raise ValueError('CBIOPORTAL_COHORT_FILTER_INVALID')
        identifiers = {row.get(cfg['patient_id']) for row in patient_rows}
        ambiguous = sum(1 for pid in identifiers if not pid or sum(row.get(cfg['patient_id']) == pid for row in patient_rows) != 1)
        if ambiguous:
            items.append({'category':'COHORT_FILTER_IDENTITY_AMBIGUOUS','status':'BLOCKED_UNKNOWN',
                          'evidence_pointers':[{'role':cfg['patient_role'],'field':field}], 'context':{'patient_count':ambiguous}})
        permitted = {pid for pid in identifiers if pid and len([row for row in patient_rows if row.get(cfg['patient_id']) == pid]) == 1
                     and all(row.get(field) in allowed for row in patient_rows if row.get(cfg['patient_id']) == pid)}
        excluded_samples = {row.get(cfg['sample_id']) for row in sample_rows if row.get(cfg['patient_id']) not in permitted}
        patient_rows = [row for row in patient_rows if row.get(field) in allowed]
        sample_rows = [row for row in sample_rows if row.get(cfg['patient_id']) in permitted]
        matrix_headers = [header for header in matrix_headers if header not in excluded_samples]
    if cfg.get('expression_samples_only'):
        axis = set(matrix_headers)
        excluded_count = sum(not row.get(cfg['sample_id']) or row.get(cfg['sample_id']) not in axis for row in sample_rows)
        if excluded_count:
            items.append({'category':'CLINICAL_WITHOUT_EXPRESSION_EXCLUDED','status':'BLOCKED_UNKNOWN',
                          'evidence_pointers':[{'role':cfg['sample_role']},{'role':cfg['matrix_role']}],
                          'context':{'sample_count':excluded_count}})
        sample_rows = [row for row in sample_rows if row.get(cfg['sample_id']) and row.get(cfg['sample_id']) in axis]
        selected_patients = {row.get(cfg['patient_id']) for row in sample_rows}
        patient_rows = [row for row in patient_rows if row.get(cfg['patient_id']) in selected_patients]
    joined = join_samples(patient_rows, sample_rows, matrix_headers, cfg)
    unmatched_samples = sum(item['category'] == 'EXPRESSION_SAMPLE_UNMATCHED' for item in joined['items'])
    for item in joined['items']:
        if item['category'] != 'EXPRESSION_SAMPLE_UNMATCHED':
            items.append({**item,'evidence_pointers':[{'role':cfg['sample_role']}], 'status':'BLOCKED_UNKNOWN'})
    if unmatched_samples:
        items.append({'category':'EXPRESSION_SAMPLE_UNMATCHED','evidence_pointers':[{'role':cfg['sample_role']}, {'role':cfg['matrix_role']}],
                      'status':'BLOCKED_UNKNOWN','context':{'sample_count':unmatched_samples}})
    source = field_map['source_objects'][cfg['sample_role']]['locator']
    patient_source = field_map['source_objects'][cfg['patient_role']]['locator']
    loc = [{'kind':'source_object','value':source}, {'kind':'source_object','value':patient_source}]
    response_source = (source if any(cfg['response_field'] in row for row in sample_rows)
                       else patient_source)
    response_role = cfg['sample_role'] if response_source == source else cfg['patient_role']
    response_loc = [{'kind':'source_object','value':response_source}]
    grouped: dict[str, list[dict[str, Any]]] = {}
    unknown_responses = 0
    unknown_timing = 0
    for sample in joined['samples']:
        if sample['patient_id']:
            grouped.setdefault(sample['patient_id'], []).append(sample)
    for pid, samples in grouped.items():
        uid=study+':PATIENT:'+hashlib.sha256(pid.encode()).hexdigest()
        baseline=[x for x in samples if x['baseline']]
        prior_values={cfg.get('prior_ici_map', {}).get(x['prior_ici'], 'UNKNOWN') for x in samples}
        prior=next(iter(prior_values)) if len(prior_values)==1 else 'UNKNOWN'
        tables['patient_registry'].append({'data_classification':'PRIVATE_PATIENT_LEVEL','patient_uid':uid,
            'study_id':study,'source_patient_id':pid,'patient_identity_confidence':'UNRESOLVED','prior_ici':prior,
            'treatment_naive_status':'UNKNOWN','inclusion_state':'CANDIDATE','source_locators':loc})
        if len(baseline)>1:
            items.append({'category':'BASELINE_SAMPLE_TIE_UNRESOLVED','status':'BLOCKED_UNKNOWN','evidence_pointers':[{'role':cfg['sample_role']}]})
        for sample in samples:
            sid=sample['sample_id']; sp=study+':SPECIMEN:'+hashlib.sha256(sid.encode()).hexdigest()
            is_pre=sample['baseline']; visit=sample['visit']
            excluded_visits = cfg.get('nonbaseline_values', []) + cfg.get('excluded_visit_values', [])
            if not is_pre and visit not in excluded_visits:
                unknown_timing += 1
            tables['specimen_registry'].append({'data_classification':'PRIVATE_PATIENT_LEVEL','specimen_uid':sp,
                'patient_uid':uid,'raw_sample_aliases':[sid], 'timing_raw_text':visit,
                'canonical_timing_category':'PRE_INDEX_BASELINE' if is_pre else 'UNKNOWN',
                'biological_compartment':'TUMOUR','baseline_candidate_status':'YES' if is_pre and len(baseline)==1 else 'NO' if visit in excluded_visits else 'UNKNOWN',
                'longitudinal_pair_status':'UNKNOWN','source_locators':loc})
            role=cfg['matrix_role'];rep=field_map.get('measurement_representations',{}).get(role,{})
            if sample['expression_linked'] and role in sources:
                tables['assay_registry'].append({'data_classification':'PRIVATE_PATIENT_LEVEL',
                    'assay_uid':study+':ASSAY:'+hashlib.sha256(sid.encode()).hexdigest(), 'specimen_uid':sp,
                    'source_sample_id':sid,'source_object_id':f'SOURCE:{cohort}:{role}','modality':'RNA_SEQ',
                    'platform':rep.get('platform','UNKNOWN'),'measurement_unit':rep.get('unit','UNKNOWN'),
                    'genome_build':rep.get('genome_build'),'feature_annotation':rep.get('annotation'),
                    'transform':rep.get('transform'),'matrix_header':sid,'qc_status':'NOT_EVALUATED',
                    'replicate_status':'UNKNOWN','branch_suitability':[], 'source_locators':[{'kind':'source_object','value':'sha256:'+sources[role].sha256}]})
        endpoint_samples = samples if cfg.get('outcomes_without_baseline') else baseline
        raw_responses={x['response'] for x in endpoint_samples if x['response']}
        if len(raw_responses)==1:
            raw=next(iter(raw_responses));category=cfg['response_map'].get(raw,'UNKNOWN')
            if category=='UNKNOWN':
                unknown_responses += 1
            tables['clinical_outcome'].append({'data_classification':'PRIVATE_PATIENT_LEVEL','outcome_id':uid+':BOR',
                'patient_uid':uid,'raw_endpoint_label':raw,'endpoint_class':'TUMOUR_RESPONSE','assessment_criteria':'UNKNOWN',
                'best_overall_response':category if category in {'CR','PR','SD','PD','NE'} else 'UNKNOWN',
                'canonical_category':category,'evaluability':'UNKNOWN','mapping_rule_version':'field-map',
                'mapping_confidence':'UNRESOLVED','discrepancy_status':'UNRESOLVED','source_locators':response_loc})
        elif endpoint_samples:
            items.append({'category':'ORR_RESPONSE_UNRESOLVED','status':'BLOCKED_UNKNOWN','evidence_pointers':[{'role':cfg['sample_role']}]})
        secondary = cfg.get('secondary_outcome')
        if isinstance(secondary, dict) and (baseline or cfg.get('outcomes_without_baseline')):
            field = secondary['field']
            source_rows = [row for row in patient_rows if row.get(cfg['patient_id']) == pid]
            secondary_role, secondary_source = cfg['patient_role'], patient_source
            if not source_rows or field not in source_rows[0]:
                source_rows = [row for row in sample_rows if row.get(cfg['patient_id']) == pid]
                secondary_role, secondary_source = cfg['sample_role'], source
            values = {row.get(field, '') for row in source_rows if row.get(field, '')}
            if len(values) == 1:
                raw = next(iter(values)); category = secondary.get('response_map', {}).get(raw, 'UNKNOWN')
                tables['clinical_outcome'].append({'data_classification':'PRIVATE_PATIENT_LEVEL','outcome_id':uid+':SOURCE_BINARY',
                    'patient_uid':uid,'raw_endpoint_label':raw,'endpoint_class':'SOURCE_BINARY','assessment_criteria':'UNKNOWN',
                    'best_overall_response':'UNKNOWN','canonical_category':category,'evaluability':'UNKNOWN',
                    'mapping_rule_version':'field-map','mapping_confidence':'UNRESOLVED','discrepancy_status':'UNRESOLVED',
                    'source_locators':[{'kind':'source_object','value':secondary_source}]})
            else:
                items.append({'category':'SECONDARY_ENDPOINT_UNRESOLVED','status':'BLOCKED_UNKNOWN',
                              'evidence_pointers':[{'role':secondary_role,'field':field}]})
        drug_values={x['drug'] for x in samples if x['drug']}; drug=next(iter(drug_values)) if len(drug_values)==1 else 'UNKNOWN'
        proposal=cfg.get('treatment',{}); exposure_id=uid+':exposure';episode_id=uid+':index'
        if proposal:
            regimen=proposal['regimen_id'];drug_class=cfg.get('drug_class_map',{}).get(drug,'UNKNOWN')
            tables['treatment_episode'].append({'schema_version':'1.1.0','data_classification':'PRIVATE_PATIENT_LEVEL',
                'treatment_episode_id':episode_id,'patient_uid':uid,'study_id':study,'regimen_id':regimen,'index_event':'START_OF_INDEX_TREATMENT',
                'start_day':None,'stop_day':None,'timing_precision':'UNKNOWN','prior_ici':prior,'episode_status':'BLOCKED_UNKNOWN',
                'component_exposure_ids':[exposure_id],'source_locators':[source]})
            tables['treatment_exposure'].append({'data_classification':'PRIVATE_PATIENT_LEVEL','treatment_exposure_id':exposure_id,
                'patient_uid':uid,'regimen_id':regimen,'agent':drug,'pharmacological_class':drug_class,'sequence':'INDEX',
                'line_of_therapy':'UNKNOWN','prior_ici':prior,'certainty':'UNRESOLVED','source_locators':loc})
    if unknown_responses:
        items.append({'category':'ORR_RESPONSE_UNKNOWN','status':'BLOCKED_UNKNOWN',
                      'evidence_pointers':[{'role':response_role,'field':cfg['response_field']}],
                      'context':{'record_count':unknown_responses}})
    if unknown_timing:
        items.append({'category':'BASELINE_TIMING_UNRESOLVED','status':'BLOCKED_UNKNOWN',
                      'evidence_pointers':[{'role':cfg['patient_role'] if cfg.get('visit_source') == 'patient' else cfg['sample_role'],'field':cfg['visit_field']}],
                      'context':{'record_count':unknown_timing}})
    cross = cfg.get('response_crosscheck')
    if isinstance(cross, dict):
        primary_rows, author_rows = parsed.get(cross['source_role']), parsed.get(cross['author_role'])
        if isinstance(primary_rows, list) and isinstance(author_rows, list):
            compared = crosscheck_by_patient(primary_rows, author_rows, cfg['patient_id'],
                                            cross['source_field'], cross['author_field'])
            if compared['different'] or compared['unmatched']:
                items.append({'category':'AUTHOR_RESPONSE_DISAGREEMENT','status':'BLOCKED_UNKNOWN',
                    'evidence_pointers':[{'role':cross['source_role'],'field':cross['source_field']},
                                         {'role':cross['author_role'],'field':cross['author_field']}],
                    'context':compared})
        else:
            items.append({'category':'AUTHOR_CROSSCHECK_UNAVAILABLE','status':'BLOCKED_UNKNOWN',
                          'evidence_pointers':[{'role':cross['author_role']}]})
    author_join = cfg.get('author_clinical_join')
    if isinstance(author_join, dict):
        mono, dual = author_join['mono_role'], author_join['dual_role']
        if isinstance(parsed.get(mono), list) and isinstance(parsed.get(dual), list):
            checked = verified_author_links({'mono': parsed[mono], 'dual': parsed[dual]}, patient_rows, sample_rows)
            links = checked['links']
            locators = {pid: field_map['source_objects'][mono if pid.startswith('PD') else dual]['locator'] for pid in links}
            apply_author_endpoint_records(tables, links, locators)
            exceptions = {key: value for key, value in checked.items() if key != 'links'}
            if any(exceptions[k] for k in ('matched_without_rna', 'unmatched_with_rna', 'rna_unknown', 'ambiguous_or_disagree')):
                items.append({'category':'AUTHOR_RNA_LINK_EXCEPTION', 'status':'BLOCKED_UNKNOWN',
                              'evidence_pointers':[{'role':mono}, {'role':dual}], 'context':exceptions})
        else:
            items.append({'category':'AUTHOR_CROSSCHECK_UNAVAILABLE','status':'BLOCKED_UNKNOWN',
                          'evidence_pointers':[{'role':mono}, {'role':dual}]})
