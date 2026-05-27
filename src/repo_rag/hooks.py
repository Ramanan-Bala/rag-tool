from __future__ import annotations

from pathlib import Path

HOOK_NAMES = ["post-commit", "post-merge", "post-checkout"]
BEGIN = "# >>> repo-rag hook >>>"
END = "# <<< repo-rag hook <<<"

HOOK_BODY = """{begin}
# Auto-installed by `rag hooks install`. Do not edit by hand.
# Runs incremental indexing in the BACKGROUND so git returns immediately.
# Output: .git/repo-rag-hook.log (truncated on every run, holds only the latest hook).
if command -v rag >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
  LOG="$ROOT/.git/repo-rag-hook.log"
  HOOK_NAME="$(basename "$0")"
  (
    cd "$ROOT" && {{
      echo "========================================"
      echo "$(date '+%Y-%m-%d %H:%M:%S')  hook=$HOOK_NAME  pid=$$"
      echo "========================================"
      rag index --changed {flags} 2>&1
      echo "$(date '+%Y-%m-%d %H:%M:%S')  hook=$HOOK_NAME  done"
    }} > "$LOG" 2>&1
  ) </dev/null >/dev/null 2>&1 &
fi
{end}
"""

DEFAULT_FLAGS = "--sequential --window-size 10 --pace-sec 0"


def _hook_path(repo_root: Path, name: str) -> Path:
    return repo_root / ".git" / "hooks" / name


def install(repo_root: Path, flags: str = DEFAULT_FLAGS) -> list[str]:
    if not (repo_root / ".git").exists():
        raise RuntimeError(f"{repo_root} is not a git repository (no .git/ directory).")
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    body = HOOK_BODY.format(begin=BEGIN, end=END, flags=flags)
    installed: list[str] = []
    for name in HOOK_NAMES:
        path = _hook_path(repo_root, name)
        existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        if BEGIN in existing and END in existing:
            head, _, rest = existing.partition(BEGIN)
            _, _, tail = rest.partition(END)
            new_content = head + body + tail.lstrip("\n")
        elif existing.strip():
            new_content = existing.rstrip() + "\n\n" + body
        else:
            new_content = "#!/bin/sh\n" + body
        path.write_text(new_content, encoding="utf-8")
        try:
            path.chmod(0o755)
        except OSError:
            pass
        installed.append(name)
    return installed


def uninstall(repo_root: Path) -> list[str]:
    removed: list[str] = []
    for name in HOOK_NAMES:
        path = _hook_path(repo_root, name)
        if not path.exists():
            continue
        existing = path.read_text(encoding="utf-8", errors="replace")
        if BEGIN not in existing or END not in existing:
            continue
        head, _, rest = existing.partition(BEGIN)
        _, _, tail = rest.partition(END)
        new_content = (head + tail.lstrip("\n")).rstrip() + "\n"
        if new_content.strip() in ("", "#!/bin/sh"):
            try:
                path.unlink()
            except OSError:
                pass
        else:
            path.write_text(new_content, encoding="utf-8")
        removed.append(name)
    return removed
