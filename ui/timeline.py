from datetime import date
from typing import List, Dict
import streamlit as st

from agent_supervisor import run as run_supervisor
from config import EventConfig


_SEVERITY_COLORS = {
    "critical":    "#d32f2f",
    "significant": "#f57c00",
    "moderate":    "#fbc02d",
}


def classify_severity(summary: str) -> str:
    s = summary.lower()
    if any(w in s for w in ["halt", "close", "block", "collapse", "crash", "surge", "spike"]):
        return "critical"
    if any(w in s for w in ["rise", "jump", "climb", "up", "rally", "tension"]):
        return "significant"
    return "moderate"


# Leading _ on _cfg tells Streamlit not to hash the arg — pydantic v2
# non-frozen models have __hash__=None. Cache still keys on as_of and
# re-invalidates implicitly because _load_cfg() in ui_app.py returns the
# same EventConfig instance per event selection.
@st.cache_data(show_spinner="Building timeline...", ttl=3600)
def fetch_timeline(_cfg: EventConfig, as_of: date) -> List[Dict]:
    result = run_supervisor(_cfg, "Give me the chronological timeline of key events", as_of)
    return result.get("timeline", [])


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Timeline")
    items = fetch_timeline(cfg, as_of)
    if not items:
        st.warning(
            "No timeline items generated. Have you run `python setup.py --event {}`?".format(cfg.name)
        )
        return
    for item in items:
        sev = classify_severity(item.get("impact_summary", ""))
        color = _SEVERITY_COLORS.get(sev, "#9e9e9e")
        with st.container():
            st.markdown(
                f"<div style='border-left:4px solid {color};padding-left:12px;margin-bottom:12px'>"
                f"<strong>{item.get('date','')}</strong> · <em>{item.get('headline','')}</em><br>"
                f"<span style='color:#555'>{item.get('impact_summary','')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
