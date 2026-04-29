# Macro Event Ripple Tracker — Project Report
*Applied Finance, v0.2 — Fordham University, 2026-04-28*

## 1. Business Problem

When a major macro or geopolitical event happens — a sanctions package, a strait closure, an OPEC+ surprise cut — analysts need to map the second-order ripples across industries and asset classes within hours, not days. Yet the inputs are scattered: hundreds of news articles per week, dozens of correlated tickers, and a moving timeline of sub-events that interact non-linearly. Doing this by hand is slow and error-prone; missing a ripple costs alpha or risk-management lead time.

**Macro Event Ripple Tracker (MERT)** is an agentic RAG system that turns a single event description into a grounded ripple analysis: a chronological timeline, a multi-level industry impact tree, attached market data, and a free-form Q&A surface — all with citations back to source articles. The MVP is wired to one event (2026 Iran War / Strait of Hormuz closure), but every component is event-agnostic and driven by a YAML config, so a new crisis is a config copy + one ingestion run away.

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Streamlit UI (M5)                                                │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────────┐     │
│  │ Price chart │ │ Detail panel │ │ Sidebar persistent chat │    │
│  └─────────────┘ └──────────────┘ └────────────────────────┘     │
│  ┌──────────────┐ ┌──────────────────────────────────────┐       │
│  │  Event axis  │ │  Ripple tree (interactive, agraph)    │      │
│  └──────────────┘ └──────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────── Supervisor (M4, LangGraph) ─────────────────────┐
│  classify_intent → { qa | timeline | market | ripple }            │
│         │                                                          │
│  ┌──────┴──────┬───────────┬────────────────┐                     │
│  ▼             ▼           ▼                ▼                      │
│ run_qa     run_news   run_market       run_ripple                 │
│  agent      agent      agent          (M3 generator)              │
└─────────┬───────────────────┬────────────────┬───────────────────┘
          │                   │                │
          ▼                   ▼                ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ Vector retrieval │  │   Market data    │  │  Ripple tree LLM │
│ (ChromaDB +      │  │   (yfinance      │  │  (Claude Sonnet) │
│  MiniLM)         │  │    CSV cache)    │  │                  │
└────────▲─────────┘  └────────▲────────┘  └──────────────────┘
         │                     │
