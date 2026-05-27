from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

try:
    import lancedb
    import pyarrow as pa
except ImportError:
    lancedb = None
    pa = None


def _sql_list(items: Sequence[str]) -> str:
    return ",".join("'" + str(i).replace("'", "''") + "'" for i in items)


class LanceStore:
    TABLE = "chunks"

    def __init__(self, lance_dir: Path, dim: int):
        if lancedb is None or pa is None:
            raise RuntimeError(
                "lancedb is not installed. Install with: pip install lancedb pyarrow"
            )
        lance_dir.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self.db = lancedb.connect(str(lance_dir))
        self._ensure_table()

    def _schema(self):
        return pa.schema(
            [
                ("chunk_id", pa.string()),
                ("path", pa.string()),
                ("vector", pa.list_(pa.float32(), self.dim)),
            ]
        )

    def _ensure_table(self):
        if self.TABLE not in self.db.table_names():
            self.db.create_table(self.TABLE, schema=self._schema())
        self._table = self.db.open_table(self.TABLE)

    def upsert(self, rows: list[dict]) -> None:
        if not rows:
            return
        normalized = []
        for r in rows:
            v = np.asarray(r["vector"], dtype=np.float32).flatten()
            if v.shape[0] != self.dim:
                continue
            normalized.append(
                {
                    "chunk_id": r["chunk_id"],
                    "path": r["path"],
                    "vector": v.tolist(),
                }
            )
        if not normalized:
            return
        ids = [r["chunk_id"] for r in normalized]
        try:
            self._table.delete(f"chunk_id IN ({_sql_list(ids)})")
        except Exception:
            pass
        self._table.add(normalized)

    def delete_chunks(self, chunk_ids: Sequence[str]) -> None:
        if not chunk_ids:
            return
        try:
            self._table.delete(f"chunk_id IN ({_sql_list(chunk_ids)})")
        except Exception:
            pass

    def clear(self) -> None:
        if self.TABLE in self.db.table_names():
            self.db.drop_table(self.TABLE)
        self._ensure_table()

    def search(self, query_vec: np.ndarray, top_k: int = 20) -> list[dict]:
        q = np.asarray(query_vec, dtype=np.float32).flatten()
        try:
            results = self._table.search(q).limit(top_k).to_list()
        except Exception:
            return []
        out = []
        for r in results:
            dist = float(r.get("_distance", 1.0))
            out.append(
                {
                    "chunk_id": r["chunk_id"],
                    "path": r["path"],
                    "score": 1.0 - dist,
                }
            )
        return out
