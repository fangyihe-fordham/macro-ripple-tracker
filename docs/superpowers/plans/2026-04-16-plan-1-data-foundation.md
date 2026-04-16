# Plan 1 — Data Foundation (M1 News + M2 Market + Event Config) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally-cached, event-agnostic data layer that (a) fetches news from GDELT + NewsAPI + RSS, deduplicates it, and embeds it into a ChromaDB vector store; and (b) downloads historical price data for a configured ticker list via yfinance. A single `python setup.py --event iran_war` populates both stores and makes the data queryable through stable Python APIs consumed by Plans 2 & 3.

**Architecture:** Event-driven: a YAML config (keywords + tickers + date range) drives a `setup.py` orchestrator that invokes `data_news` and `data_market` module entry points. Each fetcher is isolated in its own submodule for testability; public APIs (`retrieve()`, `get_price_changes()`) are importable from the top-level module. External APIs are called only through thin wrapper functions so tests can mock them cleanly.

**Tech Stack:** Python 3.11, conda env, `yfinance`, `gdeltdoc` (or `requests` to GDELT DOC API), `newsapi-python`, `feedparser`, `datasketch` (MinHash), `chromadb`, `sentence-transformers`, `pydantic` (config model), `pytest`, `pytest-mock`, `pyyaml`, `pandas`.

---

## File Structure

```
macro-ripple-tracker/                       # = /Users/fangyihe/appliedfinance
├── environment.yml                          # conda env spec
├── requirements.txt                         # pip deps pinned
├── setup.py                                 # CLI orchestrator (not packaging)
├── config.py                                # EventConfig pydantic model + loader
├── data_news/                               # M1 as a package (single-responsibility files)
│   ├── __init__.py                          # public API: retrieve(), ingest_all()
│   ├── gdelt.py                             # GDELT 2.0 fetcher
│   ├── newsapi_fetcher.py                   # NewsAPI.org fetcher
│   ├── rss.py                               # Reuters / AP RSS fetcher
│   ├── dedup.py                             # URL + MinHash dedup
│   ├── store.py                             # articles.json read/write
│   └── vector_store.py                      # ChromaDB wrapper + embedder
├── data_market.py                           # M2 single file (small surface)
├── events/
│   └── iran_war.yaml                        # reference event config
├── data/                                    # created at runtime; gitignored
│   ├── articles.json
│   ├── chroma_db/
│   ├── prices/
│   └── manifest.json
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_data_market.py
│   ├── test_gdelt.py
│   ├── test_newsapi.py
│   ├── test_rss.py
│   ├── test_dedup.py
│   ├── test_store.py
│   ├── test_vector_store.py
│   ├── test_setup_cli.py
│   └── fixtures/                            # sample API responses
└── .gitignore
```

**Deviation from spec §8:** spec shows `data_news.py` as a single file; splitting into a package because a single-file implementation would exceed ~500 lines across 3 fetchers + dedup + storage + embedding, and individual fetchers are naturally unit-testable in isolation.

---

### Task 1: Project scaffold + conda env

**Files:**
- Create: `environment.yml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `events/iran_war.yaml`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `environment.yml`**

```yaml
name: macro-ripple
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
      - -r requirements.txt
```

- [ ] **Step 2: Create `requirements.txt`**

```
# Data
yfinance==0.2.51
pandas==2.2.3
pyyaml==6.0.2
pydantic==2.9.2
requests==2.32.3

# News sources
gdeltdoc==1.6.0
newsapi-python==0.2.7
feedparser==6.0.11

# Dedup
datasketch==1.6.5

# Vector store + embeddings
chromadb==0.5.18
sentence-transformers==3.2.1

# Testing
pytest==8.3.3
pytest-mock==3.14.0
responses==0.25.3
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
data/
!data/.gitkeep
.env
.DS_Store
*.egg-info/
```

- [ ] **Step 4: Create `events/iran_war.yaml`**

```yaml
name: iran_war
display_name: "2026 Iran War / Strait of Hormuz Closure"
start_date: "2026-02-28"
end_date: "2026-04-16"
baseline_date: "2026-02-27"     # one trading day pre-event for % change baseline
seed_keywords:
  - Iran
  - Hormuz
  - Strait of Hormuz
  - oil
  - LNG
  - Brent
  - shipping
  - fertilizer
  - Qatar
tickers:
  - {category: Energy,      name: "Brent Crude Oil",     symbol: "BZ=F"}
  - {category: Energy,      name: "WTI Crude Oil",       symbol: "CL=F"}
  - {category: Energy,      name: "Natural Gas",         symbol: "NG=F"}
  - {category: Shipping,    name: "Shipping ETF",        symbol: "BOAT"}
  - {category: Agriculture, name: "Wheat Futures",       symbol: "ZW=F"}
  - {category: Agriculture, name: "Soybeans",            symbol: "ZS=F"}
  - {category: Materials,   name: "Aluminum Futures",    symbol: "ALI=F"}
  - {category: Chemicals,   name: "CF Industries",       symbol: "CF"}
  - {category: Equity,      name: "S&P 500",             symbol: "^GSPC"}
  - {category: Equity,      name: "Energy Sector ETF",   symbol: "XLE"}
  - {category: Equity,      name: "Defense ETF",         symbol: "ITA"}
