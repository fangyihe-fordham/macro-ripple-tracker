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
