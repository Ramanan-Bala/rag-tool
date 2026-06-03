from repo_rag.config import GlobalConfig
from repo_rag.search import (
    adaptive_weights,
    defines_symbol,
    is_symbolic_query,
    noise_penalty_for,
    rrf_fuse,
    stem_tokens,
    subtokenize,
)


def test_is_symbolic_query_detects_symbols():
    assert is_symbolic_query("getUserById")
    assert is_symbolic_query("Foo::bar")
    assert is_symbolic_query("user_id")
    assert is_symbolic_query("config.load")


def test_is_symbolic_query_treats_prose_as_natural():
    assert not is_symbolic_query("how is authentication handled")
    assert not is_symbolic_query("where do we read the config")


def test_adaptive_weights_shifts_for_symbols():
    cfg = GlobalConfig()
    v_sym, k_sym = adaptive_weights("getUserById", cfg)
    v_nl, k_nl = adaptive_weights("how does login work", cfg)
    assert k_sym > v_sym
    assert v_nl == cfg.retrieval.vector_weight
    assert k_nl == cfg.retrieval.keyword_weight


def test_subtokenize_splits_camel_and_snake():
    assert {"parse", "config"} <= subtokenize("parseConfig")
    assert {"config", "parser"} <= subtokenize("config_parser")
    assert {"http", "server"} <= subtokenize("HTTPServer") or {"http"} <= subtokenize("HTTPServer")


def test_stem_tokens_matches_across_naming_styles():
    stems = stem_tokens("parse config")
    assert "parse" in stems and "config" in stems
    chunk = stem_tokens("class ConfigParser: ...")
    assert stems & chunk


def test_defines_symbol_prefers_definitions():
    assert defines_symbol("def parse_config(path):\n    return 1", {"parse_config"})
    assert defines_symbol("class ConfigParser:\n    pass", {"ConfigParser"})
    assert not defines_symbol("result = parse_config(path)", {"parse_config"})


def test_noise_penalty_for_downranks_tests_and_legacy():
    cfg = GlobalConfig()
    assert noise_penalty_for("tests/test_foo.py", cfg) == cfg.retrieval.noise_penalty
    assert noise_penalty_for("src/legacy/old.py", cfg) == cfg.retrieval.noise_penalty
    assert noise_penalty_for("types/index.d.ts", cfg) == cfg.retrieval.noise_penalty
    assert noise_penalty_for("src/repo_rag/search.py", cfg) == 0.0


def test_rrf_fuse_combines_ranks_and_sources():
    combined = rrf_fuse(
        vec_pairs=[("a", 0.9), ("b", 0.8)],
        fts_pairs=[("a", 5.0), ("c", 4.0)],
        vector_weight=0.6,
        keyword_weight=0.4,
        k=60,
    )
    assert set(combined) == {"a", "b", "c"}
    assert combined["a"]["sources"] == ["vector", "keyword"]
    # "a" is top-ranked by both lists, so it must outscore single-list hits.
    assert combined["a"]["score"] > combined["b"]["score"]
    assert combined["a"]["score"] > combined["c"]["score"]
