from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_meta import features as a_features
from tools.a_scoring import core as scoring_core
from tools.freeze_audit import core as audit_core
from tools.freeze_audit.bridging import _comparison_stats, _signature_id
from tools.freeze_audit.coverage import COVERAGE_COLUMNS, make_coverage_rows
from tools.freeze_audit.identifiers import (
    _classify_gap,
    _date_mangled_sources,
    _is_date_mangled_member,
)


def _study(
    *,
    cohort="fixture",
    gene_values=None,
    feature_ids=(),
    source_symbols=(),
    canonical_symbols=(),
    gtf_symbols=None,
    targeted=False,
):
    return audit_core.StudyData(
        cohort_id=cohort,
        cancer="lung",
        platform="rnaseq",
        feature_id="ensembl",
        targeted=targeted,
        usable_baseline=False,
        gene_values=gene_values or {},
        source_feature_ids=tuple(feature_ids),
        source_symbols=tuple(source_symbols),
        canonical_source_symbols=tuple(canonical_symbols),
        source_values=tuple(),
        n_samples=3,
        expression_rows=len(tuple(feature_ids)),
        gtf_symbols=gtf_symbols or {},
        gene_history={},
    )


def test_frozen_alias_counts_hallmark_member_as_found():
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    assert aliases["RIGI"] == "DDX58"
    study = _study(gene_values={"DDX58": (1.0, 2.0, 3.0)})

    rows = make_coverage_rows(
        [study], {"HALLMARK_FIXTURE": ("RIGI",)}, {}
    )

    assert rows[0]["n_found_current"] == 1
    assert rows[0]["n_found_proposed"] == 1
    assert rows[0]["missing_members_current"] == ""


def test_fast_candidate_index_matches_a_meta_resolution():
    aliases = {"RIGI": "DDX58"}
    reference = {
        "by_id": {"101": "TP53"},
        "synonyms": {
            "TP53": frozenset({"OLD_TP53", "SHARED"}),
            "BRCA1": frozenset({"SHARED"}),
        },
    }
    symbols = ["DDX58", "RIGI", "101", "OLD_TP53", "SHARED", "UNKNOWN"]
    targets = ["DDX58", "TP53", "BRCA1"]
    expected = a_features._canonicalize_symbols(
        symbols, targets, runtime="unused", reference=reference
    )
    actual = audit_core._canonicalize_symbols_fast(
        symbols, targets, runtime=Path("unused"), reference=reference, aliases=aliases
    )
    assert actual == expected


def test_fast_probe_resolution_keeps_existing_multiple_probe_synonym_rule():
    aliases = {}
    reference = {
        "by_id": {},
        "synonyms": {"TP53": frozenset({"OLD_A", "OLD_B"})},
    }
    symbols = ["OLD_A", "OLD_B"]
    targets = ["TP53"]
    expected = a_features._canonicalize_symbols(
        symbols, targets, runtime="unused", reference=reference,
        allow_multiple_synonyms=True,
    )
    actual = audit_core._canonicalize_symbols_fast(
        symbols, targets, runtime=Path("unused"), reference=reference,
        aliases=aliases, allow_multiple_synonyms=True,
    )
    assert actual == expected


def test_old_ensembl_row_is_classified_only_with_local_one_to_one_reference():
    study = _study(
        feature_ids=("ENSG00000112096",),
        source_symbols=("ENSEMBL:ENSG00000112096",),
        canonical_symbols=("ENSEMBL:ENSG00000112096",),
        gtf_symbols={"ENSG00000112096": frozenset({"SOD2"})},
    )
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    gap = _classify_gap(
        study=study,
        set_name="HALLMARK_FIXTURE",
        member="SOD2",
        canonical="SOD2",
        aliases=aliases,
        addendum={},
        reference={"by_id": {}, "synonyms": {}},
        synonym_targets={},
        real_names=set(),
    )

    assert gap["classification"] == "old Ensembl ID"
    assert gap["candidate_source_id"] == "ENSG00000112096"
    assert gap["mapping_candidate"] == "SOD2"
    assert gap["mapping_status"] == "proposed"
    assert "GTF" in gap["evidence"]


