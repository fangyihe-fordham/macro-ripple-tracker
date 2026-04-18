import os
from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from config import load_event
import data_market


@pytest.fixture
def fake_yf(monkeypatch, fixtures_dir):
    """Replace yfinance.download with a function that returns our fixture DataFrame."""
    df = pd.read_csv(fixtures_dir / "yf_brent_sample.csv", parse_dates=["Date"]).set_index("Date")

    def fake_download(tickers, start, end, progress=False, auto_adjust=False):
        return df.copy()

    monkeypatch.setattr(data_market.yf, "download", fake_download)
    return df


def test_download_prices_writes_csv(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    price_dir = tmp_data_dir / "prices"
    assert price_dir.exists()
    csvs = list(price_dir.glob("*.csv"))
    assert len(csvs) == len(cfg.tickers)
    sample = pd.read_csv(csvs[0], parse_dates=["Date"])
    assert {"Date", "Close"}.issubset(sample.columns)


def test_get_price_on_date(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    close = data_market.get_price_on_date("BZ=F", date(2026, 2, 27))
    assert close == pytest.approx(74.20)


def test_get_price_on_date_missing_returns_none(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    # Weekend / non-trading day
    assert data_market.get_price_on_date("BZ=F", date(2026, 3, 1)) is None
