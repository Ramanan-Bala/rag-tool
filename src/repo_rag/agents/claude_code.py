"""Claude Code (Anthropic) plugin."""

from __future__ import annotations

from pathlib import Path

from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
    mcp_servers_json_snippet,
    upsert_json_mcp_entry,
)


class ClaudeCodeAgent(AgentPlugin):
    name = "claude_code"
    display = "Claude Code"

    def _config_dir(self) -> Path:
        return Path.home() / ".claude"

    def _settings_path(self) -> Path:
        return Path.home() / ".claude.json"

    def detect(self) -> bool:
        return self._config_dir().exists() or self._settings_path().exists()

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
        return upsert_json_mcp_entry(self._settings_path())

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            command="claude mcp add repo-rag rag mcp-server",
            config_path=self._settings_path(),
            config_snippet=mcp_servers_json_snippet(),
        )
