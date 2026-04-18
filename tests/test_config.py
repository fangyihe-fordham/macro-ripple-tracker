from datetime import date
from pathlib import Path
import pytest
from config import EventConfig, Ticker, load_event


def test_load_iran_war_event():
    cfg = load_event("iran_war")
    assert isinstance(cfg, EventConfig)
    assert cfg.name == "iran_war"
    assert cfg.start_date == date(2026, 2, 28)
    assert cfg.baseline_date == date(2026, 2, 27)
    assert "Hormuz" in cfg.seed_keywords
    symbols = [t.symbol for t in cfg.tickers]
    assert "BZ=F" in symbols and "^GSPC" in symbols
    assert len(cfg.tickers) == 11


def test_load_event_missing_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_event("no_such_event")


def test_baseline_before_start():
    with pytest.raises(ValueError, match="baseline_date must be before start_date"):
        EventConfig(
            name="x", display_name="x",
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 10),
            baseline_date=date(2026, 1, 2),
            seed_keywords=["x"],
            tickers=[Ticker(category="c", name="n", symbol="s")],
            rss_feeds=[],
        )
