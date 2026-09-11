"""Run every Paper B component suite; zero tests or any skip is a failure."""
from pathlib import Path
import os
import sys
import tempfile
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    scratch = root / "tmp" / "paper_b_checks"
    scratch.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(scratch)
    for key in ("TMP", "TEMP", "BF1_TEST_TMP_ROOT", "BP1_TEST_TMP_ROOT", "B_WORKFLOW_TEST_TMP_ROOT"):
        os.environ[key] = str(scratch)
    suite = unittest.TestSuite()
    for name in (
        "b_formats",
        "b_gene_registry",
        "b_annotation_normalize",
        "b_prediction",
        "b_workflow",
        "b_report",
    ):
        # Separate loaders avoid silently missing non-package test directories.
        part = unittest.TestLoader().discover(str(root / "tests" / name))
        if part.countTestCases() == 0:
            raise RuntimeError(f"No tests found for {name}")
        suite.addTests(part)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print("Paper B acceptance FAILED: skipped tests are not a pass.", file=sys.stderr)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
