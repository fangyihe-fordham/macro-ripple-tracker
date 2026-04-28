from config import load_event
from eval import retrieval


def test_precision_at_k_scores_hits(monkeypatch):
    fake_hits = [
        {"text": "t", "url": f"u{i}", "headline": "h", "metadata": {}, "score": 0.9}
        for i in range(5)
    ]
    judgments = iter([True, True, False, True, True])

    monkeypatch.setattr(retrieval, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(retrieval, "judge_relevance",
                        lambda query, keywords, snippet: next(judgments))

    q = {"id": "r1", "query": "How high did Brent go?", "must_be_about": ["Brent", "oil"]}
    score = retrieval.precision_at_k(q, k=5)

    assert score["precision"] == 0.8
    assert score["relevant"] == 4
    assert score["retrieved"] == 5


def test_run_retrieval_eval_all(monkeypatch):
    monkeypatch.setattr(retrieval, "retrieve", lambda q, top_k: [
        {"text": "t", "url": "u", "headline": "h", "metadata": {}, "score": 0.9}
    ])
    monkeypatch.setattr(retrieval, "judge_relevance",
                        lambda query, keywords, snippet: True)

    queries = [{"id": f"r{i}", "query": "q", "must_be_about": ["x"]} for i in range(5)]
    report = retrieval.run_retrieval_eval(queries, k=1)

    assert report["mean_precision"] == 1.0
    assert len(report["per_query"]) == 5


def test_precision_at_k_uses_rewriter_when_flag_set(monkeypatch):
    captured_queries = []

    def fake_retrieve(q, top_k):
        captured_queries.append(q)
        return []

    monkeypatch.setattr(retrieval, "retrieve", fake_retrieve)
    monkeypatch.setattr(retrieval, "rewrite", lambda query, cfg: f"REWRITTEN[{query}]")
    monkeypatch.setattr(retrieval, "judge_relevance", lambda *a, **kw: True)

    q = {"id": "r1", "query": "Why oil up?", "must_be_about": ["oil"]}
    cfg = load_event("iran_war")
    score = retrieval.precision_at_k(q, cfg=cfg, k=5, use_rewriter=True)

    assert captured_queries == ["REWRITTEN[Why oil up?]"]
    assert score["rewritten_query"] == "REWRITTEN[Why oil up?]"
    assert score["query"] == "Why oil up?"


def test_precision_at_k_does_not_call_rewriter_by_default(monkeypatch):
    captured_queries = []

    def fake_retrieve(q, top_k):
        captured_queries.append(q)
        return []

    monkeypatch.setattr(retrieval, "retrieve", fake_retrieve)
    monkeypatch.setattr(retrieval, "judge_relevance", lambda *a, **kw: True)

    q = {"id": "r1", "query": "Why oil up?", "must_be_about": ["oil"]}
    score = retrieval.precision_at_k(q, k=5)

    assert captured_queries == ["Why oil up?"]
    assert score.get("rewritten_query") is None
