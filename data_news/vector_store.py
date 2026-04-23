"""ChromaDB wrapper + sentence-transformers embeddings (local, free).

Single-writer assumption: ChromaDB's persistent store has no locking of its
own. `setup.py` takes an exclusive fcntl lock at `$DATA_DIR/setup.lock` for
the duration of `reset()` + `index_articles()`. Readers (Plan 3 UI) should
call `setup.is_setup_in_progress()` before firing up `retrieve()` to avoid
racing a live rebuild.
"""
import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.config import Settings
from chromadb.errors import InvalidCollectionException
from chromadb.utils import embedding_functions


# chromadb 0.5.18's posthog integration is broken at the call-site level:
# every client/collection op fires a `capture()` with a mismatched positional
# signature and logs ERROR "capture() takes 1 positional argument but 3 were
# given". Settings(anonymized_telemetry=False) does NOT prevent the capture
# attempt — it fires regardless and then fails. The only reliable
# workaround is to silence the posthog logger directly.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


_COLLECTION = "news"
_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _db_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data")) / "chroma_db"


def _client():
    _db_dir().mkdir(parents=True, exist_ok=True)
    # `anonymized_telemetry=False` suppresses posthog-integration errors
    # ("Failed to send telemetry event ... capture() takes 1 positional
    # argument but 3 were given") that chromadb 0.5.18 emits on every
    # client call. That noise drowns out the real-error prints C3 added.
    return chromadb.PersistentClient(
        path=str(_db_dir()),
        settings=Settings(anonymized_telemetry=False),
    )


def _embedder():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_MODEL)


def reset() -> None:
    p = _db_dir()
    if p.exists():
        shutil.rmtree(p)
    # chromadb 0.5.x caches per-path SQLite connections in a SharedSystemClient
    # singleton; without clearing it, the next PersistentClient(path=p) reuses
    # a stale handle pointing at the just-deleted DB and fails with
    # "attempt to write a readonly database" on the next write. Matters
    # whenever reset() is called more than once in the same process.
    chromadb.api.client.SharedSystemClient.clear_system_cache()


def _collection(create: bool = True):
    c = _client()
    if create:
        return c.get_or_create_collection(_COLLECTION, embedding_function=_embedder())
    try:
        return c.get_collection(_COLLECTION, embedding_function=_embedder())
    except InvalidCollectionException:
        return None
    except Exception as e:
        print(f"[vector_store] unexpected error opening collection '{_COLLECTION}': {e!r}")
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
        # Stable, process-independent ID: sha1 of URL (empty-URL articles still
        # uniquify on {i}). Python's builtin hash() is salted per process, so
        # IDs weren't reproducible across runs — a blocker for incremental
        # reindexing later.
        url_hash = hashlib.sha1(a.get("url", "").encode("utf-8")).hexdigest()[:16]
        ids.append(f"{a.get('source_kind','unk')}-{i}-{url_hash}")
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
