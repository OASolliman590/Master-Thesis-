"""Synthetic/seed contract tests only. No ODE, pharmacology or biology is validated."""
import unittest,copy,json,hashlib
from pathlib import Path
from e_contracts import validate_record,validate_all,check_roles,check_weights,check_unique,check_hash,scan_public
ROOT=Path(__file__).resolve().parents[1]
def fixture(name):return json.loads((ROOT/'examples/synthetic'/f'{name}.json').read_text())['record']
class Contracts(unittest.TestCase):
 def check_bad(self,name,mut):
  r=fixture(name);mut(r)
  with self.assertRaises(ValueError):validate_record(name,r)
 def test_all_schemas_and_examples(self):self.assertGreaterEqual(validate_all()['examples_validated'],33)
 def test_unknown_field(self):self.check_bad('source_access',lambda r:r.update(secret='x'))
 def test_negative_N(self):self.check_bad('observation',lambda r:r['measurement'].update(biological_n=-1))
 def test_unknown_N_requires_reason(self):self.check_bad('observation',lambda r:r['measurement'].update(biological_n=None,n_unknown_reason=None))
 def test_aggregate_not_individual(self):self.check_bad('population',lambda r:r.update(individual_ids=['invented']))
 def test_sd_se_relabel(self):self.check_bad('observation',lambda r:(r['measurement'].update(raw_uncertainty_type='SD'),r['measurement']['uncertainty'].update(type='SE')))
 def test_statistic_relabel(self):self.check_bad('observation',lambda r:r['measurement'].update(raw_statistic='geometric_mean'))
 def test_blq_needs_limit(self):self.check_bad('observation',lambda r:r.update(censoring='BLQ'))
 def test_missing_needs_reason(self):self.check_bad('observation',lambda r:r.update(censoring='missing'))
 def test_log_calibration_positive(self):self.check_bad('observation',lambda r:r.update(axis_scale='log',axis_calibration=[0,1]))
 def test_predictions_not_biological_evaluation(self):self.check_bad('observation',lambda r:r.update(evidence_class='prediction',role='independent_public_evaluation'))
 def test_extrapolation_not_validation(self):self.check_bad('observation',lambda r:r.update(evidence_class='extrapolation',role='prospective_internal_validation'))
 def test_mixed_not_target_count(self):self.check_bad('observation',lambda r:r.update(cell_signal='mixed',endpoint='target_cell_count'))
 def test_numeric_conversion(self):self.check_bad('observation',lambda r:r['measurement'].update(canonical_value=20))
 def test_cl_apparent(self):self.check_bad('observation',lambda r:(r.update(endpoint='CL'),r['measurement'].update(raw_unit='L/h/F',canonical_unit='L/h')))
 def test_v_apparent(self):self.check_bad('observation',lambda r:(r.update(endpoint='V'),r['measurement'].update(raw_unit='L/F',canonical_unit='L')))
 def test_negative_dose(self):self.check_bad('dosing_event',lambda r:r.update(quantity=-1))
 def test_missing_formulation(self):self.check_bad('dosing_event',lambda r:r.update(formulation_id=''))
 def test_ambiguous_dose_basis(self):self.check_bad('dosing_event',lambda r:r.update(dose_basis='unknown'))
 def test_retention_range(self):self.check_bad('dosing_event',lambda r:r.update(event_type='washout',retained_fraction=1.2))
 def test_washout_retention_required(self):self.check_bad('dosing_event',lambda r:r.update(event_type='washout',retained_fraction=None))
 def test_missing_time_origin(self):self.check_bad('dosing_event',lambda r:r.update(time_origin=''))
 def test_source_hash_requires_bytes(self):self.check_bad('source_object',lambda r:r.update(sha256='0'*64))
 def test_source_bytes_require_retention(self):self.check_bad('source_object',lambda r:r.update(bytes=10,sha256='0'*64))
 def test_source_missing_hash_reason(self):self.check_bad('source_object',lambda r:r.update(hash_unknown_reason=None))
 def test_restricted_required(self):self.check_bad('source_access',lambda r:r.update(required_dependency=True,access_state='restricted'))
 def test_registration_required(self):self.check_bad('source_access',lambda r:r.update(required_dependency=True,access_state='free_registration'))
 def test_metadata_not_pk(self):self.check_bad('source_object',lambda r:r.update(access_state='metadata_only',permitted_role='calibration'))
 def test_planned_not_generated(self):self.check_bad('experimental_manifest',lambda r:r.update(raw_files=['invented.raw']))
 def test_actual_approval_needed(self):self.check_bad('experimental_manifest',lambda r:r.update(synthetic=False,record_id='REAL-EXP',state='approved',privacy_class='restricted_internal'))
 def test_generated_needs_raw(self):self.check_bad('experimental_manifest',lambda r:r.update(state='generated',approval_reference='SYN-APPROVAL'))
 def test_real_numeric_source_needed(self):self.check_bad('parameter_evidence',lambda r:r.update(synthetic=False,record_id='REAL-PARAM',parameter_status='source_reported',evidence_class='reported_summary'))
 def test_unresolved_real_value_forbidden(self):self.check_bad('parameter_evidence',lambda r:r.update(synthetic=False,record_id='REAL-PARAM'))
 def test_receipt_tamper(self):self.check_bad('prospective_prediction',lambda r:r['prediction_payload']['values'].__setitem__(0,9))
 def test_synthetic_cannot_freeze(self):self.check_bad('prospective_prediction',lambda r:r.update(status='frozen',frozen_at='2026-10-13'))
 def test_interval_order(self):self.check_bad('prospective_prediction',lambda r:r['prediction_payload']['lower'].__setitem__(1,10))
 def test_role_overlap(self):
  a=fixture('role_assignment');b=copy.deepcopy(a);b['role']='prospective_internal_validation'
  with self.assertRaises(ValueError):check_roles([a,b])
 def test_next_version_update_allowed(self):
  a=fixture('role_assignment');b=copy.deepcopy(a);b.update(model_version='SYN-v2',role='prospective_internal_validation');check_roles([a,b])
 def test_weights_ess(self):self.assertAlmostEqual(check_weights([0.5,0.5]),2)
 def test_weights_negative(self):
  with self.assertRaises(ValueError):check_weights([-0.1,1.1])
 def test_weights_not_normalized(self):
  with self.assertRaises(ValueError):check_weights([1,1])
 def test_duplicate_conflict(self):
  with self.assertRaises(ValueError):check_unique([{'record_id':'x','a':1},{'record_id':'x','a':2}])
 def test_hash_integrity(self):
  with self.assertRaises(ValueError):check_hash(b'changed','0'*64)
 def test_human_target_not_culture(self):self.check_bad('vpop_target',lambda r:r.update(context='human_translational'))
 def test_culture_not_clinical(self):self.check_bad('scenario',lambda r:r.update(endpoint='ORR'))
 def test_software_not_biological(self):self.check_bad('validation_receipt',lambda r:r.update(biological_validation=True))
 def test_public_identifier_leak(self):
  with self.assertRaises(ValueError):scan_public({'donor_name':'fixture'})
 def test_public_email_leak(self):
  with self.assertRaises(ValueError):scan_public({'note':'test@example.invalid'})
 def test_synthetic_id_required(self):self.check_bad('source_access',lambda r:r.update(record_id='REAL'))
 def test_exact_reproduction_needs_asset(self):self.check_bad('model_asset',lambda r:r.update(reuse_class='exact_reproduction'))
if __name__=='__main__':unittest.main(verbosity=2)
