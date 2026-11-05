"""Outcome-blind loading and mapping for the frozen Hallmark memberships."""
from __future__ import annotations

import csv
import gzip
import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from tools.a_cohorts.view import cohort_metadata
from tools.a_meta import features as a_features
from tools.a_meta.__main__ import _signed_development_cohorts
from tools.a_p2.build import COHORTS as A_P2_BASELINE_COHORTS
from tools.a_scoring import core as scoring_core


ROOT = Path(__file__).resolve().parents[2]
HALLMARK_GMT = ROOT / "specs/amendments/2026-11-04-numerical-freeze/hallmark_2026.1.Hs.gmt"
HALLMARK_SHA256 = "01f390fb123ac08c75874030233a4252122c9d7f97c1e173366b587438f57ad5"
G026_GTF_SHA256 = "2d1bdff8d91e08f1291fd47850d9d61cfa6768cc3a4cb8516775a873b007d0f6"
GSE176307_SALMON_SHA256 = "c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894"


@dataclass(frozen=True)
class StudyData:
    cohort_id: str
    cancer: str
    platform: str
    feature_id: str
    targeted: bool
    usable_baseline: bool
    gene_values: Mapping[str, tuple[float, ...]]
    source_feature_ids: tuple[str, ...]
    source_symbols: tuple[str, ...]
    canonical_source_symbols: tuple[str | None, ...]
    source_values: tuple[tuple[float, ...], ...]
    n_samples: int
    expression_rows: int
    gtf_symbols: Mapping[str, frozenset[str]]
    gene_history: Mapping[str, frozenset[str]]


