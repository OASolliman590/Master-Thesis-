"""Small parser for sample records in GEO family SOFT objects."""
from __future__ import annotations

import gzip
from typing import Any

from .source_objects import SourceObjectError


def parse_geo_family_soft(raw: bytes) -> list[dict[str, Any]]:
    """Parse SOFT `^SAMPLE` blocks, preserving repeated characteristics and links."""
    try:
        text = gzip.decompress(raw).decode("utf-8") if raw.startswith(b"\x1f\x8b") else raw.decode("utf-8")
    except (OSError, EOFError, UnicodeError):
        raise SourceObjectError("GEO_SOFT_INVALID") from None

    samples: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if line.startswith("^SAMPLE = "):
            accession = line.removeprefix("^SAMPLE = ").strip()
            if not accession:
                raise SourceObjectError("GEO_SOFT_INVALID")
            current = {"accession": accession, "geo_accession": None, "title": None,
                       "characteristics": [], "relations": []}
            samples.append(current)
            continue
        if current is None or not line.startswith("!Sample_") or " = " not in line:
            continue
        attribute, value = line[1:].split(" = ", 1)
        if attribute == "Sample_title":
            current["title"] = value
        elif attribute == "Sample_geo_accession":
            current["geo_accession"] = value
        elif attribute == "Sample_characteristics_ch1":
            key, separator, characteristic_value = value.partition(":")
            if not separator or not key.strip():
                raise SourceObjectError("GEO_SOFT_INVALID")
            current["characteristics"].append({"key": key.strip(),
                                               "value": characteristic_value.strip()})
        elif attribute == "Sample_relation":
            kind, separator, locator = value.partition(":")
            if not separator or not kind.strip() or not locator.strip():
                raise SourceObjectError("GEO_SOFT_INVALID")
            current["relations"].append({"kind": kind.strip(), "locator": locator.strip()})
    if not samples or any(not sample["title"] or not sample["geo_accession"] for sample in samples):
        raise SourceObjectError("GEO_SOFT_INVALID")
    if any(sample["geo_accession"] != sample["accession"] for sample in samples):
        raise SourceObjectError("GEO_SOFT_INVALID")
    return samples
