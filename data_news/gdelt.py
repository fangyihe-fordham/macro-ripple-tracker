"""GDELT 2.0 fetcher — primary news source. Free, no API key, ~15min cadence."""
from typing import List, Dict
from gdeltdoc import GdeltDoc, Filters
from config import EventConfig


def fetch(cfg: EventConfig) -> List[Dict]:
    start = cfg.start_date.isoformat()
    end = cfg.end_date.isoformat()
    filters = Filters(
        keyword=cfg.seed_keywords,
        start_date=start,
        end_date=end,
    )
    filters.keyword = cfg.seed_keywords
    filters.start_date = start
    filters.end_date = end
    client = GdeltDoc()
    df = client.article_search(filters)
    if df.empty:
        return []
    out: List[Dict] = []
    for _, row in df.iterrows():
        seen = str(row.get("seendate", ""))
        iso_date = f"{seen[0:4]}-{seen[4:6]}-{seen[6:8]}" if len(seen) >= 8 else ""
        out.append({
            "url": row["url"],
            "headline": row.get("title", ""),
            "source": row.get("domain", ""),
            "date": iso_date,
            "snippet": "",
            "full_text": "",
            "source_kind": "gdelt",
        })
    return out
