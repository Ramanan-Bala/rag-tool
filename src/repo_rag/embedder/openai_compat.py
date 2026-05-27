from __future__ import annotations

import os
from collections.abc import Sequence

import httpx
import numpy as np

from .base import EmbeddingProvider


class OpenAICompatProvider(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dim: int = 1536,
        base_url: str | None = None,
        api_key_env: str = "RAG_EMBEDDING_API_KEY",
    ):
        self.model = model
        self.dim = dim
        self.base_url = (
            base_url or os.environ.get("RAG_EMBEDDING_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        api_key = os.environ.get(api_key_env) or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"OpenAI-compatible embedding provider requires an API key in "
                f"env var {api_key_env} or OPENAI_API_KEY."
            )
        self._client = httpx.Client(
            timeout=60.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        r = self._client.post(
            f"{self.base_url}/embeddings",
            json={"model": self.model, "input": list(texts)},
        )
        r.raise_for_status()
        data = r.json()
        vecs = [d["embedding"] for d in data["data"]]
        arr = np.array(vecs, dtype=np.float32)
        self.dim = arr.shape[1]
        return arr
