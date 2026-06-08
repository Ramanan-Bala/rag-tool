"""Tests for plugins that auto-write MCP configurations."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from repo_rag.agents.antigravity import AntigravityAgent
from repo_rag.agents.claude import ClaudeAgent, _desktop_config_path
from repo_rag.agents.codex import CodexAgent
from repo_rag.agents.continue_ import ContinueAgent
from repo_rag.agents.cursor import CursorAgent
from repo_rag.agents.factory import FactoryAgent
from repo_rag.agents.gemini import GeminiAgent
from repo_rag.agents.minimax import MinimaxAgent
from repo_rag.agents.windsurf import WindsurfAgent
from repo_rag.agents.zed import ZedAgent


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_factory_mcp_writes_repo_rag_entry(fake_home: Path):
    agent = FactoryAgent()
    result = agent.install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".factory" / "mcp.json"
    data = _load_json(result.path)
    assert data["mcpServers"]["repo-rag"]["command"] == "rag"
    assert data["mcpServers"]["repo-rag"]["args"] == ["mcp-server"]


def test_factory_mcp_preserves_sibling_entries(fake_home: Path):
    path = fake_home / ".factory" / "mcp.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
    FactoryAgent().install_mcp(scope="user")
    data = _load_json(path)
    assert "other" in data["mcpServers"]
    assert "repo-rag" in data["mcpServers"]


def test_claude_mcp_writes_to_dotjson(fake_home: Path):
    agent = ClaudeAgent()
    result = agent.install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".claude.json"
    assert "repo-rag" in _load_json(result.path)["mcpServers"]


def test_claude_mcp_also_writes_desktop_config(fake_home: Path):
    """ClaudeAgent.install_mcp must write the desktop config as a side effect."""
    agent = ClaudeAgent()
    # Create the desktop config parent dir so the side-effect write fires.
    desktop_config = _desktop_config_path()
    desktop_config.parent.mkdir(parents=True)
    result = agent.install_mcp(scope="user")
    assert result is not None
    # The primary result is for ~/.claude.json; the desktop config is a side effect.
    assert result.path == fake_home / ".claude.json"
    assert len(result.side_effects) == 1
    assert result.side_effects[0].path == desktop_config
    assert desktop_config.exists()
    assert "repo-rag" in _load_json(desktop_config)["mcpServers"]


def test_claude_detects_either_cli_or_desktop(fake_home: Path):
    agent = ClaudeAgent()
    # Neither present initially (fake home is empty except for std dirs).
    # detect() checks .claude/, .claude.json, and the desktop config path.
    assert agent.detect() is False

    # Create CLI config dir.
    (fake_home / ".claude").mkdir()
    assert agent.detect() is True


def test_codex_writes_valid_toml(fake_home: Path):
    result = CodexAgent().install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".codex" / "config.toml"
    with result.path.open("rb") as f:
        data = tomllib.load(f)
    assert data["mcp_servers"]["repo-rag"] == {"command": "rag", "args": ["mcp-server"]}


def test_cursor_mcp_project_scope(fake_home: Path, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    result = CursorAgent().install_mcp(scope="project", repo_root=repo)
    assert result is not None
    assert result.path == repo / ".cursor" / "mcp.json"
    assert "repo-rag" in _load_json(result.path)["mcpServers"]


def test_windsurf_mcp_writes_to_codeium_dir(fake_home: Path):
    result = WindsurfAgent().install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".codeium" / "windsurf" / "mcp_config.json"


def test_continue_mcp_writes_to_config_json(fake_home: Path):
    result = ContinueAgent().install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".continue" / "config.json"


def test_gemini_mcp_writes_settings_json(fake_home: Path):
    result = GeminiAgent().install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".gemini" / "settings.json"


def test_antigravity_mcp_writes_to_dotdir(fake_home: Path):
    result = AntigravityAgent().install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".antigravity" / "mcp.json"


def test_minimax_mcp_writes_to_minimax_mcp_json(fake_home: Path):
    result = MinimaxAgent().install_mcp(scope="user")
    assert result is not None
    assert result.path == fake_home / ".minimax" / "mcp" / "mcp.json"
    data = _load_json(result.path)
    assert data["mcpServers"]["repo-rag"] == {
        "command": "rag",
        "args": ["mcp-server"],
        "env": {},
        "enabled": True,
        "configured": True,
        "description": (
            "Local RAG indexer - search code with hybrid keyword + vector search. "
            "Tools: repo_rag_search, repo_rag_get_context, repo_rag_remember, "
            "repo_rag_forget, repo_rag_status"
        ),
    }


def test_minimax_mcp_preserves_builtin_entries(fake_home: Path):
    path = fake_home / ".minimax" / "mcp" / "mcp.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"mcpServers": {"playwright": {"command": "npx"}}}),
        encoding="utf-8",
    )
    MinimaxAgent().install_mcp(scope="user")
    data = _load_json(path)
    assert data["mcpServers"]["playwright"] == {"command": "npx"}
    assert "repo-rag" in data["mcpServers"]


def test_zed_uses_context_servers_key(fake_home: Path):
    result = ZedAgent().install_mcp(scope="user")
    assert result is not None
    data = _load_json(result.path)
    assert "context_servers" in data
    assert "repo-rag" in data["context_servers"]
