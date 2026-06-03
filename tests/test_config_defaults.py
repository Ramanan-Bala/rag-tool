from repo_rag.config import EmbeddingConfig, GlobalConfig


def test_default_provider_is_model2vec():
    cfg = GlobalConfig()
    assert cfg.embedding.provider == "model2vec"
    assert cfg.embedding.model == "minishlab/potion-code-16M"
    assert cfg.embedding.dim == 256


def test_fastembed_still_selectable_as_fallback():
    e = EmbeddingConfig(provider="fastembed", model="BAAI/bge-small-en-v1.5", dim=384)
    assert e.provider == "fastembed"
    assert e.dim == 384
