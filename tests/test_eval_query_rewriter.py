from langchain_core.messages import AIMessage

from config import load_event
from eval import query_rewriter


class _FakeLLM:
    def __init__(self, replies):
        self._replies = list(replies)

    def invoke(self, messages):
        return AIMessage(content=self._replies.pop(0))


def test_rewrite_returns_llm_response_stripped(monkeypatch):
    cfg = load_event("iran_war")
    fake = _FakeLLM(["Brent crude oil price spike Hormuz closure 2026"])
    monkeypatch.setattr(query_rewriter, "get_chat_model", lambda **kw: fake)

    out = query_rewriter.rewrite("How high did Brent go?", cfg)

    assert out == "Brent crude oil price spike Hormuz closure 2026"


def test_rewrite_strips_wrapping_quotes_from_llm_response(monkeypatch):
    cfg = load_event("iran_war")
    fake = _FakeLLM(['"oil price after Hormuz"'])
    monkeypatch.setattr(query_rewriter, "get_chat_model", lambda **kw: fake)

    out = query_rewriter.rewrite("Why oil up?", cfg)

    assert out == "oil price after Hormuz"


def test_rewrite_falls_back_to_original_on_empty_response(monkeypatch):
    cfg = load_event("iran_war")
    fake = _FakeLLM(["   "])
    monkeypatch.setattr(query_rewriter, "get_chat_model", lambda **kw: fake)

    out = query_rewriter.rewrite("Why oil up?", cfg)

    assert out == "Why oil up?"
