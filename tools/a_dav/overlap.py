"""Invented-data typed overlap graph; canonical assertions are immutable."""
from __future__ import annotations
from typing import Any, cast
from .core import SchemaStore, dependency, finish, require, stage_boundary

REASON_CODES = frozenset({"OVERLAP_POLICY_UNKNOWN", "OVERLAP_NODE_UNKNOWN", "OVERLAP_CONTRADICTION", "OVERLAP_EVIDENCE_MISSING"})
NODE_TABLES = {"STUDY": ("study_registry", "study_id"), "PUBLICATION_FAMILY": ("publication_family", "publication_family_id"),
               "SOURCE_OBJECT": ("source_record", "source_object_id"), "PATIENT": ("patient_registry", "patient_uid"),
               "SPECIMEN": ("specimen_registry", "specimen_uid"), "ASSAY": ("assay_registry", "assay_uid")}


@stage_boundary("overlap")
def validate_overlap(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    store = schemas or SchemaStore()
    dependency(packet, "registries", store)
    records = packet["records"]
    config = packet["config"].get("overlap", {})
    nodes: set[tuple[str, str]] = set()
    links: list[tuple[tuple[str, str], tuple[str, str], str]] = []
    for kind, (table, key) in NODE_TABLES.items():
        for row in records.get(table, []):
            store.validate(table, row)
            nodes.add((kind, row[key]))
    trials: dict[str, list[tuple[str, str]]] = {}
    families: dict[str, list[tuple[str, str]]] = {}
    for row in records.get("study_registry", []):
        node = ("STUDY", row["study_id"])
        families.setdefault(row["publication_family_id"], []).append(node)
        if row.get("trial_id"):
            trials.setdefault(row["trial_id"], []).append(node)
        family = ("PUBLICATION_FAMILY", row["publication_family_id"])
        require(family in nodes, "FOREIGN_KEY_UNRESOLVED")
        links.append((node, family, "VERIFIED"))
    for table, kind, key in [("source_record", "SOURCE_OBJECT", "source_object_id"), ("patient_registry", "PATIENT", "patient_uid")]:
        for row in records.get(table, []):
            parent = ("STUDY", row["study_id"])
            require(parent in nodes, "FOREIGN_KEY_UNRESOLVED")
            links.append(((kind, row[key]), parent, "VERIFIED"))
    for table, kind, key, parent_kind, parent_key in [
        ("specimen_registry", "SPECIMEN", "specimen_uid", "PATIENT", "patient_uid"),
        ("assay_registry", "ASSAY", "assay_uid", "SPECIMEN", "specimen_uid")]:
        for row in records.get(table, []):
            parent = (parent_kind, row[parent_key])
            require(parent in nodes, "FOREIGN_KEY_UNRESOLVED")
            links.append(((kind, row[key]), parent, "VERIFIED"))
    publications: dict[str, list[tuple[str, str]]] = {}
    for row in records.get("publication_family", []):
        publications.setdefault(row["publication_id"], []).append(("PUBLICATION_FAMILY", row["publication_family_id"]))
    accession_aliases: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for row in records.get("source_record", []):
        if row.get("accession"):
            accession_aliases.setdefault((row["repository"], row["accession"]), []).append(("SOURCE_OBJECT", row["source_object_id"]))
    for group in list(trials.values()) + list(families.values()) + list(publications.values()) + list(accession_aliases.values()):
        links.extend((group[0], n, "VERIFIED") for n in group[1:])
    edges = records.get("overlap_edge", [])
    ids: set[str] = set()
    independent: list[tuple[tuple[str, str], tuple[str, str]]] = []
    missing_evidence = False
    for edge in edges:
        store.validate("overlap_edge", edge)
        require(edge["overlap_edge_id"] not in ids, "DUPLICATE_ID")
        ids.add(edge["overlap_edge_id"])
        a = (edge["source_node_type"], edge["source_node_id"])
        b = (edge["target_node_type"], edge["target_node_id"])
        require(a in nodes and b in nodes, "OVERLAP_NODE_UNKNOWN")
        certainty, implication = edge["certainty"], edge["implication_for_independence"]
        if certainty == "DISPROVED":
            require(implication not in {"NOT_INDEPENDENT", "INDEPENDENCE_BLOCKED"}, "OVERLAP_CONTRADICTION")
            continue
        if implication == "INDEPENDENT_FOR_DECLARED_UNIT":
            independent.append((a, b))
        elif implication != "NO_IMPLICATION" or edge["edge_type"] != "OTHER":
            require(implication != "INDEPENDENT_FOR_DECLARED_UNIT", "OVERLAP_CONTRADICTION")
            links.append((a, b, certainty))
        if not edge.get("source_locators") or not edge["evidence"].strip():
            missing_evidence = True
    adjacency: dict[tuple[str, str], set[tuple[str, str]]] = {node: set() for node in nodes}
    for a, b, _ in links:
        adjacency[a].add(b); adjacency[b].add(a)
    components: list[dict[str, Any]] = []
    component_by_node: dict[tuple[str, str], int] = {}
    for node in sorted(nodes):
        if node in component_by_node:
            continue
        pending = [node]; members: set[tuple[str, str]] = set()
        while pending:
            current = pending.pop()
            if current in members:
                continue
            members.add(current); pending.extend(adjacency[current] - members)
        index = len(components)
        for member in members:
            component_by_node[member] = index
        potential = any(a in members and certainty != "VERIFIED" for a, _, certainty in links)
        components.append({"kind": "overlap_component", "nodes": [{"node_type": k, "node_id": v} for k, v in sorted(members)],
                           "protection": "POTENTIAL_OR_UNKNOWN" if potential else "RELATED", "independence_certified": False})
    for a, b in independent:
        require(component_by_node[a] != component_by_node[b], "OVERLAP_CONTRADICTION")
    require(not missing_evidence, "OVERLAP_EVIDENCE_MISSING", blocked=True)
    require(config.get("review_complete") is True, "OVERLAP_POLICY_UNKNOWN", blocked=True)
    return finish("overlap", packet, cast(dict[str, list[dict[str, Any]]], records), audit=components,
                  schemas=store)
