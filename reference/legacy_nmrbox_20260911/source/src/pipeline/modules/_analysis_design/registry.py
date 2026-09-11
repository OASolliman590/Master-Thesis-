from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from ...common.expression import load_expression_matrix, resolve_primary_expression_path
from ...common.io import parse_bool, write_tsv
from .._01_dataset_intake.assay_detect import classify_expression_matrix


SAMPLE_FIELDNAMES = [
    "cohort_id",
    "sample_id",
    "patient_id",
    "pair_id",
    "timing_category",
    "response_label",
    "include_flag",
    "analysis_eligible",
    "analysis_exclusion_reason",
    "assay_type",
    "input_class",
    "drug_group",
    "therapy_class_raw",
    "therapy_agent_raw",
    "cancer_group",
    "cancer_type_raw",
    "analysis_role",
]

REGISTRY_FIELDNAMES = [
    "analysis_id",
    "analysis_family",
    "legacy_contrast_alias",
    "interpretation_label",
    "contrast_type",
    "timing_scope",
    "pairing_required",
    "drug_scope",
    "cancer_scope",
    "raw_scope_label",
    "case_definition",
    "control_definition",
    "n_cohorts_total",
    "n_cohorts_eligible",
    "n_case_samples",
    "n_control_samples",
    "n_pairs_case",
    "n_pairs_control",
    "feasibility_status",
    "blocker_reason",
    "priority_status",
    "notes",
]

MEMBERSHIP_FIELDNAMES = [
    "analysis_id",
    "cohort_id",
    "sample_id",
    "patient_id",
    "pair_id",
    "timing_category",
    "response_label",
    "membership_role",
    "drug_group",
    "therapy_class_raw",
    "therapy_agent_raw",
    "cancer_group",
    "cancer_type_raw",
    "assay_type",
    "input_class",
]

TIMING_TO_LEGACY = {
    "pre-treatment": "PRE_RESPONSE",
    "on-treatment": "ON_RESPONSE",
    "post-treatment": "POST_RESPONSE",
}

TIMING_LABEL = {
    "pre-treatment": "PRE_TREATMENT",
    "on-treatment": "ON_TREATMENT",
    "post-treatment": "POST_TREATMENT",
}

TIMING_INTERPRETATION = {
    "pre-treatment": "baseline predictive responder association",
    "on-treatment": "early pharmacodynamic responder association",
    "post-treatment": "post-treatment response-state association",
}

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
HARD_EXCLUDED_ASSAYS = {"methylation_beta", "microarray_probe_matrix", "unreadable"}
ASSAY_TYPE_ALIASES = {
    "rlog_vst_or_log": "rlog_vst",
    "microarray_intensity_or_log": "microarray_intensity",
    "processed_matrix": "normalized_other",
    "already_log": "log_normalized",
}


def normalize_timing(value: str) -> str:
    raw = (value or "").strip().lower().replace("_", "-")
    raw = re.sub(r"\s+", " ", raw)
    if raw in {"pre", "baseline", "pretreatment", "pre-treatment", "before treatment"}:
        return "pre-treatment"
    if raw in {"on", "on treatment", "on-treatment", "during treatment"}:
        return "on-treatment"
    if raw in {"post", "post treatment", "post-treatment", "after treatment"}:
        return "post-treatment"
    return raw or "unknown"


def normalize_response(value: str) -> str:
    raw = (value or "").strip().lower().replace("-", "_")
    if raw in {"responder", "response", "r", "cr", "pr"}:
        return "responder"
    if raw in {"non_responder", "nonresponder", "no_response", "nr", "sd", "pd"}:
        return "non_responder"
    return "unknown"


def normalize_drug_group(therapy_class: str, therapy_agent: str = "", therapy_combination: str = "") -> str:
    raw = f"{therapy_class or ''} {therapy_agent or ''} {therapy_combination or ''}".lower()
    compact = raw.replace("-", "").replace("/", "").replace(" ", "")
    has_pd1 = any(tok in compact for tok in ["pd1", "nivolumab", "pembrolizumab", "cemiplimab"])
    has_pdl1 = any(tok in compact for tok in ["pdl1", "atezolizumab", "durvalumab", "avelumab"])
    has_ctla4 = any(tok in compact for tok in ["ctla4", "ipilimumab", "tremelimumab"])
    has_combination_marker = any(marker in raw for marker in ["combination", "+", " plus "])
    has_ici = has_pd1 or has_pdl1 or has_ctla4 or "checkpoint" in raw or "ici" in raw
    if (has_combination_marker and has_ici) or sum([has_pd1 or has_pdl1, has_ctla4]) >= 2:
        return "ICI_COMBINATION"
    if has_pdl1:
        return "PD_L1"
    if has_pd1:
        return "PD_1"
    if has_ctla4:
        return "CTLA_4"
    if "monotherapy" in raw or "ici" in raw:
        return "ICI_MONOTHERAPY"
    return "UNKNOWN"


