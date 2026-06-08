"""Claude agent plugin (CLI + Desktop).

Covers both Claude Code (terminal/IDE) and Claude Desktop (native app) in a
single plugin. ``rag agents setup --target claude`` writes the rules block
into ``CLAUDE.md`` and patches MCP configs for both the CLI (``~/.claude.json``)
and the desktop app (per-platform path).
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


def _desktop_config_path() -> Path:
    """Return the Claude Desktop MCP config path for the current platform."""
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


class ClaudeAgent(AgentPlugin):
    name = "claude"
    display = "Claude"

    def _config_dir(self) -> Path:
        return Path.home() / ".claude"

    def _settings_path(self) -> Path:
        return Path.home() / ".claude.json"

    def detect(self) -> bool:
        # Detect if either Claude Code or Claude Desktop is installed.
        if self._config_dir().exists() or self._settings_path().exists():
            return True
        desktop = _desktop_config_path()
        return desktop.exists() or desktop.parent.exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "CLAUDE.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "CLAUDE.md"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        # Primary: Claude Code CLI config.
        result = upsert_json_mcp_entry(self._settings_path())
        # Side effect: also write the desktop config.
        desktop_path = _desktop_config_path()
        if desktop_path.parent.exists():
            result.side_effects.append(upsert_json_mcp_entry(desktop_path))
        return result

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            command="claude mcp add repo-rag rag mcp-server",
            config_path=self._settings_path(),
            config_snippet=mcp_servers_json_snippet(),
            notes=[f"Also writes to {_desktop_config_path()} for Claude Desktop."],
        )
