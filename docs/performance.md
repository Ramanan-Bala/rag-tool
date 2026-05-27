# Performance and tuning

The default settings keep your machine responsive while indexing. Tune as
needed for your hardware and trade-off preferences.

## Default behaviour

- Embedding threads: `min(4, cpu // 3)` (set via `OMP_NUM_THREADS`,
  `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`).
- On Windows: `BELOW_NORMAL_PRIORITY_CLASS` plus CPU affinity pinned to all
  cores except the first four (avoids the Intel hybrid P-cores when present).
- On POSIX: `os.nice(+10)`.
- Indexer window size: 16 files.

Expected throughput: 3-10 chunks/sec on a typical laptop with the default
`fastembed` model. Larger models (sentence-transformers, Ollama
`nomic-embed-text`) scale roughly linearly with parameter count.

## Indexing flags

```bash
rag rebuild --threads 8                  # raise the OpenMP thread cap
rag rebuild --full-speed                 # NORMAL priority + all-cores affinity
rag rebuild --window-size 4              # smaller windows = lower IO pressure
rag rebuild --pace-sec 0.5               # sleep between windows
rag rebuild --sequential                 # one file at a time, verbose log
```

| Goal                                       | Flag                                            |
|--------------------------------------------|-------------------------------------------------|
| Maximum speed on an idle dev machine       | `--full-speed --window-size 16 --threads 8`     |
| Index while actively using the machine     | (defaults)                                      |
| Corporate Windows with AV scanning every write | `--sequential --window-size 10 --pace-sec 0.2` |
| Smallest possible IO spikes                | `--window-size 1 --pace-sec 1`                  |

## Environment overrides

```bash
export RAG_INDEX_THREADS=8       # OpenMP / BLAS thread cap
export RAG_FULL_SPEED=1          # disable background-mode throttle
export RAG_DISABLE_AFFINITY=1    # skip the Windows E-core pin
```

## Embedding cache

Chunks are keyed by `(provider, model, dim, sha256(content))`. The cache
lives inside `metadata.sqlite`, so:

- Re-running `rag rebuild` after an interruption is dramatically faster:
  unchanged chunks skip embedding entirely.
- Swapping models invalidates the relevant cache rows without touching the
  unrelated provider's entries.
- To force a full re-embed, pass `--wipe-cache`.

## fastembed model cache location

fastembed downloads ONNX weights into the OS temp directory the first time
you run it:

- Windows: `%TEMP%\fastembed_cache\`
- macOS / Linux: `$TMPDIR/fastembed_cache/`

If your temp directory is wiped on boot, the first index of the next session
will re-download the model.

## When to use `--sequential`

The `--sequential` flag processes one file at a time and prints a per-file
log line with file size, chunk count, cache hits, embed time, and progress.
It is the slowest mode but the lowest-impact: useful when

- corporate AV scans every embedding write,
- the embedder shares the machine with other heavy workloads,
- you want full visibility into where the indexer is stuck.

It is also what the default git-hook installer uses:

```
rag index --changed --sequential --window-size 10 --pace-sec 0
```
