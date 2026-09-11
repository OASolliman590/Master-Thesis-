"""Record-level parsers for the four bounded Paper B assay formats.

These functions yield typed assay records. They do not treat B-F1 summary JSON
as biological data and they do not choose specimens, scores or eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.b_formats.__main__ import (
    CPC_EXPRESSION_ANNOTATION,
    CPG_FIELD_RE,
    Failure,
    STAR_SUMMARY_IDS,
    TCGA_STAR_EXPECTED_HEADER,
    _load_lines,
    _normalize_fields,
    _parse_na_and_float,
    _require_nonempty,
)


@dataclass(frozen=True)
class ExpressionRecord:
    assay_id: str
    raw_gene_id: str
    symbol: str
    value: float | None
    abundance_type: str
    annotation_release: str
    source_missing_token: str | None


@dataclass(frozen=True)
class MethylationRecord:
    assay_id: str
    probe_id: str
    beta: float | None
    detection_p: float | None
    source_missing_token: str | None


@dataclass(frozen=True)
class ParsedStarExpression:
    format_name: str
    comment_lines: tuple[str, ...]
    summary_gene_ids: tuple[str, ...]
    records: tuple[ExpressionRecord, ...]
    header_repaired: bool


@dataclass(frozen=True)
class ParsedMatrixExpression:
    format_name: str
    sample_assay_ids: tuple[str, ...]
    annotation_fields: tuple[str, ...]
    records: tuple[ExpressionRecord, ...]
    header_repaired: bool


@dataclass(frozen=True)
class ParsedSingleMethylation:
    format_name: str
    records: tuple[MethylationRecord, ...]
    header_repaired: bool
    first_probe_id: str


@dataclass(frozen=True)
class ParsedPairedMethylation:
    format_name: str
    sample_assay_ids: tuple[str, ...]
    header_repaired: bool
    header_repair_action: str
    records: tuple[MethylationRecord, ...]


def parse_tcga_star_expression(
    source_bytes: bytes,
    *,
    assay_id: str,
    annotation_release: str,
    abundance_type: str = "tpm_unstranded",
) -> ParsedStarExpression:
    if not assay_id:
        raise Failure("assay_id argument reason=empty", 2)
    lines = _load_lines(source_bytes)
    comment_lines: list[str] = []
    header: list[str] = []
    header_line_no: int | None = None
    data_start = 0
    for idx, raw_line in enumerate(lines, start=1):
        if raw_line.startswith("#"):
            comment_lines.append(raw_line.lstrip("#").strip())
            continue
        if raw_line == "":
            raise Failure(f"row={idx} field=record reason=blank record", 3)
        header = _normalize_fields(raw_line)
        header_line_no = idx
        data_start = idx + 1
        break
    if not header:
        raise Failure("row=0 field=header reason=missing header line", 3)
    if header != TCGA_STAR_EXPECTED_HEADER:
        raise Failure(
            f"row={header_line_no} field=header reason=unexpected header columns",
            3,
        )
    if abundance_type not in header:
        raise Failure(
            f"row={header_line_no} field=abundance_type reason=named column missing:{abundance_type}",
            3,
        )
    value_index = header.index(abundance_type)
    records: list[ExpressionRecord] = []
    summary_ids: list[str] = []
    seen: set[str] = set()
    for row_no in range(data_start, len(lines) + 1):
        line = lines[row_no - 1]
        if line == "":
            raise Failure(f"row={row_no} field=record reason=blank record", 3)
        fields = _normalize_fields(line)
        if len(fields) != len(header):
            raise Failure(
                f"row={row_no} field=column_count reason=wrong number of columns",
                3,
            )
        gene_id = _require_nonempty(fields[0], row=row_no, field="gene_id")
        if gene_id in seen:
            raise Failure(f"row={row_no} field=gene_id reason=duplicate identifier", 3)
        seen.add(gene_id)
        if gene_id.startswith("N_"):
            if gene_id not in STAR_SUMMARY_IDS:
                raise Failure(
                    f"row={row_no} field=gene_id reason=unknown STAR summary record",
                    3,
                )
            summary_ids.append(gene_id)
            continue
        raw_value = fields[value_index]
        token = raw_value if raw_value == "NA" else None
        value = _parse_na_and_float(raw_value, row=row_no, field=abundance_type)
        records.append(
            ExpressionRecord(
                assay_id=assay_id,
                raw_gene_id=gene_id,
                symbol=fields[1],
                value=value,
                abundance_type=abundance_type,
                annotation_release=annotation_release,
                source_missing_token=token,
            )
        )
    return ParsedStarExpression(
        format_name="tcga-star-expression",
        comment_lines=tuple(comment_lines),
        summary_gene_ids=tuple(summary_ids),
        records=tuple(records),
        header_repaired=False,
    )


def parse_cpc_expression(
    source_bytes: bytes,
    *,
    annotation_release: str,
    abundance_type: str = "author-processed-expression",
) -> ParsedMatrixExpression:
    lines = _load_lines(source_bytes)
    if not lines:
        raise Failure("row=0 field=header reason=missing header", 3)
    header = _normalize_fields(lines[0])
    if len(header) < 8:
        raise Failure("row=1 field=header reason=invalid column count", 3)
    if len(lines) == 1:
        raise Failure("row=0 field=record reason=header-only input", 3)
    if header[:7] != CPC_EXPRESSION_ANNOTATION:
        raise Failure("row=1 field=header reason=unexpected annotation header", 3)
    sample_columns = header[7:]
    if not sample_columns:
        raise Failure("row=1 field=header reason=no sample columns", 3)
    if any(not column for column in sample_columns):
        raise Failure("row=1 field=header reason=empty sample column", 3)
    if len(set(sample_columns)) != len(sample_columns):
        raise Failure("row=1 field=header reason=duplicate sample columns", 3)
    records: list[ExpressionRecord] = []
    seen: set[str] = set()
    for row_idx, raw_line in enumerate(lines[1:], start=2):
        if raw_line == "":
            raise Failure(f"row={row_idx} field=record reason=blank record", 3)
        fields = _normalize_fields(raw_line)
        if len(fields) != len(header):
            raise Failure(
                f"row={row_idx} field=column_count reason=wrong number of columns",
                3,
            )
        gene_id = _require_nonempty(fields[0], row=row_idx, field="GeneID")
        if gene_id in seen:
            raise Failure(f"row={row_idx} field=GeneID reason=duplicate identifier", 3)
        seen.add(gene_id)
        symbol = fields[1]
        for assay_id, raw_value in zip(sample_columns, fields[7:]):
            token = raw_value if raw_value == "NA" else None
            value = _parse_na_and_float(raw_value, row=row_idx, field=assay_id)
            records.append(
                ExpressionRecord(
                    assay_id=assay_id,
                    raw_gene_id=gene_id,
                    symbol=symbol,
                    value=value,
                    abundance_type=abundance_type,
                    annotation_release=annotation_release,
                    source_missing_token=token,
                )
            )
    return ParsedMatrixExpression(
        format_name="cpc-expression",
        sample_assay_ids=tuple(sample_columns),
        annotation_fields=tuple(CPC_EXPRESSION_ANNOTATION),
        records=tuple(records),
        header_repaired=False,
    )


def parse_tcga_methylation(
    source_bytes: bytes,
    *,
    assay_id: str,
) -> ParsedSingleMethylation:
    if not assay_id:
        raise Failure("assay_id argument reason=empty", 2)
    lines = _load_lines(source_bytes)
    if not lines:
        raise Failure("row=0 field=record reason=header-only input", 3)
    records: list[MethylationRecord] = []
    seen: set[str] = set()
    first_probe_id = ""
    for row_idx, raw_line in enumerate(lines, start=1):
        if raw_line == "":
            raise Failure(f"row={row_idx} field=record reason=blank record", 3)
        fields = _normalize_fields(raw_line)
        if len(fields) != 2:
            raise Failure(
                f"row={row_idx} field=column_count reason=wrong number of columns",
                3,
            )
        probe_id = _require_nonempty(fields[0], row=row_idx, field="probe_id")
        if probe_id in seen:
            raise Failure(f"row={row_idx} field=probe_id reason=duplicate identifier", 3)
        seen.add(probe_id)
        if row_idx == 1:
            first_probe_id = probe_id
        raw_value = fields[1]
        token = raw_value if raw_value == "NA" else None
        beta = _parse_na_and_float(
            raw_value, row=row_idx, field="beta", strict_range=True
        )
        records.append(
            MethylationRecord(
                assay_id=assay_id,
                probe_id=probe_id,
                beta=beta,
                detection_p=None,
                source_missing_token=token,
            )
        )
    return ParsedSingleMethylation(
        format_name="tcga-methylation-beta",
        records=tuple(records),
        header_repaired=False,
        first_probe_id=first_probe_id,
    )


def parse_cpc_methylation(source_bytes: bytes) -> ParsedPairedMethylation:
    lines = _load_lines(source_bytes)
    if not lines:
        raise Failure("row=0 field=header reason=missing header", 3)
    if len(lines) == 1:
        raise Failure("row=0 field=record reason=header-only input", 3)
    raw_header = _normalize_fields(lines[0])
    if not raw_header or all(not field for field in raw_header):
        raise Failure("row=1 field=header reason=empty header", 3)
    detected_header_repair = False
    if raw_header[0] == "probe_id":
        if len(raw_header) % 2 != 1:
            raise Failure(
                "row=1 field=header reason=invalid cpc methylation header width",
                3,
            )
        header = raw_header
    else:
        if len(raw_header) % 2 != 0:
            raise Failure(
                "row=1 field=header reason=invalid cpc methylation header width",
                3,
            )
        header = ["probe_id"] + raw_header
        detected_header_repair = True
    if len(header) <= 1 or (len(header) - 1) % 2 != 0:
        raise Failure("row=1 field=header reason=invalid cpc methylation header width", 3)
    expected_fields = len(header)
    assay_ids: list[str] = []
    beta_seen: set[str] = set()
    detection_seen: set[str] = set()
    for col_idx in range(1, expected_fields, 2):
        beta_field = header[col_idx]
        detection_field = header[col_idx + 1]
        if not beta_field:
            raise Failure("row=1 field=header reason=odd cpc methylation field count", 3)
        if beta_field in beta_seen or detection_field in detection_seen:
            raise Failure("row=1 field=header reason=duplicate assay columns", 3)
        beta_seen.add(beta_field)
        detection_seen.add(detection_field)
        expected_detection = f"{beta_field}_Dectection_Pval"
        if detection_field != expected_detection:
            raise Failure(
                "row=1 field=header reason=unpaired beta/detection columns",
                3,
            )
        if not CPG_FIELD_RE.match(beta_field):
            raise Failure("row=1 field=header reason=invalid sample pair code", 3)
        assay_ids.append(beta_field)
    records: list[MethylationRecord] = []
    seen: set[str] = set()
    for row_idx, raw_line in enumerate(lines[1:], start=2):
        if raw_line == "":
            raise Failure(f"row={row_idx} field=record reason=blank record", 3)
        fields = _normalize_fields(raw_line)
        if len(fields) != expected_fields:
            raise Failure(
                f"row={row_idx} field=column_count reason=wrong number of columns",
                3,
            )
        probe_id = _require_nonempty(fields[0], row=row_idx, field="probe_id")
        if probe_id in seen:
            raise Failure(f"row={row_idx} field=probe_id reason=duplicate identifier", 3)
        seen.add(probe_id)
        for pair_index, assay_id in enumerate(assay_ids):
            beta_idx = 1 + pair_index * 2
            p_idx = beta_idx + 1
            raw_beta = fields[beta_idx]
            raw_p = fields[p_idx]
            beta_token = raw_beta if raw_beta == "NA" else None
            p_token = raw_p if raw_p == "NA" else None
            beta = _parse_na_and_float(
                raw_beta, row=row_idx, field=assay_id, strict_range=True
            )
            detection_p = _parse_na_and_float(
                raw_p,
                row=row_idx,
                field=f"{assay_id}_Dectection_Pval",
                strict_range=True,
                range_name="detection-P",
            )
            missing_token = beta_token or p_token
            records.append(
                MethylationRecord(
                    assay_id=assay_id,
                    probe_id=probe_id,
                    beta=beta,
                    detection_p=detection_p,
                    source_missing_token=missing_token,
                )
            )
    action = (
        "prepended missing leading probe_id column" if detected_header_repair else "none"
    )
    return ParsedPairedMethylation(
        format_name="cpc-methylation",
        sample_assay_ids=tuple(assay_ids),
        header_repaired=detected_header_repair,
        header_repair_action=action,
        records=tuple(records),
    )


def parse_assay_bytes(
    format_name: str,
    source_bytes: bytes,
    *,
    assay_id: str | None = None,
    annotation_release: str = "synthetic-fixture-v1",
    abundance_type: str | None = None,
) -> Any:
    if format_name == "tcga-star-expression":
        if assay_id is None:
            raise Failure("assay_id required for tcga-star-expression", 2)
        kwargs = {"assay_id": assay_id, "annotation_release": annotation_release}
        if abundance_type:
            kwargs["abundance_type"] = abundance_type
        return parse_tcga_star_expression(source_bytes, **kwargs)
    if format_name == "cpc-expression":
        kwargs = {"annotation_release": annotation_release}
        if abundance_type:
            kwargs["abundance_type"] = abundance_type
        return parse_cpc_expression(source_bytes, **kwargs)
    if format_name == "tcga-methylation-beta":
        if assay_id is None:
            raise Failure("assay_id required for tcga-methylation-beta", 2)
        return parse_tcga_methylation(source_bytes, assay_id=assay_id)
    if format_name == "cpc-methylation":
        return parse_cpc_methylation(source_bytes)
    raise Failure(f"unsupported format {format_name}", 2)
