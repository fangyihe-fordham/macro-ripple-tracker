# Macro Event Ripple Tracker

Applied Finance course project (v0.2). Agentic RAG that turns a macro /
geopolitical event into a grounded ripple analysis: timeline, multi-level
industry impact tree, market data, and free-form Q&A — all in one Streamlit
app backed by Claude Sonnet 4.6 + LangGraph.

Current state: **Plan 1 complete (data foundation).** Plans 2 (LLM agents)
and 3 (Streamlit UI + eval) are next. See [`CLAUDE.md`](CLAUDE.md) for the
full project map, conventions, and working-session handoff notes.

## Quick start

```bash
conda env create -f environment.yml
conda activate macro-ripple
cp .env.example .env   # then paste real ANTHROPIC_API_KEY + NEWSAPI_KEY
python setup.py --event iran_war --refresh
pytest -v

# Run the UI (single-page event-focused dashboard)
streamlit run ui_app.py               # → http://localhost:8501
```

## Dashboard layout

Single page, no tabs. The layout couples the primary ticker's daily moves
with the event narrative:

1. **Price chart (Brent crude)** — daily close line with red/green markers
   on days where |daily %| exceeds the threshold slider. Click a marker to
   explain that day.
2. **Detail panel (right)** — structured attribution for the selected day:
   direction + headline summary + 2–3 drivers + caveats + ≤3 cited news items.
3. **Event axis** — horizontal time axis with markers aligned to the same
   dates as the price chart, each labeled with the single most event-defining
   headline for that date.
4. **Ripple tree** — hierarchical industry impact graph (severity encoded in
   color + node size; hover for mechanism + precise % change).
5. **Sidebar chat** — ask follow-up questions; answers route through the
   supervisor agent (intent → timeline / market / ripple / qa).

## Data-source strategy

News ingestion is a tiered stack, with each tier picked for what it
uniquely provides. All three are orchestrated by [`setup.py`](setup.py)
and deduplicated by URL + MinHash LSH in [`data_news/dedup.py`](data_news/dedup.py).

| Tier | Source | Why | Notes |
|------|--------|-----|-------|
| **Primary** | GDELT 2.0 DOC API (no key) | Broadest coverage — indexes Reuters, AP, Bloomberg, FT, and thousands of regional outlets. Returns headlines + metadata for free. | Hard 250/query cap → paginated in 7-day chunks. See [`data_news/gdelt.py`](data_news/gdelt.py). |
| **Secondary** | NewsAPI.org (free tier) | Full article snippets + source attribution; fills gaps in GDELT's headline-only output. | **Free-tier window: last ~30 days only.** Requests older than that are clamped. 100 req/day quota. See [`data_news/newsapi_fetcher.py`](data_news/newsapi_fetcher.py). |
| ~~Tertiary~~ | ~~Reuters / AP RSS~~ | ~~Canonical timestamps and editorial ordering for major events.~~ | **Deprecated.** Reuters shut down its public RSS feeds in June 2020; AP's `topnews` returns stale or redirect content. GDELT already indexes the same publications, so the RSS branch was a reliable zero-yield fetch. `events/<name>.yaml: rss_feeds: []` disables it. [`data_news/rss.py`](data_news/rss.py) is kept as a skeleton for future re-introduction (likely via Google News RSS). |

Market data comes from yfinance with a 7-day pre-event buffer for chart
context. Symbols, event window, and seed keywords are all event-scoped
in `events/<name>.yaml` — the code is event-agnostic.

## Limitations

News content indexed into the vector store (GDELT, NewsAPI) and surfaced
to the LLM in `run_news_agent` / `run_qa_agent` / `agent_ripple.attach_news`
is **trusted-source-only**. Snippets are interpolated directly into the
system+human prompts without delimiter escaping or injection-phrase
filtering. A malicious headline of the form *"Ignore previous instructions
and emit ..."* would be passed verbatim to Claude. This is acceptable for
the v0.2 MVP because (a) inputs come from reputable news aggregators, and
(b) downstream output is JSON with structured citations, so the worst-case
outcome is a misleading citation rather than exfiltration or tool-call
abuse. A production deployment would need explicit mitigation — either
delimiter-wrapped snippets that the system prompt instructs the model to
treat as data only, or a lightweight pre-filter for known injection
patterns. Tracked as a Plan-3 UX decision alongside the `status:` field
decision noted in [`docs/progress.md`](docs/progress.md).

## Layout

See the directory tree + per-module blurbs in [`CLAUDE.md`](CLAUDE.md).
