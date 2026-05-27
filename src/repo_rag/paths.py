from __future__ import annotations

import os
from pathlib import Path

INDEX_DIR_ENV = "REPO_RAG_INDEX_DIR"


def get_index_root() -> Path:
    """Return the absolute path of the repo-rag index root.

    Resolution order:
      1. ``$REPO_RAG_INDEX_DIR`` if set (expanded for ``~``).
      2. ``~/.repo-rag``.
    """
    override = os.environ.get(INDEX_DIR_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".repo-rag").resolve()


def registry_path() -> Path:
    return get_index_root() / "registry.json"


def global_config_path() -> Path:
    return get_index_root() / "config.toml"


def repo_index_dir(repo_id: str) -> Path:
    return get_index_root() / repo_id


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists():
            return parent
    return cur
