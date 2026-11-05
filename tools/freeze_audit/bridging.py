"""Outcome-blind full-versus-reduced Hallmark score comparisons."""
from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from tools.a_scoring import core as scoring_core
from tools.r_bridge import run_r

from .core import ROOT, StudyData, current_member


BRIDGING_SCRIPT = ROOT / "r/scripts/singscore.R"
BRIDGING_COLUMNS = (
    "hallmark_set", "n_members", "n_qualifying_studies", "common_gene_count",
    "common_gene_membership_sha256",
    "mean_missing_n", "mean_missing_r_median", "mean_missing_r_min", "mean_missing_sd_ratio_median",
    "singscore_missing_n", "singscore_missing_r_median", "singscore_missing_r_min", "singscore_missing_sd_ratio_median",
    "mean_common_n", "mean_common_r_median", "mean_common_r_min", "mean_common_sd_ratio_median",
    "singscore_common_n", "singscore_common_r_median", "singscore_common_r_min", "singscore_common_sd_ratio_median",
    "mean_targeted_n", "mean_targeted_r_median", "mean_targeted_r_min", "mean_targeted_sd_ratio_median",
    "singscore_targeted_n", "singscore_targeted_r_median", "singscore_targeted_r_min", "singscore_targeted_sd_ratio_median",
)
_COMPARISON_KINDS = ("missing", "common", "targeted")


def make_bridging_tables(
    studies: Sequence[StudyData],
    gene_sets: Mapping[str, Sequence[str]],
    proposed_by_cohort: Mapping[str, Mapping[str, str]],
    results_dir: Path | str,
    *,
    runner=None,
) -> tuple[list[dict[str, str | int | float]], list[dict[str, str | int]], str]:
    """Compare full available scores with three reduced membership definitions.

    The function accepts expression-only StudyData. It has no clinical table or
    outcome-field interface, so outcome columns cannot enter the calculation.
    """
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    all_non_targeted = [study for study in studies if not study.targeted]
    targeted_studies = [study for study in studies if study.targeted]
    if len(all_non_targeted) != 16 or len(targeted_studies) != 4:
        raise ValueError("The freeze bridge expects 16 non-targeted and 4 targeted studies")

    values_by_study = {
        study.cohort_id: _with_proposals(study, proposed_by_cohort.get(study.cohort_id, {}))
        for study in studies
    }
    signatures: OrderedDict[tuple[str, ...], str] = OrderedDict()
    found_by_set: dict[str, dict[str, set[str]]] = {}
    common_by_set: dict[str, tuple[str, ...]] = {}

    for set_name, original_members in gene_sets.items():
        members = tuple(dict.fromkeys(current_member(member, aliases) for member in original_members))
        found = {
            study.cohort_id: {member for member in members if member in values_by_study[study.cohort_id]}
            for study in all_non_targeted
        }
        found_by_set[set_name] = found
        qualified = [
            study for study in all_non_targeted
            if len(found[study.cohort_id]) * 10 >= len(members) * 9
        ]
        common = set.intersection(*(found[study.cohort_id] for study in qualified)) if qualified else set()
        common_tuple = tuple(sorted(common))
        common_by_set[set_name] = common_tuple

        for base in qualified:
            base_found = found[base.cohort_id]
            _register_signature(signatures, tuple(sorted(base_found)))
            for mask in all_non_targeted:
                if mask.cohort_id == base.cohort_id:
                    continue
                reduced = base_found - (set(members) - found[mask.cohort_id])
                if reduced:
                    _register_signature(signatures, tuple(sorted(reduced)))
            if common_tuple:
                _register_signature(signatures, common_tuple)
            for target in targeted_studies:
                target_subset = tuple(sorted(
                    member for member in members
                    if member in base_found and member in values_by_study[target.cohort_id]
                ))
                if target_subset:
                    _register_signature(signatures, target_subset)

    results_root = Path(results_dir).expanduser()
    scores: dict[tuple[str, str], list[float]] = {}
    for study in all_non_targeted:
        values = values_by_study[study.cohort_id]
        score_members = {
            signature: members
            for members, signature in signatures.items()
            if all(gene in values for gene in members)
        }
        if not score_members:
            continue
        for signature, members in score_members.items():
            scores[(study.cohort_id, signature)] = _mean_score(values, members)
        r_scores = _run_singscore(study, values, score_members, results_root, runner=runner)
        for signature, vector in r_scores.items():
            scores[(study.cohort_id, "R:" + signature)] = vector

    common_rows = [
        _common_row(set_name, common_by_set[set_name])
        for set_name in gene_sets
    ]
    common_by_name = {row["hallmark_set"]: row for row in common_rows}
    summaries: list[dict[str, str | int | float]] = []
    for set_name, original_members in gene_sets.items():
        members = tuple(dict.fromkeys(current_member(member, aliases) for member in original_members))
        found = found_by_set[set_name]
        qualified = [
            study for study in all_non_targeted
            if len(found[study.cohort_id]) * 10 >= len(members) * 9
        ]
        common_row = common_by_name[set_name]
        record: dict[str, str | int | float] = {
            "hallmark_set": set_name,
            "n_members": len(members),
            "n_qualifying_studies": len(qualified),
            "common_gene_count": int(common_row["n_common"]),
            "common_gene_membership_sha256": str(common_row["membership_sha256"]),
        }
        for kind in _COMPARISON_KINDS:
            for method in ("mean", "singscore"):
                stats = _comparison_stats(
                    kind=kind,
                    method=method,
                    members=members,
                    qualified=qualified,
                    studies=all_non_targeted,
                    targeted=targeted_studies,
                    found=found,
                    values_by_study=values_by_study,
                    common=common_by_set[set_name],
                    scores=scores,
                )
                prefix = f"{method}_{kind}"
                record[prefix + "_n"] = len(stats)
                record[prefix + "_r_median"] = _stat(stats, 0, "median")
                record[prefix + "_r_min"] = _stat(stats, 0, "min")
                record[prefix + "_sd_ratio_median"] = _stat(stats, 1, "median")
        summaries.append(record)

    return summaries, common_rows, _bridging_readme(all_non_targeted, targeted_studies)


