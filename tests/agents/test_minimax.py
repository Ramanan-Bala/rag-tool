"""MiniMax Code agent integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repo_rag.agents import _rules_text as rt
from repo_rag.agents.minimax import MinimaxAgent
from repo_rag.cli import app

runner = CliRunner()


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


def _make_minimax_agent_files(home: Path) -> tuple[Path, Path]:
    coder = home / ".minimax" / "agents" / "coder" / "agent.md"
    mavis = home / ".minimax" / "agents" / "mavis" / "agent.md"
    for path in (coder, mavis):
        path.parent.mkdir(parents=True)
        path.write_text(
            "# existing\n\n<!-- mavis:builtin-agent-md-stub v2 -->\nkeep builtins\n",
            encoding="utf-8",
        )
    return coder, mavis


def test_minimax_detects_mcp_config_or_agent_files(fake_home: Path):
    agent = MinimaxAgent()
    assert agent.detect() is False

    mcp_config = fake_home / ".minimax" / "mcp" / "mcp.json"
    mcp_config.parent.mkdir(parents=True)
    mcp_config.write_text("{}", encoding="utf-8")
    assert agent.detect() is True

    mcp_config.unlink()
    coder, _ = _make_minimax_agent_files(fake_home)
    assert coder.exists()
    assert agent.detect() is True


def test_minimax_user_rules_install_writes_both_agent_files_before_builtin_marker(
    fake_home: Path,
):
    coder, mavis = _make_minimax_agent_files(fake_home)

    result = MinimaxAgent().install_rules(scope="user")

    assert result.written is True
    assert result.path == fake_home / ".minimax" / "agents" / "*" / "agent.md"
    for path in (coder, mavis):
        content = path.read_text(encoding="utf-8")
        assert rt.MD_BEGIN in content
        assert content.index(rt.MD_BEGIN) < content.index("<!-- mavis:builtin-agent-md-stub v2 -->")
        assert "mavis mcp call repo-rag repo_rag_search" in content


def test_minimax_user_rules_requires_minimax_directory(fake_home: Path):
    result = MinimaxAgent().install_rules(scope="user")

    assert result.written is False
    assert result.skipped_reason == "MiniMax config directory not found"


def test_minimax_uninstall_removes_repo_rag_block_from_both_agent_files(fake_home: Path):
    coder, mavis = _make_minimax_agent_files(fake_home)
    MinimaxAgent().install_rules(scope="user")

    assert MinimaxAgent().uninstall_rules(scope="user") is True

    for path in (coder, mavis):
        content = path.read_text(encoding="utf-8")
        assert rt.MD_BEGIN not in content
        assert "keep builtins" in content
        assert "<!-- mavis:builtin-agent-md-stub v2 -->" in content


def test_minimax_print_rules_uses_mavis_mcp_call_syntax(fake_home: Path):
    result = runner.invoke(
        app,
        ["agents", "print-rules", "--target", "minimax"],
        env={},
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "mavis mcp call repo-rag repo_rag_search" in result.stdout
    assert "repo_rag_forget" in result.stdout


def test_minimax_print_mcp_includes_description(fake_home: Path):
    result = runner.invoke(
        app,
        ["agents", "print-mcp", "--target", "minimax"],
        env={},
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert '"description": "Local RAG indexer' in result.stdout
    assert '"enabled": true' in result.stdout
    assert '"configured": true' in result.stdout


def test_minimax_agents_list_shows_user_rules_glob(fake_home: Path):
    _make_minimax_agent_files(fake_home)

    result = runner.invoke(app, ["agents", "list"], env={}, catch_exceptions=False)

    assert result.exit_code == 0
    assert "minimax" in result.stdout
    assert "MiniMax Code" in result.stdout
    assert ".minimax/agents/*/agent.md" in result.stdout


def test_minimax_mcp_entry_matches_required_shape(fake_home: Path):
    result = MinimaxAgent().install_mcp(scope="user")
    assert result is not None
    data = json.loads(result.path.read_text(encoding="utf-8"))

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
