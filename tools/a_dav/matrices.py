"""Outcome-blind synthetic materialized views; canonical assertions stay immutable."""
from __future__ import annotations
import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from .core import DavError, SchemaStore, canonical_bytes, dependency, digest, finish, require, stage_boundary

REASON_CODES = frozenset({'SELECTION_TIE', 'SELECTION_POLICY_UNKNOWN', 'NO_PRE_INDEX_SPECIMEN',
    'NO_FOLLOWUP_IN_WINDOW', 'LESION_MISMATCH', 'PLATFORM_MISMATCH', 'MEASUREMENT_SCALE_INCOMPATIBLE',
    'AFTER_REGIMEN_CHANGE', 'PROGRESSION_MIXED_WITH_SCHEDULED_ON', 'EPISODE_AMBIGUOUS',
    'EPISODE_MISMATCH', 'ENDPOINT_UNKNOWN', 'SOURCE_NOT_ELIGIBLE', 'ASSAY_UNSUITABLE',
    'SPLIT_NOT_FROZEN', 'BASELINE_INELIGIBLE', 'BASELINE_ELIGIBILITY_UNKNOWN', 'COMPARTMENT_INELIGIBLE', 'SPECIMEN_POLICY_UNKNOWN', 'TIMING_UNKNOWN', 'LOWER_RANK', 'NOT_BASELINE', 'SYNTHETIC_BUILD_DRAFT', 'PATIENT_EXCLUDED', 'PATIENT_UNKNOWN','ASSAY_EVIDENCE_UNKNOWN','ASSAY_EVIDENCE_CONFLICT'})


def _prepare(packet: dict[str, Any], store: SchemaStore) -> tuple[dict[str, Any], dict[str, Any]]:
    deps = {name: dependency(packet, name, store) for name in
            ('admission', 'registries', 'endpoints', 'timing', 'assays', 'split', 'exposure')}
    return copy.deepcopy(packet['records']), deps


def _eligible_sources(deps: dict[str,Any], store: SchemaStore) -> set[tuple[str,str]]:
    sources: set[tuple[str,str]]=set()
    drafts=deps['admission']['records'].get('cohort_admission_receipt',[])
    for draft in drafts:
        store.validate('cohort_admission_receipt',draft)
        synthetic_candidate = (deps['admission'].get('classification') == 'SYNTHETIC_ONLY' and
                              draft.get('branch_id') == deps['admission']['branch_id'])
        approved_real = (deps['admission']['branch_id'] in draft.get('approved_branches', []) and
                draft.get('admission_status') in {'ADMITTED', 'ADMITTED_WITH_LIMITATIONS', 'SENSITIVITY_ONLY'})
        if synthetic_candidate or approved_real:
            sources.update((draft['study_id'],source) for source in draft['source_object_ids'])
    return sources


def _episode(records: dict[str, Any], patient: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in records.get('treatment_episode', []) if r['patient_uid'] == patient['patient_uid']]
    selected = cfg.get('index_episode_by_patient', {}).get(patient['patient_uid'])
    if selected is not None:
        rows = [r for r in rows if r['treatment_episode_id'] == selected]
    require(len(rows) == 1, 'EPISODE_AMBIGUOUS', blocked=True)
    ep: dict[str, Any] = rows[0]
    require(ep['study_id'] == patient['study_id'], 'EPISODE_MISMATCH')
    require(ep['episode_status'] == 'VERIFIED', 'TIMING_UNKNOWN', blocked=True)
    return ep


