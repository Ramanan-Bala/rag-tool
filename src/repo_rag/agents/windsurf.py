"""Windsurf (Codeium) plugin."""

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


class WindsurfAgent(AgentPlugin):
    name = "windsurf"
    display = "Windsurf"

    def _config_dir(self) -> Path:
        return Path.home() / ".codeium" / "windsurf"

    def detect(self) -> bool:
        return self._config_dir().exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "global_rules.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / ".windsurfrules"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        return upsert_json_mcp_entry(self._config_dir() / "mcp_config.json")

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._config_dir() / "mcp_config.json",
            config_snippet=mcp_servers_json_snippet(),
        )
