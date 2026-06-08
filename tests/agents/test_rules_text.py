from __future__ import annotations

from repo_rag.agents import _rules_text as rt


def test_md_block_round_trip_in_empty_string():
    out = rt.upsert_md_block("")
    assert rt.MD_BEGIN in out
    assert rt.MD_END in out
    assert "Code Search Policy" in out


def test_md_block_preserves_surrounding_text():
    original = "# user rules\n\nbe nice\n"
    out = rt.upsert_md_block(original)
    assert "be nice" in out
    assert rt.MD_BEGIN in out


def test_md_block_is_idempotent():
    once = rt.upsert_md_block("# rules\n")
    twice = rt.upsert_md_block(once)
    assert once == twice


def test_remove_md_block_keeps_surrounding_text():
    original = "head\n\n" + rt.md_block() + "\ntail\n"
    out, removed = rt.remove_md_block(original)
    assert removed is True
    assert "head" in out
    assert "tail" in out
    assert rt.MD_BEGIN not in out


def test_remove_md_block_noop_when_missing():
    out, removed = rt.remove_md_block("nothing\n")
    assert removed is False
    assert out == "nothing\n"


def test_rules_markdown_has_enforcement_language():
    """The rules block MUST use precise enforcement language for all agents."""
    body = rt.rules_markdown().lower()
    # Core enforcement — all agents must follow these rules.
    assert "all agents" in body
    assert "must" in body
    assert "without exception" in body
    # Section 0 — index initiation check.
    assert "index initiation" in body
    assert "not indexed" in body
    # Section 7 — MCP server configuration.
    assert "mcp server" in body
    assert "rag agents setup" in body
    # Exception tracking.
    assert "reasonable exceptions" in body
