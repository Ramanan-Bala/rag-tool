from repo_rag.search import merge_results, normalize_scores, to_fts_query


def test_normalize_scores_min_max():
    out = normalize_scores([("a", 0.0), ("b", 0.5), ("c", 1.0)])
    assert out["a"] == 0.0
    assert out["c"] == 1.0


def test_normalize_scores_handles_equal_values():
    out = normalize_scores([("a", 0.7), ("b", 0.7)])
    assert out == {"a": 1.0, "b": 1.0}


def test_merge_results_combines_weights():
    combined = merge_results(
        vec_hits=[("a", 1.0), ("b", 0.5)],
        fts_hits=[("a", 0.5), ("c", 1.0)],
        vector_weight=0.6,
        keyword_weight=0.4,
    )
    assert set(combined.keys()) == {"a", "b", "c"}
    assert "vector" in combined["a"]["sources"]
    assert "keyword" in combined["a"]["sources"]
    assert combined["a"]["score"] > combined["b"]["score"]


def test_to_fts_query_extracts_tokens():
    q = to_fts_query("fix the auth_timeout bug in api/handler.py")
    assert '"auth_timeout"' in q
    assert '"handler"' in q
    assert " OR " in q


def test_to_fts_query_returns_text_for_no_tokens():
    assert to_fts_query("!!!") == "!!!"
