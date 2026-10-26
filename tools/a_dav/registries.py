"""Validate supplied, immutable invented registries and their lexical identities."""
from __future__ import annotations

from typing import Any

from .core import DavError, ENTITY_TABLES, SchemaStore, dependency, finish, require, stage_boundary

REASON_CODES = frozenset({"AMBIGUOUS_ALIAS", "SOURCE_CONTEXT_UNKNOWN", "SOURCE_CONTEXT_CONFLICT", "IDENTITY_UNRESOLVED"})
_KEYS = {"study_registry": "study_id", "publication_family": "publication_id", "source_record": "source_object_id", "patient_registry": "patient_uid", "specimen_registry": "specimen_uid", "assay_registry": "assay_uid", "clinical_outcome": "outcome_id", "treatment_episode": "treatment_episode_id", "treatment_exposure": "treatment_exposure_id", "episode_binding": "binding_id", "overlap_edge": "overlap_edge_id", "prior_exposure_record": "exposure_id"}


@stage_boundary("registries")
def build_registries(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    assert schemas is not None
    if "existing_seams" in packet.get("dependencies", {}):
        dependency(packet, "existing_seams", schemas)
    records = packet["records"]
    unknown_schema: DavError | None = None
    for table in sorted(ENTITY_TABLES & records.keys()):
        for row in records[table]:
            try:
                schemas.validate(table, row)
            except DavError as exc:
                if not exc.blocked:
                    raise
                unknown_schema = exc
    if unknown_schema is not None:
        raise unknown_schema
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for table in ENTITY_TABLES & records.keys():
        index: dict[str, dict[str, Any]] = {}
        for row in records[table]:
            key = row.get(_KEYS[table])
            require(isinstance(key, str) and bool(key), "MISSING_ASSERTION", blocked=True)
            require(key not in index, "DUPLICATE_ID")
            index[key] = row
        indexes[table] = index
    for table in ("study_registry", "publication_family", "source_record", "patient_registry", "specimen_registry", "assay_registry"):
        require(bool(indexes.get(table)), "MISSING_ASSERTION", blocked=True)
    studies = indexes["study_registry"]
    patients = indexes["patient_registry"]
    specimens = indexes["specimen_registry"]
    sources = indexes["source_record"]
    episodes = indexes.get("treatment_episode", {})
    for table, rows in indexes.items():
        for row in rows.values():
            for field, target in (("study_id", "study_registry"), ("patient_uid", "patient_registry"), ("specimen_uid", "specimen_registry"), ("source_object_id", "source_record"), ("treatment_episode_id", "treatment_episode")):
                if field in row and field != _KEYS[table]:
                    require(row[field] in indexes.get(target, {}), "FOREIGN_KEY_UNRESOLVED")
            if "study_id" in row and "patient_uid" in row:
                require(patients[row["patient_uid"]]["study_id"] == row["study_id"], "FOREIGN_KEY_UNRESOLVED")
            if "publication_family_id" in row:
                require(row["publication_family_id"] == studies[row["study_id"]]["publication_family_id"], "FOREIGN_KEY_UNRESOLVED")
    for study in studies.values():
        require(any(r["publication_family_id"] == study["publication_family_id"] and r["study_id"] == study["study_id"] for r in indexes["publication_family"].values()), "FOREIGN_KEY_UNRESOLVED")
    aliases: dict[tuple[str, str], str] = {}
    for patient in patients.values():
        for alias in [patient["source_patient_id"], *patient.get("source_aliases", [])]:
            key = (patient["study_id"], alias)
            require(key not in aliases or aliases[key] == patient["patient_uid"], "AMBIGUOUS_ALIAS")
            aliases[key] = patient["patient_uid"]
    sample_aliases: dict[tuple[str, str], str] = {}
    for specimen in specimens.values():
        study_id = patients[specimen["patient_uid"]]["study_id"]
        for alias in specimen["raw_sample_aliases"]:
            key = (study_id, alias)
            require(key not in sample_aliases or sample_aliases[key] == specimen["specimen_uid"], "AMBIGUOUS_ALIAS")
            sample_aliases[key] = specimen["specimen_uid"]
    headers: set[tuple[str, str]] = set()
    for assay in indexes["assay_registry"].values():
        specimen = specimens[assay["specimen_uid"]]
        require(assay["source_sample_id"] in specimen["raw_sample_aliases"], "FOREIGN_KEY_UNRESOLVED")
        require(sources[assay["source_object_id"]]["study_id"] == patients[specimen["patient_uid"]]["study_id"], "FOREIGN_KEY_UNRESOLVED")
        key = (assay["source_object_id"], assay["matrix_header"])
        require(key not in headers, "DUPLICATE_ID")
        headers.add(key)
    subjects = {"SPECIMEN": specimens, "CLINICAL_OUTCOME": indexes.get("clinical_outcome", {}), "TREATMENT_EXPOSURE": indexes.get("treatment_exposure", {})}
    for binding in indexes.get("episode_binding", {}).values():
        require(binding["subject_id"] in subjects[binding["subject_type"]], "FOREIGN_KEY_UNRESOLVED")
        subject = subjects[binding["subject_type"]][binding["subject_id"]]
        require(subject["patient_uid"] == binding["patient_uid"] == episodes[binding["treatment_episode_id"]]["patient_uid"], "FOREIGN_KEY_UNRESOLVED")
    cfg = packet["config"].get("registries", {})
    require(set(cfg.get("study_ids", [])) == set(studies), "SOURCE_CONTEXT_UNKNOWN", blocked=True)
    require(set(cfg.get("source_hashes", {})) == set(sources), "SOURCE_CONTEXT_UNKNOWN", blocked=True)
    for source in sources.values():
        require(source.get("validation_status") != "FAIL", "SOURCE_CONTEXT_CONFLICT")
        require(source.get("retrieval_status") == "RETRIEVED" and source.get("validation_status") in {"PASS", "STRUCTURAL_ONLY"} and source.get("hash_scope") == "FULL_OBJECT" and source.get("sha256") is not None, "SOURCE_CONTEXT_UNKNOWN", blocked=True)
        require(cfg["source_hashes"][source["source_object_id"]] == source["sha256"], "SOURCE_CONTEXT_CONFLICT")
    require(all(p["patient_identity_confidence"] != "DISPROVED" for p in patients.values()), "IDENTITY_UNRESOLVED")
    require(all(p["patient_identity_confidence"] == "VERIFIED" for p in patients.values()), "IDENTITY_UNRESOLVED", blocked=True)
    return finish("registries", packet, records, audit=[{"check": "LEXICAL_IDENTITIES_PRESERVED", "patient_alias_count": len(aliases), "specimen_alias_count": len(sample_aliases)}], schemas=schemas)
