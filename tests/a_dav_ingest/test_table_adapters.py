import gzip
from pathlib import Path

from tools.a_dav.delimited import read_delimited_table
from tools.a_dav.matrix_header import parse_matrix_header

FIXTURES = Path(__file__).parent / "fixtures"


def test_csv_adapter_preserves_duplicate_headers_and_reads_response_by_position():
    table = read_delimited_table((FIXTURES / "author_sample_excerpt.csv").read_bytes(), delimiter=",")
    assert table.headers[10:12] == ("Response", "Response")
    assert table.column(10) == ("PD", "PRCR", "NA", "PRCR")
    assert table.column(11) == ("GroupA", "GroupB", "GroupC", "GroupD")
    assert len(table.rows) == 4


def test_matrix_header_adapter_reads_only_first_gzipped_line():
    raw = gzip.compress((FIXTURES / "matrix_header.csv").read_bytes(), mtime=0)
    assert parse_matrix_header(raw, delimiter=",", max_header_bytes=64) == (
        "", "GSMTEST001", "GSMTEST002")


def test_matrix_header_adapter_rejects_oversized_header():
    raw = b"header-too-long-without-a-line-break"
    try:
        parse_matrix_header(raw, delimiter=",", max_header_bytes=8)
    except ValueError as error:
        assert str(error) == "MATRIX_HEADER_LIMIT"
    else:
        raise AssertionError("oversized header was accepted")
