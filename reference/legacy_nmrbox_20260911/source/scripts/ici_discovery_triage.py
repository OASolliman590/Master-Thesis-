#!/usr/bin/env python3
"""Bridge the pan-omics discovery engine to the ICI external-validation spec (080).

Reads the merged `ici_response` candidate roster produced by the pan-omics search
engine (project 47), deduplicates against the cohorts already in the thesis roster,
and applies ICI-specific readiness heuristics (ICB treatment / response label /
baseline timing / RNA modality / human) that the generic engine does not check.

Output is a dataset-centric, ranked triage table for spec 080. Every row is a
CANDIDATE: the hints are text-derived and MUST be confirmed by Stage 01 curation
(real response labels, timing, treatment) before any row becomes validation
evidence. Discovery != evidence.

Stdlib only; runs on any python3.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)

# --- default paths (override via CLI) -------------------------------------
OP_ROOT = Path(
    "/Users/omara.soliman/Desktop/Research/"
    "47-Proteome-Based Biomarkers of Silent Organ Injury due to Chronic "
    "Organophosphorus Exposure_Alzhimers_Parkisons_MS_External_Validation/"
    "op_external_validation"
)
THESIS_REPO = Path(__file__).resolve().parents[1]  # 06_analysis_pipeline_repo
DEFAULT_MERGED = OP_ROOT / "results/manifests/merged_lane2_dataset_candidates.tsv"
DEFAULT_ROSTERS = [
    THESIS_REPO / "configs/discovery_geo_unified_old_plus_timer_manifest.tsv",
    THESIS_REPO / "configs/cohort_id_reconciliation_ledger.tsv",
    THESIS_REPO / "configs/candidate_cohort_roster_combined_active_timer.tsv",
]
DEFAULT_OUT_DIR = (
    THESIS_REPO.parent / "specs/080-external-ici-treated-validation/discovery"
)

# --- accession + concept patterns -----------------------------------------
DATASET_ACC = re.compile(
    r"\b(GSE\d{3,7}|PRJNA\d{4,9}|PRJEB\d{4,9}|PRJDB\d{3,9}|E-MTAB-\d{2,6}|"
    r"E-GEOD-\d{2,7}|SRP\d{5,9}|ERP\d{5,9}|DRP\d{5,9}|PXD\d{5,7}|MTBLS\d{2,6})\b",
    re.I,
)
ANY_ACC = re.compile(r"\b(GSE\d+|PRJNA\d+|PRJEB\d+|PRJDB\d+|SRP\d+|ERP\d+|DRP\d+|"
                     r"E-MTAB-\d+|E-GEOD-\d+|PXD\d+|MTBLS\d+)\b", re.I)

ICB = re.compile(
    r"(anti[\s-]?pd[\s-]?l?1|anti[\s-]?ctla[\s-]?4|\bpd[\s-]?1\b|\bpd[\s-]?l1\b|"
    r"\bctla[\s-]?4\b|nivolumab|pembrolizumab|atezolizumab|durvalumab|avelumab|"
    r"ipilimumab|cemiplimab|tremelimumab|checkpoint|immunotherap|\bici\b|\bicb\b|"
    r"immune[\s-]?checkpoint)",
    re.I,
)
RESPONSE = re.compile(
    r"(responder|non[\s-]?responder|\bresponse\b|recist|durable (clinical )?benefit|"
    r"clinical benefit|resistan|refractory|progress|complete response|"
    r"partial response|stable disease|pathologic(al)? (complete )?response|\bpcr\b|"
    r"\bnr\b|sensitive|outcome)",
    re.I,
)
BASELINE = re.compile(
    r"(pre[\s-]?treatment|baseline|treatment[\s-]?na[iï]ve|pre[\s-]?therapy|"
    r"before treatment|untreated)",
    re.I,
)
RNA = re.compile(r"(rna[\s-]?seq|transcriptom|gene expression|single[\s-]?cell|scrna)", re.I)
PATIENT = re.compile(
    r"(\bpatient|\bcohort|biopsy|clinical|pre[\s-]?treatment|recist|\btrial\b|"
    r"resected|surgical|metastatic)",
    re.I,
)
MODEL = re.compile(
    r"(cell line|cell-line|cell lines|\bmouse\b|\bmice\b|murine|\bgemm\b|"
    r"xenograft|organoid|\bin[\s-]?vitro\b|\bcar[\s-]?t\b|cart\d|car19|"
    r"\bpdx\b|syngeneic|knockout cell)",
    re.I,
)
SINGLECELL = re.compile(r"(single[\s-]?cell|scrna|sc-rna|\bspatial\b|\bcite-?seq\b)", re.I)

DATASET_SOURCES = {
    "gds", "geo", "sra", "bioproject", "biostudies-arrayexpress",
    "biostudies-literature", "project", "ega", "dbgap", "arrayexpress",
    "pride", "massive", "iprox", "metabolights_dataset", "omicsdi",
}

# User decision 2026-07-03: keep these external-validation studies inactive.
# Match both direct GEO rows and SRA/BioProject aliases that point back to the
# same GEO records.
USER_IGNORED_STUDY_ACCESSIONS = {"GSE289743", "GSE284400", "GSE160638"}


def acc_kind(acc: str) -> str:
    a = acc.upper()
    if a.startswith("GSE") or a.startswith("E-GEOD"):
        return "GEO"
    if a.startswith(("PRJ", "SRP", "ERP", "DRP")):
        return "SRA_BioProject"
    if a.startswith("E-MTAB"):
        return "ArrayExpress"
    if a.startswith("PXD"):
        return "PRIDE"
    if a.startswith("MTBLS"):
        return "MetaboLights"
    return "other"


def load_known(rosters: list[Path]) -> set[str]:
    known: set[str] = set()
    for rp in rosters:
        if not rp.exists():
            continue
        with rp.open(newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                for v in row.values():
                    for m in ANY_ACC.findall(v or ""):
                        known.add(m.upper())
    return known


def first_nonempty(values):
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""


def user_ignored_study(acc: str, urls: set[str]) -> bool:
    haystack = " ".join([acc.upper(), *(u.upper() for u in urls)])
    return any(study in haystack for study in USER_IGNORED_STUDY_ACCESSIONS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--merged", type=Path, default=DEFAULT_MERGED)
    ap.add_argument("--roster", type=Path, action="append", default=None)
    ap.add_argument("--context", default="ici_response")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    rosters = args.roster or DEFAULT_ROSTERS
    known = load_known(rosters)

    if not args.merged.exists():
        print(f"ERROR: merged roster not found: {args.merged}", file=sys.stderr)
        return 1

    with args.merged.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh, delimiter="\t")
                if r.get("context") == args.context]

    # aggregate dataset-centric evidence keyed by accession
    agg: dict[str, dict] = defaultdict(lambda: {
        "sources": set(), "titles": [], "descs": [], "modalities": set(),
        "organisms": set(), "queries": set(), "urls": set(),
        "processed": set(), "raw": set(), "n_rows": 0,
    })
    n_literature_only = 0

    for r in rows:
        text_fields = " ".join([
            r.get("accession", ""), r.get("title", ""), r.get("description", ""),
            r.get("extracted_accessions", ""),
        ])
        accs = {m.upper() for m in DATASET_ACC.findall(text_fields)}
        if not accs:
            n_literature_only += 1
            continue
        for acc in accs:
            a = agg[acc]
            a["sources"].add(r.get("source_repository", ""))
            a["titles"].append(r.get("title", ""))
            a["descs"].append(r.get("description", ""))
            if r.get("modality_hint"):
                a["modalities"].add(r["modality_hint"])
            if r.get("organism"):
                a["organisms"].add(r["organism"])
            for q in (r.get("matched_queries", "") or r.get("query", "")).split(";"):
                if q.strip():
                    a["queries"].add(q.strip())
            for u in (r.get("omicsdi_url", ""), r.get("url", "")):
                if u:
                    a["urls"].add(u)
            if (r.get("processed_data_available", "") or "").lower() in ("true", "yes", "1"):
                a["processed"].add("yes")
            if (r.get("raw_data_available", "") or "").lower() in ("true", "yes", "1"):
                a["raw"].add("yes")
            a["n_rows"] += 1

    out_rows = []
    for acc, a in agg.items():
        blob = " ".join(a["titles"] + a["descs"])[:20000]
        icb = bool(ICB.search(blob))
        resp = bool(RESPONSE.search(blob))
        base = bool(BASELINE.search(blob))
        rna = bool(RNA.search(blob)) or bool(
            a["modalities"] & {"transcriptomics", "single_cell_or_perturbation"}
        )
        organism_human = any(("sapiens" in o.lower() or o.lower() == "human")
                             for o in a["organisms"])
        model = bool(MODEL.search(blob))
        human_conf = (organism_human or bool(PATIENT.search(blob))) and not model
        track = "single_cell" if (
            bool(SINGLECELL.search(blob)) or "single_cell_or_perturbation" in a["modalities"]
        ) else "bulk"
        already = acc in known
        score = (3 * icb + 3 * resp + 1 * base + 2 * rna + 1 * human_conf
                 - 2 * model)

        if user_ignored_study(acc, a["urls"]):
            state = "ignored_by_user"
        elif already:
            state = "already_in_thesis_roster"
        elif icb and resp and rna and human_conf:
            state = "new_candidate_high"
        elif icb and rna and human_conf:
            state = "new_candidate_review"
        elif icb and rna and not human_conf:
            state = "model_or_nonhuman"
        elif icb or resp:
            state = "new_candidate_low"
        else:
            state = "off_target"

        out_rows.append({
            "accession": acc,
            "dataset_type": acc_kind(acc),
            "triage_state": state,
            "ici_readiness_score": score,
            "already_in_thesis_roster": "true" if already else "false",
            "treatment_is_icb_hint": "true" if icb else "false",
            "has_response_label_hint": "true" if resp else "false",
            "baseline_timing_hint": "true" if base else "false",
            "rna_modality_hint": "true" if rna else "false",
            "human_confident_hint": "true" if human_conf else "false",
            "model_system_hint": "true" if model else "false",
            "assay_track": track,
            "modality_hint": ";".join(sorted(a["modalities"])) or "unknown",
            "organism": ";".join(sorted(a["organisms"]))[:80],
            "processed_data_available": "yes" if a["processed"] else "",
            "raw_data_available": "yes" if a["raw"] else "",
            "n_source_rows": a["n_rows"],
            "source_repositories": ";".join(sorted(s for s in a["sources"] if s)),
            "matched_queries": ";".join(sorted(a["queries"]))[:300],
            "best_title": first_nonempty(a["titles"])[:200],
            "url": first_nonempty(sorted(a["urls"])),
        })

    state_rank = {
        "new_candidate_high": 0, "ignored_by_user": 1, "new_candidate_review": 2,
        "model_or_nonhuman": 3, "new_candidate_low": 4,
        "already_in_thesis_roster": 5, "off_target": 6,
    }
    # bulk before single_cell within a state (bulk plugs straight into Stage 06/07)
    out_rows.sort(key=lambda r: (state_rank.get(r["triage_state"], 9),
                                 0 if r["assay_track"] == "bulk" else 1,
                                 -int(r["ici_readiness_score"]), r["accession"]))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cols = list(out_rows[0].keys()) if out_rows else []
    out_tsv = args.out_dir / "ici_external_candidates_triaged.tsv"
    with out_tsv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t")
        w.writeheader()
        w.writerows(out_rows)

    # summary
    by_state = defaultdict(int)
    for r in out_rows:
        by_state[r["triage_state"]] += 1
    high = [r for r in out_rows if r["triage_state"] == "new_candidate_high"]

    lines = [
        "# ICI External-Validation Candidate Triage (spec 080)",
        "",
        f"Source roster: `{args.merged}`",
        f"Dedup baseline: {len([p for p in rosters if p.exists()])} local roster file(s); "
        f"{len(known)} known accessions.",
        "",
        "Every row is a CANDIDATE. Hints are text-derived from titles/abstracts and "
        "MUST be confirmed by Stage 01 curation (real response labels, timing, ICB "
        "treatment) before any row becomes validation evidence. Discovery != evidence.",
        "",
        f"- dataset accessions aggregated: **{len(out_rows)}**",
        f"- literature-only rows (no dataset accession, mine later): **{n_literature_only}**",
        "",
        "## By triage state",
        "",
        "| state | count |",
        "|---|---:|",
    ]
    for st in ["new_candidate_high", "ignored_by_user", "new_candidate_review",
               "model_or_nonhuman", "new_candidate_low", "already_in_thesis_roster",
               "off_target"]:
        lines.append(f"| {st} | {by_state.get(st, 0)} |")
    high_bulk = [r for r in high if r["assay_track"] == "bulk"]
    high_sc = [r for r in high if r["assay_track"] == "single_cell"]
    lines += [
        "",
        f"`new_candidate_high` splits into **{len(high_bulk)} bulk** (directly "
        f"pluggable into Stage 06/07) and **{len(high_sc)} single-cell** (need the "
        f"single-cell / pseudobulk path).",
        f"`ignored_by_user` contains **{by_state.get('ignored_by_user', 0)} accession "
        "rows** for the three user-ignored studies (`GSE289743`, `GSE284400`, "
        "`GSE160638`) and their GEO-linked aliases.",
        "",
        f"## Top bulk new_candidate_high ({min(len(high_bulk), 30)} of {len(high_bulk)})",
        "",
        "| accession | type | score | modality | title |",
        "|---|---|---:|---|---|",
    ]
    for r in high_bulk[:30]:
        lines.append(
            f"| {r['accession']} | {r['dataset_type']} | {r['ici_readiness_score']} | "
            f"{r['modality_hint']} | {r['best_title'][:70]} |"
        )
    lines += [
        "",
        "## Next step",
        "",
        "Feed `new_candidate_high` GEO/SRA accessions into Stage 00 retrieval, then "
        "Stage 01 intake curation. NOTE: fix the `_rank_expression_candidate` "
        "series-matrix-over-suppl bug first, or new RNA-seq cohorts will silently "
        "route to 0x0 unreadable matrices.",
        "",
    ]
    out_md = args.out_dir / "ici_external_candidates_summary.md"
    out_md.write_text("\n".join(lines))

    print(f"wrote {out_tsv} ({len(out_rows)} dataset rows)")
    print(f"wrote {out_md}")
    print("triage:", dict(by_state), f"| literature_only={n_literature_only}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
