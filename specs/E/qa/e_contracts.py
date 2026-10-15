"""Bounded schema and semantic guards. Not an ODE or scientific inference engine."""
from pathlib import Path
import json,hashlib,math,re
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]
DEV={'calibration','model_selection','exploratory_qualification'}
EVAL={'independent_public_evaluation','prospective_internal_validation'}
def require(condition,message):
 if not condition:raise ValueError(message)
def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def validate_record(name,r):
 schema=json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text())
 try:Draft202012Validator(schema,format_checker=FormatChecker()).validate(r)
 except Exception as e:raise ValueError(str(e)) from e
 require(not r['synthetic'] or r['record_id'].startswith('SYN-'),'Synthetic identifier must be explicit')
 m=r.get('measurement')
 if m:
  require(m['biological_n'] is not None or bool(m['n_unknown_reason']),'Unknown N requires reason')
  require(m['statistic']==m['raw_statistic'] or bool(m['transformation']),'Statistic conversion needs explicit transformation')
  require(m['uncertainty']['type']==m['raw_uncertainty_type'] or bool(m['transformation']),'SD/SE or uncertainty relabel prohibited')
  for val in [m['canonical_value'],m['conversion_factor'],m['uncertainty']['value']]:
   require(val is None or math.isfinite(val),'Nonfinite numeric value')
  if isinstance(m['raw_value'],(float,int)) and m['canonical_value'] is not None and m['conversion_factor'] is not None:
   require(math.isclose(m['raw_value']*m['conversion_factor'],m['canonical_value'],rel_tol=1e-9,abs_tol=1e-12),'Unit conversion mismatch')
 if name=='population':require(r['representation']!='aggregate' or not r['individual_ids'],'Cannot fabricate individuals from aggregate')
 if name=='source_access' and r['required_dependency']:require(r['access_state'] in {'open_numbers','open_table','open_figure','metadata_only'},'Required source not anonymously open')
 if name=='source_object':
  require((r['bytes'] is None)==(r['sha256'] is None),'Bytes/hash must be paired')
  require(r['sha256'] is not None or bool(r['hash_unknown_reason']),'Missing original hash reason')
  require(r['sha256'] is None or r['retrieval_status']=='raw_retained','Cannot claim original bytes from browser text')
  require(r['access_state']!='metadata_only' or r['permitted_role'] in {'unassigned','contextual_corroboration'},'Metadata is not measured calibration evidence')
 if name=='observation':
  require(r['censoring']!='BLQ' or r['assay_limit'] is not None,'BLQ limit required')
  require(r['censoring']!='missing' or bool(r['missing_reason']),'Missingness reason required')
  require(r['axis_scale']!='log' or (len(r['axis_calibration'])>=2 and min(r['axis_calibration'])>0),'Log calibration invalid')
  require(not (r['evidence_class'] in {'prediction','extrapolation'} and r['role'] in EVAL),'Prediction is not biological validation data')
  require(not (r['cell_signal']=='mixed' and r['endpoint']=='target_cell_count'),'Mixed signal is not target count')
  require(not (r['endpoint'] in {'CL','V'} and '/F' in m['raw_unit'] and '/F' not in m['canonical_unit']),'Apparent parameter cannot be systemic')
 if name=='dosing_event':
  require(bool(r['compound_id']) and bool(r['formulation_id']),'Compound/formulation identity required')
  require(r['dose_basis'].lower() not in {'','unknown'},'Dose basis unresolved')
  require(bool(r['time_origin']),'Time origin required')
  require(r['quantity'] is None or r['quantity']>=0,'Negative amount/concentration')
  require(r['retained_fraction'] is None or 0<=r['retained_fraction']<=1,'Invalid carryover fraction')
  require(r['event_type'] not in {'washout','medium_change'} or r['retained_fraction'] is not None,'Withdrawal needs explicit carryover assumption/measurement')
 if name=='experimental_manifest':
  require(r['state']!='planned' or (not r['raw_files'] and not r['observation_ids']),'Plan cannot masquerade as generated data')
  if r['state']!='planned':require(bool(r['approval_reference']),'Approval evidence required')
  if r['state'] in {'generated','quality_checked','admitted','assigned_role'}:require(bool(r['raw_files']),'Generated data need raw-file evidence')
 if name=='parameter_evidence' and not r['synthetic'] and m['canonical_value'] is not None:
  require(r['parameter_status']!='unresolved','Unresolved real biological numeric default prohibited')
  if r['evidence_class'] not in {'prior','assumption','hypothesis'}:require(bool(r['source_ids']),'Numeric evidence requires source')
  else:require(bool(r['prior_definition']),'Prior/assumption numeric definition required')
 if name=='prospective_prediction':
  require(canonical_hash(r['prediction_payload'])==r['payload_sha256'],'Prediction payload changed')
  p=r['prediction_payload'];n=len(r['time_grid'])
  require(n>0 and all(len(p[k])==n for k in ['values','lower','upper']),'Prediction/time-grid length mismatch')
  require(all(lo<=v<=hi for lo,v,hi in zip(p['lower'],p['values'],p['upper'])),'Prediction interval order invalid')
  if r['status']=='frozen':require(not r['synthetic'] and bool(r['frozen_at']) and bool(r['witness_reference']),'Real freeze needs non-synthetic witnessed receipt')
 if name=='vpop_target':require(r['context']!='human_translational' or r['source_context']=='human','Culture/donor targets are not human population targets')
 if name=='scenario':require(r['context']!='culture' or r['endpoint'].upper() not in {'ORR','PFS','OS'},'Culture endpoint is not clinical outcome')
 if name=='validation_receipt':require(r['validation_level'] not in {'software_contract','source_parity'} or not r['biological_validation'],'Software/parity is not biological validation')
 if name=='model_asset' and r['reuse_class']=='exact_reproduction':require(bool(r['asset_url']) and bool(r['sha256']) and r['parity_status']=='pass','Exact reproduction needs released asset and parity')
 return True

