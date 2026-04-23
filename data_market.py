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


def _load(symbol: str) -> Optional[pd.DataFrame]:
    p = _csv_path(symbol)
    if not p.exists():
        return None
    return pd.read_csv(p, parse_dates=["Date"])


def get_price_on_date(symbol: str, d: date) -> Optional[float]:
    df = _load(symbol)
    if df is None:
        return None
    match = df[df["Date"].dt.date == d]
    if match.empty:
        return None
    return float(match["Close"].iloc[0])


def get_price_changes(cfg: EventConfig, as_of: date) -> dict:
    """For each ticker, return {'baseline', 'latest', 'pct_change'} comparing baseline_date to as_of close."""
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
    """Return a Close-price Series indexed by Date for [start, end] inclusive."""
    df = _load(symbol)
    if df is None:
        return pd.Series(dtype=float)
    mask = (df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)
    sub = df.loc[mask, ["Date", "Close"]].set_index("Date")
    return sub["Close"]