def _policy(packet: dict[str,Any], stage: str, deps: dict[str,Any], store: SchemaStore) -> dict[str,Any]:
    cfg=dict(packet['config'].get(stage,{}))
    require(cfg.get('selection_basis')=='PRESPECIFIED_METADATA','SELECTION_POLICY_UNKNOWN',blocked=True)
    require(isinstance(cfg.get('specimen_rank'),dict) and isinstance(cfg.get('assay_rank'),dict),'SELECTION_POLICY_UNKNOWN',blocked=True)
    require(all(type(v) is int and v>=0 for ranks in (cfg['specimen_rank'],cfg['assay_rank']) for v in ranks.values()),'SELECTION_POLICY_UNKNOWN')
    require(isinstance(cfg.get('build_utc'),str) and bool(cfg['build_utc']),'SELECTION_POLICY_UNKNOWN',blocked=True)
    require(cfg.get('assay_suitability') in {'BASELINE_DE','LONGITUDINAL','BASELINE_SCORING','PREDICTION_DEVELOPMENT',
            'OUTER_VALIDATION','FINAL_TEST','METHYLATION','PROTEIN','SINGLE_CELL','SPATIAL'} and
            cfg.get('coverage_suitability') in {'de_suitability','scoring_suitability','final_test_suitability','measurement_suitability'},
            'SELECTION_POLICY_UNKNOWN',blocked=True)
    named_requirements={'BASELINE_DE':'de_suitability','BASELINE_SCORING':'scoring_suitability','FINAL_TEST':'final_test_suitability'}
    if cfg['assay_suitability'] in named_requirements:
        require(cfg['coverage_suitability']==named_requirements[cfg['assay_suitability']],'SELECTION_POLICY_UNKNOWN')
    endpoint_policy=cfg.get('endpoint_policy',{})
    require(type(endpoint_policy.get('required')) is bool and endpoint_policy.get('discrepancy_policy')=='SEALED_PREFERRED_OUTCOME',
            'SELECTION_POLICY_UNKNOWN',blocked=True)
    require(endpoint_policy.get('endpoint_class') in {'ORR','DCR','DCB','PSA_RESPONSE','PATHOLOGICAL_RESPONSE','PFS','OS','SOURCE_BINARY_UNKNOWN','OTHER'}
            if endpoint_policy['required'] else endpoint_policy.get('endpoint_class') is None,'SELECTION_POLICY_UNKNOWN',blocked=True)
    require(stage!='baseline' or endpoint_policy['required'],'SELECTION_POLICY_UNKNOWN',blocked=True)
    cfg['_baseline_compartments'] = (['TUMOUR'] if packet['branch_id'] in {'A_BASELINE_BIO',
        'A_P2_DEVELOPMENT', 'A_P2_OUTER_VALIDATION', 'A_P2_FINAL_TEST'} else cfg.get('baseline_compartments'))
    cfg['_eligible_sources']=_eligible_sources(deps,store)
    contexts: dict[tuple[str,str],dict[str,Any]]={}
    bindings={(b['subject_id'],b['treatment_episode_id']):b for b in packet['records'].get('episode_binding',[]) if b['subject_type']=='SPECIMEN'}
    require(len(bindings)==sum(b['subject_type']=='SPECIMEN' for b in packet['records'].get('episode_binding',[])), 'EPISODE_AMBIGUOUS')
    for row in deps['timing']['audit']:
        if row.get('check')!='TIMING_ASSERTION':continue
        key=(row['specimen_uid'],row['treatment_episode_id'])
        require(key not in contexts and key in bindings,'EPISODE_AMBIGUOUS')
        binding=bindings[key]
        require(row.get('binding_id')==binding['binding_id'] and row.get('role')==binding['role'],'EPISODE_MISMATCH')
        require(binding['binding_status']=='VERIFIED','TIMING_UNKNOWN',blocked=True)
        contexts[key]=row
    require(set(bindings)<=set(contexts),'TIMING_UNKNOWN',blocked=True)
    cfg['_contexts']=contexts;cfg['_bindings']=bindings
    cfg['_roles'] = {r['patient_uid']: r['permanent_role'] for r in deps['split']['records'].get('split', [])}
    cfg['_exposure'] = {r['patient_uid']: r['exposure_state'] for r in deps['split']['audit'] if r.get('kind') == 'PATIENT_LEDGER'}
    require(set(cfg['_roles']) == {r['patient_uid'] for r in packet['records'].get('patient_registry', [])}
            and set(cfg['_exposure']) == set(cfg['_roles']), 'SPLIT_NOT_FROZEN', blocked=True)
    coverage: dict[str,dict[str,Any]]={}
    for row in deps['assays']['records'].get('coverage',[]):
        store.validate('coverage',row)
        if row['branch_id']!=packet['branch_id']:continue
        require(row['assay_uid'] not in coverage,'DUPLICATE_ID')
        coverage[row['assay_uid']]=row
    cfg['_coverage']=coverage
    return cfg


