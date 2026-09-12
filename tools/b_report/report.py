"""W7: deterministic, source-traceable figures for the completed APM module."""

from __future__ import annotations

import html
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_tsv,
    json_no_dups,
    publish_directory,
    read_tsv,
    remove_tree,
    sha256_file,
    utc_stamp,
    verify_published_stage,
)

SYNTHETIC_LABEL = "SYNTHETIC FIXTURE ONLY — NOT A BIOLOGICAL RESULT"
FIGURE_FILES = (
    "figures/figure_1_cohort_accountability.svg",
    "figures/figure_2_frozen_probe_state.svg",
    "figures/figure_3_development_predictions.svg",
    "figures/figure_4_external_validation.svg",
)


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W7 {message}", code, "W7")


def _verify_stage(stage_dir: Path, stage_id: str) -> dict[str, Any]:
    ok, reason = verify_published_stage(stage_dir, stage_id)
    if not ok:
        _fail(f"reason=parent-publication-invalid stage={stage_id} detail={reason}")
    complete_path = stage_dir / "COMPLETE.json"
    complete = json_no_dups(complete_path.read_bytes())
    return complete


def _rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    header, raw_rows = read_tsv(path)
    if not required.issubset(header):
        _fail(f"reason=source-table-schema file={path.name}")
    return [{name: row[i] for i, name in enumerate(header)} for row in raw_rows]


def _number(token: str, field: str) -> float:
    try:
        value = float(token)
    except ValueError as exc:
        _fail(f"reason=non-numeric-source field={field}")
        raise AssertionError from exc
    if not math.isfinite(value):
        _fail(f"reason=non-finite-source field={field}")
    return value


def _svg_text(x: float, y: float, value: str, *, size: int = 14, anchor: str = "start", weight: int = 400) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#172033">'
        f"{html.escape(value)}</text>"
    )


def _svg_document(title: str, subtitle: str, body: Iterable[str]) -> bytes:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="620" viewBox="0 0 960 620">',
        '<rect width="960" height="620" fill="#fbfaf7"/>',
        _svg_text(48, 46, SYNTHETIC_LABEL, size=15, weight=700),
        _svg_text(48, 82, title, size=25, weight=700),
        _svg_text(48, 108, subtitle, size=14),
        *body,
        "</svg>",
    ]
    return ("\n".join(parts) + "\n").encode("utf-8")


def _bar_svg(title: str, subtitle: str, bars: list[tuple[str, int, str]]) -> bytes:
    maximum = max((value for _, value, _ in bars), default=1)
    step = min(82.0, 390.0 / max(1, len(bars) - 1))
    body: list[str] = []
    for index, (label, value, color) in enumerate(bars):
        y = 155 + index * step
        width = 650 * value / maximum if maximum else 0
        body.append(_svg_text(48, y + 25, label, size=15))
        body.append(f'<rect x="260" y="{y}" width="{width:.2f}" height="34" rx="4" fill="{color}"/>')
        body.append(_svg_text(270 + width, y + 24, str(value), size=15, weight=700))
    body.append(_svg_text(48, 605, "Counts are computed from the linked source table; bar length is not manually entered.", size=12))
    return _svg_document(title, subtitle, body)


