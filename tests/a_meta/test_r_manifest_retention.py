from __future__ import annotations

import json

import pytest

from tools.a_meta.r_manifest import run_r_sanitised
from tools.r_bridge import FakeR, RScriptError


def test_sanitised_retention_keeps_private_stages_and_stable_published_manifest(tmp_path):
    script = tmp_path / "invented.R"
    script.write_text("# invented bridge fixture\n", encoding="utf-8")
    source = tmp_path / "input.tsv"
    source.write_text("value\n1\n", encoding="utf-8")
    output_dir = tmp_path / "published"
    retention_dir = tmp_path / "private-work"
    runner = FakeR({
        "invented.R": {
            "result.tsv": "value\n1\n",
            "._result.tsv": b"\x00\x05\x16\x07\x00\x00\x00\x00metadata",
        }
    })

    first = run_r_sanitised(
        script,
        {"input": source},
        {"expected_outputs": ["result.tsv"], "kind": "invented"},
        output_dir,
        script_id="invented_r_fixture",
        runner=runner,
        retention_dir=retention_dir,
    )
    published_manifest = json.loads((output_dir / "manifest.json").read_text())
    assert published_manifest == first.manifest
    assert "script_path" not in published_manifest
    assert (output_dir / "result.tsv").read_text() == "value\n1\n"
    assert not (output_dir / "bridge-runtime.json").exists()
    assert not (output_dir / "._result.tsv").exists()
    assert len(list(retention_dir.rglob("bridge-runtime.json"))) == 1
    assert len(list(retention_dir.rglob("._result.tsv"))) == 1
    assert all(str(tmp_path) not in str(value) for value in published_manifest.values())

    second = run_r_sanitised(
        script,
        {"input": source},
        {"expected_outputs": ["result.tsv"], "kind": "invented"},
        output_dir,
        script_id="invented_r_fixture",
        runner=runner,
        retention_dir=retention_dir,
    )
    assert second.manifest == first.manifest
    assert len(list(retention_dir.rglob("bridge-runtime.json"))) == 2


def test_sanitised_retention_keeps_failed_stage_without_publishing(tmp_path):
    script = tmp_path / "invented-failure.R"
    script.write_text("# invented failing bridge fixture\n", encoding="utf-8")
    retention_dir = tmp_path / "private-failed-work"
    output_dir = tmp_path / "failed-published"

    with pytest.raises(RScriptError):
        run_r_sanitised(
            script,
            {},
            {"expected_outputs": ["result.tsv"]},
            output_dir,
            script_id="invented_failure_fixture",
            runner=FakeR({}),
            retention_dir=retention_dir,
        )

    assert list(retention_dir.rglob("config.json"))
    assert not output_dir.exists()
