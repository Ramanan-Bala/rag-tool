from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .chunker import chunk_text
from .config import GlobalConfig
from .embedder import make_embedder
from .embedder.base import EmbeddingProvider
from .fileutils import changed_files_via_git, detect_language, iter_repo_files
from .hasher import chunk_id as make_chunk_id
from .hasher import hash_text
from .paths import repo_index_dir
from .store.lance import LanceStore
from .store.sqlite import SqliteStore

ProgressCallback = Callable[[dict], None]


def _git_commit(repo_root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except Exception:
        return None


@dataclass
class IndexStats:
    files_seen: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    files_removed: int = 0
    chunks_added: int = 0
    chunks_cached: int = 0
    chunks_embedded: int = 0
    elapsed_sec: float = 0.0


class Indexer:
    WINDOW_SIZE = 16

    def __init__(
        self,
        repo_root: Path,
        repo_id: str,
        cfg: GlobalConfig,
        window_size: int | None = None,
        pace_sec: float = 0.0,
    ):
        self.repo_root = repo_root.resolve()
        self.repo_id = repo_id
        self.cfg = cfg
        self.window_size = window_size if window_size and window_size > 0 else self.WINDOW_SIZE
        self.pace_sec = max(0.0, float(pace_sec))
        self.index_dir = repo_index_dir(repo_id)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        (self.index_dir / "logs").mkdir(exist_ok=True)
        (self.index_dir / "cache").mkdir(exist_ok=True)
        self.sqlite = SqliteStore(self.index_dir / "metadata.sqlite")
        self.embedder: EmbeddingProvider | None = None
        self.lance: LanceStore | None = None

    def _ensure_embedder(self) -> None:
        if self.embedder is None:
            self.embedder = make_embedder(self.cfg.embedding)
            self.lance = LanceStore(self.index_dir / "lancedb", self.embedder.dim)

    def _read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def _cache_key(self, chunk_hash: str) -> str:
        assert self.embedder is not None
        return (
            f"{self.cfg.embedding.provider}::{self.cfg.embedding.model}"
            f"::{self.embedder.dim}::{chunk_hash}"
        )

    def index_all(
        self,
        changed_only: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> IndexStats:
        start = time.time()
        stats = IndexStats()
        git_commit = _git_commit(self.repo_root)

        all_files = list(
            iter_repo_files(
                self.repo_root,
                self.cfg.include_globs,
                self.cfg.exclude_globs,
                self.cfg.chunking.max_file_bytes,
            )
        )
        if changed_only:
            since_commit = self.sqlite.get_meta("last_index_commit")
            changed = changed_files_via_git(self.repo_root, since_commit=since_commit)
            if changed is None:
                files: list[Path] = all_files
            else:
                included_set = set(all_files)
                files = [p for p in changed if p.exists() and p in included_set]
                removed_rels: list[str] = []
                for p in changed:
                    if not p.exists():
                        try:
                            removed_rels.append(p.relative_to(self.repo_root).as_posix())
                        except ValueError:
                            continue
                indexed_paths = set(self.sqlite.list_paths())
                for rel in removed_rels:
                    if rel in indexed_paths:
                        self._delete_file_from_stores(rel)
                        stats.files_removed += 1
        else:
            files = all_files
            indexed_before = set(self.sqlite.list_paths())
            current_rels = {p.relative_to(self.repo_root).as_posix() for p in all_files}
            for rel in indexed_before - current_rels:
                self._delete_file_from_stores(rel)
                stats.files_removed += 1

        self._emit(on_progress, {"event": "scan_total", "total": len(files), "stats": stats})

        if files:
            self._emit(on_progress, {"event": "embed_load_start"})
            self._ensure_embedder()
            self._emit(on_progress, {"event": "embed_load_done"})

        log_path = self.index_dir / "logs" / "index.log"
        total_files = len(files)
        for win_start in range(0, total_files, self.window_size):
            window = files[win_start : win_start + self.window_size]
            self._process_window(
                window, stats, git_commit, on_progress, log_path, total_files, win_start
            )
            if self.pace_sec > 0 and win_start + self.window_size < total_files:
                self._emit(
                    on_progress, {"event": "pause", "seconds": self.pace_sec, "stats": stats}
                )
                time.sleep(self.pace_sec)

        stats.elapsed_sec = time.time() - start
        self.sqlite.set_meta("last_index_at", str(time.time()))
        if not changed_only:
            self.sqlite.set_meta("last_rebuild_at", str(time.time()))
        if git_commit:
            self.sqlite.set_meta("last_index_commit", git_commit)
        self._emit(on_progress, {"event": "complete", "stats": stats})
        return stats

    def rebuild(
        self,
        wipe_memory: bool = False,
        wipe_cache: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> IndexStats:
        self.sqlite.wipe_data(keep_cache=not wipe_cache, keep_notes=not wipe_memory)
        self._ensure_embedder()
        assert self.lance is not None
        self.lance.clear()
        return self.index_all(changed_only=False, on_progress=on_progress)

    def _emit(self, cb: ProgressCallback | None, event: dict) -> None:
        if cb is not None:
            try:
                cb(event)
            except Exception:
                pass

    def _delete_file_from_stores(self, rel: str) -> None:
        ids = self.sqlite.delete_file(rel)
        if ids:
            self._ensure_embedder()
            assert self.lance is not None
            self.lance.delete_chunks(ids)

    def _process_window(
        self,
        window: list[Path],
        stats: IndexStats,
        git_commit: str | None,
        on_progress: ProgressCallback | None,
        log_path: Path,
        total_files: int = 0,
        win_start: int = 0,
    ) -> None:
        pending: list[dict] = []
        for offset, p in enumerate(window):
            stats.files_seen += 1
            rel = ""
            try:
                rel = p.relative_to(self.repo_root).as_posix()
            except ValueError:
                rel = str(p)
            file_idx = win_start + offset + 1
            remaining = max(0, total_files - file_idx)
            try:
                size_for_log = 0
                try:
                    size_for_log = p.stat().st_size
                except OSError:
                    pass
                self._emit(
                    on_progress,
                    {
                        "event": "file_start",
                        "rel": rel,
                        "index": file_idx,
                        "total": total_files,
                        "remaining": remaining,
                        "size_bytes": size_for_log,
                        "stats": stats,
                    },
                )
                text = self._read_text(p)
                if text is None:
                    self._emit(
                        on_progress,
                        {
                            "event": "file_unreadable",
                            "rel": rel,
                            "index": file_idx,
                            "remaining": remaining,
                            "stats": stats,
                        },
                    )
                    self._emit(
                        on_progress,
                        {
                            "event": "file_done",
                            "rel": rel,
                            "index": file_idx,
                            "remaining": remaining,
                            "stats": stats,
                        },
                    )
                    continue
                content_hash = hash_text(text)
                prev = self.sqlite.get_file_hash(rel)
                if prev == content_hash:
                    stats.files_skipped += 1
                    self._emit(
                        on_progress,
                        {
                            "event": "file_skipped",
                            "rel": rel,
                            "index": file_idx,
                            "remaining": remaining,
                            "stats": stats,
                        },
                    )
                    self._emit(
                        on_progress,
                        {
                            "event": "file_done",
                            "rel": rel,
                            "index": file_idx,
                            "remaining": remaining,
                            "stats": stats,
                        },
                    )
                    continue
                chunks = chunk_text(
                    p,
                    rel,
                    text,
                    self.cfg.chunking.code_chunk_tokens,
                    self.cfg.chunking.prose_chunk_tokens,
                    self.cfg.chunking.overlap_tokens,
                )
                size_bytes = len(text.encode("utf-8"))
                self._emit(
                    on_progress,
                    {
                        "event": "file_chunked",
                        "rel": rel,
                        "index": file_idx,
                        "chunks": len(chunks),
                        "size_bytes": size_bytes,
                        "remaining": remaining,
                        "stats": stats,
                    },
                )
                try:
                    mtime = p.stat().st_mtime
                except OSError:
                    mtime = 0.0
                if not chunks:
                    try:
                        self.sqlite.upsert_file(
                            rel,
                            content_hash,
                            detect_language(p),
                            size_bytes,
                            mtime,
                            git_commit,
                        )
                    except OSError:
                        pass
                    self._emit(
                        on_progress,
                        {
                            "event": "file_done",
                            "rel": rel,
                            "index": file_idx,
                            "remaining": remaining,
                            "stats": stats,
                        },
                    )
                    continue
                rows: list[dict] = []
                for ch in chunks:
                    chash = hash_text(ch.content)
                    cid = make_chunk_id(self.repo_id, rel, ch.start_line, ch.end_line, ch.content)
                    rows.append(
                        {
                            "chunk_id": cid,
                            "path": rel,
                            "language": ch.language,
                            "chunk_hash": chash,
                            "start_line": ch.start_line,
                            "end_line": ch.end_line,
                            "content": ch.content,
                            "summary": None,
                        }
                    )
                pending.append(
                    {
                        "path": p,
                        "rel": rel,
                        "content_hash": content_hash,
                        "had_prev": prev is not None,
                        "rows": rows,
                        "size_bytes": size_bytes,
                        "mtime": mtime,
                        "index": file_idx,
                        "remaining": remaining,
                    }
                )
            except Exception as e:
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} ERROR {p}: {e}\n")
                self._emit(
                    on_progress,
                    {
                        "event": "file_error",
                        "rel": rel,
                        "index": file_idx,
                        "error": str(e),
                        "remaining": remaining,
                        "stats": stats,
                    },
                )
                self._emit(
                    on_progress,
                    {
                        "event": "file_done",
                        "rel": rel,
                        "index": file_idx,
                        "remaining": remaining,
                        "stats": stats,
                    },
                )

        if not pending:
            return

        self._ensure_embedder()
        assert self.embedder is not None
        assert self.lance is not None

        all_keys: list[str] = []
        locators: list[tuple] = []
        for fi, info in enumerate(pending):
            for ri, row in enumerate(info["rows"]):
                key = self._cache_key(row["chunk_hash"])
                all_keys.append(key)
                locators.append((fi, ri, key, row["chunk_hash"], row["content"]))

        self._emit(
            on_progress,
            {
                "event": "window_planned",
                "window_chunks": len(all_keys),
                "stats": stats,
            },
        )

        self._emit(
            on_progress,
            {
                "event": "cache_lookup_start",
                "chunks": len(all_keys),
                "stats": stats,
            },
        )
        cache_map = self.sqlite.cache_get_many(all_keys)

        to_embed: list[tuple] = []
        cache_hits = 0
        for fi, ri, key, chash, content in locators:
            cached = cache_map.get(key)
            if cached is not None:
                pending[fi]["rows"][ri]["_vector"] = np.frombuffer(cached, dtype=np.float32).copy()
                stats.chunks_cached += 1
                cache_hits += 1
            else:
                to_embed.append((fi, ri, key, chash, content))
        self._emit(
            on_progress,
            {
                "event": "cache_lookup_done",
                "hits": cache_hits,
                "to_embed": len(to_embed),
                "stats": stats,
            },
        )
        if cache_hits:
            self._emit(
                on_progress,
                {
                    "event": "cache_resolved",
                    "advance": cache_hits,
                    "stats": stats,
                },
            )

        if to_embed:
            batch_size = max(1, self.cfg.embedding.batch_size)
            new_cache: list[tuple] = []
            self._emit(
                on_progress,
                {
                    "event": "embed_start",
                    "chunks": len(to_embed),
                    "stats": stats,
                },
            )
            embed_start_t = time.time()
            for bs in range(0, len(to_embed), batch_size):
                slice_ = to_embed[bs : bs + batch_size]
                slice_text = [s[4] for s in slice_]
                arr = self.embedder.embed(slice_text)
                for k, (fi, ri, key, chash, _) in enumerate(slice_):
                    vec = arr[k].astype(np.float32)
                    pending[fi]["rows"][ri]["_vector"] = vec
                    new_cache.append(
                        (key, chash, self.embedder.model, self.embedder.dim, vec.tobytes())
                    )
                stats.chunks_embedded += len(slice_)
                self._emit(
                    on_progress,
                    {
                        "event": "embed_batch_done",
                        "advance": len(slice_),
                        "stats": stats,
                    },
                )
            self._emit(
                on_progress,
                {
                    "event": "embed_done",
                    "chunks": len(to_embed),
                    "elapsed_sec": time.time() - embed_start_t,
                    "stats": stats,
                },
            )
            self.sqlite.cache_put_many(new_cache)

        lance_batch: list[dict] = []
        for info in pending:
            if info["had_prev"]:
                removed = self.sqlite.delete_file(info["rel"])
                if removed:
                    self.lance.delete_chunks(removed)
            self.sqlite.insert_chunks(info["rows"])
            for r in info["rows"]:
                if "_vector" in r:
                    lance_batch.append(
                        {"chunk_id": r["chunk_id"], "path": info["rel"], "vector": r["_vector"]}
                    )
            try:
                self.sqlite.upsert_file(
                    info["rel"],
                    info["content_hash"],
                    detect_language(info["path"]),
                    info["size_bytes"],
                    info["mtime"],
                    git_commit,
                )
            except OSError:
                pass
            stats.files_indexed += 1
            stats.chunks_added += len(info["rows"])
            self._emit(
                on_progress,
                {
                    "event": "file_done",
                    "rel": info["rel"],
                    "index": info.get("index", 0),
                    "remaining": info.get("remaining", 0),
                    "stats": stats,
                },
            )

        if lance_batch:
            self.lance.upsert(lance_batch)
