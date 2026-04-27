from datetime import date
from typing import Dict, List, Literal, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import EventConfig
from data_market import get_price_range


_PRIMARY_SYMBOL = "BZ=F"
_PRIMARY_NAME = "Brent Crude Oil"
_DEFAULT_THRESHOLD_PCT = 3.0
_UP_COLOR = "#d32f2f"   # red — up moves on oil are bad-news-y for demand
_DOWN_COLOR = "#2e7d32"  # green
_LINE_COLOR = "#1976d2"
_MARKERS_CURVE_INDEX = 1  # 0=line trace, 1=markers trace (build_figure adds them in this order)


def significant_moves(prices: pd.Series, threshold_pct: float = _DEFAULT_THRESHOLD_PCT) -> List[Dict]:
    """Return days where |daily pct_change| > threshold_pct.

    Each item: {date: ISO str, pct_change: float, price: float, direction: 'up'|'down'}.
    Uses calendar-adjacent rows in the series (skips weekends/holidays implicitly
    since the series only contains trading days)."""
    if prices.empty or len(prices) < 2:
        return []
    pct = prices.pct_change() * 100.0
    flagged = pct[pct.abs() > threshold_pct]
    out: List[Dict] = []
    for ts, p in flagged.items():
        out.append({
            "date": ts.strftime("%Y-%m-%d"),
            "pct_change": float(p),
            "price": float(prices.loc[ts]),
            "direction": "up" if p > 0 else "down",
        })
    return out


def to_pct_series(prices: pd.Series, baseline: date) -> pd.Series:
    """Convert a price series to % change relative to baseline-date price.

    If the baseline date isn't in the index, fall back to the first row and
    print a one-line warning so the operator notices an inaccurate anchor."""
    if prices.empty:
        return prices
    bts = pd.Timestamp(baseline)
    if bts in prices.index:
        base_price = prices.loc[bts]
    else:
        base_price = prices.iloc[0]
        print(f"[price_chart] baseline {baseline} not in price index; "
              f"using earliest available {prices.index[0].date()} as baseline anchor")
    return ((prices / base_price) - 1.0) * 100.0


def build_figure(prices: pd.Series, moves: List[Dict],
                 y_mode: Literal["price", "pct"], title: str) -> go.Figure:
    """y_mode: 'price' | 'pct'. Returns a Plotly figure with two traces:
    'price' or '% vs baseline' (line), and 'markers' (colored dots)."""
    fig = go.Figure()
    y = prices.values
    y_label = "Close ($)" if y_mode == "price" else "% vs Baseline"
    line_name = "price" if y_mode == "price" else "% vs baseline"

    fig.add_trace(go.Scatter(
        x=prices.index, y=y, mode="lines", name=line_name,
        line=dict(color=_LINE_COLOR, width=2),
        hovertemplate="%{x|%Y-%m-%d}<br>" + y_label + ": %{y:.2f}<extra></extra>",
    ))

    # Markers trace. Y-values aligned to the current y_mode.
    if moves:
        xs = [pd.Timestamp(m["date"]) for m in moves]
        if y_mode == "price":
            ys = [m["price"] for m in moves]
        else:
            # In pct mode, `prices` is the already-converted % series
            # (to_pct_series called by render() before reaching here).
            # iloc[0] is exactly 0.0 by construction, so re-dividing by it
            # would produce inf. Use the % values directly.
            ys = [float(prices.loc[x]) for x in xs]
        colors = [_UP_COLOR if m["direction"] == "up" else _DOWN_COLOR for m in moves]
        hover = [f"{m['date']}  {m['pct_change']:+.2f}%<br>(click for details)" for m in moves]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name="markers",
            marker=dict(color=colors, size=12, line=dict(color="white", width=1.5)),
            hovertext=hover, hoverinfo="text",
            # customdata lets Streamlit's on_select return the date back to us
            customdata=[m["date"] for m in moves],
        ))
    else:
        # Empty-markers trace keeps the on_select hookup stable
        fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="markers",
                                 marker=dict(color=[])))

    fig.update_layout(
        title=title,
        height=420,
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis_title="", yaxis_title=y_label,
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def _click_event_to_iso(events: list, moves: List[Dict]) -> Optional[str]:
    """Map a plotly_events click result to an ISO date string."""
    if not events:
        return None
    event = events[0]
    if event.get("curveNumber") != _MARKERS_CURVE_INDEX:
        return None
    idx = event.get("pointIndex")
    if not isinstance(idx, int) or idx < 0 or idx >= len(moves):
        return None
    return moves[idx]["date"]


# Leading _ on _cfg: @st.cache_data cannot hash pydantic v2 EventConfig.
# Same workaround as ui.ripple.fetch_tree.
@st.cache_data(show_spinner=False, ttl=3600)
def _load_prices(_cfg: EventConfig, as_of: date) -> pd.Series:
    return get_price_range(_PRIMARY_SYMBOL, _cfg.baseline_date, as_of)


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader(f"{_PRIMARY_NAME} ({_PRIMARY_SYMBOL})")

    col_toggle, col_thresh = st.columns([1, 1])
    with col_toggle:
        y_mode_label = st.radio("Y-axis",
                                options=["$ Price", "% Change vs Baseline"],
                                horizontal=True, label_visibility="collapsed")
    with col_thresh:
        thresh = st.slider("Significant-move threshold (|%|)",
                           min_value=1.0, max_value=10.0, value=_DEFAULT_THRESHOLD_PCT,
                           step=0.5)
    y_mode = "price" if y_mode_label == "$ Price" else "pct"

    prices = _load_prices(cfg, as_of)
    if prices.empty:
        st.warning(f"No price data for {_PRIMARY_SYMBOL}. Run `python setup.py --event {cfg.name}`.")
        return

    if y_mode == "pct":
        series_for_chart = to_pct_series(prices, cfg.baseline_date)
    else:
        series_for_chart = prices

    moves = significant_moves(prices, threshold_pct=thresh)
    fig = build_figure(series_for_chart, moves, y_mode, title="")

    # Use streamlit-plotly-events for real click-on-marker behavior.
    # Streamlit's native st.plotly_chart(on_select=...) only fires when the
    # user activates the box/lasso-select tool from the modebar.
    from streamlit_plotly_events import plotly_events

    click_events = plotly_events(
        fig,
        click_event=True,
        select_event=False,
        hover_event=False,
        override_height=420,
        key="price_chart_clicks",
    )
    iso = _click_event_to_iso(click_events, moves)
    if iso is not None:
        st.session_state["selected_date"] = iso

    # Render the currently-selected date below the chart as a breadcrumb.
    sel = st.session_state.get("selected_date")
    if sel:
        st.caption(f"Selected: **{sel}** — see detail panel →")
    else:
        st.caption("Click a marker to explain that day's move.")
