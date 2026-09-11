from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from ...common.io import read_tsv


def load_figure_registry(path: Path) -> list[dict[str, str]]:
    registry_path = Path(path)
    if not registry_path.exists():
        return []
    rows = read_tsv(registry_path)
    cleaned: list[dict[str, str]] = []
    for row in rows:
        pattern = (row.get("path_pattern", "") or "").strip()
        if not pattern:
            continue
        cleaned.append(
            {
                "path_pattern": pattern,
                "framing": (row.get("framing", "") or "").strip(),
                "scientific_note": (row.get("scientific_note", "") or "").strip(),
            }
        )
    return cleaned


def resolve_figure_contract(
    relative_path: str,
    registry_rows: list[dict[str, str]],
) -> tuple[str, str]:
    rel = str(relative_path)
    for row in registry_rows:
        pattern = row.get("path_pattern", "")
        if pattern and fnmatch(rel, pattern):
            framing = row.get("framing", "") or "descriptive"
            scientific_note = row.get("scientific_note", "") or "Descriptive analysis figure."
            return framing, scientific_note

    rel_low = rel.lower()
    if "tcga" in rel_low or "survival" in rel_low:
        return (
            "prognostic_only",
            "Prognostic context only (TCGA is non-ICB and not ICB-predictive).",
        )
    if "concordance" in rel_low or "gold" in rel_low or "silver" in rel_low or "bronze" in rel_low:
        return (
            "internal_robustness",
            "Internal same-sample cross-method robustness (not external predictive evidence).",
        )
    return (
        "descriptive",
        "Descriptive analysis figure for cohort-level or pooled-effect interpretation.",
    )
