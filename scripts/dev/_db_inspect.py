import sqlite3
import sys

db = r"C:\Users\LH719EC\.droid-index\raptor-forms-profile-api\metadata.sqlite"
c = sqlite3.connect(db)

print(f"files:  {c.execute('select count(*) from files').fetchone()[0]}")
print(f"chunks: {c.execute('select count(*) from chunks').fetchone()[0]}")
print(f"cached: {c.execute('select count(*) from embedding_cache').fetchone()[0]}")
print()

print("By file extension:")
rows = c.execute("SELECT path FROM files").fetchall()
from collections import Counter
exts = Counter()
for (p,) in rows:
    if "." in p:
        exts[p.rsplit(".", 1)[-1].lower()] += 1
    else:
        exts["(none)"] += 1
for ext, n in exts.most_common(10):
    print(f"  .{ext:<10} {n}")

print()
print("Random sample of 8 files in DB:")
for (p,) in c.execute("SELECT path FROM files ORDER BY random() LIMIT 8"):
    print(f"  {p}")
