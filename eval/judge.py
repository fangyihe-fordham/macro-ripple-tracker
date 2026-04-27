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
    resp = llm.invoke([
        SystemMessage(content=_RELEVANCE_SYSTEM),
        HumanMessage(content=human),
    ])
    return str(resp.content).strip().lower().startswith("y")
