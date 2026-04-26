"""Streamlit entry: streamlit run ui_app.py

Single-page event-focused dashboard (Plan 3.5).
Layout:
  sidebar: event picker, as-of, metadata, "Clear cache" button, persistent chat
  main:
    [ price_chart (70%) | price_detail_panel (30%) ]
    [ event_axis (full) ]
    [ ripple tree (full) ]
"""
from pathlib import Path
import streamlit as st

from config import load_event, EventConfig
from setup import is_setup_in_progress
from ui.price_chart import render as render_price
from ui.price_detail_panel import render as render_detail
from ui.event_axis import render as render_event_axis
from ui.ripple import render as render_ripple
from ui.sidebar_chat import render as render_chat


st.set_page_config(page_title="Macro Event Ripple Tracker", layout="wide")


def _discover_events() -> list[str]:
    return [p.stem for p in Path("events").glob("*.yaml")]


@st.cache_data(show_spinner=False, ttl=3600)
def _load_cfg(event_name: str) -> EventConfig:
    return load_event(event_name)


def main() -> None:
    st.title("Macro Event Ripple Tracker")

    events = _discover_events()
    if not events:
        st.error("No event configs found in events/*.yaml")
        return

    # Don't fire any retrieve() calls while setup.py is rebuilding the
    # ChromaDB collection — they'd race the rebuild and return empty,
    # silently misleading the user. Documented in CLAUDE.md.
    if is_setup_in_progress():
        st.warning("Data refresh in progress — please wait a moment and reload.")
        st.stop()

    # Sidebar — event controls + metadata
    event_name = st.sidebar.selectbox("Event", events, index=0, key="event_select")
    cfg = _load_cfg(event_name)
    as_of = st.sidebar.date_input(
        "As of", value=cfg.end_date,
        min_value=cfg.start_date, max_value=cfg.end_date, key="as_of_input",
    )
    st.sidebar.markdown(
        f"**{cfg.display_name}**\n\n"
        f"Window: {cfg.start_date} → {cfg.end_date}\n\n"
        f"Baseline: {cfg.baseline_date}\n\n"
        f"Tickers tracked: {len(cfg.tickers)}"
    )
    if st.sidebar.button("Clear cache & refresh"):
        st.cache_data.clear()
        # Forget any selected date on a full refresh
        st.session_state.pop("selected_date", None)
        st.rerun()

    # Reset selected_date if the event changed, so clicks from a prior event
    # don't surface on the new one.
    if st.session_state.get("_last_event") != event_name:
        st.session_state.pop("selected_date", None)
        st.session_state["_last_event"] = event_name

    # Main — three vertical zones
    col_chart, col_detail = st.columns([7, 3], gap="medium")
    with col_chart:
        render_price(cfg, as_of)
    with col_detail:
        render_detail(cfg, as_of)

    render_event_axis(cfg, as_of)
    render_ripple(cfg, as_of)

    # Sidebar chat last so it renders below the metadata
    render_chat(cfg, as_of)


if __name__ == "__main__":
    main()
