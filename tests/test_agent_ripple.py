import json
from pathlib import Path
import pytest
from langchain_core.messages import AIMessage
import agent_ripple
from config import load_event


class _FakeLLM:
    """Minimal stand-in for ChatAnthropic: .invoke(messages) -> AIMessage."""
    def __init__(self, reply: str):
        self._reply = reply
    def invoke(self, messages):
        return AIMessage(content=self._reply)


def test_generate_tree_structure(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    monkeypatch.setattr(agent_ripple, "get_chat_model", lambda **kw: _FakeLLM(raw))
    cfg = load_event("iran_war")

    tree = agent_ripple.generate_structure(
        event_description="Strait of Hormuz closed, ~25% seaborne oil blocked",
        cfg=cfg,
        max_depth=3,
    )

    assert tree["event"] == "Strait of Hormuz closure"
    assert len(tree["nodes"]) == 3
    assert tree["nodes"][0]["sector"] == "Oil Supply"
    assert len(tree["nodes"][0]["children"]) == 2
    assert "BZ=F" in tree["nodes"][0]["ticker_hints"]


def test_generate_structure_rejects_malformed_json(monkeypatch):
    monkeypatch.setattr(agent_ripple, "get_chat_model",
                        lambda **kw: _FakeLLM("not json at all"))
    cfg = load_event("iran_war")
    with pytest.raises(ValueError, match="valid JSON"):
        agent_ripple.generate_structure("x", cfg, max_depth=2)


def test_generate_structure_strips_code_fences(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    wrapped = f"```json\n{raw}\n```"
    monkeypatch.setattr(agent_ripple, "get_chat_model", lambda **kw: _FakeLLM(wrapped))
    cfg = load_event("iran_war")
    tree = agent_ripple.generate_structure("x", cfg, max_depth=3)
    assert tree["event"] == "Strait of Hormuz closure"


def test_attach_news_calls_retrieve_per_node(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    tree = json.loads(raw)

    calls = []
    def fake_retrieve(query, top_k):
        calls.append((query, top_k))
        return [
            {"text": f"article for {query}", "url": f"https://x/{len(calls)}",
             "headline": f"headline {len(calls)}", "metadata": {"date": "2026-03-01"}, "score": 0.9},
        ]
    monkeypatch.setattr(agent_ripple, "retrieve", fake_retrieve)

    enriched = agent_ripple.attach_news(tree, top_k=2)

    def all_nodes(nodes):
        for n in nodes:
            yield n
            yield from all_nodes(n.get("children", []))

    nodes = list(all_nodes(enriched["nodes"]))
    assert len(nodes) == 5
    for n in nodes:
        assert "supporting_news" in n
        assert len(n["supporting_news"]) >= 1
        assert "url" in n["supporting_news"][0]
    assert any("Oil Supply" in q for q, _ in calls)
