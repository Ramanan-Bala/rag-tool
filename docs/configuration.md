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
provider    = "model2vec"               # model2vec | fastembed | sentence_transformers | ollama | openai
model       = "minishlab/potion-code-16M"
dim         = 256
batch_size  = 32
base_url    = ""                        # only used by ollama / openai
api_key_env = "RAG_EMBEDDING_API_KEY"   # env var holding the API key

[chunking]
code_chunk_tokens  = 500
prose_chunk_tokens = 1500
overlap_tokens     = 150
max_file_bytes     = 1000000
use_tree_sitter    = true

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

Tree-sitter is installed in the base package and used by default for supported
code files. Set `chunking.use_tree_sitter = false` only when you want the older
regex boundary splitter for every code file.

## Environment overrides

These take precedence over the TOML file:

| Variable                   | Effect                                                                 |
|----------------------------|------------------------------------------------------------------------|
| `REPO_RAG_INDEX_DIR`       | Storage root (default `~/.repo-rag`).                                  |
| `RAG_EMBEDDING_PROVIDER`   | `model2vec` / `fastembed` / `sentence_transformers` / `ollama` / `openai`. |
| `RAG_EMBEDDING_MODEL`      | Model name.                                                            |
| `RAG_EMBEDDING_DIM`        | Vector dimension (must match the model).                               |
| `RAG_EMBEDDING_BASE_URL`   | API base URL for Ollama / OpenAI.                                      |
| `RAG_EMBEDDING_API_KEY_ENV`| Name of the env var that holds the key (default `RAG_EMBEDDING_API_KEY`). |
| `RAG_EMBEDDING_API_KEY`    | The key itself (resolved at request time).                             |
| `RAG_INDEX_THREADS`        | Override BLAS / OpenMP thread count.                                   |
| `RAG_FULL_SPEED`           | `1` to disable background-mode CPU throttling.                         |
| `RAG_DISABLE_AFFINITY`     | `1` to skip the Windows E-core affinity pin.                           |
| `OLLAMA_BASE_URL`          | Override Ollama URL (default `http://127.0.0.1:11434`).                |

## Choosing a provider

All local providers (`model2vec`, `fastembed`, `sentence_transformers`) keep your
code on your machine - nothing is sent anywhere at index or query time. The only
network access is a **one-time model download** the first time you use a model;
after that they run fully offline. The exception is `openai`, which sends your
text to a cloud API.

| Provider | Speed | Best for | Notes |
|---|---|---|---|
| **model2vec** (default) | fastest | **code** | Code-specialized static embeddings (`potion-code-16M`); no transformer forward pass. |
| **fastembed** | slower | prose / docs / natural-language questions | General-purpose ONNX transformer (`bge-small`); the recommended fallback. |
| sentence_transformers | slowest | higher-accuracy prose | Heavier transformer; install `repo-rag[local]`. |
| ollama | varies | larger local models | Talks to a local Ollama server. |
| openai | n/a (API) | general | **Avoid for sensitive/private repos** - sends text to a cloud API. |

Rule of thumb: keep the **model2vec** default for code-heavy repositories; switch
to **fastembed** for documentation/prose-heavy repositories.

## Provider examples

### model2vec (default, fast, code-specialized, fully local)

```toml
[embedding]
provider = "model2vec"
model    = "minishlab/potion-code-16M"
dim      = 256
```

The model is downloaded once and cached. On networks that intercept TLS or block
script downloads, repo-rag trusts the OS certificate store (via `truststore`) and
skips non-essential `*.py` files automatically.

### fastembed (fallback, best for prose/docs, fully offline)

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

> Cloud provider: your chunk text is sent to the API. Do **not** use this for
> sensitive or private repositories - prefer a local provider (`model2vec` or
> `fastembed`).

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

## Migrating the embedder

Switching embedding providers (or models) changes both the **vector dimension**
and the **vector space**, so existing vectors become unusable and every repo must
be re-embedded with a full rebuild. (`bge-small` is 384-dim; `potion-code-16M` is
256-dim.) A plain `rag rebuild` handles it - you do not need `--wipe-cache`,
because stale cache rows are ignored once the cache key changes.

Migrating an existing install to the model2vec default:

```bash
# 1. Make sure model2vec is available (it ships in the base install from this
#    version on; older installs may need an upgrade).
pipx upgrade repo-rag        # or: pip install --upgrade repo-rag

# 2. Set the default for every repo (or rely on the new built-in default).
#    Edit ~/.repo-rag/config.toml:
#    [embedding]
#    provider = "model2vec"
#    model    = "minishlab/potion-code-16M"
#    dim      = 256

# 3. Full-rebuild each registered repo so vectors match the new model.
rag rebuild /path/to/repo
```

To stay on (or move back to) fastembed for a prose-heavy repo, set
`provider = "fastembed"`, `model = "BAAI/bge-small-en-v1.5"`, `dim = 384` in that
repo's `~/.repo-rag/<repo_id>/config.toml` and run `rag rebuild` for it.
