import hashlib
import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from tools.r_bridge import FakeR, RScriptError, run_r


ROOT = Path(__file__).resolve().parents[2]
R_PROJECT = ROOT / "r"
R_SCRIPT = shutil.which("Rscript")


@lru_cache(maxsize=1)
def _renv_library_available():
    if not R_SCRIPT:
        return False
    env = os.environ.copy()
    for name in ("R_LIBS", "R_LIBS_USER", "R_LIBS_SITE"):
        env.pop(name, None)
    env.update(
        {
            "RENV_PROJECT": str(R_PROJECT),
            "RENV_CONFIG_SANDBOX_ENABLED": "FALSE",
            "R_ENVIRON_USER": str(R_PROJECT / ".Renviron"),
            "R_PROFILE_USER": str(R_PROJECT / ".Rprofile"),
        }
    )
    probe = (
        'stopifnot(normalizePath(renv::project()) == normalizePath(getwd())); '
        'stopifnot(normalizePath(.libPaths()[1]) == normalizePath(renv::paths$library()))'
    )
    try:
        result = subprocess.run(
            [R_SCRIPT, "--no-save", "--no-restore", "--no-site-file", "-e", probe],
            cwd=R_PROJECT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _script(tmp_path, name="fake.R"):
    path = tmp_path / name
    path.write_text("# synthetic test script\n")
    return path


def test_fake_runner_publishes_outputs_and_hash_provenance(tmp_path):
    class InspectingFakeR(FakeR):
        def __call__(self, command, **kwargs):
            self.command = command
            self.kwargs = kwargs
            return super().__call__(command, **kwargs)

    script = _script(tmp_path)
    input_path = tmp_path / "counts.tsv"
    input_path.write_text("gene\tsample1\ns1\t3\n")
    output_dir = tmp_path / "published"
    runner = InspectingFakeR({"fake.R": {"sums.tsv": "sample\tsum\nsample1\t3\n"}})

    result = run_r(
        script,
        {"counts": input_path},
        {"expected_outputs": ["sums.tsv"], "method": "synthetic"},
        output_dir,
        runner=runner,
    )

    assert result.outputs == {"sums.tsv": output_dir / "sums.tsv"}
    assert result.outputs["sums.tsv"].read_text() == "sample\tsum\nsample1\t3\n"
    manifest = result.manifest
    assert manifest["script_path"] == str(script.resolve())
    assert manifest["script_sha256"] == hashlib.sha256(script.read_bytes()).hexdigest()
    assert manifest["input_sha256"] == {
        "counts": hashlib.sha256(input_path.read_bytes()).hexdigest()
    }
    assert manifest["config"] == {"expected_outputs": ["sums.tsv"], "method": "synthetic"}
    assert manifest["output_sha256"]["sums.tsv"] == hashlib.sha256(
        result.outputs["sums.tsv"].read_bytes()
    ).hexdigest()
    assert manifest["r_version"] == "FakeR"
    assert manifest["bioconductor_version"] == "FakeBioconductor"
    assert manifest["session_info"] == "FakeR sessionInfo()\n"
    assert manifest["r_library"] == "~/.fake/renv/library"
    assert manifest["package_versions"] == {"jsonlite": "2.0.0"}
    assert runner.command[1:4] == ["--no-save", "--no-restore", "--no-site-file"]
    assert runner.kwargs["cwd"] == str(R_PROJECT)
    assert runner.kwargs["env"]["RENV_PROJECT"] == str(R_PROJECT)
    assert runner.kwargs["env"]["R_ENVIRON_USER"] == str(R_PROJECT / ".Renviron")
    assert runner.kwargs["env"]["R_PROFILE_USER"] == str(R_PROJECT / ".Rprofile")
    assert not {"R_LIBS", "R_LIBS_USER", "R_LIBS_SITE"} & runner.kwargs["env"].keys()
    assert (output_dir / "manifest.json").is_file()
    assert json.loads((output_dir / "manifest.json").read_text()) == manifest
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "counts.tsv",
        "fake.R",
        "published",
    ]
    reused = run_r(
        script,
        {"counts": input_path},
        {"expected_outputs": ["sums.tsv"], "method": "synthetic"},
        output_dir,
        runner=runner,
    )
    assert reused.manifest == manifest


