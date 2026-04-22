"""Live integration smoke. Hits real GDELT + yfinance. Run with: RUN_LIVE=1 pytest tests/test_smoke_live.py -v"""
import os
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1",
    reason="Live integration test. Set RUN_LIVE=1 to enable.",
)


def test_yfinance_live_fetches_spy():
    import yfinance as yf
    end = date.today()
    start = end - timedelta(days=10)
    df = yf.download("SPY", start=start.isoformat(), end=end.isoformat(), progress=False, multi_level_index=False)
    assert not df.empty
    assert "Close" in df.columns


def test_gdelt_live_returns_articles():
    from gdeltdoc import GdeltDoc, Filters
    end = date.today()
    start = end - timedelta(days=3)
    f = Filters(keyword=["oil", "crude"], start_date=start.isoformat(), end_date=end.isoformat())
    df = GdeltDoc().article_search(f)
    assert not df.empty
    assert "url" in df.columns
