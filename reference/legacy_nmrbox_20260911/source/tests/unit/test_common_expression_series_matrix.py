from __future__ import annotations

import gzip
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from src.pipeline.common.expression import (
    _coerce_expression_table,
    _read_series_matrix_table,
    load_expression_matrix,
    load_series_matrix_annotations,
)


def _write_matrix(path: Path, lines: list[str]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("".join(lines))


def test_read_series_matrix_table_tolerates_marker_whitespace_and_ragged_rows(tmp_path: Path) -> None:
    matrix_path = tmp_path / "GSE202069_series_matrix.txt.gz"
    _write_matrix(
        matrix_path,
        [
            "!Series_title\t\"Example\"\n",
            "   !series_matrix_table_begin   \n",
            '"ID_REF"\t"GSM1"\t"GSM2"\n',
            '"GENE_A"\t"10"\t"20"\n',
            # Ragged row: parser should skip this without failing the table load.
            '"GENE_B"\t"30"\n',
            '"GENE_C"\t"40"\t"50"\n',
            " !series_matrix_table_end\n",
        ],
    )

    df = _read_series_matrix_table(matrix_path)
    assert df is not None
    assert df.shape[1] >= 2
    values = {str(v) for v in df.iloc[:, 0].astype(str).tolist()}
    assert "GENE_A" in values
    assert "GENE_C" in values


def test_read_series_matrix_table_returns_none_without_table_block(tmp_path: Path) -> None:
    matrix_path = tmp_path / "empty_series_matrix.txt.gz"
    _write_matrix(
        matrix_path,
        [
            "!Series_title\t\"No data\"\n",
            "!Sample_geo_accession\t\"GSM1\"\n",
        ],
    )
    assert _read_series_matrix_table(matrix_path) is None


def test_read_series_matrix_table_handles_bom_prefixed_markers(tmp_path: Path) -> None:
    matrix_path = tmp_path / "bom_series_matrix.txt.gz"
    _write_matrix(
        matrix_path,
        [
            "\ufeff!Series_title\t\"BOM sample\"\n",
            "\ufeff !series_matrix_table_begin\r\n",
            '"ID_REF"\t"GSM1"\r\n',
            '"GENE_A"\t"10"\r\n',
            "\ufeff !series_matrix_table_end\r\n",
        ],
    )
    df = _read_series_matrix_table(matrix_path)
    assert df is not None
    assert df.shape[1] >= 1
    assert "GENE_A" in {str(v) for v in df.iloc[:, 0].astype(str).tolist()}

    annotations = load_series_matrix_annotations(matrix_path)
    assert annotations == {}


def test_load_expression_matrix_reads_simple_xlsx_without_openpyxl(tmp_path: Path) -> None:
    workbook = tmp_path / "expr.xlsx"
    sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Gene</t></is></c>
      <c r="B1" t="inlineStr"><is><t>S1</t></is></c>
      <c r="C1" t="inlineStr"><is><t>S2</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>IFNG</t></is></c>
      <c r="B2"><v>10</v></c>
      <c r="C2"><v>3</v></c>
    </row>
    <row r="3">
      <c r="A3" t="inlineStr"><is><t>CD274</t></is></c>
      <c r="B3"><v>6</v></c>
      <c r="C3"><v>9</v></c>
    </row>
  </sheetData>
</worksheet>
"""
    with ZipFile(workbook, "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", sheet)

    matrix = load_expression_matrix(workbook)
    assert matrix is not None
    assert matrix.shape == (2, 2)
    assert list(matrix.columns) == ["S1", "S2"]
    assert matrix.loc["IFNG", "S1"] == 10


def test_coerce_expression_table_uses_scalar_numeric_parser() -> None:
    df = _coerce_expression_table(
        pd.DataFrame(
            {
                "Gene": ["IFNG", "CD274", "EMPTY"],
                "S1": ['"10.5"', "not_numeric", ""],
                "S2": ["3", "9", ""],
                "empty_col": ["", "", ""],
            }
        )
    )

    assert list(df.columns) == ["S1", "S2"]
    assert "EMPTY" not in df.index
    assert df.loc["IFNG", "S1"] == 10.5
    assert df.loc["CD274", "S2"] == 9.0
