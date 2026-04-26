from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import EventConfig
from data_market import get_price_range
from data_news import retrieve
from ui.price_chart import significant_moves, _PRIMARY_SYMBOL


# Event-defining language gets a keyword bonus over pure cosine score.
_CAUSAL_KEYWORDS = [
    "closed", "closure", "closes", "declare", "declared", "announce",
    "announces", "shut", "shuts", "attack", "strike", "bomb", "seizure",
    "sanction", "sanctions", "embargo", "ceasefire", "agreement", "talks",
    "treaty", "invasion", "airstrike", "missile",
]


def pick_headline_for_date(hits: List[Dict], target_iso: str) -> Optional[Dict]:
    """Pick the most event-defining headline for target_iso from hits.

    Ranks by: (1) matches target date exactly, then (2) count of causal
    keywords in headline+text, then (3) score. Ties broken by score."""
    same_day = [h for h in hits if (h.get("metadata") or {}).get("date", "") == target_iso]
    if not same_day:
        return None

    def _score(h: Dict) -> tuple[int, float]:
        blob = (h.get("headline", "") + " " + h.get("text", "")).lower()
        kw_count = sum(1 for k in _CAUSAL_KEYWORDS if k in blob)
        return (kw_count, float(h.get("score", 0.0)))

    return max(same_day, key=_score)


@st.cache_data(show_spinner=False, ttl=3600)
def _headline_for(date_iso: str, _cfg_name: str) -> Optional[Dict]:
    """Pull 30 event-scoped hits, filter to target date, pick best headline.
    _cfg_name is accepted as part of the cache key so multi-event sessions
    don't share cached headlines — even though it's unused in the body."""
    hits = retrieve(f"event news {date_iso}", top_k=30)
    return pick_headline_for_date(hits, date_iso)


def _build_figure(dates_with_headlines: List[Dict], window_start: date, window_end: date) -> go.Figure:
    xs = [pd.Timestamp(d["date"]) for d in dates_with_headlines]
    ys = [1] * len(xs)  # constant y — axis is horizontal
    labels = [d["label"] for d in dates_with_headlines]
    hovers = [d["hover"] for d in dates_with_headlines]
    colors = ["#d32f2f" if d["direction"] == "up" else "#2e7d32"
              for d in dates_with_headlines]

    fig = go.Figure()
    # Full-window baseline axis
    fig.add_trace(go.Scatter(
        x=[pd.Timestamp(window_start), pd.Timestamp(window_end)], y=[1, 1],
        mode="lines", line=dict(color="#bbbbbb", width=2),
        hoverinfo="skip", showlegend=False,
    ))
    # Markers with above-axis text labels
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=labels, textposition="top center",
        marker=dict(color=colors, size=14, line=dict(color="white", width=1.5)),
        hovertext=hovers, hoverinfo="text",
        textfont=dict(size=11),
        showlegend=False,
    ))
    fig.update_layout(
        title="Event narrative axis — markers coupled to price movement days",
        height=260,
        margin=dict(l=40, r=40, t=60, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(visible=False, range=[0, 2]),
    )
    return fig


def _truncate(s: str, n: int = 60) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Event narrative")
    prices = get_price_range(_PRIMARY_SYMBOL, cfg.baseline_date, as_of)
    if prices.empty:
        st.warning(f"No price data for {_PRIMARY_SYMBOL}.")
        return
    moves = significant_moves(prices)
    if not moves:
        st.info("No significant-move days to annotate.")
        return

    annotated: List[Dict] = []
    for m in moves:
        h = _headline_for(m["date"], cfg.name)
        if h is None:
            label = "(no coverage)"
            hover = f"{m['date']}  {m['pct_change']:+.2f}%<br>No headline matched this date."
        else:
            label = _truncate(h.get("headline", ""), 40)
            hover = (f"{m['date']}  {m['pct_change']:+.2f}%<br>"
                     f"<b>{h.get('headline','')}</b><br>"
                     f"<span>{(h.get('text','') or '')[:200]}</span>")
        annotated.append({
            "date": m["date"], "direction": m["direction"],
            "label": label, "hover": hover,
        })

    fig = _build_figure(annotated, window_start=cfg.baseline_date, window_end=as_of)
    st.plotly_chart(fig, use_container_width=True)