def _comparison_stats(
    *,
    kind: str,
    method: str,
    members: Sequence[str],
    qualified: Sequence[StudyData],
    studies: Sequence[StudyData],
    targeted: Sequence[StudyData],
    found: Mapping[str, set[str]],
    values_by_study: Mapping[str, Mapping[str, tuple[float, ...]]],
    common: Sequence[str],
    scores: Mapping[tuple[str, str], list[float]],
) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for base in qualified:
        full_members = found[base.cohort_id]
        full_id = _signature_id(tuple(sorted(full_members)))
        full_key = "R:" + full_id if method == "singscore" else full_id
        full_score = scores.get((base.cohort_id, full_key))
        if full_score is None:
            continue

        reduced_memberships: list[tuple[str, ...]] = []
        if kind == "missing":
            for mask in studies:
                if mask.cohort_id == base.cohort_id:
                    continue
                retained = full_members - (set(members) - found[mask.cohort_id])
                if retained:
                    reduced_memberships.append(tuple(sorted(retained)))
        elif kind == "common":
            if common:
                reduced_memberships.append(tuple(common))
        else:
            for target in targeted:
                retained = tuple(sorted(
                    member for member in members
                    if member in full_members and member in values_by_study[target.cohort_id]
                ))
                if retained:
                    reduced_memberships.append(retained)

        for reduced_members in reduced_memberships:
            reduced_id = _signature_id(reduced_members)
            reduced_key = "R:" + reduced_id if method == "singscore" else reduced_id
            reduced_score = scores.get((base.cohort_id, reduced_key))
            if reduced_score is not None:
                result.append(_compare_vectors(full_score, reduced_score))
    return result


