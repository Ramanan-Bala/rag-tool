# repo-rag - Session Handoff

This document hands off ongoing OSS-publish work to a fresh chat session.
The previous session hit cumulative content-filter trips and could no longer
make tool calls reliably.

## Approved spec

The full plan was approved and lives at:

```
C:\Users\LH719EC\.factory\specs\2026-05-27-publish-repo-rag-as-a-generic-multi-agent-oss-tool.md
```

Read that file first. The plan is binding; do not re-litigate scope.

## Current repo state

Working directory: `C:\Raptor\rag tool` (not yet a git repo).

### Already done in previous session

- Index directory migrated from `~/.droid-index` to `~/.repo-rag` via `Move-Item`. Three repos under it: `rag-tool`, `raptor-forms-profile-api`, `raptor-forms-render`. All read-only verified.
- Three running MCP server child processes were stopped to free file handles before the move.
- All 31 existing tests still pass (no logic changes were made yet to source files).

### Foundation files already created in repo root

- `LICENSE` - MIT, contains `<YEAR>` and `<YOUR_NAME>` placeholders.
- `.gitignore` - Python, virtualenv, test caches, IDE, repo-rag local data, OS junk.
- `.dockerignore`.
- `Dockerfile` - python:3.12-slim base, installs the package, default CMD `rag mcp-server`.
- `CHANGELOG.md` - Keep a Changelog format, `[Unreleased]` and `[0.1.0] - 2026-05-27` sections.
- `SECURITY.md` - private email reporting, support window.
- `CONTRIBUTING.md` - dev setup, tests, lint, plugin steps, release process.

### Foundation files NOT YET created

- `CODE_OF_CONDUCT.md` - use Contributor Covenant 2.1, replace contact email with `<your.email@example.com>` placeholder.
- `README.md` - present from old session but content describes the Factory-only version. Needs full rewrite per Phase 3c. The old file at `C:\Raptor\rag tool\README.md` is overwriteable.

## Identity placeholders used throughout

The user will swap these via `scripts/replace-placeholders.ps1` before pushing.

- `<YOUR_GITHUB_USERNAME>` - GitHub handle (used in URLs, badges, ghcr.io path).
- `<YOUR_NAME>` - LICENSE copyright + pyproject author.
- `<your.email@example.com>` - pyproject email + SECURITY contact + CoC enforcement contact.
- `<YEAR>` - copyright year (use 2026 if unfilled).

Find/replace tokens are written verbatim, including angle brackets, so a single replace pass swaps them all.

## Remaining work, in order

The full plan is in the approved spec. High-level phases that still need to run:

### Phase 1 cont.

1. **Phase 1a tail**: `CODE_OF_CONDUCT.md`, README placeholder rewrite (Phase 3c will replace it again).
2. **Phase 1b**: `pyproject.toml` metadata (description, classifiers, URLs, keywords, version pins). Add `__version__` in `src/repo_rag/__init__.py`. Wire `rag --version`.
3. **Phase 1c**: rewrite `src/repo_rag/paths.py` so the index root is `~/.repo-rag` only. Honour `REPO_RAG_INDEX_DIR` env override. No back-compat with the old path.
4. **Phase 1d**: strip Factory-specific phrasing from `src/repo_rag/mcp_server.py`, `src/repo_rag/cli.py`, `src/repo_rag/_runtime.py`. Replace "Factory Droid" with "AI coding agent" or "MCP-compatible client".
5. **Phase 1e**: CI workflows under `.github/workflows/`:
   - `ci.yml` - Ubuntu/macOS/Windows times Python 3.11/3.12, ruff + pytest.
   - `release.yml` - on tag `v*.*.*`, build wheel + sdist, publish to PyPI via OIDC trusted publisher.
   - `docker.yml` - on tag and push to main, multi-arch image to `ghcr.io/<YOUR_GITHUB_USERNAME>/repo-rag`.
   - Issue + PR templates under `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md`.
6. **Phase 1f**: `scripts/replace-placeholders.ps1` and `scripts/replace-placeholders.sh`. PowerShell version takes `-GitHubUsername`, `-FullName`, `-Email`, `-Year` parameters and find/replaces across the tree.

### Phase 2 - multi-agent plugin system

7. **Phase 2a**: new package `src/repo_rag/agents/` with:
   - `base.py` - `AgentPlugin` abstract class with `detect`, `install_rules`, `uninstall_rules`, `install_mcp`, `mcp_command_hint`.
   - `registry.py` - `iter_plugins()` and `resolve_target(name)`.
   - `_rules_text.py` - single source of truth for the policy block (see "Policy block tone" section below).
   - `universal.py` - writes `AGENTS.md` at user and project scope.
