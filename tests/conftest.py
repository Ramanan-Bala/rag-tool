from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def isolated_index_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo-rag"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("REPO_RAG_INDEX_DIR", str(root))
    return root


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "myrepo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "main.py").write_text(
        "def add(a, b):\n    return a + b\n\n"
        "class Calculator:\n    def multiply(self, x, y):\n        return x * y\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        "# myrepo\n\nA test repo.\n\n## Usage\n\nCall `add(a, b)`.\n",
        encoding="utf-8",
    )
    (repo / ".git").mkdir()
    return repo
