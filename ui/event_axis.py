from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import EventConfig
from data_market import get_price_range
from data_news import retrieve
from ui.price_chart import significant_moves, _PRIMARY_SYMBOL, _UP_COLOR, _DOWN_COLOR


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


_LABEL_Y_ABOVE = 1.55
_LABEL_Y_BELOW = 0.45


def _label_y_for_index(i: int) -> tuple[float, str]:
    """Return (y_position, yanchor) for the i-th marker label."""
    if i % 2 == 0:
        return (_LABEL_Y_ABOVE, "bottom")
    return (_LABEL_Y_BELOW, "top")


def _build_figure(dates_with_headlines: List[Dict], window_start: date, window_end: date) -> go.Figure:
    fig = go.Figure()

    fig.add_shape(
        type="line",
        x0=pd.Timestamp(window_start),
        x1=pd.Timestamp(window_end),
        y0=1,
        y1=1,
        line=dict(color="#bbbbbb", width=2),
    )

    xs: List[pd.Timestamp] = []
    ys: List[float] = []
    colors: List[str] = []
    hovers: List[str] = []

    for i, item in enumerate(dates_with_headlines):
        x = pd.Timestamp(item["date"])
        color = _UP_COLOR if item["direction"] == "up" else _DOWN_COLOR
        label_y, yanchor = _label_y_for_index(i)

        fig.add_shape(
            type="line",
            x0=x,
            x1=x,
            y0=1,
            y1=label_y,
            line=dict(color=color, width=1.2),
            opacity=0.6,
        )
        fig.add_annotation(
            x=x,
            y=label_y,
            text=_truncate(item["label"], 28),
            showarrow=False,
            xanchor="center",
            yanchor=yanchor,
            font=dict(size=10, color="#222"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=color,
            borderwidth=1,
            borderpad=4,
        )

        xs.append(x)
        ys.append(1)
        colors.append(color)
        hovers.append(item["hover"])

    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="markers",
        marker=dict(color=colors, size=14, line=dict(color="white", width=1.5)),
        hovertext=hovers,
        hoverinfo="text",
        showlegend=False,
    ))
    fig.update_layout(
        title=dict(text="Event narrative axis", font=dict(size=14)),
        height=320,
        margin=dict(l=40, r=40, t=50, b=20),
        xaxis=dict(
            showgrid=False,
            range=[pd.Timestamp(window_start), pd.Timestamp(window_end)],
        ),
        yaxis=dict(visible=False, range=[0, 2]),
        showlegend=False,
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
    # KNOWN GAP (deferred to Task 8 integration): we use the module-default
    # threshold here, NOT the user-tuned slider value from price_chart.render().
    # If the user drags the Viz-1 slider to e.g. 7%, Viz-1 shows fewer markers
    # while Viz-2 still uses 3%. Fixing requires plumbing the slider value
    # through st.session_state, which the Task-8 shell rewrite can decide.
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
