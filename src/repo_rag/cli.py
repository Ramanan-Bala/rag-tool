from __future__ import annotations

from ._runtime import apply_runtime_tuning

apply_runtime_tuning()

import json
import sys
import time
from collections import deque
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from . import __version__
from .agents.registry import iter_plugins, resolve_target
from .config import load_global_config, load_repo_config, save_global_config, save_repo_config
from .context import build_context_pack
from .embedder import make_embedder
from .hooks import install as hooks_install_fn
from .hooks import uninstall as hooks_uninstall_fn
from .indexer import Indexer
from .memory import forget as memory_forget
from .memory import list_notes as list_memory_notes
from .memory import remember as memory_remember
from .paths import find_repo_root, get_index_root, repo_index_dir
from .preview import build_index_preview, preview_to_dict
from .registry import lookup, register_repo, remove_repo
from .search import hybrid_search
from .store.lance import LanceStore
from .store.sqlite import SqliteStore

app = typer.Typer(
    help="repo-rag: local RAG indexer and MCP server for AI coding agents.",
    no_args_is_help=True,
)
hooks_app = typer.Typer(help="Manage git hooks.")
agents_app = typer.Typer(help="Configure AI agent rules and MCP integration.")
droid_app = typer.Typer(help="[deprecated] Use `rag agents` instead.")
config_app = typer.Typer(help="Inspect or write the global config.")
app.add_typer(hooks_app, name="hooks")
app.add_typer(agents_app, name="agents")
app.add_typer(droid_app, name="droid")
app.add_typer(config_app, name="config")
console = Console(width=120)

PREVIEW_SORT_KEYS = {"path", "size", "chunks", "embed"}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"repo-rag {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed repo-rag version and exit.",
    ),
) -> None:
    """repo-rag root callback (declares the --version flag)."""
    return None


def _resolve_repo(path: str | None) -> Path:
    return Path(path).resolve() if path else find_repo_root()


def _require_repo_id(repo_root: Path) -> str:
    repo_id = lookup(repo_root)
    if not repo_id:
        console.print(f"[red]Repo {repo_root} is not registered. Run `rag init` first.[/red]")
        raise typer.Exit(code=1)
    return repo_id


def _load_effective_config(repo_id: str):
    return load_repo_config(repo_id)


def _fmt_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds != seconds:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:d}h{m:02d}m"
    return f"{m:02d}:{s:02d}"


def _fmt_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[phase]:<14}"),
        BarColumn(bar_width=24),
        TextColumn("[white]{task.fields[files_done]:>4}/{task.fields[files_total]:<4}f[/white]"),
        TextColumn("[dim]{task.fields[chunks_done]}/{task.fields[chunks_total]}c[/dim]"),
        TextColumn("[dim]{task.fields[cached]}cache {task.fields[embedded]}emb[/dim]"),
        TextColumn("[green]{task.fields[rate_str]}[/green]"),
        TimeElapsedColumn(),
        TextColumn("ETA [bold]{task.fields[eta_str]}[/bold]"),
        console=console,
        transient=False,
    )


