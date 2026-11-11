"""Descriptive post-meta fgsea wiring with an explicit ranking contract."""
from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping, Sequence

from .paths import (
    preflight_tree,
    reject_symlink_components,
    validate_contained_path,
    write_immutable_bytes,
)


@dataclass(frozen=True)
class MetaRankingContract:
    contract_id: str
    statistic: str

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", str(self.contract_id or "")):
            raise ValueError("An explicit meta-ranking contract ID is required")
        if self.statistic not in {"estimate", "estimate_over_se"}:
            raise ValueError("Meta-ranking statistic is not supported by this invented-contract runner")


def build_meta_ranking(
    summaries: Sequence[Mapping],
    mapping_by_unit: Mapping[str, Mapping],
    *,
    endpoint_family: str,
    endpoint_definition_id: str,
    contract: MetaRankingContract,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Build a deterministic symbol ranking only after an explicit contract is given."""
    if not isinstance(contract, MetaRankingContract):
        raise ValueError("An explicit meta-ranking contract object is required")
    ranking = []
    unmapped = 0
    excluded_status = 0
    excluded_missing_statistic = 0
    for row in summaries:
        if (
            str(row.get("unit_family", "")) != "gene"
            or str(row.get("endpoint_family", "")) != endpoint_family
            or str(row.get("endpoint_definition_id", "")) != endpoint_definition_id
        ):
            continue
        if str(row.get("status", "")) != "pooled":
            excluded_status += 1
            continue
        unit = str(row.get("unit", ""))
        mapping = mapping_by_unit.get(unit, {})
        if not isinstance(mapping, Mapping) or mapping.get("status") != "mapped":
            unmapped += 1
            continue
        try:
            estimate = float(row.get("estimate", ""))
            if contract.statistic == "estimate":
                statistic = estimate
            else:
                standard_error = float(row.get("se", ""))
                if standard_error <= 0:
                    raise ValueError
                statistic = estimate / standard_error
        except (TypeError, ValueError, OverflowError):
            excluded_missing_statistic += 1
            continue
        if not math.isfinite(statistic):
            excluded_missing_statistic += 1
            continue
        ranking.append({"gene": unit, "statistic": statistic})
    ranking.sort(key=lambda row: str(row["gene"]))
    genes = [str(row["gene"]) for row in ranking]
    if len(genes) != len(set(genes)):
        raise ValueError("Meta-ranking contains duplicate symbol identifiers")
    return ranking, {
        "ranking_contract_id": contract.contract_id,
        "ranking_statistic": contract.statistic,
        "ranked_gene_count": len(ranking),
        "unmapped_gene_count": unmapped,
        "excluded_status_count": excluded_status,
        "excluded_missing_statistic_count": excluded_missing_statistic,
    }


def run_meta_fgsea(
    dataset,
    summaries: Sequence[Mapping],
    mapping_by_unit: Mapping[str, Mapping],
    *,
    endpoint_family: str,
    endpoint_definition_id: str,
    stratum: str,
    contract: MetaRankingContract | None,
    results: Path | str,
    context_id: str = "all",
    retention_dir: Path | str | None = None,
    runner=None,
) -> dict[str, object]:
    """Execute the existing A-BULK fgsea API for an invented explicit ranking."""
    from tools.a_bulk.core import _validate_view_identifiers

    classification = str(getattr(dataset, "data_classification", ""))
    if classification not in {"real", "synthetic"}:
        raise ValueError("Meta-enrichment input needs a supported data classification")
    _validate_view_identifiers(
        dataset,
        data_classification=classification,
        reject_synthetic_spoof=True,
    )
    for value, label in (
        (getattr(dataset, "expression_path", None), "Meta-enrichment expression input"),
        (getattr(dataset, "clinical_path", None), "Meta-enrichment clinical input"),
    ):
        if value is not None:
            reject_symlink_components(value, label=label)
    result_root = preflight_tree(results, label="Meta-enrichment result")
    if retention_dir is not None:
        preflight_tree(retention_dir, label="Meta-enrichment private work")
    if classification != "synthetic":
        return {"status": "unavailable", "reason": "pending_meta_ranking_statistic_decision"}
    if contract is None:
        return {"status": "unavailable", "reason": "pending_meta_ranking_statistic_decision"}
    from tools.a_bulk.core import analyse
    from tools.a_meta.frozen import HALLMARK_GMT, REACTOME_GMT

    ranking, report = build_meta_ranking(
        summaries,
        mapping_by_unit,
        endpoint_family=endpoint_family,
        endpoint_definition_id=endpoint_definition_id,
        contract=contract,
    )
    if len(ranking) < 2:
        return {
            "status": "unavailable",
            "reason": "no_eligible_pooled_gene_rows",
            **report,
        }
    mapping_path = result_root / "symbol_mapping.tsv"
    mapping_units = sorted({
        str(row.get("unit", "")) for row in summaries
        if str(row.get("unit_family", "")) == "gene"
        and str(row.get("endpoint_family", "")) == endpoint_family
        and str(row.get("endpoint_definition_id", "")) == endpoint_definition_id
        and row.get("unit")
    })
    mapping_rows = []
    for unit in mapping_units:
        mapping = mapping_by_unit.get(unit, {})
        source_mappings = mapping.get("source_mappings", ()) if isinstance(mapping, Mapping) else ()
        if source_mappings:
            for source in sorted(
                source_mappings,
                key=lambda item: (
                    str(item.get("cohort_id", "")),
                    str(item.get("source_feature_id", "")),
                    str(item.get("method", "")),
                ),
            ):
                mapping_rows.append({
                    "unit": unit,
                    "cohort_id": str(source.get("cohort_id", "")),
                    "source_feature_id": str(source.get("source_feature_id", "")),
                    "mapping_status": str(source.get("status", "unmapped")),
                    "mapping_method": str(source.get("method", "")),
                })
        else:
            mapping_rows.append({
                "unit": unit,
                "cohort_id": "",
                "source_feature_id": str(mapping.get("source_feature_id", "")) if isinstance(mapping, Mapping) else "",
                "mapping_status": str(mapping.get("status", "unmapped")) if isinstance(mapping, Mapping) else "unmapped",
                "mapping_method": str(mapping.get("method", "")) if isinstance(mapping, Mapping) else "",
            })
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("unit", "cohort_id", "source_feature_id", "mapping_status", "mapping_method"),
            delimiter="\t", lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(mapping_rows)
        mapping_content = stream.getvalue().encode("utf-8")
    write_immutable_bytes(
        result_root,
        mapping_path,
        mapping_content,
        label="Meta-ranking mapping output",
    )
    ranking_path = result_root / "ranking.tsv"
    validate_contained_path(result_root, ranking_path, label="Meta-ranking output")
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=("gene", "statistic"), delimiter="\t", lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(ranking)
        ranking_content = stream.getvalue().encode("utf-8")
    write_immutable_bytes(result_root, ranking_path, ranking_content, label="Meta-ranking output")

    context_digest = hashlib.sha256(
        f"{stratum}|{context_id}|{endpoint_family}|{endpoint_definition_id}".encode("utf-8")
    ).hexdigest()[:12]
    meta_id = f"meta_{stratum}_{endpoint_family}_{context_digest}"
    metadata = SimpleNamespace(
        cohort_id=meta_id,
        cancer="multi" if stratum == "across_cancers" else getattr(dataset.metadata, "cancer", "multi"),
        representation=SimpleNamespace(
            platform="meta_analysis", unit="hedges_g", transform="other", feature_id="symbol",
        ),
        de_engine="limma",
        endpoint_families=(endpoint_family,),
    )
    meta_dataset = replace(
        dataset,
        dataset_id=meta_id,
        metadata=metadata,
        expression_path=ranking_path,
        clinical_rows=(),
        clinical_path=None,
        sample_id_field="patient_id",
        data_classification="synthetic",
        endpoint_definition_id=endpoint_definition_id,
    )

    outputs = {}
    for collection, gene_sets in (("hallmark", HALLMARK_GMT), ("reactome", REACTOME_GMT)):
        summary = analyse(
            meta_dataset,
            "gsea",
            paper="A",
            endpoint=endpoint_family,
            results=result_root / collection,
            gene_sets=gene_sets,
            gene_set_id_type="symbol",
            ranking_path=ranking_path,
            ranking_id_type="symbol",
            ranking_contract_id=contract.contract_id,
            allow_outcomes=False,
            retention_dir=retention_dir,
            runner=runner,
        )
        outputs[collection] = {
            "status": "complete",
            "completed_stages": summary.get("completed_stages", []),
        }
    return {
        "status": "complete",
        "reason": "",
        "stratum": stratum,
        "endpoint_family": endpoint_family,
        "endpoint_definition_id": endpoint_definition_id,
        "context_id": context_id,
        **report,
        "symbol_mapping_sha256": hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
        "collections": outputs,
    }
