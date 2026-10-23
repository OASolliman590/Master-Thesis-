"""Prepare only a new AIU synthetic payload and its private virtual environment."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile


def main() -> None:
    root = Path(sys.argv[1])
    expected_archive, expected_manifest = sys.argv[2:4]
    prefix = "/home/omics/projects/ici_thesis_pipeline/planning/2026-10-24/A_DAV_TARGET_ENV_01_f53d222_"
    assert str(root).startswith(prefix) and re.fullmatch(r"[a-f0-9]{12}", str(root)[len(prefix):])
    assert root.is_dir() and not root.is_symlink()
    assert {p.name for p in root.iterdir()} == {"payload.tar"}
    raw = (root / "payload.tar").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_archive
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for member in archive.getmembers():
            name = member.name
            path = PurePosixPath(name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            assert path.as_posix() == name and "\\" not in name and name not in files
            stream = archive.extractfile(member)
            assert stream is not None
            files[name] = stream.read()
    assert len(files) == 45
    manifest_raw = files["ALLOWLIST_MANIFEST.json"]
    assert hashlib.sha256(manifest_raw).hexdigest() == expected_manifest
    manifest = json.loads(manifest_raw)
    assert manifest["classification"] == "SYNTHETIC_ONLY"
    assert manifest["base_commit"] == "f53d2222d7d82e6dfdf4af381d71946cd247a89d"
    assert len(manifest["files"]) == 44
    assert set(files) == {x["path"] for x in manifest["files"]} | {"ALLOWLIST_MANIFEST.json"}
    for entry in manifest["files"]:
        content = files[entry["path"]]
        assert len(content) == entry["size"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
    payload = root / "payload"
    payload.mkdir()
    for name, content in files.items():
        destination = payload / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    status = {"classification": "SYNTHETIC_ONLY", "archive_sha256": expected_archive,
              "manifest_sha256": expected_manifest, "payload_files_verified": 45,
              "shared_environment_modified": False, "real_source_data_used": False,
              "status": "STARTED", "pid": os.getpid(), "stages": []}
    receipt = root / "setup-status.json"
    receipt.write_text(json.dumps(status, indent=2) + "\n")
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1",
                   "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "TZ": "UTC"}
    commands = [
        [sys.executable, "-B", "-m", "venv", str(root / "venv")],
        [str(root / "venv/bin/python"), "-B", "-m", "pip", "--isolated", "install",
         "--disable-pip-version-check", "--no-cache-dir", "--index-url", "https://pypi.org/simple",
         "--report", str(root / "dependency-install-report.json"),
         "-r", str(payload / "tools/a_dav/requirements-synthetic.txt")],
    ]
    for index, command in enumerate(commands):
        result = subprocess.run(command, env=environment, cwd=root, capture_output=True,
                                text=True, timeout=300, check=False)
        (root / f"setup-{index}.stdout.log").write_text(result.stdout)
        (root / f"setup-{index}.stderr.log").write_text(result.stderr)
        status["stages"].append({"command": command, "exit_code": result.returncode})
        if result.returncode:
            status["status"] = "FAILED"
            receipt.write_text(json.dumps(status, indent=2) + "\n")
            raise SystemExit(result.returncode)
    status["status"] = "PASSED"
    receipt.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
