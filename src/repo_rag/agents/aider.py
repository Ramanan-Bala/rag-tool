"""Aider plugin.

Aider's MCP story is still evolving; some forks read MCP servers from
``~/.aider.conf.yml``. We append a marker-tagged YAML comment block with the
expected entry so the user can move it into the supported key for their
build, and we keep the policy in ``CONVENTIONS.md`` (Aider's native rules
file) and ``AGENTS.md`` (universal).
"""

from __future__ import annotations

from pathlib import Path

from . import _rules_text
from .base import AgentPlugin, InstallResult, MCPHint, Scope

_AIDER_YAML_BLOCK = f"""\
{_rules_text.HASH_BEGIN}
# repo-rag MCP server entry (kept here as a reference; move into the
# correct key for your Aider build if your version supports MCP).
# mcp-servers:
#   repo-rag:
#     command: rag
#     args: [mcp-server]
{_rules_text.HASH_END}
"""


class AiderAgent(AgentPlugin):
    name = "aider"
    display = "Aider"

    def _config_dir(self) -> Path:
        return Path.home() / ".aider"

    def _conf_path(self) -> Path:
        return Path.home() / ".aider.conf.yml"

    def detect(self) -> bool:
        return self._config_dir().exists() or self._conf_path().exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "CONVENTIONS.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "CONVENTIONS.md"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        path = self._conf_path()
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if _rules_text.HASH_BEGIN in existing and _rules_text.HASH_END in existing:
            head, _, rest = existing.partition(_rules_text.HASH_BEGIN)
            _, _, tail = rest.partition(_rules_text.HASH_END)
            new_content = head + _AIDER_YAML_BLOCK + tail.lstrip("\n")
        elif existing.strip():
            new_content = existing.rstrip() + "\n\n" + _AIDER_YAML_BLOCK
        else:
            new_content = _AIDER_YAML_BLOCK
        if new_content != existing:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_content, encoding="utf-8")
            return InstallResult(path=path, written=True)
        return InstallResult(path=path, written=False, detail="already up to date")

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._conf_path(),
            config_snippet=_AIDER_YAML_BLOCK,
            notes=[
                "Aider's first-class MCP support is still evolving; this block is "
                "informational. Move it under the key your Aider build expects."
            ],
        )
