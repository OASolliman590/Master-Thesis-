from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

import pandas as pd

from ...common.expression import load_expression_matrix
from ...common.io import parse_bool, read_tsv, split_accessions, write_tsv


CANDIDATE_ROSTER_FIELDS = [
    "candidate_id",
    "cohort_id",
    "eligibility_status",
    "eligibility_reason",
    "independence_status",
    "ici_treatment_status",
    "response_label_status",
    "timing_compatibility",
    "expression_compatibility",
    "n_samples_total",
    "n_responders",
    "n_non_responders",
    "claim_class",
    "curation_confidence",
]

LEAKAGE_FIELDS = [
    "candidate_id",
    "check_type",
    "candidate_value",
    "matched_derivation_value",
    "leakage_status",
    "resolution",
]

SAMPLE_MANIFEST_FIELDS = [
    "external_sample_id",
    "candidate_id",
    "cohort_id",
    "patient_id",
    "timing_category",
    "response_label",
    "therapy_agent",
    "therapy_class",
    "cancer_type",
    "expression_file",
    "include_flag",
    "exclude_reason",
]

MEMBERSHIP_FIELDS = [
    "analysis_id",
    "external_sample_id",
    "cohort_id",
    "arm",
    "timing_category",
    "response_label",
    "membership_status",
    "membership_reason",
]

SCORE_FIELDS = [
    "analysis_id",
    "signature_version",
    "signature_checksum",
    "external_sample_id",
    "cohort_id",
    "signature_score",
    "n_signature_genes",
    "n_genes_observed",
    "gene_coverage_fraction",
    "scoring_method",
]

COVERAGE_FIELDS = [
    "analysis_id",
    "cohort_id",
    "gene_symbol",
    "observed_status",
    "mapping_source",
    "missing_reason",
]

BY_COHORT_FIELDS = [
    "analysis_id",
    "cohort_id",
    "n_responders",
    "n_non_responders",
    "effect_size",
    "effect_ci_low",
    "effect_ci_high",
    "p_value",
    "auc",
    "validation_status",
    "claim_class",
    "caveat",
]

SUMMARY_FIELDS = [
    "analysis_id",
    "n_eligible_cohorts",
    "n_eligible_samples",
    "n_responders",
    "n_non_responders",
    "pooled_effect_size",
    "pooled_ci_low",
    "pooled_ci_high",
    "pooled_p_value",
    "direction_concordance",
    "validation_status",
    "claim_class",
    "plain_language_interpretation",
]

CLAIM_BOUNDARY_FIELDS = ["topic", "required_label", "disallowed_label", "report_language"]


