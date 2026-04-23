"""M4: LangGraph supervisor. Routes queries to the right sub-agent."""
import json
from datetime import date
from typing import Dict, List, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from config import EventConfig
from llm import get_chat_model, strip_fences
from prompts import load as load_prompt

Intent = Literal["timeline", "ripple", "market", "qa"]
_VALID_INTENTS = {"timeline", "ripple", "market", "qa"}


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

    Returns a partial AgentState ({"intent", "focus"}); LangGraph merges the
    delta into the full state. Any parse error or invalid value degrades
    gracefully: intent -> "qa", focus -> "". Never raises.
    """
    system = load_prompt("intent_system")
    # Bumped from 10 -> 100 tokens to accommodate the JSON payload
    # (intent + focus can be ~40-60 tokens including braces and quoting).
    llm = get_chat_model(temperature=0.0, max_tokens=100)
    resp = llm.invoke([SystemMessage(content=system),
                       HumanMessage(content=state["query"])])
    raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    text = strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"intent": "qa", "focus": ""}
    word = str(parsed.get("intent", "")).strip().lower()
    intent: Intent = word if word in _VALID_INTENTS else "qa"  # type: ignore[assignment]
    focus = str(parsed.get("focus", "")).strip()
    return {"intent": intent, "focus": focus}


from data_market import get_price_changes, get_price_range


def run_market_agent(state: AgentState) -> AgentState:
    changes = get_price_changes(state["cfg"], as_of=state["as_of"])
    return {"market_data": changes}


from agent_ripple import generate_ripple_tree


def run_ripple_agent(state: AgentState) -> AgentState:
    # Use the focus phrase from classify_intent; fall back to display_name
    # when focus is empty or missing. Passing the raw query would leak
    # imperative prefixes ("Show me the ripple tree for...") into the LLM's
    # event_description input.
    event_description = state.get("focus") or state["cfg"].display_name
    tree = generate_ripple_tree(
        event_description=event_description,
        cfg=state["cfg"],
        as_of=state["as_of"],
    )
    return {"ripple_tree": tree}


from data_news import retrieve


def run_news_agent(state: AgentState) -> AgentState:
    hits = retrieve(state["query"], top_k=20)
    # retrieve() returns [] when the Chroma collection is missing or empty.
    # Short-circuit so the LLM isn't prompted with an empty snippet list.
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
    text = strip_fences(resp.content if isinstance(resp.content, str) else str(resp.content))
    try:
        timeline = json.loads(text)
    except json.JSONDecodeError:
        timeline = []
    return {"news_results": hits, "timeline": timeline}


def run_qa_agent(state: AgentState) -> AgentState:
    hits = retrieve(state["query"], top_k=8)
    # retrieve() can legitimately return []; respect the grounded-only QA
    # contract by answering honestly rather than hallucinating.
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
    text = strip_fences(resp.content if isinstance(resp.content, str) else str(resp.content))
    try:
        answer = json.loads(text)
    except json.JSONDecodeError:
        answer = {"answer": text.strip(), "citations": []}
    return {"news_results": hits, "response": answer}
