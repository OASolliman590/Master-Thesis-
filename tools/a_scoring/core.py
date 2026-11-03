"""Representation conversion, gene resolution and panel/endpoint scoring."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
ALIAS_TABLE_PATH = ROOT / 'specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv'
PANEL_REGISTRY_PATH = ROOT / 'specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json'
COHORT_REGISTRY_PATH = ROOT / 'docs/cohorts/REGISTRY.tsv'
GENE_INFO_SHA256 = 'd332c8dcc76b0fc052dd7d66b17479b63e40f6b199f2eb40e5f7ea2fa59371dc'
DEFAULT_PANELS = (
    'P_ANTIGEN_PRESENTATION', 'M2_CYTOTOXICITY', 'M3_VIRAL_MIMICRY',
    'M4_EXCLUSION',
)


def _runtime_path(runtime: Path | str | None = None) -> Path:
    selected = runtime if runtime is not None else os.environ.get('THESIS_RUNTIME', ROOT / '.scratch/runtime')
    return Path(selected).expanduser()


def gene_info_path(runtime: Path | str | None = None) -> Path:
    return _runtime_path(runtime) / 'reference_gene_maps/store/objects' / GENE_INFO_SHA256


def _checked_file(path: Path, root: Path) -> Path:
    root = root.expanduser().resolve()
    path = path.expanduser()
    if path.is_symlink():
        raise ValueError(f'Symlink in reference path: {path}')
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f'Reference path escapes its root: {path}')
    current = path
    while current != root and current != current.parent:
        if current.is_symlink():
            raise ValueError(f'Symlink in reference path: {current}')
        current = current.parent
    if not resolved.is_file():
        raise FileNotFoundError(f'Missing reference file: {path}')
    return resolved


@lru_cache(maxsize=8)
def _frozen_aliases(path_text: str) -> dict[str, str]:
    path = _checked_file(Path(path_text), ROOT)
    with path.open(newline='') as stream:
        return {
            row['source_symbol']: row['registry_symbol']
            for row in csv.DictReader(stream, delimiter='\t')
        }


@lru_cache(maxsize=8)
def _gene_info(path_text: str, runtime_text: str) -> tuple[dict[str, str], dict[str, frozenset[str]]]:
    path = _checked_file(Path(path_text), Path(runtime_text))
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != GENE_INFO_SHA256:
        raise ValueError('pinned NCBI gene_info hash mismatch')
    by_id: dict[str, str] = {}
    synonyms: dict[str, set[str]] = defaultdict(set)
    with gzip.open(path, 'rt') as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            symbol = row['Symbol']
            by_id[row['GeneID']] = symbol
            synonyms[symbol].update(value for value in row['Synonyms'].split('|') if value and value != '-')
    return by_id, {key: frozenset(values) for key, values in synonyms.items()}


@lru_cache(maxsize=4)
def _panel_registry(path_text: str) -> dict[str, tuple[str, ...]]:
    path = _checked_file(Path(path_text), ROOT)
    registry = json.loads(path.read_text())
    return {
        item['id']: tuple(item['membership'])
        for item in registry['programmes']
        if item.get('membership') is not None
    }


@lru_cache(maxsize=4)
def _cohort_endpoints(path_text: str) -> dict[str, str]:
    path = _checked_file(Path(path_text), ROOT)
    with path.open(newline='') as stream:
        return {
            row['cohort_id']: row['endpoints']
            for row in csv.DictReader(stream, delimiter='\t')
        }


def panel_definitions(panel_ids: Sequence[str] | None = None) -> dict[str, tuple[str, ...]]:
    """Return memberships from the frozen registry, defaulting to A-P2's four panels."""
    registry = _panel_registry(str(PANEL_REGISTRY_PATH))
    selected = DEFAULT_PANELS if panel_ids is None else tuple(panel_ids)
    missing = [panel for panel in selected if panel not in registry]
    if missing:
        raise ValueError('Unknown panel(s): ' + ', '.join(missing))
    return {panel: registry[panel] for panel in selected}


def _representation_fields(representation) -> tuple[str, str, str]:
    if hasattr(representation, 'clinical_rows') and hasattr(representation, 'metadata'):
        representation = representation.metadata.representation
    elif hasattr(representation, 'representation') and not isinstance(representation, Mapping):
        representation = representation.representation
    if isinstance(representation, str):
        platform, unit, transform = 'rnaseq', representation, 'linear'
    elif isinstance(representation, Mapping):
        platform = representation.get('platform', 'rnaseq')
        unit = representation.get('unit', '')
        transform = representation.get('transform', 'linear')
    else:
        platform = getattr(representation, 'platform', 'rnaseq')
        unit = getattr(representation, 'unit', '')
        transform = getattr(representation, 'transform', 'linear')
    return str(platform).casefold(), str(unit).casefold(), str(transform).casefold()


