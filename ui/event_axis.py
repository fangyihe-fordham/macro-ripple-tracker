from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage

from config import EventConfig
from data_market import get_price_range
from data_news import retrieve
from llm import get_chat_model, strip_fences
from ui.price_chart import significant_moves, _PRIMARY_SYMBOL, _UP_COLOR, _DOWN_COLOR


# Event-defining language gets a keyword bonus over pure cosine score.
_CAUSAL_KEYWORDS = [
    "closed", "closure", "closes", "declare", "declared", "announce",
    "announces", "shut", "shuts", "attack", "strike", "bomb", "seizure",
    "sanction", "sanctions", "embargo", "ceasefire", "agreement", "talks",
    "treaty", "invasion", "airstrike", "missile",
]
_TRANSLATE_SYSTEM = (
    "You translate financial/news headlines into concise natural English. "
    "If the headline is already English, return it unchanged. "
    "Return only the English headline text, with no quotes or commentary."
)
_LABEL_MAX_CHARS = 26
_LABEL_LANE_GAP_DAYS = 0.8
_LABEL_LANES = [
    (1.18, "bottom"),
    (0.82, "top"),
    (1.36, "bottom"),
    (0.64, "top"),
    (1.54, "bottom"),
    (0.46, "top"),
    (1.72, "bottom"),
    (0.28, "top"),
    (1.90, "bottom"),
    (0.10, "top"),
]
_SEVERITY_COLORS = {
    "critical": "#d32f2f",
    "significant": "#f57c00",
    "moderate": "#fbc02d",
}


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
def _headline_for(date_iso: str, event_hint: str) -> Optional[Dict]:
    """Pull 30 event-scoped hits, filter to target date, pick best headline."""
    hits = retrieve(f"{event_hint} {date_iso}", top_k=30)
    return pick_headline_for_date(hits, date_iso)


