"""OpenAI Codex CLI/Desktop plugin."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from .base import AgentPlugin, InstallResult, MCPHint, Scope


def _format_toml_snippet() -> str:
    return '[mcp_servers.repo-rag]\ncommand = "rag"\nargs = ["mcp-server"]\n'


class CodexAgent(AgentPlugin):
    name = "codex"
    display = "OpenAI Codex CLI/Desktop"

    def _config_dir(self) -> Path:
        return Path.home() / ".codex"

    def _config_path(self) -> Path:
        return self._config_dir() / "config.toml"

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
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8").strip():
            try:
                with path.open("rb") as f:
                    data = tomllib.load(f)
            except tomllib.TOMLDecodeError as exc:
                return InstallResult(
                    path=path,
                    written=False,
                    skipped_reason=f"invalid TOML: {exc}",
                )
        else:
            data = {}
        servers = data.setdefault("mcp_servers", {})
        if not isinstance(servers, dict):
            return InstallResult(
                path=path,
                written=False,
                skipped_reason="mcp_servers is not a TOML table",
            )
        before = servers.get("repo-rag")
        servers["repo-rag"] = {"command": "rag", "args": ["mcp-server"]}
        with path.open("wb") as f:
            tomli_w.dump(data, f)
        return InstallResult(path=path, written=before != servers["repo-rag"])

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._config_path(),
            config_snippet=_format_toml_snippet(),
        )
