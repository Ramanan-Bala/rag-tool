# Contributing to repo-rag

Thanks for your interest in contributing.

## Development setup

Requires Python 3.11 or later. From the repo root:

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

## Running the test suite

```bash
pytest                    # all tests
pytest -k chunker         # filter by name
pytest --cov=repo_rag     # with coverage
```

## Linting and formatting

```bash
ruff check src tests
ruff format src tests
```

CI runs the same commands across Ubuntu, macOS, and Windows on Python 3.11 and 3.12; please make sure both pass locally first.

## Adding a new agent plugin

The plugin contract lives in `src/repo_rag/agents/base.py`. See `docs/development.md` for a step-by-step walkthrough. In short:

1. Subclass `AgentPlugin` in a new module under `src/repo_rag/agents/`.
2. Implement `detect`, `install_rules`, and `uninstall_rules`. Optionally override `install_mcp` if the agent stores its MCP config in a writable file.
3. Register the plugin in `agents/registry.py`.
4. Add a unit test under `tests/agents/`.
5. Add a client guide under `docs/clients/<name>.md`.

## Submitting a pull request

1. Fork the repo and create a feature branch named `feat/short-description`, `fix/short-description`, or `docs/short-description`.
2. Keep the PR focused; unrelated changes belong in separate PRs.
3. Add or update tests for any behaviour change.
4. Add a `[Unreleased]` entry to `CHANGELOG.md`.
5. Make sure `ruff check`, `ruff format --check`, and `pytest` all pass locally.
6. Open the PR against `main`. CI will run the cross-platform matrix.

## Release process (maintainers only)

1. Bump `__version__` in `src/repo_rag/__init__.py` following SemVer.
2. Move `[Unreleased]` content under a new dated section in `CHANGELOG.md`.
3. Commit on `main`, tag `vX.Y.Z`, push the tag.
4. The `release.yml` workflow publishes to PyPI via OIDC; `docker.yml` builds and pushes the multi-arch image to `ghcr.io/ramanan-bala/repo-rag`.