def _needs_english_translation(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    ascii_letters = [c for c in letters if c.isascii()]
    return (len(ascii_letters) / len(letters)) < 0.85


@st.cache_data(show_spinner=False, ttl=3600)
def _headline_to_english(headline: str) -> str:
    if not headline:
        return ""
    if not _needs_english_translation(headline):
        return headline
    try:
        llm = get_chat_model(temperature=0.0, max_tokens=64)
        resp = llm.invoke([
            SystemMessage(content=_TRANSLATE_SYSTEM),
            HumanMessage(content=headline),
        ])
        text = strip_fences(resp.content if isinstance(resp.content, str) else str(resp.content))
        return text.splitlines()[0].strip() or ""
    except Exception as exc:
        print(f"[event_axis] headline translation failed: {exc}")
        return ""


def _label_y_for_index(i: int) -> tuple[float, str]:
    """Return (y_position, yanchor) for the i-th label lane."""
    return _LABEL_LANES[i % len(_LABEL_LANES)]


def _estimate_label_span_days(label: str, total_span_days: int) -> float:
    chars = min(len(label), _LABEL_MAX_CHARS)
    return min(max(chars * 0.38, 2.2), max(3.0, total_span_days * 0.22))


def _assign_label_lanes(dates_with_headlines: List[Dict],
                        window_start: date,
                        window_end: date) -> List[Dict]:
    total_span_days = max((window_end - window_start).days, 1)
    lane_ends = [float("-inf")] * len(_LABEL_LANES)
    assigned: List[Dict] = []

    for item in dates_with_headlines:
        placed = dict(item)
        label = _truncate(item.get("label", ""), _LABEL_MAX_CHARS).strip()
        placed["label"] = label
        if not label:
            placed["show_label"] = False
            placed["label_y"] = 1.0
            placed["yanchor"] = "bottom"
            assigned.append(placed)
            continue

        x_ord = pd.Timestamp(item["date"]).to_pydatetime().date().toordinal()
        half_span = _estimate_label_span_days(label, total_span_days) / 2.0
        start = x_ord - half_span
        end = x_ord + half_span

        lane_idx = None
        for idx in range(len(_LABEL_LANES)):
            if start > lane_ends[idx] + _LABEL_LANE_GAP_DAYS:
                lane_idx = idx
                lane_ends[idx] = end
                break

        if lane_idx is None:
            placed["show_label"] = False
            placed["label_y"] = 1.0
            placed["yanchor"] = "bottom"
        else:
            label_y, yanchor = _label_y_for_index(lane_idx)
            placed["show_label"] = True
            placed["label_y"] = label_y
            placed["yanchor"] = yanchor
        assigned.append(placed)

    return assigned


def _build_figure(dates_with_headlines: List[Dict], window_start: date, window_end: date) -> go.Figure:
    fig = go.Figure()
    laid_out = _assign_label_lanes(dates_with_headlines, window_start, window_end)

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

    for item in laid_out:
        x = pd.Timestamp(item["date"])
        direction = item.get("direction", "up")
        color = item.get("color") or (_UP_COLOR if direction == "up" else _DOWN_COLOR)

        if item.get("show_label"):
            label_y = item["label_y"]
            yanchor = item["yanchor"]
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
                text=item["label"],
                showarrow=False,
                xanchor="center",
                yanchor=yanchor,
                font=dict(size=10, color="#222"),
                bgcolor="rgba(255,255,255,0.95)",
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
        height=460,
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


def _sector_to_annotated(sector: Dict) -> List[Dict]:
    """Convert a selected ripple node into the event-axis annotated shape."""
    severity = sector.get("severity", "moderate")
    color = _SEVERITY_COLORS.get(severity, "#9e9e9e")
    mechanism = sector.get("mechanism", "")
    annotated: List[Dict] = []

    hits = sector.get("supporting_news", []) or []
    for hit in sorted(hits, key=lambda item: item.get("date", "")):
        date_str = hit.get("date", "")
        if not date_str:
            continue
        headline = hit.get("headline", "")
        english_headline = _headline_to_english(headline) if headline else ""
        label = english_headline
        hover_bits = [f"<b>{sector.get('sector', '?')}</b> · {date_str}"]
        if mechanism:
            hover_bits.append(mechanism)
        hover_bits.append(english_headline or "English translation unavailable")
        annotated.append({
            "date": date_str,
            "label": label,
            "hover": "<br>".join(hover_bits),
            "color": color,
        })

    return annotated


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Event narrative")

    sector = st.session_state.get("selected_sector")
    if sector:
        col_label, col_back = st.columns([8, 2])
        with col_label:
            sev = sector.get("severity", "moderate")
            st.caption(
                f"Showing news for **{sector.get('sector', '?')}** "
                f"(severity: `{sev}`)"
            )
        with col_back:
            if st.button("Back to price view", key="event_axis_back"):
                st.session_state.pop("selected_sector", None)
                st.rerun()

        annotated = _sector_to_annotated(sector)
        if not annotated:
            st.info("No news cited for this sector.")
            return
        fig = _build_figure(annotated, window_start=cfg.baseline_date, window_end=as_of)
        st.plotly_chart(fig, use_container_width=True)
        return

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
        h = _headline_for(m["date"], cfg.display_name)
        if h is None:
            label = ""
            hover = (
                f"{m['date']}  {m['pct_change']:+.2f}%<br>"
                "No event-specific English headline matched this date."
            )
        else:
            english_headline = _headline_to_english(h.get("headline", ""))
            label = english_headline
            hover = (
                f"{m['date']}  {m['pct_change']:+.2f}%<br>"
                f"<b>{english_headline or 'English translation unavailable'}</b>"
            )
        annotated.append({
            "date": m["date"], "direction": m["direction"],
            "label": label, "hover": hover,
        })

    fig = _build_figure(annotated, window_start=cfg.baseline_date, window_end=as_of)
    st.plotly_chart(fig, use_container_width=True)
