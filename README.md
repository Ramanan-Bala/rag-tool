# repo-rag

[![PyPI version](https://img.shields.io/pypi/v/repo-rag.svg)](https://pypi.org/project/repo-rag/)
[![CI](https://github.com/ramanan-bala/repo-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/ramanan-bala/repo-rag/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/repo-rag.svg)](https://pypi.org/project/repo-rag/)

> Local RAG indexer and MCP server for AI coding agents. Run it once per
> repo, and every MCP-compatible agent on your machine - Claude Code,
> Claude Desktop, Cursor, Windsurf, Codex CLI/Desktop, Gemini CLI, Factory Droid,
> MiniMax Agent, Antigravity, Aider, Cline, Continue.dev, Zed, and any future
> `AGENTS.md`-aware tool - searches your code through the same hybrid
> keyword + vector index instead of grepping blind.

## Quickstart

```bash
# Recommended: isolated global CLI via pipx
pipx install repo-rag

# Or inside an existing project venv
pip install repo-rag

cd /path/to/your/repo
rag init
rag rebuild

rag agents setup --all      # writes rules files + MCP configs for every detected agent
rag hooks install           # keep the index fresh on every commit / merge / checkout
```

That's it. Open Claude Code, Cursor, or any other supported agent and ask
"where is auth configured" - the agent will call `repo_rag_search` first.

> `repo-rag` pulls in lancedb, pyarrow, fastembed, and onnxruntime, so
> expect roughly **500 MB on disk** for the dependency stack regardless of
> install method. `pipx` keeps that footprint in one isolated environment
> instead of every project venv.

## What you get

- **One index, every agent.** Indexed under `~/.repo-rag/<repo-id>/` and
  shared across every MCP client. No per-tool re-embedding.
- **Hybrid retrieval.** SQLite FTS5 BM25 keyword search plus LanceDB vector
  search, merged with configurable weights.
- **Local by default.** The `fastembed` backend runs CPU-only ONNX inference
  with a 384-dim model; no network calls and no API keys.
- **Memory across sessions.** `repo_rag_remember` lets agents persist
  architectural decisions, gotchas, and invariants that survive
  `rag rebuild`.
- **Background-mode git hooks.** Re-indexing happens off the critical path
  with truncating per-run logs you can `--follow`.
- **Hardware-aware throttling.** On Windows, `BELOW_NORMAL_PRIORITY_CLASS`
  plus non-P-core affinity keeps your laptop responsive while indexing.

## Supported agents

| Agent | Rules | MCP auto-write | Docs |
|---|---|---|---|
| Factory Droid | `~/.factory/AGENTS.md`, `<repo>/AGENTS.md` | yes | [`docs/clients/factory.md`](docs/clients/factory.md) |
| Claude Code | `~/.claude/CLAUDE.md`, `<repo>/CLAUDE.md` | yes | [`docs/clients/claude_code.md`](docs/clients/claude_code.md) |
| Claude Desktop | (none) | yes (per-OS path) | [`docs/clients/claude_desktop.md`](docs/clients/claude_desktop.md) |
| Codex CLI/Desktop | `~/.codex/AGENTS.md`, `<repo>/AGENTS.md` | yes (TOML) | [`docs/clients/codex.md`](docs/clients/codex.md) |
| Cursor | `~/.cursor/rules/repo-rag.mdc`, `<repo>/.cursor/rules/repo-rag.mdc` | yes | [`docs/clients/cursor.md`](docs/clients/cursor.md) |
| Windsurf | `~/.codeium/windsurf/global_rules.md`, `<repo>/.windsurfrules` | yes | [`docs/clients/windsurf.md`](docs/clients/windsurf.md) |
| Cline | `<repo>/AGENTS.md` | manual (VS Code settings) | [`docs/clients/cline.md`](docs/clients/cline.md) |
| Continue.dev | `~/.continue/AGENTS.md`, `<repo>/AGENTS.md` | yes | [`docs/clients/continue.md`](docs/clients/continue.md) |
| Gemini CLI | `~/.gemini/GEMINI.md`, `<repo>/GEMINI.md` | yes | [`docs/clients/gemini.md`](docs/clients/gemini.md) |
| Google Antigravity | `~/.antigravity/AGENTS.md`, `<repo>/AGENTS.md` | yes | [`docs/clients/antigravity.md`](docs/clients/antigravity.md) |
| Aider | `~/.aider/CONVENTIONS.md`, `<repo>/CONVENTIONS.md` | reference YAML | [`docs/clients/aider.md`](docs/clients/aider.md) |
| MiniMax Agent | `<repo>/AGENTS.md` | yes | [`docs/clients/minimax.md`](docs/clients/minimax.md) |
| Zed | `<zed-config>/.rules`, `<repo>/.rules` | yes (`context_servers`) | [`docs/clients/zed.md`](docs/clients/zed.md) |
| Universal (AGENTS.md) | `~/.config/repo-rag/AGENTS.md`, `<repo>/AGENTS.md` | n/a | [`docs/clients/universal.md`](docs/clients/universal.md) |

Run `rag agents list` for a live table of what is detected on your machine.

## MCP tools

The server exposed by `rag mcp-server` advertises five tools (full reference
in [`docs/mcp-tools.md`](docs/mcp-tools.md)):

| Tool | Purpose |
|---|---|
| `repo_rag_search` | Primary hybrid search; use instead of Grep / ripgrep / Glob. |
| `repo_rag_get_context` | Markdown context pack for a multi-step task. |
| `repo_rag_remember` | Persist a durable note for future sessions. |
| `repo_rag_forget` | Remove a note by id. |
| `repo_rag_status` | Index health summary. |

Read-only tools are annotated `readOnlyHint=true, idempotentHint=true,
openWorldHint=false` so MCP clients can auto-approve them in strict trust
modes.

## Performance highlights

- 3-10 chunks/sec on a typical laptop with the default `fastembed` model.
- Embedding cache keyed by `(provider, model, dim, sha256(content))` makes
  interrupted rebuilds resume cheaply and lets you switch providers without
  invalidating the unrelated rows.
- `--window-size`, `--pace-sec`, `--sequential`, `--full-speed`, and
  `--threads` cover every tuning knob from "go as fast as possible" to "do
  not interfere with anything I am doing".

See [`docs/performance.md`](docs/performance.md) for the full guide.

## Configuration

The global config lives at `~/.repo-rag/config.toml`. Override per-repo at
`~/.repo-rag/<repo-id>/config.toml`. Every value can also be set with an
environment variable (`RAG_EMBEDDING_PROVIDER`, `REPO_RAG_INDEX_DIR`, ...).

Full reference: [`docs/configuration.md`](docs/configuration.md).

## Storage layout

```
~/.repo-rag/
  registry.json
  config.toml
  <repo_id>/
    metadata.sqlite      # files, chunks, FTS5, notes, embedding cache
    lancedb/             # vector store
    cache/
    logs/
```

Nothing is written inside your repo apart from optional `AGENTS.md`,
`CLAUDE.md`, etc. (which you can `.gitignore` or commit, your choice).

## Docker

```bash
docker pull ghcr.io/ramanan-bala/repo-rag:latest
```

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "~/.repo-rag:/data/.repo-rag",
        "ghcr.io/ramanan-bala/repo-rag:latest"
      ]
    }
  }
}
```

## Troubleshooting

Common gotchas (Windows model load hang, AV interaction on corporate
machines, hybrid-CPU thread tuning, MCP server PATH issues, etc.) live in
[`docs/troubleshooting.md`](docs/troubleshooting.md).

## Contributing

Pull requests welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup,
test, lint, and release-process notes. To add a new agent plugin, follow
[`docs/development.md`](docs/development.md#adding-a-new-agent-plugin).

## License

MIT. See [`LICENSE`](LICENSE).

Code of Conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
Security policy: [`SECURITY.md`](SECURITY.md).