def _candidates(records: dict[str,Any], patient: dict[str,Any], ep: dict[str,Any], cfg: dict[str,Any],
                *, baseline: bool, audit: list[dict[str,Any]]) -> list[tuple[dict[str,Any],dict[str,Any]]]:
    selected=[]
    for sp in records.get('specimen_registry',[]):
        if sp['patient_uid']!=patient['patient_uid']:continue
        key=(sp['specimen_uid'],ep['treatment_episode_id']);binding=cfg['_bindings'].get(key)
        timing=cfg['_contexts'].get(key)
        if binding is not None:require(binding['patient_uid']==patient['patient_uid'],'EPISODE_MISMATCH')
        assays=[a for a in records.get('assay_registry',[]) if a['specimen_uid']==sp['specimen_uid']]
        for assay in assays or [None]:
            reason=None
            coverage=cfg['_coverage'].get(assay['assay_uid']) if assay else None
            if patient['inclusion_state']=='EXCLUDED' or cfg['_roles'][patient['patient_uid']]=='EXCLUDED':reason='PATIENT_EXCLUDED'
            elif patient['inclusion_state']=='BLOCKED_UNKNOWN':reason='PATIENT_UNKNOWN'
            elif binding is None or timing is None:reason='EPISODE_MISMATCH'
            elif assay is None:reason='ASSAY_UNSUITABLE'
            elif (patient['study_id'],assay['source_object_id']) not in cfg['_eligible_sources']:reason='SOURCE_NOT_ELIGIBLE'
            elif baseline and (timing['canonical_category']!='PRE_INDEX_BASELINE' or binding['role']!='PRE_INDEX_BASELINE'):reason='NOT_BASELINE'
            elif baseline and sp['baseline_candidate_status']=='NO':reason='BASELINE_INELIGIBLE'
            elif baseline and sp['baseline_candidate_status']!='YES':reason='BASELINE_ELIGIBILITY_UNKNOWN'
            elif baseline and not cfg['_baseline_compartments']:reason='SPECIMEN_POLICY_UNKNOWN'
            elif baseline and sp['biological_compartment'] not in cfg['_baseline_compartments']:reason='COMPARTMENT_INELIGIBLE'
            elif assay['qc_status']!='PASS' or cfg['assay_suitability'] not in assay['branch_suitability']:reason='ASSAY_UNSUITABLE'
            elif coverage is None:reason='ASSAY_EVIDENCE_UNKNOWN'
            else:
                require(coverage['study_id']==patient['study_id'] and coverage['source_object_id']==assay['source_object_id']
                        and coverage['expression_unit']==assay['measurement_unit'] and coverage['annotation_version']==assay.get('feature_annotation'), 'ASSAY_EVIDENCE_CONFLICT')
                state=coverage[cfg['coverage_suitability']]
                if state!='PASS':reason='ASSAY_UNSUITABLE' if state=='FAIL' else 'ASSAY_EVIDENCE_UNKNOWN'
                elif not assay.get('matrix_header') or not assay.get('feature_annotation'):reason='ASSAY_UNSUITABLE'
            audit.append({'kind':'CANDIDATE','patient_uid':patient['patient_uid'],'treatment_episode_id':ep['treatment_episode_id'],
                          'specimen_uid':sp['specimen_uid'],'assay_uid':assay['assay_uid'] if assay else None,'reason':reason or 'LOWER_RANK'})
            if reason is None and assay is not None:selected.append((sp,assay))
    return selected


