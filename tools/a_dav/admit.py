"""Run a signed worksheet through the evidence chain and baseline matrix stage."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, cast

from .core import DavError, SchemaStore
from .ingest import IngestError, run_ingest, validate_output_path
from .ingestion_proposals import materialize_proposals, run_admission_chain
from .matrices import build_baseline
from .baseline_policy import build_baseline_packet
from .assay_policy import materialize_primary_assay_policy
from .release import validate_split
from .worksheet import build_worksheet, read_worksheet, validate_signed_worksheet


def retain_endpoint_source_priority(config: dict[str, Any], outcomes: list[dict[str, Any]]) -> None:
    retained = {row['outcome_id'] for row in outcomes}
    config['source_priority'] = [value for value in config.get('source_priority', []) if value in retained]


def verify_signed_cbio_identities(packet: dict[str, Any], field_map: dict[str, Any],
                                  worksheet: dict[str, Any], store_root: Path) -> dict[str, Any]:
    """Verify only signed V4 patient/sample joins reproduced from pinned clinical objects."""
    from .cbioportal import read_clinical
    from .source_objects import ContentAddressedStore
    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    cfg = field_map.get('cbio_ingest', {})
    if signed['decisions'].get('V4') != 'PASS' or not cfg or cfg.get('patient_mapping_unverified'):
        return result
    store = ContentAddressedStore(store_root)
    patients = read_clinical(store.read(field_map['source_objects'][cfg['patient_role']]['sha256']).bytes)
    samples = read_clinical(store.read(field_map['source_objects'][cfg['sample_role']]['sha256']).bytes)
    patient_key, sample_key = cfg['patient_id'], cfg['sample_id']
    for patient in result['records'].get('patient_registry', []):
        pid = patient.get('source_patient_id')
        matching_patients = [row for row in patients if row.get(patient_key) == pid]
        specimens = [row for row in result['records'].get('specimen_registry', []) if row.get('patient_uid') == patient.get('patient_uid')]
        if not pid or len(matching_patients) != 1 or not specimens:
            continue
        supported = True
        for specimen in specimens:
            aliases = specimen.get('raw_sample_aliases', [])
            matches = [row for row in samples if row.get(sample_key) in aliases]
            if len(matches) != 1 or matches[0].get(patient_key) != pid:
                supported = False
                break
        if supported:
            patient['patient_identity_confidence'] = 'VERIFIED'
            for specimen in specimens:
                specimen.setdefault('tissue_type', 'UNKNOWN')
            patient.setdefault('source_locators', []).extend([
                {'kind':'worksheet','value':'worksheet:'+worksheet['worksheet_id']+'#V4'},
                {'kind':'field_map','value':f"{cfg['patient_role']}:{patient_key}; {cfg['sample_role']}:{sample_key}/{patient_key}"}])
    return result


def verify_signed_cbio_outcome_bindings(packet: dict[str, Any], field_map: dict[str, Any],
                                        worksheet: dict[str, Any]) -> dict[str, Any]:
    """Apply the same signed V5 episode rule to declared cBioPortal source roles."""
    cfg = field_map.get('cbio_ingest', {})
    treatment = cfg.get('treatment', {})
    locator = field_map.get('source_objects', {}).get(cfg.get('patient_role'), {}).get('locator')
    if not isinstance(treatment, dict) or not treatment.get('regimen_id') or not locator:
        return copy.deepcopy(packet)
    timing_role = cfg.get('patient_role') if cfg.get('visit_source') == 'patient' else cfg.get('sample_role')
    sample_source = field_map.get('source_objects', {}).get(timing_role, {})
    virtual = {**field_map, 'geo_ingest': {'baseline_values': cfg.get('baseline_values', [])},
               'treatment_proposal': {'regimen_id': treatment['regimen_id'],
                   'index_event': 'START_OF_INDEX_TREATMENT', 'source_locator': locator},
               'source_objects': {**field_map.get('source_objects', {}), 'geo_family_soft': sample_source}}
    return verify_signed_geo_outcome_bindings(packet, virtual, worksheet)


def materialize_signed_cbio_development(packet: dict[str, Any], field_map: dict[str, Any],
                                        worksheet: dict[str, Any]) -> dict[str, Any]:
    """Apply signed development declarations without certifying independence."""
    cfg = field_map.get('decision_config', {}); preview = cfg.get('preview', {})
    exposure = cfg.get('exposure', cfg.get('exposure_policy', {})); prior = cfg.get('prior_ici_policy', {})
    if (preview.get('split_policy') != 'DEVELOPMENT' or exposure.get('state') != 'METADATA_ONLY'
            or not exposure.get('evidence') or prior.get('value') != 'UNKNOWN_ALLOWED_DEVELOPMENT'):
        return copy.deepcopy(packet)
    cbio = field_map.get('cbio_ingest', {})
    declaration = {'prior_ici_policy':'UNKNOWN_ALLOWED_DEVELOPMENT','split_role':'DEVELOPMENT',
        'exposure_state':'METADATA_ONLY','review_complete':True,'covered_subject_types':['STUDY_FAMILY','PATIENT_SET'],
        'analysis_lineage_id':'CBIO:'+field_map['cohort']+':DEVELOPMENT', 'source_locator':exposure['evidence'],
        'nonbaseline_specimens':'OUTSIDE_BRANCH',
        'nonbaseline_visit_values': cbio.get('nonbaseline_values', []) + cbio.get('excluded_visit_values', [])}
    cancer = field_map.get('cancer_type')
    cancer_source = field_map.get('source_objects', {}).get(cfg.get('cancer_evidence', {}).get('source_role'), {}).get('locator')
    if isinstance(cancer, str) and cancer and isinstance(cancer_source, str) and cancer_source:
        declaration['cancer'] = cancer
        declaration['cancer_source_locator'] = cancer_source
    virtual = {**field_map, 'geo_ingest': {'endpoint_class':'TUMOUR_RESPONSE'},
               'decision_config': {**cfg, 'development_policy': declaration}}
    result = materialize_signed_geo_development_policy(packet, virtual, worksheet)
    if preview.get('exclude_without_assay') and 'split' in result['config']:
        records = result['records']
        assayed = {a['specimen_uid'] for a in records.get('assay_registry', [])}
        eligible = {s['patient_uid'] for s in records.get('specimen_registry', []) if s['specimen_uid'] in assayed}
        records['patient_registry'] = [p for p in records.get('patient_registry', []) if p['patient_uid'] in eligible]
        for table in ('specimen_registry','clinical_outcome','treatment_episode','treatment_exposure','episode_binding'):
            records[table] = [row for row in records.get(table, []) if row.get('patient_uid') in eligible]
        records['prior_exposure_record'] = [row for row in records.get('prior_exposure_record', [])
            if row.get('subject_type') != 'PATIENT_SET' or row.get('subject_id') in eligible]
        exposure_cfg = result['config']['exposure']
        exposure_cfg['covered_subjects'] = [row for row in exposure_cfg['covered_subjects']
            if row.get('subject_type') != 'PATIENT_SET' or row.get('subject_id') in eligible]
    return result


def materialize_signed_cbio_endpoints(packet: dict[str, Any], worksheet: dict[str, Any]) -> dict[str, Any]:
    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    if signed['decisions'].get('V5') != 'PASS':
        return result
    outcomes = result['records'].get('clinical_outcome', [])
    mapping = result.get('config', {}).get('endpoints', {}).get('category_map', {})
    for outcome in outcomes:
        category = outcome.get('canonical_category'); raw = outcome.get('raw_endpoint_label')
        if mapping.get(raw) != category or category not in {'CR','PR','SD','PD','NE','UNKNOWN','SOURCE_POSITIVE','SOURCE_NEGATIVE'}:
            continue
        outcome['evaluability'] = 'NOT_EVALUABLE' if category == 'NE' else 'UNKNOWN' if category == 'UNKNOWN' else 'EVALUABLE'
        outcome['mapping_confidence'] = 'VERIFIED'
        if outcome.get('discrepancy_status') == 'UNRESOLVED' and sum(
                o.get('patient_uid') == outcome.get('patient_uid') and o.get('endpoint_class') == outcome.get('endpoint_class')
                for o in outcomes) == 1:
            outcome['discrepancy_status'] = 'RESOLVED'
    return result


def materialize_signed_cbio_overlap(packet: dict[str, Any], field_map: dict[str, Any],
                                    worksheet: dict[str, Any]) -> dict[str, Any]:
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    cfg = field_map.get('decision_config', {}).get('overlap_review', {})
    if (worksheet.get('review_status') == 'SIGNED' and signed['decisions'].get('V6') == 'PASS'
            and cfg.get('status') == 'UNKNOWN' and cfg.get('no_independence_certified') is True
            and cfg.get('evidence')):
        targets = cfg.get('targets', [])
        if not isinstance(targets, list) or not all(isinstance(target, str) and target for target in targets):
            return result
        edges = [{'target_node_type':'STUDY','target_node_id':target,'edge_type':'SUSPECTED_SAME_PATIENT',
                  'certainty':'POSSIBLE','implication_for_independence':'INDEPENDENCE_BLOCKED',
                  'evidence':'Possible overlap; independence not certified.'} for target in targets]
        virtual = {**field_map, 'decision_config': {**field_map.get('decision_config', {}),
                    'overlap_review': {'edges':edges,'source_locator':cfg['evidence']}}}
        result = materialize_signed_geo_overlap(packet, virtual, worksheet)
        result['config']['overlap'].update({'possible_overlap':'UNKNOWN','independence_certified':False})
    return result


def materialize_signed_cbio_admission(packet: dict[str, Any], field_map: dict[str, Any],
                                      worksheet: dict[str, Any]) -> dict[str, Any]:
    cfg = field_map.get('cbio_ingest', {})
    source = field_map.get('source_objects', {}).get(cfg.get('patient_role'), {})
    if not source.get('locator'):
        return copy.deepcopy(packet)
    virtual = {**field_map, 'geo_ingest': {'endpoint_class':'TUMOUR_RESPONSE'},
               'source_objects': {**field_map.get('source_objects', {}), 'geo_family_soft': source}}
    return materialize_signed_geo_admission_policy(packet, virtual, worksheet)


def materialize_signed_geo_development_policy(packet: dict[str, Any], field_map: dict[str, Any],
                                              worksheet: dict[str, Any]) -> dict[str, Any]:
    """Apply the reviewed development-only exposure and branch scope declarations."""
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    cfg = field_map.get('decision_config', {}).get('development_policy', {})
    if (worksheet.get('review_status') != 'SIGNED' or 'geo_ingest' not in field_map
            or any(signed['decisions'].get(gate) != 'PASS' for gate in ('V4', 'V5', 'V6', 'V7'))
            or cfg.get('prior_ici_policy') != 'UNKNOWN_ALLOWED_DEVELOPMENT'
            or cfg.get('split_role') != 'DEVELOPMENT' or cfg.get('exposure_state') != 'METADATA_ONLY'
            or cfg.get('review_complete') is not True
            or cfg.get('covered_subject_types') != ['STUDY_FAMILY', 'PATIENT_SET']
            or not cfg.get('analysis_lineage_id') or not cfg.get('source_locator')):
        return result
    records, config = result['records'], result['config']
    if cfg.get('cancer') and cfg.get('cancer_source_locator'):
        for patient in records.get('patient_registry', []):
            if not patient.get('cancer'):
                patient['cancer'] = cfg['cancer']
                patient.setdefault('source_locators', []).append({'kind':'decision', 'value':cfg['cancer_source_locator']})
    if cfg.get('nonbaseline_specimens') == 'OUTSIDE_BRANCH' and packet['branch_id'] == 'A_BASELINE_BIO':
        nonbaseline_values = cfg.get('nonbaseline_visit_values', [])
        retained = {s['specimen_uid'] for s in records.get('specimen_registry', [])
                    if s.get('timing_raw_text') not in nonbaseline_values}
        records['specimen_registry'] = [s for s in records.get('specimen_registry', []) if s['specimen_uid'] in retained]
        records['assay_registry'] = [a for a in records.get('assay_registry', []) if a['specimen_uid'] in retained]
        records['episode_binding'] = [b for b in records.get('episode_binding', []) if b['subject_type'] != 'SPECIMEN' or b['subject_id'] in retained]
        headers = {a['matrix_header'] for a in records['assay_registry'] if a.get('matrix_header')}
        for matrix in config.get('assays', {}).get('matrices', []):
            indexes = [i for i, h in enumerate(matrix['headers']) if h in headers]
            matrix['headers'] = [matrix['headers'][i] for i in indexes]
            matrix['values'] = [[row[i] for i in indexes] for row in matrix['values']]
            if 'library_properties' in matrix:
                matrix['library_properties'] = {h: v for h, v in matrix['library_properties'].items() if h in headers}
    lineage, locator = cfg['analysis_lineage_id'], cfg['source_locator']
    covered = ([{'subject_type':'STUDY_FAMILY', 'subject_id':row['publication_family_id']} for row in records.get('publication_family', [])]
               + [{'subject_type':'PATIENT_SET', 'subject_id':row['patient_uid']} for row in records.get('patient_registry', [])])
    new_exposure_rows = [dict(schema_version='1.1.0', exposure_id=f'{lineage}:metadata:{index}',
        **subject, analysis_lineage_id=lineage, fields_accessed=['study_identity','source_metadata','sample_identity','treatment_metadata'],
        use='METADATA_INSPECTION', occurred_utc=None, date_precision='UNKNOWN', actor_role='SOURCE_REVIEWER',
        independence_implication='METADATA_ONLY_REVIEWED', source_locators=[locator], reviewer=signed['reviewer_name'],
        notes='Reviewed metadata and table shapes; no expression or scores examined against response.')
        for index, subject in enumerate(covered)]
    prior_rows = records.get('prior_exposure_record', [])
    if {row.get('exposure_id') for row in prior_rows} & {row['exposure_id'] for row in new_exposure_rows}:
        return copy.deepcopy(packet)
    records['prior_exposure_record'] = prior_rows + new_exposure_rows
    config['exposure'] = {'analysis_lineage_id':lineage, 'review_complete':True, 'covered_subjects':covered}
    config['split'] = {'version':lineage, 'analysis_lineage_id':lineage, 'selection_basis':'PRESPECIFIED_METADATA',
                       'performance_observed':False, 'required_source_ids':config.get('admission', {}).get('required_source_object_ids', []),
                       'policy':{'permanent_role':'DEVELOPMENT','prior_exposure_state':'METADATA_ONLY'}}
    config.setdefault('timing', {})['prior_ici_policy'] = cfg['prior_ici_policy']
    endpoint = field_map['geo_ingest'].get('endpoint_class')
    if endpoint in {'SOURCE_BINARY', 'TUMOUR_RESPONSE'}:
        config['baseline'] = {'selection_basis':'PRESPECIFIED_METADATA',
            'specimen_rank':{s['specimen_uid']:0 for s in records.get('specimen_registry', [])},
            'assay_rank':{a['assay_uid']:0 for a in records.get('assay_registry', [])},
            'assay_suitability':'BASELINE_DE', 'coverage_suitability':'de_suitability',
            'endpoint_policy':{'required':True, 'endpoint_class':'OTHER' if endpoint == 'SOURCE_BINARY' else 'ORR',
                               'discrepancy_policy':'SEALED_PREFERRED_OUTCOME'}, 'build_utc':'AT_BUILD_TIME'}
        suitable = {m['source_object_id'] for m in config.get('assays', {}).get('matrices', [])
                    if m.get('feature_scope') in {'COMPLETE','COMPLETE_WITH_DOCUMENTED_EXCLUSIONS'} and m.get('lane') in {'COUNTS','CONTINUOUS','ARRAY'}}
        for assay in records.get('assay_registry', []):
            if assay.get('source_object_id') in suitable and 'BASELINE_DE' not in assay.get('branch_suitability', []):
                assay.setdefault('branch_suitability', []).append('BASELINE_DE')
    return result


def materialize_signed_geo_admission_policy(packet: dict[str, Any], field_map: dict[str, Any],
                                            worksheet: dict[str, Any]) -> dict[str, Any]:
    """Populate branch criteria only from the reviewed source roles and endpoint declaration."""
    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    if signed['decisions'].get('V7') != 'PASS' or signed['decisions'].get('V5') != 'PASS' or 'geo_ingest' not in field_map:
        return result
    roles = field_map.get('decision_config', {}).get('preview', {}).get('required_roles', [])
    role_ids = packet.get('config', {}).get('registries', {}).get('source_roles', {})
    geo = field_map.get('source_objects', {}).get('geo_family_soft', {}).get('locator')
    endpoint = field_map['geo_ingest'].get('endpoint_class')
    definition = field_map.get('decision_config', {}).get('endpoint', {}).get('source_binary_definition')
    if (not isinstance(roles, list) or not roles or not all(role in role_ids for role in roles) or
            not isinstance(geo, str) or not geo or endpoint not in {'SOURCE_BINARY', 'TUMOUR_RESPONSE'} or
            (endpoint == 'SOURCE_BINARY' and not isinstance(definition, dict))):
        return result
    baseline = {'policy_version':'field-map-signed', 'source_locators':[geo]}
    endpoint_policy: dict[str, Any] = {'policy_version':'field-map-signed', 'source_locators':[geo],
                                       'endpoint_class':'SOURCE_BINARY' if endpoint == 'SOURCE_BINARY' else 'ORR'}
    if endpoint == 'SOURCE_BINARY':
        endpoint_policy['source_binary_definition'] = copy.deepcopy(definition)
    admission = result['config'].setdefault('admission', {})
    admission['required_source_object_ids'] = [role_ids[role] for role in roles]
    admission.setdefault('branch_policies', {})[packet['branch_id']] = {'baseline':baseline, 'endpoint':endpoint_policy}
    return result


def materialize_signed_geo_overlap(packet: dict[str, Any], field_map: dict[str, Any],
                                   worksheet: dict[str, Any]) -> dict[str, Any]:
    """Record the signed overlap review and retain declared unresolved links."""
    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    declaration = field_map.get('decision_config', {}).get('overlap_review')
    if signed['decisions'].get('V6') != 'PASS' or not isinstance(declaration, dict):
        return result
    edges = declaration.get('edges'); locator = declaration.get('source_locator')
    studies = result['records'].get('study_registry', [])
    if not isinstance(edges, list) or not isinstance(locator, str) or not locator or len(studies) != 1:
        return result
    nodes = []; rows = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict) or not all(isinstance(edge.get(k), str) and edge[k] for k in ('target_node_type','target_node_id','edge_type','certainty','implication_for_independence','evidence')):
            return result
        nodes.append({'node_type':edge['target_node_type'],'node_id':edge['target_node_id']})
        rows.append({'schema_version':'1.0.0','overlap_edge_id':studies[0]['study_id']+':SIGNED_OVERLAP:'+str(index),
                     'source_node_type':'STUDY','source_node_id':studies[0]['study_id'],
                     **edge, 'source_locators':[{'kind':'decision','value':locator}],
                     'reviewer':signed['reviewer_name'],'review_date':signed['review_date']})
    result['records']['overlap_edge'] = rows
    result['config']['overlap'] = {'review_complete':True,'external_nodes':nodes}
    return result


def materialize_signed_geo_endpoints(packet: dict[str, Any], field_map: dict[str, Any],
                                     worksheet: dict[str, Any]) -> dict[str, Any]:
    """Apply the reviewed source endpoint mapping without changing its endpoint class."""
    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signed = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    cfg = field_map.get('geo_ingest', {})
    mapping = cfg.get('response_map', {})
    if signed['decisions'].get('V5') != 'PASS' or not isinstance(mapping, dict):
        return result
    definition = field_map.get('decision_config', {}).get('endpoint', {}).get('source_binary_definition', {})
    locator = definition.get('source_locator', definition.get('citation')) if isinstance(definition, dict) else None
    binary_map = {raw: int(category == 'SOURCE_POSITIVE') for raw, category in mapping.items()
                  if category in {'SOURCE_POSITIVE', 'SOURCE_NEGATIVE'}}
    outcomes = result['records'].get('clinical_outcome', [])
    for outcome in outcomes:
        raw = outcome.get('raw_endpoint_label'); category = outcome.get('canonical_category')
        if mapping.get(raw) != category or category not in {'CR', 'PR', 'SD', 'PD', 'NE', 'UNKNOWN', 'SOURCE_POSITIVE', 'SOURCE_NEGATIVE'}:
            continue
        if outcome.get('endpoint_class') == 'SOURCE_BINARY' and (not locator or raw not in binary_map):
            continue
        outcome['evaluability'] = ('NOT_EVALUABLE' if category == 'NE' else 'UNKNOWN' if category == 'UNKNOWN' else 'EVALUABLE')
        outcome['mapping_confidence'] = 'VERIFIED'
        if outcome.get('discrepancy_status') == 'UNRESOLVED' and sum(o.get('patient_uid') == outcome.get('patient_uid') for o in outcomes) == 1:
            outcome['discrepancy_status'] = 'RESOLVED'
        if outcome.get('endpoint_class') == 'SOURCE_BINARY':
            result['config'].setdefault('endpoints', {}).setdefault('binary_definitions', {})[outcome['outcome_id']] = {
                'name':definition.get('name', 'source-defined binary response'), 'version':'field-map',
                'source_locator':locator, 'raw_value_map':binary_map}
    return result


def verify_signed_geo_outcome_bindings(packet: dict[str, Any], field_map: dict[str, Any],
                                       worksheet: dict[str, Any]) -> dict[str, Any]:
    """Bind outcomes only when the signed decision and a unique declared episode agree."""
    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signature = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    proposal = field_map.get('treatment_proposal')
    if 'geo_ingest' not in field_map or not isinstance(proposal, dict) or signature['decisions'].get('V5') != 'PASS':
        return result
    records = result['records']
    bindings = records.setdefault('episode_binding', [])
    all_episodes = records.get('treatment_episode', [])
    if len({e.get('patient_uid') for e in all_episodes}) == len(all_episodes):
        timing_cfg = result['config'].setdefault('timing', {})
        timing_cfg['version'] = 'field-map-signed-v5'
        timing_cfg['episode_order'] = sorted(e['treatment_episode_id'] for e in all_episodes)
    subjects = [('CLINICAL_OUTCOME', 'outcome_id', 'OUTCOME_ASSESSMENT', row) for row in records.get('clinical_outcome', [])]
    subjects.extend(('TREATMENT_EXPOSURE', 'treatment_exposure_id', 'TREATMENT_COMPONENT', row)
                    for row in records.get('treatment_exposure', []))
    baseline_values = field_map['geo_ingest'].get('baseline_values', [])
    subjects.extend(('SPECIMEN', 'specimen_uid', 'PRE_INDEX_BASELINE', row)
                    for row in records.get('specimen_registry', [])
                    if row.get('canonical_timing_category') == 'PRE_INDEX_BASELINE' and row.get('timing_raw_text') in baseline_values)
    for subject_type, id_key, role, outcome in subjects:
        episodes = [e for e in records.get('treatment_episode', []) if e.get('patient_uid') == outcome.get('patient_uid')]
        existing = [b for b in bindings if b.get('subject_type') == subject_type and b.get('subject_id') == outcome.get(id_key)]
        if (len(episodes) != 1 or len(existing) > 1 or episodes[0].get('regimen_id') != proposal.get('regimen_id') or
                episodes[0].get('index_event') != proposal.get('index_event') or not proposal.get('source_locator')):
            continue
        episode = episodes[0]
        if subject_type == 'TREATMENT_EXPOSURE' and (outcome.get(id_key) not in episode.get('component_exposure_ids', []) or outcome.get('regimen_id') != episode.get('regimen_id')):
            continue
        if episode.get('episode_status') == 'CONFLICT' or (subject_type == 'TREATMENT_EXPOSURE' and outcome.get('certainty') == 'DISPROVED'):
            continue
        if existing and existing[0].get('treatment_episode_id') != episode.get('treatment_episode_id'):
            continue
        binding = existing[0] if existing else {'schema_version':'1.1.0', 'data_classification':packet['classification'],
            'binding_id':'BIND:' + subject_type + ':' + outcome[id_key], 'patient_uid':outcome['patient_uid'],
            'treatment_episode_id':episode['treatment_episode_id'], 'subject_type':subject_type,
            'subject_id':outcome[id_key], 'role':role}
        binding.update(binding_status='VERIFIED', reviewer=signature['reviewer_name'], reviewed_utc=signature['review_date'],
                       source_locators=[proposal['source_locator'], 'worksheet:' + worksheet['worksheet_id'] + '#V5'],
                       reason='Signed V5 and field-map treatment proposal.')
        if not existing:
            bindings.append(binding)
        if episode.get('episode_status') == 'BLOCKED_UNKNOWN':
            episode['episode_status'] = 'VERIFIED'
        if subject_type == 'TREATMENT_EXPOSURE' and outcome.get('certainty') == 'UNRESOLVED':
            outcome['certainty'] = 'VERIFIED'
        timing = result['config'].setdefault('timing', {})
        if subject_type == 'SPECIMEN':
            geo_locator = field_map.get('source_objects', {}).get('geo_family_soft', {}).get('locator')
            if geo_locator:
                timing.setdefault('specimens', {})[outcome[id_key]] = {'treatment_episode_id':episode['treatment_episode_id'],
                    'precision':'SOURCE_CATEGORY', 'canonical_category':'PRE_INDEX_BASELINE',
                    'source_locator':geo_locator, 'inferred_from_order':False, 'category_only_allowed':True}
        elif subject_type == 'TREATMENT_EXPOSURE' and outcome.get('start_date_or_day') is None and outcome.get('stop_date_or_day') is None:
            timing.setdefault('allow_undated_treatment_exposure_ids', []).append(outcome[id_key])
    return result


def verify_signed_geo_identities(packet: dict[str, Any], field_map: dict[str, Any],
                                 worksheet: dict[str, Any], store_root: Path) -> dict[str, Any]:
    """Apply V4 only to patient identities reproduced from a pinned GEO characteristic."""
    import re
    from .geo_soft import parse_geo_family_soft
    from .source_objects import ContentAddressedStore

    if worksheet.get('review_status') != 'SIGNED':
        raise DavError('WORKSHEET_UNSIGNED', blocked=True)
    signature = validate_signed_worksheet(packet, worksheet)
    result = copy.deepcopy(packet)
    cfg = field_map.get('geo_ingest')
    if not isinstance(cfg, dict) or cfg.get('patient_mapping_unverified') or signature['decisions'].get('V4') != 'PASS':
        return result
    identity = field_map.get('sample_identity', {})
    key = field_map.get('geo', {}).get('characteristics', {}).get('patient')
    title_only = identity.get('accept_title_token_with_signed_v4') is True
    if title_only and (not identity.get('title_regex') or not identity.get('patient_group')):
        return result
    if not title_only and (not isinstance(key, str) or not key or identity.get('patient_characteristic') != key):
        return result
    source = field_map.get('source_objects', {}).get('geo_family_soft', {})
    sha = source.get('sha256')
    if not isinstance(sha, str):
        return result
    samples = parse_geo_family_soft(ContentAddressedStore(store_root).read(sha).bytes)
    indexed = {s['accession']: s for s in samples}
    regex = re.compile(identity['title_regex']) if identity.get('title_regex') else None
    specimens = result['records'].get('specimen_registry', [])
    for patient in result['records'].get('patient_registry', []):
        aliases = {alias for specimen in specimens if specimen.get('patient_uid') == patient.get('patient_uid')
                   for alias in specimen.get('raw_sample_aliases', [])}
        linked = [indexed[alias] for alias in aliases if alias in indexed]
        if not linked:
            continue
        def supports(sample: dict[str, Any]) -> bool:
            if title_only:
                match = regex.match(sample['title']) if regex else None
                return bool(match and match.group(identity['patient_group']) == patient.get('source_patient_id'))
            ids = {row['value'] for row in sample['characteristics'] if row['key'] == key}
            if ids != {patient.get('source_patient_id')}:
                return False
            match = regex.match(sample['title']) if regex else None
            if match and identity.get('patient_group'):
                return bool(match.group(identity['patient_group']) == patient.get('source_patient_id'))
            return True
        if all(supports(sample) for sample in linked):
            patient['patient_identity_confidence'] = 'VERIFIED'
            patient.setdefault('source_locators', []).extend([
                {'kind': 'review', 'value': 'worksheet:' + worksheet['worksheet_id'] + '#V4'},
                {'kind': 'field_map_rule', 'value': ('sample_identity.title_regex#patient_group' if title_only else
                                                      'geo_family_soft:!Sample_characteristics_ch1:' + str(key))}])
    return result


def materialize_configured_proposals(packet: dict[str, Any], field_map: dict[str, Any]) -> dict[str, Any]:
    declaration = field_map.get('proposal_generation', {})
    if not declaration and ('geo_ingest' in field_map or 'cbio_ingest' in field_map):
        return packet
    if not isinstance(declaration, dict):
        raise ValueError('PROPOSAL_DECLARATION_MISSING')
    return materialize_proposals(packet, declaration)


def ensure_field_map_matches(packet: dict[str, Any], field_map: dict[str, Any]) -> None:
    """Refuse stale branch packets whose declared study class differs from the field map."""
    declared = field_map.get("study_class")
    if declared is None:
        return
    studies = packet.get("records", {}).get("study_registry", [])
    if (not isinstance(studies, list) or len(studies) != 1 or
            studies[0].get("study_class") != declared):
        raise DavError("FIELD_MAP_STUDY_CLASS_MISMATCH")


def certify_required_source_validation(packet: dict[str, Any], field_map: dict[str, Any],
                                       decisions: dict[str, str],
                                       ingestion_validation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Upgrade required source records only when hashes, adapters and signed joins agree."""
    result = copy.deepcopy(packet)
    records = result.get("records", {})
    evidence = ingestion_validation or {}
    if 'geo_ingest' in field_map or 'cbio_ingest' in field_map:
        roles = field_map.get('decision_config', {}).get('preview', {}).get('required_roles', [])
        patients = records.get('patient_registry', [])
        outcomes = records.get('clinical_outcome', [])
        bindings = records.get('episode_binding', [])
        if (not isinstance(roles, list) or not roles or not all(decisions.get(gate) == 'PASS' for gate in ('V2','V3','V4','V5')) or
                not patients or not outcomes or any(row.get('patient_identity_confidence') != 'VERIFIED' for row in patients) or
                any(sum(b.get('subject_type') == 'CLINICAL_OUTCOME' and b.get('subject_id') == o.get('outcome_id') and b.get('binding_status') == 'VERIFIED' for b in bindings) != 1 for o in outcomes)):
            return result
        for role in roles:
            source = field_map.get('source_objects', {}).get(role, {})
            sha, adapter = source.get('sha256'), source.get('format')
            matches = [row for row in records.get('source_record', []) if row.get('sha256') == sha]
            if (role not in evidence.get('sha256_verified_roles', []) or role not in evidence.get('parsed_source_roles', []) or
                    evidence.get('adapter_by_role', {}).get(role) != adapter or len(matches) != 1):
                continue
            row = matches[0]
            if row.get('retrieval_status') == 'RETRIEVED' and row.get('hash_scope') == 'FULL_OBJECT' and row.get('validation_status') != 'FAIL':
                row['validation_status'] = 'PASS'
                row['notes'] = 'Full-object hash and declared adapter verified; signed V2, V3, V4 and V5.'
        return result
    validation = field_map.get("source_validation", {})
    source_objects = field_map.get("source_objects", {})
    roles = validation.get("roles", []) if isinstance(validation, dict) else []
    expected_links = validation.get("baseline_specimen_patient_links") if isinstance(validation, dict) else None
    expected_bor = validation.get("baseline_bor_patients") if isinstance(validation, dict) else None
    if not isinstance(roles, list) or not roles or type(expected_links) is not int or type(expected_bor) is not int:
        return result
    if (decisions.get("V4") != "PASS" or decisions.get("V5") != "PASS"
            or not isinstance(evidence, dict)):
        return result
    patients = {row.get("patient_uid"): row for row in records.get("patient_registry", [])
                if isinstance(row, dict)}
    specimens = [row for row in records.get("specimen_registry", [])
                 if isinstance(row, dict) and row.get("timing_raw_text") == "Pre"]
    linked = [row for row in specimens if row.get("patient_uid") in patients and
              patients[row["patient_uid"]].get("patient_identity_confidence") == "VERIFIED"]
    outcomes = [row for row in records.get("clinical_outcome", [])
                if isinstance(row, dict) and row.get("patient_uid") in patients and
                isinstance(row.get("raw_endpoint_label"), str)]
    joins_pass = (len(linked) == expected_links and len({row.get("specimen_uid") for row in linked}) == expected_links
                  and len(outcomes) == expected_bor
                  and len({row.get("patient_uid") for row in outcomes}) == expected_bor)
    ingestion_hashes = evidence.get("sha256_verified_roles", [])
    parsed_roles = evidence.get("parsed_source_roles", [])
    adapters = evidence.get("adapter_by_role", {})
    if not joins_pass:
        return result
    roles = list(roles)
    matrices = result.get('config', {}).get('assays', {}).get('matrices', [])
    if decisions.get('V3') == 'PASS' and isinstance(matrices, list) and len(matrices) == 1:
        primary_sha = matrices[0].get('source_sha256') if isinstance(matrices[0], dict) else None
        primary_roles = [role for role, declaration in source_objects.items()
                         if isinstance(declaration, dict) and declaration.get('sha256') == primary_sha]
        if len(primary_roles) == 1 and primary_roles[0] not in roles:
            roles.append(primary_roles[0])
    source_rows = records.get("source_record", [])
    for role in roles:
        declaration = source_objects.get(role, {})
        sha = declaration.get("sha256") if isinstance(declaration, dict) else None
        adapter = declaration.get("format") if isinstance(declaration, dict) else None
        if adapter in {'MATRIX_HEADER_CSV', 'MATRIX_HEADER_TSV'} and decisions.get('V3') != 'PASS':
            continue
        matching = [row for row in source_rows if row.get("sha256") == sha]
        if (not isinstance(sha, str) or role not in ingestion_hashes or role not in parsed_roles
                or adapters.get(role) != adapter or len(matching) != 1):
            continue
        source = matching[0]
        if (source.get("retrieval_status") != "RETRIEVED" or source.get("hash_scope") != "FULL_OBJECT"
                or source.get("validation_status") == "FAIL"):
            continue
        source["validation_status"] = "PASS"
        source["notes"] = ("Validation checks: FULL_OBJECT_SHA256_VERIFIED; "
                           f"DECLARED_ADAPTER_PARSE_PASS:{adapter}; "
                           "SIGNED_V3_PASS_WHEN_REQUIRED; "
                           "SIGNED_V4_AND_V5_PASS; "
                           "SIGNED_V4_BASELINE_SPECIMEN_PATIENT_LINKS; "
                           "SIGNED_V5_BOR_ON_BASELINE_PATIENTS.")
    return result


