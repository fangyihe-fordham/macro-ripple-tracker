"""URL + MinHash-based near-duplicate removal. Keeps first occurrence."""
import re
from typing import Dict, List

from datasketch import MinHash, MinHashLSH


_WORD_RE = re.compile(r"\w+")


def _shingles(text: str, k: int = 5) -> set[str]:
    tokens = _WORD_RE.findall(text.lower())
    if len(tokens) < k:
        return {" ".join(tokens)}
    return {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def _minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for s in _shingles(text):
        m.update(s.encode("utf-8"))
    return m


def deduplicate(articles: List[Dict], minhash_threshold: float = 0.9) -> List[Dict]:
    seen_urls: set[str] = set()
    url_unique: List[Dict] = []
    for a in articles:
        u = a.get("url", "")
        if u and u in seen_urls:
            continue
        seen_urls.add(u)
        url_unique.append(a)

    lsh = MinHashLSH(threshold=minhash_threshold, num_perm=128)
    kept: List[Dict] = []
    for i, a in enumerate(url_unique):
        text = f"{a.get('headline', '')} {a.get('snippet', '')}".strip()
        if not text:
            kept.append(a)
            continue
        m = _minhash(text)
        if lsh.query(m):
            continue
        lsh.insert(f"doc-{i}", m)
        kept.append(a)
    return kept
