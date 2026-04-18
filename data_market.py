import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
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


def download_prices(cfg: EventConfig) -> None:
    """Fetch daily OHLCV for each ticker from baseline_date-7 through end_date."""
    start = cfg.baseline_date - timedelta(days=7)
    end = cfg.end_date + timedelta(days=1)
    for ticker in cfg.tickers:
        df = yf.download(ticker.symbol, start=start, end=end, progress=False, auto_adjust=False)
        if df.empty:
            continue
        df = df.reset_index().rename(columns={"index": "Date"})
        df.to_csv(_csv_path(ticker.symbol), index=False)


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
