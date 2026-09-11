from __future__ import annotations

import gzip
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

import pandas as pd


def resolve_primary_expression_path(
    cohort_id: str,
    expression_manifest: Path,
    downloads_root: Path,
) -> Path | None:
    if not expression_manifest.exists():
        return None
    df = pd.read_csv(expression_manifest, sep="\t", dtype=str).fillna("")
    match = df.loc[df["cohort_id"] == cohort_id]
    if match.empty:
        return None
    row = match.iloc[0]
    rel = (row.get("primary_expression_file", "") or "").strip()
    if not rel:
        return None
    rel_path = Path(rel)
    if rel_path.is_absolute():
        return rel_path
    downloads_folder = (row.get("downloads_folder", "") or "").strip()
    folder = downloads_folder or cohort_id
    preferred = downloads_root / folder / rel
    if preferred.exists():
        return preferred

    # Backward/repair fallback: some manifests store paths relative to
    # downloads_root directly rather than downloads_folder.
    direct = downloads_root / rel
    if direct.exists():
        return direct

    # Final fallback: if exactly one file under downloads_root matches the
    # expected basename, use it (avoids hard-failing on folder-renamed cohorts).
    basename = rel_path.name
    if basename:
        matches = sorted(downloads_root.rglob(basename))
        if len(matches) == 1:
            return matches[0]

    return preferred


def load_expression_matrix(path: Path) -> pd.DataFrame | None:
    if not path or not path.exists():
        return None
    name = path.name.lower()
    if "series_matrix" in name:
        table = _read_series_matrix_table(path)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        table = _read_excel(path)
    else:
        table = _read_table(path)
    if table is None or table.empty:
        return None
    table = _coerce_expression_table(table)
    if table.empty:
        return None
    return table


def load_series_matrix_annotations(path: Path) -> dict[str, dict[str, str]]:
    if not path or not path.exists():
        return {}
    data: dict[str, dict[str, str]] = {}
    for row in _read_series_matrix_annotations(path):
        sample_id = row.get("sample_id", "")
        if sample_id:
            data[sample_id] = row
    return data


def infer_tumor_adjacent_group(annotation: dict[str, str]) -> str | None:
    text = " ".join(
        [
            annotation.get("source_name_ch1", ""),
            annotation.get("characteristics_ch1", ""),
            annotation.get("title", ""),
        ]
    ).lower()
    if any(tok in text for tok in ["adjacent", "nontumor", "normal", "para-tumor"]):
        return "adjacent"
    if any(tok in text for tok in ["tumor", "cancer", "carcinoma", "hcc"]):
        return "tumor"
    return None


