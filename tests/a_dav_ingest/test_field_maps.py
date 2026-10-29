from pathlib import Path

from tools.a_dav.field_maps import load_field_map


def test_riaz_field_map_is_schema_valid_and_contains_only_declarative_rules():
    path = Path(__file__).parents[2] / "tools/a_dav/field_maps/riaz_gse91061.json"
    field_map = load_field_map(path)
    assert set(field_map["source_objects"]) == {
        "geo_family_soft", "author_sample_table", "author_clinical_table", "author_analysis_code",
        "author_fpkm_hg19", "ncbi_tpm_grch38", "ncbi_annotation_grch38",
        "cbioportal_sample", "cbioportal_patient"}
    assert field_map["sample_identity"]["title_regex"] == "^(Pt\\d+)_(Pre|On)"
    assert field_map["author_sample_table"]["duplicated_headers"]["Response"] == [10, 11]
    assert field_map["author_sample_table"]["sample_name_rule"]["replacement"] == "-\\1"
    assert field_map["author_clinical_table"]["source_of_record_for"] == ["BOR", "Cohort"]
    assert field_map["treatment"]["agent"] == "nivolumab"
    assert field_map["measurement_representations"]["author_fpkm_hg19"]["unit"] == "FPKM"
    author_fpkm = field_map["measurement_representations"]["author_fpkm_hg19"]
    assert author_fpkm["transform"] == "NONE"
    assert author_fpkm["genome_build"] == "hg19"
    assert author_fpkm["annotation"] == "Entrez"
    assert author_fpkm["feature_identifier_system"] == "Entrez"
    assert author_fpkm["platform"] == "GPL9052"
    assert author_fpkm["platform_title"] == "Illumina Genome Analyzer (Homo sapiens)"
    assert author_fpkm["instrument_model"] == "Illumina Genome Analyzer"
    assert set(author_fpkm["evidence"]) >= {
        "unit", "transform", "genome_build", "annotation", "feature_identifier_system",
        "platform", "platform_title", "instrument_model",
    }
    assert all(pointer.startswith("geo_family_soft:") for pointer in author_fpkm["evidence"].values())
    assert field_map["measurement_representations"]["ncbi_tpm_grch38"]["unit"] == "TPM"
    assert field_map["measurement_representations"]["conversion"] == "PROHIBITED"
    assert field_map["v3"]["primary_representation"] == "ncbi_tpm_grch38"
    assert field_map["v3"]["fallback_representation"] == "author_fpkm_hg19"
    assert field_map["v3"]["qc_policy"]["numeric_thresholds"] == []
    assert field_map["v3"]["qc_policy"]["historical_flags_only"] == [
        "PAPER_PCA_PT3", "TABLES6_A_R_FOUR_EXCLUSIONS"]
    assert field_map["v3"]["documentation"]["ncbi_tpm_grch38"]["status"] == "UNVERIFIED"
    assert field_map["v3"]["documentation"]["author_fpkm_hg19"]["status"] == "DOCUMENTED"
    assert field_map["v3"]["expected_counts"] == {
        "full_header_columns": 109, "baseline_selected": 51, "on_selected": 0}
    assert field_map["v3"]["representation_identity"]["ncbi_tpm_grch38"]["annotation_role"] == (
        "ncbi_annotation_grch38")
    assert field_map["v3"]["representation_identity"]["author_fpkm_hg19"]["annotation_role"] is None
    assert field_map["v3"]["representation_identity"]["author_fpkm_hg19"]["certification_level"] == (
        "ID_FORMAT_AND_UNIQUENESS")
    assert field_map["proposal_generation"]["episode"]["index_event"] == "START_OF_NIVOLUMAB"
    assert field_map["proposal_generation"]["exposure"]["author_cohort_prior_ici"] == {
        "NIV3-NAIVE": "NO", "NIV3-PROG": "YES"}
    assert field_map["proposal_generation"]["overlap"]["single_cohort_disposition"] == "NON_BLOCKING"
    assert field_map["proposal_generation"]["overlap"]["joint_split_disposition"] == "BLOCKING"
    assert field_map["proposal_generation"]["prior_exposure"]["use"] == "METADATA_INSPECTION"
    decisions = field_map["decision_config"]
    assert decisions["treatment_episode_binding"]["decision_status"] == "PROPOSED_UNSIGNED"
    assert decisions["treatment_episode_binding"]["author_cohort_target_field"] == "prior_ici"
    assert decisions["treatment_episode_binding"]["reviewer"] is None
    assert decisions["treatment_episode_binding"]["reviewed_utc"] is None
    assert decisions["timing"]["collection_day"] == "NOT_REPORTED"
    assert decisions["overlap_exposure"]["site_level_independence"] == "UNKNOWN"
    assert len(field_map["worksheet_prefill"]["gates"]) == 9
    assert field_map["source_objects"]["cbioportal_sample"]["role"] == "harmonized_cross_check"
    assert field_map["proposal_generation"]["stage_config"]["admission"]["required_source_roles"] == [
        "geo_family_soft", "author_sample_table", "author_clinical_table", "author_fpkm_hg19"]
    assert set(field_map["proposal_generation"]["stage_config"]["admission"]["required_source_roles"]).isdisjoint({
        "ncbi_tpm_grch38", "ncbi_annotation_grch38", "author_analysis_code",
        "cbioportal_sample", "cbioportal_patient"})
    assert field_map["biological_compartment"]["evidence"] == (
        "geo_family_soft:!Sample_source_name_ch1")
    assert field_map["biological_compartment"]["source_name_map"] == {"tumor": "TUMOUR"}
    hashes = [item["sha256"] for item in field_map["source_objects"].values()]
    assert len(hashes) == 9
    assert all(isinstance(value, str) and len(value) == 64 for value in hashes)
    assert field_map["source_objects"]["geo_family_soft"]["sha256"] == (
        "2ecd5f064b076fdce58fd651b0a3404cc01ef889c5cfb8d760dc5c7a01adeaf9")
    assert field_map["source_objects"]["cbioportal_sample"]["sha256"] == (
        "dcaf0a5c77c230480b7ea72491e7fdc6ddd2829ea5cdcf712ece5270d02e4199")


