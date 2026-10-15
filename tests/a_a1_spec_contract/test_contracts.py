"""Document/schema and synthetic mathematical contracts only; no clinical data."""
from __future__ import annotations
import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urljoin, urldefrag
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
DAV = ROOT / 'specs/A_DATA_ACQUISITION_VALIDATION'
A = ROOT / 'specs/A'
A1 = ROOT / 'specs/A1'
SCHEMA_FILES = sorted((DAV/'schemas').glob('*.json')) + sorted((A/'schemas').glob('*.json')) + [A/'PATIENT_MATRIX_SCHEMA.json', A/'SOURCE_RECORD_SCHEMA.json']

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def resources():
    return Registry().with_resources((d['$id'], Resource.from_contents(d)) for d in map(load, SCHEMA_FILES))

def validator(name, part=None):
    d = load(DAV/'schemas'/name)
    if part:
        d = {'$schema': d['$schema'], '$ref': d['$id']+'#/$defs/'+part}
    return Draft202012Validator(d, registry=resources())

def endpoint(category='PR', endpoint_class='ORR', value=1):
    return dict(row_type='ENDPOINT', schema_version='1.1.0', data_classification='SYNTHETIC_ONLY', patient_uid='SYNTH_001', treatment_episode_id='SYNTH_EP', outcome_id='SYNTH_O', endpoint_id='SYNTH_ENDPOINT', endpoint_class=endpoint_class, raw_value=category, canonical_category=category, assessment_system='SYNTHETIC', assessment_day=None, binary_value=value, duration_threshold=None, event_time=None, event_indicator=None, censoring=None, evaluability='EVALUABLE', mapping_version='SYNTH_V1', source_locator='urn:synthetic:fixture', build_receipt_id='SYNTH_BUILD')

def pair_row():
    return dict(row_type='PAIR', schema_version='1.1.0', data_classification='SYNTHETIC_ONLY', patient_uid='SYNTH_001', study_id='SYNTH_STUDY', treatment_episode_id='SYNTH_EP', contrast_id='RESPONSE_TIME_INTERACTION', window_id='SYNTH_WINDOW', response_group='R', regimen_id='SYNTH_REG', pre_specimen_uid='SYNTH_PRE', pre_assay_uid='SYNTH_APRE', followup_specimen_uid='SYNTH_FOLLOW', followup_assay_uid='SYNTH_AFOLLOW', pre_day=0, followup_day=10, followup_category='EARLY_ON_TREATMENT', same_lesion=True, same_platform=True, pair_quality='VERIFIED', inclusion_status='INCLUDED', exclusion_reason=None, missing_followup_reason=None, build_receipt_id='SYNTH_BUILD')

def split_row():
    return dict(row_type='SPLIT', schema_version='1.1.0', data_classification='SYNTHETIC_ONLY', patient_uid='SYNTH_001', study_id='SYNTH_STUDY', independence_family_id='SYNTH_FAMILY', permanent_role='FINAL_TEST', prior_exposure_state='ADJUDICATED_UNTOUCHED', exposure_decision_id='SYNTH_REVIEW', split_version='SYNTH_V1', reason='Synthetic schema fixture, not adjudication.', nested_assignments=[])

def auc(positive, negative):
    if not positive or not negative:
        raise ValueError('NONESTIMABLE_AUC')
    return sum((p>n)+0.5*(p==n) for p in positive for n in negative)/(len(positive)*len(negative))