def _matrix_rows(matrix) -> list[list[float]]:
    try:
        rows = [[float(value) for value in row] for row in matrix]
    except (TypeError, ValueError):
        raise ValueError('expression matrix must be a rectangular numeric matrix') from None
    if not rows:
        return rows
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError('expression matrix must be rectangular')
    if any(not math.isfinite(value) or value < 0 for row in rows for value in row):
        raise ValueError('invalid abundance: values must be finite and non-negative')
    return rows


def to_tpm(matrix, representation, lengths: Sequence[float] | None = None) -> list[list[float]]:
    """Convert linear whole-transcriptome RNA-seq values to TPM, preserving feature rows.

    `matrix` is feature × sample. Existing linear TPM is validated and returned
    unchanged. Counts require one positive effective length per feature.
    """
    platform, unit, transform = _representation_fields(representation)
    if platform != 'rnaseq':
        raise ValueError(f'Cannot convert {platform}/{unit} to TPM; whole-transcriptome RNA-seq is required')
    if transform != 'linear':
        raise ValueError(f'Cannot convert {unit} with {transform} transform to TPM; values must be linear')
    if unit not in {'tpm', 'fpkm', 'rpkm', 'counts'}:
        raise ValueError(f'Cannot convert {unit or "unknown unit"} to TPM')

    rows = _matrix_rows(matrix)
    if not rows:
        return rows
    width = len(rows[0])
    if unit == 'counts':
        if lengths is None or len(lengths) != len(rows):
            raise ValueError('counts to TPM requires one gene length per feature')
        normalized_lengths = [float(length) for length in lengths]
        if any(not math.isfinite(length) or length <= 0 for length in normalized_lengths):
            raise ValueError('missing or invalid gene length')
        rates = [[value / length for value in row] for row, length in zip(rows, normalized_lengths)]
    else:
        rates = rows

    # Keep the former left-to-right accumulation; float `sum` changed in Python 3.12.
    totals = [0.0] * width
    for row in rates:
        for column, value in enumerate(row):
            totals[column] += value
    if any(not math.isfinite(total) or total <= 0 for total in totals):
        raise ValueError('invalid abundance or zero denominator')
    if unit == 'tpm':
        return rows
    multipliers = [1e6 / total for total in totals]
    return [
        [value * multipliers[column] for column, value in enumerate(row)]
        for row in rates
    ]


def log2p1(matrix, representation=None, lengths: Sequence[float] | None = None) -> list[list[float]]:
    """Apply log2(TPM+1), converting first when a representation is supplied."""
    values = to_tpm(matrix, representation, lengths) if representation is not None else _matrix_rows(matrix)
    return [[math.log2(value + 1) for value in row] for row in values]


def _recount3_annotation(gtf_path: Path | str) -> dict[str, tuple[str, float | None, bool]]:
    primary = {f'chr{chromosome}' for chromosome in (*range(1, 23), 'X', 'Y', 'M')}
    annotation = {}
    with gzip.open(gtf_path, 'rt') as stream:
        for line in stream:
            if line.startswith('#'):
                continue
            fields = line.rstrip('\n').split('\t')
            if len(fields) != 9:
                raise ValueError('malformed GTF row')
            if fields[2] != 'gene':
                continue
            attributes = dict(re.findall(r'(\w+) "([^"]+)"', fields[8]))
            gene, symbol = attributes.get('gene_id'), attributes.get('gene_name')
            if not gene or not symbol or gene in annotation:
                raise ValueError('missing or duplicate GTF gene identifier or symbol')
            is_primary = fields[0] in primary
            if is_primary:
                try:
                    length = float(fields[5])
                except ValueError:
                    raise ValueError('invalid recount3 gene length') from None
                if not math.isfinite(length) or length <= 0:
                    raise ValueError('invalid recount3 gene length')
            else:
                length = None
            annotation[gene] = (symbol, length, is_primary)
    if not annotation:
        raise ValueError('GTF contains no gene rows')
    return annotation


