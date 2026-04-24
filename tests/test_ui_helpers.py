from datetime import date
import pytest
from config import load_event


def test_timeline_renderable_structure(monkeypatch):
    from ui import timeline
    monkeypatch.setattr(timeline, "run_supervisor", lambda cfg, query, as_of: {
        "timeline": [
            {"date": "2026-02-28", "headline": "Iran closes Hormuz", "impact_summary": "Oil transit halted."},
            {"date": "2026-03-01", "headline": "Brent tops $100", "impact_summary": "Crude +35%."},
        ]
    })
    items = timeline.fetch_timeline(load_event("iran_war"), date(2026, 4, 15))
    assert len(items) == 2
    assert items[0]["date"] == "2026-02-28"

    assert timeline.classify_severity("Oil transit halted.") in {"critical", "significant", "moderate"}


def test_ripple_tree_to_graph_elements():
    from ui import ripple
    tree = {
        "event": "Hormuz",
        "nodes": [
            {"sector": "Oil", "mechanism": "m1", "severity": "critical",
             "price_change": 49.6, "supporting_news": [{"url": "u", "headline": "h", "date": "2026-03-01"}],
             "children": [
                 {"sector": "Fertilizer", "mechanism": "m2", "severity": "significant",
                  "price_change": 15.0, "supporting_news": [], "children": []},
             ]},
            {"sector": "Defense", "mechanism": "m3", "severity": "moderate",
             "price_change": 8.0, "supporting_news": [], "children": []},
        ],
    }
    nodes, edges = ripple.tree_to_graph_elements(tree)
    assert len(nodes) == 4
    assert len(edges) == 3
    labels = [n.label for n in nodes]
    assert "Oil" in " ".join(labels) and "Fertilizer" in " ".join(labels) and "Defense" in " ".join(labels)
    non_root = [n for n in nodes if n.id != "root"]
    assert all(n.color for n in non_root)
