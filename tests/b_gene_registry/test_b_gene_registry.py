"""Acceptance tests for B-G1 registry validation and patient-free coverage audit."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from subprocess import PIPE, run
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
CLI = [PYTHON, "-m", "tools.b_gene_registry"]
REGISTRY_PATH = REPO_ROOT / "specs" / "B" / "gene_set_registry.proposed.json"
SCHEMA_PATH = REPO_ROOT / "specs" / "B" / "gene_set_registry.schema.json"
TIMEOUT = 30

ANNOTATION_HEADER = ["raw_id", "canonical_symbol", "entrez_id", "ensembl_id", "mapping_status"]
REQUIRED_SOURCE_IDS = ["tcga_gencode_v36", "gse107299_processed", "historical_v18_maps"]
EXPECTED_REGISTRY_ROWS = 137
EXPECTED_COVERAGE_ROWS = 411
FORBIDDEN_IMPORTS = {
    "numpy",
    "pandas",
    "sklearn",
    "scipy",
    "requests",
    "urllib",
    "urllib.request",
    "http",
    "http.client",
    "socket",
}
FORBIDDEN_OUTPUT_KEYS = {
    "coefficient",
    "coefficients",
    "weight",
    "weights",
    "score",
    "scores",
    "prediction",
    "predictions",
    "patient_id",
    "sample_id",
    "expression",
    "delta_r2",
    "y",
}


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_official_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _load_official_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _membership_sha256(symbols: list[str]) -> str:
    payload = json.dumps(symbols, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256(payload)


def _write_json(path: Path, payload: object) -> Path:
    path.write_bytes(_canonical_json_bytes(payload))
    return path


def _write_table(path: Path, rows: list[tuple[str, str, str, str, str]]) -> bytes:
    lines = ["\t".join(ANNOTATION_HEADER)]
    lines.extend("\t".join(row) for row in rows)
    data = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(data)
    return data


def _write_source(
    directory: Path,
    source_id: str,
    rows: list[tuple[str, str, str, str, str]],
    *,
    source_status: str = "pinned",
    extra_fields: dict | None = None,
    table_sha256: str | None = None,
    table_path: str | None = None,
    table_bytes: bytes | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    table = directory / f"{source_id}.tsv"
    if table_bytes is None:
        data = _write_table(table, rows)
    else:
        table.write_bytes(table_bytes)
        data = table_bytes
    manifest = {
        "schema_version": "B-G1-annotation-manifest-v1",
        "source_id": source_id,
        "source_status": source_status,
        "canonicalization_authority": "synthetic-test-authority-v1",
        "identifier_namespace": "symbol_entrez_ensembl",
        "source_reference": f"synthetic:{source_id}",
        "table_path": table_path if table_path is not None else table.name,
        "table_sha256": table_sha256 if table_sha256 is not None else _sha256(data),
    }
    if extra_fields:
        manifest.update(extra_fields)
    man_path = directory / f"{source_id}.manifest.json"
    _write_json(man_path, manifest)
    return man_path


def _standard_rows() -> dict[str, list[tuple[str, str, str, str, str]]]:
    p_mapped = [
        ("HLA-A", "HLA-A", "SYN_E_A", "SYN_ENS_A", "mapped"),
        ("HLA-B", "HLA-B", "SYN_E_B", "SYN_ENS_B", "mapped"),
        ("HLA-C", "HLA-C", "SYN_E_C", "SYN_ENS_C", "mapped"),
        ("B2M", "B2M", "SYN_E_B2M", "SYN_ENS_B2M", "mapped"),
        ("TAP1", "TAP1", "SYN_E_TAP1", "SYN_ENS_TAP1", "mapped"),
        ("TAP2", "TAP2", "SYN_E_TAP2", "SYN_ENS_TAP2", "mapped"),
        ("PSMB8", "PSMB8", "SYN_E_PSMB8", "SYN_ENS_PSMB8", "mapped"),
        ("PSMB9", "PSMB9", "SYN_E_PSMB9", "SYN_ENS_PSMB9", "mapped"),
        ("TAPBP", "TAPBP", "SYN_E_TAPBP", "SYN_ENS_TAPBP", "mapped"),
        ("TAPBPL", "TAPBPL", "SYN_E_TAPBPL", "SYN_ENS_TAPBPL", "mapped"),
        ("CGAS", "CGAS", "SYN_E_CGAS", "SYN_ENS_CGAS", "mapped"),
        ("STING1", "STING1", "SYN_E_STING1", "SYN_ENS_STING1", "mapped"),
        ("CXCL9", "CXCL9", "SYN_E_CXCL9", "SYN_ENS_CXCL9", "mapped"),
    ]
    gse_rows = [
        ("HLA-A", "HLA-A", "SYN_E_A1", "SYN_ENS_A1", "mapped"),
        ("HLA-A", "HLA-A", "SYN_E_A2", "SYN_ENS_A2", "mapped"),
        ("TAPBP", "TAPBP", "SYN_E_TAPBP_GSE", "", "mapped"),
        ("MISSINGGENE", "", "", "", "unmapped"),
    ]
    historical_rows = [
        ("HLA-A", "HLA-A", "SYN_E_A_AMB", "", "ambiguous"),
        ("TAPBPR", "TAPBPL", "SYN_E_TAPBPR", "SYN_ENS_TAPBPR", "mapped"),
        ("TAPBPL", "TAPBPL", "SYN_E_TAPBPL_H", "SYN_ENS_TAPBPL_H", "mapped"),
        ("MB21D1", "CGAS", "SYN_E_MB21D1", "SYN_ENS_MB21D1", "mapped"),
        ("TMEM173", "STING1", "SYN_E_TMEM173", "SYN_ENS_TMEM173", "mapped"),
        ("ORPHAN", "", "", "", "unmapped"),
    ]
    return {
        "tcga_gencode_v36": p_mapped,
        "gse107299_processed": gse_rows,
        "historical_v18_maps": historical_rows,
    }


def _write_standard_sources(directory: Path) -> list[Path]:
    rows = _standard_rows()
    return [_write_source(directory, source_id, rows[source_id]) for source_id in REQUIRED_SOURCE_IDS]


def _run_cli(args: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = run(
        [*CLI, *args],
        cwd=str(cwd or REPO_ROOT),
        check=False,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        timeout=TIMEOUT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_build(output: Path, manifests: list[Path], *, registry: Path = REGISTRY_PATH, schema: Path = SCHEMA_PATH) -> tuple[int, str, str]:
    args = ["build", "--registry", str(registry), "--schema", str(schema)]
    for manifest in manifests:
        args.extend(["--annotation-manifest", str(manifest)])
    args.extend(["--output", str(output)])
    return _run_cli(args)


def _collect_keys(payload: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        keys.update(payload)
        for value in payload.values():
            keys.update(_collect_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            keys.update(_collect_keys(item))
    return keys


def _coverage_row(rows: list[dict], *, symbol: str, source_id: str, program_id: str | None = None) -> dict:
    matched = [
        row
        for row in rows
        if row["raw_symbol"] == symbol and row["source_id"] == source_id and (program_id is None or row["program_id"] == program_id)
    ]
    if len(matched) != 1:
        raise AssertionError(f"expected one coverage row for {symbol} {source_id} {program_id}, found {len(matched)}")
    return matched[0]


class BG1AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="b_g1_")
        self.temp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_01_valid_complete_build_row_counts_and_order(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")
        output = self.temp / "out_complete"
        rc, _, err = _run_build(output, manifests)
        self.assertEqual(rc, 0, err)
        complete = _load_json(output / "COMPLETE.json")
        rows_json = _load_json(output / "registry_rows.json")
        coverage_json = _load_json(output / "coverage.json")
        checksums = _load_json(output / "checksums.json")
        self.assertEqual(complete["status"], "complete")
        self.assertEqual(complete["schema_version"], "B-G1-complete-v1")
        self.assertEqual(complete["registry_row_count"], EXPECTED_REGISTRY_ROWS)
        self.assertEqual(complete["coverage_row_count"], EXPECTED_COVERAGE_ROWS)
        self.assertEqual(complete["program_count"], 11)
        self.assertEqual(complete["null_membership_program_count"], 1)
        self.assertEqual(complete["required_source_ids"], REQUIRED_SOURCE_IDS)
        self.assertEqual(complete["checksums_sha256"], _sha256((output / "checksums.json").read_bytes()))
        self.assertEqual(rows_json["row_count"], EXPECTED_REGISTRY_ROWS)
        self.assertEqual(len(rows_json["rows"]), EXPECTED_REGISTRY_ROWS)
        self.assertEqual(coverage_json["row_count"], EXPECTED_COVERAGE_ROWS)
        self.assertEqual(len(coverage_json["rows"]), EXPECTED_COVERAGE_ROWS)
        first = rows_json["rows"][0]
        last = rows_json["rows"][-1]
        self.assertEqual(first["program_id"], "P_ANTIGEN_PRESENTATION")
        self.assertEqual(first["raw_symbol"], "HLA-A")
        self.assertEqual(first["member_index"], 0)
        self.assertEqual(last["program_id"], "M6_EPIGENETIC_REGULATORS")
        self.assertEqual(last["raw_symbol"], "KDM6A")
        self.assertEqual([row["raw_symbol"] for row in rows_json["rows"][:8]], ["HLA-A", "HLA-B", "HLA-C", "B2M", "TAP1", "TAP2", "PSMB8", "PSMB9"])
        nulls = rows_json["null_membership_programs"]
        self.assertEqual(len(nulls), 1)
        self.assertEqual(nulls[0]["program_id"], "HALLMARK_INTERFERON_GAMMA_RESPONSE")
        self.assertIsNone(nulls[0]["membership_sha256"])
        self.assertFalse(any(row["program_id"] == "HALLMARK_INTERFERON_GAMMA_RESPONSE" for row in rows_json["rows"]))
        self.assertEqual([row["source_id"] for row in coverage_json["rows"][:3]], REQUIRED_SOURCE_IDS)
        self.assertEqual(checksums["inputs"]["registry_sha256"], _sha256(REGISTRY_PATH.read_bytes()))
        self.assertEqual(checksums["inputs"]["schema_sha256"], _sha256(SCHEMA_PATH.read_bytes()))
        self.assertEqual([item["source_id"] for item in checksums["inputs"]["annotation_sources"]], REQUIRED_SOURCE_IDS)
        self.assertNotIn("checksums.json", checksums["outputs"])
        self.assertNotIn("COMPLETE.json", checksums["outputs"])
        self.assertFalse((output / "INCOMPLETE.json").exists())
        tsv_header = (output / "registry_rows.tsv").read_text(encoding="utf-8").split("\n")[0].split("\t")
        self.assertEqual(
            tsv_header,
            [
                "program_index",
                "program_id",
                "program_layer",
                "member_index",
                "raw_symbol",
                "canonical_symbol",
                "alias_applied",
                "overlap_with_primary_p",
                "membership_status",
                "direction_status",
                "weights_status",
                "scoring_status",
                "predictor_status",
            ],
        )
        self.assertTrue((output / "registry_rows.tsv").read_bytes().endswith(b"\n"))
        self.assertFalse((output / "registry_rows.tsv").read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_02_primary_gene_reorder_and_substitution_rejected(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")
        registry = _load_official_registry()
        primary = next(program for program in registry["programs"] if program["layer"] == "primary")
        reordered = list(reversed(primary["raw_gene_symbols"]))
        primary["raw_gene_symbols"] = reordered
        primary["membership_sha256"] = _membership_sha256(reordered)
        registry_path = _write_json(self.temp / "registry_reordered.json", registry)
        rc, _, err = _run_build(self.temp / "out_reordered", manifests, registry=registry_path)
        self.assertEqual(rc, 3, err)
        self.assertIn("primary-membership-locked-order", err)
        self.assertFalse((self.temp / "out_reordered").exists())

        registry = _load_official_registry()
        primary = next(program for program in registry["programs"] if program["layer"] == "primary")
        altered = list(primary["raw_gene_symbols"])
        altered[0] = "NLRC5"
        primary["raw_gene_symbols"] = altered
        primary["membership_sha256"] = _membership_sha256(altered)
        registry_path = _write_json(self.temp / "registry_altered.json", registry)
        rc, _, err = _run_build(self.temp / "out_altered", manifests, registry=registry_path)
        self.assertEqual(rc, 3, err)
        self.assertIn("primary-membership-locked-order", err)

    def test_03_duplicate_ids_members_null_hash_and_wrong_hash(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")

        registry = _load_official_registry()
        registry["programs"][1]["id"] = registry["programs"][3]["id"]
        rc, _, err = _run_build(self.temp / "out_dup_id", manifests, registry=_write_json(self.temp / "dup_id.json", registry))
        self.assertEqual(rc, 3, err)
        self.assertIn("duplicate-program-id", err)

        registry = _load_official_registry()
        primary = next(program for program in registry["programs"] if program["layer"] == "primary")
        primary["raw_gene_symbols"] = primary["raw_gene_symbols"] + ["HLA-A"]
        primary["membership_sha256"] = _membership_sha256(primary["raw_gene_symbols"])
        rc, _, err = _run_build(self.temp / "out_dup_raw", manifests, registry=_write_json(self.temp / "dup_raw.json", registry))
        self.assertEqual(rc, 3, err)
        self.assertIn("duplicate-raw-member", err)
        self.assertIn("HLA-A", err)

        registry = _load_official_registry()
        cytotoxicity = next(program for program in registry["programs"] if program["id"] == "M2_CYTOTOXICITY")
        cytotoxicity["raw_gene_symbols"] = list(cytotoxicity["raw_gene_symbols"]) + ["CD8A"]
        cytotoxicity["membership_sha256"] = _membership_sha256(cytotoxicity["raw_gene_symbols"])
        rc, _, err = _run_build(self.temp / "out_dup_raw_m2", manifests, registry=_write_json(self.temp / "dup_raw_m2.json", registry))
        self.assertEqual(rc, 3, err)
        self.assertIn("duplicate-raw-member", err)
        self.assertIn("CD8A", err)
        self.assertFalse((self.temp / "out_dup_raw_m2").exists())

        registry = _load_official_registry()
        hallmark = next(program for program in registry["programs"] if program["id"] == "HALLMARK_INTERFERON_GAMMA_RESPONSE")
        hallmark["membership_sha256"] = "0" * 64
        rc, _, err = _run_build(self.temp / "out_null_hash", manifests, registry=_write_json(self.temp / "null_hash.json", registry))
        self.assertEqual(rc, 3, err)

        registry = _load_official_registry()
        primary = next(program for program in registry["programs"] if program["layer"] == "primary")
        primary["membership_sha256"] = None
        rc, _, err = _run_build(self.temp / "out_missing_hash", manifests, registry=_write_json(self.temp / "missing_hash.json", registry))
        self.assertEqual(rc, 3, err)

        registry = _load_official_registry()
        primary = next(program for program in registry["programs"] if program["layer"] == "primary")
        primary["membership_status"] = "unresolved"
        rc, _, err = _run_build(self.temp / "out_unresolved_list", manifests, registry=_write_json(self.temp / "unresolved_list.json", registry))
        self.assertEqual(rc, 3, err)
        self.assertIn("unresolved-forbids-symbol-list", err)

        registry = _load_official_registry()
        primary = next(program for program in registry["programs"] if program["layer"] == "primary")
        primary["membership_sha256"] = "ab" * 32
        rc, _, err = _run_build(self.temp / "out_wrong_hash", manifests, registry=_write_json(self.temp / "wrong_hash.json", registry))
        self.assertEqual(rc, 3, err)
        self.assertIn("membership-hash-mismatch", err)
        self.assertIn(_membership_sha256(primary["raw_gene_symbols"]), err)

    def test_04_aliases_and_tapbp_not_collapsed_with_tapbpl(self) -> None:
        from tools.b_gene_registry.__main__ import apply_alias

        registry = _load_official_registry()
        alias_map = {rule["raw_symbol"]: rule["canonical_symbol"] for rule in registry["canonicalization"]["alias_rules"]}
        self.assertEqual(apply_alias("MB21D1", alias_map), "CGAS")
        self.assertEqual(apply_alias("TMEM173", alias_map), "STING1")
        self.assertEqual(apply_alias("TAPBPR", alias_map), "TAPBPL")
        self.assertEqual(apply_alias("TAPBP", alias_map), "TAPBP")
        self.assertEqual(apply_alias("TAPBPL", alias_map), "TAPBPL")
        self.assertNotEqual(apply_alias("TAPBP", alias_map), apply_alias("TAPBPL", alias_map))
        self.assertNotEqual(apply_alias("TAPBP", alias_map), apply_alias("TAPBPR", alias_map))

        m0 = next(program for program in registry["programs"] if program["id"] == "M0_EXTRA_ANTIGEN_PRESENTATION")
        m0["raw_gene_symbols"] = list(m0["raw_gene_symbols"]) + ["TAPBPR", "MB21D1", "TMEM173"]
        m0["membership_sha256"] = _membership_sha256(m0["raw_gene_symbols"])
        registry_path = _write_json(self.temp / "registry_alias.json", registry)
        manifests = _write_standard_sources(self.temp / "ann")
        output = self.temp / "out_alias"
        rc, _, err = _run_build(output, manifests, registry=registry_path)
        self.assertEqual(rc, 0, err)
        rows = _load_json(output / "registry_rows.json")["rows"]
        by_raw = {(row["program_id"], row["raw_symbol"]): row for row in rows}
        self.assertEqual(by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "MB21D1")]["canonical_symbol"], "CGAS")
        self.assertTrue(by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "MB21D1")]["alias_applied"])
        self.assertEqual(by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "TMEM173")]["canonical_symbol"], "STING1")
        self.assertTrue(by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "TMEM173")]["alias_applied"])
        self.assertEqual(by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "TAPBPR")]["canonical_symbol"], "TAPBPL")
        self.assertTrue(by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "TAPBPR")]["alias_applied"])
        tapbp = by_raw[("M0_EXTRA_ANTIGEN_PRESENTATION", "TAPBP")]
        self.assertEqual(tapbp["canonical_symbol"], "TAPBP")
        self.assertFalse(tapbp["alias_applied"])
        self.assertNotEqual(tapbp["canonical_symbol"], "TAPBPL")
        coverage = _load_json(output / "coverage.json")["rows"]
        tapbp_hist = _coverage_row(coverage, symbol="TAPBP", source_id="historical_v18_maps", program_id="M0_EXTRA_ANTIGEN_PRESENTATION")
        self.assertFalse(tapbp_hist["present"])
        self.assertNotIn("TAPBPL", tapbp_hist["raw_ids"])
        self.assertNotIn("TAPBPR", tapbp_hist["raw_ids"])
        tapbpr_hist = _coverage_row(coverage, symbol="TAPBPR", source_id="historical_v18_maps", program_id="M0_EXTRA_ANTIGEN_PRESENTATION")
        self.assertTrue(tapbpr_hist["present"])
        self.assertIn("TAPBPR", tapbpr_hist["raw_ids"])
        self.assertIn("TAPBPL", tapbpr_hist["raw_ids"])

    def test_05_present_absent_duplicate_and_ambiguous_coverage(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")
        output = self.temp / "out_coverage"
        rc, _, err = _run_build(output, manifests)
        self.assertEqual(rc, 0, err)
        coverage = _load_json(output / "coverage.json")["rows"]
        hla_tcga = _coverage_row(coverage, symbol="HLA-A", source_id="tcga_gencode_v36", program_id="P_ANTIGEN_PRESENTATION")
        self.assertTrue(hla_tcga["present"])
        self.assertEqual(hla_tcga["matching_row_count"], 1)
        self.assertFalse(hla_tcga["duplicate"])
        self.assertEqual(hla_tcga["aggregate_mapping_status"], "mapped")
        hla_gse = _coverage_row(coverage, symbol="HLA-A", source_id="gse107299_processed", program_id="P_ANTIGEN_PRESENTATION")
        self.assertTrue(hla_gse["present"])
        self.assertEqual(hla_gse["matching_row_count"], 2)
        self.assertTrue(hla_gse["duplicate"])
        self.assertEqual(hla_gse["aggregate_mapping_status"], "mapped")
        self.assertEqual(hla_gse["entrez_ids"], ["SYN_E_A1", "SYN_E_A2"])
        hla_hist = _coverage_row(coverage, symbol="HLA-A", source_id="historical_v18_maps", program_id="P_ANTIGEN_PRESENTATION")
        self.assertTrue(hla_hist["present"])
        self.assertEqual(hla_hist["aggregate_mapping_status"], "ambiguous")
        hla_b_gse = _coverage_row(coverage, symbol="HLA-B", source_id="gse107299_processed", program_id="P_ANTIGEN_PRESENTATION")
        self.assertFalse(hla_b_gse["present"])
        self.assertEqual(hla_b_gse["matching_row_count"], 0)
        self.assertEqual(hla_b_gse["aggregate_mapping_status"], "absent")
        self.assertEqual(hla_b_gse["raw_ids"], [])
        cgas_hist = _coverage_row(coverage, symbol="CGAS", source_id="historical_v18_maps", program_id="M3_VIRAL_MIMICRY")
        self.assertTrue(cgas_hist["present"])
        self.assertIn("MB21D1", cgas_hist["raw_ids"])
        sting_hist = _coverage_row(coverage, symbol="STING1", source_id="historical_v18_maps", program_id="M3_VIRAL_MIMICRY")
        self.assertTrue(sting_hist["present"])
        self.assertIn("TMEM173", sting_hist["raw_ids"])
        tapbp_hist = _coverage_row(coverage, symbol="TAPBP", source_id="historical_v18_maps", program_id="M0_EXTRA_ANTIGEN_PRESENTATION")
        self.assertFalse(tapbp_hist["present"])
        self.assertEqual(tapbp_hist["aggregate_mapping_status"], "absent")

    def test_06_missing_required_source_writes_only_incomplete(self) -> None:
        ann = self.temp / "ann"
        ann.mkdir()
        rows = _standard_rows()
        manifests = [
            _write_source(ann, "tcga_gencode_v36", rows["tcga_gencode_v36"]),
            _write_source(ann, "gse107299_processed", rows["gse107299_processed"]),
        ]
        output = self.temp / "out_incomplete"
        rc, _, err = _run_build(output, manifests)
        self.assertEqual(rc, 3, err)
        self.assertTrue(output.is_dir())
        self.assertEqual(sorted(path.name for path in output.iterdir()), ["INCOMPLETE.json"])
        payload = _load_json(output / "INCOMPLETE.json")
        self.assertEqual(payload["status"], "incomplete_missing_annotations")
        self.assertEqual(payload["required_source_ids"], REQUIRED_SOURCE_IDS)
        self.assertEqual(payload["supplied_source_ids"], ["tcga_gencode_v36", "gse107299_processed"])
        self.assertEqual(payload["missing_source_ids"], ["historical_v18_maps"])
        self.assertEqual(payload["registry_sha256"], _sha256(REGISTRY_PATH.read_bytes()))
        self.assertEqual(payload["schema_sha256"], _sha256(SCHEMA_PATH.read_bytes()))
        self.assertEqual([item["source_id"] for item in payload["manifests"]], ["tcga_gencode_v36", "gse107299_processed"])
        self.assertFalse((output / "COMPLETE.json").exists())
        self.assertFalse((output / "coverage.tsv").exists())
        self.assertFalse((output / "registry_rows.tsv").exists())

    def test_07_unknown_duplicate_hash_path_unknown_field_and_non_pinned(self) -> None:
        ann = self.temp / "ann"
        ann.mkdir()
        rows = _standard_rows()
        good = [_write_source(ann, source_id, rows[source_id]) for source_id in REQUIRED_SOURCE_IDS]

        unknown = _write_source(ann, "not_a_required_source", rows["tcga_gencode_v36"])
        rc, _, err = _run_build(self.temp / "out_unknown_source", good + [unknown])
        self.assertEqual(rc, 3, err)
        self.assertIn("unknown-source-id", err)
        self.assertFalse((self.temp / "out_unknown_source").exists())

        duplicate = _write_source(ann / "dup", "tcga_gencode_v36", rows["tcga_gencode_v36"])
        rc, _, err = _run_build(self.temp / "out_dup_source", good + [duplicate])
        self.assertEqual(rc, 3, err)
        self.assertIn("duplicate-source-id", err)

        bad_hash = _write_source(ann / "bad_hash", "tcga_gencode_v36", rows["tcga_gencode_v36"], table_sha256="ab" * 32)
        rc, _, err = _run_build(self.temp / "out_bad_hash", [bad_hash, good[1], good[2]])
        self.assertEqual(rc, 3, err)
        self.assertIn("table-hash-mismatch", err)

        missing_table = _write_source(
            ann / "missing_table",
            "tcga_gencode_v36",
            rows["tcga_gencode_v36"],
            table_path="does-not-exist.tsv",
            table_sha256="ab" * 32,
        )
        rc, _, err = _run_build(self.temp / "out_missing_table", [missing_table, good[1], good[2]])
        self.assertEqual(rc, 3, err)
        self.assertIn("path error", err)

        extra_field = _write_source(
            ann / "extra",
            "tcga_gencode_v36",
            rows["tcga_gencode_v36"],
            extra_fields={"unexpected": "field"},
        )
        rc, _, err = _run_build(self.temp / "out_unknown_manifest_field", [extra_field, good[1], good[2]])
        self.assertEqual(rc, 3, err)
        self.assertIn("unknown-field", err)

        non_pinned = _write_source(ann / "pending", "tcga_gencode_v36", rows["tcga_gencode_v36"], source_status="pending")
        rc, _, err = _run_build(self.temp / "out_non_pinned", [non_pinned, good[1], good[2]])
        self.assertEqual(rc, 3, err)
        self.assertIn("non-pinned", err)

        registry = _load_official_registry()
        registry["unexpected_field"] = "no"
        rc, _, err = _run_build(
            self.temp / "out_unknown_registry_field",
            good,
            registry=_write_json(self.temp / "unknown_registry.json", registry),
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("unknown-field", err)

    def test_08_forbidden_columns_and_malformed_annotation_records(self) -> None:
        ann = self.temp / "ann"
        ann.mkdir()
        rows = _standard_rows()
        good_gse = _write_source(ann, "gse107299_processed", rows["gse107299_processed"])
        good_hist = _write_source(ann, "historical_v18_maps", rows["historical_v18_maps"])

        def fail_tcga(table_bytes: bytes | None = None, table_rows=None, label: str = "x") -> tuple[int, str]:
            target = ann / label
            target.mkdir(parents=True, exist_ok=True)
            if table_rows is None:
                table_rows = rows["tcga_gencode_v36"]
            manifest = _write_source(target, "tcga_gencode_v36", table_rows, table_bytes=table_bytes)
            rc, _, err = _run_build(self.temp / f"out_{label}", [manifest, good_gse, good_hist])
            return rc, err

        patient_header = "raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status\tpatient_id\nHLA-A\tHLA-A\t1\tE\tmapped\tTCGA-00\n"
        rc, err = fail_tcga(table_bytes=patient_header.encode("utf-8"), label="patient")
        self.assertEqual(rc, 3, err)
        self.assertTrue("forbidden-column" in err or "header-mismatch" in err)

        expression_header = "raw_id\tcanonical_symbol\tentrez_id\tensembl_id\texpression\nHLA-A\tHLA-A\t1\tE\t1.0\n"
        rc, err = fail_tcga(table_bytes=expression_header.encode("utf-8"), label="expression")
        self.assertEqual(rc, 3, err)
        self.assertTrue("forbidden-column" in err or "header-mismatch" in err)

        sample_header = "raw_id\tsample_id\tentrez_id\tensembl_id\tmapping_status\nHLA-A\tS1\t1\tE\tmapped\n"
        rc, err = fail_tcga(table_bytes=sample_header.encode("utf-8"), label="sample")
        self.assertEqual(rc, 3, err)
        self.assertTrue("forbidden-column" in err or "header-mismatch" in err)

        value_header = "raw_id\tcanonical_symbol\tvalue\tensembl_id\tmapping_status\nHLA-A\tHLA-A\t1\tE\tmapped\n"
        rc, err = fail_tcga(table_bytes=value_header.encode("utf-8"), label="value")
        self.assertEqual(rc, 3, err)
        self.assertTrue("forbidden-column" in err or "header-mismatch" in err)

        rc, err = fail_tcga(table_bytes=b"\xff\xfe raw", label="utf8")
        self.assertEqual(rc, 3, err)
        self.assertIn("malformed-utf8", err)

        rc, err = fail_tcga(table_bytes=b"raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status\nHLA-A\tHLA-A\t1\tE\tmapped\r", label="cr")
        self.assertEqual(rc, 3, err)
        self.assertIn("cr-record-forbidden", err)

        rc, err = fail_tcga(table_bytes=b"\x1f\x8b" + b"not-a-table", label="gzip")
        self.assertEqual(rc, 3, err)
        self.assertIn("compressed-table-forbidden", err)

        rc, err = fail_tcga(table_rows=[("", "HLA-A", "1", "E", "mapped")], label="empty_raw")
        self.assertEqual(rc, 3, err)
        self.assertIn("empty-raw-id", err)

        dup = ("HLA-A", "HLA-A", "1", "E", "mapped")
        rc, err = fail_tcga(table_rows=[dup, dup], label="dup_row")
        self.assertEqual(rc, 3, err)
        self.assertIn("duplicate-exact-row", err)

        rc, err = fail_tcga(table_rows=[("HLA-A", "HLA-A", "", "", "mapped")], label="mapped_no_id")
        self.assertEqual(rc, 3, err)
        self.assertIn("mapped-requires-identifier", err)

        rc, err = fail_tcga(table_rows=[("HLA-A", "", "1", "", "unmapped")], label="unmapped_id")
        self.assertEqual(rc, 3, err)
        self.assertIn("unmapped-requires-empty-identifiers", err)

        bad_line = "raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status\nHLA-A\tHLA-A\t1\n"
        rc, err = fail_tcga(table_bytes=bad_line.encode("utf-8"), label="field_count")
        self.assertEqual(rc, 3, err)
        self.assertIn("field-count", err)

        nul = "raw_id\tcanonical_symbol\tentrez_id\tensembl_id\tmapping_status\nHLA-A\tHLA-A\t1\tE\tmapped\n".encode("utf-8")
        nul = nul.replace(b"HLA-A", b"HLA\x00A", 1)
        rc, err = fail_tcga(table_bytes=nul, label="nul_bytes")
        self.assertEqual(rc, 3, err)
        self.assertIn("nul-byte", err)

    def test_09_byte_identical_builds_and_existing_output_refusal(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")
        first = self.temp / "out_one"
        second = self.temp / "out_two"
        rc1, _, err1 = _run_build(first, manifests)
        rc2, _, err2 = _run_build(second, manifests)
        self.assertEqual(rc1, 0, err1)
        self.assertEqual(rc2, 0, err2)
        names = ["registry_rows.tsv", "registry_rows.json", "coverage.tsv", "coverage.json", "checksums.json", "COMPLETE.json"]
        for name in names:
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

        marker = first / "marker.txt"
        marker.write_text("keep", encoding="utf-8")
        before = {path.name: path.read_bytes() for path in first.iterdir()}
        rc, _, err = _run_build(first, manifests)
        self.assertEqual(rc, 2, err)
        self.assertIn("must not already exist", err)
        after = {path.name: path.read_bytes() for path in first.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

        existing_file = self.temp / "existing_file"
        existing_file.write_text("no", encoding="utf-8")
        rc, _, err = _run_build(existing_file, manifests)
        self.assertEqual(rc, 2, err)
        self.assertEqual(existing_file.read_text(encoding="utf-8"), "no")

    def test_10_no_invented_scoring_model_patient_or_external_access(self) -> None:
        module_path = REPO_ROOT / "tools" / "b_gene_registry" / "__main__.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                imported.add(node.module)
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported), imported.intersection(FORBIDDEN_IMPORTS))

        manifests = _write_standard_sources(self.temp / "ann")
        output = self.temp / "out_no_science"
        rc, _, err = _run_build(output, manifests)
        self.assertEqual(rc, 0, err)
        allowed_int_keys = {
            "program_index",
            "member_index",
            "matching_row_count",
            "row_count",
            "program_count",
            "registry_row_count",
            "coverage_row_count",
            "null_membership_program_count",
        }
        forbidden_exact_keys = FORBIDDEN_OUTPUT_KEYS | {
            "model",
            "intercept",
            "sign",
            "signs",
            "patient",
            "sample",
            "value",
        }
        for name in ["registry_rows.json", "coverage.json", "checksums.json", "COMPLETE.json"]:
            payload = _load_json(output / name)
            keys = _collect_keys(payload)
            self.assertTrue(forbidden_exact_keys.isdisjoint(keys), keys.intersection(forbidden_exact_keys))
            self._assert_no_invented_numeric_fields(payload, allowed_int_keys=allowed_int_keys)
            self.assertNotIn("delta_r2", (output / name).read_text(encoding="utf-8"))
        source_programs = {program["id"]: program for program in _load_official_registry()["programs"]}
        rows_payload = _load_json(output / "registry_rows.json")
        for row in rows_payload["rows"]:
            source = source_programs[row["program_id"]]
            for field in ("membership_status", "direction_status", "weights_status", "scoring_status", "predictor_status"):
                self.assertIsInstance(row[field], str)
                self.assertEqual(row[field], source[field])
                self.assertIsNone(re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", row[field].strip()))
        for null_program in rows_payload["null_membership_programs"]:
            source = source_programs[null_program["program_id"]]
            self.assertEqual(null_program["membership_status"], "unresolved")
            self.assertEqual(null_program["membership_status"], source["membership_status"])
            self.assertIsNone(null_program["membership_sha256"])
            self.assertEqual(null_program["scoring_status"], source["scoring_status"])
            self.assertEqual(null_program["weights_status"], source["weights_status"])
            self.assertEqual(null_program["direction_status"], source["direction_status"])
        tsv_headers = (output / "registry_rows.tsv").read_text(encoding="utf-8").split("\n")[0].split("\t")
        self.assertTrue(forbidden_exact_keys.isdisjoint(tsv_headers))
        rc, _, err = _run_cli([])
        self.assertEqual(rc, 2)
        rc, _, err = _run_cli(["inspect"])
        self.assertEqual(rc, 2)

    def _assert_no_invented_numeric_fields(self, payload: object, *, allowed_int_keys: set[str], path: str = "$") -> None:
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, bool):
                    continue
                if isinstance(value, int):
                    self.assertIn(key, allowed_int_keys, f"{path}.{key} invented numeric field")
                elif isinstance(value, float):
                    self.fail(f"{path}.{key} invented floating-point field")
                else:
                    self._assert_no_invented_numeric_fields(value, allowed_int_keys=allowed_int_keys, path=f"{path}.{key}")
            return
        if isinstance(payload, list):
            if payload and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in payload):
                self.fail(f"{path} invented numeric vector")
            for index, item in enumerate(payload):
                self._assert_no_invented_numeric_fields(item, allowed_int_keys=allowed_int_keys, path=f"{path}[{index}]")

    def test_11_numeric_status_and_manifest_order_do_not_change_bytes(self) -> None:
        registry = _load_official_registry()
        registry["programs"][0]["weights_status"] = "-0.25"
        manifests = _write_standard_sources(self.temp / "ann")
        rc, _, err = _run_build(
            self.temp / "out_numeric",
            manifests,
            registry=_write_json(self.temp / "numeric.json", registry),
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("numeric-status-forbidden", err)

        ann = self.temp / "ann_order"
        ann.mkdir()
        rows = _standard_rows()
        reverse_ids = list(reversed(REQUIRED_SOURCE_IDS))
        manifests = [_write_source(ann, source_id, rows[source_id]) for source_id in reverse_ids]
        first = self.temp / "out_order_a"
        second = self.temp / "out_order_b"
        rc1, _, err1 = _run_build(first, manifests)
        rc2, _, err2 = _run_build(second, list(reversed(manifests)))
        self.assertEqual(rc1, 0, err1)
        self.assertEqual(rc2, 0, err2)
        self.assertEqual((first / "coverage.json").read_bytes(), (second / "coverage.json").read_bytes())
        self.assertEqual((first / "COMPLETE.json").read_bytes(), (second / "COMPLETE.json").read_bytes())

    def _assert_exit3_no_complete(self, output: Path, rc: int, err: str, token: str) -> None:
        self.assertEqual(rc, 3, err)
        self.assertIn(token, err)
        self.assertFalse(output.exists())
        self.assertFalse((output / "COMPLETE.json").exists())
        self.assertFalse((output / "INCOMPLETE.json").exists())

    def test_12_schema_identity_and_closed_objects_required(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")

        schema = _load_official_schema()
        del schema["$schema"]
        rc, _, err = _run_build(
            self.temp / "out_schema_missing_dialect",
            manifests,
            schema=_write_json(self.temp / "schema_missing_dialect.json", schema),
        )
        self._assert_exit3_no_complete(self.temp / "out_schema_missing_dialect", rc, err, "draft-2020-12-declaration-required")

        schema = _load_official_schema()
        schema["$schema"] = "https://json-schema.org/draft-07/schema"
        rc, _, err = _run_build(
            self.temp / "out_schema_wrong_dialect",
            manifests,
            schema=_write_json(self.temp / "schema_wrong_dialect.json", schema),
        )
        self._assert_exit3_no_complete(self.temp / "out_schema_wrong_dialect", rc, err, "draft-2020-12-declaration-required")

        schema = _load_official_schema()
        schema["$id"] = "https://example.invalid/weak.schema.json"
        rc, _, err = _run_build(
            self.temp / "out_schema_wrong_id",
            manifests,
            schema=_write_json(self.temp / "schema_wrong_id.json", schema),
        )
        self._assert_exit3_no_complete(self.temp / "out_schema_wrong_id", rc, err, "schema-id-mismatch")

        weak = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://local.invalid/specs/B/gene_set_registry.schema.json",
            "type": "object",
        }
        rc, _, err = _run_build(
            self.temp / "out_schema_minimal",
            manifests,
            schema=_write_json(self.temp / "schema_minimal.json", weak),
        )
        self._assert_exit3_no_complete(self.temp / "out_schema_minimal", rc, err, "object-must-reject-unknown-fields")

        schema = _load_official_schema()
        schema["additionalProperties"] = True
        rc, _, err = _run_build(
            self.temp / "out_schema_open_root",
            manifests,
            schema=_write_json(self.temp / "schema_open_root.json", schema),
        )
        self._assert_exit3_no_complete(self.temp / "out_schema_open_root", rc, err, "object-must-reject-unknown-fields")

        schema = _load_official_schema()
        schema["$defs"]["program"]["additionalProperties"] = True
        rc, _, err = _run_build(
            self.temp / "out_schema_open_program",
            manifests,
            schema=_write_json(self.temp / "schema_open_program.json", schema),
        )
        self._assert_exit3_no_complete(self.temp / "out_schema_open_program", rc, err, "object-must-reject-unknown-fields")

        schema = _load_official_schema()
        del schema["$defs"]["program"]["properties"]["raw_gene_symbols"]["oneOf"][0]["uniqueItems"]
        rc, _, err = _run_build(
            self.temp / "out_schema_semantically_weakened",
            manifests,
            schema=_write_json(self.temp / "schema_semantically_weakened.json", schema),
        )
        self._assert_exit3_no_complete(
            self.temp / "out_schema_semantically_weakened",
            rc,
            err,
            "schema-contract-mismatch",
        )

    def test_13_required_aliases_and_tapbp_tapbpl_pair_locked(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")

        registry = _load_official_registry()
        registry["canonicalization"]["alias_rules"] = [
            rule for rule in registry["canonicalization"]["alias_rules"] if rule["raw_symbol"] != "MB21D1"
        ]
        rc, _, err = _run_build(
            self.temp / "out_alias_missing",
            manifests,
            registry=_write_json(self.temp / "alias_missing.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_alias_missing", rc, err, "missing-required-alias")
        self.assertIn("MB21D1", err)

        registry = _load_official_registry()
        for rule in registry["canonicalization"]["alias_rules"]:
            if rule["raw_symbol"] == "TMEM173":
                rule["canonical_symbol"] = "STING"
        rc, _, err = _run_build(
            self.temp / "out_alias_redirect",
            manifests,
            registry=_write_json(self.temp / "alias_redirect.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_alias_redirect", rc, err, "required-alias-mismatch")
        self.assertIn("TMEM173", err)

        registry = _load_official_registry()
        for rule in registry["canonicalization"]["alias_rules"]:
            if rule["raw_symbol"] == "TAPBPR":
                rule["canonical_symbol"] = "TAPBP"
        rc, _, err = _run_build(
            self.temp / "out_alias_collapse",
            manifests,
            registry=_write_json(self.temp / "alias_collapse.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_alias_collapse", rc, err, "required-alias-mismatch")

        registry = _load_official_registry()
        registry["canonicalization"]["do_not_collapse"] = []
        rc, _, err = _run_build(
            self.temp / "out_pair_omitted",
            manifests,
            registry=_write_json(self.temp / "pair_omitted.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_pair_omitted", rc, err, "missing-required-pair")

        registry = _load_official_registry()
        registry["canonicalization"]["do_not_collapse"] = [["TAPBPL", "TAPBP"]]
        rc, _, err = _run_build(
            self.temp / "out_pair_reversed",
            manifests,
            registry=_write_json(self.temp / "pair_reversed.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_pair_reversed", rc, err, "missing-required-pair")

        registry = _load_official_registry()
        registry["canonicalization"]["alias_rules"].append(
            {"raw_symbol": "TAPBP", "canonical_symbol": "TAPBPL", "evidence": "synthetic-conflict"}
        )
        rc, _, err = _run_build(
            self.temp / "out_pair_aliased",
            manifests,
            registry=_write_json(self.temp / "pair_aliased.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_pair_aliased", rc, err, "collapsed-distinct-loci")

    def test_14_v02_program_ids_and_layers_locked(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")

        registry = _load_official_registry()
        registry["programs"] = [program for program in registry["programs"] if program["id"] != "HOPE_18"]
        rc, _, err = _run_build(
            self.temp / "out_program_missing",
            manifests,
            registry=_write_json(self.temp / "program_missing.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_program_missing", rc, err, "minItems")

        registry = _load_official_registry()
        extra = json.loads(json.dumps(registry["programs"][-1]))
        extra["id"] = "M7_SCOPE_DRIFT"
        extra["legacy_id"] = None
        extra["membership_sha256"] = _membership_sha256(extra["raw_gene_symbols"])
        registry["programs"].append(extra)
        rc, _, err = _run_build(
            self.temp / "out_program_extra",
            manifests,
            registry=_write_json(self.temp / "program_extra.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_program_extra", rc, err, "v0.2-program-ids-mismatch")
        self.assertIn("M7_SCOPE_DRIFT", err)

        registry = _load_official_registry()
        m5 = next(program for program in registry["programs"] if program["id"] == "M5_CHECKPOINT_CANDIDATES")
        m5["layer"] = "exploratory"
        rc, _, err = _run_build(
            self.temp / "out_program_relayer",
            manifests,
            registry=_write_json(self.temp / "program_relayer.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_program_relayer", rc, err, "v0.2-program-layer-mismatch")
        self.assertIn("M5_CHECKPOINT_CANDIDATES", err)

        registry = _load_official_registry()
        hope = next(program for program in registry["programs"] if program["id"] == "HOPE_18")
        hope["id"] = "HOPE_REPLACED"
        rc, _, err = _run_build(
            self.temp / "out_program_replaced",
            manifests,
            registry=_write_json(self.temp / "program_replaced.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_program_replaced", rc, err, "v0.2-program-ids-mismatch")
        self.assertIn("HOPE_18", err)

    def test_15_rfc3339_full_date_rejects_basic_isoformat(self) -> None:
        manifests = _write_standard_sources(self.temp / "ann")
        registry = _load_official_registry()
        registry["decision_date"] = "20260910"
        rc, _, err = _run_build(
            self.temp / "out_basic_date",
            manifests,
            registry=_write_json(self.temp / "basic_date.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_basic_date", rc, err, "format-date")
        from datetime import date as date_cls

        self.assertEqual(date_cls.fromisoformat("20260910").isoformat(), "2026-09-10")

        registry = _load_official_registry()
        registry["integration_date"] = "2026-02-30"
        rc, _, err = _run_build(
            self.temp / "out_invalid_date",
            manifests,
            registry=_write_json(self.temp / "invalid_date.json", registry),
        )
        self._assert_exit3_no_complete(self.temp / "out_invalid_date", rc, err, "format-date")


if __name__ == "__main__":
    unittest.main()
