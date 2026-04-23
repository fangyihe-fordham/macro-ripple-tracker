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
