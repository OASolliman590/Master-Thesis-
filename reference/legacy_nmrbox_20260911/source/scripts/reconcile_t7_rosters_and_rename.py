#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "A": "PRE_RESPONSE only: baseline responder vs non-responder (R/NR), typically pre-treatment; no paired pre/post delta track.",
    "B": "TREATMENT_DELTA only: paired pre/post treatment change analysis; no baseline R/NR endpoint.",
    "C": "PRE_RESPONSE + TREATMENT_DELTA: supports both baseline R/NR and paired pre/post delta analysis.",
}


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def safe_float(x: str) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    if math.isnan(val):
        return None
    return val


def pretty_int_or_blank(x: Optional[float]) -> str:
    if x is None:
        return ""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}"


def slug(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t or "unknown"


def normalize_therapy(therapy: str) -> str:
    t = (therapy or "").strip().lower()
    if not t:
        return "unknown_therapy"
    t = t.replace("anti-pd1", "anti-pd-1")
    t = t.replace("anti-pdl1", "anti-pd-l1")
    t = t.replace("anti-pd-1/pd-l1", "anti-pd-1-pd-l1")
    t = t.replace("anti-pd-1/anti-pd-l1", "anti-pd-1-pd-l1")
    t = t.replace("anti-pd-1/anti-pd-1", "anti-pd-1")
    t = t.replace("anti-pd-1+anti-pd-l1", "anti-pd-1-pd-l1")
    t = t.replace("anti-pd-1/pd-l1", "anti-pd-1-pd-l1")
    t = t.replace("anti-pd-1/anti-pd-l1", "anti-pd-1-pd-l1")
    t = t.replace("anti-pd1/pd-l1", "anti-pd-1-pd-l1")
    return slug(t)


def infer_from_old_ids(old_ids: str) -> Tuple[str, str]:
    txt = (old_ids or "").lower()

    disease = ""
    disease_map = [
        ("head and neck", "Head and neck squamous cell carcinoma"),
        ("hnscc", "Head and neck squamous cell carcinoma"),
        ("nsclc", "Non small-cell lung cancer"),
        ("lung", "Lung cancer"),
        ("melanoma", "Melanoma"),
        ("hcc", "Hepatocellular carcinoma"),
        ("hepatocellular", "Hepatocellular carcinoma"),
        ("rcc", "Renal cell carcinoma"),
        ("renal", "Renal cell carcinoma"),
        ("urothelial", "Bladder urothelial carcinoma"),
        ("bladder", "Bladder urothelial carcinoma"),
        ("gastric", "Stomach adenocarcinoma"),
        ("stomach", "Stomach adenocarcinoma"),
        ("glioblastoma", "Glioblastoma"),
        ("crc", "Colorectal cancer"),
        ("mcrc", "Colorectal cancer"),
        ("prostate", "Prostate adenocarcinoma"),
        ("prad", "Prostate adenocarcinoma"),
    ]
    for needle, label in disease_map:
        if needle in txt:
            disease = label
            break

    therapy = ""
    if "ctla4" in txt and "pd1" in txt:
        therapy = "anti-CTLA-4+anti-PD-1"
    elif "ctla4" in txt:
        therapy = "anti-CTLA-4"
    elif "guadecitabine" in txt and "atezolizumab" in txt:
        therapy = "guadecitabine+atezolizumab"
    elif "durvalumab" in txt and "metformin" in txt:
        therapy = "durvalumab+metformin"
    elif "durvalumab" in txt and "tremelimumab" in txt:
        therapy = "durvalumab+tremelimumab"
    elif "regorafenib" in txt and "nivolumab" in txt:
        therapy = "regorafenib+ipilimumab+nivolumab"
    elif "nivolumab" in txt:
        therapy = "anti-PD-1"
    elif "pembrolizumab" in txt:
        therapy = "anti-PD-1"
    elif "atezolizumab" in txt:
        therapy = "anti-PD-L1"
    elif "afatinib" in txt:
        therapy = "afatinib"
    elif "pdl1" in txt:
        therapy = "anti-PD-L1"
    elif "pd1" in txt:
        therapy = "anti-PD-1"

    return disease, therapy


def detect_existing_folder(root: Path, accession: str) -> Optional[Path]:
    if not root.exists():
        return None
    acc = accession.lower()
    candidates = [d for d in root.iterdir() if d.is_dir() and d.name.lower().startswith(acc)]
    if not candidates:
        return None
    candidates.sort(key=lambda p: (len(p.name), p.name.lower()))
    return candidates[0]


def category_sort_key(cat: str) -> int:
    return {"A": 1, "B": 2, "C": 3}.get(cat, 99)


def build_md(
    title: str,
    rows: List[Dict[str, str]],
    include_missing_list: bool = True,
) -> str:
    total = len(rows)
    downloaded = sum(1 for r in rows if r["download_status"] == "downloaded_present")
    missing = total - downloaded

    by_cat: Dict[str, int] = {}
    by_cat_downloaded: Dict[str, int] = {}
    for r in rows:
        c = r["track_category"] or "NA"
        by_cat[c] = by_cat.get(c, 0) + 1
        if r["download_status"] == "downloaded_present":
            by_cat_downloaded[c] = by_cat_downloaded.get(c, 0) + 1

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total studies: {total}")
    lines.append(f"- Downloaded-present: {downloaded}")
    lines.append(f"- Missing: {missing}")
    lines.append("")
    lines.append("## Category Definitions")
    lines.append(f"- `A`: {CATEGORY_DESCRIPTIONS['A']}")
    lines.append(f"- `B`: {CATEGORY_DESCRIPTIONS['B']}")
    lines.append(f"- `C`: {CATEGORY_DESCRIPTIONS['C']}")
    lines.append("")
    lines.append("## Category Counts")
    for cat in sorted(by_cat.keys(), key=category_sort_key):
        lines.append(
            f"- `{cat}`: {by_cat.get(cat, 0)} total, {by_cat_downloaded.get(cat, 0)} downloaded"
        )

    if include_missing_list and missing > 0:
        lines.append("")
        lines.append("## Missing Accessions")
        for r in rows:
            if r["download_status"] != "downloaded_present":
                lines.append(f"- `{r['accession']}` ({r['storage_class']}, category {r['track_category']})")

    lines.append("")
    lines.append("## Snapshot Timestamp")
    lines.append(f"- {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile T7 cohort rosters and optionally rename study folders."
    )
    parser.add_argument(
        "--retrieval-root",
        default="/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval",
        help="T7 retrieval root.",
    )
    parser.add_argument(
        "--merged-47-tsv",
        default=(
            "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/"
            "2-Experimental/Computation Arm/06_analysis_pipeline_repo/configs/"
            "merged_47_studies_track_stratified.tsv"
        ),
        help="Merged 47 stratified TSV.",
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="Apply folder rename operations on disk.",
    )
    parser.add_argument(
        "--no-rename",
        action="store_true",
        help="Do not apply folder renames; only emit TSV/MD outputs.",
    )
    args = parser.parse_args()

    do_rename = args.rename and not args.no_rename

    retrieval_root = Path(args.retrieval_root)
    geo_root = retrieval_root / "cohorts_source_geo_merged30"
    raw_root = retrieval_root / "cohorts_source_raw_data"

    merged_rows = read_tsv(Path(args.merged_47_tsv))

    # Build a known patient-count map from rows that already carry explicit
    # responder or pre/post counts, then use it for linked-cohort inference.
    explicit_patient_count_by_accession: Dict[str, float] = {}
    for r in merged_rows:
        accession = (r.get("accession") or "").strip().upper()
        if not accession:
            continue
        responders = safe_float(r.get("responders", ""))
        non_responders = safe_float(r.get("non_responders", ""))
        pre_t = safe_float(r.get("pre_treatment", ""))
        post_t = safe_float(r.get("post_treatment", ""))
        patient_count: Optional[float] = None
        if responders is not None and non_responders is not None:
            patient_count = responders + non_responders
        elif pre_t is not None and post_t is not None:
            patient_count = pre_t + post_t
        if patient_count is not None:
            explicit_patient_count_by_accession[accession] = patient_count

    out_rows: List[Dict[str, str]] = []
    rename_log: List[Tuple[str, str, str, str]] = []

    for r in merged_rows:
        accession = (r.get("accession") or "").strip()
        if not accession:
            continue

        is_geo = accession.upper().startswith("GSE")
        storage_class = "GEO" if is_geo else "RAW_NON_GEO"
        storage_root = geo_root if is_geo else raw_root

        existing = detect_existing_folder(storage_root, accession)
        download_status = "downloaded_present" if existing else "not_found_local_or_t7"

        cancer_type = (r.get("cancer_type") or "").strip()
        therapy = (r.get("therapy_combination") or "").strip()
        inferred_disease, inferred_therapy = infer_from_old_ids(r.get("old_cohort_ids", ""))
        if not cancer_type:
            cancer_type = inferred_disease or "Unknown cancer"
        if not therapy:
            therapy = inferred_therapy or "unknown_therapy"

        responders = safe_float(r.get("responders", ""))
        non_responders = safe_float(r.get("non_responders", ""))
        pre_t = safe_float(r.get("pre_treatment", ""))
        post_t = safe_float(r.get("post_treatment", ""))
        patient_count: Optional[float] = None
        if responders is not None and non_responders is not None:
            patient_count = responders + non_responders
        elif pre_t is not None and post_t is not None:
            patient_count = pre_t + post_t
        inferred_patient_count_source = ""
        if patient_count is None:
            old_ids = (r.get("old_cohort_ids") or "").upper()
            linked = re.findall(r"(GSE\d+|SRP\d+|ERP\d+|PRJ[A-Z0-9]+)", old_ids)
            for acc in linked:
                if acc in explicit_patient_count_by_accession:
                    patient_count = explicit_patient_count_by_accession[acc]
                    inferred_patient_count_source = f"linked_accession:{acc}"
                    break

        patient_count_label = pretty_int_or_blank(patient_count)
        patient_count_slug = patient_count_label if patient_count_label else "NA"

        track_cat = (r.get("track_category") or "").strip() or "NA"
        category_desc = CATEGORY_DESCRIPTIONS.get(track_cat, "Category not defined.")

        disease_slug = slug(cancer_type)
        therapy_slug = normalize_therapy(therapy)
        proposed_basename = (
            f"{accession.lower()}_{disease_slug}_{therapy_slug}_n{patient_count_slug}_cat{track_cat}"
        )

        current_folder_name = existing.name if existing else ""
        folder_path = str(existing) if existing else str(storage_root / proposed_basename)

        if do_rename and existing:
            target = storage_root / proposed_basename
            if existing != target:
                if target.exists():
                    rename_log.append((accession, existing.name, target.name, "target_exists_skip"))
                else:
                    existing.rename(target)
                    rename_log.append((accession, existing.name, target.name, "renamed"))
                    current_folder_name = target.name
                    folder_path = str(target)
            else:
                rename_log.append((accession, existing.name, target.name, "already_named"))

        out_rows.append(
            {
                "cohort_id": r.get("cohort_id", ""),
                "accession": accession,
                "storage_class": storage_class,
                "track_category": track_cat,
                "track_category_label": r.get("track_category_label", ""),
                "category_description": category_desc,
                "comparison_tracks": r.get("comparison_tracks", ""),
                "download_status": download_status,
                "storage_root": str(storage_root),
                "current_folder_name": current_folder_name,
                "proposed_folder_name": proposed_basename,
                "folder_path": folder_path,
                "cancer_type": cancer_type,
                "therapy_combination": therapy,
                "normalized_disease": disease_slug,
                "normalized_therapy": therapy_slug,
                "patient_count": patient_count_label,
                "patient_count_source": inferred_patient_count_source or "explicit_or_unavailable",
                "has_rnr": r.get("has_rnr", ""),
                "responders": pretty_int_or_blank(responders),
                "non_responders": pretty_int_or_blank(non_responders),
                "has_pre_post": r.get("has_pre_post", ""),
                "pre_treatment": pretty_int_or_blank(pre_t),
                "post_treatment": pretty_int_or_blank(post_t),
                "origin_stream": r.get("origin_stream", ""),
                "in_old": r.get("in_old", ""),
                "in_timer": r.get("in_timer", ""),
                "old_cohort_ids": r.get("old_cohort_ids", ""),
                "timer_refs": r.get("timer_refs", ""),
                "stratification_source": r.get("stratification_source", ""),
                "notes": r.get("notes", ""),
                "snapshot_date": dt.date.today().isoformat(),
            }
        )

    out_rows.sort(
        key=lambda x: (
            category_sort_key(x["track_category"]),
            x["storage_class"],
            x["accession"],
        )
    )

    all_tsv = retrieval_root / "cohorts_source_reconciled_all_47.tsv"
    all_md = retrieval_root / "cohorts_source_reconciled_all_47.md"
    geo_tsv = geo_root / "cohorts_source_geo_merged30_reconciled.tsv"
    geo_md = geo_root / "cohorts_source_geo_merged30_reconciled.md"
    rename_tsv = retrieval_root / "cohorts_source_rename_log.tsv"

    fieldnames = [
        "cohort_id",
        "accession",
        "storage_class",
        "track_category",
        "track_category_label",
        "category_description",
        "comparison_tracks",
        "download_status",
        "storage_root",
        "current_folder_name",
        "proposed_folder_name",
        "folder_path",
        "cancer_type",
        "therapy_combination",
        "normalized_disease",
        "normalized_therapy",
        "patient_count",
        "patient_count_source",
        "has_rnr",
        "responders",
        "non_responders",
        "has_pre_post",
        "pre_treatment",
        "post_treatment",
        "origin_stream",
        "in_old",
        "in_timer",
        "old_cohort_ids",
        "timer_refs",
        "stratification_source",
        "notes",
        "snapshot_date",
    ]
    write_tsv(all_tsv, out_rows, fieldnames)

    geo_rows = [r for r in out_rows if r["storage_class"] == "GEO"]
    write_tsv(geo_tsv, geo_rows, fieldnames)

    all_md.write_text(build_md("Reconciled Cohort Source Roster (All 47)", out_rows), encoding="utf-8")
    geo_md.write_text(
        build_md("Reconciled GEO Cohort Source Roster (Merged 30)", geo_rows, include_missing_list=False),
        encoding="utf-8",
    )

    rename_fieldnames = ["accession", "from_name", "to_name", "action"]
    rename_rows = [
        {"accession": a, "from_name": f, "to_name": t, "action": act}
        for (a, f, t, act) in rename_log
    ]
    write_tsv(rename_tsv, rename_rows, rename_fieldnames)

    print(f"WROTE_ALL_TSV={all_tsv}")
    print(f"WROTE_ALL_MD={all_md}")
    print(f"WROTE_GEO_TSV={geo_tsv}")
    print(f"WROTE_GEO_MD={geo_md}")
    print(f"WROTE_RENAME_LOG={rename_tsv}")
    print(f"TOTAL_ROWS={len(out_rows)}")
    print(f"TOTAL_GEO_ROWS={len(geo_rows)}")
    print(f"TOTAL_RAW_ROWS={len(out_rows) - len(geo_rows)}")
    print(f"RENAME_MODE={'ON' if do_rename else 'OFF'}")
    print(f"RENAME_ACTIONS={len(rename_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