def test_declared_outputs_allow_exfat_appledouble_sidecars_on_publish_and_reuse(tmp_path):
    script = _script(tmp_path)
    output_dir = tmp_path / "published"
    runner = FakeR({
        "fake.R": {
            "result.tsv": "value\n1\n",
            "._result.tsv": "filesystem metadata\n",
        }
    })

    first = run_r(
        script,
        {},
        {"expected_outputs": ["result.tsv"]},
        output_dir,
        runner=runner,
    )
    second = run_r(
        script,
        {},
        {"expected_outputs": ["result.tsv"]},
        output_dir,
        runner=runner,
    )

    assert first.manifest == second.manifest
    assert first.outputs["result.tsv"].read_text() == "value\n1\n"
    assert (output_dir / "._result.tsv").is_file()


@pytest.mark.parametrize("damage", ["corrupt", "delete"])
def test_identical_manifest_reuse_checks_published_bytes(tmp_path, damage):
    script = _script(tmp_path)
    output_dir = tmp_path / "published"
    config = {"expected_outputs": ["result.tsv"]}
    runner = FakeR({"fake.R": {"result.tsv": "original\n"}})
    run_r(script, {}, config, output_dir, runner=runner)
    output = output_dir / "result.tsv"
    if damage == "corrupt":
        output.write_text("tampered\n")
    else:
        output.unlink()

    with pytest.raises((ValueError, FileExistsError), match="(?i)(hash|missing|integrity|output)"):
        run_r(script, {}, config, output_dir, runner=runner)

    if damage == "corrupt":
        assert output.read_text() == "tampered\n"
    else:
        assert not output.exists()


@pytest.mark.parametrize("name", ["./manifest.json", "config.json", "sessionInfo.txt"])
def test_reserved_and_noncanonical_output_names_are_rejected(tmp_path, name):
    script = _script(tmp_path)
    with pytest.raises(ValueError):
        run_r(
            script,
            {},
            {"expected_outputs": [name]},
            tmp_path / "published",
            runner=FakeR({"fake.R": {name: "bad\n"}}),
        )


def test_duplicate_normalized_output_names_are_rejected(tmp_path):
    script = _script(tmp_path)
    with pytest.raises(ValueError, match="(?i)duplicate"):
        run_r(
            script,
            {},
            {"expected_outputs": ["result.tsv", "result.tsv"]},
            tmp_path / "published",
            runner=FakeR({"fake.R": {"result.tsv": "same\n"}}),
        )


def test_missing_fake_script_raises_and_does_not_publish(tmp_path):
    script = _script(tmp_path, "missing.R")
    output_dir = tmp_path / "published"

    with pytest.raises(RScriptError) as error:
        run_r(
            script,
            {},
            {"expected_outputs": ["result.tsv"]},
            output_dir,
            runner=FakeR({"other.R": {"result.tsv": "unused\n"}}),
        )

    assert error.value.script_name == "missing.R"
    assert "No canned output for missing.R" in error.value.stderr_tail
    assert not output_dir.exists()


def test_fake_zero_exit_missing_expected_output_raises_rscript_error(tmp_path):
    script = _script(tmp_path)
    with pytest.raises(RScriptError, match="missing expected output") as error:
        run_r(
            script,
            {},
            {"expected_outputs": ["result.tsv"]},
            tmp_path / "published",
            runner=FakeR({"fake.R": {}}),
        )
    assert error.value.returncode == 0


def test_fake_unexpected_staged_file_raises_rscript_error(tmp_path):
    script = _script(tmp_path)
    output_dir = tmp_path / "published"
    with pytest.raises(RScriptError, match="unexpected staged files.*surprise.tsv"):
        run_r(
            script,
            {},
            {"expected_outputs": ["result.tsv"]},
            output_dir,
            runner=FakeR(
                {"fake.R": {"result.tsv": "expected\n", "surprise.tsv": "extra\n"}}
            ),
        )
    assert not output_dir.exists()