def _scatter_svg(
    title: str,
    subtitle: str,
    points: list[tuple[str, float, float]],
    *,
    notes: list[str] | None = None,
) -> bytes:
    values = [value for _, x, y in points for value in (x, y)]
    low = min(values)
    high = max(values)
    pad = max((high - low) * 0.08, 0.05)
    low -= pad
    high += pad
    span = high - low
    left, top, size = 120.0, 145.0, 390.0

    def sx(value: float) -> float:
        return left + (value - low) / span * size

    def sy(value: float) -> float:
        return top + size - (value - low) / span * size

    colors = {"baseline": "#2864a5", "extended": "#d85b48"}
    body = [
        f'<line x1="{left}" y1="{top + size}" x2="{left + size}" y2="{top + size}" stroke="#172033"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + size}" stroke="#172033"/>',
        f'<line x1="{sx(low):.2f}" y1="{sy(low):.2f}" x2="{sx(high):.2f}" y2="{sy(high):.2f}" stroke="#7c8493" stroke-dasharray="6 5"/>',
        _svg_text(left + size / 2, 580, "Observed Y", size=15, anchor="middle"),
        _svg_text(58, top + size / 2, "Predicted Y", size=15, anchor="middle"),
        _svg_text(left, top + size + 25, f"{low:.3g}", size=12, anchor="middle"),
        _svg_text(left + size, top + size + 25, f"{high:.3g}", size=12, anchor="middle"),
        _svg_text(left - 12, top + size, f"{low:.3g}", size=12, anchor="end"),
        _svg_text(left - 12, top + 5, f"{high:.3g}", size=12, anchor="end"),
    ]
    for model, x, y in points:
        body.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="5" fill="{colors[model]}" fill-opacity="0.82"/>')
    body.extend(
        [
            '<circle cx="610" cy="190" r="6" fill="#2864a5"/>',
            _svg_text(628, 195, "Baseline f0", size=14),
            '<circle cx="610" cy="225" r="6" fill="#d85b48"/>',
            _svg_text(628, 230, "Extended f1", size=14),
            _svg_text(590, 285, "Dashed line: perfect prediction", size=13),
            _svg_text(590, 325, "Identical axes are derived from all plotted values.", size=13),
        ]
    )
    for index, note in enumerate(notes or []):
        body.append(_svg_text(590, 380 + index * 28, note, size=13, weight=700 if index == 0 else 400))
    return _svg_document(title, subtitle, body)


def _format_metric(value: Any) -> str:
    return "undefined" if value is None else format(float(value), ".6g")


def _build_flow_rows(
    coverage: list[dict[str, str]],
    oof: list[dict[str, str]],
    external: list[dict[str, str]],
    w6_exclusions: list[dict[str, str]],
    w3_exclusions: list[dict[str, str]],
) -> tuple[list[list[Any]], list[tuple[str, int, str]]]:
    """Build patient flow plus separately labelled W3 specimen exclusions."""
    oof_ids = {row["patient_id"] for row in oof}
    evaluated_ids = {row["patient_id"] for row in external}
    excluded = {row["patient_id"]: row["exclusion_reason"] for row in w6_exclusions}
    flow_rows: list[list[Any]] = []
    status_counts: Counter[str] = Counter()
    for row in sorted(coverage, key=lambda item: item["patient_id"].encode("utf-8")):
        pid = row["patient_id"]
        if pid in oof_ids:
            status, reason = "development-oof", "NA"
        elif pid in evaluated_ids:
            status, reason = "external-evaluated", "NA"
        elif pid in excluded:
            status, reason = "external-excluded", excluded[pid]
        else:
            status, reason = "development-not-oof", "not-in-w5-oof-output"
        status_counts[status] += 1
        flow_rows.append(
            [
                "patient",
                pid,
                "NA",
                "NA",
                row["cohort"],
                row["expression_gene_count"],
                row["methylation_probe_count"],
                "NA",
                status,
                reason,
                True,
            ]
        )
    w3_patient_ids: set[str] = set()
    for row in sorted(
        w3_exclusions,
        key=lambda item: (
            item["patient_id"].encode("utf-8"),
            item["specimen_id"].encode("utf-8"),
            item["assay_id"].encode("utf-8"),
        ),
    ):
        if row["patient_id"] not in {"", "NA"}:
            w3_patient_ids.add(row["patient_id"])
        flow_rows.append(
            [
                "excluded-specimen",
                row["patient_id"],
                row["specimen_id"],
                row["assay_id"],
                row["cohort"],
                "NA",
                "NA",
                row["modality"],
                "w3-excluded-specimen",
                row["exclusion_reason"],
                True,
            ]
        )
    bars = [
        ("Development OOF patients", status_counts["development-oof"], "#2864a5"),
        ("Development not in OOF patients", status_counts["development-not-oof"], "#7c8493"),
        ("External evaluated patients", status_counts["external-evaluated"], "#2a8c72"),
        ("External excluded at W6 patients", status_counts["external-excluded"], "#d85b48"),
        ("W3-excluded patients (unique)", len(w3_patient_ids), "#b7791f"),
        ("W3-excluded specimen/assay rows", len(w3_exclusions), "#7957a8"),
    ]
    return flow_rows, bars


