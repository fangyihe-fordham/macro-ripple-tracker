"""Reuters / AP RSS fetcher — tertiary source, canonical timestamps for major events."""
from datetime import datetime
from typing import List, Dict

import feedparser

from config import EventConfig


def _parse_feed(url: str):
    return feedparser.parse(url)


def _matches_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in keywords)


def fetch(cfg: EventConfig) -> List[Dict]:
    out: List[Dict] = []
    for url in cfg.rss_feeds:
        parsed = _parse_feed(url)
        for entry in parsed.entries:
            blob = f"{entry.get('title', '')} {entry.get('summary', '')}"
            if not _matches_any(blob, cfg.seed_keywords):
                continue
            pub = entry.get("published_parsed")
            iso_date = datetime(*pub[:6]).date().isoformat() if pub else ""
            out.append({
                "url": entry.get("link", ""),
                "headline": entry.get("title", ""),
                "source": url,
                "date": iso_date,
                "snippet": entry.get("summary", "") or "",
                "full_text": "",
                "source_kind": "rss",
            })
    return out