def _run_with_progress(action, *, label: str):
    with _make_progress() as progress:
        task = progress.add_task(
            label,
            total=1,
            phase="Scanning",
            files_done=0,
            files_total=0,
            chunks_done=0,
            chunks_total=0,
            cached=0,
            embedded=0,
            rate_str="-- c/s",
            eta_str="--:--",
        )

        state = {
            "files_total": 0,
            "chunks_total": 0,
            "chunks_done": 0,
            "samples": deque(maxlen=30),
            "start": time.time(),
            "phase": "Scanning",
        }

        def _refresh_rate(force: bool = False) -> None:
            now = time.time()
            state["samples"].append((now, state["chunks_done"]))
            samples = state["samples"]
            if len(samples) >= 2:
                window = [s for s in samples if now - s[0] <= 30.0]
                if len(window) < 2:
                    window = list(samples)[-2:]
                dt = window[-1][0] - window[0][0]
                dc = window[-1][1] - window[0][1]
                rate = (dc / dt) if dt > 0 else 0.0
                if rate <= 0 and state["chunks_done"] > 0:
                    rate = state["chunks_done"] / max(1.0, now - state["start"])
                if rate > 0:
                    remaining = max(0, state["chunks_total"] - state["chunks_done"])
                    eta = remaining / rate
                    rate_str = f"{rate:.1f} c/s"
                else:
                    eta = None
                    rate_str = "-- c/s"
            else:
                rate_str = "-- c/s"
                eta = None
            progress.update(task, rate_str=rate_str, eta_str=_fmt_eta(eta))

        def cb(event: dict) -> None:
            ev = event.get("event")
            if ev == "embed_load_start":
                state["phase"] = "Loading embedder"
                progress.update(task, phase=state["phase"])
                return
            if ev == "embed_load_done":
                state["phase"] = "Embedding"
                progress.update(task, phase=state["phase"])
                return
            if ev == "scan_total":
                state["files_total"] = event.get("total", 0)
                est_total = max(1, state["files_total"] * 8)
                state["chunks_total"] = est_total
                progress.update(
                    task,
                    total=est_total,
                    files_total=state["files_total"],
                    chunks_total=est_total,
                )
                return
            if ev == "window_planned":
                window_chunks = event.get("window_chunks", 0)
                st = event.get("stats")
                processed_files = (st.files_indexed + st.files_skipped) if st else 0
                remaining_files = max(0, state["files_total"] - processed_files)
                if remaining_files > 0 and window_chunks > 0:
                    chunks_per_file = window_chunks / max(1, min(16, remaining_files))
                    refined = (
                        state["chunks_done"]
                        + window_chunks
                        + int(chunks_per_file * remaining_files)
                    )
                    if abs(refined - state["chunks_total"]) > max(50, state["chunks_total"] * 0.05):
                        state["chunks_total"] = max(refined, state["chunks_done"] + window_chunks)
                        progress.update(
                            task,
                            total=state["chunks_total"],
                            chunks_total=state["chunks_total"],
                        )
                return
            if ev in ("cache_resolved", "embed_batch_done"):
                advance = event.get("advance", 0)
                st = event.get("stats")
                state["chunks_done"] += advance
                if state["chunks_done"] > state["chunks_total"]:
                    state["chunks_total"] = state["chunks_done"]
                    progress.update(
                        task, total=state["chunks_total"], chunks_total=state["chunks_total"]
                    )
                progress.update(
                    task,
                    advance=advance,
                    chunks_done=state["chunks_done"],
                    cached=st.chunks_cached if st else 0,
                    embedded=st.chunks_embedded if st else 0,
                )
                _refresh_rate()
                return
            if ev == "file_done":
                st = event.get("stats")
                if st is not None:
                    files_done = st.files_indexed + st.files_skipped
                    progress.update(task, files_done=files_done)
                return
            if ev == "complete":
                st = event.get("stats")
                if st is not None:
                    state["chunks_done"] = st.chunks_added
                    state["chunks_total"] = max(state["chunks_total"], st.chunks_added)
                    progress.update(
                        task,
                        completed=state["chunks_total"],
                        total=state["chunks_total"],
                        files_done=st.files_indexed + st.files_skipped,
                        chunks_done=state["chunks_done"],
                        chunks_total=state["chunks_total"],
                        cached=st.chunks_cached,
                        embedded=st.chunks_embedded,
                        rate_str="done",
                        eta_str="00:00",
                        phase="Done",
                    )
                return

        return action(cb)


