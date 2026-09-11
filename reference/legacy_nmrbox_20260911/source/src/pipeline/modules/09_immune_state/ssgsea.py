from __future__ import annotations

from pathlib import Path


def resolve_ssgsea_backend(
    *,
    legacy_rank_mean: bool,
    rscript_path: str | None,
    ssgsea_script: Path,
) -> str:
    if legacy_rank_mean:
        return "legacy_rank_mean_python"
    if not rscript_path:
        raise RuntimeError("Rscript not found; required for real GSVA ssGSEA backend.")
    if not ssgsea_script.exists():
        raise RuntimeError(f"Missing GSVA ssGSEA script: {ssgsea_script}")
    return "gsva_ssgsea_r_backend"