def _with_proposals(study: StudyData, additions: Mapping[str, str]) -> dict[str, tuple[float, ...]]:
    result = dict(study.gene_values)
    if not additions:
        return result
    raw_positions: dict[str, list[int]] = defaultdict(list)
    for index, source_id in enumerate(study.source_feature_ids):
        raw_positions[source_id.split(".", 1)[0]].append(index)
    for symbol, source_id in additions.items():
        if symbol in result:
            continue
        positions = raw_positions.get(source_id.split(".", 1)[0], [])
        if len(positions) == 1:
            result[symbol] = study.source_values[positions[0]]
    return result


def _register_signature(registry: OrderedDict[tuple[str, ...], str], members: tuple[str, ...]) -> str:
    signature = tuple(sorted(set(members)))
    if not signature:
        raise ValueError("Cannot score an empty reduced gene set")
    if signature not in registry:
        registry[signature] = _signature_id(signature)
    return registry[signature]


def _signature_id(members: Sequence[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(set(members))).encode("utf-8")).hexdigest()[:16]
    return "SIG_" + digest


def _mean_score(values: Mapping[str, tuple[float, ...]], members: Sequence[str]) -> list[float]:
    if not members:
        raise ValueError("Mean score requires at least one measured member")
    n_samples = len(values[members[0]])
    if any(len(values[gene]) != n_samples for gene in members):
        raise ValueError("Expression rows do not share a sample count")
    return [
        math.fsum(values[gene][index] for gene in members) / len(members)
        for index in range(n_samples)
    ]


def _run_singscore(study, values, score_members, results_root, *, runner=None) -> dict[str, list[float]]:
    import re

    results_root.mkdir(parents=True, exist_ok=True)
    genes = sorted(values)
    n_samples = study.n_samples
    matrix_path = results_root / f"{study.cohort_id}.expression.tsv"
    with matrix_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *[f"sample_{index + 1:06d}" for index in range(n_samples)]])
        for gene in genes:
            row = values[gene]
            if len(row) != n_samples:
                raise ValueError(f"Expression row length mismatch in {study.cohort_id}")
            writer.writerow([gene, *row])

    gmt_path = results_root / f"{study.cohort_id}.gene_sets.gmt"
    with gmt_path.open("w", newline="", encoding="utf-8") as stream:
        for signature, members in score_members.items():
            if not all(member in values for member in members):
                continue
            stream.write("\t".join([signature, "freeze audit", *members]) + "\n")
    input_hash = hashlib.sha256(matrix_path.read_bytes() + gmt_path.read_bytes()).hexdigest()[:12]
    result_dir = results_root / f"{study.cohort_id}-{input_hash}"
    result = run_r(
        BRIDGING_SCRIPT,
        {"expression": matrix_path, "gene_sets": gmt_path},
        {"expected_outputs": ["scores.tsv", "coverage.tsv"]},
        result_dir,
        runner=runner,
    )
    by_signature: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with result.outputs["scores.tsv"].open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            match = re.fullmatch(r"sample_(\d+)", row["patient_row"])
            if not match:
                raise ValueError("Synthetic singscore sample key changed")
            by_signature[row["unit"]].append((int(match.group(1)), float(row["value"])))
    return {
        signature: [value for _index, value in sorted(by_signature.get(signature, []))]
        for signature in score_members
    }


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return math.nan
    return _pearson(_average_ranks(left), _average_ranks(right))


def _average_ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        stop = index + 1
        while stop < len(ordered) and ordered[stop][1] == ordered[index][1]:
            stop += 1
        average = (index + 1 + stop) / 2.0
        for offset in range(index, stop):
            result[ordered[offset][0]] = average
        index = stop
    return result


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_ss = math.fsum(value * value for value in left_centered)
    right_ss = math.fsum(value * value for value in right_centered)
    if left_ss <= 0 or right_ss <= 0:
        return math.nan
    return math.fsum(a * b for a, b in zip(left_centered, right_centered)) / math.sqrt(left_ss * right_ss)


