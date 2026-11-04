"""Run one cohort at a time through the pinned R analysis scripts."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Literal, Mapping, Sequence

from tools import a_scoring
from tools.a_cohorts import core as cohort_core
from tools.a_scoring.core import panel_definitions
from tools.r_bridge import RResult, run_r

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT.parent / "results"
PANEL_IDS = (
    "P_ANTIGEN_PRESENTATION",
    "AYERS_GEP_18",
    "HOPE_18",
    "APM_WANG_18",
    "M0_EXTRA_ANTIGEN_PRESENTATION",
    "M1_MOBILITY",
    "M2_CYTOTOXICITY",
    "M3_VIRAL_MIMICRY",
    "M4_EXCLUSION",
    "M5_CHECKPOINT_CANDIDATES",
    "M6_EPIGENETIC_REGULATORS",
)
SCORE_NAMES = (*PANEL_IDS, "CYT")
OUTCOME_STAGES = frozenset({"de", "gsea", "all"})
_MISSING = {"", "NA", "N/A", "UNKNOWN", "NULL"}
_COVARIATE_FIELDS = {
    "batch": ("batch", "batch_id", "processing_batch", "seq_batch"),
    "biopsy_site": ("biopsy_site", "site", "tissue_site", "specimen_site"),
    "drug_class": ("drug_class_normalised", "drug_class", "treatment_class"),
}
@dataclass(frozen=True)
class BulkDataset:
    """Cohort-view-like input contract used by Papers A and B."""

    paper: Literal["A", "B"]
    dataset_id: str
    metadata: Any
    expression_path: Path
    clinical_rows: Sequence[Mapping[str, Any]]
    clinical_path: Path | None = None
    gene_lengths: Mapping[str, float] | Sequence[float] | None = None
    sample_id_field: str = "patient_id"
    data_classification: Literal["real", "synthetic"] = "real"

    @property
    def representation(self):
        return self.metadata.representation

    @property
    def de_engine(self) -> str:
        return str(self.metadata.de_engine)

    @property
    def endpoint_families(self) -> tuple[str, ...]:
        return tuple(self.metadata.endpoint_families)


class OutcomeGuardError(ValueError):
    """Raised before response labels or response-associated results are read."""


def adapt_view(
    view: Any,
    *,
    paper: Literal["A", "B"] = "A",
    data_classification: Literal["real", "synthetic"] = "real",
    sample_id_field: str = "patient_id",
) -> BulkDataset:
    """Adapt a cohort-view-like object without tying the module to Paper A's loader."""
    _validate_view_identifiers(view)
    if isinstance(view, BulkDataset):
        if view.paper != paper:
            raise ValueError("Dataset paper does not match the requested paper")
        _validate_dataset(view)
        return view
    metadata = getattr(view, "metadata", None)
    expression_path = getattr(view, "expression_path", None)
    clinical_rows = getattr(view, "clinical_rows", None)
    if metadata is None or expression_path is None or clinical_rows is None:
        raise TypeError("Bulk analysis needs metadata, expression_path, and clinical_rows")
    dataset_id = getattr(metadata, "cohort_id", None)
    if not dataset_id:
        dataset_id = getattr(view, "dataset_id", None)
    if not dataset_id:
        raise ValueError("Bulk analysis input must declare a dataset identifier")
    expression_path = Path(expression_path)
    clinical_path = getattr(view, "clinical_path", None)
    if clinical_path is None:
        candidate = expression_path.with_name("clinical.tsv")
        clinical_path = candidate if candidate.is_file() else None
    dataset = BulkDataset(
        paper=paper,
        dataset_id=str(dataset_id),
        metadata=metadata,
        expression_path=expression_path,
        clinical_rows=clinical_rows,
        clinical_path=Path(clinical_path) if clinical_path is not None else None,
        gene_lengths=getattr(view, "gene_lengths", getattr(metadata, "gene_lengths", None)),
        sample_id_field=sample_id_field,
        data_classification=data_classification,
    )
    _validate_dataset(dataset)
    return dataset


def results_root(results: Path | str | None = None) -> Path:
    selected = results or os.environ.get("THESIS_RESULTS") or DEFAULT_RESULTS
    return Path(selected).expanduser().resolve()


def output_dir(dataset: BulkDataset, results: Path | str | None = None) -> Path:
    _validate_view_identifiers(dataset)
    if dataset.paper not in {"A", "B"}:
        raise ValueError("Paper must be A or B")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", dataset.dataset_id):
        raise ValueError("Invalid dataset identifier")
    return results_root(results) / dataset.paper / dataset.dataset_id


def select_de_engine(representation: Any, declared_engine: str | None = None) -> str:
    """Select DESeq2 only for linear integer-count representations."""
    unit = str(getattr(representation, "unit", "")).casefold()
    platform = str(getattr(representation, "platform", "")).casefold()
    transform = str(getattr(representation, "transform", "")).casefold()
    expected = "deseq2" if unit == "counts" else "limma"
    if expected == "deseq2" and transform != "linear":
        raise ValueError("DESeq2 requires an untransformed count representation")
    if declared_engine is not None and declared_engine != expected:
        raise ValueError("Declared DE engine does not match the measurement representation")
    return expected


