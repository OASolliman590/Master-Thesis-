import math
from types import SimpleNamespace

import pytest

from tools.a_scoring import (
    cyt, endpoint_label, log2p1, panel_scores, recount3_to_tpm, resolve, to_tpm,
)


def test_fpkm_to_tpm_uses_complete_feature_universe_per_sample():
    result = to_tpm(
        [[1, 1], [2, 3], [7, 6]],
        {'platform': 'rnaseq', 'unit': 'fpkm', 'transform': 'linear'},
    )
    assert result == [[100000, 100000], [200000, 300000], [700000, 600000]]
    assert [sum(row[column] for row in result) for column in range(2)] == [1e6, 1e6]


def test_counts_to_tpm_uses_lengths():
    result = to_tpm(
        [[10], [10], [20]],
        {'platform': 'rnaseq', 'unit': 'counts', 'transform': 'linear'},
        [1000, 2000, 1000],
    )
    assert [row[0] for row in result] == pytest.approx([2e6 / 7, 1e6 / 7, 4e6 / 7])


def test_recount3_maps_ensembl_filters_primary_and_uses_gtf_score_lengths(tmp_path):
    import gzip

    gtf = tmp_path / 'genes.gz'
    with gzip.open(gtf, 'wt') as stream:
        stream.write('chr1\tsrc\tgene\t1\t100\t10\t+\t.\tgene_id "g1"; gene_name "A";\n')
        stream.write('chrX\tsrc\tgene\t1\t80\t20\t+\t.\tgene_id "g2"; gene_name "B";\n')
        stream.write('chr1_alt\tsrc\tgene\t1\t90\t30\t+\t.\tgene_id "g3"; gene_name "ALT";\n')

    symbols, tpm, dropped = recount3_to_tpm(
        ['g1', 'g2', 'g3'], [[10], [20], [10000]], gtf,
    )
    assert symbols == ['A', 'B']
    assert [row[0] for row in tpm] == [500000, 500000]
    assert dropped == 1


def test_recount3_rejects_invalid_primary_bp_length(tmp_path):
    import gzip

    gtf = tmp_path / 'genes.gz'
    with gzip.open(gtf, 'wt') as stream:
        stream.write('chr1\tsrc\tgene\t1\t100\t.\t+\t.\tgene_id "g1"; gene_name "A";\n')
    with pytest.raises(ValueError, match='length'):
        recount3_to_tpm(['g1'], [[1]], gtf)


def test_recount3_requires_every_count_row_in_annotation(tmp_path):
    import gzip

    gtf = tmp_path / 'genes.gz'
    with gzip.open(gtf, 'wt') as stream:
        stream.write('chr1\tsrc\tgene\t1\t100\t10\t+\t.\tgene_id "g1"; gene_name "A";\n')
    with pytest.raises(ValueError, match='missing from recount3 annotation'):
        recount3_to_tpm(['missing'], [[1]], gtf)


def test_linear_tpm_is_retained_and_log2p1_is_applied():
    values = [[0, 3], [15, 7]]
    assert to_tpm(values, {'platform': 'rnaseq', 'unit': 'tpm', 'transform': 'linear'}) == values
    assert log2p1(values) == [[0, 2], [4, 3]]


@pytest.mark.parametrize(
    ('representation', 'message'),
    [
        ({'platform': 'rnaseq', 'unit': 'fpkm', 'transform': 'log2'}, 'linear'),
        ({'platform': 'microarray', 'unit': 'probe_intensity', 'transform': 'log2'}, 'microarray'),
        ({'platform': 'nanostring', 'unit': 'normalised_counts', 'transform': 'log2'}, 'nanostring'),
        ({'platform': 'targeted_rna', 'unit': 'tpm', 'transform': 'linear'}, 'targeted_rna'),
        ({'platform': 'rnaseq', 'unit': 'tpm', 'transform': 'log2'}, 'linear'),
        ({'platform': 'rnaseq', 'unit': 'tpm', 'transform': 'other'}, 'transform'),
    ],
)
def test_non_tpm_compatible_representations_are_refused(representation, message):
    with pytest.raises(ValueError, match=message):
        to_tpm([[1]], representation)


def test_counts_require_valid_lengths_and_nonzero_denominators():
    representation = {'platform': 'rnaseq', 'unit': 'counts', 'transform': 'linear'}
    with pytest.raises(ValueError, match='gene length'):
        to_tpm([[1]], representation)
    with pytest.raises(ValueError, match='length'):
        to_tpm([[1]], representation, [math.nan])
    with pytest.raises(ValueError, match='denominator'):
        to_tpm([[0]], {'platform': 'rnaseq', 'unit': 'fpkm', 'transform': 'linear'})


def test_log2p1_can_convert_from_representation_first():
    result = log2p1(
        [[1], [3]],
        {'platform': 'rnaseq', 'unit': 'fpkm', 'transform': 'linear'},
    )
    assert [row[0] for row in result] == pytest.approx([math.log2(250001), math.log2(750001)])


