from pathlib import Path

import pytest

from repo_rag.hooks import BEGIN, END, HOOK_NAMES, install, uninstall


def _make_git_repo(path: Path) -> None:
    (path / ".git" / "hooks").mkdir(parents=True)


def test_install_creates_hooks(tmp_path: Path):
    _make_git_repo(tmp_path)
    names = install(tmp_path)
    assert set(names) == set(HOOK_NAMES)
    for n in HOOK_NAMES:
        p = tmp_path / ".git" / "hooks" / n
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert BEGIN in content
        assert END in content


def test_install_preserves_existing_content(tmp_path: Path):
    _make_git_repo(tmp_path)
    pre = "#!/bin/sh\necho 'prior hook'\n"
    (tmp_path / ".git" / "hooks" / "post-commit").write_text(pre, encoding="utf-8")
    install(tmp_path)
    content = (tmp_path / ".git" / "hooks" / "post-commit").read_text(encoding="utf-8")
    assert "echo 'prior hook'" in content
    assert BEGIN in content


def test_install_idempotent(tmp_path: Path):
    _make_git_repo(tmp_path)
    install(tmp_path)
    first = (tmp_path / ".git" / "hooks" / "post-commit").read_text(encoding="utf-8")
    install(tmp_path)
    second = (tmp_path / ".git" / "hooks" / "post-commit").read_text(encoding="utf-8")
    assert first == second


def test_uninstall_removes_only_block(tmp_path: Path):
    _make_git_repo(tmp_path)
    pre = "#!/bin/sh\necho 'prior hook'\n"
    (tmp_path / ".git" / "hooks" / "post-commit").write_text(pre, encoding="utf-8")
    install(tmp_path)
    uninstall(tmp_path)
    content = (tmp_path / ".git" / "hooks" / "post-commit").read_text(encoding="utf-8")
    assert "echo 'prior hook'" in content
    assert BEGIN not in content
    assert END not in content


def test_install_without_git_raises(tmp_path: Path):
    with pytest.raises(RuntimeError):
        install(tmp_path)
