import json
from datetime import date

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


class _FixedDate(date):
    @classmethod
    def today(cls):
        return date(2026, 4, 22)


def test_fetch_newsapi_clamps_start_to_30_day_window(monkeypatch):
    """Free tier rejects queries older than ~30 days; fetcher must clamp from_param."""
    monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")
    monkeypatch.setattr(newsapi_fetcher, "date", _FixedDate)
    captured = {}

    class FakeClient:
        def __init__(self, api_key):
            pass

        def get_everything(self, q, from_param, to, language, page_size, page):
            captured["from"] = from_param
            captured["to"] = to
            return {"articles": []}

    monkeypatch.setattr(newsapi_fetcher, "NewsApiClient", FakeClient)
    cfg = load_event("iran_war")  # start=2026-02-28, end=2026-04-16
    newsapi_fetcher.fetch(cfg, max_pages=1)

    # today=2026-04-22, earliest=today-29d=2026-03-24; cfg.start_date predates it → clamped
    assert captured["from"] == "2026-03-24"
    # cfg.end_date 2026-04-16 is inside the window → not clamped
    assert captured["to"] == "2026-04-16"


def test_fetch_newsapi_skips_when_window_entirely_before_free_tier(monkeypatch):
    """If event ended before the 30-day window, short-circuit without calling the client."""
    monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")

    class _FarFuture(date):
        @classmethod
        def today(cls):
            return date(2027, 1, 1)

    monkeypatch.setattr(newsapi_fetcher, "date", _FarFuture)
    called = {"count": 0}

    class FakeClient:
        def __init__(self, api_key):
            pass

        def get_everything(self, **kwargs):
            called["count"] += 1
            return {"articles": []}

    monkeypatch.setattr(newsapi_fetcher, "NewsApiClient", FakeClient)
    cfg = load_event("iran_war")
    assert newsapi_fetcher.fetch(cfg) == []
    assert called["count"] == 0
