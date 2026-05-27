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


def test_rules_markdown_does_not_use_strict_language():
    body = rt.rules_markdown().lower()
    assert "mandatory" not in body
    assert "prohibited" not in body
    assert "enforcement" not in body
    assert "non-negotiable" not in body
