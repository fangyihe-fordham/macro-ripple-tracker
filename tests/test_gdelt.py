import json
import math

import pandas as pd

from data_news import gdelt
from config import load_event


def _expected_chunk_count(cfg) -> int:
    days = (cfg.end_date - cfg.start_date).days
    return math.ceil(days / gdelt._CHUNK_DAYS)


def test_fetch_gdelt_returns_normalized_articles(monkeypatch, fixtures_dir):
    captured = {"filters_list": []}
    payload = json.loads((fixtures_dir / "gdelt_response.json").read_text())

    class FakeGdeltDoc:
        def article_search(self, filters):
            captured["filters_list"].append(filters)
            if len(captured["filters_list"]) == 1:
                return pd.DataFrame(payload["articles"])
            return pd.DataFrame()

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())
    monkeypatch.setattr(gdelt.time, "sleep", lambda s: None)

    cfg = load_event("iran_war")
    articles = gdelt.fetch(cfg)

    assert len(captured["filters_list"]) == _expected_chunk_count(cfg)

    assert len(articles) == 2
    a = articles[0]
    assert a["url"] == "https://example.com/iran-hormuz-closure"
    assert a["headline"].startswith("Iran closes")
    assert a["source"] == "example.com"
    assert a["date"] == "2026-02-28"
    assert a["source_kind"] == "gdelt"

    first_qp = " ".join(captured["filters_list"][0].query_params)
    last_qp = " ".join(captured["filters_list"][-1].query_params)
    assert "Hormuz" in first_qp
    assert f"startdatetime={cfg.start_date.strftime('%Y%m%d')}" in first_qp
    assert f"enddatetime={cfg.end_date.strftime('%Y%m%d')}" in last_qp


def test_fetch_gdelt_empty_result(monkeypatch):
    class FakeGdeltDoc:
        def article_search(self, filters):
            return pd.DataFrame()

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())
    monkeypatch.setattr(gdelt.time, "sleep", lambda s: None)
    cfg = load_event("iran_war")
    assert gdelt.fetch(cfg) == []


def test_fetch_gdelt_chunk_failure_does_not_kill_pipeline(monkeypatch, fixtures_dir):
    payload = json.loads((fixtures_dir / "gdelt_response.json").read_text())
    call_log = []

    class FakeGdeltDoc:
        def article_search(self, filters):
            call_log.append(filters)
            if len(call_log) == 2:
                raise RuntimeError("simulated GDELT outage")
            if len(call_log) == 1:
                return pd.DataFrame(payload["articles"])
            return pd.DataFrame()

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())
    monkeypatch.setattr(gdelt.time, "sleep", lambda s: None)

    cfg = load_event("iran_war")
    articles = gdelt.fetch(cfg)

    assert len(call_log) == _expected_chunk_count(cfg)
    assert len(articles) == 2


def test_fetch_gdelt_rate_limit_retries_with_exponential_backoff(monkeypatch, fixtures_dir):
    payload = json.loads((fixtures_dir / "gdelt_response.json").read_text())
    call_log = []
    sleeps = []

    class FakeGdeltDoc:
        def article_search(self, filters):
            call_log.append(filters)
            if len(call_log) <= 2:
                raise RuntimeError("Please limit requests to one every 5 seconds")
            return pd.DataFrame(payload["articles"])

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())
    monkeypatch.setattr(gdelt.time, "sleep", lambda seconds: sleeps.append(seconds))

    cfg = load_event("iran_war")
    articles = gdelt.fetch(cfg)

    assert sleeps[:2] == [
        gdelt._RATE_LIMIT_RETRY_BASE_SECONDS,
        gdelt._RATE_LIMIT_RETRY_BASE_SECONDS * 2,
    ]
    assert len(call_log) == _expected_chunk_count(cfg) + 2
    assert len(articles) == 2 * _expected_chunk_count(cfg)
