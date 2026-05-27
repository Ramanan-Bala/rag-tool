"""Base class and shared helpers for agent plugins."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from . import _rules_text

Scope = Literal["user", "project"]


@dataclass
class InstallResult:
    """Outcome of a single ``install_*`` call."""

    path: Path | None
    written: bool = False
    skipped_reason: str | None = None
    detail: str = ""


@dataclass
class MCPHint:
    """Instructions printed when an agent's MCP config cannot be auto-written."""

    command: str | None = None
    config_path: Path | None = None
    config_snippet: str | None = None
    notes: list[str] = field(default_factory=list)


DEFAULT_MCP_ENTRY: dict[str, Any] = {"command": "rag", "args": ["mcp-server"]}


def mcp_servers_json_snippet() -> str:
    """Return the standard ``mcpServers.repo-rag`` JSON snippet."""
    return json.dumps({"mcpServers": {"repo-rag": DEFAULT_MCP_ENTRY}}, indent=2)


class AgentPlugin(ABC):
    """A single MCP-compatible AI coding agent integration target."""

    name: str
    display: str
    # When True, ``install_rules`` is a no-op (the agent has no rules file).
    rules_optional: bool = False

    # --- detection -----------------------------------------------------------
    @abstractmethod
    def detect(self) -> bool:
        """Return True if this agent appears installed on the local machine."""

    # --- rules ---------------------------------------------------------------
    def user_rules_path(self) -> Path | None:
        """Where this agent reads user-scope rules. ``None`` if the agent has none."""
        return None

    def project_rules_path(self, repo_root: Path) -> Path | None:
        """Where this agent reads project-scope rules. ``None`` if the agent has none."""
        return repo_root / "AGENTS.md"

    def _resolve_rules_path(self, scope: Scope, repo_root: Path | None) -> Path | None:
        if scope == "user":
            return self.user_rules_path()
        if repo_root is None:
            return None
        return self.project_rules_path(repo_root)

    def install_rules(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult:
        if self.rules_optional:
            return InstallResult(path=None, skipped_reason="agent has no rules file")
        path = self._resolve_rules_path(scope, repo_root)
        if path is None:
            return InstallResult(path=None, skipped_reason=f"no {scope} rules path for {self.name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        new_content = _rules_text.upsert_md_block(existing)
        if new_content != existing:
            path.write_text(new_content, encoding="utf-8")
            return InstallResult(path=path, written=True)
        return InstallResult(path=path, written=False, detail="already up to date")

    def uninstall_rules(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> bool:
        if self.rules_optional:
            return False
        path = self._resolve_rules_path(scope, repo_root)
        if path is None or not path.exists():
            return False
        existing = path.read_text(encoding="utf-8")
        new_content, removed = _rules_text.remove_md_block(existing)
        if removed:
            if new_content.strip():
                path.write_text(new_content, encoding="utf-8")
            else:
                # Only the repo-rag block was present; remove the empty file.
                try:
                    path.unlink()
                except OSError:
                    path.write_text("", encoding="utf-8")
        return removed

    # --- MCP -----------------------------------------------------------------
    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        """Default: no auto-write. Override in subclasses that can patch a JSON/TOML config."""
        return None

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_snippet=mcp_servers_json_snippet(),
            notes=[f"See docs/clients/{self.name}.md for {self.display}-specific setup."],
        )


def upsert_json_mcp_entry(
    path: Path,
    *,
    parent_key: str = "mcpServers",
    server_name: str = "repo-rag",
    entry: dict[str, Any] | None = None,
) -> InstallResult:
    """Insert or update ``parent_key.server_name = entry`` inside a JSON file.

    Creates the file (and parent directories) when missing. Preserves any
    sibling keys the user already has.
    """
    entry = entry or DEFAULT_MCP_ENTRY
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any]
    if path.exists() and path.read_text(encoding="utf-8").strip():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return InstallResult(path=path, written=False, skipped_reason=f"invalid JSON: {exc}")
        if not isinstance(data, dict):
            return InstallResult(path=path, written=False, skipped_reason="not a JSON object")
    else:
        data = {}
    servers = data.setdefault(parent_key, {})
    if not isinstance(servers, dict):
        return InstallResult(
            path=path,
            written=False,
            skipped_reason=f"{parent_key} is not a JSON object",
        )
    before = json.dumps(servers.get(server_name), sort_keys=True)
    servers[server_name] = entry
    after = json.dumps(servers.get(server_name), sort_keys=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return InstallResult(path=path, written=before != after, detail=parent_key)


def remove_json_mcp_entry(
    path: Path,
    *,
    parent_key: str = "mcpServers",
    server_name: str = "repo-rag",
) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    servers = data.get(parent_key)
    if not isinstance(servers, dict) or server_name not in servers:
        return False
    servers.pop(server_name)
    if not servers:
        data.pop(parent_key, None)
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        try:
            path.unlink()
        except OSError:
            path.write_text("{}\n", encoding="utf-8")
    return True
