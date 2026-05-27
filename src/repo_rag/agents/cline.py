"""Cline (VS Code extension) plugin.

Cline auto-loads ``AGENTS.md`` from the workspace root. Its MCP server
registration lives inside VS Code settings, so we leave that step to the
user via :func:`mcp_hint`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .base import AgentPlugin, MCPHint, Scope, mcp_servers_json_snippet


def _vscode_user_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User"
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Code" / "User"
    return Path.home() / ".config" / "Code" / "User"


class ClineAgent(AgentPlugin):
    name = "cline"
    display = "Cline"

    def detect(self) -> bool:
        return _vscode_user_dir().exists()

    def user_rules_path(self) -> Path | None:
        return None

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "AGENTS.md"

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_snippet=mcp_servers_json_snippet(),
            notes=[
                "Open VS Code → Cline extension → MCP Servers → Add server.",
                "Use command `rag` and args `mcp-server`.",
            ],
        )
