from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from .base import EmbeddingProvider


class FastEmbedProvider(EmbeddingProvider):
    name = "fastembed"

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise ImportError(
                "fastembed is not installed. Install with: pip install fastembed"
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


class Model2VecProvider(EmbeddingProvider):
    """Static, code-specialized embeddings (no transformer forward pass).

    Uses Model2Vec (e.g. `minishlab/potion-code-16M`) for very fast CPU
    embedding at index and query time. Vectors are L2-normalized so cosine
    similarity behaves consistently with the other providers.
    """

    name = "model2vec"

    def __init__(self, model: str = "minishlab/potion-code-16M", dim: int = 256):
        try:
            from model2vec import StaticModel
        except ImportError as e:
            raise ImportError(
                "model2vec is not installed. Install with: pip install repo-rag[model2vec]"
            ) from e
        # Corporate networks frequently do TLS inspection with a private root CA that
        # certifi does not trust; truststore makes downloads use the OS certificate store.
        try:
            import truststore

            truststore.inject_into_ssl()
        except Exception:
            pass
        source = model
        if not Path(model).expanduser().exists():
            # Resolve from the Hub but skip *.py: the training script is not needed for
            # inference and some corporate proxies return 403 for script downloads.
            try:
                from huggingface_hub import snapshot_download

                source = snapshot_download(model, ignore_patterns=["*.py"])
            except Exception:
                source = model
        self._impl = StaticModel.from_pretrained(source)
        self.model = model
        self.dim = int(getattr(self._impl, "dim", dim) or dim)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        arr = np.asarray(self._impl.encode(list(texts)), dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        arr = arr / norms
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
