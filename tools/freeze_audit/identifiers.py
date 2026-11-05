"""Local-reference identifier-gap classification and review proposals."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from tools.a_meta import features as a_features
from tools.a_scoring import core as scoring_core

from .core import G026_GTF_SHA256, StudyData, current_member


GAP_CLASSES = (
    "alias-resolvable",
    "NCBI synonym",
    "old Ensembl ID",
    "retired or replaced Entrez ID",
    "spreadsheet date mangling",
    "row present but dropped by our pipeline",
    "truly absent",
)
_SPREADSHEET_COHORTS = {"braun2020", "gse165278"}
_MONTHS = {
    "JAN": "JAN", "FEB": "FEB", "MAR": "MAR", "APR": "APR",
    "MAY": "MAY", "JUN": "JUN", "JUL": "JUL", "AUG": "AUG",
    "SEP": "SEP", "OCT": "OCT", "NOV": "NOV", "DEC": "DEC",
}


def audit_identifier_gaps(
    studies: Sequence[StudyData],
    gene_sets: Mapping[str, Sequence[str]],
    *,
    runtime: Path | str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]]]:
    """Classify every currently missing set member and collect unambiguous proposals."""
    reference = a_features._gene_reference(str(scoring_core._runtime_path(runtime).resolve()))
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    addendum = a_features._gene_alias_addendum()
    synonym_targets = _invert_synonyms(reference["synonyms"])
    real_names = set(reference["by_id"].values()) | set(synonym_targets)
    normalized_real_names = {_normalize_name(name) for name in real_names}
    audit_rows: list[dict[str, str]] = []
    proposal_candidates: list[dict[str, str]] = []
    proposed_by_cohort: dict[str, dict[str, str]] = defaultdict(dict)

    for study in studies:
        available = set(study.gene_values)
        identifier_index = _identifier_index(study, aliases, reference)
        for set_name, members in gene_sets.items():
            for member in members:
                canonical = current_member(member, aliases)
                if canonical in available:
                    continue
                gap = _classify_gap(
                    study=study,
                    set_name=set_name,
                    member=member,
                    canonical=canonical,
                    aliases=aliases,
                    addendum=addendum,
                    reference=reference,
                    synonym_targets=synonym_targets,
                    real_names=real_names,
                    normalized_real_names=normalized_real_names,
                    identifier_index=identifier_index,
                )
                audit_rows.append(gap)
                if gap["mapping_status"] == "proposed":
                    proposal_candidates.append({
                        "source_id": gap["candidate_source_id"].split(".", 1)[0],
                        "registry_symbol": gap["mapping_candidate"],
                        "reason": gap["proposal_reason"],
                        "cohort": study.cohort_id,
                    })

    global_source_targets: dict[str, set[str]] = defaultdict(set)
    for row in proposal_candidates:
        global_source_targets[row["source_id"]].add(row["registry_symbol"])
    safe_pairs = {
        (source, next(iter(targets)))
        for source, targets in global_source_targets.items()
        if len(targets) == 1
    }
    proposals_by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in proposal_candidates:
        pair = (row["source_id"], row["registry_symbol"])
        if pair in safe_pairs:
            proposals_by_pair[pair].add(row["cohort"])
        else:
            row["mapping_status"] = "unresolved: source identifier has multiple targets"

    proposals = []
    for (source_id, symbol), cohorts in sorted(proposals_by_pair.items()):
        if addendum.get(source_id.split(".", 1)[0]) == symbol:
            continue
        reason = _proposal_reason(source_id, symbol, sorted(cohorts), studies)
        proposals.append({
            "source_id": source_id,
            "registry_symbol": symbol,
            "reason": reason,
        })
        for study in studies:
            if study.cohort_id not in cohorts:
                continue
            proposed_by_cohort[study.cohort_id][symbol] = source_id

    # If a global source-id conflict invalidated a candidate, it must not remain
    # marked proposed in the per-gap evidence table.
    for row in audit_rows:
        pair = (row["candidate_source_id"].split(".", 1)[0], row["mapping_candidate"])
        if row["mapping_status"] == "proposed" and pair not in safe_pairs:
            row["mapping_status"] = "unresolved: one-to-many mapping refused"

    return audit_rows, proposals, dict(proposed_by_cohort)


def _classify_gap(
    *,
    study: StudyData,
    set_name: str,
    member: str,
    canonical: str,
    aliases: Mapping[str, str],
    addendum: Mapping[str, str],
    reference: Mapping,
    synonym_targets: Mapping[str, set[str]],
    real_names: set[str],
    normalized_real_names: set[str] | None = None,
    identifier_index: Mapping | None = None,
) -> dict[str, str]:
    index = identifier_index or _identifier_index(study, aliases, reference)

    alias_rows = index["alias_rows"].get(canonical, [])
    if alias_rows:
        source_id, unique = _single_source(alias_rows, canonical)
        return _gap_row(
            study, set_name, member, "alias-resolvable", alias_rows, canonical,
            "",
            "frozen alias table maps an observed source symbol to the missing member",
            "unresolved: frozen alias requires review",
        )

    pipeline_rows = index["resolved_rows"].get(canonical, [])
    if pipeline_rows:
        source_ids = sorted({source_id for source_id in pipeline_rows})
        return _gap_row(
            study, set_name, member, "row present but dropped by our pipeline",
            source_ids, canonical, "", "a_meta canonicalized a cohort row to this member, but the output gene table did not retain it",
            "unresolved: pipeline drop requires review",
        )

    row_ids = sorted(set(index["exact_rows"].get(member, ())) |
                     set(index["exact_rows"].get(canonical, ())))
    if row_ids:
        return _gap_row(
            study, set_name, member, "row present but dropped by our pipeline",
            row_ids, canonical, "",
            "exact member symbol is present in cohort feature rows but absent from the a_meta gene table",
            "unresolved: pipeline drop requires review",
        )

    grouped_rows = index["grouped_rows"].get(member, ())
    if grouped_rows:
        source_ids = sorted({source_id for source_id, _group in grouped_rows})
        group_names = sorted({group for _source_id, group in grouped_rows})
        return _gap_row(
            study, set_name, member, "row present but dropped by our pipeline",
            source_ids, "", "",
            "member occurs inside a comma-joined source feature label (" + ";".join(group_names) + "); the combined row has no one-to-one gene mapping",
            "unresolved: grouped source row is not one-to-one",
        )

    synonym_rows = [
        (source_id, synonym)
        for synonym in reference["synonyms"].get(canonical, ())
        for source_id in index["source_names"].get(synonym, ())
    ]
    if synonym_rows:
        source_ids = sorted({source_id for source_id, _ in synonym_rows})
        synonym_conflict = any(
            synonym_targets.get(synonym, set()) != {canonical}
            for _source_id, synonym in synonym_rows
        )
        source_id, unique = _single_source([source_id for source_id, _ in synonym_rows], canonical)
        safe = unique and not synonym_conflict
        return _gap_row(
            study, set_name, member, "NCBI synonym", source_ids,
            canonical if safe else "",
            source_id if safe else "",
            "NCBI gene_info synonym observed in cohort row names" + (
                "; synonym is ambiguous across official symbols" if synonym_conflict else ""
            ),
            "proposed" if safe else "unresolved: one-to-many mapping refused",
            proposal_reason="NCBI gene_info gives a unique synonym-to-symbol mapping" if safe else "",
        )

    ensembl_rows = index["ensembl_rows"].get(canonical, [])
    if ensembl_rows:
        observed_ids = [source_id for source_id, _ in ensembl_rows]
        source_ids = sorted({source_id for source_id, _ in ensembl_rows})
        source_id, unique = _single_source(observed_ids, canonical)
        # Require the local GTF to assign this ID to exactly one symbol.
        source_mapping_unique = unique and all(
            index["ensembl_targets"].get(source_id.split(".", 1)[0], set()) == {canonical}
            for source_id in source_ids
        )
        evidence = f"local recount3 GTF {G026_GTF_SHA256}; Ensembl gene_id maps to gene_name {canonical}"
        return _gap_row(
            study, set_name, member, "old Ensembl ID", source_ids,
            canonical if source_mapping_unique else "",
            source_id if source_mapping_unique else "", evidence,
            "proposed" if source_mapping_unique else "unresolved: one-to-many mapping refused",
            proposal_reason="local GTF uniquely maps an observed Ensembl row to this gene" if source_mapping_unique else "",
        )

    entrez_rows = index["entrez_rows"].get(canonical, [])
    if entrez_rows:
        observed_ids = [source_id for source_id, _ in entrez_rows]
        source_ids = sorted({source_id for source_id, _ in entrez_rows})
        source_id, unique = _single_source(observed_ids, canonical)
        mapping_unique = unique and all(symbols == {canonical} for _source, symbols in entrez_rows)
        return _gap_row(
            study, set_name, member, "retired or replaced Entrez ID", source_ids,
            canonical if mapping_unique else "",
            source_id if mapping_unique else "",
            "local NCBI gene_history links the retired identifier to a current gene_info symbol",
            "proposed" if mapping_unique else "unresolved: one-to-many mapping refused",
            proposal_reason="local NCBI gene_history uniquely replaces this Entrez ID" if mapping_unique else "",
        )

    date_rows = []
    if study.cohort_id in _SPREADSHEET_COHORTS:
        date_rows = _date_mangled_sources(
            member,
            index["normalized_source_rows"],
            normalized_real_names or {_normalize_name(name) for name in real_names},
        )
    if date_rows:
        source_id, unique = _single_source(date_rows, canonical)
        return _gap_row(
            study, set_name, member, "spreadsheet date mangling", date_rows,
            canonical if unique else "",
            source_id if unique else "",
            "spreadsheet-derived cohort row has the unique month/day rendering of this local NCBI symbol",
            "proposed" if unique else "unresolved: one-to-many mapping refused",
            proposal_reason="reversible date rendering uniquely identifies the local NCBI gene symbol" if unique else "",
        )

    references = [f"cohort row names ({study.expression_rows} features)", "pinned NCBI gene_info"]
    if study.gtf_symbols:
        references.append(f"local GTF {G026_GTF_SHA256}")
    if study.gene_history:
        references.append("local NCBI gene_history")
    return _gap_row(
        study, set_name, member, "truly absent", [], "", "",
        "no one-to-one local row or reference mapping; checked " + "; ".join(references),
        "unresolved: remains absent",
    )


def _gap_row(
    study: StudyData,
    set_name: str,
    member: str,
    classification: str,
    source_ids: Iterable[str],
    candidate: str,
    candidate_source_id: str,
    evidence: str,
    status: str,
    *,
    proposal_reason: str = "",
) -> dict[str, str]:
    return {
        "cohort": study.cohort_id,
        "cancer": study.cancer,
        "platform": study.platform,
        "feature_id": study.feature_id,
        "hallmark_set": set_name,
        "member": member,
        "classification": classification,
        "source_rows": ",".join(sorted(set(source_ids))),
        "candidate_source_id": candidate_source_id,
        "mapping_candidate": candidate,
        "mapping_status": status,
        "evidence": evidence,
        "proposal_reason": proposal_reason,
    }


def _invert_synonyms(synonyms: Mapping[str, Iterable[str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for symbol, values in synonyms.items():
        result[symbol].add(symbol)
        for value in values:
            if value and value != "-":
                result[value].add(symbol)
    return dict(result)


def _identifier_index(study: StudyData, aliases: Mapping[str, str], reference: Mapping) -> dict:
    """Index a cohort's source identifiers once for bounded gap lookups."""
    alias_rows: dict[str, list[str]] = defaultdict(list)
    resolved_rows: dict[str, list[str]] = defaultdict(list)
    source_names: dict[str, list[str]] = defaultdict(list)
    exact_rows: dict[str, list[str]] = defaultdict(list)
    normalized_source_rows: dict[str, list[str]] = defaultdict(list)
    grouped_rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    ensembl_targets: dict[str, set[str]] = defaultdict(set)
    ensembl_rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    entrez_rows: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    by_id = reference["by_id"]

    for source_id, raw_symbol, resolved in zip(
        study.source_feature_ids,
        study.source_symbols,
        study.canonical_source_symbols,
    ):
        if raw_symbol in aliases:
            alias_rows[aliases[raw_symbol]].append(source_id)
        normalized_resolved = _alias_normalize(resolved, aliases)
        if normalized_resolved:
            resolved_rows[normalized_resolved].append(source_id)
        for name in {raw_symbol, str(resolved or "")}:
            if name:
                source_names[name].append(source_id)
        exact_rows[raw_symbol].append(source_id)
        normalized_source_rows[_normalize_name(raw_symbol)].append(source_id)
        grouped = tuple(part.strip() for part in raw_symbol.split(",") if part.strip())
        if len(grouped) > 1:
            for name in grouped:
                grouped_rows[name].append((source_id, raw_symbol))

    for source_id in study.source_feature_ids:
        base = source_id.split(".", 1)[0]
        if base.startswith("ENSG"):
            targets = {
                _alias_normalize(symbol, aliases)
                for symbol in study.gtf_symbols.get(base, ())
            }
            targets.discard("")
            ensembl_targets[base].update(targets)
            for target in targets:
                ensembl_rows[target].append((source_id, target))
        if source_id.isdigit():
            symbols = {
                _alias_normalize(by_id.get(gene_id, ""), aliases)
                for gene_id in study.gene_history.get(source_id, ())
            }
            symbols.discard("")
            for symbol in symbols:
                entrez_rows[symbol].append((source_id, symbols))

    return {
        "alias_rows": alias_rows,
        "resolved_rows": resolved_rows,
        "source_names": source_names,
        "exact_rows": exact_rows,
        "grouped_rows": grouped_rows,
        "normalized_source_rows": normalized_source_rows,
        "ensembl_targets": ensembl_targets,
        "ensembl_rows": ensembl_rows,
        "entrez_rows": entrez_rows,
    }