def test_one_to_many_local_mapping_is_refused_and_remains_absent():
    study = _study(
        feature_ids=("ENSG00000112096",),
        source_symbols=("ENSEMBL:ENSG00000112096",),
        canonical_symbols=("ENSEMBL:ENSG00000112096",),
        gtf_symbols={"ENSG00000112096": frozenset({"SOD2", "TXNIP"})},
    )
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    gap = _classify_gap(
        study=study,
        set_name="HALLMARK_FIXTURE",
        member="SOD2",
        canonical="SOD2",
        aliases=aliases,
        addendum={},
        reference={"by_id": {}, "synonyms": {}},
        synonym_targets={},
        real_names=set(),
    )

    assert gap["classification"] == "old Ensembl ID"
    assert gap["mapping_candidate"] == ""
    assert gap["candidate_source_id"] == ""
    assert "one-to-many mapping refused" in gap["mapping_status"]


def test_ncbi_synonym_proposal_uses_source_id_and_refuses_official_symbol_collision():
    study = _study(
        feature_ids=("old_tp53_key",),
        source_symbols=("OLD_TP53",),
        canonical_symbols=("OLD_TP53",),
    )
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    synonym_reference = {
        "by_id": {"7157": "TP53"},
        "synonyms": {"TP53": frozenset({"OLD_TP53"})},
    }
    gap = _classify_gap(
        study=study,
        set_name="HALLMARK_FIXTURE",
        member="TP53",
        canonical="TP53",
        aliases=aliases,
        addendum={},
        reference=synonym_reference,
        synonym_targets={"TP53": {"TP53"}, "OLD_TP53": {"TP53"}},
        real_names={"TP53", "OLD_TP53"},
    )
    assert gap["classification"] == "NCBI synonym"
    assert gap["candidate_source_id"] == "old_tp53_key"
    assert gap["mapping_status"] == "proposed"

    collision_reference = {
        "by_id": {"7157": "FASN", "2308": "FAS"},
        "synonyms": {"FASN": frozenset({"FAS"}), "FAS": frozenset()},
    }
    collision = _classify_gap(
        study=_study(
            feature_ids=("FAS",),
            source_symbols=("FAS",),
            canonical_symbols=("FAS",),
        ),
        set_name="HALLMARK_FIXTURE",
        member="FASN",
        canonical="FASN",
        aliases=aliases,
        addendum={},
        reference=collision_reference,
        synonym_targets={"FAS": {"FASN", "FAS"}, "FASN": {"FASN"}},
        real_names={"FASN", "FAS"},
    )
    assert collision["classification"] == "NCBI synonym"
    assert collision["mapping_status"] == "unresolved: one-to-many mapping refused"
    assert not collision["mapping_candidate"]


def test_comma_joined_source_feature_is_reported_but_not_split_into_genes():
    study = _study(
        feature_ids=("HLA-A,HLA-G,HLA-H",),
        source_symbols=("HLA-A,HLA-G,HLA-H",),
        canonical_symbols=("HLA-A,HLA-G,HLA-H",),
    )
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    gap = _classify_gap(
        study=study,
        set_name="HALLMARK_FIXTURE",
        member="HLA-A",
        canonical="HLA-A",
        aliases=aliases,
        addendum={},
        reference={"by_id": {}, "synonyms": {}},
        synonym_targets={},
        real_names=set(),
    )

    assert gap["classification"] == "row present but dropped by our pipeline"
    assert gap["source_rows"] == "HLA-A,HLA-G,HLA-H"
    assert not gap["mapping_candidate"]
    assert "no one-to-one gene mapping" in gap["evidence"]


def test_invented_date_like_name_cannot_override_a_real_synonym():
    assert not _is_date_mangled_member("Sep-1", "SEPT1", {"Sep-1"})
    assert _is_date_mangled_member("Sep-1", "SEPT1", set())
    assert not _is_date_mangled_member("made-up", "MARCHF1", set())
    assert _date_mangled_sources("SEPT1", {"sep-1": ["old-name"]}, {"sep-1"}) == []


def test_coverage_schema_and_rows_have_no_patient_or_sample_columns():
    study = _study(gene_values={"SOD2": (1.0, 2.0, 3.0)})
    rows = make_coverage_rows(
        [study], {"HALLMARK_FIXTURE": ("SOD2", "TXNIP")}, {}
    )
    assert not any("patient" in column.casefold() or "sample" in column.casefold()
                   for column in COVERAGE_COLUMNS)
    assert not any("patient" in str(value).casefold() or "sample_" in str(value).casefold()
                   for row in rows for value in row.values())


