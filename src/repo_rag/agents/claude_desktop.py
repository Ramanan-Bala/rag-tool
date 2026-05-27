"""Claude Desktop plugin (macOS / Windows / Linux config locations).

Claude Desktop has no rules file - the policy block can still be exercised by
also installing the universal :class:`UniversalAgent`, which writes
``AGENTS.md``. This plugin only manages the MCP server configuration.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
    mcp_servers_json_snippet,
    upsert_json_mcp_entry,
)


def _config_path() -> Path:
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Claude" / "claude_desktop_config.json"
    # Linux / other POSIX
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


class ClaudeDesktopAgent(AgentPlugin):
    name = "claude_desktop"
    display = "Claude Desktop"
    rules_optional = True

    def detect(self) -> bool:
        path = _config_path()
        return path.exists() or path.parent.exists()

    def user_rules_path(self) -> Path | None:
        return None

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return None

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        return upsert_json_mcp_entry(_config_path())

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=_config_path(),
            config_snippet=mcp_servers_json_snippet(),
            notes=["Restart Claude Desktop after editing this file."],
        )
