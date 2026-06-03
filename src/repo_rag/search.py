from __future__ import annotations

import re
from dataclasses import dataclass

from .config import GlobalConfig
from .embedder.base import EmbeddingProvider
from .fileutils import languages_for_content
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


_CAMEL = re.compile(r"[a-z0-9][A-Z]")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DOTTED = re.compile(r"[A-Za-z_]\.[A-Za-z_]")
_SUBTOKEN = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
_DEF_KEYWORDS = (
    "def|class|func|fn|function|interface|struct|enum|trait|impl|type|"
    "module|namespace|var|let|const|public|private|protected|static|async|export"
)
_NOISE_SUBSTRINGS = (
    "/test",
    "test/",
    "tests/",
    "__tests__",
    "/spec",
    "spec/",
    "/legacy/",
    "/compat/",
    "/deprecated/",
    "/examples/",
    "/example/",
    "/samples/",
    "/sample/",
    "/demo/",
    "/fixtures/",
    "/vendor/",
    "/third_party/",
    "/node_modules/",
)
_NOISE_NAME = re.compile(r"(^|/)test_|_test\.|\.test\.|\.spec\.|\.stories\.")


def is_symbolic_query(query: str) -> bool:
    """Heuristic: does the query look like a code symbol rather than prose?"""
    q = query.strip()
    if not q:
        return False
    if "::" in q or "->" in q:
        return True
    tokens = q.split()
    if len(tokens) <= 2:
        for t in tokens:
            if _CAMEL.search(t) or "_" in t or _DOTTED.search(t):
                return True
        return bool(len(tokens) == 1 and _IDENT.match(tokens[0]))
    symboly = sum(1 for t in tokens if _CAMEL.search(t) or "_" in t or _DOTTED.search(t))
    return symboly >= max(2, len(tokens) // 2)


def adaptive_weights(query: str, cfg: GlobalConfig) -> tuple[float, float]:
    if is_symbolic_query(query):
        return cfg.retrieval.symbol_vector_weight, cfg.retrieval.symbol_keyword_weight
    return cfg.retrieval.vector_weight, cfg.retrieval.keyword_weight


def subtokenize(identifier: str) -> set[str]:
    """Split an identifier into lowercased sub-tokens (camelCase + snake_case)."""
    out: set[str] = set()
    for part in re.split(r"[^A-Za-z0-9]+", identifier):
        if not part:
            continue
        for sub in _SUBTOKEN.findall(part):
            s = sub.lower()
            if len(s) >= 2:
                out.add(s)
    return out


def stem_tokens(text: str) -> set[str]:
    stems: set[str] = set()
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        stems |= subtokenize(tok)
    return stems


def defines_symbol(content: str, symbols: set[str]) -> bool:
    """True if `content` appears to *define* (not just reference) a query symbol."""
    for sym in symbols:
        esc = re.escape(sym)
        if re.search(rf"\b(?:{_DEF_KEYWORDS})\b[^\n]*\b{esc}\b", content):
            return True
        if re.search(rf"(?m)^\s*(?:export\s+)?{esc}\s*[:=(]", content):
            return True
    return False


def noise_penalty_for(path: str, cfg: GlobalConfig) -> float:
    p = path.lower()
    if p.endswith(".d.ts") or any(s in p for s in _NOISE_SUBSTRINGS) or _NOISE_NAME.search(p):
        return cfg.retrieval.noise_penalty
    return 0.0


def rrf_fuse(
    vec_pairs: list[tuple[str, float]],
    fts_pairs: list[tuple[str, float]],
    vector_weight: float,
    keyword_weight: float,
    k: int = 60,
) -> dict[str, dict]:
    """Reciprocal Rank Fusion over two best-first ranked lists."""
    combined: dict[str, dict] = {}
    for rank, (cid, _) in enumerate(vec_pairs, start=1):
        entry = combined.setdefault(cid, {"score": 0.0, "sources": []})
        entry["score"] += vector_weight * (1.0 / (k + rank))
        entry["sources"].append("vector")
    for rank, (cid, _) in enumerate(fts_pairs, start=1):
        entry = combined.setdefault(cid, {"score": 0.0, "sources": []})
        entry["score"] += keyword_weight * (1.0 / (k + rank))
        if "keyword" not in entry["sources"]:
            entry["sources"].append("keyword")
    return combined


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
    content: str = "all",
) -> list[SearchHit]:
    top_k = top_k or cfg.retrieval.top_k
    allowed = languages_for_content(content)
    fetch = max(top_k * 3, 30)
    if allowed is not None:
        fetch = max(fetch, top_k * 6)

    vec = embedder.embed_one(query)
    vec_hits = lance.search(vec, top_k=fetch)
    vec_pairs = [(h["chunk_id"], h["score"]) for h in vec_hits]

    fts_query = to_fts_query(query)
    fts_hits = sqlite.fts_search(fts_query, limit=fetch)
    fts_pairs = [(cid, score) for cid, _, score in fts_hits]

    vec_w, kw_w = adaptive_weights(query, cfg)
    combined = rrf_fuse(vec_pairs, fts_pairs, vec_w, kw_w, cfg.retrieval.rrf_k)
    if not combined:
        return []

    base = normalize_scores([(cid, info["score"]) for cid, info in combined.items()])
    ranked = sorted(combined.items(), key=lambda kv: -kv[1]["score"])
    candidate_ids = [cid for cid, _ in ranked[:fetch]]
    rows = sqlite.get_chunks(candidate_ids)
    by_id = {r["chunk_id"]: r for r in rows}

    if allowed is not None:
        candidate_ids = [
            cid for cid in candidate_ids if by_id.get(cid) and by_id[cid]["language"] in allowed
        ]

    path_counts: dict[str, int] = {}
    for cid in candidate_ids:
        row = by_id.get(cid)
        if row is not None:
            path_counts[row["path"]] = path_counts.get(row["path"], 0) + 1

    mtimes = (
        sqlite.get_file_mtimes(list({r["path"] for r in rows}))
        if cfg.retrieval.recency_boost > 0
        else {}
    )
    rec_min = min(mtimes.values()) if mtimes else 0.0
    rec_span = (max(mtimes.values()) - rec_min) if mtimes else 0.0

    symbols = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query))
    stems = stem_tokens(query)

    hits: list[SearchHit] = []
    for cid in candidate_ids:
        row = by_id.get(cid)
        if row is None:
            continue
        info = combined[cid]
        score = base.get(cid, 0.0)
        content = row["content"] or ""
        path = row["path"]

        if symbols and defines_symbol(content, symbols):
            score += cfg.retrieval.definition_boost
        basename = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if basename in symbols:
            score += cfg.retrieval.definition_boost * 0.5
        if stems:
            overlap = len(stems & stem_tokens(content))
            if overlap:
                score += cfg.retrieval.identifier_stem_boost * min(1.0, overlap / len(stems))
        count = path_counts.get(path, 1)
        if count > 1:
            score += cfg.retrieval.file_coherence_boost * min(1.0, (count - 1) / 3.0)
        if rec_span > 0:
            mt = mtimes.get(path)
            if mt is not None:
                score += cfg.retrieval.recency_boost * ((mt - rec_min) / rec_span)
        score -= noise_penalty_for(path, cfg)

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
    hits.sort(key=lambda h: -h.score)
    return hits[:top_k]


def find_related(
    file_path: str,
    line: int,
    embedder: EmbeddingProvider,
    lance: LanceStore,
    sqlite: SqliteStore,
    cfg: GlobalConfig,
    top_k: int | None = None,
) -> list[SearchHit]:
    """Return chunks semantically similar to the code at `file_path:line`."""
    top_k = top_k or cfg.retrieval.top_k
    norm_path = file_path.replace("\\", "/")
    anchor = sqlite.get_chunk_at(norm_path, line)
    if anchor is None:
        return []

    vec = embedder.embed_one(anchor["content"] or "")
    raw = lance.search(vec, top_k=top_k + 5)
    hits: list[SearchHit] = []
    for h in raw:
        if h["chunk_id"] == anchor["chunk_id"]:
            continue
        row = sqlite.get_chunk(h["chunk_id"])
        if row is None:
            continue
        hits.append(
            SearchHit(
                chunk_id=h["chunk_id"],
                path=row["path"],
                score=float(h["score"]),
                start_line=row["start_line"] or 1,
                end_line=row["end_line"] or 1,
                language=row["language"] or "",
                content=row["content"] or "",
                sources=["related"],
            )
        )
        if len(hits) >= top_k:
            break
    return hits