def _alias_normalize(symbol: object, aliases: Mapping[str, str]) -> str:
    raw = str(symbol or "")
    return aliases.get(raw, raw)


def _single_source(source_ids: Iterable[str], target: str) -> tuple[str, bool]:
    ids = list(source_ids)
    return (ids[0], True) if len(ids) == 1 and bool(target) else ("", False)


def _normalize_name(value: str) -> str:
    return re.sub(r"[\s,_]", "", value).casefold()


def _date_mangled_sources(
    member: str,
    normalized_source_rows: Mapping[str, Sequence[str]],
    normalized_real_names: set[str],
) -> list[str]:
    forms = {_normalize_name(form) for form in _date_forms(member)}
    forms.difference_update(normalized_real_names)
    return sorted({
        source_id
        for form in forms
        for source_id in normalized_source_rows.get(form, ())
    })


def _is_date_mangled_member(
    raw: str,
    member: str,
    real_names: set[str],
    normalized_real_names: set[str] | None = None,
) -> bool:
    raw_key = _normalize_name(raw)
    normalized_real_names = normalized_real_names or {
        _normalize_name(name) for name in real_names
    }
    if raw in real_names or raw_key in normalized_real_names:
        return False
    return raw_key in {
        _normalize_name(form)
        for form in _date_forms(member)
    }


def _date_forms(member: str) -> set[str]:
    target = member.upper()
    match = re.fullmatch(r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEPT|SEP|OCT|NOV|DEC)(\d+)", target)
    if not match:
        return set()
    month, day = match.groups()
    month = {"MARCH": "MAR", "SEPT": "SEP"}.get(month, month)
    day_number = int(day)
    return {
        f"{month}-{day_number}", f"{month}{day_number}",
        f"{day_number}-{month}", f"{day_number}{month}",
    }


def _proposal_reason(source_id: str, symbol: str, cohorts: list[str], studies: Sequence[StudyData]) -> str:
    references = []
    for study in studies:
        if study.cohort_id not in cohorts:
            continue
        base = source_id.split(".", 1)[0]
        if base in study.gtf_symbols:
            references.append(f"local GTF {G026_GTF_SHA256}")
        elif source_id in study.gene_history:
            references.append("local NCBI gene_history")
        else:
            references.append("pinned NCBI gene_info synonyms")
    evidence = ", ".join(sorted(set(references))) or "local identifier evidence"
    return f"{evidence} uniquely maps {source_id} to {symbol}; observed in {','.join(cohorts)}"
