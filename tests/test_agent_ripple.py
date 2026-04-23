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
