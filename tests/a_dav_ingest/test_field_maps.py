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
    assert field_map["measurement_representations"]["ncbi_tpm_grch38"]["unit"] == "TPM"
    assert field_map["measurement_representations"]["conversion"] == "PROHIBITED"
    assert field_map["source_objects"]["cbioportal_sample"]["role"] == "harmonized_cross_check"
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