def recount3_to_tpm(
    gene_ids: Sequence[str], counts, gtf_path: Path | str,
) -> tuple[list[str], list[list[float]], int]:
    """Map recount3 GENCODE gene IDs and convert primary-assembly counts to TPM.

    G026's gene-row score (GTF column 6) supplies recount3 `bp_length`.
    Non-primary contigs are omitted before the per-sample TPM denominator.
    """
    rows = _matrix_rows(counts)
    if len(gene_ids) != len(rows):
        raise ValueError('recount3 gene IDs do not align with count rows')
    annotation = _recount3_annotation(gtf_path)
    symbols, retained, lengths, dropped = [], [], [], 0
    for gene_id, values in zip(gene_ids, rows):
        if gene_id not in annotation:
            raise ValueError('matrix gene missing from recount3 annotation')
        symbol, length, is_primary = annotation[gene_id]
        if not is_primary:
            dropped += 1
            continue
        symbols.append(symbol)
        retained.append(values)
        lengths.append(length)
    tpm = to_tpm(retained, {'platform': 'rnaseq', 'unit': 'counts', 'transform': 'linear'}, lengths)
    return symbols, tpm, dropped


def resolve(
    symbols: Sequence[str],
    targets: Sequence[str] | set[str],
    *,
    runtime: Path | str | None = None,
    aliases: Mapping[str, str] | None = None,
    synonyms: Mapping[str, set[str] | frozenset[str]] | None = None,
    gene_symbols: Mapping[str, str] | None = None,
) -> tuple[dict[str, int], dict[str, dict[str, object]]]:
    """Map requested symbols to unique rows and report resolution coverage per target.

    Defaults use the frozen alias table and pinned NCBI gene_info under the
    selected runtime. Optional maps make the same behavior testable on fixtures.
    """
    runtime_path = _runtime_path(runtime)
    if aliases is None:
        aliases = _frozen_aliases(str(ALIAS_TABLE_PATH))
    if synonyms is None or gene_symbols is None:
        info_path = _checked_file(gene_info_path(runtime_path), runtime_path)
        loaded_ids, loaded_synonyms = _gene_info(str(info_path), str(runtime_path.resolve()))
        if synonyms is None:
            synonyms = loaded_synonyms
        if gene_symbols is None:
            gene_symbols = loaded_ids
    synonyms = synonyms or {}
    gene_symbols = gene_symbols or {}

    canonical: list[str] = []
    for source_symbol in symbols:
        raw = str(source_symbol)
        symbol = str(gene_symbols.get(raw, raw))
        canonical.append(symbol)

    target_order = sorted(targets) if isinstance(targets, (set, frozenset)) else targets
    target_order = tuple(target_order)
    target_set = set(target_order)
    direct: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for index, source_symbol in enumerate(symbols):
        raw, symbol = str(source_symbol), canonical[index]
        mapped_target = str(aliases.get(symbol, symbol))
        if mapped_target in target_set:
            direct[mapped_target].append((index, raw, symbol))

    indices: dict[str, int] = {}
    coverage: dict[str, dict[str, object]] = {}
    used_rows: dict[int, str] = {}
    for target in target_order:
        matches = direct.get(target, [])
        if len(matches) > 1:
            raise ValueError('duplicate rows for required gene ' + target)
        if matches:
            index, raw, symbol = matches[0]
            resolution = 'alias' if aliases.get(symbol, symbol) != symbol else 'exact'
            indices[target] = index
            used_rows[index] = target
            coverage[target] = {
                'present': True, 'resolution': resolution,
                'source_symbol': raw, 'resolved_symbol': symbol,
            }

    unresolved = target_set - indices.keys()
    candidates_by_target: dict[str, list[int]] = defaultdict(list)
    targets_by_row: dict[int, set[str]] = defaultdict(set)
    for target in target_order:
        target_synonyms = synonyms.get(target, set())
        for index, symbol in enumerate(canonical):
            if symbol in target_synonyms:
                if target in unresolved:
                    candidates_by_target[target].append(index)
                targets_by_row[index].add(target)

    ambiguous_targets = {
        target
        for row_targets in targets_by_row.values()
        if len(row_targets) > 1
        for target in row_targets
    }
    for target in unresolved:
        candidates = candidates_by_target.get(target, [])
        if len(candidates) > 1:
            ambiguous_targets.add(target)
        if any(index in used_rows for index in candidates):
            ambiguous_targets.add(target)

    for target in target_order:
        if target in indices:
            continue
        candidates = candidates_by_target.get(target, [])
        if (target not in ambiguous_targets and len(candidates) == 1
                and targets_by_row[candidates[0]] == {target}
                and candidates[0] not in used_rows):
            index = candidates[0]
            indices[target] = index
            used_rows[index] = target
            coverage[target] = {
                'present': True, 'resolution': 'synonym',
                'source_symbol': str(symbols[index]), 'resolved_symbol': canonical[index],
            }
        else:
            coverage[target] = {
                'present': False,
                'resolution': 'ambiguous' if target in ambiguous_targets else 'missing',
                'source_symbol': None, 'resolved_symbol': None,
                'candidate_count': len(candidates),
            }
    return indices, coverage


