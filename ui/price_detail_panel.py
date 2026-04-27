from datetime import date, datetime
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from agent_price_explainer import explain_move
from config import EventConfig
from data_market import get_price_range
# Single-source the primary-ticker constants from ui.price_chart so this
# panel never drifts from Viz 1.
from ui.price_chart import _PRIMARY_SYMBOL as _SYMBOL, _PRIMARY_NAME as _NAME


def format_detail_markdown(attr: Dict, target_date: str, symbol: str, pct_change: float) -> str:
    direction = (attr.get("direction") or "flat").lower()
    arrow = {"up": "▲", "down": "▼"}.get(direction, "■")
    lines = [
        f"### {arrow} {symbol} on {target_date}  ({pct_change:+.2f}%)",
        "",
        f"**{attr.get('headline_summary', '').strip()}**",
        "",
    ]
    if attr.get("status") == "fallback" and attr.get("reason_detail"):
        lines += [
            "**Why this day is hard to explain**",
            f"- {attr.get('reason_detail', '').strip()}",
            "",
        ]
    lines += [
        "**Key drivers**",
    ]
    for d in attr.get("key_drivers", []) or []:
        lines.append(f"- {d}")
    caveats = attr.get("caveats", []) or []
    if caveats:
        lines += ["", "**Caveats**"]
        for c in caveats:
            lines.append(f"- {c}")
    news = attr.get("supporting_news", []) or []
    if news:
        lines += ["", "**Supporting news**"]
        for item in news:
            url = item.get("url", "")
            head = item.get("headline", url or "(link)")
            d = item.get("date", "")
            lines.append(f"- [{head}]({url}) · {d}")
    return "\n".join(lines)


@st.cache_data(show_spinner="Explaining the move...", ttl=3600)
def _cached_explain(target_date_iso: str, symbol: str, name: str,
                    pct_change: float, price_from: float, price_to: float,
                    event_display_name: str, seed_keywords: tuple[str, ...]) -> Dict:
    return explain_move(
        target_date=datetime.strptime(target_date_iso, "%Y-%m-%d").date(),
        symbol=symbol, name=name,
        pct_change=pct_change, price_from=price_from, price_to=price_to,
        event_display_name=event_display_name,
        seed_keywords=list(seed_keywords),
    )


def _move_metadata(prices: pd.Series, target_iso: str) -> Optional[Dict]:
    """Look up price_from / price_to / pct_change for target_iso in the series."""
    ts = pd.Timestamp(target_iso)
    if ts not in prices.index:
        return None
    pos = prices.index.get_loc(ts)
    # pos == 0 means the target IS the baseline date — no prior-day reference
    # to compute pct_change against. This path is structurally unreachable
    # from normal UI flow because price_chart.significant_moves uses
    # pct_change() which puts NaN at index 0, so row 0 never qualifies as
    # a marker. Defensive guard anyway in case a future caller passes the
    # baseline date directly.
    if pos == 0:
        return None
    price_to = float(prices.iloc[pos])
    price_from = float(prices.iloc[pos - 1])
    # Explicit `!= 0.0` is more readable than truthiness here — `0.0` is the
    # only falsy float we want to guard, and this also clarifies that
    # negative prices (truthy) take the divide path.
    pct = (price_to / price_from - 1.0) * 100.0 if price_from != 0.0 else 0.0
    return {"price_from": price_from, "price_to": price_to, "pct_change": pct}


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Why did it move?")
    sel = st.session_state.get("selected_date")
    if not sel:
        st.info("Click a red/green marker on the chart to explain that day's move.")
        return

    prices = get_price_range(_SYMBOL, cfg.baseline_date, as_of)
    meta = _move_metadata(prices, sel)
    if meta is None:
        st.warning(f"No price data for {_SYMBOL} on {sel}.")
        return

    attr = _cached_explain(
        target_date_iso=sel, symbol=_SYMBOL, name=_NAME,
        pct_change=meta["pct_change"], price_from=meta["price_from"],
        price_to=meta["price_to"],
        event_display_name=cfg.display_name,
        seed_keywords=tuple(cfg.seed_keywords),
    )
    st.markdown(
        format_detail_markdown(attr, target_date=sel, symbol=_SYMBOL,
                               pct_change=meta["pct_change"]),
        unsafe_allow_html=True,
    )