def _run_with_sequential_log(action, *, label: str):
    state = {"total": 0, "file_start_t": 0.0, "current_size": 0}

    def ts() -> str:
        return time.strftime("%H:%M:%S")

    def kb(n: int) -> str:
        if n >= 1024 * 1024:
            return f"{n / 1024 / 1024:.1f} MB"
        if n >= 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n} B"

    def cb(event: dict) -> None:
        ev = event.get("event")
        if ev == "scan_total":
            state["total"] = event.get("total", 0)
            console.print(
                f"[dim cyan][{ts()}][/dim cyan] Found [bold]{state['total']}[/bold] files to process"
            )
        elif ev == "embed_load_start":
            console.print(f"[dim cyan][{ts()}][/dim cyan] Loading embedding model...")
        elif ev == "embed_load_done":
            console.print(f"[dim cyan][{ts()}][/dim cyan] [green]Embedder ready[/green]")
        elif ev == "file_start":
            idx = event.get("index", 0)
            total = event.get("total", state["total"])
            rel = event.get("rel", "?")
            size = event.get("size_bytes", 0)
            state["file_start_t"] = time.time()
            state["current_size"] = size
            console.print(
                f"[dim cyan][{ts()}][/dim cyan] "
                f"[bold yellow][{idx:>5}/{total}][/bold yellow] "
                f"START [cyan]{rel}[/cyan] ({kb(size)})"
            )
        elif ev == "file_skipped":
            idx = event.get("index", 0)
            rel = event.get("rel", "?")
            remaining = event.get("remaining", 0)
            console.print(
                f"[dim cyan][{ts()}][/dim cyan] "
                f"[dim][{idx:>5}      ][/dim] "
                f"[dim]SKIP  {rel} (unchanged) | {remaining} remaining[/dim]"
            )
        elif ev == "file_chunked":
            idx = event.get("index", 0)
            chunks = event.get("chunks", 0)
            console.print(f"             [magenta]chunked into {chunks} pieces[/magenta]")
        elif ev == "cache_lookup_start":
            chunks = event.get("chunks", 0)
            console.print(f"             [blue]looking up {chunks} chunks in cache...[/blue]")
        elif ev == "cache_lookup_done":
            hits = event.get("hits", 0)
            to_embed = event.get("to_embed", 0)
            console.print(f"             [blue]cache: {hits} hits, {to_embed} to embed[/blue]")
        elif ev == "embed_start":
            chunks = event.get("chunks", 0)
            console.print(f"             [yellow]embedding {chunks} chunks...[/yellow]")
        elif ev == "embed_done":
            chunks = event.get("chunks", 0)
            elapsed = event.get("elapsed_sec", 0.0)
            rate = (chunks / elapsed) if elapsed > 0 else 0.0
            console.print(
                f"             "
                f"[yellow]embedded {chunks} chunks in {elapsed:.2f}s ({rate:.1f} c/s)[/yellow]"
            )
        elif ev == "file_done":
            idx = event.get("index", 0)
            rel = event.get("rel", "?")
            remaining = event.get("remaining", 0)
            elapsed = time.time() - state["file_start_t"] if state["file_start_t"] else 0.0
            st = event.get("stats")
            if st and state["file_start_t"]:
                console.print(
                    f"[dim cyan][{ts()}][/dim cyan] "
                    f"[bold green][{idx:>5}/{state['total']}][/bold green] "
                    f"[green]DONE[/green]  {rel} ({elapsed:.2f}s) | "
                    f"[dim]{remaining} remaining | total: {st.chunks_added}c added, {st.chunks_cached}c cached, {st.chunks_embedded}c embedded[/dim]"
                )
                state["file_start_t"] = 0.0
        elif ev == "file_unreadable":
            idx = event.get("index", 0)
            rel = event.get("rel", "?")
            console.print(
                f"[dim cyan][{ts()}][/dim cyan] [red][{idx:>5}      ] UNREADABLE {rel}[/red]"
            )
        elif ev == "file_error":
            idx = event.get("index", 0)
            rel = event.get("rel", "?")
            err = event.get("error", "?")
            console.print(
                f"[dim cyan][{ts()}][/dim cyan] [red][{idx:>5}      ] ERROR {rel}: {err}[/red]"
            )
        elif ev == "pause":
            seconds = event.get("seconds", 0)
            console.print(f"[dim cyan][{ts()}][/dim cyan] [dim]pausing {seconds:.1f}s ...[/dim]")
        elif ev == "complete":
            st = event.get("stats")
            if st is not None:
                console.print(
                    f"\n[dim cyan][{ts()}][/dim cyan] [bold green]COMPLETE[/bold green] "
                    f"files_indexed={st.files_indexed} skipped={st.files_skipped} "
                    f"removed={st.files_removed} chunks={st.chunks_added} "
                    f"cached={st.chunks_cached} embedded={st.chunks_embedded} "
                    f"elapsed={st.elapsed_sec:.1f}s"
                )

    return action(cb)


