"""Invented-ID tests for evidence-bounded assay-policy derivation."""
from __future__ import annotations

import pytest

from tools.a_dav.assay_policy import (AssayPolicyEvidenceError, derive_assay_policy_metadata,
                                     materialize_primary_assay_policy)


def invented_evidence(*, fallback_transform: str = "NONE", platform: str | None = "invented-platform"):
    field_map = {
        "v3": {"source_object_roles": {"primary": "invented_tpm", "fallback": "invented_fpkm"},
               "delimiters": {"invented_fpkm": ","}, "compressed": {"invented_fpkm": False}},
        "measurement_representations": {
            "invented_tpm": {"unit": "TPM", "transform": "NCBI_PROVIDED", "genome_build": "invented-build",
                              "annotation": "invented-ids", "modality": "RNA_SEQ", "platform": platform},
            "invented_fpkm": {"unit": "FPKM", "transform": fallback_transform, "genome_build": "invented-old-build",
                               "annotation": "invented-old-ids", "modality": "RNA_SEQ", "platform": platform,
                               "normalization": "invented normalized FPKM", "feature_scope": "COMPLETE"},
        },
        "source_objects": {
            "invented_tpm": {"sha256": "a" * 64, "format": "MATRIX_HEADER_TSV"},
            "invented_fpkm": {"sha256": "b" * 64, "format": "MATRIX_HEADER_CSV"},
        },
    }
    receipt = {
        "checks_version": "V3",
        "source_sha256": {"primary": "a" * 64, "fallback": "b" * 64},
        "checks": {
            "effective_primary": "invented_fpkm", "effective_sensitivity": "invented_tpm",
            "primary": {"representation": "invented_tpm", "status": "BLOCKED",
                        "checks": {"feature_identity": {"status": "PASS", "certification_level": "PINNED"}}},
            "fallback": {"representation": "invented_fpkm", "status": "PASS",
                         "checks": {"feature_identity": {"status": "PASS", "certification_level": "FORMAT_ONLY"}}},
        },
    }
    assays = [{"source_role": role, "modality": "RNA_SEQ", "platform": platform or ""}
              for role in ("invented_tpm", "invented_fpkm")]
    return field_map, receipt, assays


def test_materialize_policy_reads_only_effective_primary_by_pinned_hash(tmp_path):
    import hashlib

    field_map, receipt, _ = invented_evidence()
    field_map['proposal_generation'] = {'stage_config': {'materialization': {'assay_suitability': 'BASELINE_DE'}}}
    object_bytes = b"GeneID,invented_pre_1,invented_pre_2\n101,1.5,2.5\n102,0,3\n"
    source_hash = hashlib.sha256(object_bytes).hexdigest()
    field_map["source_objects"]["invented_fpkm"]["sha256"] = source_hash
    receipt["source_sha256"]["fallback"] = source_hash
    store_root = tmp_path / "store"
    (store_root / "objects").mkdir(parents=True)
    (store_root / "objects" / source_hash).write_bytes(object_bytes)
    packet = {"records": {
        "source_record": [{"source_object_id": "source-invented-fpkm", "sha256": source_hash,
                           "hash_scope": "FULL_OBJECT", "object_url": "sha256:" + source_hash,
                           "modality": "RNA_SEQ"}],
        "assay_registry": [
            {"assay_uid": "assay-invented-1", "specimen_uid": "specimen-invented-1",
             "source_sample_id": "invented_pre_1", "matrix_header": "invented_pre_1",
             "source_object_id": "source-invented-fpkm"},
            {"assay_uid": "assay-invented-2", "specimen_uid": "specimen-invented-2",
             "source_sample_id": "invented_pre_2", "matrix_header": "invented_pre_2",
             "source_object_id": "source-invented-fpkm"},
        ],
        "specimen_registry": [],
    }, "config": {}}

    result = materialize_primary_assay_policy(packet, field_map, receipt, store_root)

    assert result["config"]["assays"]["matrices"][0]["headers"] == ["invented_pre_1", "invented_pre_2"]
    assert result["config"]["assays"]["matrices"][0]["features"] == ["101", "102"]
    assert result["config"]["assays"]["matrices"][0]["values"] == [[1.5, 2.5], [0.0, 3.0]]
    assert len(result["config"]["assays"]["matrices"]) == 1
    assert result["records"]["assay_registry"][0]["platform"] == "invented-platform"
    assert result["records"]["assay_registry"][0]["branch_suitability"] == ['BASELINE_DE']