class _OutcomeGuardStudy:
    """Study payload that fails if a clinical or outcome attribute is requested."""

    def __init__(self, cohort_id):
        self.cohort_id = cohort_id
        self.targeted = False

    def __getattr__(self, name):
        if any(token in name.casefold() for token in ("clinical", "outcome", "response", "orr")):
            raise AssertionError(f"bridging accessed forbidden field {name}")
        raise AttributeError(name)


def test_bridging_comparison_has_no_clinical_or_outcome_access():
    base = _OutcomeGuardStudy("base")
    mask = _OutcomeGuardStudy("mask")
    values = {
        "base": {"A": (1.0, 2.0, 4.0), "B": (2.0, 1.0, 3.0)},
        "mask": {"A": (1.0, 2.0, 3.0)},
    }
    members = ("A", "B")
    full_id = _signature_id(members)
    reduced_id = _signature_id(("A",))
    scores = {
        ("base", full_id): [1.5, 1.5, 3.5],
        ("base", reduced_id): [1.0, 2.0, 4.0],
    }

    rows = _comparison_stats(
        kind="missing",
        method="mean",
        members=members,
        qualified=[base],
        studies=[base, mask],
        targeted=[],
        found={"base": {"A", "B"}, "mask": {"A"}},
        values_by_study=values,
        common=("A",),
        scores=scores,
    )

    assert len(rows) == 1


def test_loader_never_opens_clinical_file(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    expression_path = runtime / "fixture/simple/expression.tsv"
    expression_path.parent.mkdir(parents=True)
    expression_path.write_text("gene\ts1\ts2\nG1\t1\t2\n", encoding="utf-8")
    clinical_path = expression_path.parent / "clinical.tsv"
    clinical_path.write_text("patient_id\torr\nfixture-id\tDO_NOT_READ\n", encoding="utf-8")
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == clinical_path:
            raise AssertionError("clinical.tsv must not be opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(audit_core, "_signed_development_cohorts", lambda: ("fixture",))
    monkeypatch.setattr(audit_core, "cohort_metadata", lambda cohort: SimpleNamespace(
        cohort_id=cohort,
        cancer="lung",
        representation=SimpleNamespace(platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"),
    ))
    monkeypatch.setattr(audit_core, "_local_gtf_symbols", lambda runtime: {})
    monkeypatch.setattr(audit_core, "_local_gene_history", lambda runtime: {})
    monkeypatch.setattr(a_features, "_gene_reference", lambda runtime: {"by_id": {}, "synonyms": {}, "ensembl": {}})
    monkeypatch.setattr(a_features, "_source_symbols", lambda ids, feature_id, **kwargs: list(ids))
    monkeypatch.setattr(scoring_core, "_frozen_aliases", lambda path: {})
    monkeypatch.setattr(a_features, "_gene_alias_addendum", lambda: {})

    studies, gene_sets = audit_core.load_studies(runtime)

    assert len(studies) == 1
    assert studies[0].n_samples == 2
    assert len(gene_sets) == 50



def test_gse176307_salmon_reader_checks_hash_and_logs_tpm(tmp_path):
    import gzip
    import hashlib
    import math

    staged = tmp_path / "staged"
    with gzip.open(staged, "wt", encoding="utf-8") as stream:
        stream.write("\tA1\tA2\nMARCH1\t3\t0\nGENE2\t1\t7\n")
    digest = hashlib.sha256(staged.read_bytes()).hexdigest()
    pinned = tmp_path / digest
    staged.rename(pinned)

    features, columns, matrix = audit_core.read_gse176307_salmon(pinned)

    assert features == ["MARCH1", "GENE2"]
    assert columns == ["A1", "A2"]
    assert matrix == [[2.0, 0.0], [1.0, 3.0]]
    assert math.isfinite(matrix[0][0])

    wrong = tmp_path / ("0" * 64)
    wrong.write_bytes(pinned.read_bytes())
    with pytest.raises(ValueError, match="pinned hash"):
        audit_core.read_gse176307_salmon(wrong)
