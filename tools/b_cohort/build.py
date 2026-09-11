"""Build canonical specimen, assay, covariate, exclusion and coverage tables."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from tools.b_formats.records import (
    ExpressionRecord,
    MethylationRecord,
    parse_cpc_expression,
    parse_cpc_methylation,
    parse_tcga_methylation,
    parse_tcga_star_expression,
)
from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_json,
    atomic_write_tsv,
    code_identity_sha256,
    json_no_dups,
    parse_optional_float,
    publish_directory,
    read_tsv,
    remove_tree,
    sha256_file,
    utc_stamp,
)

SCHEMA_VERSION = "B-W3-cohort-v1"
WGS_PURITY_ALIASES = {
    "WGS_BASED_PURITY_ESTIMATION",
    "wgs_based_purity_estimation",
    "wgs_purity",
}


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W3 {message}", code, "W3")


def _index(header: list[str]) -> dict[str, int]:
    return {name: i for i, name in enumerate(header)}


def _require_cols(header: list[str], required: list[str], label: str) -> dict[str, int]:
    missing = [name for name in required if name not in header]
    if missing:
        _fail(f"reason=missing-column table={label} column={missing[0]}")
    return _index(header)


def load_table(path: Path, required: list[str], label: str) -> tuple[list[str], list[list[str]], dict[str, int]]:
    header, rows = read_tsv(path)
    idx = _require_cols(header, required, label)
    return header, rows, idx


def _payload_path(w2_dir: Path, source_id: str) -> Path:
    path = w2_dir / "cache" / source_id / "payload"
    if not path.is_file():
        _fail(f"reason=missing-acquired-payload source_id={source_id}")
    return path


def _parse_source(
    source: dict[str, Any],
    w2_dir: Path,
    assay_id: str | None,
    annotation_release: str,
    abundance_type: str | None,
) -> tuple[list[ExpressionRecord], list[MethylationRecord], dict[str, Any]]:
    payload = _payload_path(w2_dir, source["source_id"]).read_bytes()
    fmt = source["format"]
    expr: list[ExpressionRecord] = []
    meth: list[MethylationRecord] = []
    meta: dict[str, Any] = {"format": fmt, "source_id": source["source_id"]}
    if fmt == "tcga-star-expression":
        if not assay_id:
            _fail(f"reason=missing-assay-id source_id={source['source_id']}")
        parsed = parse_tcga_star_expression(
            payload,
            assay_id=assay_id,
            annotation_release=annotation_release,
            abundance_type=abundance_type or "tpm_unstranded",
        )
        expr = list(parsed.records)
        meta["summary_gene_ids"] = list(parsed.summary_gene_ids)
        meta["comment_lines"] = list(parsed.comment_lines)
    elif fmt == "cpc-expression":
        parsed = parse_cpc_expression(
            payload,
            annotation_release=annotation_release,
            abundance_type=abundance_type or "author-processed-expression",
        )
        expr = list(parsed.records)
        meta["sample_assay_ids"] = list(parsed.sample_assay_ids)
    elif fmt == "tcga-methylation-beta":
        if not assay_id:
            _fail(f"reason=missing-assay-id source_id={source['source_id']}")
        parsed = parse_tcga_methylation(payload, assay_id=assay_id)
        meth = list(parsed.records)
        meta["first_probe_id"] = parsed.first_probe_id
    elif fmt == "cpc-methylation":
        parsed = parse_cpc_methylation(payload)
        meth = list(parsed.records)
        meta["sample_assay_ids"] = list(parsed.sample_assay_ids)
        meta["header_repaired"] = parsed.header_repaired
    else:
        _fail(f"reason=unsupported-format {fmt}")
    return expr, meth, meta


def _median(values: list[float]) -> float:
    return float(median(values))


def run_cohort(
    config: dict[str, Any],
    *,
    repo_root: Path,
    w2_dir: Path,
    stage_dir: Path,
    parent_hashes: dict[str, str],
    code_identity: str,
    interpreter: str,
) -> dict[str, Any]:
    w3 = config["w3"]
    policy = w3["specimen_policy"]
    if policy.get("label") != "synthetic-fixture-only":
        _fail("reason=non-fixture-policy-rejected")
    if not policy.get("forbid_wgs_agreement_as_purity"):
        _fail("reason=wgs-purity-quarantine-required")
    annotation_release = w3["annotation"]["release"]
    universe_path = repo_root / w3["annotation"]["gene_universe_path"]
    probe_map_path = repo_root / w3["annotation"]["probe_map_path"]
    gene_map_path = repo_root / w3["annotation"]["gene_map_path"]
    specimen_path = repo_root / w3["identity"]["specimen_map_path"]
    covariate_path = repo_root / w3["identity"]["covariate_path"]

    spec_header, spec_rows, spec_idx = load_table(
        specimen_path,
        [
            "cohort",
            "patient_id",
            "specimen_id",
            "focus_id",
            "aliquot_id",
            "assay_id",
            "source_id",
            "platform",
            "modality",
            "match_status",
            "inclusion",
            "reason",
        ],
        "specimens",
    )
    gene_header, gene_rows, gene_idx = load_table(
        gene_map_path,
        ["raw_id", "canonical_symbol", "stable_gene_id", "mapping_status"],
        "gene_map",
    )
    uni_header, uni_rows, uni_idx = load_table(
        universe_path,
        ["stable_gene_id", "symbol"],
        "gene_universe",
    )
    probe_header, probe_rows, probe_idx = load_table(
        probe_map_path,
        ["probe_id", "target_gene_id", "promoter_category", "mask_status"],
        "probe_map",
    )
    cov_header, cov_rows, cov_idx = load_table(
        covariate_path,
        ["specimen_id", "patient_id", "age_years", "gleason_sum", "qpure_cellularity"],
        "covariates",
    )

    gene_map: dict[tuple[str, str], dict[str, str]] = {}
    for row_no, row in enumerate(gene_rows, start=2):
        raw_id = row[gene_idx["raw_id"]]
        source = row[gene_idx["source"]] if "source" in gene_idx else ""
        key = (raw_id, source)
        if key in gene_map:
            _fail(f"reason=duplicate-gene-map raw_id={raw_id} source={source}")
        gene_map[key] = {
            "raw_id": raw_id,
            "symbol": row[gene_idx["canonical_symbol"]],
            "stable_gene_id": row[gene_idx["stable_gene_id"]],
            "mapping_status": row[gene_idx["mapping_status"]],
            "source": source,
        }
    raw_to_maps: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in gene_map.values():
        raw_to_maps[item["raw_id"]].append(item)

    universe = []
    universe_ids = set()
    for row in uni_rows:
        sid = row[uni_idx["stable_gene_id"]]
        if sid in universe_ids:
            _fail(f"reason=duplicate-universe-id {sid}")
        universe_ids.add(sid)
        universe.append(sid)

    specimens: list[dict[str, str]] = []
    assay_index: dict[tuple[str, str], dict[str, str]] = {}
    assay_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row_no, row in enumerate(spec_rows, start=2):
        rec = {name: row[i] for i, name in enumerate(spec_header)}
        if rec["match_status"] == "unresolved" and rec["inclusion"] == "include":
            _fail(f"reason=unresolved-identifier assay_id={rec['assay_id']}")
        key = (rec["source_id"], rec["assay_id"])
        if key in assay_index:
            _fail(f"reason=duplicate-assay-map source_id={rec['source_id']} assay_id={rec['assay_id']}")
        assay_index[key] = rec
        assay_by_id[rec["assay_id"]].append(rec)
        specimens.append(rec)

    sources_by_id = {src["source_id"]: src for src in config["sources"]}
    all_expr: list[ExpressionRecord] = []
    all_meth: list[MethylationRecord] = []
    parse_meta: list[dict[str, Any]] = []
    used_source_ids = sorted({rec["source_id"] for rec in specimens})
    for source_id in used_source_ids:
        source = sources_by_id.get(source_id)
        if source is None:
            _fail(f"reason=source-not-in-config source_id={source_id}")
        mapped = [s for s in specimens if s["source_id"] == source_id]
        if source["format"] in {"tcga-star-expression", "tcga-methylation-beta"}:
            if len(mapped) != 1:
                _fail(f"reason=single-assay-source-map-mismatch source_id={source_id}")
            assay_id = mapped[0]["assay_id"]
            abundance = None
            if source["format"] == "tcga-star-expression":
                abundance = config["w4"]["abundance_column"]["tcga-star-expression"]
            expr, meth, meta = _parse_source(
                source, w2_dir, assay_id, annotation_release, abundance
            )
        else:
            abundance = None
            if source["format"] == "cpc-expression":
                abundance = config["w4"]["abundance_column"]["cpc-expression"]
            expr, meth, meta = _parse_source(
                source, w2_dir, None, annotation_release, abundance
            )
            present = set(meta.get("sample_assay_ids", []))
            needed = {s["assay_id"] for s in mapped}
            missing = sorted(needed - present)
            if missing:
                _fail(f"reason=unresolved-identifier assay_id={missing[0]} source_id={source_id}")
        all_expr.extend(expr)
        all_meth.extend(meth)
        parse_meta.append(meta)

    expr_by_assay: dict[str, list[ExpressionRecord]] = defaultdict(list)
    for rec in all_expr:
        expr_by_assay[rec.assay_id].append(rec)
    meth_by_assay: dict[str, list[MethylationRecord]] = defaultdict(list)
    for rec in all_meth:
        meth_by_assay[rec.assay_id].append(rec)

    for rec in specimens:
        if rec["modality"] == "expression" and rec["assay_id"] not in expr_by_assay:
            _fail(f"reason=unresolved-identifier assay_id={rec['assay_id']} modality=expression")
        if rec["modality"] == "methylation" and rec["assay_id"] not in meth_by_assay:
            _fail(f"reason=unresolved-identifier assay_id={rec['assay_id']} modality=methylation")

    for assay_id, recs in expr_by_assay.items():
        mapped = assay_by_id.get(assay_id, [])
        if not mapped:
            _fail(f"reason=unresolved-identifier assay_id={assay_id} modality=expression")
        if len({(m["source_id"], m["patient_id"]) for m in mapped}) != 1 and len(mapped) > 1:
            _fail(f"reason=ambiguous-assay-join assay_id={assay_id}")

    development = policy["development_cohort"]
    external = policy["external_cohort"]
    if development == external:
        _fail("reason=cohorts-must-differ")

    included = [s for s in specimens if s["inclusion"] == "include"]
    patients_dev = {s["patient_id"] for s in included if s["cohort"] == development}
    patients_ext = {s["patient_id"] for s in included if s["cohort"] == external}
    overlap = sorted(patients_dev & patients_ext)
    if overlap:
        _fail(f"reason=tcga-external-patient-overlap patient_id={overlap[0]}")

    duplicate_rows = [s["patient_id"] for s in included]
    # identity uniqueness of assay_id globally
    all_assay_ids = [s["assay_id"] for s in specimens]
    if len(set(all_assay_ids)) != len(all_assay_ids):
        # same assay_id may appear if source differs? we keyed by source+assay
        counts: dict[str, int] = defaultdict(int)
        for s in specimens:
            counts[f"{s['source_id']}::{s['assay_id']}"] += 1
        for key, n in counts.items():
            if n > 1:
                _fail(f"reason=duplicate-patient-identity {key}")

    def _collapse_group(rows: list[dict[str, str]], modality: str) -> None:
        by_patient_focus: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        for rec in rows:
            if rec["inclusion"] != "include" or rec["modality"] != modality:
                continue
            by_patient_focus[(rec["patient_id"], rec["specimen_id"], rec["focus_id"] or "")].append(rec)
        for (patient_id, specimen_id, focus_id), group in by_patient_focus.items():
            foci = {s["focus_id"] for s in [r for r in included if r["patient_id"] == patient_id and r["modality"] == modality]}
            if "" in foci and policy.get("unresolved_identifier") == "fail":
                if any(s["focus_id"] == "" for s in group):
                    _fail(f"reason=unresolved-identifier patient_id={patient_id} modality={modality}")
        patient_foci: dict[str, set[str]] = defaultdict(set)
        for rec in rows:
            if rec["inclusion"] == "include" and rec["modality"] == modality:
                patient_foci[rec["patient_id"]].add(rec["focus_id"])
        for patient_id, foci in patient_foci.items():
            if len(foci) > 1:
                if policy.get("ambiguous_focus") == "fail":
                    _fail(f"reason=ambiguous-focus-join patient_id={patient_id} modality={modality}")

    _collapse_group(specimens, "expression")
    _collapse_group(specimens, "methylation")

    # One included expression specimen/patient after collapsing same-focus replicates.
    expr_eval: dict[str, list[dict[str, str]]] = defaultdict(list)
    meth_eval: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rec in included:
        if rec["modality"] == "expression":
            expr_eval[rec["patient_id"]].append(rec)
        elif rec["modality"] == "methylation":
            meth_eval[rec["patient_id"]].append(rec)
    for patient_id, recs in expr_eval.items():
        specimen_ids = {r["specimen_id"] for r in recs}
        if len(specimen_ids) > 1:
            _fail(f"reason=more-than-one-evaluation-row patient_id={patient_id}")
    for patient_id, recs in meth_eval.items():
        specimen_ids = {r["specimen_id"] for r in recs}
        if len(specimen_ids) > 1:
            _fail(f"reason=more-than-one-evaluation-row patient_id={patient_id}")

    replicate_policy = policy["technical_replicate_collapse"]
    same_focus_rule = replicate_policy["same_focus_same_specimen"]
    if same_focus_rule not in {"median_beta_first_expression"}:
        _fail("reason=unknown-replicate-policy")

    canonical_expr_rows: list[list[Any]] = []
    expr_headers = [
        "specimen_id",
        "patient_id",
        "cohort",
        "assay_id",
        "stable_gene_id",
        "symbol",
        "raw_gene_id",
        "value",
        "abundance_type",
        "annotation_release",
        "source_missing_token",
        "synthetic",
    ]
    for patient_id, recs in sorted(expr_eval.items()):
        chosen = sorted(recs, key=lambda r: r["assay_id"])[0]
        source = sources_by_id[chosen["source_id"]]
        map_source = "tcga-star" if source["format"] == "tcga-star-expression" else "cpc-expression"
        for rec in sorted(expr_by_assay[chosen["assay_id"]], key=lambda r: r.raw_gene_id):
            mapped_list = [m for m in raw_to_maps.get(rec.raw_gene_id, []) if m["source"] in {map_source, ""}]
            if not mapped_list:
                mapped_list = raw_to_maps.get(rec.raw_gene_id, [])
            if not mapped_list:
                _fail(f"reason=unresolved-identifier gene_id={rec.raw_gene_id} assay_id={chosen['assay_id']}")
            statuses = {m["mapping_status"] for m in mapped_list}
            if "ambiguous" in statuses or len({m["stable_gene_id"] for m in mapped_list}) != 1:
                _fail(f"reason=ambiguous-focus-join gene_id={rec.raw_gene_id}")
            mapped = mapped_list[0]
            if mapped["mapping_status"] != "mapped":
                _fail(f"reason=unresolved-identifier gene_id={rec.raw_gene_id}")
            canonical_expr_rows.append(
                [
                    chosen["specimen_id"],
                    chosen["patient_id"],
                    chosen["cohort"],
                    chosen["assay_id"],
                    mapped["stable_gene_id"],
                    mapped["symbol"],
                    rec.raw_gene_id,
                    rec.value,
                    rec.abundance_type,
                    rec.annotation_release,
                    rec.source_missing_token,
                    True,
                ]
            )

    meth_headers = [
        "specimen_id",
        "patient_id",
        "cohort",
        "assay_id",
        "probe_id",
        "beta",
        "detection_p",
        "source_missing_token",
        "processing_release",
        "synthetic",
    ]
    canonical_meth_rows: list[list[Any]] = []
    for patient_id, recs in sorted(meth_eval.items()):
        by_probe: dict[str, list[tuple[dict[str, str], MethylationRecord]]] = defaultdict(list)
        for spec in recs:
            for rec in meth_by_assay[spec["assay_id"]]:
                by_probe[rec.probe_id].append((spec, rec))
        chosen_spec = sorted(recs, key=lambda r: r["assay_id"])[0]
        for probe_id in sorted(by_probe):
            pairs = by_probe[probe_id]
            if len({p[0]["focus_id"] for p in pairs}) > 1:
                _fail(f"reason=ambiguous-focus-join patient_id={patient_id} probe_id={probe_id}")
            betas = [p[1].beta for p in pairs if p[1].beta is not None]
            dets = [p[1].detection_p for p in pairs if p[1].detection_p is not None]
            missing_tokens = [p[1].source_missing_token for p in pairs if p[1].source_missing_token]
            if len(pairs) == 1:
                beta = pairs[0][1].beta
                det = pairs[0][1].detection_p
                token = pairs[0][1].source_missing_token
                assay_id = pairs[0][0]["assay_id"]
            else:
                beta = _median(betas) if betas else None
                det = _median(dets) if dets else None
                token = missing_tokens[0] if missing_tokens and beta is None else None
                assay_id = ",".join(sorted({p[0]["assay_id"] for p in pairs}))
            canonical_meth_rows.append(
                [
                    chosen_spec["specimen_id"],
                    chosen_spec["patient_id"],
                    chosen_spec["cohort"],
                    assay_id,
                    probe_id,
                    beta,
                    det,
                    token,
                    annotation_release,
                    True,
                ]
            )

    cov_by_specimen = {}
    for row_no, row in enumerate(cov_rows, start=2):
        rec = {name: row[i] for i, name in enumerate(cov_header)}
        if rec["specimen_id"] in cov_by_specimen:
            _fail(f"reason=duplicate-covariate-row specimen_id={rec['specimen_id']}")
        for name in rec:
            if name in WGS_PURITY_ALIASES or name.upper() == "WGS_BASED_PURITY_ESTIMATION":
                continue
        cov_by_specimen[rec["specimen_id"]] = rec

    cov_out_headers = [
        "specimen_id",
        "patient_id",
        "cohort",
        "age_years",
        "gleason_primary",
        "gleason_secondary",
        "gleason_sum",
        "approved_grade_category",
        "purity_value",
        "purity_method",
        "purity_scale",
        "purity_source_specimen",
        "purity_source_field",
        "wgs_agreement_quarantined",
        "synthetic",
    ]
    cov_out_rows: list[list[Any]] = []
    eval_specimens = {}
    for rec in included:
        eval_specimens.setdefault(rec["patient_id"], rec["specimen_id"])
        if eval_specimens[rec["patient_id"]] != rec["specimen_id"]:
            _fail(f"reason=more-than-one-evaluation-row patient_id={rec['patient_id']}")

    purity_method = config["w4"]["covariate_policy"]["purity_method"]
    purity_scale = config["w4"]["covariate_policy"]["purity_scale"]
    purity_field = config["w4"]["covariate_policy"]["purity_source_field"]
    quarantine_fields = set(config["w4"]["covariate_policy"]["quarantine_fields"])
    for patient_id, specimen_id in sorted(eval_specimens.items()):
        raw = cov_by_specimen.get(specimen_id)
        if raw is None:
            _fail(f"reason=unresolved-identifier specimen_id={specimen_id} table=covariates")
        for field in quarantine_fields:
            if field in raw and purity_field == field:
                _fail("reason=wgs-agreement-used-as-purity")
        wgs_value = None
        for field in quarantine_fields:
            if field in raw:
                wgs_value = raw[field]
        if purity_field not in raw:
            _fail(f"reason=missing-purity-source-field field={purity_field}")
        if purity_field in quarantine_fields or purity_field in WGS_PURITY_ALIASES:
            _fail("reason=wgs-agreement-used-as-purity")
        purity_value = parse_optional_float(raw[purity_field], field=purity_field, row=1)
        cohort = next(s["cohort"] for s in included if s["patient_id"] == patient_id)
        cov_out_rows.append(
            [
                specimen_id,
                patient_id,
                cohort,
                parse_optional_float(raw.get("age_years", "NA"), field="age_years", row=1),
                raw.get("gleason_primary", "NA"),
                raw.get("gleason_secondary", "NA"),
                parse_optional_float(raw.get("gleason_sum", "NA"), field="gleason_sum", row=1),
                raw.get("approved_grade_category", "NA"),
                purity_value,
                purity_method,
                purity_scale,
                specimen_id,
                purity_field,
                wgs_value if wgs_value not in {None, ""} else "NA",
                True,
            ]
        )

    excluded_specimens = [s for s in specimens if s["inclusion"] != "include"]
    exclusion_headers = [
        "patient_id",
        "specimen_id",
        "assay_id",
        "cohort",
        "modality",
        "exclusion_reason",
        "rule_version",
        "synthetic",
    ]
    exclusion_rows = [
        [
            s["patient_id"],
            s["specimen_id"],
            s["assay_id"],
            s["cohort"],
            s["modality"],
            s["reason"],
            policy.get("rule_version", "synthetic-fixture-v1"),
            True,
        ]
        for s in excluded_specimens
    ]

    coverage_headers = [
        "patient_id",
        "cohort",
        "expression_gene_count",
        "expression_finite_in_u",
        "methylation_probe_count",
        "methylation_finite_count",
        "has_covariates",
        "synthetic",
    ]
    u_set = set(universe)
    expr_by_patient: dict[str, list[list[Any]]] = defaultdict(list)
    for row in canonical_expr_rows:
        expr_by_patient[row[1]].append(row)
    meth_by_patient: dict[str, list[list[Any]]] = defaultdict(list)
    for row in canonical_meth_rows:
        meth_by_patient[row[1]].append(row)
    coverage_rows = []
    for patient_id, specimen_id in sorted(eval_specimens.items()):
        erows = expr_by_patient.get(patient_id, [])
        mrows = meth_by_patient.get(patient_id, [])
        finite_u = sum(
            1
            for r in erows
            if r[4] in u_set and r[7] is not None
        )
        finite_m = sum(1 for r in mrows if r[5] is not None)
        cohort = next(s["cohort"] for s in included if s["patient_id"] == patient_id)
        coverage_rows.append(
            [
                patient_id,
                cohort,
                len(erows),
                finite_u,
                len(mrows),
                finite_m,
                specimen_id in cov_by_specimen,
                True,
            ]
        )

    spec_out_headers = [
        "cohort",
        "patient_id",
        "specimen_id",
        "focus_id",
        "aliquot_id",
        "assay_id",
        "source_id",
        "platform",
        "modality",
        "match_evidence",
        "match_status",
        "rule_version",
        "inclusion",
        "reason",
        "synthetic",
    ]
    spec_out_rows = []
    for s in specimens:
        spec_out_rows.append(
            [
                s["cohort"],
                s["patient_id"],
                s["specimen_id"],
                s.get("focus_id") or "NA",
                s.get("aliquot_id") or "NA",
                s["assay_id"],
                s["source_id"],
                s["platform"],
                s["modality"],
                s.get("match_evidence", "NA"),
                s["match_status"],
                s.get("rule_version", policy.get("rule_version", "synthetic-fixture-v1")),
                s["inclusion"],
                s["reason"],
                True,
            ]
        )

    work = stage_dir.parent / f"{stage_dir.name}.work"
    if work.exists():
        remove_tree(work)
    work.mkdir(parents=True)
    hashes = {}
    hashes["specimens.tsv"] = atomic_write_tsv(work / "specimens.tsv", spec_out_headers, spec_out_rows)
    hashes["expression.tsv"] = atomic_write_tsv(work / "expression.tsv", expr_headers, canonical_expr_rows)
    hashes["methylation.tsv"] = atomic_write_tsv(work / "methylation.tsv", meth_headers, canonical_meth_rows)
    hashes["covariates.tsv"] = atomic_write_tsv(work / "covariates.tsv", cov_out_headers, cov_out_rows)
    hashes["exclusions.tsv"] = atomic_write_tsv(work / "exclusions.tsv", exclusion_headers, exclusion_rows)
    hashes["coverage.tsv"] = atomic_write_tsv(work / "coverage.tsv", coverage_headers, coverage_rows)

    scientific = {
        "schema_version": SCHEMA_VERSION,
        "stage": "W3",
        "synthetic": True,
        "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a real cohort or specimen policy.",
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "interpreter": interpreter,
        "development_cohort": development,
        "external_cohort": external,
        "n_specimens": len(spec_out_rows),
        "n_expression_rows": len(canonical_expr_rows),
        "n_methylation_rows": len(canonical_meth_rows),
        "n_evaluation_patients": len(eval_specimens),
        "n_exclusions": len(exclusion_rows),
        "universe_ids": universe,
        "parse_meta": parse_meta,
        "artifact_hashes": hashes,
        "wgs_agreement_never_used_as_purity": True,
        "policy_label": policy["label"],
    }
    hashes["checksums.json"] = None
    atomic_write_json(work / "checksums.json", {k: v for k, v in scientific.items() if k != "parse_meta"})
    hashes["checksums.json"] = sha256_file(work / "checksums.json")
    manifest = dict(scientific)
    manifest["created_utc"] = utc_stamp()
    manifest["artifact_hashes"] = hashes
    atomic_write_json(work / "manifest.json", manifest)
    complete = {
        "stage": "W3",
        "status": "complete",
        "synthetic": True,
        "checksums_sha256": hashes["checksums.json"],
        "manifest_sha256": sha256_file(work / "manifest.json"),
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
    }
    atomic_write_json(work / "COMPLETE.json", complete)
    publish_directory(work, stage_dir)
    return json_no_dups((stage_dir / "manifest.json").read_bytes())
