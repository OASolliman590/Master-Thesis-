"""Bounded specification reference checks; not an authorisation or scientific auditor.

These functions inspect declared, schema-valid flags. They do not inspect raw assays,
run model fitting, verify scientific reviews, or activate production workflows.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, ValidationError

_PACKAGE = Path(__file__).resolve().parent.parent
_SCHEMA_DIR = _PACKAGE / ('schemas_v2' if _PACKAGE.name == 'E' else 'schemas')

@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((_SCHEMA_DIR / (name+'.schema.json')).read_text()))

def validate(name: str, record: dict[str, Any]) -> None:
    try:
        _validator(name).validate(record)
    except ValidationError as exc:
        location='/'.join(str(x) for x in exc.absolute_path)
        raise ValueError(f'{name}:{location}: {exc.message}') from exc

def evaluate_core(record: dict[str, Any], *, fixture_mode: bool=False) -> dict[str, Any]:
    """Evaluate declared completion prerequisites; never certify real completion."""
    validate('core_release',record)
    reasons=[]
    if record['synthetic'] and not fixture_mode:
        return {'status':'REJECT_SYNTHETIC','declarations_eligible':False,'reasons':['synthetic-record'], 'scientific_authorisation':False}
    if not record['complete']:reasons.append('release-not-declared-complete')
    if record['profile']=='C-INCOMPLETE':reasons.append('incomplete-profile')
    reasons += ['gate:'+k for k,v in record['gates'].items() if v is not True]
    reasons += ['packet:'+k for k,v in record['packet_status'].items() if v!='COMPLETE']
    allowed={'public_external','public_project_release'}
    if not record['numeric_input_origins'] or not set(record['numeric_input_origins']) <= allowed:
        reasons.append('nonpublic-or-unknown-scientific-input')
    if not record['artifacts']:reasons.append('missing-artifact-references')
    if not record['reviewer_receipts']:reasons.append('missing-review-references')
    evidence=record['profile_evidence']
    if record['profile']=='C-SCHEDULING':
        for key in ['temporal_pd','functional_constraints','checkpoint_constraint_or_justified_transfer','nonempty_admissible_set']:
            if evidence[key] is not True:reasons.append('profile-evidence:'+key)
    if record['profile']=='C-IDENTIFIABILITY' and evidence['measurement_linked_identifiability_certificate'] is not True:
        reasons.append('missing-measurement-linked-identifiability-certificate')
    return {'status':'BLOCKED_CORE' if reasons else 'DECLARATIONS_ELIGIBLE_FOR_ARTIFACT_REVIEW', 'declarations_eligible':not reasons,'reasons':reasons,'scientific_authorisation':False}

def evaluate_run_scope(record: dict[str, Any]) -> dict[str, Any]:
    validate('public_run_input',record)
    reasons=[]
    if record['lane']=='public_core':
        for item in record['scientific_numeric_inputs']:
            if item['origin'] not in {'public_external','public_project_release'}:
                reasons.append(item['source_id']+':origin-not-public')
            if item['admitted'] is not True:
                reasons.append(item['source_id']+':not-admitted')
            if item['role']=='FIXTURE':reasons.append(item['source_id']+':fixture-is-not-scientific-input')
    return {'eligible':not reasons,'reasons':reasons,'scientific_authorisation':False}

def candidate_modules(snapshot: dict[str, Any]) -> list[str]:
    """Map capabilities to candidates for review, not identifiable parameter lists."""
    c=snapshot['capabilities']
    yes=lambda key: c.get(key) is True
    m=[]
    if yes('tumour_viability') or yes('tumour_target_counts'):m.append('tumour_viability_growth')
    if yes('exposure_events') and yes('proximal_engagement'):m.append('target_engagement')
    phenotype=yes('molecular_endpoint') or yes('protein_endpoint')
    if yes('exposure_events') and phenotype:m.append('static_phenotype')
    induction=yes('exposure_events') and phenotype and yes('tumour_timecourse')
    if induction:m.append('tumour_induction')
    if induction and yes('tumour_withdrawal_series'):m.append('tumour_recovery')
    if yes('immune_viability'):m.append('immune_viability')
    if yes('immune_viability') and yes('immune_function'):m.append('immune_function')
    if all(yes(k) for k in ['exposure_events','immune_viability','immune_function','immune_timecourse','immune_withdrawal_series']):m.append('immune_recovery')
    killing=all(yes(k) for k in ['exposure_events','target_specific_killing','compartment_controls'])
    if killing:m.append('target_killing')
    if killing and yes('checkpoint_qualified'):m.append('checkpoint_function')
    if killing and yes('checkpoint_qualified') and yes('schedule_arms'):m.append('checkpoint_schedule')
    if yes('exposure_events') and yes('analytical_exposure'):m.append('measured_exposure_bridge')
    if snapshot['donor_scope']=='MULTIPLE_DONORS' and yes('variation_estimated') and yes('population_targets_qualified'):m.append('experimental_population')
    return m

def evaluate_activation(core: dict[str, Any], snapshot: dict[str, Any], *, fixture_mode: bool=False) -> dict[str, Any]:
    validate('capability_snapshot',snapshot)
    foundation=evaluate_core(core,fixture_mode=fixture_mode)
    result={'schema_version':'2.0.0','record_id':'CHECK-'+snapshot['record_id'], 'synthetic':snapshot['synthetic'] or core['synthetic'], 'core_release_id':core['record_id'], 'capability_snapshot_id':snapshot['record_id'], 'reviewer_receipts':[], 'status':'DORMANT','candidate_modules':[],'permitted_roles':[],'reasons':[], 'limitations':[], 'scientific_authorisation':False,'core_modified':False}
    def stop(status: str, reason: str) -> dict[str, Any]:
        return result | {'status':status,'reasons':[reason]}
    if snapshot['synthetic'] and not fixture_mode:return stop('DORMANT','synthetic-record-not-real-data')
    if not foundation['declarations_eligible']:return stop('BLOCKED_CORE','foundation-declarations-incomplete')
    if snapshot['data_state']=='WITHDRAWN' or snapshot['permission']=='WITHDRAWN':return stop('WITHDRAWN_PERMISSION','permission-withdrawn')
    if snapshot['data_state'] in {'NONE','PLANNED','APPROVED'}:return stop('DEFERRED_NO_DATA','no-generated-admitted-data')
    if snapshot['permission']!='APPROVED' or not snapshot['reviewer_receipts']:return stop('BLOCKED_PERMISSION','permission-or-review-reference-missing')
    if snapshot['qc']!='PASSED' or snapshot['data_state']!='ADMITTED':return stop('QUARANTINED_QC','qc-or-admission-incomplete')
    if snapshot['identity_verified'] is not True or snapshot['biological_units_known'] is not True or not snapshot['source_object_ids']:return stop('BLOCKED_IDENTITY','identity-or-independent-unit-unknown')
    if snapshot['context_compatible'] is not True or snapshot['assay_mapping_reviewed'] is not True:return stop('BLOCKED_CONTEXT','context-or-assay-mapping-unqualified')
    modules=candidate_modules(snapshot)
    if not modules:return stop('INSUFFICIENT_CAPABILITY','no-supported-candidate-module')
    result.update(status='ELIGIBLE_FOR_REVIEW',candidate_modules=modules)
    role=snapshot['role']
    if role in {'QUALIFICATION','CALIBRATION','CONTEXTUAL'}:result['permitted_roles']=[role]
    independent=snapshot['independent_of_development'] is True and snapshot['used_for_fit'] is False
    if independent and role=='RETROSPECTIVE_EVALUATION':result['permitted_roles']=[role]
    if independent and role=='PROSPECTIVE_VALIDATION' and snapshot['prediction_freeze_before_outcomes'] is True and snapshot['freeze_receipt_verified'] is True:result['permitted_roles']=[role]
    if not result['permitted_roles']:result['reasons'].append('assigned-role-not-yet-qualified')
    if snapshot['capabilities']['analytical_exposure'] is not True:result['limitations'].append('nominal-exposure-only')
    if snapshot['donor_scope'] in {'ONE_DONOR','UNKNOWN'}:result['limitations'].append('donor-scope-not-representative')
    result['limitations'].append('declared-flags-only; verify real artifacts and scientific authority before production')
    return result

def verify_sha256(path: Path, expected: str) -> bool:
    """Check actual bytes for a referenced file; no filesystem-wide access."""
    if not path.is_file() or len(expected)!=64:return False
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()==expected
