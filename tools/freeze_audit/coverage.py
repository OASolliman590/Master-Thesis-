"""Hallmark study coverage tables and aggregate counts."""
from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

from tools.a_scoring import core as scoring_core

from .core import StudyData, current_member


COVERAGE_COLUMNS = (
    "cohort", "cancer", "platform", "feature_id", "hallmark_set", "n_total",
    "n_found_current", "n_found_proposed", "proposed_identifiers",
    "missing_members_current", "missing_members_proposed",
    "complete_current", "at_least_90pct_current", "complete", "at_least_90pct",
    "study_scope", "baseline_cancer", "usable_baseline",
)
SUMMARY_COLUMNS = (
    "hallmark_set", "population", "mapping", "n_studies", "complete_studies",
    "at_least_90pct_studies",
)
DISTRIBUTION_COLUMNS = (
    "population", "mapping", "coverage_rule", "study_count", "n_sets",
)


def make_coverage_rows(
    studies: Sequence[StudyData],
    gene_sets: Mapping[str, Sequence[str]],
    proposed_by_cohort: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str | int]]:
    aliases = scoring_core._frozen_aliases(str(scoring_core.ALIAS_TABLE_PATH))
    rows = []
    for study in studies:
        available = set(study.gene_values)
        additions = proposed_by_cohort.get(study.cohort_id, {})
        for set_name, members in gene_sets.items():
            missing_current = [
                member for member in members
                if current_member(member, aliases) not in available
            ]
            missing_proposed = [
                member for member in missing_current
                if current_member(member, aliases) not in additions
            ]
            proposed_ids = [
                f"{additions[current_member(member, aliases)]}=>{current_member(member, aliases)}"
                for member in missing_current
                if current_member(member, aliases) in additions
            ]
            n_current = len(members) - len(missing_current)
            n_proposed = len(members) - len(missing_proposed)
            total = len(members)
            rows.append({
                "cohort": study.cohort_id,
                "cancer": study.cancer,
                "platform": study.platform,
                "feature_id": study.feature_id,
                "hallmark_set": set_name,
                "n_total": total,
                "n_found_current": n_current,
                "n_found_proposed": n_proposed,
                "proposed_identifiers": ";".join(sorted(set(proposed_ids))),
                "missing_members_current": ";".join(missing_current),
                "missing_members_proposed": ";".join(missing_proposed),
                "complete_current": str(n_current == total).lower(),
                "at_least_90pct_current": str(n_current * 10 >= total * 9).lower(),
                "complete": str(n_proposed == total).lower(),
                "at_least_90pct": str(n_proposed * 10 >= total * 9).lower(),
                "study_scope": "targeted" if study.targeted else "whole_transcriptome",
                "usable_baseline": str(study.usable_baseline).lower(),
                "baseline_cancer": study.cancer if study.usable_baseline else "",
            })
    return rows


def make_coverage_summary(
    studies: Sequence[StudyData],
    coverage_rows: Sequence[Mapping[str, str | int]],
    gene_sets: Mapping[str, Sequence[str]],
) -> tuple[list[dict[str, str | int]], list[dict[str, str | int]]]:
    studies_by_id = {study.cohort_id: study for study in studies}
    non_targeted = {study.cohort_id for study in studies if not study.targeted}
    baseline_by_cancer: dict[str, set[str]] = {}
    for study in studies:
        if study.usable_baseline:
            baseline_by_cancer.setdefault(study.cancer, set()).add(study.cohort_id)

    populations: dict[str, set[str]] = {
        "all_20_signed_development": set(studies_by_id),
        "non_targeted_16": non_targeted,
    }
    populations.update({
        f"a_p2_baseline:{cancer}": cohort_ids
        for cancer, cohort_ids in sorted(baseline_by_cancer.items())
    })
    by_set_cohort = {
        (str(row["hallmark_set"]), str(row["cohort"])): row
        for row in coverage_rows
    }
    summaries: list[dict[str, str | int]] = []
    distribution: list[dict[str, str | int]] = []

    for set_name in gene_sets:
        for population, cohort_ids in populations.items():
            relevant = [
                by_set_cohort[(set_name, cohort_id)]
                for cohort_id in sorted(cohort_ids)
            ]
            for mapping in ("current", "proposed"):
                complete_col = "complete_current" if mapping == "current" else "complete"
                coverage_col = "at_least_90pct_current" if mapping == "current" else "at_least_90pct"
                summaries.append({
                    "hallmark_set": set_name,
                    "population": population,
                    "mapping": mapping,
                    "n_studies": len(relevant),
                    "complete_studies": sum(row[complete_col] == "true" for row in relevant),
                    "at_least_90pct_studies": sum(row[coverage_col] == "true" for row in relevant),
                })

    for population, cohort_ids in populations.items():
        relevant_sets = {
            set_name: [by_set_cohort[(set_name, cohort_id)] for cohort_id in sorted(cohort_ids)]
            for set_name in gene_sets
        }
        for mapping in ("current", "proposed"):
            complete_col = "complete_current" if mapping == "current" else "complete"
            coverage_col = "at_least_90pct_current" if mapping == "current" else "at_least_90pct"
            for rule, column in (("complete", complete_col), ("at_least_90pct", coverage_col)):
                counts = Counter(sum(row[column] == "true" for row in rows)
                                 for rows in relevant_sets.values())
                for study_count in range(len(cohort_ids) + 1):
                    distribution.append({
                        "population": population,
                        "mapping": mapping,
                        "coverage_rule": rule,
                        "study_count": study_count,
                        "n_sets": counts.get(study_count, 0),
                    })
    return summaries, distribution