def analyse(
    view: Any,
    action: Literal["qc", "pca", "de", "gsea", "panels", "all"],
    *,
    paper: Literal["A", "B"] = "A",
    endpoint: str = "orr",
    results: Path | str | None = None,
    gene_sets: Path | str | None = None,
    gene_set_id_type: str | None = None,
    min_gene_set_overlap: int = 10,
    allow_outcomes: bool = False,
    runner=None,
    sample_id_field: str = "patient_id",
) -> dict[str, Any]:
    """Execute one requested stage and update the patient-free dataset summary."""
    _validate_view_identifiers(view)
    dataset = adapt_view(view, paper=paper, sample_id_field=sample_id_field)
    if action not in {"qc", "pca", "de", "gsea", "panels", "all"}:
        raise ValueError(f"Unknown bulk analysis stage: {action}")
    needs_outcomes = action in OUTCOME_STAGES
    if action == "pca" and allow_outcomes:
        needs_outcomes = True
    if needs_outcomes:
        _guard_outcomes(dataset, allow_outcomes)
    if action in {"de", "all", "gsea"} and endpoint not in dataset.endpoint_families:
        raise ValueError("The requested endpoint family is not declared for this dataset")
    if action == "pca" and allow_outcomes and endpoint not in dataset.endpoint_families:
        raise ValueError("The requested endpoint family is not declared for this dataset")
    if action in {"gsea", "all"}:
        if gene_sets is None:
            raise ValueError("gsea requires --gene-sets with a local GMT file")
        ranking_id_type = str(getattr(dataset.representation, "feature_id", "")).casefold()
        gene_set_id_type = str(gene_set_id_type or "").casefold()
        if not gene_set_id_type:
            raise ValueError("gsea requires an explicit --gene-set-id-type")
        if gene_set_id_type != ranking_id_type:
            raise ValueError("Ranking and GMT identifier types must match; no mapping is configured")
        if not isinstance(min_gene_set_overlap, int) or min_gene_set_overlap < 1:
            raise ValueError("Minimum GMT/ranking membership overlap must be a positive integer")
        gene_set_path = Path(gene_sets).expanduser().resolve(strict=True)
        if not gene_set_path.is_file():
            raise ValueError("Gene-set input must be a local file")
    else:
        gene_set_path = None

    root = output_dir(dataset, results)
    root.mkdir(parents=True, exist_ok=True)
    stage_summaries: dict[str, Any] = {}
    if action in {"qc", "all"}:
        stage_summaries["qc"] = _run_qc(dataset, root, runner)
    if action in {"pca", "all"}:
        stage_summaries["pca"] = _run_pca(
            dataset, root, allow_outcomes=allow_outcomes, endpoint=endpoint, runner=runner
        )
    if action in {"de", "all"}:
        stage_summaries["de"] = _run_de(
            dataset, root, endpoint=endpoint, allow_outcomes=allow_outcomes, runner=runner
        )
    if action in {"gsea", "all"}:
        if action == "gsea":
            stage_summaries["de"] = _run_de(
                dataset, root, endpoint=endpoint, allow_outcomes=allow_outcomes, runner=runner
            )
        stage_summaries["gsea"] = _run_gsea(
            dataset, root, gene_set_path, endpoint=endpoint,
            gene_set_id_type=gene_set_id_type,
            min_gene_set_overlap=min_gene_set_overlap,
            runner=runner,
        )
    if action in {"panels", "all"}:
        stage_summaries["scores"] = _run_panels(dataset, root, runner)

    summary = _write_patient_free_summary(
        dataset,
        root,
        fresh_stage_summaries=stage_summaries,
        allow_outcomes=allow_outcomes or action in OUTCOME_STAGES,
    )
    summary["completed_stages"] = sorted(stage_summaries)
    _write_json(root / "summary.json", summary)
    return summary


def _guard_outcomes(dataset: BulkDataset, allow_outcomes: bool) -> None:
    if dataset.data_classification == "real" and not allow_outcomes:
        raise OutcomeGuardError(
            "Outcome analysis on a real cohort requires --allow-outcomes; no outcome labels were read"
        )


def validate_dataset_identifiers(*identifiers: Any) -> None:
    """Reject protected and excluded cohort identifiers before loading cohort files."""
    normalized_ids = []
    for value in identifiers:
        if value is None:
            continue
        identifier = str(value).strip()
        if not identifier:
            continue
        normalized = re.sub(r"[^a-z0-9]", "", identifier.casefold())
        if "imvigor210" in normalized or any(
            marker in normalized
            for marker in ("finaltest", "excluded", "combination", "dropped", "candidate", "parked", "onhold")
        ):
            raise ValueError("Dataset identifier is protected or excluded")
        normalized_ids.append((identifier, normalized))

    if not normalized_ids:
        return
    registry = cohort_core.registry()
    roles = {str(key).casefold(): value.get("role", "") for key, value in registry.items()}
    for identifier, normalized in normalized_ids:
        row = roles.get(identifier.casefold())
        if row is None:
            row = next((role for key, role in roles.items()
                        if re.sub(r"[^a-z0-9]", "", key) == normalized), None)
        role = str(row or "").casefold()
        if any(
            marker in role
            for marker in ("final test", "excluded", "combination", "dropped", "candidate", "parked", "on hold")
        ):
            raise ValueError("Dataset identifier is protected or excluded")


def _validate_view_identifiers(view: Any) -> None:
    metadata = getattr(view, "metadata", None)
    validate_dataset_identifiers(
        getattr(view, "dataset_id", None),
        getattr(metadata, "cohort_id", None) if metadata is not None else None,
    )


