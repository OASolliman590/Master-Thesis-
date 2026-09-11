"""
spec_patient_manifest — Phase 1 & 3
Parses sample_metadata.tsv for each cohort, corrects patient_id / timing /
response annotations from metadata_text, then pivots to a patient-level manifest.

Outputs:
  results/patient_manifest/sample_annotations_corrected.tsv  — sample-level
  results/patient_manifest/patient_manifest_v1.tsv           — patient-level
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parents[3]
GEO_TABLES   = REPO_ROOT / "results" / "geo_tables"
OUT_DIR      = REPO_ROOT / "results" / "patient_manifest"
GLOBAL_TABLE = GEO_TABLES / "cohort_input_table_all.tsv"

# ---------------------------------------------------------------------------
# Response mappers
# ---------------------------------------------------------------------------

def _recist_to_response(recist: str) -> str:
    r = recist.strip().upper().replace("/", "").replace(" ", "")
    if r in ("CR", "PR", "PRCR", "CRPR"):
        return "responder"
    if r in ("PD", "SD"):
        return "non_responder"
    return "unknown"


def _rornr_to_response(label: str) -> str:
    l = label.strip().upper()
    if l in ("R", "RESPONDER", "RESPONSE"):
        return "responder"
    if l in ("NR", "NON_RESPONDER", "NON-RESPONDER", "NONRESPONDER"):
        return "non_responder"
    return "unknown"


def _pathological_to_response(path_resp: str) -> str:
    """MPR / NMPR pathological response (gse207422). Check NMPR before MPR — 'MPR' ⊂ 'NMPR'."""
    p = path_resp.strip().upper()
    if "NMPR" in p:
        return "non_responder"
    if "MPR" in p or "PCR" in p:
        return "responder"
    return "unknown"


# ---------------------------------------------------------------------------
# Cohort-specific metadata_text parsers
# Each returns a dict with any subset of: patient_id, timing, response_label, response_source
# ---------------------------------------------------------------------------

def parse_gse91061(txt: str) -> dict:
    """Pt1_Pre_AD101148-6 | ... | visit: Pre/On | response: PD"""
    result = {}
    m = re.match(r"^(Pt\d+)_(Pre|On)_", txt)
    if m:
        result["patient_id"] = m.group(1)
        result["timing"] = "pre-treatment" if m.group(2) == "Pre" else "on-treatment"
    m2 = re.search(r"\bresponse:\s*(\w+)", txt)
    if m2:
        result["response_label"] = _recist_to_response(m2.group(1))
        result["response_source"] = "metadata_recist"
    return result


def parse_gse96619(txt: str) -> dict:
    """Pt1_baseline | ... | treatment: pre-treatment/on-treatment"""
    result = {}
    m = re.match(r"^(Pt\d+)_(baseline|OnTx)", txt)
    if m:
        result["patient_id"] = m.group(1)
        result["timing"] = "pre-treatment" if m.group(2) == "baseline" else "on-treatment"
    return result


def parse_gse106128(txt: str) -> dict:
    """Patient 79 pre-vaccination | ... | dth response: +/-"""
    result = {}
    m = re.match(r"^Patient\s+(\d+)\s+(pre|post|\d+(?:st|nd|rd|th))-vaccination", txt, re.IGNORECASE)
    if m:
        result["patient_id"] = f"Patient{m.group(1)}"
        stage = m.group(2).lower()
        if stage == "pre":
            result["timing"] = "pre-treatment"
        elif stage == "post":
            result["timing"] = "post-treatment"
        else:
            result["timing"] = "on-treatment"
    m2 = re.search(r"dth response:\s*([+\-])", txt)
    if m2:
        result["response_label"] = "responder" if m2.group(1) == "+" else "non_responder"
        result["response_source"] = "metadata_dth"
    return result


def parse_gse207422(txt: str) -> dict:
    """BD_immune01 | patient: P01 | sampling_time: Pre-treatment biopsy | pathologic_response: MPR"""
    result = {}
    m = re.search(r"patient:\s*(P\d+)", txt)
    if m:
        result["patient_id"] = m.group(1)
    m2 = re.search(r"sampling_time:\s*([^|]+)", txt)
    if m2:
        st = m2.group(1).strip().lower()
        if "pre" in st:
            result["timing"] = "pre-treatment"
        elif "post" in st:
            result["timing"] = "post-treatment"
        else:
            result["timing"] = "unknown"
    m3 = re.search(r"pathologic_response:\s*([^|]+)", txt)
    if m3:
        result["response_label"] = _pathological_to_response(m3.group(1).strip())
        result["response_source"] = "metadata_pathological_response"
    return result


def parse_gse195832(txt: str) -> dict:
    """ScRNA Pt1 Pre | ... | time point: pre/post"""
    result = {}
    m = re.match(r"^ScRNA\s+(Pt\d+)\s+(Pre|Post)", txt, re.IGNORECASE)
    if m:
        result["patient_id"] = m.group(1)
        result["timing"] = "pre-treatment" if m.group(2).lower() == "pre" else "post-treatment"
    return result


def parse_gse115821(txt: str) -> dict:
    """..._S9 | ... | response: R/NR | ..."""
    result = {}
    m = re.search(r"\bresponse:\s*([A-Z]+)", txt)
    if m:
        result["response_label"] = _rornr_to_response(m.group(1))
        result["response_source"] = "metadata_r_nr"
    return result


def parse_gse210287(txt: str) -> dict:
    """Pre, R [S9] | ... | response: R/NR | ..."""
    result = {}
    m = re.search(r"\bresponse:\s*([A-Z]+)", txt)
    if m:
        result["response_label"] = _rornr_to_response(m.group(1))
        result["response_source"] = "metadata_r_nr"
    return result


def parse_gse159067(txt: str) -> dict:
    """Targeted RNA... | best response on immunotherapy (recist): PD/PR/CR/SD"""
    result = {}
    m = re.search(r"best response on immunotherapy \(recist\):\s*(\w+)", txt, re.IGNORECASE)
    if m:
        result["response_label"] = _recist_to_response(m.group(1))
        result["response_source"] = "metadata_recist"
    return result


def parse_gse93157(txt: str) -> dict:
    """Patient1 | ... | best.resp: CR/PR/SD/PD | ..."""
    result = {}
    m = re.search(r"best\.resp:\s*(\w+)", txt)
    if m:
        result["response_label"] = _recist_to_response(m.group(1))
        result["response_source"] = "metadata_recist"
    return result


def parse_gse67501(txt: str) -> dict:
    """anti-PD-1_Response_rep1 | ... — sample name prefix encodes R vs NR."""
    result = {}
    if re.match(r"anti-PD-1_Response_", txt, re.IGNORECASE):
        result["response_label"] = "responder"
        result["response_source"] = "metadata_sample_name"
    elif re.match(r"anti-PD-1_No_Response_", txt, re.IGNORECASE):
        result["response_label"] = "non_responder"
        result["response_source"] = "metadata_sample_name"
    return result


COHORT_PARSERS = {
    "gse91061_melanoma_pd1":          parse_gse91061,
    "gse96619_melanoma_pd1":          parse_gse96619,
    "gse106128_melanoma_dcs":         parse_gse106128,
    "gse207422_nsclc_pd1":            parse_gse207422,
    "gse195832_hnscc_pd1":            parse_gse195832,
    "gse115821_melanoma_ctla4_pd1":   parse_gse115821,
    "gse210287_hnscc_pdl1":           parse_gse210287,
    "gse159067_hnscc_pd1_pdl1":       parse_gse159067,
    "gse93157_nsclc_pd1":             parse_gse93157,
    "gse67501_rcc_pd1":               parse_gse67501,
}

# Cohorts where the existing response_label_inferred is known-wrong;
# the parser result overrides it regardless of existing annotation value.
PARSER_OVERRIDES_ANNOTATION = {"gse67501_rcc_pd1"}

# Cross-sectional cohorts where every sample is pre-treatment by study design
ALL_PRE_BY_DESIGN = {
    "gse100797_melanoma_act",
    "gse115821_melanoma_ctla4_pd1",
    "gse126044_nsclc_pd1",
    "gse126044_srp183455_nsclc_pd1",
    "gse135222_srp217040_nsclc_pdl1",
    "gse136961_prjna564119_nsclc_pd1",
    "gse145996_srp250849_melanoma_pd1",
    "gse159067_hnscc_pd1_pdl1",
    "gse176307_urothelial_pd1",
    "gse210287_hnscc_pdl1",
    "gse215011_hcc_nivolumab",
    "gse218989_lung_pd1_pdl1",
    "gse235919_mcrc_durvalumab_tremelimumab_mfolfox6",
    "gse67501_rcc_pd1",
    "gse78220_melanoma_pd1",
    "gse93157_nsclc_pd1",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_global_table() -> tuple[list[dict], dict[str, list[dict]]]:
    """
    Returns (all_rows, by_cohort) where by_cohort maps cohort_id → list of row dicts.
    Using a list preserves cohorts that share sample_ids (e.g. gse126044 variants).
    """
    all_rows = []
    by_cohort: dict[str, list[dict]] = defaultdict(list)
    with open(GLOBAL_TABLE, newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            all_rows.append(row)
            by_cohort[row["cohort_id"]].append(row)
    return all_rows, by_cohort


def load_sample_metadata(cohort_id: str) -> list[dict]:
    path = GEO_TABLES / cohort_id / "sample_metadata.tsv"
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _is_stub(rows: list[dict]) -> bool:
    return len(rows) == 1 and "__sample_" in rows[0].get("sample_id", "")


# ---------------------------------------------------------------------------
# Sample resolution
# ---------------------------------------------------------------------------

def resolve_sample(txt: str, global_row: dict) -> dict:
    cohort_id    = global_row["cohort_id"]
    sample_id    = global_row["sample_id"]
    patient_id   = global_row["patient_id"]
    timing       = global_row["timing_category_inferred"]
    response     = global_row["response_label_inferred"]
    cancer_type  = global_row.get("cancer_type", "")
    therapy      = global_row.get("therapy_agent", "")
    response_src = "annotation_existing"

    parsed = {}
    if cohort_id in COHORT_PARSERS and txt:
        parsed = COHORT_PARSERS[cohort_id](txt)

    if "patient_id" in parsed:
        patient_id = parsed["patient_id"]

    if "timing" in parsed and (timing == "unknown" or cohort_id in COHORT_PARSERS):
        timing = parsed["timing"]
    elif timing == "unknown" and cohort_id in ALL_PRE_BY_DESIGN:
        timing = "pre-treatment"

    if "response_label" in parsed and (
        response == "unknown" or cohort_id in PARSER_OVERRIDES_ANNOTATION
    ):
        response     = parsed["response_label"]
        response_src = parsed.get("response_source", "metadata_parsed")
    elif response != "unknown":
        response_src = "annotation_existing"
    else:
        response_src = "unknown"

    is_tumor = True
    if txt and re.search(r"Sorted CAF|Fibroblast|sorted from", txt, re.IGNORECASE):
        is_tumor = False

    return {
        "sample_id":       sample_id,
        "patient_id":      f"{cohort_id}__{patient_id}",
        "patient_id_raw":  patient_id,
        "cohort_id":       cohort_id,
        "cancer_type":     cancer_type,
        "therapy_agent":   therapy,
        "response_label":  response,
        "timing":          timing,
        "response_source": response_src,
        "is_tumor_sample": is_tumor,
        "is_stub":         False,
    }


# ---------------------------------------------------------------------------
# Build sample table
# ---------------------------------------------------------------------------

def build_sample_table(by_cohort: dict[str, list[dict]]) -> list[dict]:
    resolved = []
    for cohort_id in sorted(by_cohort):
        global_cohort_rows = by_cohort[cohort_id]
        meta_rows = load_sample_metadata(cohort_id)

        # Build lookup: sample_id → metadata_text for this cohort
        meta_by_sid: dict[str, str] = {}
        if meta_rows and not _is_stub(meta_rows):
            for m in meta_rows:
                meta_by_sid[m["sample_id"]] = m.get("metadata_text", "")

        all_stub = _is_stub(global_cohort_rows) or (
            len(global_cohort_rows) == 1 and "__sample_" in global_cohort_rows[0]["sample_id"]
        )

        if all_stub:
            # No per-sample data available; include a single placeholder
            g = global_cohort_rows[0]
            row = resolve_sample("", g)
            row["is_stub"] = True
            resolved.append(row)
            continue

        for grow in global_cohort_rows:
            sid = grow["sample_id"]
            if "__sample_" in sid:
                continue  # skip any stub rows mixed in
            txt = meta_by_sid.get(sid, "")
            resolved.append(resolve_sample(txt, grow))

    return resolved


# ---------------------------------------------------------------------------
# Patient manifest pivot
# ---------------------------------------------------------------------------

def build_patient_manifest(sample_table: list[dict]) -> list[dict]:
    patients: dict[str, dict] = {}

    for s in sample_table:
        if not s["is_tumor_sample"]:
            continue
        pid    = s["patient_id"]
        timing = s["timing"]

        if pid not in patients:
            patients[pid] = {
                "patient_uid":        pid,
                "patient_id_raw":     s["patient_id_raw"],
                "cohort_id":          s["cohort_id"],
                "cancer_type":        s["cancer_type"],
                "therapy_agent":      s["therapy_agent"],
                "response_label":     s["response_label"],
                "response_source":    s["response_source"],
                "is_stub":            s["is_stub"],
                "pre_sample_ids":     [],
                "on_sample_ids":      [],
                "post_sample_ids":    [],
                "unknown_sample_ids": [],
            }

        p = patients[pid]

        # Propagate known response across timepoints of the same patient
        if p["response_label"] == "unknown" and s["response_label"] != "unknown":
            p["response_label"]  = s["response_label"]
            p["response_source"] = s["response_source"]

        if timing == "pre-treatment":
            p["pre_sample_ids"].append(s["sample_id"])
        elif timing == "on-treatment":
            p["on_sample_ids"].append(s["sample_id"])
        elif timing == "post-treatment":
            p["post_sample_ids"].append(s["sample_id"])
        else:
            p["unknown_sample_ids"].append(s["sample_id"])

    rows = []
    for p in patients.values():
        has_pre  = len(p["pre_sample_ids"]) > 0
        has_on   = len(p["on_sample_ids"]) > 0
        has_post = len(p["post_sample_ids"]) > 0
        n_tp     = sum([has_pre, has_on, has_post])
        rows.append({
            "patient_uid":        p["patient_uid"],
            "patient_id_raw":     p["patient_id_raw"],
            "cohort_id":          p["cohort_id"],
            "cancer_type":        p["cancer_type"],
            "therapy_agent":      p["therapy_agent"],
            "response_label":     p["response_label"],
            "response_source":    p["response_source"],
            "has_pre":            has_pre,
            "has_on":             has_on,
            "has_post":           has_post,
            "n_timepoints":       n_tp,
            "is_longitudinal":    n_tp > 1,
            "is_stub":            p["is_stub"],
            "pre_sample_ids":     ",".join(p["pre_sample_ids"]),
            "on_sample_ids":      ",".join(p["on_sample_ids"]),
            "post_sample_ids":    ",".join(p["post_sample_ids"]),
            "unknown_sample_ids": ",".join(p["unknown_sample_ids"]),
        })

    rows.sort(key=lambda r: (r["cohort_id"], r["patient_id_raw"]))
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_tsv(rows: list[dict], path: Path) -> None:
    if not rows:
        print(f"WARNING: no rows for {path}", file=sys.stderr)
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):>5} rows → {path.name}")


def print_summary(patient_rows: list[dict]) -> None:
    real = [r for r in patient_rows if not r["is_stub"]]
    total      = len(real)
    responders = sum(1 for r in real if r["response_label"] == "responder")
    non_resp   = sum(1 for r in real if r["response_label"] == "non_responder")
    unk_resp   = sum(1 for r in real if r["response_label"] == "unknown")
    long_      = sum(1 for r in real if r["is_longitudinal"])
    pre_only   = sum(1 for r in real if r["has_pre"] and not r["has_on"] and not r["has_post"])
    on_only    = sum(1 for r in real if r["has_on"] and not r["has_pre"] and not r["has_post"])
    post_only  = sum(1 for r in real if r["has_post"] and not r["has_pre"] and not r["has_on"])

    print("\n=== Patient Manifest Summary (non-stub) ===")
    print(f"Total patients:      {total}")
    print(f"  Responders:        {responders}")
    print(f"  Non-responders:    {non_resp}")
    print(f"  Unknown response:  {unk_resp}")
    print(f"Longitudinal (>1 tp):{long_}")
    print(f"  Pre-only:          {pre_only}")
    print(f"  On-only:           {on_only}")
    print(f"  Post-only:         {post_only}")
    print()

    cohorts: dict[str, list] = defaultdict(list)
    for r in real:
        cohorts[r["cohort_id"]].append(r)

    stubs = [r for r in patient_rows if r["is_stub"]]

    print(f"{'cohort_id':<55} {'pts':>4} {'R':>4} {'NR':>4} {'unk':>4} {'long':>5} {'pre':>5} {'on':>4} {'post':>5}")
    print("-" * 97)
    for cid in sorted(cohorts):
        pts = cohorts[cid]
        r_  = sum(1 for p in pts if p["response_label"] == "responder")
        nr_ = sum(1 for p in pts if p["response_label"] == "non_responder")
        u_  = sum(1 for p in pts if p["response_label"] == "unknown")
        lng = sum(1 for p in pts if p["is_longitudinal"])
        pre = sum(1 for p in pts if p["has_pre"])
        on  = sum(1 for p in pts if p["has_on"])
        pst = sum(1 for p in pts if p["has_post"])
        print(f"{cid:<55} {len(pts):>4} {r_:>4} {nr_:>4} {u_:>4} {lng:>5} {pre:>5} {on:>4} {pst:>5}")

    if stubs:
        print(f"\nStub cohorts (no per-sample metadata decomposed): {len(stubs)}")
        for s in stubs:
            print(f"  {s['cohort_id']}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading global sample table...")
    _, by_cohort = load_global_table()

    print("Resolving per-sample annotations from metadata_text...")
    sample_table = build_sample_table(by_cohort)

    print("Building patient-level manifest...")
    patient_rows = build_patient_manifest(sample_table)

    write_tsv(sample_table, OUT_DIR / "sample_annotations_corrected.tsv")
    write_tsv(patient_rows, OUT_DIR / "patient_manifest_v1.tsv")

    print_summary(patient_rows)


if __name__ == "__main__":
    main()
