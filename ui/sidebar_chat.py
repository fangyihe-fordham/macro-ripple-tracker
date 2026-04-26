from datetime import date
from typing import Dict

import streamlit as st

from agent_supervisor import run as run_supervisor
from config import EventConfig


def format_supervisor_result(result: Dict) -> str:
    intent = result.get("intent", "qa")
    if intent == "qa":
        resp = result.get("response", {}) or {}
        lines = [resp.get("answer", "").strip()]
        cites = resp.get("citations", []) or []
        if cites:
            lines += ["", "**Sources**"]
            for c in cites:
                lines.append(
                    f"- [{c.get('headline','(link)')}]({c.get('url','')}) · {c.get('date','')}"
                )
        return "\n".join(lines)

    if intent == "market":
        changes = result.get("market_data", {}) or {}
        available = [(k, v) for k, v in changes.items() if v.get("available")]
        if not available:
            return "No ticker data available for this event."
        lines = ["Market snapshot (% vs baseline):"]
        for sym, v in available:
            lines.append(f"- **{sym}**: {v['pct_change']:+.2f}%")
        unavail = [k for k, v in changes.items() if not v.get("available")]
        if unavail:
            lines += ["", f"_N/A: {', '.join(unavail)}_"]
        return "\n".join(lines)

    if intent == "timeline":
        items = result.get("timeline", []) or []
        if not items:
            return "No timeline items generated."
        return "\n".join(
            f"- **{i.get('date','')}** — {i.get('headline','')}: {i.get('impact_summary','')}"
            for i in items
        )

    if intent == "ripple":
        tree = result.get("ripple_tree", {}) or {}
        top = ", ".join(n.get("sector", "?") for n in tree.get("nodes", []))
        if not top:
            return "No ripple tree produced for this query."
        return f"Top-level affected sectors: **{top}**. See the Ripple Tree zone below for the full diagram."

    return "Sorry — couldn't route that query."


def render(cfg: EventConfig, as_of: date) -> None:
    st.sidebar.divider()
    st.sidebar.subheader("Ask anything")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Replay prior messages
    for role, content in st.session_state.chat_history:
        with st.sidebar.chat_message(role):
            st.markdown(content, unsafe_allow_html=True)

    prompt = st.sidebar.chat_input("e.g. Why did fertilizer prices rise?")
    if not prompt:
        return

    st.session_state.chat_history.append(("user", prompt))
    with st.sidebar.chat_message("user"):
        st.markdown(prompt)

    with st.sidebar.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = run_supervisor(cfg, prompt, as_of)
        md = format_supervisor_result(result)
        st.markdown(md, unsafe_allow_html=True)
        st.session_state.chat_history.append(("assistant", md))
