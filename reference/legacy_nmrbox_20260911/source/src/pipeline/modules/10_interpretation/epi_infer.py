from __future__ import annotations

from pathlib import Path

from . import contracts as c
from ...common.io import read_tsv


EPIGENETIC_PROXIES = [
    "EPIGENETIC_IMMUNE_PRIMING",
    "EPIGENETIC_CHECKPOINT_REGULATION",
    "PRC2_IMMUNE_TARGETS",
    "SWI_SNF_ICB",
    "DNMT_IMMUNE_LOCI",
    "HISTONE_WRITERS_ICB",
    "RETROELEMENT_SENSING",
    "T_CELL_EXHAUSTION_EPIGENETIC",
    "T_CELL_MEMORY_EPIGENETIC",
]


def _association(rows: list[dict[str, object]], proxy: str) -> dict[str, object]:
    resp = [
        c.float_or_nan(r.get("score"))
        for r in rows
        if r.get("regulator_proxy") == proxy and str(r.get("response_label")) == "responder"
    ]
    non = [
        c.float_or_nan(r.get("score"))
        for r in rows
        if r.get("regulator_proxy") == proxy and str(r.get("response_label")) == "non_responder"
    ]
    resp_f = c.finite(resp)
    non_f = c.finite(non)
    if len(resp_f) < 2 or len(non_f) < 2:
        return c.with_claim(
            {
                "regulator_proxy": proxy,
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
            "regulator_proxy": proxy,
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


def infer_scores(results_root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    ssgsea_path = Path(results_root) / "immune_state" / "ssgsea_scores.tsv"
    if not ssgsea_path.exists():
        audit = [
            c.with_claim(
                {
                    "module": "epi_infer",
                    "input_name": "ssgsea_scores",
                    "input_path": str(ssgsea_path),
                    "status": "missing",
                    "detail": "Stage 09 epigenetic layer scores unavailable.",
                },
                "discovery",
            )
        ]
        return [], [], audit
    rows = read_tsv(ssgsea_path)
    available = [proxy for proxy in EPIGENETIC_PROXIES if rows and proxy in rows[0]]
    response_lookup = c.sample_response_lookup(results_root)
    score_rows: list[dict[str, object]] = []
    for row in rows:
        sid = row.get("sample_id", "")
        lookup = response_lookup.get(sid, {})
        for proxy in available:
            score = c.float_or_nan(row.get(proxy))
            score_rows.append(
                c.with_claim(
                    {
                        "cohort_id": row.get("cohort_id") or lookup.get("cohort_id", ""),
                        "sample_id": sid,
                        "patient_uid": row.get("patient_uid") or lookup.get("patient_uid", ""),
                        "regulator_proxy": proxy,
                        "score": f"{score:.6g}" if score == score else "",
                        "method": "ssgsea_epigenetic_layer_proxy",
                        "response_label": lookup.get("response_label", ""),
                    },
                    "mechanism_hypothesis",
                )
            )
    assoc_rows = [_association(score_rows, proxy) for proxy in available]
    audit_rows = [
        c.with_claim(
            {
                "module": "epi_infer",
                "input_name": "ssgsea_scores",
                "input_path": str(ssgsea_path),
                "status": "ok" if available else "missing_epigenetic_proxy_columns",
                "detail": f"rows={len(rows)};available_proxies={';'.join(available)}",
            },
            "discovery",
        )
    ]
    return score_rows, assoc_rows, audit_rows


def run(
    results_root: Path,
    out: Path | None = None,
    command: str = "interpret epi-infer",
) -> list[Path]:
    interp_root = c.interpretation_root(results_root, out)
    out_dir = interp_root / "epigenetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    score_rows, assoc_rows, audit_rows = infer_scores(results_root)
    score_path = out_dir / "inferred_scores.tsv"
    assoc_path = out_dir / "epi_response_assoc.tsv"
    audit_path = out_dir / "epi_input_audit.tsv"
    c.write_claim_tsv(score_path, c.EPI_SCORE_FIELDS, score_rows)
    c.write_claim_tsv(assoc_path, c.EPI_ASSOC_FIELDS, assoc_rows)
    c.write_claim_tsv(audit_path, c.AUDIT_FIELDS, audit_rows)
    c.write_reproducibility(out_dir, command, [Path(results_root) / "immune_state" / "ssgsea_scores.tsv"])
    c.append_analysis_log(interp_root, f"interpret epi-infer outputs={out_dir}")
    return [score_path, assoc_path, audit_path]

