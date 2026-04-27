from typing import Dict, List

from data_news import retrieve

from eval.judge import judge_relevance


def precision_at_k(q: Dict, k: int = 5) -> Dict:
    hits = retrieve(q["query"], top_k=k)
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
        "retrieved": retrieved,
        "relevant": relevant,
        "precision": precision,
        "hits": per_hit,
    }


def run_retrieval_eval(queries: List[Dict], k: int = 5) -> Dict:
    per_query = [precision_at_k(q, k=k) for q in queries]
    mean_precision = (
        sum(item["precision"] for item in per_query) / len(per_query)
        if per_query else 0.0
    )
    return {
        "metric": f"precision@{k}",
        "mean_precision": mean_precision,
        "per_query": per_query,
    }