def test_runner_failure_keeps_existing_destination_untouched(tmp_path):
    class FailedRunner:
        def __call__(self, command, **kwargs):
            return subprocess.CompletedProcess(
                command, 9, stdout="captured output\n", stderr="\n".join(f"error {i}" for i in range(60))
            )

    script = _script(tmp_path)
    output_dir = tmp_path / "published"
    output_dir.mkdir()
    sentinel = output_dir / "keep.txt"
    sentinel.write_text("original\n")

    with pytest.raises(RScriptError) as error:
        run_r(
            script,
            {},
            {"expected_outputs": ["result.tsv"]},
            output_dir,
            runner=FailedRunner(),
        )

    assert error.value.script_name == "fake.R"
    assert error.value.returncode == 9
    assert error.value.stderr_tail.splitlines() == [f"error {i}" for i in range(10, 60)]
    assert sentinel.read_text() == "original\n"
    assert sorted(path.name for path in output_dir.iterdir()) == ["keep.txt"]


@pytest.mark.requires_r
def test_real_r_selftest_writes_column_sums_and_session_provenance(tmp_path):
    if not _renv_library_available():
        pytest.skip("Rscript or the configured renv library is unavailable")
    input_path = tmp_path / "counts.tsv"
    input_path.write_text("gene\tsample1\tsample2\ng1\t1\t10\ng2\t2\t20\n")
    output_dir = tmp_path / "real-output"

    result = run_r(
        R_PROJECT / "scripts" / "selftest.R",
        {"counts": input_path},
        {"expected_outputs": ["sums.tsv"]},
        output_dir,
    )

    assert result.outputs["sums.tsv"].read_text() == "sample\tsum\nsample1\t3\nsample2\t30\n"
    assert result.manifest["r_version"].startswith("4.")
    assert result.manifest["bioconductor_version"] == "3.23"
    assert result.manifest["r_library"].startswith("~/")
    assert result.manifest["package_versions"] == {
        "jsonlite": "2.0.0",
        "BiocManager": "1.30.27",
    }
    assert "R version" in result.manifest["session_info"]
    assert result.manifest["session_info"] == (output_dir / "sessionInfo.txt").read_text()


@pytest.mark.requires_r
def test_real_nonzero_exit_raises_with_stderr(tmp_path):
    if not _renv_library_available():
        pytest.skip("Rscript or the configured renv library is unavailable")
    output_dir = tmp_path / "failed-output"

    with pytest.raises(RScriptError) as error:
        run_r(
            Path(__file__).parent / "fixtures" / "fail.R",
            {},
            {"expected_outputs": ["never-written.tsv"]},
            output_dir,
        )

    assert error.value.returncode == 17
    assert "deliberate stderr diagnostic" in error.value.stderr_tail
    assert not output_dir.exists()


@pytest.mark.requires_r
def test_real_zero_exit_missing_expected_output_raises_rscript_error(tmp_path):
    if not _renv_library_available():
        pytest.skip("Rscript or the configured renv library is unavailable")
    with pytest.raises(RScriptError, match="missing expected output") as error:
        run_r(
            Path(__file__).parent / "fixtures" / "zero_missing.R",
            {},
            {"expected_outputs": ["result.tsv"]},
            tmp_path / "missing-output",
        )
    assert error.value.returncode == 0


@pytest.mark.requires_r
def test_real_unexpected_staged_file_raises_rscript_error(tmp_path):
    if not _renv_library_available():
        pytest.skip("Rscript or the configured renv library is unavailable")
    with pytest.raises(RScriptError, match="unexpected staged files.*surprise.tsv"):
        run_r(
            Path(__file__).parent / "fixtures" / "extra_output.R",
            {},
            {"expected_outputs": ["result.tsv"]},
            tmp_path / "extra-output",
        )


@pytest.mark.requires_r
def test_real_non_locked_package_version_raises_rscript_error(tmp_path):
    if not _renv_library_available():
        pytest.skip("Rscript or the configured renv library is unavailable")
    with pytest.raises(RScriptError, match="version.*renv.lock") as error:
        run_r(
            Path(__file__).parent / "fixtures" / "unlocked_version.R",
            {},
            {"expected_outputs": ["unused.tsv"]},
            tmp_path / "version-mismatch",
        )
    assert "0.0.0" in error.value.stderr_tail
