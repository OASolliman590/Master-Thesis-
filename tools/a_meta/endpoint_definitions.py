"""Explicit endpoint-definition IDs and pooling policies for A-META."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EndpointDefinition:
    cohort_id: str | None
    family: str
    loader_definition: str
    definition_id: str
    per_study_only: bool = False


# Exact loader definitions are intentionally enumerated. ORR rows share one ID;
# clinical-benefit definitions keep separate IDs where their rules differ.
ENDPOINT_DEFINITION_TABLE = (
    EndpointDefinition(None, "orr", "ORR: CR/PR versus SD/PD; original best.resp category retained.", "ORR"),
    EndpointDefinition(None, "orr", "ORR: CR/PR versus SD/NR; original category retained.", "ORR"),
    EndpointDefinition(None, "orr", "ORR: CR/PR versus SD/PD; original category retained.", "ORR"),
    EndpointDefinition(None, "orr", "Best overall response, RECIST 1.1", "ORR"),
    EndpointDefinition(None, "orr", "Best response on immunotherapy (RECIST), as named in GEO SOFT.", "ORR"),
    EndpointDefinition(None, "orr", "Best response per RECIST 1.1 (paper methods); ORR CR/PR versus SD/PD.", "ORR"),
    EndpointDefinition(None, "orr", "ORR uses best_response (PR/SD/PD); separate SOURCE_BINARY clinical benefit uses clinical_benefit_response.", "ORR"),
    EndpointDefinition(None, "orr", "source category; see admitted records", "ORR"),
    EndpointDefinition(None, "orr", "RECIST 1.1", "ORR"),
    EndpointDefinition(None, "orr", "ORR RECIST CR PR SD PD", "ORR"),
    EndpointDefinition(
        None,
        "orr",
        "Response UNKNOWN; sample-title prefixes were not interpreted as response labels.",
        "ORR",
    ),
    EndpointDefinition(
        None,
        "clinical_benefit",
        "DCB/NDB",
        "CB_DCB_NDB",
    ),
    EndpointDefinition(
        None,
        "clinical_benefit",
        "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB).",
        "CB_DCB_NDB_EXPLICIT",
    ),
    EndpointDefinition(
        None,
        "clinical_benefit",
        "Clinical benefit: PFS > 6 months.",
        "CB_PFS_GT6M",
    ),
    EndpointDefinition(
        "gse165278",
        "clinical_benefit",
        "Clinical benefit: progression-free survival > 24 weeks after starting ipilimumab (Nathanson 2017). Not ORR.",
        "CB_PFS_GT24W_IPILIMUMAB",
    ),
    EndpointDefinition(
        "gide2019",
        "clinical_benefit",
        "source category; see admitted records",
        "CB_CRPR_OR_SD_PFS_GT182P5D_GIDE2019",
    ),
    EndpointDefinition(
        "gide2019",
        "clinical_benefit",
        "RECIST 1.1",
        "CB_CRPR_OR_SD_PFS_GT182P5D_GIDE2019",
    ),
    EndpointDefinition(
        "gide2019",
        "clinical_benefit",
        "CR or PR, or SD with PFS > 182.5 days without progression: R; PD or SD with PFS <= 182.5 days: NR; unknowns remain unknown. Never merge with ORR.",
        "CB_CRPR_OR_SD_PFS_GT182P5D_GIDE2019",
    ),
    EndpointDefinition(
        "gse135222",
        "clinical_benefit",
        "DCB/NDB",
        "CB_DCB_NDB_GSE135222",
    ),
    EndpointDefinition(
        "gse135222",
        "clinical_benefit",
        "durable clinical benefit (DCB) versus non-durable benefit (NDB)",
        "CB_DCB_NDB_GSE135222",
    ),
    EndpointDefinition(
        "gse136961",
        "clinical_benefit",
        "durable clinical benefit; source does not document the patient-level category mapping or threshold in the pinned family SOFT",
        "CB_DURABLE_BENEFIT_UNSPECIFIED_GSE136961",
    ),
    EndpointDefinition(
        "gse168204",
        "clinical_benefit",
        "source category; see admitted records",
        "SOURCE_LABEL_GSE168204",
        per_study_only=True,
    ),
    EndpointDefinition(
        "braun2020",
        "clinical_benefit",
        "CB/ICB/NCB",
        "CB_ICB_NCB_BRAUN2020",
    ),
    EndpointDefinition(
        "gse140901",
        "clinical_benefit",
        "ORR uses best_response (PR/SD/PD); separate SOURCE_BINARY clinical benefit uses clinical_benefit_response.",
        "SOURCE_LABEL_GSE140901",
        per_study_only=True,
    ),
    EndpointDefinition(
        None,
        "source_label",
        "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST.",
        "SOURCE_LABEL_UNSPECIFIED",
        per_study_only=True,
    ),
    EndpointDefinition(
        None,
        "source_label",
        "SOURCE_BINARY; raw GEO categories retained; no RECIST CR/PR evidence in SOFT.",
        "SOURCE_LABEL_UNSPECIFIED",
        per_study_only=True,
    ),
    EndpointDefinition(
        "gse218989",
        "source_label",
        "SOURCE_BINARY; raw GEO categories retained; no RECIST CR/PR evidence in SOFT.",
        "SOURCE_LABEL_GSE218989",
        per_study_only=True,
    ),
    EndpointDefinition(
        "gse168204",
        "source_label",
        "source category; see admitted records",
        "SOURCE_LABEL_GSE168204",
        per_study_only=True,
    ),
    EndpointDefinition(
        "gse111636",
        "source_label",
        "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST.",
        "SOURCE_LABEL_GSE111636",
        per_study_only=True,
    ),
    EndpointDefinition(
        "gse111636",
        "source_label",
        "treatment response SOURCE_BINARY; SOFT does not define RECIST",
        "SOURCE_LABEL_GSE111636",
        per_study_only=True,
    ),
    EndpointDefinition(
        "gse140901",
        "source_label",
        "ORR uses best_response (PR/SD/PD); separate SOURCE_BINARY clinical benefit uses clinical_benefit_response.",
        "SOURCE_LABEL_GSE140901",
        per_study_only=True,
    ),
)


def endpoint_definition_id(cohort_id: str, family: str, loader_definition: object) -> str:
    definition = _normalise(loader_definition)
    if not definition:
        raise ValueError("Endpoint definition is empty and cannot be mapped")
    matches = [
        row for row in ENDPOINT_DEFINITION_TABLE
        if row.family == family
        and _normalise(row.loader_definition) == definition
        and row.cohort_id in {None, cohort_id}
    ]
    exact_cohort_matches = [row for row in matches if row.cohort_id == cohort_id]
    candidates = exact_cohort_matches or [row for row in matches if row.cohort_id is None]
    ids = {row.definition_id for row in candidates}
    if len(ids) != 1:
        raise ValueError(
            f"Unmapped or ambiguous endpoint definition for {cohort_id}/{family}: {loader_definition!r}"
        )
    return next(iter(ids))


def endpoint_is_per_study_only(definition_id: str, family: str) -> bool:
    if family == "source_label":
        return True
    matches = {row.per_study_only for row in ENDPOINT_DEFINITION_TABLE if row.definition_id == definition_id}
    return matches == {True}


def is_known_endpoint_definition(definition_id: str, family: str) -> bool:
    return any(
        row.definition_id == definition_id and row.family == family
        for row in ENDPOINT_DEFINITION_TABLE
    )


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()
