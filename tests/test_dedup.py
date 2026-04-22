from data_news.dedup import deduplicate


def test_dedup_by_url():
    articles = [
        {"url": "https://a.com/1", "headline": "Iran oil", "snippet": "", "date": "2026-03-01"},
        {"url": "https://a.com/1", "headline": "Iran oil", "snippet": "", "date": "2026-03-01"},
        {"url": "https://a.com/2", "headline": "Different", "snippet": "", "date": "2026-03-01"},
    ]
    result = deduplicate(articles)
    assert len(result) == 2
    urls = [a["url"] for a in result]
    assert urls == ["https://a.com/1", "https://a.com/2"]


def test_dedup_by_minhash_near_duplicate():
    articles = [
        {"url": "https://a.com/1",
         "headline": "Iran closes Strait of Hormuz as conflict escalates",
         "snippet": "Oil prices surged after the closure was announced overnight",
         "date": "2026-03-01"},
        {"url": "https://b.com/1",
         "headline": "Iran closes Strait of Hormuz as conflict escalates",
         "snippet": "Oil prices surged after the closure was announced overnight",
         "date": "2026-03-01"},
        {"url": "https://c.com/1",
         "headline": "Totally different unrelated article about sports",
         "snippet": "Basketball game coverage from last night",
         "date": "2026-03-01"},
    ]
    result = deduplicate(articles, minhash_threshold=0.9)
    assert len(result) == 2
    headlines = [a["headline"] for a in result]
    assert "Basketball game" in " ".join(headlines) or "sports" in " ".join(headlines).lower()