def test_study_class_is_optional_and_uses_the_frozen_registry_enum(tmp_path):
    import json

    from tools.a_dav.field_maps import FIELD_MAP_SCHEMA

    field_map = load_field_map(Path("tools/a_dav/field_maps/riaz_gse91061.json"))
    schema = json.loads(FIELD_MAP_SCHEMA.read_text())
    frozen = json.loads(Path("specs/A_DATA_ACQUISITION_VALIDATION/schemas/study_registry.schema.json").read_text())
    assert field_map["study_class"] == "CLINICAL_ICI"
    assert schema["properties"]["study_class"]["enum"] == frozen["properties"]["study_class"]["enum"]
    assert schema["properties"]["study_class"]["enum"] == [
        "CLINICAL_ICI", "NON_ICI_COMPARATOR", "VACCINE", "ADOPTIVE_CELL",
        "DENDRITIC_CELL", "MECHANISTIC_CELL_MODEL", "UNTREATED_MOLECULAR", "OTHER",
    ]
    undeclared = dict(field_map)
    undeclared.pop("study_class")
    path = tmp_path / "field-map-without-study-class.json"
    path.write_text(json.dumps(undeclared))
    assert "study_class" not in load_field_map(path)


def test_invented_template_is_a_complete_field_map():
    field_map = load_field_map(Path('tools/a_dav/field_maps/TEMPLATE.json'))
    assert field_map['cohort'] == 'invented_cohort'
    assert set(field_map['geo']['characteristics']) >= {'patient', 'visit', 'response'}
    assert field_map['biological_compartment']['source_name_map']
    assert field_map['author_clinical_table']['source_of_record_for']
    assert field_map['labels']['geo_response']
    assert field_map['measurement_representations']['invented_expression']['unit'] == 'COUNTS'
    assert field_map['proposal_generation']['episode']['index_event'] == 'START_OF_INVENTED_TREATMENT'
    assert field_map['proposal_generation']['stage_config']['split']['policy']['permanent_role'] == 'DEVELOPMENT'
    assert field_map['source_validation']['roles']
    assert field_map['v3']['expected_counts']['full_header_columns'] == 3


