"""M3: Ripple tree generator. Produces a structured multi-level impact tree."""
import json
from datetime import date
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from config import EventConfig
from data_market import get_price_changes
from data_news import retrieve
from llm import get_chat_model, strip_fences
from prompts import load as load_prompt


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
    text = strip_fences(resp.content if isinstance(resp.content, str) else str(resp.content))
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
                {"url": h.get("url", ""), "headline": h.get("headline", ""),
                 "date": h.get("metadata", {}).get("date", ""),
                 "score": h.get("score", 0.0)}
                for h in hits
            ]
            _walk(n.get("children", []))
    _walk(tree.get("nodes", []))
    return tree


def attach_prices(tree: Dict, cfg: EventConfig, as_of: date) -> Dict:
    """For each node, resolve ticker_hints -> pct_change; node gets max-magnitude and details."""
    changes = get_price_changes(cfg, as_of=as_of)

    def _walk(nodes: List[Dict]) -> None:
        for n in nodes:
            hints = n.get("ticker_hints", []) or []
            details = []
            for sym in hints:
                entry = changes.get(sym)
                # `available=True` should imply pct_change is numeric, but
                # guard explicitly — a future divide-by-zero path in
                # get_price_changes could otherwise make abs(None) crash.
                if entry and entry.get("available") and entry.get("pct_change") is not None:
                    details.append({"symbol": sym, **entry})
            if details:
                top = max(details, key=lambda d: abs(d["pct_change"]))
                n["price_change"] = top["pct_change"]
                n["price_details"] = sorted(details, key=lambda d: -abs(d["pct_change"]))
            else:
                n["price_change"] = None
                n["price_details"] = []
            _walk(n.get("children", []))
    _walk(tree.get("nodes", []))
    return tree


def generate_ripple_tree(event_description: str, cfg: EventConfig, as_of: date,
                         max_depth: int = 3, news_top_k: int = 3) -> Dict:
    """Public entrypoint: structure -> news -> prices."""
    tree = generate_structure(event_description, cfg, max_depth=max_depth)
    tree = attach_news(tree, top_k=news_top_k)
    tree = attach_prices(tree, cfg, as_of=as_of)
    return tree
