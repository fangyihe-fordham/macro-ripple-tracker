# Plan 2 — Agents (M3 Ripple + M4 LangGraph Supervisor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Changes from original (Session 3–4 reconciliation)

The original Plan 2 was written before Plan 1's Round 1 + Round 2 hardening landed. Interfaces and environment state have since shifted. Concrete changes below; all were verified against the code on disk (not against Plan 2's claims about it):

1. **`get_price_changes` return shape (commit `33f88f5`).** Now ALWAYS returns every `cfg.tickers` symbol keyed in the output dict, with an `available: bool` flag plus nullable `baseline / latest / pct_change`. Previously Plan 2 assumed only *available* tickers appeared in the dict and did `if sym in changes:` to gate attachment.
   - **Task 6 test fixture** (`fake_changes`): each entry now includes `"available": True`.
   - **Task 6 `attach_prices` impl**: gate on `changes[sym]["available"]`, not membership. This avoids a `TypeError` on `abs(None)` when a ticker is in `cfg.tickers` but has no CSV / no baseline match.
   - **Task 7 + Task 9 test fixtures**: same `available: True` addition.
2. **`.env` and `.env.example` already exist at repo root** (Plan 1 Session 2, commit `b15ba33`). `.env.example` already declares `ANTHROPIC_API_KEY` and `NEWSAPI_KEY`; `.env` already has both populated per CLAUDE.md. Task 1 Steps 3–4 changed from "create" to "verify".
3. **`python-dotenv==1.0.1` already pinned in `requirements.txt`.** Task 1 Step 1 drops that line from the append list to avoid a duplicate pin.
4. **`langgraph` pin bumped to `0.3.0`** per explicit decision outside this plan. `langchain / langchain-anthropic / langchain-core` pins left as originally scoped.
5. **`retrieve()` can legitimately return `[]`** (empty or absent collection — `vector_store._collection(create=False)` returns `None` when the collection doesn't exist; `retrieve` guards with `coll is None or coll.count() == 0`). Added early-return guards in `run_news_agent` and `run_qa_agent` impls (Tasks 11 + 12) so the LLM isn't prompted with an empty snippet list.
6. **Commit messages must include the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer** per CLAUDE.md Acceptance Criterion #5 (established in Plan 1). Every Task's commit example now shows the HEREDOC form.
7. **Query focus extraction (Session 4).** The original Plan 2 passed `state["query"]` directly to `generate_ripple_tree`, which meant imperative prefixes like "Show me the ripple tree for..." leaked into the LLM's event description input. Intent classifier now returns `{intent, focus}` as JSON; `run_ripple_agent` uses `state["focus"]` with fallback to `cfg.display_name`. Tasks 8 (prompt + state + impl + fixture + tests) and 10 (impl + test) updated. `run_news_agent`, `run_market_agent`, and `run_qa_agent` continue to use `state["query"]` directly — they benefit from the full query text for retrieval.

Non-changes worth noting (verified to still match):

- `retrieve(query, top_k)` signature and hit shape `{text, url, headline, metadata, score}` where `metadata = {url, headline, source, date, source_kind}` — unchanged.
- `config.load_event(name)` signature — unchanged.
- `EventConfig.tickers` items expose `.symbol`, `.name`, `.category` — unchanged.
- `cfg.end_date` is `datetime.date` — unchanged.
- `data_news.__init__` re-exports `retrieve` — unchanged (the `from data_news import retrieve` import in `agent_ripple.py` + `agent_supervisor.py` remains correct).

---

**Prerequisite:** Plan 1 complete — `data_news.retrieve()`, `data_market.get_price_changes()`, `data_market.get_price_range()`, and `config.load_event()` are available and tested. The conda env `macro-ripple` is active.

**Goal:** Build the AI reasoning layer: (M3) a ripple-tree generator that uses Claude Sonnet 4.6 to produce a structured multi-level industry impact tree, grounded with news citations (M1) and market data (M2); and (M4) a LangGraph supervisor that routes user queries to the right sub-agent (timeline / ripple / market / QA) and returns a unified response.

**Architecture:** Two LLM-powered components on top of the data layer. M3 is a stateless function that produces a ripple tree from an event description in three phases: (1) LLM generates causal structure as JSON; (2) each node is enriched with top-k news citations via `retrieve()`; (3) each node with a ticker mapping is enriched with % change from `get_price_changes()`. M4 is a LangGraph `StateGraph` with one entry classifier, four worker nodes (one per intent), and a synthesis node. All LLM calls use `langchain-anthropic`'s `ChatAnthropic` with `claude-sonnet-4-6`; tests inject a `FakeListChatModel` to keep unit tests deterministic and offline.

**Tech Stack:** Existing stack + `langchain==0.3.x`, `langchain-anthropic==0.3.x`, `langchain-core`, `langgraph==0.2.x`. API access via `ANTHROPIC_API_KEY` environment variable (Option A from planning discussion).

---

## File Structure

```
macro-ripple-tracker/
├── llm.py                          # ChatAnthropic factory + model constants
├── agent_ripple.py                 # M3: ripple tree generator (function, not a graph node)
├── prompts/
│   ├── __init__.py
│   ├── ripple_system.txt           # system prompt for tree generation
│   ├── intent_system.txt           # system prompt for intent classification
│   ├── qa_system.txt               # system prompt for grounded Q&A
│   └── timeline_system.txt         # system prompt for timeline summarization
├── agent_supervisor.py             # M4: LangGraph StateGraph + run() entrypoint
├── run.py                          # CLI: python run.py --event iran_war --query "..."
├── tests/
│   ├── test_llm.py
│   ├── test_agent_ripple.py
│   ├── test_agent_supervisor.py
│   └── fixtures/
│       ├── ripple_llm_response.json      # canned LLM JSON for ripple tree
│       └── intent_examples.json          # (query, expected_intent) pairs
```

**Prompts as files, not strings:** separating prompts lets us iterate on them without code churn, and tests can load them to assert structure. Small code files (each ~100–200 lines) stay easy to reason about.

---

### Task 1: Dependencies + API key setup

**Files:**
- Modify: `requirements.txt`
- Create: `.env.example`
- Modify: `.gitignore` (confirm `.env` is ignored — already done in Plan 1)
- Create: `prompts/__init__.py`

- [ ] **Step 1: Append LangChain + LangGraph deps to `requirements.txt`**

Append these lines (note: `python-dotenv==1.0.1` is already pinned on line 2 of `requirements.txt` from Plan 1, so it is NOT re-added here):

```
langchain==0.3.7
langchain-core==0.3.15
langchain-anthropic==0.3.0
langgraph==0.3.0
```

- [ ] **Step 2: Install**

Run: `pip install -r requirements.txt`
Expected: installs without conflicts against Plan 1 deps.

Verify: `python -c "from langchain_anthropic import ChatAnthropic; from langgraph.graph import StateGraph; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verify `.env.example`**

`.env.example` already exists at the repo root from Plan 1 Session 2 (commit `b15ba33`) and declares both `NEWSAPI_KEY` and `ANTHROPIC_API_KEY` as empty-value templates. No changes required. If `RUN_LIVE=` is desired as a template, append it:

```
# Optional: set to 1 to run live integration tests that hit real LLM + APIs
RUN_LIVE=
```

Do NOT overwrite the existing `.env.example` contents — just verify keys are present.

- [ ] **Step 4: Verify `.env`** (local only — gitignored)

`.env` already exists per CLAUDE.md (Session 2) with both `NEWSAPI_KEY` and `ANTHROPIC_API_KEY` populated. Confirm with:

```bash
/opt/anaconda3/envs/macro-ripple/bin/python -c "import config, os; print(bool(os.environ.get('ANTHROPIC_API_KEY')))"
```

Expected: `True`. If `False`, edit `.env` to paste the real key from console.anthropic.com (no quotes, no spaces around `=`). Never stage `.env`.

- [ ] **Step 5: Create `prompts/__init__.py`**

```python
# prompts/__init__.py
from pathlib import Path

_HERE = Path(__file__).parent


def load(name: str) -> str:
    """Load a prompt by filename (without .txt)."""
    return (_HERE / f"{name}.txt").read_text().strip()
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt prompts/__init__.py
git commit -m "$(cat <<'EOF'
chore: add LangChain/LangGraph deps + prompt loader

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Note: `.env.example` is NOT staged — it already exists from Plan 1 and was unchanged in this task.

---

### Task 2: LLM client factory

**Files:**
- Create: `llm.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm.py
import os
import pytest
from llm import get_chat_model, MODEL_ID


def test_model_id_is_sonnet_4_6():
    assert MODEL_ID == "claude-sonnet-4-6"


def test_get_chat_model_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_chat_model()


def test_get_chat_model_returns_chat_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    m = get_chat_model()
    # Loose check: we don't want to bind too tightly to the class internals.
    assert m.__class__.__name__ == "ChatAnthropic"
    assert getattr(m, "model", None) == MODEL_ID or getattr(m, "model_name", None) == MODEL_ID
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm'`

- [ ] **Step 3: Implement `llm.py`**

```python
# llm.py
"""Central LLM client factory. All agents get their chat model from here."""
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()  # pick up .env if present

MODEL_ID = "claude-sonnet-4-6"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4096


def get_chat_model(temperature: float = DEFAULT_TEMPERATURE,
                   max_tokens: int = DEFAULT_MAX_TOKENS) -> ChatAnthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and paste your key."
        )
    return ChatAnthropic(
        model=MODEL_ID,
        temperature=temperature,
        max_tokens=max_tokens,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_llm.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add llm.py tests/test_llm.py
git commit -m "$(cat <<'EOF'
feat: central ChatAnthropic factory pinned to claude-sonnet-4-6

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Ripple tree — LLM structured-output prompt

**Files:**
- Create: `prompts/ripple_system.txt`
- Create: `tests/fixtures/ripple_llm_response.json`

- [ ] **Step 1: Create `prompts/ripple_system.txt`**

```
You are a senior macro analyst. Given a macro / geopolitical event, produce a
multi-level industry impact tree that traces causal ripples across sectors.

Return ONLY valid JSON matching this schema (no prose, no code fences):

{
  "event": "<short event title>",
  "nodes": [
    {
      "sector": "<sector name, concise>",
      "mechanism": "<one sentence: why this sector is affected>",
      "severity": "critical" | "significant" | "moderate",
      "ticker_hints": ["<ticker symbols from the provided list that track this sector>"],
      "children": [ <recursive nodes, same schema, up to max_depth> ]
    }
  ]
}

Rules:
- Depth of nesting must not exceed {max_depth}.
- First-level nodes are the direct-impact sectors (Tier 1).
- Severity reflects expected magnitude and directness: critical = supply/price
  shock within days, significant = meaningful move within weeks, moderate =
  plausible but secondary.
- ticker_hints must be chosen ONLY from the provided ticker list. Leave empty
  if no listed ticker maps cleanly.
- Aim for 3-6 nodes at tier 1, 2-4 children each at deeper tiers.
- Do NOT include price_change or supporting_news — those fields are attached
  downstream; your job is the causal structure.
```

- [ ] **Step 2: Create fixture `tests/fixtures/ripple_llm_response.json`**

```json
{
  "event": "Strait of Hormuz closure",
  "nodes": [
    {
      "sector": "Oil Supply",
      "mechanism": "~25% of seaborne oil transits Hormuz; closure removes supply immediately.",
      "severity": "critical",
      "ticker_hints": ["BZ=F", "CL=F", "XLE"],
      "children": [
        {
          "sector": "Fertilizer Production",
          "mechanism": "Natural gas is the primary feedstock for ammonia; disrupted LNG lifts input costs.",
          "severity": "significant",
          "ticker_hints": ["CF", "NG=F"],
          "children": []
        },
        {
          "sector": "Airline Fuel Costs",
          "mechanism": "Jet fuel tracks crude; airline margins compress.",
          "severity": "significant",
          "ticker_hints": [],
          "children": []
        }
      ]
    },
    {
      "sector": "Shipping",
      "mechanism": "Insurance rates and rerouting costs spike for tankers transiting the region.",
      "severity": "critical",
      "ticker_hints": ["BOAT"],
      "children": []
    },
    {
      "sector": "Defense",
      "mechanism": "Military escalation risk drives defense spending expectations higher.",
      "severity": "moderate",
      "ticker_hints": ["ITA"],
      "children": []
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add prompts/ripple_system.txt tests/fixtures/ripple_llm_response.json
git commit -m "$(cat <<'EOF'
feat(M3): ripple tree prompt + fixture response

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Ripple tree — generate raw structure

**Files:**
- Create: `agent_ripple.py`
- Test: `tests/test_agent_ripple.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_ripple.py
import json
from pathlib import Path
import pytest
from langchain_core.messages import AIMessage
import agent_ripple
from config import load_event


class _FakeLLM:
    """Minimal stand-in for ChatAnthropic: .invoke(messages) -> AIMessage."""
    def __init__(self, reply: str):
        self._reply = reply
    def invoke(self, messages):
        return AIMessage(content=self._reply)


def test_generate_tree_structure(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    monkeypatch.setattr(agent_ripple, "get_chat_model", lambda **kw: _FakeLLM(raw))
    cfg = load_event("iran_war")

    tree = agent_ripple.generate_structure(
        event_description="Strait of Hormuz closed, ~25% seaborne oil blocked",
        cfg=cfg,
        max_depth=3,
    )

    assert tree["event"] == "Strait of Hormuz closure"
    assert len(tree["nodes"]) == 3
    assert tree["nodes"][0]["sector"] == "Oil Supply"
    # Children populated
    assert len(tree["nodes"][0]["children"]) == 2
    # ticker_hints preserved
    assert "BZ=F" in tree["nodes"][0]["ticker_hints"]


def test_generate_structure_rejects_malformed_json(monkeypatch):
    monkeypatch.setattr(agent_ripple, "get_chat_model",
                        lambda **kw: _FakeLLM("not json at all"))
    cfg = load_event("iran_war")
    with pytest.raises(ValueError, match="valid JSON"):
        agent_ripple.generate_structure("x", cfg, max_depth=2)


def test_generate_structure_strips_code_fences(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    wrapped = f"```json\n{raw}\n```"
    monkeypatch.setattr(agent_ripple, "get_chat_model", lambda **kw: _FakeLLM(wrapped))
    cfg = load_event("iran_war")
    tree = agent_ripple.generate_structure("x", cfg, max_depth=3)
    assert tree["event"] == "Strait of Hormuz closure"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_ripple.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_ripple'`

- [ ] **Step 3: Implement `agent_ripple.py` (structure generation only)**

```python
# agent_ripple.py
"""M3: Ripple tree generator. Produces a structured multi-level impact tree."""
import json
import re
from typing import Dict, List
from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_chat_model
from prompts import load as load_prompt
from config import EventConfig


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s.strip()).strip()


def generate_structure(event_description: str, cfg: EventConfig, max_depth: int = 3) -> Dict:
    """Ask the LLM to emit a JSON impact tree. No data enrichment yet."""
    system = load_prompt("ripple_system").replace("{max_depth}", str(max_depth))
    ticker_list = "\n".join(f"- {t.symbol}: {t.name} ({t.category})" for t in cfg.tickers)
    human = (
        f"Event: {event_description}\n\n"
        f"Allowed tickers for ticker_hints (pick only from here):\n{ticker_list}\n\n"
        f"Max depth: {max_depth}\n"
    )
    llm = get_chat_model(temperature=0.2, max_tokens=4096)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    text = _strip_fences(resp.content if isinstance(resp.content, str) else str(resp.content))
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw: {text[:500]}") from e
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_agent_ripple.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agent_ripple.py tests/test_agent_ripple.py
git commit -m "$(cat <<'EOF'
feat(M3): generate ripple tree structure via LLM

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Ripple tree — attach news citations per node

**Files:**
- Modify: `agent_ripple.py`
- Modify: `tests/test_agent_ripple.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_agent_ripple.py`:

```python
def test_attach_news_calls_retrieve_per_node(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    tree = json.loads(raw)

    calls = []
    def fake_retrieve(query, top_k):
        calls.append((query, top_k))
        return [
            {"text": f"article for {query}", "url": f"https://x/{len(calls)}",
             "headline": f"headline {len(calls)}", "metadata": {"date": "2026-03-01"}, "score": 0.9},
        ]
    monkeypatch.setattr(agent_ripple, "retrieve", fake_retrieve)

    enriched = agent_ripple.attach_news(tree, top_k=2)

    # Every node (incl. children, recursive) got a supporting_news list.
    def all_nodes(nodes):
        for n in nodes:
            yield n
            yield from all_nodes(n.get("children", []))

    nodes = list(all_nodes(enriched["nodes"]))
    assert len(nodes) == 5  # 3 top + 2 children under Oil Supply
    for n in nodes:
        assert "supporting_news" in n
        assert len(n["supporting_news"]) >= 1
        assert "url" in n["supporting_news"][0]
    # Queries include the sector name
    assert any("Oil Supply" in q for q, _ in calls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_ripple.py::test_attach_news_calls_retrieve_per_node -v`
Expected: FAIL with `AttributeError: module 'agent_ripple' has no attribute 'attach_news'`

- [ ] **Step 3: Implement `attach_news` in `agent_ripple.py`**

Append to `agent_ripple.py`:

```python
from data_news import retrieve  # Plan 1 public API


def attach_news(tree: Dict, top_k: int = 3) -> Dict:
    """Walk every node and attach supporting_news from retrieve()."""
    def _walk(nodes: List[Dict]) -> None:
        for n in nodes:
            query = f"{n['sector']} {n['mechanism']}"
            hits = retrieve(query, top_k=top_k)
            n["supporting_news"] = [
                {"url": h["url"], "headline": h["headline"],
                 "date": h.get("metadata", {}).get("date", ""),
                 "score": h["score"]}
                for h in hits
            ]
            _walk(n.get("children", []))
    _walk(tree.get("nodes", []))
    return tree
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_agent_ripple.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agent_ripple.py tests/test_agent_ripple.py
git commit -m "$(cat <<'EOF'
feat(M3): attach supporting news citations per tree node

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Ripple tree — attach price data per node

**Files:**
- Modify: `agent_ripple.py`
- Modify: `tests/test_agent_ripple.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_agent_ripple.py`:

```python
def test_attach_prices_uses_ticker_hints(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    tree = json.loads(raw)

    # Post-Plan-1 shape: every ticker keyed, with `available` flag.
    fake_changes = {
        "BZ=F": {"available": True, "baseline": 74.20, "latest": 111.00, "pct_change": 49.60},
        "CL=F": {"available": True, "baseline": 70.00, "latest": 100.00, "pct_change": 42.86},
        "XLE":  {"available": True, "baseline": 95.00, "latest": 118.00, "pct_change": 24.21},
        "CF":   {"available": True, "baseline": 80.00, "latest": 92.00,  "pct_change": 15.00},
        "NG=F": {"available": True, "baseline": 3.00,  "latest": 4.50,   "pct_change": 50.00},
        "BOAT": {"available": True, "baseline": 25.00, "latest": 27.00,  "pct_change": 8.00},
        "ITA":  {"available": True, "baseline": 150.0, "latest": 162.0,  "pct_change": 8.00},
    }
    monkeypatch.setattr(agent_ripple, "get_price_changes",
                        lambda cfg, as_of: fake_changes)

    cfg = load_event("iran_war")
    from datetime import date
    enriched = agent_ripple.attach_prices(tree, cfg, as_of=date(2026, 4, 15))

    oil = enriched["nodes"][0]
    # Takes max-magnitude pct_change across ticker_hints
    assert oil["price_change"] == pytest.approx(49.60)
    assert oil["price_details"][0]["symbol"] in ("BZ=F", "CL=F", "XLE")
    # Node with empty ticker_hints gets None
    airline = oil["children"][1]
    assert airline["price_change"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_ripple.py::test_attach_prices_uses_ticker_hints -v`
Expected: FAIL with `AttributeError: ... 'attach_prices'`

- [ ] **Step 3: Implement `attach_prices`**

Append to `agent_ripple.py`:

```python
from datetime import date
from data_market import get_price_changes


def attach_prices(tree: Dict, cfg: EventConfig, as_of: date) -> Dict:
    """For each node, resolve ticker_hints → pct_change; node gets max-magnitude and details.

    `get_price_changes` always returns every ticker in cfg keyed, with an
    `available` flag. Gate on `available` — unavailable entries have
    None for baseline/latest/pct_change, so mixing them into details would
    break abs(pct_change).
    """
    changes = get_price_changes(cfg, as_of=as_of)

    def _walk(nodes: List[Dict]) -> None:
        for n in nodes:
            hints = n.get("ticker_hints", []) or []
            details = []
            for sym in hints:
                entry = changes.get(sym)
                if entry and entry.get("available"):
                    details.append({"symbol": sym, **entry})
            if details:
                # Attach the largest-magnitude change as the node's headline number
                top = max(details, key=lambda d: abs(d["pct_change"]))
                n["price_change"] = top["pct_change"]
                n["price_details"] = sorted(details, key=lambda d: -abs(d["pct_change"]))
            else:
                n["price_change"] = None
                n["price_details"] = []
            _walk(n.get("children", []))
    _walk(tree.get("nodes", []))
    return tree
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_agent_ripple.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add agent_ripple.py tests/test_agent_ripple.py
git commit -m "$(cat <<'EOF'
feat(M3): attach market data per node from ticker_hints

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Ripple tree — public `generate_ripple_tree` orchestrator

**Files:**
- Modify: `agent_ripple.py`
- Modify: `tests/test_agent_ripple.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_agent_ripple.py`:

```python
def test_generate_ripple_tree_end_to_end(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "ripple_llm_response.json").read_text()
    monkeypatch.setattr(agent_ripple, "get_chat_model", lambda **kw: _FakeLLM(raw))
    monkeypatch.setattr(agent_ripple, "retrieve",
                        lambda q, top_k: [{"text": "x", "url": "u", "headline": "h",
                                           "metadata": {"date": "2026-03-01"}, "score": 0.8}])
    monkeypatch.setattr(agent_ripple, "get_price_changes",
                        lambda cfg, as_of: {"BZ=F": {"available": True, "baseline": 74.2, "latest": 111.0, "pct_change": 49.6}})

    cfg = load_event("iran_war")
    from datetime import date
    tree = agent_ripple.generate_ripple_tree(
        event_description="Strait of Hormuz closed",
        cfg=cfg,
        as_of=date(2026, 4, 15),
        max_depth=3,
    )
    assert tree["event"]
    oil = tree["nodes"][0]
    assert oil["supporting_news"][0]["url"] == "u"
    assert oil["price_change"] == pytest.approx(49.6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_ripple.py::test_generate_ripple_tree_end_to_end -v`
Expected: FAIL with `AttributeError: ... 'generate_ripple_tree'`

- [ ] **Step 3: Implement orchestrator**

Append to `agent_ripple.py`:

```python
def generate_ripple_tree(event_description: str, cfg: EventConfig, as_of: date,
                         max_depth: int = 3, news_top_k: int = 3) -> Dict:
    """Public entrypoint: structure → news → prices."""
    tree = generate_structure(event_description, cfg, max_depth=max_depth)
    tree = attach_news(tree, top_k=news_top_k)
    tree = attach_prices(tree, cfg, as_of=as_of)
    return tree
```

- [ ] **Step 4: Run full agent_ripple tests**

Run: `pytest tests/test_agent_ripple.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add agent_ripple.py tests/test_agent_ripple.py
git commit -m "$(cat <<'EOF'
feat(M3): public generate_ripple_tree orchestrator

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Supervisor — state + intent classifier node

**Files:**
- Create: `prompts/intent_system.txt`
- Create: `tests/fixtures/intent_examples.json`
- Create: `agent_supervisor.py`
- Test: `tests/test_agent_supervisor.py`

- [ ] **Step 1: Create `prompts/intent_system.txt`**

```
Classify the user query and extract its focus. Respond with ONLY a JSON object
(no code fences, no prose):

{"intent": "<one of: timeline | ripple | market | qa>", "focus": "<2-6 word noun phrase or empty string>"}

Intents:
- timeline: user wants a chronological list of key events
- ripple:   user wants a multi-level industry impact / causal diagram
- market:   user wants price changes / chart data for specific tickers or sectors
- qa:       anything else — free-form question about the event, needs grounded answer

Focus rules:
- focus is a 2-6 word noun phrase describing the event or sub-topic the user
  cares about. Examples: "Hormuz closure", "oil price reaction",
  "fertilizer price increase".
- Strip imperative verbs ("show me", "tell me", "draw", "what about"),
  trailing question marks, and generic filler ("the ripple tree for",
  "the impact of", "give me").
- If the query is too vague to extract a focus (e.g. "what happened?",
  "???"), return "focus": "" — downstream code falls back to the event's
  display name.
- Do NOT invent topics not present in the query. Prefer empty over guessed.

Output JSON only. No code fences. No prose.
```

- [ ] **Step 2: Create `tests/fixtures/intent_examples.json`**

```json
[
  ["What happened on March 2?", "timeline", ""],
  ["Show me the key events in order.", "timeline", ""],
  ["How did oil price react?", "market", "oil price reaction"],
  ["What's the % change in Brent since the war started?", "market", "Brent price change"],
  ["What industries are affected and why?", "ripple", ""],
  ["Show me the ripple tree for Hormuz closure", "ripple", "Hormuz closure"],
  ["Why did fertilizer prices go up?", "qa", "fertilizer price increase"],
  ["Is there a link between Hormuz and aluminum?", "qa", "Hormuz and aluminum link"]
]
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_agent_supervisor.py
import json
import pytest
from langchain_core.messages import AIMessage
import agent_supervisor
from config import load_event


class _FakeLLM:
    def __init__(self, replies):
        self._replies = list(replies)
    def invoke(self, messages):
        return AIMessage(content=self._replies.pop(0))


def test_classify_intent_all_examples(monkeypatch, fixtures_dir):
    examples = json.loads((fixtures_dir / "intent_examples.json").read_text())
    # LLM now returns JSON with both intent and focus.
    replies = [json.dumps({"intent": intent, "focus": focus})
               for _, intent, focus in examples]
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM(replies))

    for query, expected_intent, expected_focus in examples:
        state = {"query": query}
        out = agent_supervisor.classify_intent(state)
        assert out["intent"] == expected_intent
        assert out["focus"] == expected_focus


def test_classify_intent_defaults_to_qa_on_garbage(monkeypatch):
    # LLM returns JSON but with an invalid intent value — should fall back to qa.
    monkeypatch.setattr(agent_supervisor, "get_chat_model",
                        lambda **kw: _FakeLLM([json.dumps({"intent": "gibberish", "focus": ""})]))
    out = agent_supervisor.classify_intent({"query": "???"})
    assert out["intent"] == "qa"
    assert out["focus"] == ""


def test_classify_intent_malformed_json_falls_back_to_qa_empty_focus(monkeypatch):
    # LLM returns non-JSON garbage — should not crash; falls back to qa + "".
    monkeypatch.setattr(agent_supervisor, "get_chat_model",
                        lambda **kw: _FakeLLM(["not json at all"]))
    out = agent_supervisor.classify_intent({"query": "???"})
    assert out["intent"] == "qa"
    assert out["focus"] == ""
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_supervisor'`

- [ ] **Step 5: Implement state schema + classify_intent**

```python
# agent_supervisor.py
"""M4: LangGraph supervisor. Routes queries to the right sub-agent."""
import json
import re
from typing import Literal, Optional, TypedDict, List, Dict
from datetime import date

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from llm import get_chat_model
from prompts import load as load_prompt
from config import EventConfig

Intent = Literal["timeline", "ripple", "market", "qa"]
_VALID_INTENTS = {"timeline", "ripple", "market", "qa"}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s.strip()).strip()


class AgentState(TypedDict, total=False):
    query: str
    cfg: EventConfig
    as_of: date
    intent: Intent
    focus: str
    news_results: List[Dict]
    market_data: Dict
    ripple_tree: Dict
    timeline: List[Dict]
    response: Dict


def classify_intent(state: AgentState) -> AgentState:
    """Ask the LLM to classify intent AND extract a focus phrase in one call.

    Returns {"intent", "focus"}. Any parse error or invalid value degrades
    gracefully: intent → "qa", focus → "". Never raises.
    """
    system = load_prompt("intent_system")
    # Bumped from 10 → 100 tokens to accommodate the JSON payload
    # (intent + focus can be ~40-60 tokens including braces and quoting).
    llm = get_chat_model(temperature=0.0, max_tokens=100)
    resp = llm.invoke([SystemMessage(content=system),
                       HumanMessage(content=state["query"])])
    raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"intent": "qa", "focus": ""}
    word = str(parsed.get("intent", "")).strip().lower()
    intent: Intent = word if word in _VALID_INTENTS else "qa"  # type: ignore[assignment]
    focus = str(parsed.get("focus", "")).strip()
    return {"intent": intent, "focus": focus}
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add prompts/intent_system.txt tests/fixtures/intent_examples.json agent_supervisor.py tests/test_agent_supervisor.py
git commit -m "$(cat <<'EOF'
feat(M4): AgentState + intent classifier node

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Supervisor — market node

**Files:**
- Modify: `agent_supervisor.py`
- Modify: `tests/test_agent_supervisor.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_agent_supervisor.py`:

```python
def test_run_market_agent_returns_dict(monkeypatch):
    fake_changes = {
        "BZ=F": {"available": True, "baseline": 74.20, "latest": 111.00, "pct_change": 49.60},
        "XLE":  {"available": True, "baseline": 95.00, "latest": 118.00, "pct_change": 24.21},
    }
    monkeypatch.setattr(agent_supervisor, "get_price_changes",
                        lambda cfg, as_of: fake_changes)
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "how did oil move?", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_market_agent(state)
    assert out["market_data"] == fake_changes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_supervisor.py::test_run_market_agent_returns_dict -v`
Expected: FAIL with `AttributeError: ... 'run_market_agent'`

- [ ] **Step 3: Implement market node**

Append to `agent_supervisor.py`:

```python
from data_market import get_price_changes, get_price_range


def run_market_agent(state: AgentState) -> AgentState:
    changes = get_price_changes(state["cfg"], as_of=state["as_of"])
    return {"market_data": changes}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agent_supervisor.py tests/test_agent_supervisor.py
git commit -m "$(cat <<'EOF'
feat(M4): market agent node

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Supervisor — ripple node

**Files:**
- Modify: `agent_supervisor.py`
- Modify: `tests/test_agent_supervisor.py`

- [ ] **Step 1: Add failing test**

```python
def test_run_ripple_agent_uses_focus(monkeypatch):
    """When state["focus"] is populated, it becomes the event_description
    passed to generate_ripple_tree — NOT the raw user query (which may
    contain imperative prefixes like "Show me the ripple tree for...")."""
    called = {}
    def fake_generate(event_description, cfg, as_of, max_depth=3, news_top_k=3):
        called["args"] = (event_description, cfg.name, as_of, max_depth)
        return {"event": event_description, "nodes": []}
    monkeypatch.setattr(agent_supervisor, "generate_ripple_tree", fake_generate)

    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "Show me the ripple tree for Hormuz closure",
             "focus": "Hormuz closure",
             "cfg": cfg,
             "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_ripple_agent(state)
    # First positional arg = event_description = focus, NOT the raw query.
    assert called["args"][0] == "Hormuz closure"
    assert called["args"][1] == "iran_war"
    assert out["ripple_tree"]["event"] == "Hormuz closure"


def test_run_ripple_agent_falls_back_to_display_name(monkeypatch):
    """When focus is empty or missing, fall back to cfg.display_name."""
    called = {}
    def fake_generate(event_description, cfg, as_of, max_depth=3, news_top_k=3):
        called["args"] = (event_description,)
        return {"event": event_description, "nodes": []}
    monkeypatch.setattr(agent_supervisor, "generate_ripple_tree", fake_generate)

    cfg = load_event("iran_war")
    from datetime import date
    # No focus key at all — simulates classify_intent returning focus="" and
    # upstream pruning, or focus present but empty string.
    state = {"query": "What industries are affected and why?",
             "focus": "",
             "cfg": cfg,
             "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_ripple_agent(state)
    assert called["args"][0] == cfg.display_name
    assert out["ripple_tree"]["event"] == cfg.display_name
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_agent_supervisor.py::test_run_ripple_agent_uses_focus -v`
Expected: FAIL with `AttributeError: ... 'run_ripple_agent'`

- [ ] **Step 3: Implement ripple node**

Append to `agent_supervisor.py`:

```python
from agent_ripple import generate_ripple_tree


def run_ripple_agent(state: AgentState) -> AgentState:
    # Use the focus phrase extracted by classify_intent; fall back to the
    # event's display_name when focus is empty or missing. Passing the raw
    # query would leak imperative prefixes ("Show me the ripple tree for...")
    # into the LLM's event_description input.
    event_description = state.get("focus") or state["cfg"].display_name
    tree = generate_ripple_tree(
        event_description=event_description,
        cfg=state["cfg"],
        as_of=state["as_of"],
    )
    return {"ripple_tree": tree}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add agent_supervisor.py tests/test_agent_supervisor.py
git commit -m "$(cat <<'EOF'
feat(M4): ripple agent node wraps M3

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Supervisor — timeline node

**Files:**
- Create: `prompts/timeline_system.txt`
- Modify: `agent_supervisor.py`
- Modify: `tests/test_agent_supervisor.py`

- [ ] **Step 1: Create `prompts/timeline_system.txt`**

```
You are a macro-event chronicler. Given a set of news snippets and dates,
produce a compact chronological timeline of the KEY events (not every article).

Return ONLY JSON, no code fences:
[
  {"date": "YYYY-MM-DD", "headline": "<canonical headline>", "impact_summary": "<one sentence>"},
  ...
]

Rules:
- Sort ascending by date.
- Merge duplicates across sources; pick the most informative headline.
- Aim for 8-15 items.
- impact_summary is one sentence on why this event matters for markets.
```

- [ ] **Step 2: Add failing test**

```python
def test_run_news_agent_produces_timeline(monkeypatch):
    fake_hits = [
        {"text": "Iran closed Strait", "url": "u1", "headline": "Iran closes Hormuz",
         "metadata": {"date": "2026-02-28"}, "score": 0.9},
        {"text": "oil jumps", "url": "u2", "headline": "Brent tops $100",
         "metadata": {"date": "2026-03-01"}, "score": 0.85},
    ]
    monkeypatch.setattr(agent_supervisor, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM([
        json.dumps([
            {"date": "2026-02-28", "headline": "Iran closes Hormuz",
             "impact_summary": "Seaborne oil transit halted."},
            {"date": "2026-03-01", "headline": "Brent tops $100",
             "impact_summary": "Crude spikes ~35% in 24h."},
        ])
    ]))
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "Timeline of key events", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_news_agent(state)
    assert len(out["timeline"]) == 2
    assert out["timeline"][0]["date"] == "2026-02-28"
    assert "news_results" in out
    assert len(out["news_results"]) == 2
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_agent_supervisor.py::test_run_news_agent_produces_timeline -v`
Expected: FAIL with `AttributeError: ... 'run_news_agent'`

- [ ] **Step 4: Implement `run_news_agent`**

Append to `agent_supervisor.py`:

```python
import json
from data_news import retrieve


def run_news_agent(state: AgentState) -> AgentState:
    hits = retrieve(state["query"], top_k=20)
    # retrieve() returns [] when the Chroma collection is missing or empty
    # (setup.py never ran, or no articles survived dedup). Short-circuit so we
    # don't hand an empty snippet list to the LLM and get a hallucinated timeline.
    if not hits:
        return {"news_results": [], "timeline": []}
    bullets = "\n".join(
        f"- [{h.get('metadata', {}).get('date', '')}] {h.get('headline','')}: {h.get('text','')[:200]}"
        for h in hits
    )
    system = load_prompt("timeline_system")
    human = f"News snippets:\n{bullets}"
    llm = get_chat_model(temperature=0.1, max_tokens=2048)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    try:
        timeline = json.loads(text.strip().strip("`").removeprefix("json").strip())
    except json.JSONDecodeError:
        timeline = []
    return {"news_results": hits, "timeline": timeline}
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add prompts/timeline_system.txt agent_supervisor.py tests/test_agent_supervisor.py
git commit -m "$(cat <<'EOF'
feat(M4): news/timeline agent node

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Supervisor — QA node (RAG with citations)

**Files:**
- Create: `prompts/qa_system.txt`
- Modify: `agent_supervisor.py`
- Modify: `tests/test_agent_supervisor.py`

- [ ] **Step 1: Create `prompts/qa_system.txt`**

```
You are a careful macro-finance assistant. Answer the user's question using ONLY
the provided article snippets. If the snippets don't contain the answer, say so.

Format your response as JSON, no code fences:
{
  "answer": "<2-4 sentence answer>",
  "citations": [ {"url": "...", "headline": "...", "date": "YYYY-MM-DD"}, ... ]
}

Rules:
- Every factual claim must be supported by at least one snippet; cite its URL.
- Do not invent URLs, dates, or headlines.
- Keep the answer tight. No hedging filler.
```

- [ ] **Step 2: Add failing test**

```python
def test_run_qa_agent_grounded_answer(monkeypatch):
    fake_hits = [
        {"text": "Brent rose to $111 on 2026-03-04", "url": "u1",
         "headline": "Brent hits 111", "metadata": {"date": "2026-03-04"}, "score": 0.9},
    ]
    monkeypatch.setattr(agent_supervisor, "retrieve", lambda q, top_k: fake_hits)
    monkeypatch.setattr(agent_supervisor, "get_chat_model", lambda **kw: _FakeLLM([
        json.dumps({"answer": "Brent hit $111 on March 4.",
                    "citations": [{"url": "u1", "headline": "Brent hits 111", "date": "2026-03-04"}]})
    ]))
    cfg = load_event("iran_war")
    from datetime import date
    state = {"query": "How high did Brent go?", "cfg": cfg, "as_of": date(2026, 4, 15)}
    out = agent_supervisor.run_qa_agent(state)
    assert out["response"]["answer"].startswith("Brent hit $111")
    assert out["response"]["citations"][0]["url"] == "u1"
    assert len(out["news_results"]) == 1
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_agent_supervisor.py::test_run_qa_agent_grounded_answer -v`
Expected: FAIL with `AttributeError: ... 'run_qa_agent'`

- [ ] **Step 4: Implement `run_qa_agent`**

Append to `agent_supervisor.py`:

```python
def run_qa_agent(state: AgentState) -> AgentState:
    hits = retrieve(state["query"], top_k=8)
    # retrieve() can legitimately return []; respecting the grounded-only
    # contract of the QA prompt means answering honestly rather than hallucinating.
    if not hits:
        return {
            "news_results": [],
            "response": {"answer": "No indexed articles match this question.", "citations": []},
        }
    snippets = "\n\n".join(
        f"[{i+1}] url={h.get('url','')} date={h.get('metadata', {}).get('date','')}"
        f"\nheadline: {h.get('headline','')}\n{h.get('text','')[:600]}"
        for i, h in enumerate(hits)
    )
    system = load_prompt("qa_system")
    human = f"Question: {state['query']}\n\nArticle snippets:\n{snippets}"
    llm = get_chat_model(temperature=0.1, max_tokens=1024)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    try:
        answer = json.loads(text.strip().strip("`").removeprefix("json").strip())
    except json.JSONDecodeError:
        answer = {"answer": text.strip(), "citations": []}
    return {"news_results": hits, "response": answer}
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add prompts/qa_system.txt agent_supervisor.py tests/test_agent_supervisor.py
git commit -m "$(cat <<'EOF'
feat(M4): QA agent node with grounded citations

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Supervisor — synthesize node + graph assembly

**Files:**
- Modify: `agent_supervisor.py`
- Modify: `tests/test_agent_supervisor.py`

- [ ] **Step 1: Add failing test**

```python
def test_build_graph_routes_by_intent(monkeypatch, fixtures_dir):
    # Each agent writes a distinct marker; we verify only the routed one ran.
    monkeypatch.setattr(agent_supervisor, "classify_intent",
                        lambda s: {"intent": "market"})
    monkeypatch.setattr(agent_supervisor, "run_market_agent",
                        lambda s: {"market_data": {"BZ=F": {"pct_change": 49.6}}})
    monkeypatch.setattr(agent_supervisor, "run_ripple_agent",
                        lambda s: {"ripple_tree": {"touched": True}})
    monkeypatch.setattr(agent_supervisor, "run_news_agent",
                        lambda s: {"timeline": [{"touched": True}]})
    monkeypatch.setattr(agent_supervisor, "run_qa_agent",
                        lambda s: {"response": {"touched": True}})

    app = agent_supervisor.build_graph()
    cfg = load_event("iran_war")
    from datetime import date
    final = app.invoke({"query": "how did oil move?", "cfg": cfg, "as_of": date(2026, 4, 15)})
    assert final["intent"] == "market"
    assert "market_data" in final
    # Untouched branches stay absent
    assert "ripple_tree" not in final
    assert "timeline" not in final


def test_run_end_to_end_helper(monkeypatch):
    monkeypatch.setattr(agent_supervisor, "classify_intent",
                        lambda s: {"intent": "qa"})
    monkeypatch.setattr(agent_supervisor, "run_qa_agent",
                        lambda s: {"response": {"answer": "ok", "citations": []}})
    cfg = load_event("iran_war")
    from datetime import date
    out = agent_supervisor.run(cfg, "what happened?", as_of=date(2026, 4, 15))
    assert out["intent"] == "qa"
    assert out["response"]["answer"] == "ok"
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_agent_supervisor.py::test_build_graph_routes_by_intent -v`
Expected: FAIL with `AttributeError: ... 'build_graph'`

- [ ] **Step 3: Implement `build_graph` and `run`**

Append to `agent_supervisor.py`:

```python
def _route(state: AgentState) -> str:
    return state.get("intent", "qa")


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("run_news_agent", run_news_agent)
    graph.add_node("run_market_agent", run_market_agent)
    graph.add_node("run_ripple_agent", run_ripple_agent)
    graph.add_node("run_qa_agent", run_qa_agent)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route,
        {
            "timeline": "run_news_agent",
            "market": "run_market_agent",
            "ripple": "run_ripple_agent",
            "qa": "run_qa_agent",
        },
    )
    graph.add_edge("run_news_agent", END)
    graph.add_edge("run_market_agent", END)
    graph.add_edge("run_ripple_agent", END)
    graph.add_edge("run_qa_agent", END)
    return graph.compile()


def run(cfg: EventConfig, query: str, as_of: date) -> AgentState:
    app = build_graph()
    return app.invoke({"query": query, "cfg": cfg, "as_of": as_of})
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_agent_supervisor.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add agent_supervisor.py tests/test_agent_supervisor.py
git commit -m "$(cat <<'EOF'
feat(M4): LangGraph graph assembly + run() entrypoint

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: `run.py` CLI wrapper

**Files:**
- Create: `run.py`

- [ ] **Step 1: Implement `run.py`**

```python
# run.py
"""CLI: python run.py --event iran_war --query "..." [--as-of YYYY-MM-DD]"""
import argparse
import json
import sys
from datetime import date

from config import load_event
import agent_supervisor


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--event", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--as-of", default=None, help="YYYY-MM-DD; defaults to event end_date")
    args = p.parse_args(argv)

    cfg = load_event(args.event)
    as_of = date.fromisoformat(args.as_of) if args.as_of else cfg.end_date
    result = agent_supervisor.run(cfg, args.query, as_of=as_of)

    # Strip non-serializable cfg from output
    out = {k: v for k, v in result.items() if k != "cfg"}
    # dates → ISO
    if isinstance(out.get("as_of"), date):
        out["as_of"] = out["as_of"].isoformat()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry-run with mocked LLM env test** (no new tests — `run.py` is a thin CLI shell already covered by `test_run_end_to_end_helper`)

- [ ] **Step 3: Live smoke test (only if setup.py from Plan 1 already ran)**

Run: `python run.py --event iran_war --query "How did oil react to Hormuz closure?"`
Expected: JSON printed to stdout with `"intent": "market"` or `"qa"` and populated fields. Requires `ANTHROPIC_API_KEY` in `.env` and prior `python setup.py --event iran_war`.

- [ ] **Step 4: Commit**

```bash
git add run.py
git commit -m "$(cat <<'EOF'
feat: run.py CLI entrypoint for supervisor

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Live integration smoke test (gated)

**Files:**
- Create: `tests/test_live_agents.py`

- [ ] **Step 1: Write gated live test**

```python
# tests/test_live_agents.py
"""Hits real Anthropic API. Run with: RUN_LIVE=1 pytest tests/test_live_agents.py -v"""
import os
from datetime import date
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1",
    reason="Live integration test. Set RUN_LIVE=1 to enable.",
)


def test_classify_intent_live():
    from config import load_event
    import agent_supervisor
    out = agent_supervisor.classify_intent({"query": "How did oil price react to Iran war?"})
    assert out["intent"] in {"timeline", "market", "ripple", "qa"}


def test_ripple_tree_live():
    """Requires setup.py to have populated the news + price stores."""
    from config import load_event
    from agent_ripple import generate_ripple_tree
    cfg = load_event("iran_war")
    tree = generate_ripple_tree(
        "Strait of Hormuz closed, blocking ~25% of seaborne oil",
        cfg, as_of=cfg.end_date, max_depth=2,
    )
    assert tree["event"]
    assert len(tree["nodes"]) >= 2
    # Each top-level node should have news citations
    for n in tree["nodes"]:
        assert "supporting_news" in n
```

- [ ] **Step 2: Run (manual, optional)**

Run: `RUN_LIVE=1 pytest tests/test_live_agents.py -v`
Expected (requires API key + completed Plan 1 setup): 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_live_agents.py
git commit -m "$(cat <<'EOF'
test: gated live integration tests for M3+M4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Verification Checklist (end of Plan 2)

- [ ] `pytest -v` → all Plan 1 + Plan 2 unit tests pass (~24 tests total)
- [ ] `ANTHROPIC_API_KEY` in `.env` works — `python -c "from llm import get_chat_model; get_chat_model().invoke([{'role':'user','content':'hi'}])"` returns a response
- [ ] `python run.py --event iran_war --query "How did oil react?"` returns a populated `market_data` dict
- [ ] `python run.py --event iran_war --query "Show me the ripple tree"` returns a `ripple_tree` with ≥ 3 top-level nodes, each with `supporting_news` and `price_change`
- [ ] `python run.py --event iran_war --query "Timeline of the crisis"` returns a `timeline` list of 8–15 dated items
- [ ] `python run.py --event iran_war --query "Why did fertilizer prices go up?"` returns a grounded `response.answer` with ≥ 1 citation

---

## Self-Review Notes

**Spec coverage:**
- §M3 (Ripple Agent): ✅ `generate_structure` → `attach_news` → `attach_prices` matches the four-step spec; minor deviation — we pick ticker_hints from a known list instead of an open-ended ReAct tool-call loop (simpler, deterministic, testable; still grounded via the enrichment passes)
- §M4 (Supervisor): ✅ state fields match spec; 4 intents + classifier + synthesize (synthesize inlined into each worker's return)
- §M4 tool table: we don't expose LangChain `@tool`-decorated tools to the LLM because the supervisor uses a classifier-router pattern, not a tool-calling ReAct loop — this is explicitly noted in the report's architecture section

**Deviation:** spec §M3 Step 1 says "LLM generates impact tree" then "Agent calls M1.retrieve()" per node. This plan keeps generation and enrichment as three separate deterministic phases rather than a ReAct loop — easier to test, and the causal-structure quality doesn't benefit from interleaving retrieval (the model has strong priors from pretraining). If evaluation (Plan 3 §9.2) shows poor groundedness, add a refinement pass in follow-up work.

**Type consistency:** `retrieve()` return shape (from Plan 1) is consumed in `attach_news`, `run_news_agent`, `run_qa_agent` — all expect `{text, url, headline, metadata, score}`. `retrieve()` may return `[]` when the Chroma collection is missing or empty; `attach_news` is naturally safe (iteration over empty list attaches `supporting_news=[]`), and `run_news_agent` / `run_qa_agent` short-circuit explicitly. `get_price_changes()` return shape `{symbol: {available, baseline, latest, pct_change}}` — every `cfg.tickers` symbol is always keyed, and `available` gates the numeric fields. `attach_prices` checks `entry["available"]` before using `pct_change` (otherwise `abs(None)` would blow up); `run_market_agent` passes the whole dict through unchanged, letting downstream UI / formatters read the `available` flag directly.

**Deferred / out of scope for Plan 2:**
- Streamlit rendering of these outputs (Plan 3)
- Automated evaluation of ripple tree / QA faithfulness (Plan 3 §9)
- Real-time / incremental (§11.4)
