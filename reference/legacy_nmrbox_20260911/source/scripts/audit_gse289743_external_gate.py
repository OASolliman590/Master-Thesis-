#!/usr/bin/env python3
"""Audit GSE289743 for spec 080 external ICI validation readiness.

This is a narrow, metadata/processsed-expression gate. It downloads the GEO
series-level processed count matrix, maps expression columns to GSM samples via
GEO titles, checks derivation-lock independence, checks PRE response/timing
feasibility, and builds a signature-only score-ready matrix with local
gene-ID harmonization. It does not run validation statistics.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import math
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = REPO_ROOT.parent / "specs/080-external-ici-treated-validation/discovery"
DEFAULT_OUT = SPEC_ROOT / "gse289743_external_gate_20260703"
META_PATH = SPEC_ROOT / "geo_rnr_confirmation_20260703/GSE289743_sample_metadata.tsv"
EXPR_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE289nnn/GSE289743/suppl/"
    "GSE289743_Raw_counts_RNAseq_18139NR-R.csv.gz"
)
DERIVATION_LOCK = REPO_ROOT / "results/external_ici_validation/eligibility/derivation_cohort_lock.tsv"
SIGNATURE_PATHS = [
    REPO_ROOT
    / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/signature/PRE_RESPONSE/responder_signature_tiered.tsv",
    REPO_ROOT
    / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/signature/PAN_ICB_RESPONSE__PRE_TREATMENT/responder_signature_tiered.tsv",
]
GENCODE_MAP = (
    REPO_ROOT
    / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/tcga_projection/gencode_v23_gene_id_mapping_human.tsv"
)
TCGA_MAPPING_ADDENDUM = (
    REPO_ROOT
    / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/tcga_projection/tcga_signature_gene_id_mapping_addendum.tsv"
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def download_expression(out_dir: Path) -> Path:
    raw_path = out_dir / "raw/GSE289743_Raw_counts_RNAseq_18139NR-R.csv.gz"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists() and raw_path.stat().st_size > 0:
        return raw_path
    with urllib.request.urlopen(EXPR_URL, timeout=180) as response:
        raw_path.write_bytes(response.read())
    return raw_path


def load_signature_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen = set()
    for path in SIGNATURE_PATHS:
        for row in read_tsv(path):
            key = (row.get("analysis_id", ""), row.get("gene_symbol", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "analysis_id": row.get("analysis_id", ""),
                    "gene_symbol": row.get("gene_symbol", ""),
                    "signature_direction": row.get("signature_direction", ""),
                    "signature_version": row.get("signature_version", ""),
                    "signature_path": str(path.relative_to(REPO_ROOT)),
                }
            )
    return rows


def load_symbol_maps(signature_symbols: set[str]) -> dict[str, list[dict[str, str]]]:
    mappings: dict[str, list[dict[str, str]]] = defaultdict(list)
    if TCGA_MAPPING_ADDENDUM.exists():
        for row in read_tsv(TCGA_MAPPING_ADDENDUM):
            symbol = row.get("signature_symbol", "")
            if symbol in signature_symbols:
                mappings[symbol].append(
                    {
                        "ensembl_gene_id": row.get("ensembl_gene_id", ""),
                        "mapping_source": "tcga_signature_gene_id_mapping_addendum",
                        "mapped_label": row.get("previous_or_alias_symbol", ""),
                    }
                )
    if GENCODE_MAP.exists():
        with GENCODE_MAP.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                hgnc = row.get("hgnc_symbol", "")
                aliases = [a for a in (row.get("alias_symbols", "") or "").replace("|", ",").split(",") if a]
                hits = []
                if hgnc in signature_symbols:
                    hits.append(hgnc)
                hits.extend(alias for alias in aliases if alias in signature_symbols)
                for symbol in hits:
                    mappings[symbol].append(
                        {
                            "ensembl_gene_id": row.get("ensembl_gene_id", ""),
                            "mapping_source": "gencode_v23_gene_id_mapping_human",
                            "mapped_label": hgnc if hgnc != symbol else "",
                        }
                    )
    return mappings


def normalize_response(value: str) -> str:
    norm = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if norm in {"responders", "responder", "response", "r", "cr", "pr", "pcr", "mpr"}:
        return "responder"
    if norm in {"non_responders", "non_responder", "nonresponse", "non_response", "nr", "sd", "pd"}:
        return "non_responder"
    return "unknown"


def normalize_timing(value: str) -> str:
    norm = (value or "").strip().lower().replace("_", "-")
    if norm in {"pre-treatment", "pretreatment", "pre", "baseline"}:
        return "pre-treatment"
    if norm in {"post-treatment", "posttreatment", "post"}:
        return "post-treatment"
    if norm in {"on-treatment", "on"}:
        return "on-treatment"
    return "unknown"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_gate(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    expr_path = download_expression(out_dir)
    metadata = read_tsv(META_PATH)
    signature_rows = load_signature_rows()
    signature_symbols = {row["gene_symbol"] for row in signature_rows if row.get("gene_symbol")}
    symbol_maps = load_symbol_maps(signature_symbols)

    with gzip.open(expr_path, "rt", encoding="utf-8", errors="replace") as handle:
        header = next(csv.reader(handle))
    expression_columns = header[2:]
    by_title = {row.get("title", ""): row for row in metadata}
    matched_columns = [col for col in expression_columns if col in by_title]

    sample_map_rows = []
    sample_manifest_rows = []
    timing_response = Counter()
    patient_timing: dict[str, set[str]] = defaultdict(set)
    for expr_col in expression_columns:
        row = by_title.get(expr_col, {})
        sample_id = row.get("sample_id", "")
        timing = normalize_timing(row.get("sample_collection_time", ""))
        response = normalize_response(row.get("response", ""))
        patient_id = row.get("patient_id", sample_id)
        timing_response[(timing, response)] += 1
        if patient_id:
            patient_timing[patient_id].add(timing)
        sample_map_rows.append(
            {
                "expression_column": expr_col,
                "sample_id": sample_id,
                "patient_id": patient_id,
                "timing_category": timing,
                "response_label": response,
                "raw_timing": row.get("sample_collection_time", ""),
                "raw_response": row.get("response", ""),
                "match_status": "matched_title_to_geo_sample" if sample_id else "unmatched",
            }
        )
        sample_manifest_rows.append(
            {
                "external_sample_id": sample_id,
                "candidate_id": "CAND_GSE289743_CSCC_CEMIPLIMAB",
                "cohort_id": "gse289743_cscc_cemiplimab",
                "patient_id": patient_id,
                "timing_category": timing,
                "response_label": response,
                "therapy_agent": "cemiplimab",
                "therapy_class": "anti-PD-1",
                "cancer_type": "cutaneous squamous cell carcinoma",
                "expression_file": "",
                "include_flag": "true" if sample_id else "false",
                "exclude_reason": "" if sample_id else "unmatched_expression_column",
            }
        )

    df = pd.read_csv(expr_path, compression="gzip")
    df["ensembl_base"] = df["ID"].astype(str).str.split(".").str[0]
    expr_by_ens = df.set_index("ensembl_base")
    expr_symbols = set(df["Gene"].astype(str))

    coverage_rows = []
    selected_rows = []
    for symbol in sorted(signature_symbols):
        exact = df.loc[df["Gene"].astype(str) == symbol]
        status = "missing"
        expr_id = ""
        expr_gene = ""
        source = ""
        values = None
        if not exact.empty:
            values = exact[expression_columns].apply(pd.to_numeric, errors="coerce").sum(axis=0)
            status = "exact_symbol"
            expr_id = ";".join(exact["ID"].astype(str).head(3))
            expr_gene = symbol
            source = "expression_gene_symbol"
        else:
            for mapping in symbol_maps.get(symbol, []):
                ensembl = mapping.get("ensembl_gene_id", "")
                if ensembl and ensembl in expr_by_ens.index:
                    expr_row = expr_by_ens.loc[ensembl]
                    if isinstance(expr_row, pd.DataFrame):
                        values = expr_row[expression_columns].apply(pd.to_numeric, errors="coerce").sum(axis=0)
                        expr_id = ";".join(expr_row["ID"].astype(str).head(3))
                        expr_gene = ";".join(expr_row["Gene"].astype(str).head(3))
                    else:
                        values = pd.to_numeric(expr_row[expression_columns], errors="coerce")
                        expr_id = str(expr_row["ID"])
                        expr_gene = str(expr_row["Gene"])
                    status = "ensembl_mapping"
                    source = mapping.get("mapping_source", "")
                    break
        if values is not None:
            score_values = values.rename({col: by_title[col]["sample_id"] for col in matched_columns})
            selected_rows.append((symbol, score_values))
        coverage_rows.append(
            {
                "gene_symbol": symbol,
                "observed_status": "observed" if status != "missing" else "missing",
                "mapping_status": status,
                "expression_gene_id": expr_id,
                "expression_gene_symbol": expr_gene,
                "mapping_source": source,
                "missing_reason": "" if status != "missing" else "not_found_by_exact_symbol_or_local_ensembl_mapping",
            }
        )

    score_ready_path = out_dir / "gse289743_signature_mapped_log2_count_plus1_by_gsm.tsv.gz"
    score_ready = pd.DataFrame(
        {
            symbol: pd.to_numeric(values[[by_title[col]["sample_id"] for col in matched_columns]], errors="coerce")
            for symbol, values in selected_rows
        }
    ).T
    score_ready = score_ready.map(lambda value: math.log2(float(value) + 1.0) if pd.notna(value) else value)
    score_ready.index.name = "gene_symbol"
    score_ready.to_csv(score_ready_path, sep="\t", compression="gzip")

    for row in sample_manifest_rows:
        row["expression_file"] = str(score_ready_path)

    derivation_blob = "\n".join("\t".join(row.values()) for row in read_tsv(DERIVATION_LOCK)).upper()
    overlap_checks = {
        "GSE289743": "GSE289743" in derivation_blob,
        "PRJNA1224435": "PRJNA1224435" in derivation_blob,
    }
    overlap_checks["GSM_samples"] = any(row["sample_id"].upper() in derivation_blob for row in sample_map_rows if row["sample_id"])
    overlap_checks["patient_ids"] = any(row["patient_id"].upper() in derivation_blob for row in sample_map_rows if row["patient_id"])

    pre_resp = timing_response[("pre-treatment", "responder")]
    pre_non = timing_response[("pre-treatment", "non_responder")]
    observed_n = sum(1 for row in coverage_rows if row["observed_status"] == "observed")
    coverage_fraction = observed_n / len(signature_symbols) if signature_symbols else 0.0

    summary_rows = [
        {
            "accession": "GSE289743",
            "candidate_id": "CAND_GSE289743_CSCC_CEMIPLIMAB",
            "cohort_id": "gse289743_cscc_cemiplimab",
            "cancer_type": "cutaneous squamous cell carcinoma",
            "therapy_agent": "cemiplimab",
            "therapy_class": "anti-PD-1",
            "expression_file_status": "processed_counts_downloaded",
            "expression_file": str(expr_path),
            "expression_sha256": sha256(expr_path),
            "expression_rows": str(df.shape[0]),
            "expression_sample_columns": str(len(expression_columns)),
            "metadata_samples": str(len(metadata)),
            "sample_columns_matched_to_geo": str(len(matched_columns)),
            "pre_responders": str(pre_resp),
            "pre_non_responders": str(pre_non),
            "post_responders": str(timing_response[("post-treatment", "responder")]),
            "post_non_responders": str(timing_response[("post-treatment", "non_responder")]),
            "patients_total": str(len(patient_timing)),
            "patients_with_pre_and_post": str(sum(1 for timings in patient_timing.values() if {"pre-treatment", "post-treatment"} <= timings)),
            "derivation_overlap_detected": "true" if any(overlap_checks.values()) else "false",
            "derivation_overlap_checks": ";".join(f"{key}={value}" for key, value in overlap_checks.items()),
            "signature_genes_total": str(len(signature_symbols)),
            "signature_genes_observed_after_mapping": str(observed_n),
            "signature_gene_coverage_fraction": f"{coverage_fraction:.4f}",
            "score_ready_expression_file": str(score_ready_path),
            "gate_decision": "ready_for_frozen_pre_signature_scoring"
            if pre_resp >= 2 and pre_non >= 2 and not any(overlap_checks.values()) and coverage_fraction >= 0.5
            else "not_ready",
        }
    ]

    write_tsv(out_dir / "gse289743_external_gate_summary.tsv", summary_rows)
    write_tsv(out_dir / "gse289743_expression_sample_map.tsv", sample_map_rows)
    write_tsv(out_dir / "gse289743_external_validation_sample_manifest_candidate.tsv", sample_manifest_rows)
    write_tsv(
        out_dir / "gse289743_external_validation_candidate_roster.tsv",
        [
            {
                "candidate_id": "CAND_GSE289743_CSCC_CEMIPLIMAB",
                "cohort_id": "gse289743_cscc_cemiplimab",
                "accession": "GSE289743;PRJNA1224435",
                "publication_id": "PMID40836096",
                "cancer_type_raw": "cutaneous squamous cell carcinoma",
                "therapy_agent_raw": "cemiplimab",
                "therapy_class": "anti-PD-1",
                "expression_data_status": "available",
                "response_label_status": "confirmed",
                "timing_label_status": "confirmed",
                "candidate_source": "geo_series_matrix_plus_processed_counts",
                "curation_status": "curated",
                "notes": "GEO metadata has response and timing; processed featureCounts matrix is available as series supplementary file.",
            }
        ],
    )
    write_tsv(out_dir / "gse289743_signature_gene_coverage.tsv", coverage_rows)
    write_report(out_dir, summary_rows[0], coverage_rows)


def write_report(out_dir: Path, summary: dict[str, str], coverage_rows: list[dict[str, str]]) -> None:
    missing = [row["gene_symbol"] for row in coverage_rows if row["observed_status"] != "observed"]
    lines = [
        "# GSE289743 External Validation Gate Audit",
        "",
        f"Date: {dt.date.today().isoformat()}",
        "",
        "This audit checks whether `GSE289743` can move from candidate curation to frozen PRE/PAN-ICB signature scoring. It does not run validation statistics.",
        "",
        "## Verdict",
        "",
        f"- Gate decision: `{summary['gate_decision']}`",
        f"- Cohort label: `{summary['cancer_type']}` treated with `{summary['therapy_agent']}` (`{summary['therapy_class']}`).",
        f"- PRE samples: {summary['pre_responders']} responders and {summary['pre_non_responders']} non-responders.",
        f"- POST samples: {summary['post_responders']} responders and {summary['post_non_responders']} non-responders.",
        f"- Expression columns matched to GEO metadata: {summary['sample_columns_matched_to_geo']}/{summary['expression_sample_columns']}.",
        f"- Derivation overlap detected: `{summary['derivation_overlap_detected']}` ({summary['derivation_overlap_checks']}).",
        f"- Signature gene coverage after local ID mapping: {summary['signature_genes_observed_after_mapping']}/{summary['signature_genes_total']} ({summary['signature_gene_coverage_fraction']}).",
        "",
        "## Missing Signature Genes After Local Mapping",
        "",
        ", ".join(f"`{gene}`" for gene in missing) if missing else "None.",
        "",
        "## Outputs",
        "",
        "- `gse289743_external_gate_summary.tsv`",
        "- `gse289743_expression_sample_map.tsv`",
        "- `gse289743_external_validation_candidate_roster.tsv`",
        "- `gse289743_external_validation_sample_manifest_candidate.tsv`",
        "- `gse289743_signature_gene_coverage.tsv`",
        "- `gse289743_signature_mapped_log2_count_plus1_by_gsm.tsv.gz`",
        "- `raw/GSE289743_Raw_counts_RNAseq_18139NR-R.csv.gz`",
        "",
        "## Claim Boundary",
        "",
        "Passing this gate means the cohort is ready for frozen-signature scoring. It is not yet external validation evidence until the scoring run and claim-boundary tables are produced.",
        "",
        "## Reproducibility",
        "",
        "```bash",
        "python3.13 scripts/audit_gse289743_external_gate.py",
        "```",
    ]
    (out_dir / "gse289743_external_gate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "analysis_log.md").write_text(
        "\n".join(
            [
                "# Analysis Log: GSE289743 External Gate",
                "",
                f"Date: {dt.date.today().isoformat()}",
                "",
                "Command:",
                "",
                "```bash",
                "python3.13 scripts/audit_gse289743_external_gate.py",
                "```",
                "",
                f"Gate decision: `{summary['gate_decision']}`.",
                "",
                "No HPC, no full pipeline rerun, and no committed `results/` mutation.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    build_gate(DEFAULT_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
