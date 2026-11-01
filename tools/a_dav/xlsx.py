"""Read a bounded, single-sheet XLSX numeric table using the standard library."""
from __future__ import annotations

import io
import math
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def iter_xlsx_sheet(path: Path | BinaryIO, sheet_name: str, *, selected_columns: set[int] | None = None) -> Iterator[list[str]]:
    """Stream rows from one named worksheet without opening any other worksheet."""
    try:
        with zipfile.ZipFile(path) as archive:
            workbook = ET.fromstring(archive.read('xl/workbook.xml'))
            sheets = [s for s in workbook.findall(f'{NS}sheets/{NS}sheet') if s.get('name') == sheet_name]
            if len(sheets) != 1:
                raise ValueError('XLSX_SHEET_NAME_INVALID')
            rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
            targets = [r.get('Target') for r in rels.findall(f'{PKG}Relationship')
                       if r.get('Id') == sheets[0].get(f'{REL}id') and r.get('TargetMode') != 'External']
            if len(targets) != 1 or not targets[0]:
                raise ValueError('XLSX_RELATIONSHIP')
            target = targets[0]
            sheet = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if not sheet.startswith('xl/worksheets/'):
                raise ValueError('XLSX_RELATIONSHIP')
            strings: list[str] = []
            if 'xl/sharedStrings.xml' in archive.namelist():
                with archive.open('xl/sharedStrings.xml') as source:
                    for _, element in ET.iterparse(source, events=('end',)):
                        if element.tag == f'{NS}si':
                            strings.append(''.join(t.text or '' for t in element.iter(f'{NS}t')))
                            element.clear()
            with archive.open(sheet) as source:
                for _, row in ET.iterparse(source, events=('end',)):
                    if row.tag != f'{NS}row':
                        continue
                    values: list[str] = []
                    for cell in row.findall(f'{NS}c'):
                        match = re.fullmatch(r'([A-Z]+)[1-9][0-9]*', cell.get('r', ''))
                        if not match:
                            raise ValueError('XLSX_CELL_INVALID')
                        index = 0
                        for letter in match.group(1):
                            index = index * 26 + ord(letter) - 64
                        if selected_columns is not None and index not in selected_columns:
                            continue
                        if cell.find(f'{NS}f') is not None:
                            raise ValueError('XLSX_CELL_INVALID')
                        if index <= len(values) or index > 100_000:
                            raise ValueError('XLSX_CELL_INVALID')
                        values.extend([''] * (index - len(values) - 1))
                        kind, value = cell.get('t', 'n'), cell.findtext(f'{NS}v')
                        if kind == 's' and value is not None:
                            n = int(value)
                            if n < 0:
                                raise ValueError('XLSX_CELL_INVALID')
                            value = strings[n]
                        elif kind == 'inlineStr':
                            value = ''.join(t.text or '' for t in cell.iter(f'{NS}t'))
                        elif kind == 'b' and value in {'0', '1'}:
                            value = 'TRUE' if value == '1' else 'FALSE'
                        elif kind not in {'n', 'str'}:
                            raise ValueError('XLSX_CELL_INVALID')
                        values.append(value or '')
                    yield values
                    row.clear()
    except (zipfile.BadZipFile, KeyError, IndexError, ET.ParseError, OSError, OverflowError):
        raise ValueError('XLSX_INVALID') from None


