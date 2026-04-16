# Plan 3 — UI (M5 Streamlit) + §9 Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Plans 1 and 2 complete. `python setup.py --event iran_war` has been run at least once. `agent_supervisor.run()`, `generate_ripple_tree()`, `retrieve()`, `get_price_changes()`, `get_price_range()`, `load_event()` are all importable.

**Goal:** (M5) Ship the Streamlit 4-tab UI — Timeline, Ripple Tree, Market Dashboard, Ask Anything — that renders outputs from the supervisor. (§9) Ship a self-contained evaluation harness that measures the four dimensions required by the spec (retrieval precision, ripple groundedness, QA faithfulness, market data integrity) and writes a results file suitable for inclusion in the report.

**Architecture:** `ui_app.py` is a thin Streamlit presenter — it loads the event config, caches the supervisor's outputs via `@st.cache_data`, and delegates rendering per tab to dedicated helper modules. The eval harness is a separate `eval/` directory with a `run_eval.py` CLI, a small hand-curated test set in `eval/test_queries.json`, an LLM-as-judge scorer, and a Markdown report writer. The harness reuses `agent_supervisor.run()` so UI and eval observe the same code path.

**Tech Stack:** Existing stack + `streamlit==1.39.x`, `plotly==5.24.x`, `streamlit-agraph==0.0.45`. Eval uses the same `ChatAnthropic` client as the agents.

---

## File Structure

```
macro-ripple-tracker/
├── ui_app.py                          # Streamlit entry point — 4 tabs
├── ui/
│   ├── __init__.py
│   ├── timeline.py                    # Tab 1
│   ├── ripple.py                      # Tab 2 (streamlit-agraph)
│   ├── market.py                      # Tab 3 (plotly)
│   └── qa.py                          # Tab 4 (chat)
├── eval/
│   ├── __init__.py
│   ├── test_queries.json              # hand-curated eval set
│   ├── wikipedia_ground_truth.md      # Iran War impact sections (curated)
│   ├── retrieval.py                   # §9.1 precision@5
│   ├── ripple_groundedness.py         # §9.2 sector correctness
│   ├── qa_faithfulness.py             # §9.3 RAG-triad-lite faithfulness
│   ├── market_integrity.py            # §9.4 spot checks
│   ├── judge.py                       # shared LLM-as-judge helper
│   └── run_eval.py                    # CLI: run all four, write eval/results/<date>.md
├── tests/
│   ├── test_ui_helpers.py
│   ├── test_eval_retrieval.py
│   ├── test_eval_ripple_groundedness.py
│   ├── test_eval_qa_faithfulness.py
│   ├── test_eval_market_integrity.py
│   └── test_run_eval.py
```

**Why split `ui/` into per-tab modules:** keeps each ≤ 150 lines, easier to iterate on one tab without pulling in the others, and each helper is unit-testable (given small structured inputs) without spinning up Streamlit.

---

### Task 1: Streamlit shell + dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `ui_app.py`
- Create: `ui/__init__.py`

- [ ] **Step 1: Append UI deps to `requirements.txt`**

```
streamlit==1.39.0
plotly==5.24.1
streamlit-agraph==0.0.45
```

- [ ] **Step 2: Install**

Run: `pip install -r requirements.txt`
Verify: `python -c "import streamlit, plotly; from streamlit_agraph import agraph; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Create `ui/__init__.py`** (empty)

- [ ] **Step 4: Create minimal `ui_app.py`**

```python
# ui_app.py
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
    as_of = st.sidebar.date_input("As of (for % change vs baseline)",
                                  value=cfg.end_date, min_value=cfg.start_date, max_value=cfg.end_date)

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

    with tab1: render_timeline(cfg, as_of)
    with tab2: render_ripple(cfg, as_of)
    with tab3: render_market(cfg, as_of)
    with tab4: render_qa(cfg, as_of)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Smoke-run the shell**

Run: `streamlit run ui_app.py`
Expected: browser opens to `localhost:8501`; sidebar shows Iran War event; four tabs render empty (`ImportError` on tab bodies is expected until Tasks 2–5; if it errors on imports, stub the four `ui/*.py` files with empty `def render(cfg, as_of): st.write("TBD")` now to keep the shell runnable — verify.)

- [ ] **Step 6: Stub the four tab modules so the shell doesn't crash**

```python
# ui/timeline.py, ui/ripple.py, ui/market.py, ui/qa.py (all four identical for now)
import streamlit as st

def render(cfg, as_of):
    st.info("Not implemented yet.")
```

- [ ] **Step 7: Re-run**

Run: `streamlit run ui_app.py`
Expected: all 4 tabs render an info box. Quit with Ctrl-C.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt ui_app.py ui/
git commit -m "feat(M5): Streamlit shell with sidebar event selector + 4 tab stubs"
```

---

### Task 2: Tab 1 — Timeline

**Files:**
- Modify: `ui/timeline.py`
- Test: `tests/test_ui_helpers.py`

- [ ] **Step 1: Write failing test for the data helper**

```python
# tests/test_ui_helpers.py
from datetime import date
import pytest
from config import load_event


def test_timeline_renderable_structure(monkeypatch):
    from ui import timeline
    monkeypatch.setattr(timeline, "run_supervisor", lambda cfg, query, as_of: {
        "timeline": [
            {"date": "2026-02-28", "headline": "Iran closes Hormuz", "impact_summary": "Oil transit halted."},
            {"date": "2026-03-01", "headline": "Brent tops $100", "impact_summary": "Crude +35%."},
        ]
    })
    items = timeline.fetch_timeline(load_event("iran_war"), date(2026, 4, 15))
    assert len(items) == 2
    assert items[0]["date"] == "2026-02-28"

    # Severity classification
    assert timeline.classify_severity("Oil transit halted.") in {"critical", "significant", "moderate"}
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_ui_helpers.py::test_timeline_renderable_structure -v`
Expected: FAIL (module stub has no `fetch_timeline`).

- [ ] **Step 3: Implement `ui/timeline.py`**

```python
# ui/timeline.py
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
    """Very lightweight keyword heuristic; avoids an extra LLM call per item."""
    s = summary.lower()
    if any(w in s for w in ["halt", "close", "block", "collapse", "crash", "surge", "spike"]):
        return "critical"
    if any(w in s for w in ["rise", "jump", "climb", "up", "rally", "tension"]):
        return "significant"
    return "moderate"


