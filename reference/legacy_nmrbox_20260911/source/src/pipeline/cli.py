from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import importlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .common.io import (
    build_source_uri,
    infer_source_db,
    parse_bool,
    read_tsv,
    split_accessions,
    write_tsv,
)
from .common.expression import (
    infer_tumor_adjacent_group,
    load_expression_matrix,
    load_series_matrix_annotations,
    resolve_primary_expression_path,
)
from .common.contrast_resolver import (
    RESPONSE_CONTRASTS,
    SUPPORTED_CONTRASTS,
    is_contrast_eligible,
    resolve_response_contrast_sample_ids,
    resolve_treatment_delta_groups,
)
from .common.run_manifest import append_run_manifest
from .modules._analysis_design.execution_plan import build_local_execution_plan
from .modules._analysis_design.registry import write_analysis_design_outputs
from .modules._08_signature import derive_signature_outputs


RESPONSE_NONRESP_RE = re.compile(
    r"\b(non[-\s]?responder|non[-\s]?response|non[-\s]?responding|"
    r"progressive disease|poor responder|stable disease|nr\b|"
    r"nonresponder)\b",
    re.IGNORECASE,
)
RESPONSE_RESP_RE = re.compile(
    r"\b(responder|responding|respoder|good responder|complete response|partial response|"
    r"cr\b|pr\b)\b",
    re.IGNORECASE,
)
TIMING_PRE_RE = re.compile(
    r"\b(pre[-\s]?treatment|pretreatment|baseline|before treatment|prior to treatment|"
    r"collection:\s*baseline)\b",
    re.IGNORECASE,
)
TIMING_ON_RE = re.compile(
    r"\b(on[-\s]?treatment|during treatment|while on treatment|week\s*\d+|"
    r"\d+\s*wks?)\b",
    re.IGNORECASE,
)
TIMING_POST_RE = re.compile(
    r"\b(post[-\s]?treatment|post treatment|post[-\s]?ipilimumab|after treatment|"
    r"follow[-\s]?up|surgery)\b",
    re.IGNORECASE,
)
PMID_RE = re.compile(r"PMID[:\s]*([0-9]{6,9})", re.IGNORECASE)
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
ENSEMBL_GENE_RE = re.compile(r"^ENS[A-Z]*G[0-9]+(?:\.[0-9]+)?$", re.IGNORECASE)
SYMBOL_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")


def _timestamp_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _join_tokens(tokens: list[str], prefixes: tuple[str, ...]) -> str:
    values = [tok for tok in tokens if tok.startswith(prefixes)]
    return ";".join(values)


def _mark_run(args: argparse.Namespace, command: str, outputs: list[Path]) -> None:
    params = {k: str(v) for k, v in vars(args).items() if k != "func"}
    append_run_manifest(
        manifest_path=Path(args.run_manifest),
        command=command,
        params=params,
        outputs=[str(p) for p in outputs],
    )


def cmd_design_build(args: argparse.Namespace) -> int:
    sample_manifest_path = Path(args.sample_manifest)
    rows = read_tsv(sample_manifest_path)
    outputs = write_analysis_design_outputs(
        rows=rows,
        out_dir=Path(args.out),
        min_case_samples=int(getattr(args, "min_case_samples", 2)),
        min_control_samples=int(getattr(args, "min_control_samples", 2)),
        min_cohorts=int(getattr(args, "min_cohorts", 1)),
        expression_manifest=Path(getattr(args, "expression_manifest", "")),
        downloads_root=Path(getattr(args, "downloads_root", "")),
        check_expression_readiness=bool(getattr(args, "check_expression_readiness", False)),
    )
    _mark_run(args, "design build", outputs)
    print(f"Wrote analysis design outputs under {Path(args.out)}")
    return 0


def cmd_design_plan_runs(args: argparse.Namespace) -> int:
    analysis_ids: set[str] = set()
    for raw in getattr(args, "analysis_id", []) or []:
        analysis_ids.update(tok.strip() for tok in raw.split(",") if tok.strip())
    stages = set(getattr(args, "stage", []) or [])
    plan_path = build_local_execution_plan(
        registry_path=Path(args.analysis_registry),
        membership_path=Path(args.analysis_membership),
        out_dir=Path(args.out),
        execution_root=Path(args.execution_root),
        sample_manifest=Path(args.sample_manifest),
        expression_manifest=Path(args.expression_manifest),
        downloads_root=Path(args.downloads_root),
        gene_id_mapping=Path(args.gene_id_mapping),
        python_executable=args.python_executable,
        count_method=args.count_method,
        analysis_ids=analysis_ids,
        pilot_only=bool(getattr(args, "pilot", False)),
        stages=stages or None,
        allow_weak_gene_mapping=bool(getattr(args, "allow_weak_gene_mapping", False)),
        allow_welch_fallback=bool(getattr(args, "allow_welch_fallback", False)),
        skip_forest_plots=not bool(getattr(args, "include_forest_plots", False)),
    )
    _mark_run(args, "design plan-runs", [plan_path])
    print(f"Wrote {plan_path}")
    return 0


def cmd_external_validation_run(args: argparse.Namespace) -> int:
    module = importlib.import_module(
        ".modules._10_external_validation",
        package=__package__,
    )
    signature_paths: list[Path] = []
    for raw in getattr(args, "signature", []) or []:
        signature_paths.extend(Path(tok.strip()) for tok in str(raw).split(",") if tok.strip())
    if not signature_paths:
        raise ValueError("external-validation run requires at least one --signature path.")
    outputs = module.run_external_validation(
        candidate_roster=Path(args.candidate_roster),
        derivation_lock=Path(args.derivation_lock),
        sample_manifest=Path(args.sample_manifest),
        signature_paths=signature_paths,
        out_dir=Path(args.out),
    )
    _mark_run(args, "external-validation run", outputs)
    print(f"Wrote external validation outputs under {Path(args.out)}")
    return 0


def _interpret_module(name: str):
    return importlib.import_module(f".modules.10_interpretation.{name}", package=__package__)


def cmd_interpret_enrich(args: argparse.Namespace) -> int:
    module = _interpret_module("enrich")
    outputs = module.run(
        results_root=Path(args.results_root),
        analysis_id=args.analysis_id,
        collections=[Path(p) for p in args.collections],
        out=Path(args.out),
        min_overlap=args.min_overlap,
        command="interpret enrich",
    )
    _mark_run(args, "interpret enrich", outputs)
    print(f"Wrote interpretation enrichment outputs under {Path(args.out)}")
    return 0


def cmd_interpret_network(args: argparse.Namespace) -> int:
    module = _interpret_module("network")
    outputs = module.run(
        results_root=Path(args.results_root),
        analysis_id=args.analysis_id,
        out=Path(args.out),
        min_signal_floor=args.min_signal_floor,
        fdr_threshold=args.fdr_threshold,
        effect_threshold=args.effect_threshold,
        command="interpret network",
    )
    _mark_run(args, "interpret network", outputs)
    print(f"Wrote interpretation network outputs under {Path(args.out)}")
    return 0


def cmd_interpret_hub_meta(args: argparse.Namespace) -> int:
    module = _interpret_module("hub_meta")
    outputs = module.run(
        results_root=Path(args.results_root),
        out=Path(args.out),
        command="interpret hub-meta",
    )
    _mark_run(args, "interpret hub-meta", outputs)
    print(f"Wrote interpretation hub-meta outputs under {Path(args.out)}")
    return 0


def cmd_interpret_immunophenotype(args: argparse.Namespace) -> int:
    module = _interpret_module("immunophenotype")
    outputs = module.run(
        results_root=Path(args.results_root),
        criteria_registry=Path(args.criteria_registry),
        out=Path(args.out),
        command="interpret immunophenotype",
    )
    _mark_run(args, "interpret immunophenotype", outputs)
    print(f"Wrote interpretation immunophenotype outputs under {Path(args.out)}")
    return 0


def cmd_interpret_epi_infer(args: argparse.Namespace) -> int:
    module = _interpret_module("epi_infer")
    outputs = module.run(
        results_root=Path(args.results_root),
        out=Path(args.out),
        command="interpret epi-infer",
    )
    _mark_run(args, "interpret epi-infer", outputs)
    print(f"Wrote interpretation epigenetic-proxy outputs under {Path(args.out)}")
    return 0


def _write_empty(path: Path, fieldnames: list[str]) -> None:
    write_tsv(path, fieldnames=fieldnames, rows=[])


def _analysis_registry_row(registry_path: str, analysis_id: str) -> dict[str, str]:
    if not registry_path or not analysis_id:
        return {}
    path = Path(registry_path)
    if not path.exists():
        return {}
    for row in read_tsv(path):
        if row.get("analysis_id", "") == analysis_id:
            return row
    return {}


def _filter_rows_for_analysis_membership(
    rows: list[dict[str, str]],
    *,
    membership_path: str,
    analysis_id: str,
) -> list[dict[str, str]]:
    if not membership_path or not analysis_id:
        return rows
    path = Path(membership_path)
    if not path.exists():
        return rows
    member_keys = {
        (row.get("cohort_id", ""), row.get("sample_id", ""))
        for row in read_tsv(path)
        if row.get("analysis_id", "") == analysis_id
    }
    if not member_keys:
        return []
    return [
        row
        for row in rows
        if (row.get("cohort_id", ""), row.get("sample_id", "")) in member_keys
    ]


def _resolve_sample_columns(
    expr: "pd.DataFrame",
    cohort_rows: list[dict],
    include_filter: bool = False,
) -> tuple["pd.DataFrame", list[str]]:
    """Match manifest rows to expression columns, using expression_sample_alias as fallback."""
    if include_filter:
        rows = [r for r in cohort_rows if parse_bool(r.get("include_flag", "true"), default=True)]
    else:
        rows = list(cohort_rows)
    sample_ids = [r.get("sample_id", "") for r in rows]
    available = [sid for sid in sample_ids if sid in expr.columns]
    if available:
        return expr.loc[:, available], available
    # Fallback: try expression_sample_alias
    alias_map = {}
    for r in rows:
        alias = (r.get("expression_sample_alias", "") or "").strip()
        if alias and alias in expr.columns:
            alias_map[alias] = r.get("sample_id", "")
    if alias_map:
        expr = expr.loc[:, list(alias_map.keys())]
        expr = expr.rename(columns=alias_map)
        return expr, list(alias_map.values())
    return expr, []


def _looks_like_count_matrix(expr: "pd.DataFrame") -> bool:
    import numpy as np

    if expr is None or expr.empty:
        return False
    values = expr.to_numpy(dtype=float, copy=False)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return False
    if float(finite.min()) < 0.0:
        return False
    near_integer_fraction = float(np.isclose(finite, np.round(finite), atol=1e-6).mean())
    return near_integer_fraction >= 0.98


def _normalize_gene_symbol_token(token: str) -> str:
    tok = (token or "").strip()
    if not tok:
        return ""
    tok = re.sub(r"\s+", "", tok)
    return tok.upper()


def _strip_ensembl_version(token: str) -> tuple[str, bool]:
    tok = (token or "").strip()
    if not tok:
        return "", False
    if "." in tok:
        return tok.split(".", 1)[0], True
    return tok, False


def _is_ensembl_like_gene_id(token: str) -> bool:
    return bool(ENSEMBL_GENE_RE.match((token or "").strip()))


def _is_symbol_like_gene_id(token: str) -> bool:
    tok = (token or "").strip()
    if not tok or _is_ensembl_like_gene_id(tok):
        return False
    low = tok.lower()
    # Common microarray/probe IDs should not be treated as gene symbols.
    if low.endswith(("_at", "_s_at", "_x_at", "_a_at")):
        return False
    if low.startswith(("affx-", "ilmn_", "a_")):
        return False
    if tok.isdigit():
        return False
    return bool(SYMBOL_LIKE_RE.match(tok))


@lru_cache(maxsize=8)
def _cached_gene_id_mapping(mapping_path: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return (ensembl_to_symbol, alias_or_symbol_to_symbol)."""
    path = Path(mapping_path).expanduser()
    if not path.exists():
        return {}, {}

    rows = read_tsv(path)
    ensembl_to_symbol: dict[str, str] = {}
    alias_to_symbol: dict[str, str] = {}

    for row in rows:
        row_l = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}

        symbol_raw = (
            row_l.get("hgnc_symbol", "")
            or row_l.get("approved_symbol", "")
            or row_l.get("gene_symbol", "")
            or row_l.get("symbol", "")
        )
        symbol = _normalize_gene_symbol_token(symbol_raw)
        if not symbol:
            continue

        ensembl_raw = (
            row_l.get("ensembl_gene_id", "")
            or row_l.get("ensembl_id", "")
            or row_l.get("ensembl", "")
            or row_l.get("gene_id", "")
        )
        ensembl_base, _ = _strip_ensembl_version(ensembl_raw)
        if ensembl_base and _is_ensembl_like_gene_id(ensembl_base):
            ensembl_to_symbol[ensembl_base.upper()] = symbol

        aliases_raw = (
            row_l.get("alias_symbols", "")
            or row_l.get("aliases", "")
            or row_l.get("synonyms", "")
            or row_l.get("alias", "")
            or row_l.get("previous_symbols", "")
        )
        tokens = [symbol]
        if aliases_raw:
            tokens.extend(re.split(r"[;,|]", aliases_raw))
        for tok in tokens:
            norm = _normalize_gene_symbol_token(tok)
            if norm:
                alias_to_symbol[norm] = symbol

    # Optional Entrez GeneID -> HGNC symbol mapping (NCBI gene_info)
    entrez_path = path.parent / "Homo_sapiens.gene_info.gz"
    if entrez_path.exists():
        import gzip as _gzip

        with _gzip.open(str(entrez_path), "rt", encoding="utf-8", errors="replace") as efh:
            for eline in efh:
                if eline.startswith("#"):
                    continue
                parts = eline.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                entrez_id = parts[1].strip()
                symbol_raw = parts[2].strip()
                if not entrez_id.isdigit() or symbol_raw == "-":
                    continue
                symbol_norm = _normalize_gene_symbol_token(symbol_raw)
                if symbol_norm:
                    alias_to_symbol[entrez_id] = symbol_norm
                    if len(parts) >= 6:
                        for xref in parts[5].split("|"):
                            if xref.startswith("Ensembl:"):
                                ensembl_base, _ = _strip_ensembl_version(
                                    xref.split(":", 1)[1].strip()
                                )
                                if ensembl_base and _is_ensembl_like_gene_id(ensembl_base):
                                    ensembl_to_symbol[ensembl_base.upper()] = symbol_norm

    # Optional Illumina probe -> HGNC mapping (for GPL6947/GSE106128-style ILMN IDs)
    illumina_probe_map_path = path.parent / "illumina_gpl6947_probe_to_hgnc.tsv"
    if illumina_probe_map_path.exists():
        probe_rows = read_tsv(illumina_probe_map_path)
        for row in probe_rows:
            probe_id = (row.get("probe_id", "") or "").strip().upper()
            symbol_raw = (row.get("gene_symbol", "") or "").strip()
            if not probe_id or not probe_id.startswith("ILMN_"):
                continue
            symbol_norm = _normalize_gene_symbol_token(symbol_raw)
            if symbol_norm:
                alias_to_symbol[probe_id] = symbol_norm

    return ensembl_to_symbol, alias_to_symbol


def _standardize_expression_gene_ids(
    expr,
    *,
    mapping_path: Path,
    aggregation: str = "mean",
) -> tuple["object", list[dict[str, str]], dict[str, str]]:
    """
    Standardize expression row IDs to canonical symbols where possible.

    Returns:
      - standardized expression DataFrame (rows collapsed by canonical ID)
      - canonical map rows
      - summary metrics as strings
    """
    import pandas as pd

    ensembl_to_symbol, alias_to_symbol = _cached_gene_id_mapping(str(mapping_path.expanduser()))
    map_rows: list[dict[str, str]] = []
    canonical_ids: list[str] = []

    for raw in expr.index.tolist():
        raw_id = (str(raw) if raw is not None else "").strip()
        if not raw_id:
            raw_id = "UNNAMED_GENE"

        namespace = "other"
        mapping_source = "other_unmapped"
        had_version = False
        mapped_to_hgnc = False
        alias_mapped = False

        if _is_ensembl_like_gene_id(raw_id):
            namespace = "ensembl"
            base, had_version = _strip_ensembl_version(raw_id)
            base_up = base.upper()
            canon_symbol = ensembl_to_symbol.get(base_up, "")
            if canon_symbol:
                canonical_gene_id = canon_symbol
                mapping_source = "ensembl_map"
                mapped_to_hgnc = True
            else:
                canonical_gene_id = base_up
                mapping_source = "ensembl_unmapped"
        elif _is_symbol_like_gene_id(raw_id):
            namespace = "symbol"
            norm = _normalize_gene_symbol_token(raw_id)
            if not norm:
                canonical_gene_id = raw_id
                mapping_source = "symbol_unmapped"
            else:
                canon_symbol = alias_to_symbol.get(norm, "")
                if canon_symbol:
                    canonical_gene_id = canon_symbol
                    mapped_to_hgnc = True
                    alias_mapped = canon_symbol != norm
                    mapping_source = "alias_map" if alias_mapped else "symbol_mapped"
                else:
                    canonical_gene_id = norm
                    mapped_to_hgnc = True
                    mapping_source = "symbol_self"
        elif raw_id.isdigit() and raw_id in alias_to_symbol:
            namespace = "entrez"
            canonical_gene_id = alias_to_symbol[raw_id]
            mapping_source = "entrez_map"
            mapped_to_hgnc = True
        elif raw_id.upper().startswith("ILMN_") and raw_id.upper() in alias_to_symbol:
            namespace = "probe"
            canonical_gene_id = alias_to_symbol[raw_id.upper()]
            mapping_source = "probe_map"
            mapped_to_hgnc = True
            alias_mapped = True
        else:
            canonical_gene_id = raw_id

        canonical_gene_id = canonical_gene_id or raw_id
        canonical_ids.append(canonical_gene_id)
        map_rows.append(
            {
                "original_gene_id": raw_id,
                "canonical_gene_id": canonical_gene_id,
                "canonical_gene_symbol": canonical_gene_id,
                "id_namespace": namespace,
                "had_version_suffix": "true" if had_version else "false",
                "mapping_source": mapping_source,
                "mapped_to_hgnc": "true" if mapped_to_hgnc else "false",
                "alias_mapped": "true" if alias_mapped else "false",
            }
        )

    expr_std = expr.copy()
    expr_std = expr_std.copy()
    expr_std["_canonical_gene_id"] = canonical_ids
    if aggregation == "sum":
        expr_std = expr_std.groupby("_canonical_gene_id", sort=False).sum(numeric_only=True)
    else:
        expr_std = expr_std.groupby("_canonical_gene_id", sort=False).mean(numeric_only=True)
    expr_std.index.name = "gene_id"

    map_df = pd.DataFrame(map_rows)
    n_raw = int(len(map_df))
    n_canonical = int(expr_std.shape[0])
    n_collapsed = max(0, n_raw - n_canonical)

    n_ensembl = int((map_df["id_namespace"] == "ensembl").sum())
    n_symbol = int((map_df["id_namespace"] == "symbol").sum())
    n_other = int((map_df["id_namespace"] == "other").sum())
    n_version = int((map_df["had_version_suffix"] == "true").sum())
    n_mapped = int((map_df["mapped_to_hgnc"] == "true").sum())
    n_alias = int((map_df["alias_mapped"] == "true").sum())
    n_unmapped_ensembl = int(
        ((map_df["id_namespace"] == "ensembl") & (map_df["mapped_to_hgnc"] != "true")).sum()
    )

    canonical_map_rows: list[dict[str, str]] = []
    for canonical_gene_id, group in map_df.groupby("canonical_gene_id", sort=False):
        originals = sorted(set(group["original_gene_id"].tolist()))
        sources = sorted(set(group["mapping_source"].tolist()))
        canonical_map_rows.append(
            {
                "canonical_gene_id": canonical_gene_id,
                "canonical_gene_symbol": canonical_gene_id,
                "original_gene_ids": "|".join(originals),
                "n_original_ids_collapsed": str(len(originals)),
                "mapping_sources": "|".join(sources),
            }
        )

    metrics = {
        "n_genes_raw": str(n_raw),
        "n_genes_canonical": str(n_canonical),
        "n_collapsed_duplicates": str(n_collapsed),
        "collapsed_duplicate_fraction": f"{(n_collapsed / n_raw) if n_raw else 0.0:.6f}",
        "n_ensembl_like": str(n_ensembl),
        "n_symbol_like": str(n_symbol),
        "n_other_ids": str(n_other),
        "n_with_version_suffix": str(n_version),
        "n_mapped_to_hgnc": str(n_mapped),
        "mapped_fraction": f"{(n_mapped / n_raw) if n_raw else 0.0:.6f}",
        "n_alias_mapped": str(n_alias),
        "alias_mapped_fraction": f"{(n_alias / n_raw) if n_raw else 0.0:.6f}",
        "n_unmapped_ensembl": str(n_unmapped_ensembl),
        "unmapped_ensembl_fraction": f"{(n_unmapped_ensembl / n_ensembl) if n_ensembl else 0.0:.6f}",
    }
    return expr_std, canonical_map_rows, metrics


def _evaluate_gene_id_quality(
    metrics: dict[str, str],
    *,
    min_hgnc_mapping_rate: float,
    max_unmapped_ensembl_fraction: float,
    max_duplicate_collapse_fraction: float,
) -> tuple[str, str]:
    def _f(key: str) -> float:
        try:
            return float(metrics.get(key, "0") or 0.0)
        except Exception:  # noqa: BLE001
            return 0.0

    reasons: list[str] = []
    mapped_fraction = _f("mapped_fraction")
    unmapped_ens = _f("unmapped_ensembl_fraction")
    dup_frac = _f("collapsed_duplicate_fraction")

    if mapped_fraction < float(min_hgnc_mapping_rate):
        reasons.append(
            f"mapped_fraction={mapped_fraction:.4f}<min_hgnc_mapping_rate={float(min_hgnc_mapping_rate):.4f}"
        )
    if unmapped_ens > float(max_unmapped_ensembl_fraction):
        reasons.append(
            "unmapped_ensembl_fraction="
            f"{unmapped_ens:.4f}>max_unmapped_ensembl_fraction={float(max_unmapped_ensembl_fraction):.4f}"
        )
    if dup_frac > float(max_duplicate_collapse_fraction):
        reasons.append(
            "collapsed_duplicate_fraction="
            f"{dup_frac:.4f}>max_duplicate_collapse_fraction={float(max_duplicate_collapse_fraction):.4f}"
        )
    return ("pass", "") if not reasons else ("fail", "; ".join(reasons))


def _infer_timing(initial_slice: str) -> str:
    text = (initial_slice or "").lower()
    if "pre" in text:
        return "pre-treatment"
    if "on-treatment" in text or "on treatment" in text:
        return "on-treatment"
    if "post" in text:
        return "post-treatment"
    return "unknown"


def _infer_therapy_class(agent: str) -> str:
    low = (agent or "").lower()
    if "+" in low:
        return "ICI combination"
    if any(k in low for k in ["anti-pd", "anti-pdl", "anti-ctla", "nivolumab", "pembrolizumab", "atezolizumab"]):
        return "ICI monotherapy"
    return "unknown"


def _recommend_analysis_method(input_classes: set[str]) -> str:
    classes = {c for c in input_classes if c}
    if not classes:
        return "manual_curation_required"
    if classes == {"processed_matrix"}:
        return "limma_or_linear_model_scale_aware"
    if classes.issubset({"FASTQ", "raw_counts"}):
        return "count_model_deseq2_or_edger"
    return "stratify_by_input_class_then_meta"


def _canonical_timing(raw_timing: str) -> str:
    timing = (raw_timing or "").strip().lower()
    if timing in {"pre-treatment", "on-treatment", "post-treatment"}:
        return timing
    return "unknown"


def _canonical_response(raw_response: str) -> str:
    response = (raw_response or "").strip().lower()
    if response in {"responder", "non_responder"}:
        return response
    return "unknown"


def _infer_input_class(ledger_row: dict[str, str]) -> str:
    has_srr = bool(ledger_row.get("srr_id"))
    has_srx = bool(ledger_row.get("srx_id"))
    has_srp = bool(ledger_row.get("srp_id"))
    has_geo = bool(ledger_row.get("gse_id"))
    if has_srr or has_srx:
        return "FASTQ"
    if has_srp and has_geo:
        return "raw_counts"
    if has_srp:
        return "FASTQ"
    if has_geo:
        return "processed_matrix"
    return "processed_matrix"


def _infer_response_label(sample_id: str) -> tuple[str, str]:
    low = (sample_id or "").lower()
    if re.match(r"^(cr|pr)\d+", low):
        return "responder", "sample_id_prefix_heuristic"
    if re.match(r"^nr\d+", low):
        return "non_responder", "sample_id_prefix_heuristic"
    if "__r" in low or "_responder" in low or low.endswith("_r"):
        return "responder", "sample_id_heuristic"
    if "__nr" in low or "_nonresponder" in low or low.endswith("_nr"):
        return "non_responder", "sample_id_heuristic"
    return "unknown", "pending_manual_curation"


def _infer_response_from_text(text: str) -> tuple[str, str]:
    if not text:
        return "unknown", "no_metadata_text"
    low = text.lower()
    if (
        re.search(r"response_to_ici:\s*nr\b", low)
        or re.search(r"\bio\.response:\s*(sd|pd)\b", low)
        or re.search(r"\bbest response:\s*(sd|pd)\b", low)
        or re.search(r"\brecist criterion:\s*stable disease\b", low)
        or re.search(r"\brecist criterion:\s*progressive disease\b", low)
        or re.search(r"\bgroup:\s*non[-\s]?responder\b", low)
    ):
        return "non_responder", "metadata_text_inference"
    if (
        re.search(r"response_to_ici:\s*r\b", low)
        or re.search(r"\bio\.response:\s*(cr|pr)\b", low)
        or re.search(r"\bbest response:\s*(cr|pr)\b", low)
        or re.search(r"\brecist criterion:\s*(complete|partial) response\b", low)
        or re.search(r"\bgroup:\s*responder\b", low)
        or re.search(r"primary path response", low)
    ):
        return "responder", "metadata_text_inference"
    if RESPONSE_NONRESP_RE.search(text):
        return "non_responder", "metadata_text_inference"
    if RESPONSE_RESP_RE.search(text):
        return "responder", "metadata_text_inference"
    return "unknown", "metadata_text_inference"


def _infer_timing_from_text(text: str) -> str:
    if not text:
        return "unknown"
    if TIMING_PRE_RE.search(text):
        return "pre-treatment"
    if TIMING_ON_RE.search(text):
        return "on-treatment"
    if TIMING_POST_RE.search(text):
        return "post-treatment"
    return "unknown"


UNREADABLE_SERIES_MATRIX_COHORTS = {
    "gse202069_hcc_pdl1_tremelimumab",
    "gse305240_nsclc_atezolizumab",
    "gse305511_hcc_atezolizumab_bevacizumab",
    "gse222932_urothelial_guadecitabine_atezolizumab",
}


def _cohort_level_value(rows: list[dict[str, str]], column: str) -> str:
    for row in rows:
        value = (row.get(column, "") or "").strip()
        if value:
            return value
    return ""


def _is_curated_response_source(source: str) -> bool:
    low = (source or "").strip().lower()
    if not low:
        return False
    curated_tokens = (
        "manual_curation",
        "characteristics_mapping",
        "series_matrix_io",
        "metadata_tjcohort_csv",
        "soft_characteristics_accession_repair",
    )
    return any(token in low for token in curated_tokens)


def _response_sd_handling(original_endpoint: str) -> str:
    text = (original_endpoint or "").strip().lower()
    if "durable" in text or "clinical benefit" in text:
        return "SD=benefit_if_durable"
    if "recist" in text or "response" in text:
        return "SD=NR"
    return "unknown"


def _response_criteria_version(original_endpoint: str) -> str:
    text = (original_endpoint or "").strip()
    match = re.search(r"(recist\s*[\d.]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace(" ", "")
    return ""


def _resolve_response_with_provenance(row: dict[str, str]) -> tuple[str, str]:
    current = _canonical_response(row.get("response_label", ""))
    source = row.get("response_label_source", "")
    metadata_text = row.get("metadata_text", "")

    if current in {"responder", "non_responder"} and _is_curated_response_source(source):
        return current, "curated"

    text_label, _ = _infer_response_from_text(metadata_text)
    if text_label in {"responder", "non_responder"}:
        return text_label, "text_inferred"

    sampleid_label, _ = _infer_response_label(row.get("sample_id", ""))
    if sampleid_label in {"responder", "non_responder"}:
        return sampleid_label, "sampleid_inferred"

    if current in {"responder", "non_responder"}:
        return current, "curated"
    return "unknown", "unknown"


def _resolve_timing_with_provenance(row: dict[str, str]) -> tuple[str, str]:
    curated_timing = _canonical_timing(row.get("timing_category", ""))
    if curated_timing in {"pre-treatment", "on-treatment", "post-treatment"}:
        return curated_timing, "curated"

    inferred = _infer_timing_from_text(row.get("metadata_text", ""))
    if inferred in {"pre-treatment", "on-treatment", "post-treatment"}:
        return inferred, "text_inferred"
    return "pre-treatment", "default_pre"


ASSAY_TYPE_ALLOWED = {
    "raw_counts",
    "tpm",
    "fpkm",
    "rlog_vst",
    "log_normalized",
    "microarray_intensity",
    "microarray_probe_matrix",
    "normalized_other",
    "raw_counts_suspect",
    "methylation_beta",
    "unreadable",
}

ASSAY_TYPE_HARD_EXCLUDE = {"methylation_beta", "microarray_probe_matrix", "unreadable"}


def _canonical_assay_type(raw: str) -> str:
    value = (raw or "").strip().lower()
    value = value.replace("-", "_").replace(" ", "_")
    aliases = {
        "rlog_vst_or_log": "rlog_vst",
        "microarray_intensity_or_log": "microarray_intensity",
        "processed_matrix": "normalized_other",
        "already_log": "log_normalized",
    }
    if value in aliases:
        value = aliases[value]
    return value if value in ASSAY_TYPE_ALLOWED else ""


def _cohort_assay_type(cohort_rows: list[dict[str, str]]) -> str:
    override = _canonical_assay_type(_cohort_level_value(cohort_rows, "assay_type_override"))
    if override:
        return override
    declared = _canonical_assay_type(_cohort_level_value(cohort_rows, "assay_type"))
    if declared:
        return declared
    input_class = (_cohort_level_value(cohort_rows, "input_class") or "").strip().lower()
    if input_class == "raw_counts":
        return "raw_counts"
    if input_class in {"fastq", "processed_matrix"}:
        return "normalized_other"
    return "unreadable"


def _cohort_declared_assay_type(cohort_rows: list[dict[str, str]]) -> str:
    override = _canonical_assay_type(_cohort_level_value(cohort_rows, "assay_type_override"))
    if override:
        return override
    return _canonical_assay_type(_cohort_level_value(cohort_rows, "assay_type"))


def _cohort_contract_exclusion_reason(cohort_id: str, cohort_rows: list[dict[str, str]]) -> str:
    non_assay_reason = _cohort_non_assay_exclusion_reason(cohort_id)
    if non_assay_reason:
        return non_assay_reason
    assay_type = _cohort_assay_type(cohort_rows)
    if assay_type in ASSAY_TYPE_HARD_EXCLUDE:
        return f"excluded_assay_type_{assay_type}"
    return ""


def _cohort_non_assay_exclusion_reason(cohort_id: str) -> str:
    if cohort_id == "gse126044_srp183455_nsclc_pd1":
        return "duplicate_gse126044_deduped"
    if cohort_id.startswith("gse165278"):
        return "excluded_no_responder_arm"
    return ""


def _harmonize_expression_for_assay(expr, assay_type: str):
    module = importlib.import_module(".modules.06_within_cohort_de.harmonize", package=__package__)
    harmonize_expression_for_assay = module.harmonize_expression_for_assay

    return harmonize_expression_for_assay(
        expr,
        assay_type,
        canonicalize_assay_type=_canonical_assay_type,
    )


def cmd_intake_detect_assay_type(args: argparse.Namespace) -> int:
    from .modules._01_dataset_intake.assay_detect import classify_expression_matrix

    sample_rows = read_tsv(Path(args.sample_manifest))
    expression_manifest_path = Path(args.expression_manifest)
    downloads_root = Path(args.downloads_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sample_rows:
        sample_by_cohort[row.get("cohort_id", "")].append(row)

    detection_rows: list[dict[str, str]] = []
    for expr_row in read_tsv(expression_manifest_path):
        cohort_id = expr_row.get("cohort_id", "")
        source_file = resolve_primary_expression_path(cohort_id, expression_manifest_path, downloads_root)
        matrix = load_expression_matrix(source_file) if source_file else None
        detected = classify_expression_matrix(matrix)
        override = _cohort_level_value(sample_by_cohort.get(cohort_id, []), "assay_type_override")
        final_assay = override or detected.assay_type
        conflict = bool(override and override != detected.assay_type)

        cohort_flags: list[str] = []
        if cohort_id == "gse126044_srp183455_nsclc_pd1":
            cohort_flags.append("duplicate_of_gse126044_nsclc_pd1")
        if cohort_id.startswith("gse165278"):
            cohort_flags.append("exclude_pre_response_no_responder_arm")
        if cohort_id in UNREADABLE_SERIES_MATRIX_COHORTS:
            cohort_flags.append("known_series_matrix_unreadable")

        detection_rows.append(
            {
                "cohort_id": cohort_id,
                "assay_type": final_assay,
                "assay_type_detected": detected.assay_type,
                "detection_confidence": f"{detected.confidence:.2f}",
                "assay_evidence": detected.evidence,
                "n_genes": str(detected.n_genes),
                "n_samples": str(detected.n_samples),
                "source_file": str(source_file) if source_file else "",
                "assay_type_override": override,
                "override_applied": "true" if override else "false",
                "assay_type_override_conflict": "true" if conflict else "false",
                "cohort_flags": "|".join(cohort_flags),
            }
        )

    out_file = out_dir / "assay_detection.tsv"
    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "assay_type",
            "assay_type_detected",
            "detection_confidence",
            "assay_evidence",
            "n_genes",
            "n_samples",
            "source_file",
            "assay_type_override",
            "override_applied",
            "assay_type_override_conflict",
            "cohort_flags",
        ],
        rows=detection_rows,
    )
    _mark_run(args, "intake detect-assay-type", [out_file])
    print(f"Wrote {out_file}")
    return 0


def cmd_intake_build_response_record(args: argparse.Namespace) -> int:
    sample_rows = read_tsv(Path(args.sample_manifest))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sample_rows:
        rows_by_cohort[row.get("cohort_id", "")].append(row)

    response_rows: list[dict[str, str]] = []
    timing_rows: list[dict[str, str]] = []
    augmented_rows: list[dict[str, str]] = []
    for cohort_id, cohort_rows in sorted(rows_by_cohort.items()):
        n_responder = 0
        n_non_responder = 0
        n_unknown = 0
        provenance_seen: set[str] = set()
        sd_handling = _response_sd_handling(_cohort_level_value(cohort_rows, "original_endpoint"))
        applied_rule = (
            "CR/PR=R; SD/PD=NR"
            if sd_handling != "SD=benefit_if_durable"
            else "CR/PR/SD(durable)=R; PD/SD(non-durable)=NR"
        )
        response_definition_id = "rdef_" + hashlib.sha1(
            f"{cohort_id}|{applied_rule}".encode("utf-8")
        ).hexdigest()[:12]

        for row in cohort_rows:
            response_label, response_provenance = _resolve_response_with_provenance(row)
            timing_category, timing_provenance = _resolve_timing_with_provenance(row)
            provenance_seen.add(response_provenance)
            if response_label == "responder":
                n_responder += 1
            elif response_label == "non_responder":
                n_non_responder += 1
            else:
                n_unknown += 1

            timing_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": row.get("sample_id", ""),
                    "timing_category": timing_category,
                    "timing_provenance": timing_provenance,
                }
            )
            augmented_row = dict(row)
            augmented_row["response_label"] = response_label
            augmented_row["response_definition_id"] = response_definition_id
            augmented_row["timing_category"] = timing_category
            augmented_row["timing_provenance"] = timing_provenance
            augmented_rows.append(augmented_row)

        if "curated" in provenance_seen:
            label_provenance = "curated"
        elif "text_inferred" in provenance_seen:
            label_provenance = "text_inferred"
        elif "sampleid_inferred" in provenance_seen:
            label_provenance = "sampleid_inferred"
        else:
            label_provenance = "unknown"

        needs_manual = "true" if label_provenance in {"sampleid_inferred", "unknown"} else "false"
        cohort_flags: list[str] = []
        if cohort_id == "gse126044_srp183455_nsclc_pd1":
            cohort_flags.append("duplicate_of_gse126044_nsclc_pd1")
        if cohort_id.startswith("gse165278"):
            cohort_flags.append("exclude_pre_response_no_responder_arm")
        if cohort_id in UNREADABLE_SERIES_MATRIX_COHORTS:
            cohort_flags.append("known_series_matrix_unreadable")

        response_rows.append(
            {
                "response_definition_id": response_definition_id,
                "cohort_id": cohort_id,
                "original_endpoint": _cohort_level_value(cohort_rows, "original_endpoint"),
                "criteria_version": _response_criteria_version(
                    _cohort_level_value(cohort_rows, "original_endpoint")
                ),
                "applied_rule": applied_rule,
                "sd_handling": sd_handling,
                "label_provenance": label_provenance,
                "needs_manual_confirmation": needs_manual,
                "n_responder": str(n_responder),
                "n_non_responder": str(n_non_responder),
                "n_unknown": str(n_unknown),
                "cohort_flags": "|".join(cohort_flags),
            }
        )

    response_file = out_dir / "response_definition.tsv"
    write_tsv(
        response_file,
        fieldnames=[
            "response_definition_id",
            "cohort_id",
            "original_endpoint",
            "criteria_version",
            "applied_rule",
            "sd_handling",
            "label_provenance",
            "needs_manual_confirmation",
            "n_responder",
            "n_non_responder",
            "n_unknown",
            "cohort_flags",
        ],
        rows=response_rows,
    )
    timing_file = out_dir / "timing_provenance.tsv"
    write_tsv(
        timing_file,
        fieldnames=["cohort_id", "sample_id", "timing_category", "timing_provenance"],
        rows=timing_rows,
    )
    augmented_file = out_dir / "sample_manifest_with_contract.tsv"
    fieldnames = list(augmented_rows[0].keys()) if augmented_rows else []
    if fieldnames:
        write_tsv(augmented_file, fieldnames=fieldnames, rows=augmented_rows)
    else:
        _write_empty(augmented_file, ["cohort_id", "sample_id"])

    _mark_run(args, "intake build-response-record", [response_file, timing_file, augmented_file])
    print(f"Wrote {response_file}, {timing_file}, {augmented_file}")
    return 0


def cmd_intake_curation_report(args: argparse.Namespace) -> int:
    module = importlib.import_module(
        ".modules._01_dataset_intake.curation_report",
        package=__package__,
    )
    outputs = module.write_stage01_curation_report(
        assay_detection=Path(args.assay_detection),
        response_definition=Path(args.response_definition),
        timing_provenance=Path(args.timing_provenance),
        sample_manifest=Path(args.sample_manifest),
        out_dir=Path(args.out),
    )
    _mark_run(args, "intake curation-report", outputs)
    print(f"Wrote stage-01 curation report under {Path(args.out)}")
    return 0


def _normalize_metadata_key(raw: str) -> str:
    return re.sub(r"\s+", " ", (raw or "").strip().lower())


def _normalize_metadata_value(raw: str) -> str:
    return re.sub(r"\s+", " ", (raw or "").strip())


def _metadata_relevance_class(field_key: str) -> str:
    key = _normalize_metadata_key(field_key)
    if any(tok in key for tok in ["response", "recist", "responder", "bor", "objective"]):
        return "response"
    if any(tok in key for tok in ["visit", "timepoint", "time point", "baseline", "pre", "treatment status"]):
        return "timing"
    if any(tok in key for tok in ["stage", "grade", "survival", "os", "pfs", "age", "sex", "gender"]):
        return "clinical"
    return "other"


def _extract_geo_accession_from_cohort_id(cohort_id: str) -> str:
    match = re.match(r"^(gse\d+)", (cohort_id or "").strip(), re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _find_geo_soft_file(
    cohort_id: str,
    downloads_root: Path,
    downloads_folder: str = "",
) -> Path | None:
    folder = (downloads_folder or cohort_id or "").strip()
    if not folder:
        return None
    cohort_dir = downloads_root / folder
    if not cohort_dir.exists():
        return None

    accession = _extract_geo_accession_from_cohort_id(cohort_id)
    candidates: list[Path] = []
    if accession:
        candidates.extend(sorted(cohort_dir.rglob(f"{accession}_family.soft.gz")))
        candidates.extend(sorted(cohort_dir.rglob(f"{accession}_family.soft")))
    candidates.extend(sorted(cohort_dir.rglob("*_family.soft.gz")))
    candidates.extend(sorted(cohort_dir.rglob("*_family.soft")))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate
    return None


def _geo_series_prefix(gse_id: str) -> str:
    return f"{gse_id[:-3]}nnn" if len(gse_id) > 3 else gse_id


def _download_url(url: str, dest: Path) -> tuple[bool, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp, tmp_dest.open("wb") as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        tmp_dest.replace(dest)
        return True, ""
    except urllib.error.HTTPError as exc:
        tmp_dest.unlink(missing_ok=True)
        return False, f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        tmp_dest.unlink(missing_ok=True)
        return False, f"error:{exc.__class__.__name__}"


def _download_url_if_missing(url: str, dest: Path) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return True, "already_present"
    return _download_url(url, dest)


def _fetch_html_links(url: str) -> tuple[list[str], str]:
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        return [], f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return [], f"error:{exc.__class__.__name__}"
    links = [match.group(1) for match in HREF_RE.finditer(text)]
    return links, ""


def _safe_remote_filename(href: str) -> str:
    clean = urllib.parse.unquote((href or "").strip())
    return Path(clean).name


def _download_geo_family_soft(gse_id: str, cohort_dir: Path) -> tuple[int, int, list[str]]:
    attempts = 1
    series_prefix = _geo_series_prefix(gse_id)
    url = (
        f"https://ftp.ncbi.nlm.nih.gov/geo/series/{series_prefix}/{gse_id}/soft/"
        f"{gse_id}_family.soft.gz"
    )
    dest = cohort_dir / f"{gse_id}_family.soft.gz"
    ok, err = _download_url(url, dest)
    if ok:
        return attempts, 1, []
    return attempts, 0, [f"{gse_id}:soft_download_failed:{err}"]


def _download_geo_series_matrix(gse_id: str, out_dir: Path) -> tuple[int, int, list[str]]:
    attempts = 0
    successes = 0
    notes: list[str] = []
    base_url = (
        f"https://ftp.ncbi.nlm.nih.gov/geo/series/{_geo_series_prefix(gse_id)}/{gse_id}/matrix/"
    )
    links, err = _fetch_html_links(base_url)
    attempts += 1
    if err:
        return attempts, successes, [f"{gse_id}:matrix_list_failed:{err}"]

    targets = []
    for href in links:
        file_name = _safe_remote_filename(href)
        if not file_name:
            continue
        low = file_name.lower()
        if "series_matrix" in low and low.endswith((".txt.gz", ".tsv.gz", ".csv.gz", ".gz")):
            targets.append((href, file_name))

    if not targets:
        notes.append(f"{gse_id}:matrix_not_found")
        return attempts, successes, notes

    for href, file_name in sorted(set(targets), key=lambda t: t[1]):
        attempts += 1
        dest = out_dir / file_name
        ok, dl_err = _download_url_if_missing(urllib.parse.urljoin(base_url, href), dest)
        if ok:
            successes += 1
        else:
            notes.append(f"{gse_id}:matrix_download_failed:{file_name}:{dl_err}")
    return attempts, successes, notes


def _download_geo_supplementary(gse_id: str, out_dir: Path) -> tuple[int, int, list[str]]:
    attempts = 0
    successes = 0
    notes: list[str] = []
    base_url = (
        f"https://ftp.ncbi.nlm.nih.gov/geo/series/{_geo_series_prefix(gse_id)}/{gse_id}/suppl/"
    )
    links, err = _fetch_html_links(base_url)
    attempts += 1
    if err:
        return attempts, successes, [f"{gse_id}:suppl_list_failed:{err}"]

    targets = []
    for href in links:
        file_name = _safe_remote_filename(href)
        if not file_name or file_name == "index.html":
            continue
        if href.startswith("?") or href.startswith("#") or href.startswith("../"):
            continue
        if href.endswith("/"):
            continue
        targets.append((href, file_name))

    if not targets:
        notes.append(f"{gse_id}:suppl_not_found")
        return attempts, successes, notes

    for href, file_name in sorted(set(targets), key=lambda t: t[1]):
        attempts += 1
        dest = out_dir / file_name
        ok, dl_err = _download_url_if_missing(urllib.parse.urljoin(base_url, href), dest)
        if ok:
            successes += 1
        else:
            notes.append(f"{gse_id}:suppl_download_failed:{file_name}:{dl_err}")
    return attempts, successes, notes


def _download_runinfo(accession: str, cohort_dir: Path) -> tuple[int, int, list[str]]:
    attempts = 1
    url = f"https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc={accession}"
    dest = cohort_dir / f"{accession}_runinfo.csv"
    ok, err = _download_url(url, dest)
    if ok:
        # Empty or malformed runinfo still counts as failure for readiness.
        text = dest.read_text(encoding="utf-8", errors="ignore").strip()
        if not text or "Run," not in text:
            dest.unlink(missing_ok=True)
            return attempts, 0, [f"{accession}:runinfo_empty_or_invalid"]
        return attempts, 1, []
    return attempts, 0, [f"{accession}:runinfo_download_failed:{err}"]


def _sample_record_metadata_text(record: dict[str, object]) -> str:
    parts: list[str] = []
    for key in ["title", "source_name", "description"]:
        value = _normalize_metadata_value(str(record.get(key, "") or ""))
        if value:
            parts.append(value)
    for entry in record.get("characteristics", []):
        if not isinstance(entry, dict):
            continue
        field_key = _normalize_metadata_key(str(entry.get("field_key", "") or ""))
        field_value = _normalize_metadata_value(str(entry.get("field_value", "") or ""))
        if field_key and field_value:
            parts.append(f"{field_key}: {field_value}")
        elif field_value:
            parts.append(field_value)
    return " | ".join(parts)


def _parse_geo_soft_sample_records(soft_path: Path) -> list[dict[str, object]]:
    open_fn = gzip.open if soft_path.suffix == ".gz" else open
    samples: list[dict[str, object]] = []
    current_id = ""
    title_parts: list[str] = []
    source_parts: list[str] = []
    description_parts: list[str] = []
    characteristics: list[dict[str, str]] = []
    char_ordinal = 0

    def _flush_current() -> None:
        nonlocal title_parts, source_parts, description_parts, characteristics, char_ordinal, current_id
        if not current_id:
            return
        record: dict[str, object] = {
            "sample_id": current_id,
            "title": " | ".join(part for part in title_parts if part),
            "source_name": " | ".join(part for part in source_parts if part),
            "description": " | ".join(part for part in description_parts if part),
            "characteristics": list(characteristics),
        }
        text = _sample_record_metadata_text(record)
        response, _ = _infer_response_from_text(text)
        record["metadata_text"] = text
        record["response_label_inferred"] = response
        record["timing_category_inferred"] = _infer_timing_from_text(text)
        samples.append(record)
        current_id = ""
        title_parts = []
        source_parts = []
        description_parts = []
        characteristics = []
        char_ordinal = 0

    with open_fn(soft_path, "rt", encoding="utf-8", errors="ignore") as fh:  # type: ignore[arg-type]
        for line in fh:
            if line.startswith("^SAMPLE = "):
                _flush_current()
                current_id = line.split("=", 1)[1].strip()
                continue
            if not current_id:
                continue
            if line.startswith("!Sample_title = "):
                title_parts.append(line.split("=", 1)[1].strip())
            elif line.startswith("!Sample_source_name_ch"):
                source_parts.append(line.split("=", 1)[1].strip())
            elif line.startswith("!Sample_description = "):
                description_parts.append(line.split("=", 1)[1].strip())
            elif line.startswith("!Sample_characteristics_ch"):
                raw = line.split("=", 1)[1].strip()
                char_ordinal += 1
                if ":" in raw:
                    raw_key, raw_value = raw.split(":", 1)
                    field_key = _normalize_metadata_key(raw_key)
                    field_value = raw_value.strip()
                else:
                    field_key = f"characteristic_text_{char_ordinal}"
                    field_value = raw
                characteristics.append(
                    {
                        "field_key": field_key,
                        "field_value": field_value,
                        "field_value_raw": raw,
                        "ordinal": str(char_ordinal),
                    }
                )

    _flush_current()
    return samples


def _parse_geo_soft_samples(soft_path: Path) -> list[dict[str, str]]:
    parsed = _parse_geo_soft_sample_records(soft_path)
    return [
        {
            "sample_id": str(record.get("sample_id", "") or ""),
            "metadata_text": str(record.get("metadata_text", "") or ""),
            "response_label_inferred": str(record.get("response_label_inferred", "") or "unknown"),
            "timing_category_inferred": str(record.get("timing_category_inferred", "") or "unknown"),
        }
        for record in parsed
    ]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _slugify_label(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")


def _append_cell(row: dict[str, str], key: str, value: str) -> None:
    clean = (value or "").strip()
    if not clean:
        return
    existing = row.get(key, "").strip()
    if not existing:
        row[key] = clean
        return
    if clean == existing:
        return
    parts = [part.strip() for part in existing.split(" | ") if part.strip()]
    if clean not in parts:
        row[key] = existing + " | " + clean


def _parse_series_matrix_cells(line: str) -> list[str]:
    return next(csv.reader([line.rstrip("\n")], delimiter="\t", quotechar='"'))


def _normalize_sample_matrix_field(raw_field: str) -> str:
    field = re.sub(r"_ch\d+$", "", raw_field or "")
    field = field.replace("geo_accession", "sample_geo_accession")
    return _slugify_label(field)


def _parse_characteristic_cell(raw_value: str, ordinal: int) -> tuple[str, str]:
    clean = (raw_value or "").strip()
    if not clean:
        return "", ""
    if ":" in clean:
        key, value = clean.split(":", 1)
        return _slugify_label(key), value.strip()
    return f"characteristic_text_{ordinal}", clean


def _parse_geo_series_matrix_annotations(matrix_path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    open_fn = gzip.open if matrix_path.suffix == ".gz" else open
    series_rows: list[dict[str, str]] = []
    sample_field_rows: list[tuple[str, list[str]]] = []
    characteristic_rows: list[list[str]] = []

    with open_fn(matrix_path, "rt", encoding="utf-8", errors="ignore") as fh:  # type: ignore[arg-type]
        for line in fh:
            if line.startswith("!series_matrix_table_begin"):
                break
            if not line.startswith("!"):
                continue
            cells = _parse_series_matrix_cells(line)
            if not cells:
                continue
            tag = cells[0]
            values = [cell.strip() for cell in cells[1:]]
            if tag.startswith("!Series_"):
                field = _slugify_label(tag[len("!Series_") :])
                for value in values:
                    if value:
                        series_rows.append(
                            {
                                "series_field": field,
                                "value": value,
                            }
                        )
                continue
            if not tag.startswith("!Sample_"):
                continue
            sample_field = tag[len("!Sample_") :]
            normalized = _normalize_sample_matrix_field(sample_field)
            if normalized == "characteristics":
                characteristic_rows.append(values)
            else:
                sample_field_rows.append((normalized, values))

    sample_count = 0
    for _, values in sample_field_rows:
        sample_count = max(sample_count, len(values))
    for values in characteristic_rows:
        sample_count = max(sample_count, len(values))

    sample_rows = [{"sample_index": str(idx + 1)} for idx in range(sample_count)]
    for field, values in sample_field_rows:
        for idx, value in enumerate(values):
            _append_cell(sample_rows[idx], field, value)

    for ordinal, values in enumerate(characteristic_rows, start=1):
        for idx, value in enumerate(values):
            key, parsed = _parse_characteristic_cell(value, ordinal)
            if key:
                _append_cell(sample_rows[idx], key, parsed)
                _append_cell(sample_rows[idx], "all_characteristics", value)

    for idx, row in enumerate(sample_rows, start=1):
        sample_id = (
            row.get("sample_geo_accession")
            or row.get("title")
            or row.get("sample_id")
            or f"sample_{idx:03d}"
        )
        row["sample_id"] = sample_id

    return sample_rows, series_rows


def _sample_rows_fieldnames(rows: list[dict[str, str]]) -> list[str]:
    preferred = [
        "sample_id",
        "sample_index",
        "sample_geo_accession",
        "title",
        "source_name",
        "organism",
        "tissue",
        "cell_type",
        "treatment",
        "response",
        "group",
        "all_characteristics",
    ]
    all_fields = {key for row in rows for key in row.keys()}
    ordered = [field for field in preferred if field in all_fields]
    ordered.extend(sorted(all_fields - set(ordered)))
    return ordered


def _series_rows_fieldnames(rows: list[dict[str, str]]) -> list[str]:
    all_fields = {key for row in rows for key in row.keys()}
    preferred = ["series_field", "value"]
    ordered = [field for field in preferred if field in all_fields]
    ordered.extend(sorted(all_fields - set(ordered)))
    return ordered


def _title_prefixes(rows: list[dict[str, str]]) -> list[str]:
    prefixes: set[str] = set()
    for row in rows:
        title = row.get("title", "")
        match = re.match(r"^[A-Za-z]+", title)
        if match:
            prefixes.add(match.group(0))
    return sorted(prefixes)


def _join_unique(rows: list[dict[str, str]], field: str) -> str:
    values = sorted({row.get(field, "").strip() for row in rows if row.get(field, "").strip()})
    return ";".join(values)


def _infer_matrix_anchor(sample_rows: list[dict[str, str]]) -> tuple[str, int, int, int, int]:
    n_resp = 0
    n_nonresp = 0
    n_pre = 0
    n_on = 0
    n_post = 0
    has_tumor = False
    has_nontumor = False
    has_treatment = False

    for row in sample_rows:
        text = " | ".join([value for value in row.values() if value]).strip()
        response, _ = _infer_response_from_text(text)
        timing = _infer_timing_from_text(text)
        if response == "responder":
            n_resp += 1
        elif response == "non_responder":
            n_nonresp += 1
        if timing == "pre-treatment":
            n_pre += 1
        elif timing == "on-treatment":
            n_on += 1
        elif timing == "post-treatment":
            n_post += 1

        tissue_text = " ".join(
            [
                row.get("tissue", ""),
                row.get("source_name", ""),
                row.get("cell_type", ""),
            ]
        ).lower()
        if "tumor" in tissue_text and "nontumor" not in tissue_text and "non-tumor" not in tissue_text:
            has_tumor = True
        if any(token in tissue_text for token in ["nontumor", "non-tumor", "adjacent", "normal"]):
            has_nontumor = True
        if any(token in text.lower() for token in ["anti-pd", "anti-pdl", "nivolumab", "atezolizumab", "treatment:"]):
            has_treatment = True

    if has_tumor and has_nontumor and n_resp == 0 and n_nonresp == 0:
        return "tumor_vs_adjacent_primary", n_resp, n_nonresp, n_pre, n_on + n_post
    if n_resp > 0 or n_nonresp > 0:
        return "pre_response" if n_pre > 0 else "response_stratified", n_resp, n_nonresp, n_pre, n_on + n_post
    if n_pre > 0 and (n_on > 0 or n_post > 0):
        return "longitudinal", n_resp, n_nonresp, n_pre, n_on + n_post
    if has_treatment:
        return "treatment_exposed_unstratified", n_resp, n_nonresp, n_pre, n_on + n_post
    return "annotation_exploratory", n_resp, n_nonresp, n_pre, n_on + n_post


def _final_matrix_anchor(inferred_anchor: str, curation_track: str) -> str:
    track = (curation_track or "").strip()
    if track == "NSCLC_MULTIOMICS_COMPARATIVE":
        return "comparative_multiomics_nsclc"
    if track == "TUMOR_VS_ADJACENT_PRIMARY_PD1_SUBSET_SECONDARY":
        return "tumor_vs_adjacent_primary_pd1_subset_secondary"
    return inferred_anchor


def cmd_intake_analyze_geo_series_matrix(args: argparse.Namespace) -> int:
    manifest_path = Path(args.discovery_manifest)
    downloads_root = Path(args.downloads_root)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    curation_rows: dict[str, dict[str, str]] = {}
    if args.curation_sheet:
        curation_rows = {row.get("cohort_id", ""): row for row in read_tsv(Path(args.curation_sheet))}

    matrix_inventory: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    all_sample_rows: list[dict[str, str]] = []
    all_series_rows: list[dict[str, str]] = []

    for rec in read_tsv(manifest_path):
        cohort_id = rec.get("cohort_id", "").strip()
        cohort_dir = downloads_root / cohort_id
        matrix_paths = sorted(
            [
                path
                for path in cohort_dir.glob("**/matrix/*series_matrix*")
                if path.is_file() and not path.name.endswith(".part")
            ]
        )
        if not matrix_paths:
            continue

        curation = curation_rows.get(cohort_id, {})
        curation_track = curation.get("suggested_analysis_track", "")
        review_status = curation.get("manual_review_status", "")
        pmids = curation.get("pmid_candidates", "")

        for matrix_path in matrix_paths:
            gse_id = next((part for part in matrix_path.parts if part.startswith("GSE")), matrix_path.stem)
            matrix_id = re.sub(r"\.gz$", "", matrix_path.name)
            sample_rows, series_rows = _parse_geo_series_matrix_annotations(matrix_path)
            inferred_anchor, n_resp, n_nonresp, n_pre, n_transition = _infer_matrix_anchor(sample_rows)
            final_anchor = _final_matrix_anchor(inferred_anchor, curation_track)

            rel_matrix = str(matrix_path.relative_to(cohort_dir))
            matrix_out_dir = out_root / cohort_id / _slugify_label(matrix_id)
            sample_csv = matrix_out_dir / "sample_annotations.csv"
            series_csv = matrix_out_dir / "series_metadata.csv"
            _write_csv(sample_csv, _sample_rows_fieldnames(sample_rows), sample_rows)
            _write_csv(series_csv, _series_rows_fieldnames(series_rows), series_rows)

            matrix_inventory.append(
                {
                    "cohort_id": cohort_id,
                    "gse_id": gse_id,
                    "matrix_file": rel_matrix,
                    "sample_annotation_csv": str(sample_csv.relative_to(out_root)),
                    "series_metadata_csv": str(series_csv.relative_to(out_root)),
                    "n_samples": str(len(sample_rows)),
                }
            )

            for row in sample_rows:
                merged = {
                    "cohort_id": cohort_id,
                    "gse_id": gse_id,
                    "matrix_file": rel_matrix,
                }
                merged.update(row)
                all_sample_rows.append(merged)

            for row in series_rows:
                merged = {
                    "cohort_id": cohort_id,
                    "gse_id": gse_id,
                    "matrix_file": rel_matrix,
                }
                merged.update(row)
                all_series_rows.append(merged)

            summary_rows.append(
                {
                    "cohort_id": cohort_id,
                    "gse_id": gse_id,
                    "matrix_file": rel_matrix,
                    "n_samples": str(len(sample_rows)),
                    "annotation_fields_present": ";".join(_sample_rows_fieldnames(sample_rows)),
                    "title_prefixes": ";".join(_title_prefixes(sample_rows)),
                    "source_values": _join_unique(sample_rows, "source_name"),
                    "tissue_values": _join_unique(sample_rows, "tissue"),
                    "cell_type_values": _join_unique(sample_rows, "cell_type"),
                    "treatment_values": _join_unique(sample_rows, "treatment"),
                    "n_response_inferred": str(n_resp),
                    "n_nonresponse_inferred": str(n_nonresp),
                    "n_pre_inferred": str(n_pre),
                    "n_transition_inferred": str(n_transition),
                    "scientific_anchor_inferred": inferred_anchor,
                    "scientific_anchor_final": final_anchor,
                    "curation_track": curation_track,
                    "manual_review_status": review_status,
                    "pmid_candidates": pmids,
                }
            )

    inventory_tsv = out_root / "matrix_conversion_inventory.tsv"
    summary_tsv = out_root / "matrix_annotation_summary.tsv"
    all_sample_csv = out_root / "all_sample_annotations.csv"
    all_series_csv = out_root / "all_series_metadata.csv"
    summary_md = out_root / "matrix_annotation_summary.md"

    write_tsv(
        inventory_tsv,
        fieldnames=[
            "cohort_id",
            "gse_id",
            "matrix_file",
            "sample_annotation_csv",
            "series_metadata_csv",
            "n_samples",
        ],
        rows=matrix_inventory,
    )
    write_tsv(
        summary_tsv,
        fieldnames=[
            "cohort_id",
            "gse_id",
            "matrix_file",
            "n_samples",
            "annotation_fields_present",
            "title_prefixes",
            "source_values",
            "tissue_values",
            "cell_type_values",
            "treatment_values",
            "n_response_inferred",
            "n_nonresponse_inferred",
            "n_pre_inferred",
            "n_transition_inferred",
            "scientific_anchor_inferred",
            "scientific_anchor_final",
            "curation_track",
            "manual_review_status",
            "pmid_candidates",
        ],
        rows=summary_rows,
    )
    _write_csv(
        all_sample_csv,
        sorted({key for row in all_sample_rows for key in row.keys()}),
        all_sample_rows,
    )
    _write_csv(
        all_series_csv,
        sorted({key for row in all_series_rows for key in row.keys()}),
        all_series_rows,
    )

    lines = [
        "# GEO Series Matrix Annotation Summary",
        "",
        f"- discovery_manifest: {manifest_path}",
        f"- downloads_root: {downloads_root}",
        f"- n_matrices: {len(summary_rows)}",
        f"- n_cohorts_with_matrices: {len(sorted({row['cohort_id'] for row in summary_rows})) if summary_rows else 0}",
        f"- aggregate_sample_annotation_csv: {all_sample_csv}",
        f"- aggregate_series_metadata_csv: {all_series_csv}",
        "",
        "## Matrix-Level Scientific Anchor Summary",
        "",
        "| cohort_id | gse_id | n_samples | inferred_anchor | final_anchor | curation_track |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row.get('cohort_id', '')} | {row.get('gse_id', '')} | {row.get('n_samples', '')} | "
            f"{row.get('scientific_anchor_inferred', '')} | {row.get('scientific_anchor_final', '')} | "
            f"{row.get('curation_track', '')} |"
        )
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _mark_run(
        args,
        "intake analyze-geo-series-matrix",
        [inventory_tsv, summary_tsv, all_sample_csv, all_series_csv, summary_md],
    )
    print(f"Wrote matrix annotation outputs under {out_root}")
    return 0


def _parse_runinfo_samples(runinfo_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with runinfo_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for rec in reader:
            sample_id = (
                rec.get("SampleName")
                or rec.get("Run")
                or rec.get("Experiment")
                or rec.get("SRAStudy")
                or ""
            ).strip()
            meta_parts = [
                rec.get("LibraryName", ""),
                rec.get("LibraryStrategy", ""),
                rec.get("BioSample", ""),
                rec.get("SampleName", ""),
            ]
            text = " | ".join([p for p in meta_parts if p]).strip()
            response, _ = _infer_response_from_text(text)
            rows.append(
                {
                    "sample_id": sample_id or "unknown_sample",
                    "metadata_text": text,
                    "response_label_inferred": response,
                    "timing_category_inferred": _infer_timing_from_text(text),
                }
            )
    return rows


def cmd_retrieval_run(args: argparse.Namespace) -> int:
    manifest_path = Path(args.discovery_manifest)
    out_dir = Path(args.out)
    out_file = out_dir / "retrieval_ledger.tsv"

    records = read_tsv(manifest_path)
    rows: list[dict[str, str]] = []
    outputs: list[Path] = []
    for rec in records:
        cohort_id = rec.get("cohort_id", "").strip()
        raw_accession = rec.get("accession", "").strip()
        tokens = split_accessions(raw_accession)
        cohort_dir = out_dir / "downloads" / cohort_id
        attempts = 0
        successes = 0
        notes: list[str] = []
        if not args.no_download:
            for token in tokens:
                if token.startswith("GSE"):
                    a, s, n = _download_geo_family_soft(token, cohort_dir)
                    attempts += a
                    successes += s
                    notes.extend(n)
                elif token.startswith(("SRP", "SRX", "SRR", "PRJ")):
                    a, s, n = _download_runinfo(token, cohort_dir)
                    attempts += a
                    successes += s
                    notes.extend(n)

        if args.no_download:
            retrieval_status = "not_started"
            retrieval_note = "download_skipped_by_flag"
        elif attempts == 0:
            retrieval_status = "not_started"
            retrieval_note = "no_supported_accessions_for_download"
        elif successes == attempts:
            retrieval_status = "downloaded"
            retrieval_note = f"downloaded {successes}/{attempts}"
        elif successes == 0:
            retrieval_status = "failed"
            retrieval_note = f"downloaded 0/{attempts}; {'; '.join(notes[:6])}"
        else:
            retrieval_status = "partial"
            retrieval_note = f"downloaded {successes}/{attempts}; {'; '.join(notes[:6])}"

        rows.append(
            {
                "cohort_id": cohort_id,
                "input_accession": raw_accession,
                "gse_id": _join_tokens(tokens, ("GSE", "GSM", "GPL")),
                "srp_id": _join_tokens(tokens, ("SRP",)),
                "srx_id": _join_tokens(tokens, ("SRX",)),
                "srr_id": _join_tokens(tokens, ("SRR",)),
                "bioproject_id": _join_tokens(tokens, ("PRJ", "BIOPROJECT")),
                "source_db": infer_source_db(tokens),
                "source_uri": build_source_uri(tokens),
                "retrieval_status": retrieval_status,
                "retrieval_timestamp": _timestamp_utc(),
                "retrieval_note": retrieval_note,
            }
        )
        outputs.append(cohort_dir)

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "input_accession",
            "gse_id",
            "srp_id",
            "srx_id",
            "srr_id",
            "bioproject_id",
            "source_db",
            "source_uri",
            "retrieval_status",
            "retrieval_timestamp",
            "retrieval_note",
        ],
        rows=rows,
    )
    _mark_run(args, "retrieval run", [out_file, *outputs])
    print(f"Wrote {out_file}")
    return 0


def cmd_retrieval_geo_full(args: argparse.Namespace) -> int:
    manifest_path = Path(args.discovery_manifest)
    out_root = Path(args.out)
    out_file = out_root.parent / "geo_full_retrieval_ledger.tsv"

    records = read_tsv(manifest_path)
    rows: list[dict[str, str]] = []
    outputs: list[Path] = []

    for rec in records:
        cohort_id = rec.get("cohort_id", "").strip()
        tokens = split_accessions(rec.get("accession", ""))
        gse_tokens = [tok for tok in tokens if tok.startswith("GSE")]
        sra_tokens = [tok for tok in tokens if tok.startswith(("SRP", "SRX", "SRR", "PRJ"))]
        cohort_dir = out_root / cohort_id

        attempts = 0
        successes = 0
        notes: list[str] = []
        matrix_success = 0
        suppl_success = 0
        runinfo_success = 0
        soft_success = 0

        if args.no_download:
            retrieval_status = "not_started"
            retrieval_note = "download_skipped_by_flag"
        else:
            for gse_id in gse_tokens:
                a, s, n = _download_geo_family_soft(gse_id, cohort_dir)
                attempts += a
                successes += s
                soft_success += s
                notes.extend(n)

                a, s, n = _download_geo_series_matrix(gse_id, cohort_dir / gse_id / "matrix")
                attempts += a
                successes += s
                matrix_success += s
                notes.extend(n)

                if not args.skip_suppl:
                    a, s, n = _download_geo_supplementary(gse_id, cohort_dir / gse_id / "suppl")
                    attempts += a
                    successes += s
                    suppl_success += s
                    notes.extend(n)

            if not args.skip_runinfo:
                for accession in sra_tokens:
                    a, s, n = _download_runinfo(accession, cohort_dir)
                    attempts += a
                    successes += s
                    runinfo_success += s
                    notes.extend(n)

            if attempts == 0:
                retrieval_status = "not_started"
                retrieval_note = "no_supported_accessions_for_download"
            elif successes == attempts:
                retrieval_status = "downloaded"
                retrieval_note = f"downloaded {successes}/{attempts}"
            elif successes == 0:
                retrieval_status = "failed"
                retrieval_note = f"downloaded 0/{attempts}; {'; '.join(notes[:8])}"
            else:
                retrieval_status = "partial"
                retrieval_note = f"downloaded {successes}/{attempts}; {'; '.join(notes[:8])}"

        rows.append(
            {
                "cohort_id": cohort_id,
                "gse_ids": ";".join(gse_tokens),
                "sra_ids": ";".join(sra_tokens),
                "retrieval_status": retrieval_status,
                "n_download_attempts": attempts,
                "n_download_successes": successes,
                "n_soft_files_downloaded": soft_success,
                "n_matrix_files_downloaded": matrix_success,
                "n_suppl_files_downloaded": suppl_success,
                "n_runinfo_files_downloaded": runinfo_success,
                "retrieval_timestamp": _timestamp_utc(),
                "retrieval_note": retrieval_note,
            }
        )
        outputs.append(cohort_dir)

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "gse_ids",
            "sra_ids",
            "retrieval_status",
            "n_download_attempts",
            "n_download_successes",
            "n_soft_files_downloaded",
            "n_matrix_files_downloaded",
            "n_suppl_files_downloaded",
            "n_runinfo_files_downloaded",
            "retrieval_timestamp",
            "retrieval_note",
        ],
        rows=rows,
    )
    _mark_run(args, "retrieval geo-full", [out_file, *outputs])
    print(f"Wrote {out_file}")
    return 0


def _compound_ext(path: Path) -> str:
    name = path.name.lower()
    for ext in [
        ".fastq.gz",
        ".fq.gz",
        ".txt.gz",
        ".tsv.gz",
        ".csv.gz",
        ".tar.gz",
        ".bed.gz",
        ".idat.gz",
    ]:
        if name.endswith(ext):
            return ext
    return path.suffix.lower()


def _infer_geo_data_mode(
    matrix_files: list[Path],
    suppl_files: list[Path],
) -> str:
    all_files = matrix_files + suppl_files
    if not all_files:
        return "metadata_only"
    names = [f.name.lower() for f in all_files]
    if any(n.endswith((".fastq.gz", ".fq.gz")) for n in names):
        return "raw_fastq_in_geo"
    if any("count" in n or "htseq" in n for n in names):
        return "raw_counts_or_count_like"
    if matrix_files or any("fpkm" in n or "tpm" in n or "normalized" in n or "rpkm" in n for n in names):
        return "processed_matrix_or_normalized_table"
    if any("idat" in n or "450k" in n or "epic" in n or "methyl" in n for n in names):
        return "methylation_array_or_bisulfite_tables"
    return "supplementary_tables_mixed"


def cmd_retrieval_geo_manifest(args: argparse.Namespace) -> int:
    manifest_path = Path(args.discovery_manifest)
    downloads_root = Path(args.downloads_root)
    out_file = Path(args.out)
    summary_file = out_file.with_suffix(".md")

    records = read_tsv(manifest_path)
    rows: list[dict[str, str]] = []
    n_core_complete = 0
    for rec in records:
        cohort_id = rec.get("cohort_id", "").strip()
        tokens = split_accessions(rec.get("accession", ""))
        gse_tokens = [tok for tok in tokens if tok.startswith("GSE")]
        cohort_dir = downloads_root / cohort_id
        soft_files = sorted(cohort_dir.glob("GSE*_family.soft.gz"))
        runinfo_files = sorted(cohort_dir.glob("*_runinfo.csv"))
        matrix_files = sorted(
            [p for p in cohort_dir.glob("**/matrix/*") if p.is_file() and not p.name.endswith(".part")]
        )
        suppl_files = sorted(
            [p for p in cohort_dir.glob("**/suppl/*") if p.is_file() and not p.name.endswith(".part")]
        )
        all_files = soft_files + runinfo_files + matrix_files + suppl_files
        gse_soft_found = sorted({p.name.split("_family.soft.gz")[0] for p in soft_files})

        core_complete = bool(gse_tokens) and all(gse in gse_soft_found for gse in gse_tokens)
        if core_complete:
            n_core_complete += 1

        exts = sorted({_compound_ext(path) for path in (matrix_files + suppl_files)})
        mode = _infer_geo_data_mode(matrix_files, suppl_files)
        n_raw_archives = sum(
            1 for p in suppl_files if p.name.lower().endswith((".tar", ".tar.gz", ".zip", ".tgz"))
        )
        total_bytes = sum((p.stat().st_size for p in all_files), 0)
        if mode in {"raw_fastq_in_geo", "raw_counts_or_count_like"}:
            recommended_input = "raw_counts_or_fastq_path"
        elif mode == "processed_matrix_or_normalized_table":
            recommended_input = "processed_matrix"
        elif mode == "metadata_only":
            recommended_input = "manual_fetch_additional_files"
        else:
            recommended_input = "mixed_manual_routing"

        rows.append(
            {
                "cohort_id": cohort_id,
                "gse_ids_expected": ";".join(gse_tokens),
                "gse_ids_soft_downloaded": ";".join(gse_soft_found),
                "n_soft_files": len(soft_files),
                "n_matrix_files": len(matrix_files),
                "n_suppl_files": len(suppl_files),
                "n_runinfo_files": len(runinfo_files),
                "n_raw_archive_files": n_raw_archives,
                "cohort_download_size_gb": round(total_bytes / (1024**3), 3),
                "matrix_files": ";".join([str(p.relative_to(cohort_dir)) for p in matrix_files[:40]]),
                "suppl_files_sample": ";".join([str(p.relative_to(cohort_dir)) for p in suppl_files[:40]]),
                "suppl_extensions": ";".join(exts),
                "geo_core_complete": "true" if core_complete else "false",
                "geo_extended_has_matrix_or_suppl": "true" if (matrix_files or suppl_files) else "false",
                "inferred_data_mode": mode,
                "recommended_input_route": recommended_input,
            }
        )

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "gse_ids_expected",
            "gse_ids_soft_downloaded",
            "n_soft_files",
            "n_matrix_files",
            "n_suppl_files",
            "n_runinfo_files",
            "n_raw_archive_files",
            "cohort_download_size_gb",
            "matrix_files",
            "suppl_files_sample",
            "suppl_extensions",
            "geo_core_complete",
            "geo_extended_has_matrix_or_suppl",
            "inferred_data_mode",
            "recommended_input_route",
        ],
        rows=rows,
    )

    summary_lines = [
        "# GEO Data-Type Manifest",
        "",
        f"- discovery_manifest: {manifest_path}",
        f"- downloads_root: {downloads_root}",
        f"- n_cohorts: {len(rows)}",
        f"- geo_core_complete_cohorts: {n_core_complete}",
        "",
        "## Per-Study Confirmation",
        "",
        "| cohort_id | core_complete | soft | matrix | suppl | runinfo | raw_archives | size_gb | mode | route |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row.get('cohort_id', '')} | {row.get('geo_core_complete', '')} | "
            f"{row.get('n_soft_files', '')} | {row.get('n_matrix_files', '')} | "
            f"{row.get('n_suppl_files', '')} | {row.get('n_runinfo_files', '')} | "
            f"{row.get('n_raw_archive_files', '')} | {row.get('cohort_download_size_gb', '')} | "
            f"{row.get('inferred_data_mode', '')} | {row.get('recommended_input_route', '')} |"
        )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    _mark_run(args, "retrieval geo-manifest", [out_file, summary_file])
    print(f"Wrote {out_file} and {summary_file}")
    return 0


def cmd_intake_inspect(args: argparse.Namespace) -> int:
    ledger_path = Path(args.retrieval_ledger)
    out_dir = Path(args.out)
    out_file = out_dir / "dataset_inspection.tsv"

    rows: list[dict[str, str]] = []
    for row in read_tsv(ledger_path):
        cohort_id = row.get("cohort_id", "")
        input_class = _infer_input_class(row)
        if input_class == "FASTQ":
            file_format = "fastq.gz"
            normalization_state = "raw_unprocessed"
        elif input_class == "raw_counts":
            file_format = "tsv"
            normalization_state = "raw_counts"
        else:
            file_format = "tsv"
            normalization_state = "processed_normalized_or_unknown"
        cohort_dir = ledger_path.parent / "downloads" / cohort_id
        soft_files = sorted(cohort_dir.glob("GSE*_family.soft.gz"))
        runinfo_files = sorted(cohort_dir.glob("*_runinfo.csv"))

        parsed_samples: list[dict[str, str]] = []
        for soft in soft_files:
            parsed_samples.extend(_parse_geo_soft_samples(soft))
        if not parsed_samples:
            for runinfo in runinfo_files:
                parsed_samples.extend(_parse_runinfo_samples(runinfo))

        dedup: dict[str, dict[str, str]] = {}
        for sample in parsed_samples:
            sid = (sample.get("sample_id", "") or "").strip()
            if not sid:
                continue
            dedup.setdefault(sid, sample)

        selected_samples = list(dedup.values())[: args.max_samples_per_cohort]
        if not selected_samples:
            selected_samples = [
                {
                    "sample_id": f"{cohort_id}__sample_01",
                    "metadata_text": "",
                    "response_label_inferred": "unknown",
                    "timing_category_inferred": "unknown",
                }
            ]

        for sample in selected_samples:
            rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": sample.get("sample_id", ""),
                    "assay_type": "bulk RNA-seq",
                    "file_format": file_format,
                    "input_class": input_class,
                    "read_layout": "single_or_paired_unknown",
                    "is_paired_sample": "false",
                    "normalization_state": normalization_state,
                    "intake_include_flag": "true",
                    "intake_exclude_reason": "",
                    "response_label_inferred": sample.get("response_label_inferred", "unknown"),
                    "timing_category_inferred": sample.get("timing_category_inferred", "unknown"),
                    "metadata_text": sample.get("metadata_text", ""),
                }
            )

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "assay_type",
            "file_format",
            "input_class",
            "read_layout",
            "is_paired_sample",
            "normalization_state",
            "intake_include_flag",
            "intake_exclude_reason",
            "response_label_inferred",
            "timing_category_inferred",
            "metadata_text",
        ],
        rows=rows,
    )
    _mark_run(args, "intake inspect", [out_file])
    print(f"Wrote {out_file}")
    return 0


def _guess_source_type_from_filename(name: str) -> str:
    low = (name or "").lower()
    if any(tok in low for tok in ["raw_count", "rawcounts", "counts", "htseq", "featurecounts"]):
        return "raw_counts"
    if any(tok in low for tok in ["tpm", "fpkm", "rpkm", "normalized", "norm", "series_matrix", "log_trans"]):
        return "processed_matrix"
    return "unknown"


def _is_archive_file(name: str) -> bool:
    low = (name or "").lower()
    return low.endswith((".tar", ".tar.gz", ".zip", ".tgz"))


def _is_table_like_file(name: str) -> bool:
    low = (name or "").lower()
    return low.endswith(
        (
            ".txt",
            ".txt.gz",
            ".tsv",
            ".tsv.gz",
            ".csv",
            ".csv.gz",
            ".xlsx",
            ".xls",
            ".mtx",
            ".mtx.gz",
        )
    )


def _rank_expression_candidate(path: Path, preferred_source_type: str) -> int:
    name = path.name.lower()
    score = 0
    real_expression_tokens = [
        "raw_count",
        "rawcounts",
        "readcount",
        "read_count",
        "featurecount",
        "featurecounts",
        "counts",
        "count_matrix",
        "tpm",
        "fpkm",
        "rpkm",
        "cpm",
        "log2tpm",
        "log2cpm",
        "normalized",
    ]
    metadata_tokens = ["metadata", "clinical", "annotation", "phenotype", "pheno", "sampleinfo"]
    if any(tok in name for tok in real_expression_tokens):
        score += 7
    if "series_matrix" in name:
        score += 2
    if any(tok in name for tok in metadata_tokens):
        score -= 4
    source_type = _guess_source_type_from_filename(name)
    if source_type == preferred_source_type:
        score += 5
    if _is_archive_file(name):
        score -= 5
    return score


def _validate_expression_candidate(path: Path, data_modality: str) -> tuple[str, str, str]:
    if data_modality != "expression_table":
        return "not_checked", "", ""
    try:
        matrix = load_expression_matrix(path)
    except Exception:  # noqa: BLE001
        return "empty_or_unreadable", "0", "0"
    if matrix is None or matrix.empty or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        return "empty_or_unreadable", "0", "0"
    return "loadable", str(matrix.shape[0]), str(matrix.shape[1])


def _ensure_candidate_load_validation(candidate: dict[str, str], cohort_dir: Path) -> None:
    if candidate.get("load_validation_status") != "not_checked":
        return
    rel_path = candidate.get("file_path", "")
    path = cohort_dir / rel_path
    load_status, loaded_genes, loaded_samples = _validate_expression_candidate(
        path,
        candidate.get("data_modality", ""),
    )
    candidate["load_validation_status"] = load_status
    candidate["n_loaded_genes"] = loaded_genes
    candidate["n_loaded_samples"] = loaded_samples


def _select_primary_expression_file(
    sorted_candidates: list[dict[str, str]],
    *,
    cohort_dir: Path,
    source_type_selected: str,
) -> str:
    def _candidate_allowed(cand: dict[str, str], *, require_source_match: bool) -> bool:
        if cand.get("data_modality") != "expression_table":
            return False
        if require_source_match and source_type_selected != "unknown":
            if cand.get("source_type_candidate") != source_type_selected:
                return False
        _ensure_candidate_load_validation(cand, cohort_dir)
        if cand.get("load_validation_status") != "loadable":
            return False
        return True

    for require_source_match in (True, False):
        for cand in sorted_candidates:
            if _candidate_allowed(cand, require_source_match=require_source_match):
                return cand.get("file_path", "")
    return ""


def cmd_intake_build_geo_tables(args: argparse.Namespace) -> int:
    discovery_rows = read_tsv(Path(args.discovery_manifest))
    downloads_root = Path(args.downloads_root)
    out_root = Path(args.out)
    routing_map: dict[str, dict[str, str]] = {}
    routing_path = Path(args.routing_manifest)
    if routing_path.exists():
        routing_map = {row.get("cohort_id", ""): row for row in read_tsv(routing_path)}

    aggregate_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    n_raw_route = 0
    n_processed_route = 0
    n_unknown_route = 0

    for disc in discovery_rows:
        cohort_id = disc.get("cohort_id", "").strip()
        cohort_dir = downloads_root / cohort_id
        cohort_out = out_root / cohort_id
        if not cohort_id:
            continue

        preferred_route = routing_map.get(cohort_id, {}).get("recommended_input_route", "").strip()
        if preferred_route == "raw_counts_or_fastq_path":
            source_type_selected = "raw_counts"
            n_raw_route += 1
        elif preferred_route == "processed_matrix":
            source_type_selected = "processed_matrix"
            n_processed_route += 1
        else:
            source_type_selected = "unknown"
            n_unknown_route += 1

        soft_files = sorted(cohort_dir.glob("GSE*_family.soft.gz"))
        sample_rows: list[dict[str, str]] = []
        for soft_path in soft_files:
            try:
                parsed = _parse_geo_soft_samples(soft_path)
            except Exception:  # noqa: BLE001
                parsed = []
            for rec in parsed:
                sid = rec.get("sample_id", "")
                sample_rows.append(
                    {
                        "sample_id": sid,
                        "patient_id": sid,
                        "response_label_inferred": rec.get("response_label_inferred", "unknown"),
                        "timing_category_inferred": rec.get("timing_category_inferred", "unknown"),
                        "metadata_text": rec.get("metadata_text", ""),
                    }
                )
        if not sample_rows:
            sample_rows = [
                {
                    "sample_id": f"{cohort_id}__sample_01",
                    "patient_id": cohort_id,
                    "response_label_inferred": "unknown",
                    "timing_category_inferred": "unknown",
                    "metadata_text": "",
                }
            ]

        dedup_samples: dict[str, dict[str, str]] = {}
        for row in sample_rows:
            dedup_samples.setdefault(row["sample_id"], row)
        sample_rows = list(dedup_samples.values())

        candidate_paths = sorted(
            [
                p
                for p in cohort_dir.glob("**/*")
                if p.is_file() and not p.name.endswith(".part")
            ]
        )
        expression_candidates: list[dict[str, str]] = []
        for path in candidate_paths:
            rel = str(path.relative_to(cohort_dir))
            name = path.name
            if "filelist.txt" in name.lower():
                continue
            is_archive = _is_archive_file(name)
            is_table = _is_table_like_file(name)
            modality = "expression_table" if is_table and not is_archive else ("archive" if is_archive else "other")
            source_type_candidate = _guess_source_type_from_filename(name)
            rank = _rank_expression_candidate(path, source_type_selected)
            expression_candidates.append(
                {
                    "cohort_id": cohort_id,
                    "file_path": rel,
                    "file_name": name,
                    "source_type_candidate": source_type_candidate,
                    "data_modality": modality,
                    "is_archive": "true" if is_archive else "false",
                    "size_bytes": str(path.stat().st_size),
                    "rank_score": str(rank),
                    "load_validation_status": "not_checked" if modality == "expression_table" else "not_applicable",
                    "n_loaded_genes": "",
                    "n_loaded_samples": "",
                }
            )

        sorted_candidates = sorted(
            expression_candidates,
            key=lambda r: int(r.get("rank_score", "0") or 0),
            reverse=True,
        )
        primary_file = _select_primary_expression_file(
            sorted_candidates,
            cohort_dir=cohort_dir,
            source_type_selected=source_type_selected,
        )

        cohort_input_rows: list[dict[str, str]] = []
        for sample in sample_rows:
            cohort_input_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": sample.get("sample_id", ""),
                    "patient_id": sample.get("patient_id", ""),
                    "cancer_type": disc.get("cancer_type", ""),
                    "therapy_agent": disc.get("therapy_agent", ""),
                    "response_label_inferred": sample.get("response_label_inferred", "unknown"),
                    "timing_category_inferred": sample.get("timing_category_inferred", "unknown"),
                    "source_type_selected": source_type_selected,
                    "preferred_input_route": preferred_route or "unknown",
                    "primary_expression_file": primary_file,
                    "analysis_ready_flag": (
                        "true"
                        if primary_file
                        and sample.get("response_label_inferred", "unknown") in {"responder", "non_responder"}
                        else "false"
                    ),
                }
            )
        aggregate_rows.extend(cohort_input_rows)

        write_tsv(
            cohort_out / "sample_metadata.tsv",
            fieldnames=[
                "sample_id",
                "patient_id",
                "response_label_inferred",
                "timing_category_inferred",
                "metadata_text",
            ],
            rows=sample_rows,
        )
        write_tsv(
            cohort_out / "clinical_annotation.tsv",
            fieldnames=[
                "sample_id",
                "response_label_inferred",
                "timing_category_inferred",
                "cancer_type",
                "therapy_agent",
                "notes",
            ],
            rows=[
                {
                    "sample_id": s.get("sample_id", ""),
                    "response_label_inferred": s.get("response_label_inferred", "unknown"),
                    "timing_category_inferred": s.get("timing_category_inferred", "unknown"),
                    "cancer_type": disc.get("cancer_type", ""),
                    "therapy_agent": disc.get("therapy_agent", ""),
                    "notes": "",
                }
                for s in sample_rows
            ],
        )
        write_tsv(
            cohort_out / "expression_file_manifest.tsv",
            fieldnames=[
                "cohort_id",
                "file_path",
                "file_name",
                "source_type_candidate",
                "data_modality",
                "is_archive",
                "size_bytes",
                "rank_score",
                "load_validation_status",
                "n_loaded_genes",
                "n_loaded_samples",
            ],
            rows=sorted_candidates,
        )
        write_tsv(
            cohort_out / "cohort_input_table.tsv",
            fieldnames=[
                "cohort_id",
                "sample_id",
                "patient_id",
                "cancer_type",
                "therapy_agent",
                "response_label_inferred",
                "timing_category_inferred",
                "source_type_selected",
                "preferred_input_route",
                "primary_expression_file",
                "analysis_ready_flag",
            ],
            rows=cohort_input_rows,
        )
        summary_rows.append(
            {
                "cohort_id": cohort_id,
                "n_samples": len(sample_rows),
                "n_expression_candidates": len(sorted_candidates),
                "source_type_selected": source_type_selected,
                "primary_expression_file": primary_file,
            }
        )

    write_tsv(
        out_root / "cohort_input_table_all.tsv",
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_agent",
            "response_label_inferred",
            "timing_category_inferred",
            "source_type_selected",
            "preferred_input_route",
            "primary_expression_file",
            "analysis_ready_flag",
        ],
        rows=aggregate_rows,
    )
    write_tsv(
        out_root / "geo_tables_summary.tsv",
        fieldnames=[
            "cohort_id",
            "n_samples",
            "n_expression_candidates",
            "source_type_selected",
            "primary_expression_file",
        ],
        rows=summary_rows,
    )
    summary_md = out_root / "geo_tables_summary.md"
    summary_lines = [
        "# GEO Tables Summary",
        "",
        f"- n_cohorts: {len(summary_rows)}",
        f"- source_type_raw_counts: {n_raw_route}",
        f"- source_type_processed_matrix: {n_processed_route}",
        f"- source_type_unknown: {n_unknown_route}",
        "",
        "## Cohort Table Outputs",
        "",
        "| cohort_id | n_samples | source_type_selected | primary_expression_file |",
        "| --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        summary_lines.append(
            f"| {row.get('cohort_id', '')} | {row.get('n_samples', '')} | "
            f"{row.get('source_type_selected', '')} | {row.get('primary_expression_file', '')} |"
        )
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    outputs = [
        out_root / "cohort_input_table_all.tsv",
        out_root / "geo_tables_summary.tsv",
        summary_md,
    ]
    _mark_run(args, "intake build-geo-tables", outputs)
    print(f"Wrote GEO tables under {out_root}")
    return 0


def _load_curated_label_map(path: Path) -> dict[str, dict[str, str]]:
    """Map GSM sample_id -> curated {response_label, timing_category}.

    GSM accessions are globally unique, so sample_id alone is a safe join key
    across the cohort-id naming differences between the retrieval-derived and
    hand-curated manifests (Spec 010 Gate-2 label join).
    """
    mapping: dict[str, dict[str, str]] = {}
    if not path or not path.exists():
        return mapping
    for row in read_tsv(path):
        sid = (row.get("sample_id", "") or "").strip()
        if not sid:
            continue
        mapping[sid] = {
            "response_label": _canonical_response(row.get("response_label", "")),
            "timing_category": _canonical_timing(row.get("timing_category", "")),
        }
    return mapping


def cmd_intake_build_geo_sample_manifest(args: argparse.Namespace) -> int:
    cohort_rows = read_tsv(Path(args.cohort_input_table))
    out_manifest = Path(args.out)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)

    curated_arg = getattr(args, "curated_manifest", "") or ""
    curated_labels = _load_curated_label_map(Path(curated_arg)) if curated_arg else {}
    n_curated_response = 0
    n_curated_timing = 0

    allow_raw = not args.processed_only
    eligible_source_types = {"processed_matrix"} if args.processed_only else {"processed_matrix", "raw_counts"}

    by_cohort_patient: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in cohort_rows:
        cohort_id = row.get("cohort_id", "")
        patient_id = row.get("patient_id", "") or row.get("sample_id", "")
        timing = _canonical_timing(row.get("timing_category_inferred", ""))
        by_cohort_patient[(cohort_id, patient_id)].add(timing)

    sample_rows: list[dict[str, str]] = []
    ready_rows: list[dict[str, str]] = []
    n_ready = 0
    n_excluded = 0
    n_processed = 0
    n_raw = 0

    for row in cohort_rows:
        cohort_id = row.get("cohort_id", "")
        sample_id = row.get("sample_id", "")
        patient_id = row.get("patient_id", "") or sample_id
        therapy_agent = row.get("therapy_agent", "")
        source_type = (row.get("source_type_selected", "") or "").strip().lower()
        response_label = _canonical_response(row.get("response_label_inferred", ""))
        timing_category = _canonical_timing(row.get("timing_category_inferred", ""))
        # Spec 010 Gate-2 fix: join hand-curated labels by GSM sample_id. The
        # curated sheet is authoritative; retrieval inference is the fallback.
        curated = curated_labels.get(sample_id) or {}
        cur_resp = curated.get("response_label", "")
        cur_timing = curated.get("timing_category", "")
        response_from_curation = False
        if cur_resp in {"responder", "non_responder"}:
            if response_label != cur_resp:
                n_curated_response += 1
            response_label = cur_resp
            response_from_curation = True
        if cur_timing and cur_timing != "unknown":
            if timing_category != cur_timing:
                n_curated_timing += 1
            timing_category = cur_timing
        # Spec 010/011 contract: honor Stage-01 assay declarations first, then
        # fall back to source-type heuristics for legacy inputs.
        assay_type = (
            _canonical_assay_type(row.get("assay_type_override", ""))
            or _canonical_assay_type(row.get("assay_type", ""))
        )
        if not assay_type:
            if source_type == "raw_counts":
                assay_type = "raw_counts"
            elif source_type == "processed_matrix":
                assay_type = "normalized_other"
            else:
                assay_type = "unreadable"
        timing_provenance = (
            "manual_curation_sheet"
            if cur_timing and cur_timing != "unknown"
            else "curated"
            if timing_category != "unknown"
            else "default_pre"
        )
        response_definition_id = "rdef_" + hashlib.sha1(
            f"{cohort_id}|{response_label}|{source_type}".encode("utf-8")
        ).hexdigest()[:12]

        if source_type == "processed_matrix":
            n_processed += 1
        elif source_type == "raw_counts":
            n_raw += 1

        reasons: list[str] = []
        if source_type not in eligible_source_types:
            reasons.append(f"source_type_not_enabled:{source_type or 'unknown'}")
        if response_label == "unknown":
            reasons.append("response_unknown")
        if timing_category == "unknown":
            reasons.append("timing_unknown")
        cohort_gate_reason = _cohort_contract_exclusion_reason(
            cohort_id,
            [
                {
                    "assay_type": assay_type,
                    "input_class": source_type,
                }
            ],
        )
        if cohort_gate_reason:
            reasons.append(cohort_gate_reason)

        pair_key = (cohort_id, patient_id)
        pair_timings = by_cohort_patient.get(pair_key, set())
        has_transition = "pre-treatment" in pair_timings and (
            "on-treatment" in pair_timings or "post-treatment" in pair_timings
        )
        pair_id = patient_id if has_transition else ""

        include = len(reasons) == 0
        manifest_row = {
            "cohort_id": cohort_id,
            "sample_id": sample_id,
            "patient_id": patient_id,
            "cancer_type": row.get("cancer_type", ""),
            "therapy_class": _infer_therapy_class(therapy_agent),
            "therapy_agent": therapy_agent,
            "specimen_type": "bulk tumor sample",
            "timing_category": timing_category,
            "response_label": response_label,
            "pair_id": pair_id,
            "input_class": source_type if source_type else "unknown",
            "assay_type": assay_type,
            "assay_type_override": "",
            "analysis_role": "analysis",
            "include_flag": "true" if include else "false",
            "exclude_reason": "" if include else ";".join(reasons),
            "response_label_source": (
                "manual_curation_sheet_applied"
                if response_from_curation
                else "geo_tables_inference"
                if response_label in {"responder", "non_responder"}
                else "pending_manual_curation"
            ),
            "response_definition_id": response_definition_id,
            "timing_provenance": timing_provenance,
        }
        sample_rows.append(manifest_row)

        if include:
            n_ready += 1
            ready_rows.append(manifest_row)
        else:
            n_excluded += 1

    if args.ready_only:
        write_rows = ready_rows
    else:
        write_rows = sample_rows

    unique_pre_treatment_cohorts_ready = len(
        {
            row.get("cohort_id", "")
            for row in ready_rows
            if row.get("cohort_id", "") and row.get("timing_category", "") == "pre-treatment"
        }
    )
    expected_pre_treatment_cohorts = int(getattr(args, "expected_pre_treatment_cohorts", 21))
    strict_pre_treatment_denominator = bool(getattr(args, "strict_pre_treatment_denominator", False))
    pre_treatment_cohort_denominator_check = (
        "match"
        if unique_pre_treatment_cohorts_ready == expected_pre_treatment_cohorts
        else "mismatch"
    )

    write_tsv(
        out_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "pair_id",
            "input_class",
            "assay_type",
            "assay_type_override",
            "analysis_role",
            "include_flag",
            "exclude_reason",
            "response_label_source",
            "response_definition_id",
            "timing_provenance",
        ],
        rows=write_rows,
    )

    ready_out = Path(args.ready_out)
    ready_out.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        ready_out,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "pair_id",
            "input_class",
            "assay_type",
            "assay_type_override",
            "analysis_role",
            "include_flag",
            "exclude_reason",
            "response_label_source",
            "response_definition_id",
            "timing_provenance",
        ],
        rows=ready_rows,
    )

    summary_out = Path(args.summary_out)
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_lines = [
        "# GEO Sample Manifest Build",
        "",
        f"- cohort_input_table: {Path(args.cohort_input_table)}",
        f"- processed_only: {'true' if args.processed_only else 'false'}",
        f"- ready_only: {'true' if args.ready_only else 'false'}",
        f"- allow_raw_counts: {'true' if allow_raw else 'false'}",
        f"- n_rows_total: {len(sample_rows)}",
        f"- n_rows_ready: {n_ready}",
        f"- n_rows_excluded: {n_excluded}",
        f"- n_rows_processed_matrix: {n_processed}",
        f"- n_rows_raw_counts: {n_raw}",
        f"- curated_manifest: {curated_arg or '(disabled)'}",
        f"- n_curated_label_rows: {len(curated_labels)}",
        f"- n_response_labels_from_curation: {n_curated_response}",
        f"- n_timing_labels_from_curation: {n_curated_timing}",
        f"- n_unique_pre_treatment_cohorts_ready: {unique_pre_treatment_cohorts_ready}",
        f"- expected_unique_pre_treatment_cohorts: {expected_pre_treatment_cohorts}",
        f"- pre_treatment_cohort_denominator_check: {pre_treatment_cohort_denominator_check}",
        f"- output_manifest: {out_manifest}",
        f"- ready_manifest: {ready_out}",
    ]
    summary_out.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if strict_pre_treatment_denominator and pre_treatment_cohort_denominator_check != "match":
        raise RuntimeError(
            "pre-treatment cohort denominator mismatch: "
            f"observed={unique_pre_treatment_cohorts_ready}, "
            f"expected={expected_pre_treatment_cohorts}"
        )

    _mark_run(args, "intake build-geo-sample-manifest", [out_manifest, ready_out, summary_out])
    print(f"Wrote {out_manifest}, {ready_out}, and {summary_out}")
    return 0


def cmd_intake_gene_audit(args: argparse.Namespace) -> int:
    """
    Audit and standardize cohort expression gene IDs before downstream modeling.
    """
    manifest_path = Path(args.sample_manifest)
    rows = read_tsv(manifest_path)
    if not rows:
        raise RuntimeError(f"Sample manifest is empty: {manifest_path}")

    include_excluded = bool(getattr(args, "include_excluded", False))
    allow_stub_rows = bool(getattr(args, "allow_stub_rows", False))
    strict = bool(getattr(args, "strict", False))

    def _allowed(row: dict[str, str]) -> bool:
        if not include_excluded and not parse_bool(row.get("include_flag", "false"), default=False):
            return False
        if not allow_stub_rows and row.get("sync_status", "").strip() == "added_cohort_stub_no_sample_rows":
            return False
        return True

    cohorts = sorted({r.get("cohort_id", "") for r in rows if r.get("cohort_id") and _allowed(r)})
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    mapping_path = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    min_hgnc_mapping_rate = float(getattr(args, "min_hgnc_mapping_rate", 0.60))
    max_unmapped_ensembl_fraction = float(getattr(args, "max_unmapped_ensembl_fraction", 0.20))
    max_duplicate_collapse_fraction = float(getattr(args, "max_duplicate_collapse_fraction", 0.25))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))

    summary_rows: list[dict[str, str]] = []
    failed_rows: list[dict[str, str]] = []
    outputs: list[Path] = []

    for cohort_id in cohorts:
        cohort_rows = [r for r in rows if r.get("cohort_id", "") == cohort_id and _allowed(r)]
        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        input_classes = sorted({(r.get("input_class", "") or "").strip().lower() for r in cohort_rows if r.get("input_class", "")})
        agg_method = "sum" if input_classes == ["raw_counts"] else "mean"

        if expr is None or expr.empty:
            summary_rows.append(
                {
                    "cohort_id": cohort_id,
                    "expression_file": str(expr_path or ""),
                    "aggregation_method": agg_method,
                    "n_genes_raw": "0",
                    "n_genes_canonical": "0",
                    "n_collapsed_duplicates": "0",
                    "collapsed_duplicate_fraction": "0.000000",
                    "n_ensembl_like": "0",
                    "n_symbol_like": "0",
                    "n_other_ids": "0",
                    "n_with_version_suffix": "0",
                    "n_mapped_to_hgnc": "0",
                    "mapped_fraction": "0.000000",
                    "n_alias_mapped": "0",
                    "alias_mapped_fraction": "0.000000",
                    "n_unmapped_ensembl": "0",
                    "unmapped_ensembl_fraction": "0.000000",
                    "status": "missing_expression",
                    "fail_reason": "no_expression_matrix",
                }
            )
            continue

        _, _, metrics = _standardize_expression_gene_ids(expr, mapping_path=mapping_path, aggregation=agg_method)
        status, fail_reason = _evaluate_gene_id_quality(
            metrics,
            min_hgnc_mapping_rate=min_hgnc_mapping_rate,
            max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
            max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
        )

        row_out = {
            "cohort_id": cohort_id,
            "expression_file": str(expr_path or ""),
            "aggregation_method": agg_method,
            **metrics,
            "status": status,
            "fail_reason": fail_reason,
        }
        summary_rows.append(row_out)
        if status != "pass":
            failed_rows.append(row_out)

    summary_file = out_root / "gene_id_audit_by_cohort.tsv"
    failed_file = out_root / "gene_id_audit_failed.tsv"
    summary_md = out_root / "gene_id_audit_summary.md"

    write_tsv(
        summary_file,
        fieldnames=[
            "cohort_id",
            "expression_file",
            "aggregation_method",
            "n_genes_raw",
            "n_genes_canonical",
            "n_collapsed_duplicates",
            "collapsed_duplicate_fraction",
            "n_ensembl_like",
            "n_symbol_like",
            "n_other_ids",
            "n_with_version_suffix",
            "n_mapped_to_hgnc",
            "mapped_fraction",
            "n_alias_mapped",
            "alias_mapped_fraction",
            "n_unmapped_ensembl",
            "unmapped_ensembl_fraction",
            "status",
            "fail_reason",
        ],
        rows=summary_rows,
    )
    write_tsv(
        failed_file,
        fieldnames=[
            "cohort_id",
            "expression_file",
            "aggregation_method",
            "n_genes_raw",
            "n_genes_canonical",
            "n_collapsed_duplicates",
            "collapsed_duplicate_fraction",
            "n_ensembl_like",
            "n_symbol_like",
            "n_other_ids",
            "n_with_version_suffix",
            "n_mapped_to_hgnc",
            "mapped_fraction",
            "n_alias_mapped",
            "alias_mapped_fraction",
            "n_unmapped_ensembl",
            "unmapped_ensembl_fraction",
            "status",
            "fail_reason",
        ],
        rows=failed_rows,
    )

    n_pass = sum(1 for r in summary_rows if r.get("status") == "pass")
    n_fail = sum(1 for r in summary_rows if r.get("status") == "fail")
    n_missing = sum(1 for r in summary_rows if r.get("status") == "missing_expression")
    summary_lines = [
        "# Gene ID Audit Summary",
        "",
        f"- sample_manifest: {manifest_path}",
        f"- expression_manifest: {expression_manifest}",
        f"- downloads_root: {downloads_root}",
        f"- gene_id_mapping: {mapping_path} ({'present' if mapping_path.exists() else 'missing'})",
        f"- min_hgnc_mapping_rate: {min_hgnc_mapping_rate}",
        f"- max_unmapped_ensembl_fraction: {max_unmapped_ensembl_fraction}",
        f"- max_duplicate_collapse_fraction: {max_duplicate_collapse_fraction}",
        f"- strict_mode: {'true' if strict else 'false'}",
        "",
        f"- cohorts_audited: {len(summary_rows)}",
        f"- cohorts_pass: {n_pass}",
        f"- cohorts_fail: {n_fail}",
        f"- cohorts_missing_expression: {n_missing}",
        "",
        "## Failed Cohorts",
        "",
    ]
    if failed_rows:
        summary_lines.extend(["| cohort_id | fail_reason |", "| --- | --- |"])
        for row in failed_rows[:200]:
            summary_lines.append(f"| {row.get('cohort_id', '')} | {row.get('fail_reason', '')} |")
    else:
        summary_lines.append("- none")
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    outputs.extend([summary_file, failed_file, summary_md])
    _mark_run(args, "intake gene-audit", outputs)
    print(f"Wrote gene ID audit under {out_root}")

    if strict and failed_rows:
        fail_ids = ", ".join(sorted({r.get("cohort_id", "") for r in failed_rows if r.get("cohort_id", "")}))
        raise RuntimeError(
            "Gene ID audit failed quality gates for cohorts: "
            f"{fail_ids}. See {failed_file} and {summary_md}."
        )
    return 0


def _load_expression_manifest_lookup(expression_manifest: Path) -> dict[str, dict[str, str]]:
    if not expression_manifest.exists():
        return {}
    return {
        row.get("cohort_id", ""): row
        for row in read_tsv(expression_manifest)
        if row.get("cohort_id", "")
    }


def _normalized_mapping_field(raw: str) -> str:
    field = _normalize_metadata_key(raw)
    return "*" if field == "*" else field


def _mapping_value_matches(actual: str, expected: str) -> bool:
    return _normalize_metadata_value(actual).casefold() == _normalize_metadata_value(expected).casefold()


def _lookup_mapped_label(
    cohort_id: str,
    sample_fields: list[dict[str, str]],
    mapping_rows: list[dict[str, str]],
    *,
    target_class: str,
) -> tuple[str, str, str]:
    # First pass: honor explicit cohort-specific mappings against any field key.
    # This supports datasets where useful response/timing proxies live in fields
    # that are not captured by generic relevance heuristics.
    for field_row in sample_fields:
        field_key = _normalize_metadata_key(field_row.get("field_key", ""))
        field_value = field_row.get("field_value", "")
        for mapping in mapping_rows:
            mapping_cohort = (mapping.get("cohort_id", "") or "").strip()
            if mapping_cohort != cohort_id:
                continue
            source_field = _normalized_mapping_field(mapping.get("source_field", ""))
            if source_field != "*" and source_field != field_key:
                continue
            if _mapping_value_matches(field_value, mapping.get("source_value", "")):
                return (
                    mapping.get("pipeline_label", "") or "unknown",
                    field_key,
                    "high",
                )

    relevant_fields = [row for row in sample_fields if _metadata_relevance_class(row.get("field_key", "")) == target_class]
    if not relevant_fields:
        return "unknown", "", ""

    for match_scope, confidence in ((cohort_id, "high"), ("DEFAULT", "medium")):
        for field_row in relevant_fields:
            field_key = _normalize_metadata_key(field_row.get("field_key", ""))
            field_value = field_row.get("field_value", "")
            for mapping in mapping_rows:
                mapping_cohort = (mapping.get("cohort_id", "") or "").strip()
                if mapping_cohort != match_scope:
                    continue
                source_field = _normalized_mapping_field(mapping.get("source_field", ""))
                if source_field != "*" and source_field != field_key:
                    continue
                if _mapping_value_matches(field_value, mapping.get("source_value", "")):
                    return (
                        mapping.get("pipeline_label", "") or "unknown",
                        field_key,
                        confidence,
                    )

    for field_row in relevant_fields:
        field_key = _normalize_metadata_key(field_row.get("field_key", ""))
        field_value = field_row.get("field_value", "")
        if target_class == "response":
            fallback_label, _ = _infer_response_from_text(f"{field_key}: {field_value}")
        else:
            fallback_label = _infer_timing_from_text(f"{field_key}: {field_value}")
        fallback_label = _canonical_response(fallback_label) if target_class == "response" else _canonical_timing(fallback_label)
        if fallback_label != "unknown":
            return fallback_label, field_key, "low"

    return "unknown", "", ""


def _common_alias_candidates(title: str) -> list[tuple[str, str]]:
    clean = (title or "").strip()
    if not clean:
        return []
    candidates: list[tuple[str, str]] = [(clean, "title_exact")]
    transformed = re.sub(r"^(?:rna[-_\s]?seq[_-]?)", "", clean, flags=re.IGNORECASE).strip()
    if transformed and transformed != clean:
        candidates.append((transformed, "title_transform"))
    return candidates


def _pick_prefixed_expression_column(
    prefix: str,
    expr_columns: list[str],
    metadata_text: str,
) -> tuple[str, str]:
    prefix_matches = [col for col in expr_columns if col.startswith(prefix + ".") or col.startswith(prefix + "_")]
    if len(prefix_matches) == 1:
        return prefix_matches[0], "title_transform"
    if not prefix_matches:
        return "", ""

    timing = _infer_timing_from_text(metadata_text)
    timing_tokens = {
        "pre-treatment": ["baseline", "pre"],
        "on-treatment": ["on", "ontx", "week", "during"],
        "post-treatment": ["post", "progression", "after"],
    }.get(timing, [])
    if timing_tokens:
        narrowed = [
            col
            for col in prefix_matches
            if any(tok in col.lower() for tok in timing_tokens)
        ]
        if len(narrowed) == 1:
            return narrowed[0], "description_derived"
    return "", ""


def _resolve_expression_alias_for_record(
    record: dict[str, object],
    expr_columns: list[str],
) -> tuple[str, str, str]:
    sample_id = str(record.get("sample_id", "") or "")
    if sample_id and sample_id in expr_columns:
        return sample_id, "direct", "matched"

    title = str(record.get("title", "") or "")
    metadata_text = str(record.get("metadata_text", "") or "")
    for candidate, method in _common_alias_candidates(title):
        if candidate in expr_columns:
            return candidate, method, "matched"
        prefixed, prefixed_method = _pick_prefixed_expression_column(candidate, expr_columns, metadata_text)
        if prefixed:
            return prefixed, prefixed_method, "matched"

    return "", "unmatched", "unmatched"


def _required_timing_for_row(row: dict[str, str]) -> str:
    value = (row.get("comparison_tracks_final") or row.get("comparison_tracks") or "").strip().upper()
    if "PRE_RESPONSE" in value:
        return "pre-treatment"
    if "ON_RESPONSE" in value:
        return "on-treatment"
    return ""


def _recompute_manifest_include(row: dict[str, str]) -> tuple[str, str]:
    response = _canonical_response(row.get("response_label", ""))
    timing = _canonical_timing(row.get("timing_category", ""))
    reasons: list[str] = []
    if response == "unknown":
        reasons.append("response_unknown")
    required_timing = _required_timing_for_row(row)
    if required_timing:
        if timing == "unknown":
            reasons.append("timing_unknown")
        elif timing != required_timing:
            reasons.append(f"timing_not_{required_timing.replace('-', '_')}")
    return ("false", ";".join(reasons)) if reasons else ("true", "")


def cmd_intake_extract_characteristics(args: argparse.Namespace) -> int:
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    downloads_root = Path(args.downloads_root)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    manifest_lookup = _load_expression_manifest_lookup(expression_manifest)
    long_rows: list[dict[str, str]] = []
    wide_rows: list[dict[str, str]] = []
    inventory: dict[str, dict[str, object]] = {}
    dynamic_columns: set[str] = set()

    for cohort_id, manifest_row in sorted(manifest_lookup.items()):
        soft_path = _find_geo_soft_file(
            cohort_id,
            downloads_root,
            manifest_row.get("downloads_folder", ""),
        )
        if not soft_path:
            continue
        for record in _parse_geo_soft_sample_records(soft_path):
            sample_id = str(record.get("sample_id", "") or "")
            title = str(record.get("title", "") or "")
            source_name = str(record.get("source_name", "") or "")
            description = str(record.get("description", "") or "")
            wide_row = {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "title": title,
                "source_name": source_name,
                "description": description,
            }

            for field_source, field_key, field_value in [
                ("title", "title", title),
                ("source", "source_name", source_name),
                ("description", "description", description),
            ]:
                clean_value = _normalize_metadata_value(field_value)
                if clean_value:
                    long_rows.append(
                        {
                            "cohort_id": cohort_id,
                            "sample_id": sample_id,
                            "field_source": field_source,
                            "field_key": field_key,
                            "field_value": clean_value,
                        }
                    )

            for entry in record.get("characteristics", []):
                if not isinstance(entry, dict):
                    continue
                field_key = _normalize_metadata_key(str(entry.get("field_key", "") or ""))
                field_value = _normalize_metadata_value(str(entry.get("field_value", "") or ""))
                if not field_key or not field_value:
                    continue
                long_rows.append(
                    {
                        "cohort_id": cohort_id,
                        "sample_id": sample_id,
                        "field_source": "characteristics",
                        "field_key": field_key,
                        "field_value": field_value,
                    }
                )
                column_name = _slugify_label(field_key)
                dynamic_columns.add(column_name)
                _append_cell(wide_row, column_name, field_value)

                stats = inventory.setdefault(
                    field_key,
                    {
                        "cohorts": set(),
                        "samples": set(),
                        "examples": [],
                    },
                )
                stats["cohorts"].add(cohort_id)
                stats["samples"].add(f"{cohort_id}::{sample_id}")
                examples = stats["examples"]
                if field_value not in examples and len(examples) < 3:
                    examples.append(field_value)

            wide_rows.append(wide_row)

    long_file = out_root / "characteristics_extracted_long.tsv"
    wide_file = out_root / "characteristics_extracted_wide.tsv"
    inventory_file = out_root / "characteristic_key_inventory.tsv"

    write_tsv(
        long_file,
        fieldnames=["cohort_id", "sample_id", "field_source", "field_key", "field_value"],
        rows=long_rows,
    )
    write_tsv(
        wide_file,
        fieldnames=["cohort_id", "sample_id", "title", "source_name", "description", *sorted(dynamic_columns)],
        rows=wide_rows,
    )
    write_tsv(
        inventory_file,
        fieldnames=["char_key", "n_cohorts", "n_samples", "example_values", "relevance_class"],
        rows=[
            {
                "char_key": char_key,
                "n_cohorts": len(stats["cohorts"]),
                "n_samples": len(stats["samples"]),
                "example_values": " | ".join(stats["examples"]),
                "relevance_class": _metadata_relevance_class(char_key),
            }
            for char_key, stats in sorted(inventory.items())
        ],
    )

    _mark_run(args, "intake extract-characteristics", [long_file, wide_file, inventory_file])
    print(f"Wrote {long_file}, {wide_file}, and {inventory_file}")
    return 0


def cmd_intake_apply_characteristics_mapping(args: argparse.Namespace) -> int:
    characteristics_rows = read_tsv(Path(args.characteristics))
    response_mapping = read_tsv(Path(args.response_mapping))
    timing_mapping = read_tsv(Path(args.timing_mapping))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in characteristics_rows:
        key = (row.get("cohort_id", ""), row.get("sample_id", ""))
        if key[0] and key[1]:
            grouped[key].append(row)

    mapped_rows: list[dict[str, str]] = []
    unmapped_counter: dict[tuple[str, str, str], int] = defaultdict(int)

    for (cohort_id, sample_id), sample_fields in sorted(grouped.items()):
        response_label, response_source_field, response_conf = _lookup_mapped_label(
            cohort_id,
            sample_fields,
            response_mapping,
            target_class="response",
        )
        timing_label, timing_source_field, timing_conf = _lookup_mapped_label(
            cohort_id,
            sample_fields,
            timing_mapping,
            target_class="timing",
        )

        confidence_rank = {"": 0, "low": 1, "medium": 2, "high": 3}
        combined_conf = response_conf if confidence_rank.get(response_conf, 0) >= confidence_rank.get(timing_conf, 0) else timing_conf
        mapped_rows.append(
            {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "response_label": _canonical_response(response_label),
                "timing_category": _canonical_timing(timing_label),
                "response_source_field": response_source_field,
                "timing_source_field": timing_source_field,
                "confidence": combined_conf or "unmapped",
            }
        )

        for field_row in sample_fields:
            field_key = _normalize_metadata_key(field_row.get("field_key", ""))
            field_value = _normalize_metadata_value(field_row.get("field_value", ""))
            relevance = _metadata_relevance_class(field_key)
            if relevance not in {"response", "timing"}:
                continue
            if relevance == "response" and response_label == "unknown":
                unmapped_counter[(cohort_id, field_key, field_value)] += 1
            if relevance == "timing" and timing_label == "unknown":
                unmapped_counter[(cohort_id, field_key, field_value)] += 1

    mapped_file = out_root / "response_labels_mapped.tsv"
    unmapped_file = out_root / "unmapped_values_review.tsv"
    write_tsv(
        mapped_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "response_label",
            "timing_category",
            "response_source_field",
            "timing_source_field",
            "confidence",
        ],
        rows=mapped_rows,
    )
    write_tsv(
        unmapped_file,
        fieldnames=["cohort_id", "field_key", "field_value", "n_samples", "suggested_label"],
        rows=[
            {
                "cohort_id": cohort_id,
                "field_key": field_key,
                "field_value": field_value,
                "n_samples": count,
                "suggested_label": (
                    _canonical_response(_infer_response_from_text(f"{field_key}: {field_value}")[0])
                    if _metadata_relevance_class(field_key) == "response"
                    else _canonical_timing(_infer_timing_from_text(f"{field_key}: {field_value}"))
                ),
            }
            for (cohort_id, field_key, field_value), count in sorted(unmapped_counter.items())
        ],
    )

    _mark_run(args, "intake apply-characteristics-mapping", [mapped_file, unmapped_file])
    print(f"Wrote {mapped_file} and {unmapped_file}")
    return 0


def cmd_intake_extract_expression_aliases(args: argparse.Namespace) -> int:
    downloads_root = Path(args.downloads_root)
    expression_manifest = Path(args.expression_manifest)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    manifest_lookup = _load_expression_manifest_lookup(expression_manifest)
    alias_rows: list[dict[str, str]] = []

    for cohort_id, manifest_row in sorted(manifest_lookup.items()):
        soft_path = _find_geo_soft_file(
            cohort_id,
            downloads_root,
            manifest_row.get("downloads_folder", ""),
        )
        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        expr_columns = list(expr.columns) if expr is not None else []
        if not soft_path:
            continue
        for record in _parse_geo_soft_sample_records(soft_path):
            alias, match_method, match_status = ("", "unmatched", "unmatched")
            if expr_columns:
                alias, match_method, match_status = _resolve_expression_alias_for_record(record, expr_columns)
            alias_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": str(record.get("sample_id", "") or ""),
                    "expression_sample_alias": alias,
                    "match_method": match_method,
                    "match_status": match_status,
                }
            )

    alias_file = out_root / "expression_aliases.tsv"
    write_tsv(
        alias_file,
        fieldnames=["cohort_id", "sample_id", "expression_sample_alias", "match_method", "match_status"],
        rows=alias_rows,
    )
    _mark_run(args, "intake extract-expression-aliases", [alias_file])
    print(f"Wrote {alias_file}")
    return 0


def cmd_intake_merge_extracted_metadata(args: argparse.Namespace) -> int:
    sample_manifest = read_tsv(Path(args.sample_manifest))
    response_lookup = {
        (row.get("cohort_id", ""), row.get("sample_id", "")): row
        for row in read_tsv(Path(args.response_labels))
        if row.get("cohort_id") and row.get("sample_id")
    }
    alias_lookup = {
        (row.get("cohort_id", ""), row.get("sample_id", "")): row
        for row in read_tsv(Path(args.expression_aliases))
        if row.get("cohort_id") and row.get("sample_id")
    }

    out_manifest = Path(args.out)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    eligibility_report = Path(getattr(args, "eligibility_report", "results/spec_006/de_eligibility_report.tsv"))
    eligibility_report.parent.mkdir(parents=True, exist_ok=True)

    updated_rows: list[dict[str, str]] = []
    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in sample_manifest:
        updated = dict(row)
        key = (updated.get("cohort_id", ""), updated.get("sample_id", ""))
        mapped = response_lookup.get(key, {})
        alias = alias_lookup.get(key, {})
        existing_include = parse_bool(updated.get("include_flag", "false"), default=False)
        metadata_changed = False

        if (updated.get("expression_sample_alias", "") or "").strip() == "":
            new_alias = (alias.get("expression_sample_alias", "") or "").strip()
            if new_alias:
                updated["expression_sample_alias"] = new_alias

        if not existing_include:
            if _canonical_response(updated.get("response_label", "")) == "unknown":
                new_response = _canonical_response(mapped.get("response_label", ""))
                if new_response != "unknown":
                    updated["response_label"] = new_response
                    updated["response_label_source"] = "characteristics_mapping"
                    metadata_changed = True
            if _canonical_timing(updated.get("timing_category", "")) == "unknown":
                new_timing = _canonical_timing(mapped.get("timing_category", ""))
                if new_timing != "unknown":
                    updated["timing_category"] = new_timing
                    metadata_changed = True

            # Always recompute include/exclude for currently excluded rows.
            # This clears stale exclusions (e.g., legacy timing_unknown) even
            # when mapped metadata was already present in normalized form.
            include_flag, exclude_reason = _recompute_manifest_include(updated)
            updated["include_flag"] = include_flag
            updated["exclude_reason"] = exclude_reason

        updated_rows.append(updated)
        by_cohort[updated.get("cohort_id", "")].append(updated)

    eligibility_rows: list[dict[str, str]] = []
    for cohort_id, rows in sorted(by_cohort.items()):
        included = [row for row in rows if parse_bool(row.get("include_flag", "false"), default=False)]
        n_responder = sum(1 for row in included if row.get("response_label") == "responder")
        n_non_responder = sum(1 for row in included if row.get("response_label") == "non_responder")
        n_pre_treatment = sum(1 for row in rows if row.get("timing_category") == "pre-treatment")
        de_eligible = n_responder >= 2 and n_non_responder >= 2
        blocker_reason = ""
        if not de_eligible:
            if n_responder < 2 and n_non_responder < 2:
                blocker_reason = "insufficient_responders_and_nonresponders"
            elif n_responder < 2:
                blocker_reason = "insufficient_responders"
            elif n_non_responder < 2:
                blocker_reason = "insufficient_nonresponders"
        eligibility_rows.append(
            {
                "cohort_id": cohort_id,
                "n_total": len(rows),
                "n_included": len(included),
                "n_responder": n_responder,
                "n_non_responder": n_non_responder,
                "n_pre_treatment": n_pre_treatment,
                "de_eligible": "true" if de_eligible else "false",
                "blocker_reason": blocker_reason,
            }
        )

    manifest_fieldnames = list(sample_manifest[0].keys()) if sample_manifest else []
    if "expression_sample_alias" not in manifest_fieldnames:
        manifest_fieldnames.append("expression_sample_alias")
    write_tsv(out_manifest, fieldnames=manifest_fieldnames, rows=updated_rows)
    write_tsv(
        eligibility_report,
        fieldnames=[
            "cohort_id",
            "n_total",
            "n_included",
            "n_responder",
            "n_non_responder",
            "n_pre_treatment",
            "de_eligible",
            "blocker_reason",
        ],
        rows=eligibility_rows,
    )

    _mark_run(args, "intake merge-extracted-metadata", [out_manifest, eligibility_report])
    print(f"Wrote {out_manifest} and {eligibility_report}")
    return 0


def cmd_intake_build_patient_manifest(args: argparse.Namespace) -> int:
    module = importlib.import_module(
        ".modules.01_dataset_intake.patient_manifest",
        package=__package__,
    )
    outputs = module.build_and_write_patient_manifest(
        sample_manifest=Path(args.sample_manifest),
        geo_tables_dir=Path(args.geo_tables_dir),
        out_dir=Path(args.out),
        reference_manifest=Path(args.reference_manifest) if args.reference_manifest else None,
    )
    output_paths = list(outputs.values())
    _mark_run(args, "intake build-patient-manifest", output_paths)
    for path in output_paths:
        print(f"Wrote {path}")
    return 0


def cmd_intake_build_sample_allocation(args: argparse.Namespace) -> int:
    module = importlib.import_module(
        ".modules.01_dataset_intake.sample_allocation",
        package=__package__,
    )
    sample_manifest = Path(args.sample_manifest)
    outputs = module.write_allocation_outputs(
        rows=read_tsv(sample_manifest),
        sample_manifest=sample_manifest,
        out_dir=Path(args.out),
    )
    _mark_run(args, "intake build-sample-allocation", outputs)
    for path in outputs:
        print(f"Wrote {path}")
    return 0


def _token_set(raw: str) -> set[str]:
    return set(split_accessions(raw))


_ACCESSION_TOKEN_RE = re.compile(r"(GSE\d+|SRP\d+|PRJ\w+)", flags=re.IGNORECASE)


def _extract_accession_like_tokens(raw: str) -> set[str]:
    if not raw:
        return set()
    return {m.group(1).upper() for m in _ACCESSION_TOKEN_RE.finditer(raw)}


def _stage01_lookup_keys(candidate_id: str, resolved_accession: str) -> list[str]:
    keys: list[str] = []
    for key in [candidate_id.strip().lower(), resolved_accession.strip().lower()]:
        if key and key not in keys:
            keys.append(key)
    for token in sorted(_extract_accession_like_tokens(f"{candidate_id} {resolved_accession}")):
        token_key = token.lower()
        if token_key not in keys:
            keys.append(token_key)
    return keys


def _build_stage01_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        cohort_id = (row.get("cohort_id", "") or "").strip()
        if not cohort_id:
            continue
        keys = [cohort_id.lower(), *[tok.lower() for tok in _extract_accession_like_tokens(cohort_id)]]
        for key in keys:
            if key and key not in index:
                index[key] = row
    return index


def _parse_float_or_default(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def cmd_cohort_audit(args: argparse.Namespace) -> int:
    candidate_path = Path(args.candidate_roster)
    inventory_path = Path(args.inventory)
    out_dir = Path(args.out)
    out_file = out_dir / "cohort_promotion_audit.tsv"

    candidates = read_tsv(candidate_path)
    inventory = read_tsv(inventory_path)
    assay_detection_path_raw = getattr(args, "assay_detection", "")
    response_definition_path_raw = getattr(args, "response_definition", "")
    assay_detection_path = Path(assay_detection_path_raw) if assay_detection_path_raw else None
    response_definition_path = Path(response_definition_path_raw) if response_definition_path_raw else None
    min_assay_confidence = float(getattr(args, "min_assay_confidence", 0.75))
    assay_index = (
        _build_stage01_index(read_tsv(assay_detection_path))
        if assay_detection_path and assay_detection_path.exists()
        else {}
    )
    response_index = (
        _build_stage01_index(read_tsv(response_definition_path))
        if response_definition_path and response_definition_path.exists()
        else {}
    )

    inventory_tokens: list[set[str]] = []
    for inv in inventory:
        raw = inv.get("accession", "")
        inventory_tokens.append(_token_set(raw))

    token_freq: dict[str, int] = defaultdict(int)
    for cand in candidates:
        resolved_accession = cand.get("resolved_accession", cand.get("accession", ""))
        cand_tokens = _token_set(resolved_accession)
        for token in cand_tokens:
            token_freq[token] += 1

    out_rows: list[dict[str, str]] = []
    for cand in candidates:
        resolved_accession = cand.get("resolved_accession", cand.get("accession", ""))
        cand_tokens = _token_set(resolved_accession)
        already = any(cand_tokens & inv_tokens for inv_tokens in inventory_tokens) if cand_tokens else False
        duplicate_tokens = sorted([t for t in cand_tokens if token_freq[t] > 1])
        candidate_id = (cand.get("candidate_id", "") or "").strip().lower()
        assay_type = _canonical_assay_type(cand.get("assay_type", ""))
        publication = (cand.get("publication", "") or "").strip()
        has_publication = bool(publication)
        notes: list[str] = []
        reason_codes: list[str] = []

        proposed_role = (cand.get("proposed_role", "") or "").strip().lower()
        stage01_keys = _stage01_lookup_keys(candidate_id, resolved_accession)
        assay_row = next((assay_index[key] for key in stage01_keys if key in assay_index), {})
        response_row = next((response_index[key] for key in stage01_keys if key in response_index), {})
        stage01_assay_type = _canonical_assay_type(assay_row.get("assay_type", ""))
        stage01_assay_confidence = _parse_float_or_default(assay_row.get("detection_confidence", ""), default=0.0)
        stage01_label_provenance = (response_row.get("label_provenance", "") or "").strip().lower()
        stage01_needs_manual = parse_bool(response_row.get("needs_manual_confirmation", ""), default=False)
        stage01_curation_reasons: list[str] = []
        if assay_row and stage01_assay_confidence < min_assay_confidence:
            stage01_curation_reasons.append("low_assay_confidence")
        if response_row and (
            stage01_needs_manual or stage01_label_provenance in {"sampleid_inferred", "unknown"}
        ):
            stage01_curation_reasons.append("response_needs_manual_confirmation")

        if "gse165278" in candidate_id or "gse165278" in resolved_accession.lower():
            decision = "drop"
            notes.append("excluded_no_responder_arm_gse165278")
            reason_codes.append("excluded_no_responder_arm_gse165278")
        elif "gse126044_srp183455" in candidate_id:
            decision = "drop"
            notes.append("dedup_drop_duplicate_gse126044_srp183455")
            reason_codes.append("dedup_drop_duplicate_gse126044_srp183455")
        elif stage01_assay_type in ASSAY_TYPE_HARD_EXCLUDE:
            decision = "drop"
            reason = f"excluded_assay_type_{stage01_assay_type}"
            notes.append(reason)
            reason_codes.append(reason)
        elif assay_type in ASSAY_TYPE_HARD_EXCLUDE:
            decision = "drop"
            reason = f"excluded_assay_type_{assay_type}"
            notes.append(reason)
            reason_codes.append(reason)
        elif already:
            decision = "already_covered"
            notes.append("accession_overlap_with_inventory")
            reason_codes.append("accession_overlap_with_inventory")
        elif duplicate_tokens:
            decision = "hold"
            reason = f"duplicate_candidate_accessions:{';'.join(duplicate_tokens)}"
            notes.append(reason)
            reason_codes.append(reason)
        elif not cand_tokens:
            decision = "hold"
            notes.append("missing_accession")
            reason_codes.append("missing_accession")
        elif not has_publication:
            decision = "hold"
            notes.append("missing_publication_provenance")
            reason_codes.append("missing_publication_provenance")
        elif stage01_curation_reasons:
            decision = "hold"
            for reason in stage01_curation_reasons:
                notes.append(reason)
                reason_codes.append(reason)
        elif proposed_role in {"discovery", "promote_discovery"}:
            decision = "promote_discovery"
        elif proposed_role in {"validation", "promote_validation"}:
            decision = "promote_validation"
        elif proposed_role in {"context", "context_only", "context-only"}:
            decision = "context_only"
        else:
            decision = "hold"
            notes.append("unknown_or_missing_proposed_role")
            reason_codes.append("unknown_or_missing_proposed_role")

        if decision == "drop":
            include_decision = "exclude"
            audit_status = "excluded"
        elif decision == "hold":
            include_decision = "hold"
            audit_status = "needs_curation" if stage01_curation_reasons else "hold"
        else:
            include_decision = "include"
            audit_status = "ready"

        source_notes = (cand.get("notes", "") or "").strip()
        combined_notes = "; ".join([n for n in [source_notes, *notes] if n])
        out_rows.append(
            {
                "candidate_id": cand.get("candidate_id", ""),
                "source_stream": cand.get("source_stream", ""),
                "cancer_type": cand.get("cancer_type", ""),
                "therapy_context": cand.get("therapy_context", ""),
                "comparison_type": cand.get("comparison_type", ""),
                "resolved_accession": resolved_accession,
                "publication": publication,
                "already_in_inventory": "true" if already else "false",
                "proposed_role": cand.get("proposed_role", ""),
                "decision": decision,
                "audit_status": audit_status,
                "include_decision": include_decision,
                "reason": ";".join(reason_codes),
                "stage01_assay_confidence": f"{stage01_assay_confidence:.2f}" if assay_row else "",
                "stage01_label_provenance": stage01_label_provenance if response_row else "",
                "stage01_needs_manual_confirmation": "true" if stage01_needs_manual else "false",
                "notes": combined_notes,
            }
        )

    write_tsv(
        out_file,
        fieldnames=[
            "candidate_id",
            "source_stream",
            "cancer_type",
            "therapy_context",
            "comparison_type",
            "resolved_accession",
            "publication",
            "already_in_inventory",
            "proposed_role",
            "decision",
            "audit_status",
            "include_decision",
            "reason",
            "stage01_assay_confidence",
            "stage01_label_provenance",
            "stage01_needs_manual_confirmation",
            "notes",
        ],
        rows=out_rows,
    )
    _mark_run(args, "cohort audit", [out_file])
    print(f"Wrote {out_file}")
    return 0


def _split_manifest_sample_ids(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[|,]", raw or "") if part.strip()]


def _load_patient_manifest_sample_lookup(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = read_tsv(path)
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    timing_fields = [
        ("pre_sample_ids", "pre-treatment"),
        ("on_sample_ids", "on-treatment"),
        ("post_sample_ids", "post-treatment"),
        ("unknown_sample_ids", "unknown"),
    ]
    for row in rows:
        cohort_id = row.get("cohort_id", "")
        response_label = _canonical_response(row.get("response_label", ""))
        for field, timing in timing_fields:
            for sample_id in _split_manifest_sample_ids(row.get(field, "")):
                lookup[(cohort_id, sample_id)] = {
                    "patient_uid": row.get("patient_uid", ""),
                    "timing_category": timing,
                    "response_label": response_label,
                }
    return lookup


def cmd_manifest_build(args: argparse.Namespace) -> int:
    discovery = {row.get("cohort_id", ""): row for row in read_tsv(Path(args.discovery_manifest))}
    intake_rows = read_tsv(Path(args.intake_record))
    out_file = Path(args.out)
    patient_manifest_path = Path(getattr(args, "patient_manifest", "results/patient_manifest/patient_manifest.tsv"))
    divergence_out = Path(getattr(args, "divergence_out", "results/manifest_build/divergences.tsv"))
    patient_sample_lookup = (
        _load_patient_manifest_sample_lookup(patient_manifest_path)
        if patient_manifest_path.exists()
        else {}
    )

    out_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    divergence_rows: list[dict[str, str]] = []
    for intake in intake_rows:
        cohort_id = intake.get("cohort_id", "")
        disc = discovery.get(cohort_id, {})
        agent = disc.get("therapy_agent", "")
        explicit_timing = (disc.get("timing_category", "") or "").strip()
        timing_category = _infer_timing(explicit_timing or disc.get("initial_analysis_slice", ""))
        therapy_class = (disc.get("therapy_class", "") or "").strip() or _infer_therapy_class(agent)
        analysis_role = (
            (disc.get("analysis_role_merged", "") or "").strip()
            or (disc.get("analysis_role", "") or "").strip()
            or "discovery"
        )
        input_class = (intake.get("input_class", "") or "").strip()
        intake_include = parse_bool(intake.get("intake_include_flag", "true"), default=True)
        intake_timing = (intake.get("timing_category_inferred", "") or "").strip()
        if intake_timing in {"pre-treatment", "on-treatment", "post-treatment"}:
            timing_category = intake_timing

        intake_response = (intake.get("response_label_inferred", "") or "").strip()
        if intake_response in {"responder", "non_responder"}:
            response_label = intake_response
            response_source = "intake_metadata_inference"
        else:
            response_label, response_source = _infer_response_label(intake.get("sample_id", ""))

        patient_authority = patient_sample_lookup.get((cohort_id, intake.get("sample_id", "")), {})
        patient_uid = patient_authority.get("patient_uid", "")
        patient_timing = _canonical_timing(patient_authority.get("timing_category", ""))
        patient_response = _canonical_response(patient_authority.get("response_label", ""))
        if patient_timing != "unknown" and patient_timing != timing_category:
            divergence_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": intake.get("sample_id", ""),
                    "patient_uid": patient_uid,
                    "field": "timing_category",
                    "sample_manifest_value": timing_category,
                    "patient_manifest_value": patient_timing,
                    "resolution": "patient_manifest_wins",
                    "source": "patient_manifest",
                }
            )
            timing_category = patient_timing
        if patient_response != "unknown" and patient_response != response_label:
            divergence_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": intake.get("sample_id", ""),
                    "patient_uid": patient_uid,
                    "field": "response_label",
                    "sample_manifest_value": response_label,
                    "patient_manifest_value": patient_response,
                    "resolution": "patient_manifest_wins",
                    "source": "patient_manifest",
                }
            )
            response_label = patient_response
            response_source = "patient_manifest"

        exclude_reasons: list[str] = []
        if not disc:
            exclude_reasons.append("cohort_missing_from_discovery_manifest")
        if timing_category == "unknown":
            exclude_reasons.append("missing_or_ambiguous_timing_category")
        if input_class not in {"FASTQ", "raw_counts", "processed_matrix"}:
            exclude_reasons.append("unsupported_input_class")
        existing_reason = (intake.get("intake_exclude_reason", "") or "").strip()
        if existing_reason:
            exclude_reasons.append(existing_reason)
        if not intake_include:
            exclude_reasons.append("intake_flag_excluded")

        include_flag = "false" if exclude_reasons else "true"
        exclude_reason = "; ".join(dict.fromkeys(exclude_reasons))
        sample_id = intake.get("sample_id", "")
        patient_id = sample_id.split("__")[0] if "__" in sample_id else sample_id
        out_rows.append(
            {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "patient_id": patient_id,
                "cancer_type": disc.get("cancer_type", ""),
                "therapy_class": therapy_class,
                "therapy_agent": agent,
                "specimen_type": "bulk tumor sample",
                "timing_category": timing_category,
                "response_label": response_label,
                "pair_id": "",
                "input_class": input_class,
                "analysis_role": analysis_role,
                "include_flag": include_flag,
                "exclude_reason": exclude_reason,
                "response_label_source": response_source,
            }
        )
        audit_rows.append(
            {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "audit_note": (
                    "included"
                    if include_flag == "true" and response_label != "unknown"
                    else (
                        "included_response_unknown_manual_curation_needed"
                        if include_flag == "true"
                        else f"excluded:{exclude_reason}"
                    )
                ),
            }
        )

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "pair_id",
            "input_class",
            "analysis_role",
            "include_flag",
            "exclude_reason",
            "response_label_source",
        ],
        rows=out_rows,
    )

    audit_file = Path(args.run_manifest).parent / "sample_manifest_audit.tsv"
    write_tsv(
        audit_file,
        fieldnames=["cohort_id", "sample_id", "audit_note"],
        rows=audit_rows,
    )
    write_tsv(
        divergence_out,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_uid",
            "field",
            "sample_manifest_value",
            "patient_manifest_value",
            "resolution",
            "source",
        ],
        rows=divergence_rows,
    )
    _mark_run(args, "manifest build", [out_file, audit_file, divergence_out])
    print(f"Wrote {out_file}")
    return 0


def cmd_method_inspect(args: argparse.Namespace) -> int:
    sample_manifest_path = Path(args.sample_manifest)
    out_root = Path(args.out)
    out_file = out_root / "cohort_method_inspection.tsv"
    summary_file = out_root / "cohort_method_inspection.md"

    rows = read_tsv(sample_manifest_path)
    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_cohort[row.get("cohort_id", "")].append(row)

    out_rows: list[dict[str, str]] = []
    n_pre_eligible = 0
    n_delta_eligible = 0
    n_on_eligible = 0
    n_manual = 0
    for cohort_id, cohort_rows in sorted(by_cohort.items()):
        included_rows = [
            row for row in cohort_rows if parse_bool(row.get("include_flag", "true"), default=True)
        ]
        working_rows = included_rows if included_rows else cohort_rows
        input_classes = {
            (row.get("input_class", "") or "").strip() for row in working_rows if row.get("input_class", "")
        }

        timing_counts = {
            "pre-treatment": 0,
            "on-treatment": 0,
            "post-treatment": 0,
            "unknown": 0,
        }
        response_counts = {
            "responder": 0,
            "non_responder": 0,
            "unknown": 0,
        }
        pair_count = 0
        for row in working_rows:
            timing_counts[_canonical_timing(row.get("timing_category", ""))] += 1
            response_counts[_canonical_response(row.get("response_label", ""))] += 1
            if (row.get("pair_id", "") or "").strip():
                pair_count += 1

        n_pre = timing_counts["pre-treatment"]
        n_on = timing_counts["on-treatment"]
        n_post = timing_counts["post-treatment"]
        n_timing_unknown = timing_counts["unknown"]
        n_resp = response_counts["responder"]
        n_nonresp = response_counts["non_responder"]
        n_response_unknown = response_counts["unknown"]

        eligible_pre = n_pre > 0 and n_resp > 0 and n_nonresp > 0
        timing_transition_present = n_pre > 0 and (n_on > 0 or n_post > 0)
        eligible_delta = timing_transition_present and pair_count > 0
        eligible_on = n_on > 0 and n_resp > 0 and n_nonresp > 0

        if eligible_pre:
            n_pre_eligible += 1
        if eligible_delta:
            n_delta_eligible += 1
        if eligible_on:
            n_on_eligible += 1

        if eligible_pre:
            recommended_primary = "PRE_RESPONSE"
            recommended_design = "response_label + cohort_covariates (within-cohort)"
        elif eligible_delta:
            recommended_primary = "TREATMENT_DELTA"
            recommended_design = "paired_design(~ patient_id + timing + response)"
        elif eligible_on:
            recommended_primary = "ON_RESPONSE"
            recommended_design = "response_label on-treatment subset (within-cohort)"
        else:
            recommended_primary = "NONE"
            recommended_design = "manual_curation_required_before_modeling"
            n_manual += 1

        curation_flags: list[str] = []
        if not included_rows:
            curation_flags.append("no_included_samples")
        if n_response_unknown > 0:
            curation_flags.append("response_labels_incomplete")
        if n_timing_unknown > 0:
            curation_flags.append("timing_labels_incomplete")
        if timing_transition_present and pair_count == 0:
            curation_flags.append("paired_design_metadata_missing")
        if not curation_flags:
            curation_flags.append("none")

        out_rows.append(
            {
                "cohort_id": cohort_id,
                "analysis_orientation": "cohort_oriented_rnr_timing_stratified",
                "input_classes": ";".join(sorted(input_classes)),
                "n_samples_total": len(cohort_rows),
                "n_samples_included": len(included_rows),
                "n_pre": n_pre,
                "n_on": n_on,
                "n_post": n_post,
                "n_timing_unknown": n_timing_unknown,
                "n_responder": n_resp,
                "n_non_responder": n_nonresp,
                "n_response_unknown": n_response_unknown,
                "n_with_pair_id": pair_count,
                "eligible_pre_response": "true" if eligible_pre else "false",
                "eligible_treatment_delta": "true" if eligible_delta else "false",
                "eligible_on_response": "true" if eligible_on else "false",
                "recommended_primary_contrast": recommended_primary,
                "recommended_analysis_method": _recommend_analysis_method(input_classes),
                "recommended_design_formula": recommended_design,
                "contrast_priority_order": "PRE_RESPONSE>TREATMENT_DELTA>ON_RESPONSE",
                "curation_flags": ";".join(curation_flags),
            }
        )

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "analysis_orientation",
            "input_classes",
            "n_samples_total",
            "n_samples_included",
            "n_pre",
            "n_on",
            "n_post",
            "n_timing_unknown",
            "n_responder",
            "n_non_responder",
            "n_response_unknown",
            "n_with_pair_id",
            "eligible_pre_response",
            "eligible_treatment_delta",
            "eligible_on_response",
            "recommended_primary_contrast",
            "recommended_analysis_method",
            "recommended_design_formula",
            "contrast_priority_order",
            "curation_flags",
        ],
        rows=out_rows,
    )

    summary_lines = [
        "# Cohort Method Inspection",
        "",
        f"- sample_manifest: {sample_manifest_path}",
        f"- n_cohorts: {len(out_rows)}",
        f"- pre_response_eligible: {n_pre_eligible}",
        f"- treatment_delta_eligible: {n_delta_eligible}",
        f"- on_response_eligible: {n_on_eligible}",
        f"- manual_curation_required: {n_manual}",
        "",
        "## Notes",
        "",
        "- Analysis remains cohort-oriented and avoids pooled cross-cancer DE for discovery.",
        "- `PRE_RESPONSE` stays first priority, then `TREATMENT_DELTA`, then `ON_RESPONSE`.",
    ]
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    _mark_run(args, "method inspect", [out_file, summary_file])
    print(f"Wrote {out_file} and {summary_file}")
    return 0


def _split_semicolon(raw: str) -> list[str]:
    return [part.strip() for part in (raw or "").split(";") if part.strip()]


def _extract_pmids(*text_fields: str) -> list[str]:
    pmids: list[str] = []
    for text in text_fields:
        for match in PMID_RE.findall(text or ""):
            if match not in pmids:
                pmids.append(match)
    return pmids


def _manual_review_priority(
    method_row: dict[str, str],
    missing_resp_counts: bool,
    timing_needs_confirmation: bool,
    response_needs_confirmation: bool,
) -> str:
    flags = set(_split_semicolon(method_row.get("curation_flags", "")))
    if (
        method_row.get("recommended_primary_contrast", "NONE") == "NONE"
        or "response_labels_incomplete" in flags
        or "timing_labels_incomplete" in flags
        or missing_resp_counts
        or timing_needs_confirmation
        or response_needs_confirmation
    ):
        return "high"
    if "paired_design_metadata_missing" in flags:
        return "medium"
    return "low"


def cmd_method_curation_sheet(args: argparse.Namespace) -> int:
    discovery_rows = read_tsv(Path(args.discovery_manifest))
    method_rows = {
        row.get("cohort_id", ""): row for row in read_tsv(Path(args.method_inspection))
    }

    out_root = Path(args.out)
    out_file = out_root / "study_manual_curation.tsv"
    summary_file = out_root / "study_manual_curation.md"
    preserved_fields = [
        "confirmed_disease",
        "confirmed_drug_regimen",
        "confirmed_timing_schema",
        "confirmed_response_schema",
        "paired_pre_post_available",
        "responder_count_confirmed",
        "nonresponder_count_confirmed",
        "curator",
        "curation_date",
        "curation_notes",
    ]
    existing_manual: dict[str, dict[str, str]] = {}
    if out_file.exists():
        for existing_row in read_tsv(out_file):
            cohort_id = existing_row.get("cohort_id", "")
            if cohort_id:
                existing_manual[cohort_id] = existing_row

    out_rows: list[dict[str, str]] = []
    n_high = 0
    n_medium = 0
    n_low = 0
    ready_for_modeling = 0

    for row in sorted(discovery_rows, key=lambda r: r.get("cohort_id", "")):
        cohort_id = row.get("cohort_id", "")
        method_row = method_rows.get(cohort_id, {})
        tokens = split_accessions(row.get("accession", ""))
        gse_tokens = [tok for tok in tokens if tok.startswith("GSE")]
        sra_tokens = [tok for tok in tokens if tok.startswith(("SRP", "PRJ", "SRX", "SRR"))]

        n_resp = (row.get("n_responders", "") or "").strip()
        n_nonresp = (row.get("n_nonresponders", "") or "").strip()
        missing_resp_counts = not n_resp or not n_nonresp

        timing_text = (row.get("timing_category", "") or "").strip().lower()
        has_pre = "pre" in timing_text or "baseline" in timing_text
        has_on = "on-treatment" in timing_text or "on treatment" in timing_text or "week" in timing_text
        has_post = "post" in timing_text or "after" in timing_text
        has_timing_transition = has_pre and (has_on or has_post)
        timing_needs_confirmation = "unknown" in timing_text or "likely" in timing_text or "mixed" in timing_text
        response_text = (row.get("response_framework", "") or "").strip().lower()
        response_needs_confirmation = (
            "pending" in response_text
            or "expected" in response_text
            or "manual" in response_text
            or "partially" in response_text
        )

        suggested_score = 0
        if not missing_resp_counts:
            suggested_score += 4
        if has_timing_transition:
            suggested_score += 3
        if has_pre:
            suggested_score += 2
        if sra_tokens:
            suggested_score += 1

        if not missing_resp_counts and has_timing_transition:
            suggested_track = "TREATMENT_DELTA_then_PRE_RESPONSE"
        elif not missing_resp_counts and has_pre:
            suggested_track = "PRE_RESPONSE_primary"
        elif has_timing_transition:
            suggested_track = "TREATMENT_DELTA_after_response_curation"
        else:
            suggested_track = "PRE_RESPONSE_after_metadata_curation"

        priority = _manual_review_priority(
            method_row=method_row,
            missing_resp_counts=missing_resp_counts,
            timing_needs_confirmation=timing_needs_confirmation,
            response_needs_confirmation=response_needs_confirmation,
        )
        if priority == "high":
            n_high += 1
        elif priority == "medium":
            n_medium += 1
        else:
            n_low += 1

        recommended_primary = method_row.get("recommended_primary_contrast", "NONE")
        recommended_method = method_row.get("recommended_analysis_method", "manual_curation_required")
        curation_flags = method_row.get("curation_flags", "missing_method_inspection")
        manual_confirmation_required = parse_bool(
            row.get("manual_confirmation_required", "true"), default=True
        )
        pmids = _extract_pmids(
            row.get("publication", ""),
            row.get("notes", ""),
            row.get("manual_confirmation_reason", ""),
        )

        review_blockers: list[str] = []
        if manual_confirmation_required:
            review_blockers.append("manual_confirmation_required")
        if missing_resp_counts:
            review_blockers.append("missing_responder_counts")
        if timing_needs_confirmation:
            review_blockers.append("timing_needs_confirmation")
        if response_needs_confirmation:
            review_blockers.append("response_framework_needs_confirmation")
        if recommended_primary == "NONE":
            review_blockers.append("contrast_not_eligible_from_manifest")

        if not review_blockers:
            review_status = "ready_for_modeling"
            ready_for_modeling += 1
        else:
            review_status = "pending_manual_review"

        out_row = {
            "cohort_id": cohort_id,
            "accession": row.get("accession", ""),
            "source_db": row.get("source_db", ""),
            "geo_accessions": ";".join(gse_tokens),
            "sra_accessions": ";".join(sra_tokens),
            "source_uri": build_source_uri(tokens),
            "cancer_type_declared": row.get("cancer_type", ""),
            "therapy_agent_declared": row.get("therapy_agent", ""),
            "therapy_class_declared": row.get("therapy_class", ""),
            "timing_declared": row.get("timing_category", ""),
            "response_framework_declared": row.get("response_framework", ""),
            "n_samples_total_declared": row.get("n_samples_total", ""),
            "n_responders_declared": n_resp,
            "n_nonresponders_declared": n_nonresp,
            "recommended_primary_contrast": recommended_primary,
            "recommended_analysis_method": recommended_method,
            "curation_flags": curation_flags,
            "manual_review_priority": priority,
            "suggested_review_score": str(suggested_score),
            "suggested_analysis_track": suggested_track,
            "manual_review_status": review_status,
            "review_blockers": ";".join(review_blockers) if review_blockers else "none",
            "pmid_candidates": ";".join(pmids),
            "study_notes": row.get("notes", ""),
            "manual_confirmation_reason": row.get("manual_confirmation_reason", ""),
            "confirmed_disease": "",
            "confirmed_drug_regimen": "",
            "confirmed_timing_schema": "",
            "confirmed_response_schema": "",
            "paired_pre_post_available": "",
            "responder_count_confirmed": "",
            "nonresponder_count_confirmed": "",
            "curator": "",
            "curation_date": "",
            "curation_notes": "",
        }
        existing_row = existing_manual.get(cohort_id, {})
        for field in preserved_fields:
            preserved_value = (existing_row.get(field, "") or "").strip()
            if preserved_value:
                out_row[field] = preserved_value
        out_rows.append(out_row)

    write_tsv(
        out_file,
        fieldnames=[
            "cohort_id",
            "accession",
            "source_db",
            "geo_accessions",
            "sra_accessions",
            "source_uri",
            "cancer_type_declared",
            "therapy_agent_declared",
            "therapy_class_declared",
            "timing_declared",
            "response_framework_declared",
            "n_samples_total_declared",
            "n_responders_declared",
            "n_nonresponders_declared",
            "recommended_primary_contrast",
            "recommended_analysis_method",
            "curation_flags",
            "manual_review_priority",
            "suggested_review_score",
            "suggested_analysis_track",
            "manual_review_status",
            "review_blockers",
            "pmid_candidates",
            "study_notes",
            "manual_confirmation_reason",
            "confirmed_disease",
            "confirmed_drug_regimen",
            "confirmed_timing_schema",
            "confirmed_response_schema",
            "paired_pre_post_available",
            "responder_count_confirmed",
            "nonresponder_count_confirmed",
            "curator",
            "curation_date",
            "curation_notes",
        ],
        rows=out_rows,
    )

    top_rows = sorted(
        out_rows,
        key=lambda r: (
            {"high": 0, "medium": 1, "low": 2}.get(r.get("manual_review_priority", "low"), 3),
            -int(r.get("suggested_review_score", "0") or 0),
            r.get("cohort_id", ""),
        ),
    )
    summary_lines = [
        "# Study-by-Study Manual Curation Sheet",
        "",
        f"- discovery_manifest: {Path(args.discovery_manifest)}",
        f"- method_inspection: {Path(args.method_inspection)}",
        f"- n_cohorts: {len(out_rows)}",
        f"- ready_for_modeling: {ready_for_modeling}",
        f"- pending_manual_review: {len(out_rows) - ready_for_modeling}",
        f"- high_priority: {n_high}",
        f"- medium_priority: {n_medium}",
        f"- low_priority: {n_low}",
        "",
        "## Review Queue",
        "",
        "| cohort_id | priority | score | suggested_track | status | recommended_primary | review_blockers |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in top_rows:
        summary_lines.append(
            f"| {row.get('cohort_id', '')} | {row.get('manual_review_priority', '')} | "
            f"{row.get('suggested_review_score', '')} | {row.get('suggested_analysis_track', '')} | "
            f"{row.get('manual_review_status', '')} | {row.get('recommended_primary_contrast', '')} | "
            f"{row.get('review_blockers', '')} |"
        )
    summary_lines.extend(
        [
            "",
            "## How To Use",
            "",
            "- Curate one cohort at a time and fill `confirmed_*` fields in the TSV.",
            "- Keep this table as the source of truth for response/timing harmonization decisions.",
            "- Rebuild `configs/sample_manifest.tsv` after curation before re-running `method inspect`.",
        ]
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    _mark_run(args, "method curation-sheet", [out_file, summary_file])
    print(f"Wrote {out_file} and {summary_file}")
    return 0


def _first_nonempty(*values: str) -> str:
    for value in values:
        if (value or "").strip():
            return value.strip()
    return ""


def _parse_count(raw: str) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    match = re.search(r"\d+", text)
    if not match:
        return None
    return int(match.group(0))


def _schema_has_timing(schema: str, category: str) -> bool:
    text = (schema or "").lower()
    if category == "pre-treatment":
        return "pre" in text or "baseline" in text
    if category == "on-treatment":
        return "on-treatment" in text or "on treatment" in text or "during" in text or "week" in text
    if category == "post-treatment":
        return "post" in text or "after" in text or "follow-up" in text
    return False


def _cohort_default_timing_from_schema(schema: str) -> str:
    if _schema_has_timing(schema, "pre-treatment"):
        return "pre-treatment"
    if _schema_has_timing(schema, "on-treatment"):
        return "on-treatment"
    if _schema_has_timing(schema, "post-treatment"):
        return "post-treatment"
    return "unknown"


def _yes_no_unknown(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"true", "yes", "y", "paired", "present", "1"}:
        return "yes"
    if value in {"false", "no", "n", "absent", "0"}:
        return "no"
    return "unknown"


def cmd_method_apply_curation(args: argparse.Namespace) -> int:
    sample_rows = read_tsv(Path(args.sample_manifest))
    curation_rows = {row.get("cohort_id", ""): row for row in read_tsv(Path(args.curation_sheet))}

    out_manifest = Path(args.out)
    out_root = out_manifest.parent
    out_root.mkdir(parents=True, exist_ok=True)
    projection_out = Path(args.projection_out)
    audit_out = Path(args.audit_out)

    curated_rows: list[dict[str, str]] = []
    projection_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []

    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sample_rows:
        by_cohort[row.get("cohort_id", "")].append(row)

    for cohort_id, rows in sorted(by_cohort.items()):
        curation = curation_rows.get(cohort_id, {})
        if not curation:
            for row in rows:
                curated_rows.append(dict(row))
            audit_rows.append(
                {
                    "cohort_id": cohort_id,
                    "curation_applied": "false",
                    "curated_sample_rows": str(len(rows)),
                    "projection_rows": "0",
                    "status": "no_curation_row",
                    "notes": "",
                }
            )
            continue

        confirmed_disease = _first_nonempty(
            curation.get("confirmed_disease", ""),
            curation.get("cancer_type_declared", ""),
        )
        confirmed_drug = _first_nonempty(
            curation.get("confirmed_drug_regimen", ""),
            curation.get("therapy_agent_declared", ""),
        )
        timing_schema = _first_nonempty(
            curation.get("confirmed_timing_schema", ""),
            curation.get("timing_declared", ""),
        )
        default_timing = _cohort_default_timing_from_schema(timing_schema)
        n_resp = _parse_count(
            _first_nonempty(
                curation.get("responder_count_confirmed", ""),
                curation.get("n_responders_declared", ""),
            )
        )
        n_nonresp = _parse_count(
            _first_nonempty(
                curation.get("nonresponder_count_confirmed", ""),
                curation.get("n_nonresponders_declared", ""),
            )
        )
        has_pre = _schema_has_timing(timing_schema, "pre-treatment")
        curation_status = (curation.get("manual_review_status", "") or "").strip()
        normalized_status = re.sub(r"\s+", "_", curation_status.lower())
        ready = normalized_status == "ready_for_modeling"
        if not ready and n_resp is not None and n_nonresp is not None and has_pre:
            ready = True

        applied_fields: list[str] = []
        for row in rows:
            updated = dict(row)
            if confirmed_disease and confirmed_disease != updated.get("cancer_type", ""):
                updated["cancer_type"] = confirmed_disease
                applied_fields.append("cancer_type")
            if confirmed_drug and confirmed_drug != updated.get("therapy_agent", ""):
                updated["therapy_agent"] = confirmed_drug
                applied_fields.append("therapy_agent")
                inferred_class = _infer_therapy_class(confirmed_drug)
                if inferred_class != "unknown":
                    updated["therapy_class"] = inferred_class
                    applied_fields.append("therapy_class")
            if default_timing != "unknown":
                updated["timing_category"] = default_timing
                applied_fields.append("timing_category")
            if ready and parse_bool(updated.get("include_flag", "true"), default=True):
                updated["include_flag"] = "true"
            updated["response_label_source"] = "manual_curation_sheet_applied"
            curated_rows.append(updated)

        # Optional projection manifest to route contrasts from cohort-level counts.
        pairing_state = _yes_no_unknown(curation.get("paired_pre_post_available", ""))
        has_on = _schema_has_timing(timing_schema, "on-treatment")
        has_post = _schema_has_timing(timing_schema, "post-treatment")
        transition_timing = "on-treatment" if has_on else ("post-treatment" if has_post else "")

        projection_count = 0
        if n_resp is not None and n_nonresp is not None and has_pre:
            template = rows[0]
            therapy_class = _first_nonempty(template.get("therapy_class", ""), _infer_therapy_class(confirmed_drug))
            therapy_agent = _first_nonempty(template.get("therapy_agent", ""), confirmed_drug)
            cancer_type = _first_nonempty(template.get("cancer_type", ""), confirmed_disease)
            input_class = template.get("input_class", "processed_matrix")
            analysis_role = template.get("analysis_role", "analysis")

            def add_projection_samples(label: str, n: int) -> None:
                nonlocal projection_count
                prefix = "R" if label == "responder" else "NR"
                for idx in range(1, n + 1):
                    patient_id = f"{cohort_id}__{prefix}_{idx:03d}"
                    pre_sample_id = f"{patient_id}__PRE"
                    projection_rows.append(
                        {
                            "cohort_id": cohort_id,
                            "sample_id": pre_sample_id,
                            "patient_id": patient_id,
                            "cancer_type": cancer_type,
                            "therapy_class": therapy_class,
                            "therapy_agent": therapy_agent,
                            "specimen_type": "bulk tumor sample",
                            "timing_category": "pre-treatment",
                            "response_label": label,
                            "pair_id": patient_id if pairing_state == "yes" and transition_timing else "",
                            "input_class": input_class,
                            "analysis_role": analysis_role,
                            "include_flag": "true" if ready else "false",
                            "exclude_reason": "" if ready else "pending_manual_review",
                            "response_label_source": "curation_projection_counts",
                        }
                    )
                    projection_count += 1
                    if pairing_state == "yes" and transition_timing:
                        transition_sample_id = f"{patient_id}__{transition_timing.replace('-', '_').upper()}"
                        projection_rows.append(
                            {
                                "cohort_id": cohort_id,
                                "sample_id": transition_sample_id,
                                "patient_id": patient_id,
                                "cancer_type": cancer_type,
                                "therapy_class": therapy_class,
                                "therapy_agent": therapy_agent,
                                "specimen_type": "bulk tumor sample",
                                "timing_category": transition_timing,
                                "response_label": label,
                                "pair_id": patient_id,
                                "input_class": input_class,
                                "analysis_role": analysis_role,
                                "include_flag": "true" if ready else "false",
                                "exclude_reason": "" if ready else "pending_manual_review",
                                "response_label_source": "curation_projection_counts",
                            }
                        )
                        projection_count += 1

            add_projection_samples("responder", n_resp)
            add_projection_samples("non_responder", n_nonresp)

        audit_rows.append(
            {
                "cohort_id": cohort_id,
                "curation_applied": "true",
                "curated_sample_rows": str(len(rows)),
                "projection_rows": str(projection_count),
                "status": "ready_for_modeling" if ready else "pending_manual_review",
                "notes": ";".join(sorted(set(applied_fields))) if applied_fields else "no_field_changes",
            }
        )

    write_tsv(
        out_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "pair_id",
            "input_class",
            "analysis_role",
            "include_flag",
            "exclude_reason",
            "response_label_source",
        ],
        rows=curated_rows,
    )

    write_tsv(
        projection_out,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "pair_id",
            "input_class",
            "analysis_role",
            "include_flag",
            "exclude_reason",
            "response_label_source",
        ],
        rows=projection_rows,
    )

    write_tsv(
        audit_out,
        fieldnames=[
            "cohort_id",
            "curation_applied",
            "curated_sample_rows",
            "projection_rows",
            "status",
            "notes",
        ],
        rows=audit_rows,
    )

    _mark_run(args, "method apply-curation", [out_manifest, projection_out, audit_out])
    print(f"Wrote {out_manifest}, {projection_out}, and {audit_out}")
    return 0


def cmd_ingest_run(args: argparse.Namespace) -> int:
    sample_manifest = read_tsv(Path(args.sample_manifest))
    out_file = Path(args.out) / "ingest_index.tsv"
    write_tsv(
        out_file,
        fieldnames=["cohort_id", "sample_id", "input_class", "ingest_status"],
        rows=[
            {
                "cohort_id": r.get("cohort_id", ""),
                "sample_id": r.get("sample_id", ""),
                "input_class": r.get("input_class", ""),
                "ingest_status": "stub_ready",
            }
            for r in sample_manifest
        ],
    )
    _mark_run(args, "ingest run", [out_file])
    print(f"Wrote {out_file}")
    return 0


def cmd_qc_run(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
        from .qc_plots import (
            PLOTTING_AVAILABLE,
            plot_library_size_boxplot,
            plot_gene_detection_barplot,
            calculate_housekeeping_stability,
            calculate_cooks_distance,
            plot_pca,
            plot_sample_distance_heatmap,
            calculate_variance_partition
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("QC requires numpy/pandas and pipeline qc_plots module.") from exc

    rows = read_tsv(Path(args.sample_manifest))
    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_cohort[row.get("cohort_id", "")].append(row)

    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    out_root = Path(args.out)
    outputs: list[Path] = []
    
    global_expr_dfs = []
    global_metadata_rows = []

    for cohort_id, cohort_rows in by_cohort.items():
        cohort_dir = out_root / cohort_id
        cohort_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = cohort_dir / "qc_metrics.tsv"
        outlier_file = cohort_dir / "sample_outlier_flags.tsv"
        summary_file = cohort_dir / "cohort_qc_summary.md"

        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None

        n_samples_manifest = len(cohort_rows)
        qc_status = "missing_expression"
        sample_outliers: list[dict[str, str]] = []
        metric_rows: list[dict[str, str]] = [
            {"metric": "n_samples_manifest", "value": str(n_samples_manifest)},
            {"metric": "expression_file", "value": str(expr_path or "")},
        ]

        if expr is not None and not expr.empty:
            expr, available = _resolve_sample_columns(expr, cohort_rows)
            if not available:
                expr = expr
            n_samples_expr = expr.shape[1]
            n_genes = expr.shape[0]
            lib_sizes = expr.fillna(0).sum(axis=0)
            zeros = (expr.fillna(0) == 0).sum(axis=0) / max(n_genes, 1)

            qc_status = "ok" if n_samples_expr >= 2 and n_genes > 0 else "insufficient_samples"
            metric_rows.extend(
                [
                    {"metric": "n_samples_expression", "value": str(n_samples_expr)},
                    {"metric": "n_genes", "value": str(n_genes)},
                    {"metric": "library_size_median", "value": f"{lib_sizes.median():.4f}"},
                    {"metric": "library_size_min", "value": f"{lib_sizes.min():.4f}"},
                    {"metric": "library_size_max", "value": f"{lib_sizes.max():.4f}"},
                    {"metric": "zero_fraction_median", "value": f"{zeros.median():.4f}"},
                    {"metric": "qc_status", "value": qc_status},
                ]
            )

            lib_z = (lib_sizes - lib_sizes.mean()) / (lib_sizes.std(ddof=0) or 1.0)
            zero_z = (zeros - zeros.mean()) / (zeros.std(ddof=0) or 1.0)
            
            expr_log = np.log2(expr.fillna(0) + 1.0)
            cooks_z = calculate_cooks_distance(expr_log)
            
            for sid in expr.columns:
                cz_val = cooks_z.get(sid, 0.0) if cooks_z is not None else 0.0
                outlier = abs(lib_z.get(sid, 0)) >= 3 or abs(zero_z.get(sid, 0)) >= 3 or abs(cz_val) >= 3
                reason = []
                if abs(lib_z.get(sid, 0)) >= 3:
                    reason.append("library_size_outlier")
                if abs(zero_z.get(sid, 0)) >= 3:
                    reason.append("zero_fraction_outlier")
                if abs(cz_val) >= 3:
                    reason.append("cooks_distance_leverage_outlier")
                    
                sample_outliers.append(
                    {
                        "sample_id": sid,
                        "is_outlier": "true" if outlier else "false",
                        "reason": ";".join(reason),
                    }
                )
                
            # Ensure unique gene index for cross-cohort concat in global QC.
            expr_for_global = expr.loc[~expr.index.duplicated(keep="first")]
            global_expr_dfs.append(expr_for_global)
            global_metadata_rows.extend(cohort_rows)
            
            # Sub-module Visualizations
            box_png = cohort_dir / "library_size_boxplot.png"
            bar_png = cohort_dir / "gene_detection_barplot.png"
            pca_png = cohort_dir / "pca_by_response.png"
            heat_png = cohort_dir / "sample_distance_heatmap.png"
            hk_tsv = cohort_dir / "housekeeping_stability.tsv"
            
            plot_library_size_boxplot(lib_sizes, box_png)
            plot_gene_detection_barplot(zeros, bar_png)
            
            metadata = pd.DataFrame(cohort_rows)
            plot_pca(expr_log, metadata, color_by="response_label", shape_by="timing_category", out_path=pca_png, title=f"{cohort_id} PCA")
            plot_sample_distance_heatmap(expr_log, heat_png)
            
            hk_stats = calculate_housekeeping_stability(expr_log)
            hk_df = pd.DataFrame(hk_stats)
            if not hk_df.empty:
                hk_df.to_csv(hk_tsv, sep="\t", index=False)
                outputs.append(hk_tsv)
                
            outputs.extend([box_png, bar_png, pca_png, heat_png])
        else:
            metric_rows.append({"metric": "qc_status", "value": qc_status})
            for row in cohort_rows:
                sample_outliers.append(
                    {
                        "sample_id": row.get("sample_id", ""),
                        "is_outlier": "false",
                        "reason": "no_expression_matrix",
                    }
                )

        write_tsv(metrics_file, fieldnames=["metric", "value"], rows=metric_rows)
        write_tsv(
            outlier_file,
            fieldnames=["sample_id", "is_outlier", "reason"],
            rows=sample_outliers,
        )
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        summary_lines = [
            "# Cohort QC Summary",
            "",
            f"- cohort_id: {cohort_id}",
            f"- n_samples_manifest: {n_samples_manifest}",
            f"- qc_status: {qc_status}",
            f"- expression_file: {expr_path or ''}",
            "",
            "## Visual Diagnostics",
        ]
        
        if PLOTTING_AVAILABLE and expr is not None and not expr.empty:
            summary_lines.extend([
                "![Library Sizes](library_size_boxplot.png)",
                "![Gene Detection](gene_detection_barplot.png)",
                "![PCA](pca_by_response.png)",
                "![Distance Heatmap](sample_distance_heatmap.png)",
            ])
            
        summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        outputs.extend([metrics_file, outlier_file, summary_file])
        
    # Layer 2: Global Batch Effect Assessment
    if global_expr_dfs and PLOTTING_AVAILABLE:
        combined_expr = pd.concat(global_expr_dfs, axis=1, join="inner")
        combined_expr = combined_expr.loc[:, ~combined_expr.columns.duplicated()]
        global_metadata = pd.DataFrame(global_metadata_rows).drop_duplicates(subset=["sample_id"])
        
        combined_expr_log = np.log2(combined_expr.fillna(0) + 1.0)
        
        batch_dir = out_root / "global_batch_assessment"
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        pca_cohort_png = batch_dir / "combined_pca_by_cohort.png"
        pca_response_png = batch_dir / "combined_pca_by_response.png"
        
        plot_pca(combined_expr_log, global_metadata, color_by="cohort_id", shape_by=None, out_path=pca_cohort_png, title="Global PCA by Cohort")
        plot_pca(combined_expr_log, global_metadata, color_by="response_label", shape_by=None, out_path=pca_response_png, title="Global PCA by Response")
        
        vp = calculate_variance_partition(combined_expr_log, global_metadata, factors=["cohort_id", "response_label", "timing_category"])
        vp_df = pd.DataFrame([{"factor": k, "variance_explained_fraction": v} for k, v in vp.items()])
        vp_tsv = batch_dir / "variance_partition.tsv"
        vp_df.to_csv(vp_tsv, sep="\t", index=False)
        
        batch_summary = batch_dir / "batch_assessment_summary.md"
        batch_summary.write_text(
            f"# Global Batch Effect Assessment\n\n"
            f"## Variance Partition\n"
            f"Analyzed top variance principal components to quantify batch effect severity.\n\n"
            f"- Cohort Variance Explained: {vp.get('cohort_id', 0.0)*100:.1f}%\n"
            f"- Response Variance Explained: {vp.get('response_label', 0.0)*100:.1f}%\n"
            f"- Timing Variance Explained: {vp.get('timing_category', 0.0)*100:.1f}%\n\n"
            f"## Visualizations\n"
            f"![PCA Cohort](combined_pca_by_cohort.png)\n"
            f"![PCA Response](combined_pca_by_response.png)\n",
            encoding="utf-8"
        )
        outputs.extend([pca_cohort_png, pca_response_png, vp_tsv, batch_summary])

    _mark_run(args, "qc run", outputs)
    print(f"Wrote QC outputs under {out_root}")
    return 0


def _comparison_definition(
    contrast: str,
    case_ids: list[str],
    control_ids: list[str],
    case_label: str = "case",
    control_label: str = "control",
) -> str:
    return (
        f"{contrast}:"
        f"{case_label}={','.join(sorted(case_ids))};"
        f"{control_label}={','.join(sorted(control_ids))}"
    )


def _comparison_id(cohort_id: str, analysis_type: str, contrast_definition: str) -> str:
    payload = f"{cohort_id}|{analysis_type}|{contrast_definition}"
    return "cmp_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _infer_drug_class_from_rows(rows: list[dict[str, str]]) -> str:
    raw = " ".join(
        row.get(key, "")
        for row in rows[:1]
        for key in ["therapy_class", "therapy_agent", "therapy_agent_normalized"]
    ).lower()
    if not raw:
        return "unknown"
    has_pd1 = "pd1" in raw or "pd-1" in raw or "nivolumab" in raw or "pembrolizumab" in raw
    has_pdl1 = "pdl1" in raw or "pd-l1" in raw or "atezolizumab" in raw or "durvalumab" in raw
    has_ctla4 = "ctla" in raw or "ipilimumab" in raw or "tremelimumab" in raw
    if sum([has_pd1, has_pdl1, has_ctla4]) > 1 or "+" in raw or "combo" in raw:
        return "COMBO"
    if has_pd1:
        return "PD1"
    if has_pdl1:
        return "PDL1"
    if has_ctla4:
        return "CTLA4"
    return "OTHER"


def _collapse_cancer_group(raw: str) -> str:
    text = (raw or "").strip().lower()
    if "melanoma" in text:
        return "melanoma"
    if "nsclc" in text or "lung" in text:
        return "NSCLC"
    if "hnscc" in text or "head" in text or "neck" in text:
        return "HNSCC"
    return "other"


def cmd_de_run(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("DE requires numpy/pandas to be installed.") from exc
    import shutil
    import subprocess
    import tempfile
    import io

    try:
        from scipy.stats import ttest_ind, ttest_rel
    except Exception:  # noqa: BLE001
        ttest_ind = None
        ttest_rel = None

    rows = read_tsv(Path(args.sample_manifest))
    analysis_id = (getattr(args, "analysis_id", "") or "").strip()
    analysis_row = _analysis_registry_row(getattr(args, "analysis_registry", ""), analysis_id)
    contrast_for_logic = (
        analysis_row.get("legacy_contrast_alias", "") if analysis_row else ""
    ) or args.contrast
    rows = _filter_rows_for_analysis_membership(
        rows,
        membership_path=getattr(args, "analysis_membership", ""),
        analysis_id=analysis_id,
    )
    output_label = analysis_id or args.contrast
    cohorts = sorted({r.get("cohort_id", "") for r in rows if r.get("cohort_id")})
    out_root = Path(args.out) / output_label
    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    gene_id_mapping = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    min_hgnc_mapping_rate = float(getattr(args, "min_hgnc_mapping_rate", 0.60))
    max_unmapped_ensembl_fraction = float(getattr(args, "max_unmapped_ensembl_fraction", 0.20))
    max_duplicate_collapse_fraction = float(getattr(args, "max_duplicate_collapse_fraction", 0.25))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))
    allow_welch_fallback = bool(getattr(args, "allow_welch_fallback", False))

    outputs: list[Path] = []
    fieldnames = [
        "comparison_id",
        "analysis_id",
        "gene_id",
        "original_gene_id",
        "gene_symbol",
        "log2fc",
        "se_or_stat",
        "p_value",
        "fdr",
        "mean_expression",
        "contrast_family",
        "n_case",
        "n_control",
        "model_class",
        "normalization_method",
    ]
    registry_rows: list[dict[str, str]] = []
    registry_keys: set[tuple[str, str, str]] = set()
    cohort_summary: dict[str, dict[str, str]] = {}

    def _sample_drug_class(cohort_rows: list[dict[str, str]]) -> str:
        return _infer_drug_class_from_rows(cohort_rows)

    def _register_comparison(
        *,
        cohort_id: str,
        cohort_rows: list[dict[str, str]],
        analysis_type: str,
        contrast_definition: str,
        n_group_a: int,
        n_group_b: int,
        n_genes_tested: int,
        software: str,
    ) -> str:
        key = (cohort_id, analysis_type, contrast_definition)
        if key in registry_keys:
            raise RuntimeError(
                "Duplicate comparison registry key detected: "
                f"{cohort_id}, {analysis_type}, {contrast_definition}"
            )
        registry_keys.add(key)
        comparison_id = _comparison_id(cohort_id, analysis_type, contrast_definition)
        cancer_type = next((r.get("cancer_type", "") for r in cohort_rows if r.get("cancer_type")), "")
        registry_rows.append(
            {
                "comparison_id": comparison_id,
                "analysis_id": analysis_id or analysis_type,
                "analysis_type": analysis_type,
                "cohort_id": cohort_id,
                "cancer_type": cancer_type or "unknown",
                "drug_class": _sample_drug_class(cohort_rows),
                "contrast_definition": contrast_definition,
                "n_group_A": str(n_group_a),
                "n_group_B": str(n_group_b),
                "n_patients_A": str(n_group_a),
                "n_patients_B": str(n_group_b),
                "n_genes_tested": str(n_genes_tested),
                "software": software,
                "created_at": _timestamp_utc(),
            }
        )
        return comparison_id

    def bh_fdr(pvals: list[float]) -> list[float]:
        n = len(pvals)
        order = np.argsort(pvals)
        ranked = np.empty(n, dtype=float)
        prev = 1.0
        for i in range(n - 1, -1, -1):
            idx = order[i]
            rank = i + 1
            val = min(prev, pvals[idx] * n / rank)
            ranked[idx] = val
            prev = val
        return ranked.tolist()

    def _run_limma_trend(expr_log, case_ids: list[str], control_ids: list[str]) -> tuple[list[dict[str, str]], str]:
        rscript = shutil.which("Rscript")
        script = Path("scripts/rna_limma.R")
        if rscript and script.exists():
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                expr_path = tmpdir_path / "expr.tsv"
                meta_path = tmpdir_path / "metadata.tsv"
                out_path = tmpdir_path / "limma_results.tsv"
                expr_log.loc[:, case_ids + control_ids].to_csv(expr_path, sep="\t")
                meta_rows = [{"sample_id": sid, "group": "case"} for sid in case_ids]
                meta_rows.extend({"sample_id": sid, "group": "control"} for sid in control_ids)
                write_tsv(meta_path, fieldnames=["sample_id", "group"], rows=meta_rows)
                cmd = [
                    rscript,
                    str(script),
                    "--expr",
                    str(expr_path),
                    "--metadata",
                    str(meta_path),
                    "--group-col",
                    "group",
                    "--case",
                    "case",
                    "--control",
                    "control",
                    "--out",
                    str(out_path),
                ]
                try:
                    subprocess.run(cmd, check=True)
                    return read_tsv(out_path), "limma_trend"
                except subprocess.CalledProcessError:
                    pass

        if not allow_welch_fallback:
            raise RuntimeError(
                "limma-trend backend unavailable for normalized/log cohort. "
                "Install R limma and scripts/rna_limma.R dependencies, or rerun with --allow-welch-fallback."
            )

        case = expr_log[case_ids]
        control = expr_log[control_ids]
        mean_case = case.mean(axis=1)
        mean_control = control.mean(axis=1)
        log2fc = mean_case - mean_control
        if ttest_ind is None:
            se = (case.var(axis=1, ddof=1) / len(case_ids) + control.var(axis=1, ddof=1) / len(control_ids)) ** 0.5
            pvals = np.ones(expr_log.shape[0])
        else:
            _, pvals = ttest_ind(case.T.values, control.T.values, equal_var=False, nan_policy="omit")
            se = (case.var(axis=1, ddof=1) / len(case_ids) + control.var(axis=1, ddof=1) / len(control_ids)) ** 0.5
        fdr = bh_fdr(pvals.tolist())
        rows_out = []
        for idx, gene_id in enumerate(expr_log.index):
            rows_out.append(
                {
                    "gene_id": str(gene_id),
                    "log2fc": f"{log2fc.iloc[idx]:.6f}",
                    "se_or_stat": f"{se.iloc[idx]:.6f}",
                    "p_value": f"{pvals[idx]:.6g}",
                    "fdr": f"{fdr[idx]:.6g}",
                }
            )
        return rows_out, "welch_fallback_log2"

    for cohort in cohorts:
        cohort_rows = [r for r in rows if r.get("cohort_id", "") == cohort]
        input_class = next((r.get("input_class", "") for r in cohort_rows if r.get("input_class", "")), "")
        assay_type = _cohort_assay_type(cohort_rows)
        expr_path = resolve_primary_expression_path(cohort, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        contrast = contrast_for_logic.upper()
        canonical_to_original: dict[str, str] = {}

        file_path = out_root / f"{cohort}.tsv"
        out_root.mkdir(parents=True, exist_ok=True)

        exclusion_reason = _cohort_non_assay_exclusion_reason(cohort)
        if exclusion_reason:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            cohort_summary[cohort] = {
                "status": "excluded",
                "reason": exclusion_reason,
                "model_class": "",
                "top_gene": "",
                "top_effect": "",
            }
            continue

        explicit_assay_type = _cohort_declared_assay_type(cohort_rows)
        if explicit_assay_type in ASSAY_TYPE_HARD_EXCLUDE:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            cohort_summary[cohort] = {
                "status": "excluded",
                "reason": f"excluded_assay_type_{explicit_assay_type}",
                "model_class": "",
                "top_gene": "",
                "top_effect": "",
            }
            continue

        if expr is None or expr.empty:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            cohort_summary[cohort] = {
                "status": "blocked",
                "reason": "missing_or_empty_expression",
                "model_class": "",
                "top_gene": "",
                "top_effect": "",
            }
            continue

        if assay_type in {"unreadable", "normalized_other", "raw_counts_suspect"}:
            detector_module = importlib.import_module(".modules._01_dataset_intake.assay_detect", package=__package__)
            detected_assay_type = detector_module.classify_expression_matrix(expr).assay_type
            if assay_type == "unreadable" and detected_assay_type:
                assay_type = detected_assay_type
            elif detected_assay_type in ASSAY_TYPE_HARD_EXCLUDE:
                assay_type = detected_assay_type
        if assay_type in ASSAY_TYPE_HARD_EXCLUDE:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            cohort_summary[cohort] = {
                "status": "excluded",
                "reason": f"excluded_assay_type_{assay_type}",
                "model_class": "",
                "top_gene": "",
                "top_effect": "",
            }
            continue

        # Align columns to cohort sample IDs (with alias fallback)
        expr, available = _resolve_sample_columns(
            expr,
            cohort_rows,
            include_filter=contrast == "PRE_RESPONSE",
        )
        expr = expr.loc[:, available] if available else expr

        if expr.shape[1] < 2:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            cohort_summary[cohort] = {
                "status": "blocked",
                "reason": "insufficient_samples",
                "model_class": "",
                "top_gene": "",
                "top_effect": "",
            }
            continue

        agg_method = "sum" if assay_type == "raw_counts" else "mean"
        expr, canonical_map_rows, metrics = _standardize_expression_gene_ids(
            expr,
            mapping_path=gene_id_mapping,
            aggregation=agg_method,
        )
        canonical_to_original = {
            r.get("canonical_gene_id", ""): r.get("original_gene_ids", r.get("canonical_gene_id", ""))
            for r in canonical_map_rows
            if r.get("canonical_gene_id", "")
        }
        status, fail_reason = _evaluate_gene_id_quality(
            metrics,
            min_hgnc_mapping_rate=min_hgnc_mapping_rate,
            max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
            max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
        )
        if status != "pass" and not allow_weak_gene_mapping:
            raise RuntimeError(
                "Gene ID quality gate failed during de run for cohort "
                f"{cohort}: {fail_reason}. Provide a mapping file via --gene-id-mapping "
                "or rerun with --allow-weak-gene-mapping."
            )

        expr_log, norm_method = _harmonize_expression_for_assay(expr, assay_type)

        case_ids: list[str] = []
        control_ids: list[str] = []

        if contrast in RESPONSE_CONTRASTS:
            case_ids, control_ids = resolve_response_contrast_sample_ids(cohort_rows, contrast)
        elif contrast == "TREATMENT_DELTA":
            case_pre_sids, case_post_sids, control_pre_sids, control_post_sids = (
                resolve_treatment_delta_groups(cohort_rows)
            )
            
            valid_cases = [i for i in range(len(case_pre_sids)) if case_pre_sids[i] in expr_log.columns and case_post_sids[i] in expr_log.columns]
            valid_controls = [i for i in range(len(control_pre_sids)) if control_pre_sids[i] in expr_log.columns and control_post_sids[i] in expr_log.columns]
            
            case_pre_sids = [case_pre_sids[i] for i in valid_cases]
            case_post_sids = [case_post_sids[i] for i in valid_cases]
            control_pre_sids = [control_pre_sids[i] for i in valid_controls]
            control_post_sids = [control_post_sids[i] for i in valid_controls]
            
            if len(case_pre_sids) < 2 or len(control_pre_sids) < 2:
                _write_empty(file_path, fieldnames=fieldnames)
                outputs.append(file_path)
                cohort_summary[cohort] = {
                    "status": "blocked",
                    "reason": "insufficient_delta_pairs",
                    "model_class": "",
                    "top_gene": "",
                    "top_effect": "",
                }
                continue

            # Build paired deltas then fit moderated limma trend on the
            # common log2-scale DELTA values (responder-pairs vs NR-pairs).
            case_delta_ids = [f"case_delta_{i+1}" for i in range(len(case_pre_sids))]
            control_delta_ids = [f"control_delta_{i+1}" for i in range(len(control_pre_sids))]
            delta_columns = case_delta_ids + control_delta_ids
            delta_payload: dict[str, np.ndarray] = {}
            for idx, sid in enumerate(case_delta_ids):
                delta_payload[sid] = (
                    expr_log[case_post_sids[idx]].to_numpy(dtype=float)
                    - expr_log[case_pre_sids[idx]].to_numpy(dtype=float)
                )
            for idx, sid in enumerate(control_delta_ids):
                delta_payload[sid] = (
                    expr_log[control_post_sids[idx]].to_numpy(dtype=float)
                    - expr_log[control_pre_sids[idx]].to_numpy(dtype=float)
                )
            delta_expr = pd.DataFrame(delta_payload, index=expr_log.index).loc[:, delta_columns]

            de_rows, model_class = _run_limma_trend(delta_expr, case_delta_ids, control_delta_ids)
            if model_class == "limma_trend":
                model_class = "limma_trend_delta"
            elif model_class == "welch_fallback_log2":
                model_class = "welch_fallback_log2_delta"

            contrast_definition = _comparison_definition(
                contrast,
                case_pre_sids,
                control_pre_sids,
                case_label="responder_delta_pairs",
                control_label="non_responder_delta_pairs",
            )
            comparison_id = _register_comparison(
                cohort_id=cohort,
                cohort_rows=cohort_rows,
                analysis_type=contrast,
                contrast_definition=contrast_definition,
                n_group_a=len(case_pre_sids),
                n_group_b=len(control_pre_sids),
                n_genes_tested=len(de_rows),
                software=model_class,
            )
            rows_out = []
            for row in de_rows:
                gene_id = row.get("gene_id", "")
                rows_out.append(
                    {
                        "comparison_id": comparison_id,
                        "analysis_id": analysis_id or contrast,
                        "gene_id": gene_id,
                        "original_gene_id": canonical_to_original.get(gene_id, gene_id),
                        "gene_symbol": gene_id,
                        "log2fc": row.get("log2fc", ""),
                        "se_or_stat": row.get("se_or_stat", ""),
                        "p_value": row.get("p_value", ""),
                        "fdr": row.get("fdr", ""),
                        "mean_expression": (
                            f"{expr_log.loc[gene_id].mean():.6f}"
                            if gene_id in expr_log.index
                            else ""
                        ),
                        "contrast_family": contrast,
                        "n_case": str(len(case_pre_sids)),
                        "n_control": str(len(control_pre_sids)),
                        "model_class": model_class,
                        "normalization_method": norm_method,
                    }
                )
            write_tsv(file_path, fieldnames=fieldnames, rows=rows_out)
            outputs.append(file_path)
            top_gene = ""
            top_effect = ""
            if rows_out:
                try:
                    best = max(rows_out, key=lambda r: abs(float(r.get("log2fc", "0") or 0.0)))
                    top_gene = best.get("gene_id", "")
                    top_effect = best.get("log2fc", "")
                except Exception:  # noqa: BLE001
                    pass
            cohort_summary[cohort] = {
                "status": "completed",
                "reason": "",
                "model_class": model_class,
                "top_gene": top_gene,
                "top_effect": top_effect,
            }
            continue
        elif contrast == "TUMOR_VS_ADJACENT":
            if expr_path and "series_matrix" in expr_path.name.lower():
                annotations = load_series_matrix_annotations(expr_path)
            else:
                annotations = {}
            for row in cohort_rows:
                sid = row.get("sample_id", "")
                if not parse_bool(row.get("include_flag", "true"), default=True):
                    continue
                group = infer_tumor_adjacent_group(annotations.get(sid, {}))
                if group == "tumor":
                    case_ids.append(sid)
                elif group == "adjacent":
                    control_ids.append(sid)
        else:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            continue

        case_ids = [sid for sid in case_ids if sid in expr_log.columns]
        control_ids = [sid for sid in control_ids if sid in expr_log.columns]
        if len(case_ids) < 2 or len(control_ids) < 2:
            _write_empty(file_path, fieldnames=fieldnames)
            outputs.append(file_path)
            cohort_summary[cohort] = {
                "status": "blocked",
                "reason": "insufficient_case_or_control_samples",
                "model_class": "",
                "top_gene": "",
                "top_effect": "",
            }
            continue
        contrast_definition = _comparison_definition(
            contrast,
            case_ids,
            control_ids,
            case_label="responder" if contrast in RESPONSE_CONTRASTS else "tumor",
            control_label=(
                "non_responder"
                if contrast in RESPONSE_CONTRASTS
                else "adjacent"
            ),
        )
        de_models_module = importlib.import_module(".modules.06_within_cohort_de.de_models", package=__package__)
        resolve_de_backend = de_models_module.resolve_de_backend

        # Count-based DE (DESeq2/edgeR) or limma-trend on harmonized log2 scale.
        count_like_matrix = _looks_like_count_matrix(expr)
        de_backend = resolve_de_backend(
            assay_type=assay_type,
            count_like_matrix=count_like_matrix,
            hard_exclude_assays=ASSAY_TYPE_HARD_EXCLUDE,
        )
        if de_backend == "count_model":
            rscript = shutil.which("Rscript")
            if not rscript:
                raise RuntimeError("Rscript not found; required for raw-count DE.")

            method = getattr(args, "count_method", "deseq2").lower()
            script = Path("scripts/rna_deseq2.R") if method == "deseq2" else Path("scripts/rna_edger.R")
            if not script.exists():
                raise RuntimeError(f"Missing R DE script: {script}")

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                counts_path = tmpdir_path / "counts.tsv"
                meta_path = tmpdir_path / "metadata.tsv"
                out_path = tmpdir_path / "de_results.tsv"

                expr.loc[:, case_ids + control_ids].to_csv(counts_path, sep="\t")
                meta_rows = []
                for sid in case_ids:
                    meta_rows.append({"sample_id": sid, "group": "case"})
                for sid in control_ids:
                    meta_rows.append({"sample_id": sid, "group": "control"})
                write_tsv(meta_path, fieldnames=["sample_id", "group"], rows=meta_rows)
                extra_args = []

                cmd = [
                    rscript,
                    str(script),
                    "--counts",
                    str(counts_path),
                    "--metadata",
                    str(meta_path),
                    "--group-col",
                    "group",
                    "--case",
                    "case",
                    "--control",
                    "control",
                    "--out",
                    str(out_path),
                ] + extra_args
                subprocess.run(cmd, check=True)

                de_rows = read_tsv(out_path)
                comparison_id = _register_comparison(
                    cohort_id=cohort,
                    cohort_rows=cohort_rows,
                    analysis_type=contrast,
                    contrast_definition=contrast_definition,
                    n_group_a=len(case_ids),
                    n_group_b=len(control_ids),
                    n_genes_tested=len(de_rows),
                    software=method,
                )
                rows_out = []
                for row in de_rows:
                    gene_id = row.get("gene_id", "")
                    rows_out.append(
                        {
                            "comparison_id": comparison_id,
                            "analysis_id": analysis_id or contrast,
                            "gene_id": gene_id,
                            "original_gene_id": canonical_to_original.get(gene_id, gene_id),
                            "gene_symbol": gene_id,
                            "log2fc": row.get("log2fc", ""),
                            "se_or_stat": row.get("se_or_stat", ""),
                            "p_value": row.get("p_value", ""),
                            "fdr": row.get("fdr", ""),
                            "mean_expression": f"{expr_log.loc[gene_id].mean():.6f}" if gene_id in expr_log.index else "",
                            "contrast_family": contrast,
                            "n_case": str(len(case_ids)),
                            "n_control": str(len(control_ids)),
                            "model_class": method,
                            "normalization_method": "raw_counts",
                        }
                    )
                write_tsv(file_path, fieldnames=fieldnames, rows=rows_out)
                outputs.append(file_path)
                top_gene = ""
                top_effect = ""
                if rows_out:
                    try:
                        best = max(rows_out, key=lambda r: abs(float(r.get("log2fc", "0") or 0.0)))
                        top_gene = best.get("gene_id", "")
                        top_effect = best.get("log2fc", "")
                    except Exception:  # noqa: BLE001
                        pass
                cohort_summary[cohort] = {
                    "status": "completed",
                    "reason": "",
                    "model_class": method,
                    "top_gene": top_gene,
                    "top_effect": top_effect,
                }
                continue

        de_rows, model_class = _run_limma_trend(expr_log, case_ids, control_ids)
        comparison_id = _register_comparison(
            cohort_id=cohort,
            cohort_rows=cohort_rows,
            analysis_type=contrast,
            contrast_definition=contrast_definition,
            n_group_a=len(case_ids),
            n_group_b=len(control_ids),
            n_genes_tested=len(de_rows),
            software=model_class,
        )
        rows_out = []
        for row in de_rows:
            gene_id = row.get("gene_id", "")
            rows_out.append(
                {
                    "comparison_id": comparison_id,
                    "analysis_id": analysis_id or contrast,
                    "gene_id": gene_id,
                    "original_gene_id": canonical_to_original.get(gene_id, gene_id),
                    "gene_symbol": gene_id,
                    "log2fc": row.get("log2fc", ""),
                    "se_or_stat": row.get("se_or_stat", ""),
                    "p_value": row.get("p_value", ""),
                    "fdr": row.get("fdr", ""),
                    "mean_expression": f"{expr_log.loc[gene_id].mean():.6f}" if gene_id in expr_log.index else "",
                    "contrast_family": contrast,
                    "n_case": str(len(case_ids)),
                    "n_control": str(len(control_ids)),
                    "model_class": model_class,
                    "normalization_method": norm_method,
                }
            )

        write_tsv(file_path, fieldnames=fieldnames, rows=rows_out)
        outputs.append(file_path)
        top_gene = ""
        top_effect = ""
        if rows_out:
            try:
                best = max(rows_out, key=lambda r: abs(float(r.get("log2fc", "0") or 0.0)))
                top_gene = best.get("gene_id", "")
                top_effect = best.get("log2fc", "")
            except Exception:  # noqa: BLE001
                pass
        cohort_summary[cohort] = {
            "status": "completed",
            "reason": "",
            "model_class": model_class,
            "top_gene": top_gene,
            "top_effect": top_effect,
        }

    registry_file = Path(getattr(args, "comparison_registry", "results/spec_007/comparison_registry.tsv"))
    if str(registry_file) == "AUTO":
        registry_file = Path(args.out) / output_label / "comparison_registry.tsv"
    merged_registry: dict[tuple[str, str, str], dict[str, str]] = {}
    if registry_file.exists():
        for row in read_tsv(registry_file):
            key = (
                row.get("cohort_id", ""),
                row.get("analysis_type", ""),
                row.get("contrast_definition", ""),
            )
            if all(key):
                merged_registry[key] = row
    for row in registry_rows:
        key = (
            row.get("cohort_id", ""),
            row.get("analysis_type", ""),
            row.get("contrast_definition", ""),
        )
        if all(key):
            merged_registry[key] = row
    write_tsv(
        registry_file,
        fieldnames=[
            "comparison_id",
            "analysis_id",
            "analysis_type",
            "cohort_id",
            "cancer_type",
            "drug_class",
            "contrast_definition",
            "n_group_A",
            "n_group_B",
            "n_patients_A",
            "n_patients_B",
            "n_genes_tested",
            "software",
            "created_at",
        ],
        rows=merged_registry.values(),
    )
    outputs.append(registry_file)

    migration_file = out_root / "de_model_migration.md"
    baseline_root_raw = (getattr(args, "baseline_de_dir", "") or "").strip()
    baseline_root = Path(baseline_root_raw) if baseline_root_raw else None
    lines = [
        "# DE Model Migration",
        "",
        f"- contrast: {contrast_for_logic}",
        f"- analysis_id: {analysis_id or '(legacy contrast mode)'}",
        f"- current_output: {out_root}",
        f"- baseline_output: {baseline_root if baseline_root else '(none provided)'}",
        "",
        "| cohort_id | status | model_class | top_gene | top_log2fc | baseline_model_class | changed_vs_baseline | reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cohort_id in sorted(cohort_summary.keys()):
        current = cohort_summary[cohort_id]
        baseline_model = ""
        changed = ""
        if baseline_root:
            baseline_file = baseline_root / contrast_for_logic / f"{cohort_id}.tsv"
            if baseline_file.exists():
                baseline_rows = read_tsv(baseline_file)
                baseline_models = sorted(
                    {
                        (r.get("model_class", "") or "").strip()
                        for r in baseline_rows
                        if (r.get("model_class", "") or "").strip()
                    }
                )
                baseline_model = ", ".join(baseline_models)
                if baseline_model or current.get("model_class", ""):
                    changed = "true" if baseline_model != current.get("model_class", "") else "false"
        lines.append(
            "| "
            + " | ".join(
                [
                    cohort_id,
                    current.get("status", ""),
                    current.get("model_class", ""),
                    current.get("top_gene", ""),
                    current.get("top_effect", ""),
                    baseline_model,
                    changed,
                    current.get("reason", ""),
                ]
            )
            + " |"
        )
    migration_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs.append(migration_file)

    repro_dir = out_root / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)
    repro_commands = repro_dir / "commands.sh"
    command_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "python -m pipeline.cli de run \\",
        f"  --contrast {contrast_for_logic} \\",
        f"  --sample-manifest {args.sample_manifest} \\",
        f"  --expression-manifest {args.expression_manifest} \\",
        f"  --downloads-root {args.downloads_root} \\",
        f"  --count-method {args.count_method} \\",
        f"  --comparison-registry {registry_file} \\",
    ]
    if analysis_id:
        command_lines.append(f"  --analysis-id {analysis_id} \\")
    if getattr(args, "analysis_registry", ""):
        command_lines.append(f"  --analysis-registry {getattr(args, 'analysis_registry', '')} \\")
    if getattr(args, "analysis_membership", ""):
        command_lines.append(f"  --analysis-membership {getattr(args, 'analysis_membership', '')} \\")
    if baseline_root_raw:
        command_lines.append(f"  --baseline-de-dir {baseline_root_raw} \\")
    command_lines.extend([f"  --out {args.out}", ""])
    repro_commands.write_text("\n".join(command_lines), encoding="utf-8")
    repro_env = repro_dir / "environment.yml"
    repro_env.write_text(
        "\n".join(
            [
                "name: rnaseq-stage06-de",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                f"  - python={sys.version_info.major}.{sys.version_info.minor}",
                "  - pandas",
                "  - numpy",
                "  - scipy",
                "  - r-base",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_checksums = repro_dir / "checksums.sha256"
    checksum_targets = sorted(out_root.glob("*.tsv")) + [registry_file, migration_file]
    checksum_lines: list[str] = []
    seen: set[Path] = set()
    for target in checksum_targets:
        if target in seen or not target.exists():
            continue
        seen.add(target)
        checksum_lines.append(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {target}")
    repro_checksums.write_text(
        "\n".join(checksum_lines) + ("\n" if checksum_lines else ""),
        encoding="utf-8",
    )
    outputs.extend([repro_commands, repro_env, repro_checksums])
    _mark_run(args, "de run", outputs)
    print(f"Wrote DE outputs under {out_root}")
    return 0


def cmd_meta_run(args: argparse.Namespace) -> int:
    try:
        import numpy as np
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Meta-analysis requires numpy.") from exc
    import math

    de_dir_path = Path(args.de_dir)
    analysis_id = (getattr(args, "analysis_id", "") or "").strip()
    output_label = analysis_id or args.contrast
    de_root = de_dir_path / output_label
    out_file = Path(args.out) / output_label / "meta_effects.tsv"
    loo_detail_file = Path(args.out) / output_label / "meta_leave_one_out.tsv"
    loo_summary_file = Path(args.out) / output_label / "meta_leave_one_out_summary.tsv"
    subgroup_root = Path(args.out) / output_label / "subgroups"
    meta_regression_file = Path(args.out) / output_label / "meta_regression_cancer_group.tsv"
    meta_single_file = Path(args.out) / output_label / "meta_single_cohort.tsv"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    sample_manifest_raw = (getattr(args, "sample_manifest", "") or "").strip()
    sample_manifest_path = Path(sample_manifest_raw) if sample_manifest_raw else Path()
    exclude_k1 = not bool(getattr(args, "include_k1_genes", False))
    enable_subgroups = bool(getattr(args, "enable_subgroups", False))
    use_knapp_hartung = bool(getattr(args, "knapp_hartung", False))
    effect_scale_fields = [
        "effect_scale",
        "effect_scale_status",
        "effect_unit",
        "effect_direction_definition",
        "effect_reference_group",
        "common_effect_scale",
    ]

    def _effect_direction_definition(label: str) -> str:
        label_upper = (label or "").upper()
        if "DELTA" in label_upper:
            return "responder_delta_minus_non_responder_delta"
        return "responder_minus_non_responder"

    effect_scale_contract = {
        "effect_scale": "common_log2_response_logfc",
        "effect_scale_status": "common_scale",
        "effect_unit": "log2_fold_change",
        "effect_direction_definition": _effect_direction_definition(output_label),
        "effect_reference_group": "non_responder",
        "common_effect_scale": "true",
    }

    de_files = sorted(de_root.glob("*.tsv"))
    fieldnames = [
        "analysis_id",
        "gene_id",
        "original_gene_id",
        "gene_symbol",
        "meta_effect_fixed",
        "meta_effect_random",
        "meta_se_fixed",
        "meta_se_random",
        "meta_p_value",
        "meta_fdr",
        "meta_p",
        "heterogeneity_q",
        "heterogeneity_i2",
        "i2",
        "tau_squared",
        "n_cohorts_contributed",
        "n_patients_contributed",
        "direction_consistency",
        "loco_max_delta_padj",
        "loco_unstable",
        *effect_scale_fields,
    ]
    if not de_files:
        _write_empty(out_file, fieldnames=fieldnames)
        _write_empty(
            loo_detail_file,
            fieldnames=[
                "gene_id",
                "analysis_id",
                "original_gene_id",
                "gene_symbol",
                "omitted_cohort",
                "n_cohorts_contributed",
                "meta_effect_random",
                "meta_se_random",
                "meta_p_value",
                "direction_consistency",
                *effect_scale_fields,
            ],
        )
        _write_empty(
            loo_summary_file,
            fieldnames=[
                "gene_id",
                "analysis_id",
                "original_gene_id",
                "gene_symbol",
                "n_cohorts_total",
                "n_loo_runs",
                "full_meta_effect_random",
                "full_meta_fdr",
                "max_abs_delta_effect",
                "direction_flip_any",
                "loo_support_fraction",
                "signature_stability_label",
                "notes",
                *effect_scale_fields,
            ],
        )
        _write_empty(
            meta_regression_file,
            fieldnames=["analysis_id", "gene_id", "beta_NSCLC", "beta_HNSCC", "beta_other", "n_cohorts", "status", "notes"],
        )
        _write_empty(
            meta_single_file,
            fieldnames=[
                "gene_id",
                "analysis_id",
                "original_gene_id",
                "gene_symbol",
                "n_cohorts_contributed",
                "n_patients_contributed",
                "meta_basis",
                "status",
                "notes",
                *effect_scale_fields,
            ],
        )
        _mark_run(
            args,
            "meta run",
            [out_file, loo_detail_file, loo_summary_file, meta_regression_file, meta_single_file],
        )
        print(f"Wrote {out_file}")
        return 0

    def _safe_float(raw: str, default: float = float("nan")) -> float:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return default
        return value if np.isfinite(value) else default

    def _is_common_scale_normalization(normalization_method: str) -> bool:
        norm = (normalization_method or "").strip().lower()
        if not norm:
            return False
        if "log2" in norm:
            return True
        return norm in {
            "raw_counts",
            "as_is_log_scale",
            "rlog_vst",
            "rlog",
            "vst",
        }

    def _cohort_context_from_manifest(path: Path) -> dict[str, dict[str, str]]:
        if not str(path) or not path.exists() or not path.is_file():
            return {}
        by_cohort: dict[str, dict[str, str]] = {}
        rows_local = read_tsv(path)
        for cohort_id in sorted({r.get("cohort_id", "") for r in rows_local if r.get("cohort_id")}):
            cohort_rows = [r for r in rows_local if r.get("cohort_id") == cohort_id]
            included = [r for r in cohort_rows if parse_bool(r.get("include_flag", "true"), default=True)]
            cancer_raw = next((r.get("cancer_type", "") for r in cohort_rows if r.get("cancer_type")), "unknown")
            by_cohort[cohort_id] = {
                "cancer_type": _collapse_cancer_group(cancer_raw),
                "drug_class": _infer_drug_class_from_rows(cohort_rows),
                "n_patients": str(len({r.get("patient_id", "") or r.get("sample_id", "") for r in included})),
            }
        return by_cohort

    def _context_from_comparison_registry(path: Path) -> dict[str, dict[str, str]]:
        if not path or not path.exists() or not path.is_file():
            return {}
        ctx: dict[str, dict[str, str]] = {}
        for row in read_tsv(path):
            cohort_id = row.get("cohort_id", "")
            if not cohort_id:
                continue
            ctx[cohort_id] = {
                "cancer_type": _collapse_cancer_group(row.get("cancer_type", "") or "unknown"),
                "drug_class": row.get("drug_class", "") or "unknown",
                "n_patients": str(
                    int(float(row.get("n_patients_A", "0") or 0))
                    + int(float(row.get("n_patients_B", "0") or 0))
                ),
            }
        return ctx

    cohort_context = _cohort_context_from_manifest(sample_manifest_path)
    raw_registry_path = getattr(args, "comparison_registry", "")
    registry_path = Path(raw_registry_path) if raw_registry_path else Path()
    if not raw_registry_path and (de_dir_path / "comparison_registry.tsv").exists():
        registry_path = de_dir_path / "comparison_registry.tsv"
    for cohort_id, ctx in _context_from_comparison_registry(registry_path).items():
        existing = cohort_context.setdefault(cohort_id, {})
        existing.update({k: v for k, v in ctx.items() if v})

    def _compute_meta_stats(entries_local: list[tuple[float, float, float, str]]) -> dict[str, float]:
        effects = np.array([e[0] for e in entries_local], dtype=float)
        ses = np.array([e[1] for e in entries_local], dtype=float)
        k_local = len(entries_local)

        w_fixed = 1.0 / (ses**2)
        meta_effect_fixed_local = float(np.sum(w_fixed * effects) / np.sum(w_fixed))
        meta_se_fixed_local = float((1.0 / np.sum(w_fixed)) ** 0.5)

        if k_local > 1:
            q_local = float(np.sum(w_fixed * (effects - meta_effect_fixed_local) ** 2))
            df_local = k_local - 1
            i2_local = max(0.0, (q_local - df_local) / q_local) if q_local > 0 else 0.0
            c_local = np.sum(w_fixed) - np.sum(w_fixed**2) / np.sum(w_fixed)
            tau2_local = max(0.0, (q_local - df_local) / c_local) if c_local > 0 else 0.0
        else:
            q_local = 0.0
            i2_local = 0.0
            tau2_local = 0.0

        w_random = 1.0 / (ses**2 + tau2_local)
        meta_effect_random_local = float(np.sum(w_random * effects) / np.sum(w_random))
        meta_se_random_local = float((1.0 / np.sum(w_random)) ** 0.5)
        z_local = meta_effect_random_local / meta_se_random_local if meta_se_random_local > 0 else 0.0
        meta_p_local = 2.0 * (1.0 - 0.5 * (1 + math.erf(abs(z_local) / np.sqrt(2))))
        kh_q = 1.0
        if use_knapp_hartung and k_local > 1 and np.sum(w_random) > 0:
            resid = effects - meta_effect_random_local
            kh_q = float(np.sum(w_random * resid * resid) / max(k_local - 1, 1))
            kh_q = max(kh_q, 1e-12)
            se_kh = float(np.sqrt(kh_q) * meta_se_random_local)
            t_stat = meta_effect_random_local / se_kh if se_kh > 0 else 0.0
            try:
                from scipy.stats import t as student_t

                meta_p_local = float(2.0 * student_t.sf(abs(t_stat), df=max(k_local - 1, 1)))
            except Exception:  # noqa: BLE001
                meta_p_local = 2.0 * (1.0 - 0.5 * (1 + math.erf(abs(t_stat) / np.sqrt(2))))

        dominant_sign_local = np.sign(meta_effect_random_local)
        n_same_local = int(np.sum(np.sign(effects) == dominant_sign_local))
        direction_consistency_local = n_same_local / k_local if k_local > 0 else 0.0

        return {
            "meta_effect_fixed": meta_effect_fixed_local,
            "meta_effect_random": meta_effect_random_local,
            "meta_se_fixed": meta_se_fixed_local,
            "meta_se_random": meta_se_random_local,
            "meta_p_value": float(meta_p_local),
            "heterogeneity_q": q_local,
            "heterogeneity_i2": i2_local,
            "tau_squared": tau2_local,
            "n_cohorts_contributed": float(k_local),
            "direction_consistency": direction_consistency_local,
            "kh_q": kh_q,
        }

    # Collect per-cohort effects
    gene_map: dict[str, list[tuple[float, float, float, str]]] = {}
    gene_original_map: dict[str, set[str]] = defaultdict(set)
    gene_symbol_map: dict[str, str] = {}
    cohort_patient_counts: dict[str, int] = {}
    scale_guard_violations: list[str] = []
    for path in de_files:
        cohort_label = path.stem
        cohort_patient_counts[cohort_label] = int(
            _safe_float(cohort_context.get(cohort_label, {}).get("n_patients", "0"), 0.0)
        )
        for row in read_tsv(path):
            gene_id = row.get("gene_id", "")
            if not gene_id:
                continue
            normalization_method = row.get("normalization_method", "")
            if not _is_common_scale_normalization(normalization_method):
                scale_guard_violations.append(
                    f"{cohort_label}:{gene_id}:{normalization_method or 'missing'}"
                )
                continue
            model_class = (row.get("model_class", "") or "").strip().lower()
            if model_class in {"welch_t_test_log2", "welch_t_test_delta_interaction"}:
                # Legacy fallback models are accepted only when explicitly requested upstream.
                pass
            gene_original = row.get("original_gene_id", "") or gene_id
            gene_symbol = row.get("gene_symbol", "") or gene_id
            try:
                effect = float(row.get("log2fc", "nan"))
                se = float(row.get("se_or_stat", "nan"))
                pval = float(row.get("p_value", "nan"))
            except ValueError:
                continue
            if not np.isfinite(effect) or not np.isfinite(se) or se <= 0:
                continue
            gene_map.setdefault(gene_id, []).append((effect, se, pval, cohort_label))
            gene_original_map[gene_id].add(gene_original)
            if gene_id not in gene_symbol_map and gene_symbol:
                gene_symbol_map[gene_id] = gene_symbol

    if scale_guard_violations:
        preview = "; ".join(scale_guard_violations[:8])
        if len(scale_guard_violations) > 8:
            preview += f"; ... (+{len(scale_guard_violations) - 8} more)"
        raise RuntimeError(
            "Meta run aborted by common-scale input guard: found non-contract normalization_method "
            f"values in DE inputs ({preview})."
        )

    out_rows = []
    single_cohort_rows: list[dict[str, str]] = []
    for gene_id, entries in gene_map.items():
        stats = _compute_meta_stats(entries)
        k = int(stats["n_cohorts_contributed"])
        contributing_cohorts = {e[3] for e in entries}
        n_patients_contributed = sum(cohort_patient_counts.get(c, 0) for c in contributing_cohorts)
        if exclude_k1 and k < 2:
            single_cohort_rows.append(
                {
                    "analysis_id": output_label,
                    "gene_id": gene_id,
                    "original_gene_id": "|".join(sorted(gene_original_map.get(gene_id, {gene_id}))),
                    "gene_symbol": gene_symbol_map.get(gene_id, gene_id),
                    "n_cohorts_contributed": str(k),
                    "n_patients_contributed": str(n_patients_contributed),
                    "meta_basis": "single_cohort",
                    "status": "excluded_from_pooled_fdr",
                    "notes": "k=1 excluded by default common-evidence policy",
                    **effect_scale_contract,
                }
            )
            continue

        out_rows.append(
            {
                "analysis_id": output_label,
                "gene_id": gene_id,
                "original_gene_id": "|".join(sorted(gene_original_map.get(gene_id, {gene_id}))),
                "gene_symbol": gene_symbol_map.get(gene_id, gene_id),
                "meta_effect_fixed": f"{stats['meta_effect_fixed']:.6f}",
                "meta_effect_random": f"{stats['meta_effect_random']:.6f}",
                "meta_se_fixed": f"{stats['meta_se_fixed']:.6f}",
                "meta_se_random": f"{stats['meta_se_random']:.6f}",
                "meta_p_value": f"{stats['meta_p_value']:.6g}",
                "meta_fdr": "pending",
                "meta_p": f"{stats['meta_p_value']:.6g}",
                "heterogeneity_q": f"{stats['heterogeneity_q']:.6f}",
                "heterogeneity_i2": f"{stats['heterogeneity_i2']:.4f}",
                "i2": f"{stats['heterogeneity_i2'] * 100.0:.4f}",
                "tau_squared": f"{stats['tau_squared']:.6f}",
                "n_cohorts_contributed": str(k),
                "n_patients_contributed": str(n_patients_contributed),
                "direction_consistency": f"{stats['direction_consistency']:.4f}",
                "loco_max_delta_padj": "",
                "loco_unstable": "false",
                **effect_scale_contract,
                "_entries": entries,  # kept for forest plots, stripped before write
            }
        )

    # FDR
    pvals = [float(r["meta_p_value"]) for r in out_rows]
    order = np.argsort(pvals)
    fdr = np.empty(len(pvals), dtype=float)
    prev = 1.0
    for i in range(len(pvals) - 1, -1, -1):
        idx = order[i]
        rank = i + 1
        val = min(prev, pvals[idx] * len(pvals) / rank)
        fdr[idx] = val
        prev = val
    for i, row in enumerate(out_rows):
        row["meta_fdr"] = f"{fdr[i]:.6g}"

    # ---- Forest Plots (top 50 significant genes) ----
    if not bool(getattr(args, "skip_forest_plots", False)):
        from .modules._viz.forest import write_meta_forest_plots

        write_meta_forest_plots(
            out_rows=out_rows,
            out_dir=out_file.parent / "forest_plots",
            max_genes=50,
            fdr_threshold=0.05,
        )

    # Strip internal _entries before writing
    full_row_map = {row["gene_id"]: row for row in out_rows}
    loo_detail_rows: list[dict[str, str]] = []
    loo_summary_rows: list[dict[str, str]] = []
    for gene_id, entries in gene_map.items():
        cohorts = sorted({e[3] for e in entries})
        gene_symbol = gene_symbol_map.get(gene_id, gene_id)
        original_gene_id = "|".join(sorted(gene_original_map.get(gene_id, {gene_id})))
        full_row = full_row_map.get(gene_id, {})
        full_effect = float(full_row.get("meta_effect_random", "0.0") or 0.0)
        full_fdr = float(full_row.get("meta_fdr", "1.0") or 1.0)
        full_signature_like = full_fdr <= 0.05 and abs(full_effect) >= 1.0
        full_sign = np.sign(full_effect)

        gene_loo_effects: list[float] = []
        gene_loo_signature_support = 0

        if len(cohorts) >= 2:
            for omitted_cohort in cohorts:
                kept = [e for e in entries if e[3] != omitted_cohort]
                if not kept:
                    continue
                loo_stats = _compute_meta_stats(kept)
                loo_effect = float(loo_stats["meta_effect_random"])
                gene_loo_effects.append(loo_effect)
                if full_signature_like and np.sign(loo_effect) == full_sign and abs(loo_effect) >= 1.0:
                    gene_loo_signature_support += 1
                loo_detail_rows.append(
                    {
                        "gene_id": gene_id,
                        "analysis_id": output_label,
                        "original_gene_id": original_gene_id,
                        "gene_symbol": gene_symbol,
                        "omitted_cohort": omitted_cohort,
                        "n_cohorts_contributed": str(int(loo_stats["n_cohorts_contributed"])),
                        "meta_effect_random": f"{loo_effect:.6f}",
                        "meta_se_random": f"{loo_stats['meta_se_random']:.6f}",
                        "meta_p_value": f"{loo_stats['meta_p_value']:.6g}",
                        "direction_consistency": f"{loo_stats['direction_consistency']:.4f}",
                        **effect_scale_contract,
                    }
                )

        n_loo_runs = len(gene_loo_effects)
        if n_loo_runs > 0:
            max_abs_delta_effect = max(abs(v - full_effect) for v in gene_loo_effects)
            direction_flip_any = any(np.sign(v) != full_sign for v in gene_loo_effects if np.sign(v) != 0 and full_sign != 0)
        else:
            max_abs_delta_effect = float("nan")
            direction_flip_any = False

        if n_loo_runs == 0:
            stability_label = "insufficient_cohorts_for_loo"
            loo_support_fraction = ""
            notes = "Gene has fewer than 2 contributing cohorts."
        elif not full_signature_like:
            stability_label = "not_full_signature"
            loo_support_fraction = ""
            notes = "Full meta result does not meet signature-like threshold."
        else:
            loo_support_fraction_val = gene_loo_signature_support / n_loo_runs if n_loo_runs > 0 else 0.0
            loo_support_fraction = f"{loo_support_fraction_val:.4f}"
            stability_label = "stable" if loo_support_fraction_val == 1.0 and not direction_flip_any else "unstable"
            notes = "Stable requires same direction and |effect|>=1.0 for all leave-one-out runs."

        if full_row:
            full_row["loco_max_delta_padj"] = (
                f"{max_abs_delta_effect:.6f}" if np.isfinite(max_abs_delta_effect) else ""
            )
            full_row["loco_unstable"] = "true" if direction_flip_any or stability_label == "unstable" else "false"

        loo_summary_rows.append(
            {
                "gene_id": gene_id,
                "analysis_id": output_label,
                "original_gene_id": original_gene_id,
                "gene_symbol": gene_symbol,
                "n_cohorts_total": str(len(cohorts)),
                "n_loo_runs": str(n_loo_runs),
                "full_meta_effect_random": f"{full_effect:.6f}",
                "full_meta_fdr": f"{full_fdr:.6g}",
                "max_abs_delta_effect": f"{max_abs_delta_effect:.6f}" if np.isfinite(max_abs_delta_effect) else "",
                "direction_flip_any": "true" if direction_flip_any else "false",
                "loo_support_fraction": loo_support_fraction,
                "signature_stability_label": stability_label,
                "notes": notes,
                **effect_scale_contract,
            }
        )

    write_tsv(
        loo_detail_file,
        fieldnames=[
            "gene_id",
            "analysis_id",
            "original_gene_id",
            "gene_symbol",
            "omitted_cohort",
            "n_cohorts_contributed",
            "meta_effect_random",
            "meta_se_random",
            "meta_p_value",
            "direction_consistency",
            *effect_scale_fields,
        ],
        rows=loo_detail_rows,
    )
    write_tsv(
        loo_summary_file,
        fieldnames=[
            "gene_id",
            "analysis_id",
            "original_gene_id",
            "gene_symbol",
            "n_cohorts_total",
            "n_loo_runs",
            "full_meta_effect_random",
            "full_meta_fdr",
            "max_abs_delta_effect",
            "direction_flip_any",
            "loo_support_fraction",
            "signature_stability_label",
            "notes",
            *effect_scale_fields,
        ],
        rows=loo_summary_rows,
    )

    subgroup_outputs: list[Path] = []

    def _write_subgroup_meta(subgroup_type: str, subgroup_value: str, cohort_ids: set[str]) -> Path | None:
        subgroup_gene_map: dict[str, list[tuple[float, float, float, str]]] = {}
        for gene_id, entries in gene_map.items():
            kept_entries = [entry for entry in entries if entry[3] in cohort_ids]
            if kept_entries:
                subgroup_gene_map[gene_id] = kept_entries
        if not subgroup_gene_map:
            return None

        rows_local: list[dict[str, str]] = []
        for gene_id, entries in subgroup_gene_map.items():
            stats = _compute_meta_stats(entries)
            p = float(stats["meta_p_value"])
            contributing = {e[3] for e in entries}
            rows_local.append(
                {
                    "subgroup_type": subgroup_type,
                    "analysis_id": output_label,
                    "subgroup_value": subgroup_value,
                    "gene_id": gene_id,
                    "meta_p": f"{p:.6g}",
                    "meta_fdr": "pending",
                    "meta_effect_random": f"{stats['meta_effect_random']:.6f}",
                    "n_cohorts_contributed": str(int(stats["n_cohorts_contributed"])),
                    "n_patients_contributed": str(
                        sum(cohort_patient_counts.get(c, 0) for c in contributing)
                    ),
                    "i2": f"{stats['heterogeneity_i2'] * 100.0:.4f}",
                    **effect_scale_contract,
                }
            )
        pvals_local = [_safe_float(r["meta_p"], 1.0) for r in rows_local]
        order_local = np.argsort(pvals_local)
        fdr_local = np.empty(len(pvals_local), dtype=float)
        prev_local = 1.0
        for idx_rank in range(len(pvals_local) - 1, -1, -1):
            idx = order_local[idx_rank]
            rank = idx_rank + 1
            val = min(prev_local, pvals_local[idx] * len(pvals_local) / rank)
            fdr_local[idx] = val
            prev_local = val
        for idx, row in enumerate(rows_local):
            row["meta_fdr"] = f"{fdr_local[idx]:.6g}"

        safe_value = re.sub(r"[^A-Za-z0-9_.-]+", "_", subgroup_value or "unknown").strip("_") or "unknown"
        group_dir = subgroup_root / ("by_cancer_type" if subgroup_type == "cancer_type" else "by_drug_class")
        out_path = group_dir / f"{safe_value}.tsv"
        write_tsv(
            out_path,
            fieldnames=[
                "subgroup_type",
                "analysis_id",
                "subgroup_value",
                "gene_id",
                "meta_p",
                "meta_fdr",
                "meta_effect_random",
                "n_cohorts_contributed",
                "n_patients_contributed",
                "i2",
                *effect_scale_fields,
            ],
            rows=rows_local,
        )
        return out_path

    if enable_subgroups:
        for subgroup_key, subgroup_type in [("cancer_type", "cancer_type"), ("drug_class", "drug_class")]:
            grouped: dict[str, set[str]] = defaultdict(set)
            for cohort_id, ctx in cohort_context.items():
                value = ctx.get(subgroup_key, "") or "unknown"
                grouped[value].add(cohort_id)
            for subgroup_value, cohort_ids in sorted(grouped.items()):
                out_path = _write_subgroup_meta(subgroup_type, subgroup_value, cohort_ids)
                if out_path:
                    subgroup_outputs.append(out_path)

    meta_regression_rows: list[dict[str, str]] = []
    for gene_id, entries in gene_map.items():
        if exclude_k1 and len(entries) < 2:
            continue
        effects = np.array([e[0] for e in entries], dtype=float)
        ses = np.array([e[1] for e in entries], dtype=float)
        cohorts_local = [e[3] for e in entries]
        groups = [_collapse_cancer_group(cohort_context.get(c, {}).get("cancer_type", "other")) for c in cohorts_local]
        # Reference level: melanoma
        design = np.column_stack(
            [
                np.ones(len(entries), dtype=float),
                np.array([1.0 if g == "NSCLC" else 0.0 for g in groups]),
                np.array([1.0 if g == "HNSCC" else 0.0 for g in groups]),
                np.array([1.0 if g == "other" else 0.0 for g in groups]),
            ]
        )
        weights = np.diag(1.0 / np.maximum(ses * ses, 1e-12))
        status = "ok"
        notes = ""
        beta_nsclc = ""
        beta_hnscc = ""
        beta_other = ""
        try:
            xtwx = design.T @ weights @ design
            xtwy = design.T @ weights @ effects
            beta = np.linalg.solve(xtwx, xtwy)
            beta_nsclc = f"{beta[1]:.6f}"
            beta_hnscc = f"{beta[2]:.6f}"
            beta_other = f"{beta[3]:.6f}"
        except Exception as exc:  # noqa: BLE001
            status = "insufficient_information"
            notes = str(exc.__class__.__name__)
        meta_regression_rows.append(
            {
                "analysis_id": output_label,
                "gene_id": gene_id,
                "beta_NSCLC": beta_nsclc,
                "beta_HNSCC": beta_hnscc,
                "beta_other": beta_other,
                "n_cohorts": str(len(entries)),
                "status": status,
                "notes": notes,
            }
        )

    write_tsv(
        meta_regression_file,
        fieldnames=["analysis_id", "gene_id", "beta_NSCLC", "beta_HNSCC", "beta_other", "n_cohorts", "status", "notes"],
        rows=meta_regression_rows,
    )
    write_tsv(
        meta_single_file,
        fieldnames=[
            "gene_id",
            "analysis_id",
            "original_gene_id",
            "gene_symbol",
            "n_cohorts_contributed",
            "n_patients_contributed",
            "meta_basis",
            "status",
            "notes",
            *effect_scale_fields,
        ],
        rows=single_cohort_rows,
    )

    for row in out_rows:
        row.pop("_entries", None)

    # Adjust fieldnames: use meta_effect_random as the canonical "meta_effect" for downstream
    write_tsv(
        out_file,
        fieldnames=fieldnames,
        rows=out_rows,
    )

    _mark_run(
        args,
        "meta run",
        [out_file, loo_detail_file, loo_summary_file, meta_regression_file, meta_single_file] + subgroup_outputs,
    )
    print(f"Wrote {out_file}")
    return 0


def cmd_visualize_run(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Visualization requires numpy/pandas/matplotlib.") from exc

    manifest_path = Path(args.sample_manifest)
    manifest_rows = read_tsv(manifest_path)
    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in manifest_rows:
        if row.get("include_flag", "").strip().lower() != "true":
            continue
        cohort_id = row.get("cohort_id", "")
        if cohort_id:
            by_cohort[cohort_id].append(row)

    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    de_root_raw = (getattr(args, "de_dir", "") or "").strip()
    meta_root_raw = (getattr(args, "meta_dir", "") or "").strip()
    immune_dir_raw = (getattr(args, "immune_dir", "") or "").strip()
    signature_file_raw = (getattr(args, "signature_file", "") or "").strip()
    validation_dir_raw = (getattr(args, "validation_dir", "") or "").strip()
    tcga_dir_raw = (getattr(args, "tcga_dir", "") or "").strip()
    de_root = Path(de_root_raw) if de_root_raw else None
    meta_root = Path(meta_root_raw) if meta_root_raw else None
    immune_dir = Path(immune_dir_raw) if immune_dir_raw else None

    index_rows: list[dict[str, str]] = []

    def _save_plot(fig, path: Path, stage: str, plot_type: str, cohort_id: str = "", contrast: str = "", notes: str = "") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        index_rows.append(
            {
                "stage": stage,
                "plot_type": plot_type,
                "cohort_id": cohort_id,
                "contrast": contrast,
                "plot_path": str(path),
                "notes": notes,
            }
        )

    # Stage 1-3: cohort-level QC/EDA visuals
    for cohort_id, cohort_rows in sorted(by_cohort.items()):
        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        if expr is None or expr.empty:
            continue

        expr, available = _resolve_sample_columns(expr, cohort_rows)
        if len(available) < 2:
            continue

        expr = expr.loc[:, available].fillna(0.0)
        expr_log = np.log2(expr + 1.0)
        # Replace Inf/-Inf from log2 with NaN, then fill with 0
        expr_log = expr_log.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # Library size profile
        lib_sizes = expr.sum(axis=0).sort_values(ascending=False)
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.bar(range(len(lib_sizes)), lib_sizes.values, color="#4C78A8")
        ax1.set_title(f"{cohort_id} - Library Size")
        ax1.set_xlabel("Samples (sorted)")
        ax1.set_ylabel("Total counts")
        _save_plot(
            fig1,
            out_root / "qc" / f"{cohort_id}_library_size.png",
            stage="QC",
            plot_type="library_size",
            cohort_id=cohort_id,
            notes=str(expr_path or ""),
        )

        # PCA
        mat = expr_log.T.values
        mat_centered = mat - mat.mean(axis=0, keepdims=True)
        u, s, _ = np.linalg.svd(mat_centered, full_matrices=False)
        pc = u[:, :2] * s[:2]
        explained = (s**2) / max(np.sum(s**2), 1e-9)
        response_map = {r.get("sample_id", ""): r.get("response_label", "unknown") for r in cohort_rows}
        color_map = {"responder": "#1F77B4", "non_responder": "#D62728", "unknown": "#7F7F7F"}
        point_colors = [color_map.get(response_map.get(sid, "unknown"), "#7F7F7F") for sid in available]
        fig2, ax2 = plt.subplots(figsize=(6, 5))
        ax2.scatter(pc[:, 0], pc[:, 1], c=point_colors, alpha=0.85, s=30, edgecolors="none")
        ax2.set_title(f"{cohort_id} - PCA")
        ax2.set_xlabel(f"PC1 ({explained[0] * 100:.1f}%)")
        ax2.set_ylabel(f"PC2 ({explained[1] * 100:.1f}%)")
        _save_plot(
            fig2,
            out_root / "qc" / f"{cohort_id}_pca.png",
            stage="QC",
            plot_type="pca",
            cohort_id=cohort_id,
            notes="colored_by_response_label",
        )

        # Sample-distance heatmap
        corr = np.corrcoef(mat)
        dist = 1.0 - np.nan_to_num(corr, nan=0.0)
        fig3, ax3 = plt.subplots(figsize=(6, 5))
        im = ax3.imshow(dist, aspect="auto", cmap="viridis")
        ax3.set_title(f"{cohort_id} - Sample Distance (1-corr)")
        ax3.set_xticks([])
        ax3.set_yticks([])
        fig3.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
        _save_plot(
            fig3,
            out_root / "qc" / f"{cohort_id}_sample_distance_heatmap.png",
            stage="QC",
            plot_type="sample_distance_heatmap",
            cohort_id=cohort_id,
        )

    # Stage 4: DE volcano per cohort/contrast
    if de_root and de_root.exists():
        for contrast_dir in sorted([p for p in de_root.iterdir() if p.is_dir()]):
            contrast = contrast_dir.name
            for de_file in sorted(contrast_dir.glob("*.tsv")):
                rows = read_tsv(de_file)
                xvals: list[float] = []
                yvals: list[float] = []
                sig_vals: list[bool] = []
                for row in rows:
                    try:
                        log2fc = float(row.get("log2fc", "nan"))
                        pval = float(row.get("p_value", "nan"))
                    except ValueError:
                        continue
                    if not np.isfinite(log2fc) or not np.isfinite(pval) or pval <= 0:
                        continue
                    xvals.append(log2fc)
                    yvals.append(-np.log10(max(pval, 1e-300)))
                    sig_vals.append(pval <= 0.05 and abs(log2fc) >= 1.0)
                if not xvals:
                    continue
                colors = ["#D62728" if s else "#B0B0B0" for s in sig_vals]
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.scatter(xvals, yvals, c=colors, s=8, alpha=0.7, edgecolors="none")
                ax.axvline(-1.0, color="#555555", linestyle="--", linewidth=0.8)
                ax.axvline(1.0, color="#555555", linestyle="--", linewidth=0.8)
                ax.axhline(-np.log10(0.05), color="#555555", linestyle="--", linewidth=0.8)
                cohort_id = de_file.stem
                ax.set_title(f"{cohort_id} - {contrast} Volcano")
                ax.set_xlabel("log2 fold-change")
                ax.set_ylabel("-log10(p)")
                _save_plot(
                    fig,
                    out_root / "de" / contrast / f"{cohort_id}_volcano.png",
                    stage="DE",
                    plot_type="volcano",
                    cohort_id=cohort_id,
                    contrast=contrast,
                )

    # Stage 4b: Meta volcano per contrast
    if meta_root and meta_root.exists():
        for contrast_dir in sorted([p for p in meta_root.iterdir() if p.is_dir()]):
            contrast = contrast_dir.name
            meta_file = contrast_dir / "meta_effects.tsv"
            if not meta_file.exists():
                continue
            rows = read_tsv(meta_file)
            xvals: list[float] = []
            yvals: list[float] = []
            for row in rows:
                try:
                    effect = float(row.get("meta_effect", "nan"))
                    pval = float(row.get("meta_p_value", "nan"))
                except ValueError:
                    continue
                if not np.isfinite(effect) or not np.isfinite(pval) or pval <= 0:
                    continue
                xvals.append(effect)
                yvals.append(-np.log10(max(pval, 1e-300)))
            if not xvals:
                continue
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.scatter(xvals, yvals, c="#4C78A8", s=8, alpha=0.7, edgecolors="none")
            ax.axvline(0.0, color="#555555", linestyle="--", linewidth=0.8)
            ax.axhline(-np.log10(0.05), color="#555555", linestyle="--", linewidth=0.8)
            ax.set_title(f"{contrast} - Meta Volcano")
            ax.set_xlabel("meta effect")
            ax.set_ylabel("-log10(meta p)")
            _save_plot(
                fig,
                out_root / "meta" / f"{contrast}_meta_volcano.png",
                stage="META",
                plot_type="meta_volcano",
                contrast=contrast,
            )

    # Stage 5: signature x expression heatmap
    signature_file: Path | None = Path(signature_file_raw) if signature_file_raw else None
    if signature_file is None and meta_root:
        cand = meta_root.parent / "signature" / "pre_response_signature_v1.tsv"
        if cand.exists():
            signature_file = cand
    if signature_file is None and de_root:
        cand = de_root.parent / "signature" / "pre_response_signature_v1.tsv"
        if cand.exists():
            signature_file = cand
    signature_genes: set[str] = set()
    if signature_file and signature_file.is_file():
        for row in read_tsv(signature_file):
            gene = (row.get("gene_id", "") or "").strip()
            if gene:
                signature_genes.add(gene)
    if signature_genes:
        for cohort_id, cohort_rows in sorted(by_cohort.items()):
            expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
            expr = load_expression_matrix(expr_path) if expr_path else None
            if expr is None or expr.empty:
                continue
            expr, available = _resolve_sample_columns(expr, cohort_rows, include_filter=True)
            if len(available) < 2:
                continue
            expr = expr.loc[:, available].fillna(0.0)
            expr_log = np.log2(expr + 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            keep_genes = [g for g in signature_genes if g in expr_log.index]
            if len(keep_genes) < 2:
                continue
            sig_mat = expr_log.loc[keep_genes, :]
            if sig_mat.empty:
                continue
            top_n = 60
            if sig_mat.shape[0] > top_n:
                sig_mat = sig_mat.loc[sig_mat.var(axis=1).sort_values(ascending=False).head(top_n).index]
            z = (sig_mat - sig_mat.mean(axis=1).values[:, None]) / (
                sig_mat.std(axis=1).replace(0, 1).values[:, None]
            )
            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(z.values, aspect="auto", cmap="coolwarm", vmin=-2.5, vmax=2.5)
            ax.set_title(f"{cohort_id} - Signature Heatmap")
            ax.set_xlabel("Samples")
            ax.set_ylabel("Signature genes")
            ax.set_xticks([])
            ax.set_yticks(range(len(z.index)))
            ax.set_yticklabels([str(v)[:30] for v in z.index], fontsize=7)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            _save_plot(
                fig,
                out_root / "signature" / f"{cohort_id}_signature_heatmap.png",
                stage="SIGNATURE",
                plot_type="signature_heatmap",
                cohort_id=cohort_id,
                notes=str(signature_file),
            )

    # Stage 6: immune ssGSEA heatmap
    ssgsea_file = immune_dir / "ssgsea_scores.tsv" if immune_dir else None
    if immune_dir and ssgsea_file and ssgsea_file.exists():
        ssgsea_df = pd.read_csv(ssgsea_file, sep="\t")
        required = {"cohort_id", "sample_id", "gene_set_name", "ssgsea_score"}
        if not required.issubset(set(ssgsea_df.columns)):
            id_cols = [c for c in ["cohort_id", "sample_id", "patient_uid"] if c in ssgsea_df.columns]
            value_cols = [c for c in ssgsea_df.columns if c not in set(id_cols)]
            if id_cols and value_cols:
                ssgsea_df = ssgsea_df.melt(
                    id_vars=id_cols,
                    value_vars=value_cols,
                    var_name="gene_set_name",
                    value_name="ssgsea_score",
                )
        if required.issubset(set(ssgsea_df.columns)):
            for cohort_id, cohort_df in ssgsea_df.groupby("cohort_id"):
                if cohort_df.empty:
                    continue
                pivot = cohort_df.pivot_table(
                    index="gene_set_name",
                    columns="sample_id",
                    values="ssgsea_score",
                    aggfunc="mean",
                ).dropna(axis=0, how="all")
                if pivot.empty or pivot.shape[1] < 2:
                    continue
                top_n = int(getattr(args, "ssgsea_heatmap_top_sets", 25))
                top_idx = pivot.var(axis=1).sort_values(ascending=False).head(top_n).index
                pivot = pivot.loc[top_idx]
                z = (pivot - pivot.mean(axis=1).values[:, None]) / (pivot.std(axis=1).replace(0, 1).values[:, None])
                fig, ax = plt.subplots(figsize=(8, 6))
                im = ax.imshow(z.values, aspect="auto", cmap="coolwarm", vmin=-2.5, vmax=2.5)
                ax.set_title(f"{cohort_id} - ssGSEA Heatmap (top variance sets)")
                ax.set_xlabel("Samples")
                ax.set_ylabel("Gene sets")
                ax.set_xticks([])
                yticks = range(len(z.index))
                ax.set_yticks(yticks)
                ax.set_yticklabels([str(v)[:40] for v in z.index], fontsize=7)
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                _save_plot(
                    fig,
                    out_root / "immune" / f"{cohort_id}_ssgsea_heatmap.png",
                    stage="IMMUNE",
                    plot_type="ssgsea_heatmap",
                    cohort_id=cohort_id,
                )

    # Stage 6b: ssGSEA layer R-vs-NR distribution (pooled across cohorts)
    ssgsea_long = immune_dir / "ssgsea_scores_long.tsv" if immune_dir else None
    if immune_dir and ssgsea_long and ssgsea_long.exists():
        long_rows = read_tsv(ssgsea_long)
        response_lookup = {
            (r.get("cohort_id", ""), r.get("sample_id", "")): r.get("response_label", "")
            for r in manifest_rows
            if (r.get("response_label", "") or "").strip().lower() in {"responder", "non_responder"}
        }
        by_layer: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for row in long_rows:
            layer = (row.get("gene_set_layer", "") or "").strip()
            cohort_id = row.get("cohort_id", "")
            sample_id = row.get("sample_id", "")
            response = (response_lookup.get((cohort_id, sample_id), "") or "").strip().lower()
            if response not in {"responder", "non_responder"}:
                continue
            try:
                score = float(row.get("ssgsea_score", "nan"))
            except ValueError:
                continue
            if not np.isfinite(score):
                continue
            by_layer[layer][response].append(score)
        for layer, group_values in sorted(by_layer.items()):
            r_vals = group_values.get("responder", [])
            nr_vals = group_values.get("non_responder", [])
            if len(r_vals) < 2 or len(nr_vals) < 2:
                continue
            fig, ax = plt.subplots(figsize=(6, 4))
            data = [nr_vals, r_vals]
            labels = ["NR", "R"]
            bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.5)
            colors = ["#D62728", "#1F77B4"]
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.35)
            for x, vals, color in zip([1, 2], data, colors):
                jitter = np.random.default_rng(0).normal(loc=0.0, scale=0.04, size=len(vals))
                ax.scatter(np.full(len(vals), x) + jitter, vals, s=8, alpha=0.5, c=color, edgecolors="none")
            ax.set_title(f"{layer} - ssGSEA R vs NR")
            ax.set_ylabel("ssGSEA score")
            _save_plot(
                fig,
                out_root / "immune" / f"{layer.lower()}_r_vs_nr_box.png",
                stage="IMMUNE",
                plot_type="ssgsea_layer_box",
                notes=str(ssgsea_long),
            )

    # Stage 10: validation framing plots (concordance tiers)
    validation_dir: Path | None = Path(validation_dir_raw) if validation_dir_raw else None
    if validation_dir is None and de_root:
        cand = de_root.parent / "validation"
        if cand.exists():
            validation_dir = cand
    concordance_file = validation_dir / "validation_concordance.tsv" if validation_dir else None
    if validation_dir and concordance_file and concordance_file.is_file():
        rows = read_tsv(concordance_file)
        tier_counts = {"GOLD": 0, "SILVER": 0, "BRONZE": 0}
        for row in rows:
            tier = (row.get("concordance_tier", "") or "").strip().upper()
            if tier in tier_counts:
                tier_counts[tier] += 1
        if sum(tier_counts.values()) > 0:
            fig, ax = plt.subplots(figsize=(6, 4))
            tiers = ["GOLD", "SILVER", "BRONZE"]
            counts = [tier_counts[t] for t in tiers]
            ax.bar(tiers, counts, color=["#DAA520", "#A9A9A9", "#CD7F32"])
            ax.set_title("Concordance Tier Counts (Internal Robustness)")
            ax.set_ylabel("Genes")
            _save_plot(
                fig,
                out_root / "validation" / "concordance_tier_bar.png",
                stage="VALIDATION",
                plot_type="concordance_tier_bar",
                notes=str(concordance_file),
            )

    # Stage 12: TCGA continuous-Cox summary and optional Thorsson association panel
    tcga_dir: Path | None = Path(tcga_dir_raw) if tcga_dir_raw else None
    if tcga_dir is None and de_root:
        cand = de_root.parent / "tcga_projection"
        if cand.exists():
            tcga_dir = cand
    if tcga_dir and tcga_dir.exists():
        stat_files = sorted(tcga_dir.glob("*_survival_stats.tsv"))
        stat_rows: list[dict[str, str]] = []
        for sf in stat_files:
            stat_rows.extend(read_tsv(sf))
        valid_stats = []
        for row in stat_rows:
            try:
                hr = float(row.get("hazard_ratio", "nan"))
                lo = float(row.get("lower_95_ci", "nan"))
                hi = float(row.get("upper_95_ci", "nan"))
            except ValueError:
                continue
            if not (np.isfinite(hr) and np.isfinite(lo) and np.isfinite(hi)):
                continue
            valid_stats.append((row.get("project", "TCGA"), hr, lo, hi))
        if valid_stats:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            y = np.arange(len(valid_stats))
            hrs = np.array([v[1] for v in valid_stats], dtype=float)
            lows = np.array([v[2] for v in valid_stats], dtype=float)
            highs = np.array([v[3] for v in valid_stats], dtype=float)
            labels = [v[0] for v in valid_stats]
            ax.errorbar(hrs, y, xerr=[hrs - lows, highs - hrs], fmt="o", color="#1F77B4", ecolor="#666666", capsize=3)
            ax.axvline(1.0, color="#555555", linestyle="--", linewidth=0.8)
            ax.set_yticks(y)
            ax.set_yticklabels(labels, fontsize=8)
            ax.set_xlabel("Hazard Ratio (continuous Cox)")
            ax.set_title("TCGA Prognostic Cox Summary")
            _save_plot(
                fig,
                out_root / "tcga" / "continuous_cox_hazard_ratios.png",
                stage="TCGA",
                plot_type="tcga_continuous_cox",
                notes=str(tcga_dir),
            )

        thorsson_validation = tcga_dir / "thorsson_layer4" / "epigenetic_layer_tcga_validation.tsv"
        if thorsson_validation.exists():
            rows = read_tsv(thorsson_validation)
            ok_rows = [r for r in rows if (r.get("status", "") or "").strip() == "ok"]
            points = []
            for row in ok_rows:
                try:
                    fdr = float(row.get("fdr", "nan"))
                    pval = float(row.get("p_value", "nan"))
                except ValueError:
                    continue
                if np.isfinite(fdr) and np.isfinite(pval) and pval > 0:
                    points.append((row.get("gene_set", ""), row.get("tcga_project", ""), -np.log10(max(pval, 1e-300)), fdr))
            if points:
                fig, ax = plt.subplots(figsize=(8, 4.5))
                x = np.arange(len(points))
                y = np.array([p[2] for p in points], dtype=float)
                colors = ["#1F77B4" if p[3] <= 0.1 else "#B0B0B0" for p in points]
                ax.bar(x, y, color=colors)
                ax.set_xticks(x)
                ax.set_xticklabels([f"{p[1]}:{p[0]}"[:28] for p in points], rotation=90, fontsize=7)
                ax.set_ylabel("-log10(p)")
                ax.set_title("TCGA Thorsson Layer-4 Association")
                _save_plot(
                    fig,
                    out_root / "tcga" / "thorsson_layer4_association.png",
                    stage="TCGA",
                    plot_type="tcga_thorsson_association",
                    notes=str(thorsson_validation),
                )

    index_tsv = out_root / "visualization_index.tsv"
    write_tsv(
        index_tsv,
        fieldnames=["stage", "plot_type", "cohort_id", "contrast", "plot_path", "notes"],
        rows=index_rows,
    )
    index_md = out_root / "visualization_index.md"
    lines = [
        "# Visualization Index",
        "",
        f"- sample_manifest: {manifest_path}",
        f"- n_plots: {len(index_rows)}",
        "",
        "| stage | plot_type | cohort_id | contrast | plot_path |",
        "|---|---|---|---|---|",
    ]
    for row in index_rows:
        lines.append(
            f"| {row.get('stage', '')} | {row.get('plot_type', '')} | {row.get('cohort_id', '')} | "
            f"{row.get('contrast', '')} | {row.get('plot_path', '')} |"
        )
    index_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _mark_run(args, "visualize run", [index_tsv, index_md])
    print(f"Wrote visualization outputs under {out_root}")
    return 0


def cmd_viz_build(args: argparse.Namespace) -> int:
    from .modules._viz.registry import load_figure_registry, resolve_figure_contract

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    registry_rows = load_figure_registry(Path(args.figure_registry))

    visualize_args = argparse.Namespace(
        sample_manifest=args.sample_manifest,
        expression_manifest=args.expression_manifest,
        downloads_root=args.downloads_root,
        de_dir=args.de_dir,
        meta_dir=args.meta_dir,
        immune_dir=args.immune_dir,
        signature_file=getattr(args, "signature_file", ""),
        validation_dir=getattr(args, "validation_dir", ""),
        tcga_dir=getattr(args, "tcga_dir", ""),
        ssgsea_heatmap_top_sets=args.ssgsea_heatmap_top_sets,
        out=str(out_root),
        run_manifest=args.run_manifest,
    )
    cmd_visualize_run(visualize_args)

    figure_rows: list[dict[str, str]] = []
    for fig_path in sorted(out_root.rglob("*.png")):
        rel = str(fig_path.relative_to(out_root))
        framing, scientific_note = resolve_figure_contract(rel, registry_rows)
        rel_low = rel.lower()
        note_low = scientific_note.lower()
        if "tcga" in rel_low:
            if "prognostic" not in note_low:
                raise RuntimeError(
                    "Figure scientific-note lint failed: TCGA figures must be labeled prognostic."
                )
            if "validation" in note_low:
                raise RuntimeError(
                    "Figure scientific-note lint failed: TCGA figures must not be labeled as validation."
                )
        if "concordance" in rel_low and "validation" in note_low:
            raise RuntimeError(
                "Figure scientific-note lint failed: concordance figures must not be labeled as validation."
            )
        figure_id = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]
        caption_sidecar = out_root / f"{figure_id}.caption.txt"
        caption_sidecar.write_text(scientific_note + "\n", encoding="utf-8")
        figure_rows.append(
            {
                "figure_id": figure_id,
                "plot_path": str(fig_path),
                "relative_path": rel,
                "framing": framing,
                "scientific_note": scientific_note,
                "caption_sidecar": str(caption_sidecar),
            }
        )

    manifest_file = out_root / "figure_manifest.tsv"
    write_tsv(
        manifest_file,
        fieldnames=[
            "figure_id",
            "plot_path",
            "relative_path",
            "framing",
            "scientific_note",
            "caption_sidecar",
        ],
        rows=figure_rows,
    )
    repro_dir = out_root / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)
    commands_file = repro_dir / "commands.sh"
    commands_file.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "python -m pipeline.cli viz build \\",
                f"  --sample-manifest {args.sample_manifest} \\",
                f"  --expression-manifest {args.expression_manifest} \\",
                f"  --downloads-root {args.downloads_root} \\",
                f"  --de-dir {args.de_dir} \\",
                f"  --meta-dir {args.meta_dir} \\",
                f"  --immune-dir {args.immune_dir} \\",
                f"  --figure-registry {args.figure_registry} \\",
                f"  --out {out_root}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    env_file = repro_dir / "environment.yml"
    env_file.write_text(
        "\n".join(
            [
                "name: rnaseq-viz-build",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                f"  - python={sys.version_info.major}.{sys.version_info.minor}",
                "  - pandas",
                "  - matplotlib",
                "  - numpy",
                "",
            ]
        ),
        encoding="utf-8",
    )
    checksums_file = repro_dir / "checksums.sha256"
    checksum_targets = [manifest_file, *sorted(out_root.glob("*.caption.txt"))]
    checksum_lines: list[str] = []
    for target in checksum_targets:
        if not target.exists():
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {target}")
    checksums_file.write_text(
        "\n".join(checksum_lines) + ("\n" if checksum_lines else ""),
        encoding="utf-8",
    )
    _mark_run(
        args,
        "viz build",
        [manifest_file, commands_file, env_file, checksums_file],
    )
    print(f"Wrote {manifest_file}")
    return 0


def cmd_router_run(args: argparse.Namespace) -> int:
    sample_manifest_path = Path(args.sample_manifest)
    rows = read_tsv(sample_manifest_path)
    if not rows:
        raise RuntimeError(f"Sample manifest is empty: {sample_manifest_path}")

    fieldnames = list(rows[0].keys())
    out_root = Path(args.out)
    track_manifest_dir = out_root / "track_manifests"
    summary_path = out_root / "route_execution_summary.tsv"
    readiness_path = out_root / "cohort_readiness_status.tsv"
    track_manifest_dir.mkdir(parents=True, exist_ok=True)

    selected = str(getattr(args, "track", "ALL")).upper()
    requested_contrasts_raw = (getattr(args, "contrasts", "") or "").strip()
    requested_contrasts = [
        tok.strip().upper()
        for tok in re.split(r"[,|]", requested_contrasts_raw)
        if tok.strip()
    ]
    invalid_contrasts = sorted(set(requested_contrasts) - SUPPORTED_CONTRASTS)
    if invalid_contrasts:
        raise RuntimeError(f"Unsupported contrast(s): {', '.join(invalid_contrasts)}")
    include_excluded = bool(getattr(args, "include_excluded", False))
    allow_stub_rows = bool(getattr(args, "allow_stub_rows", False))
    dry_run = bool(getattr(args, "dry_run", False))
    analysis_registry_path = (getattr(args, "analysis_registry", "") or "").strip()
    analysis_membership_path = (getattr(args, "analysis_membership", "") or "").strip()
    analysis_registry_rows = read_tsv(Path(analysis_registry_path)) if analysis_registry_path else []
    feasible_analysis_rows = [
        r for r in analysis_registry_rows if r.get("feasibility_status", "") == "feasible"
    ]
    if analysis_registry_path and not dry_run:
        raise RuntimeError(
            "Spec 026 analysis-registry routing is dry-run only during the design-layer migration."
        )
    selected_tracks = (
        ["DESIGN"]
        if analysis_registry_path
        else ["MULTI"]
        if requested_contrasts
        else (["A", "B", "C"] if selected == "ALL" else [selected])
    )

    def track_label(row: dict[str, str]) -> str:
        value = (row.get("comparison_tracks_final") or row.get("comparison_tracks") or "").strip()
        if value == "PRE_RESPONSE":
            return "A"
        if value == "TREATMENT_DELTA":
            return "B"
        if value == "PRE_RESPONSE|TREATMENT_DELTA":
            return "C"
        return ""

    def row_allowed(row: dict[str, str]) -> bool:
        if not requested_contrasts and not include_excluded and row.get("include_flag", "").strip().lower() != "true":
            return False
        if not allow_stub_rows and row.get("sync_status", "").strip() == "added_cohort_stub_no_sample_rows":
            return False
        return True

    def _cohort_has_expression(cohort_id: str) -> bool:
        expr_path = resolve_primary_expression_path(cohort_id, Path(expression_manifest), Path(downloads_root))
        if expr_path is None or not expr_path.exists():
            return False
        expr = load_expression_matrix(expr_path)
        return bool(expr is not None and not expr.empty)

    summary_rows: list[dict[str, str]] = []
    readiness_rows: list[dict[str, str]] = []
    outputs: list[Path] = []
    run_manifest = str(getattr(args, "run_manifest", "logs/run_manifest.yaml"))
    expression_manifest = str(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    downloads_root = str(getattr(args, "downloads_root", "results/retrieval/downloads"))
    count_method = str(getattr(args, "count_method", "deseq2"))
    gene_id_mapping = str(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    min_hgnc_mapping_rate = float(getattr(args, "min_hgnc_mapping_rate", 0.60))
    max_unmapped_ensembl_fraction = float(getattr(args, "max_unmapped_ensembl_fraction", 0.20))
    max_duplicate_collapse_fraction = float(getattr(args, "max_duplicate_collapse_fraction", 0.25))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))
    allow_welch_fallback = bool(getattr(args, "allow_welch_fallback", False))

    feasible_analysis_ids = {
        r.get("analysis_id", "") for r in feasible_analysis_rows if r.get("analysis_id", "")
    }
    design_member_keys: set[tuple[str, str]] = set()
    if analysis_membership_path:
        design_member_keys = {
            (r.get("cohort_id", ""), r.get("sample_id", ""))
            for r in read_tsv(Path(analysis_membership_path))
            if r.get("analysis_id", "") in feasible_analysis_ids
        }

    for track in selected_tracks:
        track_rows_all = rows if track in {"MULTI", "DESIGN"} else [r for r in rows if track_label(r) == track]
        if track == "DESIGN" and design_member_keys:
            track_rows_all = [
                r
                for r in track_rows_all
                if (r.get("cohort_id", ""), r.get("sample_id", "")) in design_member_keys
            ]
        track_rows = list(track_rows_all) if track == "DESIGN" else [r for r in track_rows_all if row_allowed(r)]
        track_cohorts_all = sorted({r.get("cohort_id", "") for r in track_rows_all if r.get("cohort_id", "")})
        track_cohorts = sorted({r.get("cohort_id", "") for r in track_rows if r.get("cohort_id", "")})
        track_key = {
            "A": "pre_response_only",
            "B": "treatment_delta_only",
            "C": "dual_track",
            "MULTI": "multi_contrast",
            "DESIGN": "analysis_design",
        }[track]
        manifest_out = track_manifest_dir / f"{track_key}.tsv"
        write_tsv(manifest_out, fieldnames=fieldnames, rows=track_rows)
        outputs.append(manifest_out)

        executed = "false"
        notes = ""
        de_contrasts: list[str] = []

        contrasts = (
            sorted(
                {
                    r.get("legacy_contrast_alias", "")
                    for r in feasible_analysis_rows
                    if r.get("legacy_contrast_alias", "")
                }
            )
            if track == "DESIGN"
            else requested_contrasts
            if track == "MULTI"
            else ["PRE_RESPONSE"]
            if track == "A"
            else ["TREATMENT_DELTA"]
            if track == "B"
            else ["PRE_RESPONSE", "TREATMENT_DELTA"]
        )

        if not track_rows:
            notes = "no_rows_after_filters"
        elif dry_run:
            notes = "dry_run_only"
        else:
            executed = "true"
            gene_audit_out = out_root / "gene_id_audit" / track_key
            ingest_out = out_root / "ingest" / track_key
            qc_out = out_root / "cohort_qc" / track_key
            de_out = out_root / "within_cohort_de" / track_key
            meta_out = out_root / "meta_analysis" / track_key

            gene_audit_args = argparse.Namespace(
                sample_manifest=str(manifest_out),
                expression_manifest=expression_manifest,
                downloads_root=downloads_root,
                out=str(gene_audit_out),
                include_excluded=include_excluded,
                allow_stub_rows=allow_stub_rows,
                gene_id_mapping=gene_id_mapping,
                min_hgnc_mapping_rate=min_hgnc_mapping_rate,
                max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
                max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
                strict=not allow_weak_gene_mapping,
                run_manifest=run_manifest,
            )
            cmd_intake_gene_audit(gene_audit_args)
            outputs.extend(
                [
                    gene_audit_out / "gene_id_audit_by_cohort.tsv",
                    gene_audit_out / "gene_id_audit_failed.tsv",
                    gene_audit_out / "gene_id_audit_summary.md",
                ]
            )

            ingest_args = argparse.Namespace(
                sample_manifest=str(manifest_out),
                out=str(ingest_out),
                run_manifest=run_manifest,
            )
            cmd_ingest_run(ingest_args)
            outputs.append(ingest_out / "ingest_index.tsv")

            qc_args = argparse.Namespace(
                sample_manifest=str(manifest_out),
                ingest_dir=str(ingest_out),
                expression_manifest=expression_manifest,
                downloads_root=downloads_root,
                out=str(qc_out),
                run_manifest=run_manifest,
            )
            cmd_qc_run(qc_args)
            outputs.append(qc_out)

            for contrast in contrasts:
                de_contrasts.append(contrast)
                de_args = argparse.Namespace(
                    contrast=contrast,
                    sample_manifest=str(manifest_out),
                    ingest_dir=str(ingest_out),
                    expression_manifest=expression_manifest,
                    downloads_root=downloads_root,
                    count_method=count_method,
                    gene_id_mapping=gene_id_mapping,
                    min_hgnc_mapping_rate=min_hgnc_mapping_rate,
                    max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
                    max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
                    allow_weak_gene_mapping=allow_weak_gene_mapping,
                    allow_welch_fallback=allow_welch_fallback,
                    comparison_registry=str(out_root / "comparison_registry.tsv"),
                    out=str(de_out),
                    run_manifest=run_manifest,
                )
                cmd_de_run(de_args)
                meta_args = argparse.Namespace(
                    contrast=contrast,
                    de_dir=str(de_out),
                    sample_manifest=str(manifest_out),
                    comparison_registry=str(out_root / "comparison_registry.tsv"),
                    skip_forest_plots=False,
                    out=str(meta_out),
                    run_manifest=run_manifest,
                )
                cmd_meta_run(meta_args)
            outputs.extend([de_out, meta_out])

            viz_out = out_root / "visualizations" / track_key
            viz_args = argparse.Namespace(
                sample_manifest=str(manifest_out),
                expression_manifest=expression_manifest,
                downloads_root=downloads_root,
                de_dir=str(de_out),
                meta_dir=str(meta_out),
                immune_dir="",
                ssgsea_heatmap_top_sets=25,
                out=str(viz_out),
                run_manifest=run_manifest,
            )
            cmd_visualize_run(viz_args)
            outputs.extend([viz_out / "visualization_index.tsv", viz_out / "visualization_index.md"])

        # Cohort readiness classification for truthful execution reporting.
        analyzed_count = 0
        blocked_count = 0
        stub_excluded_count = 0
        routed_not_executed_count = 0
        for cohort_id in track_cohorts_all:
            cohort_rows_all = [r for r in track_rows_all if r.get("cohort_id", "") == cohort_id]
            cohort_rows_selected = [r for r in track_rows if r.get("cohort_id", "") == cohort_id]
            is_sync_stub = any(
                (r.get("sync_status", "") or "").strip() == "added_cohort_stub_no_sample_rows"
                for r in cohort_rows_all
            )
            has_expression = _cohort_has_expression(cohort_id)
            contrast_eligible = any(is_contrast_eligible(cohort_rows_selected, c) for c in contrasts) if cohort_rows_selected else False

            readiness_status = "routed_not_executed"
            execution_status = "not_executed"
            blocking_reason = "row_filters_excluded"

            if not cohort_rows_selected:
                if is_sync_stub and not allow_stub_rows:
                    readiness_status = "stub_excluded"
                    blocking_reason = "sync_stub_filtered"
                else:
                    readiness_status = "routed_not_executed"
                    blocking_reason = "row_filters_excluded"
            elif dry_run:
                readiness_status = "routed_not_executed"
                execution_status = "dry_run"
                blocking_reason = "dry_run_only"
            else:
                cohort_analyzed = False
                for contrast in contrasts:
                    de_path = out_root / "within_cohort_de" / track_key / contrast / f"{cohort_id}.tsv"
                    if de_path.exists() and read_tsv(de_path):
                        cohort_analyzed = True
                        break
                if cohort_analyzed:
                    readiness_status = "analyzed"
                    execution_status = "executed"
                    blocking_reason = ""
                else:
                    readiness_status = "blocked"
                    execution_status = "executed"
                    if not has_expression:
                        blocking_reason = "missing_expression"
                    elif not contrast_eligible:
                        blocking_reason = "insufficient_contrast_eligibility"
                    else:
                        blocking_reason = "no_de_rows_emitted"

            if readiness_status == "analyzed":
                analyzed_count += 1
            elif readiness_status == "blocked":
                blocked_count += 1
            elif readiness_status == "stub_excluded":
                stub_excluded_count += 1
            else:
                routed_not_executed_count += 1

            readiness_rows.append(
                {
                    "track": track,
                    "track_name": track_key,
                    "cohort_id": cohort_id,
                    "readiness_status": readiness_status,
                    "execution_status": execution_status,
                    "blocking_reason": blocking_reason,
                    "is_sync_stub": "true" if is_sync_stub else "false",
                    "has_expression": "true" if has_expression else "false",
                    "contrast_eligible": "true" if contrast_eligible else "false",
                }
            )

        if dry_run and track_rows:
            de_contrasts = contrasts

        summary_rows.append(
            {
                "track": track,
                "track_name": track_key,
                "n_rows": str(len(track_rows)),
                "n_cohorts": str(len(track_cohorts)),
                "n_routed_cohorts": str(len(track_cohorts_all)),
                "n_analyzed_cohorts": str(analyzed_count),
                "n_blocked_cohorts": str(blocked_count),
                "n_stub_excluded_cohorts": str(stub_excluded_count),
                "n_routed_not_executed_cohorts": str(routed_not_executed_count),
                "executed": executed,
                "de_contrasts": "|".join(de_contrasts),
                "analysis_ids": "|".join(
                    r.get("analysis_id", "")
                    for r in feasible_analysis_rows
                    if track == "DESIGN" and r.get("analysis_id", "")
                ),
                "manifest_path": str(manifest_out),
                "notes": notes,
            }
        )

    write_tsv(
        readiness_path,
        fieldnames=[
            "track",
            "track_name",
            "cohort_id",
            "readiness_status",
            "execution_status",
            "blocking_reason",
            "is_sync_stub",
            "has_expression",
            "contrast_eligible",
        ],
        rows=readiness_rows,
    )
    outputs.append(readiness_path)

    write_tsv(
        summary_path,
        fieldnames=[
            "track",
            "track_name",
            "n_rows",
            "n_cohorts",
            "n_routed_cohorts",
            "n_analyzed_cohorts",
            "n_blocked_cohorts",
            "n_stub_excluded_cohorts",
            "n_routed_not_executed_cohorts",
            "executed",
            "de_contrasts",
            "analysis_ids",
            "manifest_path",
            "notes",
        ],
        rows=summary_rows,
    )
    outputs.append(summary_path)
    _mark_run(args, "router run", outputs)
    print(f"Wrote {summary_path}")
    return 0


def cmd_mega_run(args: argparse.Namespace) -> int:
    """Head-to-Head Mega-Analysis: merge all cohorts, batch-correct, run unified DE."""
    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Mega-analysis requires numpy/pandas.") from exc
    import shutil
    import subprocess
    import tempfile

    manifest = read_tsv(Path(args.sample_manifest))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    contrast = getattr(args, "contrast", "PRE_RESPONSE")
    meta_dir = Path(getattr(args, "meta_dir", "")) if getattr(args, "meta_dir", "") else None
    gene_id_mapping = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    min_hgnc_mapping_rate = float(getattr(args, "min_hgnc_mapping_rate", 0.60))
    max_unmapped_ensembl_fraction = float(getattr(args, "max_unmapped_ensembl_fraction", 0.20))
    max_duplicate_collapse_fraction = float(getattr(args, "max_duplicate_collapse_fraction", 0.25))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))

    rscript = shutil.which("Rscript")
    if not rscript:
        raise RuntimeError("Rscript not found; required for ComBat-Seq and mega-DESeq2.")

    # Identify eligible cohorts
    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in manifest:
        if parse_bool(row.get("include_flag", "true"), default=True):
            by_cohort[row.get("cohort_id", "")].append(row)

    # Load & intersect gene space
    cohort_expr: dict[str, pd.DataFrame] = {}
    cohort_meta_rows: list[dict[str, str]] = []
    gene_sets: list[set] = []
    excluded_rows: list[dict[str, str]] = []

    for cohort_id, cohort_rows in by_cohort.items():
        exclusion_reason = _cohort_contract_exclusion_reason(cohort_id, cohort_rows)
        if exclusion_reason:
            excluded_rows.append({"cohort_id": cohort_id, "reason": exclusion_reason})
            continue
        cohort_assay = _cohort_assay_type(cohort_rows)
        if cohort_assay != "raw_counts":
            excluded_rows.append({"cohort_id": cohort_id, "reason": f"mega_requires_raw_counts_assay:{cohort_assay}"})
            continue
        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        if expr is None or expr.empty:
            excluded_rows.append({"cohort_id": cohort_id, "reason": "missing_expression"})
            continue

        agg_method = "sum"
        expr, _, metrics = _standardize_expression_gene_ids(
            expr,
            mapping_path=gene_id_mapping,
            aggregation=agg_method,
        )
        status, fail_reason = _evaluate_gene_id_quality(
            metrics,
            min_hgnc_mapping_rate=min_hgnc_mapping_rate,
            max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
            max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
        )
        if status != "pass" and not allow_weak_gene_mapping:
            raise RuntimeError(
                "Gene ID quality gate failed during mega run for cohort "
                f"{cohort_id}: {fail_reason}. Provide a mapping file via --gene-id-mapping "
                "or rerun with --allow-weak-gene-mapping."
            )
        if not _looks_like_count_matrix(expr):
            excluded_rows.append({"cohort_id": cohort_id, "reason": "assay_declared_raw_counts_but_not_count_like"})
            continue

        expr, available = _resolve_sample_columns(expr, cohort_rows)
        if not available:
            excluded_rows.append({"cohort_id": cohort_id, "reason": "no_matching_samples"})
            continue

        expr = expr.loc[:, available].fillna(0)
        cohort_expr[cohort_id] = expr
        gene_sets.append(set(expr.index))

        for r in cohort_rows:
            if r.get("sample_id", "") in available:
                cohort_meta_rows.append({
                    "sample_id": r.get("sample_id", ""),
                    "cohort_id": cohort_id,
                    "response_label": r.get("response_label", "unknown"),
                })

    excluded_file = out_root / "mega_excluded_cohorts.tsv"
    write_tsv(excluded_file, fieldnames=["cohort_id", "reason"], rows=excluded_rows)

    if len(cohort_expr) < 2:
        skip_file = out_root / "mega_analysis_skipped.tsv"
        write_tsv(
            skip_file,
            fieldnames=[
                "reason",
                "contrast",
                "n_cohorts_found",
                "cohorts_found",
                "note",
            ],
            rows=[
                {
                    "reason": "insufficient_cohorts",
                    "contrast": contrast,
                    "n_cohorts_found": str(len(cohort_expr)),
                    "cohorts_found": "|".join(sorted(cohort_expr.keys())),
                    "note": "Mega-analysis requires at least 2 cohorts with resolvable expression data.",
                }
            ],
        )
        _mark_run(args, "mega run", [skip_file, excluded_file])
        print(f"Mega-analysis skipped due to insufficient cohorts. Wrote {skip_file}")
        return 0

    # Intersect genes across ALL cohorts
    common_genes = sorted(set.intersection(*gene_sets))
    if len(common_genes) < 100:
        raise RuntimeError(f"Only {len(common_genes)} genes shared across all cohorts. Need ≥100 for reliable analysis.")

    # Concatenate into mega-matrix
    mega_frames = [cohort_expr[cid].loc[common_genes] for cid in sorted(cohort_expr.keys())]
    mega_matrix = pd.concat(mega_frames, axis=1)
    mega_metadata = pd.DataFrame(cohort_meta_rows)

    # Determine case/control labels
    if contrast == "PRE_RESPONSE":
        case_label = "responder"
        control_label = "non_responder"
    else:
        case_label = "responder"
        control_label = "non_responder"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        counts_tsv = tmpdir_path / "mega_counts.tsv"
        meta_tsv = tmpdir_path / "mega_metadata.tsv"
        corrected_tsv = tmpdir_path / "combat_corrected.tsv"
        mega_de_tsv = out_root / "mega_de_results.tsv"

        mega_matrix.to_csv(counts_tsv, sep="\t")
        mega_metadata.to_csv(meta_tsv, sep="\t", index=False)

        # Step 1: ComBat-Seq
        subprocess.run(
            [rscript, "scripts/combat_merge.R",
             "--counts", str(counts_tsv),
             "--metadata", str(meta_tsv),
             "--out", str(corrected_tsv)],
            check=True,
        )

        # Step 2: Mega-DESeq2
        subprocess.run(
            [rscript, "scripts/mega_deseq2.R",
             "--counts", str(corrected_tsv),
             "--metadata", str(meta_tsv),
             "--case", case_label,
             "--control", control_label,
             "--out", str(mega_de_tsv)],
            check=True,
        )

    outputs = [mega_de_tsv]
    outputs.append(excluded_file)

    # Step 3: Concordance scoring (if indirect meta results are available)
    if meta_dir and (meta_dir / contrast / "meta_effects.tsv").exists():
        indirect_rows = read_tsv(meta_dir / contrast / "meta_effects.tsv")
        indirect_map = {}
        for r in indirect_rows:
            gene_id = r.get("gene_id", "")
            try:
                fdr = float(r.get("meta_fdr", "1.0"))
                effect = float(r.get("meta_effect_random", r.get("meta_effect", "0.0")))
            except ValueError:
                continue
            indirect_map[gene_id] = (effect, fdr)

        mega_rows = read_tsv(mega_de_tsv)
        concordance_rows = []
        for r in mega_rows:
            gene_id = r.get("gene_id", "")
            try:
                mega_fdr = float(r.get("fdr", "1.0"))
                mega_effect = float(r.get("log2fc", "0.0"))
            except ValueError:
                continue

            ind_effect, ind_fdr = indirect_map.get(gene_id, (0.0, 1.0))

            ind_sig = ind_fdr <= 0.05
            mega_sig = mega_fdr <= 0.05
            same_dir = (ind_effect > 0 and mega_effect > 0) or (ind_effect < 0 and mega_effect < 0)

            if ind_sig and mega_sig and same_dir:
                tier = "GOLD"
            elif ind_sig or mega_sig:
                tier = "SILVER"
            else:
                tier = "BRONZE"

            concordance_rows.append({
                "gene_id": gene_id,
                "indirect_meta_fdr": f"{ind_fdr:.6g}",
                "mega_fdr": f"{mega_fdr:.6g}",
                "indirect_effect": f"{ind_effect:.6f}",
                "mega_effect": f"{mega_effect:.6f}",
                "concordance_tier": tier,
            })

        concordance_file = out_root / "concordance_indirect_vs_mega.tsv"
        write_tsv(
            concordance_file,
            fieldnames=["gene_id", "indirect_meta_fdr", "mega_fdr", "indirect_effect", "mega_effect", "concordance_tier"],
            rows=concordance_rows,
        )
        outputs.append(concordance_file)

        n_gold = sum(1 for r in concordance_rows if r["concordance_tier"] == "GOLD")
        n_silver = sum(1 for r in concordance_rows if r["concordance_tier"] == "SILVER")
        n_bronze = sum(1 for r in concordance_rows if r["concordance_tier"] == "BRONZE")
        print(f"Concordance: GOLD={n_gold}, SILVER={n_silver}, BRONZE={n_bronze}")

    _mark_run(args, "mega run", outputs)
    print(f"Wrote mega-analysis outputs under {out_root}")
    return 0


def cmd_signature_derive(args: argparse.Namespace) -> int:
    analysis_id = (getattr(args, "analysis_id", "") or getattr(args, "contrast", "") or "").strip()
    if not analysis_id:
        raise RuntimeError("signature derive requires --analysis-id or --contrast")
    run_root_raw = (getattr(args, "run_root", "") or "").strip()
    meta_dir_raw = (getattr(args, "meta_dir", "") or "").strip()
    if meta_dir_raw:
        meta_dir = Path(meta_dir_raw)
    elif run_root_raw:
        meta_dir = Path(run_root_raw) / "meta" / analysis_id
    else:
        raise RuntimeError("signature derive requires --meta-dir or --run-root")

    out_dir = Path(args.out)
    adjusted_meta_dir_raw = (getattr(args, "composition_adjusted_meta_dir", "") or "").strip()
    comparison_registry_raw = (getattr(args, "comparison_registry", "") or "").strip()
    if not comparison_registry_raw and run_root_raw:
        comparison_registry_raw = str(Path(run_root_raw) / "comparison_registry.tsv")
    outputs = derive_signature_outputs(
        analysis_id=analysis_id,
        meta_dir=meta_dir,
        out_dir=out_dir,
        thresholds_path=Path(args.thresholds) if getattr(args, "thresholds", "") else None,
        module_rules_path=Path(args.module_rules) if getattr(args, "module_rules", "") else None,
        comparison_registry_path=Path(comparison_registry_raw) if comparison_registry_raw else None,
        min_meta_cohorts=int(getattr(args, "min_meta_cohorts", 2)),
        allow_empty_signature=bool(getattr(args, "allow_empty_signature", False)),
        composition_adjusted_meta_dir=Path(adjusted_meta_dir_raw) if adjusted_meta_dir_raw else None,
    )
    _mark_run(args, "signature derive", outputs)
    print(f"Wrote Stage 08 signature outputs under {out_dir}")
    return 0


def cmd_immune_score(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
        import io
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Immune scoring requires numpy/pandas.") from exc

    manifest = read_tsv(Path(args.sample_manifest))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    gene_set_registry = Path(getattr(args, "gene_set_registry", "configs/immune_gene_sets_registry.tsv"))
    gene_id_mapping = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    min_hgnc_mapping_rate = float(getattr(args, "min_hgnc_mapping_rate", 0.60))
    max_unmapped_ensembl_fraction = float(getattr(args, "max_unmapped_ensembl_fraction", 0.20))
    max_duplicate_collapse_fraction = float(getattr(args, "max_duplicate_collapse_fraction", 0.25))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))

    if not gene_set_registry.exists():
        raise RuntimeError("Missing gene set registry for immune scoring.")

    import shutil
    import subprocess
    import tempfile

    legacy_rank_mean = bool(getattr(args, "legacy_rank_mean", False))
    rscript = shutil.which("Rscript")
    ssgsea_script = Path("scripts/ssgsea_gsva.R")
    estimate_script = Path("scripts/estimate_scores.R")
    epic_script = Path("scripts/epic_scores.R")
    ssgsea_module = importlib.import_module(".modules.09_immune_state.ssgsea", package=__package__)
    resolve_ssgsea_backend = ssgsea_module.resolve_ssgsea_backend

    backend_status = resolve_ssgsea_backend(
        legacy_rank_mean=legacy_rank_mean,
        rscript_path=rscript,
        ssgsea_script=ssgsea_script,
    )

    def _read_gmt(path: Path) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = [p.strip() for p in line.rstrip("\n").split("\t") if p.strip()]
                if len(parts) < 3:
                    continue
                rows.append({"term": parts[0], "description": parts[1], "genes": parts[2:]})
        return rows

    def _load_registry_gene_sets(registry_path: Path) -> list[dict[str, object]]:
        gene_sets: list[dict[str, object]] = []
        for row in read_tsv(registry_path):
            if row.get("enabled", "true").strip().lower() not in {"true", "1", "yes"}:
                continue
            layer = row.get("gene_set_layer", "").strip()
            gmt_raw = row.get("gmt_path", "").strip()
            if not layer or not gmt_raw:
                continue
            gmt_path = Path(gmt_raw).expanduser()
            if not gmt_path.is_absolute():
                gmt_path = Path.cwd() / gmt_path
            if not gmt_path.exists():
                raise RuntimeError(f"Enabled gene-set path does not exist: {gmt_path}")
            for gmt in _read_gmt(gmt_path):
                term = str(gmt["term"])
                gene_sets.append(
                    {
                        "gene_set_id": term,
                        "gene_set_layer": layer,
                        "gene_set_name": term,
                        "genes": [str(g).upper() for g in gmt["genes"]],
                        "gmt_path": str(gmt_path),
                        "source": row.get("source", ""),
                    }
                )
        if not gene_sets:
            raise RuntimeError(f"No enabled gene sets found in registry: {registry_path}")
        return gene_sets

    gene_sets = _load_registry_gene_sets(gene_set_registry)
    gene_set_ids = [str(gs["gene_set_id"]) for gs in gene_sets]

    eligible = [
        r for r in manifest if parse_bool(r.get("include_flag", "true"), default=True)
    ]

    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        by_cohort[row.get("cohort_id", "")].append(row)

    ssgsea_wide_rows: list[dict[str, object]] = []
    ssgsea_long_rows: list[dict[str, object]] = []
    layer_summary_rows: list[dict[str, object]] = []
    estimate_rows: list[dict[str, object]] = []
    epic_rows: list[dict[str, object]] = []
    layer_gate_rows: list[dict[str, object]] = []
    hope_rows: list[dict[str, object]] = []
    hope18_rows: list[dict[str, object]] = []

    def _patient_uid(row: dict[str, str]) -> str:
        raw = (row.get("patient_uid") or row.get("patient_id") or row.get("sample_id") or "").strip()
        return raw if "::" in raw else f"{row.get('cohort_id', '')}::{raw}"

    def _score_gene_sets_legacy(expr_log) -> dict[str, dict[str, float]]:
        ranks = expr_log.rank(axis=0, method="average", pct=True)
        score_by_set: dict[str, dict[str, float]] = {}
        for gs in gene_sets:
            genes = [g for g in gs["genes"] if g in ranks.index]
            if not genes:
                score_by_set[str(gs["gene_set_id"])] = {sample: float("nan") for sample in ranks.columns}
                continue
            values = ranks.loc[genes, :].mean(axis=0)
            score_by_set[str(gs["gene_set_id"])] = {sample: float(values.loc[sample]) for sample in ranks.columns}
        return score_by_set

    def _score_gene_sets_real(expr_log) -> dict[str, dict[str, float]]:
        if not rscript:
            raise RuntimeError("Rscript not found for real GSVA ssGSEA scoring.")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            expr_path = tmpdir_path / "expr_log.tsv"
            gmt_path = tmpdir_path / "combined_sets.gmt"
            out_path = tmpdir_path / "ssgsea_scores.tsv"
            expr_log.to_csv(expr_path, sep="\t")
            with gmt_path.open("w", encoding="utf-8") as fh:
                for gs in gene_sets:
                    genes = [g for g in gs["genes"] if g in expr_log.index]
                    if not genes:
                        continue
                    line = "\t".join(
                        [str(gs["gene_set_id"]), str(gs.get("gene_set_name", gs["gene_set_id"])), *genes]
                    )
                    fh.write(line + "\n")
            subprocess.run(
                [
                    rscript,
                    str(ssgsea_script),
                    "--expr",
                    str(expr_path),
                    "--gmt",
                    str(gmt_path),
                    "--out",
                    str(out_path),
                ],
                check=True,
            )
            df = pd.read_csv(out_path, sep="\t", index_col=0)
            score_by_set: dict[str, dict[str, float]] = {}
            for gene_set_id in gene_set_ids:
                if gene_set_id in df.index:
                    score_by_set[gene_set_id] = {
                        sample: float(df.loc[gene_set_id, sample]) for sample in df.columns
                    }
                else:
                    score_by_set[gene_set_id] = {sample: float("nan") for sample in expr_log.columns}
            return score_by_set

    def _parse_estimate_table(path: Path) -> dict[str, dict[str, float]]:
        if not path.exists():
            return {}
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            return {}
        start_idx = 0
        if lines[0].startswith("#1.2"):
            start_idx = 2
        table = pd.read_csv(
            io.StringIO("\n".join(lines[start_idx:])),
            sep="\t",
        )
        if table.empty:
            return {}
        key_col = table.columns[0]
        score_map: dict[str, dict[str, float]] = {}
        wanted = {
            "StromalScore": "stromal_score",
            "ImmuneScore": "immune_score",
            "ESTIMATEScore": "estimate_score",
            "TumorPurity": "purity_proxy",
        }
        for sample in table.columns[2:]:
            score_map[sample] = {}
        for _, row in table.iterrows():
            metric = str(row.get(key_col, ""))
            if metric not in wanted:
                continue
            out_key = wanted[metric]
            for sample in table.columns[2:]:
                try:
                    score_map.setdefault(sample, {})[out_key] = float(row.get(sample))
                except Exception:  # noqa: BLE001
                    score_map.setdefault(sample, {})[out_key] = float("nan")
        return score_map

    for cohort_id, cohort_rows in by_cohort.items():
        if _cohort_contract_exclusion_reason(cohort_id, cohort_rows):
            continue
        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        if expr is None or expr.empty:
            continue

        cohort_assay_type = _cohort_assay_type(cohort_rows)
        if cohort_assay_type in {"unreadable", "normalized_other", "raw_counts_suspect"}:
            detector_module = importlib.import_module(".modules._01_dataset_intake.assay_detect", package=__package__)
            detected_assay_type = detector_module.classify_expression_matrix(expr).assay_type
            if cohort_assay_type == "unreadable" and detected_assay_type:
                cohort_assay_type = detected_assay_type
            elif detected_assay_type in ASSAY_TYPE_HARD_EXCLUDE:
                cohort_assay_type = detected_assay_type
        if cohort_assay_type in ASSAY_TYPE_HARD_EXCLUDE:
            continue
        agg_method = "sum" if cohort_assay_type == "raw_counts" else "mean"
        expr, _, metrics = _standardize_expression_gene_ids(
            expr,
            mapping_path=gene_id_mapping,
            aggregation=agg_method,
        )
        status, fail_reason = _evaluate_gene_id_quality(
            metrics,
            min_hgnc_mapping_rate=min_hgnc_mapping_rate,
            max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
            max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
        )
        if status != "pass" and not allow_weak_gene_mapping:
            raise RuntimeError(
                "Gene ID quality gate failed during immune score for cohort "
                f"{cohort_id}: {fail_reason}. Provide a mapping file via --gene-id-mapping "
                "or rerun with --allow-weak-gene-mapping."
            )

        expr, available = _resolve_sample_columns(expr, cohort_rows)
        expr = expr.loc[:, available] if available else expr
        if expr.empty:
            continue
        expr_log, _ = _harmonize_expression_for_assay(expr, cohort_assay_type)

        row_by_sample = {r.get("sample_id", ""): r for r in cohort_rows}
        score_by_set = _score_gene_sets_legacy(expr_log) if legacy_rank_mean else _score_gene_sets_real(expr_log)

        estimate_by_sample: dict[str, dict[str, float]] = {}
        epic_by_sample: dict[str, dict[str, float]] = {}
        if rscript and estimate_script.exists() and epic_script.exists():
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                expr_linear = expr.copy().fillna(0.0)
                if cohort_assay_type in {"log_normalized", "rlog_vst", "microarray_intensity"}:
                    expr_linear = np.maximum(np.power(2.0, expr_log) - 1.0, 0.0)
                expr_linear_path = tmpdir_path / "expr_linear.tsv"
                expr_linear.to_csv(expr_linear_path, sep="\t")

                estimate_out = tmpdir_path / "estimate_scores.tsv"
                epic_out = tmpdir_path / "epic_scores.tsv"
                subprocess.run(
                    [rscript, str(estimate_script), "--expr", str(expr_linear_path), "--out", str(estimate_out)],
                    check=True,
                )
                subprocess.run(
                    [rscript, str(epic_script), "--expr", str(expr_linear_path), "--out", str(epic_out)],
                    check=True,
                )
                estimate_by_sample = _parse_estimate_table(estimate_out)
                try:
                    epic_df = pd.read_csv(epic_out, sep="\t")
                    if not epic_df.empty and "cell_type" in epic_df.columns:
                        for sample_col in [c for c in epic_df.columns if c != "cell_type"]:
                            epic_by_sample[sample_col] = {
                                str(row["cell_type"]): float(row[sample_col]) if pd.notna(row[sample_col]) else float("nan")
                                for _, row in epic_df.iterrows()
                            }
                except Exception:  # noqa: BLE001
                    epic_by_sample = {}

        for sample_id in expr_log.columns:
            source_row = row_by_sample.get(sample_id, {})
            wide_row: dict[str, object] = {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "patient_uid": _patient_uid(source_row) if source_row else f"{cohort_id}::{sample_id}",
            }
            layer_values: dict[str, list[float]] = defaultdict(list)
            for gs in gene_sets:
                gene_set_id = str(gs["gene_set_id"])
                layer = str(gs["gene_set_layer"])
                score = score_by_set[gene_set_id].get(sample_id, float("nan"))
                wide_row[gene_set_id] = f"{score:.6f}" if np.isfinite(score) else "nan"
                if np.isfinite(score):
                    layer_values[layer].append(score)
                ssgsea_long_rows.append(
                    {
                        "cohort_id": cohort_id,
                        "sample_id": sample_id,
                        "patient_uid": wide_row["patient_uid"],
                        "gene_set_id": gene_set_id,
                        "gene_set_name": gs["gene_set_name"],
                        "ssgsea_score": f"{score:.6f}" if np.isfinite(score) else "nan",
                        "gene_set_layer": layer,
                        "method": "ssgsea_rank_mean_python_legacy" if legacy_rank_mean else "gsva_ssgsea_r",
                    }
                )
            ssgsea_wide_rows.append(wide_row)

            for layer, vals in sorted(layer_values.items()):
                layer_summary_rows.append(
                    {
                        "cohort_id": cohort_id,
                        "sample_id": sample_id,
                        "patient_uid": wide_row["patient_uid"],
                        "gene_set_layer": layer,
                        "n_gene_sets_scored": len(vals),
                        "mean_score": f"{float(np.mean(vals)):.6f}",
                        "median_score": f"{float(np.median(vals)):.6f}",
                        "method": "ssgsea",
                    }
                )

            immune_vals = layer_values.get("L1_ICB_PREDICTOR", []) + layer_values.get("L2_C7_EXHAUSTION", [])
            immune_score = float(np.mean(immune_vals)) if immune_vals else float("nan")
            est = estimate_by_sample.get(sample_id, {})
            estimate_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": sample_id,
                    "immune_score": (
                        f"{est.get('immune_score', immune_score):.6f}"
                        if np.isfinite(est.get("immune_score", immune_score))
                        else "nan"
                    ),
                    "stromal_score": (
                        f"{est.get('stromal_score', float('nan')):.6f}"
                        if np.isfinite(est.get("stromal_score", float("nan")))
                        else "nan"
                    ),
                    "estimate_score": (
                        f"{est.get('estimate_score', float('nan')):.6f}"
                        if np.isfinite(est.get("estimate_score", float("nan")))
                        else "nan"
                    ),
                    "purity_proxy": (
                        f"{est.get('purity_proxy', float('nan')):.6f}"
                        if np.isfinite(est.get("purity_proxy", float("nan")))
                        else "nan"
                    ),
                    "score_scale": "ESTIMATE_real_or_na",
                }
            )
            for cell_type, value in epic_by_sample.get(sample_id, {}).items():
                epic_rows.append(
                    {
                        "cohort_id": cohort_id,
                        "sample_id": sample_id,
                        "cell_type": cell_type,
                        "fraction": f"{value:.6f}" if np.isfinite(value) else "nan",
                        "deconvolution_method": "EPIC",
                    }
                )

        # HOPE classification from CD274/CD8B expression is retained as the legacy subtype proxy.
        cd274 = expr_log.loc["CD274"] if "CD274" in expr_log.index else pd.Series(0.0, index=expr_log.columns, dtype=float)
        cd8b = expr_log.loc["CD8B"] if "CD8B" in expr_log.index else pd.Series(0.0, index=expr_log.columns, dtype=float)
        cd274_med = cd274.median()
        cd8b_med = cd8b.median()
        hope18_sets = [gs for gs in gene_sets if str(gs["gene_set_layer"]) == "L5_HOPE_18"]
        hope18_genes = [g for gs in hope18_sets for g in gs["genes"] if g in expr_log.index]
        for sample_id in expr_log.columns:
            cd274_state = "+" if cd274.get(sample_id, -np.inf) >= cd274_med else "-"
            cd8b_state = "+" if cd8b.get(sample_id, -np.inf) >= cd8b_med else "-"
            hope_type = (
                "A"
                if cd274_state == "+" and cd8b_state == "+"
                else "B"
                if cd274_state == "+" and cd8b_state == "-"
                else "D"
                if cd274_state == "-" and cd8b_state == "+"
                else "C"
            )
            hope_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": sample_id,
                    "cd274_state": cd274_state,
                    "cd8b_state": cd8b_state,
                    "hope_type": hope_type,
                    "classification_threshold_source": "cohort_median",
                }
            )
            if hope18_genes:
                score = float(expr_log.loc[hope18_genes, sample_id].mean())
                method = "mean_log2_expression"
            else:
                score = float("nan")
                method = "no_genes_available"
            hope18_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": sample_id,
                    "hope18_score": f"{score:.6f}" if np.isfinite(score) else "",
                    "n_genes_used": str(len(hope18_genes)),
                    "score_method": method,
                }
            )

        for layer in sorted({str(gs["gene_set_layer"]) for gs in gene_sets}):
            layer_gate_rows.append(
                {
                    "cohort_id": cohort_id,
                    "gene_set_layer": layer,
                    "backend_status": backend_status,
                    "gate_reason": "scored",
                }
            )

    estimate_file = out_root / "estimate_scores.tsv"
    epic_file = out_root / "epic_fractions.tsv"
    ssgsea_file = out_root / "ssgsea_scores.tsv"
    ssgsea_long_file = out_root / "ssgsea_scores_long.tsv"
    layer_summary_file = out_root / "layer_summary.tsv"
    gate_file = out_root / "gene_set_layer_gate.tsv"
    hope_file = out_root / "hope_types.tsv"
    hope18_file = out_root / "hope18_scores.tsv"
    mediator_file = out_root / "composition_mediator_inputs.tsv"

    write_tsv(
        estimate_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "immune_score",
            "stromal_score",
            "estimate_score",
            "purity_proxy",
            "score_scale",
        ],
        rows=estimate_rows,
    )
    write_tsv(
        epic_file,
        fieldnames=["cohort_id", "sample_id", "cell_type", "fraction", "deconvolution_method"],
        rows=epic_rows,
    )
    write_tsv(
        ssgsea_file,
        fieldnames=["cohort_id", "sample_id", "patient_uid"] + gene_set_ids,
        rows=ssgsea_wide_rows,
    )
    write_tsv(
        ssgsea_long_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_uid",
            "gene_set_id",
            "gene_set_name",
            "ssgsea_score",
            "gene_set_layer",
            "method",
        ],
        rows=ssgsea_long_rows,
    )
    write_tsv(
        layer_summary_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_uid",
            "gene_set_layer",
            "n_gene_sets_scored",
            "mean_score",
            "median_score",
            "method",
        ],
        rows=layer_summary_rows,
    )
    write_tsv(
        gate_file,
        fieldnames=["cohort_id", "gene_set_layer", "backend_status", "gate_reason"],
        rows=layer_gate_rows,
    )
    write_tsv(
        hope_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "cd274_state",
            "cd8b_state",
            "hope_type",
            "classification_threshold_source",
        ],
        rows=hope_rows,
    )
    write_tsv(
        hope18_file,
        fieldnames=["cohort_id", "sample_id", "hope18_score", "n_genes_used", "score_method"],
        rows=hope18_rows,
    )
    mediator_rows = []
    for row in estimate_rows:
        mediator_rows.append(
            {
                "cohort_id": row.get("cohort_id", ""),
                "sample_id": row.get("sample_id", ""),
                "immune_score": row.get("immune_score", ""),
                "stromal_score": row.get("stromal_score", ""),
                "estimate_score": row.get("estimate_score", ""),
                "purity_proxy": row.get("purity_proxy", ""),
                "mediator_role": "composition_mediator_candidate",
                "intended_use": "spec015_d5_secondary_mediation",
            }
        )
    write_tsv(
        mediator_file,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "immune_score",
            "stromal_score",
            "estimate_score",
            "purity_proxy",
            "mediator_role",
            "intended_use",
        ],
        rows=mediator_rows,
    )

    excluded = [
        {
            "cohort_id": r.get("cohort_id", ""),
            "sample_id": r.get("sample_id", ""),
            "exclude_reason": "not_rna_or_not_included_or_missing_expression",
        }
        for r in manifest
        if r not in eligible
    ]
    excluded_file = out_root / "immune_scoring_excluded.tsv"
    write_tsv(excluded_file, fieldnames=["cohort_id", "sample_id", "exclude_reason"], rows=excluded)

    outputs = [
        estimate_file,
        epic_file,
        ssgsea_file,
        ssgsea_long_file,
        layer_summary_file,
        gate_file,
        hope_file,
        hope18_file,
        mediator_file,
        excluded_file,
    ]
    repro_dir = out_root / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)
    repro_commands = repro_dir / "commands.sh"
    repro_commands.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "python -m pipeline.cli immune score \\",
                f"  --sample-manifest {args.sample_manifest} \\",
                f"  --expression-manifest {args.expression_manifest} \\",
                f"  --downloads-root {args.downloads_root} \\",
                f"  --gene-set-registry {args.gene_set_registry} \\",
                f"  --out {args.out}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_env = repro_dir / "environment.yml"
    repro_env.write_text(
        "\n".join(
            [
                "name: rnaseq-stage09-immune",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                f"  - python={sys.version_info.major}.{sys.version_info.minor}",
                "  - pandas",
                "  - numpy",
                "  - r-base",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_checksums = repro_dir / "checksums.sha256"
    checksum_lines = []
    for target in outputs:
        if isinstance(target, Path) and target.exists():
            checksum_lines.append(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {target}")
    repro_checksums.write_text(
        "\n".join(checksum_lines) + ("\n" if checksum_lines else ""),
        encoding="utf-8",
    )
    outputs.extend([repro_commands, repro_env, repro_checksums])
    _mark_run(args, "immune score", outputs)
    print(f"Wrote immune-state outputs under {out_root}")
    return 0


def cmd_immune_effects(args: argparse.Namespace) -> int:
    try:
        import numpy as np
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Immune effects requires numpy.") from exc

    try:
        from scipy.stats import spearmanr, ttest_ind
    except Exception:  # noqa: BLE001
        spearmanr = None
        ttest_ind = None

    manifest = read_tsv(Path(args.sample_manifest))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    cohort_ids = sorted({r.get("cohort_id", "") for r in manifest if r.get("cohort_id")})

    downloads_root = Path(getattr(args, "downloads_root", "results/retrieval/downloads"))
    expression_manifest = Path(getattr(args, "expression_manifest", "results/geo_tables/geo_tables_summary.tsv"))
    gene_id_mapping = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    min_hgnc_mapping_rate = float(getattr(args, "min_hgnc_mapping_rate", 0.60))
    max_unmapped_ensembl_fraction = float(getattr(args, "max_unmapped_ensembl_fraction", 0.20))
    max_duplicate_collapse_fraction = float(getattr(args, "max_duplicate_collapse_fraction", 0.25))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))

    estimate_path = Path(args.immune_dir) / "estimate_scores.tsv"
    estimate_rows = (
        {(r.get("cohort_id", ""), r.get("sample_id", "")): r for r in read_tsv(estimate_path)}
        if estimate_path.exists()
        else {}
    )
    ssgsea_path = Path(args.immune_dir) / "ssgsea_scores_long.tsv"
    ssgsea_rows = read_tsv(ssgsea_path) if ssgsea_path.exists() else []
    layer_path = Path(args.immune_dir) / "layer_summary.tsv"
    layer_rows = read_tsv(layer_path) if layer_path.exists() else []

    def _as_float(value: object) -> float:
        try:
            val = float(value)
        except Exception:
            return float("nan")
        return val if np.isfinite(val) else float("nan")

    def _finite(values: list[float]) -> list[float]:
        return [v for v in values if np.isfinite(v)]

    def _fmt(value: float) -> str:
        return "nan" if not np.isfinite(value) else f"{value:.6f}"

    def _mean_or_nan(values: list[float]) -> float:
        vals = _finite(values)
        return float(np.mean(vals)) if vals else float("nan")

    def _response_effect_row(
        *,
        cohort_id: str,
        feature_name: str,
        feature_values: dict[str, float],
        case_ids: list[str],
        control_ids: list[str],
        feature_source: str,
        gene_set_layer: str = "",
        model_class: str = "welch_t_test",
    ) -> dict[str, str]:
        case_vals = _finite([feature_values.get(sid, float("nan")) for sid in case_ids])
        control_vals = _finite([feature_values.get(sid, float("nan")) for sid in control_ids])
        mean_case = _mean_or_nan(case_vals)
        mean_control = _mean_or_nan(control_vals)
        effect = mean_case - mean_control if np.isfinite(mean_case) and np.isfinite(mean_control) else float("nan")
        stat = 0.0
        p_val = 1.0
        if ttest_ind is not None and len(case_vals) >= 2 and len(control_vals) >= 2:
            stat, p_val = ttest_ind(case_vals, control_vals, equal_var=False, nan_policy="omit")
            stat = 0.0 if stat is None or not np.isfinite(float(stat)) else float(stat)
            p_val = 1.0 if p_val is None or not np.isfinite(float(p_val)) else float(p_val)
        return {
            "cohort_id": cohort_id,
            "contrast_family": "PRE_RESPONSE",
            "immune_feature": feature_name,
            "feature_source": feature_source,
            "gene_set_layer": gene_set_layer,
            "effect_type": "response_association",
            "effect_size": _fmt(effect),
            "se_or_stat": _fmt(float(stat)),
            "p_value": f"{float(p_val):.6g}",
            "fdr": "pending",
            "model_class": model_class,
            "analysis_mode": "continuous_primary",
            "n_responders": str(len(case_vals)),
            "n_non_responders": str(len(control_vals)),
            "mean_responder": _fmt(mean_case),
            "mean_non_responder": _fmt(mean_control),
        }

    def _apply_bh_fdr(rows: list[dict[str, str]]) -> None:
        if not rows:
            return
        pvals = []
        for row in rows:
            pval = _as_float(row.get("p_value", "1"))
            pvals.append(1.0 if not np.isfinite(pval) else pval)
        pvals_array = np.array(pvals, dtype=float)
        order = np.argsort(pvals_array)
        fdr = np.empty(len(pvals_array), dtype=float)
        prev = 1.0
        for i in range(len(pvals_array) - 1, -1, -1):
            idx = order[i]
            rank = i + 1
            val = min(prev, pvals_array[idx] * len(pvals_array) / rank)
            fdr[idx] = val
            prev = val
        for i, row in enumerate(rows):
            row["fdr"] = f"{fdr[i]:.6g}"

    marker_rows: list[dict[str, str]] = []
    effect_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    markers = ["CD8A", "IFNG", "CXCL9", "CD274"]
    features = ["immune_score", "estimate_score"]

    ssgsea_by_cohort_feature: dict[tuple[str, str], dict[str, object]] = {}
    for row in ssgsea_rows:
        cohort_id = row.get("cohort_id", "")
        gene_set_id = row.get("gene_set_id", "")
        sample_id = row.get("sample_id", "")
        if not cohort_id or not gene_set_id or not sample_id:
            continue
        key = (cohort_id, gene_set_id)
        bucket = ssgsea_by_cohort_feature.setdefault(
            key,
            {
                "gene_set_layer": row.get("gene_set_layer", ""),
                "values": {},
            },
        )
        bucket["values"][sample_id] = _as_float(row.get("ssgsea_score", "nan"))

    layer_by_cohort_feature: dict[tuple[str, str], dict[str, object]] = {}
    for row in layer_rows:
        cohort_id = row.get("cohort_id", "")
        layer = row.get("gene_set_layer", "")
        sample_id = row.get("sample_id", "")
        if not cohort_id or not layer or not sample_id:
            continue
        key = (cohort_id, f"layer_mean::{layer}")
        bucket = layer_by_cohort_feature.setdefault(
            key,
            {
                "gene_set_layer": layer,
                "values": {},
            },
        )
        bucket["values"][sample_id] = _as_float(row.get("mean_score", "nan"))

    for cohort_id in cohort_ids:
        cohort_rows = [
            r
            for r in manifest
            if r.get("cohort_id", "") == cohort_id and parse_bool(r.get("include_flag", "true"), default=True)
        ]
        case_ids = [
            r.get("sample_id", "")
            for r in cohort_rows
            if r.get("timing_category", "") == "pre-treatment" and r.get("response_label", "") == "responder"
        ]
        control_ids = [
            r.get("sample_id", "")
            for r in cohort_rows
            if r.get("timing_category", "") == "pre-treatment" and r.get("response_label", "") == "non_responder"
        ]

        for feature in features:
            feature_values = {
                sid: _as_float(estimate_rows.get((cohort_id, sid), {}).get(feature, "nan"))
                for sid in case_ids + control_ids
            }
            effect_rows.append(
                _response_effect_row(
                    cohort_id=cohort_id,
                    feature_name=feature,
                    feature_values=feature_values,
                    case_ids=case_ids,
                    control_ids=control_ids,
                    feature_source="estimate",
                )
            )

        for (feature_cohort, feature_name), bucket in sorted(ssgsea_by_cohort_feature.items()):
            if feature_cohort != cohort_id:
                continue
            effect_rows.append(
                _response_effect_row(
                    cohort_id=cohort_id,
                    feature_name=feature_name,
                    feature_values=bucket["values"],
                    case_ids=case_ids,
                    control_ids=control_ids,
                    feature_source="gsva_ssgsea",
                    gene_set_layer=str(bucket.get("gene_set_layer", "")),
                )
            )

        for (feature_cohort, feature_name), bucket in sorted(layer_by_cohort_feature.items()):
            if feature_cohort != cohort_id:
                continue
            effect_rows.append(
                _response_effect_row(
                    cohort_id=cohort_id,
                    feature_name=feature_name,
                    feature_values=bucket["values"],
                    case_ids=case_ids,
                    control_ids=control_ids,
                    feature_source="ssgsea_layer_mean",
                    gene_set_layer=str(bucket.get("gene_set_layer", "")),
                )
            )

        expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
        expr = load_expression_matrix(expr_path) if expr_path else None
        if expr is None or expr.empty:
            audit_rows.append(
                {
                    "cohort_id": cohort_id,
                    "expression_path": str(expr_path or ""),
                    "marker_correlation_status": "missing_expression",
                    "marker_correlations_emitted": "0",
                    "note": "cohort-level immune effects were computed from immune score tables when available",
                }
            )
            continue

        input_classes = sorted(
            {
                (r.get("input_class", "") or "").strip().lower()
                for r in cohort_rows
                if r.get("input_class", "")
            }
        )
        agg_method = "sum" if input_classes == ["raw_counts"] else "mean"
        expr, _, metrics = _standardize_expression_gene_ids(
            expr,
            mapping_path=gene_id_mapping,
            aggregation=agg_method,
        )
        status, fail_reason = _evaluate_gene_id_quality(
            metrics,
            min_hgnc_mapping_rate=min_hgnc_mapping_rate,
            max_unmapped_ensembl_fraction=max_unmapped_ensembl_fraction,
            max_duplicate_collapse_fraction=max_duplicate_collapse_fraction,
        )
        if status != "pass" and not allow_weak_gene_mapping:
            raise RuntimeError(
                "Gene ID quality gate failed during immune effects for cohort "
                f"{cohort_id}: {fail_reason}. Provide a mapping file via --gene-id-mapping "
                "or rerun with --allow-weak-gene-mapping."
            )

        sample_ids = [r.get("sample_id", "") for r in cohort_rows if r.get("sample_id", "") in expr.columns]
        if not sample_ids:
            audit_rows.append(
                {
                    "cohort_id": cohort_id,
                    "expression_path": str(expr_path or ""),
                    "marker_correlation_status": "no_matching_expression_samples",
                    "marker_correlations_emitted": "0",
                    "note": "cohort-level immune effects were computed from immune score tables when available",
                }
            )
            continue

        expr = expr.loc[:, sample_ids].fillna(0.0)
        expr_log = np.log2(expr + 1.0)

        # Marker correlations
        marker_count_before = len(marker_rows)
        for marker in markers:
            if marker not in expr_log.index:
                continue
            marker_vals = expr_log.loc[marker].values
            immune_vals = np.array(
                [
                    float(estimate_rows.get((cohort_id, sid), {}).get("immune_score", "nan"))
                    for sid in sample_ids
                ]
            )
            if spearmanr is None or np.isnan(immune_vals).all():
                corr_val, p_val = 0.0, 1.0
            else:
                corr_val, p_val = spearmanr(marker_vals, immune_vals, nan_policy="omit")
                if corr_val is None or not np.isfinite(float(corr_val)):
                    corr_val, p_val = 0.0, 1.0
            marker_rows.append(
                {
                    "cohort_id": cohort_id,
                    "marker_gene": marker,
                    "immune_feature": "immune_score",
                    "correlation_method": "spearman",
                    "correlation_value": f"{corr_val:.6f}",
                    "p_value": f"{p_val:.6g}",
                    "fdr": "pending",
                }
            )
        audit_rows.append(
            {
                "cohort_id": cohort_id,
                "expression_path": str(expr_path or ""),
                "marker_correlation_status": "completed" if len(marker_rows) > marker_count_before else "markers_absent",
                "marker_correlations_emitted": str(len(marker_rows) - marker_count_before),
                "note": "",
            }
        )

    # FDR
    _apply_bh_fdr(marker_rows)
    _apply_bh_fdr(effect_rows)

    marker_file = out_root / "marker_correlations.tsv"
    effects_file = out_root / "cohort_level_effects.tsv"
    audit_file = out_root / "immune_effects_input_audit.tsv"
    write_tsv(
        marker_file,
        fieldnames=[
            "cohort_id",
            "marker_gene",
            "immune_feature",
            "correlation_method",
            "correlation_value",
            "p_value",
            "fdr",
        ],
        rows=marker_rows,
    )
    write_tsv(
        effects_file,
        fieldnames=[
            "cohort_id",
            "contrast_family",
            "immune_feature",
            "feature_source",
            "gene_set_layer",
            "effect_type",
            "effect_size",
            "se_or_stat",
            "p_value",
            "fdr",
            "model_class",
            "analysis_mode",
            "n_responders",
            "n_non_responders",
            "mean_responder",
            "mean_non_responder",
        ],
        rows=effect_rows,
    )
    write_tsv(
        audit_file,
        fieldnames=[
            "cohort_id",
            "expression_path",
            "marker_correlation_status",
            "marker_correlations_emitted",
            "note",
        ],
        rows=audit_rows,
    )
    _mark_run(args, "immune effects", [marker_file, effects_file, audit_file])
    print(f"Wrote {marker_file}, {effects_file}, and {audit_file}")
    return 0


def cmd_validate_run(args: argparse.Namespace) -> int:
    import math

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    results_root = Path(getattr(args, "results_root", "")).expanduser() if getattr(args, "results_root", "") else None
    contrast = getattr(args, "contrast", "PRE_RESPONSE")

    signature_path = Path(args.signature).expanduser()
    if not signature_path.exists():
        raise RuntimeError(f"Missing signature file for validation: {signature_path}")

    def _path_arg(name: str, default_from_results_root: str = "") -> Path:
        value = getattr(args, name, "")
        if value:
            return Path(value).expanduser()
        if results_root and default_from_results_root:
            return results_root / default_from_results_root
        return Path("")

    def _first_existing_path_arg(name: str, defaults_from_results_root: list[str]) -> Path:
        value = getattr(args, name, "")
        if value:
            return Path(value).expanduser()
        if not results_root:
            return Path("")
        for default in defaults_from_results_root:
            candidate = results_root / default
            if candidate.exists():
                return candidate
        return results_root / defaults_from_results_root[0] if defaults_from_results_root else Path("")

    indirect_meta_path = _first_existing_path_arg(
        "indirect_meta",
        [
            f"meta/{contrast}/meta_effects.tsv",
            f"router/meta_analysis/pre_response_only/{contrast}/meta_effects.tsv",
        ],
    )
    mega_results_path = _path_arg("mega_results", "mega_analysis/mega_de_results.tsv")
    mega_concordance_path = _path_arg("mega_concordance", "mega_analysis/concordance_indirect_vs_mega.tsv")
    tcga_projection_dir = _path_arg("tcga_projection", "tcga_projection")
    heldout_evaluation_path = _path_arg("heldout_evaluation", "validation/heldout_evaluation.tsv")
    meta_loco_summary_path = _first_existing_path_arg(
        "meta_loco_summary",
        [f"meta/{contrast}/meta_leave_one_out_summary.tsv"],
    )
    nested_loco_input_path = (
        Path(getattr(args, "nested_loco_evaluation", "")).expanduser()
        if getattr(args, "nested_loco_evaluation", "")
        else Path("")
    )
    sample_manifest_path = Path(getattr(args, "sample_manifest", "configs/sample_manifest_curated.tsv")).expanduser()

    signature_rows = read_tsv(signature_path)
    signature_genes = {r.get("gene_id", "") for r in signature_rows if r.get("gene_id", "")}
    signature_direction_by_gene = {
        r.get("gene_id", ""): (r.get("signature_direction", "") or "").strip().lower()
        for r in signature_rows
        if r.get("gene_id", "")
    }
    signature_n = len(signature_genes)
    signature_readiness_status = "completed" if signature_n > 0 else "blocked"
    signature_readiness_reason = "non_empty_signature" if signature_n > 0 else "empty_signature"
    signature_readiness_detail = f"signature_genes={signature_n}"

    # ---------- Concordance Validation ----------
    concordance_file = out_root / "validation_concordance.tsv"
    concordance_summary_file = out_root / "validation_concordance_summary.tsv"
    robustness_concordance_file = out_root / "robustness_concordance.tsv"
    robustness_concordance_summary_file = out_root / "robustness_concordance_summary.tsv"
    readiness_file = out_root / "validation_readiness_status.tsv"
    concordance_rows: list[dict[str, str]] = []
    concordance_summary_rows: list[dict[str, str]] = []

    def _as_float(value: str, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:  # noqa: BLE001
            return default

    indirect_rows = read_tsv(indirect_meta_path) if indirect_meta_path and indirect_meta_path.is_file() else []
    mega_rows = read_tsv(mega_results_path) if mega_results_path and mega_results_path.is_file() else []

    if indirect_rows and mega_rows:
        indirect_map = {
            r.get("gene_id", ""): (
                _as_float(r.get("meta_effect_random", r.get("meta_effect", "0.0"))),
                _as_float(r.get("meta_fdr", "1.0"), default=1.0),
            )
            for r in indirect_rows
            if r.get("gene_id", "")
        }
        mega_map = {
            r.get("gene_id", ""): (
                _as_float(r.get("log2fc", "0.0")),
                _as_float(r.get("fdr", "1.0"), default=1.0),
            )
            for r in mega_rows
            if r.get("gene_id", "")
        }
        overlap = sorted(set(indirect_map.keys()).intersection(mega_map.keys()))
        for gene_id in overlap:
            ind_effect, ind_fdr = indirect_map[gene_id]
            mega_effect, mega_fdr = mega_map[gene_id]
            ind_sig = ind_fdr <= 0.05
            mega_sig = mega_fdr <= 0.05
            same_dir = (ind_effect > 0 and mega_effect > 0) or (ind_effect < 0 and mega_effect < 0)
            if ind_sig and mega_sig and same_dir:
                tier = "GOLD"
            elif ind_sig or mega_sig:
                tier = "SILVER"
            else:
                tier = "BRONZE"
            concordance_rows.append(
                {
                    "gene_id": gene_id,
                    "in_signature": "true" if gene_id in signature_genes else "false",
                    "indirect_effect": f"{ind_effect:.6f}",
                    "indirect_meta_fdr": f"{ind_fdr:.6g}",
                    "mega_effect": f"{mega_effect:.6f}",
                    "mega_fdr": f"{mega_fdr:.6g}",
                    "concordance_tier": tier,
                }
            )

        n_gold = sum(1 for r in concordance_rows if r["concordance_tier"] == "GOLD")
        n_silver = sum(1 for r in concordance_rows if r["concordance_tier"] == "SILVER")
        n_bronze = sum(1 for r in concordance_rows if r["concordance_tier"] == "BRONZE")
        sig_overlap = [r for r in concordance_rows if r["in_signature"] == "true"]
        sig_gold = sum(1 for r in sig_overlap if r["concordance_tier"] == "GOLD")
        concordance_status = "ok" if concordance_rows else "no_overlap_genes"
        concordance_note = ""
    elif mega_concordance_path and mega_concordance_path.is_file():
        pre_rows = read_tsv(mega_concordance_path)
        for row in pre_rows:
            gene_id = row.get("gene_id", "")
            if not gene_id:
                continue
            concordance_rows.append(
                {
                    "gene_id": gene_id,
                    "in_signature": "true" if gene_id in signature_genes else "false",
                    "indirect_effect": row.get("indirect_effect", ""),
                    "indirect_meta_fdr": row.get("indirect_meta_fdr", ""),
                    "mega_effect": row.get("mega_effect", ""),
                    "mega_fdr": row.get("mega_fdr", ""),
                    "concordance_tier": row.get("concordance_tier", "BRONZE"),
                }
            )
        n_gold = sum(1 for r in concordance_rows if r["concordance_tier"] == "GOLD")
        n_silver = sum(1 for r in concordance_rows if r["concordance_tier"] == "SILVER")
        n_bronze = sum(1 for r in concordance_rows if r["concordance_tier"] == "BRONZE")
        sig_overlap = [r for r in concordance_rows if r["in_signature"] == "true"]
        sig_gold = sum(1 for r in sig_overlap if r["concordance_tier"] == "GOLD")
        concordance_status = "ok_precomputed"
        concordance_note = str(mega_concordance_path)
    else:
        n_gold = n_silver = n_bronze = 0
        sig_overlap = []
        sig_gold = 0
        mega_skip_file = mega_results_path.parent / "mega_analysis_skipped.tsv" if mega_results_path else Path("")
        if mega_skip_file.exists():
            skip_rows = read_tsv(mega_skip_file)
            skip_reason = skip_rows[0].get("reason", "mega_skipped") if skip_rows else "mega_skipped"
            concordance_status = "blocked_mega_skipped"
            concordance_note = f"mega_analysis_skipped: {skip_reason}"
        elif not indirect_rows:
            concordance_status = "blocked_missing_indirect_meta"
            concordance_note = str(indirect_meta_path) if str(indirect_meta_path) else "indirect meta path not provided"
        else:
            concordance_status = "blocked_missing_mega_results"
            concordance_note = str(mega_results_path) if str(mega_results_path) else "mega results path not provided"

    def _direction_concordant(signature_direction: str, effect: float) -> bool:
        if signature_direction == "up":
            return effect > 0.0
        if signature_direction == "down":
            return effect < 0.0
        return False

    def _fraction_str(numer: int, denom: int) -> str:
        return f"{(numer / denom):.6g}" if denom else ""

    def _is_real_path(path: Path) -> bool:
        return str(path).strip() not in {"", "."}

    def _build_nested_loco_evaluation() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        source_path = (
            nested_loco_input_path
            if _is_real_path(nested_loco_input_path) and nested_loco_input_path.is_file()
            else Path("")
        )
        source_rows = read_tsv(source_path) if _is_real_path(source_path) else []
        source_kind = "precomputed_nested_loco"
        if not source_rows and meta_loco_summary_path and meta_loco_summary_path.is_file():
            source_path = meta_loco_summary_path
            source_rows = read_tsv(meta_loco_summary_path)
            source_kind = "meta_leave_one_out_summary"

        rows: list[dict[str, str]] = []
        if source_rows:
            by_gene = {row.get("gene_id", ""): row for row in source_rows if row.get("gene_id", "")}
            for gene_id in sorted(signature_genes):
                row = by_gene.get(gene_id, {})
                if not row:
                    continue
                full_effect = _as_float(
                    row.get("full_meta_effect_random", row.get("meta_effect_random", row.get("indirect_effect", ""))),
                    default=float("nan"),
                )
                full_fdr = _as_float(
                    row.get("full_meta_fdr", row.get("meta_fdr", row.get("indirect_meta_fdr", ""))),
                    default=float("nan"),
                )
                direction = signature_direction_by_gene.get(gene_id, "")
                direction_flip = parse_bool(row.get("direction_flip_any", "false"), default=False)
                full_effect_direction_ok = (
                    _direction_concordant(direction, full_effect) if math.isfinite(full_effect) else False
                )
                direction_ok = full_effect_direction_ok and not direction_flip
                common_scale = parse_bool(row.get("common_effect_scale", ""), default=False) or (
                    row.get("effect_scale_status", "") == "common_scale"
                )
                robustness_pass = direction_ok and not direction_flip and common_scale
                stability_label = row.get("signature_stability_label", "")
                rows.append(
                    {
                        "analysis_id": row.get("analysis_id", contrast) or contrast,
                        "gene_id": gene_id,
                        "in_signature": "true",
                        "signature_direction": direction,
                        "full_meta_effect": f"{full_effect:.6g}" if math.isfinite(full_effect) else "",
                        "full_meta_fdr": f"{full_fdr:.6g}" if math.isfinite(full_fdr) else "",
                        "n_loo_runs": row.get("n_loo_runs", ""),
                        "max_abs_delta_effect": row.get("max_abs_delta_effect", ""),
                        "direction_flip_any": "true" if direction_flip else "false",
                        "loo_support_fraction": row.get("loo_support_fraction", ""),
                        "signature_stability_label": stability_label,
                        "effect_direction_concordant": "true" if direction_ok else "false",
                        "common_effect_scale": "true" if common_scale else "false",
                        "robustness_pass": "true" if robustness_pass else "false",
                        "evidence_scope": "internal_nested_loco_robustness",
                        "evaluation_label": "internal nested LOCO robustness, not external validation",
                        "source_file": str(source_path),
                        "source_kind": source_kind,
                    }
                )

        evaluated = len(rows)
        direction_ok_count = sum(1 for row in rows if row.get("effect_direction_concordant") == "true")
        pass_count = sum(1 for row in rows if row.get("robustness_pass") == "true")
        stable_count = sum(1 for row in rows if row.get("signature_stability_label") == "stable")
        missing_signature_genes = max(signature_n - evaluated, 0)
        if evaluated:
            status = "completed"
            reason = "nested_loco_signature_genes_evaluated"
        elif signature_n == 0:
            status = "blocked"
            reason = "empty_signature"
        elif _is_real_path(source_path):
            status = "blocked"
            reason = "signature_genes_missing_from_loco_summary"
        else:
            status = "missing"
            reason = "missing_meta_leave_one_out_summary"
        summary = [
            {
                "contrast": contrast,
                "analysis_id": contrast,
                "status": status,
                "reason": reason,
                "n_signature_genes": str(signature_n),
                "n_signature_genes_evaluated": str(evaluated),
                "n_signature_genes_missing_from_loco": str(missing_signature_genes),
                "n_direction_concordant": str(direction_ok_count),
                "n_robustness_pass": str(pass_count),
                "n_stable": str(stable_count),
                "effect_concordance": _fraction_str(direction_ok_count, evaluated),
                "robustness_pass_fraction": _fraction_str(pass_count, evaluated),
                "stability_fraction": _fraction_str(stable_count, evaluated),
                "evidence_scope": "internal_nested_loco_robustness",
                "interpretation": "Internal leave-one-cohort-out robustness only; not external validation and not a sample-level classifier AUC.",
                "source_file": str(source_path) if source_path else str(meta_loco_summary_path),
            }
        ]
        return rows, summary

    nested_loco_file = out_root / "nested_loco_evaluation.tsv"
    nested_loco_summary_file = out_root / "nested_loco_evaluation_summary.tsv"
    nested_loco_rows, nested_loco_summary_rows = _build_nested_loco_evaluation()
    nested_loco_summary = nested_loco_summary_rows[0] if nested_loco_summary_rows else {}
    nested_loco_status = nested_loco_summary.get("status", "missing")
    nested_loco_reason = nested_loco_summary.get("reason", "missing_meta_leave_one_out_summary")
    nested_loco_detail = (
        f"evaluated={nested_loco_summary.get('n_signature_genes_evaluated', '0')}; "
        f"effect_concordance={nested_loco_summary.get('effect_concordance', '')}; "
        f"stability_fraction={nested_loco_summary.get('stability_fraction', '')}; "
        f"source={nested_loco_summary.get('source_file', '')}"
    )

    if concordance_status in {"ok", "ok_precomputed"}:
        upstream_meta_status = "completed"
        upstream_meta_reason = "meta_concordance_available"
    elif nested_loco_status == "completed":
        upstream_meta_status = "completed"
        upstream_meta_reason = "nested_loco_robustness_available"
    elif concordance_status == "no_overlap_genes":
        upstream_meta_status = "blocked"
        upstream_meta_reason = "no_overlap_genes"
    elif concordance_status.startswith("blocked_"):
        upstream_meta_status = "blocked"
        upstream_meta_reason = concordance_status
    else:
        upstream_meta_status = "missing"
        upstream_meta_reason = concordance_status or "meta_state_unknown"
    upstream_meta_detail = (
        nested_loco_detail
        if upstream_meta_reason == "nested_loco_robustness_available"
        else concordance_note or f"overlap_genes={len(concordance_rows)}"
    )

    if signature_readiness_status == "completed" and upstream_meta_status == "completed":
        validation_readiness_status = "completed"
        validation_readiness_reason = "signature_and_meta_ready"
    elif signature_readiness_status == "missing" or upstream_meta_status == "missing":
        validation_readiness_status = "missing"
        validation_readiness_reason = "upstream_state_missing"
    else:
        validation_readiness_status = "blocked"
        validation_readiness_reason = "upstream_signature_or_meta_blocked"
    validation_readiness_detail = (
        f"signature={signature_readiness_status}; meta={upstream_meta_status}; "
        f"concordance_status={concordance_status}; nested_loco_status={nested_loco_status}"
    )
    external_rows = (
        read_tsv(heldout_evaluation_path)
        if heldout_evaluation_path and heldout_evaluation_path.is_file()
        else []
    )
    if external_rows:
        required_external_cols = {"auc", "effect_concordance"}
        present_cols = set(external_rows[0].keys())
        missing_cols = sorted(required_external_cols - present_cols)
        if missing_cols:
            raise RuntimeError(
                "heldout evaluation contract requires columns: "
                f"{', '.join(sorted(required_external_cols))}; "
                f"missing={', '.join(missing_cols)}"
            )
    external_auc_vals: list[float] = []
    external_effect_vals: list[float] = []
    for row in external_rows:
        auc = _as_float(row.get("auc", ""), default=float("nan"))
        eff = _as_float(row.get("effect_concordance", ""), default=float("nan"))
        if math.isfinite(auc):
            if auc < 0.0 or auc > 1.0:
                raise RuntimeError(
                    "heldout evaluation values must be in [0,1]: "
                    f"auc={auc} at fold={row.get('fold_id', '') or row.get('cohort_id', '') or 'unknown'}"
                )
            external_auc_vals.append(float(auc))
        if math.isfinite(eff):
            if eff < 0.0 or eff > 1.0:
                raise RuntimeError(
                    "heldout evaluation values must be in [0,1]: "
                    f"effect_concordance={eff} at fold={row.get('fold_id', '') or row.get('cohort_id', '') or 'unknown'}"
                )
            external_effect_vals.append(float(eff))
    if external_rows and (not external_auc_vals or not external_effect_vals):
        raise RuntimeError(
            "heldout evaluation must provide at least one numeric auc and effect_concordance "
            f"(n_valid_auc={len(external_auc_vals)}, "
            f"n_valid_effect_concordance={len(external_effect_vals)})"
        )
    auc_min = min(external_auc_vals) if external_auc_vals else float("nan")
    auc_max = max(external_auc_vals) if external_auc_vals else float("nan")
    effect_concordance_min = min(external_effect_vals) if external_effect_vals else float("nan")
    effect_concordance_max = max(external_effect_vals) if external_effect_vals else float("nan")
    auc_mean = (
        float(sum(external_auc_vals) / len(external_auc_vals)) if external_auc_vals else float("nan")
    )
    effect_concordance_mean = (
        float(sum(external_effect_vals) / len(external_effect_vals)) if external_effect_vals else float("nan")
    )
    if external_rows:
        external_validation_status = "completed"
        external_validation_reason = "external_holdout_evaluation_available"
        external_validation_detail = (
            f"rows={len(external_rows)}; "
            f"auc_mean={auc_mean:.3g}; "
            f"effect_concordance_mean={effect_concordance_mean:.3g}"
            if math.isfinite(auc_mean) and math.isfinite(effect_concordance_mean)
            else f"rows={len(external_rows)}"
        )
    else:
        external_validation_status = "missing"
        external_validation_reason = "missing_external_holdout_evaluation"
        external_validation_detail = str(heldout_evaluation_path) if heldout_evaluation_path else ""

    write_tsv(
        concordance_file,
        fieldnames=[
            "gene_id",
            "in_signature",
            "indirect_effect",
            "indirect_meta_fdr",
            "mega_effect",
            "mega_fdr",
            "concordance_tier",
        ],
        rows=concordance_rows,
    )
    nested_loco_fieldnames = [
        "analysis_id",
        "gene_id",
        "in_signature",
        "signature_direction",
        "full_meta_effect",
        "full_meta_fdr",
        "n_loo_runs",
        "max_abs_delta_effect",
        "direction_flip_any",
        "loo_support_fraction",
        "signature_stability_label",
        "effect_direction_concordant",
        "common_effect_scale",
        "robustness_pass",
        "evidence_scope",
        "evaluation_label",
        "source_file",
        "source_kind",
    ]
    nested_loco_summary_fieldnames = [
        "contrast",
        "analysis_id",
        "status",
        "reason",
        "n_signature_genes",
        "n_signature_genes_evaluated",
        "n_signature_genes_missing_from_loco",
        "n_direction_concordant",
        "n_robustness_pass",
        "n_stable",
        "effect_concordance",
        "robustness_pass_fraction",
        "stability_fraction",
        "evidence_scope",
        "interpretation",
        "source_file",
    ]
    write_tsv(nested_loco_file, fieldnames=nested_loco_fieldnames, rows=nested_loco_rows)
    write_tsv(nested_loco_summary_file, fieldnames=nested_loco_summary_fieldnames, rows=nested_loco_summary_rows)
    concordance_summary_rows.append(
        {
            "contrast": contrast,
            "status": concordance_status,
            "n_genes_indirect_meta": str(len(indirect_rows)),
            "n_genes_mega": str(len(mega_rows)),
            "n_genes_overlap": str(len(concordance_rows)),
            "n_gold": str(n_gold),
            "n_silver": str(n_silver),
            "n_bronze": str(n_bronze),
            "signature_gene_count": str(signature_n),
            "signature_overlap_count": str(len(sig_overlap)),
            "signature_gold_count": str(sig_gold),
            "signature_readiness_status": signature_readiness_status,
            "signature_readiness_reason": signature_readiness_reason,
            "upstream_meta_status": upstream_meta_status,
            "upstream_meta_reason": upstream_meta_reason,
            "external_validation_status": external_validation_status,
            "external_validation_reason": external_validation_reason,
            "readiness_status": validation_readiness_status,
            "readiness_reason": validation_readiness_reason,
            "nested_loco_status": nested_loco_status,
            "nested_loco_reason": nested_loco_reason,
            "nested_loco_effect_concordance": nested_loco_summary.get("effect_concordance", ""),
            "nested_loco_stability_fraction": nested_loco_summary.get("stability_fraction", ""),
            "notes": concordance_note,
        }
    )
    concordance_summary_fieldnames = [
        "contrast",
        "status",
        "n_genes_indirect_meta",
        "n_genes_mega",
        "n_genes_overlap",
        "n_gold",
        "n_silver",
        "n_bronze",
        "signature_gene_count",
        "signature_overlap_count",
        "signature_gold_count",
        "signature_readiness_status",
        "signature_readiness_reason",
        "upstream_meta_status",
        "upstream_meta_reason",
        "external_validation_status",
        "external_validation_reason",
        "readiness_status",
        "readiness_reason",
        "nested_loco_status",
        "nested_loco_reason",
        "nested_loco_effect_concordance",
        "nested_loco_stability_fraction",
        "notes",
    ]
    write_tsv(
        concordance_summary_file,
        fieldnames=concordance_summary_fieldnames,
        rows=concordance_summary_rows,
    )
    robustness_rows = list(concordance_rows)
    robustness_summary_rows = [dict(row) for row in concordance_summary_rows]
    robustness_fieldnames = [
        "gene_id",
        "in_signature",
        "indirect_effect",
        "indirect_meta_fdr",
        "mega_effect",
        "mega_fdr",
        "concordance_tier",
        "nested_loco_full_meta_effect",
        "nested_loco_full_meta_fdr",
        "nested_loco_direction_flip_any",
        "nested_loco_max_abs_delta_effect",
        "nested_loco_support_fraction",
        "nested_loco_stability_label",
        "nested_loco_direction_concordant",
        "nested_loco_robustness_pass",
        "robustness_metric_type",
        "evidence_scope",
    ]
    if nested_loco_status == "completed":
        nested_pass = sum(1 for row in nested_loco_rows if row.get("robustness_pass") == "true")
        nested_direction_ok = sum(
            1 for row in nested_loco_rows if row.get("effect_direction_concordant") == "true"
        )
        nested_flagged = max(len(nested_loco_rows) - nested_pass, 0)
        robustness_rows = []
        for row in nested_loco_rows:
            robustness_rows.append(
                {
                    "gene_id": row.get("gene_id", ""),
                    "in_signature": row.get("in_signature", ""),
                    "indirect_effect": row.get("full_meta_effect", ""),
                    "indirect_meta_fdr": row.get("full_meta_fdr", ""),
                    "mega_effect": "",
                    "mega_fdr": "",
                    "concordance_tier": (
                        "NESTED_LOCO_PASS" if row.get("robustness_pass") == "true" else "NESTED_LOCO_FLAG"
                    ),
                    "nested_loco_full_meta_effect": row.get("full_meta_effect", ""),
                    "nested_loco_full_meta_fdr": row.get("full_meta_fdr", ""),
                    "nested_loco_direction_flip_any": row.get("direction_flip_any", ""),
                    "nested_loco_max_abs_delta_effect": row.get("max_abs_delta_effect", ""),
                    "nested_loco_support_fraction": row.get("loo_support_fraction", ""),
                    "nested_loco_stability_label": row.get("signature_stability_label", ""),
                    "nested_loco_direction_concordant": row.get("effect_direction_concordant", ""),
                    "nested_loco_robustness_pass": row.get("robustness_pass", ""),
                    "robustness_metric_type": "nested_loco_effect_direction_stability",
                    "evidence_scope": "internal_nested_loco_robustness",
                }
            )
        robustness_summary = dict(concordance_summary_rows[0])
        robustness_summary.update(
            {
                "status": "ok_nested_loco",
                "n_genes_overlap": str(len(nested_loco_rows)),
                "n_gold": str(nested_pass),
                "n_silver": str(max(nested_direction_ok - nested_pass, 0)),
                "n_bronze": str(nested_flagged),
                "signature_overlap_count": str(len(nested_loco_rows)),
                "signature_gold_count": str(nested_pass),
                "notes": "Nested LOCO effect-direction/stability robustness; no corrected mega-DE result available.",
            }
        )
        robustness_summary_rows = [robustness_summary]
    write_tsv(
        robustness_concordance_file,
        fieldnames=robustness_fieldnames,
        rows=robustness_rows,
    )
    write_tsv(
        robustness_concordance_summary_file,
        fieldnames=concordance_summary_fieldnames,
        rows=robustness_summary_rows,
    )

    write_tsv(
        readiness_file,
        fieldnames=["stage", "status", "reason", "detail"],
        rows=[
            {
                "stage": "signature_upstream",
                "status": signature_readiness_status,
                "reason": signature_readiness_reason,
                "detail": signature_readiness_detail,
            },
            {
                "stage": "meta_upstream",
                "status": upstream_meta_status,
                "reason": upstream_meta_reason,
                "detail": upstream_meta_detail,
            },
            {
                "stage": "validation_concordance",
                "status": validation_readiness_status,
                "reason": validation_readiness_reason,
                "detail": validation_readiness_detail,
            },
            {
                "stage": "nested_loco_robustness",
                "status": nested_loco_status,
                "reason": nested_loco_reason,
                "detail": nested_loco_detail,
            },
            {
                "stage": "external_validation",
                "status": external_validation_status,
                "reason": external_validation_reason,
                "detail": external_validation_detail,
            },
        ],
    )

    # ---------- TCGA Survival Validation ----------
    tcga_survival_file = out_root / "validation_tcga_survival.tsv"
    tcga_survival_rows: list[dict[str, str]] = []
    if tcga_projection_dir.exists():
        for stats_path in sorted(tcga_projection_dir.glob("*_survival_stats.tsv")):
            rows = read_tsv(stats_path)
            for row in rows:
                tcga_survival_rows.append(
                    {
                        "project": row.get("project", stats_path.stem.replace("_survival_stats", "")),
                        "n_samples": row.get("n_samples", ""),
                        "hazard_ratio": row.get("hazard_ratio", ""),
                        "lower_95_ci": row.get("lower_95_ci", ""),
                        "upper_95_ci": row.get("upper_95_ci", ""),
                        "p_value": row.get("p_value", ""),
                        "status": "ok",
                        "source_file": str(stats_path),
                    }
                )
    if not tcga_survival_rows:
        tcga_survival_rows.append(
            {
                "project": "",
                "n_samples": "",
                "hazard_ratio": "",
                "lower_95_ci": "",
                "upper_95_ci": "",
                "p_value": "",
                "status": "missing_survival_outputs",
                "source_file": str(tcga_projection_dir),
            }
        )
    write_tsv(
        tcga_survival_file,
        fieldnames=[
            "project",
            "n_samples",
            "hazard_ratio",
            "lower_95_ci",
            "upper_95_ci",
            "p_value",
            "status",
            "source_file",
        ],
        rows=tcga_survival_rows,
    )

    # ---------- Leakage Guard ----------
    leakage_file = out_root / "validation_leakage_guard.tsv"
    leakage_overlap_file = out_root / "validation_leakage_overlap_samples.tsv"
    discovery_ids = set()
    if sample_manifest_path.exists():
        discovery_ids = {r.get("sample_id", "") for r in read_tsv(sample_manifest_path) if r.get("sample_id", "")}

    tcga_inputs = []
    if tcga_projection_dir.exists():
        tcga_inputs = sorted(tcga_projection_dir.glob("*_survival_input.tsv"))
    tcga_ids = set()
    overlap_rows: list[dict[str, str]] = []
    for input_path in tcga_inputs:
        project = input_path.stem.replace("_survival_input", "")
        for row in read_tsv(input_path):
            sid = row.get("sample_id", "")
            if not sid:
                continue
            tcga_ids.add(sid)
            if sid in discovery_ids:
                overlap_rows.append(
                    {
                        "sample_id": sid,
                        "project": project,
                        "source_file": str(input_path),
                    }
                )

    write_tsv(
        leakage_overlap_file,
        fieldnames=["sample_id", "project", "source_file"],
        rows=overlap_rows,
    )
    leakage_status = "pass" if not overlap_rows else "fail"
    write_tsv(
        leakage_file,
        fieldnames=[
            "check_name",
            "status",
            "n_discovery_samples",
            "n_tcga_samples",
            "n_overlap",
            "notes",
        ],
        rows=[
            {
                "check_name": "discovery_vs_tcga_sample_id_overlap",
                "status": leakage_status,
                "n_discovery_samples": str(len(discovery_ids)),
                "n_tcga_samples": str(len(tcga_ids)),
                "n_overlap": str(len(overlap_rows)),
                "notes": "No discovery sample_id should appear in TCGA survival inputs.",
            }
        ],
    )

    external_validation_file = out_root / "validation_external_holdout.tsv"
    write_tsv(
        external_validation_file,
        fieldnames=[
            "stage",
            "status",
            "reason",
            "detail",
            "source_file",
            "n_rows",
            "n_valid_auc",
            "n_valid_effect_concordance",
            "auc_mean",
            "auc_min",
            "auc_max",
            "effect_concordance_mean",
            "effect_concordance_min",
            "effect_concordance_max",
        ],
        rows=[
            {
                "stage": "external_validation",
                "status": external_validation_status,
                "reason": external_validation_reason,
                "detail": external_validation_detail,
                "source_file": str(heldout_evaluation_path) if heldout_evaluation_path else "",
                "n_rows": str(len(external_rows)),
                "n_valid_auc": str(len(external_auc_vals)),
                "n_valid_effect_concordance": str(len(external_effect_vals)),
                "auc_mean": f"{auc_mean:.6g}" if math.isfinite(auc_mean) else "",
                "auc_min": f"{auc_min:.6g}" if math.isfinite(auc_min) else "",
                "auc_max": f"{auc_max:.6g}" if math.isfinite(auc_max) else "",
                "effect_concordance_mean": (
                    f"{effect_concordance_mean:.6g}" if math.isfinite(effect_concordance_mean) else ""
                ),
                "effect_concordance_min": (
                    f"{effect_concordance_min:.6g}" if math.isfinite(effect_concordance_min) else ""
                ),
                "effect_concordance_max": (
                    f"{effect_concordance_max:.6g}" if math.isfinite(effect_concordance_max) else ""
                ),
            }
        ],
    )

    # ---------- Summary ----------
    summary_file = out_root / "validation_summary.md"
    summary_lines = [
        "# Internal Robustness & Prognostic Context Summary",
        "",
        f"- contrast: {contrast}",
        f"- signature_file: {signature_path}",
        f"- signature_genes: {signature_n}",
        f"- signature_readiness_status: {signature_readiness_status}",
        f"- signature_readiness_reason: {signature_readiness_reason}",
        f"- upstream_meta_status: {upstream_meta_status}",
        f"- upstream_meta_reason: {upstream_meta_reason}",
        f"- external_validation_status: {external_validation_status}",
        f"- external_validation_reason: {external_validation_reason}",
        f"- validation_readiness_status: {validation_readiness_status}",
        f"- validation_readiness_reason: {validation_readiness_reason}",
        f"- concordance_status: {concordance_status} (internal same-sample cross-method robustness, not external validation)",
        f"- nested_loco_status: {nested_loco_status}",
        f"- nested_loco_reason: {nested_loco_reason}",
        (
            f"- nested_loco_effect_concordance: "
            f"{nested_loco_summary.get('effect_concordance', '')}"
        ),
        (
            f"- nested_loco_stability_fraction: "
            f"{nested_loco_summary.get('stability_fraction', '')}"
        ),
        "- nested_loco_framing: internal nested LOCO robustness, not external validation",
        f"- tcga_survival_rows: {sum(1 for r in tcga_survival_rows if r.get('status') == 'ok')}",
        "- tcga_framing: prognostic context only (non-ICB-treated cohorts)",
        f"- leakage_status: {leakage_status}",
        "",
        "## Artifacts",
        "",
        f"- {concordance_file}",
        f"- {concordance_summary_file}",
        f"- {robustness_concordance_file}",
        f"- {robustness_concordance_summary_file}",
        f"- {nested_loco_file}",
        f"- {nested_loco_summary_file}",
        f"- {readiness_file}",
        f"- {tcga_survival_file}",
        f"- {leakage_file}",
        f"- {leakage_overlap_file}",
        f"- {external_validation_file}",
    ]
    summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    repro_dir = out_root / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)
    repro_commands = repro_dir / "commands.sh"
    repro_commands.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "python -m pipeline.cli validate run \\",
                f"  --signature {signature_path} \\",
                f"  --results-root {results_root or ''} \\",
                f"  --contrast {contrast} \\",
                f"  --indirect-meta {indirect_meta_path} \\",
                f"  --mega-results {mega_results_path} \\",
                f"  --mega-concordance {mega_concordance_path} \\",
                f"  --meta-loco-summary {meta_loco_summary_path} \\",
                f"  --nested-loco-evaluation {nested_loco_input_path} \\",
                f"  --tcga-projection {tcga_projection_dir} \\",
                f"  --heldout-evaluation {heldout_evaluation_path} \\",
                f"  --sample-manifest {sample_manifest_path} \\",
                f"  --out {out_root}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_env = repro_dir / "environment.yml"
    repro_env.write_text(
        "\n".join(
            [
                "name: rnaseq-validate-run",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                f"  - python={sys.version_info.major}.{sys.version_info.minor}",
                "  - pandas",
                "  - numpy",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_checksums = repro_dir / "checksums.sha256"
    checksum_targets = [
        concordance_file,
        concordance_summary_file,
        robustness_concordance_file,
        robustness_concordance_summary_file,
        nested_loco_file,
        nested_loco_summary_file,
        readiness_file,
        tcga_survival_file,
        leakage_file,
        leakage_overlap_file,
        external_validation_file,
        summary_file,
    ]
    checksum_lines: list[str] = []
    for target in checksum_targets:
        if not target.exists():
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {target}")
    repro_checksums.write_text(
        "\n".join(checksum_lines) + ("\n" if checksum_lines else ""),
        encoding="utf-8",
    )

    outputs = [
        concordance_file,
        concordance_summary_file,
        robustness_concordance_file,
        robustness_concordance_summary_file,
        nested_loco_file,
        nested_loco_summary_file,
        readiness_file,
        tcga_survival_file,
        leakage_file,
        leakage_overlap_file,
        external_validation_file,
        summary_file,
        repro_commands,
        repro_env,
        repro_checksums,
    ]
    _mark_run(args, "validate run", outputs)
    print(f"Wrote validation outputs under {out_root}")
    return 0


def _is_treatment_column(col_name: str) -> bool:
    name = (col_name or "").strip().lower()
    if not name:
        return False
    include_hints = (
        "treatment",
        "therapy",
        "drug",
        "pharmaceutical",
        "radiation",
        "neoadjuvant",
        "adjuvant",
        "immunotherapy",
        "chemotherapy",
        "hormone",
    )
    exclude_hints = (
        "days_to",
        "os.time",
        "pfs.time",
        "dss.time",
        "vital_status",
        "age",
        "gender",
        "sex",
        "race",
        "ethnicity",
        "stage",
        "grade",
    )
    return any(h in name for h in include_hints) and not any(h in name for h in exclude_hints)


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    txt = str(value).strip().lower()
    if txt in {"", "nan", "na", "n/a", "null", "none", "[not available]", "not reported", "unknown"}:
        return ""
    return txt


def _infer_treatment_any_flag(row: dict[str, object], treatment_cols: list[str]) -> tuple[str, str]:
    if not treatment_cols:
        return "NA", "no_treatment_columns"

    positive_hits: list[str] = []
    negative_hits: list[str] = []
    for col in treatment_cols:
        value = _normalize_text(row.get(col, ""))
        if not value:
            continue

        if (
            re.search(r"\b(no|false|untreated|treatment[-\s]?naive|no prior)\b", value)
            and not re.search(r"\byes\b", value)
        ):
            negative_hits.append(f"{col}={value}")
            continue
        if re.fullmatch(r"(0|n|no|false)", value):
            negative_hits.append(f"{col}={value}")
            continue
        if re.fullmatch(r"(1|y|yes|true)", value):
            positive_hits.append(f"{col}={value}")
            continue
        if re.search(
            r"\b(treated|received|prior|adjuvant|neoadjuvant|immunotherapy|chemotherapy|radiation|pharmaceutical)\b",
            value,
        ):
            positive_hits.append(f"{col}={value}")
            continue

    if positive_hits:
        return "1", "; ".join(positive_hits[:5])
    if negative_hits:
        return "0", "; ".join(negative_hits[:5])
    return "NA", "no_interpretable_treatment_values"


def _load_expression_sample_ids(expr_path: Path) -> set[str]:
    if not expr_path.exists():
        return set()
    opener = gzip.open if str(expr_path).endswith(".gz") else open
    with opener(expr_path, "rt", encoding="utf-8", errors="replace") as fh:
        header = fh.readline().rstrip("\n").split("\t")
    if len(header) <= 1:
        return set()
    return {tok.strip() for tok in header[1:] if tok.strip()}


def _infer_case_id(sample_id: str) -> str:
    sid = (sample_id or "").strip()
    m = re.match(r"^(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", sid, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return sid


def _pick_first_value(row: dict[str, object], candidates: list[str]) -> str:
    lower_map = {str(k).lower(): k for k in row.keys()}
    for cand in candidates:
        src_col = lower_map.get(cand.lower())
        if src_col is None:
            continue
        val = row.get(src_col, "")
        txt = "" if val is None else str(val).strip()
        if txt and txt.lower() not in {"nan", "na", "n/a", "null", "none"}:
            return txt
    return ""


def _canonical_geo_cancer_group(cancer_type: str) -> str:
    text = (cancer_type or "").strip().lower()
    if "melanoma" in text:
        return "Melanoma"
    if "non-small cell lung" in text or "non small-cell lung" in text or text == "lung cancer":
        return "NSCLC"
    if "head and neck squamous cell carcinoma" in text:
        return "HNSCC"
    if "hepatocellular carcinoma" in text:
        return "HCC"
    if "renal cell carcinoma" in text:
        return "RCC"
    if "stomach adenocarcinoma" in text:
        return "Stomach adenocarcinoma"
    if "glioblastoma" in text:
        return "Glioblastoma"
    return ""


def cmd_tcga_naive_map(args: argparse.Namespace) -> int:
    sample_manifest = Path(args.sample_manifest)
    project_registry = Path(args.project_registry)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if not sample_manifest.exists():
        raise RuntimeError(f"Missing sample manifest: {sample_manifest}")
    if not project_registry.exists():
        raise RuntimeError(f"Missing project registry: {project_registry}")

    cohort_rows = read_tsv(sample_manifest)
    registry_rows = read_tsv(project_registry)
    eligible_projects = [r for r in registry_rows if parse_bool(r.get("analysis_include_flag", "1"))]

    project_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible_projects:
        group = (row.get("matched_geo_group") or "").strip()
        if not group:
            continue
        project_by_group[group].append(row)

    for group in project_by_group:
        project_by_group[group].sort(key=lambda r: int((r.get("priority") or "999").strip() or "999"))

    cohort_to_cancer: dict[str, str] = {}
    for row in cohort_rows:
        cohort_id = (row.get("cohort_id") or "").strip()
        if not cohort_id:
            continue
        if cohort_id not in cohort_to_cancer:
            cohort_to_cancer[cohort_id] = (row.get("cancer_type") or "").strip()

    mapping_rows: list[dict[str, str]] = []
    unmapped = 0
    for cohort_id, cancer_type in sorted(cohort_to_cancer.items()):
        group = _canonical_geo_cancer_group(cancer_type)
        matched = project_by_group.get(group, [])
        if not matched:
            unmapped += 1
            mapping_rows.append(
                {
                    "cohort_id": cohort_id,
                    "geo_cancer_type": cancer_type,
                    "tcga_project": "",
                    "tcga_cancer_type": "",
                    "mapping_basis": "unmapped",
                    "mapping_confidence": "low",
                    "include_flag": "0",
                    "notes": "No eligible TCGA project for cancer group.",
                }
            )
            continue

        for proj in matched:
            priority = int((proj.get("priority") or "999").strip() or "999")
            confidence = "high" if priority == 1 else "moderate"
            mapping_rows.append(
                {
                    "cohort_id": cohort_id,
                    "geo_cancer_type": cancer_type,
                    "tcga_project": proj.get("tcga_project", ""),
                    "tcga_cancer_type": proj.get("tcga_cancer_type", ""),
                    "mapping_basis": f"group_rule:{group}",
                    "mapping_confidence": confidence,
                    "include_flag": "1",
                    "notes": "",
                }
            )

    mapping_file = out_root / "geo_tcga_cancer_mapping.tsv"
    summary_file = out_root / "geo_tcga_cancer_mapping_summary.tsv"

    write_tsv(
        mapping_file,
        fieldnames=[
            "cohort_id",
            "geo_cancer_type",
            "tcga_project",
            "tcga_cancer_type",
            "mapping_basis",
            "mapping_confidence",
            "include_flag",
            "notes",
        ],
        rows=mapping_rows,
    )
    write_tsv(
        summary_file,
        fieldnames=[
            "n_unique_cohorts",
            "n_mapping_rows",
            "n_unmapped_cohorts",
            "n_projects_available",
        ],
        rows=[
            {
                "n_unique_cohorts": str(len(cohort_to_cancer)),
                "n_mapping_rows": str(len(mapping_rows)),
                "n_unmapped_cohorts": str(unmapped),
                "n_projects_available": str(len(eligible_projects)),
            }
        ],
    )

    _mark_run(args, "tcga naive-map", [mapping_file, summary_file])
    print(f"Wrote TCGA naive-map outputs to {out_root}")
    return 0


def cmd_tcga_naive_manifest(args: argparse.Namespace) -> int:
    try:
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tcga naive-manifest requires pandas.") from exc

    tcga_map_path = Path(args.tcga_map)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if not tcga_map_path.exists():
        raise RuntimeError(f"Missing TCGA map file: {tcga_map_path}")

    map_rows = read_tsv(tcga_map_path)
    manifest_rows: list[dict[str, str]] = []
    clinical_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    status_rows: list[dict[str, str]] = []

    for row in map_rows:
        project = row.get("project", "TCGA-UNKNOWN")
        expr_path = Path(row.get("local_expression_path", ""))
        surv_path = Path(row.get("local_survival_path", ""))

        if not surv_path.exists():
            status_rows.append(
                {
                    "stage": "tcga_naive_manifest",
                    "project": project,
                    "status": "blocked",
                    "reason": "missing_survival_file",
                    "detail": str(surv_path),
                }
            )
            summary_rows.append(
                {
                    "project": project,
                    "n_survival_rows": "0",
                    "n_naive": "0",
                    "n_treated": "0",
                    "n_unknown_treatment": "0",
                    "n_include_primary": "0",
                    "n_missing_rna": "0",
                    "status": "blocked_missing_survival_file",
                }
            )
            continue

        surv_df = pd.read_csv(surv_path, sep="\t")
        if surv_df.empty:
            status_rows.append(
                {
                    "stage": "tcga_naive_manifest",
                    "project": project,
                    "status": "blocked",
                    "reason": "empty_survival_file",
                    "detail": str(surv_path),
                }
            )
            summary_rows.append(
                {
                    "project": project,
                    "n_survival_rows": "0",
                    "n_naive": "0",
                    "n_treated": "0",
                    "n_unknown_treatment": "0",
                    "n_include_primary": "0",
                    "n_missing_rna": "0",
                    "status": "blocked_empty_survival_file",
                }
            )
            continue

        sample_col_candidates = ["sample_id", "sample", "submitter_id", "barcode", "bcr_patient_barcode"]
        lower_cols = {str(c).lower(): c for c in surv_df.columns}
        sample_col = None
        for cand in sample_col_candidates:
            if cand in lower_cols:
                sample_col = lower_cols[cand]
                break
        if sample_col is None:
            sample_col = surv_df.columns[0]
        surv_df = surv_df.rename(columns={sample_col: "sample_id"})
        surv_df = surv_df[surv_df["sample_id"].notna()].copy()
        surv_df["sample_id"] = surv_df["sample_id"].astype(str).str.strip()
        surv_df = surv_df[surv_df["sample_id"] != ""]

        treatment_cols = [c for c in surv_df.columns if c != "sample_id" and _is_treatment_column(str(c))]
        expr_ids = _load_expression_sample_ids(expr_path) if expr_path.exists() else set()

        n_naive = 0
        n_treated = 0
        n_unknown = 0
        n_include = 0
        n_missing_rna = 0

        for record in surv_df.to_dict(orient="records"):
            sample_id = str(record.get("sample_id", "")).strip()
            if not sample_id:
                continue

            treatment_any_flag, treatment_evidence = _infer_treatment_any_flag(record, treatment_cols)
            if treatment_any_flag == "0":
                naive_flag = "1"
                n_naive += 1
            elif treatment_any_flag == "1":
                naive_flag = "0"
                n_treated += 1
            else:
                naive_flag = "NA"
                n_unknown += 1

            if expr_path.exists():
                if expr_ids:
                    rna_available_flag = "1" if sample_id in expr_ids else "0"
                else:
                    rna_available_flag = "1"
            else:
                rna_available_flag = "0"
            if rna_available_flag != "1":
                n_missing_rna += 1

            survival_available_flag = "1"
            include_primary = "1" if naive_flag == "1" and rna_available_flag == "1" else "0"
            if include_primary == "1":
                n_include += 1

            if naive_flag == "0":
                exclude_reason = "treated"
            elif naive_flag == "NA":
                exclude_reason = "missing_treatment"
            elif rna_available_flag != "1":
                exclude_reason = "missing_rna"
            else:
                exclude_reason = ""

            manifest_rows.append(
                {
                    "project": project,
                    "case_id": _infer_case_id(sample_id),
                    "sample_id": sample_id,
                    "naive_flag": naive_flag,
                    "naive_rule_version": "v1_keyword_heuristic",
                    "treatment_any_flag": treatment_any_flag,
                    "treatment_evidence": treatment_evidence,
                    "rna_available_flag": rna_available_flag,
                    "survival_available_flag": survival_available_flag,
                    "include_primary_projection": include_primary,
                    "exclude_reason": exclude_reason,
                }
            )

            clinical_rows.append(
                {
                    "project": project,
                    "case_id": _infer_case_id(sample_id),
                    "sample_id": sample_id,
                    "age_at_index": _pick_first_value(record, ["age_at_index", "age_at_diagnosis", "age", "age_at_initial_pathologic_diagnosis"]),
                    "sex": _pick_first_value(record, ["sex", "gender"]),
                    "race": _pick_first_value(record, ["race"]),
                    "ethnicity": _pick_first_value(record, ["ethnicity"]),
                    "vital_status": _pick_first_value(record, ["vital_status", "overall_survival_status"]),
                    "days_to_death": _pick_first_value(record, ["days_to_death"]),
                    "days_to_last_follow_up": _pick_first_value(record, ["days_to_last_follow_up", "days_to_last_followup", "days_to_last_known_alive"]),
                    "ajcc_pathologic_stage": _pick_first_value(record, ["ajcc_pathologic_stage", "pathologic_stage", "ajcc_stage"]),
                    "tumor_grade": _pick_first_value(record, ["tumor_grade", "grade", "histological_grade"]),
                    "smoking_status": _pick_first_value(record, ["tobacco_smoking_status", "smoking_status", "smoking_history"]),
                    "pack_years_smoked": _pick_first_value(record, ["pack_years_smoked", "pack_years", "tobacco_smoking_pack_years_smoked"]),
                    "alcohol_history": _pick_first_value(record, ["alcohol_history", "alcohol_intensity", "alcohol_consumption"]),
                    "molecular_subtype": _pick_first_value(record, ["molecular_subtype", "subtype", "integrated_subtype", "msi_status", "hpv_status", "braf_status", "egfr_status", "kras_status"]),
                }
            )

        status_rows.append(
            {
                "stage": "tcga_naive_manifest",
                "project": project,
                "status": "completed",
                "reason": "",
                "detail": f"rows={len(surv_df)}; treatment_cols={len(treatment_cols)}",
            }
        )
        summary_rows.append(
            {
                "project": project,
                "n_survival_rows": str(len(surv_df)),
                "n_naive": str(n_naive),
                "n_treated": str(n_treated),
                "n_unknown_treatment": str(n_unknown),
                "n_include_primary": str(n_include),
                "n_missing_rna": str(n_missing_rna),
                "status": "ok",
            }
        )

    manifest_file = out_root / "tcga_naive_patient_manifest.tsv"
    clinical_file = out_root / "tcga_clinical_flat.tsv"
    summary_file = out_root / "tcga_naive_manifest_summary.tsv"
    status_file = out_root / "tcga_naive_manifest_status.tsv"

    write_tsv(
        manifest_file,
        fieldnames=[
            "project",
            "case_id",
            "sample_id",
            "naive_flag",
            "naive_rule_version",
            "treatment_any_flag",
            "treatment_evidence",
            "rna_available_flag",
            "survival_available_flag",
            "include_primary_projection",
            "exclude_reason",
        ],
        rows=manifest_rows,
    )
    write_tsv(
        clinical_file,
        fieldnames=[
            "project",
            "case_id",
            "sample_id",
            "age_at_index",
            "sex",
            "race",
            "ethnicity",
            "vital_status",
            "days_to_death",
            "days_to_last_follow_up",
            "ajcc_pathologic_stage",
            "tumor_grade",
            "smoking_status",
            "pack_years_smoked",
            "alcohol_history",
            "molecular_subtype",
        ],
        rows=clinical_rows,
    )
    write_tsv(
        summary_file,
        fieldnames=[
            "project",
            "n_survival_rows",
            "n_naive",
            "n_treated",
            "n_unknown_treatment",
            "n_include_primary",
            "n_missing_rna",
            "status",
        ],
        rows=summary_rows,
    )
    write_tsv(
        status_file,
        fieldnames=["stage", "project", "status", "reason", "detail"],
        rows=status_rows,
    )

    outputs = [manifest_file, clinical_file, summary_file, status_file]
    _mark_run(args, "tcga naive-manifest", outputs)
    print(f"Wrote TCGA naive-manifest outputs to {out_root}")
    return 0


def _bh_fdr_epi(pvals: list[float]) -> list[float]:
    if not pvals:
        return []
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    out = [0.0] * n
    prev = 1.0
    for rank_rev, idx in enumerate(reversed(order), start=1):
        rank = n - rank_rev + 1
        val = min(prev, pvals[idx] * n / rank)
        prev = val
        out[idx] = min(1.0, max(0.0, val))
    return out


def _tcga_patient_barcode(sample_id: str) -> str:
    parts = (sample_id or "").strip().split("-")
    if len(parts) >= 3:
        return "-".join(parts[:3])
    return (sample_id or "").strip()


def _read_layer4_gene_sets_from_registry(registry_path: Path) -> list[dict[str, object]]:
    gene_sets: list[dict[str, object]] = []
    for row in read_tsv(registry_path):
        if row.get("enabled", "true").strip().lower() not in {"true", "1", "yes"}:
            continue
        if row.get("gene_set_layer", "").strip() != "L4_EPIGENETIC":
            continue
        gmt_raw = row.get("gmt_path", "").strip()
        if not gmt_raw:
            continue
        gmt_path = Path(gmt_raw).expanduser()
        if not gmt_path.is_absolute():
            gmt_path = Path.cwd() / gmt_path
        if not gmt_path.exists():
            raise RuntimeError(f"Layer 4 GMT path does not exist: {gmt_path}")
        with gmt_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = [part.strip() for part in line.rstrip("\n").split("\t") if part.strip()]
                if len(parts) < 3:
                    continue
                gene_sets.append(
                    {
                        "gene_set": parts[0],
                        "description": parts[1],
                        "genes": [g.upper() for g in parts[2:]],
                        "gmt_path": str(gmt_path),
                    }
                )
    if not gene_sets:
        raise RuntimeError(f"No enabled L4_EPIGENETIC gene sets found in {registry_path}")
    return gene_sets


def cmd_tcga_epigenetic_layer(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
        from scipy.stats import kruskal
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tcga epigenetic-layer requires numpy, pandas, and scipy.") from exc

    expression_manifest = Path(args.expression_manifest)
    subtype_manifest = Path(args.subtype_manifest)
    gene_set_registry = Path(getattr(args, "gene_set_registry", "configs/immune_gene_sets_registry.tsv"))
    gene_id_mapping = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if not expression_manifest.exists():
        raise RuntimeError(f"Missing TCGA expression manifest: {expression_manifest}")
    if not subtype_manifest.exists():
        raise RuntimeError(f"Missing TCGA subtype manifest: {subtype_manifest}")

    min_samples = int(getattr(args, "min_samples", 3))
    min_subtype_samples = int(getattr(args, "min_subtype_samples", 1))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))

    gene_sets = _read_layer4_gene_sets_from_registry(gene_set_registry)
    expr_manifest_rows = read_tsv(expression_manifest)
    subtype_rows = read_tsv(subtype_manifest)

    subtype_lookup: dict[str, dict[str, str]] = defaultdict(dict)
    for row in subtype_rows:
        project = (
            row.get("tcga_project", "")
            or row.get("project", "")
            or row.get("cancer_project", "")
        ).strip()
        sample_id = (
            row.get("sample_id", "")
            or row.get("barcode", "")
            or row.get("patient_id", "")
            or row.get("case_id", "")
        ).strip()
        subtype = (
            row.get("immune_subtype", "")
            or row.get("thorsson_immune_subtype", "")
            or row.get("subtype", "")
            or row.get("ImmuneSubtype", "")
        ).strip()
        if project and sample_id and subtype:
            subtype_lookup[project][sample_id] = subtype
            subtype_lookup[project][_tcga_patient_barcode(sample_id)] = subtype

    score_rows: list[dict[str, str]] = []
    validation_rows: list[dict[str, str]] = []

    for manifest_row in expr_manifest_rows:
        project = (
            manifest_row.get("tcga_project", "")
            or manifest_row.get("project", "")
            or manifest_row.get("cancer_project", "")
        ).strip()
        expr_raw = (
            manifest_row.get("expression_path", "")
            or manifest_row.get("input_expression_path", "")
            or manifest_row.get("local_expression_path", "")
        ).strip()
        if not project or not expr_raw:
            continue
        expr_path = Path(expr_raw).expanduser()
        if not expr_path.is_absolute():
            expr_path = Path.cwd() / expr_path
        expr = load_expression_matrix(expr_path)
        if expr is None or expr.empty:
            for gs in gene_sets:
                validation_rows.append(
                    {
                        "gene_set": str(gs["gene_set"]),
                        "tcga_project": project,
                        "n_patients": "0",
                        "n_subtypes": "0",
                        "kw_statistic": "",
                        "p_value": "",
                        "fdr": "",
                        "input_expression_path": str(expr_path),
                        "input_subtype_path": str(subtype_manifest),
                        "status": "blocked_expression_empty",
                    }
                )
            continue

        if gene_id_mapping.exists():
            expr, _, _ = _standardize_expression_gene_ids(
                expr,
                mapping_path=gene_id_mapping,
                aggregation="mean",
            )
        expr.index = [str(idx).strip().upper() for idx in expr.index]
        expr = expr.fillna(0.0)
        try:
            is_log = float(expr.max().max()) < 50.0 and float(expr.median().median()) < 25.0
        except Exception:
            is_log = False
        expr_log = expr if is_log else np.log2(expr + 1.0)

        project_subtypes = subtype_lookup.get(project, {})
        sample_to_subtype: dict[str, str] = {}
        for sample_id in expr_log.columns:
            sample_str = str(sample_id)
            subtype = project_subtypes.get(sample_str) or project_subtypes.get(_tcga_patient_barcode(sample_str))
            if subtype:
                sample_to_subtype[sample_str] = subtype

        if not sample_to_subtype:
            for gs in gene_sets:
                validation_rows.append(
                    {
                        "gene_set": str(gs["gene_set"]),
                        "tcga_project": project,
                        "n_patients": "0",
                        "n_subtypes": "0",
                        "kw_statistic": "",
                        "p_value": "",
                        "fdr": "",
                        "input_expression_path": str(expr_path),
                        "input_subtype_path": str(subtype_manifest),
                        "status": "blocked_no_subtype_overlap",
                    }
                )
            continue

        ranks = expr_log.rank(axis=0, method="average", pct=True)
        project_validation_indices: list[int] = []
        project_pvals: list[float] = []
        for gs in gene_sets:
            gene_set = str(gs["gene_set"])
            genes = [g for g in gs["genes"] if g in ranks.index]
            if genes:
                scores = ranks.loc[genes, list(sample_to_subtype)].mean(axis=0)
            else:
                scores = pd.Series(float("nan"), index=list(sample_to_subtype), dtype=float)

            values_by_subtype: dict[str, list[float]] = defaultdict(list)
            for sample_id, subtype in sample_to_subtype.items():
                score = float(scores.loc[sample_id]) if sample_id in scores.index else float("nan")
                score_rows.append(
                    {
                        "tcga_project": project,
                        "sample_id": sample_id,
                        "patient_id": _tcga_patient_barcode(sample_id),
                        "immune_subtype": subtype,
                        "gene_set": gene_set,
                        "score": f"{score:.6f}" if np.isfinite(score) else "nan",
                        "n_genes_used": str(len(genes)),
                    }
                )
                if np.isfinite(score):
                    values_by_subtype[subtype].append(score)

            groups = [
                vals
                for vals in values_by_subtype.values()
                if len(vals) >= min_subtype_samples
            ]
            n_patients = sum(len(vals) for vals in values_by_subtype.values())
            n_subtypes = len(groups)
            status = "ok"
            kw_stat = float("nan")
            pval = float("nan")
            if len(genes) == 0:
                status = "blocked_no_gene_overlap"
            elif n_patients < min_samples or n_subtypes < 2:
                status = "blocked_insufficient_subtypes_or_samples"
            else:
                try:
                    kw_stat, pval = kruskal(*groups)
                    kw_stat = float(kw_stat)
                    pval = float(pval)
                except Exception:  # noqa: BLE001
                    status = "blocked_kruskal_failed"

            validation_rows.append(
                {
                    "gene_set": gene_set,
                    "tcga_project": project,
                    "n_patients": str(n_patients),
                    "n_subtypes": str(n_subtypes),
                    "kw_statistic": f"{kw_stat:.6g}" if np.isfinite(kw_stat) else "",
                    "p_value": f"{pval:.6g}" if np.isfinite(pval) else "",
                    "fdr": "",
                    "input_expression_path": str(expr_path),
                    "input_subtype_path": str(subtype_manifest),
                    "status": status,
                }
            )
            if status == "ok" and np.isfinite(pval):
                project_validation_indices.append(len(validation_rows) - 1)
                project_pvals.append(pval)

        if project_pvals:
            qvals = _bh_fdr_epi(project_pvals)
            for idx, qval in zip(project_validation_indices, qvals):
                validation_rows[idx]["fdr"] = f"{qval:.6g}"

    validation_file = out_root / "epigenetic_layer_tcga_validation.tsv"
    scores_file = out_root / "epigenetic_layer_tcga_scores.tsv"
    contracts_file = out_root / "tcga_epigenetic_layer_input_contracts.md"

    write_tsv(
        validation_file,
        fieldnames=[
            "gene_set",
            "tcga_project",
            "n_patients",
            "n_subtypes",
            "kw_statistic",
            "p_value",
            "fdr",
            "input_expression_path",
            "input_subtype_path",
            "status",
        ],
        rows=validation_rows,
    )
    write_tsv(
        scores_file,
        fieldnames=[
            "tcga_project",
            "sample_id",
            "patient_id",
            "immune_subtype",
            "gene_set",
            "score",
            "n_genes_used",
        ],
        rows=score_rows,
    )
    contracts_file.write_text(
        "\n".join(
            [
                "# TCGA Epigenetic Layer Input Contracts",
                "",
                "## Expression Manifest",
                "",
                "Required columns: `tcga_project` or `project`; one expression path column from `expression_path`, `input_expression_path`, or `local_expression_path`.",
                "Expression files are gene-by-sample matrices with a first gene identifier column and TCGA sample barcodes as columns.",
                "",
                "## Subtype Manifest",
                "",
                "Required columns: `tcga_project` or `project`; `sample_id` or `barcode` or `patient_id`; `immune_subtype` or `thorsson_immune_subtype` or `subtype`.",
                "Subtype labels should contain Thorsson immune subtype calls such as C1-C6.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    outputs = [validation_file, scores_file, contracts_file]
    _mark_run(args, "tcga epigenetic-layer", outputs)
    print(f"Wrote TCGA epigenetic-layer validation to {validation_file}")
    return 0


def _clean_numeric(series):
    return series.astype(str).str.strip().replace({"": None, "nan": None, "NA": None, "N/A": None, "null": None, "None": None})


def _stage_group(value: object) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    if "stage i" in text or "stage ii" in text:
        return "early_I_II"
    if "stage iii" in text or "stage iv" in text:
        return "late_III_IV"
    return text


def _shrink_categories(values, max_levels: int = 4):
    ser = values.astype(str).str.strip()
    ser = ser.replace({"": None, "nan": None, "NA": None, "N/A": None, "null": None, "None": None})
    counts = ser.value_counts(dropna=True)
    if counts.empty:
        return ser
    keep = set(counts.head(max_levels).index.tolist())
    return ser.apply(lambda x: x if x in keep else ("Other" if x is not None else None))


def cmd_tcga_epi_model(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
        from scipy.stats import chi2
        import statsmodels.formula.api as smf
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tcga epi-model requires numpy, pandas, scipy, and statsmodels.") from exc

    score_dir = Path(args.score_dir)
    naive_manifest_path = Path(args.naive_manifest)
    clinical_flat_path = Path(args.clinical_flat) if args.clinical_flat else naive_manifest_path.parent / "tcga_clinical_flat.tsv"
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if not score_dir.exists():
        raise RuntimeError(f"Missing score dir: {score_dir}")
    if not naive_manifest_path.exists():
        raise RuntimeError(f"Missing naive manifest: {naive_manifest_path}")
    if not clinical_flat_path.exists():
        raise RuntimeError(f"Missing clinical flat file: {clinical_flat_path}")

    min_samples = int(args.min_samples)

    naive_df = pd.read_csv(naive_manifest_path, sep="\t")
    clinical_df = pd.read_csv(clinical_flat_path, sep="\t")
    if "sample_id" not in naive_df.columns or "project" not in naive_df.columns:
        raise RuntimeError("naive manifest must include project and sample_id columns.")
    if "sample_id" not in clinical_df.columns or "project" not in clinical_df.columns:
        raise RuntimeError("clinical flat file must include project and sample_id columns.")

    naive_df["sample_id"] = naive_df["sample_id"].astype(str).str.strip()
    naive_df["project"] = naive_df["project"].astype(str).str.strip()
    clinical_df["sample_id"] = clinical_df["sample_id"].astype(str).str.strip()
    clinical_df["project"] = clinical_df["project"].astype(str).str.strip()

    naive_keep = naive_df[["project", "sample_id", "naive_flag", "include_primary_projection"]].drop_duplicates()
    clinical_keep = clinical_df.drop_duplicates(subset=["project", "sample_id"], keep="first")

    candidate_files = sorted(score_dir.glob("*_survival_input.tsv"))
    interaction_rows: list[dict[str, str]] = []
    diagnostics_rows: list[dict[str, str]] = []

    covariates = [
        ("demographic", "age_at_index", "numeric"),
        ("demographic", "sex", "categorical"),
        ("demographic", "race", "categorical"),
        ("demographic", "ethnicity", "categorical"),
        ("clinical_stage", "ajcc_pathologic_stage", "categorical_stage"),
        ("clinical_stage", "tumor_grade", "categorical"),
        ("exposure", "smoking_status", "categorical"),
        ("exposure", "pack_years_smoked", "numeric"),
        ("exposure", "alcohol_history", "categorical"),
        ("molecular_subtype", "molecular_subtype", "categorical"),
    ]

    if not candidate_files:
        interaction_rows.append(
            {
                "project": "",
                "endpoint": "OS",
                "signature_tier": "ALL",
                "covariate_family": "demographic",
                "covariate_name": "age_at_index",
                "interaction_term": "signature_score:age_at_index",
                "beta_interaction": "",
                "se_interaction": "",
                "p_value": "",
                "fdr": "",
                "n_samples": "0",
                "status": "blocked_no_projection_inputs",
                "notes": f"No *_survival_input.tsv files found in {score_dir}",
            }
        )
    else:
        for input_path in candidate_files:
            project = input_path.stem.replace("_survival_input", "")
            proj_df = pd.read_csv(input_path, sep="\t")
            if proj_df.empty or "sample_id" not in proj_df.columns or "signature_score" not in proj_df.columns:
                interaction_rows.append(
                    {
                        "project": project,
                        "endpoint": "OS",
                        "signature_tier": "ALL",
                        "covariate_family": "demographic",
                        "covariate_name": "age_at_index",
                        "interaction_term": "signature_score:age_at_index",
                        "beta_interaction": "",
                        "se_interaction": "",
                        "p_value": "",
                        "fdr": "",
                        "n_samples": "0",
                        "status": "blocked_invalid_projection_input",
                        "notes": f"Missing required columns in {input_path.name}",
                    }
                )
                continue

            proj_df["sample_id"] = proj_df["sample_id"].astype(str).str.strip()
            proj_df["project"] = project
            merged = (
                proj_df.merge(naive_keep, on=["project", "sample_id"], how="left", suffixes=("", "_naive"))
                .merge(clinical_keep, on=["project", "sample_id"], how="left", suffixes=("", "_clin"))
            )
            if merged.empty:
                interaction_rows.append(
                    {
                        "project": project,
                        "endpoint": "OS",
                        "signature_tier": "ALL",
                        "covariate_family": "demographic",
                        "covariate_name": "age_at_index",
                        "interaction_term": "signature_score:age_at_index",
                        "beta_interaction": "",
                        "se_interaction": "",
                        "p_value": "",
                        "fdr": "",
                        "n_samples": "0",
                        "status": "blocked_no_project_rows_after_merge",
                        "notes": "No rows left after joining naive/clinical tables.",
                    }
                )
                continue

            include_col = "include_primary_projection"
            if include_col in merged.columns:
                merged = merged[merged[include_col].astype(str).str.strip() == "1"].copy()

            endpoints = []
            for endpoint in ("OS", "PFS", "DSS"):
                if endpoint in merged.columns:
                    endpoints.append(endpoint)
            if not endpoints:
                interaction_rows.append(
                    {
                        "project": project,
                        "endpoint": "OS",
                        "signature_tier": "ALL",
                        "covariate_family": "demographic",
                        "covariate_name": "age_at_index",
                        "interaction_term": "signature_score:age_at_index",
                        "beta_interaction": "",
                        "se_interaction": "",
                        "p_value": "",
                        "fdr": "",
                        "n_samples": str(len(merged)),
                        "status": "blocked_missing_endpoints",
                        "notes": "No OS/PFS/DSS endpoint columns found in survival input.",
                    }
                )
                continue

            for endpoint in endpoints:
                work = merged.copy()
                work["event"] = pd.to_numeric(work[endpoint], errors="coerce")
                work["signature_score"] = pd.to_numeric(work["signature_score"], errors="coerce")
                work = work[work["event"].isin([0, 1])].copy()
                work = work[work["signature_score"].notna()].copy()

                if len(work) < min_samples or work["event"].nunique() < 2:
                    interaction_rows.append(
                        {
                            "project": project,
                            "endpoint": endpoint,
                            "signature_tier": "ALL",
                            "covariate_family": "demographic",
                            "covariate_name": "age_at_index",
                            "interaction_term": "signature_score:age_at_index",
                            "beta_interaction": "",
                            "se_interaction": "",
                            "p_value": "",
                            "fdr": "",
                            "n_samples": str(len(work)),
                            "status": "blocked_insufficient_samples_or_events",
                            "notes": f"min_samples={min_samples}, event_unique={work['event'].nunique()}",
                        }
                    )
                    continue

                for family, cov_name, cov_type in covariates:
                    if cov_name not in work.columns:
                        interaction_rows.append(
                            {
                                "project": project,
                                "endpoint": endpoint,
                                "signature_tier": "ALL",
                                "covariate_family": family,
                                "covariate_name": cov_name,
                                "interaction_term": f"signature_score:{cov_name}",
                                "beta_interaction": "",
                                "se_interaction": "",
                                "p_value": "",
                                "fdr": "",
                                "n_samples": str(len(work)),
                                "status": "blocked_missing_covariate",
                                "notes": "Covariate column not present.",
                            }
                        )
                        continue

                    model_df = work[["signature_score", "event", cov_name]].copy()
                    if cov_type == "numeric":
                        model_df[cov_name] = pd.to_numeric(model_df[cov_name], errors="coerce")
                    elif cov_type == "categorical_stage":
                        model_df[cov_name] = model_df[cov_name].apply(_stage_group)
                        model_df[cov_name] = _shrink_categories(model_df[cov_name], max_levels=3)
                    else:
                        model_df[cov_name] = _shrink_categories(model_df[cov_name], max_levels=4)

                    n_before = len(model_df)
                    model_df = model_df.dropna()
                    n_after = len(model_df)

                    diagnostics_rows.append(
                        {
                            "project": project,
                            "endpoint": endpoint,
                            "covariate_name": cov_name,
                            "covariate_family": family,
                            "n_before_dropna": str(n_before),
                            "n_after_dropna": str(n_after),
                            "event_rate": f"{model_df['event'].mean():.6f}" if n_after > 0 else "",
                            "n_levels": str(model_df[cov_name].nunique()) if n_after > 0 else "0",
                            "status": "ok" if n_after >= min_samples else "insufficient_after_dropna",
                            "notes": "",
                        }
                    )

                    if n_after < min_samples:
                        interaction_rows.append(
                            {
                                "project": project,
                                "endpoint": endpoint,
                                "signature_tier": "ALL",
                                "covariate_family": family,
                                "covariate_name": cov_name,
                                "interaction_term": f"signature_score:{cov_name}",
                                "beta_interaction": "",
                                "se_interaction": "",
                                "p_value": "",
                                "fdr": "",
                                "n_samples": str(n_after),
                                "status": "blocked_insufficient_after_dropna",
                                "notes": f"min_samples={min_samples}",
                            }
                        )
                        continue

                    if cov_type == "numeric":
                        if model_df[cov_name].nunique() < 2:
                            interaction_rows.append(
                                {
                                    "project": project,
                                    "endpoint": endpoint,
                                    "signature_tier": "ALL",
                                    "covariate_family": family,
                                    "covariate_name": cov_name,
                                    "interaction_term": f"signature_score:{cov_name}",
                                    "beta_interaction": "",
                                    "se_interaction": "",
                                    "p_value": "",
                                    "fdr": "",
                                    "n_samples": str(n_after),
                                    "status": "blocked_no_covariate_variation",
                                    "notes": "",
                                }
                            )
                            continue
                        formula = f"event ~ signature_score + {cov_name} + signature_score:{cov_name}"
                        term = f"signature_score:{cov_name}"
                        try:
                            fit = smf.logit(formula, data=model_df).fit(disp=0)
                            p_val = float(fit.pvalues.get(term, np.nan))
                            beta = float(fit.params.get(term, np.nan))
                            se = float(fit.bse.get(term, np.nan))
                            if not np.isfinite(p_val):
                                raise ValueError("non-finite p-value")
                            status = "ok"
                            note = ""
                        except Exception as exc:  # noqa: BLE001
                            p_val = np.nan
                            beta = np.nan
                            se = np.nan
                            status = "model_failed"
                            note = str(exc)
                    else:
                        if model_df[cov_name].nunique() < 2:
                            interaction_rows.append(
                                {
                                    "project": project,
                                    "endpoint": endpoint,
                                    "signature_tier": "ALL",
                                    "covariate_family": family,
                                    "covariate_name": cov_name,
                                    "interaction_term": f"signature_score:C({cov_name})",
                                    "beta_interaction": "",
                                    "se_interaction": "",
                                    "p_value": "",
                                    "fdr": "",
                                    "n_samples": str(n_after),
                                    "status": "blocked_no_covariate_variation",
                                    "notes": "",
                                }
                            )
                            continue
                        full_formula = f"event ~ signature_score + C({cov_name}) + signature_score:C({cov_name})"
                        red_formula = f"event ~ signature_score + C({cov_name})"
                        try:
                            full_fit = smf.logit(full_formula, data=model_df).fit(disp=0)
                            red_fit = smf.logit(red_formula, data=model_df).fit(disp=0)
                            lr = 2.0 * (full_fit.llf - red_fit.llf)
                            df_diff = int(max(full_fit.df_model - red_fit.df_model, 1))
                            p_val = float(chi2.sf(lr, df_diff))
                            beta = np.nan
                            se = np.nan
                            status = "ok"
                            note = f"global_interaction_lr_test_df={df_diff}"
                        except Exception as exc:  # noqa: BLE001
                            p_val = np.nan
                            beta = np.nan
                            se = np.nan
                            status = "model_failed"
                            note = str(exc)

                    interaction_rows.append(
                        {
                            "project": project,
                            "endpoint": endpoint,
                            "signature_tier": "ALL",
                            "covariate_family": family,
                            "covariate_name": cov_name,
                            "interaction_term": f"signature_score:{cov_name}",
                            "beta_interaction": "" if not np.isfinite(beta) else f"{beta:.6g}",
                            "se_interaction": "" if not np.isfinite(se) else f"{se:.6g}",
                            "p_value": "" if not np.isfinite(p_val) else f"{p_val:.6g}",
                            "fdr": "",
                            "n_samples": str(n_after),
                            "status": status,
                            "notes": note,
                        }
                    )

    tested_idx = [i for i, r in enumerate(interaction_rows) if r.get("status") == "ok" and r.get("p_value")]
    tested_pvals = []
    for i in tested_idx:
        try:
            tested_pvals.append(float(interaction_rows[i]["p_value"]))
        except Exception:  # noqa: BLE001
            tested_pvals.append(np.nan)
    finite_mask = [np.isfinite(v) for v in tested_pvals]
    finite_vals = [v for v, keep in zip(tested_pvals, finite_mask) if keep]
    finite_fdr = _bh_fdr_epi(finite_vals)
    fdr_iter = iter(finite_fdr)
    for idx, keep in zip(tested_idx, finite_mask):
        if keep:
            interaction_rows[idx]["fdr"] = f"{next(fdr_iter):.6g}"

    interactions_file = out_root / "tcga_epidemiology_interactions.tsv"
    diagnostics_file = out_root / "tcga_epidemiology_model_diagnostics.tsv"
    status_file = out_root / "tcga_epidemiology_status.tsv"

    write_tsv(
        interactions_file,
        fieldnames=[
            "project",
            "endpoint",
            "signature_tier",
            "covariate_family",
            "covariate_name",
            "interaction_term",
            "beta_interaction",
            "se_interaction",
            "p_value",
            "fdr",
            "n_samples",
            "status",
            "notes",
        ],
        rows=interaction_rows,
    )
    write_tsv(
        diagnostics_file,
        fieldnames=[
            "project",
            "endpoint",
            "covariate_name",
            "covariate_family",
            "n_before_dropna",
            "n_after_dropna",
            "event_rate",
            "n_levels",
            "status",
            "notes",
        ],
        rows=diagnostics_rows,
    )

    status_rows = []
    if interaction_rows:
        by_project = defaultdict(lambda: {"ok": 0, "blocked": 0, "failed": 0})
        for r in interaction_rows:
            proj = r.get("project", "")
            st = r.get("status", "")
            if st == "ok":
                by_project[proj]["ok"] += 1
            elif st.startswith("blocked"):
                by_project[proj]["blocked"] += 1
            else:
                by_project[proj]["failed"] += 1
        for proj, counts in sorted(by_project.items()):
            status_rows.append(
                {
                    "stage": "tcga_epi_model",
                    "project": proj,
                    "status": "completed" if counts["ok"] > 0 else "blocked",
                    "reason": "ok_models_present" if counts["ok"] > 0 else "no_successful_models",
                    "detail": f"ok={counts['ok']}; blocked={counts['blocked']}; failed={counts['failed']}",
                }
            )
    write_tsv(
        status_file,
        fieldnames=["stage", "project", "status", "reason", "detail"],
        rows=status_rows,
    )

    outputs = [interactions_file, diagnostics_file, status_file]
    _mark_run(args, "tcga epi-model", outputs)
    print(f"Wrote TCGA epidemiology outputs to {out_root}")
    return 0


def _as_float_or_nan(value: object) -> float:
    try:
        if value is None:
            return float("nan")
        txt = str(value).strip()
        if txt == "":
            return float("nan")
        return float(txt)
    except Exception:  # noqa: BLE001
        return float("nan")


def _random_effects_from_log_hr(log_hr_values, se_values):
    import numpy as np
    from scipy.stats import norm

    effects = np.array(log_hr_values, dtype=float)
    ses = np.array(se_values, dtype=float)
    valid = np.isfinite(effects) & np.isfinite(ses) & (ses > 0)
    effects = effects[valid]
    ses = ses[valid]
    k = len(effects)
    if k == 0:
        return None

    w_fixed = 1.0 / (ses**2)
    mu_fixed = float(np.sum(w_fixed * effects) / np.sum(w_fixed))

    if k > 1:
        q = float(np.sum(w_fixed * (effects - mu_fixed) ** 2))
        df = k - 1
        c = float(np.sum(w_fixed) - np.sum(w_fixed**2) / np.sum(w_fixed))
        tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
        i2 = max(0.0, (q - df) / q) if q > 0 else 0.0
    else:
        q = 0.0
        tau2 = 0.0
        i2 = 0.0

    w_random = 1.0 / (ses**2 + tau2)
    mu_random = float(np.sum(w_random * effects) / np.sum(w_random))
    se_random = float((1.0 / np.sum(w_random)) ** 0.5)
    z = mu_random / se_random if se_random > 0 else 0.0
    p = float(2.0 * norm.sf(abs(z)))
    lo = float(mu_random - 1.96 * se_random)
    hi = float(mu_random + 1.96 * se_random)

    return {
        "k": k,
        "pooled_log_hr": mu_random,
        "pooled_hr": float(np.exp(mu_random)),
        "lower_95_ci": float(np.exp(lo)),
        "upper_95_ci": float(np.exp(hi)),
        "p_value": p,
        "q": q,
        "i2_percent": float(i2 * 100.0),
        "tau2": tau2,
    }


def cmd_tcga_pan_cancer(args: argparse.Namespace) -> int:
    import os
    import tempfile

    if not os.environ.get("MPLCONFIGDIR"):
        os.environ["MPLCONFIGDIR"] = str(Path(tempfile.gettempdir()) / f"matplotlib-{os.environ.get('USER', 'user')}")

    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tcga pan-cancer requires numpy and matplotlib.") from exc

    survival_dir = Path(args.survival_dir)
    epi_dir = Path(args.epi_dir) if args.epi_dir else None
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    project_registry_path = Path(args.project_registry) if args.project_registry else None
    project_to_cancer = {}
    if project_registry_path and project_registry_path.exists():
        for r in read_tsv(project_registry_path):
            project_to_cancer[r.get("tcga_project", "")] = r.get("tcga_cancer_type", "")

    summary_rows: list[dict[str, str]] = []
    heterogeneity_rows: list[dict[str, str]] = []
    status_rows: list[dict[str, str]] = []

    stats_files = sorted(survival_dir.glob("*_survival_stats.tsv")) if survival_dir.exists() else []
    if not stats_files:
        summary_rows.append(
            {
                "project": "",
                "tcga_cancer_type": "",
                "endpoint": "OS",
                "signature_tier": "ALL",
                "hazard_ratio": "",
                "lower_95_ci": "",
                "upper_95_ci": "",
                "p_value": "",
                "n_samples": "0",
                "n_events": "",
                "status": "blocked_no_survival_stats",
            }
        )
        heterogeneity_rows.append(
            {
                "endpoint": "OS",
                "signature_tier": "ALL",
                "n_projects": "0",
                "pooled_log_hr": "",
                "pooled_hr": "",
                "q_statistic": "",
                "i2_percent": "",
                "tau2": "",
                "status": "blocked_no_survival_stats",
            }
        )
        status_rows.append(
            {
                "stage": "tcga_pan_cancer",
                "project": "",
                "status": "blocked",
                "reason": "no_survival_stats_files",
                "detail": str(survival_dir),
            }
        )
    else:
        for stats_path in stats_files:
            rows = read_tsv(stats_path)
            project_from_name = stats_path.stem.replace("_survival_stats", "")
            if not rows:
                status_rows.append(
                    {
                        "stage": "tcga_pan_cancer",
                        "project": project_from_name,
                        "status": "blocked",
                        "reason": "empty_survival_stats_file",
                        "detail": str(stats_path),
                    }
                )
                continue

            for r in rows:
                project = (r.get("project") or project_from_name).strip()
                endpoint = (r.get("endpoint") or "OS").strip() or "OS"
                tier = (r.get("signature_tier") or "ALL").strip() or "ALL"
                hr = _as_float_or_nan(r.get("hazard_ratio"))
                lo = _as_float_or_nan(r.get("lower_95_ci"))
                hi = _as_float_or_nan(r.get("upper_95_ci"))
                p = _as_float_or_nan(r.get("p_value"))
                n_samples = r.get("n_samples", "")
                n_events = r.get("n_events", "")
                row_status = (r.get("status") or "").strip()
                if not row_status:
                    row_status = (
                        "ok" if np.isfinite(hr) and np.isfinite(lo) and np.isfinite(hi) and hr > 0 and lo > 0 and hi > 0
                        else "blocked_invalid_hr_or_ci"
                    )

                summary_rows.append(
                    {
                        "project": project,
                        "tcga_cancer_type": project_to_cancer.get(project, ""),
                        "endpoint": endpoint,
                        "signature_tier": tier,
                        "hazard_ratio": "" if not np.isfinite(hr) else f"{hr:.6g}",
                        "lower_95_ci": "" if not np.isfinite(lo) else f"{lo:.6g}",
                        "upper_95_ci": "" if not np.isfinite(hi) else f"{hi:.6g}",
                        "p_value": "" if not np.isfinite(p) else f"{p:.6g}",
                        "n_samples": str(n_samples),
                        "n_events": str(n_events),
                        "status": row_status,
                    }
                )

        groups = defaultdict(list)
        for row in summary_rows:
            groups[(row.get("endpoint", "OS"), row.get("signature_tier", "ALL"))].append(row)

        for (endpoint, tier), rows in sorted(groups.items()):
            entries = []
            for row in rows:
                if row.get("status") != "ok":
                    continue
                hr = _as_float_or_nan(row.get("hazard_ratio"))
                lo = _as_float_or_nan(row.get("lower_95_ci"))
                hi = _as_float_or_nan(row.get("upper_95_ci"))
                if not (np.isfinite(hr) and np.isfinite(lo) and np.isfinite(hi) and hr > 0 and lo > 0 and hi > 0):
                    continue
                log_hr = float(np.log(hr))
                se = float((np.log(hi) - np.log(lo)) / (2.0 * 1.96))
                if np.isfinite(se) and se > 0:
                    entries.append((log_hr, se))

            if not entries:
                heterogeneity_rows.append(
                    {
                        "endpoint": endpoint,
                        "signature_tier": tier,
                        "n_projects": "0",
                        "pooled_log_hr": "",
                        "pooled_hr": "",
                        "q_statistic": "",
                        "i2_percent": "",
                        "tau2": "",
                        "status": "blocked_no_valid_projects",
                    }
                )
                continue

            meta = _random_effects_from_log_hr([e[0] for e in entries], [e[1] for e in entries])
            if meta is None:
                heterogeneity_rows.append(
                    {
                        "endpoint": endpoint,
                        "signature_tier": tier,
                        "n_projects": "0",
                        "pooled_log_hr": "",
                        "pooled_hr": "",
                        "q_statistic": "",
                        "i2_percent": "",
                        "tau2": "",
                        "status": "blocked_meta_failed",
                    }
                )
                continue

            heterogeneity_rows.append(
                {
                    "endpoint": endpoint,
                    "signature_tier": tier,
                    "n_projects": str(meta["k"]),
                    "pooled_log_hr": f"{meta['pooled_log_hr']:.6g}",
                    "pooled_hr": f"{meta['pooled_hr']:.6g}",
                    "q_statistic": f"{meta['q']:.6g}",
                    "i2_percent": f"{meta['i2_percent']:.6g}",
                    "tau2": f"{meta['tau2']:.6g}",
                    "status": "ok",
                }
            )

        project_status_counts = defaultdict(lambda: {"ok": 0, "blocked": 0})
        for row in summary_rows:
            proj = row.get("project", "")
            st = row.get("status", "")
            if st == "ok":
                project_status_counts[proj]["ok"] += 1
            else:
                project_status_counts[proj]["blocked"] += 1
        for proj, counts in sorted(project_status_counts.items()):
            status_rows.append(
                {
                    "stage": "tcga_pan_cancer",
                    "project": proj,
                    "status": "completed" if counts["ok"] > 0 else "blocked",
                    "reason": "ok_survival_rows_present" if counts["ok"] > 0 else "no_ok_survival_rows",
                    "detail": f"ok={counts['ok']}; blocked={counts['blocked']}",
                }
            )

    summary_file = out_root / "tcga_pan_cancer_survival_summary.tsv"
    heterogeneity_file = out_root / "tcga_pan_cancer_heterogeneity.tsv"
    status_file = out_root / "tcga_pan_cancer_status.tsv"
    forest_file = out_root / "tcga_pan_cancer_forest.png"

    write_tsv(
        summary_file,
        fieldnames=[
            "project",
            "tcga_cancer_type",
            "endpoint",
            "signature_tier",
            "hazard_ratio",
            "lower_95_ci",
            "upper_95_ci",
            "p_value",
            "n_samples",
            "n_events",
            "status",
        ],
        rows=summary_rows,
    )
    write_tsv(
        heterogeneity_file,
        fieldnames=[
            "endpoint",
            "signature_tier",
            "n_projects",
            "pooled_log_hr",
            "pooled_hr",
            "q_statistic",
            "i2_percent",
            "tau2",
            "status",
        ],
        rows=heterogeneity_rows,
    )
    write_tsv(
        status_file,
        fieldnames=["stage", "project", "status", "reason", "detail"],
        rows=status_rows,
    )

    plot_rows = [r for r in summary_rows if r.get("status") == "ok" and r.get("hazard_ratio") and r.get("lower_95_ci") and r.get("upper_95_ci")]
    if plot_rows:
        plot_rows = sorted(plot_rows, key=lambda r: (r.get("endpoint", ""), r.get("signature_tier", ""), r.get("project", "")))
        labels = [f"{r['project']} ({r.get('endpoint','OS')}/{r.get('signature_tier','ALL')})" for r in plot_rows]
        hrs = np.array([float(r["hazard_ratio"]) for r in plot_rows], dtype=float)
        lows = np.array([float(r["lower_95_ci"]) for r in plot_rows], dtype=float)
        highs = np.array([float(r["upper_95_ci"]) for r in plot_rows], dtype=float)
        y = np.arange(len(plot_rows))
        fig_h = max(4.0, 0.35 * len(plot_rows) + 1.5)
        fig, ax = plt.subplots(figsize=(9, fig_h))
        ax.errorbar(
            hrs,
            y,
            xerr=np.vstack([hrs - lows, highs - hrs]),
            fmt="o",
            color="#1f77b4",
            ecolor="#1f77b4",
            capsize=3,
        )
        ax.axvline(1.0, color="black", linestyle="--", linewidth=1.0)
        ax.set_xscale("log")
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Hazard Ratio (log scale)")
        ax.set_title("TCGA Pan-Cancer Signature Survival Forest")
        ax.invert_yaxis()
        fig.tight_layout()
        fig.savefig(forest_file, dpi=220)
        plt.close(fig)
    else:
        status_rows.append(
            {
                "stage": "tcga_pan_cancer",
                "project": "",
                "status": "blocked",
                "reason": "no_forest_plot_rows",
                "detail": "No rows with status=ok and valid HR/CI available for plotting.",
            }
        )
        write_tsv(
            status_file,
            fieldnames=["stage", "project", "status", "reason", "detail"],
            rows=status_rows,
        )

    if epi_dir and epi_dir.exists():
        epi_status = epi_dir / "tcga_epidemiology_status.tsv"
        if not epi_status.exists():
            status_rows.append(
                {
                    "stage": "tcga_pan_cancer",
                    "project": "",
                    "status": "blocked",
                    "reason": "missing_epi_status",
                    "detail": str(epi_status),
                }
            )
            write_tsv(
                status_file,
                fieldnames=["stage", "project", "status", "reason", "detail"],
                rows=status_rows,
            )

    outputs = [summary_file, heterogeneity_file, status_file]
    if forest_file.exists():
        outputs.append(forest_file)
    _mark_run(args, "tcga pan-cancer", outputs)
    print(f"Wrote TCGA pan-cancer outputs to {out_root}")
    return 0


def _canonical_tier_name(raw: str) -> str:
    value = (raw or "").strip().upper().replace("-", "_").replace("+", "_").replace(" ", "_")
    if value in {"GOLD"}:
        return "GOLD"
    if value in {"GOLD_SILVER", "GOLD__SILVER", "GOLDSILVER", "SILVER_GOLD"}:
        return "GOLD_SILVER"
    if value in {"ALL", "FULL"}:
        return "ALL"
    if value in {"BRONZE", "SILVER"}:
        return value
    return "ALL"


def _infer_tier_from_filename(stem: str) -> str:
    low = (stem or "").lower()
    if "gold_silver" in low or "goldsilver" in low or "gold-silver" in low:
        return "GOLD_SILVER"
    if "gold" in low and "silver" not in low:
        return "GOLD"
    if "all" in low:
        return "ALL"
    return "ALL"


def cmd_tcga_tier_validate(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        from scipy.stats import mannwhitneyu
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tcga tier-validate requires numpy and scipy.") from exc

    concordance_path = Path(args.concordance)
    survival_dir = Path(args.survival_dir)
    signature_path = Path(args.signature) if args.signature else None
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if not concordance_path.exists():
        raise RuntimeError(f"Missing concordance file: {concordance_path}")

    concordance_rows = read_tsv(concordance_path)
    signature_rows = read_tsv(signature_path) if signature_path and signature_path.exists() else []

    direction_map = {r.get("gene_id", ""): r.get("signature_direction", "") for r in signature_rows if r.get("gene_id")}

    all_genes: set[str] = set()
    gold_genes: set[str] = set()
    gold_silver_genes: set[str] = set()
    source_tier_map: dict[str, str] = {}

    for row in concordance_rows:
        gene_id = (row.get("gene_id") or "").strip()
        if not gene_id:
            continue
        in_signature = parse_bool(row.get("in_signature", "false"))
        if not in_signature:
            continue
        tier = _canonical_tier_name(row.get("concordance_tier", ""))
        all_genes.add(gene_id)
        source_tier_map.setdefault(gene_id, tier if tier else "ALL")
        if tier == "GOLD":
            gold_genes.add(gene_id)
            gold_silver_genes.add(gene_id)
        elif tier == "SILVER":
            gold_silver_genes.add(gene_id)

    if not all_genes and signature_rows:
        for row in signature_rows:
            gene_id = (row.get("gene_id") or "").strip()
            if not gene_id:
                continue
            all_genes.add(gene_id)
            source_tier_map.setdefault(gene_id, "ALL")

    tier_definitions = {
        "GOLD": gold_genes,
        "GOLD_SILVER": gold_silver_genes,
        "ALL": all_genes,
    }

    tier_files = []
    tier_counts_rows = []
    for tier_name, gene_set in tier_definitions.items():
        out_file = out_root / f"tier_signature_{tier_name.lower()}.tsv"
        rows = []
        for gene_id in sorted(gene_set):
            rows.append(
                {
                    "gene_id": gene_id,
                    "signature_direction": direction_map.get(gene_id, ""),
                    "source_tier": source_tier_map.get(gene_id, "ALL"),
                    "signature_tier": tier_name,
                }
            )
        write_tsv(
            out_file,
            fieldnames=["gene_id", "signature_direction", "source_tier", "signature_tier"],
            rows=rows,
        )
        tier_files.append(out_file)
        tier_counts_rows.append(
            {
                "signature_tier": tier_name,
                "n_genes": str(len(gene_set)),
                "status": "ok" if len(gene_set) > 0 else "blocked_empty_tier_gene_set",
            }
        )

    survival_rows = []
    stats_files = sorted(survival_dir.glob("*_survival_stats.tsv")) if survival_dir.exists() else []
    for stats_path in stats_files:
        rows = read_tsv(stats_path)
        inferred_project = stats_path.stem.replace("_survival_stats", "")
        inferred_tier = _infer_tier_from_filename(stats_path.stem)
        for r in rows:
            project = (r.get("project") or inferred_project).strip()
            tier = _canonical_tier_name(r.get("signature_tier", "")) if r.get("signature_tier") else inferred_tier
            endpoint = (r.get("endpoint") or "OS").strip() or "OS"
            hr = _as_float_or_nan(r.get("hazard_ratio"))
            p = _as_float_or_nan(r.get("p_value"))
            status = (r.get("status") or "").strip()
            if not status:
                status = "ok" if np.isfinite(hr) and hr > 0 else "blocked_invalid_hr"
            survival_rows.append(
                {
                    "project": project,
                    "signature_tier": tier,
                    "endpoint": endpoint,
                    "hazard_ratio": hr,
                    "p_value": p,
                    "status": status,
                }
            )

    tier_summary_rows = []
    tier_metric_map: dict[str, list[float]] = defaultdict(list)
    for tier_name in ["GOLD", "GOLD_SILVER", "ALL"]:
        tier_data = [r for r in survival_rows if r["signature_tier"] == tier_name and r["status"] == "ok" and np.isfinite(r["hazard_ratio"]) and r["hazard_ratio"] > 0]
        if not tier_data:
            tier_summary_rows.append(
                {
                    "signature_tier": tier_name,
                    "n_genes": str(len(tier_definitions[tier_name])),
                    "n_projects_with_signal": "0",
                    "median_hr_abs_distance_from_1": "",
                    "median_p_value": "",
                    "best_project": "",
                    "best_project_hr": "",
                    "status": "blocked_no_tier_survival_stats",
                }
            )
            continue

        abs_log_hr = [abs(float(np.log(r["hazard_ratio"]))) for r in tier_data]
        pvals = [r["p_value"] for r in tier_data if np.isfinite(r["p_value"])]
        best = sorted(
            tier_data,
            key=lambda r: (
                1e9 if not np.isfinite(r["p_value"]) else r["p_value"],
                abs(float(np.log(r["hazard_ratio"]))),
            ),
        )[0]
        tier_metric_map[tier_name] = abs_log_hr
        tier_summary_rows.append(
            {
                "signature_tier": tier_name,
                "n_genes": str(len(tier_definitions[tier_name])),
                "n_projects_with_signal": str(len({r['project'] for r in tier_data})),
                "median_hr_abs_distance_from_1": f"{float(np.median(abs_log_hr)):.6g}",
                "median_p_value": f"{float(np.median(pvals)):.6g}" if pvals else "",
                "best_project": best["project"],
                "best_project_hr": f"{float(best['hazard_ratio']):.6g}",
                "status": "ok",
            }
        )

    comparison_rows = []
    tier_pairs = [("GOLD", "GOLD_SILVER"), ("GOLD", "ALL"), ("GOLD_SILVER", "ALL")]
    for a, b in tier_pairs:
        xa = tier_metric_map.get(a, [])
        xb = tier_metric_map.get(b, [])
        if len(xa) < 2 or len(xb) < 2:
            comparison_rows.append(
                {
                    "tier_a": a,
                    "tier_b": b,
                    "n_a": str(len(xa)),
                    "n_b": str(len(xb)),
                    "metric": "abs_log_hr_distance_from_1",
                    "p_value": "",
                    "status": "blocked_insufficient_points",
                    "notes": "Need >=2 values per tier for Mann-Whitney comparison.",
                }
            )
            continue
        try:
            stat = mannwhitneyu(xa, xb, alternative="two-sided")
            p_val = float(stat.pvalue)
            status = "ok"
            notes = ""
        except Exception as exc:  # noqa: BLE001
            p_val = float("nan")
            status = "model_failed"
            notes = str(exc)
        comparison_rows.append(
            {
                "tier_a": a,
                "tier_b": b,
                "n_a": str(len(xa)),
                "n_b": str(len(xb)),
                "metric": "abs_log_hr_distance_from_1",
                "p_value": "" if not np.isfinite(p_val) else f"{p_val:.6g}",
                "status": status,
                "notes": notes,
            }
        )

    summary_file = out_root / "tier_performance_summary.tsv"
    counts_file = out_root / "tier_gene_counts.tsv"
    comparison_file = out_root / "tier_performance_comparison.tsv"
    status_file = out_root / "tier_validation_status.tsv"

    write_tsv(
        summary_file,
        fieldnames=[
            "signature_tier",
            "n_genes",
            "n_projects_with_signal",
            "median_hr_abs_distance_from_1",
            "median_p_value",
            "best_project",
            "best_project_hr",
            "status",
        ],
        rows=tier_summary_rows,
    )
    write_tsv(
        counts_file,
        fieldnames=["signature_tier", "n_genes", "status"],
        rows=tier_counts_rows,
    )
    write_tsv(
        comparison_file,
        fieldnames=["tier_a", "tier_b", "n_a", "n_b", "metric", "p_value", "status", "notes"],
        rows=comparison_rows,
    )

    overall_status = "completed" if any(r.get("status") == "ok" for r in tier_summary_rows) else "blocked"
    write_tsv(
        status_file,
        fieldnames=["stage", "status", "reason", "detail"],
        rows=[
            {
                "stage": "tcga_tier_validate",
                "status": overall_status,
                "reason": "ok_tier_rows_present" if overall_status == "completed" else "no_ok_tier_rows",
                "detail": f"survival_stats_files={len(stats_files)}; concordance_rows={len(concordance_rows)}",
            }
        ],
    )

    outputs = tier_files + [summary_file, counts_file, comparison_file, status_file]
    _mark_run(args, "tcga tier-validate", outputs)
    print(f"Wrote TCGA tier validation outputs to {out_root}")
    return 0


def cmd_tcga_map(args: argparse.Namespace) -> int:
    out_file = Path(args.out) / "tcga_sample_map.tsv"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for project in args.projects:
        project_upper = project.upper()
        if not project_upper.startswith("TCGA-"):
            project_upper = f"TCGA-{project_upper}"
            
        rows.append(
            {
                "project": project_upper,
                "expression_url": f"https://gdc-hub.s3.us-east-1.amazonaws.com/download/{project_upper}.htseq_counts.tsv.gz",
                "survival_url": f"https://gdc-hub.s3.us-east-1.amazonaws.com/download/{project_upper}.survival.tsv",
                "local_expression_path": f"results/tcga_data/{project_upper}.htseq_counts.tsv.gz",
                "local_survival_path": f"results/tcga_data/{project_upper}.survival.tsv",
                "status": "pending_download",
            }
        )
    write_tsv(
        out_file,
        fieldnames=[
            "project",
            "expression_url",
            "survival_url",
            "local_expression_path",
            "local_survival_path",
            "status",
        ],
        rows=rows,
    )
    _mark_run(args, "tcga map", [out_file])
    print(f"Wrote TCGA manifest to {out_file}. Please download the URLs to the local paths before projection.")
    return 0


def cmd_tcga_project(args: argparse.Namespace) -> int:
    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("TCGA projection requires numpy and pandas.") from exc
    import shutil
    import subprocess

    signature_path = Path(args.signature)
    tcga_map_path = Path(args.tcga_map)
    naive_manifest_path = Path(args.naive_manifest) if args.naive_manifest else None
    tier_signatures_dir = Path(args.tier_signatures_dir) if args.tier_signatures_dir else None
    gene_id_mapping = Path(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv"))
    allow_weak_gene_mapping = bool(getattr(args, "allow_weak_gene_mapping", False))
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if not signature_path.exists():
        raise RuntimeError(f"Missing signature file: {signature_path}")
    if not tcga_map_path.exists():
        raise RuntimeError(f"Missing TCGA map file: {tcga_map_path}")
    if not gene_id_mapping.exists():
        raise RuntimeError(f"Missing TCGA gene ID mapping file: {gene_id_mapping}")

    sig_rows = read_tsv(signature_path)
    base_direction_map = {
        r.get("gene_id", ""): (r.get("signature_direction", "") or "").strip().lower()
        for r in sig_rows
        if r.get("gene_id")
    }
    base_up = {g for g, d in base_direction_map.items() if d == "up"}
    base_down = {g for g, d in base_direction_map.items() if d == "down"}

    signature_definitions: dict[str, dict[str, set[str] | str]] = {
        "ALL": {
            "up": set(base_up),
            "down": set(base_down),
            "signature_name": signature_path.stem,
        }
    }

    if tier_signatures_dir and tier_signatures_dir.exists():
        tier_files = sorted(tier_signatures_dir.glob("tier_signature_*.tsv"))
        for tier_file in tier_files:
            tier = _canonical_tier_name(tier_file.stem.replace("tier_signature_", ""))
            rows = read_tsv(tier_file)
            up_set: set[str] = set()
            down_set: set[str] = set()
            for row in rows:
                gene_id = (row.get("gene_id") or "").strip()
                if not gene_id:
                    continue
                direction = (row.get("signature_direction") or base_direction_map.get(gene_id, "")).strip().lower()
                if direction == "up":
                    up_set.add(gene_id)
                elif direction == "down":
                    down_set.add(gene_id)
            signature_definitions[tier] = {
                "up": up_set,
                "down": down_set,
                "signature_name": tier_file.stem,
            }

    status_rows: list[dict[str, str]] = []
    if not any((defn["up"] or defn["down"]) for defn in signature_definitions.values()):
        status_file = out_root / "tcga_projection_status.tsv"
        write_tsv(
            status_file,
            fieldnames=["stage", "project", "signature_tier", "status", "reason", "detail"],
            rows=[
                {
                    "stage": "tcga_project",
                    "project": "",
                    "signature_tier": "ALL",
                    "status": "blocked",
                    "reason": "empty_signature",
                    "detail": f"No up/down genes found in {signature_path}",
                }
            ],
        )
        _mark_run(args, "tcga project", [status_file])
        print("Warning: Signature is empty. TCGA projection skipped with status artifact.")
        return 0

    map_rows = read_tsv(tcga_map_path)
    outputs: list[Path] = []

    rscript = shutil.which("Rscript")
    script = Path("scripts/tcga_survival.R")
    if not rscript or not script.exists():
        raise RuntimeError("Rscript or scripts/tcga_survival.R missing.")

    naive_include: dict[str, set[str]] = defaultdict(set)
    naive_lookup: dict[tuple[str, str], dict[str, str]] = {}
    if naive_manifest_path and naive_manifest_path.exists():
        for row in read_tsv(naive_manifest_path):
            project = (row.get("project") or "").strip()
            sample_id = (row.get("sample_id") or "").strip()
            if not project or not sample_id:
                continue
            include_flag = row.get("include_primary_projection", "")
            if include_flag == "":
                include_flag = "1" if row.get("naive_flag", "") == "1" else "0"
            if parse_bool(include_flag):
                naive_include[project].add(sample_id)
            naive_lookup[(project, sample_id)] = {
                "naive_flag": row.get("naive_flag", ""),
                "include_primary_projection": "1" if parse_bool(include_flag) else "0",
            }

    for row in map_rows:
        project = row.get("project", "TCGA-UNKNOWN")
        expr_path = Path(row.get("local_expression_path", ""))
        surv_path = Path(row.get("local_survival_path", ""))

        if not expr_path.exists() or not surv_path.exists():
            status_rows.append(
                {
                    "stage": "tcga_project",
                    "project": project,
                    "signature_tier": "ALL",
                    "status": "blocked",
                    "reason": "missing_local_expression_or_survival",
                    "detail": f"expr={expr_path.exists()} surv={surv_path.exists()}",
                }
            )
            continue

        print(f"Projecting signature onto {project}...")

        expr_df = pd.read_csv(expr_path, sep="\t", index_col=0)
        expr_df, _, gene_metrics = _standardize_expression_gene_ids(
            expr_df,
            mapping_path=gene_id_mapping,
            aggregation="mean",
        )
        gene_status, gene_fail_reason = _evaluate_gene_id_quality(
            gene_metrics,
            min_hgnc_mapping_rate=0.60,
            max_unmapped_ensembl_fraction=0.20,
            max_duplicate_collapse_fraction=0.25,
        )
        status_rows.append(
            {
                "stage": "tcga_gene_id_mapping",
                "project": project,
                "signature_tier": "ALL",
                "status": "completed" if gene_status == "pass" else "blocked",
                "reason": gene_status if gene_status == "pass" else gene_fail_reason,
                "detail": (
                    f"raw={gene_metrics.get('n_genes_raw', '')}; "
                    f"canonical={gene_metrics.get('n_genes_canonical', '')}; "
                    f"mapped_fraction={gene_metrics.get('mapped_fraction', '')}; "
                    f"unmapped_ensembl_fraction={gene_metrics.get('unmapped_ensembl_fraction', '')}; "
                    f"mapping={gene_id_mapping}"
                ),
            }
        )
        if gene_status != "pass" and not allow_weak_gene_mapping:
            continue

        surv_df = pd.read_csv(surv_path, sep="\t")
        surv_col = "sample" if "sample" in surv_df.columns else surv_df.columns[0]
        surv_df = surv_df.rename(columns={surv_col: "sample_id"})

        tiers = sorted(signature_definitions.keys(), key=lambda t: (t != "ALL", t))
        for tier in tiers:
            up_genes = set(signature_definitions[tier]["up"])  # type: ignore[index]
            down_genes = set(signature_definitions[tier]["down"])  # type: ignore[index]
            signature_name = str(signature_definitions[tier]["signature_name"])  # type: ignore[index]

            if not up_genes and not down_genes:
                status_rows.append(
                    {
                        "stage": "tcga_project",
                        "project": project,
                        "signature_tier": tier,
                        "status": "blocked",
                        "reason": "empty_tier_signature",
                        "detail": f"tier={tier}",
                    }
                )
                continue

            up_found = list(up_genes.intersection(expr_df.index))
            down_found = list(down_genes.intersection(expr_df.index))
            if not up_found and not down_found:
                status_rows.append(
                    {
                        "stage": "tcga_project",
                        "project": project,
                        "signature_tier": tier,
                        "status": "blocked",
                        "reason": "no_signature_genes_in_expression",
                        "detail": f"tier={tier}",
                    }
                )
                continue

            score_series = pd.Series(0.0, index=expr_df.columns, dtype=float)
            if up_found:
                score_series += expr_df.loc[up_found].mean(axis=0)
            if down_found:
                score_series -= expr_df.loc[down_found].mean(axis=0)
            score_std = float(score_series.std(ddof=0))
            if score_std > 0:
                score_z = (score_series - float(score_series.mean())) / score_std
            else:
                score_z = pd.Series(0.0, index=score_series.index, dtype=float)

            median_score = score_series.median()
            group_series = score_series.apply(lambda x: "High" if x >= median_score else "Low")
            score_df = pd.DataFrame(
                {
                    "project": project,
                    "sample_id": score_series.index,
                    "signature_name": signature_name,
                    "signature_tier": tier,
                    "n_up_genes_used": len(up_found),
                    "n_down_genes_used": len(down_found),
                    "signature_score": score_series.values,
                    "signature_score_z": score_z.values,
                    "score_group": group_series.values,
                    "signature_group": group_series.values,
                }
            )

            merged_df = pd.merge(score_df, surv_df, on="sample_id", how="inner")
            if naive_include.get(project):
                merged_df = merged_df[merged_df["sample_id"].isin(naive_include[project])].copy()

            if merged_df.empty:
                status_rows.append(
                    {
                        "stage": "tcga_project",
                        "project": project,
                        "signature_tier": tier,
                        "status": "blocked",
                        "reason": "no_samples_after_merge_or_naive_filter",
                        "detail": f"tier={tier}",
                    }
                )
                continue

            merged_df["naive_flag"] = merged_df["sample_id"].apply(lambda s: naive_lookup.get((project, str(s)), {}).get("naive_flag", ""))
            merged_df["include_primary_projection"] = merged_df["sample_id"].apply(
                lambda s: naive_lookup.get((project, str(s)), {}).get("include_primary_projection", "1")
            )

            use_suffix = len(tiers) > 1 or tier != "ALL"
            tier_tag = tier.lower()
            score_input_name = f"{project}_{tier_tag}_score_input.tsv" if use_suffix else f"{project}_score_input.tsv"
            merged_name = f"{project}_{tier_tag}_survival_input.tsv" if use_suffix else f"{project}_survival_input.tsv"
            stats_name = f"{project}_{tier_tag}_survival_stats.tsv" if use_suffix else f"{project}_survival_stats.tsv"
            plot_name = f"{project}_{tier_tag}_survival_km.png" if use_suffix else f"{project}_survival_km.png"

            score_out = out_root / score_input_name
            merged_path = out_root / merged_name
            stats_path = out_root / stats_name
            plot_path = out_root / plot_name

            score_cols = [
                "project",
                "sample_id",
                "signature_name",
                "signature_tier",
                "n_up_genes_used",
                "n_down_genes_used",
                "signature_score",
                "signature_score_z",
                "score_group",
                "naive_flag",
                "include_primary_projection",
            ]
            merged_df[score_cols].to_csv(score_out, sep="\t", index=False)
            merged_df.to_csv(merged_path, sep="\t", index=False)
            outputs.extend([score_out, merged_path])

            cmd = [
                rscript,
                str(script),
                "--input",
                str(merged_path),
                "--out-stats",
                str(stats_path),
                "--out-plot",
                str(plot_path),
                "--project",
                project,
                "--score-col",
                "signature_score_z",
                "--group-col",
                "signature_group",
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as exc:
                status_rows.append(
                    {
                        "stage": "tcga_project",
                        "project": project,
                        "signature_tier": tier,
                        "status": "blocked",
                        "reason": "survival_model_failed",
                        "detail": str(exc),
                    }
                )
                continue

            n_events = ""
            if "OS" in merged_df.columns:
                try:
                    n_events = str(int(pd.to_numeric(merged_df["OS"], errors="coerce").fillna(0).sum()))
                except Exception:  # noqa: BLE001
                    n_events = ""

            raw_stats_rows = read_tsv(stats_path)
            hr = ""
            lo = ""
            hi = ""
            pval = ""
            model_covariates = "signature_score_z_continuous"
            n_samples = str(len(merged_df))
            if raw_stats_rows:
                raw = raw_stats_rows[0]
                hr = raw.get("hazard_ratio", "")
                lo = raw.get("lower_95_ci", "")
                hi = raw.get("upper_95_ci", "")
                pval = raw.get("p_value", "")
                n_samples = raw.get("n_samples", n_samples)
                model_covariates = (raw.get("model_covariates", "") or "").strip() or model_covariates

            normalized_stats = [
                {
                    "project": project,
                    "endpoint": "OS",
                    "signature_tier": tier,
                    "n_samples": str(n_samples),
                    "n_events": n_events,
                    "hazard_ratio": hr,
                    "lower_95_ci": lo,
                    "upper_95_ci": hi,
                    "p_value": pval,
                    "model_covariates": model_covariates,
                    "status": "ok",
                }
            ]
            write_tsv(
                stats_path,
                fieldnames=[
                    "project",
                    "endpoint",
                    "signature_tier",
                    "n_samples",
                    "n_events",
                    "hazard_ratio",
                    "lower_95_ci",
                    "upper_95_ci",
                    "p_value",
                    "model_covariates",
                    "status",
                ],
                rows=normalized_stats,
            )
            outputs.extend([stats_path, plot_path])
            status_rows.append(
                {
                    "stage": "tcga_project",
                    "project": project,
                    "signature_tier": tier,
                    "status": "completed",
                    "reason": "ok",
                    "detail": f"n_samples={n_samples}; n_events={n_events}",
                }
            )

    status_file = out_root / "tcga_projection_status.tsv"

    thorsson_subtypes_raw = (getattr(args, "thorsson_subtypes", "") or "").strip()
    if thorsson_subtypes_raw:
        subtype_manifest = Path(thorsson_subtypes_raw).expanduser()
        if not subtype_manifest.exists():
            status_rows.append(
                {
                    "stage": "tcga_layer4_vs_thorsson",
                    "project": "",
                    "signature_tier": "ALL",
                    "status": "blocked",
                    "reason": "missing_thorsson_subtypes",
                    "detail": str(subtype_manifest),
                }
            )
        else:
            layer4_out = out_root / "thorsson_layer4"
            layer4_args = argparse.Namespace(
                expression_manifest=str(tcga_map_path),
                subtype_manifest=str(subtype_manifest),
                gene_set_registry=str(getattr(args, "gene_set_registry", "configs/immune_gene_sets_registry.tsv")),
                gene_id_mapping=str(getattr(args, "gene_id_mapping", "configs/gene_id_mapping_human.tsv")),
                min_samples=int(getattr(args, "min_layer4_samples", 3)),
                min_subtype_samples=int(getattr(args, "min_layer4_subtype_samples", 1)),
                allow_weak_gene_mapping=bool(getattr(args, "allow_weak_gene_mapping", False)),
                out=str(layer4_out),
                run_manifest=str(getattr(args, "run_manifest", "logs/run_manifest.yaml")),
            )
            cmd_tcga_epigenetic_layer(layer4_args)
            outputs.extend(
                [
                    layer4_out / "epigenetic_layer_tcga_validation.tsv",
                    layer4_out / "epigenetic_layer_tcga_scores.tsv",
                    layer4_out / "tcga_epigenetic_layer_input_contracts.md",
                ]
            )
            status_rows.append(
                {
                    "stage": "tcga_layer4_vs_thorsson",
                    "project": "",
                    "signature_tier": "ALL",
                    "status": "completed",
                    "reason": "ok",
                    "detail": str(layer4_out),
                }
            )

    write_tsv(
        status_file,
        fieldnames=["stage", "project", "signature_tier", "status", "reason", "detail"],
        rows=status_rows,
    )
    outputs.append(status_file)

    completed_rows = [row for row in status_rows if row.get("status") == "completed"]
    blocked_rows = [row for row in status_rows if row.get("status") == "blocked"]
    framing_file = out_root / "tcga_projection_framing.md"
    framing_file.write_text(
        "\n".join(
            [
                "# TCGA Projection Framing",
                "",
                f"- signature_file: {signature_path}",
                f"- tcga_map: {tcga_map_path}",
                f"- naive_manifest: {naive_manifest_path or ''}",
                "- interpretation_scope: prognostic_context_only",
                "- claim_boundary: TCGA cohorts are not ICB-treated response cohorts; these outputs must not be labelled predictive ICB validation.",
                "- allowed_language: association/projection/prognostic context/triangulation",
                "- disallowed_language: external ICB validation, responder prediction validation, treatment-response validation",
                f"- completed_status_rows: {len(completed_rows)}",
                f"- blocked_status_rows: {len(blocked_rows)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    outputs.append(framing_file)

    repro_dir = out_root / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)
    repro_commands = repro_dir / "commands.sh"
    repro_commands.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "python -m pipeline.cli tcga project \\",
                f"  --signature {signature_path} \\",
                f"  --tcga-map {tcga_map_path} \\",
                f"  --naive-manifest {naive_manifest_path or ''} \\",
                f"  --tier-signatures-dir {tier_signatures_dir or ''} \\",
                f"  --thorsson-subtypes {(getattr(args, 'thorsson_subtypes', '') or '').strip()} \\",
                f"  --gene-set-registry {(getattr(args, 'gene_set_registry', '') or '').strip()} \\",
                f"  --gene-id-mapping {(getattr(args, 'gene_id_mapping', '') or '').strip()} \\",
                f"  --min-layer4-samples {int(getattr(args, 'min_layer4_samples', 3))} \\",
                f"  --min-layer4-subtype-samples {int(getattr(args, 'min_layer4_subtype_samples', 1))} \\",
                f"  --out {out_root}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_env = repro_dir / "environment.yml"
    repro_env.write_text(
        "\n".join(
            [
                "name: rnaseq-tcga-project",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                f"  - python={sys.version_info.major}.{sys.version_info.minor}",
                "  - pandas",
                "  - numpy",
                "  - r-base",
                "  - r-survival",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repro_checksums = repro_dir / "checksums.sha256"
    checksum_targets = [status_file, framing_file, *sorted(out_root.glob("*_survival_stats.tsv"))]
    layer4_validation = out_root / "thorsson_layer4" / "epigenetic_layer_tcga_validation.tsv"
    if layer4_validation.exists():
        checksum_targets.append(layer4_validation)
    checksum_lines: list[str] = []
    for target in checksum_targets:
        if not target.exists():
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {target}")
    repro_checksums.write_text(
        "\n".join(checksum_lines) + ("\n" if checksum_lines else ""),
        encoding="utf-8",
    )
    outputs.extend([repro_commands, repro_env, repro_checksums])

    _mark_run(args, "tcga project", outputs)
    print(f"Wrote TCGA projections and survival analysis to {out_root}")
    return 0


def cmd_tcia_overlay(args: argparse.Namespace) -> int:
    out_file = Path(args.out) / "tcia_ips_annotations.tsv"
    rows = [
        {
            "project": project,
            "sample_barcode": f"{project}-SAMPLE-PLACEHOLDER",
            "ips_score": "",
            "ips_percentile": "",
            "annotation_source": "TCIA",
            "non_independent_tcga_flag": "true",
        }
        for project in args.projects
    ]
    write_tsv(
        out_file,
        fieldnames=[
            "project",
            "sample_barcode",
            "ips_score",
            "ips_percentile",
            "annotation_source",
            "non_independent_tcga_flag",
        ],
        rows=rows,
    )
    _mark_run(args, "tcia overlay", [out_file])
    print(f"Wrote {out_file}")
    return 0


def cmd_methylation_integrate(args: argparse.Namespace) -> int:
    projection_rows = read_tsv(Path(args.tcga_projection) / "candidate_projection.tsv")
    out_file = Path(args.out) / "tcga_immune_methylation_integration.tsv"
    rows = [
        {
            "gene_id": r.get("gene_id", ""),
            "gene_symbol": r.get("gene_symbol", ""),
            "signature_direction": r.get("signature_direction", ""),
            "prad_expression_state": r.get("prad_expression_state", "unknown"),
            "prad_immune_state": "unknown",
            "comparator_immune_state": "unknown",
            "ips_overlay_state": "unknown",
            "prad_methylation_state": "unknown",
            "promoter_probe_support": "0",
            "epigenetic_repression_flag": "false",
            "integration_priority_tier": "pending",
        }
        for r in projection_rows
    ]
    write_tsv(
        out_file,
        fieldnames=[
            "gene_id",
            "gene_symbol",
            "signature_direction",
            "prad_expression_state",
            "prad_immune_state",
            "comparator_immune_state",
            "ips_overlay_state",
            "prad_methylation_state",
            "promoter_probe_support",
            "epigenetic_repression_flag",
            "integration_priority_tier",
        ],
        rows=rows,
    )
    _mark_run(args, "methylation integrate", [out_file])
    print(f"Wrote {out_file}")
    return 0


def cmd_report_build(args: argparse.Namespace) -> int:
    results_root = Path(args.results_root)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    figure_root_raw = (getattr(args, "figure_root", "") or "").strip()
    figure_root = Path(figure_root_raw) if figure_root_raw else None
    out_file = out_root / "pipeline_summary.md"
    readiness_summary_file = out_root / "run_readiness_summary.tsv"
    evidence_status_file = out_root / "evidence_readiness_status.tsv"
    contrast_summary_file = out_root / "multi_contrast_summary.tsv"
    claim_boundary_file = out_root / "report_claim_boundaries.tsv"
    figure_summary_file = out_root / "figure_manifest_summary.tsv"
    tsv_files = sorted(results_root.rglob("*.tsv")) if results_root.exists() else []
    lines = [
        "# Pipeline Summary",
        "",
        f"- results_root: {results_root}",
        f"- n_tsv_files: {len(tsv_files)}",
    ]

    claim_boundary_rows = [
        {
            "topic": "tcga_projection",
            "required_label": "prognostic_projection",
            "disallowed_label": "ICB_response_validation",
            "report_language": "TCGA cohorts provide non-ICB prognostic context and biological triangulation only.",
        },
        {
            "topic": "cross_method_concordance",
            "required_label": "internal_robustness",
            "disallowed_label": "external_validation",
            "report_language": "Indirect-vs-mega agreement is internal same-sample robustness, not independent validation.",
        },
        {
            "topic": "signature_status",
            "required_label": "discovery_signature",
            "disallowed_label": "validated_predictor",
            "report_language": "Signatures remain discovery outputs unless evaluated in held-out ICB-treated cohorts.",
        },
    ]
    write_tsv(
        claim_boundary_file,
        fieldnames=["topic", "required_label", "disallowed_label", "report_language"],
        rows=claim_boundary_rows,
    )
    lines.extend(["", "## Scientific Claim Boundaries", ""])
    for row in claim_boundary_rows:
        lines.append(
            f"- {row['topic']}: required label `{row['required_label']}`. "
            f"{row['report_language']}"
        )

    mega_skip_files = sorted(results_root.rglob("mega_analysis_skipped.tsv")) if results_root.exists() else []
    if mega_skip_files:
        lines.extend(["", "## Stage Notes", ""])
        for skip_path in mega_skip_files:
            for row in read_tsv(skip_path):
                lines.append(
                    "- mega_analysis: skipped "
                    f"(reason={row.get('reason', 'unknown')}, "
                    f"contrast={row.get('contrast', '')}, "
                    f"n_cohorts_found={row.get('n_cohorts_found', '')})"
                )
                break

    def _status_summary(file_name: str) -> tuple[int, int, dict[str, int]]:
        files = sorted(results_root.rglob(file_name)) if results_root.exists() else []
        row_count = 0
        status_counts: dict[str, int] = {}
        for path in files:
            for row in read_tsv(path):
                row_count += 1
                status = (row.get("status", "") or "").strip() or "missing"
                status_counts[status] = status_counts.get(status, 0) + 1
        return len(files), row_count, status_counts

    lines.extend(["", "## TCGA Naive Projection", ""])
    tcga_status_targets = [
        ("naive_manifest_status", "tcga_naive_manifest_status.tsv"),
        ("projection_status", "tcga_projection_status.tsv"),
        ("epidemiology_status", "tcga_epidemiology_status.tsv"),
        ("pan_cancer_status", "tcga_pan_cancer_status.tsv"),
        ("tier_validation_status", "tier_validation_status.tsv"),
    ]
    for label, file_name in tcga_status_targets:
        file_hits, row_count, status_counts = _status_summary(file_name)
        if file_hits == 0:
            lines.append(f"- {label}: missing")
            continue
        status_blob = ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))
        lines.append(f"- {label}: files={file_hits}, rows={row_count}, {status_blob}")

    tcga_table_targets = [
        ("pan_cancer_survival_rows", "tcga_pan_cancer_survival_summary.tsv"),
        ("pan_cancer_heterogeneity_rows", "tcga_pan_cancer_heterogeneity.tsv"),
        ("tier_performance_rows", "tier_performance_summary.tsv"),
        ("epi_interaction_rows", "tcga_epidemiology_interactions.tsv"),
    ]
    for label, file_name in tcga_table_targets:
        table_files = sorted(results_root.rglob(file_name)) if results_root.exists() else []
        if not table_files:
            lines.append(f"- {label}: missing")
            continue
        n_rows = sum(len(read_tsv(path)) for path in table_files)
        lines.append(f"- {label}: files={len(table_files)}, rows={n_rows}")

    lines.extend(["", "## Visualization Artifacts", ""])
    figure_summary_rows: list[dict[str, str]] = []
    if figure_root and figure_root.exists():
        figure_manifest_files = sorted(figure_root.rglob("figure_manifest.tsv"))
        if figure_manifest_files:
            for manifest in figure_manifest_files:
                rows = read_tsv(manifest)
                n_tcga = 0
                n_concordance = 0
                lint_failures = 0
                for row in rows:
                    rel = (row.get("relative_path", "") or "").lower()
                    note = (row.get("scientific_note", "") or "").lower()
                    if "tcga" in rel:
                        n_tcga += 1
                        if "prognostic" not in note or "validation" in note:
                            lint_failures += 1
                    if "concordance" in rel:
                        n_concordance += 1
                        if "validation" in note:
                            lint_failures += 1
                figure_summary_rows.append(
                    {
                        "figure_root": str(figure_root),
                        "figure_manifest": str(manifest),
                        "n_figures": str(len(rows)),
                        "n_tcga_figures": str(n_tcga),
                        "n_concordance_figures": str(n_concordance),
                        "caption_lint_failures": str(lint_failures),
                    }
                )
                lines.append(
                    f"- {manifest}: figures={len(rows)}, tcga={n_tcga}, "
                    f"concordance={n_concordance}, caption_lint_failures={lint_failures}"
                )
        else:
            lines.append(f"- figure_manifest: missing under {figure_root}")
    elif figure_root:
        lines.append(f"- figure_root: missing ({figure_root})")
    else:
        lines.append("- figure_root: not provided")
    write_tsv(
        figure_summary_file,
        fieldnames=[
            "figure_root",
            "figure_manifest",
            "n_figures",
            "n_tcga_figures",
            "n_concordance_figures",
            "caption_lint_failures",
        ],
        rows=figure_summary_rows,
    )

    lines.extend(["", "## Spec 007 Patient And Immune State Artifacts", ""])
    spec007_artifact_targets = [
        ("patient_manifest", "patient_manifest.tsv"),
        ("patient_clinical_record", "patient_clinical_record.tsv"),
        ("sample_annotations_corrected", "sample_annotations_corrected.tsv"),
        ("patient_manifest_validation", "patient_manifest_validation.tsv"),
        ("comparison_registry", "comparison_registry.tsv"),
        ("immune_ssgsea_scores", "ssgsea_scores.tsv"),
        ("immune_ssgsea_scores_long", "ssgsea_scores_long.tsv"),
        ("immune_layer_summary", "layer_summary.tsv"),
        ("tcga_epigenetic_layer_association", "epigenetic_layer_tcga_validation.tsv"),
    ]
    spec007_artifact_status: dict[str, tuple[int, int]] = {}
    for label, file_name in spec007_artifact_targets:
        artifact_files = sorted(results_root.rglob(file_name)) if results_root.exists() else []
        if not artifact_files:
            spec007_artifact_status[label] = (0, 0)
            lines.append(f"- {label}: missing")
            continue
        n_rows = sum(len(read_tsv(path)) for path in artifact_files)
        spec007_artifact_status[label] = (len(artifact_files), n_rows)
        lines.append(f"- {label}: files={len(artifact_files)}, rows={n_rows}")

    lines.extend(["", "## Spec 008 Multi-Contrast Allocation", ""])
    allocation_files = sorted(results_root.rglob("sample_allocation_matrix.tsv")) if results_root.exists() else []
    unallocated_files = sorted(results_root.rglob("unallocated_samples.tsv")) if results_root.exists() else []
    delta_audit_files = sorted(results_root.rglob("treatment_delta_pair_audit.tsv")) if results_root.exists() else []
    delta_summary_files = sorted(results_root.rglob("treatment_delta_pair_summary.tsv")) if results_root.exists() else []
    template_index_files = (
        sorted(results_root.rglob("unallocated_curation_template_index.tsv")) if results_root.exists() else []
    )

    contrast_summary_rows: list[dict[str, str]] = []
    if allocation_files:
        contrast_counts: dict[str, dict[str, object]] = {
            contrast: {
                "n_sample_memberships": 0,
                "n_case": 0,
                "n_control": 0,
                "cohorts": set(),
                "cohort_roles": defaultdict(lambda: defaultdict(int)),
            }
            for contrast in sorted(SUPPORTED_CONTRASTS)
        }
        total_allocation_rows = 0
        for allocation_file in allocation_files:
            for row in read_tsv(allocation_file):
                total_allocation_rows += 1
                role = row.get("role", "")
                cohort_id = row.get("cohort_id", "")
                for contrast in [tok for tok in row.get("eligible_contrasts", "").split("|") if tok]:
                    if contrast not in contrast_counts:
                        continue
                    bucket = contrast_counts[contrast]
                    bucket["n_sample_memberships"] = int(bucket["n_sample_memberships"]) + 1
                    bucket["cohorts"].add(cohort_id)
                    bucket["cohort_roles"][cohort_id][role] += 1
                    if role == "case":
                        bucket["n_case"] = int(bucket["n_case"]) + 1
                    elif role == "control":
                        bucket["n_control"] = int(bucket["n_control"]) + 1

        delta_pair_eligible_cohorts = 0
        for delta_summary_file in delta_summary_files:
            for row in read_tsv(delta_summary_file):
                if parse_bool(row.get("delta_contrast_eligible", "false")):
                    delta_pair_eligible_cohorts += 1

        for contrast in sorted(contrast_counts):
            bucket = contrast_counts[contrast]
            cohort_roles = bucket["cohort_roles"]
            n_de_eligible = 0
            if contrast == "TREATMENT_DELTA" and delta_summary_files:
                n_de_eligible = delta_pair_eligible_cohorts
            else:
                for role_counts in cohort_roles.values():
                    if role_counts.get("case", 0) >= 2 and role_counts.get("control", 0) >= 2:
                        n_de_eligible += 1
            contrast_summary_rows.append(
                {
                    "contrast_id": contrast,
                    "n_sample_memberships": str(bucket["n_sample_memberships"]),
                    "n_case": str(bucket["n_case"]),
                    "n_control": str(bucket["n_control"]),
                    "n_cohorts_with_membership": str(len(bucket["cohorts"])),
                    "n_cohorts_de_eligible": str(n_de_eligible),
                }
            )
        write_tsv(
            contrast_summary_file,
            fieldnames=[
                "contrast_id",
                "n_sample_memberships",
                "n_case",
                "n_control",
                "n_cohorts_with_membership",
                "n_cohorts_de_eligible",
            ],
            rows=contrast_summary_rows,
        )
        unallocated_rows = sum(len(read_tsv(path)) for path in unallocated_files)
        delta_pairs = sum(len(read_tsv(path)) for path in delta_audit_files)
        lines.append(f"- sample_allocation_matrix: files={len(allocation_files)}, rows={total_allocation_rows}")
        lines.append(f"- unallocated_samples: files={len(unallocated_files)}, rows={unallocated_rows}")
        lines.append(f"- treatment_delta_pair_audit: files={len(delta_audit_files)}, rows={delta_pairs}")
        lines.append(f"- curation_template_index: files={len(template_index_files)}")
        for row in contrast_summary_rows:
            lines.append(
                f"- {row['contrast_id']}: samples={row['n_sample_memberships']}, "
                f"case={row['n_case']}, control={row['n_control']}, "
                f"cohorts={row['n_cohorts_with_membership']}, "
                f"de_eligible={row['n_cohorts_de_eligible']}"
            )
    else:
        lines.append("- sample_allocation_matrix: missing")
        write_tsv(
            contrast_summary_file,
            fieldnames=[
                "contrast_id",
                "n_sample_memberships",
                "n_case",
                "n_control",
                "n_cohorts_with_membership",
                "n_cohorts_de_eligible",
            ],
            rows=[],
        )

    # Execution/readiness truth table.
    readiness_rows: list[dict[str, str]] = []
    readiness_inputs = sorted(results_root.rglob("cohort_readiness_status.tsv")) if results_root.exists() else []
    if readiness_inputs:
        agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for path in readiness_inputs:
            for row in read_tsv(path):
                track_name = (row.get("track_name", "") or "").strip() or "unknown"
                status = (row.get("readiness_status", "") or "").strip() or "unknown"
                agg[track_name][status] += 1
                if (row.get("contrast_eligible", "") or "").strip().lower() == "true":
                    agg[track_name]["contrast_eligible"] += 1
        for track_name in sorted(agg.keys()):
            row = agg[track_name]
            readiness_rows.append(
                {
                    "run_root": str(results_root),
                    "track_name": track_name,
                    "n_routed_cohorts": str(sum(v for k, v in row.items() if k != "contrast_eligible")),
                    "n_analyzed_cohorts": str(row.get("analyzed", 0)),
                    "n_blocked_cohorts": str(row.get("blocked", 0)),
                    "n_stub_excluded_cohorts": str(row.get("stub_excluded", 0)),
                    "n_meta_eligible_cohorts": str(row.get("contrast_eligible", 0)),
                    "signature_status": "",
                    "validation_status": "",
                    "external_validation_status": "",
                }
            )

    signature_files = sorted(results_root.rglob("*signature_v1.tsv")) if results_root.exists() else []
    if not signature_files:
        signature_status = "missing_signature"
    else:
        signature_has_rows = any(bool(read_tsv(path)) for path in signature_files)
        signature_status = "non_empty_signature" if signature_has_rows else "empty_signature"

    validation_status = "missing_validation"
    external_validation_status = "missing_external_validation"
    robustness_summaries = (
        sorted(results_root.rglob("robustness_concordance_summary.tsv"))
        if results_root.exists()
        else []
    )
    validation_summaries = (
        sorted(results_root.rglob("validation_concordance_summary.tsv"))
        if results_root.exists()
        else []
    )
    summary_sources = robustness_summaries if robustness_summaries else validation_summaries
    if summary_sources:
        statuses = []
        external_statuses = []
        for path in summary_sources:
            for row in read_tsv(path):
                status = (row.get("readiness_status", "") or row.get("status", "") or "").strip()
                if status:
                    statuses.append(status)
                ext_status = (row.get("external_validation_status", "") or "").strip()
                if ext_status:
                    external_statuses.append(ext_status)
        if statuses:
            validation_status = "|".join(sorted(set(statuses)))
        if external_statuses:
            external_validation_status = "|".join(sorted(set(external_statuses)))

    for row in readiness_rows:
        row["signature_status"] = signature_status
        row["validation_status"] = validation_status
        row["external_validation_status"] = external_validation_status

    write_tsv(
        readiness_summary_file,
        fieldnames=[
            "run_root",
            "track_name",
            "n_routed_cohorts",
            "n_analyzed_cohorts",
            "n_blocked_cohorts",
            "n_stub_excluded_cohorts",
            "n_meta_eligible_cohorts",
            "signature_status",
            "validation_status",
            "external_validation_status",
        ],
        rows=readiness_rows,
    )

    evidence_status_rows: list[dict[str, str]] = []
    if allocation_files:
        evidence_status_rows.append(
            {
                "stage": "sample_allocation",
                "status": "completed",
                "reason": "allocation_matrix_present",
                "detail": f"files={len(allocation_files)}; contrast_summary={contrast_summary_file}",
            }
        )
    else:
        evidence_status_rows.append(
            {
                "stage": "sample_allocation",
                "status": "missing",
                "reason": "allocation_matrix_missing",
                "detail": "",
            }
        )

    if readiness_rows:
        total_analyzed = sum(int(r.get("n_analyzed_cohorts", "0") or 0) for r in readiness_rows)
        total_routed = sum(int(r.get("n_routed_cohorts", "0") or 0) for r in readiness_rows)
        if total_analyzed > 0:
            evidence_status_rows.append(
                {
                    "stage": "router",
                    "status": "completed",
                    "reason": "cohorts_analyzed",
                    "detail": f"analyzed={total_analyzed}; routed={total_routed}",
                }
            )
        else:
            evidence_status_rows.append(
                {
                    "stage": "router",
                    "status": "blocked",
                    "reason": "no_analyzed_cohorts",
                    "detail": f"routed={total_routed}",
                }
            )

    meta_files = sorted(results_root.rglob("meta_effects.tsv")) if results_root.exists() else []
    if not meta_files:
        evidence_status_rows.append(
            {"stage": "meta_analysis", "status": "missing", "reason": "meta_effects_missing", "detail": ""}
        )
    else:
        meta_non_empty = sum(1 for path in meta_files if read_tsv(path))
        if meta_non_empty > 0:
            evidence_status_rows.append(
                {
                    "stage": "meta_analysis",
                    "status": "completed",
                    "reason": "meta_effects_available",
                    "detail": f"non_empty_files={meta_non_empty}",
                }
            )
        else:
            evidence_status_rows.append(
                {
                    "stage": "meta_analysis",
                    "status": "blocked",
                    "reason": "meta_effects_empty_or_underpowered",
                    "detail": f"files={len(meta_files)}",
                }
            )

    if signature_status == "non_empty_signature":
        evidence_status_rows.append(
            {"stage": "signature", "status": "completed", "reason": "non_empty_signature", "detail": ""}
        )
    elif signature_status == "empty_signature":
        evidence_status_rows.append(
            {"stage": "signature", "status": "blocked", "reason": "empty_signature", "detail": ""}
        )
    else:
        evidence_status_rows.append(
            {"stage": "signature", "status": "missing", "reason": "signature_missing", "detail": ""}
        )

    patient_manifest_files, patient_manifest_rows = spec007_artifact_status.get("patient_manifest", (0, 0))
    if patient_manifest_files and patient_manifest_rows:
        evidence_status_rows.append(
            {
                "stage": "patient_manifest",
                "status": "completed",
                "reason": "patient_level_manifest_present",
                "detail": f"files={patient_manifest_files}; rows={patient_manifest_rows}",
            }
        )
    else:
        evidence_status_rows.append(
            {
                "stage": "patient_manifest",
                "status": "missing",
                "reason": "patient_level_manifest_missing",
                "detail": "",
            }
        )

    immune_layer_files, immune_layer_rows = spec007_artifact_status.get("immune_layer_summary", (0, 0))
    immune_score_files, immune_score_rows = spec007_artifact_status.get("immune_ssgsea_scores", (0, 0))
    if immune_layer_files and immune_layer_rows and immune_score_files and immune_score_rows:
        evidence_status_rows.append(
            {
                "stage": "immune_state_layers",
                "status": "completed",
                "reason": "layered_gene_set_scores_present",
                "detail": f"score_rows={immune_score_rows}; layer_rows={immune_layer_rows}",
            }
        )
    else:
        evidence_status_rows.append(
            {
                "stage": "immune_state_layers",
                "status": "missing",
                "reason": "layered_gene_set_scores_missing",
                "detail": "",
            }
        )

    marker_files = sorted(results_root.rglob("marker_correlations.tsv")) if results_root.exists() else []
    effects_files = sorted(results_root.rglob("cohort_level_effects.tsv")) if results_root.exists() else []
    if marker_files and effects_files:
        marker_rows = sum(len(read_tsv(path)) for path in marker_files)
        effect_rows = sum(len(read_tsv(path)) for path in effects_files)
        if marker_rows > 0 or effect_rows > 0:
            evidence_status_rows.append(
                {
                    "stage": "immune_effects",
                    "status": "completed",
                    "reason": "immune_effect_outputs_present",
                    "detail": f"marker_rows={marker_rows}; effect_rows={effect_rows}",
                }
            )
        else:
            evidence_status_rows.append(
                {
                    "stage": "immune_effects",
                    "status": "blocked",
                    "reason": "immune_effect_outputs_empty",
                    "detail": f"marker_files={len(marker_files)}; effect_files={len(effects_files)}",
                }
            )
    else:
        evidence_status_rows.append(
            {
                "stage": "immune_effects",
                "status": "missing",
                "reason": "immune_effect_outputs_missing",
                "detail": "",
            }
        )

    validation_tokens = {tok.strip() for tok in validation_status.split("|") if tok.strip()}
    has_completed_validation = any(tok in {"ok", "ok_precomputed", "completed"} for tok in validation_tokens)

    if validation_status == "missing_validation":
        evidence_status_rows.append(
            {"stage": "validation", "status": "missing", "reason": "validation_missing", "detail": ""}
        )
    elif has_completed_validation:
        evidence_status_rows.append(
            {"stage": "validation", "status": "completed", "reason": validation_status, "detail": ""}
        )
    else:
        evidence_status_rows.append(
            {"stage": "validation", "status": "blocked", "reason": validation_status, "detail": ""}
        )
    external_validation_tokens = {
        tok.strip() for tok in external_validation_status.split("|") if tok.strip()
    }
    if external_validation_status == "missing_external_validation" or external_validation_tokens <= {
        "missing",
        "missing_external_validation",
    }:
        evidence_status_rows.append(
            {
                "stage": "external_validation",
                "status": "missing",
                "reason": "external_validation_missing",
                "detail": "",
            }
        )
    elif "completed" in external_validation_tokens:
        evidence_status_rows.append(
            {
                "stage": "external_validation",
                "status": "completed",
                "reason": external_validation_status,
                "detail": "",
            }
        )
    else:
        evidence_status_rows.append(
            {
                "stage": "external_validation",
                "status": "blocked",
                "reason": external_validation_status,
                "detail": "",
            }
        )

    if figure_root and figure_root.exists() and figure_summary_rows:
        total_lint_failures = sum(int(row.get("caption_lint_failures", "0") or 0) for row in figure_summary_rows)
        total_figures = sum(int(row.get("n_figures", "0") or 0) for row in figure_summary_rows)
        evidence_status_rows.append(
            {
                "stage": "visualization",
                "status": "completed" if total_lint_failures == 0 and total_figures > 0 else "blocked",
                "reason": "figure_manifests_caption_linted" if total_lint_failures == 0 else "figure_caption_lint_failed",
                "detail": f"figures={total_figures}; caption_lint_failures={total_lint_failures}; figure_root={figure_root}",
            }
        )
    elif figure_root:
        evidence_status_rows.append(
            {
                "stage": "visualization",
                "status": "missing",
                "reason": "figure_manifest_missing",
                "detail": str(figure_root),
            }
        )

    write_tsv(
        evidence_status_file,
        fieldnames=["stage", "status", "reason", "detail"],
        rows=evidence_status_rows,
    )

    lines.extend(["", "## Execution Readiness", ""])
    if readiness_rows:
        for row in readiness_rows:
            lines.append(
                f"- {row.get('track_name', 'unknown')}: "
                f"routed={row.get('n_routed_cohorts', '0')}, "
                f"analyzed={row.get('n_analyzed_cohorts', '0')}, "
                f"blocked={row.get('n_blocked_cohorts', '0')}, "
                f"stub_excluded={row.get('n_stub_excluded_cohorts', '0')}, "
                f"meta_eligible={row.get('n_meta_eligible_cohorts', '0')}"
            )
    else:
        lines.append("- readiness_status: missing")
    lines.append(f"- signature_status: {signature_status}")
    lines.append(f"- validation_status: {validation_status}")
    lines.append(f"- external_validation_status: {external_validation_status}")

    lines.extend(
        [
        "",
        "## TSV Artifacts",
        "",
        ]
    )
    lines.extend([f"- {path}" for path in tsv_files[:500]])
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _mark_run(
        args,
        "report build",
        [
            out_file,
            readiness_summary_file,
            evidence_status_file,
            contrast_summary_file,
            claim_boundary_file,
            figure_summary_file,
        ],
    )
    print(f"Wrote {out_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ICI thesis pipeline scaffold CLI")
    sub = parser.add_subparsers(dest="group", required=True)

    def add_run_manifest_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument("--run-manifest", default="logs/run_manifest.yaml")

    # retrieval run
    p_retrieval = sub.add_parser("retrieval")
    s_retrieval = p_retrieval.add_subparsers(dest="action", required=True)
    p_retrieval_run = s_retrieval.add_parser("run")
    p_retrieval_run.add_argument("--discovery-manifest", required=True)
    p_retrieval_run.add_argument("--out", required=True)
    p_retrieval_run.add_argument("--no-download", action="store_true")
    add_run_manifest_arg(p_retrieval_run)
    p_retrieval_run.set_defaults(func=cmd_retrieval_run)
    p_retrieval_geo_full = s_retrieval.add_parser("geo-full")
    p_retrieval_geo_full.add_argument("--discovery-manifest", required=True)
    p_retrieval_geo_full.add_argument("--out", required=True)
    p_retrieval_geo_full.add_argument("--no-download", action="store_true")
    p_retrieval_geo_full.add_argument("--skip-suppl", action="store_true")
    p_retrieval_geo_full.add_argument("--skip-runinfo", action="store_true")
    add_run_manifest_arg(p_retrieval_geo_full)
    p_retrieval_geo_full.set_defaults(func=cmd_retrieval_geo_full)
    p_retrieval_geo_manifest = s_retrieval.add_parser("geo-manifest")
    p_retrieval_geo_manifest.add_argument("--discovery-manifest", required=True)
    p_retrieval_geo_manifest.add_argument("--downloads-root", required=True)
    p_retrieval_geo_manifest.add_argument("--out", required=True)
    add_run_manifest_arg(p_retrieval_geo_manifest)
    p_retrieval_geo_manifest.set_defaults(func=cmd_retrieval_geo_manifest)

    # intake inspect
    p_intake = sub.add_parser("intake")
    s_intake = p_intake.add_subparsers(dest="action", required=True)
    p_intake_inspect = s_intake.add_parser("inspect")
    p_intake_inspect.add_argument("--retrieval-ledger", required=True)
    p_intake_inspect.add_argument("--out", required=True)
    p_intake_inspect.add_argument("--max-samples-per-cohort", type=int, default=500)
    add_run_manifest_arg(p_intake_inspect)
    p_intake_inspect.set_defaults(func=cmd_intake_inspect)
    p_intake_detect_assay = s_intake.add_parser("detect-assay-type")
    p_intake_detect_assay.add_argument("--sample-manifest", required=True)
    p_intake_detect_assay.add_argument("--expression-manifest", required=True)
    p_intake_detect_assay.add_argument("--downloads-root", required=True)
    p_intake_detect_assay.add_argument("--out", required=True)
    add_run_manifest_arg(p_intake_detect_assay)
    p_intake_detect_assay.set_defaults(func=cmd_intake_detect_assay_type)
    p_intake_response_record = s_intake.add_parser("build-response-record")
    p_intake_response_record.add_argument("--sample-manifest", required=True)
    p_intake_response_record.add_argument("--out", required=True)
    add_run_manifest_arg(p_intake_response_record)
    p_intake_response_record.set_defaults(func=cmd_intake_build_response_record)
    p_intake_curation_report = s_intake.add_parser("curation-report")
    p_intake_curation_report.add_argument("--assay-detection", required=True)
    p_intake_curation_report.add_argument("--response-definition", required=True)
    p_intake_curation_report.add_argument("--timing-provenance", required=True)
    p_intake_curation_report.add_argument("--sample-manifest", required=True)
    p_intake_curation_report.add_argument("--out", required=True)
    add_run_manifest_arg(p_intake_curation_report)
    p_intake_curation_report.set_defaults(func=cmd_intake_curation_report)
    p_intake_gene_audit = s_intake.add_parser("gene-audit")
    p_intake_gene_audit.add_argument("--sample-manifest", required=True)
    p_intake_gene_audit.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_intake_gene_audit.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_intake_gene_audit.add_argument("--out", required=True)
    p_intake_gene_audit.add_argument("--include-excluded", action="store_true")
    p_intake_gene_audit.add_argument("--allow-stub-rows", action="store_true")
    p_intake_gene_audit.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_intake_gene_audit.add_argument("--min-hgnc-mapping-rate", required=False, type=float, default=0.60)
    p_intake_gene_audit.add_argument("--max-unmapped-ensembl-fraction", required=False, type=float, default=0.20)
    p_intake_gene_audit.add_argument("--max-duplicate-collapse-fraction", required=False, type=float, default=0.25)
    p_intake_gene_audit.add_argument("--strict", action="store_true")
    add_run_manifest_arg(p_intake_gene_audit)
    p_intake_gene_audit.set_defaults(func=cmd_intake_gene_audit)
    p_intake_geo_tables = s_intake.add_parser("build-geo-tables")
    p_intake_geo_tables.add_argument("--discovery-manifest", required=True)
    p_intake_geo_tables.add_argument("--downloads-root", required=True)
    p_intake_geo_tables.add_argument("--out", required=True)
    p_intake_geo_tables.add_argument(
        "--routing-manifest",
        default="configs/geo_input_routing_manifest.tsv",
    )
    add_run_manifest_arg(p_intake_geo_tables)
    p_intake_geo_tables.set_defaults(func=cmd_intake_build_geo_tables)
    p_intake_geo_manifest = s_intake.add_parser("build-geo-sample-manifest")
    p_intake_geo_manifest.add_argument(
        "--cohort-input-table",
        default="results/geo_tables/cohort_input_table_all.tsv",
    )
    p_intake_geo_manifest.add_argument(
        "--curated-manifest",
        default="configs/sample_manifest_curated.tsv",
        help="Hand-curated label sheet joined by GSM sample_id to supply "
             "response_label/timing where retrieval inference is unknown. "
             "Set to '' to disable the join.",
    )
    p_intake_geo_manifest.add_argument("--out", required=True)
    p_intake_geo_manifest.add_argument(
        "--ready-out",
        default="configs/sample_manifest_geo_ready.tsv",
    )
    p_intake_geo_manifest.add_argument(
        "--summary-out",
        default="results/geo_tables/sample_manifest_build_summary.md",
    )
    p_intake_geo_manifest.add_argument(
        "--ready-only",
        action="store_true",
        help="Write only analysis-ready rows to --out (still always writes --ready-out).",
    )
    p_intake_geo_manifest.add_argument(
        "--processed-only",
        action="store_true",
        help="Exclude raw-count routed cohorts from readiness and inclusion.",
    )
    p_intake_geo_manifest.add_argument(
        "--expected-pre-treatment-cohorts",
        type=int,
        default=21,
        help="Expected unique PRE-treatment ready cohort denominator for contract checks.",
    )
    p_intake_geo_manifest.add_argument(
        "--strict-pre-treatment-denominator",
        action="store_true",
        help="Fail if observed unique PRE-treatment ready cohorts differ from --expected-pre-treatment-cohorts.",
    )
    add_run_manifest_arg(p_intake_geo_manifest)
    p_intake_geo_manifest.set_defaults(func=cmd_intake_build_geo_sample_manifest)
    p_intake_geo_matrix = s_intake.add_parser("analyze-geo-series-matrix")
    p_intake_geo_matrix.add_argument("--discovery-manifest", required=True)
    p_intake_geo_matrix.add_argument("--downloads-root", required=True)
    p_intake_geo_matrix.add_argument("--out", required=True)
    p_intake_geo_matrix.add_argument(
        "--curation-sheet",
        default="",
        help="Optional study-level curation TSV to attach scientific-anchor routing context.",
    )
    add_run_manifest_arg(p_intake_geo_matrix)
    p_intake_geo_matrix.set_defaults(func=cmd_intake_analyze_geo_series_matrix)
    p_intake_extract_chars = s_intake.add_parser("extract-characteristics")
    p_intake_extract_chars.add_argument("--downloads-root", required=True)
    p_intake_extract_chars.add_argument(
        "--expression-manifest",
        required=False,
        default="results/geo_tables/geo_tables_summary.tsv",
    )
    p_intake_extract_chars.add_argument("--out", required=True)
    add_run_manifest_arg(p_intake_extract_chars)
    p_intake_extract_chars.set_defaults(func=cmd_intake_extract_characteristics)
    p_intake_apply_chars = s_intake.add_parser("apply-characteristics-mapping")
    p_intake_apply_chars.add_argument("--characteristics", required=True)
    p_intake_apply_chars.add_argument("--response-mapping", required=True)
    p_intake_apply_chars.add_argument("--timing-mapping", required=True)
    p_intake_apply_chars.add_argument("--out", required=True)
    add_run_manifest_arg(p_intake_apply_chars)
    p_intake_apply_chars.set_defaults(func=cmd_intake_apply_characteristics_mapping)
    p_intake_extract_aliases = s_intake.add_parser("extract-expression-aliases")
    p_intake_extract_aliases.add_argument("--downloads-root", required=True)
    p_intake_extract_aliases.add_argument(
        "--expression-manifest",
        required=False,
        default="results/geo_tables/geo_tables_summary.tsv",
    )
    p_intake_extract_aliases.add_argument("--out", required=True)
    add_run_manifest_arg(p_intake_extract_aliases)
    p_intake_extract_aliases.set_defaults(func=cmd_intake_extract_expression_aliases)
    p_intake_merge_metadata = s_intake.add_parser("merge-extracted-metadata")
    p_intake_merge_metadata.add_argument("--sample-manifest", required=True)
    p_intake_merge_metadata.add_argument("--response-labels", required=True)
    p_intake_merge_metadata.add_argument("--expression-aliases", required=True)
    p_intake_merge_metadata.add_argument("--out", required=True)
    p_intake_merge_metadata.add_argument(
        "--eligibility-report",
        required=False,
        default="results/spec_006/de_eligibility_report.tsv",
    )
    add_run_manifest_arg(p_intake_merge_metadata)
    p_intake_merge_metadata.set_defaults(func=cmd_intake_merge_extracted_metadata)
    p_intake_patient_manifest = s_intake.add_parser("build-patient-manifest")
    p_intake_patient_manifest.add_argument(
        "--sample-manifest",
        required=False,
        default="configs/sample_manifest_curated.tsv",
    )
    p_intake_patient_manifest.add_argument(
        "--cohort-input-table",
        required=False,
        default="results/geo_tables/cohort_input_table_all.tsv",
        help="Reserved for backward-compatible Spec 007 provenance; current build uses --sample-manifest.",
    )
    p_intake_patient_manifest.add_argument(
        "--geo-tables-dir",
        required=False,
        default="results/geo_tables",
    )
    p_intake_patient_manifest.add_argument(
        "--out",
        required=False,
        default="results/patient_manifest",
    )
    p_intake_patient_manifest.add_argument(
        "--reference-manifest",
        required=False,
        default="results/patient_manifest/patient_manifest_v1.tsv",
    )
    add_run_manifest_arg(p_intake_patient_manifest)
    p_intake_patient_manifest.set_defaults(func=cmd_intake_build_patient_manifest)
    p_intake_sample_allocation = s_intake.add_parser("build-sample-allocation")
    p_intake_sample_allocation.add_argument(
        "--sample-manifest",
        required=False,
        default="configs/sample_manifest_curated.tsv",
    )
    p_intake_sample_allocation.add_argument(
        "--out",
        required=False,
        default="results/spec_008",
    )
    add_run_manifest_arg(p_intake_sample_allocation)
    p_intake_sample_allocation.set_defaults(func=cmd_intake_build_sample_allocation)

    # cohort audit
    p_cohort = sub.add_parser("cohort")
    s_cohort = p_cohort.add_subparsers(dest="action", required=True)
    p_cohort_audit = s_cohort.add_parser("audit")
    p_cohort_audit.add_argument("--candidate-roster", required=True)
    p_cohort_audit.add_argument("--inventory", required=True)
    p_cohort_audit.add_argument(
        "--assay-detection",
        required=False,
        default="",
        help="Optional Stage-01 assay_detection.tsv used to flag low-confidence cohorts as needs_curation.",
    )
    p_cohort_audit.add_argument(
        "--response-definition",
        required=False,
        default="",
        help="Optional Stage-01 response_definition.tsv used to flag cohorts needing manual confirmation.",
    )
    p_cohort_audit.add_argument(
        "--min-assay-confidence",
        required=False,
        type=float,
        default=0.75,
        help="Minimum acceptable Stage-01 assay detection confidence before marking cohort as needs_curation.",
    )
    p_cohort_audit.add_argument("--out", required=True)
    add_run_manifest_arg(p_cohort_audit)
    p_cohort_audit.set_defaults(func=cmd_cohort_audit)

    # manifest build
    p_manifest = sub.add_parser("manifest")
    s_manifest = p_manifest.add_subparsers(dest="action", required=True)
    p_manifest_build = s_manifest.add_parser("build")
    p_manifest_build.add_argument("--discovery-manifest", required=True)
    p_manifest_build.add_argument("--retrieval-ledger", required=True)
    p_manifest_build.add_argument("--intake-record", required=True)
    p_manifest_build.add_argument("--out", required=True)
    p_manifest_build.add_argument(
        "--patient-manifest",
        required=False,
        default="results/patient_manifest/patient_manifest.tsv",
        help="Optional patient-level authority table for response/timing overrides.",
    )
    p_manifest_build.add_argument(
        "--divergence-out",
        required=False,
        default="results/manifest_build/divergences.tsv",
        help="TSV of sample-level disagreements resolved by patient-manifest authority.",
    )
    add_run_manifest_arg(p_manifest_build)
    p_manifest_build.set_defaults(func=cmd_manifest_build)

    # analysis design
    p_design = sub.add_parser("design")
    s_design = p_design.add_subparsers(dest="action", required=True)
    p_design_build = s_design.add_parser("build")
    p_design_build.add_argument(
        "--sample-manifest",
        required=False,
        default="configs/sample_manifest_curated.tsv",
    )
    p_design_build.add_argument("--out", required=True)
    p_design_build.add_argument("--min-case-samples", required=False, type=int, default=2)
    p_design_build.add_argument("--min-control-samples", required=False, type=int, default=2)
    p_design_build.add_argument("--min-cohorts", required=False, type=int, default=1)
    p_design_build.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_design_build.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_design_build.add_argument(
        "--check-expression-readiness",
        action="store_true",
        help="Mark cohorts without a resolvable expression file as blocked in the design layer.",
    )
    add_run_manifest_arg(p_design_build)
    p_design_build.set_defaults(func=cmd_design_build)
    p_design_plan = s_design.add_parser("plan-runs")
    p_design_plan.add_argument("--analysis-registry", required=True)
    p_design_plan.add_argument("--analysis-membership", required=True)
    p_design_plan.add_argument("--out", required=True)
    p_design_plan.add_argument("--execution-root", required=False, default="results/analysis_id_runs")
    p_design_plan.add_argument("--sample-manifest", required=False, default="configs/sample_manifest_curated.tsv")
    p_design_plan.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_design_plan.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_design_plan.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_design_plan.add_argument("--python-executable", required=False, default="python3.13")
    p_design_plan.add_argument("--count-method", required=False, default="deseq2")
    p_design_plan.add_argument(
        "--analysis-id",
        action="append",
        default=[],
        help="Restrict to one analysis_id; may be repeated or comma-separated.",
    )
    p_design_plan.add_argument(
        "--pilot",
        action="store_true",
        help="Restrict plan to the local pilot: PRE, pan-ICB PRE, and ICI-combination PRE.",
    )
    p_design_plan.add_argument(
        "--stage",
        action="append",
        choices=["stage06_de", "stage07_meta"],
        default=[],
        help="Restrict planned stages; may be repeated. Defaults to both Stage 06 and Stage 07.",
    )
    p_design_plan.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_design_plan.add_argument("--allow-welch-fallback", action="store_true")
    p_design_plan.add_argument("--include-forest-plots", action="store_true")
    add_run_manifest_arg(p_design_plan)
    p_design_plan.set_defaults(func=cmd_design_plan_runs)

    # external ICI-treated validation
    p_external_validation = sub.add_parser("external-validation")
    s_external_validation = p_external_validation.add_subparsers(dest="action", required=True)
    p_external_run = s_external_validation.add_parser("run")
    p_external_run.add_argument("--candidate-roster", required=True)
    p_external_run.add_argument("--derivation-lock", required=True)
    p_external_run.add_argument("--sample-manifest", required=True)
    p_external_run.add_argument(
        "--signature",
        action="append",
        required=True,
        help="Frozen Stage 08 signature TSV. Repeat or pass comma-separated paths.",
    )
    p_external_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_external_run)
    p_external_run.set_defaults(func=cmd_external_validation_run)

    # interpretation layer (spec 027)
    p_interpret = sub.add_parser("interpret")
    s_interpret = p_interpret.add_subparsers(dest="action", required=True)
    p_interpret_enrich = s_interpret.add_parser("enrich")
    p_interpret_enrich.add_argument("--results-root", required=True)
    p_interpret_enrich.add_argument("--analysis-id", required=True)
    p_interpret_enrich.add_argument("--collections", nargs="+", required=True)
    p_interpret_enrich.add_argument("--min-overlap", type=int, default=2)
    p_interpret_enrich.add_argument("--out", required=True)
    add_run_manifest_arg(p_interpret_enrich)
    p_interpret_enrich.set_defaults(func=cmd_interpret_enrich)
    p_interpret_network = s_interpret.add_parser("network")
    p_interpret_network.add_argument("--results-root", required=True)
    p_interpret_network.add_argument("--analysis-id", required=True)
    p_interpret_network.add_argument("--expression-manifest", required=False, default="")
    p_interpret_network.add_argument("--downloads-root", required=False, default="")
    p_interpret_network.add_argument("--min-signal-floor", type=int, default=25)
    p_interpret_network.add_argument("--fdr-threshold", type=float, default=0.5)
    p_interpret_network.add_argument("--effect-threshold", type=float, default=0.3)
    p_interpret_network.add_argument("--out", required=True)
    add_run_manifest_arg(p_interpret_network)
    p_interpret_network.set_defaults(func=cmd_interpret_network)
    p_interpret_hub_meta = s_interpret.add_parser("hub-meta")
    p_interpret_hub_meta.add_argument("--results-root", required=True)
    p_interpret_hub_meta.add_argument("--out", required=True)
    add_run_manifest_arg(p_interpret_hub_meta)
    p_interpret_hub_meta.set_defaults(func=cmd_interpret_hub_meta)
    p_interpret_phenotype = s_interpret.add_parser("immunophenotype")
    p_interpret_phenotype.add_argument("--results-root", required=True)
    p_interpret_phenotype.add_argument("--criteria-registry", required=True)
    p_interpret_phenotype.add_argument("--out", required=True)
    add_run_manifest_arg(p_interpret_phenotype)
    p_interpret_phenotype.set_defaults(func=cmd_interpret_immunophenotype)
    p_interpret_epi = s_interpret.add_parser("epi-infer")
    p_interpret_epi.add_argument("--results-root", required=True)
    p_interpret_epi.add_argument("--expression-manifest", required=False, default="")
    p_interpret_epi.add_argument("--out", required=True)
    add_run_manifest_arg(p_interpret_epi)
    p_interpret_epi.set_defaults(func=cmd_interpret_epi_infer)

    # method inspect
    p_method = sub.add_parser("method")
    s_method = p_method.add_subparsers(dest="action", required=True)
    p_method_inspect = s_method.add_parser("inspect")
    p_method_inspect.add_argument("--sample-manifest", required=True)
    p_method_inspect.add_argument("--out", required=True)
    add_run_manifest_arg(p_method_inspect)
    p_method_inspect.set_defaults(func=cmd_method_inspect)
    p_method_curation = s_method.add_parser("curation-sheet")
    p_method_curation.add_argument("--discovery-manifest", required=True)
    p_method_curation.add_argument("--method-inspection", required=True)
    p_method_curation.add_argument("--out", required=True)
    add_run_manifest_arg(p_method_curation)
    p_method_curation.set_defaults(func=cmd_method_curation_sheet)
    p_method_apply = s_method.add_parser("apply-curation")
    p_method_apply.add_argument("--sample-manifest", required=True)
    p_method_apply.add_argument("--curation-sheet", required=True)
    p_method_apply.add_argument("--out", required=True)
    p_method_apply.add_argument(
        "--projection-out",
        default="results/manual_curation/sample_manifest_projection.tsv",
    )
    p_method_apply.add_argument(
        "--audit-out",
        default="results/manual_curation/curation_apply_audit.tsv",
    )
    add_run_manifest_arg(p_method_apply)
    p_method_apply.set_defaults(func=cmd_method_apply_curation)

    # ingest run
    p_ingest = sub.add_parser("ingest")
    s_ingest = p_ingest.add_subparsers(dest="action", required=True)
    p_ingest_run = s_ingest.add_parser("run")
    p_ingest_run.add_argument("--sample-manifest", required=True)
    p_ingest_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_ingest_run)
    p_ingest_run.set_defaults(func=cmd_ingest_run)

    # qc run
    p_qc = sub.add_parser("qc")
    s_qc = p_qc.add_subparsers(dest="action", required=True)
    p_qc_run = s_qc.add_parser("run")
    p_qc_run.add_argument("--sample-manifest", required=True)
    p_qc_run.add_argument("--ingest-dir", required=False, default="")
    p_qc_run.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_qc_run.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_qc_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_qc_run)
    p_qc_run.set_defaults(func=cmd_qc_run)

    # de run
    p_de = sub.add_parser("de")
    s_de = p_de.add_subparsers(dest="action", required=True)
    p_de_run = s_de.add_parser("run")
    p_de_run.add_argument("--contrast", required=True)
    p_de_run.add_argument("--sample-manifest", required=True)
    p_de_run.add_argument("--ingest-dir", required=False, default="")
    p_de_run.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_de_run.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_de_run.add_argument("--count-method", required=False, default="deseq2")
    p_de_run.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_de_run.add_argument("--min-hgnc-mapping-rate", required=False, type=float, default=0.60)
    p_de_run.add_argument("--max-unmapped-ensembl-fraction", required=False, type=float, default=0.20)
    p_de_run.add_argument("--max-duplicate-collapse-fraction", required=False, type=float, default=0.25)
    p_de_run.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_de_run.add_argument(
        "--allow-welch-fallback",
        action="store_true",
        help="Permit Welch fallback only when limma backend is unavailable for normalized/log assays.",
    )
    p_de_run.add_argument(
        "--comparison-registry",
        required=False,
        default="results/spec_007/comparison_registry.tsv",
    )
    p_de_run.add_argument(
        "--baseline-de-dir",
        required=False,
        default="",
        help="Optional prior DE output root used to annotate model migration deltas.",
    )
    p_de_run.add_argument(
        "--analysis-id",
        required=False,
        default="",
        help="Optional Spec 026 analysis_id; output directory uses analysis_id while model logic uses --contrast or registry alias.",
    )
    p_de_run.add_argument(
        "--analysis-registry",
        required=False,
        default="",
        help="Optional Spec 026 analysis_contrast_registry.tsv.",
    )
    p_de_run.add_argument(
        "--analysis-membership",
        required=False,
        default="",
        help="Optional Spec 026 analysis_contrast_membership.tsv used to subset samples for --analysis-id.",
    )
    p_de_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_de_run)
    p_de_run.set_defaults(func=cmd_de_run)

    # meta run
    p_meta = sub.add_parser("meta")
    s_meta = p_meta.add_subparsers(dest="action", required=True)
    p_meta_run = s_meta.add_parser("run")
    p_meta_run.add_argument("--contrast", required=True)
    p_meta_run.add_argument("--de-dir", required=True)
    p_meta_run.add_argument("--sample-manifest", required=False, default="")
    p_meta_run.add_argument("--comparison-registry", required=False, default="")
    p_meta_run.add_argument(
        "--analysis-id",
        required=False,
        default="",
        help="Optional Spec 026 analysis_id; DE and meta directories are keyed by this ID.",
    )
    p_meta_run.add_argument("--skip-forest-plots", action="store_true")
    p_meta_run.add_argument("--include-k1-genes", action="store_true")
    p_meta_run.add_argument("--enable-subgroups", action="store_true")
    p_meta_run.add_argument("--knapp-hartung", action="store_true")
    p_meta_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_meta_run)
    p_meta_run.set_defaults(func=cmd_meta_run)

    # mega run (head-to-head)
    p_mega = sub.add_parser("mega")
    s_mega = p_mega.add_subparsers(dest="action", required=True)
    p_mega_run = s_mega.add_parser("run")
    p_mega_run.add_argument("--contrast", required=True)
    p_mega_run.add_argument("--sample-manifest", required=True)
    p_mega_run.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_mega_run.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_mega_run.add_argument("--meta-dir", required=False, default="", help="Path to indirect meta results for concordance scoring")
    p_mega_run.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_mega_run.add_argument("--min-hgnc-mapping-rate", required=False, type=float, default=0.60)
    p_mega_run.add_argument("--max-unmapped-ensembl-fraction", required=False, type=float, default=0.20)
    p_mega_run.add_argument("--max-duplicate-collapse-fraction", required=False, type=float, default=0.25)
    p_mega_run.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_mega_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_mega_run)
    p_mega_run.set_defaults(func=cmd_mega_run)

    # visualize run
    p_visualize = sub.add_parser("visualize")
    s_visualize = p_visualize.add_subparsers(dest="action", required=True)
    p_visualize_run = s_visualize.add_parser("run")
    p_visualize_run.add_argument("--sample-manifest", required=True)
    p_visualize_run.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_visualize_run.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_visualize_run.add_argument("--de-dir", required=False, default="")
    p_visualize_run.add_argument("--meta-dir", required=False, default="")
    p_visualize_run.add_argument("--immune-dir", required=False, default="")
    p_visualize_run.add_argument("--signature-file", required=False, default="")
    p_visualize_run.add_argument("--validation-dir", required=False, default="")
    p_visualize_run.add_argument("--tcga-dir", required=False, default="")
    p_visualize_run.add_argument("--ssgsea-heatmap-top-sets", required=False, type=int, default=25)
    p_visualize_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_visualize_run)
    p_visualize_run.set_defaults(func=cmd_visualize_run)

    # visualization module build (spec 025)
    p_viz = sub.add_parser("viz")
    s_viz = p_viz.add_subparsers(dest="action", required=True)
    p_viz_build = s_viz.add_parser("build")
    p_viz_build.add_argument("--sample-manifest", required=True)
    p_viz_build.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_viz_build.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_viz_build.add_argument("--de-dir", required=False, default="")
    p_viz_build.add_argument("--meta-dir", required=False, default="")
    p_viz_build.add_argument("--immune-dir", required=False, default="")
    p_viz_build.add_argument("--signature-file", required=False, default="")
    p_viz_build.add_argument("--validation-dir", required=False, default="")
    p_viz_build.add_argument("--tcga-dir", required=False, default="")
    p_viz_build.add_argument("--ssgsea-heatmap-top-sets", required=False, type=int, default=25)
    p_viz_build.add_argument("--figure-registry", required=False, default="configs/figure_registry.tsv")
    p_viz_build.add_argument("--out", required=True)
    add_run_manifest_arg(p_viz_build)
    p_viz_build.set_defaults(func=cmd_viz_build)

    # router run
    p_router = sub.add_parser("router")
    s_router = p_router.add_subparsers(dest="action", required=True)
    p_router_run = s_router.add_parser("run")
    p_router_run.add_argument("--sample-manifest", required=True)
    p_router_run.add_argument("--track", required=False, default="ALL", choices=["ALL", "A", "B", "C"])
    p_router_run.add_argument(
        "--contrasts",
        required=False,
        default="",
        help=(
            "Comma-separated Spec 008 contrast IDs. When set, routing uses a contrast-first "
            "multi_contrast manifest instead of legacy A/B/C track labels."
        ),
    )
    p_router_run.add_argument("--out", required=True)
    p_router_run.add_argument("--include-excluded", action="store_true")
    p_router_run.add_argument("--allow-stub-rows", action="store_true")
    p_router_run.add_argument("--dry-run", action="store_true")
    p_router_run.add_argument(
        "--analysis-registry",
        required=False,
        default="",
        help="Optional Spec 026 analysis_contrast_registry.tsv. In this migration step, router consumes it for dry-runs only.",
    )
    p_router_run.add_argument(
        "--analysis-membership",
        required=False,
        default="",
        help="Optional Spec 026 analysis_contrast_membership.tsv used to build the dry-run design manifest.",
    )
    p_router_run.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_router_run.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_router_run.add_argument("--count-method", required=False, default="deseq2")
    p_router_run.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_router_run.add_argument("--min-hgnc-mapping-rate", required=False, type=float, default=0.60)
    p_router_run.add_argument("--max-unmapped-ensembl-fraction", required=False, type=float, default=0.20)
    p_router_run.add_argument("--max-duplicate-collapse-fraction", required=False, type=float, default=0.25)
    p_router_run.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_router_run.add_argument(
        "--allow-welch-fallback",
        action="store_true",
        help="Permit Stage-06 Welch fallback for normalized/log cohorts when limma backend is unavailable.",
    )
    add_run_manifest_arg(p_router_run)
    p_router_run.set_defaults(func=cmd_router_run)

    # signature derive
    p_sig = sub.add_parser("signature")
    s_sig = p_sig.add_subparsers(dest="action", required=True)
    p_sig_derive = s_sig.add_parser("derive")
    p_sig_derive.add_argument("--contrast", required=False, default="")
    p_sig_derive.add_argument("--analysis-id", required=False, default="")
    p_sig_derive.add_argument("--run-root", required=False, default="")
    p_sig_derive.add_argument("--meta-dir", required=False, default="")
    p_sig_derive.add_argument(
        "--composition-adjusted-meta-dir",
        required=False,
        default="",
        help=(
            "Optional secondary meta directory for composition-adjusted signature "
            "(written as labeled secondary artifact only)."
        ),
    )
    p_sig_derive.add_argument("--thresholds", required=False, default="configs/signature_thresholds.yaml")
    p_sig_derive.add_argument("--module-rules", required=False, default="configs/signature_module_rules.tsv")
    p_sig_derive.add_argument("--comparison-registry", required=False, default="")
    p_sig_derive.add_argument("--out", required=True)
    p_sig_derive.add_argument("--min-meta-cohorts", required=False, type=int, default=2)
    p_sig_derive.add_argument("--allow-empty-signature", action="store_true")
    add_run_manifest_arg(p_sig_derive)
    p_sig_derive.set_defaults(func=cmd_signature_derive)

    # immune score/effects
    p_immune = sub.add_parser("immune")
    s_immune = p_immune.add_subparsers(dest="action", required=True)
    p_immune_score = s_immune.add_parser("score")
    p_immune_score.add_argument("--sample-manifest", required=True)
    p_immune_score.add_argument("--ingest-dir", required=False, default="")
    p_immune_score.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_immune_score.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_immune_score.add_argument("--gene-set-registry", required=False, default="configs/immune_gene_sets_registry.tsv")
    p_immune_score.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_immune_score.add_argument("--min-hgnc-mapping-rate", required=False, type=float, default=0.60)
    p_immune_score.add_argument("--max-unmapped-ensembl-fraction", required=False, type=float, default=0.20)
    p_immune_score.add_argument("--max-duplicate-collapse-fraction", required=False, type=float, default=0.25)
    p_immune_score.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_immune_score.add_argument("--hallmark-direction-min-fraction", required=False, type=float, default=0.60)
    p_immune_score.add_argument("--hallmark-stability-min-std", required=False, type=float, default=0.05)
    p_immune_score.add_argument("--hallmark-fdr-max", required=False, type=float, default=0.10)
    p_immune_score.add_argument("--hallmark-min-significant-sets", required=False, type=int, default=1)
    p_immune_score.add_argument("--skip-backend-check", action="store_true")
    p_immune_score.add_argument(
        "--legacy-rank-mean",
        action="store_true",
        help="Deprecated: use historical Python rank-mean scorer instead of GSVA ssGSEA backend.",
    )
    p_immune_score.add_argument("--out", required=True)
    add_run_manifest_arg(p_immune_score)
    p_immune_score.set_defaults(func=cmd_immune_score)
    p_immune_effects = s_immune.add_parser("effects")
    p_immune_effects.add_argument("--sample-manifest", required=True)
    p_immune_effects.add_argument("--immune-dir", required=True)
    p_immune_effects.add_argument("--expression-manifest", required=False, default="results/geo_tables/geo_tables_summary.tsv")
    p_immune_effects.add_argument("--downloads-root", required=False, default="results/retrieval/downloads")
    p_immune_effects.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_immune_effects.add_argument("--min-hgnc-mapping-rate", required=False, type=float, default=0.60)
    p_immune_effects.add_argument("--max-unmapped-ensembl-fraction", required=False, type=float, default=0.20)
    p_immune_effects.add_argument("--max-duplicate-collapse-fraction", required=False, type=float, default=0.25)
    p_immune_effects.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_immune_effects.add_argument("--out", required=True)
    add_run_manifest_arg(p_immune_effects)
    p_immune_effects.set_defaults(func=cmd_immune_effects)

    # validate run
    p_validate = sub.add_parser("validate")
    s_validate = p_validate.add_subparsers(dest="action", required=True)
    p_validate_run = s_validate.add_parser("run")
    p_validate_run.add_argument("--signature", required=True)
    p_validate_run.add_argument("--validation-manifest", required=False, default="")
    p_validate_run.add_argument("--results-root", required=False, default="")
    p_validate_run.add_argument("--contrast", required=False, default="PRE_RESPONSE")
    p_validate_run.add_argument("--indirect-meta", required=False, default="")
    p_validate_run.add_argument("--mega-results", required=False, default="")
    p_validate_run.add_argument("--mega-concordance", required=False, default="")
    p_validate_run.add_argument(
        "--meta-loco-summary",
        required=False,
        default="",
        help="Optional corrected meta_leave_one_out_summary.tsv used for nested LOCO robustness metrics.",
    )
    p_validate_run.add_argument(
        "--nested-loco-evaluation",
        required=False,
        default="",
        help="Optional precomputed nested LOCO robustness table. If absent, validation derives it from --meta-loco-summary.",
    )
    p_validate_run.add_argument("--tcga-projection", required=False, default="")
    p_validate_run.add_argument(
        "--heldout-evaluation",
        required=False,
        default="",
        help="Optional held-out or nested-LOCO external evaluation table (AUC/effect concordance).",
    )
    p_validate_run.add_argument("--sample-manifest", required=False, default="configs/sample_manifest_curated.tsv")
    p_validate_run.add_argument("--out", required=True)
    add_run_manifest_arg(p_validate_run)
    p_validate_run.set_defaults(func=cmd_validate_run)

    # tcga map/project
    p_tcga = sub.add_parser("tcga")
    s_tcga = p_tcga.add_subparsers(dest="action", required=True)
    p_tcga_map = s_tcga.add_parser("map")
    p_tcga_map.add_argument("--projects", nargs="+", required=True)
    p_tcga_map.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_map)
    p_tcga_map.set_defaults(func=cmd_tcga_map)
    p_tcga_naive_map = s_tcga.add_parser("naive-map")
    p_tcga_naive_map.add_argument("--sample-manifest", required=True)
    p_tcga_naive_map.add_argument("--project-registry", required=True)
    p_tcga_naive_map.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_naive_map)
    p_tcga_naive_map.set_defaults(func=cmd_tcga_naive_map)
    p_tcga_naive = s_tcga.add_parser("naive-manifest")
    p_tcga_naive.add_argument("--tcga-map", required=True)
    p_tcga_naive.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_naive)
    p_tcga_naive.set_defaults(func=cmd_tcga_naive_manifest)
    p_tcga_epi = s_tcga.add_parser("epi-model")
    p_tcga_epi.add_argument("--score-dir", required=True)
    p_tcga_epi.add_argument("--naive-manifest", required=True)
    p_tcga_epi.add_argument("--clinical-flat", required=False, default="")
    p_tcga_epi.add_argument("--min-samples", type=int, default=30)
    p_tcga_epi.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_epi)
    p_tcga_epi.set_defaults(func=cmd_tcga_epi_model)
    p_tcga_epi_layer = s_tcga.add_parser("epigenetic-layer")
    p_tcga_epi_layer.add_argument("--expression-manifest", required=True)
    p_tcga_epi_layer.add_argument("--subtype-manifest", required=True)
    p_tcga_epi_layer.add_argument("--gene-set-registry", required=False, default="configs/immune_gene_sets_registry.tsv")
    p_tcga_epi_layer.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_tcga_epi_layer.add_argument("--min-samples", required=False, type=int, default=3)
    p_tcga_epi_layer.add_argument("--min-subtype-samples", required=False, type=int, default=1)
    p_tcga_epi_layer.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_tcga_epi_layer.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_epi_layer)
    p_tcga_epi_layer.set_defaults(func=cmd_tcga_epigenetic_layer)
    p_tcga_pan = s_tcga.add_parser("pan-cancer")
    p_tcga_pan.add_argument("--survival-dir", required=True)
    p_tcga_pan.add_argument("--epi-dir", required=False, default="")
    p_tcga_pan.add_argument("--project-registry", required=False, default="configs/tcga_naive_project_registry.tsv")
    p_tcga_pan.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_pan)
    p_tcga_pan.set_defaults(func=cmd_tcga_pan_cancer)
    p_tcga_tier = s_tcga.add_parser("tier-validate")
    p_tcga_tier.add_argument("--concordance", required=True)
    p_tcga_tier.add_argument("--survival-dir", required=True)
    p_tcga_tier.add_argument("--signature", required=False, default="")
    p_tcga_tier.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_tier)
    p_tcga_tier.set_defaults(func=cmd_tcga_tier_validate)
    p_tcga_project = s_tcga.add_parser("project")
    p_tcga_project.add_argument("--signature", required=True)
    p_tcga_project.add_argument("--tcga-map", required=True)
    p_tcga_project.add_argument("--naive-manifest", required=False, default="")
    p_tcga_project.add_argument("--tier-signatures-dir", required=False, default="")
    p_tcga_project.add_argument(
        "--thorsson-subtypes",
        required=False,
        default="",
        help="Optional TCGA immune-subtype manifest (Thorsson C1-C6) to run Layer-4 association in the same projection pass.",
    )
    p_tcga_project.add_argument("--gene-set-registry", required=False, default="configs/immune_gene_sets_registry.tsv")
    p_tcga_project.add_argument("--gene-id-mapping", required=False, default="configs/gene_id_mapping_human.tsv")
    p_tcga_project.add_argument("--min-layer4-samples", required=False, type=int, default=3)
    p_tcga_project.add_argument("--min-layer4-subtype-samples", required=False, type=int, default=1)
    p_tcga_project.add_argument("--allow-weak-gene-mapping", action="store_true")
    p_tcga_project.add_argument("--out", required=True)
    add_run_manifest_arg(p_tcga_project)
    p_tcga_project.set_defaults(func=cmd_tcga_project)

    # Stage 13 TCIA overlay is deprecated in Spec 007 and intentionally not
    # registered as an active CLI workflow.

    # methylation integrate
    p_meth = sub.add_parser("methylation")
    s_meth = p_meth.add_subparsers(dest="action", required=True)
    p_meth_integrate = s_meth.add_parser("integrate")
    p_meth_integrate.add_argument("--tcga-projection", required=True)
    p_meth_integrate.add_argument("--tcga-map", required=True)
    p_meth_integrate.add_argument("--immune-dir", required=False, default="")
    p_meth_integrate.add_argument("--tcia-annotations", required=False, default="")
    p_meth_integrate.add_argument("--out", required=True)
    add_run_manifest_arg(p_meth_integrate)
    p_meth_integrate.set_defaults(func=cmd_methylation_integrate)

    # report build
    p_report = sub.add_parser("report")
    s_report = p_report.add_subparsers(dest="action", required=True)
    p_report_build = s_report.add_parser("build")
    p_report_build.add_argument("--results-root", required=True)
    p_report_build.add_argument("--out", required=True)
    p_report_build.add_argument("--figure-root", required=False, default="")
    add_run_manifest_arg(p_report_build)
    p_report_build.set_defaults(func=cmd_report_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    try:
        return int(func(args))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
