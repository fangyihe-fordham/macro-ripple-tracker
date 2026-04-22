import feedparser
from data_news import rss
from config import load_event


def test_fetch_rss_filters_by_keywords(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "rss_sample.xml").read_text()
    parsed = feedparser.parse(raw)
    monkeypatch.setattr(rss, "_parse_feed", lambda url: parsed)

    cfg = load_event("iran_war")
    articles = rss.fetch(cfg)

    kept_urls = {a["url"] for a in articles}
    assert "https://example.com/rss-1" in kept_urls
    assert "https://example.com/rss-3" in kept_urls
    assert "https://example.com/rss-2" not in kept_urls
    for a in articles:
        assert a["source_kind"] == "rss"
        assert a["date"].startswith("2026-")
