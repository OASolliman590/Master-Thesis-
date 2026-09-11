from __future__ import annotations

from collections import defaultdict

from .io import parse_bool


RESPONSE_CONTRAST_TIMING = {
    "PRE_RESPONSE": "pre-treatment",
    "POST_RESPONSE": "post-treatment",
    "ON_RESPONSE": "on-treatment",
}
RESPONSE_CONTRASTS = set(RESPONSE_CONTRAST_TIMING)
SUPPORTED_CONTRASTS = RESPONSE_CONTRASTS | {"TREATMENT_DELTA"}


def _normalized(value: str) -> str:
    return (value or "").strip()


def _pair_id(row: dict[str, str]) -> str:
    return _normalized(row.get("pair_id") or row.get("patient_id") or row.get("patient_uid") or "")


def resolve_response_contrast_sample_ids(
    cohort_rows: list[dict[str, str]],
    contrast: str,
) -> tuple[list[str], list[str]]:
    """Return responder/non-responder sample IDs for one timing-aware contrast."""
    contrast = contrast.upper()
    timing = RESPONSE_CONTRAST_TIMING.get(contrast)
    if not timing:
        return [], []

    case_ids: list[str] = []
    control_ids: list[str] = []
    for row in cohort_rows:
        if contrast == "PRE_RESPONSE" and not parse_bool(row.get("include_flag", "true"), default=True):
            continue
        if _normalized(row.get("timing_category", "")) != timing:
            continue
        label = _normalized(row.get("response_label", ""))
        sample_id = _normalized(row.get("sample_id", ""))
        if not sample_id:
            continue
        if label == "responder":
            case_ids.append(sample_id)
        elif label == "non_responder":
            control_ids.append(sample_id)
    return case_ids, control_ids


def resolve_treatment_delta_groups(
    cohort_rows: list[dict[str, str]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return paired pre/after sample IDs split by responder status."""
    patient_to_pre: dict[str, str] = {}
    patient_to_after: dict[str, str] = {}
    patient_to_resp: dict[str, str] = {}

    for row in cohort_rows:
        pair_id = _pair_id(row)
        sample_id = _normalized(row.get("sample_id", ""))
        if not pair_id or not sample_id:
            continue
        timing = _normalized(row.get("timing_category", ""))
        response = _normalized(row.get("response_label", ""))
        if timing == "pre-treatment":
            patient_to_pre[pair_id] = sample_id
        elif timing in {"on-treatment", "post-treatment"}:
            patient_to_after[pair_id] = sample_id
        if response in {"responder", "non_responder"}:
            patient_to_resp[pair_id] = response

    case_pre_sids: list[str] = []
    case_after_sids: list[str] = []
    control_pre_sids: list[str] = []
    control_after_sids: list[str] = []
    for pair_id, pre_sid in sorted(patient_to_pre.items()):
        after_sid = patient_to_after.get(pair_id, "")
        response = patient_to_resp.get(pair_id, "")
        if not after_sid or response not in {"responder", "non_responder"}:
            continue
        if response == "responder":
            case_pre_sids.append(pre_sid)
            case_after_sids.append(after_sid)
        else:
            control_pre_sids.append(pre_sid)
            control_after_sids.append(after_sid)
    return case_pre_sids, case_after_sids, control_pre_sids, control_after_sids


def is_contrast_eligible(cohort_rows: list[dict[str, str]], contrast: str) -> bool:
    contrast = contrast.upper()
    if contrast in RESPONSE_CONTRASTS:
        case_ids, control_ids = resolve_response_contrast_sample_ids(cohort_rows, contrast)
        return len(case_ids) >= 2 and len(control_ids) >= 2
    if contrast == "TREATMENT_DELTA":
        case_pre, _, control_pre, _ = resolve_treatment_delta_groups(cohort_rows)
        return len(case_pre) >= 2 and len(control_pre) >= 2
    return False


def build_treatment_delta_pair_audit(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    pairs: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        cohort_id = _normalized(row.get("cohort_id", ""))
        pair_id = _pair_id(row)
        if cohort_id and pair_id:
            pairs[(cohort_id, pair_id)].append(row)

    audit_rows: list[dict[str, str]] = []
    for (cohort_id, pair_id), pair_rows in sorted(pairs.items()):
        pre_ids = [
            _normalized(r.get("sample_id", ""))
            for r in pair_rows
            if _normalized(r.get("timing_category", "")) == "pre-treatment"
        ]
        after_ids = [
            _normalized(r.get("sample_id", ""))
            for r in pair_rows
            if _normalized(r.get("timing_category", "")) in {"on-treatment", "post-treatment"}
        ]
        responses = sorted(
            {
                _normalized(r.get("response_label", ""))
                for r in pair_rows
                if _normalized(r.get("response_label", "")) in {"responder", "non_responder"}
            }
        )
        response = responses[0] if len(responses) == 1 else ("conflicting" if responses else "unknown")
        has_pre = bool(pre_ids)
        has_after = bool(after_ids)
        if response not in {"responder", "non_responder"}:
            status = "blocked"
            reason = "missing_or_conflicting_response"
        elif not has_pre:
            status = "blocked"
            reason = "missing_pre_treatment_sample"
        elif not has_after:
            status = "blocked"
            reason = "missing_on_or_post_treatment_sample"
        else:
            status = "eligible"
            reason = ""
        audit_rows.append(
            {
                "cohort_id": cohort_id,
                "pair_id": pair_id,
                "response_label": response,
                "has_pre": "true" if has_pre else "false",
                "has_after": "true" if has_after else "false",
                "n_pre": str(len([sid for sid in pre_ids if sid])),
                "n_after": str(len([sid for sid in after_ids if sid])),
                "pre_sample_ids": "|".join([sid for sid in pre_ids if sid]),
                "after_sample_ids": "|".join([sid for sid in after_ids if sid]),
                "delta_pair_status": status,
                "blocker_reason": reason,
            }
        )
    return audit_rows
