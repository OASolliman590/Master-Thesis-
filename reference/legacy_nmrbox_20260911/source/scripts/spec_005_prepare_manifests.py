#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DISCOVERY_FIELDS = [
    "cohort_id",
    "accession",
    "source_db",
    "cancer_type",
    "therapy_class",
    "therapy_agent",
    "therapy_group",
    "assay_type",
    "sample_unit",
    "timing_category",
    "response_framework",
    "n_samples_total",
    "n_responders",
    "n_nonresponders",
    "raw_or_processed",
    "original_analysis_role",
    "analysis_role_merged",
    "include_in_main_analysis",
    "contrast_pre_response_candidate",
    "contrast_treatment_delta_candidate",
    "contrast_on_response_candidate",
    "epigenetic_ici_priority",
    "manual_confirmation_required",
    "manual_confirmation_reason",
    "notes",
]

ROUTING_FIELDS = [
    "cohort_id",
    "downloads_folder",
    "recommended_input_route",
    "inferred_data_mode",
    "preferred_expression_source",
    "n_soft_files",
    "n_matrix_files",
    "n_suppl_files",
    "n_runinfo_files",
    "n_raw_archive_files",
    "cohort_download_size_gb",
    "geo_core_complete",
]

LEDGER_FIELDS = [
    "canonical_cohort_id",
    "accession",
    "t7_folder_name",
    "legacy_cohort_id",
    "timer_stub_id",
    "reconciliation_status",
    "in_geo_tables",
    "in_sample_manifest",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def first_gse(accession: str) -> str:
    for token in re.split(r"[;,]", accession or ""):
        tok = token.strip().upper()
        if tok.startswith("GSE"):
            return tok
    return ""


def slug(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def disease_short(value: str) -> str:
    mapping = {
        "non_small_cell_lung_cancer": "nsclc",
        "head_and_neck_squamous_cell_carcinoma": "hnscc",
        "bladder_urothelial_carcinoma": "urothelial",
        "hepatocellular_carcinoma": "hcc",
        "renal_cell_carcinoma": "rcc",
        "stomach_adenocarcinoma": "gastric",
        "colorectal_cancer": "mcrc",
        "lung_cancer": "lung",
        "melanoma": "melanoma",
    }
    key = slug(value)
    if key in mapping:
        return mapping[key]
    parts = [p for p in key.split("_") if p]
    return "_".join(parts[:2]) if parts else "unknown"


def therapy_short(value: str) -> str:
    mapping = {
        "anti_pd_1": "pd1",
        "anti_pd_l1": "pdl1",
        "anti_pd_1_pd_l1": "pd1_pdl1",
        "anti_ctla_4": "ctla4",
        "anti_ctla_4_anti_pd_1": "ctla4_pd1",
        "guadecitabine_atezolizumab": "guadecitabine_atezolizumab",
        "durvalumab_tremelimumab": "durvalumab_tremelimumab",
        "regorafenib_ipilimumab_nivolumab": "regorafenib_ipilimumab_nivolumab",
        "durvalumab_metformin": "durvalumab_metformin",
        "dcs_treated": "dcs",
        "act": "act",
        "afatinib": "afatinib",
    }
    key = slug(value)
    if key in mapping:
        return mapping[key]
    parts = [p for p in key.split("_") if p]
    return "_".join(parts[:3]) if parts else "therapy"


def infer_therapy_class(value: str) -> str:
    low = (value or "").lower()
    if "guadecitabine" in low or "decitabine" in low or "epigenetic" in low:
        return "epigenetic priming + ICI combination"
    if "+" in low and ("pd" in low or "ctla" in low):
        return "ICI combination"
    if "pd" in low or "ctla" in low or "nivolumab" in low or "pembrolizumab" in low or "atezolizumab" in low:
        return "ICI monotherapy"
    return "therapy pending curation"


def infer_therapy_group(value: str) -> str:
    low = (value or "").lower()
    if "guadecitabine" in low:
        return "epigenetic_plus_ici"
    if "+" in low:
        return "combination_regimen"
    if "pd" in low or "ctla" in low:
        return "ici_monotherapy_or_single_agent"
    return "unclassified_regimen"


def infer_timing_category(comparison_tracks: str) -> str:
    tokens = {x.strip().upper() for x in (comparison_tracks or "").split("|") if x.strip()}
    has_pre = "PRE_RESPONSE" in tokens
    has_delta = "TREATMENT_DELTA" in tokens
    if has_pre and has_delta:
        return "pre-treatment; post-treatment"
    if has_delta:
        return "pre-treatment; post-treatment"
    if has_pre:
        return "pre-treatment"
    return "timing pending curation"


def infer_response_framework(has_rnr: str, comparison_tracks: str) -> str:
    if (has_rnr or "").strip().lower() in {"yes", "true"}:
        return "responder vs non-responder"
    tokens = {x.strip().upper() for x in (comparison_tracks or "").split("|") if x.strip()}
    if "TREATMENT_DELTA" in tokens:
        return "paired pre/post delta"
    return "response framework pending curation"


def classify_folder(folder: Path) -> dict[str, str]:
    n_soft = 0
    n_matrix = 0
    n_suppl = 0
    n_runinfo = 0
    n_raw_archive = 0
    size_bytes = 0
    has_raw_or_counts_in_suppl = False

    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        low_name = path.name.lower()
        low_rel = str(path.relative_to(folder)).lower()
        size_bytes += path.stat().st_size

        if low_name.endswith("_family.soft.gz"):
            n_soft += 1
        if "/matrix/" in f"/{low_rel}":
            n_matrix += 1
        if "/suppl/" in f"/{low_rel}":
            n_suppl += 1
            if "raw" in low_name or "count" in low_name:
                has_raw_or_counts_in_suppl = True
        if "run_info" in low_name or "sra_run" in low_name:
            n_runinfo += 1
        if low_name.endswith((".sra", ".fastq.gz", ".fq.gz", ".bam", ".cram", ".tar", ".tar.gz", ".zip", ".tgz")):
            n_raw_archive += 1

    if has_raw_or_counts_in_suppl:
        route = "raw_counts_or_fastq_path"
        inferred_mode = "raw_counts_or_count_like"
        preferred_source = "supplementary_raw_counts_or_archives"
    else:
        route = "processed_matrix"
        inferred_mode = "processed_matrix_or_normalized_table"
        preferred_source = "series_matrix_or_normalized_supplementary"

    return {
        "recommended_input_route": route,
        "inferred_data_mode": inferred_mode,
        "preferred_expression_source": preferred_source,
        "n_soft_files": str(n_soft),
        "n_matrix_files": str(n_matrix),
        "n_suppl_files": str(n_suppl),
        "n_runinfo_files": str(n_runinfo),
        "n_raw_archive_files": str(n_raw_archive),
        "cohort_download_size_gb": f"{(size_bytes / (1024**3)):.3f}",
        "geo_core_complete": "true" if n_soft > 0 and (n_matrix > 0 or n_suppl > 0) else "false",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Spec-005 reconciliation and expanded GEO manifests.")
    parser.add_argument("--reconciled-tsv", required=True)
    parser.add_argument("--discovery-in", required=True)
    parser.add_argument("--routing-in", required=True)
    parser.add_argument("--sample-manifest-curated", required=True)
    parser.add_argument("--downloads-root", required=True)
    parser.add_argument("--ledger-out", required=True)
    parser.add_argument("--discovery-out", required=True)
    parser.add_argument("--routing-out", required=True)
    parser.add_argument("--alias-root", default="")
    args = parser.parse_args()

    reconciled_rows = read_tsv(Path(args.reconciled_tsv))
    discovery_rows = read_tsv(Path(args.discovery_in))
    _routing_rows = read_tsv(Path(args.routing_in))
    sample_manifest_rows = read_tsv(Path(args.sample_manifest_curated))

    downloads_root = Path(args.downloads_root)
    ledger_out = Path(args.ledger_out)
    discovery_out = Path(args.discovery_out)
    routing_out = Path(args.routing_out)
    alias_root = Path(args.alias_root) if args.alias_root else None

    existing_primary_by_accession: dict[str, dict[str, str]] = {}
    used_cohort_ids = {r.get("cohort_id", "").strip() for r in discovery_rows if r.get("cohort_id", "").strip()}
    for row in discovery_rows:
        acc = first_gse(row.get("accession", ""))
        if acc and acc not in existing_primary_by_accession:
            existing_primary_by_accession[acc] = row

    sample_manifest_cohorts = {r.get("cohort_id", "").strip() for r in sample_manifest_rows if r.get("cohort_id", "").strip()}
    geo_summary_path = Path("results/geo_tables/geo_tables_summary.tsv")
    geo_summary_cohorts: set[str] = set()
    if geo_summary_path.exists():
        geo_summary_cohorts = {
            r.get("cohort_id", "").strip()
            for r in read_tsv(geo_summary_path)
            if r.get("cohort_id", "").strip()
        }

    by_accession = {r.get("accession", "").strip().upper(): r for r in reconciled_rows}
    ordered_accessions = sorted(by_accession.keys())

    canonical_by_accession: dict[str, str] = {}
    status_by_accession: dict[str, str] = {}
    for acc in ordered_accessions:
        rec = by_accession[acc]
        if acc in existing_primary_by_accession:
            cid = existing_primary_by_accession[acc]["cohort_id"].strip()
            status = "legacy_primary_preserved"
        else:
            cid_base = f"{acc.lower()}_{disease_short(rec.get('normalized_disease', ''))}_{therapy_short(rec.get('normalized_therapy', ''))}"
            cid = cid_base
            i = 2
            while cid in used_cohort_ids:
                cid = f"{cid_base}_v{i}"
                i += 1
            used_cohort_ids.add(cid)
            status = "generated_from_reconciled"
        canonical_by_accession[acc] = cid
        status_by_accession[acc] = status

    expanded_discovery = [dict(r) for r in discovery_rows]
    for acc in ordered_accessions:
        if acc in existing_primary_by_accession:
            continue
        rec = by_accession[acc]
        tracks = rec.get("comparison_tracks", "")
        route_classification = classify_folder(downloads_root / rec.get("current_folder_name", ""))
        expanded_discovery.append(
            {
                "cohort_id": canonical_by_accession[acc],
                "accession": acc,
                "source_db": "GEO",
                "cancer_type": rec.get("cancer_type", ""),
                "therapy_class": infer_therapy_class(rec.get("therapy_combination", "")),
                "therapy_agent": rec.get("therapy_combination", ""),
                "therapy_group": infer_therapy_group(rec.get("therapy_combination", "")),
                "assay_type": "bulk RNA-seq",
                "sample_unit": "bulk tumor sample",
                "timing_category": infer_timing_category(tracks),
                "response_framework": infer_response_framework(rec.get("has_rnr", ""), tracks),
                "n_samples_total": rec.get("patient_count", ""),
                "n_responders": rec.get("responders", ""),
                "n_nonresponders": rec.get("non_responders", ""),
                "raw_or_processed": "raw counts preferred" if route_classification["recommended_input_route"] == "raw_counts_or_fastq_path" else "processed matrix preferred",
                "original_analysis_role": "discovery" if rec.get("in_timer", "").strip().lower() == "true" else "validation",
                "analysis_role_merged": "analysis",
                "include_in_main_analysis": "true",
                "contrast_pre_response_candidate": "true" if "PRE_RESPONSE" in tracks else "false",
                "contrast_treatment_delta_candidate": "true" if "TREATMENT_DELTA" in tracks else "false",
                "contrast_on_response_candidate": "false",
                "epigenetic_ici_priority": "false",
                "manual_confirmation_required": "true",
                "manual_confirmation_reason": "spec_005_full_publication_review",
                "notes": rec.get("notes", "") or "Added during Spec-005 full GEO ingestion expansion.",
            }
        )

    routing_rows: list[dict[str, str]] = []
    for row in expanded_discovery:
        acc = first_gse(row.get("accession", ""))
        rec = by_accession.get(acc)
        if rec is None:
            continue
        downloads_folder = rec.get("current_folder_name", "")
        classification = classify_folder(downloads_root / downloads_folder)
        routing_rows.append(
            {
                "cohort_id": row.get("cohort_id", ""),
                "downloads_folder": downloads_folder,
                "recommended_input_route": classification["recommended_input_route"],
                "inferred_data_mode": classification["inferred_data_mode"],
                "preferred_expression_source": classification["preferred_expression_source"],
                "n_soft_files": classification["n_soft_files"],
                "n_matrix_files": classification["n_matrix_files"],
                "n_suppl_files": classification["n_suppl_files"],
                "n_runinfo_files": classification["n_runinfo_files"],
                "n_raw_archive_files": classification["n_raw_archive_files"],
                "cohort_download_size_gb": classification["cohort_download_size_gb"],
                "geo_core_complete": classification["geo_core_complete"],
            }
        )

    routing_by_cohort = {r["cohort_id"]: r for r in routing_rows}
    expanded_discovery_sorted = []
    for row in expanded_discovery:
        cid = row.get("cohort_id", "")
        if cid in routing_by_cohort:
            expanded_discovery_sorted.append(row)
    expanded_discovery = expanded_discovery_sorted

    ledger_rows: list[dict[str, str]] = []
    for acc in ordered_accessions:
        rec = by_accession[acc]
        canonical_id = canonical_by_accession[acc]
        stub_candidate = f"{acc.lower()}_timer_sync_stub"
        timer_stub_id = stub_candidate if stub_candidate in sample_manifest_cohorts else ""
        ledger_rows.append(
            {
                "canonical_cohort_id": canonical_id,
                "accession": acc,
                "t7_folder_name": rec.get("current_folder_name", ""),
                "legacy_cohort_id": rec.get("old_cohort_ids", ""),
                "timer_stub_id": timer_stub_id,
                "reconciliation_status": status_by_accession[acc],
                "in_geo_tables": "true" if canonical_id in geo_summary_cohorts else "false",
                "in_sample_manifest": "true" if canonical_id in sample_manifest_cohorts else "false",
            }
        )

    if alias_root is not None:
        alias_root.mkdir(parents=True, exist_ok=True)
        for row in ledger_rows:
            cid = row["canonical_cohort_id"]
            folder = row["t7_folder_name"]
            if not cid or not folder:
                continue
            target = downloads_root / folder
            if not target.exists():
                continue
            link = alias_root / cid
            if link.is_symlink():
                if link.resolve() == target.resolve():
                    continue
                link.unlink()
            elif link.exists():
                continue
            link.symlink_to(target)

    write_tsv(ledger_out, LEDGER_FIELDS, ledger_rows)
    write_tsv(discovery_out, DISCOVERY_FIELDS, expanded_discovery)
    write_tsv(routing_out, ROUTING_FIELDS, routing_rows)

    print(f"Wrote reconciliation ledger: {ledger_out} ({len(ledger_rows)} rows)")
    print(f"Wrote expanded discovery manifest: {discovery_out} ({len(expanded_discovery)} rows)")
    print(f"Wrote expanded routing manifest: {routing_out} ({len(routing_rows)} rows)")
    if alias_root is not None:
        print(f"Prepared alias downloads root: {alias_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