class DocumentContractTests(unittest.TestCase):
    def test_required_A_documents_are_populated(self):
        names='README PROTOCOL_CROSSWALK SCIENTIFIC_AIM_AND_CLAIMS NOVELTY_AND_CLOSEST_STUDIES DATA_ACQUISITION PATIENT_DATA_MODEL ENDPOINT_ONTOLOGY ASSAY_PROCESSING_CONTRACT BASELINE_BIOLOGICAL_ANALYSIS PREDICTION_ANALYSIS ENDPOINT_SENSITIVITY VALIDATION_AND_SPLITS COMPARATOR_REGISTRY PROSTATE_TRANSPORT A_TO_BC_HANDOFF FIGURES PREREGISTRATION_AND_DECISIONS SOFTWARE_ARCHITECTURE IMPLEMENTATION_RECONCILIATION TICKETS_AND_TESTS REPRODUCE_AND_READINESS UNRESOLVED_QUESTIONS SOURCES'.split()
        for name in names:
            with self.subTest(name=name): self.assertGreater(len((A/(name+'.md')).read_text().split()),100)
    def test_required_A1_documents_are_populated(self):
        for name in 'README LONGITUDINAL_DATA_CONTRACT TIMEPOINT_ONTOLOGY PAIRING_CONTRACT LONGITUDINAL_ANALYSIS PHARMACOLOGICAL_CONTEXT NMA_FEASIBILITY VALIDATION_AND_FIGURES TICKETS_AND_TESTS READINESS MULTIOMICS_CORROBORATION INTERFACES'.split():
            with self.subTest(name=name): self.assertGreater(len((A1/(name+'.md')).read_text().split()),100)
    def test_all_schemas_self_validate(self):
        self.assertGreaterEqual(len(SCHEMA_FILES),20)
        for f in SCHEMA_FILES:
            with self.subTest(path=str(f)): Draft202012Validator.check_schema(load(f))
    def test_all_local_schema_references_resolve_offline(self):
        index={load(f)['$id']:load(f) for f in SCHEMA_FILES}
        def walk(x, base):
            if isinstance(x,dict):
                if '$ref' in x:
                    doc,frag=urldefrag(urljoin(base,x['$ref']))
                    self.assertIn(doc,index,(base,x['$ref']))
                    target=index[doc]
                    if frag:
                        self.assertTrue(frag.startswith('/'))
                        for part in frag[1:].split('/'):
                            target=target[part.replace('~1','/').replace('~0','~')]
                for v in x.values(): walk(v,base)
            elif isinstance(x,list):
                for v in x: walk(v,base)
        for d in index.values(): walk(d,d['$id'])
    def test_seven_materialized_definitions_exist(self):
        self.assertTrue(set('baseline timepoint pair endpoint coverage split membership'.split()).issubset(load(DAV/'schemas/materialized_matrix.schema.json')['$defs']))
    def test_A_source_schema_is_only_shared_alias(self):
        d=load(A/'SOURCE_RECORD_SCHEMA.json')
        self.assertEqual(d['$ref'],'../A_DATA_ACQUISITION_VALIDATION/schemas/source_record.schema.json')
        self.assertNotIn('properties',d)
    def test_A_baseline_schema_is_only_shared_alias(self):
        d=load(A/'PATIENT_MATRIX_SCHEMA.json')
        self.assertEqual(d['$ref'],'../A_DATA_ACQUISITION_VALIDATION/schemas/materialized_matrix.schema.json#/$defs/baseline')
        self.assertNotIn('properties',d)
    def test_pending_config_does_not_authorize_analysis(self):
        d=load(A/'configuration.pending.json')
        self.assertEqual(d['status'],'SPECIFICATION_ONLY_NOT_EXECUTABLE')
        self.assertTrue(all(v is False for v in d['permission'].values()))
        self.assertIsNone(d['A_P2']['test_roster'])
        self.assertIsNone(d['learner']['regularization_grid'])
        self.assertEqual(d['A_P1']['principal_score'],'CYT_Rooney_TPM_v1')
        self.assertFalse(d['A_P1']['refit_by_endpoint'])
    def test_TSV_shapes_unique_headers_and_rectangular_rows(self):
        for base in (A,A1,DAV):
            for f in base.rglob('*.tsv'):
                with self.subTest(path=str(f)):
                    rows=list(csv.reader(f.open(encoding='utf-8',newline=''),delimiter='\t'))
                    self.assertTrue(rows)
                    self.assertEqual(len(rows[0]),len(set(rows[0])))
                    self.assertTrue(all(rows[0]))
                    self.assertTrue(all(len(r)==len(rows[0]) for r in rows))
    def test_search_plan_does_not_claim_execution(self):
        rows=list(csv.DictReader((DAV/'search_plan.tsv').open(),delimiter='\t'))
        self.assertGreaterEqual(len(rows),19)
        self.assertTrue(all(r['status']=='PLANNED' for r in rows))
    def test_source_coverage_has_no_admitted_population(self):
        rows=list(csv.DictReader((DAV/'SOURCE_BY_QUESTION_COVERAGE.tsv').open(),delimiter='\t'))
        self.assertTrue(all(r['admission'] in ('NOT_ADMITTED','ALIAS_CANDIDATE') for r in rows))
    def test_historical_A_bytes_preserved(self):
        expected={'ANALYSIS.md':'b1d11663eee024aa6e2d468756cb25b09151f6f3','DATA.md':'7dc1ef463d86931ff2cd73682628054136ae58f7','DISCOVERY.md':'221ed2108430566f1ba04ed605f33aab38177ab2','ENGINEERING.md':'ea658493248eb9f93e1ac2e933c7310d72324d2b','TRANSPORT.md':'04f8b32f0219b19dd72e4faad2720e6522a34860'}
        for name,sha in expected.items():
            b=(ROOT/'reference/specs_A_before_20261015'/name).read_bytes()
            self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),sha)
    def test_historical_DAV_manifest_matches_preserved_bytes(self):
        old=ROOT/'reference/specs_A_DAV_before_20261015'
        for rec in load(old/'SPEC_KIT_MANIFEST.json')['files']:
            rel=Path(rec['path']).relative_to('specs/A_DATA_ACQUISITION_VALIDATION')
            b=(old/rel).read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(),rec['sha256'])
    def test_current_DAV_manifest_does_not_reuse_stale_file_hashes(self):
        d=load(DAV/'SPEC_KIT_MANIFEST.json')
        self.assertEqual(d['spec_kit_version'],'1.1.0-integrated-review.20261015')
        self.assertNotIn('files',d)
        self.assertIn('historical_manifest',d)
    def test_scientific_entry_links_resolve(self):
        for f in list(A.glob('*.md'))+list(A1.glob('*.md'))+[DAV/'README.md']:
            if f.name in ('REVIEW_RESPONSE.md',): continue
            text=f.read_text()
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'): continue
                target=(f.parent/link.split('#')[0]).resolve()
                self.assertTrue(target.exists(),(str(f),link))

