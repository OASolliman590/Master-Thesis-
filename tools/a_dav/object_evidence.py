"""Apply approved, outcome-blind rules to a pinned expression object's values."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit


def derive_object_evidence(rows: Iterable[tuple[str, Sequence[str]]], *, source_sha256: str,
                           rsem_source: str | None = None, filename_unit: str | None = None,
                           filename_locator: str | None = None,
                           paper_noncontradiction: str | None = None) -> dict[str, Any]:
    """Return aggregate facts and excluded feature identifiers, never sample data."""
    if not re.fullmatch(r'[a-f0-9]{64}', source_sha256):
        raise ValueError('SOURCE_HASH_INVALID')
    types: set[str] = set()
    feature_count = missing_cells = missing_genes = values_count = 0
    whole_nonnegative = True
    fractional = False
    invalid_values = False
    identifiers: list[str] = []
    maximum: Decimal | None = None
    for feature, values in rows:
        feature_count += 1
        value = feature.strip()
        identifiers.append(value)
        if re.fullmatch(r'ENSG\d{11}(?:\.\d+)?', value):
            types.add('ENSEMBL_GENE')
        elif re.fullmatch(r'\d+', value):
            types.add('ENTREZ_GENE')
        elif re.fullmatch(r'[A-Za-z][A-Za-z0-9.-]*', value) and not re.match(r'^ENSG\d', value):
            types.add('GENE_SYMBOL')
        else:
            types.add('AMBIGUOUS')
        missing = False
        for raw in values:
            text = str(raw).strip()
            if not text or text.upper() in {'NA', 'N/A', 'NULL'}:
                missing_cells += 1
                missing = True
                continue
            try:
                number = Decimal(text)
            except InvalidOperation:
                invalid_values = True
                continue
            if not number.is_finite() or number < 0:
                invalid_values = True
                continue
            values_count += 1
            maximum = number if maximum is None else max(maximum, number)
            if number != number.to_integral_value():
                whole_nonnegative = False
                fractional = True
        missing_genes += int(missing)
    def fact(value: str, rule: str, **evidence: str) -> dict[str, Any]:
        return {'status': 'DERIVED', 'value': value, 'evidence_type': 'DERIVED_FROM_OBJECT',
                'rule': rule, 'source_sha256': source_sha256, **evidence}
    def blocked(reason: str) -> dict[str, Any]:
        return {'status': 'BLOCKED', 'value': None, 'reason': reason}
    symbol_count = sum(bool(re.fullmatch(r'[A-Z0-9][A-Za-z0-9.-]*', x)) for x in identifiers)
    symbol_share = symbol_count / feature_count if feature_count else 0.0
    frequencies = Counter(identifiers)
    excluded_rows = []
    for index, identifier in enumerate(identifiers, 1):
        if not re.fullmatch(r'[A-Z0-9][A-Za-z0-9.-]*', identifier):
            reason = 'NONSTANDARD_IDENTIFIER'
        elif re.fullmatch(r'(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?:[1-9]|[12][0-9]|3[01])', identifier):
            reason = 'DATE_MANGLED_APPEARANCE'
        elif frequencies[identifier] > 1:
            reason = 'DUPLICATE_SYMBOL'
        else:
            continue
        excluded_rows.append({'row': index, 'identifier': identifier, 'reason': reason})
    ensembl_count = sum(bool(re.fullmatch(r'ENSG\d{11}(?:\.\d+)?', x)) for x in identifiers)
    # Ensembl IDs also match the broad symbol regex; a substantial mixed Ensembl
    # population is ambiguous rather than evidence of HGNC symbols.
    mixed_ensembl = len(types) > 1 and ensembl_count * 100 > feature_count
    if feature_count and symbol_count * 100 >= 99 * feature_count and not mixed_ensembl and types not in ({'ENSEMBL_GENE'}, {'ENTREZ_GENE'}):
        feature_fact = fact('GENE_SYMBOL', 'GENE_SYMBOL_MAJORITY')
    elif feature_count and len(types) == 1 and 'AMBIGUOUS' not in types:
        kind = next(iter(types))
        feature_fact = fact(kind, {'ENSEMBL_GENE':'ALL_ENSEMBL_GENE_FORMAT',
                              'ENTREZ_GENE':'ALL_NUMERIC_GENE_FORMAT',
                              'GENE_SYMBOL':'ALL_HGNC_LIKE_SYMBOL_FORMAT'}[kind])
    else:
        feature_fact = blocked('FEATURE_IDENTIFIER_FORMAT_MIXED_OR_AMBIGUOUS')
    count_candidate = values_count > 0 and not invalid_values and whole_nonnegative
    rsem_candidate = values_count > 0 and not invalid_values and fractional and bool(rsem_source)
    filename_candidate = (not invalid_values and values_count > 0 and filename_unit == 'FPKM' and bool(filename_locator) and bool(paper_noncontradiction)
                          and 'FPKM' in urlsplit(filename_locator or '').path.rsplit('/', 1)[-1].upper())
    candidates = sum((count_candidate, rsem_candidate, filename_candidate))
    if candidates != 1:
        unit = blocked('UNIT_RULES_CONFLICT' if candidates > 1 else 'UNIT_RULE_NOT_ESTABLISHED')
        transform = (fact('NONE', 'LINEAR_FPKM_BY_RANGE')
                     if filename_candidate and maximum is not None and maximum > 50
                     else blocked('TRANSFORM_RULE_NOT_ESTABLISHED'))
    elif count_candidate:
        unit = fact('READ_COUNTS', 'ALL_RETAINED_VALUES_WHOLE_NONNEGATIVE')
        transform = fact('NONE', 'ALL_RETAINED_VALUES_WHOLE_NONNEGATIVE')
    elif rsem_candidate:
        unit = fact('RSEM expected counts', 'FRACTIONAL_NONNEGATIVE_VALUES_WITH_RSEM_SOURCE', source_locator=str(rsem_source))
        transform = fact('NONE', 'FRACTIONAL_NONNEGATIVE_VALUES_WITH_RSEM_SOURCE', source_locator=str(rsem_source))
    else:
        unit = fact('FPKM', 'FILENAME_PLUS_NONCONTRADICTING_PAPER', filename_locator=str(filename_locator),
                    paper_locator=str(paper_noncontradiction))
        transform = (fact('NONE', 'LINEAR_FPKM_BY_RANGE') if maximum is not None and maximum > 50
                     else blocked('TRANSFORM_RULE_NOT_ESTABLISHED'))
    return {'feature_identifier_system': feature_fact, 'unit': unit, 'transform': transform,
            'feature_count': feature_count, 'missing_cells': missing_cells,
            'genes_with_missing_cells': missing_genes,
            'gene_symbol_share': symbol_share, 'excluded_rows': excluded_rows,
            'gene_symbol_share_evidence': fact('GENE_SYMBOL_SHARE', 'GENE_SYMBOL_MAJORITY'),
            'excluded_rows_evidence': fact('EXCLUDED_ROWS', 'NONSTANDARD_ROWS_EXCLUDED'),
            'counts_evidence': fact('SOURCE_COUNTS', 'COUNT_SOURCE_MISSING_CELLS_AND_FEATURES')}


def derive_file_evidence(path: Any, *, source_sha256: str, source_format: str, delimiter: str,
                         compressed: bool, auxiliary_columns: list[dict[str, Any]] | None = None,
                         rsem_source: str | None = None, filename_unit: str | None = None,
                         filename_locator: str | None = None, paper_noncontradiction: str | None = None) -> dict[str, Any]:
    """Derive evidence only from the exact pinned file and declared matrix columns."""
    import hashlib
    from pathlib import Path
    from .matrix_header import matrix_rows
    source = Path(path)
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha256:
        raise ValueError('SOURCE_HASH_MISMATCH')
    with matrix_rows(source, delimiter=delimiter, compressed=compressed, source_format=source_format) as reader:
        header = next(reader, [])
        auxiliary = auxiliary_columns or []
        indexes = [item.get('index') for item in auxiliary]
        if (len(header) < 2 or len(indexes) != len(set(indexes)) or
                any(type(index) is not int or index <= 0 or index >= len(header) or
                    header[index] != item.get('header') for index, item in zip(indexes, auxiliary))):
            raise ValueError('MATRIX_HEADER_INVALID')
        excluded = set(indexes)
        def values() -> Iterable[tuple[str, Sequence[str]]]:
            for row in reader:
                if len(row) != len(header):
                    raise ValueError('MATRIX_ROW_WIDTH_MISMATCH')
                yield row[0], [value for index, value in enumerate(row) if index > 0 and index not in excluded]
        return derive_object_evidence(values(), source_sha256=source_sha256, rsem_source=rsem_source,
                                      filename_unit=filename_unit, filename_locator=filename_locator,
                                      paper_noncontradiction=paper_noncontradiction)
