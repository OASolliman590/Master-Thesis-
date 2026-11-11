"""Path guards shared by the A-BIO runner and invented-fixture writer."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path


def absolute_path(value: Path | str, *, label: str) -> Path:
    raw_text = os.fspath(value)
    _validate_path_components(raw_text, label=label)
    raw = Path(value).expanduser()
    if ".." in raw.parts:
        raise ValueError(f"{label} path contains an escaping component")
    absolute = Path(os.path.abspath(raw))
    _validate_path_components(str(absolute), label=label)
    try:
        resolved = absolute.resolve(strict=False)
    except (OSError, RuntimeError):
        raise ValueError(f"{label} path cannot be resolved safely") from None
    _validate_path_components(str(resolved), label=label)
    return absolute


def _validate_path_components(value: str, *, label: str) -> None:
    """Refuse forbidden names in lexical, absolute, and resolved path components."""
    components = [part for part in re.split(r"[\\/]", str(value)) if part]
    for component in components:
        normalized = re.sub(r"[^a-z0-9]", "", component.casefold())
        if "ingestionpacket" in normalized:
            raise ValueError(f"{label} path contains a forbidden packet component")
        if not normalized:
            continue
        markers = (
            "imvigor210", "finaltest", "excluded", "combination",
            "dropped", "candidate", "parked", "onhold",
        )
        if any(marker in normalized for marker in markers) or any(
            token and token in normalized for token in _protected_registry_tokens()
        ):
            raise ValueError(f"{label} path contains a protected component") from None


@lru_cache(maxsize=1)
def _protected_registry_tokens() -> tuple[str, ...]:
    from tools.a_cohorts import core as cohort_core

    role_markers = (
        "final test", "excluded", "combination", "dropped", "candidate", "parked", "on hold",
    )
    tokens = []
    for identifier, row in cohort_core.registry().items():
        role = str(row.get("role", "")).casefold()
        if any(marker in role for marker in role_markers):
            tokens.append(re.sub(r"[^a-z0-9]", "", str(identifier).casefold()))
    return tuple(tokens)


def validate_single_component(value: str, *, label: str) -> str:
    component = str(value).strip()
    if (
        component in {".", ".."}
        or "/" in component
        or "\\" in component
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", component)
    ):
        raise ValueError(f"{label} must be one safe path component")
    return component


def reject_symlink_components(path: Path | str, *, label: str) -> Path:
    absolute = absolute_path(path, label=label)
    cursor = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError(f"{label} path contains a symlink")
    return absolute


def validate_contained_path(
    root: Path | str,
    path: Path | str,
    *,
    label: str,
    must_exist: bool = False,
) -> Path:
    root_path = reject_symlink_components(root, label=label)
    target = reject_symlink_components(path, label=label)
    if not target.is_relative_to(root_path):
        raise ValueError(f"{label} path escapes its declared root")
    if must_exist and not target.exists():
        raise FileNotFoundError(f"{label} path is unavailable")
    return target


def preflight_tree(root: Path | str, *, label: str) -> Path:
    """Check every existing component below a declared root without reading files."""
    selected = reject_symlink_components(root, label=label)
    if not selected.exists():
        return selected
    if not selected.is_dir():
        raise ValueError(f"{label} root is not a directory")
    for parent, directories, files in os.walk(selected, followlinks=False):
        parent_path = Path(parent)
        for name in (*directories, *files):
            child = parent_path / name
            absolute_path(child, label=label)
            if child.is_symlink():
                raise ValueError(f"{label} tree contains a symlink")
    return selected


def write_immutable_bytes(root: Path | str, path: Path | str, content: bytes, *, label: str) -> Path:
    target = validate_contained_path(root, path, label=label)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = validate_contained_path(root, target, label=label)
    if target.exists():
        if target.is_dir() or target.read_bytes() != content:
            raise FileExistsError(f"Refusing to replace different existing {label}")
        return target
    try:
        with target.open("xb") as stream:
            stream.write(content)
    except FileExistsError:
        if target.is_symlink() or target.is_dir() or target.read_bytes() != content:
            raise FileExistsError(f"Refusing to replace different existing {label}") from None
    return target

