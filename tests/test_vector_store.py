import pytest
from data_news import vector_store


@pytest.fixture
def sample_articles():
    return [
        {"url": "https://a.com/oil",  "headline": "Brent crude jumps as Iran closes Hormuz",
         "source": "a.com", "date": "2026-03-01",
         "snippet": "Oil prices surged above $100 as Iran shut the Strait of Hormuz.",
         "full_text": "", "source_kind": "gdelt"},
        {"url": "https://b.com/ag",   "headline": "Fertilizer costs climb on natural gas spike",
         "source": "b.com", "date": "2026-03-05",
         "snippet": "Ammonia producers face higher input costs as natural gas rallies.",
         "full_text": "", "source_kind": "gdelt"},
        {"url": "https://c.com/def",  "headline": "Defense stocks rally on Middle East tensions",
         "source": "c.com", "date": "2026-03-02",
         "snippet": "Lockheed, Raytheon, Northrop rose sharply.",
         "full_text": "", "source_kind": "rss"},
    ]


def test_index_and_retrieve(tmp_data_dir, sample_articles):
    vector_store.reset()
    vector_store.index_articles(sample_articles)
    hits = vector_store.retrieve("How did oil prices move after Hormuz closed?", top_k=2)
    assert len(hits) == 2
    top = hits[0]
    assert top["url"] == "https://a.com/oil"
    assert "metadata" in top
    assert top["metadata"]["source_kind"] == "gdelt"
    assert "score" in top


def test_retrieve_empty_when_no_index(tmp_data_dir):
    vector_store.reset()
    assert vector_store.retrieve("anything", top_k=3) == []
