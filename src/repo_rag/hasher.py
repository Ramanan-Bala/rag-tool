from __future__ import annotations

import hashlib
from pathlib import Path


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def short_hash(text: str, length: int = 12) -> str:
    return hash_text(text)[:length]


def hash_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def chunk_id(repo_id: str, rel_path: str, start_line: int, end_line: int, content: str) -> str:
    key = f"{repo_id}\0{rel_path}\0{start_line}-{end_line}\0{hash_text(content)}"
    return short_hash(key, 16)
