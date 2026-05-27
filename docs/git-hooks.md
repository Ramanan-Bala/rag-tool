# Git hooks

repo-rag ships with optional `post-commit`, `post-merge`, and `post-checkout`
git hooks that re-index changed files in the background after every git
operation. Output goes to `.git/repo-rag-hook.log` (truncated at the start
of each run, holds only the latest hook).

## Install

```bash
cd /path/to/your/repo
rag init                     # required once
rag hooks install
```

The default command run by each hook is:

```
rag index --changed --sequential --window-size 10 --pace-sec 0
```

You can customise the flags:

```bash
rag hooks install --flags "--changed --threads 8 --window-size 16"
```

Each hook backgrounds the indexer so `git commit`, `git merge`, and
`git checkout` return immediately.

## Watch the log

```bash
rag hooks log              # last 50 lines
rag hooks log --tail 200
rag hooks log --follow     # tail -f equivalent
```

## Uninstall

```bash
rag hooks uninstall
```

Removes only the marker-tagged block; any other content in the hook scripts
is preserved.

## Implementation notes

- Hooks are POSIX shell scripts (`#!/bin/sh`), which works on Linux, macOS,
  and Git for Windows (which ships its own `sh.exe`).
- The hook detaches with `( ... ) </dev/null >/dev/null 2>&1 &` so git never
  blocks on the indexer.
- `repo-rag-hook.log` is truncated on every run, so it holds only the most
  recent hook's output - useful for tailing without log rotation.
- The hook resolves the repo with `git rev-parse --show-toplevel`, so it
  works from any directory inside the repo.

## Troubleshooting

- "command not found: rag" - the hook runs `rag` from PATH. Either install
  repo-rag globally, or wrap the hook command to activate your virtualenv
  first.
- Hook fires but log is empty - check `git rev-parse --show-toplevel` from a
  shell. If git itself reports an error the hook silently skips.
- Slow `git commit` - the indexer is supposed to run detached. If your shell
  does not honour `&` (rare), `rag index --changed` may be running in the
  foreground. Re-install the hook from a `bash` or `sh` session.
