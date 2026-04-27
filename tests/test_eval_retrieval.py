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
