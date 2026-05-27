import sys
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo_rag.config import load_global_config
from repo_rag.fileutils import iter_repo_files

parser = argparse.ArgumentParser()
parser.add_argument("repo")
args = parser.parse_args()

repo = Path(args.repo)
if not repo.exists():
    print(f"REPO NOT FOUND: {repo}")
    sys.exit(1)

cfg = load_global_config()
files = list(iter_repo_files(repo, cfg.include_globs, cfg.exclude_globs, cfg.chunking.max_file_bytes))
total = sum(p.stat().st_size for p in files)
print(f"Files to index: {len(files)}")
print(f"Total size: {total/1024/1024:.2f} MB")
print(f"Est. chunks: ~{int(total/2000):,}")
print()

ext = Counter(p.suffix.lower() for p in files)
print("By extension:")
for e, n in ext.most_common(10):
    label = e or "(none)"
    print(f"  {label:<10} {n}")

print()
top = sorted(files, key=lambda p: -p.stat().st_size)[:8]
print("Top 8 largest:")
for p in top:
    print(f"  {p.stat().st_size/1024:>6.0f} KB  {p.relative_to(repo).as_posix()}")
