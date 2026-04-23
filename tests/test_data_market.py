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

    def fake_download(tickers, start, end, progress=False, auto_adjust=False, **kwargs):
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


def test_get_price_changes_vs_baseline(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    changes = data_market.get_price_changes(cfg, as_of=date(2026, 3, 4))
    # BZ=F: baseline Feb 27 close = 74.20, as_of Mar 4 close = 111.00
    # pct_change = (111.00 - 74.20) / 74.20 * 100 ≈ 49.60%
    assert "BZ=F" in changes
    assert changes["BZ=F"]["baseline"] == pytest.approx(74.20)
    assert changes["BZ=F"]["latest"] == pytest.approx(111.00)
    assert changes["BZ=F"]["pct_change"] == pytest.approx(49.60, abs=0.1)


def test_get_price_range(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    series = data_market.get_price_range("BZ=F", date(2026, 2, 26), date(2026, 3, 3))
    # Inclusive on both ends; trading days only (no 2026-03-01 because fixture skips weekend)
    assert list(series.index.date.astype(str)) == ["2026-02-26", "2026-02-27", "2026-03-02", "2026-03-03"]
    assert series.iloc[-1] == pytest.approx(102.30)


def test_download_prices_returns_missing_symbols(tmp_data_dir, monkeypatch, fixtures_dir):
    """Tickers that yfinance returns empty for must surface in the return value, not silent."""
    cfg = load_event("iran_war")
    ok_df = pd.read_csv(fixtures_dir / "yf_brent_sample.csv", parse_dates=["Date"]).set_index("Date")

    def selective_download(tickers, start, end, progress=False, auto_adjust=False, **kwargs):
        # Two specific symbols return empty; everything else returns the fixture.
        if tickers in {"BZ=F", "CL=F"}:
            return pd.DataFrame()
        return ok_df.copy()

    monkeypatch.setattr(data_market.yf, "download", selective_download)
    missing = data_market.download_prices(cfg)
    assert set(missing) == {"BZ=F", "CL=F"}
    assert len(missing) == 2