def _build_probe_rows(state: dict[str, Any]) -> tuple[list[list[Any]], list[tuple[str, int, str]]]:
    probe_rows: list[list[Any]] = []
    probe_counts: Counter[tuple[str, str]] = Counter()
    for gene, probes in sorted(state.get("eligible_probes_by_gene", {}).items()):
        for probe in probes:
            probe_rows.append([gene, probe, "selected", "NA", True])
            probe_counts[(gene, "selected")] += 1
    for field in ("probe_exclusions", "annotation_exclusions"):
        for item in state.get(field, []):
            gene = str(item.get("target_gene_id", "unassigned"))
            probe_rows.append([gene, item.get("probe_id", "NA"), "excluded", item.get("reason", "unspecified"), True])
            probe_counts[(gene, "excluded")] += 1
    probe_rows.sort(key=lambda row: (str(row[0]).encode("utf-8"), str(row[1]).encode("utf-8"), str(row[2])))
    bars: list[tuple[str, int, str]] = []
    for gene in sorted({str(row[0]) for row in probe_rows}):
        bars.append((f"{gene} selected", probe_counts[(gene, "selected")], "#2a8c72"))
        bars.append((f"{gene} excluded", probe_counts[(gene, "excluded")], "#d85b48"))
    return probe_rows, bars


def _build_prediction_rows(
    rows: list[dict[str, str]],
    *,
    source_label: str,
) -> tuple[list[list[Any]], list[tuple[str, float, float]]]:
    output: list[list[Any]] = []
    points: list[tuple[str, float, float]] = []
    for row in rows:
        y = _number(row["Y"], f"{source_label}.Y")
        for model, field in (("baseline", "f0"), ("extended", "f1")):
            prediction = _number(row[field], f"{source_label}.{field}")
            output.append([row["patient_id"], y, model, prediction, (y - prediction) ** 2, True])
            points.append((model, y, prediction))
    return output, points


