# MCP tools

repo-rag exposes five MCP tools when you run `rag mcp-server`. All read-only
tools are annotated `readOnlyHint=true, idempotentHint=true, openWorldHint=false`
so MCP clients that support auto-approval (Claude Code, Cursor, Factory Droid,
etc.) can run them without prompting.

If you omit the `repo` argument the server infers the current repo from its
working directory and looks it up in `~/.repo-rag/registry.json`.

## `repo_rag_search`

```json
{
  "name": "repo_rag_search",
  "arguments": {
    "query": "where is auth configured",
    "top_k": 20,
    "repo": null
  }
}
```

Returns JSON:

```json
{
  "repo": "/abs/path/to/repo",
  "results": [
    {
      "chunk_id": 42,
      "path": "src/auth.py",
      "score": 0.872,
      "start_line": 18,
      "end_line": 41,
      "language": "python",
      "sources": ["vector", "keyword"],
      "content": "..."
    }
  ]
}
```

Use this as the primary code search instead of Grep / ripgrep / Glob.

## `repo_rag_get_context`

```json
{
  "name": "repo_rag_get_context",
  "arguments": {
    "task": "fix the auth timeout regression in #1234",
    "max_tokens": 6000,
    "repo": null
  }
}
```

Returns a markdown context pack: a header summarising the task, any
remembered notes that look relevant, then the top chunks formatted as
`path:lines` code blocks. Call at the START of multi-step coding tasks.

## `repo_rag_remember`

```json
{
  "name": "repo_rag_remember",
  "arguments": {
    "note": "Redis TTL is the source of truth for session expiry",
    "source": "incident-2143",
    "repo": null
  }
}
```

Saves a durable note. Returns `{"id": 7, "ok": true}`. Notes survive
`rag rebuild` unless you pass `--wipe-memory`.

## `repo_rag_forget`

```json
{
  "name": "repo_rag_forget",
  "arguments": {
    "id": 7,
    "repo": null
  }
}
```

Removes a previously remembered note by id.

## `repo_rag_status`

```json
{
  "name": "repo_rag_status",
  "arguments": {"repo": null}
}
```

Returns:

```json
{
  "repo": "/abs/path/to/repo",
  "repo_id": "myrepo-1a2b3c",
  "indexed": true,
  "files": 1956,
  "chunks": 19800,
  "notes": 3,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "last_index_at": "2026-05-27T16:21:08Z",
  "last_rebuild_at": "2026-05-22T17:04:33Z",
  "hint": "Call repo_rag_search before Grep/ripgrep."
}
```

If the repo is not registered, returns `{"indexed": false, "hint": "Run `rag init` then `rag rebuild`."}`.
