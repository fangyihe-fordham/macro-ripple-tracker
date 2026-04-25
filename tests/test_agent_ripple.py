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


def test_attach_prices_uses_ticker_hints(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    tree = json.loads(raw)

    fake_changes = {
        "BZ=F": {"available": True, "baseline": 74.20, "latest": 111.00, "pct_change": 49.60},
        "CL=F": {"available": True, "baseline": 70.00, "latest": 100.00, "pct_change": 42.86},
        "XLE":  {"available": True, "baseline": 95.00, "latest": 118.00, "pct_change": 24.21},
        "CF":   {"available": True, "baseline": 80.00, "latest": 92.00,  "pct_change": 15.00},
        "NG=F": {"available": True, "baseline": 3.00,  "latest": 4.50,   "pct_change": 50.00},
        "BOAT": {"available": True, "baseline": 25.00, "latest": 27.00,  "pct_change": 8.00},
        "ITA":  {"available": True, "baseline": 150.0, "latest": 162.0,  "pct_change": 8.00},
    }
    monkeypatch.setattr(agent_ripple, "get_price_changes",
                        lambda cfg, as_of: fake_changes)

    cfg = load_event("iran_war")
    from datetime import date
    enriched = agent_ripple.attach_prices(tree, cfg, as_of=date(2026, 4, 15))

    oil = enriched["nodes"][0]
    assert oil["price_change"] == pytest.approx(49.60)
    assert oil["price_details"][0]["symbol"] in ("BZ=F", "CL=F", "XLE")
    airline = oil["children"][1]
    assert airline["price_change"] is None


def test_generate_structure_raises_on_wrong_shape_json(monkeypatch):
    """An LLM that returns valid JSON of the wrong shape (list, scalar, etc.)
    must raise ValueError so run_ripple_agent's fallback fires correctly."""
    import json as _json
    monkeypatch.setattr(agent_ripple, "get_chat_model",
                        lambda **kw: _FakeLLM(_json.dumps([{"sector": "Oil"}])))
    cfg = load_event("iran_war")
    with pytest.raises(ValueError, match="wrong shape"):
        agent_ripple.generate_structure("Fake event", cfg, max_depth=2)


def test_generate_ripple_tree_end_to_end(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    monkeypatch.setattr(agent_ripple, "get_chat_model", lambda **kw: _FakeLLM(raw))
    monkeypatch.setattr(agent_ripple, "retrieve",
                        lambda q, top_k: [{"text": "x", "url": "u", "headline": "h",
                                           "metadata": {"date": "2026-03-01"}, "score": 0.8}])
    monkeypatch.setattr(agent_ripple, "get_price_changes",
                        lambda cfg, as_of: {"BZ=F": {"available": True, "baseline": 74.2, "latest": 111.0, "pct_change": 49.6}})

    cfg = load_event("iran_war")
    from datetime import date
    tree = agent_ripple.generate_ripple_tree(
        event_description="Strait of Hormuz closed",
        cfg=cfg,
        as_of=date(2026, 4, 15),
        max_depth=3,
    )
    assert tree["event"]
    oil = tree["nodes"][0]
    assert oil["supporting_news"][0]["url"] == "u"
    assert oil["price_change"] == pytest.approx(49.6)
