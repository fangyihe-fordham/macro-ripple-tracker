from data_news.dedup import deduplicate


def test_dedup_by_url():
    articles = [
        {"url": "https://a.com/1", "headline": "Iran oil", "snippet": "", "date": "2026-03-01"},
        {"url": "https://a.com/1", "headline": "Iran oil", "snippet": "", "date": "2026-03-01"},
        {"url": "https://a.com/2", "headline": "Different", "snippet": "", "date": "2026-03-01"},
    ]
    kept, stats = deduplicate(articles)
    assert len(kept) == 2
    urls = [a["url"] for a in kept]
    assert urls == ["https://a.com/1", "https://a.com/2"]
    assert stats == {"input": 3, "url_dropped": 1, "minhash_dropped": 0, "kept": 2}


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
    kept, stats = deduplicate(articles, minhash_threshold=0.9)
    assert len(kept) == 2
    headlines = [a["headline"] for a in kept]
    assert "Basketball game" in " ".join(headlines) or "sports" in " ".join(headlines).lower()
    assert stats["input"] == 3
    assert stats["url_dropped"] == 0
    assert stats["minhash_dropped"] == 1
    assert stats["kept"] == 2
