"""Plugin registry: maps short names to :class:`AgentPlugin` instances."""

from __future__ import annotations

from collections.abc import Iterable

from .aider import AiderAgent
from .antigravity import AntigravityAgent
from .base import AgentPlugin
from .claude import ClaudeAgent
from .cline import ClineAgent
from .codex import CodexAgent
from .continue_ import ContinueAgent
from .cursor import CursorAgent
from .factory import FactoryAgent
from .gemini import GeminiAgent
from .minimax import MinimaxAgent
from .universal import UniversalAgent
from .windsurf import WindsurfAgent
from .zed import ZedAgent


def _all_plugin_classes() -> list[type[AgentPlugin]]:
    return [
        UniversalAgent,
        FactoryAgent,
        ClaudeAgent,
        CodexAgent,
        CursorAgent,
        WindsurfAgent,
        ClineAgent,
        ContinueAgent,
        GeminiAgent,
        AntigravityAgent,
        AiderAgent,
        MinimaxAgent,
        ZedAgent,
    ]


# Backward-compat aliases so old names still resolve.
_ALIASES: dict[str, str] = {
    "claude_code": "claude",
    "claude_desktop": "claude",
}


def iter_plugins() -> Iterable[AgentPlugin]:
    """Yield one fresh instance of every registered plugin."""
    seen: set[str] = set()
    for cls in _all_plugin_classes():
        plugin = cls()
        if plugin.name not in seen:
            seen.add(plugin.name)
            yield plugin


def resolve_target(name: str) -> AgentPlugin:
    """Return the plugin whose ``name`` matches ``name`` (case-insensitive)."""
    key = name.strip().lower().replace("-", "_")
    # Check aliases first for backward compat.
    resolved = _ALIASES.get(key, key)
    for plugin in iter_plugins():
        if plugin.name == resolved:
            return plugin
    known = ", ".join(sorted(p.name for p in iter_plugins()))
    raise KeyError(f"Unknown agent target {name!r}. Known: {known}.")
