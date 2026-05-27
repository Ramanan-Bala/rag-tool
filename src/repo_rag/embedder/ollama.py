from __future__ import annotations

import os
from collections.abc import Sequence

import httpx
import numpy as np

from .base import EmbeddingProvider


class OllamaProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(
        self, model: str = "nomic-embed-text", dim: int = 768, base_url: str | None = None
    ):
        self.model = model
        self.dim = dim
        self.base_url = (
            base_url or os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
        ).rstrip("/")
        self._client = httpx.Client(timeout=60.0)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        out = []
        for t in texts:
            r = self._client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": t},
            )
            r.raise_for_status()
            data = r.json()
            out.append(data["embedding"])
        arr = np.array(out, dtype=np.float32)
        self.dim = arr.shape[1]
        return arr
