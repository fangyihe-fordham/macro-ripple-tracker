from datetime import date
import pytest
import pandas as pd


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


def test_significant_moves_filters_by_threshold():
    from ui import price_chart
    idx = pd.to_datetime(["2026-02-27", "2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05"])
    # pct: NaN, +7.3%, +4.7%, -2.0%, +5.0%
    prices = pd.Series([72.48, 77.74, 81.40, 79.78, 83.76], index=idx)
    moves = price_chart.significant_moves(prices, threshold_pct=3.0)
    # 03-02 (+7.3%), 03-03 (+4.7%), 03-05 (+5.0%) qualify; 03-04 (-2.0%) does not
    dates = [m["date"] for m in moves]
    assert "2026-03-02" in dates
    assert "2026-03-03" in dates
    assert "2026-03-05" in dates
    assert "2026-03-04" not in dates
    # up/down direction
    m_0302 = next(m for m in moves if m["date"] == "2026-03-02")
    assert m_0302["direction"] == "up"
    assert m_0302["pct_change"] > 0


def test_significant_moves_empty_for_flat_series():
    from ui import price_chart
    idx = pd.to_datetime(["2026-02-27", "2026-02-28", "2026-03-01"])
    prices = pd.Series([100.0, 100.5, 101.0], index=idx)  # all <1%
    moves = price_chart.significant_moves(prices, threshold_pct=3.0)
    assert moves == []


def test_to_pct_series_is_change_vs_baseline():
    from ui import price_chart
    idx = pd.to_datetime(["2026-02-27", "2026-03-01", "2026-03-02"])
    prices = pd.Series([100.0, 110.0, 90.0], index=idx)
    pct = price_chart.to_pct_series(prices, baseline=date(2026, 2, 27))
    assert pct.iloc[0] == pytest.approx(0.0)
    assert pct.iloc[1] == pytest.approx(10.0)  # +10%
    assert pct.iloc[2] == pytest.approx(-10.0)  # -10%


def test_build_figure_has_line_and_marker_traces():
    from ui import price_chart
    idx = pd.to_datetime(["2026-02-27", "2026-03-02", "2026-03-03"])
    prices = pd.Series([72.48, 77.74, 81.40], index=idx)
    moves = price_chart.significant_moves(prices, threshold_pct=3.0)
    fig = price_chart.build_figure(prices, moves, y_mode="price", title="Brent Crude Oil (BZ=F)")
    # One line trace + one markers trace (even if markers is empty)
    trace_names = [t.name for t in fig.data]
    assert "price" in trace_names or "% vs baseline" in trace_names
    assert "markers" in trace_names
    # Red-up, green-down color encoding present in marker colors
    markers_trace = next(t for t in fig.data if t.name == "markers")
    # colors array should be same length as markers' x
    if len(markers_trace.x) > 0:
        assert len(markers_trace.marker.color) == len(markers_trace.x)