def normalize_cancer_group(cancer_type: str) -> str:
    raw = (cancer_type or "").strip().lower()
    if not raw:
        return "UNKNOWN"
    if "melanoma" in raw:
        return "MELANOMA"
    if "nsclc" in raw or "non small" in raw or "non-small" in raw or "lung" in raw:
        return "NSCLC_LUNG"
    if "head and neck" in raw or "hnscc" in raw or "hpv-positive" in raw:
        return "HNSCC"
    if "urothelial" in raw or "bladder" in raw:
        return "UROTHELIAL"
    if "renal" in raw or raw == "rcc":
        return "RCC"
    if any(tok in raw for tok in ["colorectal", "gastric", "stomach", "hepatocellular", "hcc"]):
        return "GI_HCC"
    return "OTHER"


def _clean(value: str) -> str:
    return (value or "").strip()


def _canonical_assay_type(raw: str) -> str:
    value = _clean(raw).lower().replace("-", "_").replace(" ", "_")
    value = ASSAY_TYPE_ALIASES.get(value, value)
    return value if value in ASSAY_TYPE_ALLOWED else ""


def _declared_assay_type(row: dict[str, str]) -> str:
    override = _canonical_assay_type(row.get("assay_type_override", ""))
    if override:
        return override
    return _canonical_assay_type(row.get("assay_type", ""))


def _stage06_assay_type(row: dict[str, str]) -> str:
    declared = _declared_assay_type(row)
    if declared:
        return declared
    input_class = _clean(row.get("input_class", "")).lower()
    if input_class == "raw_counts":
        return "raw_counts"
    if input_class in {"fastq", "processed_matrix"}:
        return "normalized_other"
    return "unreadable"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper()).strip("_")
    return slug or "UNKNOWN"


def _sample_key(row: dict[str, str]) -> tuple[str, str]:
    return (_clean(row.get("cohort_id", "")), _clean(row.get("sample_id", "")))


def _manifest_exclusion_is_global(reason: str) -> bool:
    tokens = [
        token.strip()
        for token in re.split(r"[;|]", reason or "")
        if token.strip()
    ]
    if not tokens:
        return True
    legacy_timing_only = {
        "timing_not_pre_treatment",
        "post_treatment_excluded_from_pre_response",
    }
    return not all(token in legacy_timing_only for token in tokens)


