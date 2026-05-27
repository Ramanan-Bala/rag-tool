Build a local repo RAG system with automatic indexing hooks and rebuild support.

Goal:
Create an external memory/RAG tool for this codebase because Factory Droid sessions have no persistent memory. The tool should index the repository, store semantic + keyword searchable chunks, and generate compact context packs that I can paste into new Droid sessions.

Project name:
repo-rag

Core requirements:
1. CLI commands
  - rag index
  - rag index --changed
  - rag rebuild
  - rag context "<task>"
  - rag ask "<question>"
  - rag remember "<note>"
  - rag hooks install
  - rag hooks uninstall
  - rag status

2. Tech stack
  - Python 3.11+
  - SQLite for metadata and memory notes
  - LanceDB for vector storage
  - ripgrep or Python fallback for keyword search
  - OpenAI-compatible embeddings provider, configurable via env
  - No hard dependency on any cloud except embeddings API
  - Clean modular code

3. Files to index
  Include:
  - src/**
  - app/**
  - lib/**
  - packages/**
  - services/**
  - docs/**
  - README.md
  - package.json
  - pyproject.toml
  - tsconfig.json
  - Dockerfile
  - docker-compose.yml

  Exclude:
  - .git/**
  - node_modules/**
  - dist/**
  - build/**
  - coverage/**
  - .next/**
  - .turbo/**
  - vendor/**
  - __pycache__/**
  - *.lock
  - *.min.js
  - binary files

4. Chunking
  For v1, implement reliable text chunking:
  - chunk size around 1200-1800 tokens or approximate characters
  - overlap around 150-250 tokens
  - preserve path, language, start line, end line
  - later extensible for tree-sitter symbol-aware chunking

5. Metadata per chunk
  Store:
  - chunk_id
  - repo_root
  - path
  - language
  - content_hash
  - chunk_hash
  - start_line
  - end_line
  - content
  - summary
  - imports if cheaply detectable
  - git_commit
  - last_modified
  - indexed_at

6. Embeddings
  Implement EmbeddingProvider interface.
  Support env vars:
  - RAG_EMBEDDING_BASE_URL
  - RAG_EMBEDDING_API_KEY
  - RAG_EMBEDDING_MODEL
  - RAG_EMBEDDING_DIM

  Default to OpenAI-compatible /v1/embeddings API.
  Batch embeddings.
  Cache embeddings by chunk_hash so unchanged chunks are not re-embedded.

7. Search
  Implement hybrid retrieval:
  - vector search from LanceDB
  - keyword search using ripgrep/BM25/simple SQLite FTS5
  - merge results using weighted scoring
  - deduplicate by chunk_id/path/line range
  - prefer exact identifier/path matches when task contains code symbols

8. Context generation
  Command:
  rag context "fix auth timeout bug"

  Output markdown with:
  - task
  - top relevant files
  - relevant chunks with path and line numbers
  - remembered notes
  - architecture/decision notes
  - constraints
  - suggested investigation order
  - max token budget configurable with --max-tokens

  Keep output compact and useful for pasting into Factory Droid.

9. Memory notes
  Command:
  rag remember "We use Redis TTL as source of truth for session expiry"

  Store human notes in SQLite with:
  - id
  - note
  - tags inferred from text
  - created_at
  - updated_at
  - optional source

  Include relevant remembered notes in rag context.

10. Git hooks
  Implement:
  rag hooks install

  This should install:
  - .git/hooks/post-commit
  - .git/hooks/post-merge
  - .git/hooks/post-checkout

  Hooks should run:
  rag index --changed

  Requirements:
  - hooks must be idempotent
  - preserve existing hook content by wrapping with clearly marked block
  - allow uninstall cleanly
  - do not break commit if indexing fails; log warning only
  - write logs to .rag/logs/hooks.log

11. Rebuild
  Command:
  rag rebuild

  Should:
  - clear LanceDB index
  - clear stale metadata
  - re-index entire repo
  - preserve remembered notes unless --wipe-memory is passed

12. Incremental indexing
  rag index --changed should:
  - detect changed files using git diff, git status, and file mtimes
  - re-index changed files
  - remove deleted files from index
  - skip unchanged files based on content_hash

13. Status
  rag status should show:
  - indexed files count
  - chunks count
  - memory notes count
  - embedding model
  - last full rebuild time
  - last incremental index time
  - index storage location
  - dirty/unindexed changed files

14. Storage layout
  Create:
  .rag/
    config.toml
    metadata.sqlite
    lancedb/
    logs/
    cache/

15. Config
  Support .rag/config.toml:
  - include_globs
  - exclude_globs
  - embedding model/base_url/dim
  - chunk size
  - overlap
  - max context tokens
  - retrieval top_k
  - vector weight
  - keyword weight

16. Quality
  - Add type hints
  - Add docstrings where useful
  - Add helpful errors
  - Make it work on macOS/Linux
  - Keep secrets out of files
  - Add README.md with setup and usage
  - Add tests for chunking, hashing, config loading, hook install/uninstall, and retrieval merge

17. Deliverables
  - Complete working implementation
  - pyproject.toml
  - README.md
  - example .rag/config.toml
  - tests
  - clear run instructions

Implementation preference:
Use Typer for CLI, Pydantic for config models if useful, SQLite FTS5 for keyword search if available, and LanceDB for vector search.

Important behavior:
When I run:
pip install -e .
rag rebuild
rag remember "Redis TTL is the source of truth for sessions"
rag context "fix auth timeout issue"

I should get a useful markdown context pack that can be pasted into a fresh Factory Droid session.

Start by inspecting the repo structure, then implement the full system.