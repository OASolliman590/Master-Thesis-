from __future__ import annotations

import re


def _extract_geo_accession_from_cohort_id(cohort_id: str) -> str:
    match = re.match(r"^(gse\d+)", (cohort_id or "").strip(), re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _geo_series_prefix(gse_id: str) -> str:
    clean = (gse_id or "").strip().upper()
    if len(clean) <= 3:
        return clean
    if len(clean) <= 6:
        # Short ids like GSE99 still must retain the GSE prefix.
        return "GSEnnn" if clean.startswith("GSE") else f"{clean}nnn"
    return f"{clean[:-3]}nnn"
