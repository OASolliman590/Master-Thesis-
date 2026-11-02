import math
import pytest
from tools.a_p2.build import fpkm_to_tpm, counts_to_tpm, panel_mean, cyt, resolve_genes


def test_fpkm_to_tpm_uses_all_genes():
    assert fpkm_to_tpm([1, 2, 7]) == pytest.approx([100000, 200000, 700000])


def test_counts_to_tpm_uses_lengths():
    assert counts_to_tpm([10, 10, 20], [1000, 2000, 1000]) == pytest.approx([2e6/7, 1e6/7, 4e6/7])


def test_panel_and_cyt():
    assert panel_mean([0, 3]) == pytest.approx(1)
    assert cyt(4, 9) == 6
    assert cyt(0, 9) == 0


def test_alias_and_unique_synonym():
    found, added = resolve_genes(['OLD', 'SYN'], {'A', 'B'}, {'OLD': 'A'}, {'B': {'SYN'}})
    assert found == {'A': 0, 'B': 1}
    assert added == {'B': 'SYN'}


def test_duplicate_mapped_gene_stops():
    with pytest.raises(ValueError, match='duplicate'):
        resolve_genes(['A', 'OLD'], {'A'}, {'OLD': 'A'}, {})


def test_missing_gene_never_fills_in():
    found, _ = resolve_genes(['A'], {'A', 'B'}, {}, {})
    assert set(found) != {'A', 'B'}


def test_invalid_abundance():
    with pytest.raises(ValueError): fpkm_to_tpm([0, 0])
    with pytest.raises(ValueError): counts_to_tpm([1], [math.nan])


def test_exon_union_lengths_and_gene_symbols(tmp_path):
    from tools.a_p2.build import exon_annotation
    import gzip
    p = tmp_path / 'annotation.gz'
    with gzip.open(p, 'wt') as f:
        f.write('chr1\tsrc\tgene\t1\t100\t.\t+\t.\tgene_id "g1"; gene_name "A";\n')
        for start, end in [(10, 20), (15, 25), (30, 31), (10, 20)]:
            f.write(f'chr1\tsrc\texon\t{start}\t{end}\t.\t+\t.\tgene_id "g1"; gene_name "A";\n')
        f.write('chr2\tsrc\texon\t1\t3\t.\t-\t.\tgene_id "g2"; gene_name "B";\n')
    lengths, names = exon_annotation(p)
    assert lengths == {'g1': 18, 'g2': 3}
    assert names == {'g1': 'A', 'g2': 'B'}


def test_gene_only_gtf_is_rejected(tmp_path):
    from tools.a_p2.build import exon_annotation
    import gzip
    p = tmp_path / 'annotation.gz'
    with gzip.open(p, 'wt') as f:
        f.write('chr1\tsrc\tgene\t1\t10\t10\t+\t.\tgene_id "g"; gene_name "A";\n')
    with pytest.raises(ValueError, match='no exon rows'):
        exon_annotation(p)


def test_accepted_gide_identity_requires_exact_loader_match():
    from tools.a_p2.build import accepted_gide_pairs
    proposal = [{'run': 'r1', 'patient': 'p1'}, {'run': 'r2', 'patient': 'p2'}]
    patients = {'p1': 'uid1', 'p2': 'uid2'}
    assert accepted_gide_pairs(proposal, patients, {'r1': 'uid1', 'r2': 'uid2'}) == {'uid1': 'r1', 'uid2': 'r2'}
    assert accepted_gide_pairs(proposal, patients, {'r1': 'wrong', 'r2': 'uid2'}) == {'uid2': 'r2'}


def test_recount_annotation_uses_score_and_excludes_alternate_loci(tmp_path, monkeypatch):
    import gzip
    import tools.a_p2.build as prep
    gtf = tmp_path / 'genes.gz'
    with gzip.open(gtf, 'wt') as f:
        f.write('chr1\tsrc\tgene\t1\t100\t10\t+\t.\tgene_id "g1"; gene_name "A";\n')
        f.write('chrX\tsrc\tgene\t1\t80\t20\t+\t.\tgene_id "g2"; gene_name "B";\n')
        f.write('chr1_alt\tsrc\tgene\t1\t90\t30\t+\t.\tgene_id "g3"; gene_name "A";\n')
    matrix = tmp_path / 'counts.tsv'
    matrix.write_text('gene\tsample\ng1\t10\ng2\t20\ng3\t10000\n')
    monkeypatch.setattr(prep, 'safe_path', lambda p: p)
    annotation = prep.recount_annotation(gtf)
    symbols, values, totals, dropped = prep.matrix(matrix, ['sample'], None, annotation)
    assert symbols == ['A', 'B']
    assert values == [[1], [1]]
    assert totals == [2]
    assert dropped == 1
    assert [v[0] * 1e6 / totals[0] for v in values] == pytest.approx([500000, 500000])


def test_recount_annotation_rejects_invalid_primary_length(tmp_path):
    import gzip
    from tools.a_p2.build import recount_annotation
    gtf = tmp_path / 'genes.gz'
    with gzip.open(gtf, 'wt') as f:
        f.write('chr1\tsrc\tgene\t1\t100\t.\t+\t.\tgene_id "g1"; gene_name "A";\n')
    with pytest.raises(ValueError, match='length'):
        recount_annotation(gtf)
