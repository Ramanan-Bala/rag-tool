"""Factory Droid plugin (formerly the only target before plugin system)."""

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


class FactoryAgent(AgentPlugin):
    name = "factory"
    display = "Factory Droid"

    def _config_dir(self) -> Path:
        return Path.home() / ".factory"

    def detect(self) -> bool:
        return self._config_dir().exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "AGENTS.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "AGENTS.md"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        return upsert_json_mcp_entry(self._config_dir() / "mcp.json")

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            command='droid mcp add repo-rag "rag mcp-server"',
            config_path=self._config_dir() / "mcp.json",
            config_snippet=mcp_servers_json_snippet(),
        )
