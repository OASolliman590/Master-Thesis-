"""Acceptance tests for B-G2 patient-free annotation normalization."""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import PIPE, run


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
CLI = [PYTHON, "-m", "tools.b_annotation_normalize"]
PLAN = REPO_ROOT / "specs" / "B" / "annotation_normalization.proposed.json"
SCHEMA = REPO_ROOT / "specs" / "B" / "annotation_normalization.schema.json"
HEADER = ("raw_id", "canonical_symbol", "entrez_id", "ensembl_id", "mapping_status")
SOURCE_IDS = ("tcga_gencode_v36", "gse107299_processed", "historical_v18_maps")
TIMEOUT = 40
SUCCESS_FILES = {
    "annotation.tsv",
    "MANIFEST.json",
    "checksums.json",
    "PROVENANCE.json",
    "CONFLICTS.tsv",
    "HLA_CAUTION.tsv",
    "UNMAPPED.tsv",
    "COMPLETE.json",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: object) -> Path:
    path.write_bytes(_json_bytes(payload))
    return path


def _run(args: list[str]) -> tuple[int, str, str]:
    completed = run(
        [*CLI, *args],
        cwd=REPO_ROOT,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        check=False,
        timeout=TIMEOUT,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _table_bytes(rows: list[tuple[str, str, str, str, str]]) -> bytes:
    lines = ["\t".join(HEADER), *("\t".join(row) for row in rows)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _descriptor(role: str, path: Path, *, object_name: str | None = None) -> dict:
    raw = path.read_bytes()
    return {
        "role": role,
        "object_name": object_name or path.name,
        "byte_count": len(raw),
        "sha256": _sha256(raw),
        "retrieved_utc": "2026-09-11T00:00:00Z",
        "exact_url": f"https://example.invalid/{role}",
        "access_class": "public",
        "completeness": "complete_synthetic_identifier_fixture",
        "redistribution": "not_adjudicated",
        "committed_path": None,
    }


def _receipt(source_id: str, descriptors: list[dict], **overrides: object) -> dict:
    payload = {
        "schema_version": "B-G2-source-freeze-receipt-v1",
        "purpose": "source_freeze",
        "source_id": source_id,
        "pin_authorized": True,
        "plan_sha256": _sha256(PLAN.read_bytes()),
        "schema_sha256": _sha256(SCHEMA.read_bytes()),
        "inputs": descriptors,
        "reviewer_id": "synthetic-parent-reviewer",
        "reviewer_identity": "Synthetic parent test identity",
        "reviewed_utc": "2026-09-11T00:00:00Z",
        "notes": "Synthetic patient-free software acceptance fixture only.",
    }
    payload.update(overrides)
    return payload


def _tcga_bytes() -> bytes:
    header = (
        "gene_id\tgene_name\tgene_type\tunstranded\tstranded_first\tstranded_second\t"
        "tpm_unstranded\tfpkm_unstranded\tfpkm_uq_unstranded"
    )
    rows = [
        "N_unmapped\t\t\t1\t2\t3\t4\t5\t6",
        "ENSG000001.1\tHLA-A\tprotein_coding\t1\t2\t3\t4\t5\t6",
        "ENSG000002.2\tMB21D1\tprotein_coding\t9\t8\t7\t6\t5\t4",
        "ENSG000003.3\tTAPBP\tprotein_coding\t0\t0\t0\t0\t0\t0",
        "ENSG000004.4\tTAPBPR\tprotein_coding\t0\t0\t0\t0\t0\t0",
        "ENSG000005.5\t\tprotein_coding\t0\t0\t0\t0\t0\t0",
    ]
    return ("# gene-model: GENCODE v36\n" + header + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def _gse_bytes(*, extra_header: str = "") -> bytes:
    header = "GeneID\tSymbol_UCSC\tName_UCSC\tChr_UCSC\tStart_UCSC\tEnd_UCSC\tRefSeq_UCSC" + extra_header
    rows = [
        "1\tHLA-A\tA\t6\t1\t2\tNM_1",
        "2\tTMEM173\tB\t5\t3\t4\tNM_2",
        "3\tTAPBP\tC\t6\t5\t6\tNM_3",
        "4\tTAPBPR\tD\t12\t7\t8\tNM_4",
        "5\t\tE\t1\t9\t10\tNM_5",
    ]
    if extra_header:
        rows = [row + "\t0.25" for row in rows]
    return (header + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def _sqlite_fixture(path: Path, rows: list[tuple[str, int | None, int]], symbols: list[tuple[int, str]], ensembl: list[tuple[int, str]]) -> Path:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE probes(probe_id TEXT, gene_id INTEGER, is_multiple INTEGER)")
        connection.execute("CREATE TABLE symbol(gene_id INTEGER, symbol TEXT)")
        connection.execute("CREATE TABLE ensembl(gene_id INTEGER, ensembl_id TEXT)")
        connection.executemany("INSERT INTO probes VALUES(?,?,?)", rows)
        connection.executemany("INSERT INTO symbol VALUES(?,?)", symbols)
        connection.executemany("INSERT INTO ensembl VALUES(?,?)", ensembl)
        connection.commit()
    finally:
        connection.close()
    return path


class BG2AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="b_g2_")
        self.temp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _prepare(
        self,
        source_id: str,
        inputs: list[tuple[str, Path]],
        *,
        receipt_payload: dict | None = None,
        receipt_path: Path | None = None,
        plan: Path = PLAN,
        schema: Path = SCHEMA,
        output: Path | None = None,
    ) -> tuple[int, str, str, Path]:
        descriptors = [_descriptor(role, path) for role, path in inputs]
        if receipt_path is None:
            receipt_path = self.temp / f"{source_id}.receipt.json"
            _write_json(receipt_path, receipt_payload or _receipt(source_id, descriptors))
        target = output or self.temp / f"{source_id}.out"
        args = [
            "prepare",
            "--plan",
            str(plan),
            "--schema",
            str(schema),
            "--source-id",
            source_id,
            "--freeze-receipt",
            str(receipt_path),
        ]
        for role, path in inputs:
            args.extend(["--input", f"{role}={path}"])
        args.extend(["--output", str(target)])
        rc, stdout, stderr = _run(args)
        return rc, stdout, stderr, target

    def test_01_validate_table_is_synthetic_only_for_each_source(self) -> None:
        rows = [
            ("A", "A", "1", "", "mapped"),
            ("B", "", "", "", "unmapped"),
            ("C", "C1", "2", "", "ambiguous"),
        ]
        table = self.temp / "annotation.tsv"
        table.write_bytes(_table_bytes(rows))
        for source_id in SOURCE_IDS:
            output = self.temp / f"validated-{source_id}"
            rc, _, err = _run(
                [
                    "validate-table",
                    "--purpose",
                    "synthetic_test",
                    "--table",
                    str(table),
                    "--source-id",
                    source_id,
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(rc, 0, err)
            self.assertEqual({path.name for path in output.iterdir()}, {"VALIDATED.json"})
            receipt = json.loads((output / "VALIDATED.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["table_sha256"], _sha256(table.read_bytes()))
            self.assertEqual(receipt["mapping_status_counts"], {"ambiguous": 1, "mapped": 1, "unmapped": 1})
            self.assertFalse(receipt["biological_validation"])

    def test_02_prepare_tcga_success_aliases_hla_unmapped_and_bg1_compatibility(self) -> None:
        source = self.temp / "tcga.tsv"
        source.write_bytes(_tcga_bytes())
        rc, _, err, output = self._prepare("tcga_gencode_v36", [("tcga_gencode_v36", source)])
        self.assertEqual(rc, 0, err)
        self.assertEqual({path.name for path in output.iterdir()}, SUCCESS_FILES)
        table = output / "annotation.tsv"
        text = table.read_text(encoding="utf-8")
        self.assertNotIn("N_unmapped", text)
        self.assertIn("ENSG000002.2\tCGAS\t\tENSG000002.2\tmapped", text)
        self.assertIn("ENSG000003.3\tTAPBP", text)
        self.assertIn("ENSG000004.4\tTAPBPL", text)
        self.assertIn("ENSG000005.5\t\t\t\tunmapped", text)
        self.assertIn("HLA-A", (output / "HLA_CAUTION.tsv").read_text(encoding="utf-8"))
        manifest = json.loads((output / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), {
            "schema_version", "source_id", "source_status", "canonicalization_authority",
            "identifier_namespace", "source_reference", "table_path", "table_sha256",
        })
        self.assertEqual(manifest["table_sha256"], _sha256(table.read_bytes()))
        checksums_raw = (output / "checksums.json").read_bytes()
        checksums = json.loads(checksums_raw)
        for name, digest in checksums["outputs"].items():
            self.assertEqual(digest, _sha256((output / name).read_bytes()), name)
        complete = json.loads((output / "COMPLETE.json").read_text(encoding="utf-8"))
        self.assertEqual(complete["checksums_sha256"], _sha256(checksums_raw))
        self.assertFalse(complete["biological_analysis_released"])
        from tools.b_gene_registry.__main__ import load_annotation_source

        loaded = load_annotation_source(output / "MANIFEST.json")
        self.assertEqual(len(loaded["rows"]), 5)

    def test_03_prepare_gse_identifier_only_never_invents_ensembl_or_suffix(self) -> None:
        source = self.temp / "gse.tsv"
        source.write_bytes(_gse_bytes())
        rc, _, err, output = self._prepare("gse107299_processed", [("gse107299_processed", source)])
        self.assertEqual(rc, 0, err)
        text = (output / "annotation.tsv").read_text(encoding="utf-8")
        self.assertIn("2\tSTING1\t2\t\tmapped", text)
        self.assertIn("3\tTAPBP\t3\t\tmapped", text)
        self.assertIn("4\tTAPBPL\t4\t\tmapped", text)
        self.assertNotIn("_at", text)
        for line in text.splitlines()[1:]:
            self.assertEqual(line.split("\t")[3], "")

    def test_04_prepare_v18_sqlite_platform_qualification_and_null_conflict(self) -> None:
        hta = _sqlite_fixture(
            self.temp / "hta20hsentrezg.sqlite",
            [("1_at", 1, 0), ("101928749_at", None, 0), ("2_at", 2, 0)],
            [(1, "HLA-A"), (2, "MB21D1")],
            [(1, "ENSG1"), (2, "ENSG2"), (2, "ENSG2_ALT")],
        )
        hugene = _sqlite_fixture(
            self.temp / "hugene20sthsentrezg.sqlite",
            [("1_at", 1, 0), ("3_at", 3, 0)],
            [(1, "HLA-A"), (3, "TAPBPR")],
            [(1, "ENSG1"), (3, "ENSG3")],
        )
        rc, _, err, output = self._prepare(
            "historical_v18_maps", [("hta20", hta), ("hugene20st", hugene)]
        )
        self.assertEqual(rc, 0, err)
        text = (output / "annotation.tsv").read_text(encoding="utf-8")
        self.assertIn("hta20:1_at\tHLA-A\t1\tENSG1\tmapped", text)
        self.assertIn("hugene20st:1_at\tHLA-A\t1\tENSG1\tmapped", text)
        self.assertIn("hta20:101928749_at\t\t\t\tunmapped", text)
        self.assertIn("hugene20st:3_at\tTAPBPL\t3\tENSG3\tmapped", text)
        conflicts = (output / "CONFLICTS.tsv").read_text(encoding="utf-8")
        self.assertIn("historical-null-no-suffix-repair", conflicts)
        self.assertIn("one-to-many-ensembl", conflicts)
        self.assertNotIn("24937", "".join(path.read_text(encoding="utf-8") for path in output.iterdir()))

    def test_05_prepare_outputs_are_byte_identical_across_fresh_directories(self) -> None:
        source = self.temp / "gse.tsv"
        source.write_bytes(_gse_bytes())
        descriptors = [_descriptor("gse107299_processed", source)]
        receipt = self.temp / "receipt.json"
        _write_json(receipt, _receipt("gse107299_processed", descriptors))
        first = self._prepare(
            "gse107299_processed", [("gse107299_processed", source)], receipt_path=receipt, output=self.temp / "one"
        )
        second = self._prepare(
            "gse107299_processed", [("gse107299_processed", source)], receipt_path=receipt, output=self.temp / "two"
        )
        self.assertEqual(first[0], 0, first[2])
        self.assertEqual(second[0], 0, second[2])
        self.assertEqual(
            {path.name: path.read_bytes() for path in first[3].iterdir()},
            {path.name: path.read_bytes() for path in second[3].iterdir()},
        )

    def test_06_missing_false_or_synthetic_freeze_never_pins(self) -> None:
        source = self.temp / "gse.tsv"
        source.write_bytes(_gse_bytes())
        descriptors = [_descriptor("gse107299_processed", source)]
        cases = [
            (self.temp / "missing.json", None),
            (self.temp / "false.json", _receipt("gse107299_processed", descriptors, pin_authorized=False)),
            (self.temp / "synthetic.json", _receipt("gse107299_processed", descriptors, purpose="synthetic_test")),
        ]
        for index, (receipt_path, payload) in enumerate(cases):
            if payload is not None:
                _write_json(receipt_path, payload)
            rc, _, _, output = self._prepare(
                "gse107299_processed",
                [("gse107299_processed", source)],
                receipt_path=receipt_path,
                output=self.temp / f"incomplete-{index}",
            )
            self.assertEqual(rc, 3)
            self.assertEqual({path.name for path in output.iterdir()}, {"INCOMPLETE.json"})
            self.assertFalse((output / "MANIFEST.json").exists())
            self.assertFalse((output / "COMPLETE.json").exists())

    def test_07_wrong_hash_and_byte_count_fail_before_parser(self) -> None:
        source = self.temp / "not-even-a-table.bin"
        source.write_bytes(b"not a parser input")
        for field, value in (("sha256", "0" * 64), ("byte_count", 999)):
            descriptor = _descriptor("gse107299_processed", source)
            descriptor[field] = value
            receipt = _receipt("gse107299_processed", [descriptor])
            rc, _, err, output = self._prepare(
                "gse107299_processed",
                [("gse107299_processed", source)],
                receipt_payload=receipt,
                output=self.temp / f"bad-{field}",
            )
            self.assertEqual(rc, 3, err)
            self.assertEqual({path.name for path in output.iterdir()}, {"INCOMPLETE.json"})
            failure = json.loads((output / "INCOMPLETE.json").read_text(encoding="utf-8"))
            self.assertIn("mismatch", failure["status"])
            self.assertEqual(failure["input_hashes"][0]["sha256"], _sha256(source.read_bytes()))

    def test_08_unknown_receipt_and_descriptor_fields_fail_closed(self) -> None:
        source = self.temp / "gse.tsv"
        source.write_bytes(_gse_bytes())
        descriptor = _descriptor("gse107299_processed", source)
        cases = []
        receipt_extra = _receipt("gse107299_processed", [descriptor])
        receipt_extra["unexpected"] = True
        cases.append(receipt_extra)
        descriptor_extra = dict(descriptor)
        descriptor_extra["private_path"] = "forbidden"
        cases.append(_receipt("gse107299_processed", [descriptor_extra]))
        path_like_object_name = dict(descriptor)
        path_like_object_name["object_name"] = "nested/source.tsv"
        cases.append(_receipt("gse107299_processed", [path_like_object_name]))
        for index, payload in enumerate(cases):
            rc, _, err, output = self._prepare(
                "gse107299_processed",
                [("gse107299_processed", source)],
                receipt_payload=payload,
                output=self.temp / f"unknown-{index}",
            )
            self.assertEqual(rc, 3, err)
            self.assertEqual({path.name for path in output.iterdir()}, {"FAILURE.json"})

    def test_09_altered_plan_unknown_field_and_altered_schema_are_rejected(self) -> None:
        source = self.temp / "gse.tsv"
        source.write_bytes(_gse_bytes())
        altered_plan_payload = json.loads(PLAN.read_text(encoding="utf-8"))
        altered_plan_payload["unexpected"] = True
        altered_plan = _write_json(self.temp / "plan.json", altered_plan_payload)
        altered_schema_payload = json.loads(SCHEMA.read_text(encoding="utf-8"))
        altered_schema_payload["title"] = "weakened"
        altered_schema = _write_json(self.temp / "schema.json", altered_schema_payload)
        for index, (plan, schema) in enumerate(((altered_plan, SCHEMA), (PLAN, altered_schema))):
            descriptor = _descriptor("gse107299_processed", source)
            receipt = _receipt("gse107299_processed", [descriptor])
            receipt["plan_sha256"] = _sha256(plan.read_bytes())
            receipt["schema_sha256"] = _sha256(schema.read_bytes())
            rc, _, err, output = self._prepare(
                "gse107299_processed",
                [("gse107299_processed", source)],
                receipt_payload=receipt,
                plan=plan,
                schema=schema,
                output=self.temp / f"altered-{index}",
            )
            self.assertEqual(rc, 3, err)
            self.assertFalse((output / "MANIFEST.json").exists())

    def test_10_tcga_rejects_gzip_missing_comment_summary_as_gene_and_late_comment(self) -> None:
        valid = _tcga_bytes()
        cases = [
            gzip.compress(valid),
            valid.replace(b"# gene-model: GENCODE v36\n", b""),
            valid.replace(b"N_unmapped\t\t", b"N_not_a_summary\t\t"),
            valid.replace(b"# gene-model: GENCODE v36\n", b"") + b"# gene-model: GENCODE v36\n",
            valid.split(b"\n", 2)[0] + b"\n" + valid.split(b"\n", 2)[1] + b"\n",
        ]
        for index, data in enumerate(cases):
            source = self.temp / f"tcga-{index}.bin"
            source.write_bytes(data)
            rc, _, _, output = self._prepare(
                "tcga_gencode_v36",
                [("tcga_gencode_v36", source)],
                output=self.temp / f"tcga-bad-{index}",
            )
            if index == 2:
                self.assertEqual(rc, 0)
                self.assertIn("N_not_a_summary", (output / "annotation.tsv").read_text(encoding="utf-8"))
            else:
                self.assertEqual(rc, 3)

    def test_11_gse_refuses_uncompressed_patient_or_value_columns_and_prefix_hash(self) -> None:
        source = self.temp / "gse-extra.tsv"
        source.write_bytes(_gse_bytes(extra_header="\tpatient_001_expression"))
        rc, _, _, output = self._prepare(
            "gse107299_processed", [("gse107299_processed", source)], output=self.temp / "gse-extra-out"
        )
        self.assertEqual(rc, 3)
        self.assertEqual({path.name for path in output.iterdir()}, {"INCOMPLETE.json"})
        compressed = self.temp / "synthetic.gz"
        compressed.write_bytes(gzip.compress(_gse_bytes(extra_header="\tsample")))
        rc, _, _, output = self._prepare(
            "gse107299_processed", [("gse107299_processed", compressed)], output=self.temp / "gse-gzip-out"
        )
        self.assertEqual(rc, 3)
        self.assertIn("hash", json.loads((output / "INCOMPLETE.json").read_text(encoding="utf-8"))["status"])

    def test_12_v18_wrong_order_unqualified_probe_and_cross_chip_collapse_fail(self) -> None:
        bad = _sqlite_fixture(self.temp / "hta20hsentrezg.sqlite", [("1", 1, 0)], [(1, "A")], [])
        good = _sqlite_fixture(self.temp / "hugene20sthsentrezg.sqlite", [("1_at", 1, 0)], [(1, "A")], [])
        rc, _, _, output = self._prepare(
            "historical_v18_maps", [("hta20", bad), ("hugene20st", good)], output=self.temp / "bad-suffix"
        )
        self.assertEqual(rc, 3)
        self.assertFalse((output / "MANIFEST.json").exists())
        descriptors = [_descriptor("hugene20st", good), _descriptor("hta20", good)]
        receipt = _receipt("historical_v18_maps", descriptors)
        rc, _, _, output = self._prepare(
            "historical_v18_maps",
            [("hugene20st", good), ("hta20", good)],
            receipt_payload=receipt,
            output=self.temp / "wrong-order",
        )
        self.assertEqual(rc, 3)

    def test_13_validate_table_adversarial_cases(self) -> None:
        cases = {
            "patient-column": b"raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status\tpatient\n",
            "nul": _table_bytes([("A", "A", "1", "", "mapped")]).replace(b"A\tA", b"A\x00\tA", 1),
            "cr": _table_bytes([("A", "A", "1", "", "mapped")]).replace(b"\n", b"\r", 1),
            "utf8": b"raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status\n\xff",
            "empty-raw": _table_bytes([("", "A", "1", "", "mapped")]),
            "duplicate": _table_bytes([("A", "A", "1", "", "mapped"), ("A", "A", "1", "", "mapped")]),
            "tap-collapse": _table_bytes([("TAPBP", "TAPBPL", "1", "", "mapped")]),
            "alias": _table_bytes([("MB21D1", "MB21D1", "1", "", "mapped")]),
            "unsorted": _table_bytes([("B", "B", "2", "", "mapped"), ("A", "A", "1", "", "mapped")]),
        }
        for name, data in cases.items():
            table = self.temp / f"{name}.tsv"
            table.write_bytes(data)
            output = self.temp / f"{name}.out"
            rc, _, _ = _run(
                ["validate-table", "--purpose", "synthetic_test", "--table", str(table), "--source-id", SOURCE_IDS[0], "--output", str(output)]
            )
            self.assertEqual(rc, 3, name)
            self.assertFalse(output.exists(), name)

    def test_14_existing_output_is_refused_without_mutation(self) -> None:
        table = self.temp / "annotation.tsv"
        table.write_bytes(_table_bytes([("A", "A", "1", "", "mapped")]))
        output = self.temp / "existing"
        output.mkdir()
        sentinel = output / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")
        rc, _, _ = _run(
            ["validate-table", "--purpose", "synthetic_test", "--table", str(table), "--source-id", SOURCE_IDS[0], "--output", str(output)]
        )
        self.assertEqual(rc, 2)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertEqual({path.name for path in output.iterdir()}, {"sentinel.txt"})

    def test_15_wrong_roles_duplicates_and_cardinality_fail(self) -> None:
        source = self.temp / "gse.tsv"
        source.write_bytes(_gse_bytes())
        cases = [
            [("tcga_gencode_v36", source)],
            [("gse107299_processed", source), ("gse107299_processed", source)],
            [],
        ]
        for index, inputs in enumerate(cases):
            receipt = self.temp / f"roles-{index}.json"
            _write_json(receipt, _receipt("gse107299_processed", [_descriptor(role, path) for role, path in inputs]))
            rc, _, _, output = self._prepare(
                "gse107299_processed", inputs, receipt_path=receipt, output=self.temp / f"roles-out-{index}"
            )
            self.assertEqual(rc, 3)
            self.assertFalse((output / "MANIFEST.json").exists())

    def test_16_source_has_no_network_or_scientific_dependencies(self) -> None:
        source_path = REPO_ROOT / "tools" / "b_annotation_normalize" / "__main__.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden = {"numpy", "pandas", "scipy", "sklearn", "requests", "http", "socket", "subprocess"}
        self.assertFalse(imported & forbidden)
        text = source_path.read_text(encoding="utf-8").lower()
        for forbidden_call in ("urlopen(", "requests.", "socket.", "git commit", "notion"):
            self.assertNotIn(forbidden_call, text)


if __name__ == "__main__":
    unittest.main()
