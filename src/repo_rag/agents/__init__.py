"""Multi-agent plugin system for repo-rag.

Each subclass of :class:`AgentPlugin` describes one MCP-compatible AI coding
agent (Factory Droid, Claude Code, Cursor, etc.) and knows:

* how to detect whether that agent is installed locally;
* where its user-scope and project-scope rules file lives;
* how to enable repo-rag as an MCP server in that agent's native config.

All edits use marker-tagged blocks so an uninstall preserves anything the user
wrote outside the marker. JSON MCP configs are merged by key rather than
wrapped in markers, since most clients reject inline comments.
"""

from __future__ import annotations

from .base import AgentPlugin, InstallResult, MCPHint, Scope
from .registry import iter_plugins, resolve_target

__all__ = [
    "AgentPlugin",
    "InstallResult",
    "MCPHint",
    "Scope",
    "iter_plugins",
    "resolve_target",
]
