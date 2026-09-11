from __future__ import annotations

import hashlib
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

from ...common.contrast_resolver import build_treatment_delta_pair_audit
from ...common.io import parse_bool, write_tsv


CONTRAST_ORDER = ["PRE_RESPONSE", "POST_RESPONSE", "ON_RESPONSE", "TREATMENT_DELTA"]


def normalize_timing(value: str) -> str:
    raw = (value or "").strip().lower().replace("_", "-")
    if raw in {"pre", "baseline", "pretreatment", "pre-treatment"}:
        return "pre-treatment"
    if raw in {"on", "on treatment", "on-treatment"}:
        return "on-treatment"
    if raw in {"post", "post treatment", "post-treatment"}:
        return "post-treatment"
    return raw or "unknown"


def normalize_response(value: str) -> str:
    raw = (value or "").strip().lower().replace("-", "_")
    if raw in {"responder", "response", "r"}:
        return "responder"
    if raw in {"non_responder", "nonresponder", "no_response", "nr"}:
        return "non_responder"
    return "unknown"


def _response_role(response: str) -> str:
    if response == "responder":
        return "case"
    if response == "non_responder":
        return "control"
    return "qc_only"


def _timing_contrast(timing: str) -> str:
    if timing == "pre-treatment":
        return "PRE_RESPONSE"
    if timing == "post-treatment":
        return "POST_RESPONSE"
    if timing == "on-treatment":
        return "ON_RESPONSE"
    return ""


def _pair_key(row: dict[str, str]) -> str:
    return (row.get("pair_id") or row.get("patient_id") or row.get("patient_uid") or "").strip()