def run_report(
    *,
    w3_dir: Path,
    w5_dir: Path,
    w6_dir: Path,
    stage_dir: Path,
    parent_hashes: dict[str, str],
    code_identity: str,
    interpreter: str,
) -> dict[str, Any]:
    for path, stage_id in ((w3_dir, "W3"), (w5_dir, "W5"), (w6_dir, "W6")):
        _verify_stage(path, stage_id)

    coverage = _rows(
        w3_dir / "coverage.tsv",
        {"patient_id", "cohort", "expression_gene_count", "methylation_probe_count", "synthetic"},
    )
    w3_exclusions = _rows(
        w3_dir / "exclusions.tsv",
        {"patient_id", "specimen_id", "assay_id", "cohort", "modality", "exclusion_reason", "synthetic"},
    )
    oof = _rows(w5_dir / "bundle" / "oof_predictions.tsv", {"patient_id", "Y", "f0", "f1"})
    external = _rows(w6_dir / "predictions.tsv", {"patient_id", "Y", "f0", "f1", "synthetic"})
    w6_exclusions = _rows(w6_dir / "exclusions.tsv", {"patient_id", "exclusion_reason", "synthetic"})
    state = json_no_dups((w5_dir / "bundle" / "final_feature_state.json").read_bytes())
    development_metrics = json_no_dups((w5_dir / "bundle" / "development_metrics.json").read_bytes())
    evaluation = json_no_dups((w6_dir / "evaluation.json").read_bytes())
    if any(
        row.get("synthetic") != "true"
        for row in coverage + w3_exclusions + external + w6_exclusions
    ):
        _fail("reason=non-synthetic-source-row")
    if (
        evaluation.get("synthetic") is not True
        or development_metrics.get("synthetic") is not True
        or state.get("synthetic") is not True
    ):
        _fail("reason=non-synthetic-source-artifact")

    work = stage_dir.parent / f"{stage_dir.name}.work"
    if work.exists():
        remove_tree(work)
    (work / "figures").mkdir(parents=True)
    (work / "tables").mkdir(parents=True)

    flow_rows, bars = _build_flow_rows(coverage, oof, external, w6_exclusions, w3_exclusions)
    atomic_write_tsv(
        work / "tables" / "figure_1_cohort_accountability.tsv",
        [
            "unit_type",
            "patient_id",
            "specimen_id",
            "assay_id",
            "cohort",
            "expression_gene_count",
            "methylation_probe_count",
            "modality",
            "analysis_status",
            "reason",
            "synthetic",
        ],
        flow_rows,
    )
    atomic_write_bytes(
        work / FIGURE_FILES[0],
        _bar_svg("Figure 1. Cohort accountability", "Patient counts from W3, W5 and W6 synthetic outputs", bars),
    )

    probe_rows, probe_bars = _build_probe_rows(state)
    atomic_write_tsv(
        work / "tables" / "figure_2_frozen_probe_state.tsv",
        ["gene", "probe_id", "state", "reason", "synthetic"],
        probe_rows,
    )
    atomic_write_bytes(
        work / FIGURE_FILES[1],
        _bar_svg("Figure 2. Frozen promoter-probe state", "Training-selected and excluded probes; associations and composition are pending", probe_bars),
    )

    development_rows, development_points = _build_prediction_rows(oof, source_label="W5")
    atomic_write_tsv(
        work / "tables" / "figure_3_development_predictions.tsv",
        ["patient_id", "Y", "model", "prediction", "squared_error", "synthetic"],
        development_rows,
    )
    development_pooled = development_metrics.get("pooled")
    if not isinstance(development_pooled, dict):
        _fail("reason=missing-development-metrics")
    atomic_write_tsv(
        work / "tables" / "figure_3_development_metrics.tsv",
        ["n", "sse_baseline", "sse_extended", "sst", "r2_baseline", "r2_extended", "delta_r2", "status", "synthetic"],
        [[
            development_metrics.get("n_oof"),
            development_pooled.get("sse_baseline"),
            development_pooled.get("sse_extended"),
            development_pooled.get("sst"),
            development_pooled.get("r2_baseline"),
            development_pooled.get("r2_extended"),
            development_pooled.get("delta_r2"),
            "undefined" if development_pooled.get("delta_r2") is None else "defined",
            True,
        ]],
    )
    atomic_write_bytes(
        work / FIGURE_FILES[2],
        _scatter_svg(
            "Figure 3. Internal development predictions",
            "Nested out-of-fold W5 predictions; internal evidence only",
            development_points,
            notes=[f"Pooled Delta_R2 = {_format_metric(development_pooled.get('delta_r2'))}"],
        ),
    )

    external_rows, external_points = _build_prediction_rows(external, source_label="W6")
    atomic_write_tsv(
        work / "tables" / "figure_4_external_predictions.tsv",
        ["patient_id", "Y", "model", "prediction", "squared_error", "synthetic"],
        external_rows,
    )
    metrics = evaluation.get("metrics")
    if not isinstance(metrics, dict):
        _fail("reason=missing-external-metrics")
    bootstrap = metrics.get("bootstrap") or {}
    atomic_write_tsv(
        work / "tables" / "figure_4_external_metrics.tsv",
        ["n", "sse_baseline", "sse_extended", "sst", "r2_baseline", "r2_extended", "delta_r2", "ci_lower", "ci_upper", "status", "reason", "synthetic"],
        [[
            evaluation.get("n"),
            metrics.get("sse_baseline"),
            metrics.get("sse_extended"),
            metrics.get("sst"),
            metrics.get("r2_baseline"),
            metrics.get("r2_extended"),
            metrics.get("delta_r2"),
            bootstrap.get("delta_ci_lower"),
            bootstrap.get("delta_ci_upper"),
            metrics.get("status"),
            metrics.get("reason"),
            True,
        ]],
    )
    atomic_write_bytes(
        work / FIGURE_FILES[3],
        _scatter_svg(
            "Figure 4. Frozen external validation",
            "No-refit W6 predictions on identical eligible synthetic patients",
            external_points,
            notes=[
                f"Delta_R2 = {_format_metric(metrics.get('delta_r2'))}",
                f"95% paired-bootstrap interval: {_format_metric(bootstrap.get('delta_ci_lower'))} to {_format_metric(bootstrap.get('delta_ci_upper'))}",
                f"n = {evaluation.get('n')}; status = {metrics.get('status')}",
            ],
        ),
    )

    explanations = [
        {
            "figure": 1,
            "figure_file": FIGURE_FILES[0],
            "source_tables": ["tables/figure_1_cohort_accountability.tsv"],
            "what": "Patient-level development and external flow, joined to measured assay coverage.",
            "how": "Blue/grey bars are development patients, green/red bars are W6 external patients, and amber/purple bars separately count unique W3-excluded patients and excluded specimen/assay rows. These W3 bars are not additive flow categories. The TSV retains each unit and reason.",
            "supports": "The software preserves separate development and external populations and explicit exclusions.",
            "cannot_establish": "These fixture counts do not establish real-cohort eligibility, independence or representativeness.",
        },
        {
            "figure": 2,
            "figure_file": FIGURE_FILES[1],
            "source_tables": ["tables/figure_2_frozen_probe_state.tsv"],
            "what": "The promoter probes selected or excluded by the frozen W5 feature state.",
            "how": "Green bars count selected probes and red bars count excluded probes. Each bar aggregates exact probe-state rows; exclusion reasons remain in the linked TSV.",
            "supports": "W7 reports the actual training-frozen probe state rather than inventing molecular values.",
            "cannot_establish": "No promoter-expression association, composition adjustment, MethylCIBERSORT result or causal silencing claim was computed.",
        },
        {
            "figure": 3,
            "figure_file": FIGURE_FILES[2],
            "source_tables": [
                "tables/figure_3_development_predictions.tsv",
                "tables/figure_3_development_metrics.tsv",
            ],
            "what": "Observed synthetic Y against baseline and extended nested out-of-fold predictions.",
            "how": "Blue points are baseline f0 and red points are extended f1. Points nearer the dashed identity line have smaller error; both models use identical axes. The displayed pooled Delta_R2 is sourced from the linked metrics TSV.",
            "supports": "This visualizes W5 internal development behavior and retains both better and worse errors.",
            "cannot_establish": "Internal synthetic performance is not independent validation or biological evidence.",
        },
        {
            "figure": 4,
            "figure_file": FIGURE_FILES[3],
            "source_tables": [
                "tables/figure_4_external_predictions.tsv",
                "tables/figure_4_external_metrics.tsv",
            ],
            "what": "Observed synthetic external Y against frozen baseline and extended W6 predictions.",
            "how": "Blue points are baseline f0 and red points are extended f1, plotted for the same eligible patients against the dashed identity line. The interval is the 2.5th-to-97.5th percentile of paired-patient bootstrap Delta_R2 draws; it describes fixture resampling variability and is not a separately declared significance test.",
            "supports": "The reporting path preserves a negative, null or undefined result without changing layout.",
            "cannot_establish": "This fixture does not validate CPC-GENE biology, clinical ICI response, treatment benefit or a broad immune-barrier claim.",
        },
    ]
    report_payload = {
        "schema_version": "B-W7-report-1",
        "purpose": "synthetic-test",
        "synthetic": True,
        "synthetic_label": SYNTHETIC_LABEL,
        "scope_status": "partial-apm-component",
        "broader_immune_barrier_framework_complete": False,
        "methylcibersort_status": "pending-source-reference-platform-and-statistical-contracts",
        "w8_status": "not-consumed-by-this-W7-report",
        "metrics": {
            "development_delta_r2": development_metrics.get("pooled", {}).get("delta_r2"),
            "external_delta_r2": metrics.get("delta_r2"),
            "external_status": metrics.get("status"),
        },
        "figures": explanations,
    }
    atomic_write_json(work / "report.json", report_payload)
    report_lines = [
        "# Paper B W7 synthetic APM-component report",
        "",
        f"**{SYNTHETIC_LABEL}.**",
        "",
        "Status: partial APM component report. The broader immune-deficit/epigenetic/composition framework is not complete. Downstream W8 software status is recorded in ../run_status.json. MethylCIBERSORT is not implemented here.",
        "",
        f"W5 pooled internal Delta_R2: {_format_metric(report_payload['metrics']['development_delta_r2'])}.",
        f"W6 external Delta_R2: {_format_metric(report_payload['metrics']['external_delta_r2'])} ({report_payload['metrics']['external_status']}).",
        "",
    ]
    for item in explanations:
        table_links = " · ".join(
            f"[Source table {index}]({path})"
            for index, path in enumerate(item["source_tables"], start=1)
        )
        report_lines.extend(
            [
                f"## Figure {item['figure']}",
                "",
                f"[Open SVG]({item['figure_file']}) · {table_links}",
                "",
                f"What is plotted: {item['what']}",
                "",
                f"How to read it: {item['how']}",
                "",
                f"What it supports: {item['supports']}",
                "",
                f"What it cannot establish: {item['cannot_establish']}",
                "",
            ]
        )
    report_lines.extend(
        [
            "## Open scientific work",
            "",
            "Real feature construction and evaluation remain behind E1–E4/E6 and release review. The revised immune-barrier figures require separately frozen deficit, association, composition and B-to-C contracts. Missing analyses remain explicit gaps; no composite barrier score or placeholder biological value was generated.",
            "",
        ]
    )
    atomic_write_bytes(work / "report.md", "\n".join(report_lines).encode("utf-8"))

    table_paths = sorted((work / "tables").glob("*.tsv"), key=lambda path: path.name)
    traceability = {
        "schema_version": "B-W7-traceability-1",
        "synthetic": True,
        "scope_status": "partial-apm-component",
        "source_artifacts": {
            "W3/checksums.json": sha256_file(w3_dir / "checksums.json"),
            "W3/coverage.tsv": sha256_file(w3_dir / "coverage.tsv"),
            "W3/exclusions.tsv": sha256_file(w3_dir / "exclusions.tsv"),
            "W5/checksums.json": sha256_file(w5_dir / "checksums.json"),
            "W5/bundle/development_metrics.json": sha256_file(w5_dir / "bundle" / "development_metrics.json"),
            "W5/bundle/final_feature_state.json": sha256_file(w5_dir / "bundle" / "final_feature_state.json"),
            "W5/bundle/oof_predictions.tsv": sha256_file(w5_dir / "bundle" / "oof_predictions.tsv"),
            "W6/checksums.json": sha256_file(w6_dir / "checksums.json"),
            "W6/evaluation.json": sha256_file(w6_dir / "evaluation.json"),
            "W6/predictions.tsv": sha256_file(w6_dir / "predictions.tsv"),
        },
        "figure_sources": {
            item["figure_file"]: item["source_tables"] for item in explanations
        },
        "source_table_hashes": {f"tables/{path.name}": sha256_file(path) for path in table_paths},
    }
    atomic_write_json(work / "traceability.json", traceability)

    payloads = [work / rel for rel in FIGURE_FILES]
    payloads.extend(table_paths)
    payloads.extend([work / "report.json", work / "report.md", work / "traceability.json"])
    artifact_hashes = {path.relative_to(work).as_posix(): sha256_file(path) for path in payloads}
    scientific = {
        "schema_version": "B-W7-manifest-v1",
        "stage": "W7",
        "synthetic": True,
        "synthetic_label": SYNTHETIC_LABEL,
        "scope_status": "partial-apm-component",
        "broader_immune_barrier_framework_complete": False,
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "interpreter": interpreter,
        "figure_count": 4,
        "artifact_hashes": artifact_hashes,
        "pipeline_complete": False,
    }
    atomic_write_json(work / "checksums.json", scientific)
    manifest = dict(scientific)
    manifest["created_utc"] = utc_stamp()
    atomic_write_json(work / "manifest.json", manifest)
    atomic_write_json(
        work / "COMPLETE.json",
        {
            "stage": "W7",
            "status": "complete",
            "synthetic": True,
            "scope_status": "partial-apm-component",
            "checksums_sha256": sha256_file(work / "checksums.json"),
            "manifest_sha256": sha256_file(work / "manifest.json"),
            "parent_hashes": parent_hashes,
            "code_identity_sha256": code_identity,
            "figure_count": 4,
            "pipeline_complete": False,
        },
    )
    publish_directory(work, stage_dir)
    return json_no_dups((stage_dir / "manifest.json").read_bytes())