def read_clinical_xlsx(raw: bytes, *, header_row: int) -> list[dict[str, str]]:
    """Read one sparse clinical worksheet; preserve cell strings and missing values."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 200_000_000:
                raise ValueError('XLSX_LIMIT')
            workbook = ET.fromstring(archive.read('xl/workbook.xml'))
            sheets = workbook.findall(f'{NS}sheets/{NS}sheet')
            if len(sheets) != 1:
                raise ValueError('XLSX_SHEET_COUNT')
            rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
            targets = [r.get('Target') for r in rels.findall(f'{PKG}Relationship')
                       if r.get('Id') == sheets[0].get(f'{REL}id') and r.get('TargetMode') != 'External']
            if len(targets) != 1 or not targets[0]:
                raise ValueError('XLSX_RELATIONSHIP')
            target = targets[0]
            path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if not path.startswith('xl/'):
                raise ValueError('XLSX_RELATIONSHIP')
            strings: list[str] = []
            if 'xl/sharedStrings.xml' in archive.namelist():
                shared = ET.fromstring(archive.read('xl/sharedStrings.xml'))
                strings = [''.join(t.text or '' for t in si.iter(f'{NS}t')) for si in shared.findall(f'{NS}si')]
            sheet = ET.fromstring(archive.read(path))
            headers: list[str] | None = None
            result: list[dict[str, str]] = []
            for row in sheet.findall(f'{NS}sheetData/{NS}row'):
                rownum = int(row.get('r', '0'))
                if rownum < header_row:
                    continue
                values: dict[int, str] = {}
                for cell in row.findall(f'{NS}c'):
                    match = re.fullmatch(r'([A-Z]+)[1-9][0-9]*', cell.get('r', ''))
                    if not match or cell.find(f'{NS}f') is not None:
                        raise ValueError('XLSX_CELL_INVALID')
                    index = 0
                    for letter in match.group(1):
                        index = index * 26 + ord(letter) - 64
                    kind, value = cell.get('t', 'n'), cell.findtext(f'{NS}v')
                    if kind == 's' and value is not None:
                        value = strings[int(value)]
                    elif kind == 'inlineStr':
                        value = ''.join(t.text or '' for t in cell.iter(f'{NS}t'))
                    elif kind not in {'n', 'str'}:
                        raise ValueError('XLSX_CELL_INVALID')
                    values[index] = value or ''
                if rownum == header_row:
                    headers = [values.get(i, '') for i in range(1, max(values, default=0) + 1)]
                    if not headers or any(not v for v in headers) or len(set(headers)) != len(headers):
                        raise ValueError('XLSX_HEADER_INVALID')
                elif headers is not None and values.get(1, '').strip():
                    result.append({name: values.get(i, '') for i, name in enumerate(headers, 1)})
            if headers is None:
                raise ValueError('XLSX_HEADER_INVALID')
            return result
    except (zipfile.BadZipFile, KeyError, IndexError, ET.ParseError, OSError, OverflowError):
        raise ValueError('XLSX_INVALID') from None


def read_numeric_xlsx(raw: bytes) -> tuple[tuple[str, ...], tuple[tuple[str | float, ...], ...]]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 200_000_000:
                raise ValueError('XLSX_LIMIT')
            workbook = ET.fromstring(archive.read('xl/workbook.xml'))
            sheets = workbook.findall(f'{NS}sheets/{NS}sheet')
            if len(sheets) != 1:
                raise ValueError('XLSX_SHEET_COUNT')
            relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
            targets = [r.get('Target') for r in relationships.findall(f'{PKG}Relationship')
                       if r.get('Id') == sheets[0].get(f'{REL}id') and r.get('TargetMode') != 'External']
            if len(targets) != 1 or not targets[0]:
                raise ValueError('XLSX_RELATIONSHIP')
            target = targets[0]
            path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if not path.startswith('xl/'):
                raise ValueError('XLSX_RELATIONSHIP')
            strings: list[str] = []
            if 'xl/sharedStrings.xml' in archive.namelist():
                shared = ET.fromstring(archive.read('xl/sharedStrings.xml'))
                strings = [''.join(t.text or '' for t in si.iter(f'{NS}t')) for si in shared.findall(f'{NS}si')]
            sheet = ET.fromstring(archive.read(path))
            rows: list[list[str | float]] = []
            for row in sheet.findall(f'{NS}sheetData/{NS}row'):
                values: list[str | float] = []
                for cell in row.findall(f'{NS}c'):
                    ref = cell.get('r', '')
                    match = re.fullmatch(r'([A-Z]+)[1-9][0-9]*', ref)
                    if not match or cell.find(f'{NS}f') is not None:
                        raise ValueError('XLSX_CELL_INVALID')
                    index = 0
                    for letter in match.group(1):
                        index = index * 26 + ord(letter) - 64
                    if index != len(values) + 1:
                        raise ValueError('XLSX_CELL_INVALID')
                    kind = cell.get('t', 'n')
                    value = cell.findtext(f'{NS}v')
                    if kind == 's' and value is not None:
                        n = int(value)
                        if n < 0:
                            raise ValueError('XLSX_CELL_INVALID')
                        values.append(strings[n])
                    elif kind == 'inlineStr':
                        values.append(''.join(t.text or '' for t in cell.iter(f'{NS}t')))
                    elif kind == 'n' and value is not None:
                        number = float(value)
                        if not math.isfinite(number):
                            raise ValueError('XLSX_CELL_INVALID')
                        values.append(number)
                    else:
                        raise ValueError('XLSX_CELL_INVALID')
                rows.append(values)
            if not rows or len(rows[0]) < 2 or any(not isinstance(v, str) or not v for v in rows[0]):
                raise ValueError('XLSX_HEADER_INVALID')
            if any(len(row) != len(rows[0]) or not isinstance(row[0], str) or any(not isinstance(v, float) for v in row[1:]) for row in rows[1:]):
                raise ValueError('XLSX_TABLE_INVALID')
            return tuple(str(v) for v in rows[0]), tuple(tuple(row) for row in rows[1:])
    except (zipfile.BadZipFile, KeyError, IndexError, ET.ParseError, OSError, OverflowError):
        raise ValueError('XLSX_INVALID') from None
