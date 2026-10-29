import pytest

from tools.a_dav.object_evidence import derive_object_evidence


@pytest.mark.parametrize(('features', 'expected'), [
    (['ENSG00000000001', 'ENSG00000000002.1'], 'ENSEMBL_GENE'),
    (['101', '202'], 'ENTREZ_GENE'),
    (['STAT1', 'HLA-A'], 'GENE_SYMBOL'),
    (['101', 'STAT1'], 'GENE_SYMBOL'),
    (['STAT1', 'GENE_2'], None),
])
def test_feature_identity_requires_homogeneous_unambiguous_format(features, expected):
    rows = [(feature, ['1', '2']) for feature in features]
    result = derive_object_evidence(rows, source_sha256='a' * 64)
    assert result['feature_identifier_system']['value'] == expected
    if expected:
        assert result['feature_identifier_system']['evidence_type'] == 'DERIVED_FROM_OBJECT'
        assert result['feature_identifier_system']['rule']
    else:
        assert result['feature_identifier_system']['status'] == 'BLOCKED'


def test_rsem_fractional_values_require_source_naming_rsem():
    rows = [('GENEA', ['1.25', '2.0'])]
    declared = derive_object_evidence(rows, source_sha256='a' * 64, rsem_source='geo_family_soft:!Sample_data_processing')
    assert declared['unit']['value'] == 'RSEM expected counts'
    assert declared['transform']['value'] == 'NONE'
    assert declared['unit']['evidence_type'] == declared['transform']['evidence_type'] == 'DERIVED_FROM_OBJECT'
    unspecified = derive_object_evidence(rows, source_sha256='a' * 64)
    assert unspecified['unit']['status'] == unspecified['transform']['status'] == 'BLOCKED'


def test_counts_and_missing_values_are_recorded_without_filling():
    result = derive_object_evidence([('GENEA', ['1', '']), ('GENEB', ['0', '3'])], source_sha256='a' * 64)
    assert result['unit']['value'] == 'READ_COUNTS'
    assert result['transform']['value'] == 'NONE'
    assert result['missing_cells'] == 1
    assert result['genes_with_missing_cells'] == 1
    assert result['unit']['rule'] == 'ALL_RETAINED_VALUES_WHOLE_NONNEGATIVE'


def test_filename_and_paper_rule_does_not_invent_a_transform():
    result = derive_object_evidence([('GENEA', ['0.5', '1.2'])], source_sha256='a' * 64,
        filename_unit='FPKM', filename_locator='https://example.org/expression-FPKM.xlsx',
        paper_noncontradiction='https://example.org/paper')
    assert result['unit']['value'] == 'FPKM'
    assert result['unit']['rule'] == 'FILENAME_PLUS_NONCONTRADICTING_PAPER'
    assert result['unit']['evidence_type'] == 'DERIVED_FROM_OBJECT'
    assert result['transform']['status'] == 'BLOCKED'


def test_conflicting_unit_rules_leave_unit_unresolved():
    result = derive_object_evidence([('GENEA', ['1', '2'])], source_sha256='a' * 64,
        filename_unit='FPKM', filename_locator='https://example.org/expression-FPKM.xlsx',
        paper_noncontradiction='https://example.org/paper')
    assert result['unit']['status'] == 'BLOCKED'
    assert result['transform']['status'] == 'BLOCKED'


def test_object_file_evidence_is_hash_bound_and_ignores_only_declared_auxiliary_columns(tmp_path):
    import hashlib
    from tools.a_dav.object_evidence import derive_file_evidence
    raw = b'gene,sample,,gene\nGENEA,1,,annotation\nGENEB,, ,annotation\n'
    source = tmp_path / 'matrix.csv'; source.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    result = derive_file_evidence(source, source_sha256=sha, source_format='MATRIX_HEADER_CSV', delimiter=',', compressed=False,
        auxiliary_columns=[{'index': 2, 'header': ''}, {'index': 3, 'header': 'gene'}])
    assert result['missing_cells'] == 1 and result['genes_with_missing_cells'] == 1
    assert result['counts_evidence']['rule'] == 'COUNT_SOURCE_MISSING_CELLS_AND_FEATURES'
    assert result['counts_evidence']['evidence_type'] == 'DERIVED_FROM_OBJECT'
    with pytest.raises(ValueError, match='SOURCE_HASH_MISMATCH'):
        derive_file_evidence(source, source_sha256='a' * 64, source_format='MATRIX_HEADER_CSV', delimiter=',', compressed=False)