def test_frozen_aliases_resolve_and_report_target_coverage():
    mapping, coverage = resolve(
        ['MB21D1', 'TMEM173', 'RIGI'],
        {'CGAS', 'STING1', 'DDX58'},
        synonyms={},
        gene_symbols={},
    )
    assert mapping == {'CGAS': 0, 'STING1': 1, 'DDX58': 2}
    assert {gene: coverage[gene]['resolution'] for gene in mapping} == {
        'CGAS': 'alias', 'STING1': 'alias', 'DDX58': 'alias',
    }
    assert all(coverage[gene]['present'] for gene in mapping)


def test_ncbi_synonym_is_used_only_when_unique():
    mapping, coverage = resolve(
        ['SYN'], {'B'}, aliases={}, synonyms={'B': {'SYN'}}, gene_symbols={},
    )
    assert mapping == {'B': 0}
    assert coverage['B']['resolution'] == 'synonym'

    missing, ambiguous = resolve(
        ['SYN', 'SYN'], {'B'}, aliases={}, synonyms={'B': {'SYN'}}, gene_symbols={},
    )
    assert missing == {}
    assert ambiguous['B']['resolution'] == 'ambiguous'
    assert ambiguous['B']['candidate_count'] == 2


def test_one_synonym_row_cannot_complete_two_gene_panel():
    mapping, coverage = resolve(
        ['SHARED'], {'A', 'B'}, aliases={},
        synonyms={'A': {'SHARED'}, 'B': {'SHARED'}}, gene_symbols={},
    )
    scores, panel_coverage = panel_scores(
        {target: 1.0 for target in mapping}, panels={'panel': ['A', 'B']},
    )
    assert mapping == {}
    assert coverage['A']['resolution'] == coverage['B']['resolution'] == 'ambiguous'
    assert scores['panel'] is None
    assert panel_coverage['panel']['complete'] is False


def test_synonym_row_is_ambiguous_even_when_other_target_has_a_direct_row():
    mapping, coverage = resolve(
        ['SHARED', 'B'], {'A', 'B'}, aliases={},
        synonyms={'A': {'SHARED'}, 'B': {'SHARED'}}, gene_symbols={},
    )
    assert mapping == {'B': 1}
    assert coverage['A']['resolution'] == 'ambiguous'
    assert coverage['B']['resolution'] == 'exact'


def test_duplicate_rows_for_required_gene_are_rejected():
    with pytest.raises(ValueError, match='duplicate'):
        resolve(['A', 'OLD'], {'A'}, aliases={'OLD': 'A'}, synonyms={}, gene_symbols={})


def test_incomplete_panel_is_na_with_coverage_record():
    scores, coverage = panel_scores(
        {'A': 1.0}, panels={'panel': ['A', 'B']}, require_complete=True,
    )
    assert scores == {'panel': None}
    assert coverage['panel'] == {
        'found': ('A',), 'missing': ('B',), 'n_found': 1,
        'n_total': 2, 'complete': False,
    }


def test_panel_mean_uses_supplied_scale_and_can_report_partial_score():
    scores, coverage = panel_scores(
        {'A': 0.0, 'B': 2.0}, panels={'panel': ['A', 'B']},
    )
    assert scores == {'panel': 1.0}
    assert coverage['panel']['complete'] is True

    partial, _ = panel_scores(
        {'A': 2.0}, panels={'panel': ['A', 'B']}, require_complete=False,
    )
    assert partial == {'panel': 2.0}


def test_cyt_is_unoffset_geometric_mean():
    assert cyt(4, 9) == 6
    assert cyt(0, 9) == 0


def test_orr_ne_and_unknown_are_excluded_not_nonresponse():
    rows = [{'orr': value} for value in ['CR', 'PR', 'SD', 'PD', 'NE', 'UNKNOWN', '']]
    labels, excluded = endpoint_label(rows, 'orr')
    assert labels == [1, 1, 0, 0, None, None, None]
    assert excluded == {'not_evaluable': 1, 'unknown': 2}


def test_clinical_benefit_family_uses_loader_binary_and_counts_unknown():
    labels, excluded = endpoint_label(
        [{'clinical_benefit': 'R'}, {'clinical_benefit': 'NR'}, {'clinical_benefit': 'UNKNOWN'}],
        'clinical_benefit',
    )
    assert labels == [1, 0, None]
    assert excluded == {'unknown': 1}


def test_source_label_uses_loader_recorded_source_fields_and_accepts_cohort_view():
    view = SimpleNamespace(metadata=SimpleNamespace(cohort_id=None), clinical_rows=[
        {'treatment_outcome': 'Responder'},
        {'treatment_outcome': 'Non-responder'},
        {'treatment_outcome': ''},
    ])
    labels, excluded = endpoint_label(view, 'source_label')
    assert labels == [1, 0, None]
    assert excluded == {'unknown': 1}


