from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .chunker import chunk_text
from .config import GlobalConfig
from .fileutils import changed_files_via_git, detect_language, iter_repo_files
from .hasher import hash_text
from .paths import repo_index_dir
from .store.sqlite import SqliteStore


@dataclass
class PreviewFile:
    path: str
    size_bytes: int
    language: str
    chunks: int
    cached_chunks: int
    embed_chunks: int


@dataclass
class PreviewGroup:
    key: str
    files: int
    bytes: int
    chunks: int
    cached_chunks: int
    embed_chunks: int


@dataclass
class IndexPreview:
    repo_root: Path
    repo_id: str
    config_path: Path
    files: list[PreviewFile]
    cache_available: bool

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files)

    @property
    def total_chunks(self) -> int:
        return sum(item.chunks for item in self.files)

    @property
    def cached_chunks(self) -> int:
        return sum(item.cached_chunks for item in self.files)

    @property
    def embed_chunks(self) -> int:
        return sum(item.embed_chunks for item in self.files)

    def by_extension(self) -> list[PreviewGroup]:
        return _group_files(self.files, lambda item: Path(item.path).suffix.lower() or "(none)")

    def by_language(self) -> list[PreviewGroup]:
        return _group_files(self.files, lambda item: item.language)


def _group_files(
    files: list[PreviewFile], key_fn: Callable[[PreviewFile], str]
) -> list[PreviewGroup]:
    grouped: dict[str, PreviewGroup] = {}
    for item in files:
        key = key_fn(item)
        group = grouped.get(key)
        if group is None:
            group = PreviewGroup(
                key=key, files=0, bytes=0, chunks=0, cached_chunks=0, embed_chunks=0
            )
            grouped[key] = group
        group.files += 1
        group.bytes += item.size_bytes
        group.chunks += item.chunks
        group.cached_chunks += item.cached_chunks
        group.embed_chunks += item.embed_chunks
    return sorted(grouped.values(), key=lambda group: (-group.chunks, group.key))


def _cache_key(cfg: GlobalConfig, chunk_hash: str) -> str:
    return f"{cfg.embedding.provider}::{cfg.embedding.model}::{cfg.embedding.dim}::{chunk_hash}"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _candidate_files(
    repo_root: Path,
    sqlite: SqliteStore,
    cfg: GlobalConfig,
    changed_only: bool,
) -> list[Path]:
    all_files = list(
        iter_repo_files(
            repo_root,
            cfg.include_globs,
            cfg.exclude_globs,
            cfg.chunking.max_file_bytes,
        )
    )
    if not changed_only:
        return all_files
    changed = changed_files_via_git(repo_root, since_commit=sqlite.get_meta("last_index_commit"))
    if changed is None:
        return all_files
    included = set(all_files)
    return [path for path in changed if path.exists() and path in included]


def build_index_preview(
    repo_root: Path,
    repo_id: str,
    cfg: GlobalConfig,
    *,
    changed_only: bool = False,
    include_cache_counts: bool = True,
) -> IndexPreview:
    root = repo_root.resolve()
    index_dir = repo_index_dir(repo_id)
    index_dir.mkdir(parents=True, exist_ok=True)
    sqlite = SqliteStore(index_dir / "metadata.sqlite")
    cache_available = include_cache_counts
    preview_files: list[PreviewFile] = []

    try:
        files = _candidate_files(root, sqlite, cfg, changed_only)
        for path in files:
            try:
                rel = path.relative_to(root).as_posix()
                size = path.stat().st_size
            except OSError:
                continue
            text = _read_text(path)
            if text is None:
                continue
            chunks = chunk_text(
                path,
                rel,
                text,
                cfg.chunking.code_chunk_tokens,
                cfg.chunking.prose_chunk_tokens,
                cfg.chunking.overlap_tokens,
            )
            cache_keys = [_cache_key(cfg, hash_text(chunk.content)) for chunk in chunks]
            cached = 0
            if include_cache_counts and cache_keys:
                try:
                    cached = len(sqlite.cache_get_many(cache_keys))
                except Exception:
                    cache_available = False
                    cached = 0
            preview_files.append(
                PreviewFile(
                    path=rel,
                    size_bytes=size,
                    language=detect_language(path),
                    chunks=len(chunks),
                    cached_chunks=cached,
                    embed_chunks=max(0, len(chunks) - cached),
                )
            )
    finally:
        sqlite.close()

    preview_files.sort(key=lambda item: item.path)
    return IndexPreview(
        repo_root=root,
        repo_id=repo_id,
        config_path=index_dir / "config.toml",
        files=preview_files,
        cache_available=cache_available,
    )


def preview_to_dict(preview: IndexPreview, *, include_files: bool = True) -> dict:
    payload = {
        "repo": str(preview.repo_root),
        "repo_id": preview.repo_id,
        "config_path": str(preview.config_path),
        "files": preview.total_files,
        "bytes": preview.total_bytes,
        "chunks": preview.total_chunks,
        "cached_chunks": preview.cached_chunks,
        "embed_chunks": preview.embed_chunks,
        "cache_available": preview.cache_available,
        "by_extension": [_group_to_dict(group, "extension") for group in preview.by_extension()],
        "by_language": [_group_to_dict(group, "language") for group in preview.by_language()],
    }
    if include_files:
        payload["files_detail"] = [item.__dict__.copy() for item in preview.files]
    return payload


def _group_to_dict(group: PreviewGroup, key_name: str) -> dict:
    return {
        key_name: group.key,
        "files": group.files,
        "bytes": group.bytes,
        "chunks": group.chunks,
        "cached_chunks": group.cached_chunks,
        "embed_chunks": group.embed_chunks,
    }