@app.command()
def init(
    path: str | None = typer.Argument(None, help="Repo path. Defaults to cwd."),
    name: str | None = typer.Option(None, help="Override the index folder name."),
):
    """Register this repo and create its index folder under the index root."""
    repo_root = _resolve_repo(path)
    repo_id = register_repo(repo_root, override_id=name)
    index_dir = repo_index_dir(repo_id)
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "logs").mkdir(exist_ok=True)
    (index_dir / "cache").mkdir(exist_ok=True)
    meta = {"repo_root": str(repo_root), "repo_id": repo_id}
    (index_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    console.print(f"[green]Registered[/green] {repo_root}")
    console.print(f"  index_id: {repo_id}")
    console.print(f"  index_dir: {index_dir}")
    console.print("  next: run `rag rebuild`")


@app.command()
def index(
    path: str | None = typer.Argument(None),
    changed: bool = typer.Option(False, "--changed", help="Only re-index changed files."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress bar."),
    threads: int | None = typer.Option(
        None,
        "--threads",
        "-t",
        help="OMP threads for embedding. Default is a conservative value to keep the system responsive.",
    ),
    full_speed: bool = typer.Option(
        False,
        "--full-speed",
        help="Disable background-mode throttling and E-core affinity for maximum speed on an idle system.",
    ),
    sequential: bool = typer.Option(
        False,
        "--sequential",
        "-s",
        help="Process one file at a time with detailed per-file logs (slowest but lowest IO pressure).",
    ),
    pace_sec: float = typer.Option(
        0.0,
        "--pace-sec",
        help="Sleep N seconds between windows (lets corporate drivers/Defender recover).",
    ),
    window_size: int | None = typer.Option(
        None,
        "--window-size",
        help="Override default window size (16). Use 1 for fully sequential.",
    ),
):
    """Index the repo. With --changed only refreshes modified files."""
    if full_speed:
        from ._runtime import force_threads, release_background_mode

        release_background_mode()
        force_threads(threads or 8)
        console.print(
            "[yellow]--full-speed[/yellow]: P-cores enabled, threads=" + str(threads or 8)
        )
    elif threads is not None:
        from ._runtime import force_threads

        force_threads(threads)
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    if window_size and window_size > 0:
        effective_window = window_size
    elif sequential:
        effective_window = 1
    else:
        effective_window = None
    idx = Indexer(repo_root, repo_id, cfg, window_size=effective_window, pace_sec=pace_sec)
    if sequential:
        console.print(
            f"[yellow]--sequential[/yellow]: window_size={idx.window_size}, pace_sec={pace_sec}"
        )
        stats = _run_with_sequential_log(
            lambda cb: idx.index_all(changed_only=changed, on_progress=cb),
            label="Indexing",
        )
    elif quiet:
        stats = idx.index_all(changed_only=changed)
    else:
        stats = _run_with_progress(
            lambda cb: idx.index_all(changed_only=changed, on_progress=cb),
            label="Indexing",
        )
    console.print(
        f"[green]Indexed[/green] files={stats.files_indexed} "
        f"skipped={stats.files_skipped} removed={stats.files_removed} "
        f"chunks_added={stats.chunks_added} embedded={stats.chunks_embedded} "
        f"cached={stats.chunks_cached} elapsed={stats.elapsed_sec:.1f}s"
    )


@app.command()
def rebuild(
    path: str | None = typer.Argument(None),
    wipe_memory: bool = typer.Option(False, "--wipe-memory", help="Also delete remembered notes."),
    wipe_cache: bool = typer.Option(
        False, "--wipe-cache", help="Also delete the embedding cache (forces re-embedding)."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress bar."),
    threads: int | None = typer.Option(
        None,
        "--threads",
        "-t",
        help="OMP threads for embedding. Default is a conservative value to keep the system responsive.",
    ),
    full_speed: bool = typer.Option(
        False,
        "--full-speed",
        help="Disable background-mode throttling and E-core affinity for maximum speed on an idle system.",
    ),
    sequential: bool = typer.Option(
        False,
        "--sequential",
        "-s",
        help="Process one file at a time with detailed per-file logs (slowest but lowest IO pressure).",
    ),
    pace_sec: float = typer.Option(
        0.0,
        "--pace-sec",
        help="Sleep N seconds between windows (lets corporate drivers/Defender recover).",
    ),
    window_size: int | None = typer.Option(
        None,
        "--window-size",
        help="Override default window size (16). Use 1 for fully sequential.",
    ),
):
    """Drop the entire index and rebuild from scratch.

    By default the embedding cache is preserved so re-embedding is skipped for
    chunks whose content hasn't changed - this makes a re-run after an interrupted
    rebuild dramatically faster.
    """
    if full_speed:
        from ._runtime import force_threads, release_background_mode

        release_background_mode()
        force_threads(threads or 8)
        console.print(
            "[yellow]--full-speed[/yellow]: P-cores enabled, threads=" + str(threads or 8)
        )
    elif threads is not None:
        from ._runtime import force_threads

        force_threads(threads)
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    if window_size and window_size > 0:
        effective_window = window_size
    elif sequential:
        effective_window = 1
    else:
        effective_window = None
    idx = Indexer(repo_root, repo_id, cfg, window_size=effective_window, pace_sec=pace_sec)
    if sequential:
        console.print(
            f"[yellow]--sequential[/yellow]: window_size={idx.window_size}, pace_sec={pace_sec}"
        )
        stats = _run_with_sequential_log(
            lambda cb: idx.rebuild(wipe_memory=wipe_memory, wipe_cache=wipe_cache, on_progress=cb),
            label="Rebuilding",
        )
    elif quiet:
        stats = idx.rebuild(wipe_memory=wipe_memory, wipe_cache=wipe_cache)
    else:
        stats = _run_with_progress(
            lambda cb: idx.rebuild(wipe_memory=wipe_memory, wipe_cache=wipe_cache, on_progress=cb),
            label="Rebuilding",
        )
    console.print(
        f"[green]Rebuilt[/green] files={stats.files_indexed} "
        f"chunks={stats.chunks_added} embedded={stats.chunks_embedded} "
        f"cached={stats.chunks_cached} elapsed={stats.elapsed_sec:.1f}s"
    )


@app.command()
def preview(
    path: str | None = typer.Argument(None, help="Repo path. Defaults to cwd."),
    changed: bool = typer.Option(False, "--changed", help="Preview only changed files."),
    show_all: bool = typer.Option(False, "--all", help="Show every file in text output."),
    limit: int = typer.Option(20, "--limit", help="Limit file rows in text output."),
    sort: str = typer.Option(
        "embed",
        "--sort",
        help="Sort file rows by path, size, chunks, or embed.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
):
    """Show what would be indexed before running index/rebuild."""
    if sort not in PREVIEW_SORT_KEYS:
        console.print("[red]--sort must be one of: path, size, chunks, embed[/red]")
        raise typer.Exit(code=2)
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    report = build_index_preview(repo_root, repo_id, cfg, changed_only=changed)
    if as_json:
        typer.echo(json.dumps(preview_to_dict(report, include_files=True), indent=2))
        return

    console.print(f"[bold]repo[/bold]: {report.repo_root}")
    console.print(f"[bold]index_id[/bold]: {report.repo_id}")
    console.print(f"[bold]config[/bold]: {report.config_path}")
    console.print(f"[bold]files[/bold]: {report.total_files}")
    console.print(f"[bold]size[/bold]: {_fmt_bytes(report.total_bytes)}")
    console.print(
        f"[bold]chunks[/bold]: {report.total_chunks} "
        f"cached={report.cached_chunks} embed={report.embed_chunks}"
    )

    ext_table = Table(show_header=True, header_style="bold cyan")
    ext_table.add_column("extension")
    ext_table.add_column("files", justify="right")
    ext_table.add_column("size", justify="right")
    ext_table.add_column("chunks", justify="right")
    ext_table.add_column("embed", justify="right")
    for group in report.by_extension()[:10]:
        ext_table.add_row(
            group.key,
            str(group.files),
            _fmt_bytes(group.bytes),
            str(group.chunks),
            str(group.embed_chunks),
        )
    console.print(ext_table)

    files = list(report.files)
    if sort == "path":
        files.sort(key=lambda item: item.path)
    elif sort == "size":
        files.sort(key=lambda item: (-item.size_bytes, item.path))
    elif sort == "chunks":
        files.sort(key=lambda item: (-item.chunks, item.path))
    else:
        files.sort(key=lambda item: (-item.embed_chunks, item.path))
    if show_all or files:
        file_limit = len(files) if show_all else max(0, limit)
        file_table = Table(show_header=True, header_style="bold cyan")
        file_table.add_column("path")
        file_table.add_column("size", justify="right")
        file_table.add_column("lang")
        file_table.add_column("chunks", justify="right")
        file_table.add_column("cached", justify="right")
        file_table.add_column("embed", justify="right")
        for item in files[:file_limit]:
            file_table.add_row(
                item.path,
                _fmt_bytes(item.size_bytes),
                item.language,
                str(item.chunks),
                str(item.cached_chunks),
                str(item.embed_chunks),
            )
        console.print(file_table)
        if not show_all and len(files) > file_limit:
            console.print(f"[dim]Use --all to show all {len(files)} files.[/dim]")


@app.command()
def context(
    task: str = typer.Argument(...),
    path: str | None = typer.Option(None, "--path"),
    max_tokens: int | None = typer.Option(None, "--max-tokens"),
    output: str | None = typer.Option(None, "--output", "-o", help="Write to file."),
):
    """Produce a markdown context pack for the given task."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    embedder = make_embedder(cfg.embedding)
    lance = LanceStore(repo_index_dir(repo_id) / "lancedb", embedder.dim)
    hits = hybrid_search(task, embedder, lance, sqlite, cfg)
    pack = build_context_pack(task, hits, sqlite, cfg, repo_root, max_tokens=max_tokens)
    if output:
        Path(output).write_text(pack, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output}")
    else:
        sys.stdout.write(pack)
        if not pack.endswith("\n"):
            sys.stdout.write("\n")


@app.command()
def ask(
    question: str = typer.Argument(...),
    path: str | None = typer.Option(None, "--path"),
    top_k: int = typer.Option(8, "--top-k"),
):
    """Search for chunks answering a question, print short previews."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    embedder = make_embedder(cfg.embedding)
    lance = LanceStore(repo_index_dir(repo_id) / "lancedb", embedder.dim)
    hits = hybrid_search(question, embedder, lance, sqlite, cfg, top_k=top_k)
    if not hits:
        console.print("[yellow]No results.[/yellow]")
        return
    for h in hits:
        console.print(
            f"[cyan]{h.path}[/cyan] [{h.start_line}-{h.end_line}] "
            f"score={h.score:.3f} via={'+'.join(h.sources)}"
        )
        for line in h.content.strip().splitlines()[:3]:
            console.print(f"  {line}")


@app.command()
def search(
    query: str = typer.Argument(...),
    path: str | None = typer.Option(None, "--path"),
    top_k: int = typer.Option(20, "--top-k"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Hybrid search (use --json for programmatic output)."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    embedder = make_embedder(cfg.embedding)
    lance = LanceStore(repo_index_dir(repo_id) / "lancedb", embedder.dim)
    hits = hybrid_search(query, embedder, lance, sqlite, cfg, top_k=top_k)
    if as_json:
        payload = [
            {
                "chunk_id": h.chunk_id,
                "path": h.path,
                "score": h.score,
                "start_line": h.start_line,
                "end_line": h.end_line,
                "language": h.language,
                "sources": h.sources,
                "content": h.content,
            }
            for h in hits
        ]
        typer.echo(json.dumps(payload, indent=2))
    else:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("score")
        table.add_column("path")
        table.add_column("lines")
        table.add_column("via")
        for h in hits:
            table.add_row(
                f"{h.score:.3f}",
                h.path,
                f"{h.start_line}-{h.end_line}",
                "+".join(h.sources),
            )
        console.print(table)


@app.command()
def remember(
    note: str = typer.Argument(...),
    path: str | None = typer.Option(None, "--path"),
    source: str | None = typer.Option(None, "--source"),
):
    """Save a durable note about this repo."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    note_id = memory_remember(sqlite, note, source)
    console.print(f"[green]Remembered[/green] id={note_id}")


@app.command()
def forget(
    id: int = typer.Argument(...),
    path: str | None = typer.Option(None, "--path"),
):
    """Delete a remembered note by id."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    ok = memory_forget(sqlite, id)
    console.print(f"[{'green' if ok else 'yellow'}]{'Removed' if ok else 'No such note'}[/]")


@app.command()
def notes(path: str | None = typer.Option(None, "--path")):
    """List all remembered notes."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    sqlite = SqliteStore(repo_index_dir(repo_id) / "metadata.sqlite")
    rows = list_memory_notes(sqlite)
    if not rows:
        console.print("[yellow]No notes.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("id")
    table.add_column("note")
    table.add_column("tags")
    for r in rows:
        table.add_row(str(r["id"]), r["note"], r["tags"] or "")
    console.print(table)


@app.command()
def status(path: str | None = typer.Option(None, "--path")):
    """Show index status for the current (or given) repo."""
    repo_root = _resolve_repo(path)
    repo_id = lookup(repo_root)
    console.print(f"[bold]repo[/bold]: {repo_root}")
    console.print(f"[bold]index_root[/bold]: {get_index_root()}")
    if not repo_id:
        console.print("[yellow]Not registered.[/yellow] Run `rag init` then `rag rebuild`.")
        return
    cfg = _load_effective_config(repo_id)
    index_dir = repo_index_dir(repo_id)
    sqlite = SqliteStore(index_dir / "metadata.sqlite")
    console.print(f"[bold]index_id[/bold]: {repo_id}")
    console.print(f"[bold]index_dir[/bold]: {index_dir}")
    console.print(f"[bold]files[/bold]: {sqlite.count_files()}")
    console.print(f"[bold]chunks[/bold]: {sqlite.count_chunks()}")
    console.print(f"[bold]notes[/bold]: {sqlite.count_notes()}")
    console.print(
        f"[bold]embedding[/bold]: {cfg.embedding.provider}/"
        f"{cfg.embedding.model} dim={cfg.embedding.dim}"
    )
    console.print(f"[bold]last_index_at[/bold]: {sqlite.get_meta('last_index_at')}")
    console.print(f"[bold]last_rebuild_at[/bold]: {sqlite.get_meta('last_rebuild_at')}")


@app.command()
def deregister(path: str | None = typer.Option(None, "--path")):
    """Remove the repo from the registry. Does NOT delete the index folder."""
    repo_root = _resolve_repo(path)
    repo_id = remove_repo(repo_root)
    if repo_id:
        console.print(f"[green]Deregistered[/green] {repo_root} (index_id={repo_id})")
    else:
        console.print(f"[yellow]Repo {repo_root} was not registered.[/yellow]")


@app.command("mcp-server")
def mcp_server():
    """Run the MCP server over stdio (used by MCP-compatible AI agents)."""
    from .mcp_server import run

    run()


@hooks_app.command("install")
def hooks_install_cmd(
    path: str | None = typer.Option(None, "--path"),
    flags: str = typer.Option(
        "--sequential --window-size 10 --pace-sec 0",
        "--flags",
        help="Extra flags appended to `rag index --changed` inside the hook.",
    ),
):
    """Install repo-rag git hooks (post-commit, post-merge, post-checkout).

    The hook runs `rag index --changed <FLAGS>` in the BACKGROUND so git does
    not block. All output is appended to .git/repo-rag-hook.log.
    """
    repo_root = _resolve_repo(path)
    installed = hooks_install_fn(repo_root, flags=flags)
    console.print(f"[green]Installed hooks[/green]: {', '.join(installed)}")
    console.print(f"  command: [cyan]rag index --changed {flags}[/cyan]")
    console.print(f"  log:     [cyan]{repo_root / '.git' / 'repo-rag-hook.log'}[/cyan]")
    console.print("  watch:   [cyan]rag hooks log --follow[/cyan]")


@hooks_app.command("uninstall")
def hooks_uninstall_cmd(path: str | None = typer.Option(None, "--path")):
    """Remove repo-rag git hooks (preserves any other content)."""
    repo_root = _resolve_repo(path)
    removed = hooks_uninstall_fn(repo_root)
    if removed:
        console.print(f"[green]Removed hooks[/green]: {', '.join(removed)}")
    else:
        console.print("[yellow]No repo-rag hooks were installed.[/yellow]")


@hooks_app.command("log")
def hooks_log_cmd(
    path: str | None = typer.Option(None, "--path"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow the log live."),
    tail: int = typer.Option(50, "--tail", "-n", help="Show last N lines."),
):
    """Show the git-hook indexing log."""
    repo_root = _resolve_repo(path)
    log = repo_root / ".git" / "repo-rag-hook.log"
    if not log.exists():
        console.print(f"[yellow]No log yet at[/yellow] {log}")
        console.print("Make a git commit (or merge/checkout) to trigger the hook.")
        return
    if follow:
        import time as _t

        with log.open("r", encoding="utf-8", errors="replace") as f:
            try:
                f.seek(0, 2)
                size = f.tell()
                start = max(0, size - 8192)
                f.seek(start)
                console.print(f"[dim]--- tail of {log} (Ctrl+C to stop) ---[/dim]")
                console.print(f.read(), end="")
                while True:
                    line = f.readline()
                    if line:
                        console.print(line, end="")
                    else:
                        _t.sleep(0.5)
            except KeyboardInterrupt:
                pass
    else:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-tail:]:
            console.print(line)


def _selected_plugins(target: str | None, detected_only: bool):
    plugins = list(iter_plugins())
    if target:
        return [resolve_target(target)]
    if detected_only:
        return [p for p in plugins if p.detect()]
    return plugins


def _format_path(path: str | Path | None) -> str:
    if not path:
        return "-"
    text = str(path)
    home = str(Path.home())
    if text == home:
        return "~"
    if text.startswith(home + "/"):
        return "~/" + text.removeprefix(home + "/")
    return text


@agents_app.command("list")
def agents_list_cmd():
    """Show every known agent plugin with detection status and paths."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("name")
    table.add_column("display")
    table.add_column("detected")
    table.add_column("user rules", overflow="ignore", no_wrap=True)
    table.add_column("auto MCP")
    for plugin in iter_plugins():
        detected = "yes" if plugin.detect() else "no"
        rules_path = plugin.user_rules_display_path() if not plugin.rules_optional else None
        auto_mcp = "yes" if _supports_auto_mcp(plugin) else "no"
        table.add_row(plugin.name, plugin.display, detected, _format_path(rules_path), auto_mcp)
    console.print(table)


def _supports_auto_mcp(plugin) -> bool:
    from .agents.base import AgentPlugin

    return type(plugin).install_mcp is not AgentPlugin.install_mcp


def _run_agents_setup(
    *,
    target: str | None,
    scopes: list[str],
    detected_only: bool = False,
    include_rules: bool = True,
    include_mcp: bool = True,
    repo_root: Path | None = None,
) -> None:
    repo_root = repo_root or _resolve_repo(None)
    plugins = _selected_plugins(target, detected_only=detected_only and not target)
    if not plugins:
        console.print("[yellow]No agent plugins selected.[/yellow]")
        return
    for plugin in plugins:
        console.print(f"\n[bold]{plugin.display}[/bold] ([cyan]{plugin.name}[/cyan])")
        if include_rules:
            for scope in scopes:
                if scope not in ("user", "project"):
                    continue
                result = plugin.install_rules(
                    scope=scope, repo_root=repo_root if scope == "project" else None
                )
                _print_install_result(scope, "rules", result)
        if include_mcp:
            for scope in scopes:
                if scope not in ("user", "project"):
                    continue
                result = plugin.install_mcp(
                    scope=scope, repo_root=repo_root if scope == "project" else None
                )
                if result is None:
                    if scope == "user":
                        hint = plugin.mcp_hint(scope=scope, repo_root=repo_root)
                        _print_mcp_hint(plugin.display, hint)
                else:
                    _print_install_result(scope, "mcp", result)


def _run_agents_uninstall(
    *,
    target: str | None,
    scopes: list[str],
    repo_root: Path | None = None,
) -> None:
    repo_root = repo_root or _resolve_repo(None)
    plugins = _selected_plugins(target, detected_only=False)
    for plugin in plugins:
        for scope in scopes:
            if scope not in ("user", "project"):
                continue
            removed = plugin.uninstall_rules(
                scope=scope,
                repo_root=repo_root if scope == "project" else None,
            )
            if removed:
                console.print(f"[green]Removed[/green] {plugin.name} {scope} rules")


def _print_install_result(scope: str, kind: str, result) -> None:
    if result is None:
        return
    if result.skipped_reason:
        console.print(f"  [yellow]skipped {scope} {kind}[/yellow]: {result.skipped_reason}")
        return
    if result.written:
        console.print(f"  [green]wrote {scope} {kind}[/green]: {result.path}")
    else:
        console.print(f"  [dim]{scope} {kind} unchanged[/dim]: {result.path}")


def _print_mcp_hint(display: str, hint) -> None:
    console.print(f"  [cyan]Manual MCP setup for {display}:[/cyan]")
    if hint.command:
        console.print(f"    command: [bold]{hint.command}[/bold]")
    if hint.config_path:
        console.print(f"    file:    {hint.config_path}")
    if hint.config_snippet:
        console.print("    snippet:")
        for line in hint.config_snippet.rstrip().splitlines():
            console.print(f"      {line}", soft_wrap=True)
    for note in hint.notes:
        console.print(f"    note: {note}")


@agents_app.command("setup")
def agents_setup_cmd(
    target: str | None = typer.Option(None, "--target", help="Single plugin name."),
    all_targets: bool = typer.Option(False, "--all", help="Set up every detected agent."),
    scope: str = typer.Option("both", "--scope", help="user | project | both"),
    skip_rules: bool = typer.Option(False, "--skip-rules", help="Do not write rules files."),
    skip_mcp: bool = typer.Option(False, "--skip-mcp", help="Do not patch MCP configs."),
    path: str | None = typer.Option(None, "--path", help="Repo path for project scope."),
):
    """Write rules files and patch MCP configs for one or more agents."""
    scopes = ["user", "project"] if scope == "both" else [scope]
    repo_root = _resolve_repo(path)
    detected_only = all_targets and target is None
    _run_agents_setup(
        target=target,
        scopes=scopes,
        detected_only=detected_only,
        include_rules=not skip_rules,
        include_mcp=not skip_mcp,
        repo_root=repo_root,
    )


@agents_app.command("uninstall")
def agents_uninstall_cmd(
    target: str | None = typer.Option(None, "--target", help="Single plugin name."),
    all_targets: bool = typer.Option(False, "--all", help="Uninstall from every agent."),
    scope: str = typer.Option("both", "--scope", help="user | project | both"),
    path: str | None = typer.Option(None, "--path", help="Repo path for project scope."),
):
    """Remove marker-tagged rules blocks (and only those blocks) from one or more agents."""
    if not target and not all_targets:
        console.print(
            "[yellow]Pass --target NAME or --all to choose which agent(s) to uninstall.[/yellow]"
        )
        raise typer.Exit(code=2)
    scopes = ["user", "project"] if scope == "both" else [scope]
    repo_root = _resolve_repo(path)
    _run_agents_uninstall(target=target, scopes=scopes, repo_root=repo_root)


@agents_app.command("print-rules")
def agents_print_rules_cmd(
    target: str | None = typer.Option(None, "--target", help="Plugin name."),
):
    """Dump the rules Markdown that gets installed into agent rules files."""
    from .agents import _rules_text as rt

    if target:
        typer.echo(resolve_target(target).rules_block())
    else:
        typer.echo(rt.md_block())


@agents_app.command("print-mcp")
def agents_print_mcp_cmd(
    target: str | None = typer.Option(None, "--target", help="Plugin name."),
):
    """Dump the recommended MCP configuration snippet for a target (or all)."""
    plugins = [resolve_target(target)] if target else list(iter_plugins())
    for plugin in plugins:
        hint = plugin.mcp_hint()
        console.print(f"\n[bold]{plugin.display}[/bold] ([cyan]{plugin.name}[/cyan])")
        if hint.command:
            console.print(f"  command: {hint.command}")
        if hint.config_path:
            console.print(f"  file:    {hint.config_path}")
        if hint.config_snippet:
            for line in hint.config_snippet.rstrip().splitlines():
                console.print(f"  {line}", soft_wrap=True)
        for note in hint.notes:
            console.print(f"  note: {note}")


@droid_app.command("setup")
def droid_setup(
    skip_agents_md: bool = typer.Option(False, "--skip-agents-md"),
):
    """[deprecated] Alias for `rag agents setup --target factory`."""
    console.print(
        "[yellow]`rag droid setup` is deprecated[/yellow]; "
        "use `rag agents setup --target factory` instead."
    )
    scopes: list[str] = ["user"] if skip_agents_md else ["user", "project"]
    _run_agents_setup(
        target="factory",
        scopes=scopes,
        include_rules=not skip_agents_md,
    )


@droid_app.command("uninstall")
def droid_uninstall():
    """[deprecated] Alias for `rag agents uninstall --target factory`."""
    console.print(
        "[yellow]`rag droid uninstall` is deprecated[/yellow]; "
        "use `rag agents uninstall --target factory` instead."
    )
    _run_agents_uninstall(target="factory", scopes=["user", "project"])


@config_app.command("show")
def config_show(path: str | None = typer.Option(None, "--path", help="Show repo config merge.")):
    """Print the effective global config, or a repo merge with --path."""
    if path:
        repo_root = _resolve_repo(path)
        repo_id = _require_repo_id(repo_root)
        cfg = _load_effective_config(repo_id)
    else:
        cfg = load_global_config()
    typer.echo(json.dumps(cfg.model_dump(), indent=2))


@config_app.command("init")
def config_init():
    """Write the default global config to the index root."""
    cfg = load_global_config()
    save_global_config(cfg)
    console.print(f"[green]Wrote[/green] {get_index_root() / 'config.toml'}")


@config_app.command("repo-init")
def config_repo_init(path: str | None = typer.Argument(None, help="Repo path. Defaults to cwd.")):
    """Write the effective config to this repo's index folder."""
    repo_root = _resolve_repo(path)
    repo_id = _require_repo_id(repo_root)
    cfg = _load_effective_config(repo_id)
    cfg_path = save_repo_config(repo_id, cfg)
    console.print(f"[green]Wrote[/green] {cfg_path}")
    console.print("Edit exclude_globs here to skip files only for this repo.")


if __name__ == "__main__":
    app()
