# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- OpenCode (CLI + Desktop) agent plugin (`rag agents setup --target opencode`).

## [0.1.6] - 2026-06-03

### Fixed

- Report default `model2vec` model download/cache failures as a concise,
  actionable CLI error instead of exposing the full Hugging Face traceback.

## [0.1.5] - 2026-06-01

### Added

- New `model2vec` embedding provider using code-specialized static embeddings
  (`minishlab/potion-code-16M`); it is now the **default** for fast, local,
  code-focused retrieval. `fastembed` remains bundled as the transformer
  fallback (better for prose/docs). The provider auto-trusts the OS certificate
  store (via `truststore`) and skips non-essential `*.py` files so model
  downloads work behind TLS-inspecting corporate proxies.
- `repo_rag_find_related` MCP tool and `rag find-related <file> <line>` CLI to
  surface code semantically similar to a known location.
- Content scoping for search: `rag search --content code|docs|config|all` and a
  matching `content` argument on the `repo_rag_search` / `repo_rag_get_context`
  MCP tools.
- Tree-sitter AST-aware chunking is installed and enabled by default
  (`chunking.use_tree_sitter`), with automatic fallback to regex chunking when
  a file's parser is unavailable or unsupported.

### Changed

- Retrieval ranking rewritten: Reciprocal Rank Fusion of vector + BM25 results,
  adaptive vector/keyword weighting for symbol-like queries, definition boosts,
  identifier sub-token matching, file-coherence boosts, and noise penalties for
  test/legacy/example files. `recency_boost` is now actually applied.

### Fixed

- `agents list` now renders correctly on Windows (paths are normalized so the
  `~` home shortcut applies, preventing the table from collapsing).
- `agents print-mcp` now emits the MCP JSON snippet as plain text so it is valid
  and copy-pasteable (previously Rich highlighting injected ANSI codes).

## [0.1.3] - 2026-05-31

### Added

- Add `rag preview` to show the files, chunks, cache hits, and embedding work before indexing.
- Add per-repo config helpers with `rag config repo-init` and `rag config show --path`.

### Fixed

- Apply per-repo config overrides consistently across repo-aware CLI and MCP operations.
- Omit `None` values when writing TOML config files.

## [0.1.2] - 2026-05-31

### Added

- Add MiniMax Agent / MiniMax Code integration via `rag agents setup --target minimax`.

## [0.1.1] - 2026-05-27

### Fixed

- Allow Python 3.14 installs to resolve PyArrow versions that publish CPython 3.14 wheels.

## [0.1.0] - 2026-05-27

### Added

- Initial public release.
- Local RAG indexer with hybrid keyword + vector search backed by SQLite (FTS5) and LanceDB.
- MCP server exposing `repo_rag_search`, `repo_rag_get_context`, `repo_rag_remember`, `repo_rag_forget`, and `repo_rag_status` with proper `ToolAnnotations` so read-only tools can be auto-approved by clients that support it.
- Multi-agent setup: hybrid `AGENTS.md` writer plus per-agent native plugins for Factory Droid, Claude Code, Claude Desktop, Codex CLI, Cursor, Windsurf, Cline, Continue.dev, Gemini CLI, Antigravity, Aider, and Zed.
- Background-mode git hooks (`post-commit`, `post-merge`, `post-checkout`) with truncating per-run log and `rag hooks log [--follow|--tail]` viewer.
- Hardware-aware runtime tuning: `BELOW_NORMAL_PRIORITY_CLASS` plus non-P-core affinity on Windows; `os.nice(+10)` on POSIX. Disable with `RAG_DISABLE_AFFINITY=1` or `--full-speed`.
- Windowed batch indexer with `--window-size`, `--pace-sec`, `--sequential`, `--full-speed`, `--threads`, and `--changed` flags.
- Six-section Code Search Policy installable into any agent's rules file via `rag agents setup`.

[Unreleased]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ramanan-bala/repo-rag/releases/tag/v0.1.0