┌────────┴─────────┐  ┌────────┴────────┐
│ M1 news ingest   │  │ M2 market data  │
│ (GDELT+NewsAPI)  │  │ (yfinance)      │
└──────────────────┘  └─────────────────┘
```

**Tech stack.** Python 3.11; Claude Sonnet 4.6 via `langchain-anthropic` + `langgraph`; ChromaDB + sentence-transformers `all-MiniLM-L6-v2` (local, free) for dense retrieval; Streamlit + Plotly + streamlit-agraph for the UI; yfinance + pandas for prices. All news sources are free-tier (per course constraint).

**Key design decisions.**

1. **Event config drives every event-specific knob** — keywords, tickers, date windows live in `events/iran_war.yaml`; production code holds zero hardcoded event references. Adding a new event = copying the YAML.
2. **Modular per-zone UI** — `ui/price_chart.py`, `ui/event_axis.py`, `ui/ripple.py`, `ui/sidebar_chat.py`, `ui/price_detail_panel.py` each export a single `render(cfg, as_of)` so layouts can be re-arranged without touching logic, and pure helpers are unit-testable in isolation.
3. **LangGraph for the supervisor loop** — `agent_supervisor.py` classifies user intent, routes to one of four specialized workers, and merges partial state. Workers can be tested independently with mocked LLMs.
4. **Three-phase ripple generation** — `agent_ripple.py` first asks the LLM for the bare tree structure, then attaches news citations per node via vector retrieval, then attaches market data. Avoids one giant LLM call and keeps each phase auditable.
5. **Honest fallbacks at every LLM-JSON boundary** — every consumer guards both `json.JSONDecodeError` and an `isinstance` shape gate. Wrong-shape JSON is a strictly more likely failure than parse failure when the model is instructed to "emit JSON," so both must be handled.

## 3. Dataset

**News corpus — 1,387 unique articles** over the event window 2026-02-28 → 2026-04-16, deduplicated across three sources:

| Source | Raw count | Mechanism |
|---|---|---|
| GDELT 2.0 DOC API | 1,750 | 7 weekly chunks × 250-record cap (GDELT's hard ceiling per query) |
| NewsAPI.org (free) | 100 | 100-result hard cap on free tier; 30-day lookback |
| RSS (Reuters/AP) | 0 | Feeds shut down June 2020; kept as pluggable but empty |
| **After MinHash LSH dedup** | **1,387 unique** | URL dedup: −6; near-duplicate (Jaccard ≥ 0.95): −457 |

**Market data — 11 tickers**, daily OHLCV from yfinance, cached as CSV. Includes Brent (BZ=F), WTI (CL=F), natural gas (NG=F), aluminum (ALI=F), S&P 500 (^GSPC), defense ETF (ITA), energy ETF (XLE), CF Industries (fertilizer), plus three more spanning shipping / petrochemicals / utilities.

**Embeddings.** ChromaDB persistent index over `headline + snippet` text, embedded via `all-MiniLM-L6-v2` (local sentence-transformer, 256-token input window, ~80MB on first download). Embedding model is free and runs entirely on CPU.

**Why free-only.** The course rule excludes paid APIs (Mediastack, NewsCatcher, Bloomberg, Refinitiv) and any full-text scraping that would touch ToS gray-area domains. The dataset section's biggest single consequence is that the corpus is built over headlines + ~200-character previews rather than full article bodies — see Limitations §1.

## 4. Evaluation

The eval harness in `eval/` measures four dimensions per spec §9, run end-to-end via `python -m eval.run_eval --event iran_war`. Per Lecture 9 Slide 10's Week 2/3 emphasis on iterative quality-testing, the system was iterated **six times** (v1 → v6) over 2026-04-27/28, with each iteration committed as a code/prompt change paired with a markdown report.

### v1 → v6 numbers

| Dimension | v1 | v6 | Δ | What drove the change |
|---|---|---|---|---|
| §9.1 retrieval precision@5 | 0.76 | 0.76 | — | (plateau is structural) |
| §9.2 ripple sector precision | 21.2% | **58.6%** | **+37.4pp** | Scoring bug fix + token-overlap matcher |
| §9.2 ripple sector recall | 58.3% | **75.0%** | **+16.7pp** | Token-overlap matcher + corpus refresh |
| §9.2 price integrity (in tree) | 33/33 | 36/36 | — | always perfect |
| §9.3 QA faithfulness | 0.55 | **0.60** | +0.05 | Corpus refresh broke out of judge noise band |
| §9.4 market spot-check | 5/5 | 5/5 | — | always perfect |

### Iteration narrative

**Iteration 1 — §9.2 N:1 scoring bug.** The original `score()` loop iterated truth sectors first, with an early `break` after the first AI-sector match. Once one AI sector matched a given truth, every sibling AI sector that referred to the same truth was incorrectly labelled "hallucinated." Fix: invert the loop so each AI sector is scored independently against all truths. Precision: 21.2% → 37.1%.

**Iteration 2 — token-overlap fuzzy matcher.** Substring-only matching missed obvious paraphrases — "Industrial Metals & Materials" was hallucinated against "Aluminum / energy-intensive metals" because no literal substring matched. Added a fallback: lowercase + plural-strip + a small stoplist of generic business words (industry, manufacturing, service, market, system, supply, equipment, global, energy) + token Jaccard. Precision: 37.1% → 48.1%; recall: 58.3% → 66.7%.

**Iteration 3 — QA prompt tightening.** Added four hardening rules to `prompts/qa_system.txt` forbidding extrapolation (no inventing numbers/prices, prefer snippet-close phrasing, offer "available coverage indicates X but does not specify Y" instead of filling gaps). Empirical impact on §9.3 alone was within LLM-judge noise (0.50–0.55 range). Kept anyway because the rules are forward-compatible with any future corpus expansion.

**Iteration 4 — corpus refresh.** Re-fetched GDELT + NewsAPI to lift the corpus from 1,031 → 1,387 unique articles. §9.3 jumped to **0.60** — the first real movement on §9.3, breaking out of the noise band. §9.2 recall to 75.0%. §9.1 precision@5 stayed at 0.76, which **proves corpus size was not the §9.1 bottleneck**.

**Iteration 5 — query rewriting.** Hypothesis: §9.1 stuck at 0.76 because retrieval queries were too generic. Added `eval/query_rewriter.py` to LLM-rewrite each test query with event context before retrieval (e.g., *"How high did Brent crude go after Hormuz closed?"* became *"Brent crude oil price spike Hormuz closure Iran war 2026 shipping disruption"*). precision@5 stayed at 0.76. Per-query analysis showed the LLM judge consistently rejects ~24% of hits because it strictly enforces `must_be_about` keywords — articles about general "oil prices" get rejected for not naming "Brent" specifically. The plateau is **structural**, not a query-phrasing problem.

The complete v1–v6 reports are preserved at [`eval/results/eval-iran_war-*.{md,json}`](../eval/results/) and form the appendix evidence for this writeup.

## 5. Limitations

### 5.1 Primary: Free-tier APIs only — corpus is headline + ~200 chars, not full article text

The ingestion pipeline uses only free-tier data sources, per the course constraint. The consequence is structural:

- **GDELT 2.0** DOC API returns article **metadata only** — URL, headline, domain, publication date. No body content.
- **NewsAPI.org free tier** returns a ~200-character `content` preview, capped at 100 total results per query, within a 30-day lookback.
- **Reuters / AP RSS feeds** shut down in June 2020 and return zero usable content.

The vector index is therefore built primarily over **headlines plus short descriptions**, not full articles. This caps analytical depth in two specific ways: (a) the grounded QA agent cannot cite mid-article evidence, only headline-level claims — which is why §9.3 faithfulness tops out near 0.60 even with a tightened prompt; (b) the ripple tree's "supporting news" per sector is a snippet pointer rather than an excerpted quote, which is informative but not exhaustive. The system responds honestly when coverage is insufficient — the UI surfaces explicit `no_nearby_news` / `insufficient_evidence` reason codes instead of hallucinating.

Lifting this single constraint would require either (a) **full-text scraping** — blocked by paywalls on major outlets (WSJ, FT, NYT, Bloomberg, Economist) and ToS gray-area on others, or (b) a **paid news API tier** (Mediastack, NewsCatcher, etc.) — both excluded by the project's free-only constraint. Every other limitation in this report is downstream of this one.

### 5.2 Single-event scope

All wiring is event-agnostic and YAML-driven (a new event = `cp events/iran_war.yaml events/<new>.yaml`, edit keywords + tickers, run `setup.py`), but only the 2026 Iran War / Strait of Hormuz crisis is fully populated. A reference corpus from analogous historical events (1979 Iranian Revolution, 1990–91 Gulf War) was scoped as a week-2 add-on but did not ship in v0.2.

### 5.3 Prompt injection surface

News snippets are interpolated directly into the QA / news worker system prompts without delimiter escaping. A hostile snippet of the form *"Ignore previous instructions..."* would be passed verbatim to Claude. Acceptable for an MVP that ingests from reputable aggregators (worst case is a misleading citation, not exfiltration), but a production deployment would need delimiter-wrapped context blocks or an injection-pattern pre-filter.

## 6. Next Steps

In rough priority order, all anchored to spec §11 ("Future Work"):

- **More events.** The architecture is already event-agnostic. The first multi-event sprint is to populate two more `events/*.yaml` files (a non-energy macro shock for breadth, a historical event for depth) and walk through the same ingestion + ripple-generation pipeline end-to-end. (§11.1)
- **Historical reference corpus** — curated summaries from the **1979 Iranian Revolution** and **1990-91 Gulf War**, loaded by `agent_ripple.generate_structure` as few-shot priors. The goal is not a full pipeline for those events but a small set of hand-edited markdown files that anchor sector mechanics in historical analogy when the LLM generates the ripple tree.
- **Multi-event side-by-side comparison.** Once two events exist, a comparison dashboard lets analysts hold sector mechanics constant and see how a different event reshapes the tree (which sectors recur, which severity rankings invert).
- **User-input arbitrary events.** A "New Event" UI form replacing the YAML edit step, validating ticker symbols and date ranges before kicking off `setup.py`. (§11.1)
- **Full-text article access.** The single biggest unblocker for analytical depth — see Limitations §5.1. Two paths: (a) a paid API tier outside the course's free-data rule, or (b) targeted full-text scraping with a ToS-safe domain whitelist. Lifting this directly raises the §9.3 faithfulness ceiling. (§11.2)
- **Real-time / incremental data refresh.** Today `setup.py --refresh` rebuilds the full window from scratch. Production use needs an incremental path — daily GDELT chunks, rolling-window expiry, streaming dashboard. (§11.4)
- **Quantitative event-study layer.** Per §11.3, layer Granger causality and event-study return / volatility statistics onto the qualitative ripple tree, converting "Defense / Aerospace surged" into measured Δ-returns + significance tests against a baseline.
- **Knowledge-Graph RAG.** Model sector dependencies as graph edges (fertilizer ← natural gas ← oil ← geopolitical) so ripple chains are queryable rather than re-generated each time. (§11.3)
- **Continuous eval-drift detection** with TruLens or equivalent, replacing the current snapshot-only harness with online quality monitoring. (§11.5)

---

**Repository:** [github.com/fangyihe-fordham/macro-ripple-tracker](https://github.com/fangyihe-fordham/macro-ripple-tracker)
**Final eval report:** [`eval/results/eval-iran_war-20260428-003229.md`](../eval/results/eval-iran_war-20260428-003229.md)
**Test suite:** 112 passed + 4 RUN_LIVE-gated
