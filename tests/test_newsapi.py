import json

from data_news import newsapi_fetcher
from config import load_event


def test_fetch_newsapi_returns_normalized(monkeypatch, fixtures_dir):
    monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")
    payload = json.loads((fixtures_dir / "newsapi_response.json").read_text())
    captured = {}

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key

        def get_everything(self, q, from_param, to, language, page_size, page):
            captured.setdefault("calls", []).append(
                {"q": q, "from": from_param, "to": to, "page": page}
            )
            return payload

    monkeypatch.setattr(newsapi_fetcher, "NewsApiClient", FakeClient)
    cfg = load_event("iran_war")
    articles = newsapi_fetcher.fetch(cfg, max_pages=1)

    assert captured["api_key"] == "dummy-key"
    assert len(articles) == 2
    assert articles[0]["source"] == "Reuters"
    assert articles[0]["snippet"] == "Brent crude surged above $100 on Monday."
    assert articles[0]["date"] == "2026-03-01"
    assert articles[0]["source_kind"] == "newsapi"


def test_fetch_newsapi_no_key_returns_empty(monkeypatch):
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    cfg = load_event("iran_war")
    assert newsapi_fetcher.fetch(cfg) == []
