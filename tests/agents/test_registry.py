from __future__ import annotations

import pytest

from repo_rag.agents import iter_plugins, resolve_target
from repo_rag.agents.base import AgentPlugin

EXPECTED_NAMES = {
    "universal",
    "factory",
    "claude",
    "codex",
    "cursor",
    "windsurf",
    "cline",
    "continue",
    "gemini",
    "antigravity",
    "aider",
    "minimax",
    "zed",
}


def test_iter_plugins_yields_every_target():
    names = {p.name for p in iter_plugins()}
    assert names == EXPECTED_NAMES


def test_resolve_target_returns_claude_plugin():
    plugin = resolve_target("claude")
    assert isinstance(plugin, AgentPlugin)
    assert plugin.name == "claude"


def test_claude_code_alias_resolves_to_claude():
    plugin = resolve_target("claude_code")
    assert plugin.name == "claude"


def test_claude_desktop_alias_resolves_to_claude():
    plugin = resolve_target("claude_desktop")
    assert plugin.name == "claude"


def test_resolve_target_accepts_dashes():
    plugin = resolve_target("claude-code")
    assert plugin.name == "claude"


def test_resolve_target_unknown_raises():
    with pytest.raises(KeyError):
        resolve_target("not-an-agent")


def test_every_plugin_has_display_string():
    for plugin in iter_plugins():
        assert plugin.display
        assert isinstance(plugin.display, str)