def test_policy_metadata_uses_effective_primary_and_leaves_blocked_sensitivity_out():
    field_map, receipt, assays = invented_evidence()
    result = derive_assay_policy_metadata(field_map, receipt, assays)

    assert result["effective_primary"] == "invented_fpkm"
    assert result["effective_sensitivity"] == "invented_tpm"
    assert result["representations"] == {"invented_fpkm": {
        "source_sha256": "b" * 64, "unit": "FPKM", "transform": "NONE",
        "genome_build": "invented-old-build", "annotation": "invented-old-ids",
        "feature_identity_certification": "FORMAT_ONLY", "modality": "RNA_SEQ",
        "platform": "invented-platform",
    }}


def test_policy_generation_blocks_on_transform_label_without_supported_transform_semantics():
    field_map, receipt, assays = invented_evidence(fallback_transform="AUTHOR_REPORTED")

    with pytest.raises(AssayPolicyEvidenceError, match="ASSAY_POLICY_EVIDENCE_MISSING:transform:invented_fpkm"):
        derive_assay_policy_metadata(field_map, receipt, assays)


def test_policy_generation_blocks_when_platform_evidence_is_empty():
    field_map, receipt, assays = invented_evidence(platform=None)

    with pytest.raises(AssayPolicyEvidenceError, match="ASSAY_POLICY_EVIDENCE_MISSING:platform:invented_fpkm"):
        derive_assay_policy_metadata(field_map, receipt, assays)


def test_policy_reads_sample_rows_using_declared_orientation(tmp_path):
    import hashlib
    field_map, receipt, _ = invented_evidence()
    field_map['measurement_representations']['invented_fpkm']['orientation'] = 'samples_as_rows'
    data = b'GeneID,101,102\ninvented_pre_1,1.5,0\ninvented_pre_2,2.5,3\n'
    sha = hashlib.sha256(data).hexdigest()
    field_map['source_objects']['invented_fpkm']['sha256'] = sha
    receipt['source_sha256']['fallback'] = sha
    (tmp_path / 'objects').mkdir()
    (tmp_path / 'objects' / sha).write_bytes(data)
    packet = {'records': {'source_record': [{'source_object_id': 'invented-source', 'sha256': sha, 'hash_scope': 'FULL_OBJECT', 'object_url': 'sha256:' + sha, 'modality': 'RNA_SEQ'}],
        'assay_registry': [{'assay_uid': 'assay-1', 'specimen_uid': 'specimen-1', 'source_sample_id': 'invented_pre_1', 'matrix_header': 'invented_pre_1', 'source_object_id': 'invented-source'},
                           {'assay_uid': 'assay-2', 'specimen_uid': 'specimen-2', 'source_sample_id': 'invented_pre_2', 'matrix_header': 'invented_pre_2', 'source_object_id': 'invented-source'}],
        'specimen_registry': []}, 'config': {}}
    result = materialize_primary_assay_policy(packet, field_map, receipt, tmp_path)
    assert result['config']['assays']['matrices'][0]['values'] == [[1.5, 2.5], [0.0, 3.0]]


def test_policy_accepts_a_single_pinned_primary_representation():
    field_map, receipt, assays = invented_evidence()
    field_map['v3']['source_object_roles'] = {'primary': 'invented_fpkm'}
    receipt['source_sha256'] = {'primary': 'b' * 64}
    receipt['checks'] = {'effective_primary': 'invented_fpkm', 'effective_sensitivity': None,
        'primary': {'representation': 'invented_fpkm', 'status': 'PASS',
                    'checks': {'feature_identity': {'status': 'PASS', 'certification_level': 'FORMAT_ONLY'}}}, 'fallback': None}
    result = derive_assay_policy_metadata(field_map, receipt, assays)
    assert result['effective_primary'] == 'invented_fpkm'
    assert result['effective_sensitivity'] is None


