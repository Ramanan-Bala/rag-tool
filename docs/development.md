# Development guide

## Project layout

```
src/repo_rag/
  agents/             # per-agent plugins (factory, claude_code, ...)
  embedder/           # provider adapters (fastembed, openai, ollama, ...)
  store/              # sqlite + lance abstractions
  chunker.py
  cli.py
  config.py
  context.py
  fileutils.py
  hasher.py
  hooks.py
  indexer.py
  mcp_server.py
  memory.py
  paths.py
  registry.py
  _runtime.py
  search.py
tests/
  agents/             # plugin round-trip + MCP install tests
  ...
docs/
  clients/            # per-agent setup guides
scripts/
  replace-placeholders.ps1
  replace-placeholders.sh
  watch.ps1
  dev/                # diagnostic helpers (not packaged)
```

## Setup

```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/repo-rag.git
cd repo-rag
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

## Running tests

```bash
pytest -q
pytest -k agents              # plugin tests only
pytest --cov=repo_rag
```

## Linting and formatting

```bash
ruff check src tests
ruff format src tests
```

CI runs the same commands on Ubuntu, macOS, and Windows for Python 3.11 and 3.12.

## Adding a new agent plugin

1. **Create the module** under `src/repo_rag/agents/<name>.py`. Subclass
   `AgentPlugin` and implement `detect`. The base class already handles the
   marker-tagged Markdown block install / uninstall; override only what
   differs.
2. **Override the path methods**:

   ```python
   def user_rules_path(self) -> Path | None: ...
   def project_rules_path(self, repo_root: Path) -> Path | None: ...
   ```

3. **Optional**: override `install_mcp(scope, repo_root)` to auto-write
   the MCP config. Use `upsert_json_mcp_entry()` for JSON files or write
   custom logic for TOML / YAML.
4. **Always** override `mcp_hint(scope, repo_root)` so users with auto-write
   disabled can paste the config manually.
5. **Register** the plugin in `src/repo_rag/agents/registry.py`:

   ```python
   from .myagent import MyAgentAgent
   # add MyAgentAgent to _all_plugin_classes()
   ```

6. **Test**. The parametrised round-trip suite in
   `tests/agents/test_plugin_round_trip.py` picks the new plugin up
   automatically. Add MCP-specific assertions in
   `tests/agents/test_mcp_install.py` if `install_mcp` is implemented.
7. **Document**. Drop a `docs/clients/<name>.md` describing setup,
   gotchas, and the MCP config location.

## Releasing (maintainers)

1. Bump `__version__` in `src/repo_rag/__init__.py` (SemVer).
2. Move the `[Unreleased]` section in `CHANGELOG.md` under a new dated
   header, add a matching `[X.Y.Z]: https://github.com/...` link at the
   bottom.
3. Commit on `main`.
4. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
5. `release.yml` builds the sdist + wheel and publishes to PyPI via the
   OIDC trusted publisher you configured on PyPI's web UI.
6. `docker.yml` builds the multi-arch image (`linux/amd64`, `linux/arm64`)
   and pushes to `ghcr.io/<YOUR_GITHUB_USERNAME>/repo-rag:<version>` and
   `:latest`.

## Code style

- Python 3.11+, type hints everywhere.
- `from __future__ import annotations` at the top of every module.
- `pathlib.Path` exclusively; no raw string paths.
- One stdlib import per line per `ruff` rules.
- Markers: `<!-- repo-rag:begin -->` / `<!-- repo-rag:end -->` for Markdown;
  `# >>> repo-rag >>>` / `# <<< repo-rag <<<` for hash-comment files;
  `// >>> repo-rag >>>` / `// <<< repo-rag <<<` for JSON-with-comments
  (rare; most JSON consumers reject inline comments).
- All edits to user-owned files MUST preserve content outside the marker
  block.
