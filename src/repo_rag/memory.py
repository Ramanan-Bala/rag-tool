from __future__ import annotations

import re

from .store.sqlite import SqliteStore

_TAG_HINT_RE = re.compile(r"#([A-Za-z][A-Za-z0-9_-]{1,})")
_KEYWORDS = [
    "auth",
    "redis",
    "cache",
    "db",
    "database",
    "session",
    "api",
    "perf",
    "performance",
    "bug",
    "security",
    "deploy",
    "config",
    "test",
    "migration",
    "queue",
    "ssl",
    "token",
]


def infer_tags(note: str) -> str:
    explicit = _TAG_HINT_RE.findall(note)
    keywords = []
    for kw in _KEYWORDS:
        if re.search(rf"\b{kw}s?\b", note, re.IGNORECASE):
            keywords.append(kw.lower())
    tags = sorted(set(explicit + keywords))
    return ",".join(tags)


def remember(sqlite: SqliteStore, note: str, source: str | None = None) -> int:
    return sqlite.add_note(note.strip(), infer_tags(note) or None, source)


def forget(sqlite: SqliteStore, note_id: int) -> bool:
    return sqlite.delete_note(note_id)


def list_notes(sqlite: SqliteStore) -> list[dict]:
    return [dict(r) for r in sqlite.list_notes()]
