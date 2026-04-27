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


def test_build_figure_pct_mode_markers_use_pct_values():
    """pct-mode markers must use the already-converted % values directly,
    not re-divide by iloc[0] (which is 0.0 in a pct series → inf)."""
    from ui import price_chart
    import math
    idx = pd.to_datetime(["2026-02-27", "2026-03-02", "2026-03-03"])
    pct_series = pd.Series([0.0, 7.26, 12.31], index=idx)
    moves = [
        {"date": "2026-03-02", "pct_change": 7.26, "price": 77.74, "direction": "up"},
        {"date": "2026-03-03", "pct_change": 4.71, "price": 81.40, "direction": "up"},
    ]
    fig = price_chart.build_figure(pct_series, moves, y_mode="pct", title="x")
    markers = next(t for t in fig.data if t.name == "markers")
    # Each marker y must be finite and equal to the pct_series value at that date
    ys = list(markers.y)
    assert all(math.isfinite(v) for v in ys), f"non-finite marker y values: {ys}"
    assert ys[0] == pytest.approx(7.26)
    assert ys[1] == pytest.approx(12.31)


def test_click_event_to_selected_date_uses_marker_pointindex():
    """plotly_events returns a list of dicts with curveNumber + pointIndex.
    Marker trace is curveNumber=1; line trace is curveNumber=0. We must only
    set selected_date on a marker click, and use pointIndex to look up the
    date from the moves list."""
    from ui import price_chart

    moves = [
        {"date": "2026-03-02", "pct_change": 7.26, "price": 77.74, "direction": "up"},
        {"date": "2026-03-12", "pct_change": 9.22, "price": 99.50, "direction": "up"},
    ]

    events = [{"x": "2026-03-12", "y": 99.5, "curveNumber": 1, "pointIndex": 1, "pointNumber": 1}]
    iso = price_chart._click_event_to_iso(events, moves)
    assert iso == "2026-03-12"

    events = [{"x": "2026-03-12", "y": 99.5, "curveNumber": 0, "pointIndex": 5, "pointNumber": 5}]
    assert price_chart._click_event_to_iso(events, moves) is None

    assert price_chart._click_event_to_iso([], moves) is None

    events = [{"x": "x", "y": 0, "curveNumber": 1, "pointIndex": 99, "pointNumber": 99}]
    assert price_chart._click_event_to_iso(events, moves) is None


def test_format_detail_markdown_renders_all_sections():
    from ui import price_detail_panel as pdp
    attribution = {
        "direction": "up",
        "headline_summary": "Brent rallied on Hormuz closure.",
        "key_drivers": ["Strait of Hormuz closed", "Speculative long flows"],
        "caveats": ["SUMED pipeline partial bypass available."],
        "supporting_news": [
            {"url": "https://x/1", "headline": "Brent hits $88", "date": "2026-03-02"},
            {"url": "https://x/2", "headline": "Oil analysts revise", "date": "2026-03-02"},
        ],
    }
    md = pdp.format_detail_markdown(attribution, target_date="2026-03-02",
                                    symbol="BZ=F", pct_change=7.26)
    assert "2026-03-02" in md
    assert "▲" in md or "up" in md.lower()
    assert "Brent rallied" in md
    assert "Strait of Hormuz closed" in md
    assert "SUMED" in md
    assert "https://x/1" in md and "https://x/2" in md


def test_format_detail_markdown_down_arrow_for_negative():
    from ui import price_detail_panel as pdp
    attribution = {
        "direction": "down", "headline_summary": "Oil fell on diplomacy.",
        "key_drivers": ["US-Iran talks resumed"],
        "caveats": [],
        "supporting_news": [],
    }
    md = pdp.format_detail_markdown(attribution, target_date="2026-04-14",
                                    symbol="BZ=F", pct_change=-3.1)
    assert "▼" in md or "down" in md.lower()
    assert "-3.1" in md or "−3.1" in md


def test_pick_headline_for_date_prefers_causal_keywords():
    from ui import event_axis
    target = "2026-03-02"
    hits = [
        {"headline": "Analyst view: oil still volatile", "text": "...",
         "metadata": {"date": "2026-03-02"}, "score": 0.4},
        {"headline": "Iran declares Strait of Hormuz closed",
         "text": "Iran announced the immediate closure...",
         "metadata": {"date": "2026-03-02"}, "score": 0.9},
        {"headline": "Brent traders react",
         "text": "Trading volumes spiked...",
         "metadata": {"date": "2026-03-02"}, "score": 0.6},
    ]
    h = event_axis.pick_headline_for_date(hits, target)
    assert "Hormuz" in h["headline"]  # causal keyword wins over score


