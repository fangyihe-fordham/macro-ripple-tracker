"""ChromaDB wrapper + sentence-transformers embeddings (local, free)."""
import os
import shutil
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.utils import embedding_functions


_COLLECTION = "news"
_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _db_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data")) / "chroma_db"


def _client():
    _db_dir().mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(_db_dir()))


def _embedder():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_MODEL)


def reset() -> None:
    p = _db_dir()
    if p.exists():
        shutil.rmtree(p)


def _collection(create: bool = True):
    c = _client()
    if create:
        return c.get_or_create_collection(_COLLECTION, embedding_function=_embedder())
    try:
        return c.get_collection(_COLLECTION, embedding_function=_embedder())
    except Exception:
        return None


def index_articles(articles: List[Dict]) -> None:
    if not articles:
        return
    coll = _collection(create=True)
    ids, docs, metas = [], [], []
    for i, a in enumerate(articles):
        body = " ".join(x for x in [a.get("headline", ""), a.get("snippet", ""), a.get("full_text", "")] if x).strip()
        if not body:
            continue
        ids.append(f"{a.get('source_kind','unk')}-{i}-{abs(hash(a.get('url','')))}")
        docs.append(body)
        metas.append({
            "url": a.get("url", ""),
            "headline": a.get("headline", ""),
            "source": a.get("source", ""),
            "date": a.get("date", ""),
            "source_kind": a.get("source_kind", ""),
        })
    coll.add(ids=ids, documents=docs, metadatas=metas)


def retrieve(query: str, top_k: int = 5) -> List[Dict]:
    coll = _collection(create=False)
    if coll is None or coll.count() == 0:
        return []
    res = coll.query(query_texts=[query], n_results=top_k)
    hits: List[Dict] = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({
            "text": doc,
            "url": meta.get("url", ""),
            "headline": meta.get("headline", ""),
            "metadata": meta,
            "score": 1.0 - float(dist),
        })
    return hits
