from __future__ import annotations

from pathlib import Path

from . import contracts as c
from ...common.io import read_tsv


FEATURE_MAP = {
    "hope_checkpoint_expression": "EPIGENETIC_CHECKPOINT_REGULATION",
    "hope_tcell_inflamed_gep": "T_CELL_INFLAMED_GEP_18",
    "hope_ifng_signature": "HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI",
    "hope_composite_rna": "HOPE_18",
}


def load_criteria(path: Path) -> list[dict[str, str]]:
    rows = read_tsv(path)
    required = {"criteria_id", "rna_derivable", "data_type", "method"}
    if rows:
        missing = required - set(rows[0])
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")
    return rows


def _median(values: list[float]) -> float:
    vals = sorted(c.finite(values))
    if not vals:
        return float("nan")
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2


def phenotype_class(criteria_id: str, score: float, median: float) -> str:
    if not score == score or not median == median:
        return "unclassified"
    high = score >= median
    if criteria_id == "hope_tcell_inflamed_gep":
        return "hot_tis_like" if high else "cold_tis_low"
    if criteria_id == "hope_ifng_signature":
        return "ifng_high" if high else "ifng_low"
    if criteria_id == "hope_checkpoint_expression":
        return "checkpoint_axis_high" if high else "checkpoint_axis_low"
    if criteria_id == "hope_composite_rna":
        return "hope_rna_favorable" if high else "hope_rna_low"
    return "rna_proxy_high" if high else "rna_proxy_low"


def _association(rows: list[dict[str, object]], criteria_id: str, phenotype: str) -> dict[str, object]:
    resp = [
        c.float_or_nan(r.get("score"))
        for r in rows
        if r.get("criteria_id") == criteria_id and str(r.get("response_label")) == "responder"
    ]
    non = [
        c.float_or_nan(r.get("score"))
        for r in rows
        if r.get("criteria_id") == criteria_id and str(r.get("response_label")) == "non_responder"
    ]
    resp_f = c.finite(resp)
    non_f = c.finite(non)
    if len(resp_f) < 2 or len(non_f) < 2:
        return c.with_claim(
            {
                "criteria_id": criteria_id,
                "phenotype_class": phenotype,
                "n_responder": len(resp_f),
                "n_non_responder": len(non_f),
                "mean_responder": f"{c.mean(resp_f):.6g}" if resp_f else "",
                "mean_non_responder": f"{c.mean(non_f):.6g}" if non_f else "",
                "effect_responder_minus_non_responder": "",
                "p_value": "",
                "status": "insufficient_response_groups",
            },
            "mechanism_hypothesis",
        )
    diff = c.mean(resp_f) - c.mean(non_f)
    se = ((c.stdev(resp_f) ** 2 / len(resp_f)) + (c.stdev(non_f) ** 2 / len(non_f))) ** 0.5
    p_value = c.normal_two_sided_p(diff / se) if se > 0 else 1.0
    return c.with_claim(
        {
            "criteria_id": criteria_id,
            "phenotype_class": phenotype,
            "n_responder": len(resp_f),
            "n_non_responder": len(non_f),
            "mean_responder": f"{c.mean(resp_f):.6g}",
            "mean_non_responder": f"{c.mean(non_f):.6g}",
            "effect_responder_minus_non_responder": f"{diff:.6g}",
            "p_value": f"{p_value:.6g}",
            "status": "ok",
        },
        "mechanism_hypothesis",
    )


