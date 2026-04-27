from datetime import date
from typing import Dict, List, Tuple
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from agent_supervisor import run as run_supervisor
from config import EventConfig


_SEVERITY_COLORS = {
    "critical":    "#d32f2f",
    "significant": "#f57c00",
    "moderate":    "#fbc02d",
}

_SEVERITY_SIZES = {
    "critical":    22,
    "significant": 18,
    "moderate":    14,
}

_MAX_LABEL_LEN = 20


def _label(node: Dict) -> str:
    """Sector name, truncated to 20 chars with …. Price change moved to tooltip."""
    sec = node.get("sector", "?")
    if len(sec) > _MAX_LABEL_LEN:
        sec = sec[: _MAX_LABEL_LEN - 1].rstrip() + "…"
    return sec


def _tooltip(node: Dict) -> str:
    """Hover-only content: mechanism + precise price change."""
    parts: List[str] = []
    mech = node.get("mechanism", "")
    if mech:
        parts.append(mech)
    pc = node.get("price_change")
    if isinstance(pc, (int, float)):
        parts.append(f"Δ {pc:+.1f}%")
    return " · ".join(parts)


def tree_to_graph_elements(tree: Dict) -> Tuple[List[Node], List[Edge], Dict[str, Dict]]:
    nodes: List[Node] = [Node(id="root", label=tree.get("event", "Event"), size=25, color="#1976d2")]
    edges: List[Edge] = []
    id_map: Dict[str, Dict] = {}
    counter = {"i": 0}

    def _walk(children: List[Dict], parent_id: str) -> None:
        for n in children:
            counter["i"] += 1
            nid = f"n{counter['i']}"
            sev = n.get("severity", "moderate")
            color = _SEVERITY_COLORS.get(sev, "#9e9e9e")
            size = _SEVERITY_SIZES.get(sev, 14)
            nodes.append(Node(id=nid, label=_label(n), size=size, color=color,
                              title=_tooltip(n)))
            edges.append(Edge(source=parent_id, target=nid))
            id_map[nid] = n
            _walk(n.get("children", []), nid)

    _walk(tree.get("nodes", []), "root")
    return nodes, edges, id_map


# Leading _ on _cfg: @st.cache_data can't hash pydantic v2 EventConfig
# (non-frozen → __hash__=None). Same pattern as ui.timeline.
@st.cache_data(show_spinner="Generating ripple tree...", ttl=3600)
def fetch_tree(_cfg: EventConfig, as_of: date) -> Dict:
    result = run_supervisor(_cfg, "Generate the industry ripple tree.", as_of)
    return result.get("ripple_tree", {})


def _render_node_detail(node: Dict, depth: int = 0) -> None:
    pad = "&nbsp;" * (depth * 4)
    pc = node.get("price_change")
    pc_str = f"{pc:+.1f}%" if isinstance(pc, (int, float)) else "—"
    st.markdown(
        f"{pad}**{node.get('sector','?')}**  ·  severity: `{node.get('severity','?')}`  ·  Δ {pc_str}",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"{pad}<span style='color:#666'>{node.get('mechanism','')}</span>",
        unsafe_allow_html=True,
    )
    for src in node.get("supporting_news", [])[:3]:
        st.markdown(
            f"{pad}&nbsp;&nbsp;↳ [{src.get('headline','(link)')}]({src.get('url','')}) · {src.get('date','')}",
            unsafe_allow_html=True,
        )
    for c in node.get("children", []):
        _render_node_detail(c, depth + 1)


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Industry Ripple Tree")
    tree = fetch_tree(cfg, as_of)
    if not tree or not tree.get("nodes"):
        st.warning("No ripple tree produced. Check that setup.py ran and ANTHROPIC_API_KEY is set.")
        return

    nodes, edges, id_map = tree_to_graph_elements(tree)
    cfg_graph = Config(
        width=1000, height=650, directed=True, physics=True,
        hierarchical=True, collapsible=True,
    )
    clicked_id = agraph(nodes=nodes, edges=edges, config=cfg_graph)

    if isinstance(clicked_id, str) and clicked_id in id_map:
        node_data = id_map[clicked_id]
        selected_sector = {
            "sector": node_data.get("sector", "?"),
            "mechanism": node_data.get("mechanism", ""),
            "severity": node_data.get("severity", "moderate"),
            "supporting_news": node_data.get("supporting_news", []),
        }
        if st.session_state.get("selected_sector") != selected_sector:
            st.session_state["selected_sector"] = selected_sector
            st.rerun()

    st.caption(
        "Legend: :red_circle: critical   :orange_circle: significant   :yellow_circle: moderate"
    )

    st.markdown("### Node details")
    with st.expander("All nodes (flat)"):
        for n in tree["nodes"]:
            _render_node_detail(n)