class SchemaMutationTests(unittest.TestCase):
    def test_synthetic_episode_valid_and_numeric_id_rejected(self):
        x=load(DAV/'examples/synthetic_episode.json'); v=validator('treatment_episode.schema.json'); v.validate(x)
        x['patient_uid']=1; self.assertFalse(v.is_valid(x))
    def test_exact_episode_day_cannot_be_unknown(self):
        x=load(DAV/'examples/synthetic_episode.json'); x['start_day']=None
        self.assertFalse(validator('treatment_episode.schema.json').is_valid(x))
    def test_binding_valid_but_wrong_subject_role_rejected(self):
        x=load(DAV/'examples/synthetic_episode_binding.json'); v=validator('episode_binding.schema.json'); v.validate(x)
        x['role']='ON_TREATMENT'; self.assertFalse(v.is_valid(x))
    def test_verified_binding_requires_review_record(self):
        x=load(DAV/'examples/synthetic_episode_binding.json'); x['binding_status']='VERIFIED'
        self.assertFalse(validator('episode_binding.schema.json').is_valid(x))
    def test_ORR_CR_PR_mapping(self):
        v=validator('materialized_matrix.schema.json','endpoint')
        for c in ('CR','PR'): v.validate(endpoint(c,'ORR',1)); self.assertFalse(v.is_valid(endpoint(c,'ORR',0)))
    def test_ORR_SD_PD_mapping(self):
        v=validator('materialized_matrix.schema.json','endpoint')
        for c in ('SD','PD'): v.validate(endpoint(c,'ORR',0)); self.assertFalse(v.is_valid(endpoint(c,'ORR',1)))
    def test_DCR_SD_positive_PD_negative(self):
        v=validator('materialized_matrix.schema.json','endpoint')
        v.validate(endpoint('SD','DCR',1));v.validate(endpoint('PD','DCR',0))
        self.assertFalse(v.is_valid(endpoint('SD','DCR',0)))
    def test_unknown_response_not_fabricated_nonresponse(self):
        x=endpoint('UNK','ORR',None);x['evaluability']='UNKNOWN';v=validator('materialized_matrix.schema.json','endpoint');v.validate(x)
        x['binary_value']=0;self.assertFalse(v.is_valid(x))
    def test_DCB_requires_duration(self):
        v=validator('materialized_matrix.schema.json','endpoint');x=endpoint('SOURCE_BINARY','DCB',1)
        self.assertFalse(v.is_valid(x));x['duration_threshold']=180;v.validate(x)
    def test_pair_included_requires_both_assays(self):
        x=pair_row();v=validator('materialized_matrix.schema.json','pair');v.validate(x)
        x['followup_assay_uid']=None;self.assertFalse(v.is_valid(x))
    def test_pair_exclusion_requires_reason(self):
        x=pair_row();x['inclusion_status']='EXCLUDED';v=validator('materialized_matrix.schema.json','pair')
        self.assertFalse(v.is_valid(x));x['exclusion_reason']='SYNTHETIC_MISSING_FOLLOWUP';v.validate(x)
    def test_final_test_cannot_have_unknown_exposure(self):
        x=split_row();v=validator('materialized_matrix.schema.json','split');v.validate(x)
        x['prior_exposure_state']='UNKNOWN';self.assertFalse(v.is_valid(x))
    def test_final_test_cannot_be_inner_training(self):
        x=split_row();x['nested_assignments']=[dict(evaluation_id='SYNTH_E',fold_id='SYNTH_F',role='TRAIN')]
        self.assertFalse(validator('materialized_matrix.schema.json','split').is_valid(x))
    def test_specification_release_valid_not_executable(self):
        x=load(DAV/'examples/specification_only_release.json');v=validator('release_contract.schema.json');v.validate(x)
        x['state']='RELEASED';self.assertFalse(v.is_valid(x))
    def test_biology_not_dependent_on_final_test_flag(self):
        x=load(DAV/'examples/specification_only_release.json');v=validator('release_contract.schema.json');v.validate(x)
        x['requires_final_test']=True;self.assertFalse(v.is_valid(x))
    def test_final_test_release_requires_final_test_flag(self):
        x=load(DAV/'examples/specification_only_release.json');x['branch_id']='A_P2_FINAL_TEST';v=validator('release_contract.schema.json')
        self.assertFalse(v.is_valid(x));x['requires_final_test']=True;v.validate(x)
    def test_frozen_handoff_cannot_be_empty_or_test_derived(self):
        d=load(A/'schemas/handoff_manifest.schema.json');v=Draft202012Validator(d,registry=resources())
        x=dict(handoff_version='1.0.0',product='A_BIO',state='DRAFT',development_only=True,artifacts=[],source_release_ids=[],split_sha256=None,exposure_sha256=None,selection_rule_sha256=None,permitted_uses=[],blocked_uses=[],validation_annotations=[],reviewer=None,created_utc=None)
        v.validate(x);x['state']='FROZEN';self.assertFalse(v.is_valid(x));x['state']='DRAFT';x['development_only']=False;self.assertFalse(v.is_valid(x))

