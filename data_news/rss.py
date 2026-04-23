"""Reuters / AP RSS fetcher — tertiary source, canonical timestamps for major events."""
import html
import re
from datetime import datetime
from typing import List, Dict

import feedparser

from config import EventConfig


# Order matters: script/style/comment blocks must be removed (content AND
# wrapper) BEFORE tag stripping. A naive `<[^>]+>` strip would leave the
# inner text — `<script>alert(1)</script>` → `alert(1)` — which is both
# noise for the embedder and a prompt-injection surface for Plan 2's LLM
# agents (user-controlled JS fragments masquerading as article text).
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.IGNORECASE | re.DOTALL)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _parse_feed(url: str):
    return feedparser.parse(url)


def _strip_html(s: str) -> str:
    # RSS summaries often contain raw <p>/<a>/<img>; both the embedder and
    # Plan 2's LLM prompts get cleaner input if we strip tags + unescape entities.
    if not s:
        return ""
    s = _SCRIPT_RE.sub(" ", s)
    s = _STYLE_RE.sub(" ", s)
    s = _COMMENT_RE.sub(" ", s)
    s = _TAG_RE.sub(" ", s)
    return _WS_RE.sub(" ", html.unescape(s)).strip()


def _matches_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in keywords)


def fetch(cfg: EventConfig) -> List[Dict]:
    out: List[Dict] = []
    for url in cfg.rss_feeds:
        parsed = _parse_feed(url)
        for entry in parsed.entries:
            title = entry.get("title", "")
            summary = _strip_html(entry.get("summary", "") or "")
            if not _matches_any(f"{title} {summary}", cfg.seed_keywords):
                continue
            pub = entry.get("published_parsed")
            iso_date = datetime(*pub[:6]).date().isoformat() if pub else ""
            out.append({
                "url": entry.get("link", ""),
                "headline": title,
                "source": url,
                "date": iso_date,
                "snippet": summary,
                "full_text": "",
                "source_kind": "rss",
            })
    return out
