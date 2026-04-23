"""NewsAPI.org fetcher — secondary source, 100 req/day free tier, snippets only."""
import os
from datetime import date, timedelta
from typing import Dict, List

from newsapi import NewsApiClient

from config import EventConfig


_FREE_TIER_LOOKBACK_DAYS = 29


def fetch(cfg: EventConfig, max_pages: int = 1) -> List[Dict]:
    """Fetch via NewsAPI /v2/everything. Free tier only serves the last 30 days;
    clamps start_date accordingly and returns [] if the event window is entirely older."""
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return []
    try:
        today = date.today()
        earliest = today - timedelta(days=_FREE_TIER_LOOKBACK_DAYS)
        if cfg.end_date < earliest or cfg.start_date > today:
            print(
                f"[newsapi] Event window {cfg.start_date}→{cfg.end_date} "
                f"is outside the free-tier 30-day range ({earliest}→{today}); skipping."
            )
            return []
        effective_start = max(cfg.start_date, earliest)
        effective_end = min(cfg.end_date, today)
        client = NewsApiClient(api_key=key)
        q = " OR ".join(cfg.seed_keywords)
        results: List[Dict] = []
        for page in range(1, max_pages + 1):
            resp = client.get_everything(
                q=q,
                from_param=effective_start.isoformat(),
                to=effective_end.isoformat(),
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
    except Exception as e:
        print(f"[newsapi] fetch failed: {e}")
        return []