@st.cache_data(show_spinner="Building timeline...", ttl=3600)
def fetch_timeline(cfg: EventConfig, as_of: date) -> List[Dict]:
    result = run_supervisor(cfg, "Give me the chronological timeline of key events", as_of)
    return result.get("timeline", [])


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Timeline")
    items = fetch_timeline(cfg, as_of)
    if not items:
        st.warning("No timeline items generated. Have you run `python setup.py --event {}`?".format(cfg.name))
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
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_ui_helpers.py::test_timeline_renderable_structure -v`
Expected: 1 passed.

- [ ] **Step 5: Visual smoke**

Run: `streamlit run ui_app.py` → click "Timeline" tab.
Expected: 8–15 cards render with dates, headlines, summaries, left-border color by severity.

- [ ] **Step 6: Commit**

```bash
git add ui/timeline.py tests/test_ui_helpers.py
git commit -m "feat(M5): Tab 1 Timeline with severity color bars"
```

---

### Task 3: Tab 2 — Ripple Tree (streamlit-agraph)

**Files:**
- Modify: `ui/ripple.py`
- Modify: `tests/test_ui_helpers.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui_helpers.py`:

```python
def test_ripple_tree_to_graph_elements():
    from ui import ripple
    tree = {
        "event": "Hormuz",
        "nodes": [
            {"sector": "Oil", "mechanism": "m1", "severity": "critical",
             "price_change": 49.6, "supporting_news": [{"url": "u", "headline": "h", "date": "2026-03-01"}],
             "children": [
                 {"sector": "Fertilizer", "mechanism": "m2", "severity": "significant",
                  "price_change": 15.0, "supporting_news": [], "children": []},
             ]},
            {"sector": "Defense", "mechanism": "m3", "severity": "moderate",
             "price_change": 8.0, "supporting_news": [], "children": []},
        ],
    }
    nodes, edges = ripple.tree_to_graph_elements(tree)
    # 1 root (event) + 3 sector nodes
    assert len(nodes) == 4
    # edges: root->Oil, root->Defense, Oil->Fertilizer
    assert len(edges) == 3
    labels = [n.label for n in nodes]
    assert "Oil" in labels and "Fertilizer" in labels and "Defense" in labels
    # Severity color present on each non-root node
    non_root = [n for n in nodes if n.id != "root"]
    assert all(n.color for n in non_root)
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_ui_helpers.py::test_ripple_tree_to_graph_elements -v`
Expected: FAIL.

- [ ] **Step 3: Implement `ui/ripple.py`**

```python
# ui/ripple.py
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


@st.cache_data(show_spinner="Generating ripple tree...", ttl=3600)
def fetch_tree(cfg: EventConfig, as_of: date) -> Dict:
    result = run_supervisor(cfg, "Generate the industry ripple tree.", as_of)
    return result.get("ripple_tree", {})


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Industry Ripple Tree")
    tree = fetch_tree(cfg, as_of)
    if not tree or not tree.get("nodes"):
        st.warning("No ripple tree produced. Check that setup.py ran and ANTHROPIC_API_KEY is set.")
        return

    nodes, edges = tree_to_graph_elements(tree)
    cfg_graph = Config(width=1000, height=650, directed=True, physics=True,
                       hierarchical=True, collapsible=True)
    agraph(nodes=nodes, edges=edges, config=cfg_graph)

    st.caption("Legend: "
               " :red_circle: critical   :orange_circle: significant   :yellow_circle: moderate")

    st.markdown("### Node details")
    with st.expander("All nodes (flat)"):
        for n in tree["nodes"]:
            _render_node_detail(n)


def _render_node_detail(node: Dict, depth: int = 0) -> None:
    pad = "&nbsp;" * (depth * 4)
    pc = node.get("price_change")
    pc_str = f"{pc:+.1f}%" if isinstance(pc, (int, float)) else "—"
    st.markdown(f"{pad}**{node.get('sector','?')}**  ·  severity: `{node.get('severity','?')}`  ·  Δ {pc_str}",
                unsafe_allow_html=True)
    st.markdown(f"{pad}<span style='color:#666'>{node.get('mechanism','')}</span>",
                unsafe_allow_html=True)
    for src in node.get("supporting_news", [])[:3]:
        st.markdown(f"{pad}&nbsp;&nbsp;↳ [{src.get('headline','(link)')}]({src.get('url','')}) · {src.get('date','')}",
                    unsafe_allow_html=True)
    for c in node.get("children", []):
        _render_node_detail(c, depth + 1)
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_ui_helpers.py::test_ripple_tree_to_graph_elements -v`
Expected: 1 passed.

- [ ] **Step 5: Visual smoke**

Run: `streamlit run ui_app.py` → "Ripple Tree" tab.
Expected: interactive graph with event root, Tier-1 sectors, expandable children colored by severity; details expander lists each node with citations.

- [ ] **Step 6: Commit**

```bash
git add ui/ripple.py tests/test_ui_helpers.py
git commit -m "feat(M5): Tab 2 interactive ripple tree (streamlit-agraph) with node details"
```

---

### Task 4: Tab 3 — Market Dashboard (Plotly)

**Files:**
- Modify: `ui/market.py`
- Modify: `tests/test_ui_helpers.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui_helpers.py`:

```python
def test_market_build_figure_per_ticker():
    import pandas as pd
    from ui import market
    cfg = load_event("iran_war")
    # Fake price series
    idx = pd.to_datetime(["2026-02-26", "2026-02-27", "2026-03-02", "2026-03-03"])
    s = pd.Series([73.9, 74.2, 88.5, 102.3], index=idx, name="Close")
    fig = market.build_ticker_figure("BZ=F", "Brent Crude Oil", s, event_start=date(2026, 2, 28))
    # Plotly figure has data + layout
    assert len(fig.data) >= 1
    # Event start vline should be in layout shapes
    assert any(getattr(sh, "x0", None) is not None for sh in fig.layout.shapes)
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_ui_helpers.py::test_market_build_figure_per_ticker -v`
Expected: FAIL.

- [ ] **Step 3: Implement `ui/market.py`**

```python
# ui/market.py
from datetime import date
from typing import Dict
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import EventConfig
from data_market import get_price_changes, get_price_range


