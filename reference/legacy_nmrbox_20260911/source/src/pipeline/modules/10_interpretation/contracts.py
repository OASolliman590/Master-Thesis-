from __future__ import annotations

import hashlib
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ...common.io import read_tsv, write_tsv


VALID_CLAIM_CLASSES = {"mechanism_hypothesis", "discovery"}

GSEA_FIELDS = [
    "analysis_id",
    "collection",
    "pathway",
    "n_genes",
    "n_overlap",
    "statistic",
    "nes",
    "p_value",
    "fdr",
    "leading_edge_genes",
    "method",
    "status",
    "claim_class",
]
ORA_FIELDS = [
    "analysis_id",
    "collection",
    "pathway",
    "n_genes",
    "n_overlap",
    "signature_genes",
    "odds_proxy",
    "p_value",
    "fdr",
    "overlap_genes",
    "method",
    "status",
    "claim_class",
]
DOTPLOT_FIELDS = [
    "analysis_id",
    "source",
    "collection",
    "pathway",
    "n_overlap",
    "score",
    "fdr",
    "claim_class",
]
HUB_FIELDS = [
    "analysis_id",
    "gene",
    "centrality",
    "permutation_fdr",
    "direction",
    "module",
    "status",
    "reason",
    "claim_class",
]
EDGE_FIELDS = [
    "analysis_id",
    "source_gene",
    "target_gene",
    "weight",
    "edge_source",
    "status",
    "claim_class",
]
HUB_DIFF_FIELDS = [
    "analysis_id",
    "comparison",
    "n_edges",
    "n_hubs",
    "status",
    "reason",
    "claim_class",
]
HUB_META_FIELDS = [
    "gene",
    "n_analysis_ids",
    "pan_cancer_flag",
    "moderator_status",
    "mean_effect",
    "effect_range",
    "status",
    "claim_class",
]
FOREST_FIELDS = [
    "gene",
    "analysis_id",
    "cancer_scope",
    "effect",
    "standard_error",
    "claim_class",
]
PHENOTYPE_SAMPLE_FIELDS = [
    "cohort_id",
    "sample_id",
    "patient_uid",
    "criteria_id",
    "score",
    "phenotype_class",
    "response_label",
    "score_status",
    "claim_class",
]
PHENOTYPE_ASSOC_FIELDS = [
    "criteria_id",
    "phenotype_class",
    "n_responder",
    "n_non_responder",
    "mean_responder",
    "mean_non_responder",
    "effect_responder_minus_non_responder",
    "p_value",
    "status",
    "claim_class",
]
HOPE_SKIP_FIELDS = [
    "criteria_id",
    "data_type",
    "method",
    "skip_reason",
    "route_to_spec",
    "claim_class",
]
AUDIT_FIELDS = [
    "module",
    "input_name",
    "input_path",
    "status",
    "detail",
    "claim_class",
]
EPI_SCORE_FIELDS = [
    "cohort_id",
    "sample_id",
    "patient_uid",
    "regulator_proxy",
    "score",
    "method",
    "response_label",
    "claim_class",
]
EPI_ASSOC_FIELDS = [
    "regulator_proxy",
    "n_responder",
    "n_non_responder",
    "mean_responder",
    "mean_non_responder",
    "effect_responder_minus_non_responder",
    "p_value",
    "status",
    "claim_class",
]


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def interpretation_root(results_root: Path, out: Path | None = None) -> Path:
    root = Path(results_root).resolve()
    expected = (root / "interpretation").resolve()
    target = Path(out).resolve() if out is not None else expected
    try:
        target.relative_to(expected)
    except ValueError as exc:
        raise ValueError(
            f"Interpretation outputs must be written under {expected}; got {target}"
        ) from exc
    target.mkdir(parents=True, exist_ok=True)
    return target


def module_dir(results_root: Path, out: Path | None, name: str) -> Path:
    root = interpretation_root(results_root, out)
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    return target


def validate_claim_class(value: str) -> str:
    if value not in VALID_CLAIM_CLASSES:
        raise ValueError(f"Invalid claim_class {value!r}; expected one of {sorted(VALID_CLAIM_CLASSES)}")
    return value


def with_claim(row: dict[str, object], claim_class: str = "discovery") -> dict[str, object]:
    validate_claim_class(claim_class)
    updated = dict(row)
    updated["claim_class"] = claim_class
    return updated


def write_claim_tsv(path: Path, fieldnames: Iterable[str], rows: Iterable[dict[str, object]]) -> None:
    checked: list[dict[str, object]] = []
    for row in rows:
        claim = str(row.get("claim_class", ""))
        validate_claim_class(claim)
        checked.append(row)
    write_tsv(path, fieldnames, checked)


def append_analysis_log(interpretation: Path, message: str) -> None:
    log_path = interpretation / "analysis_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"- {timestamp()} {message}\n")


