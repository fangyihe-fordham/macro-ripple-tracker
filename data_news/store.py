import json
import os
from pathlib import Path
from typing import Dict, List


def _path() -> Path:
    return Path(os.environ.get("DATA_DIR", "data")) / "articles.json"


def write_articles(articles: List[Dict]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(articles, indent=2, ensure_ascii=False))


def read_articles() -> List[Dict]:
    p = _path()
    if not p.exists():
        return []
    return json.loads(p.read_text())