def build_ticker_figure(symbol: str, name: str, series: pd.Series, event_start: date) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=symbol))
    # Event marker
    fig.add_vline(x=event_start.isoformat(), line_width=2, line_dash="dash",
                  line_color="red", annotation_text="Event", annotation_position="top")
    fig.update_layout(title=f"{name} ({symbol})", height=280,
                      margin=dict(l=40, r=20, t=40, b=30),
                      xaxis_title="", yaxis_title="Close")
    return fig


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_changes(cfg: EventConfig, as_of: date) -> Dict:
    return get_price_changes(cfg, as_of=as_of)


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Market Dashboard")
    changes = fetch_changes(cfg, as_of)
    if not changes:
        st.warning("No price data. Run `python setup.py --event {}` first.".format(cfg.name))
        return

    # Summary table
    rows = []
    for t in cfg.tickers:
        c = changes.get(t.symbol)
        if c is None: continue
        rows.append({
            "Category": t.category, "Name": t.name, "Symbol": t.symbol,
            "Baseline": round(c["baseline"], 2), "Latest": round(c["latest"], 2),
            "% Change": round(c["pct_change"], 2),
        })
    df = pd.DataFrame(rows).sort_values("% Change", key=lambda s: s.abs(), ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Per-ticker charts, 2 columns
    cols = st.columns(2)
    for i, t in enumerate(cfg.tickers):
        series = get_price_range(t.symbol, cfg.baseline_date, cfg.end_date)
        if series.empty: continue
        with cols[i % 2]:
            st.plotly_chart(
                build_ticker_figure(t.symbol, t.name, series, event_start=cfg.start_date),
                use_container_width=True,
            )
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_ui_helpers.py::test_market_build_figure_per_ticker -v`
Expected: 1 passed.

- [ ] **Step 5: Visual smoke**

Run: `streamlit run ui_app.py` → "Market" tab.
Expected: ranked summary table at top, then 11 line charts (two columns) with a red dashed line at event start.

- [ ] **Step 6: Commit**

```bash
git add ui/market.py tests/test_ui_helpers.py
git commit -m "feat(M5): Tab 3 Market dashboard with Plotly per-ticker charts"
```

---

### Task 5: Tab 4 — Ask Anything (chat)

**Files:**
- Modify: `ui/qa.py`
- Modify: `tests/test_ui_helpers.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui_helpers.py`:

```python
def test_qa_format_answer_with_citations():
    from ui import qa
    response = {
        "answer": "Brent hit $111 on March 4.",
        "citations": [
            {"url": "https://x/1", "headline": "Brent hits 111", "date": "2026-03-04"},
            {"url": "https://x/2", "headline": "Oil rally continues",  "date": "2026-03-05"},
        ]
    }
    md = qa.format_answer_markdown(response)
    assert "Brent hit $111" in md
    assert "Brent hits 111" in md
    assert "https://x/1" in md
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_ui_helpers.py::test_qa_format_answer_with_citations -v`
Expected: FAIL.

- [ ] **Step 3: Implement `ui/qa.py`**

```python
# ui/qa.py
from datetime import date
from typing import Dict
import streamlit as st

from agent_supervisor import run as run_supervisor
from config import EventConfig


def format_answer_markdown(response: Dict) -> str:
    ans = response.get("answer", "").strip()
    cites = response.get("citations", []) or []
    if not cites:
        return ans
    lines = [ans, "", "**Sources**"]
    for c in cites:
        url = c.get("url", "")
        head = c.get("headline", url)
        d = c.get("date", "")
        lines.append(f"- [{head}]({url}) · {d}")
    return "\n".join(lines)


def render(cfg: EventConfig, as_of: date) -> None:
    st.subheader("Ask Anything")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # list of (role, content_markdown)

    for role, content in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(content, unsafe_allow_html=True)

    prompt = st.chat_input("Ask about the event (e.g. 'Why did fertilizer prices rise?')")
    if not prompt:
        return

    st.session_state.chat_history.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = run_supervisor(cfg, prompt, as_of)
        intent = result.get("intent", "qa")
        if intent == "qa":
            md = format_answer_markdown(result.get("response", {}))
        elif intent == "market":
            changes = result.get("market_data", {})
            md = "Market snapshot:\n" + "\n".join(
                f"- {k}: {v['pct_change']:+.1f}% vs baseline" for k, v in changes.items()
            )
        elif intent == "timeline":
            items = result.get("timeline", [])
            md = "\n".join(f"- **{i['date']}** — {i['headline']}: {i['impact_summary']}" for i in items)
        elif intent == "ripple":
            tree = result.get("ripple_tree", {})
            top = ", ".join(n["sector"] for n in tree.get("nodes", []))
            md = f"Top-level affected sectors: {top}. See the **Ripple Tree** tab for the full diagram."
        else:
            md = "Sorry — couldn't classify that query."
        st.markdown(md, unsafe_allow_html=True)
        st.session_state.chat_history.append(("assistant", md))
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_ui_helpers.py -v`
Expected: all UI helper tests pass (4+ tests).

- [ ] **Step 5: Visual smoke**

Run: `streamlit run ui_app.py` → "Ask Anything" tab.
Expected: chat input; typing "Why did fertilizer prices rise?" produces a grounded answer with source links.

- [ ] **Step 6: Commit**

```bash
git add ui/qa.py tests/test_ui_helpers.py
git commit -m "feat(M5): Tab 4 Ask Anything chat with cited answers"
```

---

### Task 6: Eval test queries + ground truth

**Files:**
- Create: `eval/__init__.py`
- Create: `eval/test_queries.json`
- Create: `eval/wikipedia_ground_truth.md`

- [ ] **Step 1: Create `eval/__init__.py`** (empty)

- [ ] **Step 2: Create `eval/test_queries.json`**

Five queries per dimension (retrieval, QA, ripple comes from the generated tree itself, market integrity picks (ticker,date) pairs).

```json
{
  "retrieval": [
    {"id": "r1", "query": "How high did Brent crude go after Hormuz closed?",
     "must_be_about": ["Brent", "oil price", "crude"]},
    {"id": "r2", "query": "Did shipping rates change after the Iran war started?",
     "must_be_about": ["shipping", "freight", "tanker", "insurance"]},
    {"id": "r3", "query": "What is happening with LNG exports from Qatar?",
     "must_be_about": ["LNG", "Qatar", "natural gas", "exports"]},
    {"id": "r4", "query": "Fertilizer producers affected by Iran war",
     "must_be_about": ["fertilizer", "ammonia", "CF", "urea"]},
    {"id": "r5", "query": "Defense stocks reaction to Iran escalation",
     "must_be_about": ["defense", "Lockheed", "Raytheon", "military", "ITA"]}
  ],
  "qa": [
    {"id": "q1", "query": "Why would the closure of the Strait of Hormuz affect global oil prices?"},
    {"id": "q2", "query": "How did the Iran war affect fertilizer production costs?"},
    {"id": "q3", "query": "Which shipping companies were most impacted by tanker insurance rate increases?"},
    {"id": "q4", "query": "What were the top price movers in the week after Hormuz closed?"},
    {"id": "q5", "query": "How did defense stocks move and why?"}
  ],
  "market_integrity": [
    {"symbol": "BZ=F", "date": "2026-03-02"},
    {"symbol": "CL=F", "date": "2026-03-03"},
    {"symbol": "XLE",  "date": "2026-03-04"},
    {"symbol": "NG=F", "date": "2026-03-05"},
    {"symbol": "^GSPC","date": "2026-03-06"}
  ]
}
```

- [ ] **Step 3: Create `eval/wikipedia_ground_truth.md`** (canonical impact sectors; populated by hand from Wikipedia's "2026 Strait of Hormuz crisis" article at eval time)

```markdown
# Ground Truth — 2026 Strait of Hormuz Crisis Economic Impact

Source: Wikipedia "2026 Strait of Hormuz crisis" (retrieved YYYY-MM-DD).

## Sectors directly impacted (critical / significant)
- Oil Supply (crude, refined products)
- Natural Gas / LNG (Qatar exports)
- Shipping / Tanker insurance
- Fertilizer / Ammonia
- Airlines / Jet fuel
- Petrochemicals / Plastics
- Aluminum / energy-intensive metals
- Defense / Aerospace
- Broad equity markets (risk-off)

## Notes
- Populate this file at eval time by hand-reading the Wikipedia article.
- Sector names are normalized: use these canonical strings when matching.
```

- [ ] **Step 4: Commit**

```bash
git add eval/__init__.py eval/test_queries.json eval/wikipedia_ground_truth.md
git commit -m "eval: test queries + ground truth skeleton"
```

---

### Task 7: Eval §9.1 — Retrieval precision@5 (LLM-as-judge)

**Files:**
- Create: `eval/judge.py`
- Create: `eval/retrieval.py`
- Test: `tests/test_eval_retrieval.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_eval_retrieval.py
from langchain_core.messages import AIMessage
from eval import retrieval


class _FakeLLM:
    def __init__(self, replies): self._r = list(replies)
    def invoke(self, msgs): return AIMessage(content=self._r.pop(0))


def test_precision_at_k_scores_hits(monkeypatch):
    # 5 hits; 4 judged relevant -> precision = 0.8
    fake_hits = [{"text": "t", "url": f"u{i}", "headline": "h", "metadata": {}, "score": 0.9}
                 for i in range(5)]
    monkeypatch.setattr(retrieval, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(retrieval, "get_chat_model",
                        lambda **kw: _FakeLLM(["yes", "yes", "no", "yes", "yes"]))
    q = {"id": "r1", "query": "How high did Brent go?",
         "must_be_about": ["Brent", "oil"]}
    score = retrieval.precision_at_k(q, k=5)
    assert score["precision"] == 0.8
    assert score["relevant"] == 4
    assert score["retrieved"] == 5


def test_run_retrieval_eval_all(monkeypatch):
    monkeypatch.setattr(retrieval, "retrieve", lambda q, top_k: [
        {"text": "t", "url": "u", "headline": "h", "metadata": {}, "score": 0.9}])
    monkeypatch.setattr(retrieval, "get_chat_model", lambda **kw: _FakeLLM(["yes"] * 5))
    queries = [{"id": f"r{i}", "query": "q", "must_be_about": ["x"]} for i in range(5)]
    report = retrieval.run_retrieval_eval(queries, k=1)
    assert report["mean_precision"] == 1.0
    assert len(report["per_query"]) == 5
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_eval_retrieval.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `eval/judge.py`**

```python
# eval/judge.py
"""Shared LLM-as-judge helpers."""
from langchain_core.messages import HumanMessage, SystemMessage
from llm import get_chat_model


_RELEVANCE_SYSTEM = (
    "You are a strict relevance judge. Answer ONLY 'yes' or 'no'.\n"
    "Given a user query, topic keywords, and an article snippet, "
    "decide if the snippet is topically relevant to the query."
)


def judge_relevance(query: str, keywords: list[str], snippet: str) -> bool:
    llm = get_chat_model(temperature=0.0, max_tokens=5)
    human = (
        f"Query: {query}\n"
        f"Topic keywords: {', '.join(keywords)}\n"
        f"Snippet: {snippet[:800]}\n\nRelevant?"
    )
    resp = llm.invoke([SystemMessage(content=_RELEVANCE_SYSTEM), HumanMessage(content=human)])
    word = str(resp.content).strip().lower()
    return word.startswith("y")
```

- [ ] **Step 4: Implement `eval/retrieval.py`**

```python
# eval/retrieval.py
from typing import Dict, List
from data_news import retrieve
from llm import get_chat_model
from eval.judge import judge_relevance


def precision_at_k(q: Dict, k: int = 5) -> Dict:
    hits = retrieve(q["query"], top_k=k)
    relevant = 0
    per_hit = []
    for h in hits:
        rel = judge_relevance(q["query"], q.get("must_be_about", []),
                              f"{h.get('headline','')} {h.get('text','')}")
        per_hit.append({"url": h.get("url"), "headline": h.get("headline"), "relevant": rel})
        if rel: relevant += 1
    retrieved = len(hits)
    p = relevant / retrieved if retrieved else 0.0
    return {"id": q["id"], "query": q["query"], "retrieved": retrieved,
            "relevant": relevant, "precision": p, "hits": per_hit}


def run_retrieval_eval(queries: List[Dict], k: int = 5) -> Dict:
    per = [precision_at_k(q, k=k) for q in queries]
    mean = sum(x["precision"] for x in per) / len(per) if per else 0.0
    return {"metric": f"precision@{k}", "mean_precision": mean, "per_query": per}
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_eval_retrieval.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add eval/judge.py eval/retrieval.py tests/test_eval_retrieval.py
git commit -m "eval(§9.1): retrieval precision@5 with LLM-as-judge"
```

---

### Task 8: Eval §9.2 — Ripple tree groundedness

**Files:**
- Create: `eval/ripple_groundedness.py`
- Test: `tests/test_eval_ripple_groundedness.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_eval_ripple_groundedness.py
import pytest
from eval import ripple_groundedness


def test_match_sectors_exact_and_fuzzy():
    tree = {"event": "x", "nodes": [
        {"sector": "Oil Supply", "children": [
            {"sector": "Jet Fuel / Airlines", "children": []},
        ]},
        {"sector": "Shipping", "children": []},
        {"sector": "Crypto Moon Lambo", "children": []},   # hallucinated
    ]}
    truth = ["Oil Supply", "Shipping", "Fertilizer", "Airlines / Jet fuel"]
    result = ripple_groundedness.score(tree, truth)
    # Matched: Oil Supply (exact), Airlines (fuzzy via substring on "Jet Fuel / Airlines"),
    # Shipping (exact). Missed: Fertilizer. Hallucinated: Crypto Moon Lambo.
    assert set(result["matched"]) == {"Oil Supply", "Shipping", "Airlines / Jet fuel"}
    assert set(result["missed"]) == {"Fertilizer"}
    assert set(result["hallucinated"]) == {"Crypto Moon Lambo"}
    assert result["precision"] == pytest.approx(3 / 4)   # 3 correct / 4 AI-generated sectors
    assert result["recall"] == pytest.approx(3 / 4)       # 3 matched / 4 truth sectors


def test_price_change_matches_real_data():
    tree = {"event": "x", "nodes": [
        {"sector": "Oil", "price_change": 49.6, "price_details": [
            {"symbol": "BZ=F", "pct_change": 49.6}], "children": []},
        {"sector": "Gas", "price_change": 50.1, "price_details": [
            {"symbol": "NG=F", "pct_change": 50.1}], "children": []},
    ]}
    actual = {"BZ=F": {"pct_change": 49.60}, "NG=F": {"pct_change": 12.0}}  # Gas is off
    report = ripple_groundedness.check_price_integrity(tree, actual, tolerance=0.5)
    assert report["ok_count"] == 1
    assert report["mismatch_count"] == 1
    assert report["mismatches"][0]["symbol"] == "NG=F"
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_eval_ripple_groundedness.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `eval/ripple_groundedness.py`**

```python
# eval/ripple_groundedness.py
from typing import Dict, List


def _flatten_sectors(tree: Dict) -> List[str]:
    out = []
    def _walk(nodes):
        for n in nodes:
            out.append(n.get("sector", ""))
            _walk(n.get("children", []))
    _walk(tree.get("nodes", []))
    return [s for s in out if s]


def _fuzzy_contains(ai_sector: str, truth_sector: str) -> bool:
    a = ai_sector.lower()
    t = truth_sector.lower()
    # Split truth on " / " to allow e.g. "Airlines / Jet fuel" to match "Jet Fuel".
    parts = [p.strip() for p in t.split("/")] + [t]
    return any(p in a for p in parts if p)


def score(tree: Dict, truth_sectors: List[str]) -> Dict:
    ai_sectors = _flatten_sectors(tree)
    matched_truths = set()
    matched_ai = set()
    for t in truth_sectors:
        for a in ai_sectors:
            if _fuzzy_contains(a, t) or _fuzzy_contains(t, a):
                matched_truths.add(t)
                matched_ai.add(a)
                break
    missed = [t for t in truth_sectors if t not in matched_truths]
    hallucinated = [a for a in ai_sectors if a not in matched_ai]
    precision = len(matched_ai) / len(ai_sectors) if ai_sectors else 0.0
    recall = len(matched_truths) / len(truth_sectors) if truth_sectors else 0.0
    return {
        "ai_sectors": ai_sectors,
        "truth_sectors": truth_sectors,
        "matched": sorted(matched_truths),
        "missed": sorted(missed),
        "hallucinated": sorted(hallucinated),
        "precision": precision,
        "recall": recall,
    }


def check_price_integrity(tree: Dict, actual_changes: Dict, tolerance: float = 0.5) -> Dict:
    """For every node with price_details, confirm each symbol's pct_change matches actual within tolerance."""
    oks: List[Dict] = []
    bads: List[Dict] = []
    def _walk(nodes):
        for n in nodes:
            for d in n.get("price_details", []) or []:
                sym = d.get("symbol")
                claimed = d.get("pct_change")
                actual = (actual_changes.get(sym) or {}).get("pct_change")
                if actual is None or claimed is None:
                    continue
                if abs(claimed - actual) <= tolerance:
                    oks.append({"symbol": sym, "claimed": claimed, "actual": actual})
                else:
                    bads.append({"symbol": sym, "claimed": claimed, "actual": actual,
                                 "delta": claimed - actual})
            _walk(n.get("children", []))
    _walk(tree.get("nodes", []))
    return {"ok_count": len(oks), "mismatch_count": len(bads), "mismatches": bads, "ok": oks}
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_eval_ripple_groundedness.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add eval/ripple_groundedness.py tests/test_eval_ripple_groundedness.py
git commit -m "eval(§9.2): ripple tree sector recall/precision + price integrity"
```

---

### Task 9: Eval §9.3 — QA faithfulness

**Files:**
- Create: `eval/qa_faithfulness.py`
- Test: `tests/test_eval_qa_faithfulness.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_eval_qa_faithfulness.py
from langchain_core.messages import AIMessage
from eval import qa_faithfulness


class _FakeLLM:
    def __init__(self, replies): self._r = list(replies)
    def invoke(self, msgs): return AIMessage(content=self._r.pop(0))


def test_split_sentences():
    s = "Brent hit $111. Oil supply tightened. Fertilizer rose 15%."
    assert qa_faithfulness.split_sentences(s) == [
        "Brent hit $111.", "Oil supply tightened.", "Fertilizer rose 15%."
    ]


def test_faithfulness_per_sentence(monkeypatch):
    monkeypatch.setattr(qa_faithfulness, "run_supervisor", lambda cfg, q, as_of: {
        "intent": "qa",
        "response": {"answer": "Brent rose. Shipping fell.",
                     "citations": [{"url": "u", "headline": "h", "date": "2026-03-01"}]},
        "news_results": [{"text": "Brent surged on Hormuz.", "url": "u",
                          "headline": "Brent surged", "metadata": {"date": "2026-03-01"}, "score": 0.9}],
    })
    monkeypatch.setattr(qa_faithfulness, "get_chat_model", lambda **kw: _FakeLLM(["yes", "no"]))

    from config import load_event
    from datetime import date
    q = {"id": "q1", "query": "What happened?"}
    report = qa_faithfulness.score_query(q, load_event("iran_war"), date(2026, 4, 15))
    assert report["supported_sentences"] == 1
    assert report["total_sentences"] == 2
    assert report["faithfulness"] == 0.5
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_eval_qa_faithfulness.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `eval/qa_faithfulness.py`**

```python
# eval/qa_faithfulness.py
import re
from datetime import date
from typing import Dict, List
from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_chat_model
from agent_supervisor import run as run_supervisor
from config import EventConfig


_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_SYSTEM = (
    "You are a strict faithfulness judge. Given a claim and a context, "
    "answer ONLY 'yes' or 'no': is the claim supported by the context?"
)


def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text: return []
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


def _judge(claim: str, context: str) -> bool:
    llm = get_chat_model(temperature=0.0, max_tokens=5)
    human = f"Claim: {claim}\n\nContext:\n{context[:2000]}\n\nSupported?"
    resp = llm.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=human)])
    return str(resp.content).strip().lower().startswith("y")


def score_query(q: Dict, cfg: EventConfig, as_of: date) -> Dict:
    result = run_supervisor(cfg, q["query"], as_of)
    answer = (result.get("response") or {}).get("answer", "")
    hits = result.get("news_results", [])
    context = "\n\n".join(f"- {h.get('text','')}" for h in hits)
    sentences = split_sentences(answer)
    supported = sum(1 for s in sentences if _judge(s, context))
    total = len(sentences)
    return {"id": q["id"], "query": q["query"], "answer": answer,
            "total_sentences": total, "supported_sentences": supported,
            "faithfulness": supported / total if total else 0.0}


def run_qa_eval(queries: List[Dict], cfg: EventConfig, as_of: date) -> Dict:
    per = [score_query(q, cfg, as_of) for q in queries]
    mean = sum(x["faithfulness"] for x in per) / len(per) if per else 0.0
    return {"metric": "faithfulness", "mean": mean, "per_query": per}
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_eval_qa_faithfulness.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add eval/qa_faithfulness.py tests/test_eval_qa_faithfulness.py
git commit -m "eval(§9.3): QA sentence-level faithfulness"
```

---

### Task 10: Eval §9.4 — Market data integrity

**Files:**
- Create: `eval/market_integrity.py`
- Test: `tests/test_eval_market_integrity.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_eval_market_integrity.py
from datetime import date
from eval import market_integrity


def test_spot_check_matches(monkeypatch):
    monkeypatch.setattr(market_integrity, "get_price_on_date",
                        lambda sym, d: {"BZ=F": 88.5, "XLE": None}.get(sym))
    pairs = [{"symbol": "BZ=F", "date": "2026-03-02"},
             {"symbol": "XLE",  "date": "2026-03-02"}]
    report = market_integrity.run(pairs)
    assert report["ok_count"] == 1
    assert report["missing_count"] == 1
    assert report["results"][0]["close"] == 88.5
    assert report["results"][1]["close"] is None
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_eval_market_integrity.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `eval/market_integrity.py`**

```python
# eval/market_integrity.py
from datetime import date
from typing import Dict, List
from data_market import get_price_on_date


def run(pairs: List[Dict]) -> Dict:
    results = []
    ok = 0
    missing = 0
    for p in pairs:
        d = date.fromisoformat(p["date"])
        close = get_price_on_date(p["symbol"], d)
        results.append({"symbol": p["symbol"], "date": p["date"], "close": close})
        if close is None:
            missing += 1
        else:
            ok += 1
    return {"metric": "market_integrity",
            "ok_count": ok, "missing_count": missing,
            "results": results}
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_eval_market_integrity.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add eval/market_integrity.py tests/test_eval_market_integrity.py
git commit -m "eval(§9.4): market data spot-check integrity"
```

---

### Task 11: `eval/run_eval.py` orchestrator + Markdown report

**Files:**
- Create: `eval/run_eval.py`
- Test: `tests/test_run_eval.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_run_eval.py
import json
from pathlib import Path
from datetime import date
from eval import run_eval


def test_run_eval_writes_report(monkeypatch, tmp_path, fixtures_dir):
    # Patch each sub-eval to return deterministic dicts
    monkeypatch.setattr(run_eval, "run_retrieval_eval",
                        lambda qs, k: {"metric": "precision@5", "mean_precision": 0.8, "per_query": []})
    monkeypatch.setattr(run_eval, "run_qa_eval",
                        lambda qs, cfg, as_of: {"metric": "faithfulness", "mean": 0.9, "per_query": []})
    monkeypatch.setattr(run_eval, "score",
                        lambda tree, truth: {"ai_sectors": [], "truth_sectors": [],
                                             "matched": [], "missed": [], "hallucinated": [],
                                             "precision": 0.75, "recall": 0.85})
    monkeypatch.setattr(run_eval, "check_price_integrity",
                        lambda tree, actual, tolerance=0.5: {"ok_count": 5, "mismatch_count": 0,
                                                             "mismatches": [], "ok": []})
    monkeypatch.setattr(run_eval, "run_market_integrity",
                        lambda pairs: {"metric": "market_integrity", "ok_count": 5,
                                       "missing_count": 0, "results": []})
    monkeypatch.setattr(run_eval, "generate_ripple_tree",
                        lambda event_description, cfg, as_of, max_depth=3: {"event": "x", "nodes": []})
    monkeypatch.setattr(run_eval, "get_price_changes",
                        lambda cfg, as_of: {})

    out_dir = tmp_path / "eval_out"
    report_path = run_eval.main(["--event", "iran_war", "--out-dir", str(out_dir)])
    p = Path(report_path)
    assert p.exists()
    body = p.read_text()
    assert "# Evaluation Report" in body
    assert "precision@5" in body
    assert "0.80" in body or "0.8" in body
    assert "faithfulness" in body
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_run_eval.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `eval/run_eval.py`**

```python
# eval/run_eval.py
"""CLI: python -m eval.run_eval --event iran_war"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict

from config import load_event
from agent_ripple import generate_ripple_tree
from data_market import get_price_changes
from eval.retrieval import run_retrieval_eval
from eval.qa_faithfulness import run_qa_eval
from eval.ripple_groundedness import score, check_price_integrity
from eval.market_integrity import run as run_market_integrity


def _load_queries() -> Dict:
    return json.loads(Path("eval/test_queries.json").read_text())


def _load_ground_truth_sectors() -> list[str]:
    text = Path("eval/wikipedia_ground_truth.md").read_text()
    sectors: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            sectors.append(line[2:].split("(")[0].strip())
    return sectors


def _fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"


def main(argv=None) -> str:
    p = argparse.ArgumentParser()
    p.add_argument("--event", required=True)
    p.add_argument("--as-of", default=None)
    p.add_argument("--out-dir", default="eval/results")
    args = p.parse_args(argv)

    cfg = load_event(args.event)
    as_of = date.fromisoformat(args.as_of) if args.as_of else cfg.end_date
    queries = _load_queries()

    # Run each dimension
    retrieval_report = run_retrieval_eval(queries["retrieval"], k=5)
    qa_report = run_qa_eval(queries["qa"], cfg, as_of)

    tree = generate_ripple_tree(
        "Major macro event: " + cfg.display_name,
        cfg, as_of=as_of, max_depth=3,
    )
    truth_sectors = _load_ground_truth_sectors()
    ripple_report = score(tree, truth_sectors)
    price_integrity_report = check_price_integrity(
        tree, get_price_changes(cfg, as_of=as_of), tolerance=0.5,
    )

    market_report = run_market_integrity(queries["market_integrity"])

    # Assemble Markdown
    md = [
        "# Evaluation Report",
        f"- Event: {cfg.display_name}",
        f"- As of: {as_of.isoformat()}",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## §9.1 Retrieval (precision@5)",
        f"- **Mean precision@5: {retrieval_report['mean_precision']:.2f}**  (target ≥ 0.80)",
        "",
        "## §9.2 Ripple tree groundedness",
        f"- AI-generated sectors: {len(ripple_report['ai_sectors'])}",
        f"- Ground-truth sectors: {len(ripple_report['truth_sectors'])}",
        f"- **Precision: {_fmt_pct(ripple_report['precision'])}** · **Recall: {_fmt_pct(ripple_report['recall'])}**",
        f"- Matched: {', '.join(ripple_report['matched']) or '—'}",
        f"- Missed (truth → not in tree): {', '.join(ripple_report['missed']) or '—'}",
        f"- Hallucinated (tree → not in truth): {', '.join(ripple_report['hallucinated']) or '—'}",
        "",
        f"### Price integrity (within ±0.5%)",
        f"- Matched: {price_integrity_report['ok_count']}   Mismatched: {price_integrity_report['mismatch_count']}",
        "",
        "## §9.3 QA faithfulness",
        f"- **Mean faithfulness: {qa_report['mean']:.2f}**",
        "",
        "## §9.4 Market data integrity",
        f"- Spot checks: {market_report['ok_count']} / {market_report['ok_count'] + market_report['missing_count']}  passed",
        "",
    ]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = out_dir / f"eval-{args.event}-{stamp}.md"
    report_path.write_text("\n".join(md))

    # Also dump raw JSON for further analysis
    (out_dir / f"eval-{args.event}-{stamp}.json").write_text(json.dumps({
        "retrieval": retrieval_report,
        "ripple": ripple_report,
        "price_integrity": price_integrity_report,
        "qa": qa_report,
        "market_integrity": market_report,
    }, indent=2, default=str))

    print(f"Wrote {report_path}")
    return str(report_path)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_run_eval.py -v`
Expected: 1 passed.

- [ ] **Step 5: Dry run on real data** (requires Plan 1 setup complete + API key)

Run: `python -m eval.run_eval --event iran_war`
Expected: `eval/results/eval-iran_war-<timestamp>.md` created; precision@5, faithfulness, ripple precision/recall, and market integrity counts populated. Open the file and sanity-check.

- [ ] **Step 6: Commit**

```bash
git add eval/run_eval.py tests/test_run_eval.py
git commit -m "eval: run_eval CLI writing Markdown + JSON reports"
```

---

### Task 12: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Macro Event Ripple Tracker

Applied Finance project v0.2 — general-purpose macro-event mechanism analyzer.

## Quick start

```bash
conda env create -f environment.yml
conda activate macro-ripple
cp .env.example .env                  # add ANTHROPIC_API_KEY

# One-time data fetch (~3-5 minutes, downloads ~80MB embedding model on first run)
python setup.py --event iran_war

# Run the UI
streamlit run ui_app.py               # → http://localhost:8501

# CLI supervisor (no UI)
python run.py --event iran_war --query "Why did fertilizer prices rise?"

# Run evaluation
python -m eval.run_eval --event iran_war
```

## Structure

- `setup.py` — fetch news + prices for an event
- `data_news/`, `data_market.py` — retrieval / market data layers (M1, M2)
- `agent_ripple.py` — ripple tree generator (M3)
- `agent_supervisor.py` — LangGraph supervisor (M4)
- `ui_app.py`, `ui/` — Streamlit 4-tab interface (M5)
- `eval/` — §9 evaluation harness
- `events/<name>.yaml` — event configuration (keywords, tickers, dates)

## Adding a new event

1. Copy `events/iran_war.yaml` → `events/<your_event>.yaml`, edit keywords + tickers + dates.
2. `python setup.py --event <your_event>`
3. Launch the UI; your event appears in the sidebar.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick-start + structure"
```

---

## Verification Checklist (end of Plan 3)

- [ ] `pytest -v` → all 3-plan tests pass (~35 tests total across Plans 1+2+3)
- [ ] `streamlit run ui_app.py` opens at localhost:8501 and all 4 tabs render real content for the Iran War event
- [ ] Tab 1 shows a chronological timeline with 8–15 items, severity colors visible
- [ ] Tab 2 shows an interactive ripple graph; clicking a node shows mechanism tooltip
- [ ] Tab 3 shows the ranked summary table + 11 Plotly charts with the event marker
- [ ] Tab 4 answers "Why did fertilizer prices rise?" with a grounded answer + source links
- [ ] `python -m eval.run_eval --event iran_war` writes `eval/results/eval-iran_war-*.md` with all four sections populated and no errors

---

## Self-Review Notes

**Spec coverage:**
- §M5 (Streamlit, 4 tabs): ✅ one module per tab
- §9.1 retrieval precision@5 (target ≥ 0.8): ✅ `eval/retrieval.py`
- §9.2 ripple tree vs Wikipedia: ✅ `eval/ripple_groundedness.py` with explicit matched/missed/hallucinated lists + price integrity sub-check
- §9.3 QA faithfulness (LLM-as-judge per sentence): ✅ `eval/qa_faithfulness.py`
- §9.4 market data spot checks: ✅ `eval/market_integrity.py`

**Deferred (spec §11):**
- Event-template UI (§11.1) — adding new events still requires editing a YAML
- Retrospective benchmarks across 3 historical events (§11.1) — harness supports arbitrary event names, but hand-written ground truth is scoped to Iran War
- Knowledge-Graph RAG (§11.3), event-study stats (§11.3), Granger causality (§11.3) — all deferred
- Continuous TruLens loop (§11.5) — MVP uses snapshot eval only

**Type consistency:** all tabs and eval modules consume the exact `AgentState` shape returned by `agent_supervisor.run()` (Plan 2). `ripple_tree` nodes are expected to have `{sector, mechanism, severity, price_change, price_details, supporting_news, children}` — matches Plan 2 Task 7 output.

**Risk to flag before executing:** the live eval run hits the Anthropic API ~40 times (5 retrieval × 5 hits each + 5 QA with ~3–4 sentence judgments + 1 ripple tree generation + intent classification). Rough cost: well under $1 per full eval run at sonnet-4-6 rates.
