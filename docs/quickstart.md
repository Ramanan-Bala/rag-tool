# Quickstart

repo-rag indexes a code repository on your machine, exposes hybrid keyword +
vector search through a CLI, and serves the same search as MCP tools so any
MCP-compatible AI coding agent can call it as a first-class action.

## 1. Install

### With pipx (recommended)

```bash
pipx install repo-rag
```

`pipx` creates a dedicated, hidden virtualenv under `~/.local/pipx/venvs/repo-rag/`
(or `%USERPROFILE%\pipx\venvs\repo-rag\` on Windows) and puts the `rag`
launcher on your PATH. The CLI is then usable from any directory without
polluting your project Pythons. Upgrade with `pipx upgrade repo-rag`,
uninstall with `pipx uninstall repo-rag`.

If you do not have pipx yet:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

### Inside an existing project venv

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell
# source .venv/bin/activate  # macOS / Linux
pip install repo-rag
```

This gives one `rag` per project; useful if you want pinned versions per
codebase, but the dependency stack is duplicated for each venv.

### Footprint disclosure

Either install path pulls in lancedb, pyarrow, fastembed, and onnxruntime
as transitive dependencies. Plan for **~500 MB on disk** for the dependency
stack. The `repo-rag` wheel itself is well under 1 MB - the size is native
binaries from the vector-store and embedding stack.

### Or with Docker

```bash
docker pull ghcr.io/<YOUR_GITHUB_USERNAME>/repo-rag:latest
```

The Docker image runs `rag mcp-server` by default and persists the index under
`/data/.repo-rag`. Mount your home index directory in:

```bash
docker run -i --rm \
  -v "$HOME/.repo-rag:/data/.repo-rag" \
  ghcr.io/<YOUR_GITHUB_USERNAME>/repo-rag:latest
```

## 2. Verify

```bash
rag --version
rag --help
```

## 3. Index your first repo

```bash
cd /path/to/your/repo
rag init
rag rebuild
```

The first `rag rebuild` downloads the default embedding model (`BAAI/bge-small-en-v1.5`,
about 80 MB) into a fastembed cache and produces:

- `~/.repo-rag/<repo-id>/metadata.sqlite` - files, chunks, FTS5 keyword index, memory notes, embedding cache
- `~/.repo-rag/<repo-id>/lancedb/` - vector store

Nothing is written inside the repo apart from optional git hooks.

## 4. Search

```bash
rag search "where is auth configured"
rag search "auth timeout" --json
rag ask "how does session expiry work"
rag context "fix slow login" --max-tokens 6000 -o ctx.md
```

## 5. Wire up an AI agent

```bash
rag agents list                  # see which agents are detected on this machine
rag agents setup --all           # write rules files + MCP configs everywhere
rag agents setup --target cursor # only Cursor
rag agents print-mcp             # dump the JSON snippet to paste manually
```

After setup, your agent will see five MCP tools - `repo_rag_search`,
`repo_rag_get_context`, `repo_rag_remember`, `repo_rag_forget`,
`repo_rag_status` - and a rules file telling it to prefer those tools over
Grep/Glob for code questions.

## 6. Keep the index fresh

```bash
rag index --changed
rag hooks install                # auto re-index after commit/merge/checkout
rag hooks log --follow           # watch the hook output live
```

## Where to go next

- [`docs/configuration.md`](configuration.md) - every knob, plus env overrides.
- [`docs/mcp-tools.md`](mcp-tools.md) - reference for the five MCP tools.
- [`docs/performance.md`](performance.md) - tuning indexing speed vs system load.
- [`docs/clients/`](clients/) - per-agent setup guides.
- [`docs/troubleshooting.md`](troubleshooting.md) - common issues and workarounds.
