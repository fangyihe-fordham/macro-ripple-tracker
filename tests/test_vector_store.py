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


def test_retrieve_surfaces_unexpected_errors_instead_of_silent_empty(
    tmp_data_dir, sample_articles, monkeypatch, capsys
):
    """C3 contract: a real misconfig (non-InvalidCollectionException) must NOT
    silently collapse to an empty result set — either raise or print."""
    # Seed a real collection first so the failure is on re-open, not first-create.
    vector_store.reset()
    vector_store.index_articles(sample_articles)

    # Now make re-opening the collection blow up. _embedder() is called eagerly
    # as get_collection's kwarg, so raising here lands inside _collection's try/except.
    def _broken_embedder():
        raise RuntimeError("embedder misconfigured")

    monkeypatch.setattr(vector_store, "_embedder", _broken_embedder)

    # Behavior: retrieve() returns [] (graceful degradation) AND prints a
    # clearly visible error so operators + LLM agents can tell "broken" from "no data".
    hits = vector_store.retrieve("anything", top_k=3)
    assert hits == []

    out = capsys.readouterr().out
    assert "[vector_store]" in out
    assert "unexpected error" in out
    assert "embedder misconfigured" in out


def test_index_ids_are_stable_across_runs(tmp_data_dir, sample_articles):
    """I5 contract: the same URL must get the same ChromaDB id on separate runs
    so that future incremental-reindex paths can dedupe. Python's salted hash()
    did not satisfy this."""
    vector_store.reset()
    vector_store.index_articles(sample_articles)
    first_ids = set(vector_store._collection(create=False).get()["ids"])

    vector_store.reset()
    vector_store.index_articles(sample_articles)
    second_ids = set(vector_store._collection(create=False).get()["ids"])

    assert first_ids == second_ids
    # Sanity: ids actually contain the sha1 slice, not salted integers.
    assert all("-" in i and len(i.rsplit("-", 1)[-1]) == 16 for i in first_ids)