def read_hallmark_sets(path: Path | str = HALLMARK_GMT) -> dict[str, tuple[str, ...]]:
    path = Path(path)
    digest = _sha256(path)
    if digest != HALLMARK_SHA256:
        raise ValueError("Hallmark GMT does not match the numerical-freeze draft hash")
    result: dict[str, tuple[str, ...]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 3 or not fields[0]:
                raise ValueError(f"Malformed Hallmark GMT row {line_number}")
            name, members = fields[0], tuple(fields[2:])
            if name in result or not members or any(not member for member in members):
                raise ValueError(f"Invalid Hallmark membership at row {line_number}")
            if len(set(members)) != len(members):
                raise ValueError(f"Duplicate member in Hallmark set {name}")
            result[name] = members
    if len(result) != 50:
        raise ValueError("The frozen Hallmark GMT must contain exactly 50 sets")
    return result


def load_studies(runtime: Path | str | None = None) -> tuple[list[StudyData], dict[str, tuple[str, ...]]]:
    """Load signed cohort expression only; no clinical table is opened here."""
    gene_sets = read_hallmark_sets()
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    original_targets = {member for members in gene_sets.values() for member in members}
    target_symbols = tuple(sorted({aliases.get(x, x) for x in original_targets}))
    runtime_path = scoring_core._runtime_path(runtime).expanduser().resolve()
    gtf_symbols = _local_gtf_symbols(runtime_path)
    gene_history = _local_gene_history(runtime_path)
    baseline_roster = set(A_P2_BASELINE_COHORTS)
    studies: list[StudyData] = []

    for cohort_id in _signed_development_cohorts():
        metadata = cohort_metadata(cohort_id)
        expression_path = runtime_path / cohort_id / "simple" / "expression.tsv"
        reference = a_features._gene_reference(str(runtime_path))
        representation = metadata.representation
        feature_id = str(representation.feature_id)
        if cohort_id == "gse176307":
            # A-META scores this study from Salmon TPM. Every assay column is
            # read directly, so the identity packet is never opened.
            feature_ids, sample_columns, scaled_matrix = read_gse176307_salmon(
                runtime_path / "gse176307/store_tpm/objects" / GSE176307_SALMON_SHA256
            )
            feature_id = a_features._gse176307_feature_id(feature_ids)
        else:
            feature_ids, sample_columns, matrix = a_features._read_expression(expression_path)
            _, scaled_matrix = a_features._study_scale(matrix, representation)
        if metadata.representation.platform == "microarray" and metadata.representation.feature_id == "probe":
            probe_map = a_features._probe_mapping(expression_path.parent / "probe_to_gene.tsv")
            source_symbols = tuple(
                a_features._probe_source_symbol(probe_map.get(probe), {}, reference)
                for probe in feature_ids
            )
            canonical = _canonicalize_symbols_fast(
                source_symbols,
                target_symbols,
                runtime=runtime_path,
                reference=reference,
                aliases=aliases,
                allow_multiple_synonyms=True,
            )
            gene_ids, gene_matrix, _, _ = a_features._collapse_probes(
                feature_ids, scaled_matrix, canonical
            )
            canonical_source = tuple(canonical)
        else:
            source_symbols = tuple(a_features._source_symbols(
                feature_ids,
                feature_id,
                custom_map={},
                reference=reference,
            ))
            canonical_source = tuple(_canonicalize_symbols_fast(
                source_symbols,
                target_symbols,
                runtime=runtime_path,
                reference=reference,
                aliases=aliases,
            ))
            gene_ids, gene_matrix, _, _ = a_features._collapse_duplicate_genes(
                canonical_source, scaled_matrix
            )

        values: dict[str, tuple[float, ...]] = {}
        for symbol, row in zip(gene_ids, gene_matrix):
            if any(value is None or not math.isfinite(float(value)) for value in row):
                raise ValueError(f"Non-finite expression remains in {cohort_id}")
            values[symbol] = tuple(float(value) for value in row)
        source_values = tuple(tuple(float(value) for value in row) for row in scaled_matrix)

        studies.append(StudyData(
            cohort_id=cohort_id,
            cancer=metadata.cancer,
            platform=str(metadata.representation.platform),
            feature_id=feature_id,
            targeted=metadata.representation.platform in {"targeted_rna", "nanostring"},
            usable_baseline=cohort_id in baseline_roster,
            gene_values=values,
            source_feature_ids=tuple(feature_ids),
            source_symbols=source_symbols,
            canonical_source_symbols=canonical_source,
            source_values=source_values,
            n_samples=len(sample_columns),
            expression_rows=len(feature_ids),
            gtf_symbols=gtf_symbols,
            gene_history=gene_history,
        ))
    return studies, gene_sets


def read_gse176307_salmon(path: Path | str) -> tuple[list[str], list[str], list[list[float]]]:
    """Return the hash-checked Salmon matrix on log2(TPM+1), all assay columns."""
    path = Path(path)
    if _sha256(path) != path.name:
        raise ValueError("GSE176307 Salmon TPM does not match its pinned hash")
    feature_ids: list[str] = []
    matrix: list[list[float]] = []
    with gzip.open(path, "rt", newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        header = next(reader)
        columns = header[1:]
        if len(set(columns)) != len(columns):
            raise ValueError("GSE176307 Salmon TPM has duplicate assay columns")
        for row in reader:
            if len(row) != len(header):
                raise ValueError("GSE176307 Salmon TPM has a malformed row")
            values = [float(value) for value in row[1:]]
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError("GSE176307 Salmon TPM has an invalid abundance")
            feature_ids.append(row[0])
            matrix.append([math.log2(value + 1.0) for value in values])
    return feature_ids, columns, matrix


def _canonicalize_symbols_fast(
    symbols: Sequence[str],
    targets: Sequence[str],
    *,
    runtime: Path,
    reference: Mapping,
    aliases: Mapping[str, str],
    allow_multiple_synonyms: bool = False,
) -> list[str | None]:
    """Use a_meta's row normalization and a_scoring.resolve on indexed candidates.

    The general a_meta resolver considers every source row against every target.
    Hallmark has thousands of targets, so this adapter indexes the local NCBI
    synonym map first and delegates each small, relevant candidate set to the
    unchanged a_scoring resolver. Ambiguous target/source relationships are
    refused with the same rule as resolve().
    """
    normalized = [aliases.get(str(symbol), str(symbol)) if symbol else "" for symbol in symbols]
    unique_symbols = list(dict.fromkeys(symbol for symbol in normalized if symbol))
    target_set = set(targets)
    gene_symbols = reference["by_id"]
    synonyms = reference["synonyms"]
    resolver_symbol = {
        symbol: gene_symbols.get(symbol, symbol)
        for symbol in unique_symbols
    }
    synonym_targets: dict[str, set[str]] = defaultdict(set)
    for target in targets:
        for synonym in synonyms.get(target, ()):
            if synonym:
                synonym_targets[synonym].add(target)

    direct_by_target: dict[str, list[str]] = defaultdict(list)
    synonym_by_target: dict[str, list[str]] = defaultdict(list)
    for symbol in unique_symbols:
        current = resolver_symbol[symbol]
        direct = aliases.get(current, current)
        if direct in target_set:
            direct_by_target[direct].append(symbol)
        for target in synonym_targets.get(current, ()):
            if target in target_set:
                synonym_by_target[target].append(symbol)

    direct_sources = {symbol for rows in direct_by_target.values() for symbol in rows}
    resolved: dict[str, str] = {}
    for target in targets:
        direct = direct_by_target.get(target, [])
        if direct:
            indexes, _ = scoring_core.resolve(
                direct,
                [target],
                runtime=runtime,
                aliases=aliases,
                synonyms=synonyms,
                gene_symbols=gene_symbols,
            )
            if target in indexes:
                resolved[direct[indexes[target]]] = target

    for target in targets:
        if target in {value for value in resolved.values()}:
            continue
        candidates = list(dict.fromkeys(synonym_by_target.get(target, ())))
        if not candidates:
            continue
        ambiguous = not allow_multiple_synonyms and any(
            len(synonym_targets.get(resolver_symbol[symbol], ())) > 1
            or symbol in direct_sources
            for symbol in candidates
        )
        if ambiguous:
            continue
        if len(candidates) == 1:
            indexes, _ = scoring_core.resolve(
                candidates,
                [target],
                runtime=runtime,
                aliases=aliases,
                synonyms=synonyms,
                gene_symbols=gene_symbols,
            )
            if target in indexes:
                resolved[candidates[indexes[target]]] = target
        elif allow_multiple_synonyms:
            for candidate in sorted(candidates):
                indexes, _ = scoring_core.resolve(
                    [candidate],
                    [target],
                    runtime=runtime,
                    aliases=aliases,
                    synonyms=synonyms,
                    gene_symbols=gene_symbols,
                )
                if target in indexes and candidate not in resolved:
                    resolved[candidate] = target

    return [resolved.get(symbol, symbol) if symbol else None for symbol in normalized]


def _local_gtf_symbols(runtime: Path) -> dict[str, frozenset[str]]:
    """Use only the locally pinned recount3 G026 GTF, when present."""
    candidates = (
        runtime / "kim2018/store-recount3/objects" / G026_GTF_SHA256,
        runtime / "gide2019/store-recount3/objects" / G026_GTF_SHA256,
    )
    symbols: dict[str, set[str]] = {}
    for path in candidates:
        if not path.is_file():
            continue
        annotation = scoring_core._recount3_annotation(path)
        for ensembl_id, (symbol, _length, _primary) in annotation.items():
            base = ensembl_id.split(".", 1)[0]
            symbols.setdefault(base, set()).add(symbol)
    return {key: frozenset(value) for key, value in symbols.items()}


def _local_gene_history(runtime: Path) -> dict[str, frozenset[str]]:
    """Read an optional local NCBI gene_history object, if this runtime has one."""
    root = runtime / "reference_gene_maps"
    if not root.is_dir():
        return {}
    matches = sorted(
        path for path in root.rglob("*")
        if path.is_file() and "gene_history" in path.name.casefold()
    )
    result: dict[str, set[str]] = {}
    for path in matches:
        opener = __import__("gzip").open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            fields = {name.lstrip("#").casefold(): name for name in (reader.fieldnames or [])}
            old_id = fields.get("discontinued_geneid")
            current_id = fields.get("geneid")
            if not old_id or not current_id:
                continue
            for row in reader:
                old, current = row.get(old_id, "").strip(), row.get(current_id, "").strip()
                if old and current:
                    result.setdefault(old, set()).add(current)
    return {key: frozenset(value) for key, value in result.items()}


def current_member(member: str, aliases: Mapping[str, str]) -> str:
    """Apply the frozen alias table to a GMT member before availability checks."""
    return aliases.get(member, member)


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
