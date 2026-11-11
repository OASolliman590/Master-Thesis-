"""Invented, hash-matched A-BIO inputs for software checks only."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .paths import (
    absolute_path,
    preflight_tree,
    validate_contained_path,
    validate_single_component,
    write_immutable_bytes,
)


SYNTHETIC_PRODUCER = "tools.a_bio.synthetic_fixture"
INVENTED_SOURCE = "All rows and expression values were invented for software tests."
ENDPOINT_DEFINITIONS = {
    "orr": "Best response per RECIST 1.1 (paper methods); ORR CR/PR versus SD/PD.",
    "clinical_benefit": (
        "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB)."
    ),
    "source_label": (
        "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST."
    ),
}


def write_fixture(
    runtime: Path | str,
    *,
    cohort_id: str = "invented_a_bio_demo",
    endpoint_family: str = "orr",
    sample_count: int = 8,
    cancer: str = "melanoma",
) -> Path:
    """Create one fully invented simple materialization with the existing loader shape."""
    if endpoint_family not in ENDPOINT_DEFINITIONS:
        raise ValueError("Unknown synthetic endpoint family")
    if sample_count < 8 or sample_count % 2:
        raise ValueError("Synthetic fixtures need an even sample count of at least eight")
    cohort_id = validate_single_component(cohort_id, label="Synthetic cohort identifier")
    from tools.a_bulk.core import validate_dataset_identifiers
    from tools.a_meta.provenance import known_cohort_ids

    validate_dataset_identifiers(cohort_id)
    token = "".join(char for char in cohort_id.casefold() if char.isalnum())
    known_tokens = {
        "".join(char for char in known.casefold() if char.isalnum())
        for known in known_cohort_ids()
    }
    if any(known and known in token for known in known_tokens):
        raise ValueError("Known cohort identifiers are not synthetic")
    if cancer not in {"melanoma", "lung", "kidney", "bladder", "gastric", "liver", "head_and_neck"}:
        raise ValueError("Synthetic cancer must be a named single-cancer stratum")

    runtime_root = absolute_path(runtime, label="Synthetic runtime")
    simple = validate_contained_path(
        runtime_root, runtime_root / cohort_id / "simple", label="Synthetic fixture destination"
    )
    for name in ("expression.tsv", "clinical.tsv", "caveats.md", "manifest.json"):
        validate_contained_path(runtime_root, simple / name, label="Synthetic fixture destination")
    preflight_tree(simple, label="Synthetic fixture destination")
    simple.mkdir(parents=True, exist_ok=True)
    sample_ids = [f"invented_{cohort_id}_{index:03d}" for index in range(sample_count)]
    genes = _frozen_gene_universe()
    expression_content = _expression_content(genes, sample_ids)
    clinical_content = _clinical_content(sample_ids, endpoint_family, cancer)
    caveats_content = "Invented fixture only; no biological or clinical inference is valid.\n"
    outputs = {
        "expression.tsv": expression_content,
        "clinical.tsv": clinical_content,
        "caveats.md": caveats_content,
    }
    for name, content in outputs.items():
        path = simple / name
        write_immutable_bytes(
            runtime_root, path, content.encode("utf-8"), label=f"synthetic fixture file {name}"
        )

    manifest = {
        "manifest_version": 1,
        "producer": SYNTHETIC_PRODUCER,
        "kind": "cohort_input",
        "data_classification": "synthetic",
        "cohort_id": cohort_id,
        "invented_source": INVENTED_SOURCE,
        "source_inputs_sha256": {
            "invented_fixture_definition": hashlib.sha256(
                b"A-BIO invented cohort fixture v1"
            ).hexdigest(),
        },
        "patients": sample_count,
        "metadata": {
            "cancer": cancer,
            "representation": {
                "platform": "rnaseq",
                "unit": "tpm",
                "transform": "linear",
                "feature_id": "symbol",
            },
            "de_engine": "limma",
            "endpoint_families": [endpoint_family],
            "uniform_drug_class": None,
        },
        "outputs_sha256": {
            name: hashlib.sha256(content.encode("utf-8")).hexdigest()
            for name, content in outputs.items()
        },
    }
    manifest_path = simple / "manifest.json"
    rendered_manifest = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    write_immutable_bytes(
        runtime_root, manifest_path, rendered_manifest.encode("utf-8"), label="synthetic fixture manifest"
    )
    return manifest_path


def _frozen_gene_universe() -> tuple[str, ...]:
    from tools.a_meta.features import AVAILABLE_PANEL_IDS
    from tools.a_meta.frozen import (
        HALLMARK_GMT,
        REACTOME_GMT,
        read_common_gene_sets,
        read_frozen_aliases,
        read_gmt,
    )
    from tools.a_scoring.core import panel_definitions

    aliases = read_frozen_aliases()
    panel_ids = tuple(item for item in AVAILABLE_PANEL_IDS if item != "HALLMARK_INTERFERON_GAMMA_RESPONSE")
    panels = panel_definitions(panel_ids)
    hallmarks = read_gmt(HALLMARK_GMT)
    reactome = read_gmt(REACTOME_GMT)
    common = read_common_gene_sets(aliases=aliases)
    genes = {"GZMA", "PRF1", "CD8A", "CD8B", "IFNG"}
    genes.update(aliases.get(gene, gene) for members in panels.values() for gene in members)
    genes.update(
        aliases.get(gene, gene)
        for gene in hallmarks["HALLMARK_INTERFERON_GAMMA_RESPONSE"]
    )
    genes.update(common["HALLMARK_INTERFERON_GAMMA_RESPONSE"])
    reactome_members = next(
        tuple(aliases.get(gene, gene) for gene in members)
        for members in reactome.values()
        if len(set(aliases.get(gene, gene) for gene in members)) >= 15
    )
    genes.update(reactome_members[:15])
    return tuple(sorted(genes))


def _expression_content(genes: tuple[str, ...], sample_ids: list[str]) -> str:
    rows = [["gene", *sample_ids]]
    group_size = len(sample_ids) // 2
    for gene_index, gene in enumerate(genes):
        values = [
            f"{1 + (gene_index % 31) * 0.7 + sample * 0.2 + ((gene_index * 17 + sample * 11) % 23) / 10 + (5 if sample < group_size else 0):.3f}"
            for sample in range(len(sample_ids))
        ]
        rows.append([gene, *values])
    return _render_tsv(rows)


def _clinical_content(sample_ids: list[str], endpoint_family: str, cancer: str) -> str:
    columns = (
        "patient_id", "drug_class", "batch", "biopsy", "raw_orr", "orr",
        "clinical_benefit", "raw_clinical_benefit", "treatment_outcome",
        "endpoint_definition", "cancer", "pfs", "os", "Tumor_Shrinkage",
    )
    group_size = len(sample_ids) // 2
    rows = [columns]
    for index, sample_id in enumerate(sample_ids):
        responder = index < group_size
        rows.append((
            sample_id,
            "ANTI_PD_L1_AXIS",
            "batch_1" if index % 2 else "batch_2",
            "primary",
            "CR" if responder else "PD",
            "R" if responder else "NR",
            "DCB" if responder else "NDB",
            "DCB" if responder else "NDB",
            "R" if responder else "NR",
            ENDPOINT_DEFINITIONS[endpoint_family],
            cancer,
            "240 days",
            "480 days",
            "invented-only-hidden-value",
        ))
    return _render_tsv(rows)


def _render_tsv(rows) -> str:
    import io

    stream = io.StringIO(newline="")
    csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(rows)
    return stream.getvalue()
