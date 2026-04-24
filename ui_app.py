"""Streamlit entry: streamlit run ui_app.py"""
from datetime import date
from pathlib import Path
import streamlit as st

from config import load_event, EventConfig


st.set_page_config(page_title="Macro Event Ripple Tracker", layout="wide")


def _discover_events() -> list[str]:
    return [p.stem for p in Path("events").glob("*.yaml")]


@st.cache_data(show_spinner=False)
def _load_cfg(event_name: str) -> EventConfig:
    return load_event(event_name)


def main():
    st.title("Macro Event Ripple Tracker")
    events = _discover_events()
    if not events:
        st.error("No event configs found in events/*.yaml")
        return
    event_name = st.sidebar.selectbox("Event", events, index=0)
    cfg = _load_cfg(event_name)
    as_of = st.sidebar.date_input(
        "As of (for % change vs baseline)",
        value=cfg.end_date,
        min_value=cfg.start_date,
        max_value=cfg.end_date,
    )

    st.sidebar.markdown(
        f"**{cfg.display_name}**\n\n"
        f"Window: {cfg.start_date} → {cfg.end_date}\n\n"
        f"Baseline: {cfg.baseline_date}\n\n"
        f"Tickers tracked: {len(cfg.tickers)}"
    )

    tab1, tab2, tab3, tab4 = st.tabs(["Timeline", "Ripple Tree", "Market", "Ask Anything"])
    from ui.timeline import render as render_timeline
    from ui.ripple import render as render_ripple
    from ui.market import render as render_market
    from ui.qa import render as render_qa

    with tab1:
        render_timeline(cfg, as_of)
    with tab2:
        render_ripple(cfg, as_of)
    with tab3:
        render_market(cfg, as_of)
    with tab4:
        render_qa(cfg, as_of)


if __name__ == "__main__":
    main()