def check_roles(records):
 groups={}
 for r in records:
  k=(r['model_version'],r['group_type'],r['group_id']);groups.setdefault(k,set()).add(r['role'])
 for rs in groups.values():require(not(rs&DEV and rs&EVAL),'Development/evaluation group overlap')

def check_weights(weights):
 require(bool(weights),'Empty population weights')
 require(all(math.isfinite(w) and w>=0 for w in weights),'Invalid weights')
 require(math.isclose(sum(weights),1,rel_tol=1e-9,abs_tol=1e-9),'Weights not normalized')
 return 1/sum(w*w for w in weights)

def check_unique(records):
 seen={}
 for r in records:
  k=r['record_id'];h=canonical_hash(r)
  require(k not in seen or seen[k]==h,'Conflicting duplicate record ID');seen[k]=h

def check_hash(data,expected):require(hashlib.sha256(data).hexdigest()==expected,'Cache/input hash mismatch')

def scan_public(value):
 if isinstance(value,dict):
  forbidden={'donor_name','patient_name','raw_donor_id','email','password','access_token','consent_form','reidentification_key'}
  require(not (set(k.lower() for k in value)&forbidden),'Private field in public data')
  for v in value.values():scan_public(v)
 elif isinstance(value,list):
  for v in value:scan_public(v)
 elif isinstance(value,str):require(re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',value) is None,'Potential personal email in public data')

def validate_all():
 schemas=list((ROOT/'schemas').glob('*.schema.json'))
 for p in schemas:Draft202012Validator.check_schema(json.loads(p.read_text()))
 records=[];count=0
 for p in sorted((ROOT/'examples').rglob('*.json')):
  a=json.loads(p.read_text());validate_record(a['schema'],a['record']);records.append(a['record']);count+=1
  if not a['record']['synthetic']:scan_public(a['record'])
 check_unique(records)
 decisions=ROOT/'decisions/decisions.jsonl'
 if decisions.exists():
  for line in decisions.read_text().splitlines():
   if line.strip():validate_record('decision',json.loads(line))
 return {'schemas_checked':len(schemas),'examples_validated':count,'biological_validation':False}