def test_filename_unit_blocks_if_numeric_content_conflicts():
    result = derive_object_evidence([('GENEA', ['-1.5'])], source_sha256='a' * 64,
        filename_unit='FPKM', filename_locator='https://example.org/expression-FPKM.xlsx',
        paper_noncontradiction='https://example.org/paper')
    assert result['unit']['status'] == 'BLOCKED'
    assert result['transform']['status'] == 'BLOCKED'


def test_majority_symbol_rule_records_each_excluded_row_without_remapping():
    rows = [(f'GENE{i}', ['1']) for i in range(198)] + [('BAD_NAME', ['1']), ('SEP15', ['1'])]
    result = derive_object_evidence(rows, source_sha256='a' * 64)
    assert result['feature_identifier_system']['rule'] == 'GENE_SYMBOL_MAJORITY'
    assert result['feature_identifier_system']['evidence_type'] == 'DERIVED_FROM_OBJECT'
    assert result['gene_symbol_share'] == 199 / 200
    assert result['excluded_rows'] == [
        {'row': 199, 'identifier': 'BAD_NAME', 'reason': 'NONSTANDARD_IDENTIFIER'},
        {'row': 200, 'identifier': 'SEP15', 'reason': 'DATE_MANGLED_APPEARANCE'}]
    assert result['excluded_rows_evidence']['rule'] == 'NONSTANDARD_ROWS_EXCLUDED'


def test_below_threshold_and_duplicate_rows_are_not_guessed():
    rows = [(f'GENE{i}', ['1']) for i in range(98)] + [('BAD_1', ['1']), ('BAD_2', ['1'])]
    assert derive_object_evidence(rows, source_sha256='a' * 64)['feature_identifier_system']['status'] == 'BLOCKED'
    duplicates = [(f'GENE{i}', ['1']) for i in range(100)] + [('GENE1', ['2'])]
    result = derive_object_evidence(duplicates, source_sha256='a' * 64)
    assert [row['row'] for row in result['excluded_rows']] == [2, 101]
    assert {row['reason'] for row in result['excluded_rows']} == {'DUPLICATE_SYMBOL'}


@pytest.mark.parametrize(('values', 'expected'), [(['0', '50'], False), (['0', '50.01'], True), (['-1', '51'], False)])
def test_fpkm_range_requires_max_above_50_and_all_values_nonnegative(values, expected):
    result = derive_object_evidence([('GENEA', values)], source_sha256='a' * 64,
        filename_unit='FPKM', filename_locator='https://example.org/expression-FPKM.xlsx',
        paper_noncontradiction='https://example.org/paper')
    assert (result['transform']['value'] == 'NONE') is expected
    if expected:
        assert result['transform']['rule'] == 'LINEAR_FPKM_BY_RANGE'
        assert result['transform']['evidence_type'] == 'DERIVED_FROM_OBJECT'


def test_clean_symbol_rows_record_the_approved_majority_rule():
    result = derive_object_evidence([('GENEA', ['1']), ('GENEB', ['2'])], source_sha256='a' * 64)
    assert result['feature_identifier_system']['rule'] == 'GENE_SYMBOL_MAJORITY'


def test_fpkm_range_rule_is_independent_of_conflicting_unit_inference():
    result = derive_object_evidence([('GENEA', ['0', '51'])], source_sha256='a' * 64,
        filename_unit='FPKM', filename_locator='https://example.org/expression-FPKM.xlsx',
        paper_noncontradiction='https://example.org/paper')
    assert result['unit']['status'] == 'BLOCKED'
    assert result['transform']['rule'] == 'LINEAR_FPKM_BY_RANGE'


def test_symbol_share_has_rule_and_object_provenance():
    result = derive_object_evidence([('GENEA', ['1'])], source_sha256='a' * 64)
    assert result['gene_symbol_share_evidence']['evidence_type'] == 'DERIVED_FROM_OBJECT'
    assert result['gene_symbol_share_evidence']['rule'] == 'GENE_SYMBOL_MAJORITY'
    assert result['gene_symbol_share_evidence']['source_sha256'] == 'a' * 64
