"""CLI boundary tests for B-F1 format inspection."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from subprocess import PIPE, TimeoutExpired, run
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
CLI = ["-m", "tools.b_formats", "inspect"]
RESEARCH_ROOT = REPO_ROOT / "docs" / "research" / "B_readiness"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
TEST_TIMEOUT_SEC = 30


def _tmpdir_root() -> Path:
    explicit = os.environ.get("BF1_TEST_TMP_ROOT")
    return Path(explicit) if explicit else Path(tempfile.gettempdir())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _run_command(args, output_path: Path, *, cwd: Path | None = None) -> tuple[int, str, str]:
    command = [PYTHON, *CLI, *args, "--output", str(output_path)]
    try:
        proc = run(
            command,
            cwd=str(cwd or REPO_ROOT),
            check=False,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            timeout=TEST_TIMEOUT_SEC,
        )
    except TimeoutExpired:
        raise AssertionError(f"timeout running command: {' '.join(command)}")
    return proc.returncode, proc.stdout, proc.stderr


def _run_fixture(
    fmt: str,
    input_path: Path,
    sha: str,
    completeness: str,
    tmpdir: Path,
    *,
    output_name: str,
    extra_input: list[str] | None = None,
) -> tuple[int, str, str, Path]:
    args = [
        "--format",
        fmt,
        "--input",
        str(input_path),
        "--source-sha256",
        sha,
        "--completeness",
        completeness,
    ]
    if extra_input:
        args.extend(extra_input)
    output_path = tmpdir / output_name
    code, stdout, stderr = _run_command(args, output_path)
    return code, stdout, stderr, output_path


class TestBFormatInspectionCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = _tmpdir_root()
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def test_real_fixtures_all_formats(self):
        real_cases = [
            {
                "format": "tcga-star-expression",
                "path": RESEARCH_ROOT / "tcga_a4980c9c-6c37-46da-8db3-c60a1c29081f.tsv",
                "sha": "8339cb0b1bf80236a7fff6ec9ee18b5d8779a35fa32adf4f43c20e2495fd6d2c",
                "completeness": "full",
                "check": lambda s: (
                    self.assertEqual(s["format_summary"]["row_count"], 60664),
                    self.assertEqual(s["format_summary"]["summary_record_count"], 4),
                    self.assertEqual(s["format_summary"]["identifier_count"], 60660),
                    self.assertIn("summary_structural_missing_count", s["format_summary"]),
                    self.assertIn("summary_finite_value_count", s["format_summary"]),
                ),
            },
            {
                "format": "tcga-methylation-beta",
                "path": RESEARCH_ROOT / "tcga_9cebe5e9-f133-479a-b0f6-e91d8b06ab38.tsv",
                "sha": "11d9fa63a4b9b69b9131ebdb535501fe221751cfe172b8295526d70003d40cf7",
                "completeness": "full",
                "check": lambda s: (
                    self.assertEqual(s["format_summary"]["row_count"], 486427),
                    self.assertEqual(s["format_summary"]["identifier_count"], 486427),
                    self.assertEqual(s["format_summary"]["finite_value_count"], 417183),
                    self.assertEqual(s["format_summary"]["missing_value_count"], 69244),
                ),
            },
            {
                "format": "cpc-expression",
                "path": RESEARCH_ROOT / "GSE107299_processed_prefix.tsv",
                "sha": "5a9aaaacb96c4548083bf680aaf4cef6c2a61a8ef83464da5278910318d4e8d1",
                "completeness": "bounded-prefix",
                "check": lambda s: (
                    self.assertEqual(s["format_summary"]["row_count"], 194),
                    self.assertEqual(s["format_summary"]["sample_count"], 213),
                    self.assertEqual(s["format_summary"]["annotation_field_count"], 7),
                ),
            },
            {
                "format": "cpc-methylation",
                "path": RESEARCH_ROOT / "GSE107298_processed_prefix.tsv",
                "sha": "d2539ed67b6bae02c2abeb7cbcd0b4d4ef5d51acf164eb571d2555743b249f7a",
                "completeness": "bounded-prefix",
                "check": lambda s: (
                    self.assertEqual(s["format_summary"]["row_count"], 77),
                    self.assertEqual(s["format_summary"]["sample_pair_count"], 394),
                    self.assertEqual(s["format_summary"]["sample_code_count"], 286),
                    self.assertTrue(s["format_summary"]["header_repaired"]),
                ),
            },
        ]

        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            for idx, case in enumerate(real_cases):
                output_name = f"summary_real_{idx}.json"
                code, _, stderr, output = _run_fixture(
                    case["format"],
                    case["path"],
                    case["sha"],
                    case["completeness"],
                    tmpdir,
                    output_name=output_name,
                )
                self.assertEqual(code, 0, stderr)
                summary = _read_summary(output)
                self.assertEqual(summary["format"], case["format"])
                self.assertEqual(summary["supplied_completeness"], case["completeness"])
                self.assertEqual(summary["source_sha256"], case["sha"])
                self.assertEqual(summary["actual_source_sha256"], case["sha"])
                self.assertFalse(summary["format_summary"]["header_repaired"] and summary["format"] == "tcga-star-expression")
                case["check"](summary)
                oracle = _read_summary(REPO_ROOT / "docs/validation/B_formats/real_summaries_expected.json")
                for key, expected in oracle[case["format"]].items():
                    self.assertEqual(summary["format_summary"][key], expected, key)
                manifest = _read_summary(REPO_ROOT / "docs/validation/B_formats/fixture_manifest.json")
                entry = manifest["formats"][case["format"]]
                self.assertEqual(entry["source_sha256"], case["sha"])
                self.assertEqual(REPO_ROOT / entry["path"], case["path"])

    def test_argument_errors_and_hash_validation(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            valid = FIXTURE_ROOT / "synthetic_tcga_methylation.tsv"
            sha = _sha256(valid)
            output = tmpdir / "summary.json"

            code, _, _ = _run_command(
                [
                    "--format",
                    "tcga-methylation-beta",
                    "--input",
                    str(valid),
                    "--source-sha256",
                    "NOT-A-HEX",
                    "--completeness",
                    "full",
                ],
                output_path=tmpdir / "malformed.json",
            )
            self.assertEqual(code, 2)

            bad_sha = "00" * 32
            code, _, stderr = _run_command(
                [
                    "--format",
                    "tcga-methylation-beta",
                    "--input",
                    str(valid),
                    "--source-sha256",
                    bad_sha,
                    "--completeness",
                    "full",
                ],
                output_path=tmpdir / "badhash.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("hash mismatch", stderr)

            code, _, _ = _run_command(
                [
                    "--format",
                    "bad-format",
                    "--input",
                    str(valid),
                    "--source-sha256",
                    sha,
                    "--completeness",
                    "full",
                ],
                output_path=output,
            )
            self.assertEqual(code, 2)

    def test_synthetic_known_oracles(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            fixtures = [
                (
                    "tcga-star-expression",
                    FIXTURE_ROOT / "synthetic_tcga_star.tsv",
                    "full",
                ),
                (
                    "tcga-methylation-beta",
                    FIXTURE_ROOT / "synthetic_tcga_methylation.tsv",
                    "full",
                ),
                (
                    "cpc-expression",
                    FIXTURE_ROOT / "synthetic_cpc_expression.tsv",
                    "bounded-prefix",
                ),
                (
                    "cpc-methylation",
                    FIXTURE_ROOT / "synthetic_cpc_methylation.tsv",
                    "bounded-prefix",
                ),
            ]
            for idx, (fmt, path, completeness) in enumerate(fixtures):
                code, _, stderr, output = _run_fixture(
                    fmt,
                    path,
                    _sha256(path),
                    completeness,
                    tmpdir,
                    output_name=f"synthetic_{idx}.json",
                )
                self.assertEqual(code, 0, stderr)
                summary = _read_summary(output)
                self.assertEqual(summary["format"], fmt)
                self.assertEqual(summary["supplied_completeness"], completeness)

    def test_synthetic_failures_wrong_width_and_duplicates(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            malformed = tmpdir / "bad.tsv"
            malformed.write_text(
                "gene_id\tgene_name\tgene_type\tunstranded\tstranded_first\tstranded_second\ttpm_unstranded\tfpkm_unstranded\tfpkm_uq_unstranded\n"
                "ENSG1\tA\tcoding\t1\t2\t3\n",
                encoding="utf-8",
            )
            bad_sha = _sha256(malformed)
            code, _, stderr, _ = _run_fixture(
                "tcga-star-expression", malformed, bad_sha, "full", tmpdir, output_name="wrong_width.json"
            )
            self.assertEqual(code, 3)
            self.assertIn("row=2", stderr)

            bad = tmpdir / "dup.tsv"
            bad.write_text(
                "cg000001\t0.1\ncg000001\t0.2\n",
                encoding="utf-8",
            )
            dup_sha = _sha256(bad)
            code, _, stderr, _ = _run_fixture(
                "tcga-methylation-beta",
                bad,
                dup_sha,
                "full",
                tmpdir,
                output_name="dup.tsv.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("row=2", stderr)

    def test_invalid_numeric_and_range_failures(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)

            invalid = tmpdir / "invalid.tsv"
            invalid.write_text("cg000001\tbad\n", encoding="utf-8")
            invalid_sha = _sha256(invalid)
            code, _, stderr, _ = _run_fixture(
                "tcga-methylation-beta",
                invalid,
                invalid_sha,
                "full",
                tmpdir,
                output_name="invalid.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("reason=non-numeric token", stderr)

            out_of_range = tmpdir / "out_of_range.tsv"
            out_of_range.write_text("cg000001\t1.5\n", encoding="utf-8")
            oos = _sha256(out_of_range)
            code, _, stderr, _ = _run_fixture(
                "tcga-methylation-beta",
                out_of_range,
                oos,
                "full",
                tmpdir,
                output_name="out_of_range.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("reason=beta value outside [0, 1]", stderr)

            swapped = tmpdir / "swapped.tsv"
            swapped.write_text(
                "CPCG0001_rep1_Dectection_Pval\tCPCG0001_rep1\tCPCG0002_rep2\tCPCG0002_rep2_Dectection_Pval\n"
                "cg000001\t0.1\t0.2\t0.3\t0.4\n",
                encoding="utf-8",
            )
            swapped_sha = _sha256(swapped)
            code, _, stderr, _ = _run_fixture(
                "cpc-methylation",
                swapped,
                swapped_sha,
                "bounded-prefix",
                tmpdir,
                output_name="swapped.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("reason=unpaired beta/detection columns", stderr)

    def test_wrong_width_prefix_row(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            incomplete = tmpdir / "prefix.tsv"
            incomplete.write_text(
                "CPCG0001_rep1\tCPCG0001_rep1_Dectection_Pval\n"
                "cg000001\t0.1\t0.9\n"
                "cg000002\t0.2\n",
                encoding="utf-8",
            )
            code, _, stderr, _ = _run_fixture(
                "cpc-methylation",
                incomplete,
                _sha256(incomplete),
                "bounded-prefix",
                tmpdir,
                output_name="wrong_prefix.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("wrong number of columns", stderr)

    def test_compressed_input_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            gz = tmpdir / "compressed_input.tsv"
            gz.write_bytes(b"\x1f\x8b\x08\x00test")
            code, _, stderr, _ = _run_fixture(
                "tcga-methylation-beta",
                gz,
                _sha256(gz),
                "full",
                tmpdir,
                output_name="gzip.json",
            )
            self.assertEqual(code, 2)
            self.assertIn("gzip", stderr.lower())

    def test_missing_final_newline_not_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            no_newline = tmpdir / "no_newline.tsv"
            no_newline.write_text("cg000001\t0.4", encoding="utf-8", newline="")
            code, _, _, output = _run_fixture(
                "tcga-methylation-beta",
                no_newline,
                _sha256(no_newline),
                "bounded-prefix",
                tmpdir,
                output_name="no_newline.json",
            )
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())

    def test_output_identity_and_stale_output_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            valid = tmpdir / "input.tsv"
            valid.write_text("cg000001\t0.5\n", encoding="utf-8")
            sha = _sha256(valid)

            code, _, _ = _run_command(
                [
                    "--format",
                    "tcga-methylation-beta",
                    "--input",
                    str(valid),
                    "--source-sha256",
                    sha,
                    "--completeness",
                    "full",
                ],
                output_path=valid,
            )
            self.assertEqual(code, 2)
            self.assertTrue(valid.exists())

            stale = tmpdir / "stale.json"
            stale.write_text("{\"sentinel\": true}", encoding="utf-8")
            code, _, stderr, _ = _run_fixture(
                "tcga-methylation-beta",
                valid,
                sha,
                "full",
                tmpdir,
                output_name="stale.json",
            )
            self.assertEqual(code, 2)
            self.assertIn("output path must not already exist", stderr)
            self.assertEqual(json.loads(stale.read_text(encoding="utf-8")), {"sentinel": True})

            bad_parent = tmpdir / "not_a_dir"
            bad_parent.write_text("blocked", encoding="utf-8")
            code, _, _, _ = _run_fixture(
                "tcga-methylation-beta",
                valid,
                sha,
                "full",
                tmpdir,
                output_name="not_a_dir/output.json",
            )
            self.assertEqual(code, 4)

    def test_empty_and_header_only_inputs_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            empty = tmpdir / "empty.tsv"
            empty.write_text("", encoding="utf-8")
            code, _, _, _ = _run_fixture(
                "tcga-star-expression",
                empty,
                _sha256(empty),
                "full",
                tmpdir,
                output_name="empty_star.json",
            )
            self.assertEqual(code, 3)

            empty_m = tmpdir / "empty_meth.tsv"
            empty_m.write_text("", encoding="utf-8")
            code, _, _, _ = _run_fixture(
                "tcga-methylation-beta",
                empty_m,
                _sha256(empty_m),
                "full",
                tmpdir,
                output_name="empty_meth.json",
            )
            self.assertEqual(code, 3)

            header_only = tmpdir / "header_only.tsv"
            header_only.write_text(
                "GeneID\tSymbol_UCSC\tName_UCSC\tChr_UCSC\tStart_UCSC\tEnd_UCSC\tRefSeq_UCSC\n",
                encoding="utf-8",
            )
            code, _, _, _ = _run_fixture(
                "cpc-expression",
                header_only,
                _sha256(header_only),
                "bounded-prefix",
                tmpdir,
                output_name="header_only.json",
            )
            self.assertEqual(code, 3)

    def test_blank_records_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            blank = tmpdir / "blank.tsv"
            blank.write_text(
                "cg000001\t0.1\n\ncg000002\t0.2\n",
                encoding="utf-8",
            )
            code, _, stderr, _ = _run_fixture(
                "tcga-methylation-beta",
                blank,
                _sha256(blank),
                "full",
                tmpdir,
                output_name="blank.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("blank record", stderr)

    def test_cpc_expression_malformed_schema_and_duplicate_columns(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            dup = tmpdir / "dup_columns.tsv"
            dup.write_text(
                "GeneID\tSymbol_UCSC\tName_UCSC\tChr_UCSC\tStart_UCSC\tEnd_UCSC\tRefSeq_UCSC\tCPCG0001\tCPCG0001\n"
                "1\tA\tAnn\t1\t1\t10\tRS1\t1.0\t2.0\n",
                encoding="utf-8",
            )
            code, _, stderr, _ = _run_fixture(
                "cpc-expression",
                dup,
                _sha256(dup),
                "bounded-prefix",
                tmpdir,
                output_name="dup_columns.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("duplicate sample columns", stderr)

            bad_header = tmpdir / "bad_header.tsv"
            bad_header.write_text(
                "foo\tSymbol_UCSC\tName_UCSC\tChr_UCSC\tStart_UCSC\tEnd_UCSC\tRefSeq_UCSC\tC1\n"
                "1\tA\tAnn\t1\t1\t10\tRS1\t1.0\n",
                encoding="utf-8",
            )
            code, _, stderr, _ = _run_fixture(
                "cpc-expression",
                bad_header,
                _sha256(bad_header),
                "bounded-prefix",
                tmpdir,
                output_name="bad_header.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("unexpected annotation header", stderr)

    def test_cpc_methylation_duplicate_pairs_and_schema(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            duppair = tmpdir / "duppair.tsv"
            duppair.write_text(
                "CPCG0001_rep1\tCPCG0001_rep1_Dectection_Pval\tCPCG0001_rep1\tCPCG0001_rep1_Dectection_Pval\n"
                "cg000001\t0.1\t0.2\t0.3\n",
                encoding="utf-8",
            )
            code, _, stderr, _ = _run_fixture(
                "cpc-methylation",
                duppair,
                _sha256(duppair),
                "bounded-prefix",
                tmpdir,
                output_name="duppair.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("duplicate assay columns", stderr)

            wrong_label = tmpdir / "wronglabel.tsv"
            wrong_label.write_text(
                "sampleX_rep1\tsampleX_rep1_Dectection_Pval\n"
                "cg000001\t0.1\t0.2\n",
                encoding="utf-8",
            )
            code, _, stderr, _ = _run_fixture(
                "cpc-methylation",
                wrong_label,
                _sha256(wrong_label),
                "bounded-prefix",
                tmpdir,
                output_name="wronglabel.json",
            )
            self.assertEqual(code, 3)
            self.assertIn("invalid sample pair code", stderr)

    def test_repeated_runs_use_fresh_outputs(self):
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            tmpdir = Path(td)
            path = FIXTURE_ROOT / "synthetic_cpc_methylation.tsv"
            sha = _sha256(path)
            code, _, _, out1 = _run_fixture(
                "cpc-methylation",
                path,
                sha,
                "bounded-prefix",
                tmpdir,
                output_name="run1.json",
            )
            self.assertEqual(code, 0)
            first = _read_summary(out1)

            code, _, _, out2 = _run_fixture(
                "cpc-methylation",
                path,
                sha,
                "bounded-prefix",
                tmpdir,
                output_name="run2.json",
            )
            self.assertEqual(code, 0)
            second = _read_summary(out2)

            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
