from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from threading import Lock

from .paths import registry_path

_lock = Lock()


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return cleaned or "repo"


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:6]


def load_registry() -> dict[str, str]:
    path = registry_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_registry(reg: dict[str, str]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, indent=2, sort_keys=True), encoding="utf-8")


def lookup(repo_root: Path) -> str | None:
    return load_registry().get(str(repo_root.resolve()))


def register_repo(repo_root: Path, override_id: str | None = None) -> str:
    repo_root = repo_root.resolve()
    with _lock:
        reg = load_registry()
        key = str(repo_root)
        if key in reg and not override_id:
            return reg[key]
        existing_ids = {v for k, v in reg.items() if k != key}
        base = _safe_name(override_id or repo_root.name)
        repo_id = base
        if repo_id in existing_ids:
            repo_id = f"{base}-{_short_hash(key)}"
        reg[key] = repo_id
        save_registry(reg)
        return repo_id


def remove_repo(repo_root: Path) -> str | None:
    with _lock:
        reg = load_registry()
        key = str(repo_root.resolve())
        repo_id = reg.pop(key, None)
        if repo_id:
            save_registry(reg)
        return repo_id