def attempt_baseline_build(packet: dict[str, Any], *, schemas: SchemaStore) -> dict[str, Any]:
    """Run the existing split and baseline stages, translating a blocker to a safe result."""
    try:
        split = validate_split(packet, schemas=schemas)
        if split["status"] != "READY":
            return {"status": split["status"], "reasons": split["reasons"], "split": split}
        current = copy.deepcopy(packet)
        current["records"] = split["records"]
        current.setdefault("dependencies", {})["split"] = split
        baseline = build_baseline(current, schemas=schemas)
        return {"status": baseline["status"], "reasons": baseline["reasons"],
                "baseline": baseline, "split": split}
    except DavError as error:
        return {"status": "BLOCKED_UNKNOWN" if error.blocked else "FAIL",
                "reasons": [error.code]}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _item_label(item: dict[str, Any]) -> str:
    return str(item.get("gate") or item.get("category") or item.get("kind") or "unknown_item")


def _changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(_changed_paths(before[key], after[key], path))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        paths = []
        if len(before) != len(after):
            paths.append(f"{prefix}.length")
        for index, (old, new) in enumerate(zip(before, after)):
            paths.extend(_changed_paths(old, new, f"{prefix}[{index}]"))
        return paths
    return [] if before == after else [prefix or "$value"]