def panel_scores(
    expression: Mapping[str, float],
    panels: Mapping[str, Sequence[str]] | None = None,
    require_complete: bool = True,
) -> tuple[dict[str, float | None], dict[str, dict[str, object]]]:
    """Score one sample as an unweighted mean on the supplied expression scale.

    Incomplete panels receive `None` when complete coverage is required. The
    coverage map records members found and missing after callers resolve aliases.
    """
    selected = panel_definitions() if panels is None else {
        name: tuple(genes) for name, genes in panels.items()
    }
    scores: dict[str, float | None] = {}
    coverage: dict[str, dict[str, object]] = {}
    for name, genes in selected.items():
        found = tuple(gene for gene in genes if gene in expression and expression[gene] is not None)
        missing = tuple(gene for gene in genes if gene not in expression or expression[gene] is None)
        complete = not missing
        coverage[name] = {
            'found': found, 'missing': missing,
            'n_found': len(found), 'n_total': len(genes), 'complete': complete,
        }
        if not found or (require_complete and not complete):
            scores[name] = None
        else:
            scores[name] = sum(float(expression[gene]) for gene in found) / len(found)
    return scores, coverage


def cyt(gzma: float, prf1: float) -> float:
    """The frozen no-offset CYT comparator: sqrt(TPM_GZMA × TPM_PRF1)."""
    return math.sqrt(gzma * prf1)


def _label_token(value: object) -> str:
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def _has_orr_definition(text: str) -> bool:
    if re.search(r'\bno\s+(?:RECIST|ORR)|does not define.{0,50}RECIST|not called.{0,30}ORR', text):
        return False
    has_orr = bool(re.search(r'\borr\b', text))
    has_recist = bool(re.search(r'\b(?:i?recist)\b', text))
    has_positive = bool(re.search(r'\b(?:cr|pr)\b|complete response|partial response', text))
    has_negative = bool(re.search(r'\b(?:sd|pd|nr)\b|stable disease|progressive disease', text))
    return (has_orr and has_recist) or ((has_orr or has_recist) and has_positive and has_negative)


def _has_clinical_benefit_definition(text: str) -> bool:
    if re.search(r'\b(?:dcb|ndb)\b|\bcb\s*/\s*icb\s*/\s*ncb\b', text):
        return True
    clinical = bool(re.search(r'clinical benefit|durable benefit|durable clinical benefit', text))
    criteria = bool(re.search(
        r'\b(?:pfs|progression.free survival|duration|durable|weeks?|months?|days?)\b|[<>]=?\s*\d',
        text,
    ))
    return clinical and criteria


def _source_binary_definition(text: str) -> bool:
    return bool(re.search(r'source[_ ]binary|treatment outcome|treatment response', text))


def _registry_declares_orr(text: str) -> bool:
    return bool(re.search(r'\borr\b', text) and not re.search(r'\bnot\s+orr\b', text))


def _registry_declares_clinical_benefit(text: str) -> bool:
    return bool(re.search(r'clinical benefit|clinical_benefit|\b(?:dcb|ndb)\b|\bcb\s*/\s*icb\s*/\s*ncb\b', text))


def _family_context_allows(family: str, text: str, has_context: bool) -> bool:
    if not has_context:
        return True
    orr = _has_orr_definition(text)
    clinical_benefit = _has_clinical_benefit_definition(text)
    if family == 'orr':
        return _registry_declares_orr(text) and not re.search(
            r'no\s+(?:RECIST|ORR)|does not define.{0,50}RECIST|not called.{0,30}ORR', text,
        )
    if family == 'clinical_benefit':
        return _registry_declares_clinical_benefit(text) or clinical_benefit
    return _source_binary_definition(text) and not orr and not clinical_benefit


