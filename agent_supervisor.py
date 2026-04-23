"""M4: LangGraph supervisor. Routes queries to the right sub-agent."""
import json
import re
from typing import Literal, TypedDict, List, Dict
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
    gracefully: intent -> "qa", focus -> "". Never raises.
    """
    system = load_prompt("intent_system")
    # Bumped from 10 -> 100 tokens to accommodate the JSON payload
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
