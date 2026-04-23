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
