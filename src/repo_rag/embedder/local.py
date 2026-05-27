from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .base import EmbeddingProvider


class FastEmbedProvider(EmbeddingProvider):
    name = "fastembed"

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise ImportError(
                "fastembed is required for the default embedding provider. "
                "Install with: pip install fastembed"
            ) from e
        self._impl = TextEmbedding(model_name=model)
        self.model = model
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        items = list(texts)
        vectors = list(self._impl.embed(items, batch_size=max(len(items), 1)))
        arr = np.array(vectors, dtype=np.float32)
        if arr.size and arr.shape[1] != self.dim:
            self.dim = arr.shape[1]
        return arr


class SentenceTransformersProvider(EmbeddingProvider):
    name = "sentence_transformers"

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2", dim: int = 384):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is not installed. Install with: pip install repo-rag[local]"
            ) from e
        self._impl = SentenceTransformer(model)
        self.model = model
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        arr = self._impl.encode(list(texts), convert_to_numpy=True, normalize_embeddings=True)
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32)
        self.dim = arr.shape[1]
        return arr
