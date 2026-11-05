"""Python mirror of the signed random-stream table; no random draws occur here."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class RandomStream:
    seed: int
    task_id: str
    role: str
    reported_only: bool = False


RANDOM_STREAMS = {
    "a_p2_bootstrap": RandomStream(20261102, "one task", "signed A-P2 bootstrap"),
    "a_p2_splits": RandomStream(20261103, "<study>|rep<01-20>", "A-P2 split sensitivity"),
    "fgsea": RandomStream(20261104, "<dataset>|<endpoint>|<collection>", "fgsea"),
    "sc_embedding": RandomStream(20261105, "<atlas>", "single-cell embedding"),
    "b_bootstrap": RandomStream(20261106, "set by Paper B contract", "Paper B bootstrap"),
    "second_check": RandomStream(20261107, "<stream>", "reported-only Monte Carlo check", True),
    "a_p1_bootstrap": RandomStream(20261108, "one task", "A-P1 bootstrap"),
}


def stream_seed(stream: str) -> int:
    try:
        return RANDOM_STREAMS[stream].seed
    except KeyError:
        raise ValueError(f"Unknown random stream: {stream}") from None


def derive_task_seed(stream: str, task_id: str) -> int:
    if stream not in RANDOM_STREAMS:
        raise ValueError(f"Unknown random stream: {stream}")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("Task ID must be a non-empty string")
    payload = f"{stream_seed(stream)}|{task_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:7], 16)


def seed_for_task(stream: str, task_id: str | None = None) -> int:
    contract = RANDOM_STREAMS.get(stream)
    if contract is None:
        raise ValueError(f"Unknown random stream: {stream}")
    if contract.task_id == "one task":
        if task_id is not None:
            raise ValueError(f"Stream {stream} has one task and uses its root seed directly")
        return contract.seed
    if task_id is None:
        raise ValueError(f"Stream {stream} requires a task ID")
    return derive_task_seed(stream, task_id)