def _endpoint(records: dict[str,Any], patient: dict[str,Any], ep: dict[str,Any], cfg: dict[str,Any],
              deps: dict[str,Any], store: SchemaStore, *, endpoint_class: str | None = None,
              optional: bool = False) -> dict[str,Any]:
    policy=cfg['endpoint_policy']
    absent={'outcome_id':None,'endpoint_class':None,'raw_value':None,'assessment_system':None,
            'assessment_day':None,'canonical_category':'NOT_APPLICABLE','binary_value':None,'evaluability':'UNKNOWN'}
    if not policy['required']:return absent
    selected_class=endpoint_class or policy['endpoint_class']
    rows=[r for r in records.get('endpoint',[]) if r['patient_uid']==patient['patient_uid']
          and r['treatment_episode_id']==ep['treatment_episode_id'] and r['endpoint_class']==selected_class]
    if optional and not rows:return absent
    for row in rows:store.validate('endpoint',row)
    if len(rows)>1:
        adjudications=[a for a in deps['endpoints']['audit'] if a.get('check')=='DISCREPANCY_RETAINED'
            and a.get('patient_uid')==patient['patient_uid'] and a.get('treatment_episode_id')==ep['treatment_episode_id']]
        require(len(adjudications)==1,'ENDPOINT_UNKNOWN',blocked=True)
        chosen=adjudications[0]
        require({r['outcome_id'] for r in rows}<=set(chosen.get('all_outcome_ids',[])), 'ENDPOINT_UNKNOWN')
        rows=[r for r in rows if r['outcome_id']==chosen['preferred_outcome_id']]
    require(len(rows)==1,'ENDPOINT_UNKNOWN',blocked=True)
    return dict(rows[0])


def _blocked_tie(stage: str, packet: dict[str,Any], records: dict[str,Any], audit: list[dict[str,Any]],
                 error: DavError, store: SchemaStore) -> dict[str,Any]:
    if error.code!='SELECTION_TIE':raise error
    return finish(stage,packet,records,status='BLOCKED_UNKNOWN',reasons=[error.code],audit=audit,schemas=store)