def test_validate_command_reports_valid_and_plain_errors(tmp_path):
    import json
    import os
    import subprocess
    import sys

    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    valid = subprocess.run([sys.executable, '-m', 'tools.a_dav.field_maps', 'validate',
                            'tools/a_dav/field_maps/TEMPLATE.json'], capture_output=True, text=True, env=env)
    assert valid.returncode == 0 and valid.stdout.strip() == 'valid'
    invalid_path = tmp_path / 'bad.json'
    invalid_path.write_text(json.dumps({'cohort': 'invented'}))
    invalid = subprocess.run([sys.executable, '-m', 'tools.a_dav.field_maps', 'validate', str(invalid_path)],
                             capture_output=True, text=True, env=env)
    assert invalid.returncode != 0
    assert 'branch_id' in invalid.stdout and 'required' in invalid.stdout
    assert 'Traceback' not in invalid.stdout + invalid.stderr


def test_cross_check_source_roles_are_not_cohort_specific(tmp_path):
    import json

    example = json.loads(Path('tools/a_dav/field_maps/TEMPLATE.json').read_text())
    example['harmonized_cross_checks'] = [{'resource': 'invented atlas', 'role': 'CROSS_CHECK_ONLY',
                                           'expected_sample_count': 3,
                                           'source_object_roles': ['invented_atlas']}]
    path = tmp_path / 'map.json'
    path.write_text(json.dumps(example))
    assert load_field_map(path)['harmonized_cross_checks'][0]['source_object_roles'] == ['invented_atlas']


def test_field_map_allows_tagged_source_derived_expression_binding(tmp_path):
    import json
    from pathlib import Path
    from tools.a_dav.field_maps import load_field_map
    original=json.loads(Path('tools/a_dav/field_maps/hugo_gse78220.json').read_text())
    rule=original['expression_column_map']['geo_author_expression']
    rule['evidence_type']='DERIVED_FROM_OBJECT'
    rule['rule_name']='TITLE_TOKEN_AND_SOURCE_VISIT'
    target=tmp_path/'map.json';target.write_text(json.dumps(original))
    loaded=load_field_map(target)
    assert loaded['expression_column_map']['geo_author_expression']['rule_name']=='TITLE_TOKEN_AND_SOURCE_VISIT'


def test_derived_binding_requires_its_rule_name(tmp_path):
    import json
    import pytest
    from pathlib import Path
    from tools.a_dav.field_maps import FieldMapError, load_field_map
    original=json.loads(Path('tools/a_dav/field_maps/hugo_gse78220.json').read_text())
    original['expression_column_map']['geo_author_expression'].pop('rule_name')
    target=tmp_path/'map.json';target.write_text(json.dumps(original))
    with pytest.raises(FieldMapError):
        load_field_map(target)


def test_object_derived_fact_requires_a_rule_and_evidence_tag(tmp_path):
    import json
    import pytest
    from pathlib import Path
    from tools.a_dav.field_maps import FieldMapError, load_field_map
    original=json.loads(Path('tools/a_dav/field_maps/gse248014.json').read_text())
    del original['measurement_representations']['geo_rsem_expected_counts']['derived_facts']['unit']['rule']
    target=tmp_path/'map.json';target.write_text(json.dumps(original))
    with pytest.raises(FieldMapError):
        load_field_map(target)
