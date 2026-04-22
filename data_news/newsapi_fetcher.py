"""NewsAPI.org fetcher — secondary source, 100 req/day free tier, snippets only."""
import os
from typing import Dict, List

from newsapi import NewsApiClient

from config import EventConfig


def fetch(cfg: EventConfig, max_pages: int = 1) -> List[Dict]:
    """Fetch via NewsAPI /v2/everything. Skips silently if NEWSAPI_KEY is unset."""
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return []
    client = NewsApiClient(api_key=key)
    q = " OR ".join(cfg.seed_keywords)
    results: List[Dict] = []
    for page in range(1, max_pages + 1):
        resp = client.get_everything(
            q=q,
            from_param=cfg.start_date.isoformat(),
            to=cfg.end_date.isoformat(),
            language="en",
            page_size=100,
            page=page,
        )
        articles = resp.get("articles", [])
        for a in articles:
            pub = a.get("publishedAt", "")[:10]
            results.append({
                "url": a.get("url", ""),
                "headline": a.get("title", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "date": pub,
                "snippet": a.get("description", "") or "",
                "full_text": a.get("content", "") or "",
                "source_kind": "newsapi",
            })
        if len(articles) < 100:
            break
    return results
