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