def worksheet_item_diff(regenerated: dict[str, Any], signed: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe item-level context changes without exporting patient identifiers."""
    def group(value: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        items = value.get("items", [])
        result: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            if isinstance(item, dict):
                result.setdefault(_item_label(item), []).append(item)
        return result

    fresh, prior = group(regenerated), group(signed)
    differences: list[dict[str, Any]] = []
    for label in sorted(set(fresh) | set(prior)):
        current = fresh.get(label, [])
        old = prior.get(label, [])
        if current == old:
            continue
        changed_fields = sorted({path for index in range(max(len(old), len(current)))
                                 for path in (_changed_paths(old[index], current[index])
                                              if index < len(old) and index < len(current)
                                              else ["item_count"])})
        current_statuses = sorted(str(row.get("prefilled_decision", {}).get("status", row.get("status", "")))
                                  for row in current)
        old_statuses = sorted(str(row.get("prefilled_decision", {}).get("status", row.get("status", "")))
                              for row in old)
        differences.append({"item": label, "signed_count": len(old), "regenerated_count": len(current),
                            "changed_fields": changed_fields, "signed_statuses": old_statuses,
                            "regenerated_statuses": current_statuses,
                            "signed_evidence_pointer_counts": sorted(len(row.get("evidence_pointers", []))
                                                                      for row in old),
                            "regenerated_evidence_pointer_counts": sorted(len(row.get("evidence_pointers", []))
                                                                          for row in current)})
    return differences


def run_fresh_signed_admission(cohort: str, branch: str, store_root: Path,
                               field_map: dict[str, Any], v3_receipt_path: Path,
                               worksheet: dict[str, Any], output_dir: Path, *,
                               schemas: SchemaStore | None = None) -> dict[str, Any]:
    """Re-ingest pinned objects, rebuild branch context, then stop on stale signatures."""
    if field_map.get("status") == "PARKED":
        raise ValueError("Cohort is PARKED: " + field_map["parked_reason"])
    if field_map.get('decision_config', {}).get('family_protection', {}).get('status') == 'UNTOUCHED_FINAL_TEST':
        raise DavError('UNTOUCHED_FINAL_TEST_PROTECTED', blocked=True)
    if (field_map.get('decision_config', {}).get('representation_restrictions', {}).get('development_only')
            and field_map.get('decision_config', {}).get('preview', {}).get('split_policy') != 'DEVELOPMENT'):
        raise DavError('DEVELOPMENT_ONLY_REPRESENTATION', blocked=True)
    if field_map.get('decision_config', {}).get('preview', {}).get('author_endpoint_join') == 'UNRESOLVED':
        raise DavError('AUTHOR_ENDPOINT_JOIN_UNRESOLVED', blocked=True)
    store = schemas or SchemaStore()
    output = validate_output_path(output_dir)
    if output.exists():
        raise DavError("OUTPUT_ALREADY_EXISTS")
    output.mkdir(parents=True, exist_ok=False)
    ingest_result = run_ingest(cohort, branch, store_root, output / "fresh-ingest")
    candidate = (build_baseline_packet(ingest_result["packet"], field_map=field_map)
                 if "geo_ingest" in field_map or "cbio_ingest" in field_map else build_baseline_packet(ingest_result["packet"]))
    try:
        receipt = json.loads(v3_receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise DavError("V3_RECEIPT_INVALID") from None
    candidate = materialize_primary_assay_policy(candidate, field_map, receipt, store_root)
    # The review context describes unsigned proposals. Signer decisions are applied
    # only after the frozen context and signature have been validated.
    candidate = materialize_configured_proposals(candidate, field_map)
    regenerated = build_worksheet(candidate)
    if regenerated.get("context_hash") != worksheet.get("context_hash"):
        differences = worksheet_item_diff(regenerated, worksheet)
        preflight = output / "pre-admission"
        preflight.mkdir(exist_ok=True)
        _write_json(preflight / "review_packet.json", candidate)
        _write_json(preflight / "reviewer_worksheet.regenerated.json", regenerated)
        _write_json(preflight / "worksheet_context_diff.json", {
            "status": "WORKSHEET_CONTEXT_MISMATCH",
            "signed_context_hash": worksheet.get("context_hash"),
            "regenerated_context_hash": regenerated.get("context_hash"),
            "changed_items": differences,
        })
        return {"status": "WORKSHEET_CONTEXT_MISMATCH", "changed_items": differences,
                "packet": candidate, "worksheet": regenerated}
    ingestion_validation = ingest_result["packet"]["config"].get("ingestion_validation", {})
    return run_signed_admission(candidate, field_map, worksheet, output, schemas=store,
                                ingestion_validation=ingestion_validation, store_root=store_root, v3_receipt=receipt)


def run_fresh_provisional(cohort: str, branch: str, store_root: Path, field_map: dict[str, Any],
                          v3_receipt_path: Path, output_dir: Path,
                          worksheet: dict[str, Any] | None = None) -> dict[str, Any]:
    from .provisional import run_provisional
    if field_map.get("status") == "PARKED":
        raise ValueError("Cohort is PARKED: " + field_map["parked_reason"])
    if field_map.get('decision_config', {}).get('family_protection', {}).get('status') == 'UNTOUCHED_FINAL_TEST':
        raise DavError('UNTOUCHED_FINAL_TEST_PROTECTED', blocked=True)
    output = validate_output_path(output_dir)
    if output.exists():
        raise DavError("OUTPUT_ALREADY_EXISTS")
    output.mkdir(parents=True)
    ingested = run_ingest(cohort, branch, store_root, output / "fresh-ingest")
    if 'cbio_ingest' in field_map or 'geo_ingest' in field_map:
        from .provisional import add_v3_blocker_item, add_v3_exclusion_item, cbio_preview_blockers
        receipt = json.loads(v3_receipt_path.read_text(encoding='utf-8'))
        ingested['packet'] = add_v3_exclusion_item(ingested['packet'], receipt)
        ingested['worksheet'] = build_worksheet(ingested['packet'])
        reasons = cbio_preview_blockers(field_map, receipt)
        if reasons:
            ingested['packet'] = add_v3_blocker_item(ingested['packet'], receipt)
            ingested['worksheet'] = build_worksheet(ingested['packet'])
            result = {'status':'BLOCKED_UNKNOWN', 'releasable':False, 'reasons':reasons}
            _write_json(output / 'PROVISIONAL.json', result)
            _write_json(output / 'reviewer_worksheet.unsigned.json', ingested['worksheet'])
            return result
    packet = (build_baseline_packet(ingested["packet"], field_map=field_map)
              if "geo_ingest" in field_map or "cbio_ingest" in field_map else build_baseline_packet(ingested["packet"]))
    receipt = json.loads(v3_receipt_path.read_text(encoding="utf-8"))
    packet = materialize_primary_assay_policy(packet, field_map, receipt, store_root, provisional=True)
    packet = materialize_configured_proposals(packet, field_map)
    ensure_field_map_matches(packet, field_map)
    return run_provisional(packet, field_map, store_root, output, worksheet=worksheet, v3_receipt=receipt)


def run_signed_admission(packet: dict[str, Any], field_map: dict[str, Any],
                         worksheet: dict[str, Any], output_dir: Path, *,
                         schemas: SchemaStore | None = None,
                         ingestion_validation: dict[str, Any] | None = None,
                         store_root: Path | None = None,
                         v3_receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the signature, materialize declared proposals, and preserve live receipts."""
    if field_map.get("status") == "PARKED":
        raise ValueError("Cohort is PARKED: " + field_map["parked_reason"])
    if field_map.get('decision_config', {}).get('family_protection', {}).get('status') == 'UNTOUCHED_FINAL_TEST':
        raise DavError('UNTOUCHED_FINAL_TEST_PROTECTED', blocked=True)
    if field_map.get('decision_config', {}).get('representation_restrictions', {}).get('development_only'):
        declared = field_map.get('decision_config', {}).get('preview', {}).get('split_policy')
        packet_role = packet.get('config', {}).get('split', {}).get('policy', {}).get('permanent_role')
        if declared != 'DEVELOPMENT' or packet_role not in (None, 'DEVELOPMENT'):
            raise DavError('DEVELOPMENT_ONLY_REPRESENTATION', blocked=True)
    if field_map.get('decision_config', {}).get('preview', {}).get('author_endpoint_join') == 'UNRESOLVED':
        raise DavError('AUTHOR_ENDPOINT_JOIN_UNRESOLVED', blocked=True)
    store = schemas or SchemaStore()
    ensure_field_map_matches(packet, field_map)
    validate_signed_worksheet(packet, worksheet)
    signature = validate_signed_worksheet(packet, worksheet)
    declaration = field_map.get("proposal_generation", {})
    current = (packet if not declaration and ('geo_ingest' in field_map or 'cbio_ingest' in field_map) else
               materialize_proposals(packet, declaration, reviewer_worksheet=worksheet, schemas=store))
    decisions_by_gate = {item["gate"]: signature["decisions"].get(item["item_id"])
                         for item in worksheet.get("items", []) if item.get("kind") == "gate"}
    if 'cbio_ingest' in field_map and store_root is not None:
        current = verify_signed_cbio_identities(packet, field_map, worksheet, store_root)
        bound = verify_signed_cbio_outcome_bindings(packet, field_map, worksheet)
        for name in ('episode_binding', 'treatment_episode', 'treatment_exposure'):
            current['records'][name] = bound['records'].get(name, [])
        if 'timing' in bound['config']:
            current['config']['timing'] = bound['config']['timing']
        endpoints = materialize_signed_cbio_endpoints(packet, worksheet)
        current['records']['clinical_outcome'] = endpoints['records'].get('clinical_outcome', [])
        overlap = materialize_signed_cbio_overlap(packet, field_map, worksheet)
        if 'overlap' in overlap['config']:
            current['config']['overlap'] = overlap['config']['overlap']
            current['records']['overlap_edge'] = overlap['records'].get('overlap_edge', [])
        admission_policy = materialize_signed_cbio_admission(packet, field_map, worksheet)
        current['config']['admission'] = admission_policy['config'].get('admission', {})
        development = materialize_signed_cbio_development(packet, field_map, worksheet)
        if 'split' in development['config']:
            current['records']['prior_exposure_record'] = development['records'].get('prior_exposure_record', [])
            for name in ('exposure', 'split', 'baseline'):
                current['config'][name] = development['config'][name]
            current['config']['split']['required_source_ids'] = current['config']['admission'].get('required_source_object_ids', [])
            current['config'].setdefault('timing', {})['prior_ici_policy'] = development['config'].get('timing', {}).get('prior_ici_policy')
            retained = {row['specimen_uid'] for row in development['records'].get('specimen_registry', [])}
            eligible_patients = {row['patient_uid'] for row in development['records'].get('patient_registry', [])}
            current['records']['patient_registry'] = [row for row in current['records'].get('patient_registry', []) if row['patient_uid'] in eligible_patients]
            declared_patients = {row['patient_uid']:row for row in development['records'].get('patient_registry', [])}
            for patient in current['records']['patient_registry']:
                declared_patient = declared_patients.get(patient['patient_uid'], {})
                if declared_patient.get('cancer') and not patient.get('cancer'):
                    patient['cancer'] = declared_patient['cancer']
                    patient['source_locators'] = declared_patient.get('source_locators', patient.get('source_locators', [])) + [
                        loc for loc in patient.get('source_locators', []) if loc.get('kind') in {'worksheet','field_map'}]
            for name in ('clinical_outcome','treatment_episode','treatment_exposure','episode_binding'):
                current['records'][name] = [row for row in current['records'].get(name, []) if row.get('patient_uid') in eligible_patients]
            retain_endpoint_source_priority(current['config']['endpoints'], current['records']['clinical_outcome'])
            timing_config = current['config'].get('timing', {})
            retained_episodes = {row['treatment_episode_id'] for row in current['records'].get('treatment_episode', [])}
            timing_config['episode_order'] = [value for value in timing_config.get('episode_order', []) if value in retained_episodes]
            current['records']['specimen_registry'] = [row for row in current['records'].get('specimen_registry', []) if row['specimen_uid'] in retained]
            current['records']['assay_registry'] = development['records'].get('assay_registry', [])
            current['records']['episode_binding'] = [b for b in current['records'].get('episode_binding', []) if b['subject_type'] != 'SPECIMEN' or b['subject_id'] in retained]
            current['config']['assays'] = development['config'].get('assays', {})
    if not declaration and 'geo_ingest' in field_map and store_root is not None:
        current = verify_signed_geo_identities(packet, field_map, worksheet, store_root)
        bound = verify_signed_geo_outcome_bindings(packet, field_map, worksheet)
        current['records']['episode_binding'] = bound['records'].get('episode_binding', [])
        current['records']['treatment_episode'] = bound['records'].get('treatment_episode', [])
        current['records']['treatment_exposure'] = bound['records'].get('treatment_exposure', [])
        current['config']['timing'] = bound['config'].get('timing', {})
        endpoints = materialize_signed_geo_endpoints(packet, field_map, worksheet)
        current['records']['clinical_outcome'] = endpoints['records'].get('clinical_outcome', [])
        current['config']['endpoints'] = endpoints['config'].get('endpoints', {})
        overlap = materialize_signed_geo_overlap(packet, field_map, worksheet)
        current['records']['overlap_edge'] = overlap['records'].get('overlap_edge', [])
        if 'overlap' in overlap['config']:
            current['config']['overlap'] = overlap['config']['overlap']
        admission_policy = materialize_signed_geo_admission_policy(packet, field_map, worksheet)
        current['config']['admission'] = admission_policy['config'].get('admission', {})
        # Validate against the original signed context, then apply the reviewed declarations.
        development = materialize_signed_geo_development_policy(packet, field_map, worksheet)
        for name in ('prior_exposure_record',):
            if name in development['records']:
                current['records'][name] = development['records'][name]
        if 'split' in development['config']:
            signed_patients = {p['patient_uid']:p for p in development['records'].get('patient_registry', [])}
            for patient in current['records'].get('patient_registry', []):
                declared_patient = signed_patients.get(patient['patient_uid'], {})
                if not patient.get('cancer') and declared_patient.get('cancer'):
                    patient['cancer'] = declared_patient['cancer']
                    patient.setdefault('source_locators', []).append({'kind':'decision', 'value':field_map['decision_config']['development_policy']['cancer_source_locator']})
        for name in ('exposure', 'split', 'baseline'):
            if name in development['config']:
                current['config'][name] = development['config'][name]
        if 'split' in development['config']:
            current['config']['split']['required_source_ids'] = current['config']['admission'].get('required_source_object_ids', [])
        if development['config'].get('timing', {}).get('prior_ici_policy'):
            current['config']['timing']['prior_ici_policy'] = development['config']['timing']['prior_ici_policy']
        if 'baseline' in development['config']:
            current['records']['assay_registry'] = development['records']['assay_registry']
        if field_map.get('decision_config', {}).get('development_policy', {}).get('nonbaseline_specimens') == 'OUTSIDE_BRANCH' and 'split' in development['config']:
            retained = {s['specimen_uid'] for s in development['records']['specimen_registry']}
            current['records']['specimen_registry'] = development['records']['specimen_registry']
            current['records']['assay_registry'] = development['records']['assay_registry']
            current['records']['episode_binding'] = [b for b in current['records']['episode_binding'] if b['subject_type'] != 'SPECIMEN' or b['subject_id'] in retained]
            current['config']['assays'] = development['config']['assays']
    current = certify_required_source_validation(current, field_map, decisions_by_gate,
                                                 ingestion_validation)
    chain_options: dict[str, Any] = {'reviewer_worksheet': worksheet, 'worksheet_context_packet': packet, 'schemas': store}
    if not declaration and ('geo_ingest' in field_map or 'cbio_ingest' in field_map):
        chain_options['collect_blockers'] = True
    result = run_admission_chain(current, declaration, **chain_options)
    statuses = result["stage_statuses"]
    admission = result["admission"]
    matrix: dict[str, Any] | None = None
    if admission["status"] == "READY":
        matrix = attempt_baseline_build(result["packet"], schemas=store)
        matrix_status = matrix["status"]
        statuses.append({"stage": "split", "status": (matrix.get("split") or {}).get("status", matrix_status),
                         "reasons": (matrix.get("split") or {}).get("reasons", matrix["reasons"])})
        if "baseline" in matrix:
            statuses.append({"stage": "baseline", "status": matrix["baseline"]["status"],
                             "reasons": matrix["baseline"]["reasons"]})

    try:
        output = validate_output_path(output_dir)
    except IngestError as error:
        raise DavError(str(error)) from None
    output.mkdir(parents=True, exist_ok=True)
    products = None
    if matrix is not None and matrix.get('baseline', {}).get('status') == 'READY':
        if store_root is None:
            matrix['status'] = 'BLOCKED_UNKNOWN'
            matrix['reasons'] = ['SOURCE_STORE_MISSING']
        else:
            from .expression_materialization import write_validated_products
            source_hash = result['packet']['config']['assays']['matrices'][0]['source_sha256']
            roles = [role for role, source in field_map['source_objects'].items() if source.get('sha256') == source_hash]
            if len(roles) != 1:
                raise DavError('HASH_OR_VERSION_MISMATCH')
            role = roles[0]
            receipt_key = next((key for key, value in field_map.get('v3', {}).get('source_object_roles', {}).items() if value == role), None)
            excluded_rows = (v3_receipt or {}).get('checks', {}).get(receipt_key, {}).get('object_derived_evidence', {}).get('excluded_rows', [])
            product_packet = copy.deepcopy(result['packet'])
            product_packet['records'] = matrix['baseline']['records']
            product_packet['dependencies']['split'] = matrix['split']
            product_packet['dependencies']['baseline'] = matrix['baseline']
            products = write_validated_products(product_packet, store_root, source_hash, output / 'products',
                                                delimiter=field_map['v3']['delimiters'][role],
                                                compressed=field_map['v3']['compressed'][role],
                                                orientation=field_map.get('measurement_representations', {}).get(role, {}).get('orientation', 'samples_as_columns'),
                                                source_format=field_map['source_objects'][role].get('format', 'MATRIX_HEADER_CSV'),
                                                missing_policy=field_map.get('measurement_representations', {}).get(role, {}).get('missing_policy', 'BLOCK'),
                                                excluded_feature_rows=excluded_rows,
                                                auxiliary_columns=field_map.get('measurement_representations', {}).get(role, {}).get('auxiliary_columns'))
    _write_json(output / "review_packet.json", result["packet"])
    _write_json(output / "stage_statuses.json", statuses)
    _write_json(output / "admission.json", admission)
    if matrix is not None:
        private_matrix = matrix.get("baseline")
        if isinstance(private_matrix, dict):
            _write_json(output / "baseline_matrix.json", private_matrix["records"].get("baseline", []))
            rows = private_matrix["records"].get("baseline", [])
            duplicate_patients = len(rows) - len({row.get("patient_uid") for row in rows})
            eligible = [row for row in rows if row.get("inclusion_status") == "INCLUDED"]
            _write_json(output / "matrix_contract.json", {
                "status": "PASS" if duplicate_patients == 0 else "FAIL",
                "row_count": len(rows), "eligible_row_count": len(eligible),
                "duplicate_patient_rows": duplicate_patients,
                "checks": {"one_row_per_patient": "PASS" if duplicate_patients == 0 else "FAIL",
                           "branch_matches": "PASS" if all(row.get("branch_id") == result["packet"]["branch_id"] for row in rows) else "FAIL",
                           "patient_rows_match_registry": "PASS" if len(rows) == len(result["packet"]["records"].get("patient_registry", [])) else "FAIL"},
            })
    summary = {"admission_status": admission["status"], "admission_reasons": admission["reasons"],
               "stages": statuses,
               "matrix_status": matrix["status"] if matrix is not None else "NOT_RUN"}
    _write_json(output / "SUMMARY.json", summary)
    result["stage_statuses"] = statuses
    result["matrix"] = matrix
    result["products"] = products
    return result


def _read_packet(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise DavError("MALFORMED_INPUT") from None
    if not isinstance(value, dict):
        raise DavError("MALFORMED_INPUT")
    return cast(dict[str, Any], value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, help="prepared branch packet; omit for a fresh local ingest")
    parser.add_argument("--cohort", help="field-map cohort for a fresh local ingest")
    parser.add_argument("--branch", help="branch for a fresh local ingest")
    parser.add_argument("--store", type=Path, help="local content-addressed object store")
    parser.add_argument("--v3-receipt", type=Path, help="validated local V3 receipt")
    parser.add_argument("--worksheet", type=Path)
    parser.add_argument("--provisional", action="store_true", help="build an unsigned, non-releasable preview")
    parser.add_argument("--field-map", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        from .field_maps import load_field_map
        field_map = load_field_map(args.field_map)
        if field_map.get("status") == "PARKED":
            raise ValueError("Cohort is PARKED: " + field_map["parked_reason"])
        worksheet = read_worksheet(args.worksheet) if args.worksheet else None
        if args.provisional:
            if args.packet is not None or not all((args.cohort, args.branch, args.store, args.v3_receipt)):
                parser.error("PROVISIONAL_REQUIRES_FRESH_INGEST")
            if args.cohort != field_map.get("cohort") or args.branch != field_map.get("branch_id"):
                parser.error("COHORT_BRANCH_MISMATCH")
            run_fresh_provisional(args.cohort, args.branch, args.store, field_map,
                                  args.v3_receipt, args.out, worksheet)
            return 0
        if worksheet is None:
            parser.error("SIGNED_WORKSHEET_REQUIRED")
        if args.packet is not None:
            packet = _read_packet(args.packet)
            result = run_signed_admission(packet, field_map, worksheet, args.out, store_root=args.store)
        else:
            if not all((args.cohort, args.branch, args.store, args.v3_receipt)):
                parser.error("FRESH_INGEST_REQUIRES_COHORT_BRANCH_STORE_AND_V3_RECEIPT")
            if args.cohort != field_map.get("cohort") or args.branch != field_map.get("branch_id"):
                parser.error("COHORT_BRANCH_MISMATCH")
            result = run_fresh_signed_admission(args.cohort, args.branch, args.store, field_map,
                                                args.v3_receipt, worksheet, args.out)
            if result.get("status") == "WORKSHEET_CONTEXT_MISMATCH":
                print(json.dumps({"status": result["status"], "changed_items": result["changed_items"]},
                                 sort_keys=True))
                return 2
        if (result.get('admission', {}).get('status') != 'READY' or
                not isinstance(result.get('matrix'), dict) or result['matrix'].get('status') != 'READY' or
                result.get('products') is None):
            return 2
    except (DavError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
