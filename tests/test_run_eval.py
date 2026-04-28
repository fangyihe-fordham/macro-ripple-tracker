from pathlib import Path

from eval import run_eval


def test_run_eval_writes_report(monkeypatch, tmp_path):
    monkeypatch.setattr(run_eval, "run_retrieval_eval",
                        lambda qs, cfg=None, k=5, use_rewriter=False: {
                            "metric": "precision@5", "mean_precision": 0.8,
                            "use_rewriter": use_rewriter, "per_query": []})
    monkeypatch.setattr(run_eval, "run_qa_eval",
                        lambda qs, cfg, as_of: {"metric": "faithfulness", "mean": 0.9, "per_query": []})
    monkeypatch.setattr(run_eval, "score",
                        lambda tree, truth: {"ai_sectors": [], "truth_sectors": [],
                                             "matched": [], "missed": [], "hallucinated": [],
                                             "precision": 0.75, "recall": 0.85})
    monkeypatch.setattr(run_eval, "check_price_integrity",
                        lambda tree, actual, tolerance=0.5: {"ok_count": 5, "mismatch_count": 0,
                                                             "mismatches": [], "ok": []})
    monkeypatch.setattr(run_eval, "run_market_integrity",
                        lambda pairs: {"metric": "market_integrity", "ok_count": 5,
                                       "missing_count": 0, "results": []})
    monkeypatch.setattr(run_eval, "generate_ripple_tree",
                        lambda event_description, cfg, as_of, max_depth=3: {"event": "x", "nodes": []})
    monkeypatch.setattr(run_eval, "get_price_changes",
                        lambda cfg, as_of: {})

    out_dir = tmp_path / "eval_out"
    report_path = run_eval.main(["--event", "iran_war", "--out-dir", str(out_dir)])
    report_file = Path(report_path)

    assert report_file.exists()
    body = report_file.read_text()
    assert "# Evaluation Report" in body
    assert "precision@5" in body
    assert "0.80" in body or "0.8" in body
    assert "faithfulness" in body
