from __future__ import annotations

import re
from dataclasses import dataclass

from .config import GlobalConfig
from .embedder.base import EmbeddingProvider
from .store.lance import LanceStore
from .store.sqlite import SqliteStore


@dataclass
class SearchHit:
    chunk_id: str
    path: str
    score: float
    start_line: int
    end_line: int
    language: str
    content: str
    sources: list[str]


def to_fts_query(text: str) -> str:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
    if not tokens:
        return text
    return " OR ".join(f'"{t}"' for t in tokens[:32])


def normalize_scores(items: list[tuple[str, float]]) -> dict[str, float]:
    if not items:
        return {}
    scores = [s for _, s in items]
    smin = min(scores)
    smax = max(scores)
    if smax - smin < 1e-9:
        return {cid: 1.0 for cid, _ in items}
    return {cid: (s - smin) / (smax - smin) for cid, s in items}


def merge_results(
    vec_hits: list[tuple[str, float]],
    fts_hits: list[tuple[str, float]],
    vector_weight: float,
    keyword_weight: float,
) -> dict[str, dict]:
    vec_norm = normalize_scores(vec_hits)
    fts_norm = normalize_scores(fts_hits)
    combined: dict[str, dict] = {}
    for cid, score in vec_norm.items():
        combined.setdefault(cid, {"score": 0.0, "sources": []})
        combined[cid]["score"] += vector_weight * score
        combined[cid]["sources"].append("vector")
    for cid, score in fts_norm.items():
        combined.setdefault(cid, {"score": 0.0, "sources": []})
        combined[cid]["score"] += keyword_weight * score
        combined[cid]["sources"].append("keyword")
    return combined


def hybrid_search(
    query: str,
    embedder: EmbeddingProvider,
    lance: LanceStore,
    sqlite: SqliteStore,
    cfg: GlobalConfig,
    top_k: int | None = None,
) -> list[SearchHit]:
    top_k = top_k or cfg.retrieval.top_k

    vec = embedder.embed_one(query)
    vec_hits = lance.search(vec, top_k=top_k * 3)
    vec_pairs = [(h["chunk_id"], h["score"]) for h in vec_hits]

    fts_query = to_fts_query(query)
    fts_hits = sqlite.fts_search(fts_query, limit=top_k * 3)
    fts_pairs = [(cid, score) for cid, _, score in fts_hits]

    combined = merge_results(
        vec_pairs,
        fts_pairs,
        cfg.retrieval.vector_weight,
        cfg.retrieval.keyword_weight,
    )

    symbols = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query))
    ranked = sorted(combined.items(), key=lambda kv: -kv[1]["score"])
    candidate_ids = [cid for cid, _ in ranked[: top_k * 2]]
    rows = sqlite.get_chunks(candidate_ids)
    by_id = {r["chunk_id"]: r for r in rows}

    hits: list[SearchHit] = []
    for cid, info in ranked:
        row = by_id.get(cid)
        if row is None:
            continue
        score = info["score"]
        content = row["content"] or ""
        if symbols and any(s in content for s in symbols):
            score += 0.05
        path = row["path"]
        basename = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if basename in symbols:
            score += 0.10
        hits.append(
            SearchHit(
                chunk_id=cid,
                path=path,
                score=score,
                start_line=row["start_line"] or 1,
                end_line=row["end_line"] or 1,
                language=row["language"] or "",
                content=content,
                sources=info["sources"],
            )
        )
        if len(hits) >= top_k:
            break
    hits.sort(key=lambda h: -h.score)
    return hits
