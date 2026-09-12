"""Stage graph, code identity and scientific gates for Paper B W1-W8."""

from __future__ import annotations

from pathlib import Path

CODE_PATHS = (
    "tools/b_workflow/__init__.py",
    "tools/b_workflow/__main__.py",
    "tools/b_workflow/config.py",
    "tools/b_workflow/io.py",
    "tools/b_workflow/plan.py",
    "tools/b_workflow/run.py",
    "tools/b_workflow/stages.py",
    "tools/b_acquire/__init__.py",
    "tools/b_acquire/__main__.py",
    "tools/b_acquire/acquire.py",
    "tools/b_cohort/__init__.py",
    "tools/b_cohort/__main__.py",
    "tools/b_cohort/build.py",
    "tools/b_features/__init__.py",
    "tools/b_features/__main__.py",
    "tools/b_features/provider.py",
    "tools/b_features/scores.py",
    "tools/b_formats/records.py",
    "tools/b_prediction/__init__.py",
    "tools/b_prediction/__main__.py",
    "tools/b_prediction/adapter.py",
    "tools/b_prediction/fold_develop.py",
    "tools/b_prediction/fold_evaluate.py",
    "tools/b_prediction/w5_bundle.py",
    "tools/b_report/__init__.py",
    "tools/b_report/__main__.py",
    "tools/b_report/report.py",
    "tools/b_acquire/audit.py",
    "tools/b_secondary/__init__.py",
    "tools/b_secondary/secondary.py",
)

STAGE_ORDER = ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8")

STAGE_DEPS = {
    "W1": [],
    "W2": ["W1"],
    "W3": ["W2"],
    "W4": ["W3"],
    "W5": ["W4"],
    "W6": ["W5"],
    "W7": ["W3", "W5", "W6"],
    "W8": ["W3", "W5", "W6", "W7"],
}

IMPLEMENTED = {"W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"}

STAGE_GATES = {
    "W1": ["versioned-config", "explicit-interpreter", "permitted-source-manifest"],
    "W2": ["exact-url", "expected-checksum-size", "no-silent-accession-substitution"],
    "W3": ["b-g2-annotations", "explicit-specimen-policy", "one-patient-evaluation-row"],
    "W4": ["E1-P", "E2-U", "E3-Q", "E4-specimen-linkage", "E6-precision", "explicit-fixture-policy"],
    "W5": [
        "fold-local-feature-state-interface",
        "tcga-only-development-ids",
        "signed-training-contract",
    ],
    "W6": [
        "frozen-training-artifacts",
        "evaluation-release-receipt",
        "independently-eligible-external-specimens",
    ],
    "W7": ["four-figure-contract", "no-manually-entered-values", "partial-apm-scope-labelled"],
    "W8": [
        "individually-frozen-secondary-contracts",
        "ayers-weights-not-inferred",
        "hope-scoring-not-inferred",
        "m0-m6-not-automatically-scored",
    ],
}


def descendants(stage_id: str) -> list[str]:
    found: list[str] = []
    for sid in STAGE_ORDER:
        if stage_id in STAGE_DEPS.get(sid, []) or any(d in found for d in STAGE_DEPS.get(sid, [])):
            if sid != stage_id:
                found.append(sid)
    # include transitive
    changed = True
    while changed:
        changed = False
        for sid in STAGE_ORDER:
            if sid in found or sid == stage_id:
                continue
            if any(dep == stage_id or dep in found for dep in STAGE_DEPS[sid]):
                found.append(sid)
                changed = True
    return [sid for sid in STAGE_ORDER if sid in found]


def stage_dir_name(stage_id: str) -> str:
    return stage_id
