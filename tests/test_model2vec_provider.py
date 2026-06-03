from __future__ import annotations

import sys
from types import ModuleType

import pytest

from repo_rag.embedder.local import Model2VecProvider


def test_model2vec_provider_reports_missing_offline_model(monkeypatch: pytest.MonkeyPatch):
    hf = ModuleType("huggingface_hub")

    def snapshot_download(*_args, **_kwargs):
        raise OSError("dns lookup failed")

    hf.snapshot_download = snapshot_download  # type: ignore[attr-defined]

    model2vec = ModuleType("model2vec")

    class StaticModel:
        @classmethod
        def from_pretrained(cls, source):
            assert source == "missing/model"
            raise OSError("no local snapshot")

    model2vec.StaticModel = StaticModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
    monkeypatch.setitem(sys.modules, "model2vec", model2vec)

    with pytest.raises(RuntimeError, match="model2vec embedding model"):
        Model2VecProvider(model="missing/model")