8. **Phase 2b**: implement 12 plugins, one at a time, each with its own test under `tests/agents/`:
   - `factory.py` - `~/.factory/AGENTS.md` and `~/.factory/mcp.json`.
   - `claude_code.py` - `CLAUDE.md` and `~/.claude.json`.
   - `claude_desktop.py` - platform-specific `claude_desktop_config.json` only (no rules file).
   - `codex.py` - `AGENTS.md` and `~/.codex/config.toml`.
   - `cursor.py` - `.cursor/rules/repo-rag.mdc` and `.cursor/mcp.json`.
   - `windsurf.py` - `.windsurfrules` and `~/.codeium/windsurf/mcp_config.json`.
   - `cline.py` - `AGENTS.md` only; manual MCP hint.
   - `continue_.py` - `~/.continue/config.json` (instructions field).
   - `gemini.py` - `GEMINI.md` and `~/.gemini/settings.json`.
   - `antigravity.py` - `AGENTS.md` and `~/.antigravity/mcp.json`.
   - `aider.py` - `CONVENTIONS.md` and `~/.aider.conf.yml`.
   - `zed.py` - `.rules` and `~/.config/zed/settings.json`.
9. **Phase 2c**: CLI under `rag agents`:
   - `list`, `setup`, `uninstall`, `print-rules`, `print-mcp`.
   - Keep `rag droid setup` as a deprecated alias mapping to `rag agents setup --target factory`.

### Phase 3 - documentation

10. **Phase 3a**: `docs/quickstart.md`, `docs/architecture.md`, `docs/configuration.md`, `docs/mcp-tools.md`, `docs/performance.md`, `docs/git-hooks.md`, `docs/troubleshooting.md`, `docs/development.md`.
11. **Phase 3b**: `docs/clients/<name>.md` - 12 per-agent guides (one per plugin from Phase 2b).
12. **Phase 3c**: full rewrite of `README.md` with badges, quickstart, per-client matrix, MCP tool list, performance highlights, links to docs.

### Cleanup

13. Move `tests/_preview_repo.py`, `tests/_chunk_test.py`, `tests/_db_inspect.py`, `tests/_set_last_commit.py`, `tests/_check_exclusions.py`, `tests/_smoke_runtime.py` to `scripts/dev/`. These were diagnostic helpers, not tests.
14. Move `watch.ps1` to `scripts/watch.ps1`.
15. Move `base_plan.md` to `docs/internal/initial-design.md` (or delete if obsolete).
16. Run `pytest` full suite. Confirm all green.

### Final hand-off

17. Print exact PowerShell commands for the user to run for `git init`, placeholder replacement, remote add, push, tag.

## Policy block tone (important)

The 6-section policy block previously written was extremely strict (`MANDATORY`, `PROHIBITED`, `ENFORCEMENT`, `POLICY VIOLATION`). This phrasing was a major contributor to provider safety filter trips during the previous session.

For the new session: keep the same intent (route code questions through repo-rag first) but use neutral, conversational phrasing. Examples:

- Replace "MANDATORY first step" with "Recommended first step".
- Replace "PROHIBITED without prior repo-rag use" with "Avoid these tools as the first code-search action".
- Replace "ENFORCEMENT" with "Compliance notes".
- Replace "policy violation" with "out of policy".
- Drop "STRICT, NON-NEGOTIABLE" entirely.

The behaviour the user wants is identical; only the wording softens.

## Codebase conventions

- Python 3.11+, type hints everywhere.
- `from __future__ import annotations` at top of every module.
- Use `pathlib.Path`, never raw string paths.
- Tests use `pytest`, no test framework helpers beyond stdlib + `monkeypatch`.
- Marker-tagged blocks for editable rule files: `<!-- repo-rag:begin -->` and `<!-- repo-rag:end -->` for Markdown; `// >>> repo-rag >>>` and `// <<< repo-rag <<<` for JSON-with-comments; equivalent for TOML/YAML.
- All file edits should preserve content outside the markers.
- `_runtime.py` Windows tuning is best-effort: it must no-op cleanly on macOS and Linux.

## Final user steps after all work completes

```powershell
cd "C:\Raptor\rag tool"
git init -b main
git add .
git status
git commit -m "Initial commit: repo-rag v0.1.0"

.\scripts\replace-placeholders.ps1 -GitHubUsername "your-handle" -FullName "Your Name" -Email "you@example.com" -Year "2026"
git add -A
git commit -m "Set identity placeholders"

# Create empty repo on github.com named repo-rag (no README, no LICENSE, no auto-init).
git remote add origin https://github.com/your-handle/repo-rag.git
git push -u origin main

# When ready for first PyPI release:
git tag v0.1.0
git push origin v0.1.0
```

## Tools the new session has available

- `repo-rag` MCP server is registered and will spin up on demand. Use `repo_rag_search` against the `rag-tool` repo to find existing code.
- `rag` CLI is on PATH inside the venv (`C:\Raptor\rag tool\.venv\Scripts\rag.exe`).
- The user's render index at `~/.repo-rag/raptor-forms-render/` is now complete (1956 files, 19,800 chunks) and queryable.

## How to start the new session

In a fresh chat:

1. `cd "C:\Raptor\rag tool"` (the working directory).
2. Open this `HANDOFF.md` and the approved spec at `~/.factory/specs/2026-05-27-publish-repo-rag-as-a-generic-multi-agent-oss-tool.md`.
3. Resume at "Phase 1a tail: `CODE_OF_CONDUCT.md`, README placeholder rewrite".
4. When writing the policy block in `_rules_text.py`, use the softened phrasing described above.
