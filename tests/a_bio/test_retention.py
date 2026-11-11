from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.a_bio import runner as a_bio_runner
from tests.a_bio.fakes import FakeBridge
from tests.a_bio.helpers import write_synthetic_materialization


class _FailFirstPathwayBridge(FakeBridge):
    def __init__(self):
        self.failed = False

    def __call__(self, command, *, cwd, env, capture_output, text, check=False):
        if Path(command[-2]).name == "singscore.R" and not self.failed:
            config = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
            if config["config"]["family"] == "pathway":
                self.failed = True
                output_dir = Path(config["output_dir"])
                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / "invented_failure_marker.txt").write_text(
                    "invented R failure stage\n", encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 17, "", "invented R failure")
        return super().__call__(
            command,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            text=text,
            check=check,
        )


def _retained_script_names(retention_dir):
    names = set()
    for path in retention_dir.rglob("manifest.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        script = manifest.get("script") or manifest.get("script_path")
        if script:
            names.add(Path(script).name)
    return names


def test_a_bio_retains_successful_and_failed_r_stages_outside_public_manifest(tmp_path):
    runtime = tmp_path / "runtime"
    cohort_ids = (
        "invented_retention_a",
        "invented_retention_b",
        "invented_retention_c",
    )
    manifests = tuple(
        write_synthetic_materialization(
            runtime,
            cohort_id=cohort_id,
            endpoint_families=("orr",),
            cancer="melanoma",
            include_frozen_genes=True,
        )
        for cohort_id in cohort_ids
    )
    retention_dir = tmp_path / "private-work"

    summary = a_bio_runner.run(
        "outcomes",
        cohorts=cohort_ids,
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=manifests,
        meta_ranking_contract=a_bio_runner.MetaRankingContract(
            contract_id="invented-retention-v1", statistic="estimate",
        ),
        retention_dir=retention_dir,
        runner=_FailFirstPathwayBridge(),
    )

    run_root = tmp_path / "results" / "A" / "a_bio" / "outcomes" / summary["run_id"]
    public_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    private_files = [path for path in retention_dir.rglob("*") if path.is_file()]

    assert summary["status"] == "partial"
    assert any(path.name == "bridge-runtime.json" for path in private_files)
    assert any(path.name == "invented_failure_marker.txt" for path in private_files)
    assert any(path.name == "config.json" for path in private_files)
    assert not any(path.name == "bridge-runtime.json" for path in run_root.rglob("*"))
    assert not any(path.name == "invented_failure_marker.txt" for path in run_root.rglob("*"))
    assert all("private-work" not in name for name in public_manifest["output_sha256"])
    assert str(retention_dir) not in json.dumps(public_manifest, sort_keys=True)
    assert {"singscore.R", "meta_rma.R", "de_limma.R", "fgsea_rank.R"} <= _retained_script_names(
        retention_dir
    )

    cached = a_bio_runner.run(
        "outcomes",
        cohorts=cohort_ids,
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=manifests,
        meta_ranking_contract=a_bio_runner.MetaRankingContract(
            contract_id="invented-retention-v1", statistic="estimate",
        ),
        retention_dir=tmp_path / "alternate-private-work",
        runner=_FailFirstPathwayBridge(),
    )
    assert cached["run_id"] == summary["run_id"]
    assert not (tmp_path / "alternate-private-work").exists()


def test_outcome_free_retains_qc_pca_and_panel_bridge_stages_by_default(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("THESIS_RUNTIME", str(runtime))
    cohort_id = "invented_retention_outcome_free"
    manifest = write_synthetic_materialization(
        runtime,
        cohort_id=cohort_id,
        endpoint_families=("orr",),
        cancer="melanoma",
        include_frozen_genes=True,
    )
    summary = a_bio_runner.run(
        "outcome-free",
        cohorts=(cohort_id,),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=(manifest,),
        runner=FakeBridge(),
    )

    run_root = tmp_path / "results" / "A" / "a_bio" / "outcome-free" / summary["run_id"]
    private_work = run_root.with_name(f".{run_root.name}.work")
    public_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))

    assert summary["status"] == "complete"
    assert "bulk_qc_pca.R" in _retained_script_names(private_work)
    assert any(path.name == "bridge-runtime.json" for path in private_work.rglob("*"))
    assert not any(path.name == "bridge-runtime.json" for path in run_root.rglob("*"))
    assert str(private_work) not in json.dumps(public_manifest, sort_keys=True)
