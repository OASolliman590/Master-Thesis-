"""Public-stage checks for registry-owned entity validation and run hashing."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from tools.a_dav.core import SchemaStore
from tools.a_dav.registries import build_registries
from test_group_a import packet as registry_packet


def test_registry_schema_validates_each_canonical_entity_row_once(monkeypatch: pytest.MonkeyPatch) -> None:
    packet = registry_packet()
    store = SchemaStore()
    calls: Counter[str] = Counter()
    original = SchemaStore.validate

    def counted(self: SchemaStore, table: str, row: dict[str, Any]) -> None:
        if self is store:
            calls[table] += 1
        original(self, table, row)

    monkeypatch.setattr(SchemaStore, "validate", counted)
    result = build_registries(packet, schemas=store)
    assert result["status"] == "READY"
    assert calls == Counter({table: len(rows) for table, rows in packet["records"].items()
                             if table in {"study_registry", "publication_family", "source_record",
                                          "patient_registry", "specimen_registry", "assay_registry",
                                          "clinical_outcome", "treatment_episode", "treatment_exposure",
                                          "episode_binding"}})


def test_run_hashes_runtime_modules_once_but_rechecks_packet_receipts(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools.a_dav import core
    from tools.a_dav.demo import synthetic_workflow_packet
    from tools.a_dav.workflow import run_workflow

    reads: Counter[Path] = Counter()
    original = Path.read_bytes

    def counted(path: Path) -> bytes:
        if path.suffix == ".py" and path.name in {"core.py", "registries.py", "workflow.py"}:
            reads[path.resolve()] += 1
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted)
    first = run_workflow(synthetic_workflow_packet())
    assert first["status"] == "READY"
    assert reads[Path(core.__file__).resolve()] == 1
    assert reads[Path(core.__file__).with_name("registries.py").resolve()] == 1
    assert reads[Path(core.__file__).with_name("workflow.py").resolve()] == 1

    # The cache belongs to one workflow invocation; a later packet is verified afresh.
    run_workflow(synthetic_workflow_packet())
    assert reads[Path(core.__file__).resolve()] == 2
