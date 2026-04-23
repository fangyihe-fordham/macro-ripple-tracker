"""Hits real Anthropic API. Run with: RUN_LIVE=1 pytest tests/test_live_agents.py -v"""
import os
from datetime import date
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1",
    reason="Live integration test. Set RUN_LIVE=1 to enable.",
)


def test_classify_intent_live():
    from config import load_event
    import agent_supervisor
    out = agent_supervisor.classify_intent({"query": "How did oil price react to Iran war?"})
    assert out["intent"] in {"timeline", "market", "ripple", "qa"}


def test_ripple_tree_live():
    """Requires setup.py to have populated the news + price stores."""
    from config import load_event
    from agent_ripple import generate_ripple_tree
    cfg = load_event("iran_war")
    tree = generate_ripple_tree(
        "Strait of Hormuz closed, blocking ~25% of seaborne oil",
        cfg, as_of=cfg.end_date, max_depth=2,
    )
    assert tree["event"]
    assert len(tree["nodes"]) >= 2
    for n in tree["nodes"]:
        assert "supporting_news" in n