def _validate_dataset(dataset: BulkDataset) -> None:
    _validate_view_identifiers(dataset)
    if dataset.paper not in {"A", "B"}:
        raise ValueError("Paper must be A or B")
    if dataset.data_classification not in {"real", "synthetic"}:
        raise ValueError("Data classification must be real or synthetic")
    if not dataset.expression_path.is_file():
        raise FileNotFoundError("Expression matrix is not available")
    if not dataset.sample_id_field:
        raise ValueError("Sample identity field must be declared")
    select_de_engine(dataset.representation, dataset.de_engine)


def _matrix_header(dataset: BulkDataset) -> tuple[str, ...]:
    with dataset.expression_path.open("r", encoding="utf-8", newline="") as stream:
        header = next(csv.reader(stream, delimiter="\t"), None)
    if not header or len(header) < 4:
        raise ValueError("Expression matrix must contain a feature column and at least three samples")
    sample_ids = tuple(header[1:])
    if len(set(sample_ids)) != len(sample_ids) or any(not value for value in sample_ids):
        raise ValueError("Expression matrix sample columns must be unique and non-empty")
    return sample_ids


def _sample_metadata_content(
    dataset: BulkDataset,
    *,
    include_response: bool = False,
    endpoint: str = "orr",
    drop_excluded: bool = False,
) -> tuple[str, dict[str, Any]]:
    sample_ids = _matrix_header(dataset)
    clinical = {}
    for row in dataset.clinical_rows:
        sample_id = str(row.get(dataset.sample_id_field, ""))
        if not sample_id or sample_id in clinical:
            raise ValueError("Clinical rows need unique sample identities")
        clinical[sample_id] = row
    missing = [sample_id for sample_id in sample_ids if sample_id not in clinical]
    if missing:
        raise ValueError("Expression columns do not all have a matching clinical row")

    response_by_id: dict[str, str] = {}
    excluded: dict[str, int] = {}
    if include_response:
        labels, excluded = a_scoring.endpoint_label(dataset, endpoint)
        if len(labels) != len(dataset.clinical_rows):
            raise ValueError("Endpoint labels do not align to the clinical rows")
        response_by_id = {
            str(row[dataset.sample_id_field]): "R" if label == 1 else "NR" if label == 0 else ""
            for row, label in zip(dataset.clinical_rows, labels)
        }

    covariates: dict[str, dict[str, str]] = {}
    for name, fields in _COVARIATE_FIELDS.items():
        field = next((candidate for candidate in fields
                      if any(str(row.get(candidate, "")).strip() not in _MISSING for row in dataset.clinical_rows)), None)
        if field is not None:
            covariates[name] = {
                sample_id: _normalise_missing(clinical[sample_id].get(field, ""))
                for sample_id in sample_ids
            }
    platform = str(getattr(dataset.representation, "platform", "unknown"))

    fieldnames = ["sample_id", "platform"]
    if "batch" in covariates:
        fieldnames.append("batch")
    if "biopsy_site" in covariates:
        fieldnames.append("biopsy_site")
    if "drug_class" in covariates:
        fieldnames.append("drug_class")
    if include_response:
        fieldnames.append("response")
    rows = []
    for sample_id in sample_ids:
        response = response_by_id.get(sample_id, "") if include_response else ""
        if drop_excluded and not response:
            continue
        item = {"sample_id": sample_id, "platform": platform}
        for name in fieldnames[2:]:
            if name == "response":
                item[name] = response
            else:
                item[name] = covariates[name].get(sample_id, "")
        rows.append(item)
    values = {name: [row.get(name, "") for row in rows] for name in fieldnames}
    batch_values = {value for value in values.get("batch", []) if value not in _MISSING}
    config = {
        "covariates": [name for name in ("batch", "platform", "biopsy_site", "drug_class", "response")
                       if name in values and any(value not in _MISSING for value in values[name])],
        "include_batch": len(batch_values) > 1,
        "excluded_reason_counts": excluded,
        "input_sample_count": len(sample_ids),
        "analysis_sample_count": len(rows),
    }
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue(), config


