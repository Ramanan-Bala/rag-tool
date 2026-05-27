"""Round-trip tests for every plugin's rules install/uninstall."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_rag.agents import _rules_text as rt
from repo_rag.agents import iter_plugins
from repo_rag.agents.base import AgentPlugin


def _redirect_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setattr(Path, "home", lambda: home)


def _fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fakerepo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


@pytest.mark.parametrize("plugin", list(iter_plugins()), ids=lambda p: p.name)
def test_project_rules_round_trip_preserves_existing_text(
    plugin: AgentPlugin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    home = tmp_path / "home"
    home.mkdir()
    _redirect_home(monkeypatch, home)
    repo = _fake_repo(tmp_path)

    project_path = plugin.project_rules_path(repo)
    if project_path is None:
        pytest.skip(f"{plugin.name} has no project rules path")

    # Cursor's plugin always overwrites the whole .mdc file, so the "preserve
    # outside text" contract only applies to plugins that use Markdown markers.
    if plugin.name == "cursor":
        plugin.install_rules(scope="project", repo_root=repo)
        assert project_path.exists()
        assert rt.MD_BEGIN in project_path.read_text(encoding="utf-8")
        assert plugin.uninstall_rules(scope="project", repo_root=repo)
        assert not project_path.exists()
        return

    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text("# existing user content\nkeep me\n", encoding="utf-8")

    result = plugin.install_rules(scope="project", repo_root=repo)
    assert result is not None
    assert project_path.exists()
    assert "keep me" in project_path.read_text(encoding="utf-8")
    assert rt.MD_BEGIN in project_path.read_text(encoding="utf-8")

    assert plugin.uninstall_rules(scope="project", repo_root=repo) is True
    assert "keep me" in project_path.read_text(encoding="utf-8")
    assert rt.MD_BEGIN not in project_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("plugin", list(iter_plugins()), ids=lambda p: p.name)
def test_user_rules_round_trip(
    plugin: AgentPlugin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    home = tmp_path / "home"
    home.mkdir()
    _redirect_home(monkeypatch, home)
    if plugin.rules_optional:
        result = plugin.install_rules(scope="user")
        assert result.skipped_reason
        return
    user_path = plugin.user_rules_path()
    if user_path is None:
        result = plugin.install_rules(scope="user")
        assert result.skipped_reason
        return
    result = plugin.install_rules(scope="user")
    assert result.path == user_path
    assert user_path.exists()
    assert plugin.uninstall_rules(scope="user") is True
