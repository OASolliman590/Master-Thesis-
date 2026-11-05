from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

pytest.importorskip("numpy", reason="run with envs/sc-analysis Python")
pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.a_meta.random_streams import seed_for_task
from tools.sc import prostate


def test_embedding_uses_frozen_seed_and_single_thread_neighbor_graph(tmp_path, monkeypatch):
    calls = {}

    def record(name):
        def call(*_args, **kwargs):
            calls[name] = kwargs
        return call

    scanpy = SimpleNamespace(
        settings=SimpleNamespace(n_jobs=8),
        pp=SimpleNamespace(
            normalize_total=record("normalize_total"),
            log1p=record("log1p"),
            highly_variable_genes=record("highly_variable_genes"),
            neighbors=record("neighbors"),
        ),
        tl=SimpleNamespace(
            pca=record("pca"),
            umap=record("umap"),
            leiden=record("leiden"),
        ),
        pl=SimpleNamespace(umap=record("plot_umap")),
    )
    matplotlib = ModuleType("matplotlib")
    matplotlib.__path__ = []
    pyplot = ModuleType("matplotlib.pyplot")
    pyplot.savefig = lambda *_args, **_kwargs: None
    pyplot.close = lambda *_args, **_kwargs: None
    matplotlib.pyplot = pyplot
    monkeypatch.setattr(prostate, "configure_runtime", lambda: None)
    monkeypatch.setitem(sys.modules, "scanpy", scanpy)
    monkeypatch.setitem(sys.modules, "matplotlib", matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", pyplot)

    class SyntheticAtlas:
        layers = {"counts": [[1.0]]}
        X = None

        def write_h5ad(self, path):
            Path(path).write_bytes(b"synthetic embedding")

    result = prostate.run_embedding(SyntheticAtlas(), tmp_path / "embedding")
    seed = seed_for_task("sc_embedding", "prostate_hormone_naive_atlas")

    assert result == {
        "random_stream": "sc_embedding",
        "random_task_id": "prostate_hormone_naive_atlas",
        "seed": seed,
        "neighbor_threads": 1,
    }
    assert calls["pca"]["random_state"] == seed
    assert calls["neighbors"]["random_state"] == seed
    assert calls["umap"]["random_state"] == seed
    assert calls["leiden"]["random_state"] == seed
    assert scanpy.settings.n_jobs == 1
