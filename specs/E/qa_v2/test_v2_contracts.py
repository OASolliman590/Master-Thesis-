"""Specification reference checks, not simulation or biological validation."""
from pathlib import Path
from copy import deepcopy
import hashlib
import itertools
import json
import tempfile
import unittest
from jsonschema import Draft202012Validator
try:
    import contract_checks as cc
except ModuleNotFoundError:
    cc = None

PACKAGE = Path(__file__).resolve().parent.parent
SCHEMAS = PACKAGE / ('schemas_v2' if PACKAGE.name == 'E' else 'schemas')
EXAMPLES = PACKAGE / ('examples_v2' if PACKAGE.name == 'E' else 'examples')

def example(name):
    return json.loads((EXAMPLES / (name+'.json')).read_text())

class V2Contracts(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cc, 'The v2 declared-contract checker has not yet been implemented')
        self.core=example('core_release_complete_fixture')
        self.cap=example('capability_full_fixture')

    def act(self): return cc.evaluate_activation(self.core,self.cap,fixture_mode=True)
    def modules(self): return set(self.act()['candidate_modules'])

    def test_activation_results_match_receipt_schema(self):
        schema=json.loads((SCHEMAS/'extension_activation.schema.json').read_text())
        for state in ['NONE','PLANNED','GENERATED','ADMITTED','WITHDRAWN']:
            self.cap['data_state']=state
            Draft202012Validator(schema).validate(self.act())

    def test_admitted_record_needs_source_and_review_references(self):
        self.cap['source_object_ids']=[]
        self.assertEqual(self.act()['status'],'BLOCKED_IDENTITY')
        self.cap=example('capability_full_fixture');self.cap['reviewer_receipts']=[]
        self.assertEqual(self.act()['status'],'BLOCKED_PERMISSION')

    def test_all_schemas_are_valid(self):
        for path in SCHEMAS.glob('*.schema.json'):
            Draft202012Validator.check_schema(json.loads(path.read_text()))

    def test_all_examples_valid_and_synthetic(self):
        index=json.loads((EXAMPLES/'INDEX.json').read_text())
        for name,schema in index.items():
            payload=json.loads((EXAMPLES/name).read_text())
            Draft202012Validator(json.loads((SCHEMAS/schema).read_text())).validate(payload)
            self.assertIs(payload['synthetic'],True)

    def test_unknown_schema_key_rejected(self):
        self.core['fake_validation']=True
        with self.assertRaises(ValueError): cc.evaluate_core(self.core,fixture_mode=True)

    def test_unknown_gate_not_true(self):
        self.core['gates']['public_numerical_exposure']=None
        self.assertFalse(cc.evaluate_core(self.core,fixture_mode=True)['declarations_eligible'])

    def test_synthetic_never_authorises_science(self):
        self.assertEqual(cc.evaluate_core(self.core)['status'],'REJECT_SYNTHETIC')
        r=self.act()
        self.assertFalse(r['scientific_authorisation'])
        self.assertEqual(r['status'],'ELIGIBLE_FOR_REVIEW')

    def test_real_declarations_only_ready_for_artifact_review(self):
        self.core['synthetic']=False
        r=cc.evaluate_core(self.core)
        self.assertEqual(r['status'],'DECLARATIONS_ELIGIBLE_FOR_ARTIFACT_REVIEW')
        self.assertFalse(r['scientific_authorisation'])

    def test_every_foundation_gate_required(self):
        for key in self.core['gates']:
            bad=deepcopy(self.core);bad['gates'][key]=False
            self.assertFalse(cc.evaluate_core(bad,fixture_mode=True)['declarations_eligible'],key)

    def test_every_packet_required(self):
        for key in self.core['packet_status']:
            bad=deepcopy(self.core);bad['packet_status'][key]='PENDING'
            self.assertFalse(cc.evaluate_core(bad,fixture_mode=True)['declarations_eligible'])

    def test_profile_incomplete_never_complete(self):
        self.core['profile']='C-INCOMPLETE'
        self.assertFalse(cc.evaluate_core(self.core,fixture_mode=True)['declarations_eligible'])

    def test_identifiability_needs_observation_linked_certificate(self):
        self.core['profile_evidence']['measurement_linked_identifiability_certificate']=False
        self.assertFalse(cc.evaluate_core(self.core,fixture_mode=True)['declarations_eligible'])

    def test_scheduling_needs_temporal_functional_checkpoint_and_nonempty(self):
        self.core['profile']='C-SCHEDULING'
        fields=['temporal_pd','functional_constraints','checkpoint_constraint_or_justified_transfer','nonempty_admissible_set']
        for key in fields:self.core['profile_evidence'][key]=True
        self.assertTrue(cc.evaluate_core(self.core,fixture_mode=True)['declarations_eligible'])
        for key in fields:
            bad=deepcopy(self.core);bad['profile_evidence'][key]=False
            self.assertFalse(cc.evaluate_core(bad,fixture_mode=True)['declarations_eligible'],key)

    def test_internal_unknown_and_synthetic_inputs_rejected(self):
        for origin in ['internal_unpublished','unknown','synthetic']:
            bad=deepcopy(self.core);bad['numeric_input_origins']=[origin]
            self.assertFalse(cc.evaluate_core(bad,fixture_mode=True)['declarations_eligible'])

    def test_empty_artifact_or_review_references_block(self):
        for field in ['artifacts','reviewer_receipts','numeric_input_origins']:
            bad=deepcopy(self.core);bad[field]=[]
            self.assertFalse(cc.evaluate_core(bad,fixture_mode=True)['declarations_eligible'])

    def test_public_core_input_scope_rejects_original_data(self):
        run=example('public_run_fixture');run['scientific_numeric_inputs'][0]['origin']='internal_unpublished'
        self.assertFalse(cc.evaluate_run_scope(run)['eligible'])

    def test_unadmitted_numeric_input_cannot_enter_core(self):
        run=example('public_run_fixture');run['scientific_numeric_inputs'][0]['admitted']=False
        self.assertFalse(cc.evaluate_run_scope(run)['eligible'])

    def test_core_contract_unchanged_by_extension_changes(self):
        before=cc.evaluate_core(self.core,fixture_mode=True)
        for state in ['NONE','PLANNED','GENERATED','ADMITTED','WITHDRAWN']:
            self.cap['data_state']=state
            self.act()
            self.assertEqual(before,cc.evaluate_core(self.core,fixture_mode=True))

    def test_activation_does_not_mutate_inputs(self):
        core_before=deepcopy(self.core);cap_before=deepcopy(self.cap)
        self.act()
        self.assertEqual(core_before,self.core);self.assertEqual(cap_before,self.cap)

    def test_incomplete_core_blocks_extension(self):
        self.core['complete']=False
        self.assertEqual(self.act()['status'],'BLOCKED_CORE')

    def test_no_or_planned_data_defers_only_extension(self):
        for state in ['NONE','PLANNED','APPROVED']:
            self.cap['data_state']=state
            self.assertEqual(self.act()['status'],'DEFERRED_NO_DATA')
            self.assertTrue(cc.evaluate_core(self.core,fixture_mode=True)['declarations_eligible'])

    def test_permission_unknown_denied_withdrawn_blocks(self):
        for permission in ['UNKNOWN','DENIED']:
            self.cap['permission']=permission
            self.assertEqual(self.act()['status'],'BLOCKED_PERMISSION')
        self.cap['permission']='WITHDRAWN'
        self.assertEqual(self.act()['status'],'WITHDRAWN_PERMISSION')

    def test_qc_and_not_yet_admitted_block(self):
        for status in ['PENDING','FAILED','UNKNOWN']:
            self.cap['qc']=status
            self.assertEqual(self.act()['status'],'QUARANTINED_QC')
        self.cap['qc']='PASSED';self.cap['data_state']='GENERATED'
        self.assertEqual(self.act()['status'],'QUARANTINED_QC')

    def test_identity_and_biological_grouping_required(self):
        for field in ['identity_verified','biological_units_known']:
            old=self.cap[field];self.cap[field]=None
            self.assertEqual(self.act()['status'],'BLOCKED_IDENTITY');self.cap[field]=old

    def test_changed_context_or_unreviewed_mapping_blocks(self):
        for field in ['context_compatible','assay_mapping_reviewed']:
            old=self.cap[field];self.cap[field]=False
            self.assertEqual(self.act()['status'],'BLOCKED_CONTEXT');self.cap[field]=old

    def test_unknown_capabilities_fail_closed_for_affected_modules(self):
        self.cap['capabilities']={k:None for k in self.cap['capabilities']}
        self.assertEqual(self.act()['status'],'INSUFFICIENT_CAPABILITY')
        self.assertEqual(self.modules(),set())

    def test_static_endpoint_not_kinetics(self):
        self.cap['capabilities']={k:False for k in self.cap['capabilities']}
        self.cap['capabilities'].update(exposure_events=True,protein_endpoint=True)
        self.assertIn('static_phenotype',self.modules())
        self.assertNotIn('tumour_induction',self.modules());self.assertNotIn('tumour_recovery',self.modules())

    def test_induction_without_washout_not_recovery(self):
        self.cap['capabilities']['tumour_withdrawal_series']=False
        self.assertIn('tumour_induction',self.modules());self.assertNotIn('tumour_recovery',self.modules())

    def test_immune_viability_not_function(self):
        self.cap['capabilities']['immune_function']=False
        self.assertIn('immune_viability',self.modules());self.assertNotIn('immune_function',self.modules())
        self.assertNotIn('immune_recovery',self.modules())

    def test_mixed_signal_not_target_killing(self):
        self.cap['capabilities']['target_specific_killing']=False
        self.assertNotIn('target_killing',self.modules());self.assertNotIn('checkpoint_function',self.modules())

    def test_general_killing_not_checkpoint_specific(self):
        self.cap['capabilities']['checkpoint_qualified']=False
        self.assertIn('target_killing',self.modules());self.assertNotIn('checkpoint_function',self.modules())
        self.assertNotIn('checkpoint_schedule',self.modules())

    def test_function_without_schedule_not_timing(self):
        self.cap['capabilities']['schedule_arms']=False
        self.assertIn('checkpoint_function',self.modules());self.assertNotIn('checkpoint_schedule',self.modules())

    def test_no_analytical_measurement_limits_bridge_not_pd(self):
        self.cap['capabilities']['analytical_exposure']=False
        self.assertIn('tumour_recovery',self.modules());self.assertNotIn('measured_exposure_bridge',self.modules())
        self.assertIn('nominal-exposure-only',self.act()['limitations'])

    def test_used_for_fit_not_independent_validation(self):
        self.cap['used_for_fit']=True
        self.assertNotIn('PROSPECTIVE_VALIDATION',self.act()['permitted_roles'])
        self.assertNotIn('RETROSPECTIVE_EVALUATION',self.act()['permitted_roles'])

    def test_retrospective_not_prospective_without_freeze(self):
        self.cap['role']='RETROSPECTIVE_EVALUATION';self.cap['prediction_freeze_before_outcomes']=False
        self.assertIn('RETROSPECTIVE_EVALUATION',self.act()['permitted_roles'])
        self.assertNotIn('PROSPECTIVE_VALIDATION',self.act()['permitted_roles'])

    def test_unverified_or_postoutcome_freeze_never_prospective(self):
        for field in ['prediction_freeze_before_outcomes','freeze_receipt_verified','independent_of_development']:
            original=self.cap[field];self.cap[field]=False
            self.assertNotIn('PROSPECTIVE_VALIDATION',self.act()['permitted_roles']);self.cap[field]=original

    def test_unassigned_role_requires_review(self):
        self.cap['role']='UNASSIGNED'
        self.assertEqual(self.act()['status'],'ELIGIBLE_FOR_REVIEW')
        self.assertEqual(self.act()['permitted_roles'],[])

    def test_null_adverse_conflicting_sign_never_changes_admission(self):
        baseline=self.act()
        for sign in ['BENEFICIAL','NULL','ADVERSE','CONTRADICTORY','MIXED','IMPRECISE']:
            self.cap['outcome_sign']=sign
            r=self.act()
            self.assertEqual(r['status'],baseline['status']);self.assertEqual(r['candidate_modules'],baseline['candidate_modules'])
            self.assertEqual(r['permitted_roles'],baseline['permitted_roles'])

    def test_one_donor_not_representative_population(self):
        self.cap['donor_scope']='ONE_DONOR'
        self.assertNotIn('experimental_population',self.modules())
        self.assertIn('donor-scope-not-representative',self.act()['limitations'])

    def test_population_needs_distribution_and_target_evidence(self):
        for field in ['variation_estimated','population_targets_qualified']:
            original=self.cap['capabilities'][field];self.cap['capabilities'][field]=False
            self.assertNotIn('experimental_population',self.modules());self.cap['capabilities'][field]=original

    def test_hash_mutation_detected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'receipt.json';path.write_bytes(b'original')
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(cc.verify_sha256(path,sha))
            path.write_bytes(b'changed');self.assertFalse(cc.verify_sha256(path,sha))
            self.assertFalse(cc.verify_sha256(Path(d)/'missing',sha))

    def test_exhaustive_key_capability_combinations(self):
        keys=['exposure_events','molecular_endpoint','protein_endpoint','tumour_timecourse','tumour_withdrawal_series','immune_viability','immune_function','target_specific_killing','compartment_controls','checkpoint_qualified','schedule_arms','analytical_exposure']
        for values in itertools.product([False,True],repeat=len(keys)):
            caps={k:False for k in self.cap['capabilities']};caps.update(dict(zip(keys,values)))
            self.cap['capabilities']=caps
            m=cc.candidate_modules(self.cap)
            self.assertEqual('tumour_recovery' in m,caps['exposure_events'] and (caps['molecular_endpoint'] or caps['protein_endpoint']) and caps['tumour_timecourse'] and caps['tumour_withdrawal_series'])
            self.assertEqual('checkpoint_schedule' in m,all(caps[k] for k in ['exposure_events','target_specific_killing','compartment_controls','checkpoint_qualified','schedule_arms']))
            self.assertEqual('immune_function' in m,caps['immune_viability'] and caps['immune_function'])
            self.assertEqual('measured_exposure_bridge' in m,caps['analytical_exposure'] and caps['exposure_events'])

if __name__=='__main__':unittest.main()
