from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np


class EmbeddingProvider(ABC):
    name: str
    model: str
    dim: int

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> np.ndarray: ...

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