def _choose(candidates: list[tuple[dict[str, Any], dict[str, Any]]], cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not candidates: return None
    ranked = []
    for sp, assay in candidates:
        require(sp['specimen_uid'] in cfg['specimen_rank'] and assay['assay_uid'] in cfg['assay_rank'],
                'SELECTION_POLICY_UNKNOWN', blocked=True)
        ranked.append(((cfg['specimen_rank'][sp['specimen_uid']],cfg['assay_rank'][assay['assay_uid']]),sp,assay))
    best = min(row[0] for row in ranked)
    winners = [(sp,a) for rank,sp,a in ranked if rank == best]
    require(len(winners) == 1, 'SELECTION_TIE', blocked=True)
    return winners[0]


def _draft(stage: str, packet: dict[str, Any], records: dict[str, Any], deps: dict[str, Any],
           cfg: dict[str, Any], store: SchemaStore, build_id: str) -> dict[str, Any]:
    row = {'matrix_build_receipt_id':build_id,'matrix_id':'synthetic-'+stage,'branch_id':packet['branch_id'],
           'schema_version_used':'1.1.0','source_admission_receipt_ids':[deps['admission']['receipt_id']],
           'patient_count':len(records.get('patient_registry',[])),
           'input_hashes':sorted(v['receipt_id'] for v in deps.values()),
           'code_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'config_hash':digest(packet['config']),'output_hash':digest({k:sorted(v,key=canonical_bytes) for k,v in records.items()}),
           'build_utc':datetime.now(timezone.utc).isoformat() if cfg['build_utc']=='AT_BUILD_TIME' else cfg['build_utc'],
           'test_status':'NOT_RUN','validation_status':'BLOCKED_UNKNOWN'}
    store.validate('matrix_build_receipt',row)
    return row

@stage_boundary('baseline')
def build_baseline(packet: dict[str,Any], *, schemas: SchemaStore | None = None) -> dict[str,Any]:
    store=schemas or SchemaStore();records,deps=_prepare(packet,store);cfg=_policy(packet,'baseline',deps,store)
    audit: list[dict[str,Any]]=[];rows=[]
    build_id='synthetic-baseline-'+digest([packet['config'],deps['admission']['receipt_id']])[:20]
    for patient in records.get('patient_registry',[]):
        ep=_episode(records,patient,cfg)
        try:chosen=_choose(_candidates(records,patient,ep,cfg,baseline=True,audit=audit),cfg)
        except DavError as exc:return _blocked_tie('baseline',packet,records,audit,exc,store)
        endpoint=_endpoint(records,patient,ep,cfg,deps,store)
        dcr=_endpoint(records,patient,ep,cfg,deps,store,endpoint_class='DCR',optional=True) if endpoint['endpoint_class']=='ORR' else {}
        sp,assay=chosen if chosen else ({},{})
        included=chosen is not None and endpoint['evaluability']=='EVALUABLE'
        require(patient.get('cancer'),'MISSING_ASSERTION',blocked=True)
        reason=None if included else 'PATIENT_EXCLUDED' if patient['inclusion_state']=='EXCLUDED' or cfg['_roles'][patient['patient_uid']]=='EXCLUDED' else 'PATIENT_UNKNOWN' if patient['inclusion_state']=='BLOCKED_UNKNOWN' else 'NO_PRE_INDEX_SPECIMEN' if chosen is None else 'ENDPOINT_UNKNOWN'
        row={'row_type':'BASELINE','schema_version':'1.1.0','data_classification':packet['classification'],
            'patient_uid':patient['patient_uid'],'study_id':patient['study_id'],'cancer':patient['cancer'],'subtype':patient.get('subtype'),
            'treatment_episode_id':ep['treatment_episode_id'],'regimen_id':ep['regimen_id'],'treatment_class':None,'prior_ici':ep['prior_ici'],
            'prior_treatment':patient.get('prior_systemic_treatment'),'specimen_uid':sp.get('specimen_uid'),'assay_uid':assay.get('assay_uid'),
            'expression_column':assay.get('matrix_header'),'biopsy_site':sp.get('lesion_site'),'raw_response':endpoint['raw_value'],
            'response_system':endpoint['assessment_system'],'canonical_category':endpoint['canonical_category'],
            'orr':endpoint['binary_value'] if endpoint['endpoint_class']=='ORR' else None,'dcr':dcr.get('binary_value'),
            'endpoint_evaluability':endpoint['evaluability'],'inclusion_status':'INCLUDED' if included else 'EXCLUDED','exclusion_reason':reason,
            'expression_unit':assay.get('measurement_unit'),'feature_annotation':assay.get('feature_annotation'),'branch_id':packet['branch_id'],
            'split_role':cfg['_roles'][patient['patient_uid']],'prior_exposure_status':cfg['_exposure'][patient['patient_uid']],'build_receipt_id':build_id}
        store.validate('baseline',row);rows.append(row)
        audit.append({'kind':'BASELINE_SELECTION','patient_uid':patient['patient_uid'],'specimen_uid':sp.get('specimen_uid'),
                      'assay_uid':assay.get('assay_uid'),'endpoint_class':endpoint['endpoint_class'],'outcome_id':endpoint['outcome_id'],
                      'reason':reason or 'SYNTHETIC_BUILD_DRAFT'})
    records['baseline']=rows
    records.setdefault('matrix_build_receipt',[]).append(_draft('baseline',packet,records,deps,cfg,store,build_id))
    unknown={str(a['reason']) for a in audit if a.get('reason') in
             {'ASSAY_EVIDENCE_UNKNOWN','PATIENT_UNKNOWN','BASELINE_ELIGIBILITY_UNKNOWN','SPECIMEN_POLICY_UNKNOWN'}}
    return finish('baseline',packet,records,status='BLOCKED_UNKNOWN' if unknown else 'READY',
                  reasons=unknown,audit=audit,schemas=store)


@stage_boundary('longitudinal')
def build_longitudinal(packet: dict[str,Any], *, schemas: SchemaStore | None = None) -> dict[str,Any]:
    store=schemas or SchemaStore();records,deps=_prepare(packet,store);cfg=_policy(packet,'longitudinal',deps,store)
    raw_windows=cfg.get('windows');require(isinstance(raw_windows,list) and bool(raw_windows),'SELECTION_POLICY_UNKNOWN',blocked=True)
    windows=cast(list[dict[str,Any]],raw_windows);window_ids: set[str]=set()
    for w in windows:
        require(set(w)=={'window_id','contrast_id','category','lower_day','upper_day'} and w['window_id'] not in window_ids
                and w['lower_day']<=w['upper_day'],'SELECTION_POLICY_UNKNOWN')
        require(w['category'] in {'EARLY_ON_TREATMENT','LATE_ON_TREATMENT','RESPONSE_ASSESSMENT','MAXIMAL_RESPONSE','PROGRESSION','POST_TREATMENT','POST_DISCONTINUATION'},'SELECTION_POLICY_UNKNOWN')
        window_ids.add(w['window_id'])
    audit: list[dict[str,Any]]=[];points=[];pairs=[]
    build_id='synthetic-longitudinal-'+digest([packet['config'],deps['admission']['receipt_id']])[:20]
    patients={p['patient_uid']:p for p in records.get('patient_registry',[])}
    episodes={e['treatment_episode_id']:e for e in records.get('treatment_episode',[])}
    for sp in records.get('specimen_registry',[]):
        require(sp['patient_uid'] in patients,'FOREIGN_KEY_UNRESOLVED')
        contexts=[(key,t) for key,t in cfg['_contexts'].items() if key[0]==sp['specimen_uid']]
        require(bool(contexts),'TIMING_UNKNOWN',blocked=True)
        assays=[a for a in records.get('assay_registry',[]) if a['specimen_uid']==sp['specimen_uid']]
        for key,timing in contexts:
            binding=cfg['_bindings'][key];require(key[1] in episodes,'FOREIGN_KEY_UNRESOLVED')
            episode=episodes[key[1]]
            require(binding['patient_uid']==sp['patient_uid']==episode['patient_uid'],'EPISODE_MISMATCH')
            endpoint=_endpoint(records,patients[sp['patient_uid']],episode,cfg,deps,store,optional=True)
            for assay in assays or [None]:
                row={'row_type':'TIMEPOINT','schema_version':'1.1.0','data_classification':packet['classification'],
                    'patient_uid':sp['patient_uid'],'study_id':patients[sp['patient_uid']]['study_id'],'specimen_uid':sp['specimen_uid'],
                    'assay_uid':assay['assay_uid'] if assay else None,'treatment_episode_id':key[1],'raw_timing_label':sp.get('timing_raw_text'),
                    'canonical_timing':timing['canonical_category'],'relative_day':timing.get('relative_day'),'timing_precision':timing['precision'],
                    'lesion_site':sp.get('lesion_site'),'outcome_id':endpoint.get('outcome_id'),'endpoint_assessment_day':endpoint.get('assessment_day'),
                    'pairability':sp['longitudinal_pair_status'],'missingness_reason':None if assay else 'ASSAY_UNSUITABLE','build_receipt_id':build_id}
                store.validate('timepoint',row);points.append(row)
    records['timepoint']=points
    for patient in patients.values():
        ep=_episode(records,patient,cfg);episode_id=ep['treatment_episode_id']
        try:pre=_choose(_candidates(records,patient,ep,cfg,baseline=True,audit=audit),cfg)
        except DavError as exc:return _blocked_tie('longitudinal',packet,records,audit,exc,store)
        all_follow=_candidates(records,patient,ep,cfg,baseline=False,audit=audit)
        endpoint=_endpoint(records,patient,ep,cfg,deps,store)
        for w in windows:
            candidates=[]
            for sp,assay in all_follow:
                timing=cfg['_contexts'][(sp['specimen_uid'],episode_id)]
                category=timing['canonical_category'];day=timing.get('relative_day')
                if category=='PRE_INDEX_BASELINE':continue
                reason=None
                if category=='AFTER_REGIMEN_CHANGE':reason='AFTER_REGIMEN_CHANGE'
                elif category=='PROGRESSION' and w['category']!='PROGRESSION':reason='PROGRESSION_MIXED_WITH_SCHEDULED_ON'
                elif timing['precision']!='EXACT' or day is None:reason='TIMING_UNKNOWN'
                elif category!=w['category'] or not w['lower_day']<=day<=w['upper_day']:reason='NO_FOLLOWUP_IN_WINDOW'
                elif sp['longitudinal_pair_status']!='PAIRABLE':reason='TIMING_UNKNOWN'
                audit.append({'kind':'WINDOW_CANDIDATE','patient_uid':patient['patient_uid'],'treatment_episode_id':episode_id,
                    'window_id':w['window_id'],'specimen_uid':sp['specimen_uid'],'assay_uid':assay['assay_uid'],'reason':reason or 'LOWER_RANK'})
                if reason is None:candidates.append((sp,assay))
            try:follow=_choose(candidates,cfg)
            except DavError as exc:return _blocked_tie('longitudinal',packet,records,audit,exc,store)
            pre_sp,pre_a=pre if pre else ({},{})
            sp,assay=follow if follow else ({},{})
            pre_t=cfg['_contexts'].get((pre_sp.get('specimen_uid'),episode_id),{})
            follow_t=cfg['_contexts'].get((sp.get('specimen_uid'),episode_id),{})
            reason='PATIENT_EXCLUDED' if patient['inclusion_state']=='EXCLUDED' or cfg['_roles'][patient['patient_uid']]=='EXCLUDED' else 'PATIENT_UNKNOWN' if patient['inclusion_state']=='BLOCKED_UNKNOWN' else 'NO_PRE_INDEX_SPECIMEN' if pre is None else 'NO_FOLLOWUP_IN_WINDOW' if follow is None else None
            lesion=None if pre_sp.get('lesion_site') is None or sp.get('lesion_site') is None else pre_sp['lesion_site']==sp['lesion_site']
            platform=None if not pre or not follow else pre_a['platform']==assay['platform']
            if reason is None:
                if pre_sp['longitudinal_pair_status']!='PAIRABLE' or pre_t['precision']!='EXACT' or pre_t.get('relative_day') is None:reason='TIMING_UNKNOWN'
                elif lesion is not True:reason='LESION_MISMATCH'
                elif platform is not True:reason='PLATFORM_MISMATCH'
                elif (pre_a['measurement_unit'],pre_a.get('transform'),pre_a.get('feature_annotation'))!=(assay['measurement_unit'],assay.get('transform'),assay.get('feature_annotation')):reason='MEASUREMENT_SCALE_INCOMPATIBLE'
                elif pre_t['relative_day']>=follow_t['relative_day']:reason='TIMING_UNKNOWN'
                elif cfg['endpoint_policy']['required'] and endpoint['evaluability']!='EVALUABLE':reason='ENDPOINT_UNKNOWN'
            audit.append({'kind':'PAIR_DENOMINATOR','patient_uid':patient['patient_uid'],'treatment_episode_id':episode_id,
                'window_id':w['window_id'],'contrast_id':w['contrast_id'],'reason':reason or 'SYNTHETIC_BUILD_DRAFT',
                'inclusion_status':'INCLUDED' if reason is None else 'EXCLUDED','pre_specimen_uid':pre_sp.get('specimen_uid'),
                'followup_specimen_uid':sp.get('specimen_uid')})
            if pre is None or follow is None:continue
            row={'row_type':'PAIR','schema_version':'1.1.0','data_classification':packet['classification'],'patient_uid':patient['patient_uid'],
                'study_id':patient['study_id'],'treatment_episode_id':episode_id,'contrast_id':w['contrast_id'],'window_id':w['window_id'],
                'response_group':'NOT_APPLICABLE' if not cfg['endpoint_policy']['required'] else 'R' if endpoint['binary_value']==1 else 'NR' if endpoint['binary_value']==0 else 'UNKNOWN',
                'regimen_id':ep['regimen_id'],'pre_specimen_uid':pre_sp['specimen_uid'],'pre_assay_uid':pre_a['assay_uid'],
                'followup_specimen_uid':sp['specimen_uid'],'followup_assay_uid':assay['assay_uid'],'pre_day':pre_t.get('relative_day'),
                'followup_day':follow_t.get('relative_day'),'followup_category':w['category'],'same_lesion':lesion,'same_platform':platform,
                'pair_quality':'VERIFIED' if reason is None else 'EXCLUDED','inclusion_status':'INCLUDED' if reason is None else 'EXCLUDED',
                'exclusion_reason':reason,'missing_followup_reason':None,'build_receipt_id':build_id}
            store.validate('pair',row);pairs.append(row)
            audit.append({'kind':'PAIR_SELECTION','patient_uid':patient['patient_uid'],'treatment_episode_id':episode_id,
                          'window_id':w['window_id'],'reason':reason or 'SYNTHETIC_BUILD_DRAFT'})
    records['pair']=pairs
    records.setdefault('matrix_build_receipt',[]).append(_draft('longitudinal',packet,records,deps,cfg,store,build_id))
    unknown={str(a['reason']) for a in audit if a.get('reason') in
             {'ASSAY_EVIDENCE_UNKNOWN','PATIENT_UNKNOWN','BASELINE_ELIGIBILITY_UNKNOWN','SPECIMEN_POLICY_UNKNOWN'}}
    return finish('longitudinal',packet,records,status='BLOCKED_UNKNOWN' if unknown else 'READY',
                  reasons=unknown,audit=audit,schemas=store)
