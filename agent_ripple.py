"""M3: Ripple tree generator. Produces a structured multi-level impact tree."""
import json
import re
from typing import Dict, List
from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_chat_model
from prompts import load as load_prompt
from config import EventConfig
from data_news import retrieve


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
