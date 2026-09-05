"""CLI for bounded B-format inspections."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path


SCHEMA_VERSION = "1.0.0"
EXIT_ARGUMENT = 2
EXIT_SCHEMA = 3
EXIT_IO = 4

GZIP_MAGIC = b"\x1f\x8b"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
STAR_SUMMARY_IDS = {"N_unmapped", "N_multimapping", "N_noFeature", "N_ambiguous"}

ALLOWED_FORMATS = {
    "tcga-star-expression",
    "tcga-methylation-beta",
    "cpc-expression",
    "cpc-methylation",
}

TCGA_STAR_EXPECTED_HEADER = [
    "gene_id",
    "gene_name",
    "gene_type",
    "unstranded",
    "stranded_first",
    "stranded_second",
    "tpm_unstranded",
    "fpkm_unstranded",
    "fpkm_uq_unstranded",
]

CPC_EXPRESSION_ANNOTATION = [
    "GeneID",
    "Symbol_UCSC",
    "Name_UCSC",
    "Chr_UCSC",
    "Start_UCSC",
    "End_UCSC",
    "RefSeq_UCSC",
]

CPG_FIELD_RE = re.compile(r"^(?P<base>CPCG\d+)_rep(?P<rep>\d+)$")


class Failure(Exception):
    def __init__(self, message: str, code: int = EXIT_SCHEMA):
        super().__init__(message)
        self.code = code


def _forbidden_input(path: Path, source_bytes: bytes) -> None:
    lower = path.suffix.lower()
    if lower in {".gz", ".gzip", ".bgz"}:
        raise Failure(
            "input_path argument reason=compressed input rejected; provide UTF-8 TSV",
            EXIT_ARGUMENT,
        )
    if source_bytes.startswith(GZIP_MAGIC):
        raise Failure(
            "input_path argument reason=compressed input rejected (gzip bytes detected)",
            EXIT_ARGUMENT,
        )


def _validate_sha_argument(value: str) -> None:
    if not SHA256_RE.fullmatch(value):
        raise Failure("source-sha256 argument reason=malformed sha256", EXIT_ARGUMENT)


def _validate_output_path(input_path: Path, output_path: Path) -> None:
    try:
        output_exists = os.path.lexists(output_path)
        if output_exists and output_path.exists() and output_path.samefile(input_path):
            raise Failure(
                "output argument reason=output path resolves to input",
                EXIT_ARGUMENT,
            )
        if output_exists:
            raise Failure(
                "output argument reason=output path must not already exist",
                EXIT_ARGUMENT,
            )
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise Failure(f"I/O failure resolving output path {output_path}", EXIT_IO) from exc


def _parse_na_and_float(raw: str, *, row: int, field: str, strict_range: bool = False,
                        range_name: str = "beta") -> float | None:
    if raw == "NA":
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise Failure(f"row={row} field={field} reason=non-numeric token", EXIT_SCHEMA) from exc
    if not math.isfinite(value):
        raise Failure(
            f"row={row} field={field} reason=non-finite numeric token",
            EXIT_SCHEMA,
        )
    if strict_range and not (0.0 <= value <= 1.0):
        raise Failure(
            f"row={row} field={field} reason={range_name} value outside [0, 1]",
            EXIT_SCHEMA,
        )
    return value


def _require_nonempty(value: str, *, row: int, field: str) -> str:
    if not value:
        raise Failure(f"row={row} field={field} reason=empty value", EXIT_SCHEMA)
    return value


def _normalize_fields(line: str) -> list[str]:
    return line.rstrip("\r\n").split("\t")


def _inspect_tcga_star_expression(lines: list[str], *, completeness: str) -> dict:
    comment_lines: list[str] = []
    header: list[str] = []
    header_line_no: int | None = None
    data_start = 0

    for idx, raw_line in enumerate(lines, start=1):
        if raw_line.startswith("#"):
            comment_lines.append(raw_line.lstrip("#").strip())
            continue
        if raw_line == "":
            raise Failure(f"row={idx} field=record reason=blank record", EXIT_SCHEMA)
        header = _normalize_fields(raw_line)
        header_line_no = idx
        data_start = idx + 1
        break

    if not header:
        raise Failure("row=0 field=header reason=missing header line", EXIT_SCHEMA)
    if header != TCGA_STAR_EXPECTED_HEADER:
        raise Failure(
            f"row={header_line_no} field=header reason=unexpected header columns",
            EXIT_SCHEMA,
        )
    if header_line_no is None or len(lines) < header_line_no:
        raise Failure("row=0 field=record reason=header-only input", EXIT_SCHEMA)
    if len(lines) < data_start:
        raise Failure("row=0 field=record reason=header-only input", EXIT_SCHEMA)

    row_count = 0
    summary_rows = 0
    ids: set[str] = set()
    numeric_counts = {"missing": 0, "finite": 0}
    summary_structural_missing = 0
    summary_missing = 0
    summary_finite = 0

    for row_no in range(data_start, len(lines) + 1):
        line = lines[row_no - 1]
        if line == "":
            raise Failure(f"row={row_no} field=record reason=blank record", EXIT_SCHEMA)
        row_count += 1
        fields = _normalize_fields(line)
        if len(fields) != len(header):
            raise Failure(
                f"row={row_no} field=column_count reason=wrong number of columns",
                EXIT_SCHEMA,
            )
        gene_id = _require_nonempty(fields[0], row=row_no, field="gene_id")
        if gene_id in ids:
            raise Failure(
                f"row={row_no} field=gene_id reason=duplicate identifier",
                EXIT_SCHEMA,
            )
        ids.add(gene_id)
        if gene_id.startswith("N_"):
            if gene_id not in STAR_SUMMARY_IDS:
                raise Failure(f"row={row_no} field=gene_id reason=unknown STAR summary record", EXIT_SCHEMA)
            summary_rows += 1
            for col_index in range(3, len(header)):
                value = fields[col_index]
                if col_index >= 6 and value == "":
                    summary_structural_missing += 1
                else:
                    parsed = _parse_na_and_float(
                        value,
                        row=row_no,
                        field=header[col_index],
                        strict_range=False,
                    )
                    if parsed is None:
                        summary_missing += 1
                    else:
                        summary_finite += 1
            continue
        for col_index in range(3, len(header)):
            parsed = _parse_na_and_float(
                fields[col_index],
                row=row_no,
                field=header[col_index],
                strict_range=False,
            )
            if parsed is None:
                numeric_counts["missing"] += 1
            else:
                numeric_counts["finite"] += 1

    return {
        "format": "tcga-star-expression",
        "completeness": completeness,
        "comment_lines": comment_lines,
        "header_repaired": False,
        "row_count": row_count,
        "summary_record_count": summary_rows,
        "identifier_count": len(ids) - summary_rows,
        "numeric_field_count": len(header) - 3,
        "finite_value_count": numeric_counts["finite"],
        "missing_value_count": numeric_counts["missing"],
        "summary_structural_missing_count": summary_structural_missing,
        "summary_missing_value_count": summary_missing,
        "summary_finite_value_count": summary_finite,
    }


def _inspect_tcga_methylation(lines: list[str], *, completeness: str) -> dict:
    if not lines:
        raise Failure("row=0 field=record reason=header-only input", EXIT_SCHEMA)
    ids: set[str] = set()
    row_count = 0
    finite_count = 0
    missing_count = 0
    cg_rows = {"cg": 0, "ch": 0, "other": 0}

    for row_idx, raw_line in enumerate(lines, start=1):
        if raw_line == "":
            raise Failure(f"row={row_idx} field=record reason=blank record", EXIT_SCHEMA)
        fields = _normalize_fields(raw_line)
        if len(fields) != 2:
            raise Failure(
                f"row={row_idx} field=column_count reason=wrong number of columns",
                EXIT_SCHEMA,
            )
        probe_id = _require_nonempty(fields[0], row=row_idx, field="probe_id")
        if probe_id in ids:
            raise Failure(
                f"row={row_idx} field=probe_id reason=duplicate identifier",
                EXIT_SCHEMA,
            )
        ids.add(probe_id)
        if probe_id.startswith("cg"):
            cg_rows["cg"] += 1
        elif probe_id.startswith("ch"):
            cg_rows["ch"] += 1
        else:
            cg_rows["other"] += 1
        row_count += 1
        value = _parse_na_and_float(fields[1], row=row_idx, field="beta", strict_range=True)
        if value is None:
            missing_count += 1
        else:
            finite_count += 1

    return {
        "format": "tcga-methylation-beta",
        "completeness": completeness,
        "header_repaired": False,
        "row_count": row_count,
        "identifier_count": len(ids),
        "sample_count": 1,
        "finite_value_count": finite_count,
        "missing_value_count": missing_count,
        "value_columns": 1,
        "probe_class_counts": cg_rows,
    }


def _inspect_cpc_expression(lines: list[str], *, completeness: str) -> dict:
    if not lines:
        raise Failure("row=0 field=header reason=missing header", EXIT_SCHEMA)
    header = _normalize_fields(lines[0])
    if len(header) < 8:
        raise Failure("row=1 field=header reason=invalid column count", EXIT_SCHEMA)
    if len(lines) == 1:
        raise Failure("row=0 field=record reason=header-only input", EXIT_SCHEMA)
    if header[:7] != CPC_EXPRESSION_ANNOTATION:
        raise Failure("row=1 field=header reason=unexpected annotation header", EXIT_SCHEMA)

    expected_fields = len(header)
    annotation_fields = 7
    sample_fields = expected_fields - annotation_fields
    sample_columns = header[annotation_fields:]

    if sample_fields == 0:
        raise Failure("row=1 field=header reason=no sample columns", EXIT_SCHEMA)
    if any(not column for column in sample_columns):
        raise Failure("row=1 field=header reason=empty sample column", EXIT_SCHEMA)
    if len(set(sample_columns)) != len(sample_columns):
        raise Failure("row=1 field=header reason=duplicate sample columns", EXIT_SCHEMA)

    row_count = 0
    ids: set[str] = set()
    finite_count = 0
    missing_count = 0

    for row_idx, raw_line in enumerate(lines[1:], start=2):
        if raw_line == "":
            raise Failure(f"row={row_idx} field=record reason=blank record", EXIT_SCHEMA)
        fields = _normalize_fields(raw_line)
        row_count += 1
        if len(fields) != expected_fields:
            raise Failure(
                f"row={row_idx} field=column_count reason=wrong number of columns",
                EXIT_SCHEMA,
            )
        identifier = _require_nonempty(fields[0], row=row_idx, field="GeneID")
        if identifier in ids:
            raise Failure(
                f"row={row_idx} field=GeneID reason=duplicate identifier",
                EXIT_SCHEMA,
            )
        ids.add(identifier)
        for raw_name, raw_value in zip(sample_columns, fields[annotation_fields:]):
            value = _parse_na_and_float(raw_value, row=row_idx, field=raw_name, strict_range=False)
            if value is None:
                missing_count += 1
            else:
                finite_count += 1

    return {
        "format": "cpc-expression",
        "completeness": completeness,
        "header_repaired": False,
        "row_count": row_count,
        "sample_count": sample_fields,
        "annotation_field_count": annotation_fields,
        "identifier_count": len(ids),
        "finite_value_count": finite_count,
        "missing_value_count": missing_count,
    }


def _inspect_cpc_methylation(lines: list[str], *, completeness: str) -> dict:
    if not lines:
        raise Failure("row=0 field=header reason=missing header", EXIT_SCHEMA)
    if len(lines) == 1:
        raise Failure("row=0 field=record reason=header-only input", EXIT_SCHEMA)
    raw_header = _normalize_fields(lines[0])
    if not raw_header or all(not field for field in raw_header):
        raise Failure("row=1 field=header reason=empty header", EXIT_SCHEMA)

    detected_header_repair = False
    if raw_header[0] == "probe_id":
        if len(raw_header) % 2 != 1:
            raise Failure(
                "row=1 field=header reason=invalid cpc methylation header width",
                EXIT_SCHEMA,
            )
        header = raw_header
    else:
        if len(raw_header) % 2 != 0:
            raise Failure(
                "row=1 field=header reason=invalid cpc methylation header width",
                EXIT_SCHEMA,
            )
        header = ["probe_id"] + raw_header
        detected_header_repair = True

    if len(header) <= 1 or (len(header) - 1) % 2 != 0:
        raise Failure("row=1 field=header reason=invalid cpc methylation header width", EXIT_SCHEMA)

    expected_fields = len(header)
    pair_count = (expected_fields - 1) // 2
    beta_columns = pair_count
    detection_columns = pair_count

    sample_codes = set[str]()
    beta_seen = set[str]()
    detection_seen = set[str]()

    for col_idx in range(1, expected_fields, 2):
        beta_field = header[col_idx]
        detection_field = header[col_idx + 1] if col_idx + 1 < expected_fields else None
        if not beta_field or detection_field is None:
            raise Failure(
                "row=1 field=header reason=odd cpc methylation field count",
                EXIT_SCHEMA,
            )
        if beta_field in beta_seen or detection_field in detection_seen:
            raise Failure(
                "row=1 field=header reason=duplicate assay columns",
                EXIT_SCHEMA,
            )
        beta_seen.add(beta_field)
        detection_seen.add(detection_field)

        expected_detection = f"{beta_field}_Dectection_Pval"
        if detection_field != expected_detection:
            raise Failure(
                "row=1 field=header reason=unpaired beta/detection columns",
                EXIT_SCHEMA,
            )
        match = CPG_FIELD_RE.match(beta_field)
        if not match:
            raise Failure(
                "row=1 field=header reason=invalid sample pair code",
                EXIT_SCHEMA,
            )
        sample_codes.add(match.group("base"))

    row_count = 0
    ids: set[str] = set()
    beta_missing = 0
    beta_finite = 0
    detection_missing = 0
    detection_finite = 0

    for row_idx, raw_line in enumerate(lines[1:], start=2):
        if raw_line == "":
            raise Failure(f"row={row_idx} field=record reason=blank record", EXIT_SCHEMA)
        fields = _normalize_fields(raw_line)
        row_count += 1
        if len(fields) != expected_fields:
            raise Failure(
                f"row={row_idx} field=column_count reason=wrong number of columns",
                EXIT_SCHEMA,
            )
        probe_id = _require_nonempty(fields[0], row=row_idx, field="probe_id")
        if probe_id in ids:
            raise Failure(
                f"row={row_idx} field=probe_id reason=duplicate identifier",
                EXIT_SCHEMA,
            )
        ids.add(probe_id)

        for field_idx in range(1, expected_fields):
            raw_name = header[field_idx]
            raw_value = fields[field_idx]
            value = _parse_na_and_float(
                raw_value,
                row=row_idx,
                field=raw_name,
                strict_range=True,
                range_name="beta" if field_idx % 2 else "detection-P",
            )
            if value is None:
                if (field_idx % 2) == 1:
                    beta_missing += 1
                else:
                    detection_missing += 1
            else:
                if (field_idx % 2) == 1:
                    beta_finite += 1
                else:
                    detection_finite += 1

    return {
        "format": "cpc-methylation",
        "completeness": completeness,
        "detected_header_repair": detected_header_repair,
        "header_repaired": detected_header_repair,
        "header_repair_action": "prepended missing leading probe_id column" if detected_header_repair else "none",
        "row_count": row_count,
        "sample_pair_count": pair_count,
        "value_columns": beta_columns + detection_columns,
        "beta_columns": beta_columns,
        "detection_pval_columns": detection_columns,
        "sample_code_count": len(sample_codes),
        "identifier_count": len(ids),
        "beta_finite_value_count": beta_finite,
        "beta_missing_value_count": beta_missing,
        "detection_finite_value_count": detection_finite,
        "detection_missing_value_count": detection_missing,
        "finite_value_count": beta_finite + detection_finite,
        "missing_value_count": beta_missing + detection_missing,
    }


def _load_lines(source_bytes: bytes) -> list[str]:
    try:
        return source_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise Failure("input file must be UTF-8 encoded", EXIT_SCHEMA) from exc


def _build_summary(payload: dict, actual_bytes: int, actual_sha256: str, completeness: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "tools.b_formats.inspect",
        "format": payload["format"],
        "supplied_completeness": completeness,
        "actual_bytes": actual_bytes,
        "source_sha256": actual_sha256,
        "actual_source_sha256": actual_sha256,
        "no_biological_validation": "format-only inspection; no assay values logged; no modeling",
        "detected_header_repair": bool(payload.get("detected_header_repair") or payload.get("header_repaired")),
        "row_count": payload.get("row_count"),
        "identifier_count": payload.get("identifier_count"),
        "sample_count": payload.get("sample_count"),
        "finite_value_count": payload.get("finite_value_count"),
        "missing_value_count": payload.get("missing_value_count"),
        "summary_record_count": payload.get("summary_record_count"),
        "format_summary": payload,
    }


def _assert_sha(source_bytes: bytes, expected_sha256: str) -> str:
    observed = hashlib.sha256(source_bytes).hexdigest()
    if observed.lower() != expected_sha256.lower():
        raise Failure(
            f"row=0 field=source-sha256 reason=hash mismatch supplied={expected_sha256.lower()} actual={observed}",
            EXIT_SCHEMA,
        )
    return observed


def _atomic_write_json(path: Path, payload: dict) -> None:
    out_dir = path.parent
    temp_name: str | None = None
    fd: int | None = None
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=".b_formats_", suffix=".json", dir=str(out_dir)
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Publish the completed file atomically without replacing another writer.
        # The temporary file shares the destination directory/filesystem.
        try:
            if os.name == "nt":
                # Windows rename refuses an existing destination. Unlike hard
                # links, it also works on the project's mounted E: filesystem.
                os.rename(temp_name, path)
            else:
                os.link(temp_name, path)
        except FileExistsError as exc:
            raise Failure("output argument reason=output path must not already exist", EXIT_ARGUMENT) from exc
    except OSError as exc:
        raise Failure(f"I/O failure writing output {path}", EXIT_IO) from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def run_inspect(
    input_path: Path,
    source_sha256: str,
    completeness: str,
    output_path: Path,
    format_name: str,
) -> int:
    _validate_sha_argument(source_sha256)
    _validate_output_path(input_path, output_path)
    if completeness not in {"full", "bounded-prefix"}:
        raise Failure("completeness must be full or bounded-prefix", EXIT_ARGUMENT)

    try:
        source_bytes = input_path.read_bytes()
    except OSError as exc:
        raise Failure(f"I/O failure reading {input_path}", EXIT_IO) from exc
    _forbidden_input(input_path, source_bytes)
    actual_bytes = len(source_bytes)
    actual_sha256 = _assert_sha(source_bytes, source_sha256)
    lines = _load_lines(source_bytes)

    if format_name == "tcga-star-expression":
        payload = _inspect_tcga_star_expression(lines, completeness=completeness)
    elif format_name == "tcga-methylation-beta":
        payload = _inspect_tcga_methylation(lines, completeness=completeness)
    elif format_name == "cpc-expression":
        payload = _inspect_cpc_expression(lines, completeness=completeness)
    elif format_name == "cpc-methylation":
        payload = _inspect_cpc_methylation(lines, completeness=completeness)
    else:
        raise Failure(f"unsupported format {format_name}", EXIT_ARGUMENT)

    summary = _build_summary(payload, actual_bytes, actual_sha256, completeness)
    _atomic_write_json(output_path, summary)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect bounded B-format files.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--format", required=True, choices=sorted(ALLOWED_FORMATS))
    inspect_parser.add_argument("--input", required=True, type=Path)
    inspect_parser.add_argument("--source-sha256", required=True)
    inspect_parser.add_argument(
        "--completeness",
        required=True,
        choices=["full", "bounded-prefix"],
    )
    inspect_parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return run_inspect(
            input_path=args.input,
            source_sha256=args.source_sha256,
            completeness=args.completeness,
            output_path=args.output,
            format_name=args.format,
        )
    except Failure as exc:
        print(f"{exc}", file=sys.stderr)
        return exc.code
    except Exception as exc:  # pragma: no cover
        print(f"unexpected_error={exc}", file=sys.stderr)
        return EXIT_SCHEMA


if __name__ == "__main__":
    raise SystemExit(main())
