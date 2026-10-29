"""Read a bounded, single-sheet XLSX numeric table using the standard library."""
from __future__ import annotations

import io
import math
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'


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
