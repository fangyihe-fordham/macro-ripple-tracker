import re
from datetime import date
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from agent_supervisor import run as run_supervisor
from config import EventConfig
from llm import get_chat_model


_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_SYSTEM = (
    "You are a strict faithfulness judge. Given a claim and a context, "
    "answer ONLY 'yes' or 'no': is the claim supported by the context?"
)


def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [sentence.strip() for sentence in _SENT_RE.split(text) if sentence.strip()]


def _judge(claim: str, context: str, llm=None) -> bool:
    llm = llm or get_chat_model(temperature=0.0, max_tokens=5)
    human = f"Claim: {claim}\n\nContext:\n{context[:2000]}\n\nSupported?"
    resp = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=human),
    ])
    return str(resp.content).strip().lower().startswith("y")


def score_query(q: Dict, cfg: EventConfig, as_of: date) -> Dict:
    result = run_supervisor(cfg, q["query"], as_of)
    answer = (result.get("response") or {}).get("answer", "")
    hits = result.get("news_results", [])
    context = "\n\n".join(f"- {hit.get('text', '')}" for hit in hits)
    sentences = split_sentences(answer)
    judge_llm = get_chat_model(temperature=0.0, max_tokens=5)
    supported = sum(1 for sentence in sentences if _judge(sentence, context, llm=judge_llm))
    total = len(sentences)
    return {
        "id": q["id"],
        "query": q["query"],
        "answer": answer,
        "total_sentences": total,
        "supported_sentences": supported,
        "faithfulness": supported / total if total else 0.0,
    }


def run_qa_eval(queries: List[Dict], cfg: EventConfig, as_of: date) -> Dict:
    per_query = [score_query(q, cfg, as_of) for q in queries]
    mean = (
        sum(item["faithfulness"] for item in per_query) / len(per_query)
        if per_query else 0.0
    )
    return {"metric": "faithfulness", "mean": mean, "per_query": per_query}
