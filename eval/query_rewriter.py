from langchain_core.messages import HumanMessage, SystemMessage

from config import EventConfig
from llm import get_chat_model


_SYSTEM = (
    "You reformulate a user question into a concise search-optimized query for "
    "a corpus of news articles about a specific macro event. Add 2-4 event-specific "
    "keywords likely to appear in relevant articles. Output ONLY the rewritten "
    "query as a single line -- no JSON, no preamble, no quotes."
)


def rewrite(query: str, cfg: EventConfig) -> str:
    llm = get_chat_model(temperature=0.0, max_tokens=200)
    seed_str = ", ".join(cfg.seed_keywords[:8])
    human = (
        f"Event: {cfg.display_name}\n"
        f"Window: {cfg.start_date} to {cfg.end_date}\n"
        f"Seed keywords: {seed_str}\n"
        f"Original question: {query}\n\n"
        f"Rewrite as a search-optimized query."
    )
    resp = llm.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=human)])
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    text = text.strip().strip('"').strip("'").strip()
    return text if text else query
