from typing import Dict, List, Optional

from config import EventConfig
from data_news import retrieve

from eval.judge import judge_relevance
from eval.query_rewriter import rewrite


def precision_at_k(
    q: Dict,
    cfg: Optional[EventConfig] = None,
    k: int = 5,
    use_rewriter: bool = False,
) -> Dict:
    search_query = q["query"]
    rewritten_query = None
    if use_rewriter and cfg is not None:
        rewritten_query = rewrite(q["query"], cfg)
        search_query = rewritten_query

    hits = retrieve(search_query, top_k=k)
    relevant = 0
    per_hit = []

    for h in hits:
        snippet = f"{h.get('headline', '')} {h.get('text', '')}".strip()
        rel = judge_relevance(q["query"], q.get("must_be_about", []), snippet)
        per_hit.append({
            "url": h.get("url"),
            "headline": h.get("headline"),
            "relevant": rel,
        })
        if rel:
            relevant += 1

    retrieved = len(hits)
    precision = relevant / retrieved if retrieved else 0.0
    return {
        "id": q["id"],
        "query": q["query"],
        "rewritten_query": rewritten_query,
        "retrieved": retrieved,
        "relevant": relevant,
        "precision": precision,
        "hits": per_hit,
    }


def run_retrieval_eval(
    queries: List[Dict],
    cfg: Optional[EventConfig] = None,
    k: int = 5,
    use_rewriter: bool = False,
) -> Dict:
    per_query = [
        precision_at_k(q, cfg=cfg, k=k, use_rewriter=use_rewriter)
        for q in queries
    ]
    mean_precision = (
        sum(item["precision"] for item in per_query) / len(per_query)
        if per_query else 0.0
    )
    return {
        "metric": f"precision@{k}",
        "mean_precision": mean_precision,
        "use_rewriter": use_rewriter,
        "per_query": per_query,
    }
