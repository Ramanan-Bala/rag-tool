import sqlite3
from pathlib import Path

db = Path.home() / ".droid-index" / "raptor-forms-render" / "metadata.sqlite"
c = sqlite3.connect(str(db))
total = c.execute("select count(*) from files").fetchone()[0]
testdata = c.execute("select count(*) from files where path like '%TestData%'").fetchone()[0]
drawio = c.execute("select count(*) from files where path like '%.drawio%'").fetchone()[0]
k_json = c.execute("select count(*) from files where path like '%/Data/K%.json'").fetchone()[0]
print(f"Total files indexed: {total}")
print(f"In TestData/:        {testdata}")
print(f".drawio files:       {drawio}")
print(f"/Data/K*.json:       {k_json}")
print()
print("Latest 8 file paths indexed:")
for r in c.execute("select path from files order by file_id desc limit 8").fetchall():
    print("  ", r[0])
