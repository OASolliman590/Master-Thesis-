"""Read locally retained source objects by their complete SHA-256 identity."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SourceObjectError(ValueError):
    """Safe source object error code without echoing private metadata."""


@dataclass(frozen=True)
class SourceObject:
    sha256: str
    locator: str
    version: str
    byte_size: int
    retrieved_at: str
    bytes: bytes
    receipt: dict[str, Any] | None = None


def _valid_receipt(value: Any, sha256: str) -> bool:
    return (
        isinstance(value, dict)
        and value.get("complete_sha256") == sha256
        and type(value.get("http_status")) is int
        and isinstance(value.get("final_url"), str)
        and isinstance(value.get("redirect_chain"), list)
        and all(isinstance(hop, str) and hop for hop in value["redirect_chain"])
        and isinstance(value.get("headers"), dict)
        and type(value.get("attempts")) is int
        and value["attempts"] >= 1
    )


class ContentAddressedStore:
    """Local-only `<store>/objects/<sha256>` reader; performs no network access."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._manifest: dict[str, Any] | None = None

    def _load_manifest(self) -> dict[str, Any]:
        if self._manifest is not None:
            return self._manifest
        path = self.root / "MANIFEST.json"
        if path.is_symlink() or not path.is_file():
            raise SourceObjectError("STORE_MANIFEST_INVALID")
        try:
            manifest = json.loads(path.read_bytes())
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise SourceObjectError("STORE_MANIFEST_INVALID") from None
        if (not isinstance(manifest, dict) or set(manifest) != {"objects"}
                or not isinstance(manifest["objects"], dict)):
            raise SourceObjectError("STORE_MANIFEST_INVALID")
        self._manifest = manifest["objects"]
        return self._manifest

    def read(self, sha256: str) -> SourceObject:
        if not isinstance(sha256, str) or re.fullmatch(r"[a-f0-9]{64}", sha256) is None:
            raise SourceObjectError("SOURCE_HASH_INVALID")
        entry = self._load_manifest().get(sha256)
        required = {"locator", "version", "byte_size", "retrieved_at"}
        if (not isinstance(entry, dict) or not required.issubset(entry)
                or set(entry) - required not in (set(), {"receipt"})
                or not isinstance(entry["locator"], str) or not entry["locator"]
                or not isinstance(entry["version"], str) or not entry["version"]
                or type(entry["byte_size"]) is not int or entry["byte_size"] < 0
                or not isinstance(entry["retrieved_at"], str) or not entry["retrieved_at"]
                or ("receipt" in entry and not _valid_receipt(entry["receipt"], sha256))):
            raise SourceObjectError("STORE_MANIFEST_INVALID")
        objects_dir = self.root / "objects"
        path = objects_dir / sha256
        if objects_dir.is_symlink() or not objects_dir.is_dir() or path.is_symlink() or not path.is_file():
            raise SourceObjectError("SOURCE_OBJECT_MISSING")
        try:
            raw = path.read_bytes()
        except OSError:
            raise SourceObjectError("SOURCE_OBJECT_MISSING") from None
        if len(raw) != entry["byte_size"]:
            raise SourceObjectError("SOURCE_SIZE_MISMATCH")
        if hashlib.sha256(raw).hexdigest() != sha256:
            raise SourceObjectError("SOURCE_HASH_MISMATCH")
        return SourceObject(sha256, entry["locator"], entry["version"], len(raw),
                            entry["retrieved_at"], raw, entry.get("receipt"))
