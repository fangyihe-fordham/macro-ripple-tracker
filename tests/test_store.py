from data_news import store


def test_write_and_read_articles_roundtrip(tmp_data_dir):
    articles = [
        {"url": "https://a.com/1", "headline": "h1", "source": "a.com",
         "date": "2026-03-01", "snippet": "s1", "full_text": "", "source_kind": "gdelt"},
        {"url": "https://b.com/1", "headline": "h2", "source": "b.com",
         "date": "2026-03-02", "snippet": "s2", "full_text": "", "source_kind": "rss"},
    ]
    store.write_articles(articles)
    loaded = store.read_articles()
    assert loaded == articles


def test_read_articles_missing_returns_empty(tmp_data_dir):
    assert store.read_articles() == []
