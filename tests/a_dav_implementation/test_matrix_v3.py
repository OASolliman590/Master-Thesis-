"""Invented-ID tests for outcome-blind V3 matrix validation."""
from __future__ import annotations

import gzip
import ast
import inspect
from pathlib import Path

from tools.a_dav.matrix_v3 import main, run_v3_with_fallback, validate_v3_matrix


def _matrix(path: Path, text: str) -> Path:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return path


def _arguments() -> dict[str, object]:
    return {
        "expected_sample_ids": {"invented_pre_1", "invented_pre_2", "invented_on_1"},
        "pre_sample_ids": {"invented_pre_1", "invented_pre_2"},
        "on_sample_ids": {"invented_on_1"},
        "annotation_feature_ids": {"101", "102"},
        "selected_sample_ids": {"invented_pre_1", "invented_pre_2"},
        "expected_counts": {"full_header_columns": 3, "baseline_selected": 2, "on_selected": 0},
        "annotation_evidence_status": "PINNED_ANNOTATION",
        "feature_id_pattern": r"^[0-9]+$",
        "annotation_label": "invented annotation",
        "genome_build": "invented build",
        "certification_level": "MATCHED_PINNED_ANNOTATION",
        "representation": "invented_tpm",
        "processing_documented": True,
    }


def test_v3_passes_complete_matrix_and_flags_duplicate_profiles_without_removing_them(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "matrix.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1.0\t1.0\t2\n102\t0\t0\t3\n")
    result = validate_v3_matrix(matrix, **_arguments())
    assert result["status"] == "PASS"
    assert result["counts"] == {
        "features": 2, "sample_columns": 3, "selected_pre_columns": 2,
        "source_on_inventory_columns": 1, "selected_on_columns": 0,
        "cells": 6, "missing_cells": 0,
        "nonnumeric_cells": 0, "nonfinite_cells": 0, "negative_cells": 0,
        "blank_feature_ids": 0, "duplicate_feature_ids": 0,
        "feature_identifier_system_incompatible": 0, "unmapped_features": 0,
        "row_width_mismatches": 0,
        "duplicate_profile_groups": 1, "quarantined_columns": 2,
    }
    assert result["checks"]["duplicate_profiles"]["groups"] == [
        ["invented_pre_1", "invented_pre_2"]]
    assert result["checks"]["duplicate_profiles"]["disposition"] == "QUARANTINE_KEEP"


def test_v3_blocks_missing_values_and_annotation_mismatch(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "matrix.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1.0\t\t2\nid-x\t0\t0\t3\n")
    result = validate_v3_matrix(matrix, **_arguments())
    assert result["status"] == "BLOCKED"
    assert "MISSING_CELLS_PRESENT" in result["reasons"]
    assert "FEATURE_IDENTIFIER_SYSTEM_INCOMPATIBLE" in result["reasons"]
    assert result["counts"]["missing_cells"] == 1
    assert result["counts"]["feature_identifier_system_incompatible"] == 1
    assert result["checks"]["numeric_validity"]["counts"]["missing_cells"] == 1
    assert result["checks"]["feature_identity"]["counts"]["identifier_system_incompatible"] == 1


def test_unmapped_numeric_feature_ids_are_retained_as_coverage_outcomes(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "matrix.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1\t2\t3\n102\t2\t3\t4\n")
    args = _arguments()
    args["annotation_feature_ids"] = {"101"}
    result = validate_v3_matrix(matrix, **args)
    assert result["status"] == "PASS"
    assert result["checks"]["feature_identity"]["counts"]["unmapped_features"] == 1
    assert result["checks"]["feature_identity"]["unmapped_disposition"] == "RETAINED_COVERAGE_OUTCOME"


def test_v3_blocks_unreconciled_header_nonfinite_and_negative_values(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "matrix.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_extra\n"
                     "101\tNaN\t-1\t2\n")
    result = validate_v3_matrix(matrix, **_arguments())
    assert result["status"] == "BLOCKED"
    assert {"SAMPLE_HEADER_RECONCILIATION_FAILED", "NONFINITE_VALUES_PRESENT",
            "NEGATIVE_VALUES_PRESENT"}.issubset(set(result["reasons"]))


