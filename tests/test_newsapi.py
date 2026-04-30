import json
from datetime import date, timedelta

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
    cfg = load_event("iran_war")
    newsapi_fetcher.fetch(cfg, max_pages=1)

    # today=2026-04-22, earliest = today - 29d = 2026-03-24.
    # `from` should be clamped up to 2026-03-24 if cfg.start_date predates it.
    expected_from = max(cfg.start_date, _FixedDate.today() - timedelta(days=29)).isoformat()
    # `to` should be clamped down to today if cfg.end_date is in the future.
    expected_to = min(cfg.end_date, _FixedDate.today()).isoformat()
    assert captured["from"] == expected_from
    assert captured["to"] == expected_to


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


def test_fetch_newsapi_preserves_page1_when_free_tier_cap_hits_on_page2(monkeypatch):
    """Free tier hard-caps at 100 total; page 2 raises NewsAPIException with
    code 'maximumResultsReached'. The fetcher must KEEP the 100 page-1
    articles — dropping them was a regression introduced with paging."""
    from newsapi.newsapi_exception import NewsAPIException

    monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")
    monkeypatch.setattr(newsapi_fetcher, "date", _FixedDate)

    def make_article(i):
        return {
            "url": f"https://x.com/{i}", "title": f"headline {i}",
            "source": {"name": "X"}, "publishedAt": "2026-04-01T00:00:00Z",
            "description": "", "content": "",
        }

    class FakeClient:
        def __init__(self, api_key):
            pass

        def get_everything(self, q, from_param, to, language, page_size, page):
            if page == 1:
                return {"totalResults": 464343,
                        "articles": [make_article(i) for i in range(100)]}
            raise NewsAPIException({
                "status": "error",
                "code": "maximumResultsReached",
                "message": "Developer accounts are limited to a max of 100 results.",
            })

    monkeypatch.setattr(newsapi_fetcher, "NewsApiClient", FakeClient)
    cfg = load_event("iran_war")
    articles = newsapi_fetcher.fetch(cfg, max_pages=5)

    # Page 1's 100 articles must survive the page-2 cap error.
    assert len(articles) == 100
    assert articles[0]["url"] == "https://x.com/0"
    assert articles[-1]["url"] == "https://x.com/99"


def test_fetch_newsapi_paginates_until_short_page(monkeypatch, capsys):
    """Pages 1+2 full (100 each) + page 3 partial (7) → fetcher stops after page 3."""
    monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")
    monkeypatch.setattr(newsapi_fetcher, "date", _FixedDate)

    def make_article(i):
        return {
            "url": f"https://x.com/{i}", "title": f"headline {i}",
            "source": {"name": "X"}, "publishedAt": "2026-04-01T00:00:00Z",
            "description": "", "content": "",
        }

    pages_seen: list[int] = []

    class FakeClient:
        def __init__(self, api_key):
            pass

        def get_everything(self, q, from_param, to, language, page_size, page):
            pages_seen.append(page)
            if page == 1:
                return {"totalResults": 207, "articles": [make_article(i) for i in range(100)]}
            if page == 2:
                return {"totalResults": 207, "articles": [make_article(100 + i) for i in range(100)]}
            if page == 3:
                return {"totalResults": 207, "articles": [make_article(200 + i) for i in range(7)]}
            raise AssertionError(f"unexpected page={page}")

    monkeypatch.setattr(newsapi_fetcher, "NewsApiClient", FakeClient)
    cfg = load_event("iran_war")
    articles = newsapi_fetcher.fetch(cfg, max_pages=5)

    # Stopped exactly after the short page, did not hit pages 4 or 5.
    assert pages_seen == [1, 2, 3]
    assert len(articles) == 207

    # totalResults log printed on the first page.
    out = capsys.readouterr().out
    assert "totalResults=207" in out