def test_pick_headline_for_date_returns_none_when_no_match():
    from ui import event_axis
    hits = [{"headline": "x", "text": "x", "metadata": {"date": "2026-02-15"}, "score": 0.5}]
    assert event_axis.pick_headline_for_date(hits, "2026-03-02") is None


def test_event_axis_label_y_alternates_above_below():
    from ui import event_axis

    above = event_axis._label_y_for_index(0)
    below = event_axis._label_y_for_index(1)
    above2 = event_axis._label_y_for_index(2)

    assert above[0] > 1.0
    assert below[0] < 1.0
    assert above2[0] == above[0]
    assert above[1] == "bottom"
    assert below[1] == "top"


def test_event_axis_build_figure_pins_full_window_range():
    from ui import event_axis

    annotated = [
        {
            "date": "2026-03-05",
            "direction": "up",
            "label": "Oil jumps on closure",
            "hover": "x",
        },
        {
            "date": "2026-03-12",
            "direction": "down",
            "label": "Talks cool prices",
            "hover": "y",
        },
    ]

    fig = event_axis._build_figure(
        annotated,
        window_start=date(2026, 2, 27),
        window_end=date(2026, 4, 15),
    )

    assert fig.layout.xaxis.range[0] == pd.Timestamp("2026-02-27")
    assert fig.layout.xaxis.range[1] == pd.Timestamp("2026-04-15")


def test_format_supervisor_result_qa_has_citations():
    from ui import sidebar_chat
    result = {
        "intent": "qa",
        "response": {
            "answer": "Brent rose on Hormuz closure.",
            "citations": [{"url": "https://x/1", "headline": "Brent hits 88", "date": "2026-03-02"}],
        },
    }
    md = sidebar_chat.format_supervisor_result(result)
    assert "Brent rose" in md
    assert "Brent hits 88" in md
    assert "https://x/1" in md


def test_format_supervisor_result_market_shows_deltas():
    from ui import sidebar_chat
    result = {
        "intent": "market",
        "market_data": {
            "BZ=F": {"available": True, "baseline": 72.48, "latest": 99.39, "pct_change": 37.12},
            "NG=F": {"available": False, "baseline": None, "latest": None, "pct_change": None},
        },
    }
    md = sidebar_chat.format_supervisor_result(result)
    assert "BZ=F" in md
    assert "37.1" in md
    assert "N/A" in md or "unavailable" in md.lower() or "NG=F" not in md


def test_format_supervisor_result_timeline_bulleted():
    from ui import sidebar_chat
    result = {
        "intent": "timeline",
        "timeline": [
            {"date": "2026-03-01", "headline": "Iran closes Hormuz", "impact_summary": "Oil up."},
        ],
    }
    md = sidebar_chat.format_supervisor_result(result)
    assert "2026-03-01" in md
    assert "Iran closes Hormuz" in md


def test_ripple_label_truncates_long_sectors():
    from ui import ripple
    long_sector = {"sector": "This Is A Very Very Very Long Sector Name",
                   "severity": "critical", "price_change": 10.0}
    lbl = ripple._label(long_sector)
    assert len(lbl) <= 21  # 20 chars + optional ellipsis
    assert "…" in lbl or lbl.endswith("…")
    # percentage no longer in label
    assert "%" not in lbl


def test_ripple_label_short_sector_unchanged_no_pct():
    from ui import ripple
    n = {"sector": "Oil Supply", "severity": "significant", "price_change": 49.6}
    assert ripple._label(n) == "Oil Supply"  # price change moved to tooltip


def test_ripple_node_size_scales_with_severity():
    from ui import ripple
    tree = {"event": "E", "nodes": [
        {"sector": "A", "severity": "critical", "price_change": 10, "children": []},
        {"sector": "B", "severity": "significant", "price_change": 5, "children": []},
        {"sector": "C", "severity": "moderate", "price_change": 2, "children": []},
    ]}
    nodes, _ = ripple.tree_to_graph_elements(tree)
    by_label = {n.label: n for n in nodes}
    assert by_label["A"].size > by_label["B"].size > by_label["C"].size


def test_ripple_node_title_contains_mechanism_and_pct():
    from ui import ripple
    tree = {"event": "E", "nodes": [
        {"sector": "Oil", "mechanism": "Hormuz closure", "severity": "critical",
         "price_change": 49.6, "children": []},
    ]}
    nodes, _ = ripple.tree_to_graph_elements(tree)
    oil = next(n for n in nodes if n.id != "root")
    # Plotly/streamlit-agraph uses `title` for hover tooltip text
    assert "Hormuz closure" in oil.title
    assert "49" in oil.title  # percentage now in hover, not label