def normalize_sample_rows(
    rows: list[dict[str, str]],
    *,
    missing_expression_cohorts: set[str] | None = None,
    cohort_assay_overrides: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    missing_expression_cohorts = missing_expression_cohorts or set()
    cohort_assay_overrides = cohort_assay_overrides or {}
    out: list[dict[str, str]] = []
    for row in rows:
        cohort_id = _clean(row.get("cohort_id", ""))
        assay_type = cohort_assay_overrides.get(cohort_id, "") or _stage06_assay_type(row)
        timing = normalize_timing(row.get("timing_category", ""))
        response = normalize_response(row.get("response_label", ""))
        sync_status = _clean(row.get("sync_status", ""))
        include_flag_bool = parse_bool(row.get("include_flag", "true"), default=True)
        manifest_exclusion_reason = _clean(row.get("exclude_reason", ""))
        analysis_exclusion_reason = ""
        if cohort_id == "gse126044_srp183455_nsclc_pd1":
            analysis_exclusion_reason = "duplicate_gse126044_deduped"
        elif cohort_id.startswith("gse165278"):
            analysis_exclusion_reason = "excluded_no_responder_arm"
        elif assay_type in HARD_EXCLUDED_ASSAYS:
            analysis_exclusion_reason = f"excluded_assay_type:{assay_type}"
        elif not include_flag_bool and _manifest_exclusion_is_global(manifest_exclusion_reason):
            analysis_exclusion_reason = manifest_exclusion_reason or "manifest_include_flag_false"
        elif cohort_id in missing_expression_cohorts:
            analysis_exclusion_reason = "missing_expression_file"
        elif sync_status == "added_cohort_stub_no_sample_rows":
            analysis_exclusion_reason = "sync_stub_no_sample_rows"
        elif not _clean(row.get("sample_id", "")):
            analysis_exclusion_reason = "missing_sample_id"

        therapy_class = _clean(row.get("therapy_class", ""))
        therapy_agent = _clean(row.get("therapy_agent_normalized", "") or row.get("therapy_agent", ""))
        therapy_combination = _clean(row.get("therapy_combination_final", ""))
        cancer_type = _clean(row.get("cancer_type", ""))
        include_flag = str(include_flag_bool).lower()
        out.append(
            {
                "cohort_id": cohort_id,
                "sample_id": _clean(row.get("sample_id", "")),
                "patient_id": _clean(row.get("patient_id", "") or row.get("patient_uid", "")),
                "pair_id": _clean(row.get("pair_id", "") or row.get("patient_id", "") or row.get("patient_uid", "")),
                "timing_category": timing,
                "response_label": response,
                "include_flag": include_flag,
                "analysis_eligible": "false" if analysis_exclusion_reason else "true",
                "analysis_exclusion_reason": analysis_exclusion_reason,
                "assay_type": assay_type,
                "input_class": _clean(row.get("input_class", "")),
                "drug_group": normalize_drug_group(therapy_class, therapy_agent, therapy_combination),
                "therapy_class_raw": therapy_class,
                "therapy_agent_raw": therapy_agent,
                "cancer_group": normalize_cancer_group(cancer_type),
                "cancer_type_raw": cancer_type,
                "analysis_role": _clean(row.get("analysis_role", "")),
            }
        )
    return sorted(out, key=lambda r: (r["cohort_id"], r["sample_id"]))


def _eligible_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("analysis_eligible") == "true"
        and row.get("response_label") in {"responder", "non_responder"}
    ]