def _normalise_missing(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.upper() in _MISSING else text


def _metadata_input(dataset: BulkDataset, root: Path, stage: str, *,
                    include_response: bool = False, endpoint: str = "orr", drop_excluded: bool = False):
    temp_root = root / "inputs"
    temp_root.mkdir(exist_ok=True)
    content, config = _sample_metadata_content(
        dataset, include_response=include_response,
        endpoint=endpoint, drop_excluded=drop_excluded,
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    final_path = temp_root / f"{stage}-{digest}.tsv"
    if final_path.exists():
        if _sha256(final_path) != digest:
            raise ValueError("Hash-addressed analysis input failed integrity validation")
    else:
        final_path.write_text(content, encoding="utf-8")
    return final_path, config


def _run_qc(dataset: BulkDataset, root: Path, runner=None) -> dict[str, Any]:
    stage = root / "qc"
    metadata_path, metadata_config = _metadata_input(dataset, root, "qc")
    expected = ["qc.tsv", "correlation_summary.tsv", "qc_summary.json"]
    config = _base_config(dataset, "qc", metadata_config, expected)
    config["top_variance_genes"] = 2000
    result = _call_r(
        dataset, stage, "bulk_qc_pca.R",
        {"expression": dataset.expression_path, "sample_metadata": metadata_path},
        config,
        expected, runner,
    )
    return _read_json(result.outputs["qc_summary.json"])


def _run_pca(dataset: BulkDataset, root: Path, *, allow_outcomes: bool, endpoint: str, runner=None) -> dict[str, Any]:
    stage = root / "pca"
    include_response = bool(allow_outcomes)
    metadata_path, metadata_config = _metadata_input(
        dataset, root, "pca", include_response=include_response, endpoint=endpoint,
    )
    covariates = [name for name in metadata_config["covariates"]
                  if name in {"batch", "platform", "biopsy_site", "drug_class"}
                  or (name == "response" and include_response)]
    outputs = ["pca.tsv", "variance_explained.tsv", "pca_summary.json"]
    outputs.extend(f"pca_{name}.png" for name in covariates)
    config = _base_config(dataset, "pca", metadata_config, outputs)
    config["top_variance_genes"] = 2000
    config["plot_covariates"] = covariates
    config["response_coloring_allowed"] = include_response
    config["endpoint"] = endpoint if include_response else None
    result = _call_r(
        dataset, stage, "bulk_qc_pca.R",
        {"expression": dataset.expression_path, "sample_metadata": metadata_path},
        config, outputs, runner,
        endpoint=endpoint if include_response else None,
    )
    return _read_json(result.outputs["pca_summary.json"])


def _run_de(dataset: BulkDataset, root: Path, *, endpoint: str, allow_outcomes: bool, runner=None) -> dict[str, Any]:
    _guard_outcomes(dataset, allow_outcomes=allow_outcomes or dataset.data_classification == "synthetic")
    engine = select_de_engine(dataset.representation, dataset.de_engine)
    stage = root / "de"
    metadata_path, metadata_config = _metadata_input(
        dataset, root, "de", include_response=True, endpoint=endpoint, drop_excluded=True,
    )
    included = _read_metadata(metadata_path)
    groups = {str(row.get("response", "")) for row in included}
    if groups != {"R", "NR"}:
        raise ValueError("DE requires at least one eligible responder and non-responder")
    script = "de_deseq2.R" if engine == "deseq2" else "de_limma.R"
    expected = ["de.tsv", "de_summary.json", "volcano.png"]
    config = _base_config(dataset, "de", metadata_config, expected)
    config.update({
        "engine": engine,
        "endpoint": endpoint,
        "include_batch": metadata_config["include_batch"],
        "representation": _representation_config(dataset),
    })
    result = _call_r(
        dataset, stage, script,
        {"expression": dataset.expression_path, "sample_metadata": metadata_path},
        config, expected, runner,
        endpoint=endpoint,
    )
    return _read_json(result.outputs["de_summary.json"])


def _run_gsea(
    dataset: BulkDataset,
    root: Path,
    gene_sets: Path,
    *,
    endpoint: str,
    gene_set_id_type: str,
    min_gene_set_overlap: int,
    runner=None,
) -> dict[str, Any]:
    stage = root / "gsea"
    de_path = root / "de" / "bridge" / "de.tsv"
    de_manifest = root / "de" / "manifest.json"
    if not de_path.is_file() or not de_manifest.is_file():
        raise FileNotFoundError("GSEA requires DE output for the same dataset and endpoint")
    de_metadata = _read_json(de_manifest)
    if de_metadata.get("endpoint") != endpoint:
        raise ValueError("GSEA endpoint does not match the existing DE ranking")
    expected = ["fgsea.tsv", "membership_overlap.tsv", "gsea_summary.json"]
    config = _base_config(dataset, "gsea", {}, expected)
    config["endpoint"] = endpoint
    config["ranking_id_type"] = str(getattr(dataset.representation, "feature_id", "")).casefold()
    config["gene_set_id_type"] = gene_set_id_type
    config["min_gene_set_overlap"] = min_gene_set_overlap
    config["min_size"] = 1
    config["max_size"] = 5000
    result = _call_r(
        dataset, stage, "fgsea_rank.R",
        {"ranking": de_path, "gene_sets": gene_sets}, config, expected,
        runner, endpoint=endpoint, extra_inputs=[de_manifest],
    )
    return _read_json(result.outputs["gsea_summary.json"])


def _run_panels(dataset: BulkDataset, root: Path, runner=None) -> dict[str, Any]:
    stage = root / "scores"
    score_table = stage / "panel_scores.tsv"
    coverage_table = stage / "panel_coverage.tsv"
    feature_ids, sample_ids, raw_matrix = _read_expression_matrix(dataset.expression_path)
    resolved, coverage = _resolve_panel_features(dataset, feature_ids)
    transformed, linear_tpm, transform_name = _panel_analysis_scale(
        raw_matrix, feature_ids, dataset
    )
    feature_index = {feature: index for index, feature in enumerate(feature_ids)}
    score_rows = []
    panel_defs = panel_definitions(PANEL_IDS)
    cyt_available = linear_tpm is not None and {"GZMA", "PRF1"}.issubset(resolved)
    for column, sample_id in enumerate(sample_ids):
        expression = {
            target: transformed[feature_index[source]][column]
            for target, source in resolved.items()
        }
        scores, _ = a_scoring.panel_scores(expression, panel_defs, require_complete=True)
        if cyt_available:
            gzma_index = feature_index[resolved["GZMA"]]
            prf1_index = feature_index[resolved["PRF1"]]
            try:
                cyt_score = a_scoring.cyt(
                    linear_tpm[gzma_index][column], linear_tpm[prf1_index][column]
                )
            except (OverflowError, ValueError):
                cyt_score = None
        else:
            cyt_score = None
        record = {"sample_id": sample_id}
        record.update({name: _format_number(scores.get(name)) for name in PANEL_IDS})
        record["CYT"] = _format_number(cyt_score)
        score_rows.append(record)
    _write_tsv_immutable(stage / "panel_scores.tsv", ["sample_id", *SCORE_NAMES], score_rows)
    coverage_rows = [
        {"gene": target, "present": int(target in resolved),
         "resolution": coverage[target].get("resolution", "missing"),
         "source_feature": coverage[target].get("source_symbol") or ""}
        for target in sorted({gene for genes in panel_defs.values() for gene in genes} | {"GZMA", "PRF1"})
    ]
    _write_tsv_immutable(coverage_table, ["gene", "present", "resolution", "source_feature"], coverage_rows)

    expected = ["correlation.tsv", "correlation_heatmap.png", "scores_summary.json"]
    config = {
        "mode": "panels",
        "expected_outputs": expected,
        "score_names": list(SCORE_NAMES),
    }
    result = run_r(
        ROOT / "r/scripts/bulk_qc_pca.R",
        {"scores": stage / "panel_scores.tsv"}, config,
        stage / "bridge", runner=runner,
    )
    r_summary = _read_json(result.outputs["scores_summary.json"])
    present_samples = sum(1 for row in score_rows if any(_number(row.get(name)) is not None for name in SCORE_NAMES))
    summary = {
        **r_summary,
        "panel_count": len(PANEL_IDS),
        "score_count": len(SCORE_NAMES),
        "samples_with_any_score": present_samples,
        "analysis_transform": transform_name,
        "cyt_available": cyt_available,
        "cyt_unavailable_reason": None if cyt_available else (
            "verified linear TPM is unavailable"
            if linear_tpm is None else "GZMA or PRF1 is absent"
        ),
        "genes_resolved": sum(row["present"] for row in coverage_rows),
        "genes_requested": len(coverage_rows),
    }
    _write_immutable_json(stage / "summary.json", summary)
    _write_module_manifest(
        dataset, stage, "panels",
        [dataset.expression_path, stage / "panel_scores.tsv", coverage_table],
        run_r=result, runner_script="bulk_qc_pca.R", endpoint=None,
        extra_outputs=[stage / "panel_scores.tsv", coverage_table, stage / "summary.json"],
    )
    return summary


def _resolve_panel_features(
    dataset: BulkDataset, feature_ids: Sequence[str]
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    panel_defs = panel_definitions(PANEL_IDS)
    targets = tuple(dict.fromkeys(gene for genes in panel_defs.values() for gene in genes))
    targets = tuple(dict.fromkeys((*targets, "GZMA", "PRF1")))
    feature_id_type = str(getattr(dataset.representation, "feature_id", "symbol"))
    if feature_id_type == "entrez":
        resolved_indices, coverage = a_scoring.resolve(feature_ids, targets)
    else:
        resolved_indices, coverage = a_scoring.resolve(
            feature_ids, targets, synonyms={}, gene_symbols={}
        )
    resolved = {gene: feature_ids[index] for gene, index in resolved_indices.items()}
    return resolved, coverage


def _read_expression_matrix(path: Path) -> tuple[list[str], list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t")
        header = next(reader, None)
        if not header or len(header) < 4:
            raise ValueError("Expression matrix must contain one feature column and three samples")
        sample_ids = header[1:]
        feature_ids = []
        matrix = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(header) or not row[0]:
                raise ValueError("Expression matrix rows must align to the declared samples")
            values = []
            for value in row[1:]:
                if value.strip().upper() in {"", "NA", "N/A", "NULL"}:
                    values.append(math.nan)
                    continue
                try:
                    values.append(float(value))
                except ValueError:
                    raise ValueError("Expression matrix contains a non-numeric value") from None
            feature_ids.append(row[0])
            matrix.append(values)
    if len(set(feature_ids)) != len(feature_ids):
        raise ValueError("Expression feature identifiers must be unique for panel scoring")
    if len(set(sample_ids)) != len(sample_ids) or any(not sample for sample in sample_ids):
        raise ValueError("Expression matrix sample columns must be unique and non-empty")
    return feature_ids, sample_ids, matrix


def _aligned_gene_lengths(dataset: BulkDataset, feature_ids: Sequence[str]) -> list[float] | None:
    lengths = dataset.gene_lengths
    if lengths is None:
        return None
    if isinstance(lengths, Mapping):
        if any(feature not in lengths for feature in feature_ids):
            return None
        raw_lengths = [lengths[feature] for feature in feature_ids]
    else:
        raw_lengths = list(lengths)
        if len(raw_lengths) != len(feature_ids):
            raise ValueError("Gene lengths must align to every expression feature")
    try:
        parsed = [float(value) for value in raw_lengths]
    except (TypeError, ValueError):
        raise ValueError("Gene lengths must be numeric") from None
    if any(not math.isfinite(value) or value <= 0 for value in parsed):
        raise ValueError("Gene lengths must be finite and positive")
    return parsed


def _panel_analysis_scale(
    matrix: list[list[float]], feature_ids: Sequence[str], dataset: BulkDataset
) -> tuple[list[list[float]], list[list[float]] | None, str]:
    representation = dataset.representation
    unit = str(getattr(representation, "unit", "")).casefold()
    platform = str(getattr(representation, "platform", "")).casefold()
    transform = str(getattr(representation, "transform", "")).casefold()
    lengths = _aligned_gene_lengths(dataset, feature_ids)

    if unit == "counts":
        if any(
            not math.isfinite(value) or value < 0 or value != round(value)
            for row in matrix for value in row
        ):
            raise ValueError("Count panel inputs must be finite non-negative integers")
        if platform == "rnaseq" and lengths is not None:
            tpm = a_scoring.to_tpm(matrix, representation, lengths)
            return a_scoring.log2p1(tpm), tpm, "log2_tpm"
        library_sizes = [sum(row[column] for row in matrix) for column in range(len(matrix[0]))]
        if any(not math.isfinite(size) or size <= 0 for size in library_sizes):
            raise ValueError("Count panel inputs need positive full-library totals")
        cpm = [
            [value * 1_000_000.0 / library_sizes[column] for column, value in enumerate(row)]
            for row in matrix
        ]
        return a_scoring.log2p1(cpm), None, "log2_cpm"

    if platform == "rnaseq" and transform == "linear" and unit in {"tpm", "fpkm", "rpkm"}:
        tpm = a_scoring.to_tpm(matrix, representation, lengths)
        return a_scoring.log2p1(tpm), tpm, "log2_tpm"
    if transform in {"log2", "log2p1", "other"}:
        return matrix, None, f"source_{transform}"
    if transform == "linear":
        return a_scoring.log2p1(matrix), None, "log2p1_source"
    raise ValueError("Panel scoring needs a recognized linear or log expression transform")


def _base_config(dataset: BulkDataset, mode: str, extra: Mapping[str, Any], outputs: Sequence[str]) -> dict[str, Any]:
    return {
        "paper": dataset.paper,
        "dataset_id": dataset.dataset_id,
        "mode": mode,
        "representation": _representation_config(dataset),
        "expected_outputs": list(outputs),
        **dict(extra),
    }


def _representation_config(dataset: BulkDataset) -> dict[str, str]:
    rep = dataset.representation
    return {
        "platform": str(getattr(rep, "platform", "unknown")),
        "unit": str(getattr(rep, "unit", "unknown")),
        "transform": str(getattr(rep, "transform", "unknown")),
        "feature_id": str(getattr(rep, "feature_id", "unknown")),
        "de_engine": dataset.de_engine,
    }


def _call_r(
    dataset: BulkDataset,
    stage: Path,
    script_name: str,
    inputs: Mapping[str, Path],
    config: dict[str, Any],
    expected: Sequence[str],
    runner,
    *,
    endpoint: str | None = None,
    extra_inputs: Sequence[Path] = (),
) -> RResult:
    script = ROOT / "r/scripts" / script_name
    config = dict(config)
    config["expected_outputs"] = list(expected)
    bridge_output = stage / "bridge"
    result = run_r(script, dict(inputs), config, bridge_output, runner=runner)
    _write_module_manifest(
        dataset, stage, str(config.get("mode")), [*inputs.values(), *extra_inputs],
        run_r=result, runner_script=script_name, endpoint=endpoint,
    )
    return result


def _write_module_manifest(
    dataset: BulkDataset,
    stage: Path,
    name: str,
    input_paths: Sequence[Path],
    *,
    run_r: RResult,
    runner_script: str,
    endpoint: str | None,
    extra_outputs: Sequence[Path] = (),
) -> None:
    inputs = {}
    for index, path in enumerate(input_paths):
        label = path.name
        if label in inputs:
            label = f"{index}:{label}"
        inputs[label] = _sha256(path)
    if dataset.paper == "A":
        representation_file = ROOT / "docs/cohorts/REPRESENTATION.tsv"
        if representation_file.is_file():
            inputs.setdefault("REPRESENTATION.tsv", _sha256(representation_file))
    code_hashes = _module_code_sha256(dataset, runner_script)
    if name in {"panels", "scores"}:
        for path in (a_scoring.PANEL_REGISTRY_PATH, a_scoring.ALIAS_TABLE_PATH):
            inputs.setdefault(path.name, _sha256(path))
        runtime = Path(os.environ.get("THESIS_RUNTIME", ROOT / ".scratch/runtime")).expanduser()
        gene_info = a_scoring.gene_info_path(runtime)
        if gene_info.is_file():
            inputs.setdefault("pinned_gene_info", _sha256(gene_info))
    bridge_manifest = stage / "bridge" / "manifest.json"
    outputs = {
        str(Path("bridge") / output_name): _sha256(stage / "bridge" / output_name)
        for output_name in run_r.manifest["output_sha256"]
        if (stage / "bridge" / output_name).is_file()
    }
    for path in extra_outputs:
        if path.is_file():
            outputs[path.relative_to(stage).as_posix()] = _sha256(path)
    manifest = {
        "schema_version": 2,
        "paper": dataset.paper,
        "dataset_id": dataset.dataset_id,
        "stage": name,
        "data_classification": dataset.data_classification,
        "representation": _representation_config(dataset),
        "dataset_identity": _dataset_identity(dataset),
        "dataset_input_sha256": _dataset_input_sha256(dataset),
        "endpoint": endpoint,
        "r_script": runner_script,
        "input_sha256": inputs,
        "code_sha256": code_hashes,
        "output_sha256": outputs,
        "run_r_manifest": {
            "path": "bridge/manifest.json",
            "sha256": _sha256(bridge_manifest),
        },
    }
    _write_immutable_json(stage / "manifest.json", manifest)


def _module_code_sha256(dataset: BulkDataset, runner_script: str) -> dict[str, str]:
    code_paths = [
        ROOT / "tools/a_bulk/core.py",
        ROOT / "tools/a_bulk/__main__.py",
        ROOT / "tools/a_scoring/core.py",
        ROOT / "tools/r_bridge/__init__.py",
        ROOT / "r/scripts" / runner_script,
    ]
    if dataset.paper == "A":
        code_paths.append(ROOT / "tools/a_cohorts/view.py")
        code_paths.append(ROOT / "tools/a_cohorts/core.py")
    return {path.relative_to(ROOT).as_posix(): _sha256(path) for path in code_paths}


def _write_immutable_json(path: Path, content: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(content, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise FileExistsError(f"Existing analysis manifest differs: {path.name}")
        return
    path.write_text(rendered, encoding="utf-8")


def _write_patient_free_summary(
    dataset: BulkDataset,
    root: Path,
    *,
    fresh_stage_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    allow_outcomes: bool = False,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema_version": 2,
        "paper": dataset.paper,
        "dataset_id": dataset.dataset_id,
        "data_classification": dataset.data_classification,
        "representation": _representation_config(dataset),
        "stages": {},
        "provenance": {},
        "excluded_stage_summaries": {},
    }
    stage_contracts = (
        ("qc", "qc_summary.json", True),
        ("pca", "pca_summary.json", True),
        ("de", "de_summary.json", True),
        ("gsea", "gsea_summary.json", True),
        ("scores", "summary.json", False),
    )
    fresh = fresh_stage_summaries or {}
    for step, filename, in_bridge in stage_contracts:
        stage_dir = root / step
        summary_path = stage_dir / "bridge" / filename if in_bridge else stage_dir / filename
        manifest_path = stage_dir / "manifest.json"
        if step in {"de", "gsea"} and (not allow_outcomes or step not in fresh):
            if summary_path.is_file() or manifest_path.is_file():
                summary["excluded_stage_summaries"][step] = (
                    "outcome_guard_required" if not allow_outcomes
                    else "outcome_summary_must_be_from_current_run"
                )
            continue
        if step not in fresh and not (summary_path.is_file() or manifest_path.is_file()):
            continue

        manifest = None
        if manifest_path.is_file():
            try:
                manifest = _read_json(manifest_path)
            except (OSError, ValueError, TypeError):
                manifest = None
        if step == "pca" and not allow_outcomes and manifest and manifest.get("endpoint"):
            summary["excluded_stage_summaries"][step] = "response_colored_pca_requires_outcome_guard"
            continue

        reason, provenance = _verify_stage_summary(
            dataset, stage_dir, step, filename, in_bridge, manifest
        )
        if reason:
            if step in fresh:
                raise ValueError(f"Fresh {step} summary failed provenance validation: {reason}")
            summary["excluded_stage_summaries"][step] = reason
            continue
        if step in fresh:
            stage_summary = dict(fresh[step])
        else:
            if not summary_path.is_file():
                summary["excluded_stage_summaries"][step] = "summary_file_missing"
                continue
            try:
                stage_summary = _read_json(summary_path)
            except (OSError, ValueError, TypeError):
                summary["excluded_stage_summaries"][step] = "summary_file_invalid"
                continue
        summary["stages"][step] = stage_summary
        summary["provenance"][step] = provenance
    return summary


def _dataset_identity(dataset: BulkDataset) -> dict[str, Any]:
    return {
        "paper": dataset.paper,
        "dataset_id": dataset.dataset_id,
        "data_classification": dataset.data_classification,
        "representation": _representation_config(dataset),
        "endpoint_families": list(dataset.endpoint_families),
        "sample_id_field": dataset.sample_id_field,
    }


def _dataset_input_sha256(dataset: BulkDataset) -> dict[str, str]:
    stable_rows = [
        {str(key): None if value is None else str(value) for key, value in row.items()}
        for row in dataset.clinical_rows
    ]
    rendered_rows = json.dumps(stable_rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    row_digest = hashlib.sha256(rendered_rows.encode("utf-8")).hexdigest()
    source_digest = (
        _sha256(dataset.clinical_path)
        if dataset.clinical_path is not None and dataset.clinical_path.is_file()
        else ""
    )
    clinical_digest = hashlib.sha256(f"{source_digest}:{row_digest}".encode("ascii")).hexdigest()
    result = {
        "expression": _sha256(dataset.expression_path),
        "clinical": clinical_digest,
    }
    if dataset.gene_lengths is not None:
        if isinstance(dataset.gene_lengths, Mapping):
            stable_lengths = sorted((str(key), str(value)) for key, value in dataset.gene_lengths.items())
        else:
            stable_lengths = [str(value) for value in dataset.gene_lengths]
        rendered_lengths = json.dumps(stable_lengths, separators=(",", ":"), ensure_ascii=False)
        result["gene_lengths"] = hashlib.sha256(rendered_lengths.encode("utf-8")).hexdigest()
    return result


def _verify_stage_summary(
    dataset: BulkDataset,
    stage_dir: Path,
    stage: str,
    summary_filename: str,
    summary_in_bridge: bool,
    manifest: Mapping[str, Any] | None,
) -> tuple[str | None, dict[str, Any]]:
    if manifest is None:
        return "stage_manifest_missing_or_invalid", {}
    if manifest.get("dataset_identity") != _dataset_identity(dataset):
        return "dataset_identity_mismatch", {}
    if manifest.get("dataset_input_sha256") != _dataset_input_sha256(dataset):
        return "dataset_input_hash_mismatch", {}
    summary_relative = f"bridge/{summary_filename}" if summary_in_bridge else summary_filename
    recorded_outputs = manifest.get("output_sha256")
    if not isinstance(recorded_outputs, Mapping):
        return "summary_output_hash_missing", {}
    safe_outputs = _sanitized_hash_map(recorded_outputs)
    if safe_outputs is None or summary_relative not in safe_outputs:
        return "summary_output_hash_missing", {}
    for identifier, digest in safe_outputs.items():
        output_path = stage_dir / identifier
        if output_path.is_symlink() or not output_path.is_file() or _sha256(output_path) != digest:
            return "stage_output_hash_mismatch", {}
    bridge_info = manifest.get("run_r_manifest")
    if not isinstance(bridge_info, Mapping):
        return "bridge_manifest_hash_missing", {}
    bridge_relative = bridge_info.get("path")
    if not isinstance(bridge_relative, str):
        return "bridge_manifest_path_invalid", {}
    bridge_path_obj = Path(bridge_relative)
    if (
        bridge_path_obj.is_absolute()
        or PureWindowsPath(bridge_relative).is_absolute()
        or ".." in bridge_path_obj.parts
    ):
        return "bridge_manifest_path_invalid", {}
    bridge_path = stage_dir / bridge_path_obj
    if not bridge_path.is_file() or _sha256(bridge_path) != bridge_info.get("sha256"):
        return "bridge_manifest_hash_mismatch", {}
    script = manifest.get("r_script")
    if (
        not isinstance(script, str)
        or Path(script).is_absolute()
        or PureWindowsPath(script).is_absolute()
        or ".." in Path(script).parts
        or script not in {"bulk_qc_pca.R", "de_deseq2.R", "de_limma.R", "fgsea_rank.R"}
    ):
        return "script_identifier_invalid", {}
    safe_hashes = {}
    for field in ("dataset_input_sha256", "input_sha256", "code_sha256", "output_sha256"):
        mapping = manifest.get(field)
        if not isinstance(mapping, Mapping):
            return "manifest_hash_map_invalid", {}
        sanitized = _sanitized_hash_map(mapping)
        if sanitized is None:
            return "manifest_hash_map_invalid", {}
        safe_hashes[field] = sanitized
    if safe_hashes["code_sha256"] != _module_code_sha256(dataset, script):
        return "code_hash_mismatch", {}
    if not _stage_input_hashes_match(dataset, stage, manifest, safe_hashes["input_sha256"]):
        return "stage_input_hash_mismatch", {}
    provenance = {
        "stage_manifest": f"{stage}/manifest.json",
        "stage_manifest_sha256": _sha256(stage_dir / "manifest.json"),
        "bridge_manifest": f"{stage}/{bridge_path_obj.as_posix()}",
        "bridge_manifest_sha256": str(bridge_info["sha256"]),
        "r_script": f"r/scripts/{script}",
        **safe_hashes,
    }
    return None, provenance


def _stage_input_hashes_match(
    dataset: BulkDataset,
    stage: str,
    manifest: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> bool:
    observed = set(input_hashes.values())
    expected = set()
    if stage != "gsea":
        expected.add(_sha256(dataset.expression_path))
    if dataset.paper == "A":
        representation_file = ROOT / "docs/cohorts/REPRESENTATION.tsv"
        if representation_file.is_file():
            expected.add(_sha256(representation_file))
    if stage in {"qc", "pca", "de"}:
        include_response = stage == "de" or (stage == "pca" and bool(manifest.get("endpoint")))
        endpoint = str(manifest.get("endpoint") or "orr")
        metadata, _ = _sample_metadata_content(
            dataset,
            include_response=include_response,
            endpoint=endpoint,
            drop_excluded=stage == "de",
        )
        expected.add(hashlib.sha256(metadata.encode("utf-8")).hexdigest())
    if stage == "scores":
        expected.update(
            _sha256(path)
            for path in (a_scoring.PANEL_REGISTRY_PATH, a_scoring.ALIAS_TABLE_PATH)
        )
        runtime = Path(os.environ.get("THESIS_RUNTIME", ROOT / ".scratch/runtime")).expanduser()
        gene_info = a_scoring.gene_info_path(runtime)
        if gene_info.is_file():
            expected.add(_sha256(gene_info))
        elif "pinned_gene_info" in input_hashes:
            return False
    return expected.issubset(observed)


def _sanitized_hash_map(value: Mapping[str, Any]) -> dict[str, str] | None:
    sanitized = {}
    for identifier, digest in value.items():
        if not isinstance(identifier, str):
            return None
        relative = Path(identifier)
        if (
            relative.is_absolute()
            or PureWindowsPath(identifier).is_absolute()
            or ".." in relative.parts
            or not re.fullmatch(r"[0-9a-f]{64}", str(digest))
        ):
            return None
        sanitized[identifier] = str(digest)
    return sanitized


def _read_metadata(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream, delimiter="\t")]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_tsv_immutable(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    rendered = buffer.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise FileExistsError(f"Existing analysis output differs: {path.name}")
        return
    path.write_text(rendered, encoding="utf-8")


def _format_number(value: Any) -> str:
    if value is None:
        return "NA"
    number = float(value)
    return format(number, ".17g") if math.isfinite(number) else "NA"


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
