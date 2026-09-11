from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from ...common.io import read_tsv, write_tsv


VALID_TIMING = {"pre-treatment", "on-treatment", "post-treatment", "unknown"}
VALID_RESPONSE = {"responder", "non_responder", "unknown"}
PATIENT_MANIFEST_FIELDS = [
    "patient_uid",
    "patient_id_raw",
    "cohort_id",
    "cancer_type",
    "therapy_agent",
    "response_label",
    "response_source",
    "has_pre",
    "has_on",
    "has_post",
    "n_timepoints",
    "is_longitudinal",
    "is_stub",
    "pre_sample_ids",
    "on_sample_ids",
    "post_sample_ids",
    "unknown_sample_ids",
]
SAMPLE_ANNOTATION_FIELDS = [
    "cohort_id",
    "sample_id",
    "patient_uid",
    "patient_id_raw",
    "timing_category",
    "response_label",
    "response_source",
    "correction_source",
    "is_stub",
    "cancer_type",
    "therapy_agent",
    "therapy_agent_normalized",
    "therapy_class",
    "include_flag",
    "expression_sample_alias",
]
CLINICAL_FIELDS = [
    "patient_uid",
    "cancer_type",
    "clinical_stage",
    "icb_drug",
    "icb_drug_class",
    "prior_treatment_lines",
    "biopsy_site",
    "dose_schedule",
    "source_field",
]
VALIDATION_FIELDS = ["metric", "expected_value", "observed_value", "status", "notes"]


def _norm_timing(value: str) -> str:
    value = (value or "").strip().replace("_", "-").lower()
    aliases = {
        "pre": "pre-treatment",
        "pretreatment": "pre-treatment",
        "baseline": "pre-treatment",
        "pre-treatment": "pre-treatment",
        "on": "on-treatment",
        "on-treatment": "on-treatment",
        "ontreatment": "on-treatment",
        "post": "post-treatment",
        "post-treatment": "post-treatment",
        "posttreatment": "post-treatment",
    }
    return aliases.get(value, value if value in VALID_TIMING else "unknown")


def _norm_response(value: str) -> str:
    value = (value or "").strip().lower().replace("-", "_")
    if value in VALID_RESPONSE:
        return value
    if value in {"r", "response", "responding", "complete_response", "partial_response", "cr", "pr"}:
        return "responder"
    if value in {"nr", "nonresponse", "non_response", "nonresponder", "pd", "sd"}:
        return "non_responder"
    return "unknown"


def _recist_to_response(recist: str) -> str:
    value = (recist or "").strip().upper().replace("/", "").replace(" ", "")
    if value in {"CR", "PR", "PRCR", "CRPR"}:
        return "responder"
    if value in {"PD", "SD"}:
        return "non_responder"
    return "unknown"


def _rornr_to_response(label: str) -> str:
    value = (label or "").strip().upper().replace("-", "_")
    if value in {"R", "RESPONDER", "RESPONSE"}:
        return "responder"
    if value in {"NR", "NON_RESPONDER", "NONRESPONDER"}:
        return "non_responder"
    return "unknown"


def _pathological_to_response(path_resp: str) -> str:
    value = (path_resp or "").strip().upper()
    if "NMPR" in value or "NON-MPR" in value:
        return "non_responder"
    if "MPR" in value or "PCR" in value:
        return "responder"
    return "unknown"


