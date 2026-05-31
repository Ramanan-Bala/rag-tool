"""Plugin registry: maps short names to :class:`AgentPlugin` instances."""

from __future__ import annotations

from collections.abc import Iterable

from .aider import AiderAgent
from .antigravity import AntigravityAgent
from .base import AgentPlugin
from .claude_code import ClaudeCodeAgent
from .claude_desktop import ClaudeDesktopAgent
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
        ClaudeCodeAgent,
        ClaudeDesktopAgent,
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


def iter_plugins() -> Iterable[AgentPlugin]:
    """Yield one fresh instance of every registered plugin."""
    for cls in _all_plugin_classes():
        yield cls()


def resolve_target(name: str) -> AgentPlugin:
    """Return the plugin whose ``name`` matches ``name`` (case-insensitive)."""
    key = name.strip().lower().replace("-", "_")
    for plugin in iter_plugins():
        if plugin.name == key:
            return plugin
    known = ", ".join(sorted(p.name for p in iter_plugins()))
    raise KeyError(f"Unknown agent target {name!r}. Known: {known}.")
