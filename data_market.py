import os
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional
import pandas as pd
import yfinance as yf
from config import EventConfig


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def _prices_dir() -> Path:
    d = _data_dir() / "prices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _csv_path(symbol: str) -> Path:
    safe = symbol.replace("=", "_").replace("^", "").replace("/", "_")
    return _prices_dir() / f"{safe}.csv"


def download_prices(cfg: EventConfig) -> List[str]:
    """Fetch daily OHLCV for each ticker from baseline_date-7 through end_date.

    Returns a list of symbols that yfinance returned empty for — these had no
    CSV written and will be invisible to get_price_changes. Callers should
    surface this (e.g. into manifest.json) so silent gaps become visible.
    """
    start = cfg.baseline_date - timedelta(days=7)
    end = cfg.end_date + timedelta(days=1)
    missing: List[str] = []
    for ticker in cfg.tickers:
        # yfinance 0.2.x defaults to MultiIndex columns for single-ticker calls;
        # multi_level_index=False flattens back to ['Open','Close',...] so CSV
        # write/read round-trips cleanly. See CLAUDE.md "Library Quirks".
        df = yf.download(ticker.symbol, start=start, end=end, progress=False, auto_adjust=False, multi_level_index=False)
        if df.empty:
            print(f"[market] {ticker.symbol}: empty response from yfinance; skipping")
            missing.append(ticker.symbol)
            continue
        df = df.reset_index().rename(columns={"index": "Date"})
        df.to_csv(_csv_path(ticker.symbol), index=False)
    return missing


# One-shot per-symbol warning so bulk calls don't spam logs. Reset across processes,
# which is fine — this is observability for ingestion gaps, not a correctness hook.
_WARNED_MISSING: set[str] = set()


def _load(symbol: str) -> Optional[pd.DataFrame]:
    p = _csv_path(symbol)
    if not p.exists():
        if symbol not in _WARNED_MISSING:
            print(f"[market] {symbol}: no CSV on disk at {p}; "
                  f"setup.py may not have run or ticker was missing in last ingest")
            _WARNED_MISSING.add(symbol)
        return None
    return pd.read_csv(p, parse_dates=["Date"])


def get_price_on_date(symbol: str, d: date) -> Optional[float]:
    """Close price for `symbol` on `d`.

    Returns None in two distinct cases:
      - No CSV on disk for this symbol (ingestion gap; warning logged once per symbol).
      - CSV exists but `d` is not a trading day (weekend/holiday; silent, no warning).
    """
    df = _load(symbol)
    if df is None:
        return None
    match = df[df["Date"].dt.date == d]
    if match.empty:
        return None
    return float(match["Close"].iloc[0])


def get_price_changes(cfg: EventConfig, as_of: date) -> dict:
    """For each ticker in cfg, return {'baseline', 'latest', 'pct_change'}.

    A ticker is *omitted* from the returned dict if any of these are true:
      - No CSV on disk (ingestion gap; warning logged via _load).
      - No row matches `cfg.baseline_date` (weekend/pre-trading).
      - No row matches `as_of` (weekend/pre-trading).
    Callers inspecting `cfg.tickers` vs. the returned keys can detect gaps.
    """
    out = {}
    for ticker in cfg.tickers:
        df = _load(ticker.symbol)
        if df is None or df.empty:
            continue
        baseline = df[df["Date"].dt.date == cfg.baseline_date]
        latest = df[df["Date"].dt.date == as_of]
        if baseline.empty or latest.empty:
            continue
        b = float(baseline["Close"].iloc[0])
        l = float(latest["Close"].iloc[0])
        out[ticker.symbol] = {
            "baseline": b,
            "latest": l,
            "pct_change": (l - b) / b * 100.0,
        }
    return out


def get_price_range(symbol: str, start: date, end: date) -> pd.Series:
    """Close-price Series indexed by Date for [start, end] inclusive, trading days only.

    Returns an empty Series in two distinct cases:
      - No CSV on disk for this symbol (ingestion gap; warning logged via _load).
      - CSV exists but no trading days fall inside [start, end] (silent).
    """
    df = _load(symbol)
    if df is None:
        return pd.Series(dtype=float)
    mask = (df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)
    sub = df.loc[mask, ["Date", "Close"]].set_index("Date")
    return sub["Close"]
