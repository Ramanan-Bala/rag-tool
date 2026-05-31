# Configuration

repo-rag has two layers of configuration:

1. **Global**: `~/.repo-rag/config.toml`. Affects every repo unless overridden.
2. **Per-repo**: `~/.repo-rag/<repo_id>/config.toml`. Merges shallowly on top
   of global.

Write the default global config explicitly with `rag config init`. Write the
effective config for one registered repo with:

```bash
rag config repo-init /path/to/repo
```

The repo command writes `~/.repo-rag/<repo_id>/config.toml`; edit
`exclude_globs` there when only one repository needs extra skips.

Preview the resolved indexing inventory before rebuilding:

```bash
rag preview /path/to/repo
rag preview /path/to/repo --all --sort embed
```

## Schema

```toml
[embedding]
provider    = "fastembed"               # fastembed | sentence_transformers | ollama | openai
model       = "BAAI/bge-small-en-v1.5"
dim         = 384
batch_size  = 32
base_url    = ""                        # only used by ollama / openai
api_key_env = "RAG_EMBEDDING_API_KEY"   # env var holding the API key

[chunking]
code_chunk_tokens  = 500
prose_chunk_tokens = 1500
overlap_tokens     = 150
max_file_bytes     = 1000000

[retrieval]
top_k              = 20
vector_weight      = 0.6
keyword_weight     = 0.4
recency_boost      = 0.05
max_context_tokens = 6000

include_globs = ["src/**", "lib/**", "*.py", ...]
exclude_globs = [".git/**", "node_modules/**", "*.lock", ...]
```

See `src/repo_rag/config.py` for the default `include_globs` and
`exclude_globs` lists.

## Environment overrides

These take precedence over the TOML file:

| Variable                   | Effect                                                                 |
|----------------------------|------------------------------------------------------------------------|
| `REPO_RAG_INDEX_DIR`       | Storage root (default `~/.repo-rag`).                                  |
| `RAG_EMBEDDING_PROVIDER`   | `fastembed` / `sentence_transformers` / `ollama` / `openai`.           |
| `RAG_EMBEDDING_MODEL`      | Model name.                                                            |
| `RAG_EMBEDDING_DIM`        | Vector dimension (must match the model).                               |
| `RAG_EMBEDDING_BASE_URL`   | API base URL for Ollama / OpenAI.                                      |
| `RAG_EMBEDDING_API_KEY_ENV`| Name of the env var that holds the key (default `RAG_EMBEDDING_API_KEY`). |
| `RAG_EMBEDDING_API_KEY`    | The key itself (resolved at request time).                             |
| `RAG_INDEX_THREADS`        | Override BLAS / OpenMP thread count.                                   |
| `RAG_FULL_SPEED`           | `1` to disable background-mode CPU throttling.                         |
| `RAG_DISABLE_AFFINITY`     | `1` to skip the Windows E-core affinity pin.                           |
| `OLLAMA_BASE_URL`          | Override Ollama URL (default `http://127.0.0.1:11434`).                |

## Provider examples

### fastembed (default, fully offline)

```toml
[embedding]
provider = "fastembed"
model    = "BAAI/bge-small-en-v1.5"
dim      = 384
```

### sentence-transformers (heavier, also offline)

```bash
pip install "repo-rag[local]"
```

```toml
[embedding]
provider = "sentence_transformers"
model    = "BAAI/bge-base-en-v1.5"
dim      = 768
```

### Ollama (local server, larger models)

```toml
[embedding]
provider = "ollama"
model    = "nomic-embed-text"
dim      = 768
base_url = "http://127.0.0.1:11434"
```

### Azure OpenAI (cloud)

```bash
pip install "repo-rag[openai]"
```

```toml
[embedding]
provider    = "openai"
model       = "text-embedding-3-small"
dim         = 1536
base_url    = "https://<resource>.openai.azure.com/openai/deployments/<deployment>"
api_key_env = "AZURE_OPENAI_API_KEY"
```

Embedding cache keys include `(provider, model, dim, chunk_hash)` so swapping
providers invalidates the right vectors automatically.
