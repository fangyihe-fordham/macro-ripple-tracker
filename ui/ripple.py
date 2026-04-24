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


def _label(node: Dict) -> str:
    pc = node.get("price_change")
    pc_str = f"  ({pc:+.1f}%)" if isinstance(pc, (int, float)) else ""
    return f"{node.get('sector','?')}{pc_str}"


def tree_to_graph_elements(tree: Dict) -> Tuple[List[Node], List[Edge]]:
    nodes: List[Node] = [Node(id="root", label=tree.get("event", "Event"), size=25, color="#1976d2")]
    edges: List[Edge] = []
    counter = {"i": 0}

    def _walk(children: List[Dict], parent_id: str) -> None:
        for n in children:
            counter["i"] += 1
            nid = f"n{counter['i']}"
            color = _SEVERITY_COLORS.get(n.get("severity", "moderate"), "#9e9e9e")
            nodes.append(Node(id=nid, label=_label(n), size=18, color=color,
                              title=n.get("mechanism", "")))
            edges.append(Edge(source=parent_id, target=nid))
            _walk(n.get("children", []), nid)

    _walk(tree.get("nodes", []), "root")
    return nodes, edges


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

    nodes, edges = tree_to_graph_elements(tree)
    cfg_graph = Config(
        width=1000, height=650, directed=True, physics=True,
        hierarchical=True, collapsible=True,
    )
    agraph(nodes=nodes, edges=edges, config=cfg_graph)

    st.caption(
        "Legend: :red_circle: critical   :orange_circle: significant   :yellow_circle: moderate"
    )

    st.markdown("### Node details")
    with st.expander("All nodes (flat)"):
        for n in tree["nodes"]:
            _render_node_detail(n)
