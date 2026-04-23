"""One-shot data pipeline: python setup.py --event iran_war"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from config import load_event
from data_news import gdelt, newsapi_fetcher, rss
from data_news import store, vector_store
from data_news.dedup import deduplicate
import data_market


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch news + market data for an event.")
    parser.add_argument("--event", required=True, help="Event config name (e.g. iran_war)")
    parser.add_argument("--refresh", action="store_true", help="Wipe prior index before fetching")
    args = parser.parse_args(argv)

    cfg = load_event(args.event)
    print(f"[setup] Event: {cfg.display_name}  window: {cfg.start_date} → {cfg.end_date}")

    if args.refresh:
        # --refresh means "nuke everything and rebuild". Previously only wiped
        # the ChromaDB directory, leaving stale articles.json and prices/*.csv
        # behind — a ticker removed from the YAML would silently keep its old
        # CSV, and a shrunken/failed news fetch would overwrite a good snapshot
        # partially. Now we wipe all three together.
        vector_store.reset()
        arts_path = _data_dir() / "articles.json"
        if arts_path.exists():
            arts_path.unlink()
        prices_dir = _data_dir() / "prices"
        if prices_dir.exists():
            shutil.rmtree(prices_dir)

    print("[setup] Fetching GDELT...")
    g = gdelt.fetch(cfg)
    print(f"  {len(g)} articles")

    print("[setup] Fetching NewsAPI...")
    n = newsapi_fetcher.fetch(cfg)
    print(f"  {len(n)} articles")

    print("[setup] Fetching RSS...")
    r = rss.fetch(cfg)
    print(f"  {len(r)} articles")

    all_articles = g + n + r
    print(f"[setup] Deduplicating {len(all_articles)} total...")
    unique = deduplicate(all_articles)
    print(f"  {len(unique)} unique")

    store.write_articles(unique)
    print("[setup] Indexing into ChromaDB...")
    vector_store.index_articles(unique)

    print("[setup] Downloading prices...")
    data_market.download_prices(cfg)

    manifest = {
        "event": cfg.name,
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "source_counts": {"gdelt": len(g), "newsapi": len(n), "rss": len(r)},
        "ticker_count": len(cfg.tickers),
    }
    (_data_dir() / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[setup] Done. Manifest: {_data_dir() / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
