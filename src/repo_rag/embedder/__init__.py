from __future__ import annotations

from ..config import EmbeddingConfig
from .base import EmbeddingProvider


def make_embedder(cfg: EmbeddingConfig) -> EmbeddingProvider:
    if cfg.provider == "fastembed":
        from .local import FastEmbedProvider

        return FastEmbedProvider(model=cfg.model, dim=cfg.dim)
    if cfg.provider == "sentence_transformers":
        from .local import SentenceTransformersProvider

        return SentenceTransformersProvider(model=cfg.model, dim=cfg.dim)
    if cfg.provider == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(model=cfg.model, dim=cfg.dim, base_url=cfg.base_url)
    if cfg.provider == "openai":
        from .openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(
            model=cfg.model,
            dim=cfg.dim,
            base_url=cfg.base_url,
            api_key_env=cfg.api_key_env,
        )
    raise ValueError(f"Unknown embedding provider: {cfg.provider}")