def _loader_view(cohort_id, rows):
    return SimpleNamespace(metadata=SimpleNamespace(cohort_id=cohort_id), clinical_rows=rows)


def test_gse67501_recist_loader_categories_and_binary_mapping():
    rows = [
        {'orr': 'R', 'raw_orr': 'CR', 'endpoint_definition': 'ORR: CR/PR versus SD/NR; original category retained.'},
        {'orr': 'R', 'raw_orr': 'PR', 'endpoint_definition': 'ORR: CR/PR versus SD/NR; original category retained.'},
        {'orr': 'NR', 'raw_orr': 'SD', 'endpoint_definition': 'ORR: CR/PR versus SD/NR; original category retained.'},
        {'orr': 'NR', 'raw_orr': 'NR', 'endpoint_definition': 'ORR: CR/PR versus SD/NR; original category retained.'},
        {'orr': 'UNKNOWN', 'raw_orr': 'NE', 'endpoint_definition': 'ORR: CR/PR versus SD/NR; original category retained.'},
        {'orr': 'UNKNOWN', 'raw_orr': 'UNKNOWN', 'endpoint_definition': 'ORR: CR/PR versus SD/NR; original category retained.'},
    ]
    labels, excluded = endpoint_label(_loader_view('gse67501', rows), 'orr')
    assert labels == [1, 1, 0, 0, None, None]
    assert excluded == {'not_evaluable': 1, 'unknown': 1}


@pytest.mark.parametrize('cohort_id', ['gse135222', 'gse136961'])
def test_dcb_ndb_loader_categories_are_clinical_benefit(cohort_id):
    definition = 'UNKNOWN'
    rows = [
        {'clinical_benefit': 'DCB', 'raw_clinical_benefit': 'DCB', 'endpoint_definition': definition},
        {'clinical_benefit': 'NDB', 'raw_clinical_benefit': 'NDB', 'endpoint_definition': definition},
        {'clinical_benefit': 'UNKNOWN', 'raw_clinical_benefit': 'UNKNOWN', 'endpoint_definition': definition},
    ]
    labels, excluded = endpoint_label(_loader_view(cohort_id, rows), 'clinical_benefit')
    assert labels == [1, 0, None]
    assert excluded == {'unknown': 1}


def test_braun_intermediate_clinical_benefit_is_excluded():
    rows = [
        {'clinical_benefit': 'CB', 'endpoint_definition': 'clinical benefit categories CB/ICB/NCB'},
        {'clinical_benefit': 'ICB', 'endpoint_definition': 'clinical benefit categories CB/ICB/NCB'},
        {'clinical_benefit': 'NCB', 'endpoint_definition': 'clinical benefit categories CB/ICB/NCB'},
        {'clinical_benefit': 'UNKNOWN', 'endpoint_definition': 'clinical benefit categories CB/ICB/NCB'},
    ]
    labels, excluded = endpoint_label(_loader_view('braun2020', rows), 'clinical_benefit')
    assert labels == [1, None, 0, None]
    assert excluded == {'intermediate_benefit': 1, 'unknown': 1}


@pytest.mark.parametrize(
    ('cohort_id', 'row', 'expected'),
    [
        ('gse218989', {'treatment_outcome': 'Responder', 'endpoint_definition': 'SOURCE_BINARY; no RECIST CR/PR evidence.'}, 1),
        ('gse111636', {'treatment_outcome': 'Progressor', 'endpoint_definition': 'SOURCE_BINARY; responder/progressor labels, not RECIST.'}, 0),
        ('gse168204', {'raw_clinical_benefit': 'NR', 'endpoint_definition': 'source category; see admitted records'}, 0),
    ],
)
def test_source_binary_loader_categories_remain_source_labels(cohort_id, row, expected):
    labels, excluded = endpoint_label(_loader_view(cohort_id, [row]), 'source_label')
    assert labels == [expected]
    assert excluded == {}


def test_source_binary_r_nr_is_not_promoted_to_orr():
    view = _loader_view('gse111636', [
        {'orr': 'R', 'raw_orr': '', 'treatment_outcome': 'Responder',
         'endpoint_definition': 'SOURCE_BINARY; SOFT does not define RECIST.'},
    ])
    labels, excluded = endpoint_label(view, 'orr')
    assert labels == [None]
    assert excluded == {'family_mismatch': 1}


def test_recist_definition_allows_loader_r_nr_orr_categories():
    view = _loader_view('gse67501', [
        {'orr': 'R', 'raw_orr': 'UNKNOWN', 'endpoint_definition': 'ORR: CR/PR versus SD/NR.'},
        {'orr': 'NR', 'raw_orr': 'UNKNOWN', 'endpoint_definition': 'ORR: CR/PR versus SD/NR.'},
    ])
    labels, excluded = endpoint_label(view, 'orr')
    assert labels == [1, 0]
    assert excluded == {}


def test_unknown_endpoint_family_is_rejected():
    with pytest.raises(ValueError, match='Unknown endpoint family'):
        endpoint_label([], 'pfs')
