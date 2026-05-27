# Troubleshooting

## Model load hangs forever on Windows

**Symptom**: `rag rebuild` shows "Loading embedding model..." and never
proceeds. The python process sits at 0% CPU.

**Cause**: An older version of repo-rag set `PROCESS_MODE_BACKGROUND_BEGIN`,
which forces IDLE I/O priority. Windows Defender's real-time scanner has
higher I/O priority and preempts the read of the fastembed model files in
`%TEMP%\fastembed_cache\` indefinitely.

**Fix**: Upgrade to a version with the `BELOW_NORMAL_PRIORITY_CLASS` fix
(everything 0.1 onward). Workaround: `RAG_FULL_SPEED=1 rag rebuild` runs at
NORMAL priority.

## Chunker appears to hang on a single file

**Symptom**: One file logs "chunked into N pieces" but the next file never
starts.

**Cause**: An old chunker bug looped indefinitely on files with lines longer
than `max_chunk_chars / 2`.

**Fix**: 0.1 and later detect zero forward progress and bail. Workaround for
older builds: add the offending file to `exclude_globs`.

## "Ctrl+C won't kill rag" on Windows

**Symptom**: `rag rebuild` keeps running after `Ctrl+C`. Process is pinned
to non-P-core CPUs (high logical CPU numbers).

**Cause**: BELOW_NORMAL priority plus a tight C extension (fastembed,
LanceDB) means signal delivery can be delayed by a few seconds. Combined
with PowerShell's quirky Ctrl+C handling, the process appears unresponsive.

**Fix**: From a separate shell,

```powershell
Get-Process | Where-Object {
  $_.Path -like "*\.venv\Scripts\*" -and $_.ProcessName -match 'rag|python'
} | Stop-Process -Force
```

## Embeddings stop on corporate Windows after a while

**Symptom**: Index proceeds for ~50 files, then no further progress; CPU
is high but disk is idle.

**Cause**: PGDriver (or another endpoint security agent) intercepts every
SQLite write, eventually queuing writes faster than they drain.

**Fix**: `rag rebuild --sequential --window-size 10 --pace-sec 0.5` adds a
breather between windows. On chronic systems run inside the official Docker
image instead.

## High thread counts freeze the machine on Intel hybrid CPUs

**Symptom**: `--threads 16` or higher on an Intel 12th/13th/14th-gen laptop
causes UI lag and audio glitches.

**Cause**: OpenMP spawns threads on both P-cores and E-cores. The kernel
scheduler keeps migrating them under load, which starves foreground apps.

**Fix**: Leave the default thread cap, or use `--threads 8 --full-speed` to
opt into NORMAL priority but cap threads.

## "MCP server keeps restarting" in Claude / Cursor

**Symptom**: The MCP client logs `repo-rag` server starting and dying in a
loop.

**Cause**: `rag` is not on PATH for the GUI app's environment. macOS Finder
and Windows shortcuts do not pick up `~/.local/bin` automatically.

**Fix**: Use the absolute path to the script in the MCP config:

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "/Users/you/.local/bin/rag",
      "args": ["mcp-server"]
    }
  }
}
```

or use the Docker form, which has no PATH dependency:

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/you/.repo-rag:/data/.repo-rag",
        "ghcr.io/<YOUR_GITHUB_USERNAME>/repo-rag:latest"
      ]
    }
  }
}
```

## Vector / keyword scores are zero for every result

**Symptom**: `rag search "query"` returns hits with `score=0.000`.

**Cause**: The query embedding dimension does not match the LanceDB table
dimension (most often after switching models without `--wipe-cache`).

**Fix**: `rag rebuild --wipe-cache` rebuilds the embedding cache and
LanceDB table with the current model dimension.

## "Repo at /path/... is not registered with repo-rag"

**Symptom**: `rag search` or the MCP server complains the repo is not
registered.

**Cause**: `rag init` has not run for that repo, or you moved the repo
directory after registering it.

**Fix**:

```bash
cd /new/path/to/repo
rag deregister                 # if you had registered the old location
rag init
rag rebuild
```

## `pip install repo-rag` fails on Python 3.10

**Symptom**: `Could not find a version that satisfies the requirement`.

**Cause**: repo-rag targets Python 3.11+ (uses `tomllib`, modern typing).

**Fix**: Install Python 3.11 or 3.12. Docker users can rely on the official
image which ships 3.12.