def _sample_sd(values: Sequence[float]) -> float:
    mean = math.fsum(values) / len(values)
    return math.sqrt(math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _compare_vectors(full: Sequence[float], reduced: Sequence[float]) -> tuple[float, float]:
    if len(full) != len(reduced) or len(full) < 2:
        return math.nan, math.nan
    full_sd = _sample_sd(full)
    ratio = _sample_sd(reduced) / full_sd if full_sd > 0 else math.nan
    return spearman(full, reduced), ratio


def _stat(stats: Sequence[tuple[float, float]], index: int, mode: str) -> float | str:
    values = [row[index] for row in stats if math.isfinite(row[index])]
    if not values:
        return "NA"
    return min(values) if mode == "min" else statistics.median(values)


def _common_row(set_name: str, members: Sequence[str]) -> dict[str, str | int]:
    canonical = tuple(sorted(set(members)))
    membership_bytes = ("\n".join(canonical) + ("\n" if canonical else "")).encode("utf-8")
    return {
        "hallmark_set": set_name,
        "n_common": len(canonical),
        "common_genes": ";".join(canonical),
        "membership_sha256": hashlib.sha256(membership_bytes).hexdigest(),
    }


def _bridging_readme(non_targeted: Sequence[StudyData], targeted: Sequence[StudyData]) -> str:
    def universe_rows(studies: Sequence[StudyData]) -> str:
        return "\n".join(
            f"- `{study.cohort_id}` — {study.cancer}, `{study.platform}`"
            for study in studies
        )

    return f"""# Hallmark full-versus-reduced score bridge

This is an outcome-blind comparison of expression scores. The study universe is
the following {len(non_targeted)} signed development cohorts whose platform is
not `targeted_rna` or `nanostring`:

{universe_rows(non_targeted)}

The following {len(targeted)} targeted studies define reduced gene subsets only:

{universe_rows(targeted)}

GSE176307 uses its hash-pinned Salmon TPM matrix on log2(TPM+1), the source
A-META scores. This audit reads every assay column directly; A-META keeps only
the assays linked to patients through an identity packet, which this
outcome-blind audit does not open.

For each Hallmark set, membership symbols are normalized through the frozen
alias table. A non-targeted study qualifies when at least 90% of the set's
members are available after the proposed, locally supported identifier
crosswalk. The full score in a qualifying study uses every set member available
in that study. Reduced scores use (1) the same study's full members minus the
members absent from each other non-targeted study, (2) the intersection of
members present in every qualifying non-targeted study, and (3) each targeted
study's measured members intersected with the full members in the qualifying
study. Empty subsets are omitted.

Both score methods use the same per-study expression values: the unweighted
arithmetic mean, and `singscore::simpleScore` from the repository's
`r/scripts/singscore.R`, with `rankGenes(..., tiesMethod = "min")`, the measured
gene rows as the background, `upSet` as the gene set, and
`knownDirection = TRUE`. No clinical field enters either score.

Each comparison is paired within one study. Spearman correlation uses average
ranks for ties; the SD ratio is sample SD(reduced) / sample SD(full). The
reported median and minimum are across all qualifying-study × reduced-pattern
comparisons for that set. Scores and synthetic sample-row keys are kept only
under ignored `results/`; the tracked tables contain aggregate summaries.

For one set, let `A(s)` be the unique Hallmark members available in study `s`
after frozen aliases and proposed, locally supported identifier mappings.
Qualifying studies are the non-targeted studies with `10 * |A(s)| >= 9 * N`,
where `N` is the unique set membership count. The common membership is the
sorted set intersection of `A(s)` across all qualifying studies; if there are
no qualifying studies, it is empty. The membership hash is SHA-256 of those
sorted symbols encoded as UTF-8, one symbol per line with a final newline (an
empty membership hashes the empty byte string). The common-gene TSV carries
the exact membership as well as its count and hash.
"""
