from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.a_meta.random_streams import RANDOM_STREAMS, derive_task_seed, seed_for_task
from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "r/scripts/freeze_checks/random_streams.R"


@pytest.mark.requires_r
def test_r_and_python_random_stream_contracts_match_on_synthetic_indices(tmp_path):
    receipt_root = tmp_path / "synthetic-receipts"
    result = run_r(
        SCRIPT,
        {},
        {
            "receipt_dir": str(receipt_root),
            "expected_outputs": ["checks.tsv", "task_seeds.tsv", "random_stream_table.tsv"],
        },
        tmp_path / "random-stream-checks",
    )

    with result.outputs["random_stream_table.tsv"].open(newline="", encoding="utf-8") as stream:
        r_streams = {row["stream"]: row for row in csv.DictReader(stream, delimiter="\t")}
    assert set(r_streams) == set(RANDOM_STREAMS)
    for stream, contract in RANDOM_STREAMS.items():
        assert int(r_streams[stream]["seed"]) == contract.seed
        assert r_streams[stream]["task_id"] == contract.task_id
        assert (r_streams[stream]["reported_only"].casefold() == "true") is contract.reported_only
    assert seed_for_task("a_p2_bootstrap") == int(r_streams["a_p2_bootstrap"]["seed"])

    with result.outputs["task_seeds.tsv"].open(newline="", encoding="utf-8") as stream:
        task_rows = list(csv.DictReader(stream, delimiter="\t"))
    for row in task_rows:
        assert int(row["seed"]) == derive_task_seed(row["stream"], row["task_id"])

    with result.outputs["checks.tsv"].open(newline="", encoding="utf-8") as stream:
        checks = {row["check"]: row["value"] for row in csv.DictReader(stream, delimiter="\t")}
    assert checks["a_p2_repeat_identical"] == "TRUE"
    assert checks["a_p2_other_seed_differs"] == "TRUE"
    assert checks["a_p2_strata_order"] == "R,NR"
    assert checks["a_p1_strata_order"] == "O,SD,PD"
    assert checks["split_r_train_odd_n"] == "4"
    assert checks["split_nr_train_odd_n"] == "2"
    assert checks["a_p2_reordered_input_equivalent"] == "TRUE"
    assert checks["split_reordered_input_equivalent"] == "TRUE"
    assert checks["a_p2_tiny_expected_assignment"] == "TRUE"

    bootstrap_receipt = json.loads((receipt_root / "bootstrap" / "receipt.json").read_text())
    split_receipt = json.loads((receipt_root / "splits" / "receipt.json").read_text())
    assert bootstrap_receipt["stream"] == "a_p2_bootstrap"
    assert len(bootstrap_receipt["receipt_sha256"]) == 64
    assert split_receipt["stream"] == "a_p2_splits"
    assert len(split_receipt["receipt_sha256"]) == 64
