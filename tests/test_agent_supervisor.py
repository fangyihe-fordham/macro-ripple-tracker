import json
import pytest
from langchain_core.messages import AIMessage
import agent_supervisor
from config import load_event


class _FakeLLM:
    def __init__(self, replies):
        self._replies = list(replies)
    def invoke(self, messages):
        return AIMessage(content=self._replies.pop(0))


def test_classify_intent_all_examples(monkeypatch, fixtures_dir):
    examples = json.loads((fixtures_dir / "intent_examples.json").read_text())
    replies = [json.dumps({"intent": intent, "focus": focus})
               for _, intent, focus in examples]
    fake = _FakeLLM(replies)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: fake)

    for query, expected_intent, expected_focus in examples:
        state = {"query": query}
        out = agent_supervisor.classify_intent(state)
        assert out["intent"] == expected_intent
        assert out["focus"] == expected_focus


def test_classify_intent_defaults_to_qa_on_garbage(monkeypatch):
    monkeypatch.setattr(agent_supervisor, "get_chat_model",
                        lambda **kw: _FakeLLM([json.dumps({"intent": "gibberish", "focus": ""})]))
    out = agent_supervisor.classify_intent({"query": "???"})
    assert out["intent"] == "qa"
    assert out["focus"] == ""


def test_classify_intent_malformed_json_falls_back_to_qa_empty_focus(monkeypatch):
    monkeypatch.setattr(agent_supervisor, "get_chat_model",
                        lambda **kw: _FakeLLM(["not json at all"]))
    out = agent_supervisor.classify_intent({"query": "???"})
    assert out["intent"] == "qa"
    assert out["focus"] == ""


def test_classify_intent_returns_qa_when_json_is_list(monkeypatch):
    """Valid JSON but wrong shape (list instead of object) must not raise
    AttributeError on .get() — degrade gracefully to qa/empty."""
    monkeypatch.setattr(agent_supervisor, "get_chat_model",
                        lambda **kw: _FakeLLM([json.dumps(["timeline"])]))
    out = agent_supervisor.classify_intent({"query": "???"})
    assert out["intent"] == "qa"
    assert out["focus"] == ""


def test_classify_intent_returns_qa_when_json_is_scalar(monkeypatch):
    """Valid JSON scalar (string) must not raise — degrade to qa/empty."""
    monkeypatch.setattr(agent_supervisor, "get_chat_model",
                        lambda **kw: _FakeLLM([json.dumps("timeline")]))
    out = agent_supervisor.classify_intent({"query": "???"})
    assert out["intent"] == "qa"
    assert out["focus"] == ""


def test_run_market_agent_returns_dict(monkeypatch):
    fake_changes = {
        "BZ=F": {"available": True, "baseline": 74.20, "latest": 111.00, "pct_change": 49.60},
        "XLE":  {"available": True, "baseline": 95.00, "latest": 118.00, "pct_change": 24.21},
    }
    monkeypatch.setattr(agent_supervisor, "get_price_changes",
                        lambda cfg, as_of: fake_changes)
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "how did oil move?", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_market_agent(state)
    assert out["market_data"] == fake_changes


def test_run_ripple_agent_uses_focus(monkeypatch):
    """When state["focus"] is populated, it becomes the event_description
    passed to generate_ripple_tree — NOT the raw user query (which may
    contain imperative prefixes like "Show me the ripple tree for...")."""
    called = {}
    def fake_generate(event_description, cfg, as_of, max_depth=3, news_top_k=3):
        called["args"] = (event_description, cfg.name, as_of, max_depth)
        return {"event": event_description, "nodes": []}
    monkeypatch.setattr(agent_supervisor, "generate_ripple_tree", fake_generate)

    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "Show me the ripple tree for Hormuz closure",
             "focus": "Hormuz closure",
             "cfg": cfg,
             "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_ripple_agent(state)
    assert called["args"][0] == "Hormuz closure"
    assert called["args"][1] == "iran_war"
    assert out["ripple_tree"]["event"] == "Hormuz closure"


def test_run_ripple_agent_falls_back_to_display_name(monkeypatch):
    """When focus is empty or missing, fall back to cfg.display_name."""
    called = {}
    def fake_generate(event_description, cfg, as_of, max_depth=3, news_top_k=3):
        called["args"] = (event_description,)
        return {"event": event_description, "nodes": []}
    monkeypatch.setattr(agent_supervisor, "generate_ripple_tree", fake_generate)

    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "What industries are affected and why?",
             "focus": "",
             "cfg": cfg,
             "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_ripple_agent(state)
    assert called["args"][0] == cfg.display_name
    assert out["ripple_tree"]["event"] == cfg.display_name