def write_reproducibility(module_path: Path, command: str, input_paths: Iterable[Path]) -> None:
    repro = module_path / "reproducibility"
    repro.mkdir(parents=True, exist_ok=True)
    (repro / "commands.sh").write_text(command.rstrip() + "\n", encoding="utf-8")
    env_text = "\n".join(
        [
            "name: spec027-interpretation",
            "channels:",
            "  - defaults",
            "dependencies:",
            f"  - python={sys.version_info.major}.{sys.version_info.minor}",
            "metadata:",
            f"  platform: {platform.platform()}",
            f"  generated_utc: {timestamp()}",
            "",
        ]
    )
    (repro / "environment.yml").write_text(env_text, encoding="utf-8")
    checksum_lines = []
    for path in input_paths:
        p = Path(path)
        if p.exists() and p.is_file():
            checksum_lines.append(f"{file_sha256(p)}  {p}")
    (repro / "checksums.sha256").write_text("\n".join(checksum_lines) + ("\n" if checksum_lines else ""), encoding="utf-8")


def active_analysis_ids(results_root: Path) -> list[str]:
    meta_root = Path(results_root) / "meta"
    if not meta_root.exists():
        return []
    return sorted(p.name for p in meta_root.iterdir() if (p / "meta_effects.tsv").exists())


def meta_effects_path(results_root: Path, analysis_id: str) -> Path:
    return Path(results_root) / "meta" / analysis_id / "meta_effects.tsv"


def signature_path(results_root: Path, analysis_id: str) -> Path:
    return Path(results_root) / "signature" / analysis_id / "responder_signature_tiered.tsv"


def load_meta_effects(results_root: Path, analysis_id: str) -> list[dict[str, str]]:
    path = meta_effects_path(results_root, analysis_id)
    rows = read_tsv(path)
    required = {"gene_symbol", "meta_effect_random"}
    if rows:
        missing = required - set(rows[0])
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")
    return rows


def load_signature(results_root: Path, analysis_id: str) -> list[dict[str, str]]:
    path = signature_path(results_root, analysis_id)
    if not path.exists():
        return []
    return read_tsv(path)


def row_gene(row: dict[str, str]) -> str:
    return (row.get("gene_symbol") or row.get("gene_id") or row.get("original_gene_id") or "").strip()


def float_or_nan(value: object) -> float:
    try:
        x = float(str(value))
    except (TypeError, ValueError):
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def finite(values: Iterable[float]) -> list[float]:
    return [v for v in values if math.isfinite(v)]


def mean(values: Iterable[float]) -> float:
    vals = finite(values)
    if not vals:
        return float("nan")
    return sum(vals) / len(vals)


def stdev(values: Iterable[float]) -> float:
    vals = finite(values)
    if len(vals) < 2:
        return float("nan")
    mu = mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def normal_two_sided_p(z: float) -> float:
    if not math.isfinite(z):
        return 1.0
    return max(0.0, min(1.0, math.erfc(abs(z) / math.sqrt(2.0))))


def bh_fdr(p_values: list[float]) -> list[float]:
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda item: (math.inf if not math.isfinite(item[1]) else item[1]))
    out = [1.0] * n
    running = 1.0
    for rank, (idx, p_val) in reversed(list(enumerate(indexed, start=1))):
        p = 1.0 if not math.isfinite(p_val) else max(0.0, min(1.0, p_val))
        running = min(running, p * n / rank)
        out[idx] = max(0.0, min(1.0, running))
    return out


def log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def hypergeom_sf(overlap: int, universe_size: int, pathway_size: int, signature_size: int) -> float:
    max_k = min(pathway_size, signature_size)
    if overlap <= 0 or universe_size <= 0 or pathway_size <= 0 or signature_size <= 0:
        return 1.0
    denom = log_comb(universe_size, signature_size)
    probs = []
    for k in range(overlap, max_k + 1):
        log_p = log_comb(pathway_size, k) + log_comb(universe_size - pathway_size, signature_size - k) - denom
        if math.isfinite(log_p):
            probs.append(math.exp(min(0.0, log_p)))
    return max(0.0, min(1.0, sum(probs)))


def sample_response_lookup(results_root: Path) -> dict[str, dict[str, str]]:
    manifest = Path(results_root) / "patient_manifest" / "patient_manifest.tsv"
    lookup: dict[str, dict[str, str]] = {}
    if not manifest.exists():
        return lookup
    for row in read_tsv(manifest):
        response = (row.get("response_label") or row.get("best_response_label") or "").strip().lower()
        payload = {
            "patient_uid": row.get("patient_uid", ""),
            "cohort_id": row.get("cohort_id", ""),
            "response_label": response,
        }
        for col in [
            "pre_sample_ids",
            "on_sample_ids",
            "post_sample_ids",
            "unknown_timing_sample_ids",
            "unknown_sample_ids",
            "sample_ids",
        ]:
            for sample_id in str(row.get(col, "")).replace("|", ";").split(";"):
                sid = sample_id.strip()
                if sid:
                    lookup[sid] = payload
    return lookup
