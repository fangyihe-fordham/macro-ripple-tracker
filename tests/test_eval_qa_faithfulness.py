from datetime import date

from config import load_event
from eval import qa_faithfulness


class _FakeLLM:
    def __init__(self, replies):
        self._replies = list(replies)

    def invoke(self, messages):
        return type("Resp", (), {"content": self._replies.pop(0)})()


def test_split_sentences():
    text = "Brent hit $111. Oil supply tightened. Fertilizer rose 15%."
    assert qa_faithfulness.split_sentences(text) == [
        "Brent hit $111.",
        "Oil supply tightened.",
        "Fertilizer rose 15%.",
    ]


def test_faithfulness_per_sentence(monkeypatch):
    monkeypatch.setattr(qa_faithfulness, "run_supervisor", lambda cfg, q, as_of: {
        "intent": "qa",
        "response": {
            "answer": "Brent rose. Shipping fell.",
            "citations": [{"url": "u", "headline": "h", "date": "2026-03-01"}],
        },
        "news_results": [{
            "text": "Brent surged on Hormuz.",
            "url": "u",
            "headline": "Brent surged",
            "metadata": {"date": "2026-03-01"},
            "score": 0.9,
        }],
    })
    monkeypatch.setattr(qa_faithfulness, "get_chat_model",
                        lambda **kw: _FakeLLM(["yes", "no"]))

    report = qa_faithfulness.score_query(
        {"id": "q1", "query": "What happened?"},
        load_event("iran_war"),
        date(2026, 4, 15),
    )
    assert report["supported_sentences"] == 1
    assert report["total_sentences"] == 2
    assert report["faithfulness"] == 0.5