def test_run_news_agent_produces_timeline(monkeypatch):
    fake_hits = [
        {"text": "Iran closed Strait", "url": "u1", "headline": "Iran closes Hormuz",
         "metadata": {"date": "2026-02-28"}, "score": 0.9},
        {"text": "oil jumps", "url": "u2", "headline": "Brent tops $100",
         "metadata": {"date": "2026-03-01"}, "score": 0.85},
    ]
    monkeypatch.setattr(agent_supervisor, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM([
        json.dumps([
            {"date": "2026-02-28", "headline": "Iran closes Hormuz",
             "impact_summary": "Seaborne oil transit halted."},
            {"date": "2026-03-01", "headline": "Brent tops $100",
             "impact_summary": "Crude spikes ~35% in 24h."},
        ])
    ]))
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "Timeline of key events", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_news_agent(state)
    assert len(out["timeline"]) == 2
    assert out["timeline"][0]["date"] == "2026-02-28"
    assert "news_results" in out
    assert len(out["news_results"]) == 2


def test_run_news_agent_falls_back_on_wrong_shape_json(monkeypatch):
    """Valid JSON but not a list-of-dicts (e.g. dict or list-of-strings) must
    degrade to timeline=[]; otherwise Plan-3 UI would see malformed state."""
    fake_hits = [
        {"text": "Iran closed Strait", "url": "u1", "headline": "Iran closes Hormuz",
         "metadata": {"date": "2026-02-28"}, "score": 0.9},
    ]
    monkeypatch.setattr(agent_supervisor, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM([
        json.dumps({"not": "a list"})
    ]))
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "Timeline of key events", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_news_agent(state)
    assert out["timeline"] == []
    assert len(out["news_results"]) == 1


def test_run_qa_agent_falls_back_on_wrong_shape_json(monkeypatch):
    """Valid JSON but not a dict with an 'answer' key must degrade to the
    raw-text fallback — otherwise Plan-3 UI sees a list where it expects a dict."""
    fake_hits = [
        {"text": "Brent rose to $111 on 2026-03-04", "url": "u1",
         "headline": "Brent hits 111", "metadata": {"date": "2026-03-04"}, "score": 0.9},
    ]
    monkeypatch.setattr(agent_supervisor, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM([
        json.dumps(["citation1", "citation2"])
    ]))
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "How high?", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_qa_agent(state)
    assert isinstance(out["response"], dict)
    assert "answer" in out["response"]
    assert out["response"]["citations"] == []


def test_run_qa_agent_grounded_answer(monkeypatch):
    fake_hits = [
        {"text": "Brent rose to $111 on 2026-03-04", "url": "u1",
         "headline": "Brent hits 111", "metadata": {"date": "2026-03-04"}, "score": 0.9},
    ]
    monkeypatch.setattr(agent_supervisor, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM([
        json.dumps({"answer": "Brent hit $111 on March 4.",
                    "citations": [{"url": "u1", "headline": "Brent hits 111", "date": "2026-03-04"}]})
    ]))
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "How high did Brent go?", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_qa_agent(state)
    assert out["response"]["answer"].startswith("Brent hit $111")
    assert out["response"]["citations"][0]["url"] == "u1"
    assert len(out["news_results"]) == 1


def test_build_graph_routes_by_intent(monkeypatch, fixtures_dir):
    monkeypatch.setattr(agent_supervisor, "classify_intent",
                        lambda s: {"intent": "market"})
    monkeypatch.setattr(agent_supervisor, "run_market_agent",
                        lambda s: {"market_data": {"BZ=F": {"pct_change": 49.6}}})
    monkeypatch.setattr(agent_supervisor, "run_ripple_agent",
                        lambda s: {"ripple_tree": {"touched": True}})
    monkeypatch.setattr(agent_supervisor, "run_news_agent",
                        lambda s: {"timeline": [{"touched": True}]})
    monkeypatch.setattr(agent_supervisor, "run_qa_agent",
                        lambda s: {"response": {"touched": True}})

    app = agent_supervisor.build_graph()
    cfg = load_event("iran_war")
    from datetime import date
    final = app.invoke({"query": "how did oil move?", "cfg": cfg, "as_of": date(2026, 4, 15)})
    assert final["intent"] == "market"
    assert "market_data" in final
    assert "ripple_tree" not in final
    assert "timeline" not in final


def test_run_end_to_end_helper(monkeypatch):
    monkeypatch.setattr(agent_supervisor, "classify_intent",
                        lambda s: {"intent": "qa"})
    monkeypatch.setattr(agent_supervisor, "run_qa_agent",
                        lambda s: {"response": {"answer": "ok", "citations": []}})
    cfg = load_event("iran_war")
    from datetime import date
    out = agent_supervisor.run(cfg, "what happened?", as_of=date(2026, 4, 15))
    assert out["intent"] == "qa"
    assert out["response"]["answer"] == "ok"


def test_run_ripple_agent_falls_back_when_generate_raises(monkeypatch):
    """generate_ripple_tree raising should NOT bubble out of run_ripple_agent —
    UI renders an empty tree with a warning instead of crashing the whole page."""

    def _boom(*a, **kw):
        raise ValueError("simulated LLM JSON parse failure")

    monkeypatch.setattr(agent_supervisor, "generate_ripple_tree", _boom)
    state = {"query": "ripple please", "cfg": object(), "as_of": object(),
             "focus": "Hormuz closure"}
    out = agent_supervisor.run_ripple_agent(state)
    assert out == {"ripple_tree": {"event": "Hormuz closure", "nodes": []}}
