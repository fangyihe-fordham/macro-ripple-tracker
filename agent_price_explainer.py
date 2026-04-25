"""Price Explainer — leaf agent answering 'why did <ticker> move on <date>?'.

Called directly by the UI layer (not on the supervisor graph). Returns a
structured attribution dict; degrades gracefully on LLM parse/shape failure
so the UI never sees an exception bubble up.
"""
import json
from datetime import date, datetime
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from data_news import retrieve
from llm import get_chat_model, strip_fences
from prompts import load as load_prompt


_RETRIEVE_TOP_K = 20
_DATE_WINDOW_DAYS = 3
_MAX_SUPPORTING_NEWS = 3


def _filter_by_date(hits: List[Dict], target: date, window_days: int) -> List[Dict]:
    """Keep hits whose metadata.date is within ±window_days of target, sorted
    by absolute distance ascending (closest first)."""
    def _distance(h: Dict) -> Optional[int]:
        d_str = (h.get("metadata") or {}).get("date", "")
        if not d_str:
            return None
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            return None
        return abs((d - target).days)

    scored = []
    for h in hits:
        d = _distance(h)
        if d is None or d > window_days:
            continue
        scored.append((d, h))
    scored.sort(key=lambda t: t[0])
    return [h for _, h in scored]


def _direction(pct_change: float) -> str:
    if pct_change >= 0.5:
        return "up"
    if pct_change <= -0.5:
        return "down"
    return "flat"


def _fallback(pct_change: float, price_from: float, price_to: float,
              close_hits: List[Dict]) -> Dict:
    """Used when retrieval is empty OR the LLM response is unparseable.
    Surfaces raw retrieved news so the UI still has something to render."""
    direction = _direction(pct_change)
    if not close_hits:
        summary = "No indexed news close to this date; attribution unavailable."
    else:
        summary = (f"Price moved {direction} {pct_change:+.2f}% "
                   f"(${price_from:.2f} → ${price_to:.2f}); "
                   f"see news items below for context.")
    supporting = [
        {"url": h.get("url", ""),
         "headline": h.get("headline", ""),
         "date": (h.get("metadata") or {}).get("date", "")}
        for h in close_hits[:_MAX_SUPPORTING_NEWS]
    ]
    return {
        "direction": direction,
        "headline_summary": summary,
        "key_drivers": ["No clear attribution in available news."] if close_hits else [],
        "caveats": ["Coverage for this date is thin."] if close_hits else [],
        "supporting_news": supporting,
    }


def explain_move(target_date: date, symbol: str, name: str,
                 pct_change: float, price_from: float, price_to: float,
                 top_k: int = _RETRIEVE_TOP_K) -> Dict:
    """Return a structured attribution for the given ticker's net daily move.

    Shape: {direction, headline_summary, key_drivers, caveats, supporting_news}.
    Never raises; on LLM failure, returns a fallback populated from raw news.
    """
    # Broad event-scoped retrieval (vector store is not ticker-tagged), then
    # Python-side filter by date proximity.
    query = f"{name} {symbol} {target_date.isoformat()}"
    raw = retrieve(query, top_k=top_k)
    close = _filter_by_date(raw, target_date, _DATE_WINDOW_DAYS)

    if not close:
        return _fallback(pct_change, price_from, price_to, [])

    bullets = "\n".join(
        f"- [{(h.get('metadata') or {}).get('date','')}] {h.get('headline','')}: "
        f"{h.get('text','')[:300]}"
        for h in close
    )
    system = load_prompt("price_explainer_system")
    human = (
        f"Target date: {target_date.isoformat()}\n"
        f"Ticker: {symbol} ({name})\n"
        f"Net move: {pct_change:+.2f}%  (${price_from:.2f} → ${price_to:.2f})\n\n"
        f"News snippets (chronologically close, sorted closest first):\n{bullets}"
    )

    llm = get_chat_model(temperature=0.1, max_tokens=2048)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    text = strip_fences(resp.content if isinstance(resp.content, str) else str(resp.content))

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _fallback(pct_change, price_from, price_to, close)

    # Shape gate — same pattern as Session-7 hardening for classify_intent / run_qa_agent.
    if not isinstance(parsed, dict):
        return _fallback(pct_change, price_from, price_to, close)
    required = {"direction", "headline_summary", "key_drivers", "caveats", "supporting_news"}
    if not required.issubset(parsed.keys()):
        return _fallback(pct_change, price_from, price_to, close)

    # Bound supporting_news length defensively even if the LLM ignored the rule.
    parsed["supporting_news"] = (parsed.get("supporting_news") or [])[:_MAX_SUPPORTING_NEWS]
    return parsed
