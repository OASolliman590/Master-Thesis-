"""Inputs fixed by the signed 4 Nov 2026 numerical freeze."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
FREEZE_DIR = ROOT / "specs/amendments/2026-11-04-numerical-freeze"
HALLMARK_GMT = FREEZE_DIR / "hallmark_2026.1.Hs.gmt"
REACTOME_GMT = FREEZE_DIR / "reactome_2026.1.Hs.gmt"
COMMON_GENE_TABLE = ROOT / "docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv"
IDENTIFIER_PROPOSALS = ROOT / "docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv"
FROZEN_ALIASES = ROOT / "specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv"

HALLMARK_SHA256 = "01f390fb123ac08c75874030233a4252122c9d7f97c1e173366b587438f57ad5"
REACTOME_SHA256 = "4e1b4a6231ccb812985bffef6b9991bc54745c1b72bbcbcd2d132d5188b006bb"
COMMON_GENE_TABLE_SHA256 = "1ce5611a406b98d96016eed697ccaf2642df847ca0907fc7f877da65b9d53e51"
IDENTIFIER_PROPOSALS_SHA256 = "7f90583f0548cafecd57a3a059c087ea9d3b945867e09262fec3c23e13287d84"
IFNG_MEMBERSHIP_SHA256 = "51d3b96ed77916fc7da2e2dfcde2fbdee4a8dc3f3a2c60f469050889bc4cf714"

FROZEN_GENE_SETS = {
    "hallmark": (HALLMARK_GMT, HALLMARK_SHA256),
    "reactome": (REACTOME_GMT, REACTOME_SHA256),
}


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_sha256(path: Path | str, expected: str, label: str) -> str:
    actual = file_sha256(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch")
    return actual


def frozen_gene_set_path(collection: str = "hallmark") -> Path:
    try:
        path, expected = FROZEN_GENE_SETS[collection.casefold()]
    except KeyError:
        raise ValueError("Gene-set collection must be hallmark or reactome") from None
    require_sha256(path, expected, f"Frozen {collection} GMT")
    return path


def identify_frozen_gene_set(path: Path | str, *, allowed: tuple[str, ...] | None = None) -> str:
    actual = file_sha256(path)
    candidates = FROZEN_GENE_SETS.items()
    for collection, (_frozen_path, expected) in candidates:
        if actual == expected and (allowed is None or collection in allowed):
            return collection
    raise ValueError("Gene-set input does not match a signed frozen GMT hash")


def read_gmt(path: Path | str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    with Path(path).open(newline="", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = next(csv.reader([line.rstrip("\r\n")], delimiter="\t"))
            if len(fields) < 3 or not fields[0] or any(not value for value in fields[2:]):
                raise ValueError(f"Malformed GMT row {line_number}")
            if fields[0] in result or len(fields[2:]) != len(set(fields[2:])):
                raise ValueError(f"Invalid or duplicate membership at GMT row {line_number}")
            result[fields[0]] = tuple(fields[2:])
    if not result:
        raise ValueError("Gene-set input is empty")
    return result


def read_hallmark_gene_sets(
    path: Path | str | None = None,
    *,
    aliases: Mapping[str, str] | None = None,
    test_only: bool = False,
) -> dict[str, tuple[str, ...]]:
    selected = Path(path) if path is not None else HALLMARK_GMT
    if not test_only:
        require_sha256(selected, HALLMARK_SHA256, "Frozen Hallmark GMT")
    gene_sets = read_gmt(selected)
    if not test_only:
        if len(gene_sets) != 50:
            raise ValueError("The frozen Hallmark GMT must contain exactly 50 sets")
        if "HALLMARK_INTERFERON_GAMMA_RESPONSE" not in gene_sets:
            raise ValueError("The frozen Hallmark GMT is missing IFN-gamma")
        if _json_membership_sha256(gene_sets["HALLMARK_INTERFERON_GAMMA_RESPONSE"]) != IFNG_MEMBERSHIP_SHA256:
            raise ValueError("Frozen IFN-gamma membership hash mismatch")
    if aliases:
        gene_sets = {name: _map_members(members, aliases) for name, members in gene_sets.items()}
    return gene_sets


def read_common_gene_sets(
    path: Path | str = COMMON_GENE_TABLE,
    *,
    aliases: Mapping[str, str] | None = None,
) -> dict[str, tuple[str, ...]]:
    require_sha256(path, COMMON_GENE_TABLE_SHA256, "Frozen Hallmark common-gene table")
    result: dict[str, tuple[str, ...]] = {}
    with Path(path).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            name = row["hallmark_set"]
            members = tuple(row["common_genes"].split(";"))
            if not name or not members or any(not member for member in members):
                raise ValueError("Common-gene table contains an empty set")
            if len(members) != int(row["n_common"]) or tuple(sorted(set(members))) != members:
                raise ValueError(f"Common-gene membership is malformed for {name}")
            if membership_sha256(members) != row["membership_sha256"]:
                raise ValueError(f"Common-gene membership hash mismatch for {name}")
            if name in result:
                raise ValueError("Common-gene table contains a duplicate Hallmark set")
            result[name] = _map_members(members, aliases) if aliases else members
    if len(result) != 50:
        raise ValueError("The frozen common-gene table must contain exactly 50 sets")
    return result


def read_identifier_proposals(path: Path | str = IDENTIFIER_PROPOSALS) -> list[dict[str, str]]:
    require_sha256(path, IDENTIFIER_PROPOSALS_SHA256, "Hallmark identifier proposals")
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != 23 or any(not row.get("source_id") or not row.get("registry_symbol") for row in rows):
        raise ValueError("Signed Hallmark identifier proposals must contain 23 complete mappings")
    if len({row["source_id"] for row in rows}) != len(rows):
        raise ValueError("Signed Hallmark identifier proposals contain duplicate source IDs")
    return rows


def membership_sha256(members: tuple[str, ...] | list[str]) -> str:
    payload = ("\n".join(members) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_membership_sha256(members: tuple[str, ...] | list[str]) -> str:
    payload = json.dumps(members, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _map_members(members: tuple[str, ...], aliases: Mapping[str, str]) -> tuple[str, ...]:
    mapped = tuple(aliases.get(member, member) for member in members)
    if len(mapped) != len(set(mapped)):
        raise ValueError("Frozen aliases collapse duplicate genes within a set")
    return mapped


def read_frozen_aliases(path: Path | str = FROZEN_ALIASES) -> dict[str, str]:
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    mapping = {row["source_symbol"]: row["registry_symbol"] for row in rows}
    if len(mapping) != len(rows) or any(not key or not value for key, value in mapping.items()):
        raise ValueError("Frozen gene aliases are malformed")
    return mapping
