"""One-shot data pipeline: python setup.py --event iran_war"""
import argparse
import contextlib
import fcntl
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List

from config import load_event
from data_news import gdelt, newsapi_fetcher, rss
from data_news import store, vector_store
from data_news.dedup import deduplicate
import data_market


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def _lock_path() -> Path:
    return _data_dir() / "setup.lock"


@contextlib.contextmanager
def _setup_lock() -> Iterator[None]:
    """Prevent two concurrent `setup.py` runs from corrupting ChromaDB / articles.json.

    Uses fcntl.flock (POSIX advisory, per-process); macOS + Linux honor it.
    Raises RuntimeError immediately if another run holds the lock — Plan 3's
    Streamlit UI should prefer `is_setup_in_progress()` over just calling
    setup.main() to avoid racing the user.
    """
    _data_dir().mkdir(parents=True, exist_ok=True)
    path = _lock_path()
    fh = open(path, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        raise RuntimeError(
            f"Another setup.py run is in progress (lock held at {path}). "
            f"Wait for it to finish, or delete the file if no process owns it."
        )
    try:
        fh.write(f"pid={os.getpid()} started={datetime.now(timezone.utc).isoformat()}\n")
        fh.flush()
        yield
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


def is_setup_in_progress() -> bool:
    """Returns True if setup.py is currently running against this DATA_DIR.

    Intended for Plan 3's Streamlit UI to gate "refresh now" buttons and to
    warn the user if a background ingest is in flight.
    """
    path = _lock_path()
    if not path.exists():
        return False
    try:
        fh = open(path, "r")
    except OSError:
        return False
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # We got it — nobody else holds it. Release and report free.
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    finally:
        fh.close()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch news + market data for an event.")
    parser.add_argument("--event", required=True, help="Event config name (e.g. iran_war)")
    parser.add_argument("--refresh", action="store_true", help="Wipe prior index before fetching")
    args = parser.parse_args(argv)

    with _setup_lock():
        return _run(args)


def _run(args) -> int:
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
    unique, dedup_stats = deduplicate(all_articles)
    print(f"  {len(unique)} unique "
          f"(url_dropped={dedup_stats['url_dropped']}, "
          f"minhash_dropped={dedup_stats['minhash_dropped']})")

    store.write_articles(unique)
    print("[setup] Indexing into ChromaDB...")
    vector_store.index_articles(unique)

    print("[setup] Downloading prices...")
    missing_tickers = data_market.download_prices(cfg)
    if missing_tickers:
        print(f"[setup] WARNING: {len(missing_tickers)} tickers returned empty: {missing_tickers}")

    manifest = {
        "event": cfg.name,
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "source_counts": {"gdelt": len(g), "newsapi": len(n), "rss": len(r)},
        "dedup": dedup_stats,
        "ticker_count": len(cfg.tickers),
        "missing_tickers": missing_tickers,
    }
    (_data_dir() / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[setup] Done. Manifest: {_data_dir() / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
