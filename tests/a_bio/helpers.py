from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


SYNTHETIC_PRODUCER = "tools.a_bio.synthetic_fixture"


def write_synthetic_materialization(
    runtime: Path,
    *,
    cohort_id: str = "invented_study",
    platform: str = "rnaseq",
    endpoint_families: tuple[str, ...] = ("orr",),
    endpoint_definition: str | None = None,
    sample_count: int = 8,
    cancer: str = "melanoma",
    include_frozen_genes: bool = False,
) -> Path:
    simple = runtime / cohort_id / "simple"
    simple.mkdir(parents=True)
    sample_ids = [f"demo_{cohort_id}_{index:02d}" for index in range(sample_count)]

    endpoint_definitions = {
        "orr": "Best response per RECIST 1.1 (paper methods); ORR CR/PR versus SD/PD.",
        "clinical_benefit": (
            "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB)."
        ),
        "source_label": (
            "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST."
        ),
    }
    if endpoint_definition is None:
        if len(endpoint_families) != 1:
            raise ValueError("Invented fixtures need one endpoint family per cohort")
        endpoint_definition = endpoint_definitions[endpoint_families[0]]

    genes = {"GZMA", "PRF1", "CD8A", "CD8B", "IFNG"}
    if include_frozen_genes:
        from tools.a_bio.fixtures import _frozen_gene_universe

        genes.update(_frozen_gene_universe())
    genes = sorted(genes)

    with (simple / "expression.tsv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *sample_ids])
        for gene_index, gene in enumerate(genes):
            writer.writerow([
                gene,
                *[
                    f"{1.0 + (gene_index % 31) * 0.7 + sample * 0.2 + ((gene_index * 17 + sample * 11) % 23) / 10 + (5 if sample < sample_count // 2 else 0):.3f}"
                    for sample in range(sample_count)
                ],
            ])

    clinical_columns = [
        "patient_id", "drug_class", "batch", "biopsy", "raw_orr", "orr",
        "clinical_benefit", "raw_clinical_benefit", "treatment_outcome",
        "endpoint_definition", "cancer", "pfs", "os", "Tumor_Shrinkage",
    ]
    with (simple / "clinical.tsv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=clinical_columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, sample_id in enumerate(sample_ids):
            label = "CR" if index < sample_count // 2 else "PD"
            writer.writerow({
                "patient_id": sample_id,
                "drug_class": "ANTI_PD_L1_AXIS",
                "batch": "batch_1" if index % 2 else "batch_2",
                "biopsy": "primary",
                "raw_orr": label,
                "orr": "R" if index < sample_count // 2 else "NR",
                "clinical_benefit": "DCB" if index < sample_count // 2 else "NDB",
                "raw_clinical_benefit": "DCB" if index < sample_count // 2 else "NDB",
                "treatment_outcome": "R" if index < sample_count // 2 else "NR",
                "endpoint_definition": endpoint_definition,
                "cancer": ("melanoma" if index % 2 == 0 else "lung") if cancer == "multi" else cancer,
                "pfs": "240 days",
                "os": "480 days",
                "Tumor_Shrinkage": "invented-only-hidden-value",
            })
    (simple / "caveats.md").write_text("Invented fixture only.\n", encoding="utf-8")

    representation = {
        "platform": platform,
        "unit": "tpm",
        "transform": "linear",
        "feature_id": "symbol",
    }
    manifest = {
        "manifest_version": 1,
        "producer": SYNTHETIC_PRODUCER,
        "kind": "cohort_input",
        "data_classification": "synthetic",
        "cohort_id": cohort_id,
        "invented_source": "All rows and expression values were invented for software tests.",
        "source_inputs_sha256": {
            "invented_fixture_definition": hashlib.sha256(
                b"A-BIO invented cohort fixture v1"
            ).hexdigest(),
        },
        "patients": sample_count,
        "metadata": {
            "cancer": cancer,
            "representation": representation,
            "de_engine": "limma",
            "endpoint_families": list(endpoint_families),
            "uniform_drug_class": None,
        },
        "outputs_sha256": {
            name: hashlib.sha256((simple / name).read_bytes()).hexdigest()
            for name in ("expression.tsv", "clinical.tsv", "caveats.md")
        },
    }
    manifest_path = simple / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))
