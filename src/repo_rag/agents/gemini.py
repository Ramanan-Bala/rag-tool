"""Gemini CLI (Google) plugin."""

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


class GeminiAgent(AgentPlugin):
    name = "gemini"
    display = "Gemini CLI"

    def _config_dir(self) -> Path:
        return Path.home() / ".gemini"

    def detect(self) -> bool:
        return self._config_dir().exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "GEMINI.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "GEMINI.md"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        return upsert_json_mcp_entry(self._config_dir() / "settings.json")

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._config_dir() / "settings.json",
            config_snippet=mcp_servers_json_snippet(),
        )
