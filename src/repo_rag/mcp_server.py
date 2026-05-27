from __future__ import annotations

from ._runtime import apply_runtime_tuning

apply_runtime_tuning(low_priority=False)

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .config import load_global_config
from .context import build_context_pack
from .embedder import make_embedder
from .memory import forget as memory_forget
from .memory import remember as memory_remember
from .paths import find_repo_root, repo_index_dir
from .registry import lookup
from .search import hybrid_search
from .store.lance import LanceStore
from .store.sqlite import SqliteStore

# MCP server for repo-rag. Speaks the Model Context Protocol over stdio so any
# MCP-compatible AI coding agent (Claude Code, Claude Desktop, Codex CLI,
# Cursor, Windsurf, Gemini CLI, Factory Droid, Antigravity, Aider, Cline,
# Continue.dev, Zed, and any future agent that loads MCP tools) can call its
# read-only and memory tools as first-class actions.
mcp = FastMCP("repo-rag")


def _open_repo(repo: str | None = None):
    repo_root = Path(repo).resolve() if repo else find_repo_root()
    repo_id = lookup(repo_root)
    if not repo_id:
        raise RuntimeError(
            f"Repo at {repo_root} is not registered with repo-rag. "
            f"Run `rag init` inside the repo first."
        )
    cfg = load_global_config()
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    embedder = make_embedder(cfg.embedding)
    lance = LanceStore(repo_index_dir(repo_id) / "lancedb", embedder.dim)
    return repo_root, repo_id, cfg, sqlite, embedder, lance


@mcp.tool(
    description=(
        "PRIMARY code search for the current repository. ALWAYS prefer this tool over "
        "Grep, ripgrep, or Glob for any question about code, symbols, files, or behavior "
        "in the indexed codebase. Returns ranked semantic + keyword matches with file "
        "paths and line ranges."
    ),
    annotations=ToolAnnotations(
        title="Search Code (repo-rag)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def repo_rag_search(query: str, top_k: int = 20, repo: str | None = None) -> str:
    repo_root, _, cfg, sqlite, embedder, lance = _open_repo(repo)
    hits = hybrid_search(query, embedder, lance, sqlite, cfg, top_k=top_k)
    payload = [
        {
            "chunk_id": h.chunk_id,
            "path": h.path,
            "score": round(h.score, 4),
            "start_line": h.start_line,
            "end_line": h.end_line,
            "language": h.language,
            "sources": h.sources,
            "content": h.content,
        }
        for h in hits
    ]
    return json.dumps({"repo": str(repo_root), "results": payload}, indent=2)


@mcp.tool(
    description=(
        "Build a curated markdown context pack for a given task. Call at the START of "
        "any non-trivial task to load relevant files, chunks, and remembered notes."
    ),
    annotations=ToolAnnotations(
        title="Build Context Pack (repo-rag)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def repo_rag_get_context(task: str, max_tokens: int = 6000, repo: str | None = None) -> str:
    repo_root, _, cfg, sqlite, embedder, lance = _open_repo(repo)
    hits = hybrid_search(task, embedder, lance, sqlite, cfg)
    return build_context_pack(task, hits, sqlite, cfg, repo_root, max_tokens=max_tokens)


@mcp.tool(
    description=(
        "Persist a durable note (architectural decision, gotcha, invariant) for future "
        "sessions. Tags are inferred automatically."
    ),
    annotations=ToolAnnotations(
        title="Remember Note (repo-rag)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
def repo_rag_remember(note: str, source: str | None = None, repo: str | None = None) -> str:
    _, _, _, sqlite, _, _ = _open_repo(repo)
    note_id = memory_remember(sqlite, note, source)
    return json.dumps({"id": note_id, "ok": True})


@mcp.tool(
    description="Remove a previously remembered note by its numeric id.",
    annotations=ToolAnnotations(
        title="Forget Note (repo-rag)",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def repo_rag_forget(id: int, repo: str | None = None) -> str:
    _, _, _, sqlite, _, _ = _open_repo(repo)
    ok = memory_forget(sqlite, int(id))
    return json.dumps({"id": id, "removed": ok})


@mcp.tool(
    description=(
        "Return index health: counts, last index time, embedding model, and a hint "
        "to use repo_rag_search before Grep/ripgrep."
    ),
    annotations=ToolAnnotations(
        title="Index Status (repo-rag)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def repo_rag_status(repo: str | None = None) -> str:
    repo_root = Path(repo).resolve() if repo else find_repo_root()
    repo_id = lookup(repo_root)
    if not repo_id:
        return json.dumps(
            {
                "repo": str(repo_root),
                "indexed": False,
                "hint": "Run `rag init` then `rag rebuild`.",
            }
        )
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    cfg = load_global_config()
    status = {
        "repo": str(repo_root),
        "repo_id": repo_id,
        "indexed": True,
        "files": sqlite.count_files(),
        "chunks": sqlite.count_chunks(),
        "notes": sqlite.count_notes(),
        "embedding_model": cfg.embedding.model,
        "last_index_at": sqlite.get_meta("last_index_at"),
        "last_rebuild_at": sqlite.get_meta("last_rebuild_at"),
        "hint": "Call repo_rag_search before Grep/ripgrep.",
    }
    return json.dumps(status, indent=2)


def run() -> None:
    mcp.run()