rss_feeds:
  - https://feeds.reuters.com/reuters/topNews
  - https://feeds.apnews.com/rss/topnews
```

- [ ] **Step 5: Create `tests/__init__.py`** (empty file)

- [ ] **Step 6: Create `tests/conftest.py`**

```python
import json
from pathlib import Path
import pytest


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Isolated data/ dir per test; modules read DATA_DIR env if set."""
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setenv("DATA_DIR", str(d))
    return d
```

- [ ] **Step 7: Create conda env and install**

Run:
```bash
conda env create -f environment.yml
conda activate macro-ripple
```

Expected: env created, `python -c "import yfinance, chromadb, langchain"` (langchain not installed here — that's fine; test the ones we installed):
```bash
python -c "import yfinance, chromadb, pandas, pydantic, feedparser, datasketch, sentence_transformers; print('ok')"
```
Expected: `ok`

- [ ] **Step 8: Commit**

```bash
cd /Users/fangyihe/appliedfinance
git init
git add environment.yml requirements.txt .gitignore events/iran_war.yaml tests/
git commit -m "chore: project scaffold, conda env, iran_war event config"
```

---

### Task 2: Event config loader (`config.py`)

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from datetime import date
from pathlib import Path
import pytest
from config import EventConfig, Ticker, load_event


def test_load_iran_war_event():
    cfg = load_event("iran_war")
    assert isinstance(cfg, EventConfig)
    assert cfg.name == "iran_war"
    assert cfg.start_date == date(2026, 2, 28)
    assert cfg.baseline_date == date(2026, 2, 27)
    assert "Hormuz" in cfg.seed_keywords
    symbols = [t.symbol for t in cfg.tickers]
    assert "BZ=F" in symbols and "^GSPC" in symbols
    assert len(cfg.tickers) == 11


def test_load_event_missing_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_event("no_such_event")


def test_baseline_before_start():
    with pytest.raises(ValueError, match="baseline_date must be before start_date"):
        EventConfig(
            name="x", display_name="x",
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 10),
            baseline_date=date(2026, 1, 2),
            seed_keywords=["x"],
            tickers=[Ticker(category="c", name="n", symbol="s")],
            rss_feeds=[],
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
# config.py
from datetime import date
from pathlib import Path
from typing import List
import yaml
from pydantic import BaseModel, field_validator, model_validator


class Ticker(BaseModel):
    category: str
    name: str
    symbol: str


class EventConfig(BaseModel):
    name: str
    display_name: str
    start_date: date
    end_date: date
    baseline_date: date
    seed_keywords: List[str]
    tickers: List[Ticker]
    rss_feeds: List[str] = []

    @model_validator(mode="after")
    def _check_dates(self):
        if self.baseline_date >= self.start_date:
            raise ValueError("baseline_date must be before start_date")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


def load_event(name: str, events_dir: Path | None = None) -> EventConfig:
    root = events_dir or Path("events")
    path = root / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Event config not found: {path}")
    with path.open() as f:
        raw = yaml.safe_load(f)
    return EventConfig(**raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): pydantic EventConfig + YAML loader with date validation"
```

---

### Task 3: M2 market data — download + cache

**Files:**
- Create: `data_market.py`
- Test: `tests/test_data_market.py`
- Test fixture: `tests/fixtures/yf_brent_sample.csv`

- [ ] **Step 1: Create test fixture `tests/fixtures/yf_brent_sample.csv`**

```csv
Date,Open,High,Low,Close,Volume
2026-02-23,73.10,73.80,72.90,73.50,100000
2026-02-24,73.50,74.20,73.10,73.80,110000
2026-02-25,73.80,74.00,73.20,73.40,105000
2026-02-26,73.40,74.10,73.00,73.90,120000
2026-02-27,73.90,74.50,73.60,74.20,115000
2026-03-02,74.20,92.00,74.00,88.50,500000
2026-03-03,88.50,105.00,87.00,102.30,650000
2026-03-04,102.30,112.00,100.00,111.00,700000
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_data_market.py
import os
from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from config import load_event
import data_market


@pytest.fixture
def fake_yf(monkeypatch, fixtures_dir):
    """Replace yfinance.download with a function that returns our fixture DataFrame."""
    df = pd.read_csv(fixtures_dir / "yf_brent_sample.csv", parse_dates=["Date"]).set_index("Date")

    def fake_download(tickers, start, end, progress=False, auto_adjust=False):
        # yfinance returns MultiIndex cols for multiple tickers, flat for one.
        # We'll return a fresh copy per call.
        return df.copy()

    monkeypatch.setattr(data_market.yf, "download", fake_download)
    return df


def test_download_prices_writes_csv(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    # One CSV per ticker, in data/prices/
    price_dir = tmp_data_dir / "prices"
    assert price_dir.exists()
    csvs = list(price_dir.glob("*.csv"))
    assert len(csvs) == len(cfg.tickers)
    # Round-trip check on one file
    sample = pd.read_csv(csvs[0], parse_dates=["Date"])
    assert {"Date", "Close"}.issubset(sample.columns)


def test_get_price_on_date(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    close = data_market.get_price_on_date("BZ=F", date(2026, 2, 27))
    assert close == pytest.approx(74.20)


def test_get_price_on_date_missing_returns_none(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    # Weekend / non-trading day
    assert data_market.get_price_on_date("BZ=F", date(2026, 3, 1)) is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_data_market.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_market'`

- [ ] **Step 4: Implement `data_market.py` (download + per-date lookup)**

```python
# data_market.py
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import yfinance as yf
from config import EventConfig


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def _prices_dir() -> Path:
    d = _data_dir() / "prices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _csv_path(symbol: str) -> Path:
    # "BZ=F" -> "BZ_F.csv" (safe filename)
    safe = symbol.replace("=", "_").replace("^", "").replace("/", "_")
    return _prices_dir() / f"{safe}.csv"


def download_prices(cfg: EventConfig) -> None:
    """Fetch daily OHLCV for each ticker from baseline_date-7 through end_date; write one CSV per ticker."""
    start = cfg.baseline_date - timedelta(days=7)
    end = cfg.end_date + timedelta(days=1)  # yfinance end is exclusive
    for ticker in cfg.tickers:
        df = yf.download(ticker.symbol, start=start, end=end, progress=False, auto_adjust=False)
        if df.empty:
            continue
        df = df.reset_index().rename(columns={"index": "Date"})
        df.to_csv(_csv_path(ticker.symbol), index=False)


def _load(symbol: str) -> Optional[pd.DataFrame]:
    p = _csv_path(symbol)
    if not p.exists():
        return None
    return pd.read_csv(p, parse_dates=["Date"])


def get_price_on_date(symbol: str, d: date) -> Optional[float]:
    df = _load(symbol)
    if df is None:
        return None
    match = df[df["Date"].dt.date == d]
    if match.empty:
        return None
    return float(match["Close"].iloc[0])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_data_market.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add data_market.py tests/test_data_market.py tests/fixtures/yf_brent_sample.csv
git commit -m "feat(M2): yfinance download + per-date price lookup with CSV cache"
```

---

### Task 4: M2 — % change from baseline + range query

**Files:**
- Modify: `data_market.py` (add functions)
- Modify: `tests/test_data_market.py` (add tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_data_market.py`:

```python
def test_get_price_changes_vs_baseline(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    changes = data_market.get_price_changes(cfg, as_of=date(2026, 3, 4))
    # BZ=F: baseline Feb 27 close = 74.20, as_of Mar 4 close = 111.00
    # pct_change = (111.00 - 74.20) / 74.20 * 100 ≈ 49.60%
    assert "BZ=F" in changes
    assert changes["BZ=F"]["baseline"] == pytest.approx(74.20)
    assert changes["BZ=F"]["latest"] == pytest.approx(111.00)
    assert changes["BZ=F"]["pct_change"] == pytest.approx(49.60, abs=0.1)


def test_get_price_range(tmp_data_dir, fake_yf):
    cfg = load_event("iran_war")
    data_market.download_prices(cfg)
    series = data_market.get_price_range("BZ=F", date(2026, 2, 26), date(2026, 3, 3))
    # Inclusive on both ends; trading days only (no 2026-03-01 because fixture skips weekend)
    assert list(series.index.date.astype(str)) == ["2026-02-26", "2026-02-27", "2026-03-02", "2026-03-03"]
    assert series.iloc[-1] == pytest.approx(102.30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_data_market.py::test_get_price_changes_vs_baseline tests/test_data_market.py::test_get_price_range -v`
Expected: FAIL with `AttributeError: module 'data_market' has no attribute 'get_price_changes'`

- [ ] **Step 3: Implement the new functions**

Append to `data_market.py`:

```python
def get_price_changes(cfg: EventConfig, as_of: date) -> dict:
    """For each ticker, return {'baseline', 'latest', 'pct_change'} comparing baseline_date to as_of close."""
    out = {}
    for ticker in cfg.tickers:
        df = _load(ticker.symbol)
        if df is None or df.empty:
            continue
        baseline = df[df["Date"].dt.date == cfg.baseline_date]
        latest = df[df["Date"].dt.date == as_of]
        if baseline.empty or latest.empty:
            continue
        b = float(baseline["Close"].iloc[0])
        l = float(latest["Close"].iloc[0])
        out[ticker.symbol] = {
            "baseline": b,
            "latest": l,
            "pct_change": (l - b) / b * 100.0,
        }
    return out


def get_price_range(symbol: str, start: date, end: date) -> pd.Series:
    """Return a Close-price Series indexed by Date for [start, end] inclusive."""
    df = _load(symbol)
    if df is None:
        return pd.Series(dtype=float)
    mask = (df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)
    sub = df.loc[mask, ["Date", "Close"]].set_index("Date")
    return sub["Close"]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_data_market.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add data_market.py tests/test_data_market.py
git commit -m "feat(M2): % change vs baseline + price range query"
```

---

### Task 5: M1 — GDELT fetcher

**Files:**
- Create: `data_news/__init__.py`
- Create: `data_news/gdelt.py`
- Test: `tests/test_gdelt.py`
- Fixture: `tests/fixtures/gdelt_response.json`

- [ ] **Step 1: Create `data_news/__init__.py`** (empty for now; public API added in Task 10)

- [ ] **Step 2: Create fixture `tests/fixtures/gdelt_response.json`**

```json
{
  "articles": [
    {
      "url": "https://example.com/iran-hormuz-closure",
      "url_mobile": "",
      "title": "Iran closes Strait of Hormuz as conflict escalates",
      "seendate": "20260228T120000Z",
      "socialimage": "",
      "domain": "example.com",
      "language": "English",
      "sourcecountry": "US"
    },
    {
      "url": "https://other.com/oil-price-surge",
      "url_mobile": "",
      "title": "Brent jumps above $100 on Hormuz fears",
      "seendate": "20260301T080000Z",
      "socialimage": "",
      "domain": "other.com",
      "language": "English",
      "sourcecountry": "UK"
    }
  ]
}
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_gdelt.py
import json
from datetime import date
import pytest
from data_news import gdelt
from config import load_event


def test_fetch_gdelt_returns_normalized_articles(monkeypatch, fixtures_dir):
    captured = {}

    class FakeGdeltDoc:
        def article_search(self, filters):
            captured["filters"] = filters
            payload = json.loads((fixtures_dir / "gdelt_response.json").read_text())
            import pandas as pd
            return pd.DataFrame(payload["articles"])

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())

    cfg = load_event("iran_war")
    articles = gdelt.fetch(cfg)

    assert len(articles) == 2
    a = articles[0]
    assert a["url"] == "https://example.com/iran-hormuz-closure"
    assert a["headline"].startswith("Iran closes")
    assert a["source"] == "example.com"
    assert a["date"] == "2026-02-28"
    assert a["source_kind"] == "gdelt"
    # Filters must include seed keywords and the event date range
    f = captured["filters"]
    assert f.keyword and "Hormuz" in f.keyword
    assert f.start_date == "2026-02-28"
    assert f.end_date == "2026-04-16"


def test_fetch_gdelt_empty_result(monkeypatch):
    class FakeGdeltDoc:
        def article_search(self, filters):
            import pandas as pd
            return pd.DataFrame()

    monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())
    cfg = load_event("iran_war")
    assert gdelt.fetch(cfg) == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_gdelt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_news.gdelt'`

- [ ] **Step 5: Implement `data_news/gdelt.py`**

```python
# data_news/gdelt.py
"""GDELT 2.0 fetcher — primary news source. Free, no API key, ~15min cadence."""
from typing import List, Dict
from gdeltdoc import GdeltDoc, Filters
from config import EventConfig


def fetch(cfg: EventConfig) -> List[Dict]:
    """Query GDELT DOC API for the event keywords over the event window. Return normalized records."""
    filters = Filters(
        keyword=cfg.seed_keywords,
        start_date=cfg.start_date.isoformat(),
        end_date=cfg.end_date.isoformat(),
        language="english",
    )
    client = GdeltDoc()
    df = client.article_search(filters)
    if df.empty:
        return []
    out: List[Dict] = []
    for _, row in df.iterrows():
        seen = str(row.get("seendate", ""))
        # seendate format: 20260228T120000Z -> 2026-02-28
        iso_date = f"{seen[0:4]}-{seen[4:6]}-{seen[6:8]}" if len(seen) >= 8 else ""
        out.append({
            "url": row["url"],
            "headline": row.get("title", ""),
            "source": row.get("domain", ""),
            "date": iso_date,
            "snippet": "",           # GDELT DOC doesn't return snippets
            "full_text": "",         # filled later if enabled
            "source_kind": "gdelt",
        })
    return out
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_gdelt.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add data_news/__init__.py data_news/gdelt.py tests/test_gdelt.py tests/fixtures/gdelt_response.json
git commit -m "feat(M1): GDELT 2.0 news fetcher with keyword+date filters"
```

---

### Task 6: M1 — NewsAPI fetcher

**Files:**
- Create: `data_news/newsapi_fetcher.py`
- Test: `tests/test_newsapi.py`
- Fixture: `tests/fixtures/newsapi_response.json`

- [ ] **Step 1: Create fixture `tests/fixtures/newsapi_response.json`**

```json
{
  "status": "ok",
  "totalResults": 2,
  "articles": [
    {
      "source": {"id": null, "name": "Reuters"},
      "author": "Reuters Staff",
      "title": "Oil tops $100 as Iran escalation threatens Hormuz",
      "description": "Brent crude surged above $100 on Monday.",
      "url": "https://reuters.com/article-1",
      "publishedAt": "2026-03-01T07:30:00Z",
      "content": "Brent crude surged..."
    },
    {
      "source": {"id": null, "name": "FT"},
      "author": "FT Staff",
      "title": "Shipping rates spike on Hormuz uncertainty",
      "description": "Freight rates jumped 40%.",
      "url": "https://ft.com/article-2",
      "publishedAt": "2026-03-02T09:15:00Z",
      "content": "Freight rates jumped..."
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_newsapi.py
import json
import os
import pytest
from data_news import newsapi_fetcher
from config import load_event


def test_fetch_newsapi_returns_normalized(monkeypatch, fixtures_dir):
    monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")
    payload = json.loads((fixtures_dir / "newsapi_response.json").read_text())
    captured = {}

    class FakeClient:
        def __init__(self, api_key): captured["api_key"] = api_key
        def get_everything(self, q, from_param, to, language, page_size, page):
            captured.setdefault("calls", []).append(
                {"q": q, "from": from_param, "to": to, "page": page}
            )
            return payload

    monkeypatch.setattr(newsapi_fetcher, "NewsApiClient", FakeClient)
    cfg = load_event("iran_war")
    articles = newsapi_fetcher.fetch(cfg, max_pages=1)

    assert captured["api_key"] == "dummy-key"
    assert len(articles) == 2
    assert articles[0]["source"] == "Reuters"
    assert articles[0]["snippet"] == "Brent crude surged above $100 on Monday."
    assert articles[0]["date"] == "2026-03-01"
    assert articles[0]["source_kind"] == "newsapi"


def test_fetch_newsapi_no_key_returns_empty(monkeypatch):
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    cfg = load_event("iran_war")
    assert newsapi_fetcher.fetch(cfg) == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_newsapi.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_news.newsapi_fetcher'`

- [ ] **Step 4: Implement `data_news/newsapi_fetcher.py`**

```python
# data_news/newsapi_fetcher.py
"""NewsAPI.org fetcher — secondary source, 100 req/day free tier, snippets only."""
import os
from typing import List, Dict
from newsapi import NewsApiClient
from config import EventConfig


def fetch(cfg: EventConfig, max_pages: int = 1) -> List[Dict]:
    """Fetch via NewsAPI /v2/everything. Skips silently if NEWSAPI_KEY is unset."""
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return []
    client = NewsApiClient(api_key=key)
    q = " OR ".join(cfg.seed_keywords)
    results: List[Dict] = []
    for page in range(1, max_pages + 1):
        resp = client.get_everything(
            q=q,
            from_param=cfg.start_date.isoformat(),
            to=cfg.end_date.isoformat(),
            language="en",
            page_size=100,
            page=page,
        )
        for a in resp.get("articles", []):
            pub = a.get("publishedAt", "")[:10]
            results.append({
                "url": a.get("url", ""),
                "headline": a.get("title", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "date": pub,
                "snippet": a.get("description", "") or "",
                "full_text": a.get("content", "") or "",
                "source_kind": "newsapi",
            })
        if len(resp.get("articles", [])) < 100:
            break
    return results
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_newsapi.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add data_news/newsapi_fetcher.py tests/test_newsapi.py tests/fixtures/newsapi_response.json
git commit -m "feat(M1): NewsAPI.org fetcher (secondary, opt-in via NEWSAPI_KEY env)"
```

---

### Task 7: M1 — RSS fetcher

**Files:**
- Create: `data_news/rss.py`
- Test: `tests/test_rss.py`
- Fixture: `tests/fixtures/rss_sample.xml`

- [ ] **Step 1: Create fixture `tests/fixtures/rss_sample.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>Iran escalation drives oil higher</title>
      <link>https://example.com/rss-1</link>
      <description>Oil climbed sharply.</description>
      <pubDate>Mon, 02 Mar 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Unrelated story</title>
      <link>https://example.com/rss-2</link>
      <description>Sports news.</description>
      <pubDate>Tue, 03 Mar 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Hormuz shipping delays mount</title>
      <link>https://example.com/rss-3</link>
      <description>Vessels diverting around the strait.</description>
      <pubDate>Wed, 04 Mar 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_rss.py
from unittest.mock import patch
import feedparser
from data_news import rss
from config import load_event


def test_fetch_rss_filters_by_keywords(monkeypatch, fixtures_dir):
    raw = (fixtures_dir / "rss_sample.xml").read_text()
    # feedparser can parse from a string directly
    parsed = feedparser.parse(raw)
    monkeypatch.setattr(rss, "_parse_feed", lambda url: parsed)

    cfg = load_event("iran_war")
    articles = rss.fetch(cfg)

    # Only 2 of 3 items mention seed keywords (Iran/Hormuz); "Unrelated story" filtered.
    # Filter runs once per feed; config has 2 feeds -> 4 total records before dedup.
    # But dedup is a separate step; here we just assert keyword filter.
    kept_urls = {a["url"] for a in articles}
    assert "https://example.com/rss-1" in kept_urls
    assert "https://example.com/rss-3" in kept_urls
    assert "https://example.com/rss-2" not in kept_urls
    for a in articles:
        assert a["source_kind"] == "rss"
        assert a["date"].startswith("2026-")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_rss.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_news.rss'`

- [ ] **Step 4: Implement `data_news/rss.py`**

```python
# data_news/rss.py
"""Reuters / AP RSS fetcher — tertiary source, canonical timestamps for major events."""
from datetime import datetime
from typing import List, Dict
import feedparser
from config import EventConfig


def _parse_feed(url: str):
    return feedparser.parse(url)


def _matches_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in keywords)


def fetch(cfg: EventConfig) -> List[Dict]:
    out: List[Dict] = []
    for url in cfg.rss_feeds:
        parsed = _parse_feed(url)
        for entry in parsed.entries:
            blob = f"{entry.get('title', '')} {entry.get('summary', '')}"
            if not _matches_any(blob, cfg.seed_keywords):
                continue
            pub = entry.get("published_parsed")
            iso_date = datetime(*pub[:6]).date().isoformat() if pub else ""
            out.append({
                "url": entry.get("link", ""),
                "headline": entry.get("title", ""),
                "source": url,
                "date": iso_date,
                "snippet": entry.get("summary", "") or "",
                "full_text": "",
                "source_kind": "rss",
            })
    return out
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_rss.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add data_news/rss.py tests/test_rss.py tests/fixtures/rss_sample.xml
git commit -m "feat(M1): RSS fetcher with keyword filtering"
```

---

### Task 8: M1 — Deduplication (URL + MinHash near-duplicate)

**Files:**
- Create: `data_news/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dedup.py
from data_news.dedup import deduplicate


def test_dedup_by_url():
    articles = [
        {"url": "https://a.com/1", "headline": "Iran oil", "snippet": "", "date": "2026-03-01"},
        {"url": "https://a.com/1", "headline": "Iran oil", "snippet": "", "date": "2026-03-01"},
        {"url": "https://a.com/2", "headline": "Different", "snippet": "", "date": "2026-03-01"},
    ]
    result = deduplicate(articles)
    assert len(result) == 2
    urls = [a["url"] for a in result]
    assert urls == ["https://a.com/1", "https://a.com/2"]


def test_dedup_by_minhash_near_duplicate():
    # Same headline + snippet but different URL -> near-duplicate, one survives.
    articles = [
        {"url": "https://a.com/1",
         "headline": "Iran closes Strait of Hormuz as conflict escalates",
         "snippet": "Oil prices surged after the closure was announced overnight",
         "date": "2026-03-01"},
        {"url": "https://b.com/1",
         "headline": "Iran closes Strait of Hormuz as conflict escalates",
         "snippet": "Oil prices surged after the closure was announced overnight",
         "date": "2026-03-01"},
        {"url": "https://c.com/1",
         "headline": "Totally different unrelated article about sports",
         "snippet": "Basketball game coverage from last night",
         "date": "2026-03-01"},
    ]
    result = deduplicate(articles, minhash_threshold=0.9)
    assert len(result) == 2
    headlines = [a["headline"] for a in result]
    assert "Basketball game" in " ".join(headlines) or "sports" in " ".join(headlines).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_news.dedup'`

- [ ] **Step 3: Implement `data_news/dedup.py`**

```python
# data_news/dedup.py
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
    # Stage 1: URL dedup (stable order)
    seen_urls: set[str] = set()
    url_unique: List[Dict] = []
    for a in articles:
        u = a.get("url", "")
        if u and u in seen_urls:
            continue
        seen_urls.add(u)
        url_unique.append(a)

    # Stage 2: MinHash near-duplicate
    lsh = MinHashLSH(threshold=minhash_threshold, num_perm=128)
    kept: List[Dict] = []
    for i, a in enumerate(url_unique):
        text = f"{a.get('headline', '')} {a.get('snippet', '')}".strip()
        if not text:
            kept.append(a)
            continue
        m = _minhash(text)
        if lsh.query(m):
            continue  # near-duplicate exists
        lsh.insert(f"doc-{i}", m)
        kept.append(a)
    return kept
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_dedup.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add data_news/dedup.py tests/test_dedup.py
git commit -m "feat(M1): URL + MinHash dedup for cross-source news"
```

---

### Task 9: M1 — Article storage (articles.json)

**Files:**
- Create: `data_news/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
from data_news import store


def test_write_and_read_articles_roundtrip(tmp_data_dir):
    articles = [
        {"url": "https://a.com/1", "headline": "h1", "source": "a.com",
         "date": "2026-03-01", "snippet": "s1", "full_text": "", "source_kind": "gdelt"},
        {"url": "https://b.com/1", "headline": "h2", "source": "b.com",
         "date": "2026-03-02", "snippet": "s2", "full_text": "", "source_kind": "rss"},
    ]
    store.write_articles(articles)
    loaded = store.read_articles()
    assert loaded == articles


def test_read_articles_missing_returns_empty(tmp_data_dir):
    assert store.read_articles() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_news.store'`

- [ ] **Step 3: Implement `data_news/store.py`**

```python
# data_news/store.py
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_store.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add data_news/store.py tests/test_store.py
git commit -m "feat(M1): articles.json read/write layer"
```

---

### Task 10: M1 — ChromaDB vector store + retrieve()

**Files:**
- Create: `data_news/vector_store.py`
- Modify: `data_news/__init__.py` (expose `retrieve`)
- Test: `tests/test_vector_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vector_store.py
import pytest
from data_news import vector_store


@pytest.fixture
def sample_articles():
    return [
        {"url": "https://a.com/oil",  "headline": "Brent crude jumps as Iran closes Hormuz",
         "source": "a.com", "date": "2026-03-01",
         "snippet": "Oil prices surged above $100 as Iran shut the Strait of Hormuz.",
         "full_text": "", "source_kind": "gdelt"},
        {"url": "https://b.com/ag",   "headline": "Fertilizer costs climb on natural gas spike",
         "source": "b.com", "date": "2026-03-05",
         "snippet": "Ammonia producers face higher input costs as natural gas rallies.",
         "full_text": "", "source_kind": "gdelt"},
        {"url": "https://c.com/def",  "headline": "Defense stocks rally on Middle East tensions",
         "source": "c.com", "date": "2026-03-02",
         "snippet": "Lockheed, Raytheon, Northrop rose sharply.",
         "full_text": "", "source_kind": "rss"},
    ]


def test_index_and_retrieve(tmp_data_dir, sample_articles):
    vector_store.reset()
    vector_store.index_articles(sample_articles)
    hits = vector_store.retrieve("How did oil prices move after Hormuz closed?", top_k=2)
    assert len(hits) == 2
    top = hits[0]
    # Oil article should be top hit
    assert top["url"] == "https://a.com/oil"
    assert "metadata" in top
    assert top["metadata"]["source_kind"] == "gdelt"
    assert "score" in top


def test_retrieve_empty_when_no_index(tmp_data_dir):
    vector_store.reset()
    assert vector_store.retrieve("anything", top_k=3) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vector_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_news.vector_store'`

- [ ] **Step 3: Implement `data_news/vector_store.py`**

```python
# data_news/vector_store.py
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
            "score": 1.0 - float(dist),  # cosine distance → similarity
        })
    return hits
```

- [ ] **Step 4: Expose public API in `data_news/__init__.py`**

```python
# data_news/__init__.py
from data_news.vector_store import retrieve, index_articles, reset
from data_news.store import read_articles, write_articles

__all__ = ["retrieve", "index_articles", "reset", "read_articles", "write_articles"]
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_vector_store.py -v`
Expected: 2 passed. First run will download the MiniLM model (~80 MB) — one-time.

- [ ] **Step 6: Commit**

```bash
git add data_news/vector_store.py data_news/__init__.py tests/test_vector_store.py
git commit -m "feat(M1): ChromaDB + MiniLM vector store with retrieve() API"
```

---

### Task 11: `setup.py` orchestrator CLI

**Files:**
- Create: `setup.py`
- Test: `tests/test_setup_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_setup_cli.py
import json
import subprocess
import sys
from pathlib import Path
import pytest


def test_setup_runs_end_to_end(tmp_data_dir, monkeypatch, fixtures_dir):
    """Monkey-patch each fetcher to return fixture data; confirm setup writes articles.json + prices + manifest."""
    # Delegate to an in-process runner so we can patch before import.
    import data_news.gdelt as gdelt_mod
    import data_news.newsapi_fetcher as newsapi_mod
    import data_news.rss as rss_mod
    import data_market

    monkeypatch.setattr(gdelt_mod, "fetch", lambda cfg: [
        {"url": "https://g.com/1", "headline": "Iran Hormuz closed", "source": "g.com",
         "date": "2026-03-01", "snippet": "Oil surged.", "full_text": "",
         "source_kind": "gdelt"},
    ])
    monkeypatch.setattr(newsapi_mod, "fetch", lambda cfg, max_pages=1: [])
    monkeypatch.setattr(rss_mod, "fetch", lambda cfg: [
        {"url": "https://r.com/1", "headline": "Shipping delays on Hormuz", "source": "r.com",
         "date": "2026-03-02", "snippet": "Vessels reroute.", "full_text": "",
         "source_kind": "rss"},
    ])

    import pandas as pd
    fake_df = pd.read_csv(fixtures_dir / "yf_brent_sample.csv", parse_dates=["Date"]).set_index("Date")
    monkeypatch.setattr(data_market.yf, "download",
                        lambda *a, **kw: fake_df.copy())

    import setup as setup_mod
    setup_mod.main(["--event", "iran_war"])

    # Assertions
    arts_path = tmp_data_dir / "articles.json"
    manifest_path = tmp_data_dir / "manifest.json"
    prices_dir = tmp_data_dir / "prices"

    arts = json.loads(arts_path.read_text())
    assert len(arts) == 2
    manifest = json.loads(manifest_path.read_text())
    assert manifest["event"] == "iran_war"
    assert manifest["article_count"] == 2
    assert "snapshot_utc" in manifest
    assert prices_dir.exists() and len(list(prices_dir.glob("*.csv"))) == 11

    # Vector store populated
    from data_news import retrieve
    hits = retrieve("oil price Hormuz", top_k=1)
    assert len(hits) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_setup_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'setup'` OR setup.py has no `main`.

- [ ] **Step 3: Implement `setup.py`**

```python
# setup.py
"""One-shot data pipeline: python setup.py --event iran_war"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from config import load_event
from data_news import gdelt, newsapi_fetcher, rss
from data_news.dedup import deduplicate
from data_news import store, vector_store
import data_market


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch news + market data for an event.")
    parser.add_argument("--event", required=True, help="Event config name (e.g. iran_war)")
    parser.add_argument("--refresh", action="store_true", help="Wipe prior index before fetching")
    args = parser.parse_args(argv)

    cfg = load_event(args.event)
    print(f"[setup] Event: {cfg.display_name}  window: {cfg.start_date} → {cfg.end_date}")

    if args.refresh:
        vector_store.reset()

    # News
    print("[setup] Fetching GDELT...")
    g = gdelt.fetch(cfg)
    print(f"  {len(g)} articles")

    print("[setup] Fetching NewsAPI...")
    n = newsapi_fetcher.fetch(cfg)
    print(f"  {len(n)} articles")

    print("[setup] Fetching RSS...")
    r = rss.fetch(cfg)
    print(f"  {len(r)} articles")

    all_articles = g + n + r
    print(f"[setup] Deduplicating {len(all_articles)} total...")
    unique = deduplicate(all_articles)
    print(f"  {len(unique)} unique")

    store.write_articles(unique)
    print("[setup] Indexing into ChromaDB...")
    vector_store.index_articles(unique)

    # Market
    print("[setup] Downloading prices...")
    data_market.download_prices(cfg)

    # Manifest
    manifest = {
        "event": cfg.name,
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "source_counts": {"gdelt": len(g), "newsapi": len(n), "rss": len(r)},
        "ticker_count": len(cfg.tickers),
    }
    (_data_dir() / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[setup] Done. Manifest: {_data_dir() / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_setup_cli.py -v`
Expected: 1 passed

- [ ] **Step 5: Run full suite**

Run: `pytest -v`
Expected: all tests pass (target: ~15 tests passing).

- [ ] **Step 6: Commit**

```bash
git add setup.py tests/test_setup_cli.py
git commit -m "feat: setup.py CLI orchestrator with manifest.json for reproducibility"
```

---

### Task 12: Live smoke test (gated)

**Files:**
- Create: `tests/test_smoke_live.py`

- [ ] **Step 1: Write a gated integration test**

```python
# tests/test_smoke_live.py
"""Live integration smoke. Hits real GDELT + yfinance. Run with: RUN_LIVE=1 pytest tests/test_smoke_live.py -v"""
import os
from datetime import date, timedelta
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1",
    reason="Live integration test. Set RUN_LIVE=1 to enable.",
)


def test_yfinance_live_fetches_spy():
    import yfinance as yf
    end = date.today()
    start = end - timedelta(days=10)
    df = yf.download("SPY", start=start.isoformat(), end=end.isoformat(), progress=False)
    assert not df.empty
    assert "Close" in df.columns


def test_gdelt_live_returns_articles():
    from gdeltdoc import GdeltDoc, Filters
    end = date.today()
    start = end - timedelta(days=3)
    f = Filters(keyword=["oil"], start_date=start.isoformat(), end_date=end.isoformat(), language="english")
    df = GdeltDoc().article_search(f)
    assert not df.empty
    assert "url" in df.columns
```

- [ ] **Step 2: Run once manually to confirm it works**

Run: `RUN_LIVE=1 pytest tests/test_smoke_live.py -v`
Expected: 2 passed (network required). In normal runs (without env var): 2 skipped.

- [ ] **Step 3: Run a real setup**

Run: `python setup.py --event iran_war --refresh`
Expected: console prints article counts per source and finishes with `[setup] Done.`; `data/articles.json`, `data/prices/*.csv`, `data/chroma_db/`, and `data/manifest.json` are created.

Sanity check — open a Python REPL:
```python
from data_news import retrieve
hits = retrieve("How did Brent react to Hormuz closure?", top_k=3)
for h in hits:
    print(h["headline"], "—", h["score"])
```
Expected: 3 real article headlines with similarity scores between 0 and 1.

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke_live.py
git commit -m "test: add opt-in live smoke for yfinance + GDELT"
```

---

## Verification Checklist (end of Plan 1)

- [ ] `pytest -v` → all non-live tests pass (~16 tests)
- [ ] `python setup.py --event iran_war --refresh` runs without errors
- [ ] `data/articles.json` contains ≥ 500 unique articles
- [ ] `data/prices/` contains 11 CSVs, one per ticker
- [ ] `data/manifest.json` contains snapshot timestamp + counts
- [ ] `from data_news import retrieve; retrieve("oil Hormuz", top_k=5)` returns relevant hits
- [ ] `from data_market import get_price_changes; from config import load_event; get_price_changes(load_event("iran_war"), date(2026,4,15))` returns a dict with 11 entries including `BZ=F`

Plan 1 is done when every box above is checked. Plans 2 and 3 build on top of `retrieve()` and `get_price_changes()`.

---

## Self-Review Notes

**Spec coverage for §4 M1/M2 + §5 + §6 SETUP:** ✅ every requirement mapped to a task.

**Deferred / out of scope for Plan 1:**
- Full-text article body scraping (spec §M1 shows `full_text` field; Plan 1 leaves it blank except where NewsAPI returns `content`; deferred to §11.2)
- Real-time / incremental updates (deferred to §11.4)
- M3, M4, M5 (Plans 2 and 3)

**Type consistency:** `retrieve()` returns `List[Dict]` with `{text, url, headline, metadata, score}`. Plan 2 (ripple agent) and Plan 3 (QA tab) must consume this exact shape.