def _source_binary(value: object) -> int | None:
    key = _label_token(value)
    if key in {'1', 'R', 'RESPONDER', 'RESPONDERS', 'RESPONDED', 'SOURCEPOSITIVE', 'POSITIVE', 'YES', 'TRUE'}:
        return 1
    if key in {'0', 'NR', 'NONRESPONDER', 'NONRESPONDERS', 'NONRESPONSE', 'PROGRESSOR', 'PROGRESSORS', 'PROGRESSED', 'SOURCENEGATIVE', 'NEGATIVE', 'NO', 'FALSE'}:
        return 0
    return None


def _first_label(row: Mapping[str, object], fields: Sequence[str]) -> object:
    for field in fields:
        value = row.get(field)
        if str(value or '').strip().upper() not in {'', 'UNKNOWN', 'NA', 'N/A'}:
            return value
    return ''


def endpoint_label(rows, family: str) -> tuple[list[int | None], dict[str, int]]:
    """Normalize a cohort endpoint and count excluded rows by reason.

    CohortView input supplies the cohort ID. R/NR is interpreted only when the
    registry and loader definition establish the corresponding endpoint family.
    """
    if family not in {'orr', 'clinical_benefit', 'source_label'}:
        raise ValueError(f'Unknown endpoint family: {family!r}')
    view = rows if hasattr(rows, 'clinical_rows') and hasattr(rows, 'metadata') else None
    if view is not None:
        records = list(view.clinical_rows)
        cohort_id = getattr(view.metadata, 'cohort_id', None)
    else:
        records = list(rows)
        cohort_ids = {str(row.get('cohort_id')) for row in records if row.get('cohort_id')}
        cohort_id = next(iter(cohort_ids)) if len(cohort_ids) == 1 else None
    registry_text = _cohort_endpoints(str(COHORT_REGISTRY_PATH)).get(cohort_id, '') if cohort_id else ''
    has_context = bool(cohort_id and registry_text)
    labels: list[int | None] = []
    excluded: Counter[str] = Counter()
    for row in records:
        definition = str(row.get('endpoint_definition', '') or '').casefold()
        text = f'{registry_text} {definition}'.casefold()
        token = _label_token(_first_label(row, {
            'orr': ('raw_orr', 'orr'),
            'clinical_benefit': ('clinical_benefit', 'raw_clinical_benefit'),
            'source_label': ('treatment_outcome', 'raw_clinical_benefit', 'raw_orr',
                             'clinical_benefit', 'orr'),
        }[family]))
        if token in {'NE', 'NOTEVALUABLE'}:
            label, reason = None, 'not_evaluable'
        elif token in {'ICB', 'INTERMEDIATEBENEFIT', 'INTERMEDIATECLINICALBENEFIT'}:
            label, reason = None, 'intermediate_benefit'
        elif token in {'', 'UNKNOWN', 'NA'}:
            label, reason = None, 'unknown'
        elif not _family_context_allows(family, text, has_context):
            label, reason = None, 'family_mismatch'
        elif family == 'orr':
            if token in {'CR', 'COMPLETERESPONSE', 'PR', 'PARTIALRESPONSE'}:
                label, reason = 1, ''
            elif token in {'SD', 'STABLEDISEASE', 'PD', 'PROGRESSIVEDISEASE'}:
                label, reason = 0, ''
            elif token == 'R' and _has_orr_definition(text):
                label, reason = 1, ''
            elif token == 'NR' and _has_orr_definition(text):
                label, reason = 0, ''
            else:
                label, reason = None, 'unmapped_category'
        elif family == 'clinical_benefit':
            if token in {'DCB', 'CB', 'DURABLEBENEFIT', 'DURABLECLINICALBENEFIT', 'CLINICALBENEFIT', 'BENEFIT'}:
                label, reason = 1, ''
            elif token in {'NDB', 'NCB', 'NODURABLEBENEFIT', 'NOCLINICALBENEFIT', 'NOBENEFIT'}:
                label, reason = 0, ''
            elif not has_context or _has_clinical_benefit_definition(text):
                label = _source_binary(token)
                reason = '' if label is not None else 'unmapped_category'
            else:
                label, reason = None, 'unmapped_category'
        else:
            if token in {'DCB', 'NDB', 'CB', 'ICB', 'NCB'}:
                label, reason = None, 'family_mismatch'
            else:
                label = _source_binary(token)
                reason = '' if label is not None else 'unmapped_category'
        if reason:
            excluded[reason] += 1
        labels.append(label)
    return labels, dict(sorted(excluded.items()))
