# tests/test_gdelt.py
import json
from datetime import date
import pytest
from data_news import gdelt
from config import load_event


def test_fetch_gdelt_returns_normalized_articles(monkeypatch, fixtures_dir):
    captured = {}

    class FakeGdeltDoc:
        def article_search(self, filters):
            captured["filters"] = filters
            payload = json.loads((fixtures_dir / "gdelt_response.json").read_text())
            import pandas as pd
            return pd.DataFrame(payload["articles"])

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())

    cfg = load_event("iran_war")
    articles = gdelt.fetch(cfg)

    assert len(articles) == 2
    a = articles[0]
    assert a["url"] == "https://example.com/iran-hormuz-closure"
    assert a["headline"].startswith("Iran closes")
    assert a["source"] == "example.com"
    assert a["date"] == "2026-02-28"
    assert a["source_kind"] == "gdelt"
    # Filters must include seed keywords and the event date range.
    # gdeltdoc.Filters stashes everything into query_params, not named attrs.
    f = captured["filters"]
    qp = " ".join(f.query_params)
    assert "Hormuz" in qp
    assert "startdatetime=20260228" in qp
    assert "enddatetime=20260416" in qp


def test_fetch_gdelt_empty_result(monkeypatch):
    class FakeGdeltDoc:
        def article_search(self, filters):
            import pandas as pd
            return pd.DataFrame()

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())
    cfg = load_event("iran_war")
    assert gdelt.fetch(cfg) == []
