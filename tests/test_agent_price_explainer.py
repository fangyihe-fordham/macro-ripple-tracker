from datetime import date
import json

from langchain_core.messages import AIMessage

import agent_price_explainer as ape


class _FakeLLM:
    def __init__(self, replies):
        self._r = list(replies)
    def invoke(self, msgs):
        return AIMessage(content=self._r.pop(0))


_SAMPLE_HITS = [
    {"url": "https://x/1", "headline": "Brent hits $88 as Hormuz closes",
     "text": "Iran's closure of the Strait of Hormuz pushed Brent crude higher...",
     "metadata": {"date": "2026-03-02"}, "score": 0.82},
    {"url": "https://x/2", "headline": "Oil traders eye pipeline alternatives",
     "text": "Analysts discuss SUMED and East-West pipeline capacity...",
     "metadata": {"date": "2026-03-01"}, "score": 0.71},
    {"url": "https://x/3", "headline": "Hedge funds pile into long oil calls",
     "text": "CFTC data shows record speculative length...",
     "metadata": {"date": "2026-03-02"}, "score": 0.63},
    {"url": "https://x/4", "headline": "Unrelated: EU sugar quotas",
     "text": "Brussels discusses sugar trade...",
     "metadata": {"date": "2026-02-15"}, "score": 0.31},
]


def test_filter_hits_by_date_proximity_keeps_close_dates():
    target = date(2026, 3, 2)
    close = ape._filter_by_date(_SAMPLE_HITS, target, window_days=2)
    urls = [h["url"] for h in close]
    assert "https://x/1" in urls  # 2026-03-02, +0d
    assert "https://x/2" in urls  # 2026-03-01, -1d
    assert "https://x/3" in urls  # 2026-03-02, +0d
    assert "https://x/4" not in urls  # 2026-02-15, -15d


def test_happy_path_returns_structured_attribution(monkeypatch):
    canned = {
        "direction": "up",
        "headline_summary": "Brent rallied as Iran closed Hormuz.",
        "key_drivers": ["Hormuz closure", "Speculative flows"],
        "caveats": ["SUMED pipeline offers partial bypass."],
        "supporting_news": [
            {"url": "https://x/1", "headline": "Brent hits $88 as Hormuz closes", "date": "2026-03-02"},
            {"url": "https://x/3", "headline": "Hedge funds pile into long oil calls", "date": "2026-03-02"},
        ],
    }
    monkeypatch.setattr(ape, "retrieve", lambda q, top_k: _SAMPLE_HITS)
    monkeypatch.setattr(ape, "get_chat_model", lambda **kw: _FakeLLM([json.dumps(canned)]))

    out = ape.explain_move(
        target_date=date(2026, 3, 2),
        symbol="BZ=F",
        name="Brent Crude Oil",
        pct_change=7.26,
        price_from=72.48,
        price_to=77.74,
    )
    assert out["direction"] == "up"
    assert "Hormuz" in out["headline_summary"]
    assert len(out["key_drivers"]) == 2
    assert len(out["supporting_news"]) == 2
    assert out["supporting_news"][0]["url"] == "https://x/1"


def test_malformed_json_falls_back_with_raw_news(monkeypatch):
    monkeypatch.setattr(ape, "retrieve", lambda q, top_k: _SAMPLE_HITS)
    monkeypatch.setattr(ape, "get_chat_model", lambda **kw: _FakeLLM(["NOT JSON"]))

    out = ape.explain_move(
        target_date=date(2026, 3, 2), symbol="BZ=F", name="Brent Crude Oil",
        pct_change=7.26, price_from=72.48, price_to=77.74,
    )
    assert out["direction"] == "up"  # inferred from positive pct_change
    assert out["headline_summary"].startswith("Price moved")
    # Fallback populates supporting_news from raw retrieved hits (proximity-sorted)
    assert len(out["supporting_news"]) <= 3
    assert out["supporting_news"][0]["url"] in {"https://x/1", "https://x/3"}  # same-day hits


def test_wrong_shape_json_falls_back(monkeypatch):
    # valid JSON, but an ARRAY instead of an OBJECT — triggers isinstance gate
    monkeypatch.setattr(ape, "retrieve", lambda q, top_k: _SAMPLE_HITS)
    monkeypatch.setattr(ape, "get_chat_model",
                        lambda **kw: _FakeLLM([json.dumps(["not", "an", "object"])]))

    out = ape.explain_move(
        target_date=date(2026, 3, 2), symbol="BZ=F", name="Brent Crude Oil",
        pct_change=-4.2, price_from=80.0, price_to=76.64,
    )
    assert out["direction"] == "down"  # inferred from negative pct_change
    assert "key_drivers" in out and "supporting_news" in out
    # Fallback should populate supporting_news from same-day close hits
    # (https://x/1 and https://x/3 are both 2026-03-02 in _SAMPLE_HITS).
    assert len(out["supporting_news"]) > 0
    assert out["supporting_news"][0]["url"] in {"https://x/1", "https://x/3"}


def test_missing_required_keys_falls_back(monkeypatch):
    """Valid dict missing one or more required keys must trigger fallback."""
    monkeypatch.setattr(ape, "retrieve", lambda q, top_k: _SAMPLE_HITS)
    monkeypatch.setattr(
        ape, "get_chat_model",
        lambda **kw: _FakeLLM([json.dumps({"direction": "up",
                                           "headline_summary": "x"})]),
    )
    out = ape.explain_move(
        target_date=date(2026, 3, 2), symbol="BZ=F", name="Brent Crude Oil",
        pct_change=2.0, price_from=75.0, price_to=76.5,
    )
    # Fell back: direction inferred from pct_change; supporting_news populated
    # from close hits (since _SAMPLE_HITS has same-day matches for 2026-03-02).
    assert out["direction"] == "up"
    assert out["headline_summary"].startswith("Price moved")
    assert "key_drivers" in out and "caveats" in out
    assert len(out["supporting_news"]) > 0
    assert len(out["supporting_news"]) <= 3


def test_empty_retrieval_returns_graceful_no_news(monkeypatch):
    monkeypatch.setattr(ape, "retrieve", lambda q, top_k: [])
    # LLM should NOT be called if there are no hits
    monkeypatch.setattr(ape, "get_chat_model", lambda **kw: (_ for _ in ()).throw(
        AssertionError("LLM should not be invoked on empty retrieval")))

    out = ape.explain_move(
        target_date=date(2026, 3, 2), symbol="BZ=F", name="Brent Crude Oil",
        pct_change=0.1, price_from=80.0, price_to=80.08,
    )
    assert out["direction"] == "flat"
    assert out["supporting_news"] == []
    # On empty retrieval, _fallback returns empty drivers and caveats too —
    # confirm a future change doesn't accidentally start populating them.
    assert out["key_drivers"] == []
    assert out["caveats"] == []
    assert "No indexed" in out["headline_summary"] or "thin" in out["headline_summary"].lower()