def parse_gse91061(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.match(r"^(Pt\d+)_(Pre|On)_", txt or "")
    if m:
        parsed["patient_id"] = m.group(1)
        parsed["timing_category"] = "pre-treatment" if m.group(2) == "Pre" else "on-treatment"
    m = re.search(r"\bresponse:\s*(\w+)", txt or "", re.IGNORECASE)
    if m:
        parsed["response_label"] = _recist_to_response(m.group(1))
        parsed["response_source"] = "metadata_recist"
    return parsed


def parse_gse96619(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.match(r"^(Pt\d+)_(baseline|OnTx)", txt or "", re.IGNORECASE)
    if m:
        parsed["patient_id"] = m.group(1)
        parsed["timing_category"] = (
            "pre-treatment" if m.group(2).lower() == "baseline" else "on-treatment"
        )
    return parsed


def parse_gse106128(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.match(
        r"^Patient\s+(\d+)\s+(pre|post|\d+(?:st|nd|rd|th))-vaccination",
        txt or "",
        re.IGNORECASE,
    )
    if m:
        parsed["patient_id"] = f"Patient{m.group(1)}"
        stage = m.group(2).lower()
        if stage == "pre":
            parsed["timing_category"] = "pre-treatment"
        elif stage == "post":
            parsed["timing_category"] = "post-treatment"
        else:
            parsed["timing_category"] = "on-treatment"
    m = re.search(r"dth response:\s*([+\-])", txt or "", re.IGNORECASE)
    if m:
        parsed["response_label"] = "responder" if m.group(1) == "+" else "non_responder"
        parsed["response_source"] = "metadata_dth"
    return parsed


def parse_gse207422(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.search(r"patient:\s*(P\d+)", txt or "", re.IGNORECASE)
    if m:
        parsed["patient_id"] = m.group(1)
    m = re.search(r"sampling_time:\s*([^|]+)", txt or "", re.IGNORECASE)
    if m:
        value = m.group(1).strip().lower()
        if "pre" in value:
            parsed["timing_category"] = "pre-treatment"
        elif "post" in value:
            parsed["timing_category"] = "post-treatment"
    m = re.search(r"pathologic_response:\s*([^|]+)", txt or "", re.IGNORECASE)
    if m:
        parsed["response_label"] = _pathological_to_response(m.group(1))
        parsed["response_source"] = "metadata_pathological_response"
    return parsed


def parse_gse195832(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.match(r"^ScRNA\s+(Pt\d+)\s+(Pre|Post)", txt or "", re.IGNORECASE)
    if m:
        parsed["patient_id"] = m.group(1)
        parsed["timing_category"] = (
            "pre-treatment" if m.group(2).lower() == "pre" else "post-treatment"
        )
    return parsed


def parse_gse115821(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.search(r"\bresponse:\s*([A-Z]+)", txt or "", re.IGNORECASE)
    if m:
        parsed["response_label"] = _rornr_to_response(m.group(1))
        parsed["response_source"] = "metadata_r_nr"
    return parsed


def parse_gse210287(txt: str) -> dict[str, str]:
    return parse_gse115821(txt)


def parse_gse159067(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.search(
        r"best response on immunotherapy \(recist\):\s*(\w+)",
        txt or "",
        re.IGNORECASE,
    )
    if m:
        parsed["response_label"] = _recist_to_response(m.group(1))
        parsed["response_source"] = "metadata_recist"
    return parsed


def parse_gse93157(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    m = re.search(r"best\.resp:\s*(\w+)", txt or "", re.IGNORECASE)
    if m:
        parsed["response_label"] = _recist_to_response(m.group(1))
        parsed["response_source"] = "metadata_recist"
    return parsed


def parse_gse67501(txt: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if re.match(r"anti-PD-1_Response_", txt or "", re.IGNORECASE):
        parsed["response_label"] = "responder"
        parsed["response_source"] = "metadata_sample_name"
    elif re.match(r"anti-PD-1_No_Response_", txt or "", re.IGNORECASE):
        parsed["response_label"] = "non_responder"
        parsed["response_source"] = "metadata_sample_name"
    return parsed


COHORT_PARSERS = {
    "gse91061_melanoma_pd1": parse_gse91061,
    "gse96619_melanoma_pd1": parse_gse96619,
    "gse106128_melanoma_dcs": parse_gse106128,
    "gse207422_nsclc_pd1": parse_gse207422,
    "gse195832_hnscc_pd1": parse_gse195832,
    "gse115821_melanoma_ctla4_pd1": parse_gse115821,
    "gse210287_hnscc_pdl1": parse_gse210287,
    "gse159067_hnscc_pd1_pdl1": parse_gse159067,
    "gse93157_nsclc_pd1": parse_gse93157,
    "gse67501_rcc_pd1": parse_gse67501,
}
PARSER_OVERRIDES_ANNOTATION = {"gse67501_rcc_pd1"}
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
    "gse289583_crc_pd1",
    "gse67501_rcc_pd1",
    "gse78220_melanoma_pd1",
    "gse93157_nsclc_pd1",
}


def _read_optional_tsv(path: Path) -> list[dict[str, str]]:
    return read_tsv(path) if path.exists() else []


def _metadata_text_by_sample(geo_tables_dir: Path, cohort_id: str) -> dict[str, str]:
    rows = _read_optional_tsv(geo_tables_dir / cohort_id / "sample_metadata.tsv")
    return {r.get("sample_id", ""): r.get("metadata_text", "") for r in rows if r.get("sample_id")}


def _is_stub_sample(row: dict[str, str]) -> bool:
    sample_id = row.get("sample_id", "")
    sync_status = row.get("sync_status", "")
    return "__sample_" in sample_id or sample_id.endswith("_SYNC_STUB") or "stub" in sync_status.lower()


def _clean_patient_id(row: dict[str, str]) -> str:
    patient_id = (row.get("patient_id") or row.get("pair_id") or row.get("sample_id") or "").strip()
    if not patient_id:
        patient_id = "unknown_patient"
    cohort_id = row.get("cohort_id", "")
    prefix = f"{cohort_id}__"
    if patient_id.startswith(prefix):
        patient_id = patient_id[len(prefix) :]
    return patient_id


def _patient_uid(cohort_id: str, patient_id_raw: str) -> str:
    return f"{cohort_id}::{patient_id_raw}"


def _is_tumor_sample(row: dict[str, str], metadata_text: str) -> bool:
    specimen = (row.get("specimen_type", "") or "").lower()
    if "caf" in specimen or "fibroblast" in specimen:
        return False
    if re.search(r"Sorted CAF|Fibroblast|sorted from", metadata_text or "", re.IGNORECASE):
        return False
    return True


def _apply_parser(row: dict[str, str], metadata_text: str) -> tuple[dict[str, str], str]:
    cohort_id = row.get("cohort_id", "")
    patient_id_raw = _clean_patient_id(row)
    timing = _norm_timing(row.get("timing_category") or row.get("timing_category_inferred", "unknown"))
    response = _norm_response(row.get("response_label") or row.get("response_label_inferred", "unknown"))
    response_source = row.get("response_label_source") or "annotation_existing"
    correction_source = "sample_manifest"

    parsed: dict[str, str] = {}
    parser = COHORT_PARSERS.get(cohort_id)
    if parser and metadata_text:
        parsed = parser(metadata_text)

    if parsed.get("patient_id"):
        patient_id_raw = parsed["patient_id"]
        correction_source = "metadata_parser"

    if parsed.get("timing_category") and (
        timing == "unknown" or cohort_id in COHORT_PARSERS
    ):
        timing = _norm_timing(parsed["timing_category"])
        correction_source = "metadata_parser"
    elif timing == "unknown" and cohort_id in ALL_PRE_BY_DESIGN:
        timing = "pre-treatment"
        correction_source = "study_design_all_pre"

    parsed_response = _norm_response(parsed.get("response_label", ""))
    if parsed_response != "unknown" and (
        response == "unknown" or cohort_id in PARSER_OVERRIDES_ANNOTATION
    ):
        response = parsed_response
        response_source = parsed.get("response_source", "metadata_parsed")
        correction_source = "metadata_parser"
    elif response == "unknown":
        response_source = "unknown"

    return (
        {
            "patient_id_raw": patient_id_raw,
            "timing_category": timing,
            "response_label": response,
            "response_source": response_source,
        },
        correction_source,
    )


def build_sample_annotations(sample_manifest: Path, geo_tables_dir: Path) -> list[dict[str, object]]:
    rows = read_tsv(sample_manifest)
    metadata_cache: dict[str, dict[str, str]] = {}
    corrected: list[dict[str, object]] = []

    for row in rows:
        cohort_id = row.get("cohort_id", "")
        if cohort_id not in metadata_cache:
            metadata_cache[cohort_id] = _metadata_text_by_sample(geo_tables_dir, cohort_id)
        metadata_text = metadata_cache[cohort_id].get(row.get("sample_id", ""), "")
        parsed, correction_source = _apply_parser(row, metadata_text)
        patient_uid = _patient_uid(cohort_id, parsed["patient_id_raw"])
        corrected.append(
            {
                "cohort_id": cohort_id,
                "sample_id": row.get("sample_id", ""),
                "patient_uid": patient_uid,
                "patient_id_raw": parsed["patient_id_raw"],
                "timing_category": parsed["timing_category"],
                "response_label": parsed["response_label"],
                "response_source": parsed["response_source"],
                "correction_source": correction_source,
                "is_stub": _is_stub_sample(row),
                "cancer_type": row.get("cancer_type", "") or "unknown",
                "therapy_agent": row.get("therapy_agent", "") or "unknown",
                "therapy_agent_normalized": row.get("therapy_agent_normalized", "") or "",
                "therapy_class": row.get("therapy_class", "") or "",
                "include_flag": row.get("include_flag", ""),
                "expression_sample_alias": row.get("expression_sample_alias", ""),
                "is_tumor_sample": _is_tumor_sample(row, metadata_text),
            }
        )
    return corrected


def _pick_patient_response(samples: list[dict[str, object]]) -> tuple[str, str]:
    known = [
        str(s["response_label"])
        for s in samples
        if str(s.get("response_label", "unknown")) in {"responder", "non_responder"}
    ]
    if not known:
        return "unknown", "unknown"
    if len(set(known)) == 1:
        source = next(
            str(s.get("response_source", "annotation_existing"))
            for s in samples
            if str(s.get("response_label")) == known[0]
        )
        return known[0], source
    pre_known = [
        str(s["response_label"])
        for s in samples
        if s.get("timing_category") == "pre-treatment"
        and str(s.get("response_label")) in {"responder", "non_responder"}
    ]
    if pre_known and len(set(pre_known)) == 1:
        return pre_known[0], "pre_treatment_annotation_existing"
    return "unknown", "conflicting_sample_annotations"


def build_patient_manifest(sample_annotations: list[dict[str, object]]) -> list[dict[str, object]]:
    by_patient: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in sample_annotations:
        if row.get("is_tumor_sample") is False:
            continue
        by_patient[str(row["patient_uid"])].append(row)

    patient_rows: list[dict[str, object]] = []
    for patient_uid, samples in sorted(by_patient.items()):
        first = samples[0]
        timing_to_field = {
            "pre-treatment": "pre_sample_ids",
            "on-treatment": "on_sample_ids",
            "post-treatment": "post_sample_ids",
            "unknown": "unknown_sample_ids",
        }
        sample_lists = {field: [] for field in timing_to_field.values()}
        for sample in samples:
            timing = _norm_timing(str(sample.get("timing_category", "unknown")))
            sample_lists[timing_to_field[timing]].append(str(sample.get("sample_id", "")))

        has_pre = bool(sample_lists["pre_sample_ids"])
        has_on = bool(sample_lists["on_sample_ids"])
        has_post = bool(sample_lists["post_sample_ids"])
        n_timepoints = sum([has_pre, has_on, has_post])
        response, response_source = _pick_patient_response(samples)
        patient_rows.append(
            {
                "patient_uid": patient_uid,
                "patient_id_raw": first.get("patient_id_raw", ""),
                "cohort_id": first.get("cohort_id", ""),
                "cancer_type": first.get("cancer_type", "unknown") or "unknown",
                "therapy_agent": first.get("therapy_agent", "unknown") or "unknown",
                "response_label": response,
                "response_source": response_source,
                "has_pre": has_pre,
                "has_on": has_on,
                "has_post": has_post,
                "n_timepoints": n_timepoints,
                "is_longitudinal": n_timepoints > 1,
                "is_stub": any(bool(s.get("is_stub")) for s in samples),
                "pre_sample_ids": "|".join(sample_lists["pre_sample_ids"]),
                "on_sample_ids": "|".join(sample_lists["on_sample_ids"]),
                "post_sample_ids": "|".join(sample_lists["post_sample_ids"]),
                "unknown_sample_ids": "|".join(sample_lists["unknown_sample_ids"]),
            }
        )
    return patient_rows


def _classify_icb_drug(row: dict[str, object]) -> str:
    text = " ".join(
        str(row.get(k, ""))
        for k in ["therapy_agent", "therapy_agent_normalized", "therapy_class"]
    ).lower()
    if not text.strip():
        return "unknown"
    has_pd1 = "pd1" in text or "pd-1" in text or "nivolumab" in text or "pembrolizumab" in text
    has_pdl1 = "pdl1" in text or "pd-l1" in text or "atezolizumab" in text or "durvalumab" in text
    has_ctla4 = "ctla" in text or "ipilimumab" in text or "tremelimumab" in text
    if sum([has_pd1, has_pdl1, has_ctla4]) > 1 or "combo" in text or "+" in text:
        return "COMBO"
    if has_pd1:
        return "PD1"
    if has_pdl1:
        return "PDL1"
    if has_ctla4:
        return "CTLA4"
    if "unknown" in text:
        return "unknown"
    return "OTHER"


def build_patient_clinical_records(
    patient_manifest: list[dict[str, object]],
    sample_annotations: list[dict[str, object]],
) -> list[dict[str, object]]:
    sample_by_patient = defaultdict(list)
    for row in sample_annotations:
        sample_by_patient[str(row["patient_uid"])].append(row)

    rows: list[dict[str, object]] = []
    for patient in patient_manifest:
        patient_uid = str(patient["patient_uid"])
        samples = sample_by_patient.get(patient_uid, [])
        first = samples[0] if samples else patient
        icb_drug = (
            str(first.get("therapy_agent_normalized", "") or first.get("therapy_agent", "") or "unknown")
        )
        rows.append(
            {
                "patient_uid": patient_uid,
                "cancer_type": patient.get("cancer_type", "unknown") or "unknown",
                "clinical_stage": "unknown",
                "icb_drug": icb_drug or "unknown",
                "icb_drug_class": _classify_icb_drug(first),
                "prior_treatment_lines": "unknown",
                "biopsy_site": "unknown",
                "dose_schedule": "unknown",
                "source_field": "sample_manifest_curated",
            }
        )
    return rows


def _summarize_patient_manifest(rows: list[dict[str, object]]) -> dict[str, int]:
    non_stub = [
        r
        for r in rows
        if str(r.get("is_stub", "")).lower() not in {"true", "1"}
        and r.get("is_stub") is not True
    ]
    counts = Counter(str(r.get("response_label", "unknown")) for r in non_stub)
    return {
        "row_count": len(rows),
        "non_stub_patients": len(non_stub),
        "responder_patients": counts.get("responder", 0),
        "non_responder_patients": counts.get("non_responder", 0),
        "unknown_response_patients": counts.get("unknown", 0),
        "longitudinal_patients": sum(
            1 for r in non_stub if str(r.get("is_longitudinal", "")).lower() == "true" or r.get("is_longitudinal") is True
        ),
    }


def build_validation_rows(
    patient_manifest: list[dict[str, object]],
    reference_manifest: Path | None = None,
) -> list[dict[str, object]]:
    observed = _summarize_patient_manifest(patient_manifest)
    reference_rows = read_tsv(reference_manifest) if reference_manifest and reference_manifest.exists() else []
    expected = _summarize_patient_manifest(reference_rows) if reference_rows else {}
    rows: list[dict[str, object]] = []
    for metric, observed_value in observed.items():
        expected_value = expected.get(metric, "")
        if expected_value == "":
            status = "no_reference"
            notes = "reference manifest not available"
        else:
            status = "pass" if int(expected_value) == int(observed_value) else "warn"
            notes = "matches reference" if status == "pass" else "differs from patient_manifest_v1.tsv"
        rows.append(
            {
                "metric": metric,
                "expected_value": expected_value,
                "observed_value": observed_value,
                "status": status,
                "notes": notes,
            }
        )
    return rows


def build_and_write_patient_manifest(
    sample_manifest: Path,
    geo_tables_dir: Path,
    out_dir: Path,
    reference_manifest: Path | None = None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_annotations = build_sample_annotations(sample_manifest, geo_tables_dir)
    patient_rows = build_patient_manifest(sample_annotations)
    clinical_rows = build_patient_clinical_records(patient_rows, sample_annotations)
    validation_rows = build_validation_rows(patient_rows, reference_manifest)

    sample_path = out_dir / "sample_annotations_corrected.tsv"
    patient_path = out_dir / "patient_manifest.tsv"
    clinical_path = out_dir / "patient_clinical_record.tsv"
    validation_path = out_dir / "patient_manifest_validation.tsv"

    write_tsv(sample_path, SAMPLE_ANNOTATION_FIELDS, sample_annotations)
    write_tsv(patient_path, PATIENT_MANIFEST_FIELDS, patient_rows)
    write_tsv(clinical_path, CLINICAL_FIELDS, clinical_rows)
    write_tsv(validation_path, VALIDATION_FIELDS, validation_rows)

    return {
        "sample_annotations": sample_path,
        "patient_manifest": patient_path,
        "patient_clinical_record": clinical_path,
        "patient_manifest_validation": validation_path,
    }
