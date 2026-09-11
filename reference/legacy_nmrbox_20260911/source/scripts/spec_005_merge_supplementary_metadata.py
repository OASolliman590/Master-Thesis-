#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


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


def first_gse(value: str) -> str:
    for token in re.split(r"[;,]", value or ""):
        tok = token.strip().upper()
        if tok.startswith("GSE"):
            return tok
    return ""


def infer_response_from_text(text: str) -> str:
    low = (text or "").lower()
    if any(tok in low for tok in ["non-responder", "non responder", "non_responder", "poor responder", "progressive disease", "\tpd\t", " recist\tpd"]):
        return "non_responder"
    if any(tok in low for tok in ["responder", "complete response", "partial response", " recist\tcr", " recist\tpr", "\tcr\t", "\tpr\t"]):
        return "responder"
    return ""


def infer_timing_from_text(text: str) -> str:
    low = (text or "").lower()
    has_pre = any(tok in low for tok in ["pre-treatment", "pretreatment", "baseline", "before", "pre "])
    has_post = any(tok in low for tok in ["post-treatment", "post treatment", "after", "on-treatment", "week", "post "])
    if has_pre and not has_post:
        return "pre-treatment"
    if has_post and not has_pre:
        return "on-treatment"
    if has_pre and has_post:
        return "mixed_or_paired"
    return ""


def infer_disease_from_text(text: str) -> str:
    low = (text or "").lower()
    mapping = [
        ("non-small", "Non-small cell lung cancer"),
        ("nsclc", "Non-small cell lung cancer"),
        ("melanoma", "Melanoma"),
        ("hepatocellular", "Hepatocellular carcinoma"),
        ("hcc", "Hepatocellular carcinoma"),
        ("urothelial", "Bladder urothelial carcinoma"),
        ("bladder", "Bladder urothelial carcinoma"),
        ("head and neck", "Head and neck squamous cell carcinoma"),
        ("hnscc", "Head and neck squamous cell carcinoma"),
        ("gastric", "Stomach adenocarcinoma"),
        ("stomach", "Stomach adenocarcinoma"),
        ("colorectal", "Colorectal cancer"),
        ("crc", "Colorectal cancer"),
        ("renal", "Renal cell carcinoma"),
    ]
    for needle, label in mapping:
        if needle in low:
            return label
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Spec-005 supplementary metadata merge scaffold.")
    parser.add_argument("--sample-manifest", required=True)
    parser.add_argument("--discovery-manifest", required=False, default="configs/discovery_geo_focus.tsv")
    parser.add_argument("--supplementary-dir", required=False, default="results/spec_005/extract_geo_metadata")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = read_tsv(Path(args.sample_manifest))
    discovery_rows = read_tsv(Path(args.discovery_manifest)) if Path(args.discovery_manifest).exists() else []
    supplementary_dir = Path(args.supplementary_dir)

    accession_by_cohort: dict[str, str] = {}
    for row in discovery_rows:
        cid = row.get("cohort_id", "").strip()
        acc = first_gse(row.get("accession", ""))
        if cid and acc:
            accession_by_cohort[cid] = acc

    supplementary_by_accession: dict[str, dict[str, dict[str, str]]] = {}
    for tsv_path in sorted(supplementary_dir.glob("GSE*.tsv")):
        acc = tsv_path.stem.upper()
        try:
            sup_rows = read_tsv(tsv_path)
        except Exception:
            continue
        by_sample = {}
        for sup_row in sup_rows:
            sid = (sup_row.get("Sample_ID", "") or sup_row.get("sample_id", "")).strip()
            if sid:
                by_sample[sid.upper()] = sup_row
        supplementary_by_accession[acc] = by_sample

    merged_rows: list[dict[str, str]] = []
    for row in rows:
        cohort_id = row.get("cohort_id", "")
        sample_id = row.get("sample_id", "")
        accession = accession_by_cohort.get(cohort_id, first_gse(cohort_id))
        sup_row = supplementary_by_accession.get(accession, {}).get(sample_id.upper(), {})
        sup_text = " ".join(str(v) for v in sup_row.values())
        response_supp = infer_response_from_text(sup_text) if sup_row else ""
        timing_supp = infer_timing_from_text(sup_text) if sup_row else ""
        disease_supp = infer_disease_from_text(sup_text) if sup_row else ""
        response_soft = row.get("response_label", "")
        timing_soft = row.get("timing_category", "")
        disease_soft = row.get("cancer_type", "")

        response_disagree = (
            "true"
            if response_soft.strip() and response_supp.strip() and response_soft.strip().lower() != response_supp.strip().lower()
            else "false"
        )
        timing_disagree = (
            "true"
            if timing_soft.strip() and timing_supp.strip() and timing_soft.strip().lower() != timing_supp.strip().lower()
            else "false"
        )
        disease_disagree = (
            "true"
            if disease_soft.strip() and disease_supp.strip() and disease_soft.strip().lower() != disease_supp.strip().lower()
            else "false"
        )

        merged_rows.append(
            {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "response_label_soft": response_soft,
                "response_label_supplementary": response_supp,
                "timing_category_soft": timing_soft,
                "timing_category_supplementary": timing_supp,
                "disease_soft": disease_soft,
                "disease_supplementary": disease_supp,
                "response_disagreement_flag": response_disagree,
                "timing_disagreement_flag": timing_disagree,
                "disease_disagreement_flag": disease_disagree,
            }
        )

    write_tsv(
        Path(args.out),
        [
            "cohort_id",
            "sample_id",
            "response_label_soft",
            "response_label_supplementary",
            "timing_category_soft",
            "timing_category_supplementary",
            "disease_soft",
            "disease_supplementary",
            "response_disagreement_flag",
            "timing_disagreement_flag",
            "disease_disagreement_flag",
        ],
        merged_rows,
    )
    print(f"Wrote {args.out} ({len(merged_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