def score_samples(
    results_root: Path,
    criteria_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    ssgsea_path = Path(results_root) / "immune_state" / "ssgsea_scores.tsv"
    if not ssgsea_path.exists():
        audit = [
            c.with_claim(
                {
                    "module": "immunophenotype",
                    "input_name": "ssgsea_scores",
                    "input_path": str(ssgsea_path),
                    "status": "missing",
                    "detail": "Stage 09 scores unavailable; cannot score RNA immunophenotypes.",
                },
                "discovery",
            )
        ]
        return [], [], [], audit
    score_rows = read_tsv(ssgsea_path)
    response_lookup = c.sample_response_lookup(results_root)
    sample_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = [
        c.with_claim(
            {
                "module": "immunophenotype",
                "input_name": "ssgsea_scores",
                "input_path": str(ssgsea_path),
                "status": "ok",
                "detail": f"rows={len(score_rows)}",
            },
            "discovery",
        )
    ]
    skipped_rows: list[dict[str, object]] = []
    available_scores: dict[str, list[float]] = {}
    for criteria in criteria_rows:
        cid = criteria.get("criteria_id", "")
        if str(criteria.get("rna_derivable", "")).strip().lower() != "yes":
            route = "spec020" if criteria.get("data_type") in {"dna_wes", "ihc", "clinical"} else "spec010"
            skipped_rows.append(
                c.with_claim(
                    {
                        "criteria_id": cid,
                        "data_type": criteria.get("data_type", ""),
                        "method": criteria.get("method", ""),
                        "skip_reason": "not_rna_derivable",
                        "route_to_spec": route,
                    },
                    "discovery",
                )
            )
            continue
        feature = FEATURE_MAP.get(cid)
        if not feature or not score_rows or feature not in score_rows[0]:
            audit_rows.append(
                c.with_claim(
                    {
                        "module": "immunophenotype",
                        "input_name": cid,
                        "input_path": str(ssgsea_path),
                        "status": "missing_direct_expression_or_matching_score",
                        "detail": "RNA-derivable in principle, but no reviewed-root expression matrix or matching Stage 09 score is available.",
                    },
                    "discovery",
                )
            )
            continue
        available_scores[cid] = [c.float_or_nan(r.get(feature)) for r in score_rows]
    medians = {cid: _median(vals) for cid, vals in available_scores.items()}
    for row in score_rows:
        sid = row.get("sample_id", "")
        lookup = response_lookup.get(sid, {})
        response = lookup.get("response_label", "")
        patient_uid = row.get("patient_uid") or lookup.get("patient_uid", "")
        cohort_id = row.get("cohort_id") or lookup.get("cohort_id", "")
        for cid in available_scores:
            feature = FEATURE_MAP[cid]
            score = c.float_or_nan(row.get(feature))
            sample_rows.append(
                c.with_claim(
                    {
                        "cohort_id": cohort_id,
                        "sample_id": sid,
                        "patient_uid": patient_uid,
                        "criteria_id": cid,
                        "score": f"{score:.6g}" if score == score else "",
                        "phenotype_class": phenotype_class(cid, score, medians[cid]),
                        "response_label": response,
                        "score_status": "ok" if score == score else "missing_score",
                    },
                    "mechanism_hypothesis",
                )
            )
    assoc_rows = []
    for cid in sorted(available_scores):
        classes = sorted({str(r["phenotype_class"]) for r in sample_rows if r.get("criteria_id") == cid})
        phenotype = ";".join(classes)
        assoc_rows.append(_association(sample_rows, cid, phenotype))
    return sample_rows, assoc_rows, skipped_rows, audit_rows


def run(
    results_root: Path,
    criteria_registry: Path,
    out: Path | None = None,
    command: str = "interpret immunophenotype",
) -> list[Path]:
    interp_root = c.interpretation_root(results_root, out)
    out_dir = interp_root / "immunophenotype"
    out_dir.mkdir(parents=True, exist_ok=True)
    criteria_rows = load_criteria(criteria_registry)
    sample_rows, assoc_rows, skipped_rows, audit_rows = score_samples(results_root, criteria_rows)
    sample_path = out_dir / "sample_phenotype.tsv"
    assoc_path = out_dir / "phenotype_response_assoc.tsv"
    skipped_path = out_dir / "hope_skipped_criteria.tsv"
    audit_path = out_dir / "immunophenotype_input_audit.tsv"
    c.write_claim_tsv(sample_path, c.PHENOTYPE_SAMPLE_FIELDS, sample_rows)
    c.write_claim_tsv(assoc_path, c.PHENOTYPE_ASSOC_FIELDS, assoc_rows)
    c.write_claim_tsv(skipped_path, c.HOPE_SKIP_FIELDS, skipped_rows)
    c.write_claim_tsv(audit_path, c.AUDIT_FIELDS, audit_rows)
    inputs = [criteria_registry, Path(results_root) / "immune_state" / "ssgsea_scores.tsv"]
    c.write_reproducibility(out_dir, command, inputs)
    c.append_analysis_log(interp_root, f"interpret immunophenotype outputs={out_dir}")
    return [sample_path, assoc_path, skipped_path, audit_path]