def _delta_eligible_pairs(rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    pairs: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        pair_id = _pair_key(row)
        cohort_id = (row.get("cohort_id") or "").strip()
        if cohort_id and pair_id:
            pairs[(cohort_id, pair_id)].append(row)

    eligible: set[tuple[str, str]] = set()
    for key, pair_rows in pairs.items():
        timings = {normalize_timing(r.get("timing_category", "")) for r in pair_rows}
        responses = {normalize_response(r.get("response_label", "")) for r in pair_rows}
        if "pre-treatment" in timings and {"on-treatment", "post-treatment"} & timings:
            if responses & {"responder", "non_responder"}:
                eligible.add(key)
    return eligible


def build_sample_allocation(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    delta_pairs = _delta_eligible_pairs(rows)
    out_rows: list[dict[str, str]] = []

    for row in rows:
        cohort_id = (row.get("cohort_id") or "").strip()
        sample_id = (row.get("sample_id") or "").strip()
        timing = normalize_timing(row.get("timing_category", ""))
        response = normalize_response(row.get("response_label", ""))
        pair_id = _pair_key(row)
        patient_uid = (row.get("patient_uid") or row.get("patient_id") or pair_id or sample_id).strip()

        eligible: list[str] = []
        role = _response_role(response)
        timing_contrast = _timing_contrast(timing)
        if timing_contrast and role in {"case", "control"}:
            eligible.append(timing_contrast)
        if cohort_id and pair_id and (cohort_id, pair_id) in delta_pairs and role in {"case", "control"}:
            eligible.append("TREATMENT_DELTA")

        if eligible:
            assigned_bucket = eligible[0]
            unallocated_reason = ""
            curation_priority = "none"
        elif response == "unknown":
            assigned_bucket = "UNALLOCATED_REQUIRES_CURATION"
            unallocated_reason = "unknown_response"
            curation_priority = "high"
        elif timing == "unknown":
            assigned_bucket = "UNALLOCATED_REQUIRES_CURATION"
            unallocated_reason = "unknown_timing"
            curation_priority = "high"
        else:
            assigned_bucket = "QC_ONLY"
            unallocated_reason = "unsupported_timing_response_combination"
            curation_priority = "medium"

        out_rows.append(
            {
                "cohort_id": cohort_id,
                "sample_id": sample_id,
                "patient_uid": patient_uid,
                "pair_id": pair_id,
                "timing_category": timing,
                "response_label": response,
                "include_flag": str(parse_bool(row.get("include_flag", "false"), default=False)).lower(),
                "assigned_bucket": assigned_bucket,
                "eligible_contrasts": "|".join([c for c in CONTRAST_ORDER if c in set(eligible)]),
                "role": role,
                "eligible": "true" if eligible else "false",
                "unallocated_reason": unallocated_reason,
                "curation_priority": curation_priority,
                "source_fields": "timing_category;response_label;pair_id;patient_id;patient_uid",
            }
        )
    return out_rows


def summarize_allocation(allocation_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_cohort: dict[str, Counter[str]] = defaultdict(Counter)
    for row in allocation_rows:
        cohort_id = row.get("cohort_id", "")
        by_cohort[cohort_id]["n_samples"] += 1
        by_cohort[cohort_id][f"bucket__{row.get('assigned_bucket', 'unknown')}"] += 1
        for contrast in (row.get("eligible_contrasts", "") or "").split("|"):
            if contrast:
                by_cohort[cohort_id][f"eligible__{contrast}"] += 1

    rows: list[dict[str, str]] = []
    for cohort_id in sorted(by_cohort):
        counts = by_cohort[cohort_id]
        rows.append(
            {
                "cohort_id": cohort_id,
                "n_samples": str(counts.get("n_samples", 0)),
                "n_pre_response": str(counts.get("eligible__PRE_RESPONSE", 0)),
                "n_post_response": str(counts.get("eligible__POST_RESPONSE", 0)),
                "n_on_response": str(counts.get("eligible__ON_RESPONSE", 0)),
                "n_treatment_delta": str(counts.get("eligible__TREATMENT_DELTA", 0)),
                "n_qc_only": str(counts.get("bucket__QC_ONLY", 0)),
                "n_unallocated": str(counts.get("bucket__UNALLOCATED_REQUIRES_CURATION", 0)),
            }
        )
    return rows


def summarize_delta_pairs(delta_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_cohort: dict[str, Counter[str]] = defaultdict(Counter)
    for row in delta_rows:
        cohort_id = row.get("cohort_id", "")
        by_cohort[cohort_id]["n_pairs"] += 1
        status = row.get("delta_pair_status", "unknown")
        response = row.get("response_label", "unknown")
        by_cohort[cohort_id][f"status__{status}"] += 1
        if status == "eligible" and response in {"responder", "non_responder"}:
            by_cohort[cohort_id][f"eligible__{response}"] += 1

    rows: list[dict[str, str]] = []
    for cohort_id in sorted(by_cohort):
        counts = by_cohort[cohort_id]
        n_responder = counts.get("eligible__responder", 0)
        n_non_responder = counts.get("eligible__non_responder", 0)
        rows.append(
            {
                "cohort_id": cohort_id,
                "n_pairs": str(counts.get("n_pairs", 0)),
                "n_eligible_pairs": str(counts.get("status__eligible", 0)),
                "n_responder_pairs": str(n_responder),
                "n_non_responder_pairs": str(n_non_responder),
                "delta_contrast_eligible": "true" if n_responder >= 2 and n_non_responder >= 2 else "false",
                "n_blocked_pairs": str(counts.get("status__blocked", 0)),
            }
        )
    return rows


def write_unallocated_curation_templates(
    *,
    unallocated_rows: list[dict[str, str]],
    out_dir: Path,
) -> list[Path]:
    template_dir = out_dir / "curation_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in unallocated_rows:
        by_cohort[row.get("cohort_id", "")].append(row)

    index_rows: list[dict[str, str]] = []
    written: list[Path] = []
    template_fields = [
        "cohort_id",
        "sample_id",
        "patient_uid",
        "pair_id",
        "current_timing_category",
        "current_response_label",
        "unallocated_reason",
        "proposed_timing_category",
        "proposed_response_label",
        "evidence_source",
        "evidence_note",
        "review_status",
        "reviewer",
    ]
    for cohort_id, cohort_rows in sorted(by_cohort.items(), key=lambda item: (-len(item[1]), item[0])):
        safe_id = cohort_id or "unknown_cohort"
        template_path = template_dir / f"{safe_id}_unallocated_curation.tsv"
        template_rows = [
            {
                "cohort_id": row.get("cohort_id", ""),
                "sample_id": row.get("sample_id", ""),
                "patient_uid": row.get("patient_uid", ""),
                "pair_id": row.get("pair_id", ""),
                "current_timing_category": row.get("timing_category", ""),
                "current_response_label": row.get("response_label", ""),
                "unallocated_reason": row.get("unallocated_reason", ""),
                "proposed_timing_category": "",
                "proposed_response_label": "",
                "evidence_source": "",
                "evidence_note": "",
                "review_status": "pending",
                "reviewer": "",
            }
            for row in cohort_rows
        ]
        write_tsv(template_path, fieldnames=template_fields, rows=template_rows)
        written.append(template_path)
        reason_counts = Counter(row.get("unallocated_reason", "") for row in cohort_rows)
        index_rows.append(
            {
                "cohort_id": cohort_id,
                "n_unallocated": str(len(cohort_rows)),
                "top_unallocated_reason": reason_counts.most_common(1)[0][0] if reason_counts else "",
                "template_path": str(template_path),
            }
        )

    index_path = template_dir / "unallocated_curation_template_index.tsv"
    write_tsv(
        index_path,
        fieldnames=["cohort_id", "n_unallocated", "top_unallocated_reason", "template_path"],
        rows=index_rows,
    )
    return [index_path, *written]


def write_allocation_reproducibility_bundle(
    *,
    out_dir: Path,
    sample_manifest: Path,
    allocation_file: Path,
    summary_file: Path,
    unallocated_file: Path,
    audit_file: Path,
    delta_audit_file: Path,
    delta_summary_file: Path,
    template_index_file: Path,
) -> list[Path]:
    repro_dir = out_dir / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)

    commands_file = repro_dir / "commands.sh"
    commands_file.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "python -m pipeline.cli intake build-sample-allocation \\",
                f"  --sample-manifest {sample_manifest} \\",
                f"  --out {out_dir}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env_file = repro_dir / "environment.yml"
    env_file.write_text(
        "\n".join(
            [
                "name: rnaseq-spec008-allocation",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                f"  - python={sys.version_info.major}.{sys.version_info.minor}",
                "  - pandas",
                "",
            ]
        ),
        encoding="utf-8",
    )

    checksums_file = repro_dir / "checksums.sha256"
    checksum_targets = [
        sample_manifest,
        allocation_file,
        summary_file,
        unallocated_file,
        audit_file,
        delta_audit_file,
        delta_summary_file,
        template_index_file,
    ]
    checksum_rows = []
    for path in checksum_targets:
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksum_rows.append(f"{digest}  {path}")
    checksums_file.write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")

    return [commands_file, env_file, checksums_file]


def write_allocation_outputs(
    *,
    rows: list[dict[str, str]],
    sample_manifest: Path,
    out_dir: Path,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    allocation_rows = build_sample_allocation(rows)
    summary_rows = summarize_allocation(allocation_rows)
    delta_rows = build_treatment_delta_pair_audit(rows)
    delta_summary_rows = summarize_delta_pairs(delta_rows)
    unallocated_rows = [
        row for row in allocation_rows if row.get("assigned_bucket") == "UNALLOCATED_REQUIRES_CURATION"
    ]

    allocation_file = out_dir / "sample_allocation_matrix.tsv"
    summary_file = out_dir / "cohort_allocation_summary.tsv"
    unallocated_file = out_dir / "unallocated_samples.tsv"
    delta_audit_file = out_dir / "treatment_delta_pair_audit.tsv"
    delta_summary_file = out_dir / "treatment_delta_pair_summary.tsv"
    audit_file = out_dir / "allocation_audit.md"

    allocation_fields = [
        "cohort_id",
        "sample_id",
        "patient_uid",
        "pair_id",
        "timing_category",
        "response_label",
        "include_flag",
        "assigned_bucket",
        "eligible_contrasts",
        "role",
        "eligible",
        "unallocated_reason",
        "curation_priority",
        "source_fields",
    ]
    write_tsv(allocation_file, fieldnames=allocation_fields, rows=allocation_rows)
    write_tsv(
        summary_file,
        fieldnames=[
            "cohort_id",
            "n_samples",
            "n_pre_response",
            "n_post_response",
            "n_on_response",
            "n_treatment_delta",
            "n_qc_only",
            "n_unallocated",
        ],
        rows=summary_rows,
    )
    write_tsv(unallocated_file, fieldnames=allocation_fields, rows=unallocated_rows)
    write_tsv(
        delta_audit_file,
        fieldnames=[
            "cohort_id",
            "pair_id",
            "response_label",
            "has_pre",
            "has_after",
            "n_pre",
            "n_after",
            "pre_sample_ids",
            "after_sample_ids",
            "delta_pair_status",
            "blocker_reason",
        ],
        rows=delta_rows,
    )
    write_tsv(
        delta_summary_file,
        fieldnames=[
            "cohort_id",
            "n_pairs",
            "n_eligible_pairs",
            "n_responder_pairs",
            "n_non_responder_pairs",
            "delta_contrast_eligible",
            "n_blocked_pairs",
        ],
        rows=delta_summary_rows,
    )
    template_files = write_unallocated_curation_templates(
        unallocated_rows=unallocated_rows,
        out_dir=out_dir,
    )
    template_index_file = template_files[0]

    bucket_counts = Counter(row.get("assigned_bucket", "") for row in allocation_rows)
    delta_status_counts = Counter(row.get("delta_pair_status", "") for row in delta_rows)
    audit_file.write_text(
        "\n".join(
            [
                "# Spec 008 Allocation Audit",
                "",
                f"- sample_manifest: {sample_manifest}",
                f"- python: {platform.python_version()}",
                f"- total_samples: {len(allocation_rows)}",
                f"- allocated_samples: {len(allocation_rows) - len(unallocated_rows)}",
                f"- unallocated_samples: {len(unallocated_rows)}",
                "",
                "## Buckets",
                "",
                *[f"- {bucket}: {count}" for bucket, count in sorted(bucket_counts.items())],
                "",
                "## TREATMENT_DELTA Pair Audit",
                "",
                f"- total_pairs: {len(delta_rows)}",
                *[f"- {status}: {count}" for status, count in sorted(delta_status_counts.items())],
                f"- pair_summary: {delta_summary_file}",
                "",
                "## Unallocated Curation Templates",
                "",
                f"- template_index: {template_index_file}",
                f"- template_files: {max(0, len(template_files) - 1)}",
                "",
                "## ClawBio-Informed Contract",
                "",
                "- Every sample is assigned to an explicit bucket.",
                "- Unknown-response samples are never silently included in response DE.",
                "- Reproducibility files are written under `reproducibility/`.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    repro_files = write_allocation_reproducibility_bundle(
        out_dir=out_dir,
        sample_manifest=sample_manifest,
        allocation_file=allocation_file,
        summary_file=summary_file,
        unallocated_file=unallocated_file,
        audit_file=audit_file,
        delta_audit_file=delta_audit_file,
        delta_summary_file=delta_summary_file,
        template_index_file=template_index_file,
    )
    return [
        allocation_file,
        summary_file,
        unallocated_file,
        delta_audit_file,
        delta_summary_file,
        audit_file,
        *template_files,
        *repro_files,
    ]
