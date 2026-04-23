"""URL + MinHash-based near-duplicate removal. Keeps first occurrence."""
import re
from typing import Dict, List, Tuple

from datasketch import MinHash, MinHashLSH


_WORD_RE = re.compile(r"\w+")

# Bumped 0.9 → 0.95: GDELT articles ship with empty `snippet`, so MinHash
# shingling runs on headline-only text and threshold=0.9 collapsed distinct
# stories whose headlines shared boilerplate ("Iran closes Strait of Hormuz
# amid ..."). 0.95 keeps near-identical reposts together without collapsing
# genuinely distinct stories.
_DEFAULT_MINHASH_THRESHOLD = 0.95


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


def deduplicate(
    articles: List[Dict],
    minhash_threshold: float = _DEFAULT_MINHASH_THRESHOLD,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Return (kept_articles, stats). stats = input / url_dropped / minhash_dropped / kept."""
    input_n = len(articles)
    seen_urls: set[str] = set()
    url_unique: List[Dict] = []
    for a in articles:
        u = a.get("url", "")
        if u and u in seen_urls:
            continue
        seen_urls.add(u)
        url_unique.append(a)
    url_dropped = input_n - len(url_unique)

    lsh = MinHashLSH(threshold=minhash_threshold, num_perm=128)
    kept: List[Dict] = []
    minhash_dropped = 0
    for i, a in enumerate(url_unique):
        text = f"{a.get('headline', '')} {a.get('snippet', '')}".strip()
        if not text:
            kept.append(a)
            continue
        m = _minhash(text)
        if lsh.query(m):
            minhash_dropped += 1
            continue
        lsh.insert(f"doc-{i}", m)
        kept.append(a)

    stats = {
        "input": input_n,
        "url_dropped": url_dropped,
        "minhash_dropped": minhash_dropped,
        "kept": len(kept),
    }
    return kept, stats
