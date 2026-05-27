import sqlite3
import sys
import subprocess
from pathlib import Path

repo = Path(sys.argv[1])
db = Path(sys.argv[2])

head = subprocess.run(
    ["git", "-C", str(repo), "rev-parse", "HEAD"],
    capture_output=True, text=True, check=True,
).stdout.strip()
print(f"HEAD = {head}")

c = sqlite3.connect(db)
c.execute(
    "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
    ("last_index_commit", head),
)
c.commit()
val = c.execute("SELECT value FROM meta WHERE key='last_index_commit'").fetchone()[0]
print(f"Stored last_index_commit = {val}")
