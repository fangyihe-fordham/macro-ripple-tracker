"""GDELT 2.0 fetcher — primary news source. Free, no API key, ~15min cadence."""
import time
from datetime import timedelta
from typing import Dict, List

from gdeltdoc import GdeltDoc, Filters

from config import EventConfig


_CHUNK_DAYS = 7
_MAX_RECORDS_PER_CHUNK = 250
_SLEEP_BETWEEN_CHUNKS = 2


def fetch(cfg: EventConfig) -> List[Dict]:
    client = GdeltDoc()
    out: List[Dict] = []
    chunk_start = cfg.start_date
    chunk_idx = 0
    while chunk_start < cfg.end_date:
        chunk_end = min(chunk_start + timedelta(days=_CHUNK_DAYS), cfg.end_date)
        chunk_idx += 1
        if chunk_idx > 1:
            time.sleep(_SLEEP_BETWEEN_CHUNKS)
        filters = Filters(
            keyword=cfg.seed_keywords,
            start_date=chunk_start.isoformat(),
            end_date=chunk_end.isoformat(),
            num_records=_MAX_RECORDS_PER_CHUNK,
        )
        try:
            df = client.article_search(filters)
        except Exception as e:
            print(f"[gdelt] Chunk {chunk_idx} {chunk_start}→{chunk_end} failed: {e}")
            chunk_start = chunk_end
            continue
        count = 0 if df.empty else len(df)
        print(f"[gdelt] Chunk {chunk_idx} {chunk_start}→{chunk_end}: {count} articles")
        if not df.empty:
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
        chunk_start = chunk_end
    return out
