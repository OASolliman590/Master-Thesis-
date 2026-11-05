"""Run the outcome-blind numerical-freeze evidence audits."""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from tools.a_scoring import core as scoring_core

from .bridging import BRIDGING_COLUMNS, make_bridging_tables
from .core import ROOT, load_studies, read_hallmark_sets
from .coverage import (
    COVERAGE_COLUMNS,
    DISTRIBUTION_COLUMNS,
    SUMMARY_COLUMNS,
    make_coverage_rows,
    make_coverage_summary,
)
from .identifiers import audit_identifier_gaps


COHORTS_DIR = ROOT / "docs/cohorts"
RESULTS_DEFAULT = ROOT / "results/freeze_audit"
IDENTIFIER_COLUMNS = (
    "cohort", "cancer", "platform", "feature_id", "hallmark_set", "member",
    "classification", "source_rows", "candidate_source_id", "mapping_candidate",
    "mapping_status", "evidence",
)
PROPOSAL_COLUMNS = ("source_id", "registry_symbol", "reason")
COMMON_COLUMNS = ("hallmark_set", "n_common", "common_genes", "membership_sha256")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.freeze_audit")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("coverage", "identifiers", "bridging"):
        sub = commands.add_parser(name)
        sub.add_argument("--runtime", type=Path, default=None)
        sub.add_argument("--results-dir", type=Path, default=RESULTS_DEFAULT)
    args = parser.parse_args(argv)

    runtime = args.runtime or Path(os.environ.get("THESIS_RUNTIME", scoring_core._runtime_path(None)))
    studies, gene_sets = load_studies(runtime)
    _assert_study_universe(studies)
    audit_rows, proposals, proposed_by_cohort = audit_identifier_gaps(
        studies, gene_sets, runtime=runtime
    )

    if args.command == "coverage":
        rows = make_coverage_rows(studies, gene_sets, proposed_by_cohort)
        summary, distribution = make_coverage_summary(studies, rows, gene_sets)
        _write_tsv(COHORTS_DIR / "HALLMARK_COVERAGE.tsv", rows, COVERAGE_COLUMNS)
        _write_tsv(COHORTS_DIR / "HALLMARK_COVERAGE_SUMMARY.tsv", summary, SUMMARY_COLUMNS)
        _write_tsv(COHORTS_DIR / "HALLMARK_COVERAGE_DISTRIBUTION.tsv", distribution, DISTRIBUTION_COLUMNS)
        print(f"cohorts={len(studies)} sets={len(gene_sets)} rows={len(rows)} proposals={len(proposals)}")
        print("outputs=docs/cohorts/HALLMARK_COVERAGE.tsv,docs/cohorts/HALLMARK_COVERAGE_SUMMARY.tsv,docs/cohorts/HALLMARK_COVERAGE_DISTRIBUTION.tsv")
    elif args.command == "identifiers":
        _write_tsv(COHORTS_DIR / "HALLMARK_IDENTIFIER_AUDIT.tsv", audit_rows, IDENTIFIER_COLUMNS)
        _write_tsv(COHORTS_DIR / "HALLMARK_IDENTIFIER_PROPOSALS.tsv", proposals, PROPOSAL_COLUMNS)
        classes = sorted({row["classification"] for row in audit_rows})
        print(f"gap_rows={len(audit_rows)} proposals={len(proposals)} classes={','.join(classes)}")
        print("outputs=docs/cohorts/HALLMARK_IDENTIFIER_AUDIT.tsv,docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv")
    else:
        summaries, common_rows, readme = make_bridging_tables(
            studies,
            gene_sets,
            proposed_by_cohort,
            args.results_dir / "bridging",
        )
        _write_tsv(COHORTS_DIR / "HALLMARK_BRIDGING.tsv", summaries, BRIDGING_COLUMNS)
        _write_tsv(COHORTS_DIR / "HALLMARK_BRIDGING_COMMON_GENES.tsv", common_rows, COMMON_COLUMNS)
        (COHORTS_DIR / "HALLMARK_BRIDGING_README.md").write_text(readme, encoding="utf-8")
        print(f"sets={len(summaries)} common_memberships={len(common_rows)}")
        print("outputs=docs/cohorts/HALLMARK_BRIDGING.tsv,docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv,docs/cohorts/HALLMARK_BRIDGING_README.md")
    return 0


def _assert_study_universe(studies) -> None:
    if len(studies) != 20 or len({study.cohort_id for study in studies}) != 20:
        raise ValueError("Expected the 20 signed development cohorts")
    if sum(not study.targeted for study in studies) != 16:
        raise ValueError("Expected 16 non-targeted signed development cohorts")
    if sum(study.targeted for study in studies) != 4:
        raise ValueError("Expected four targeted signed development cohorts")


def _write_tsv(path: Path, rows: Iterable[Mapping[str, object]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})


if __name__ == "__main__":
    raise SystemExit(main())