def _read_excel(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_excel(path)
    except Exception:
        if path.name.lower().endswith(".xlsx"):
            return _read_xlsx_zip(path)
        return None


def _read_xlsx_zip(path: Path) -> pd.DataFrame | None:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    try:
        with ZipFile(path) as zf:
            shared_strings = _read_xlsx_shared_strings(zf, ns)
            sheet_names = sorted(
                (
                    name
                    for name in zf.namelist()
                    if re.match(r"^xl/worksheets/sheet\d+\.xml$", name)
                ),
                key=lambda value: int(re.search(r"sheet(\d+)\.xml$", value).group(1)),
            )
            best: pd.DataFrame | None = None
            best_score = -1
            for sheet_name in sheet_names:
                rows = _read_xlsx_sheet_rows(zf, sheet_name, shared_strings, ns)
                if len(rows) < 2:
                    continue
                width = max(len(row) for row in rows)
                if width < 2:
                    continue
                padded = [row + [""] * (width - len(row)) for row in rows]
                header = [str(value) for value in padded[0]]
                df = pd.DataFrame(padded[1:], columns=header)
                coerced = _coerce_expression_table(df)
                score = int(coerced.shape[0] * coerced.shape[1])
                if score > best_score:
                    best = df
                    best_score = score
            return best
    except Exception:
        return None
    return None


def _read_xlsx_shared_strings(zf: ZipFile, ns: dict[str, str]) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("x:si", ns):
        parts = [node.text or "" for node in item.findall(".//x:t", ns)]
        values.append("".join(parts))
    return values


def _read_xlsx_sheet_rows(
    zf: ZipFile,
    sheet_name: str,
    shared_strings: list[str],
    ns: dict[str, str],
) -> list[list[str]]:
    root = ET.fromstring(zf.read(sheet_name))
    rows: list[list[str]] = []
    for row_node in root.findall(".//x:sheetData/x:row", ns):
        row: list[str] = []
        for cell in row_node.findall("x:c", ns):
            col_idx = _xlsx_cell_col_index(cell.attrib.get("r", ""))
            while len(row) <= col_idx:
                row.append("")
            row[col_idx] = _xlsx_cell_value(cell, shared_strings, ns)
        rows.append(row)
    return rows


def _xlsx_cell_col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    if not letters:
        return 0
    idx = 0
    for ch in letters.upper():
        idx = idx * 26 + ord(ch) - ord("A") + 1
    return idx - 1


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t", "")
    value_node = cell.find("x:v", ns)
    value = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s" and value:
        try:
            return shared_strings[int(value)]
        except (IndexError, ValueError):
            return ""
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//x:t", ns))
    return value


def _read_table(path: Path) -> pd.DataFrame | None:
    def _open(p: Path):
        if p.suffix == ".gz":
            return gzip.open(p, "rt", encoding="utf-8", errors="replace")
        return p.open("r", encoding="utf-8", errors="replace")

    # Try common delimiters; some GEO CSV exports use semicolons.
    for sep in ("\t", ",", ";"):
        try:
            with _open(path) as fh:
                df = pd.read_csv(fh, sep=sep)
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue
    return None


def _read_series_matrix_table(path: Path) -> pd.DataFrame | None:
    lines: list[str] = []
    in_table = False
    for line in _iter_text_lines(path):
        marker = line.strip().lstrip("\ufeff").strip().lower()
        if marker.startswith("!series_matrix_table_begin"):
            in_table = True
            continue
        if marker.startswith("!series_matrix_table_end"):
            break
        if in_table:
            lines.append(line)
    if not lines:
        return None
    content = "".join(lines)
    # Some GEO tables include extra quoted header fields or ragged rows.
    # Parse defensively with multiple engines and skip malformed lines.
    parsers = [
        {"sep": "\t", "engine": "python"},
        {"sep": r"\t+|\s{2,}", "engine": "python"},
        {"sep": "\t", "engine": "c"},
    ]
    for kwargs in parsers:
        try:
            df = pd.read_csv(
                io.StringIO(content),
                on_bad_lines="skip",
                **kwargs,
            )
            if df is not None and not df.empty and df.shape[1] >= 2:
                return df
        except Exception:
            continue
    return None


def _read_series_matrix_annotations(path: Path) -> Iterable[dict[str, str]]:
    header_fields: dict[str, list[str]] = {}
    for line in _iter_text_lines(path):
        marker = line.strip().lstrip("\ufeff").strip().lower()
        if marker.startswith("!series_matrix_table_begin"):
            break
        line_norm = line.lstrip("\ufeff").lstrip()
        if not line_norm.startswith("!Sample_"):
            continue
        key, _, rest = line_norm.partition("=")
        key = key.replace("!Sample_", "").strip()
        values = [v.strip() for v in rest.strip().split("\t") if v.strip()]
        header_fields[key] = values

    accessions = header_fields.get("geo_accession", [])
    titles = header_fields.get("title", [])
    sources = header_fields.get("source_name_ch1", [])
    characteristics = header_fields.get("characteristics_ch1", [])

    rows = []
    for idx, sample_id in enumerate(accessions):
        rows.append(
            {
                "sample_id": sample_id,
                "title": titles[idx] if idx < len(titles) else "",
                "source_name_ch1": sources[idx] if idx < len(sources) else "",
                "characteristics_ch1": characteristics[idx] if idx < len(characteristics) else "",
            }
        )
    return rows


def _iter_text_lines(path: Path) -> Iterable[str]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line
    else:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line


def _coerce_expression_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    first_col = df.columns[0]
    df.rename(columns={first_col: "feature_id"}, inplace=True)
    df = df.set_index("feature_id")
    df = pd.DataFrame(
        {
            column: [_coerce_numeric_value(value) for value in df[column].to_numpy(dtype=object, copy=False)]
            for column in df.columns
        },
        index=df.index,
    )
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    return df


def _coerce_numeric_value(value: object) -> float:
    if value is None:
        return float("nan")
    try:
        if pd.isna(value):
            return float("nan")
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        value = value.strip().strip('"')
        if not value:
            return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
