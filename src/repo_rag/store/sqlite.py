from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    language TEXT,
    size_bytes INTEGER,
    last_modified REAL,
    indexed_at REAL,
    git_commit TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    language TEXT,
    chunk_hash TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    content TEXT NOT NULL,
    summary TEXT,
    indexed_at REAL,
    FOREIGN KEY (path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(chunk_hash);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    path UNINDEXED,
    chunk_id UNINDEXED,
    tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS memory_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note TEXT NOT NULL,
    tags TEXT,
    source TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_notes_fts USING fts5(
    note,
    tags,
    id UNINDEXED,
    tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS embedding_cache (
    cache_key TEXT PRIMARY KEY,
    chunk_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class SqliteStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def tx(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def upsert_file(
        self,
        path: str,
        content_hash: str,
        language: str,
        size_bytes: int,
        last_modified: float,
        git_commit: str | None,
    ) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO files(path, content_hash, language, size_bytes, last_modified, indexed_at, git_commit) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET "
                "content_hash=excluded.content_hash, language=excluded.language, "
                "size_bytes=excluded.size_bytes, last_modified=excluded.last_modified, "
                "indexed_at=excluded.indexed_at, git_commit=excluded.git_commit",
                (path, content_hash, language, size_bytes, last_modified, time.time(), git_commit),
            )

    def get_file_hash(self, path: str) -> str | None:
        row = self._conn.execute(
            "SELECT content_hash FROM files WHERE path = ?", (path,)
        ).fetchone()
        return row["content_hash"] if row else None

    def delete_file(self, path: str) -> list[str]:
        with self.tx() as c:
            cur = c.execute("SELECT chunk_id FROM chunks WHERE path = ?", (path,))
            chunk_ids = [r["chunk_id"] for r in cur.fetchall()]
            c.execute(
                "DELETE FROM chunks_fts WHERE chunk_id IN "
                "(SELECT chunk_id FROM chunks WHERE path = ?)",
                (path,),
            )
            c.execute("DELETE FROM chunks WHERE path = ?", (path,))
            c.execute("DELETE FROM files WHERE path = ?", (path,))
        return chunk_ids

    def insert_chunks(self, chunks: Iterable[dict]) -> None:
        rows = list(chunks)
        if not rows:
            return
        with self.tx() as c:
            now = time.time()
            for r in rows:
                r["indexed_at"] = now
            c.executemany(
                "INSERT OR REPLACE INTO chunks"
                "(chunk_id, path, language, chunk_hash, start_line, end_line, content, summary, indexed_at) "
                "VALUES (:chunk_id, :path, :language, :chunk_hash, :start_line, :end_line, :content, :summary, :indexed_at)",
                rows,
            )
            c.executemany(
                "INSERT INTO chunks_fts(content, path, chunk_id) "
                "VALUES (:content, :path, :chunk_id)",
                rows,
            )

    def list_paths(self) -> list[str]:
        rows = self._conn.execute("SELECT path FROM files").fetchall()
        return [r["path"] for r in rows]

    def fts_search(self, query: str, limit: int = 50) -> list[tuple[str, str, float]]:
        try:
            rows = self._conn.execute(
                "SELECT chunk_id, path, bm25(chunks_fts) AS score "
                "FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY score LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [(r["chunk_id"], r["path"], -float(r["score"])) for r in rows]

    def get_chunk(self, chunk_id: str) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()

    def get_chunks(self, chunk_ids: Sequence[str]) -> list[sqlite3.Row]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" * len(chunk_ids))
        rows = self._conn.execute(
            f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})",
            tuple(chunk_ids),
        ).fetchall()
        return list(rows)

    def wipe_data(self, keep_cache: bool = True, keep_notes: bool = True) -> None:
        with self.tx() as c:
            c.execute("DELETE FROM chunks_fts")
            c.execute("DELETE FROM chunks")
            c.execute("DELETE FROM files")
            c.execute("DELETE FROM meta")
            if not keep_cache:
                c.execute("DELETE FROM embedding_cache")
            if not keep_notes:
                c.execute("DELETE FROM memory_notes_fts")
                c.execute("DELETE FROM memory_notes")

    def count_files(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS n FROM files").fetchone()["n"]

    def count_chunks(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]

    def set_meta(self, key: str, value: str) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def add_note(self, note: str, tags: str | None, source: str | None) -> int:
        with self.tx() as c:
            now = time.time()
            cur = c.execute(
                "INSERT INTO memory_notes(note, tags, source, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (note, tags, source, now, now),
            )
            note_id = cur.lastrowid
            c.execute(
                "INSERT INTO memory_notes_fts(note, tags, id) VALUES (?, ?, ?)",
                (note, tags or "", str(note_id)),
            )
            return note_id

    def list_notes(self) -> list[sqlite3.Row]:
        return list(
            self._conn.execute("SELECT * FROM memory_notes ORDER BY updated_at DESC").fetchall()
        )

    def delete_note(self, note_id: int) -> bool:
        with self.tx() as c:
            cur = c.execute("DELETE FROM memory_notes WHERE id = ?", (note_id,))
            c.execute("DELETE FROM memory_notes_fts WHERE id = ?", (str(note_id),))
            return cur.rowcount > 0

    def search_notes(self, query: str, limit: int = 10) -> list[sqlite3.Row]:
        try:
            rows = self._conn.execute(
                "SELECT n.* FROM memory_notes_fts f "
                "JOIN memory_notes n ON n.id = CAST(f.id AS INTEGER) "
                "WHERE memory_notes_fts MATCH ? "
                "ORDER BY bm25(memory_notes_fts) LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return list(rows)

    def count_notes(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS n FROM memory_notes").fetchone()["n"]

    def cache_get(self, cache_key: str) -> bytes | None:
        row = self._conn.execute(
            "SELECT vector FROM embedding_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        return row["vector"] if row else None

    def cache_get_many(self, cache_keys: Sequence[str]) -> dict:
        if not cache_keys:
            return {}
        out: dict = {}
        CHUNK = 500
        for start in range(0, len(cache_keys), CHUNK):
            slab = cache_keys[start : start + CHUNK]
            placeholders = ",".join("?" * len(slab))
            rows = self._conn.execute(
                f"SELECT cache_key, vector FROM embedding_cache WHERE cache_key IN ({placeholders})",
                tuple(slab),
            ).fetchall()
            for r in rows:
                out[r["cache_key"]] = r["vector"]
        return out

    def cache_put(
        self, cache_key: str, chunk_hash: str, model: str, dim: int, vector: bytes
    ) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO embedding_cache"
                "(cache_key, chunk_hash, model, dim, vector, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (cache_key, chunk_hash, model, dim, vector, time.time()),
            )

    def cache_put_many(self, items: Sequence[tuple[str, str, str, int, bytes]]) -> None:
        if not items:
            return
        now = time.time()
        with self.tx() as c:
            c.executemany(
                "INSERT OR REPLACE INTO embedding_cache"
                "(cache_key, chunk_hash, model, dim, vector, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(k, ch, m, d, v, now) for (k, ch, m, d, v) in items],
            )
