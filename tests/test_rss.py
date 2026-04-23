import feedparser
from data_news import rss
from config import load_event


def test_fetch_rss_filters_by_keywords(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "rss_sample.xml").read_text()
    parsed = feedparser.parse(raw)
    monkeypatch.setattr(rss, "_parse_feed", lambda url: parsed)

    cfg = load_event("iran_war")
    # iran_war.yaml disables RSS in production (deprecated feeds); inject a
    # synthetic feed URL here so rss.fetch has something to iterate over.
    cfg.rss_feeds = ["https://example.com/feed.xml"]
    articles = rss.fetch(cfg)

    kept_urls = {a["url"] for a in articles}
    assert "https://example.com/rss-1" in kept_urls
    assert "https://example.com/rss-3" in kept_urls
    assert "https://example.com/rss-2" not in kept_urls
    for a in articles:
        assert a["source_kind"] == "rss"
        assert a["date"].startswith("2026-")
        # Snippets must be plain text: no HTML tags, entities decoded.
        assert "<" not in a["snippet"] and ">" not in a["snippet"]
        assert "&amp;" not in a["snippet"] and "&nbsp;" not in a["snippet"]

    rss3 = next(a for a in articles if a["url"] == "https://example.com/rss-3")
    assert "Vessels diverting around the strait." in rss3["snippet"]
    assert "Read more" in rss3["snippet"]
