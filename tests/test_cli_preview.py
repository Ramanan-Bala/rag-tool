import json
from pathlib import Path

from typer.testing import CliRunner

from repo_rag.cli import app
from repo_rag.paths import repo_index_dir
from repo_rag.registry import register_repo

runner = CliRunner()


def test_preview_defaults_to_cwd(fake_repo: Path, isolated_index_root: Path, monkeypatch):
    register_repo(fake_repo)
    monkeypatch.chdir(fake_repo)

    result = runner.invoke(app, ["preview", "--json"], env={}, catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repo"] == str(fake_repo.resolve())
    assert payload["files"] == 2
    assert {item["path"] for item in payload["files_detail"]} == {"README.md", "src/main.py"}


def test_preview_uses_per_repo_config(fake_repo: Path, isolated_index_root: Path):
    repo_id = register_repo(fake_repo)
    repo_index_dir(repo_id).mkdir(parents=True)
    (repo_index_dir(repo_id) / "config.toml").write_text(
        'exclude_globs = ["README.md"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["preview", str(fake_repo), "--json"],
        env={},
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [item["path"] for item in payload["files_detail"]] == ["src/main.py"]


def test_config_repo_init_writes_repo_config(fake_repo: Path, isolated_index_root: Path):
    repo_id = register_repo(fake_repo)
    cfg_path = repo_index_dir(repo_id) / "config.toml"

    result = runner.invoke(
        app,
        ["config", "repo-init", str(fake_repo)],
        env={},
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert cfg_path.exists()
    content = cfg_path.read_text(encoding="utf-8")
    assert "exclude_globs" in content
    assert "config.toml" in result.stdout


def test_config_show_path_uses_repo_config(fake_repo: Path, isolated_index_root: Path):
    repo_id = register_repo(fake_repo)
    repo_index_dir(repo_id).mkdir(parents=True)
    (repo_index_dir(repo_id) / "config.toml").write_text(
        'exclude_globs = ["README.md"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["config", "show", "--path", str(fake_repo)],
        env={},
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["exclude_globs"] == ["README.md"]