def _cohort_arm_counts(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[row["cohort_id"]][row["response_label"]] += 1
    return counts


def _feasible_cohorts(
    rows: list[dict[str, str]],
    *,
    min_case_samples: int,
    min_control_samples: int,
) -> set[str]:
    counts = _cohort_arm_counts(rows)
    return {
        cohort
        for cohort, counter in counts.items()
        if counter["responder"] >= min_case_samples and counter["non_responder"] >= min_control_samples
    }


def _response_membership_rows(analysis_id: str, rows: list[dict[str, str]], feasible_cohorts: set[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        if row["cohort_id"] not in feasible_cohorts:
            continue
        out.append(
            {
                "analysis_id": analysis_id,
                "cohort_id": row["cohort_id"],
                "sample_id": row["sample_id"],
                "patient_id": row["patient_id"],
                "pair_id": row["pair_id"],
                "timing_category": row["timing_category"],
                "response_label": row["response_label"],
                "membership_role": "case" if row["response_label"] == "responder" else "control",
                "drug_group": row["drug_group"],
                "therapy_class_raw": row["therapy_class_raw"],
                "therapy_agent_raw": row["therapy_agent_raw"],
                "cancer_group": row["cancer_group"],
                "cancer_type_raw": row["cancer_type_raw"],
                "assay_type": row["assay_type"],
                "input_class": row["input_class"],
            }
        )
    return out


def _registry_row(
    *,
    analysis_id: str,
    analysis_family: str,
    legacy_contrast_alias: str,
    interpretation_label: str,
    contrast_type: str,
    timing_scope: str,
    pairing_required: bool,
    drug_scope: str,
    cancer_scope: str,
    raw_scope_label: str,
    case_definition: str,
    control_definition: str,
    n_cohorts_total: int,
    n_cohorts_eligible: int,
    n_case_samples: int,
    n_control_samples: int,
    n_pairs_case: int = 0,
    n_pairs_control: int = 0,
    notes: str = "",
) -> dict[str, str]:
    blockers: list[str] = []
    if n_cohorts_eligible == 0:
        blockers.append("no_cohort_passes_arm_gates")
    if n_case_samples == 0 and n_pairs_case == 0:
        blockers.append("no_responder_arm")
    if n_control_samples == 0 and n_pairs_control == 0:
        blockers.append("no_non_responder_arm")
    feasible = not blockers
    return {
        "analysis_id": analysis_id,
        "analysis_family": analysis_family,
        "legacy_contrast_alias": legacy_contrast_alias,
        "interpretation_label": interpretation_label,
        "contrast_type": contrast_type,
        "timing_scope": timing_scope,
        "pairing_required": "true" if pairing_required else "false",
        "drug_scope": drug_scope,
        "cancer_scope": cancer_scope,
        "raw_scope_label": raw_scope_label,
        "case_definition": case_definition,
        "control_definition": control_definition,
        "n_cohorts_total": str(n_cohorts_total),
        "n_cohorts_eligible": str(n_cohorts_eligible),
        "n_case_samples": str(n_case_samples),
        "n_control_samples": str(n_control_samples),
        "n_pairs_case": str(n_pairs_case),
        "n_pairs_control": str(n_pairs_control),
        "feasibility_status": "feasible" if feasible else "blocked",
        "blocker_reason": ";".join(blockers),
        "priority_status": "co_equal_top_level",
        "notes": notes,
    }


def _add_response_candidate(
    *,
    registry_rows: list[dict[str, str]],
    membership_rows: list[dict[str, str]],
    rows: list[dict[str, str]],
    analysis_id: str,
    analysis_family: str,
    timing: str,
    drug_scope: str,
    cancer_scope: str,
    raw_scope_label: str,
    interpretation_label: str,
    min_case_samples: int,
    min_control_samples: int,
    min_cohorts: int,
) -> None:
    scoped = [r for r in _eligible_rows(rows) if r["timing_category"] == timing]
    total_cohorts = {r["cohort_id"] for r in scoped}
    feasible_cohorts = _feasible_cohorts(
        scoped,
        min_case_samples=min_case_samples,
        min_control_samples=min_control_samples,
    )
    if len(feasible_cohorts) < min_cohorts:
        feasible_cohorts = set()
    member_rows = _response_membership_rows(analysis_id, scoped, feasible_cohorts)
    n_case = sum(1 for r in member_rows if r["membership_role"] == "case")
    n_control = sum(1 for r in member_rows if r["membership_role"] == "control")
    registry_rows.append(
        _registry_row(
            analysis_id=analysis_id,
            analysis_family=analysis_family,
            legacy_contrast_alias=TIMING_TO_LEGACY[timing],
            interpretation_label=interpretation_label,
            contrast_type="response_cross_sectional",
            timing_scope=timing,
            pairing_required=False,
            drug_scope=drug_scope,
            cancer_scope=cancer_scope,
            raw_scope_label=raw_scope_label,
            case_definition=f"{timing} responder",
            control_definition=f"{timing} non_responder",
            n_cohorts_total=len(total_cohorts),
            n_cohorts_eligible=len(feasible_cohorts),
            n_case_samples=n_case,
            n_control_samples=n_control,
            notes="timing-specific unpaired response contrast",
        )
    )
    if feasible_cohorts:
        membership_rows.extend(member_rows)


def _after_timing_from_scope(scope: str) -> str:
    if scope == "pre-to-on-treatment":
        return "on-treatment"
    if scope == "pre-to-post-treatment":
        return "post-treatment"
    raise ValueError(f"Unsupported delta scope: {scope}")


def _delta_pairs(rows: list[dict[str, str]], after_timing: str) -> list[tuple[dict[str, str], dict[str, str], str]]:
    by_pair: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in _eligible_rows(rows):
        pair_id = row.get("pair_id", "")
        if row.get("cohort_id", "") and pair_id:
            by_pair[(row["cohort_id"], pair_id)].append(row)

    pairs: list[tuple[dict[str, str], dict[str, str], str]] = []
    for _, pair_rows in sorted(by_pair.items()):
        pre = [r for r in pair_rows if r["timing_category"] == "pre-treatment"]
        after = [r for r in pair_rows if r["timing_category"] == after_timing]
        responses = {r["response_label"] for r in pair_rows if r["response_label"] in {"responder", "non_responder"}}
        if len(pre) != 1 or len(after) != 1 or len(responses) != 1:
            continue
        response = next(iter(responses))
        pairs.append((pre[0], after[0], response))
    return pairs


def _add_delta_candidate(
    *,
    registry_rows: list[dict[str, str]],
    membership_rows: list[dict[str, str]],
    rows: list[dict[str, str]],
    analysis_id: str,
    timing_scope: str,
    min_case_samples: int,
    min_control_samples: int,
    min_cohorts: int,
) -> None:
    after_timing = _after_timing_from_scope(timing_scope)
    pairs = _delta_pairs(rows, after_timing)
    by_cohort: dict[str, Counter[str]] = defaultdict(Counter)
    for pre, _, response in pairs:
        by_cohort[pre["cohort_id"]][response] += 1
    feasible_cohorts = {
        cohort
        for cohort, counts in by_cohort.items()
        if counts["responder"] >= min_case_samples and counts["non_responder"] >= min_control_samples
    }
    if len(feasible_cohorts) < min_cohorts:
        feasible_cohorts = set()

    n_case_pairs = 0
    n_control_pairs = 0
    candidate_members: list[dict[str, str]] = []
    for pre, after, response in pairs:
        if pre["cohort_id"] not in feasible_cohorts:
            continue
        role_prefix = "case" if response == "responder" else "control"
        if response == "responder":
            n_case_pairs += 1
        else:
            n_control_pairs += 1
        for suffix, row in [("pre", pre), ("after", after)]:
            candidate_members.append(
                {
                    "analysis_id": analysis_id,
                    "cohort_id": row["cohort_id"],
                    "sample_id": row["sample_id"],
                    "patient_id": row["patient_id"],
                    "pair_id": row["pair_id"],
                    "timing_category": row["timing_category"],
                    "response_label": response,
                    "membership_role": f"{role_prefix}_{suffix}",
                    "drug_group": row["drug_group"],
                    "therapy_class_raw": row["therapy_class_raw"],
                    "therapy_agent_raw": row["therapy_agent_raw"],
                    "cancer_group": row["cancer_group"],
                    "cancer_type_raw": row["cancer_type_raw"],
                    "assay_type": row["assay_type"],
                    "input_class": row["input_class"],
                }
            )

    registry_rows.append(
        _registry_row(
            analysis_id=analysis_id,
            analysis_family="DELTA_RESPONSE",
            legacy_contrast_alias="TREATMENT_DELTA",
            interpretation_label="paired treatment-induced change by responder status",
            contrast_type="paired_delta_response",
            timing_scope=timing_scope,
            pairing_required=True,
            drug_scope="ALL",
            cancer_scope="ALL",
            raw_scope_label=timing_scope,
            case_definition=f"responder {timing_scope} paired delta",
            control_definition=f"non_responder {timing_scope} paired delta",
            n_cohorts_total=len(by_cohort),
            n_cohorts_eligible=len(feasible_cohorts),
            n_case_samples=n_case_pairs * 2,
            n_control_samples=n_control_pairs * 2,
            n_pairs_case=n_case_pairs,
            n_pairs_control=n_control_pairs,
            notes="paired only; unpaired after-treatment samples excluded",
        )
    )
    if feasible_cohorts:
        membership_rows.extend(candidate_members)


def build_analysis_design(
    rows: list[dict[str, str]],
    *,
    min_case_samples: int = 2,
    min_control_samples: int = 2,
    min_cohorts: int = 1,
    expression_manifest: Path | None = None,
    downloads_root: Path | None = None,
    check_expression_readiness: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], str]:
    missing_expression_cohorts: set[str] = set()
    cohort_assay_overrides: dict[str, str] = {}
    if check_expression_readiness and expression_manifest and downloads_root:
        for cohort_id in sorted({_clean(r.get("cohort_id", "")) for r in rows if _clean(r.get("cohort_id", ""))}):
            expr_path = resolve_primary_expression_path(cohort_id, expression_manifest, downloads_root)
            if expr_path is None or not expr_path.exists():
                missing_expression_cohorts.add(cohort_id)
                continue
            cohort_rows = [r for r in rows if _clean(r.get("cohort_id", "")) == cohort_id]
            declared = _stage06_assay_type(cohort_rows[0]) if cohort_rows else "unreadable"
            explicit_assay = _declared_assay_type(cohort_rows[0]) if cohort_rows else "unreadable"
            if declared in {"unreadable", "normalized_other", "raw_counts_suspect"} and explicit_assay not in HARD_EXCLUDED_ASSAYS:
                matrix = load_expression_matrix(expr_path)
                detected = classify_expression_matrix(matrix)
                if declared == "unreadable" or detected.assay_type in HARD_EXCLUDED_ASSAYS:
                    cohort_assay_overrides[cohort_id] = detected.assay_type

    samples = normalize_sample_rows(
        rows,
        missing_expression_cohorts=missing_expression_cohorts,
        cohort_assay_overrides=cohort_assay_overrides,
    )
    registry_rows: list[dict[str, str]] = []
    membership_rows: list[dict[str, str]] = []

    for timing in ["pre-treatment", "on-treatment", "post-treatment"]:
        _add_response_candidate(
            registry_rows=registry_rows,
            membership_rows=membership_rows,
            rows=samples,
            analysis_id=TIMING_TO_LEGACY[timing],
            analysis_family=TIMING_TO_LEGACY[timing],
            timing=timing,
            drug_scope="ALL",
            cancer_scope="ALL",
            raw_scope_label="all therapies; all cancers",
            interpretation_label=TIMING_INTERPRETATION[timing],
            min_case_samples=min_case_samples,
            min_control_samples=min_control_samples,
            min_cohorts=min_cohorts,
        )
        _add_response_candidate(
            registry_rows=registry_rows,
            membership_rows=membership_rows,
            rows=samples,
            analysis_id=f"PAN_ICB_RESPONSE__{TIMING_LABEL[timing]}",
            analysis_family="PAN_ICB_RESPONSE",
            timing=timing,
            drug_scope="ALL",
            cancer_scope="ALL",
            raw_scope_label="pan-ICB pooled within timing",
            interpretation_label=f"pan-ICB {TIMING_INTERPRETATION[timing]}",
            min_case_samples=min_case_samples,
            min_control_samples=min_control_samples,
            min_cohorts=min_cohorts,
        )

    for timing in ["pre-treatment", "on-treatment", "post-treatment"]:
        for drug_group in sorted({r["drug_group"] for r in samples if r["drug_group"] != "UNKNOWN"}):
            scoped_rows = [r for r in samples if r["drug_group"] == drug_group]
            _add_response_candidate(
                registry_rows=registry_rows,
                membership_rows=membership_rows,
                rows=scoped_rows,
                analysis_id=f"DRUG_STRATIFIED_RESPONSE__{TIMING_LABEL[timing]}__{_slug(drug_group)}",
                analysis_family="DRUG_STRATIFIED_RESPONSE",
                timing=timing,
                drug_scope=drug_group,
                cancer_scope="ALL",
                raw_scope_label=drug_group,
                interpretation_label=f"therapy-stratified {TIMING_INTERPRETATION[timing]}",
                min_case_samples=min_case_samples,
                min_control_samples=min_control_samples,
                min_cohorts=min_cohorts,
            )
        combination_rows = [r for r in samples if r["drug_group"] == "ICI_COMBINATION"]
        _add_response_candidate(
            registry_rows=registry_rows,
            membership_rows=membership_rows,
            rows=combination_rows,
            analysis_id=f"ICI_COMBINATION_RESPONSE__{TIMING_LABEL[timing]}",
            analysis_family="ICI_COMBINATION_RESPONSE",
            timing=timing,
            drug_scope="ICI_COMBINATION",
            cancer_scope="ALL",
            raw_scope_label="any ICI-containing combination",
            interpretation_label=f"ICI-combination-specific {TIMING_INTERPRETATION[timing]}",
            min_case_samples=min_case_samples,
            min_control_samples=min_control_samples,
            min_cohorts=min_cohorts,
        )
        for cancer_group in sorted({r["cancer_group"] for r in samples if r["cancer_group"] != "UNKNOWN"}):
            scoped_rows = [r for r in samples if r["cancer_group"] == cancer_group]
            _add_response_candidate(
                registry_rows=registry_rows,
                membership_rows=membership_rows,
                rows=scoped_rows,
                analysis_id=f"CANCER_STRATIFIED_RESPONSE__{TIMING_LABEL[timing]}__{_slug(cancer_group)}",
                analysis_family="CANCER_STRATIFIED_RESPONSE",
                timing=timing,
                drug_scope="ALL",
                cancer_scope=cancer_group,
                raw_scope_label=cancer_group,
                interpretation_label=f"cancer-stratified {TIMING_INTERPRETATION[timing]}",
                min_case_samples=min_case_samples,
                min_control_samples=min_control_samples,
                min_cohorts=min_cohorts,
            )

    _add_delta_candidate(
        registry_rows=registry_rows,
        membership_rows=membership_rows,
        rows=samples,
        analysis_id="DELTA_RESPONSE__PRE_TO_ON_TREATMENT",
        timing_scope="pre-to-on-treatment",
        min_case_samples=min_case_samples,
        min_control_samples=min_control_samples,
        min_cohorts=min_cohorts,
    )
    _add_delta_candidate(
        registry_rows=registry_rows,
        membership_rows=membership_rows,
        rows=samples,
        analysis_id="DELTA_RESPONSE__PRE_TO_POST_TREATMENT",
        timing_scope="pre-to-post-treatment",
        min_case_samples=min_case_samples,
        min_control_samples=min_control_samples,
        min_cohorts=min_cohorts,
    )

    registry_rows.sort(key=lambda r: (r["analysis_family"], r["analysis_id"]))
    membership_rows.sort(key=lambda r: (r["analysis_id"], r["cohort_id"], r["pair_id"], r["sample_id"], r["membership_role"]))
    audit = render_analysis_design_audit(samples, registry_rows)
    return samples, registry_rows, membership_rows, audit


def render_analysis_design_audit(samples: list[dict[str, str]], registry_rows: list[dict[str, str]]) -> str:
    feasible = [r for r in registry_rows if r["feasibility_status"] == "feasible"]
    blocked = [r for r in registry_rows if r["feasibility_status"] == "blocked"]
    lines = [
        "# Analysis Design Audit",
        "",
        "## Overview",
        "",
        f"- Samples: {len(samples)}",
        f"- Feasible analyses: {len(feasible)}",
        f"- Blocked analyses: {len(blocked)}",
        "",
        "## Feasible Analyses",
        "",
    ]
    lines.extend(_registry_table(feasible[:80]))
    lines.extend(["", "## Blocked Analyses", ""])
    lines.extend(_registry_table(blocked[:80]))
    lines.extend(["", "## Timing By Response Counts", ""])
    lines.extend(_count_table(samples, ["timing_category", "response_label"]))
    lines.extend(["", "## Drug By Timing Counts", ""])
    lines.extend(_count_table(samples, ["drug_group", "timing_category"]))
    lines.extend(["", "## Cancer By Timing Counts", ""])
    lines.extend(_count_table(samples, ["cancer_group", "timing_category"]))
    lines.append("")
    return "\n".join(lines)


def _registry_table(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ["No rows."]
    out = ["| analysis_id | family | timing | status | blocker |", "|---|---|---|---|---|"]
    for row in rows:
        out.append(
            "| {analysis_id} | {analysis_family} | {timing_scope} | {feasibility_status} | {blocker_reason} |".format(
                **row
            )
        )
    return out


def _count_table(rows: list[dict[str, str]], keys: list[str]) -> list[str]:
    counts: Counter[tuple[str, ...]] = Counter(tuple(row.get(key, "") for key in keys) for row in rows)
    header = [*keys, "n"]
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for values, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        out.append("| " + " | ".join([*values, str(count)]) + " |")
    return out


def write_analysis_design_outputs(
    *,
    rows: list[dict[str, str]],
    out_dir: Path,
    min_case_samples: int = 2,
    min_control_samples: int = 2,
    min_cohorts: int = 1,
    expression_manifest: Path | None = None,
    downloads_root: Path | None = None,
    check_expression_readiness: bool = False,
) -> list[Path]:
    samples, registry_rows, membership_rows, audit = build_analysis_design(
        rows,
        min_case_samples=min_case_samples,
        min_control_samples=min_control_samples,
        min_cohorts=min_cohorts,
        expression_manifest=expression_manifest,
        downloads_root=downloads_root,
        check_expression_readiness=check_expression_readiness,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / "analysis_sample_manifest.tsv"
    registry_path = out_dir / "analysis_contrast_registry.tsv"
    membership_path = out_dir / "analysis_contrast_membership.tsv"
    audit_path = out_dir / "analysis_design_audit.md"
    write_tsv(sample_path, fieldnames=SAMPLE_FIELDNAMES, rows=samples)
    write_tsv(registry_path, fieldnames=REGISTRY_FIELDNAMES, rows=registry_rows)
    write_tsv(membership_path, fieldnames=MEMBERSHIP_FIELDNAMES, rows=membership_rows)
    audit_path.write_text(audit, encoding="utf-8")
    return [sample_path, registry_path, membership_path, audit_path]