def test_policy_reads_xlsx_primary_from_pinned_bytes(tmp_path):
    import hashlib
    import io
    import zipfile
    field_map, receipt, _ = invented_evidence()
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>gene</t></si><si><t>invented_pre_1</t></si><si><t>101</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>1.5</v></c></row></sheetData></worksheet>')
    raw=data.getvalue(); sha=hashlib.sha256(raw).hexdigest()
    field_map['source_objects']['invented_fpkm'].update(sha256=sha,format='XLSX_NUMERIC')
    receipt['source_sha256']['fallback']=sha
    (tmp_path / 'objects').mkdir(); (tmp_path / 'objects' / sha).write_bytes(raw)
    packet={'records': {'source_record':[{'source_object_id':'invented-source','sha256':sha,'hash_scope':'FULL_OBJECT','object_url':'sha256:'+sha,'modality':'RNA_SEQ'}],
      'assay_registry':[{'assay_uid':'assay-1','specimen_uid':'specimen-1','source_sample_id':'invented_pre_1','matrix_header':'invented_pre_1','source_object_id':'invented-source'}], 'specimen_registry':[]},'config':{}}
    result=materialize_primary_assay_policy(packet, field_map, receipt, tmp_path)
    assert result['config']['assays']['matrices'][0]['values'] == [[1.5]]


def test_provisional_policy_preserves_unknown_metadata_and_excludes_rejected_rows(tmp_path):
    import hashlib
    field_map, receipt, _ = invented_evidence()
    rep = field_map['measurement_representations']['invented_fpkm']
    rep.pop('normalization'); rep.pop('feature_scope')
    raw = b'GeneID,invented_pre_1\nGENEA,1\nBAD_NAME,2\nGENEB,3\n'
    sha = hashlib.sha256(raw).hexdigest()
    field_map['source_objects']['invented_fpkm']['sha256'] = sha
    receipt['source_sha256']['fallback'] = sha
    receipt['checks']['fallback']['object_derived_evidence'] = {'excluded_rows': [{'row': 2, 'identifier': 'BAD_NAME', 'reason': 'NONSTANDARD_IDENTIFIER'}]}
    (tmp_path / 'objects').mkdir(); (tmp_path / 'objects' / sha).write_bytes(raw)
    packet = {'records': {'source_record': [{'source_object_id':'invented-source','sha256':sha}],
      'assay_registry':[{'assay_uid':'invented-assay','specimen_uid':'invented-specimen','matrix_header':'invented_pre_1','source_object_id':'invented-source'}]}, 'config':{}}
    result = materialize_primary_assay_policy(packet, field_map, receipt, tmp_path, provisional=True)
    matrix = result['config']['assays']['matrices'][0]
    assert matrix['features'] == ['GENEA', 'GENEB']
    assert matrix['normalization'] == matrix['feature_scope'] == 'UNKNOWN'


@pytest.mark.parametrize(('source_unit','expected_unit','values'), [('READ_COUNTS','counts', ('2','3')), ('RSEM expected counts','estimated_counts', ('2.5','3.25'))])
def test_count_policy_preserves_values_and_derives_library_size_from_retained_rows(tmp_path, source_unit, expected_unit, values):
    import hashlib
    fmap, receipt, _ = invented_evidence()
    rep = fmap['measurement_representations']['invented_fpkm']
    rep.update(unit=source_unit, normalization='NONE', missing_policy='EXCLUDE_FEATURE_IF_ANY_MISSING')
    raw = ('gene,invented_pre_1,invented_pre_2\nGENEA,'+values[0]+',4\nBAD_NAME,100,100\nGENEB,'+values[1]+',\nGENEC,1,1\n').encode()
    sha=hashlib.sha256(raw).hexdigest(); fmap['source_objects']['invented_fpkm']['sha256']=sha; receipt['source_sha256']['fallback']=sha
    receipt['checks']['fallback']['object_derived_evidence']={'excluded_rows':[{'row':2,'identifier':'BAD_NAME','reason':'NONSTANDARD_IDENTIFIER'}]}
    (tmp_path/'objects').mkdir(); (tmp_path/'objects'/sha).write_bytes(raw)
    packet={'records':{'source_record':[{'source_object_id':'source','sha256':sha}], 'assay_registry':[{'assay_uid':'assay','specimen_uid':'specimen','matrix_header':'invented_pre_1','source_object_id':'source'}]},'config':{}}
    result=materialize_primary_assay_policy(packet,fmap,receipt,tmp_path)
    matrix=result['config']['assays']['matrices'][0]
    assert matrix['lane']=='COUNTS' and matrix['unit']==expected_unit
    assert matrix['features']==['GENEA','GENEC'] and matrix['values']==[[float(values[0])],[1.0]]
    assert matrix['library_properties']['invented_pre_1']=={'library_size':float(values[0])+1.0,'source_locator':'sha256:'+sha,'evidence_type':'DERIVED_FROM_OBJECT','rule':'COLUMN_SUM_LIBRARY_SIZE'}
    if expected_unit=='estimated_counts':
        assert matrix['quantifier']=='RSEM' and matrix['estimated_count_structure']
