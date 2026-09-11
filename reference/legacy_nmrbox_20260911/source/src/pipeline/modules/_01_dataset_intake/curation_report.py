from __future__ import annotations

import hashlib
import platform
import sys
from collections import defaultdict
from pathlib import Path

from ...common.io import read_tsv, write_tsv


def _by_cohort(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        cohort_id = (row.get("cohort_id", "") or "").strip()
        if cohort_id:
            out[cohort_id].append(row)
    return out


def _write_reproducibility_bundle(
    *,
    out_dir: Path,
    assay_detection: Path,
    response_definition: Path,
    timing_provenance: Path,
    sample_manifest: Path,
    report_tsv: Path,
    report_md: Path,
) -> list[Path]:
    repro_dir = out_dir / "reproducibility"
    repro_dir.mkdir(parents=True, exist_ok=True)

    commands_file = repro_dir / "commands.sh"
    commands_file.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "python -m pipeline.cli intake curation-report \\",
                f"  --assay-detection {assay_detection} \\",
                f"  --response-definition {response_definition} \\",
                f"  --timing-provenance {timing_provenance} \\",
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
                "name: rnaseq-stage01-curation-report",
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

    checksum_file = repro_dir / "checksums.sha256"
    targets = [assay_detection, response_definition, timing_provenance, sample_manifest, report_tsv, report_md]
    lines: list[str] = []
    for target in targets:
        if not target.exists():
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        lines.append(f"{digest}  {target}")
    checksum_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return [commands_file, env_file, checksum_file]


def write_stage01_curation_report(
    *,
    assay_detection: Path,
    response_definition: Path,
    timing_provenance: Path,
    sample_manifest: Path,
    out_dir: Path,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_tsv = out_dir / "intake_curation_report.tsv"
    report_md = out_dir / "intake_curation_report.md"

    assay_rows = read_tsv(assay_detection)
    response_rows = read_tsv(response_definition)
    timing_rows = read_tsv(timing_provenance)
    sample_rows = read_tsv(sample_manifest)

    assay_by_cohort = {row.get("cohort_id", ""): row for row in assay_rows}
    response_by_cohort = {row.get("cohort_id", ""): row for row in response_rows}
    timing_by_cohort = _by_cohort(timing_rows)
    sample_by_cohort = _by_cohort(sample_rows)

    all_cohorts = sorted(
        {
            *assay_by_cohort.keys(),
            *response_by_cohort.keys(),
            *timing_by_cohort.keys(),
            *sample_by_cohort.keys(),
        }
    )
    rows: list[dict[str, str]] = []
    for cohort_id in all_cohorts:
        assay = assay_by_cohort.get(cohort_id, {})
        response = response_by_cohort.get(cohort_id, {})
        timings = timing_by_cohort.get(cohort_id, [])
        samples = sample_by_cohort.get(cohort_id, [])

        n_default_pre = sum(1 for row in timings if (row.get("timing_provenance", "") or "") == "default_pre")
        n_unknown = int(float(response.get("n_unknown", "0") or 0))
        needs_manual = (response.get("needs_manual_confirmation", "false") or "").lower() == "true"
        assay_type = (assay.get("assay_type", "") or "").strip()
        hard_excluded = assay_type in {"methylation_beta", "unreadable"}
        status = "ready"
        reasons: list[str] = []
        if needs_manual:
            status = "review_required"
            reasons.append("manual_response_confirmation")
        if n_default_pre > 0:
            status = "review_required"
            reasons.append("timing_defaulted_pre")
        if n_unknown > 0:
            status = "review_required"
            reasons.append("unknown_response_labels")
        if hard_excluded:
            status = "excluded"
            reasons = [f"excluded_assay_type_{assay_type}"]

        rows.append(
            {
                "cohort_id": cohort_id,
                "n_samples": str(len(samples)),
                "assay_type": assay_type,
                "detection_confidence": assay.get("detection_confidence", ""),
                "label_provenance": response.get("label_provenance", ""),
                "needs_manual_confirmation": "true" if needs_manual else "false",
                "n_unknown_responses": str(n_unknown),
                "n_timing_default_pre": str(n_default_pre),
                "cohort_flags": (
                    response.get("cohort_flags", "")
                    or assay.get("cohort_flags", "")
                    or ""
                ),
                "status": status,
                "notes": ";".join(reasons),
            }
        )

    write_tsv(
        report_tsv,
        fieldnames=[
            "cohort_id",
            "n_samples",
            "assay_type",
            "detection_confidence",
            "label_provenance",
            "needs_manual_confirmation",
            "n_unknown_responses",
            "n_timing_default_pre",
            "cohort_flags",
            "status",
            "notes",
        ],
        rows=rows,
    )

    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[row.get("status", "unknown")] += 1
    report_md.write_text(
        "\n".join(
            [
                "# Stage 01 Intake Curation Report",
                "",
                f"- cohorts: {len(rows)}",
                f"- ready: {status_counts.get('ready', 0)}",
                f"- review_required: {status_counts.get('review_required', 0)}",
                f"- excluded: {status_counts.get('excluded', 0)}",
                f"- platform: {platform.platform()}",
                "",
                "## Inputs",
                "",
                f"- assay_detection: {assay_detection}",
                f"- response_definition: {response_definition}",
                f"- timing_provenance: {timing_provenance}",
                f"- sample_manifest: {sample_manifest}",
                "",
                "## Output",
                "",
                f"- {report_tsv}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    repro_files = _write_reproducibility_bundle(
        out_dir=out_dir,
        assay_detection=assay_detection,
        response_definition=response_definition,
        timing_provenance=timing_provenance,
        sample_manifest=sample_manifest,
        report_tsv=report_tsv,
        report_md=report_md,
    )
    return [report_tsv, report_md, *repro_files]