def test_fallback_runs_when_primary_processing_is_not_documented(tmp_path: Path) -> None:
    primary = _matrix(tmp_path / "primary.tsv.gz",
                      "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                      "101\t1\t2\t3\n102\t2\t3\t4\n")
    fallback = _matrix(tmp_path / "fallback.tsv.gz",
                       "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                       "101\t1.5\t2.5\t3.5\n102\t2.5\t3.5\t4.5\n")
    args = _arguments()
    result = run_v3_with_fallback(primary, fallback, primary_arguments={
        **args, "representation": "invented_primary", "processing_documented": False,
    }, fallback_arguments={
        **args, "representation": "invented_fallback", "processing_documented": True,
    })
    assert result["primary"]["status"] == "BLOCKED"
    assert "PROCESSING_DOCUMENTATION_INSUFFICIENT" in result["primary"]["reasons"]
    assert result["fallback"]["status"] == "PASS"
    assert result["selected_representation"] == "invented_fallback"
    assert result["effective_primary"] == "invented_fallback"
    assert result["effective_sensitivity"] == "invented_primary"


def test_v3_result_does_not_depend_on_or_read_outcome_fields(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "matrix.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1\t2\t3\n102\t2\t3\t4\n")
    result = validate_v3_matrix(matrix, **_arguments())
    assert not ({"BOR", "response", "response_group", "outcome"} & set(result))
    for function in (validate_v3_matrix, run_v3_with_fallback, main):
        tree = ast.parse(inspect.getsource(function))
        identifiers = {node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert not ({"bor", "response", "response_group", "outcome", "clinical_outcomes"} & identifiers)


def test_empty_baseline_selection_and_declared_count_mismatch_block(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "matrix.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1\t2\t3\n")
    args = {
        **_arguments(),
        "selected_sample_ids": set(),
        "expected_counts": {"full_header_columns": 3, "baseline_selected": 2, "on_selected": 0},
        "annotation_evidence_status": "PINNED_ANNOTATION",
        "feature_id_pattern": r"^[0-9]+$",
        "annotation_label": "invented annotation",
        "genome_build": "invented build",
    }
    result = validate_v3_matrix(matrix, **args)
    assert result["status"] == "BLOCKED"
    assert "EMPTY_BASELINE_SELECTION" in result["reasons"]
    assert "BASELINE_SELECTION_COUNT_MISMATCH" in result["reasons"]

    args["selected_sample_ids"] = {"invented_pre_1"}
    result = validate_v3_matrix(matrix, **args)
    assert result["status"] == "BLOCKED"
    assert "BASELINE_SELECTION_COUNT_MISMATCH" in result["reasons"]


def test_header_only_matrix_blocks_data_dependent_checks_consistently(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "header-only.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n")
    args = {
        **_arguments(),
        "selected_sample_ids": {"invented_pre_1", "invented_pre_2"},
        "expected_counts": {"full_header_columns": 3, "baseline_selected": 2, "on_selected": 0},
        "annotation_evidence_status": "PINNED_ANNOTATION",
        "feature_id_pattern": r"^[0-9]+$",
        "annotation_label": "invented annotation",
        "genome_build": "invented build",
    }
    result = validate_v3_matrix(matrix, **args)
    assert result["status"] == "BLOCKED"
    assert result["checks"]["dimensions_and_parse"]["status"] == "BLOCKED"
    assert result["checks"]["feature_identity"]["status"] == "BLOCKED"
    assert result["checks"]["numeric_validity"]["status"] == "BLOCKED"


def test_duplicate_profiles_compare_numeric_values_and_keep_private_column_ids(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "numeric-profiles.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1\t1.0\t4\n102\t1e0\t1\t5\n103\t2.0\t2e0\t6\n")
    args = {
        **_arguments(),
        "selected_sample_ids": {"invented_pre_1", "invented_pre_2"},
        "expected_counts": {"full_header_columns": 3, "baseline_selected": 2, "on_selected": 0},
        "annotation_evidence_status": "PINNED_ANNOTATION",
        "feature_id_pattern": r"^[0-9]+$",
        "annotation_label": "invented annotation",
        "genome_build": "invented build",
    }
    result = validate_v3_matrix(matrix, **args)
    assert result["counts"]["duplicate_profile_groups"] == 1
    assert result["checks"]["duplicate_profiles"]["groups"] == [["invented_pre_1", "invented_pre_2"]]


def test_missing_annotation_evidence_blocks_and_format_only_is_limited(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / "annotation-evidence.tsv.gz",
                     "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                     "101\t1\t2\t3\n102\t2\t3\t4\n")
    common = {
        **_arguments(),
        "selected_sample_ids": {"invented_pre_1", "invented_pre_2"},
        "expected_counts": {"full_header_columns": 3, "baseline_selected": 2, "on_selected": 0},
        "feature_id_pattern": r"^[0-9]+$",
        "annotation_label": "invented hg19 Entrez identifiers",
        "genome_build": "invented hg19",
    }
    missing = validate_v3_matrix(matrix, **{
        **common, "annotation_feature_ids": set(), "annotation_evidence_status": "PINNED_ANNOTATION",
    })
    assert missing["status"] == "BLOCKED"
    assert "ANNOTATION_EVIDENCE_MISSING" in missing["reasons"]

    limited = validate_v3_matrix(matrix, **{
        **common, "annotation_feature_ids": None,
        "annotation_evidence_status": "DECLARED_ID_FORMAT_ONLY",
        "certification_level": "ID_FORMAT_AND_UNIQUENESS",
        "feature_identity_limit": "No pinned hg19 annotation object; numeric Entrez format and uniqueness only.",
    })
    assert limited["checks"]["feature_identity"]["status"] == "PASS"
    assert limited["checks"]["feature_identity"]["certification_level"] == "ID_FORMAT_AND_UNIQUENESS"
    assert "No pinned hg19 annotation object" in limited["checks"]["feature_identity"]["limit"]


def test_fallback_effective_sensitivity_is_the_nonselected_representation(tmp_path: Path) -> None:
    primary = _matrix(tmp_path / "primary.tsv.gz",
                      "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                      "101\t1\t2\t3\n102\t2\t3\t4\n")
    fallback = _matrix(tmp_path / "fallback.tsv.gz",
                       "GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n"
                       "101\t1.5\t2.5\t3.5\n102\t2.5\t3.5\t4.5\n")
    args = {
        **_arguments(),
        "selected_sample_ids": {"invented_pre_1", "invented_pre_2"},
        "expected_counts": {"full_header_columns": 3, "baseline_selected": 2, "on_selected": 0},
        "annotation_evidence_status": "PINNED_ANNOTATION",
        "feature_id_pattern": r"^[0-9]+$",
        "annotation_label": "invented annotation",
        "genome_build": "invented build",
    }
    result = run_v3_with_fallback(primary, fallback, primary_arguments={
        **args, "representation": "invented_tpm", "processing_documented": False,
    }, fallback_arguments={
        **args, "representation": "invented_fpkm", "processing_documented": True,
    })
    assert result["effective_primary"] == "invented_fpkm"
    assert result["effective_sensitivity"] == "invented_tpm"


def test_patient_free_summary_omits_private_duplicate_column_identifiers() -> None:
    from tools.a_dav.matrix_v3 import patient_free_summary

    result = {"primary": {"representation": "invented_tpm", "status": "BLOCKED",
                          "counts": {"duplicate_profile_groups": 1}, "reasons": [],
                          "checks": {"duplicate_profiles": {"groups": [["invented_a", "invented_b"]]}}},
              "fallback": None, "selected_representation": "invented_tpm",
              "effective_primary": "invented_tpm", "effective_sensitivity": "invented_fpkm",
              "selection_reason": "PRIMARY_V3_PASSED"}
    summary = patient_free_summary(result)
    assert "invented_a" not in str(summary)
    assert "invented_b" not in str(summary)
    assert summary["primary"]["counts"]["duplicate_profile_groups"] == 1



def test_v3_accepts_sample_rows_and_matches_transposed_counts(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'row-matrix.tsv.gz',
        'sample\t101\t102\ninvented_pre_1\t1\t0\ninvented_pre_2\t1\t0\ninvented_on_1\t2\t3\n')
    result = validate_v3_matrix(matrix, **_arguments(), orientation='samples_as_rows')
    assert result['status'] == 'PASS'
    assert result['counts']['features'] == 2
    assert result['counts']['sample_columns'] == 3
    assert result['counts']['cells'] == 6
    assert result['counts']['duplicate_profile_groups'] == 1


def test_primary_only_v3_does_not_invent_a_fallback(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'primary.tsv.gz',
        'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n101\t1\t2\t3\n102\t2\t3\t4\n')
    result = run_v3_with_fallback(matrix, None, primary_arguments=_arguments(), fallback_arguments=None)
    assert result['primary']['status'] == 'PASS'
    assert result['fallback'] is None
    assert result['selected_representation'] == 'invented_tpm'
    assert result['effective_sensitivity'] is None
    blocked = run_v3_with_fallback(matrix, None,
        primary_arguments={**_arguments(), 'processing_documented': False}, fallback_arguments=None)
    assert blocked['primary']['status'] == 'BLOCKED'
    assert blocked['selected_representation'] is None
    assert blocked['fallback'] is None


def test_v3_blocks_when_feature_identity_is_unknown(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'primary.tsv.gz',
        'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n101\t1\t2\t3\n102\t2\t3\t4\n')
    result = validate_v3_matrix(matrix, **{**_arguments(), 'annotation_evidence_status': 'UNKNOWN',
        'annotation_feature_ids': None, 'feature_id_pattern': '.*', 'certification_level': 'UNKNOWN'})
    assert result['status'] == 'BLOCKED'
    assert 'FEATURE_IDENTITY_UNDOCUMENTED' in result['reasons']
    assert result['checks']['numeric_validity']['status'] == 'PASS'


def test_v3_blocks_undocumented_measurement_fields(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'primary.tsv.gz',
        'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n101\t1\t2\t3\n102\t2\t3\t4\n')
    result = validate_v3_matrix(matrix, **_arguments(), undocumented_fields=['transform'])
    assert result['status'] == 'BLOCKED'
    assert result['checks']['documented_processing']['status'] == 'BLOCKED'
    assert result['checks']['documented_processing']['undocumented_fields'] == ['transform']


def test_v3_validates_xlsx_with_single_representation(tmp_path: Path) -> None:
    import zipfile
    book = tmp_path / 'invented.xlsx'
    with zipfile.ZipFile(book, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Gene</t></si><si><t>invented_pre_1</t></si><si><t>invented_pre_2</t></si><si><t>invented_on_1</t></si><si><t>101</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c><c r="D1" t="s"><v>3</v></c></row><row r="2"><c r="A2" t="s"><v>4</v></c><c r="B2"><v>1</v></c><c r="C2"><v>2</v></c><c r="D2"><v>3</v></c></row></sheetData></worksheet>')
    result = validate_v3_matrix(book, **_arguments(), source_format='XLSX_NUMERIC')
    assert result['status'] == 'PASS'
    assert result['counts']['features'] == 1
    assert result['counts']['cells'] == 3


def test_primary_only_geo_cli_runs_checks_and_records_unknown_evidence(tmp_path: Path, monkeypatch) -> None:
    import hashlib
    import json
    from tools.a_dav import matrix_v3
    soft = b'^SAMPLE = invented-sample\n!Sample_geo_accession = invented-sample\n!Sample_title = invented-patient_pre\n!Sample_characteristics_ch1 = visit: pre\n'
    matrix = b'gene,invented-patient_pre\n101,1\n'
    objects = tmp_path / 'store' / 'objects'
    objects.mkdir(parents=True)
    geo_sha, matrix_sha = [hashlib.sha256(blob).hexdigest() for blob in (soft, matrix)]
    (objects / geo_sha).write_bytes(soft)
    (objects / matrix_sha).write_bytes(matrix)
    mapping = {'cohort': 'invented', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'sha256': geo_sha, 'format': 'GEO_FAMILY_SOFT', 'locator': 'https://example.org/soft', 'version': '1'},
                           'expression': {'sha256': matrix_sha, 'format': 'MATRIX_HEADER_CSV', 'locator': 'https://example.org/matrix', 'version': '1'}},
        'sample_identity': {'title_regex': '^(invented-patient)_', 'patient_group': 1},
        'geo': {'characteristics': {'visit': 'visit'}},
        'geo_ingest': {'baseline_values': ['pre'], 'baseline_tie_rule': None},
        'expression_column_map': {'expression': {'method': 'TITLE'}},
        'measurement_representations': {'expression': {'unit': 'counts', 'transform': 'NONE', 'platform': 'invented-platform', 'genome_build': 'invented-build', 'annotation': 'UNKNOWN', 'feature_identifier_system': 'UNKNOWN'}},
        'v3': {'primary_representation': 'expression', 'sample_inventory_source_role': 'geo_family_soft',
               'expected_counts': {'full_header_columns': 1, 'baseline_selected': 1, 'on_selected': 0},
               'source_object_roles': {'primary': 'expression'}, 'delimiters': {'expression': ','},
               'compressed': {'expression': False}, 'documentation': {'expression': {'status': 'DOCUMENTED'}}}}
    config = tmp_path / 'map.json'
    config.write_text(json.dumps(mapping))
    monkeypatch.setattr(matrix_v3, 'validate_output_path', lambda path: path)
    assert main(['--store', str(tmp_path / 'store'), '--field-map', str(config), '--out', str(tmp_path / 'out')]) == 2
    receipt = json.loads((tmp_path / 'out' / 'receipt.json').read_text())
    assert receipt['checks']['primary']['status'] == 'BLOCKED'
    assert 'FEATURE_IDENTITY_UNDOCUMENTED' in receipt['checks']['primary']['reasons']
    assert receipt['checks']['primary']['checks']['numeric_validity']['status'] == 'PASS'
    assert receipt['checks']['primary']['counts']['selected_pre_columns'] == 1
    assert receipt['checks']['fallback'] is None
    mapping['measurement_representations']['expression']['feature_identifier_system'] = 'invented numeric IDs'
    mapping['v3']['representation_identity'] = {'expression': {'annotation_role': None, 'annotation_evidence_status': 'DECLARED_ID_FORMAT_ONLY', 'identifier_pattern': '^[0-9]+$', 'certification_level': 'FORMAT_ONLY', 'limit': 'Format only; invented evidence'}}
    config.write_text(json.dumps(mapping))
    assert main(['--store', str(tmp_path / 'store'), '--field-map', str(config), '--out', str(tmp_path / 'out2')]) == 0
    checked = json.loads((tmp_path / 'out2' / 'receipt.json').read_text())
    assert checked['checks']['primary']['status'] == 'PASS'


def test_v3_ignores_only_declared_auxiliary_columns(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'matrix.tsv.gz',
        'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\t\tgene\n'
        '101\t1\t2\t3\t\tannotation\n102\t2\t3\t4\t\tannotation\n')
    result = validate_v3_matrix(matrix, **_arguments(), auxiliary_columns=[{'index': 4, 'header': ''}, {'index': 5, 'header': 'gene'}])
    assert result['status'] == 'PASS'
    assert result['counts']['sample_columns'] == 3
    assert result['counts']['nonnumeric_cells'] == 0
    assert result['counts']['missing_cells'] == 0


def test_primary_only_non_geo_cli_runs_without_fallback(tmp_path: Path, monkeypatch) -> None:
    import hashlib
    import json
    from tools.a_dav import matrix_v3
    soft = b'^SAMPLE = invented-sample\n!Sample_geo_accession = invented-sample\n!Sample_title = invented-patient_Pre\n!Sample_characteristics_ch1 = visit: Pre\n'
    matrix = b'gene,invented-patient_Pre\n101,1\n'
    objects=tmp_path/'store'/'objects';objects.mkdir(parents=True)
    geo_sha,matrix_sha=[hashlib.sha256(blob).hexdigest() for blob in (soft,matrix)]
    (objects/geo_sha).write_bytes(soft);(objects/matrix_sha).write_bytes(matrix)
    mapping={'source_objects':{'soft':{'sha256':geo_sha},'expression':{'sha256':matrix_sha}},
      'sample_identity':{'title_regex':'^(invented-patient)_(Pre)$','patient_group':1,'visit_group':2},
      'geo':{'characteristics':{'visit':'visit'}},'measurement_representations':{'expression':{'annotation':'invented'}},
      'v3':{'primary_representation':'expression','sample_inventory_source_role':'soft',
      'expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},
      'source_object_roles':{'primary':'expression'},'header_key_by_role':{'expression':'title'},
      'representation_identity':{'expression':{'annotation_role':None,'genome_build':'invented','annotation_evidence_status':'DECLARED_ID_FORMAT_ONLY','identifier_pattern':'^[0-9]+$','certification_level':'FORMAT_ONLY','limit':'format only'}},
      'delimiters':{'expression':','},'compressed':{'expression':False},'documentation':{'expression':{'status':'DOCUMENTED'}}}}
    config=tmp_path/'map.json';config.write_text(json.dumps(mapping));monkeypatch.setattr(matrix_v3,'validate_output_path',lambda path:path)
    assert main(['--store',str(tmp_path/'store'),'--field-map',str(config),'--out',str(tmp_path/'out')]) == 0
    r=json.loads((tmp_path/'out'/'receipt.json').read_text())
    assert r['checks']['primary']['status']=='PASS' and r['checks']['fallback'] is None


def test_v3_declared_missing_gene_exclusion_preserves_and_reports_missingness(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'matrix.tsv.gz',
        'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n101\t1\t\t2\n102\t0\t0\t3\n')
    result = validate_v3_matrix(matrix, **_arguments(), missing_policy='EXCLUDE_FEATURE_IF_ANY_MISSING')
    assert result['status'] == 'PASS'
    assert result['counts']['missing_cells'] == 1
    assert result['counts']['excluded_missing_features'] == 1
    assert result['checks']['numeric_validity']['missing_policy'] == 'EXCLUDE_FEATURE_IF_ANY_MISSING'


def test_v3_primary_checks_hash_bound_object_derived_feature_type(tmp_path: Path, monkeypatch) -> None:
    import hashlib,json
    from tools.a_dav import matrix_v3
    from tools.a_dav.object_evidence import derive_object_evidence
    soft=b'^SAMPLE = invented-sample\n!Sample_geo_accession = invented-sample\n!Sample_title = invented-patient\n!Sample_characteristics_ch1 = visit: pre\n'
    raw=b'gene,invented-patient\n101,1\n'; gs=hashlib.sha256(soft).hexdigest();ms=hashlib.sha256(raw).hexdigest();o=tmp_path/'store'/'objects';o.mkdir(parents=True);(o/gs).write_bytes(soft);(o/ms).write_bytes(raw)
    facts=derive_object_evidence([('101',['1'])],source_sha256=ms)
    mapping={'cohort':'invented','branch_id':'A_BASELINE_BIO',
      'source_objects':{'geo_family_soft':{'sha256':gs,'format':'GEO_FAMILY_SOFT','locator':'https://example.org/geo','version':'1'},'expression':{'sha256':ms,'format':'MATRIX_HEADER_CSV','locator':'https://example.org/matrix','version':'1'}},
      'sample_identity':{'title_regex':'^(invented-patient)$','patient_group':1},'geo':{'characteristics':{'visit':'visit'}},'geo_ingest':{'baseline_values':['pre'],'baseline_tie_rule':None},
      'expression_column_map':{'expression':{'method':'TITLE'}},
      'measurement_representations':{'expression':{'unit':'READ_COUNTS','transform':'NONE','platform':'invented','genome_build':'invented','annotation':'UNKNOWN','feature_identifier_system':'ENTREZ_GENE','derived_facts':{'unit':facts['unit'],'transform':facts['transform'],'feature_identifier_system':facts['feature_identifier_system']}}},
      'v3':{'primary_representation':'expression','sample_inventory_source_role':'geo_family_soft','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'source_object_roles':{'primary':'expression'},'delimiters':{'expression':','},'compressed':{'expression':False},'documentation':{'expression':{'status':'DOCUMENTED'}}}}
    config=tmp_path/'map.json';config.write_text(json.dumps(mapping));monkeypatch.setattr(matrix_v3,'validate_output_path',lambda path:path)
    assert main(['--store',str(tmp_path/'store'),'--field-map',str(config),'--out',str(tmp_path/'out')])==0
    result=json.loads((tmp_path/'out'/'receipt.json').read_text())['checks']['primary']
    assert result['status']=='PASS'
    assert result['checks']['feature_identity']['certification_level']=='DERIVED_FROM_OBJECT'
    forged=mapping['measurement_representations']['expression']['derived_facts']['feature_identifier_system']
    forged['value']='GENE_SYMBOL';mapping['measurement_representations']['expression']['feature_identifier_system']='GENE_SYMBOL'
    config.write_text(json.dumps(mapping))
    assert main(['--store',str(tmp_path/'store'),'--field-map',str(config),'--out',str(tmp_path/'forged')])==2
    blocked=json.loads((tmp_path/'forged'/'receipt.json').read_text())['checks']['primary']
    assert blocked['status']=='BLOCKED'
    assert 'derived_evidence_conflict:feature_identifier_system' in blocked['checks']['documented_processing']['undocumented_fields']


def test_v3_rejects_response_dependent_binding_rule(tmp_path: Path, monkeypatch) -> None:
    import hashlib,json,pytest
    from tools.a_dav import matrix_v3
    soft=b'^SAMPLE = invented-sample\n!Sample_geo_accession = invented-sample\n!Sample_title = invented-patient\n!Sample_characteristics_ch1 = visit: pre\n!Sample_characteristics_ch1 = label: invented\n'
    raw=b'gene,invented-patient-x\n101,1\n'; gs=hashlib.sha256(soft).hexdigest();ms=hashlib.sha256(raw).hexdigest();o=tmp_path/'store'/'objects';o.mkdir(parents=True);(o/gs).write_bytes(soft);(o/ms).write_bytes(raw)
    mapping={'cohort':'invented','source_objects':{'geo_family_soft':{'sha256':gs},'expression':{'sha256':ms,'format':'MATRIX_HEADER_CSV','locator':'https://example.org/matrix','version':'1'}},
      'sample_identity':{'title_regex':'^(invented-patient)$','patient_group':1},'geo':{'characteristics':{'visit':'visit','response':'label'}},'geo_ingest':{'baseline_values':['pre']},
      'expression_column_map':{'expression':{'method':'REGEX','header_regex':r'^(?P<sample>invented-patient)-(?P<label>x)$','title_regex':r'^(?P<sample>invented-patient)$','characteristic_groups':{'label':{'characteristic':'label','values':{'x':'invented'}}}}},
      'measurement_representations':{'expression':{'unit':'UNKNOWN','transform':'UNKNOWN','platform':'UNKNOWN','genome_build':'UNKNOWN','feature_identifier_system':'UNKNOWN','annotation':'UNKNOWN'}},
      'v3':{'primary_representation':'expression','sample_inventory_source_role':'geo_family_soft','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'source_object_roles':{'primary':'expression'},'delimiters':{'expression':','},'compressed':{'expression':False},'documentation':{'expression':{'status':'DOCUMENTED'}}}}
    config=tmp_path/'map.json';config.write_text(json.dumps(mapping));monkeypatch.setattr(matrix_v3,'validate_output_path',lambda path:path)
    with pytest.raises(SystemExit) as exc:
        main(['--store',str(tmp_path/'store'),'--field-map',str(config),'--out',str(tmp_path/'out')])
    assert exc.value.code == 2
    assert not (tmp_path/'out'/'receipt.json').exists()


def test_v3_applies_declared_row_exclusions_before_identity_check(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'matrix.tsv.gz', 'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\n101\t1\t2\t3\nBAD_NAME\t2\t3\t4\n102\t3\t4\t5\n')
    args = _arguments()
    args['excluded_feature_rows'] = [{'row': 2, 'identifier': 'BAD_NAME', 'reason': 'NONSTANDARD_IDENTIFIER'}]
    result = validate_v3_matrix(matrix, **args)
    assert result['status'] == 'PASS'
    assert result['counts']['excluded_feature_rows'] == 1


def test_v3_blocks_when_missing_and_nonstandard_exclusions_leave_no_features(tmp_path: Path) -> None:
    matrix = _matrix(tmp_path / 'matrix.tsv.gz', 'GeneID\tinvented_pre_1\tinvented_pre_2\tinvented_on_1\nBAD_NAME\t1\t2\t3\n101\t\t3\t4\n')
    args = _arguments()
    args['excluded_feature_rows'] = [{'row': 1, 'identifier': 'BAD_NAME', 'reason': 'NONSTANDARD_IDENTIFIER'}]
    args['missing_policy'] = 'EXCLUDE_FEATURE_IF_ANY_MISSING'
    result = validate_v3_matrix(matrix, **args)
    assert result['status'] == 'BLOCKED'
    assert 'NO_FEATURES_REMAIN_AFTER_MISSING_EXCLUSION' in result['reasons']
