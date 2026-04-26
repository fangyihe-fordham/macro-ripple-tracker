from datetime import date
from typing import Dict, List, Optional

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

    If the baseline date isn't in the index, fall back to the first row."""
    if prices.empty:
        return prices
    bts = pd.Timestamp(baseline)
    base_price = prices.loc[bts] if bts in prices.index else prices.iloc[0]
    return ((prices / base_price) - 1.0) * 100.0


def build_figure(prices: pd.Series, moves: List[Dict], y_mode: str, title: str) -> go.Figure:
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
            ys = [float(prices.loc[x] / prices.iloc[0] * 100.0 - 100.0) for x in xs]
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

    event = st.plotly_chart(
        fig, use_container_width=True,
        on_select="rerun", selection_mode="points",
        key="price_chart_select",
    )

    # Streamlit 1.39 returns a dict-like object with .selection.points when
    # on_select="rerun". Only markers (trace name == "markers") carry
    # customdata=[ISO date]; line-point clicks have None customdata and we ignore.
    if event and getattr(event, "selection", None):
        pts = event.selection.get("points", []) if isinstance(event.selection, dict) \
              else getattr(event.selection, "points", [])
        for p in pts:
            cd = p.get("customdata") if isinstance(p, dict) else getattr(p, "customdata", None)
            if cd:
                # customdata may be a list (one-element) or a scalar depending on plotly version
                iso = cd[0] if isinstance(cd, list) else cd
                st.session_state["selected_date"] = iso
                break

    # Render the currently-selected date below the chart as a breadcrumb.
    sel = st.session_state.get("selected_date")
    if sel:
        st.caption(f"Selected: **{sel}** — see detail panel →")
    else:
        st.caption("Click a marker to explain that day's move.")
