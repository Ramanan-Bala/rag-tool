# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/ramanan-bala/repo-rag/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ramanan-bala/repo-rag/releases/tag/v0.1.0