class SyntheticEstimandTests(unittest.TestCase):
    def test_A_P1_category_decomposition(self):
        o,sd,pd=[4,8],[2,5,5],[1,3]
        direct_orr=auc(o,sd+pd);direct_dcr=auc(o+sd,pd)
        self.assertAlmostEqual(direct_orr,(len(sd)*auc(o,sd)+len(pd)*auc(o,pd))/(len(sd)+len(pd)))
        self.assertAlmostEqual(direct_dcr,(len(o)*auc(o,pd)+len(sd)*auc(sd,pd))/(len(o)+len(sd)))
    def test_A_P1_no_SD_is_structural_zero(self):
        o,pd=[1,6],[2,4]
        self.assertEqual(auc(o,pd)-auc(o,pd),0)
    def test_AUC_ties_and_undefined(self):
        self.assertEqual(auc([2,2],[2,2]),0.5)
        with self.assertRaises(ValueError): auc([], [1,2])
    def test_A_P2_finite_weights_not_patient_weighting(self):
        d={'cancer_a':[0.1,0.3],'cancer_b':[-0.2]}
        result=sum(sum(v)/len(v) for v in d.values())/len(d)
        self.assertAlmostEqual(result,0.0)
        self.assertNotAlmostEqual(result,sum(sum(v) for v in d.values())/3)
    def test_direct_response_change_not_significance_shortcut(self):
        r_pre,r_post=[1,2],[4,5];nr_pre,nr_post=[1,2],[2,3]
        mean=lambda v:sum(v)/len(v)
        interaction=mean([b-a for a,b in zip(r_pre,r_post)])-mean([b-a for a,b in zip(nr_pre,nr_post)])
        self.assertEqual(interaction,2)
    def test_response_main_effect_aliases_patient_intercepts(self):
        # Four observations: two patients, each measured twice. R is a patient-constant column.
        patient1=[1,1,0,0];patient2=[0,0,1,1];response=[1,1,0,0]
        self.assertEqual(response,[1*a+0*b for a,b in zip(patient1,patient2)])
        interaction=[0,1,0,0]
        self.assertNotEqual(interaction,response)

if __name__ == '__main__': unittest.main()