def run_external_validation(
    *,
    candidate_roster: Path,
    derivation_lock: Path,
    sample_manifest: Path,
    signature_paths: list[Path],
    out_dir: Path,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = read_tsv(candidate_roster)
    derivation_rows = read_tsv(derivation_lock)
    sample_rows = [_normalize_sample_row(row) for row in read_tsv(sample_manifest)]
    signatures = [_load_signature(path) for path in signature_paths]

    cohort_roster, leakage_rows = review_candidate_roster(candidates, derivation_rows, sample_rows)
    normalized_samples, membership_rows = build_membership(sample_rows, cohort_roster, signatures)
    score_rows, coverage_rows = score_external_samples(membership_rows, normalized_samples, signatures)
    by_cohort_rows, summary_rows = summarize_validation(score_rows, membership_rows, signatures)
    claim_boundary_rows = external_validation_claim_boundaries()
    signature_checksum_rows = [
        {
            "analysis_id": sig["analysis_id"],
            "signature_version": sig["signature_version"],
            "signature_path": str(sig["path"]),
            "signature_checksum": sig["checksum"],
            "n_signature_genes": str(len(sig["genes"])),
        }
        for sig in signatures
    ]

    outputs = {
        "cohort_roster": out_dir / "eligibility" / "external_validation_cohort_roster.tsv",
        "leakage": out_dir / "eligibility" / "leakage_audit.tsv",
        "signature_checksums": out_dir / "eligibility" / "frozen_signature_checksums.tsv",
        "sample_manifest": out_dir / "membership" / "external_validation_sample_manifest.tsv",
        "membership": out_dir / "membership" / "external_validation_membership.tsv",
        "scores": out_dir / "scores" / "external_signature_scores.tsv",
        "coverage": out_dir / "scores" / "external_signature_gene_coverage.tsv",
        "by_cohort": out_dir / "validation" / "external_validation_by_cohort.tsv",
        "summary": out_dir / "validation" / "external_validation_summary.tsv",
        "claim_boundaries": out_dir / "validation" / "external_validation_claim_boundaries.tsv",
    }
    write_tsv(outputs["cohort_roster"], CANDIDATE_ROSTER_FIELDS, cohort_roster)
    write_tsv(outputs["leakage"], LEAKAGE_FIELDS, leakage_rows)
    write_tsv(
        outputs["signature_checksums"],
        ["analysis_id", "signature_version", "signature_path", "signature_checksum", "n_signature_genes"],
        signature_checksum_rows,
    )
    write_tsv(outputs["sample_manifest"], SAMPLE_MANIFEST_FIELDS, normalized_samples)
    write_tsv(outputs["membership"], MEMBERSHIP_FIELDS, membership_rows)
    write_tsv(outputs["scores"], SCORE_FIELDS, score_rows)
    write_tsv(outputs["coverage"], COVERAGE_FIELDS, coverage_rows)
    write_tsv(outputs["by_cohort"], BY_COHORT_FIELDS, by_cohort_rows)
    write_tsv(outputs["summary"], SUMMARY_FIELDS, summary_rows)
    write_tsv(outputs["claim_boundaries"], CLAIM_BOUNDARY_FIELDS, claim_boundary_rows)
    return list(outputs.values())


def review_candidate_roster(
    candidates: list[dict[str, str]],
    derivation_rows: list[dict[str, str]],
    sample_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    derivation_index = _build_derivation_index(derivation_rows)
    samples_by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sample_rows:
        samples_by_candidate[row.get("candidate_id", "")].append(row)
        samples_by_candidate[row.get("cohort_id", "")].append(row)

    roster_rows: list[dict[str, str]] = []
    leakage_rows: list[dict[str, str]] = []
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id", "") or candidate.get("cohort_id", "")
        cohort_id = candidate.get("cohort_id", "")
        matches = _find_derivation_overlaps(candidate, derivation_index)
        leakage_rows.extend(_leakage_rows(candidate_id, matches))
        tcga = _is_tcga_candidate(candidate)
        candidate_samples = samples_by_candidate.get(candidate_id, []) or samples_by_candidate.get(cohort_id, [])
        n_resp = sum(1 for row in candidate_samples if row.get("response_label") == "responder")
        n_non = sum(1 for row in candidate_samples if row.get("response_label") == "non_responder")
        n_total = sum(1 for row in candidate_samples if parse_bool(row.get("include_flag", "true"), default=True))

        ici_status = "confirmed" if _is_ici(candidate) else "missing_or_unclear"
        response_status = _status(candidate.get("response_label_status", ""))
        timing_status = _status(candidate.get("timing_label_status", ""))
        expression_status = _status(candidate.get("expression_data_status", ""))
        curation_status = candidate.get("curation_status", "").strip().lower()

        if tcga:
            eligibility_status = "excluded"
            eligibility_reason = "tcga_is_prognostic_projection_not_ici_response_validation"
            independence_status = "not_applicable_tcga"
            claim_class = "not_eligible"
        elif matches:
            eligibility_status = "excluded"
            eligibility_reason = "overlaps_derivation_evidence"
            independence_status = "overlap_detected"
            claim_class = "not_eligible"
        elif (
            ici_status != "confirmed"
            or response_status != "confirmed"
            or timing_status != "confirmed"
            or expression_status != "confirmed"
            or curation_status in {"needs_paper_curation", "uncurated", "pending"}
        ):
            eligibility_status = "needs_paper_curation"
            eligibility_reason = "missing_or_uncertain_required_metadata"
            independence_status = "no_overlap_detected"
            claim_class = "metadata_curation_needed"
        elif n_resp < 1 or n_non < 1:
            eligibility_status = "needs_paper_curation"
            eligibility_reason = "missing_response_arm_counts"
            independence_status = "no_overlap_detected"
            claim_class = "metadata_curation_needed"
        else:
            eligibility_status = "eligible"
            eligibility_reason = "passes_external_ici_validation_gates"
            independence_status = "no_overlap_detected"
            claim_class = "external_ici_validation" if n_resp >= 2 and n_non >= 2 else "underpowered_external_check"

        roster_rows.append(
            {
                "candidate_id": candidate_id,
                "cohort_id": cohort_id,
                "eligibility_status": eligibility_status,
                "eligibility_reason": eligibility_reason,
                "independence_status": independence_status,
                "ici_treatment_status": ici_status,
                "response_label_status": response_status,
                "timing_compatibility": timing_status,
                "expression_compatibility": expression_status,
                "n_samples_total": str(n_total),
                "n_responders": str(n_resp),
                "n_non_responders": str(n_non),
                "claim_class": claim_class,
                "curation_confidence": "high" if curation_status == "curated" else "needs_review",
            }
        )

    return roster_rows, leakage_rows


def build_membership(
    sample_rows: list[dict[str, str]],
    cohort_roster: list[dict[str, str]],
    signatures: list[dict[str, object]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    eligible = {
        row["candidate_id"]: row
        for row in cohort_roster
        if row.get("eligibility_status") == "eligible"
    }
    eligible.update(
        {
            row["cohort_id"]: row
            for row in cohort_roster
            if row.get("eligibility_status") == "eligible"
        }
    )
    normalized_samples: list[dict[str, str]] = []
    membership_rows: list[dict[str, str]] = []
    for sample in sample_rows:
        normalized = dict(sample)
        candidate_key = sample.get("candidate_id", "") or sample.get("cohort_id", "")
        cohort_key = sample.get("cohort_id", "")
        is_eligible_cohort = candidate_key in eligible or cohort_key in eligible
        include = parse_bool(sample.get("include_flag", "true"), default=True)
        if not is_eligible_cohort:
            normalized["include_flag"] = "false"
            normalized["exclude_reason"] = sample.get("exclude_reason", "") or "cohort_not_eligible"
        elif not include:
            normalized["include_flag"] = "false"
            normalized["exclude_reason"] = sample.get("exclude_reason", "") or "include_flag_false"
        else:
            normalized["include_flag"] = "true"
            normalized["exclude_reason"] = ""
        normalized_samples.append(normalized)

        if normalized["include_flag"] != "true":
            continue
        response = sample.get("response_label", "")
        timing = sample.get("timing_category", "")
        if response not in {"responder", "non_responder"}:
            continue
        for signature in signatures:
            analysis_id = str(signature["analysis_id"])
            required_timing = _required_timing_for_analysis(analysis_id)
            if required_timing and timing != required_timing:
                continue
            membership_rows.append(
                {
                    "analysis_id": analysis_id,
                    "external_sample_id": sample.get("external_sample_id", ""),
                    "cohort_id": sample.get("cohort_id", ""),
                    "arm": response,
                    "timing_category": timing,
                    "response_label": response,
                    "membership_status": "included",
                    "membership_reason": "eligible_independent_ici_sample",
                }
            )
    return normalized_samples, membership_rows


def score_external_samples(
    membership_rows: list[dict[str, str]],
    sample_rows: list[dict[str, str]],
    signatures: list[dict[str, object]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    sample_lookup = {row["external_sample_id"]: row for row in sample_rows}
    by_expr: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in membership_rows:
        sample = sample_lookup.get(row["external_sample_id"], {})
        expr_file = sample.get("expression_file", "")
        if expr_file:
            by_expr[(row["analysis_id"], expr_file)].append(row)

    signatures_by_id = {str(sig["analysis_id"]): sig for sig in signatures}
    score_rows: list[dict[str, str]] = []
    coverage_rows: list[dict[str, str]] = []
    seen_coverage: set[tuple[str, str, str]] = set()

    for (analysis_id, expr_file), members in sorted(by_expr.items()):
        signature = signatures_by_id[analysis_id]
        expr = load_expression_matrix(Path(expr_file))
        if expr is None or expr.empty:
            continue
        sample_ids = [row["external_sample_id"] for row in members if row["external_sample_id"] in expr.columns]
        if not sample_ids:
            continue
        expr = expr.loc[:, sample_ids].apply(pd.to_numeric, errors="coerce")
        genes: list[dict[str, str]] = signature["genes"]  # type: ignore[assignment]
        observed_genes = [gene for gene in genes if gene["gene_symbol"] in expr.index]
        z_by_gene: dict[str, pd.Series] = {}
        for gene in observed_genes:
            values = expr.loc[gene["gene_symbol"], sample_ids].astype(float)
            sd = float(values.std(ddof=0))
            if sd == 0 or math.isnan(sd):
                z_by_gene[gene["gene_symbol"]] = values * 0.0
            else:
                z_by_gene[gene["gene_symbol"]] = (values - float(values.mean())) / sd

        cohort_ids = sorted({row["cohort_id"] for row in members})
        for cohort_id in cohort_ids:
            for gene in genes:
                key = (analysis_id, cohort_id, gene["gene_symbol"])
                if key in seen_coverage:
                    continue
                seen_coverage.add(key)
                observed = gene["gene_symbol"] in z_by_gene
                coverage_rows.append(
                    {
                        "analysis_id": analysis_id,
                        "cohort_id": cohort_id,
                        "gene_symbol": gene["gene_symbol"],
                        "observed_status": "observed" if observed else "missing",
                        "mapping_source": "exact_symbol" if observed else "",
                        "missing_reason": "" if observed else "not_found_in_external_expression",
                    }
                )

        for member in members:
            sid = member["external_sample_id"]
            if sid not in sample_ids:
                continue
            values: list[float] = []
            for gene in observed_genes:
                direction = gene.get("signature_direction", "")
                weight = -1.0 if direction == "down" else 1.0
                values.append(weight * float(z_by_gene[gene["gene_symbol"]][sid]))
            score = mean(values) if values else float("nan")
            n_genes = len(genes)
            n_observed = len(observed_genes)
            coverage = n_observed / n_genes if n_genes else 0.0
            score_rows.append(
                {
                    "analysis_id": analysis_id,
                    "signature_version": str(signature["signature_version"]),
                    "signature_checksum": str(signature["checksum"]),
                    "external_sample_id": sid,
                    "cohort_id": member["cohort_id"],
                    "signature_score": _fmt(score),
                    "n_signature_genes": str(n_genes),
                    "n_genes_observed": str(n_observed),
                    "gene_coverage_fraction": _fmt(coverage),
                    "scoring_method": "direction_weighted_mean_zscore_no_refit",
                }
            )
    return score_rows, coverage_rows


def summarize_validation(
    score_rows: list[dict[str, str]],
    membership_rows: list[dict[str, str]],
    signatures: list[dict[str, object]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    response_lookup = {
        (row["analysis_id"], row["external_sample_id"]): row["response_label"]
        for row in membership_rows
    }
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in score_rows:
        grouped[(row["analysis_id"], row["cohort_id"])].append(row)

    by_cohort_rows: list[dict[str, str]] = []
    for (analysis_id, cohort_id), rows in sorted(grouped.items()):
        responder_scores = [
            float(row["signature_score"])
            for row in rows
            if response_lookup.get((analysis_id, row["external_sample_id"])) == "responder"
        ]
        non_scores = [
            float(row["signature_score"])
            for row in rows
            if response_lookup.get((analysis_id, row["external_sample_id"])) == "non_responder"
        ]
        stats = _effect_stats(responder_scores, non_scores)
        status, claim, caveat = _validation_labels(len(responder_scores), len(non_scores))
        by_cohort_rows.append(
            {
                "analysis_id": analysis_id,
                "cohort_id": cohort_id,
                "n_responders": str(len(responder_scores)),
                "n_non_responders": str(len(non_scores)),
                "effect_size": _fmt(stats["effect"]),
                "effect_ci_low": _fmt(stats["ci_low"]),
                "effect_ci_high": _fmt(stats["ci_high"]),
                "p_value": _fmt(stats["p_value"]),
                "auc": _fmt(_auc(responder_scores, non_scores)),
                "validation_status": status,
                "claim_class": claim,
                "caveat": caveat,
            }
        )

    summary_rows: list[dict[str, str]] = []
    signature_ids = [str(sig["analysis_id"]) for sig in signatures]
    for analysis_id in signature_ids:
        rows = [row for row in score_rows if row["analysis_id"] == analysis_id]
        responder_scores = [
            float(row["signature_score"])
            for row in rows
            if response_lookup.get((analysis_id, row["external_sample_id"])) == "responder"
        ]
        non_scores = [
            float(row["signature_score"])
            for row in rows
            if response_lookup.get((analysis_id, row["external_sample_id"])) == "non_responder"
        ]
        cohort_rows = [row for row in by_cohort_rows if row["analysis_id"] == analysis_id]
        stats = _effect_stats(responder_scores, non_scores)
        n_completed = sum(1 for row in cohort_rows if row["validation_status"] == "completed")
        if n_completed:
            status = "completed"
            claim = "external_ici_validation"
            interpretation = (
                "Frozen signature was evaluated in independent ICI-treated validation "
                "samples with both responder and non-responder arms."
            )
        elif responder_scores and non_scores:
            status = "underpowered"
            claim = "underpowered_external_check"
            interpretation = "External ICI-treated check exists but is underpowered."
        else:
            status = "missing"
            claim = "missing_no_eligible_independent_ici_cohort"
            interpretation = "No eligible independent ICI-treated validation cohort was scored."
        effects = [float(row["effect_size"]) for row in cohort_rows if row["effect_size"] != "nan"]
        direction_concordance = (
            sum(1 for effect in effects if effect > 0) / len(effects)
            if effects
            else float("nan")
        )
        summary_rows.append(
            {
                "analysis_id": analysis_id,
                "n_eligible_cohorts": str(len({row["cohort_id"] for row in cohort_rows})),
                "n_eligible_samples": str(len(rows)),
                "n_responders": str(len(responder_scores)),
                "n_non_responders": str(len(non_scores)),
                "pooled_effect_size": _fmt(stats["effect"]),
                "pooled_ci_low": _fmt(stats["ci_low"]),
                "pooled_ci_high": _fmt(stats["ci_high"]),
                "pooled_p_value": _fmt(stats["p_value"]),
                "direction_concordance": _fmt(direction_concordance),
                "validation_status": status,
                "claim_class": claim,
                "plain_language_interpretation": interpretation,
            }
        )
    return by_cohort_rows, summary_rows


def external_validation_claim_boundaries() -> list[dict[str, str]]:
    return [
        {
            "topic": "external_ici_validation",
            "required_label": "external_ici_validation",
            "disallowed_label": "TCGA_response_validation",
            "report_language": "Only independent ICI-treated response-labelled cohorts can validate ICI response signatures.",
        },
        {
            "topic": "frozen_signature_scoring",
            "required_label": "frozen_signature_no_refit",
            "disallowed_label": "validation_refit",
            "report_language": "External samples are scored using frozen Stage 08 genes without reselection or refitting.",
        },
        {
            "topic": "underpowered_external_check",
            "required_label": "underpowered_external_check",
            "disallowed_label": "validated_predictor",
            "report_language": "Underpowered external checks are retained but cannot support validated-predictor language.",
        },
    ]


def _load_signature(path: Path) -> dict[str, object]:
    rows = read_tsv(path)
    if not rows:
        raise ValueError(f"Signature file has no rows: {path}")
    genes: list[dict[str, str]] = []
    for row in rows:
        symbol = (row.get("gene_symbol", "") or row.get("gene_id", "")).strip()
        if not symbol:
            continue
        direction = (row.get("signature_direction", "") or "").strip().lower()
        if direction not in {"up", "down"}:
            effect = _safe_float(row.get("effect", "nan"))
            direction = "down" if effect < 0 else "up"
        genes.append({"gene_symbol": symbol, "signature_direction": direction})
    if not genes:
        raise ValueError(f"Signature file has no usable genes: {path}")
    analysis_id = rows[0].get("analysis_id", "") or path.parent.name or path.stem
    signature_version = rows[0].get("signature_version", "") or path.stem
    return {
        "path": path,
        "analysis_id": analysis_id,
        "signature_version": signature_version,
        "checksum": _sha256(path),
        "genes": genes,
    }


def _normalize_sample_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {field: row.get(field, "") for field in SAMPLE_MANIFEST_FIELDS}
    normalized["timing_category"] = _normalize_timing(normalized["timing_category"])
    normalized["response_label"] = _normalize_response(normalized["response_label"])
    if not normalized["external_sample_id"]:
        normalized["external_sample_id"] = row.get("sample_id", "")
    if not normalized["include_flag"]:
        normalized["include_flag"] = "true"
    return normalized


def _normalize_timing(value: str) -> str:
    norm = (value or "").strip().lower().replace("_", "-")
    if norm in {"pre", "baseline", "pretreatment", "pre-treatment"}:
        return "pre-treatment"
    if norm in {"on", "on-treatment", "during-treatment"}:
        return "on-treatment"
    if norm in {"post", "post-treatment", "after-treatment"}:
        return "post-treatment"
    return norm or "unknown"


def _normalize_response(value: str) -> str:
    norm = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if norm in {"r", "response", "responder", "responding", "cr", "pr"}:
        return "responder"
    if norm in {"nr", "non_responder", "nonresponse", "non_response", "sd", "pd"}:
        return "non_responder"
    return norm or "unknown"


def _status(value: str) -> str:
    norm = (value or "").strip().lower()
    if norm in {"available", "confirmed", "present", "yes", "true", "ok", "pass", "curated"}:
        return "confirmed"
    if norm in {"missing", "unknown", "unclear", "needs_paper_curation", "pending", ""}:
        return "missing"
    return norm


def _is_ici(candidate: dict[str, str]) -> bool:
    text = " ".join(
        [
            candidate.get("therapy_class", ""),
            candidate.get("therapy_agent_raw", ""),
            candidate.get("notes", ""),
        ]
    ).lower()
    return bool(
        re.search(
            r"\b(pd-?1|pd-?l1|ctla-?4|ici|checkpoint|nivolumab|pembrolizumab|ipilimumab|"
            r"atezolizumab|durvalumab|avelumab|cemiplimab)\b",
            text,
        )
    )


def _is_tcga_candidate(candidate: dict[str, str]) -> bool:
    text = " ".join(
        [
            candidate.get("candidate_id", ""),
            candidate.get("cohort_id", ""),
            candidate.get("accession", ""),
            candidate.get("candidate_source", ""),
        ]
    ).upper()
    return "TCGA" in text


def _build_derivation_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        for field in ("cohort_id", "publication_id", "sample_id", "patient_id"):
            value = (row.get(field, "") or "").strip()
            if value:
                index[f"{field}:{value.upper()}"] = row
        for token in split_accessions(
            " ".join([row.get("accession", ""), row.get("secondary_accessions", "")])
        ):
            index[f"accession:{token.upper()}"] = row
    return index


def _find_derivation_overlaps(
    candidate: dict[str, str],
    derivation_index: dict[str, dict[str, str]],
) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str]] = []
    for token in split_accessions(candidate.get("accession", "")):
        checks.append(("accession", token.upper()))
    for field in ("cohort_id", "publication_id"):
        value = (candidate.get(field, "") or "").strip()
        if value:
            checks.append((field, value.upper()))
    matches: list[tuple[str, str, str]] = []
    for check_type, value in checks:
        key = f"{check_type}:{value}"
        if key in derivation_index:
            matches.append((check_type, value, key))
    return matches


def _leakage_rows(candidate_id: str, matches: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    if not matches:
        return [
            {
                "candidate_id": candidate_id,
                "check_type": "derivation_overlap",
                "candidate_value": "",
                "matched_derivation_value": "",
                "leakage_status": "pass",
                "resolution": "no_overlap_detected",
            }
        ]
    return [
        {
            "candidate_id": candidate_id,
            "check_type": check_type,
            "candidate_value": value,
            "matched_derivation_value": key,
            "leakage_status": "fail_overlap",
            "resolution": "exclude_from_external_validation",
        }
        for check_type, value, key in matches
    ]


def _required_timing_for_analysis(analysis_id: str) -> str:
    if "ON_TREATMENT" in analysis_id or analysis_id == "ON_RESPONSE":
        return "on-treatment"
    if "POST_TREATMENT" in analysis_id or analysis_id == "POST_RESPONSE":
        return "post-treatment"
    if "PRE_TREATMENT" in analysis_id or analysis_id in {"PRE_RESPONSE", "PAN_ICB_RESPONSE"}:
        return "pre-treatment"
    return ""


def _effect_stats(case: list[float], control: list[float]) -> dict[str, float]:
    if not case or not control:
        return {"effect": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "p_value": float("nan")}
    effect = mean(case) - mean(control)
    se = _se_diff(case, control)
    ci_low = effect - 1.96 * se if not math.isnan(se) else float("nan")
    ci_high = effect + 1.96 * se if not math.isnan(se) else float("nan")
    p_value = _welch_p_value(case, control)
    return {"effect": effect, "ci_low": ci_low, "ci_high": ci_high, "p_value": p_value}


def _se_diff(case: list[float], control: list[float]) -> float:
    if len(case) < 2 or len(control) < 2:
        return float("nan")
    var_case = sum((x - mean(case)) ** 2 for x in case) / (len(case) - 1)
    var_control = sum((x - mean(control)) ** 2 for x in control) / (len(control) - 1)
    return math.sqrt(var_case / len(case) + var_control / len(control))


def _welch_p_value(case: list[float], control: list[float]) -> float:
    if len(case) < 2 or len(control) < 2:
        return float("nan")
    try:
        from scipy.stats import ttest_ind

        _, p_value = ttest_ind(case, control, equal_var=False, nan_policy="omit")
        return float(p_value)
    except Exception:
        return float("nan")


def _auc(case: list[float], control: list[float]) -> float:
    if not case or not control:
        return float("nan")
    wins = 0.0
    total = len(case) * len(control)
    for c in case:
        for n in control:
            if c > n:
                wins += 1.0
            elif c == n:
                wins += 0.5
    return wins / total


def _validation_labels(n_resp: int, n_non: int) -> tuple[str, str, str]:
    if n_resp >= 2 and n_non >= 2:
        return "completed", "external_ici_validation", "Eligible independent ICI-treated cohort."
    if n_resp >= 1 and n_non >= 1:
        return "underpowered", "underpowered_external_check", "Both arms present but sample size is below primary gate."
    return "not_validated", "not_eligible", "Missing responder or non-responder arm."


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _fmt(value: float) -> str:
    if value is None or math.isnan(value):
        return "nan"
    return f"{value:.6g}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
