# CLAUDE.md — Macro Event Ripple Tracker

> **For the next Claude Code session.** Read this file first. It is the single source of truth for project conventions and active scope.

## Project

Applied Finance course project, v0.2. Agentic RAG that turns a macro/geopolitical event into a grounded ripple analysis: timeline, multi-level industry impact tree, market data, and free-form Q&A — all in one Streamlit app backed by Claude Sonnet + LangGraph.

**Authoritative design spec:** [`MacroRippleTracker_Spec_v0.2.docx`](MacroRippleTracker_Spec_v0.2.docx) in repo root. Translated markdown version is on disk at `/tmp/spec.md` (not committed). If that tmp file is gone, re-run `pandoc --track-changes=all MacroRippleTracker_Spec_v0.2.docx -o /tmp/spec.md`.

## Implementation Plans

All saved in `docs/superpowers/plans/`:

- [`2026-04-16-plan-1-data-foundation.md`](docs/superpowers/plans/2026-04-16-plan-1-data-foundation.md) — **DONE + HARDENED (end of Session 4).** 12 tasks + 2 Session-3 infra follow-ups + 15 Session-4 hardening/cleanup commits (8 code-review-driven in Round 1, 6 user-directed in Round 2, 1 regression fix). All Plan 1 verification checklist items still green; live run delivers richer data (1,387 unique articles vs 1,217 in Session 3; retrieval top hit 0.533 vs 0.39).
- [`2026-04-16-plan-2-agents.md`](docs/superpowers/plans/2026-04-16-plan-2-agents.md) — **DONE + REVIEWED + HARDENED (end of Session 7).** 15 tasks + 2 mid-plan code-review checkpoints (after Task 8 + after Task 13) + 1 post-completion comprehensive review (Session 7) driving a final hardening commit (`d98e492`). Plan 1 reconciliation (`35f46e2`) + Session-6 additions to plan file footer (`0.3.17` patch bump, `override=True` note, `strip_fences` hoist, Task-8 test snippet correction). Four deliberate deviations from plan text in Session 6, all user-approved at decision time (see progress.md). Session 7 added LLM-JSON shape validation, graceful `run.py` exits, defensive `.get()`/`None` guards in `agent_ripple`, and a README prompt-injection note. Suite: 60 passed + 4 skipped.
- [`2026-04-16-plan-3-ui-eval.md`](docs/superpowers/plans/2026-04-16-plan-3-ui-eval.md) — **Tasks 1–3 DONE inline (Session 9, commits `1c0e0fa` → `c750b01` + Timeline-bug fix `a835bf0`); Tasks 4–5 SUPERSEDED by Plan 3.5; Tasks 6–12 (eval harness §9) NOT STARTED.** Plan 3 UI should call `setup.is_setup_in_progress()` before triggering `retrieve()` against ChromaDB — see `vector_store.py` docstring and C4 lock commit `e5a84ad`. Plan 3 UI must import `llm.get_chat_model()` (not instantiate `ChatAnthropic` directly) so it inherits Plan 2's `load_dotenv(override=True)` fix for the Claude-Desktop-empty-key quirk — see Library Quirks → `python-dotenv`. **Two Plan 3 UX decisions** (carried into Plan 3.5/3.6): (1) `status` field on news/qa empty-retrieval responses, (2) prompt-injection mitigation for news snippets — both still in `README.md` "Limitations" as deferred items.
- [`2026-04-24-plan-3.5-ui-redesign.md`](docs/superpowers/plans/2026-04-24-plan-3.5-ui-redesign.md) — **DONE + REVIEWED (end of Session 9).** 9 tasks, executed via subagent-driven mode → 16 commits on `main` (`7b8f6a1` → `4b102aa`). Replaces 4-tab dashboard with single-page event-focused dashboard: sidebar (event picker + as-of + metadata + chat) + main `[ price_chart 70% | detail_panel 30% ]` + `event_axis` full + `ripple_tree` full. New leaf agent `agent_price_explainer.py` + `prompts/price_explainer_system.txt`. Carryover hardening landed: ripple agent now has English-only prompt + graceful `try/except` in `run_ripple_agent` (`7b8f6a1` + `2c94a5e`). Suite: 85 passed + 4 skipped. **Three live UX failures discovered in Plan 3.5's UI** are addressed in Plan 3.6 below — do NOT treat Plan 3.5 as production-ready; only a finished Plan 3.6 makes the UI demo-ready.
- [`2026-04-26-plan-3.6-ui-interaction-fixes.md`](docs/superpowers/plans/2026-04-26-plan-3.6-ui-interaction-fixes.md) — **PARTIALLY EXECUTED (Session 10).** Task 1 landed cleanly (`52a269a`): real click handler via `streamlit-plotly-events`. Task 2 landed in two commits because the first visual pass (`bc67b5f`) passed tests but failed the user's live review; follow-up `dcc5850` reworked the axis into English-only, multi-lane, collision-suppressing labels and tightened retrieval relevance via `cfg.display_name`. The plan file now includes an Addendum with runtime corrections and a mandatory user-review gate after every task. **Task 3 has NOT started** — execution is blocked until the user reviews the revised Task-2 UI and explicitly says `continue`. One additional user-directed follow-up commit (`9c9334e`) is adjacent but **out of original Plan-3.6 scope**: it improved price-detail fallback diagnostics (`±2`-day window, stronger query, explicit `reason_code` / `reason_detail`). Plan-file end-state target is **91 passed + 4 skipped**; current repo state is **92 passed + 4 skipped** because of that extra diagnostics commit.

Execute plans task-by-task. Each task = TDD cycle + a single `git commit`. Do not batch tasks into one commit.

## Tech Stack

- **Python 3.11** in dedicated conda env `macro-ripple` at `/opt/anaconda3/envs/macro-ripple/bin/python`. Do **not** use the user's `base` env (Python 3.13, risky for chromadb + sentence-transformers).
- **Config:** `python-dotenv` (loads `.env` at `config.py` import time)
- **Data:** `yfinance`, `pandas`, `pyyaml`, `pydantic` v2
- **News:** `gdeltdoc`, `newsapi-python`, `feedparser`
- **Dedup:** `datasketch` (MinHash LSH)
- **Vector store:** `chromadb` (persistent, local) + `sentence-transformers` (`all-MiniLM-L6-v2`, local, free)
- **Agents:** `langchain-anthropic` + `langgraph` + `claude-sonnet-4-6` via `ANTHROPIC_API_KEY` (provided via `.env` as of Session 2)
- **UI:** `streamlit` + `plotly` + `streamlit-agraph` + `streamlit-plotly-events` (local web app at http://localhost:8501; no deployment)
- **Testing:** `pytest`, `pytest-mock`, `responses`

All pinned versions are in [`requirements.txt`](requirements.txt).

## Working Mode

**Subagent-driven development** with the following per-task mapping (locked for Plan 1; revisit after Plan 1 finishes):

| Plan 1 tasks | Mode | Rationale |
|---|---|---|
| 1 — Scaffold | inline | Already done |
| 2 — `config.py` | inline | Shared foundation, simple |
| 3–4 — M2 market | inline | Small surface, single file |
| **5–10 — M1 news package** | **subagent** | 6 sibling submodules, easy to parallelize cognitive load; each task gets a fresh context |
| 11 — `setup.py` orchestrator | inline | Integration glue — needs to see all M1 submodule shapes together |
| 12 — Live smoke | inline | Trivial |

When dispatching a subagent for an M1 task: pass the full task text from the plan verbatim, plus a brief context paragraph telling the subagent which prior commits have landed and what public APIs exist. Do **not** let the subagent read the plan file — give it the exact task text inline.

For Plans 2 and 3: decide per-task after Plan 1 lands. Default to subagent for LLM-heavy code (agent_ripple, supervisor nodes), inline for UI tabs and eval modules (small and tightly coupled to user-visible behavior).

**Plan 2 post-mortem (Session 6):** all 15 tasks were executed **inline**, not subagent. Rationale: each task built directly on the previous one's just-written interface (e.g. Task 7 orchestrator calls Tasks 4+5+6; Task 13 graph assembly wires Tasks 9+10+11+12), and the total surface was small (~3 production modules, ~300 lines). Subagent parallelism would have either (a) duplicated context for each task or (b) required careful handoff of the just-landed public API, both more expensive than running inline. **Plan 3 mode guidance (revised):** default to **inline** for UI tabs + eval harness tasks that share module state; subagent only for parallelizable independent work (e.g. one subagent per evaluation metric if they don't share a mock LLM setup).

## Git Convention

- Single branch: `main`. No feature branches unless user asks.
- **One commit per task.** Commit message format: `<type>(<scope>): <summary>` where `<type>` ∈ {feat, chore, test, docs, eval, fix}, `<scope>` is the module code (`M1`, `M2`, `config`, etc.) when applicable. Include the Co-Authored-By trailer.
- Never skip hooks. Never amend. Never force-push.
- Stage explicitly by file (`git add <files>`) — do not `git add -A`.

## Acceptance Criteria (every task)

Every task — inline or subagent — must clear all six before being declared done:

1. **`pytest -v` — all PASSED, zero failures.** Run the full suite, not just the new test file.
2. **`git diff HEAD~1 --stat` — only files listed in the plan are touched.** No drive-by edits to unrelated modules.
3. **New function signatures match `MacroRippleTracker_Spec_v0.2.docx`.** If a plan task's function shape contradicts the spec, stop and flag it before implementing.
4. **No hardcoded tickers / dates / keywords / paths in production code.** Everything event-specific comes from `EventConfig` (via `load_event`) or from function parameters. `DATA_DIR` env var is the one allowed runtime knob.
5. **Commit message is `<type>(<scope>): <desc>` with the `Co-Authored-By: Codex Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.** One commit per task.
6. **Show the full `pytest -v` output before declaring done.** No paraphrasing the result — paste the tail that shows `N passed`.

If a subagent returns green but any criterion above is unmet (e.g. extra files touched, hardcoded values, test-shaped decoration in production code), review and fix in a follow-up commit before moving on.

## Current Directory Structure (real, end of Session 10 — Plan 3.6 Tasks 1–2 landed; Task 3 blocked at user review gate)

```
/Users/fangyihe/appliedfinance/
├── CLAUDE.md                     # ← this file
├── README.md                     # data-source strategy + quickstart + Plan-3.5 "Dashboard layout" section
├── MacroRippleTracker_Spec_v0.2.docx
├── environment.yml               # conda spec
├── requirements.txt              # pinned deps; Session-9 added: streamlit==1.39.0 + plotly==5.24.1 + streamlit-agraph==0.0.45; Session-10 re-added: streamlit-plotly-events==0.0.6
├── .gitignore                    # includes `.env` and `data/`
├── .env                          # gitignored — NEWSAPI_KEY, ANTHROPIC_API_KEY (both populated)
├── .env.example                  # committed template — same keys, empty values
├── config.py                     # EventConfig pydantic (MUTABLE); load_event() calls load_dotenv() WITHOUT override (tests monkeypatch env vars before importing)
├── llm.py                        # ChatAnthropic factory pinned to claude-sonnet-4-6; strip_fences() utility; load_dotenv(override=True) — Claude Desktop can export empty ANTHROPIC_API_KEY
├── agent_ripple.py               # M3 three-phase ripple tree generator: generate_structure (Session-9 +isinstance shape gate `2c94a5e`) → attach_news → attach_prices; public entrypoint generate_ripple_tree()
├── agent_supervisor.py           # M4 LangGraph supervisor; AgentState TypedDict; 5 nodes; Session-9: max_tokens 2048→4096 in run_news_agent (`a835bf0`); run_ripple_agent now wraps generate_ripple_tree in try/except (ValueError, JSONDecodeError) → graceful empty tree (`7b8f6a1`)
├── agent_price_explainer.py      # [Session 9 + 10] Leaf agent for "why did <ticker> move on <date>?". Retrieves event-context news within ±2 days using date + ticker + cfg.display_name + cfg.seed_keywords, asks LLM for {direction, headline_summary, key_drivers, caveats, supporting_news}; never raises; returns explicit status/reason_code/reason_detail on fallback (`no_retrieval`, `no_nearby_news`, `insufficient_evidence`)
├── run.py                        # CLI wrapper (argparse --event/--query/--as-of) → agent_supervisor.run() → JSON stdout
├── data_market.py                # M2: download_prices, get_price_on_date, get_price_changes (always keyed by ALL cfg.tickers with `available` flag), get_price_range
├── setup.py                      # orchestrator CLI: fcntl-locked (setup.lock); --refresh wipes prices/+articles.json+chroma_db; exports is_setup_in_progress()
├── data_news/                    # M1 news package (unchanged in Session 9)
│   ├── __init__.py               # re-exports retrieve, index_articles, reset, read_articles, write_articles
│   ├── gdelt.py                  # 7-day chunk pagination (num_records=250, 2s sleep, per-chunk try/except — load-bearing)
│   ├── newsapi_fetcher.py        # 30-day clamp + per-page try/except + 100-total-cap detection via NewsAPIException code
│   ├── rss.py                    # keyword-filtered on STRIPPED summary; _strip_html removes <script>/<style>/<!--...--> content-and-all before tag strip
│   ├── dedup.py                  # URL dedup → MinHash LSH (threshold 0.95; returns (kept, stats))
│   ├── store.py                  # articles.json read/write via DATA_DIR env var
│   └── vector_store.py           # ChromaDB + MiniLM; telemetry logger silenced at module load; reset() clears SharedSystemClient cache; sha1 stable IDs
├── prompts/                      # file-backed prompts
│   ├── __init__.py               # load(name) reads prompts/<name>.txt and .strip()s
│   ├── ripple_system.txt         # M3 ripple tree JSON schema prompt; {max_depth} placeholder; Session-9 adds English-only rule
│   ├── intent_system.txt         # M4 intent classifier — emits JSON {intent, focus}
│   ├── timeline_system.txt       # M4 news/timeline — emits JSON list; Session-9 adds English-only rule (`a835bf0`)
│   ├── qa_system.txt             # M4 grounded QA — emits JSON {answer, citations}; cites snippet URLs only
│   └── price_explainer_system.txt # [NEW Session 9] M3.5 per-day price attribution; English-only; structured 5-key JSON
├── ui/                           # [Session 9 + 10] Streamlit modular UI (single-page event-focused dashboard)
│   ├── __init__.py               # empty
│   ├── price_chart.py            # Viz 1: Brent line + significant-move markers + y-toggle ($ / %) + threshold slider; Session-10 Task 1 switched click handling to plotly_events(click_event=True) + _click_event_to_iso helper, so plain marker click now updates selected_date without modebar tool activation
│   ├── price_detail_panel.py     # Zone 3: reads st.session_state["selected_date"] → calls agent_price_explainer.explain_move via @st.cache_data wrapper (cache key now includes cfg.display_name + seed_keywords) → renders ▲/▼ + summary + drivers + caveats + ≤3 cited news + explicit fallback reason block when status=="fallback"
│   ├── event_axis.py             # Viz 2: horizontal time axis with markers at significant-move dates; Session-10 Task 2 replaced markers+text with multi-lane annotations + stems + pinned x-range + English headline translation + strict collision suppression; Task 3 sector-mode branch NOT started yet
│   ├── sidebar_chat.py           # Persistent chat in sidebar; calls agent_supervisor.run; format_supervisor_result() intent-branches for qa/market/timeline/ripple
│   └── ripple.py                 # M5 ripple tree (streamlit-agraph); 20-char label truncation + pct-in-tooltip + size-by-severity (critical=22/significant=18/moderate=14); Task 3 NOT started, so tree_to_graph_elements still returns 2-tuple (nodes, edges) and agraph() return value is still discarded
├── ui_app.py                     # [REWRITTEN Session 9] Single-page event-focused dashboard shell. 2-col top: [price_chart 70% | detail_panel 30%]; below: event_axis full-width; below: ripple_tree full-width; sidebar: event picker + as-of + metadata + "Clear cache & refresh" + persistent chat. Resets selected_date on event switch; selected_sector wiring NOT landed yet
├── events/
│   └── iran_war.yaml             # RSS feeds deprecated (empty list)
├── data/                         # runtime, gitignored; populated by setup.py run
│   ├── articles.json             # ~1,387 unique articles after cross-source dedup
│   ├── prices/*.csv              # 11 files, one per cfg.tickers entry
│   ├── chroma_db/                # persistent MiniLM vector index
│   ├── manifest.json             # event, snapshot_utc, article_count, source_counts, dedup, ticker_count, missing_tickers
│   └── setup.lock                # fcntl lock file; presence + non-free state = setup.py is running
├── docs/
│   ├── progress.md               # session log (Sessions 1–10)
│   └── superpowers/plans/
│       ├── 2026-04-16-plan-1-data-foundation.md     # DONE + hardened
│       ├── 2026-04-16-plan-2-agents.md              # DONE + reviewed (Session 6)
│       ├── 2026-04-16-plan-3-ui-eval.md             # Tasks 1-3 DONE inline, Tasks 4-5 SUPERSEDED by Plan 3.5, Tasks 6-12 NOT STARTED
│       ├── 2026-04-24-plan-3.5-ui-redesign.md       # [NEW Session 9] DONE via subagent-driven (16 commits)
│       └── 2026-04-26-plan-3.6-ui-interaction-fixes.md  # [Session 9 + 10] PARTIALLY EXECUTED: Task 1 done, Task 2 done after follow-up, Addendum appended, Task 3 blocked on user "continue"
└── tests/
    ├── __init__.py               # empty
    ├── conftest.py               # fixtures_dir, tmp_data_dir (sets DATA_DIR env)
    ├── test_config.py            # 3 tests
    ├── test_data_market.py       # 8 tests
    ├── test_gdelt.py             # 3 tests (incl. chunk-failure resilience; monkeypatches gdelt.time.sleep)
    ├── test_newsapi.py           # 6 tests
    ├── test_rss.py               # 3 tests
    ├── test_dedup.py             # 2 tests
    ├── test_store.py             # 2 tests
    ├── test_vector_store.py      # 4 tests
    ├── test_setup_cli.py         # 3 tests
    ├── test_smoke_live.py        # 2 tests, gated by RUN_LIVE=1
    ├── test_llm.py               # 3 tests
    ├── test_agent_ripple.py      # 6 tests + 1 Session-9 hardening test (`2c94a5e`) on isinstance shape gate
    ├── test_agent_supervisor.py  # 10 + 2 Session-9 tests: ripple-fallback path (`7b8f6a1`) + ?? for graceful run_ripple_agent
    ├── test_live_agents.py       # 2 tests, gated by RUN_LIVE=1
    ├── test_run_cli.py           # 3 tests
    ├── test_agent_price_explainer.py  # [Session 9 + 10] 5 base tests + 2 Session-9 tightening tests (`bc78f03`) + 1 query-builder test + 1 no-nearby-news reason test; existing fallback tests now assert status/reason_code
    ├── test_ui_helpers.py        # [Sessions 9–10 evolve] ripple + price_chart click helper (5) + price_detail_panel (3 incl. fallback-reason rendering) + event_axis (3: pinned range, multi-lane placement, translation) + sidebar_chat (3) + ripple-polish (4)
    └── fixtures/
        ├── yf_brent_sample.csv
        ├── gdelt_response.json
        ├── newsapi_response.json
        ├── rss_sample.xml
        ├── ripple_llm_response.json
        └── intent_examples.json
```

**Test counts:** 96 collected → **92 pass + 4 gated-skip** (end of Session 10). Relative to end of Session 9's 85+4, Session 10 added +7 net tests: +1 price-chart click helper (`52a269a`) +2 Task-2 first-pass event-axis tests (`bc67b5f`) +1 translation/relevance event-axis test (`dcc5850`) +3 price-attribution diagnostics tests (`9c9334e`).

**Modules deleted in Session 9 (Plan 3.5 Task 8 single-page rewrite):** `ui/timeline.py` (superseded by `event_axis.py` for narrative timeline), `ui/market.py` (stub never implemented; `price_chart.py` covers Brent specifically + `sidebar_chat.py` market-intent route covers ad-hoc), `ui/qa.py` (stub never implemented; `sidebar_chat.py` is the chat surface). Their corresponding tests were deleted (timeline) or never existed (market, qa).

**Commits on `main` added in Session 10 (newest first):** `9c9334e` (price-detail fallback diagnostics) → `dcc5850` (event_axis readability follow-up — English lanes + relevance) → `bc67b5f` (event_axis annotations + pinned x-range + plan addendum) → `52a269a` (price_chart click handler via plotly_events). 4 code commits total since end of Session 9 wrap-up (`b2734bb`).

**Commits on `main` added in Session 9 (newest first):** `4b102aa` (post-Plan-3.5 review cleanups) → `f4483c2` (README update) → `a4db058` (Task 8 single-page shell) → `154f490` (Task 7 ripple polish) → `f4f6f20` (Task 6 fix: None pct guard) → `5905649` (Task 6 sidebar_chat) → `5a368fc` (Task 5 follow-up: color import) → `1713b6b` (Task 5 event_axis) → `46a357c` (Task 4 follow-up: readability) → `a73ab81` (Task 4 price_detail_panel) → `2d56cc5` (Task 3 follow-up: pct-mode div-by-zero) → `e4bd3be` (Task 3 price_chart) → `bc78f03` (Task 2 follow-up: tighten fallback tests) → `4935e01` (Task 2 agent_price_explainer) → `2c94a5e` (Task 1 follow-up: isinstance shape gate) → `7b8f6a1` (Task 1 ripple harden) → `c750b01` (Plan-3 Task 3 ripple) → `a835bf0` (Plan-3 Task 2 timeline-bug fix) → `f5178a6` (Plan-3 Task 2 timeline) → `1c0e0fa` (Plan-3 Task 1 shell). 20 commits total since end of Session 8 (`ab18138`).

**Commits on `main` added in Session 8:** 0 code commits.

**Commits on `main` added in Session 7 (newest first):** **`d98e492`**.

**Commits on `main` added in Session 7 (newest first):**
**`d98e492`** (fix(plan-2): pre-plan-3 hardening — shape validation + graceful CLI errors).

**Commits on `main` added in Session 6 (newest first, all 20 bolded as session-6 additions):**
**`98dbae4`** (docs: session 6 wrap-up) → **`b245786`** (test: gated live) → **`db2c339`** (Task 14 run.py) → **`002d5de`** (plan snippet sync) → **`7464292`** (chore: import consolidation) → **`980cfad`** (Task 13) → **`14c6b56`** (Task 12) → **`5e4d5a5`** (Task 11) → **`0aabd63`** (Task 10) → **`907c5c0`** (Task 9) → **`f74284c`** (CLAUDE.md dotenv quirk) → **`3ff4548`** (refactor: strip_fences hoist) → **`1bba33a`** (plan-2 Task 8 snippet amend) → **`939e126`** (Task 8) → **`728b939`** (Task 7) → **`0db7a0d`** (Task 6) → **`f1f2b8b`** (Task 5) → **`b80d3b9`** (Task 4) → **`bb69ed6`** (Task 3) → **`4d61c68`** (Task 2 llm.py) → **`fdf78bf`** (Task 1 deps + prompt loader).

**Pre-Session-6 commits on `main` (end of Session 5 → end of Session 4, newest first):** `1e70bdd` → `f47e757` → `35f46e2` → `862d263` → `33f88f5` → `0726337` → `90f02db` → `db8beb9` → `5fb2c8c` → `a1138b2` → `e5a84ad` → `15edf56` → `eba54a7` → `36a4d3d` → `62dbc4c` → `45b6157` → `c454c8b` → `ecd92fc` → `aa2f3ea` → `fc3704c` → `3beabee` → `deb4650` → `0b69dbe` → `44e2d12` → `24adb51` → `3e25d3f` → `717d6c2` → `1c0793e` → `d1a23f2` → `b15ba33` → `c3e8fc0` → `60df2ee` → `b4e9fbe` → `d6a9519` → `178f0d0` → `1c5d7ed` → `77bfd0b` → `70e5bc9` → `1a4638a`.

**Live-run baseline (last full `setup.py --refresh` against real APIs, end of Session 4):**
- GDELT: 1,750 (7 chunks, all succeeded this time; rate-limit hits are session-dependent and recovered-by-design).
- NewsAPI: 100 (paginated, capped at page-2 by free tier's 100-total limit as designed).
- RSS: 0 (expected post-deprecation).
- Dedup: 1,850 total → **1,387 unique** (`url_dropped=6, minhash_dropped=457`).
- Prices: 11/11 CSVs, `missing_tickers=[]`.
- Retrieval: `retrieve("Hormuz closure oil price", top_k=3)` → top hit 0.533 on "Crude oil could top $100 as Strait of Hormuz closure halts flows".
- Market: all 11 tickers `available=True`, Brent +30.97%, WTI +36.21%, Aluminum +18.71%, CF +21.37%, S&P 500 +2.09%.

## Scope Lock

**These are firm. Future sessions must not expand scope without explicit user approval.**

**MVP (Plans 1–3):**
- Single event: **2026 Iran War / Strait of Hormuz closure** (`events/iran_war.yaml`)
- All code is event-agnostic (driven by YAML config), but only this one event is wired up

**Week 2 addition (after MVP ships):**
- Add a **reference corpus** from two historical oil shocks: **1979 Iranian Revolution** and **1990–91 Gulf War**
- These are **analytical material only** — curated summaries / excerpts feeding M3's ripple generation as few-shot priors or comparison benchmarks. **Not** a full news + market pipeline for those events.
- Concretely, expect: a `events/historical_reference/` directory with 2–5 hand-curated markdown files per crisis, loaded by M3 at generation time

**Explicitly Out of Scope for MVP (live in §11 Next Steps):**
- User-input arbitrary events via a "New Event" form (§11.1)
- Multi-event side-by-side comparison dashboards
- Real-time / incremental data refresh (§11.4)
- Full-text article scraping beyond what NewsAPI returns (§11.2)
- Cloud deployment (§11.4)
- Knowledge-Graph RAG / Neo4j (§11.3)
- Event-study stats / Granger causality (§11.3)
- TruLens continuous eval (§11.5)

If the user asks for any of the above mid-stream, flag the scope conflict before implementing.

### Course Grading Context & Plan 2.5 Rejection (Session 8, 2026-04-24)

**This is a Fordham Applied Finance course project.** The course context is a scope governor, not a preference. Future sessions MUST read this subsection before proposing any data-layer expansion or any output-quality improvement that would consume >30 minutes of user time.

**Course constraint — 100% FREE data sources only.** Not "prefer free," not "free for MVP" — a rule. The professor requires all ingested data to come from free-tier APIs. This **excludes by course rule**, not by MVP priority:
- Paid NewsAPI tiers (Pro, Business), Mediastack paid, NewsCatcher paid, Bloomberg Terminal API, Refinitiv/Eikon, FactSet.
- Any commercial full-text article provider.
- Any "best-effort" scraping strategy that targets ToS-gray domains or content behind soft paywalls — the gradient between "freely accessible" and "technically free-to-read but restricts automated access" is a judgment call the course rule does not permit taking.

**Professor's grading posture (confirmed by user 2026-04-23 in office-hours-style conversation):** *"Just run the pipeline end-to-end. The final output quality doesn't need to be perfect. Limitations just need to be written up."* The grading weights **process correctness + documented honesty** over **output polish**. A transparent, self-aware limitation is an acceptable deliverable — possibly a better deliverable than a half-built mitigation.

**Four deliverables (all required):**
1. **In-class presentation** — has a dedicated Limitations section.
2. **Live demo** — audience-facing interactive run of the app.
3. **Written report** — has a dedicated Limitations section.
4. **Code repo + README** — current state (end of Session 7): clean, 60+4 tests, ~850 lines production code, README has Limitations section stub that Plan 3 / demo prep should fill in.

**Plan 2.5 (full-text article scraping via `trafilatura` + ChromaDB rebuild) was PROPOSED and REJECTED in Session 8, 2026-04-24.** The rejection is **durable and first-order**. Unless the course constraint itself changes, do NOT re-propose Plan 2.5 in a future session. Three reasons, each independently sufficient:

1. **It would blur the free-data constraint.** Best-effort scraping hits sites on a ToS / paywall gradient. A hard-paywall blacklist (WSJ/FT/NYT/Bloomberg/Economist) is easy. The gray-area middle tier (sites technically free-to-read but restricting automated access) is exactly the judgment call the course rule forbids.
2. **The grading posture says a documented limitation is an acceptable answer.** Scraping targets a quality dimension the grading does not prioritize. Building it consumes time without moving the grade.
3. **Time budget.** User's remaining project time is constrained (self-reported in Session 8). Hours are better spent on Plan 3 execution + live-demo rehearsal than on a second data-layer pass.

**If a future session is tempted to re-propose Plan 2.5 "as a small fix":** stop. All three reasons above are first-order concerns, not judgment calls. Re-proposing implicitly asks the user to re-surface the course constraint that was already surfaced — it's a regression in session memory, not new insight.

**What Plan 2.5 would have looked like (archived here so Session 8 discussion is not re-derived from scratch if the course constraint changes):**
- New module `data_news/scraper.py` wrapping `trafilatura` (open-source Python boilerplate-removal library — `fetch_url` + `extract`). For each article URL surviving dedup: fetch → extract main body → quality filter (length < 500 chars = drop as paywall-teaser / extraction-failure). Articles whose scrape fails retain original headline-only body.
- Concurrency via `concurrent.futures.ThreadPoolExecutor` with ~10 workers, per-domain rate limiting (>=1s same-domain gap) to avoid triggering HTTP 429.
- Hard-paywall domain blacklist (WSJ, FT, NYT, Bloomberg, Economist, Barron's) to skip requests that are guaranteed to fail with an aggregated login-wall page.
- `setup.py` pipeline inserts scraper between `dedup.deduplicate()` and `vector_store.index_articles()`. Adds `scrape_stats: {attempted, succeeded, paywall_detected, failed}` to `manifest.json`.
- **Vector rebuild required** because embeddings are a function of body text: `vector_store.reset()` clears `data/chroma_db/` + `SharedSystemClient` cache; `index_articles(articles_with_full_text)` re-embeds with the longer bodies under the existing `all-MiniLM-L6-v2` sentence-transformer. Re-embedding ~1400 docs on CPU ≈ 15-30s.
- **Token-window caveat:** MiniLM has a ~256-token input window — longer `full_text` is silently truncated by sentence-transformers. B-simple variant accepts the truncation (headline + first ~1000 chars still beats headline alone). B-chunked variant splits long articles into ~800-char chunks, each embedded as its own Chroma document with metadata `parent_url` + `chunk_idx`. UI merges same-URL chunks at render time.
- **Estimated effort at user's measured pace (~15 min/task):** B-simple ~1.5-2h, B-chunked ~3-4h.

**Canonical Limitations paragraph (Session 8, ready to paste into report / presentation / README — DO NOT diverge from this text when Plan 3 edits README's Limitations section):**

> **Data Source Limitation: Article-body Access Constrained by Free-tier APIs.**
> The ingestion pipeline uses only free-tier data sources (per course constraint). GDELT 2.0's DOC API returns article **metadata only** (URL, headline, domain, publication date) and does not include article body. NewsAPI.org's free tier returns a ~200-character `content` preview, capped at 100 total results per query, within a 30-day lookback window. As a result, the vector index (ChromaDB + `all-MiniLM-L6-v2` embeddings) is built primarily over headlines and short descriptions rather than full article text. This constrains the grounded-QA agent's ability to cite mid-article evidence; it responds honestly when snippet coverage is insufficient. Lifting this limitation would require either (a) full-text scraping — blocked by paywalls on major outlets (WSJ, FT, NYT, Bloomberg) and ToS concerns on others, or (b) a paid news API (Mediastack, NewsCatcher) — excluded by the project's free-only constraint. Both paths are captured in §11.2 "Future Work."

**Live-demo tactic (Session 8 guidance to future UI / demo-prep sessions):** the corpus has visible thin spots; audience-freestyle queries risk exposing them. Pre-select and rehearse 4-5 queries. Good demo-query categories:
- (a) Queries where the **ripple-tree structure itself** is the deliverable ("show the impact tree for the Hormuz closure") — not citation-deep-dive.
- (b) Queries that happen to hit the 100 NewsAPI articles with 150-char descriptions (oil / shipping / aluminum / fertilizer topics are NewsAPI-dense in this corpus).
- (c) Market-only queries that route to `run_market_agent` — pure numerical, zero snippet dependency.

**Avoid demo queries that require mid-article facts** (specific quotes, specific numbers buried inside articles whose headlines don't contain them). These are the thin spots.

**Project memory file (outside repo):** `~/.claude/projects/-Users-fangyihe-appliedfinance/memory/project_grading_and_deliverables.md` mirrors this subsection in condensed form. Future sessions auto-load it via the auto-memory system, so if a session asks "should we add X feature," the memory surfaces the professor's constraint without requiring the user to re-explain. The CLAUDE.md subsection you are reading now is the **authoritative in-repo record**; if the two ever diverge, trust this file and update the memory.

## Conventions Established in Tasks 1–5 (+ Session 4 hardening + Session 6 Plan 2 + Session 7 pre-Plan-3 hardening + Session 9 Plan 3 / 3.5 / 3.6)

### UI Conventions (Session 9 — Plan 3 / 3.5 / 3.6)

- **Modular UI under `ui/`.** One Streamlit zone per file: `ui/price_chart.py`, `ui/price_detail_panel.py`, `ui/event_axis.py`, `ui/sidebar_chat.py`, `ui/ripple.py`. Each module exports `render(cfg: EventConfig, as_of: date) -> None`. `ui_app.py` is a thin shell that imports each module's `render` and composes the layout via `st.columns([7, 3])` etc. **Do not consolidate** modules — each is small and unit-testable in isolation.
- **All `@st.cache_data`-wrapped functions taking `EventConfig` use `_cfg` (leading underscore).** See Library Quirks → `streamlit==1.39.0`. Failing this raises `UnhashableParamError` at first call. If you add a new cached function, repeat the convention.
- **Pure-function helpers TDD'd; rendering visually smoked.** Every UI module has unit tests on its pure helpers (`significant_moves`, `to_pct_series`, `_click_event_to_iso`, `_label_y_for_index`, `_assign_label_lanes`, `_headline_to_english`, `pick_headline_for_date`, `format_supervisor_result`, `format_detail_markdown`, `tree_to_graph_elements`). The `render(cfg, as_of)` Streamlit-context function itself is NOT unit-tested (its body interleaves `st.*` calls with helper calls); visual smoke in a `streamlit run` is the verification.
- **Session-state lifecycle discipline.** Every `selected_*` key in `st.session_state` MUST be `pop()`'d in two places: (1) the event-switch reset block (`if st.session_state.get("_last_event") != event_name`); (2) the "Clear cache & refresh" sidebar button. Landed keys today: `selected_date` (Plan 3.5 Task 3) and `chat_history` (sidebar chat, exempt from event-reset semantics). **`selected_sector` is still only a planned Task-3 key, not landed code.** If Task 3 eventually lands, it must be added to BOTH reset paths immediately in the same commit.
- **LLM-touching cached functions need short retry escape valves.** LLM calls flake; `@st.cache_data` locks in flakes for the TTL window. Convention: every Streamlit app that consumes LLMs needs a sidebar "Clear cache & refresh" button (Plan 3 Task-2 follow-up established this; Plan 3.5 preserved it). For demo, this is the user's single recovery action.
- **Plan-↔-API real-fire smoke required for UI-event APIs.** `inspect.signature` showing a kwarg present is necessary but not sufficient. Before locking a UI-event choice (`on_select`, `plotly_events`, `agraph` return) into a plan, run a manual `streamlit run` and trigger the gesture. Plan 3.5 spec deviation #1 missed this and shipped a UI where clicks didn't fire. Lesson cost: one full plan cycle (Plan 3.6).
- **Capture component return values even when unused.** `streamlit-agraph.agraph(...)` returns the clicked node id; Plan 3.5 ignored the return and node clicks did nothing. Convention: any component that returns a value MUST be assigned to a named variable, even if the variable goes unused for now. Discoverable failure beats silent failure.
- **Imports of Streamlit-frontend components scoped INSIDE `render()`.** `streamlit_plotly_events` and similar packages emit `ScriptRunContext` warnings at import time when no Streamlit runtime is active (e.g. during pytest collection). Lazy-import inside the function that uses them. Module-top imports are fine for `streamlit` itself, `streamlit_agraph` (no warning), and `plotly`.
- **Event-axis labels are a demo-readability surface, not a raw retrieval dump.** Session 10's Task-2 checkpoint proved that "alternating top/bottom" is not enough for a 22-marker axis. Current convention: query with `cfg.display_name` for better relevance, translate non-English headlines before rendering label boxes, use multi-lane placement with collision budgeting, suppress `(no coverage)` / untranslated / unplaceable label boxes entirely, and keep the marker+hover rather than forcing overlap.
- **User-requested UI review gates are hard stops.** When the user says "checkpoint after every task," the executor must stop after commit + full pytest + diff-stat and wait for a literal `continue` before starting the next task. Session 10 followed this for Plan 3.6; Task 3 is still blocked because Task 2 has not yet received that approval.

### Price attribution conventions (Session 10)

- **`agent_price_explainer.explain_move(...)` now distinguishes three honest fallback modes.** `status="fallback"` always comes with `reason_code ∈ {"no_retrieval", "no_nearby_news", "insufficient_evidence"}` plus user-facing `reason_detail`. UI callers should surface that reason; do not collapse back to a single generic "could not explain" message.
- **Attribution query quality matters more than ticker purity.** The current helper `_build_query(...)` combines the date, ticker symbol, ticker display name, `cfg.display_name`, and `cfg.seed_keywords`. The Session-9 ticker-only query shape pulled too much generic market filler and too little event-specific context.
- **The attribution window is now intentionally `±2` days, not `±3`.** This was a user decision in Session 10. If a future session wants to widen or narrow it, that is a product-behavior change and should be called out explicitly.

### Plan execution mode lessons (Session 9)

- **Subagent-driven mode produces N main commits + occasional follow-up commits.** Plan 3.5 had 9 tasks, executed via subagent-driven, produced 16 commits on `main`. Excess came from inter-task code-review-driven follow-ups (the CLAUDE.md "Corrective workflow when a smell is found" pattern). Net behavior matched the plan; the commit count is honest about the iteration cycle. **Do not budget a 1:1 task:commit ratio for subagent-driven execution** — 1.5-1.8:1 is realistic with code-review checkpoints.
- **Plan-spec test-count predictions can drift by ±5 from actuals.** Plan 3.5 forecast 82 passed; actual was 85 (+3 from subagent-led tightening). This is a positive signal (bonus tests added); track in the wrap-up but do not retroactively edit the plan. Convention: plan task expected-pytest counts are forecasts, not contracts. The verification checklist's "all green" is the contract.
- **Inline execution can still require same-task follow-up commits when a user checkpoint fails.** Session 10's Plan 3.6 Task 2 passed unit tests in `bc67b5f` and still had to be reworked in `dcc5850` because the live UI review showed that the labels were unusable. "One commit per task" remains the target, but user-facing visual failures are first-order evidence; fix them honestly instead of pretending the first pass is done.

### Python

- **Type hints always** on public function signatures. `Optional[T]` for nullable returns. Use `date` (not `datetime`) for calendar dates.
- **pydantic v2 syntax**: `model_validator(mode="after")` for cross-field validation (example in `config.py`). Do not mix in v1 syntax.
- **pydantic models are MUTABLE by default** (v2 unless `model_config = ConfigDict(frozen=True)`). `EventConfig` is not frozen → tests can do `cfg = load_event("iran_war"); cfg.rss_feeds = ["..."]` to inject synthetic values instead of constructing a throwaway model. Session 4's `test_rss.py` relies on this after `iran_war.yaml` deprecated its RSS feeds. DO NOT add `frozen=True` to `EventConfig` without checking which tests mutate fields.
- **No comments** unless the *why* is non-obvious. Load-bearing comments in the codebase now explain (a) weekend gaps in market data tests, (b) `config.py` calling `load_dotenv()` at import time, (c) GDELT `query_params` introspection, (d) yfinance `multi_level_index=False` flag, (e) `_WARNED_MISSING` one-shot log cache, (f) `chromadb` posthog-logger suppression, (g) `SharedSystemClient.clear_system_cache()` after `rmtree`, (h) NewsAPI 100-total-cap rationale in the pagination loop. If you add a comment, match that register.
- **`DATA_DIR` env var** isolates the runtime data directory (`data/` by default). Every module that reads/writes files under `data/` **must** resolve via `Path(os.environ.get("DATA_DIR", "data"))` — the `tmp_data_dir` pytest fixture depends on this for isolation. Session-4-added targets under `$DATA_DIR`: `setup.lock` (fcntl lock file) in addition to the existing `articles.json`, `prices/`, `chroma_db/`, `manifest.json`.
- **Session 6 — LLM module imports at top with monkeypatch-contract guard comment.** `agent_supervisor.py:11-16` imports `from agent_ripple import generate_ripple_tree`, `from data_market import get_price_changes`, `from data_news import retrieve` at module scope (not inside functions). Tests rely on these bindings being present on the module, so `monkeypatch.setattr(agent_supervisor, "retrieve", ...)` works. The guard comment explicitly says: "Do NOT refactor to `import data_market` + `data_market.get_price_changes(...)` inside functions — that would break every monkeypatch in test_agent_supervisor.py." If you consolidate imports in any future file that uses the same test pattern, preserve `from X import Y` form, not `import X`.
- **Session 6 — TypedDict with `total=False` for LangGraph state.** `agent_supervisor.AgentState(TypedDict, total=False)` declares all keys Optional so workers can return partial state deltas (e.g. `{"market_data": changes}`) without type-checker pain. LangGraph merges the deltas into full state. Don't "fix" return annotations to `Dict` or introduce `Partial[T]` — the current form is idiomatic LangGraph.

### Filenames / ticker sanitization

CSVs under `data/prices/` are named via `symbol.replace("=", "_").replace("^", "").replace("/", "_")`. So `BZ=F` → `BZ_F.csv`, `^GSPC` → `GSPC.csv`. Any future code that reads these must use the same sanitization (helper is `data_market._csv_path`).

### Error handling

- **Trust internal contracts.** No try/except wrappers around calls to our own modules.
- **Validate at config boundaries.** `EventConfig` raises `ValueError` with specific messages; `load_event()` raises `FileNotFoundError`. Tests assert on the exception type AND message substring.
- **Fail loud on missing data files** only where it matters (e.g., `get_price_on_date()` returns `None` for a missing CSV or missing date — it's a *query*, not a pipeline step).
- **Silent-skip on missing external credentials** where a fetcher is opt-in. Convention: `data_news.newsapi_fetcher.fetch(cfg)` returns `[]` if `NEWSAPI_KEY` is unset. This keeps the `setup.py` orchestrator resilient when the free-tier quota is exhausted or a user is running without a key.
- **Missing-data return contracts** (Session 4 hardening — Plan 2 agents depend on these):
  - `get_price_on_date(symbol, d) -> Optional[float]` — returns `None` for BOTH missing CSV and non-trading day. Distinguishing the two requires reading stdout (`_WARNED_MISSING` logs once per symbol on missing CSV).
  - `get_price_changes(cfg, as_of) -> Dict[str, Dict]` — **always keyed by every `cfg.tickers` symbol.** Each entry is `{"available": bool, "baseline": Optional[float], "latest": Optional[float], "pct_change": Optional[float]}`. Consumers iterate `cfg.tickers`, look up each symbol, branch on `available`. **No KeyError paths, no surprise partial dicts.** This was a breaking change in Session 4 (commit `33f88f5`); the prior shape (partial dict) was removed.
  - `get_price_range(symbol, start, end) -> pd.Series` — returns EMPTY `pd.Series(dtype=float)` for BOTH missing CSV and empty date window. Callers must `.empty` check.
- **Boundary try/except must be PER-ITERATION, not whole-body, when accumulating state.** Session 4 had a regression where `newsapi_fetcher.fetch()`'s whole-body `try/except Exception: return []` discarded page-1's 100 articles when page 2 raised. Fixed (`862d263`) by moving try/except INSIDE the page loop and `break`ing on `NewsAPIException` with `code=='maximumResultsReached'`. Rule of thumb: if you already appended to `results`, don't throw it away because a later iteration fails.
- **Silence external library log spam at the logger level, not via settings flags.** `chromadb==0.5.18`'s `Settings(anonymized_telemetry=False)` does NOT prevent the telemetry `capture()` call from firing — the call fires, fails with a signature mismatch, and logs ERROR via `chromadb.telemetry.product.posthog`. Only reliable fix: `logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)`. Documented in "Library Quirks → chromadb" below.
- **Session 6 — LLM error handling is asymmetric by role and deliberate (updated Session 7 with shape gates).**
  - **`agent_ripple.generate_structure` raises `ValueError("Model did not return valid JSON: ...")`** on parse failure. Rationale: ripple-tree generation is stateless and on demand; a malformed LLM response is worth surfacing loudly so the UI shows an error state rather than a hallucinated structure.
  - **`agent_supervisor.classify_intent` NEVER raises** — on `json.JSONDecodeError`, non-dict JSON, or invalid intent value, it returns `{"intent": "qa", "focus": ""}` (graceful degradation to the safest worker). Rationale: this runs in the graph's request path; any raise here would bubble out of `app.invoke(...)` and crash `run.py` / `app.py`.
  - **`agent_supervisor.run_news_agent` on `json.JSONDecodeError` OR wrong-shape → `timeline = []`.** Wrong-shape = `timeline` is not `list[dict]`. Soft degradation; UI renders empty timeline. `news_results` still populated.
  - **`agent_supervisor.run_qa_agent` on `json.JSONDecodeError` OR wrong-shape → `{"answer": text.strip(), "citations": []}`.** Wrong-shape = `answer` is not a dict with an `"answer"` key. Soft degradation; UI shows the LLM's raw text as the answer with no citations.
  - **DO NOT make all four symmetric** — the different failure modes are by design.
- **Session 7 — LLM-JSON consumer contract: `json.loads` try/except is NOT sufficient — ALWAYS add an `isinstance` shape gate.** Session 7's code review surfaced (and fixed) two real instances of this bug. The LLM returning valid JSON of the wrong shape is a strictly-more-likely failure mode than `JSONDecodeError` for a model instructed to "emit JSON": the model knows how to emit JSON, but may emit a list when you asked for an object (or vice versa) if the prompt is ambiguous. Required pattern:
  ```python
  try:
      parsed = json.loads(strip_fences(text))
  except json.JSONDecodeError:
      return <degraded value>
  if not isinstance(parsed, <expected type>):
      return <degraded value>
  # for list-of-dicts:
  # if not isinstance(parsed, list) or not all(isinstance(e, dict) for e in parsed):
  # for dict with required key:
  # if not isinstance(parsed, dict) or "answer" not in parsed:
  ```
  All four LLM-JSON call sites (`generate_structure`, `classify_intent`, `run_news_agent`, `run_qa_agent`) now follow this. **Do NOT** broaden the except to `(json.JSONDecodeError, AttributeError, TypeError)` as a shortcut — an explicit `isinstance` gate is self-documenting and catches wrong-element-type inside a valid outer container (which `AttributeError` won't catch until the second level of access).
- **Session 7 — CLI-boundary error handling: catch the TWO arg-decode exception types, not the rest.** `run.py` catches `FileNotFoundError` from `load_event()` and `ValueError` from `date.fromisoformat()` — these two are the ONLY exceptions that argparse-happy-path code can raise before control reaches `agent_supervisor.run()`. Pattern for any future CLI entrypoint:
  ```python
  args = p.parse_args(argv)
  try:
      cfg = load_event(args.event)
  except FileNotFoundError as e:
      print(f"error: unknown --event {args.event!r}: {e}", file=sys.stderr)
      return 2
  try:
      as_of = date.fromisoformat(args.as_of) if args.as_of else cfg.end_date
  except ValueError as e:
      print(f"error: --as-of must be YYYY-MM-DD ({e})", file=sys.stderr)
      return 2
  ```
  Exit code `2` (not 1) matches argparse's own convention for bad-input exits. `print(..., file=sys.stderr)` not `print(..., file=sys.stderr, end="\n")` — the default newline is what you want. **Do NOT wrap the whole `main()` in a top-level `try/except Exception`** — deeper failures (API key missing, network, etc.) should fail loud with a traceback so the user sees where.
- **Session 7 — defensive `.get()` on external-contract dicts, even when the contract guarantees keys.** `attach_news` in `agent_ripple.py` uses `.get()` on every field from `retrieve()` hits (`url`, `headline`, `score`, `metadata.date`) — even though `retrieve()` always populates them today. Rationale: (1) parity with the existing `metadata.get("date", "")` pattern already in the code; (2) `retrieve()` is crossing a module boundary and the hit shape could change without `attach_news` noticing; (3) silent-empty-string is better than `KeyError` for a Plan-3 UI rendering a tree. Apply the same rule to any `get_price_changes()` / future `data_news.*` consumers.
- **Session 6 — empty-retrieval short-circuit contract.** `data_news.retrieve()` returns `[]` when the Chroma collection is missing or empty (Plan 1 C3, `vector_store.py:108`). Every LLM-calling consumer MUST check for this and either skip the LLM call or return a deterministic degraded response:
  - `run_news_agent`: `{"news_results": [], "timeline": []}`.
  - `run_qa_agent`: `{"news_results": [], "response": {"answer": "No indexed articles match this question.", "citations": []}}`.
  - `attach_news` (agent_ripple): naturally safe — empty-list iteration attaches `supporting_news=[]` to each node; no explicit check needed.
  - **Rationale:** an LLM prompted with an empty snippet list will hallucinate. The short-circuit is the honest response.

### Tests

- File: `tests/test_<module>.py`, mirroring source filename.
- **Mock external APIs** at the module boundary via `monkeypatch.setattr(module.yf, "download", fake_download)` — never patch the library globally. Pattern also applied in Task 5: `monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())`.
- **One fact per test.** Test names read like the assertion: `test_baseline_before_start`, not `test_config`.
- **Assert on the library's real surface, not a plan's imagined surface.** If the plan's test text asserts `f.keyword`, verify at the REPL that the pinned library version actually exposes `.keyword` before writing that assertion. When it doesn't, rewrite the test to use what's real (see `Filters.query_params` case in Task 5). Do NOT decorate the production object with phantom attrs to make the plan's assertion pass.
- Live integration tests live in `tests/test_*_live.py` and are gated via `pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", ...)`.
- **Time-sensitive tests monkeypatch the `date` reference inside the target module, not globally.** Session 4's NewsAPI clamp test subclasses `datetime.date` with an overridden `today()` classmethod and does `monkeypatch.setattr(newsapi_fetcher, "date", _FixedDate)`. This is the only way to pin `date.today()` without a `freezegun`-style dep. Pattern:
  ```python
  class _FixedDate(date):
      @classmethod
      def today(cls):
          return date(2026, 4, 22)
  monkeypatch.setattr(newsapi_fetcher, "date", _FixedDate)
  ```
  The target module must have imported `from datetime import date` (re-bindable via `setattr`), not `import datetime` (un-rebindable without patching the stdlib).
- **One-shot log caches must be cleared between tests.** `data_market._WARNED_MISSING` (set of symbols we've already warned about) persists across test boundaries in the same process. Tests that depend on log content do `data_market._WARNED_MISSING.clear()` at the start (see `test_missing_csv_logs_once_per_symbol`).
- **`capsys` captures stdout `print()`, not Python `logging` records.** Session 4's C3 test uses `capsys.readouterr().out` to assert on `[vector_store] unexpected error ...` because the error goes through `print()`, not `logging`. If we ever switch `vector_store.py` from `print` to `logger.error`, tests must switch to `caplog` — and callers won't see the messages without a handler.
- **Concurrent-state tests use `subprocess.Popen`, not threads.** `tests/test_setup_cli.py::test_setup_lock_blocks_concurrent_run` spawns a child Python that acquires the fcntl lock and sleeps. Tests reading the lock's "busy" state from the parent process work because fcntl.flock is advisory AND per-process. In-process concurrency (threads) wouldn't exercise the lock — POSIX locks ignore same-process holders' requests. If you ever write a lock-contention test differently, it's probably wrong.
- **Tests requiring real ChromaDB writes must not reset() twice in-process without verifying the cache-clear path.** `reset()` now calls `SharedSystemClient.clear_system_cache()`; without that, the second `index_articles()` hits `sqlite3.OperationalError: attempt to write a readonly database`. See Library Quirks → chromadb.
- **LLM test fakes: use a SHARED `_FakeLLM` instance, not a factory.** A `lambda **kw: _FakeLLM(replies)` builds a FRESH fake on every `get_chat_model()` call, with a FRESH copy of `replies` (via `self._replies = list(replies)` in `_FakeLLM.__init__`). If a test iterates and expects `.pop(0)` to advance, that pattern fails because each iteration sees `replies[0]` again. Correct pattern (discovered Session 6 on Plan 2 Task 8):
  ```python
  class _FakeLLM:
      def __init__(self, replies):
          self._replies = list(replies)
      def invoke(self, messages):
          return AIMessage(content=self._replies.pop(0))

  replies = [json.dumps({...}) for ... in examples]
  fake = _FakeLLM(replies)  # ONE instance
  monkeypatch.setattr(module, "get_chat_model", lambda **kw: fake)
  for example in examples:
      ...  # each call advances through `replies`
  ```
  **If the test only invokes the LLM once per test function**, `lambda **kw: _FakeLLM([reply])` is fine (single-shot). It's specifically the "iterate-and-pop" pattern that requires sharing.
- **`monkeypatch.setattr(agent_supervisor, "retrieve", ...)` requires `retrieve` to be a module-level name in `agent_supervisor`.** Session 6 consolidated the late `from data_news import retrieve` / `from data_market import get_price_changes` / `from agent_ripple import generate_ripple_tree` imports to the top of `agent_supervisor.py`, with a guard comment (`agent_supervisor.py:11-16`). Do NOT "simplify" to `import data_news` + `data_news.retrieve(...)` inside the function — that would break every monkeypatch in `test_agent_supervisor.py` silently, because `monkeypatch.setattr(agent_supervisor, "retrieve", ...)` would set a new module-level attr that the function's `data_news.retrieve(...)` would ignore.
- **LangGraph tests that patch node functions must do so BEFORE calling `build_graph()`.** `add_node(name, callable)` captures the callable at build time. If you patch after, the compiled app still holds the unpatched reference. `test_build_graph_routes_by_intent` and `test_run_end_to_end_helper` both patch-then-build; this is the correct order.
- **Session 7 — CLI entrypoint tests mock the downstream API module, not the network.** `tests/test_run_cli.py::test_cli_happy_path_prints_result_and_returns_zero` does `monkeypatch.setattr(agent_supervisor, "run", lambda cfg, query, as_of: fake_result)` + `capsys.readouterr().out` + `json.loads(out)`. This exercises argparse wiring, exit codes, stdout JSON roundtrip, and the `date` → `.isoformat()` serialization path in `run.py`, WITHOUT ever touching `build_graph()` or the LLM. Pattern for any future CLI entrypoint: mock at the function boundary ONE level below the CLI, not at the HTTP client level.
- **Session 7 — CLI error-path tests assert `rc != 0` AND stderr substring, not exact message text.** `test_cli_unknown_event_exits_nonzero` asserts `"does_not_exist" in err`; `test_cli_malformed_asof_exits_nonzero` asserts `"as-of" in err.lower() or "iso" in err.lower() or "date" in err.lower()`. Rationale: exact message text changes as we iterate error wording; the contract under test is "user gets actionable feedback + nonzero exit," not "the error message is exactly this string." Don't pin exact messages.
- **Session 7 — Wrong-shape LLM-JSON tests use `json.dumps(<wrong_shape_value>)` as the canned reply.** `_FakeLLM([json.dumps(["timeline"])])` — valid JSON, wrong shape (list instead of dict). Four instances in `tests/test_agent_supervisor.py`: `test_classify_intent_returns_qa_when_json_is_list`, `test_classify_intent_returns_qa_when_json_is_scalar`, `test_run_news_agent_falls_back_on_wrong_shape_json`, `test_run_qa_agent_falls_back_on_wrong_shape_json`. **Distinct from the pre-existing `test_*_malformed_json_falls_back_*` tests** (which feed `"not json at all"`, triggering `JSONDecodeError`). Both classes of test are required — one covers the parse failure, one covers the shape mismatch. They are NOT redundant.

### yfinance specifics

- **Pinned at `0.2.66`.** `0.2.51` (original pin) was broken upstream: Yahoo's backend returned non-JSON for every ticker, surfacing as `YFTzMissingError('$%ticker%: possibly delisted; no timezone found')`. Discovered by the Task 12 live smoke; bumped to `0.2.66` in the same work.
- **Always pass `multi_level_index=False` to `yf.download`.** Starting in the 0.2.x line, single-ticker calls default to MultiIndex columns (`[('Close', 'SPY'), ('Open', 'SPY'), ...]`) instead of flat (`['Close', 'Open', ...]`). Without the flag, `df.to_csv()` writes a garbage "ticker-name subheader" row under the real header, and downstream `pd.read_csv(..., parse_dates=["Date"])` reads the junk row as data and tries to parse `"SPY"` as a Date. `data_market.download_prices()` passes it; any new yfinance call site must too. The live smoke in `tests/test_smoke_live.py` mirrors this.
- `start` is inclusive, `end` is exclusive — always pass `end_date + timedelta(days=1)` when we want end-date data.
- Fetch window: `baseline_date - 7 days` through `end_date + 1` (pre-event buffer for chart context).

### Running commands

- Use `/opt/anaconda3/envs/macro-ripple/bin/python` and `.../bin/pytest` directly. Shell state does not persist between Bash tool calls, so `conda activate` does not carry.

## Library Quirks & Gotchas

Third-party library behaviors a future session MUST NOT re-discover the hard way. These are pinned to the exact versions in `requirements.txt`; if you bump a version, re-verify.

### `gdeltdoc==1.6.0` — `Filters` is a builder, not a dataclass

`from gdeltdoc import Filters`. The constructor:

```
Filters.__init__(self, start_date=None, end_date=None, timespan=None,
                 num_records=250, keyword=None, domain=None, domain_exact=None,
                 near=None, repeat=None, country=None, theme=None)
```

Things to know:

- **No `language` kwarg.** Passing `language="english"` raises `TypeError`. (The plan text for Task 5 included this; it was dropped in the implementation. If English-only is needed, post-filter the returned DataFrame on the `language` column, or use `near=` with a carefully chosen phrase.)
- **Kwargs are consumed, not retained.** After construction, `Filters` only exposes `query_params: list[str]`, `_valid_countries`, `_valid_themes`. There is no `.keyword`, `.start_date`, `.end_date` attribute. Do not write `filters.keyword` and do not write code or tests that expect it.
- **`query_params` is a list of URL fragments** like `['(Iran OR Hormuz OR oil) ', '&startdatetime=20260228000000', '&enddatetime=20260416000000', '&maxrecords=250']`. Test introspection pattern: `" ".join(f.query_params)` then substring-match (`"Hormuz" in qp`, `"startdatetime=20260228" in qp`).
- **Dates serialize to `YYYYMMDDHHMMSS` (no dashes)** in `query_params`. The kwarg accepts ISO `YYYY-MM-DD` strings, but the fragment is compact.
- **Empty result handling:** `GdeltDoc().article_search(filters)` returns an empty `pd.DataFrame` (not `None`) when zero matches. Our `gdelt.fetch()` returns `[]` via the `df.empty` check.
- **Seendate format in results:** `seendate` column values look like `20260228T120000Z`. Parse with slicing: `f"{seen[0:4]}-{seen[4:6]}-{seen[6:8]}"`.
- **250-records-per-query hard cap.** GDELT's DOC API maxes `num_records` at 250 regardless of what you pass. The single call `article_search(Filters(start=2026-02-28, end=2026-04-16, keyword=[...]))` returned exactly 250 articles for a 47-day window. Our `data_news/gdelt.py` paginates by splitting the window into 7-day chunks and querying each with `num_records=250` (`while chunk_start < cfg.end_date: chunk_end = min(chunk_start + 7d, cfg.end_date)`). Chunks do not overlap and do not miss days because GDELT treats `enddatetime` as exclusive (midnight of that day). On a 47-day window this produces 7 chunks and ~1,500 articles (vs. the 250 ceiling of a single call).
- **1-element `keyword=["oil"]` rejected.** Single-word queries trigger GDELT's "The specified phrase is too short" error because the serialized query becomes `(oil)` with a single OR'd term. Pass ≥2 terms (`keyword=["oil", "crude"]`) or a multi-word phrase (`keyword="oil crude"`). Our live smoke test in `tests/test_smoke_live.py` uses 2 keywords for this reason.
- **Rate-limit + transient connection resets are routine on a multi-chunk run.** `data_news/gdelt.py` sleeps 2s between chunks (`time.sleep(_SLEEP_BETWEEN_CHUNKS)`) and wraps EACH chunk's `article_search` in `try/except Exception: print + continue` so one `ConnectionResetError` or GDELT 5xx doesn't kill the whole run. The last real run (commit `fc3704c`) saw one chunk fail with `ConnectionResetError(54, 'Connection reset by peer')` and the other 6 chunks completed — pipeline recovered cleanly. **Do NOT narrow the except to a specific exception class** without carefully checking what GDELT/`requests` can raise; the broad-except is load-bearing here.
- **`tests/test_gdelt.py` monkeypatches `gdelt.time.sleep` to a no-op.** Without this, pagination tests would add `num_chunks × 2s = 14s` of sleep to the suite. The test that validates pagination also only returns the fixture from the FIRST chunk (FakeGdeltDoc uses a call counter); otherwise every chunk would multiply the expected article count.

### `newsapi-python==0.2.7`

- `NewsApiClient(api_key=str)`. `.get_everything(...)` returns a **plain dict** `{"status", "totalResults", "articles"}`. Safe to introspect — no opaque wrapper objects.
- Full signature (verified via `inspect.signature` on the pinned version): `get_everything(self, q=None, qintitle=None, sources=None, domains=None, exclude_domains=None, from_param=None, to=None, language=None, sort_by=None, page=None, page_size=None)`. The date kwarg is `from_param=` (not `from=` — `from` is a Python keyword); easy to get wrong.
- **Free-tier "100 requests/day" is actually a 100-TOTAL-results-per-query hard cap, not 100 per page.** The docs' "100 requests/day" language is ambiguous. In practice: page_size=100 + page=1 returns up to 100 articles, but requesting page=2 returns HTTP 426 `{"status": "error", "code": "maximumResultsReached", "message": "Developer accounts are limited to a max of 100 results. You are trying to request results 100 to 200. Please upgrade..."}`. **Pagination past page 1 is a mirage on free tier.** Session 4 discovered this on a live run after adding `max_pages=5` — the old `max_pages=1` default never hit page 2. Our fetcher now calls the client INSIDE a `try/except NewsAPIException` per page, checks `e.get_code() == "maximumResultsReached"`, and `break`s — preserving page-1's results. `setup.py` passes `max_pages=5` for the hypothetical day we upgrade; on free tier it will always short-circuit at page 2 as designed.
- **`totalResults` is not a useful count.** Live runs report values like `totalResults=464343` — this appears to be either an unfiltered-by-language upper bound or a rough estimate, not the number of articles actually fetchable. Log it for operator awareness but don't drive decisions off it.
- **Free-tier 30-day window.** Free tier only serves the last ~30 days of history. Requesting `from_param=<date older than 30 days ago>` returns an HTTP 426 "parameterInvalid" error. `data_news/newsapi_fetcher.py` clamps `effective_start = max(cfg.start_date, today - 29d)` and `effective_end = min(cfg.end_date, today)`, and short-circuits to `[]` with a skip-message if the entire event window predates the 30-day window. If you bump the `_FREE_TIER_LOOKBACK_DAYS = 29` constant, verify first that the NewsAPI plan has actually changed. Clamp behavior is pinned by `tests/test_newsapi.py::test_fetch_newsapi_clamps_start_to_30_day_window` (added Session 4).
- **Per-page try/except pattern for NewsAPI.** After Session 4's regression (commit `862d263`), the pattern is:
  ```python
  for page in range(1, max_pages + 1):
      try:
          resp = client.get_everything(..., page=page)
      except NewsAPIException as e:
          code = e.get_code() if hasattr(e, "get_code") else ""
          if code == "maximumResultsReached":
              break  # free-tier 100 cap; prior results SURVIVE
          print(f"[newsapi] page {page} failed: {e}; keeping prior")
          break
      ...append articles to results...
  ```
  **Do NOT collapse this back into whole-body try/except** — a page-N failure would discard pages 1..N-1.
- If `NEWSAPI_KEY` unset, `fetch(cfg)` returns `[]` without calling the client (no raise). Unit tests `monkeypatch.delenv("NEWSAPI_KEY", raising=False)` to exercise this path; the "normalized" test `monkeypatch.setenv("NEWSAPI_KEY", "dummy-key")` so the code path runs under a fake client.
- To monkeypatch `date.today()` in tests (e.g., to pin the 30-day window), subclass `datetime.date` with a `@classmethod today()` override and do `monkeypatch.setattr(newsapi_fetcher, "date", _FixedDate)`. Module must have `from datetime import date` (rebindable reference) — ours does.

### `pydantic==2.9.2`

- `model_validator(mode="after")` is the v2 idiom; `@root_validator` is v1 and will break. Cross-field validation goes in a post-init method, not in individual field validators.
- `@field_validator` is also v2 but not currently used; prefer `model_validator` when you need multiple fields' final values.

### `chromadb==0.5.18`

- Use `chromadb.PersistentClient(path=str(dir), settings=Settings(anonymized_telemetry=False))`. Do NOT use the deprecated `chromadb.Client(Settings(persist_directory=...))`.
- First-run embedding model download (~80 MB for `all-MiniLM-L6-v2`) happens silently; expect a delay on the first `index_articles()` call of a fresh clone. Subsequent runs use the cache in `~/.cache/huggingface/`.
- `collection.query()` returns a dict with `{documents, metadatas, distances}` each wrapped in a one-element outer list (because the API accepts batch queries). Unpack with `res["documents"][0]`, etc.
- `distance` is cosine distance in `[0, 2]` by default; convert to similarity via `1.0 - distance`. In practice for English news text, typical similarity scores land in `[0.1, 0.5]` on broad corpora, but curated event corpora push higher — Session 4's 1,387-article corpus scored 0.533 top-hit on "Hormuz closure oil price" (Session 3 was 0.39 at 1,217 articles).
- **`get_collection` raises `chromadb.errors.InvalidCollectionException`** when the collection doesn't exist. Our `vector_store._collection(create=False)` catches it narrowly (line-for-line as of Session 4 commit `ecd92fc`):
  ```python
  try:
      return c.get_collection(_COLLECTION, embedding_function=_embedder())
  except InvalidCollectionException:
      return None
  except Exception as e:
      print(f"[vector_store] unexpected error opening collection '{_COLLECTION}': {e!r}")
      return None
  ```
  The narrow catch is deliberate: a fresh DB legitimately raises `InvalidCollectionException` → silent None is correct. Any OTHER exception (embedder misconfig, corrupt persist dir, permission error) would silently degrade to "empty retrieval" and Plan 2's LLM would hallucinate rather than error — so we print. Regression test: `tests/test_vector_store.py::test_retrieve_surfaces_unexpected_errors_instead_of_silent_empty`. **Do NOT reintroduce a blanket `except Exception: return None`** — this was the pre-Session-4 bug.
- **Telemetry is actively broken in 0.5.18 — silence it at the logger level, not via Settings.** Every `PersistentClient`, `get_or_create_collection`, `collection.add`, `collection.query` call invokes `posthog.capture(*args)` with a mismatched signature, triggering `ERROR chromadb.telemetry.product.posthog: capture() takes 1 positional argument but 3 were given`. `Settings(anonymized_telemetry=False)` does NOT prevent the call from firing (verified empirically Session 4); the documentation claim that it disables "anonymous data collection" is true but the buggy capture call fires anyway. The only reliable suppression is:
  ```python
  # At vector_store.py module-load time, before any client op
  logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
  ```
  We do this and also pass `Settings(anonymized_telemetry=False)` (belt + suspenders — the Settings line may start working if chromadb ever fixes the posthog bug). Spam comes through Python's `logging` → stderr, not `print` → stdout; pytest catches it in "Captured log call" sections, which is how Session 4 caught the initial failed suppression. Prior CLAUDE.md guidance said "do NOT suppress"; **that was wrong** (the noise drowns out our own C3-added error prints). The current suppression is narrow (one logger, one level) and does not risk hiding unrelated errors.
- **`reset()` must clear `SharedSystemClient` cache, not just rmtree the dir.** chromadb keeps a per-path singleton of `SharedSystemClient` caching its SQLite handles. After `shutil.rmtree($DATA_DIR/chroma_db)`, the next `PersistentClient(path=same_dir)` hands back the old cached client with a handle pointing at the deleted inode — next write raises `sqlite3.OperationalError: attempt to write a readonly database`. Our `reset()` now:
  ```python
  def reset() -> None:
      p = _db_dir()
      if p.exists():
          shutil.rmtree(p)
      chromadb.api.client.SharedSystemClient.clear_system_cache()
  ```
  This is required for any caller that invokes `reset()` more than once in a single process — notably the I5 stable-ID test (`reset → index → read → reset → index → read`) and any future `setup.py`-within-a-process orchestrator. Session 4 commit `90f02db`.
- **ID format in `index_articles`:** `f"{source_kind}-{i}-{sha1(url)[:16]}"`. `sha1(url)[:16]` is deterministic across processes. Previously used `abs(hash(url))` which is salted per-process by `PYTHONHASHSEED`. Switched in Session 4 commit `15edf56` to unblock any future incremental-reindex path. Regression test: `tests/test_vector_store.py::test_index_ids_are_stable_across_runs` — if a future refactor swaps back to `hash()`, this fails because the trailing segment wouldn't be exactly 16 hex chars.
- **Single-process LSH with fcntl lock.** `data_news.vector_store` still assumes one writer, but since Session 4 commit `e5a84ad` the orchestrator (`setup.py`) takes an exclusive `fcntl.flock` on `$DATA_DIR/setup.lock` for the full pipeline run. Two concurrent `setup.py` invocations fail fast. Plan 3's UI should call `setup.is_setup_in_progress()` before firing `retrieve()` to avoid racing a rebuild. Test: `tests/test_setup_cli.py::test_setup_lock_blocks_concurrent_run` — uses `subprocess.Popen` to hold the lock since fcntl is advisory and per-process (threads inside one process don't exercise it).

### `datasketch==1.6.5` — MinHash LSH

- **Default threshold 0.95** (Session 4 bump from 0.9). With 5-token word shingles and `num_perm=128`, 0.9 was dropping ~20% of the live corpus because GDELT ships with empty `snippet`, meaning MinHash runs on headline-only text and boilerplate-similar-but-factually-distinct stories ("Iran closes Strait of Hormuz amid escalating tensions" vs "Iran closes Strait of Hormuz as conflict grows") collapsed together. 0.95 is stricter and keeps more. Session 3 (0.9): 1,600 → 1,217 unique. Session 4 (0.95): 1,850 → 1,387 unique.
- **`deduplicate()` returns `(kept, stats)`**, not a bare list (changed Session 4, commit `36a4d3d`). Stats dict: `{"input": int, "url_dropped": int, "minhash_dropped": int, "kept": int}`. Callers MUST unpack the tuple. `setup.py` surfaces this into `manifest.json` as the `dedup` key for observability.
- Articles with empty `{headline + snippet}` text bypass LSH and are always kept (`if not text: kept.append(a); continue` at `dedup.py:45`). This is probably wrong for truly empty / corrupted articles, but rare in practice — a future cleanup would filter them earlier.

### `feedparser==6.0.11` + RSS generally

- **Reuters RSS (feeds.reuters.com) is DEAD** — shut down June 2020. AP's `topnews` feed returns stale/redirect content. `events/iran_war.yaml: rss_feeds: []` as of Session 4 (commit `5fb2c8c`). GDELT already indexes Reuters/AP publications via URL, so the RSS branch was zero-yield. If RSS is ever re-added, Google News RSS (`news.google.com/rss/search?q=...`) is the likely path — keyword-queried per-event, more maintenance but usable.
- **`entry.summary` is raw HTML, always.** Even well-behaved feeds return `<p>…<a href=…>…</a></p>` and `&amp;` / `&nbsp;` entities. Our `_strip_html` in `data_news/rss.py` removes `<script>`, `<style>`, `<!-- -->` blocks INCLUDING their content (case-insensitive, multiline) BEFORE generic tag-strip, then `html.unescape`. Order matters: if you tag-strip first, `<script>alert(1)</script>` becomes `alert(1)` in the snippet — both noise for MiniLM and prompt-injection for Plan 2. Tests: `test_strip_html_removes_script_style_and_comments`, `test_strip_html_case_insensitive_and_spanning_newlines`. **DO NOT "simplify" to a single `<[^>]+>` regex** — that's the pre-Session-4 bug.
- The module still exists (`data_news/rss.py`) as a skeleton for future RSS re-introduction. `setup.py` still calls it (returns `[]` when `cfg.rss_feeds` is empty). Tests inject `cfg.rss_feeds = ["..."]` to exercise the fetch path.

### `langchain==0.3.7` / `langchain-core==0.3.17` / `langchain-anthropic==0.3.0` / `langgraph==0.3.0` (Session 6)

- **The `langchain-core` pin you want is `0.3.17`, NOT `0.3.15`.** `langchain-anthropic==0.3.0` has a minimum floor of `langchain-core>=0.3.17`; the plan's `0.3.15` pin caused `pip install -r requirements.txt` to return `ResolutionImpossible`. Session 6 bumped by one patch; see plan file "Execution Notes (Session 6)" footer and `requirements.txt`. If a future upgrade bumps `langchain-anthropic`, re-check the `langchain-core` floor.
- **`ChatAnthropic.invoke([SystemMessage, HumanMessage, ...])` returns an `AIMessage`** whose `.content` is EITHER `str` (plain text replies) OR `List[Dict]` (tool-calling / vision). Our three LLM call sites (`agent_ripple.generate_structure`, `agent_supervisor.classify_intent`, `agent_supervisor.run_news_agent`, `agent_supervisor.run_qa_agent`) all do `resp.content if isinstance(resp.content, str) else str(resp.content)`. This is correct for current pure-text usage. If Plan 3 ever adds tool-calling, `str(list_of_blocks)` produces `"[{'type': 'text', 'text': '...'}]"` which `json.loads` will reject — switch those call sites to extract the text block explicitly. Not a bug today; flag for Plan 3.
- **Prompt-file placeholders use `.replace("{var}", value)`, not `.format()`.** `prompts/ripple_system.txt` has `{max_depth}` which is filled by `load_prompt("ripple_system").replace("{max_depth}", str(max_depth))` in `agent_ripple.generate_structure`. Rationale: `.format()` breaks on any other `{...}` literal in the prompt (there are many, since the prompt documents a JSON schema full of `{`/`}`). If you add more placeholders, either switch to `str.format(**kwargs)` AND escape every schema `{` as `{{`, or keep chaining `.replace()`. Stick with `.replace()`; it's a three-line footgun to switch.
- **`strip_fences` lives in `llm.py`, not each agent module.** Session 6's post-Task-8 refactor hoisted it from `agent_ripple.py` + `agent_supervisor.py` into `llm.py`. All four LLM call sites (`generate_structure`, `classify_intent`, `run_news_agent`, `run_qa_agent`) import `from llm import ..., strip_fences`. The plan file's older Tasks 11/12 snippets used `.strip().strip("\`").removeprefix("json").strip()` — that pattern was retired; use `strip_fences`. If Plan 3 adds another LLM-JSON caller, reuse `strip_fences` — do NOT reinvent.
- **`strip_fences` regex:** `re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)`. Handles the canonical `\n\`\`\`json\n...\n\`\`\`\n` form. Empirically brittle on pathological inputs like `\`\`\`json{"x":1}\`\`\`` (all one line, no newline before closing fence) — the `$` anchor with MULTILINE matches line end, so this case works, but `{"x":1}\`\`\`\n` (closing fence only, no opening) with no trailing whitespace at string end might leave the fence unmatched. Claude Sonnet 4.6 reliably emits the canonical form; not a worry today. If you ever see JSON parse errors in prod on LLM output that looked fenced, the regex is the first place to check.

### `langgraph==0.3.0` — StateGraph specifics (Session 6)

- **`graph.add_node(name, callable)` captures the callable reference AT `add_node` TIME, not at graph invocation time.** `agent_supervisor.build_graph()` does `graph.add_node("classify_intent", classify_intent)` — the `classify_intent` reference is resolved and bound then and there. `tests/test_agent_supervisor.py::test_build_graph_routes_by_intent` works because `monkeypatch.setattr(agent_supervisor, "classify_intent", ...)` runs BEFORE `build_graph()`, so `add_node` captures the patched reference. **Consequence:** never cache a compiled app as a module-level singleton (`_APP = build_graph()` at import time) — doing so would freeze stale callable references and silently break every monkeypatch-based test. Documented in-line at `build_graph`; also in `agent_supervisor.py` top-of-file import guard comment.
- **Node functions return PARTIAL `AgentState` dicts, and LangGraph merges them into the full state.** `AgentState` is declared `TypedDict(total=False)`, so `return {"market_data": changes}` IS a valid `AgentState` — mypy/pyright won't complain. Every worker node (`run_market_agent`, `run_ripple_agent`, `run_news_agent`, `run_qa_agent`) and `classify_intent` annotate `-> AgentState` but return partials. This is idiomatic LangGraph; don't "fix" the return type to `Dict` or `Partial[AgentState]`.
- **Conditional routing: `add_conditional_edges(from_node, route_fn, {intent_str: to_node})`.** Our `_route(state)` returns `state.get("intent", "qa")` — the default-to-qa is a genuine safety net: `classify_intent`'s fallback path ALSO returns `intent="qa"`, so the default only fires if a future node mutates state without setting intent. Keep the `.get(..., "qa")` form.
- **`app.invoke(initial_state)` returns the final merged state**; unvisited branches' keys are absent (`"ripple_tree" not in final` when intent was market). Test `test_build_graph_routes_by_intent` asserts both presence and exclusion — if a future refactor changes LangGraph merge semantics (e.g. always-runs-all-nodes), this test fails loudly.
- **Classes of things LangGraph WILL NOT do for us:**
  - retry failed node invocations (Plan 2 currently doesn't need; evaluate for Plan 3 eval runner).
  - stream node outputs (use `app.stream(...)` not `app.invoke(...)` if Plan 3 UI wants progressive updates).
  - cache results across invocations (every `run()` call rebuilds the graph via `build_graph()`; cheap but not free — ~10ms per invocation).

### `streamlit==1.39.0` (Session 9, Plan 3 / 3.5 / 3.6)

- **`@st.cache_data` cannot hash pydantic v2 `EventConfig` (or any non-frozen pydantic model).** Pydantic v2 sets `__hash__ = None` on non-frozen models, which makes them unhashable. `@st.cache_data` raises `streamlit.runtime.caching.cache_errors.UnhashableParamError` with a message pointing at "add a leading underscore to the argument's name." **Convention:** any cached function that takes an `EventConfig` MUST name the parameter `_cfg` (leading underscore). This tells Streamlit "skip hashing this arg." Cache key then keys only on the OTHER args (e.g. `as_of`). Cache discrimination across events is naturally upstream because `_load_cfg(event_name)` in `ui_app.py` is itself `@st.cache_data`-wrapped and returns the same `EventConfig` instance per event. Applies to: `ui/timeline.py:fetch_timeline` (now deleted), `ui/ripple.py:fetch_tree`, `ui/price_chart.py:_load_prices`, `ui/event_axis.py:_headline_for`, `ui/price_detail_panel.py:_cached_explain`. Discovered Session 9 Plan-3 Task 2 first try; if you add `EventConfig` to a future cached function, repeat the underscore.
- **`@st.cache_data` caches empty results — LLM flakes get locked in for the TTL window.** Symptom (Session 9 timeline-bug): the FIRST call hit the LLM during a flake, returned `[]`, and that empty got cached for `ttl=3600`. Every subsequent browser refresh hit the cache and never re-tried the LLM. The user saw "No timeline items generated" for an hour despite valid backend state. **Three mitigations now applied across the codebase:**
  - **English-only instruction in every prompt** that emits structured JSON. The original symptom was the LLM mirroring Arabic-language source articles → Arabic output → Arabic tokenizes ~3× denser than English → JSON truncated mid-string at `max_tokens=2048` → `JSONDecodeError: Unterminated string` → Session-7 shape-gate falls back to `[]`.
  - **`max_tokens` ≥ 4096 in `run_news_agent`** (was 2048 — too tight for non-English fallthrough).
  - **"Clear cache & refresh" sidebar button** in `ui_app.py` calling `st.cache_data.clear() + st.session_state.pop(...) + st.rerun()`. This is the demo-day escape valve when a flake locks the cache.
- **Streamlit's in-process `MemoryCacheStorageManager` survives browser refresh.** Without a Streamlit runtime, `@st.cache_data` falls through to `MemoryCacheStorageManager` (visible warning: `No runtime found, using MemoryCacheStorageManager`). This is per-process and survives ALL browser actions short of restarting the `streamlit run` process. To clear: explicit `st.cache_data.clear()` call (the new sidebar button), or kill+restart the Streamlit process. **Browser refresh DOES NOT flush the cache** — a common debugging false trail.
- **`st.plotly_chart(on_select="rerun", selection_mode="points")` ONLY fires on box-select / lasso-select, NOT on a plain marker click.** Plan 3.5 dropped `streamlit-plotly-events` based on `inspect.signature(st.plotly_chart)` showing `on_select` and `selection_mode` params present in 1.39 — a real but **insufficient** signal. The API exists. The params accept the values. The gesture **does not fire** unless the user activates the modebar's box-select or lasso-select tool. The default Pan tool produces no event. Plan 3.5 Phase-3 shipped a UI where clicking markers showed the hover but never set `selected_date`; Plan 3.6 Task 1 fixes by re-adding `streamlit-plotly-events==0.0.6`. **General lesson — applies to any future UI-event API choice: presence of an API in `inspect.signature` is not a sufficient design check. Manually trigger the target gesture in a `streamlit run`-ed app before locking the API choice into a plan.**
- **`st.session_state` keys need explicit lifecycle discipline.** Streamlit does NOT clear `st.session_state` on event switch, browser refresh, or any user action short of process restart. Convention established Session 9 Plan-3.5/3.6:
  - Every `selected_*` key must be `pop()`'d when the user switches events (`if st.session_state.get("_last_event") != event_name`)
  - Every `selected_*` key must be `pop()`'d in the "Clear cache & refresh" button alongside `st.cache_data.clear()`
  - Current landed keys: `selected_date` (price_chart writes; price_detail_panel reads), `chat_history` (sidebar_chat owns). Planned-but-not-landed key: `selected_sector` (Task 3). Each new key requires updates in BOTH the event-switch reset block AND the cache-clear block in `ui_app.py:main()`.
- **`streamlit-plotly-events` import scoped INSIDE `render()` not at module top.** Importing `streamlit_plotly_events` at module load time emits `Streamlit ScriptRunContext` warnings during pytest collection. Keeping the import inside `render()` (where it only fires under live Streamlit) keeps `pytest -v` quiet. Convention: any third-party Streamlit-frontend component that emits load-time logs should be lazy-imported inside the function that calls it.

### `streamlit-agraph==0.0.45` (Session 9, Plan 3 / 3.5 / 3.6)

- **`agraph(nodes, edges, config)` RETURNS the clicked node's id as a string (or `None`).** Verified by reading `streamlit_agraph/__init__.py:38-39`: `component_value = _agraph(...)`. The returned value IS the click signal — Plan 3.5 Task 8 wrote `agraph(...)` ignoring the return, which is why ripple node clicks did nothing. Plan 3.6 Task 3 captures it: `clicked_id = agraph(nodes=nodes, edges=edges, config=cfg_graph)`. **Convention going forward:** any new Streamlit component that returns a value should at minimum capture it into a named variable, even when not yet using it — discoverable failure beats silent failure.
- **Node id ↔ data mapping is the caller's responsibility.** `tree_to_graph_elements` auto-generates ids `"n1", "n2", ...` because Node ids must be unique strings and the original tree dicts may have non-unique sector names. To resolve a clicked id back to the original tree node, the caller (Plan 3.6 Task 3) extends `tree_to_graph_elements` to also return an `id_map: dict[str, dict]`. The `"root"` id is intentionally excluded from `id_map` so root-clicks don't trigger sector-mode (the root is just the event title).
- **`Node`'s `title` parameter is the hover-tooltip text** in streamlit-agraph (NOT the node label). The visible text on the node is `label`; `title` only shows on hover. Plan 3.5 Task 7 ripple polish moved the price-change pct from `label` to `title` for visual cleanup.
- **`Edge(source=..., target=...)` accepts `target` as a kwarg but stores it as `to` internally.** Tests should not assert on `edge.target`; use `edge.to` if you need to introspect (or just count edges by `len(edges)` which is what our tests do).

### `plotly==5.24.1` (Sessions 9–10 lessons)

- **`mode="markers+text"` does NOT auto-arrange labels.** Plotly is plotting-grade, not Tufte-grade — there is no built-in collision avoidance for text labels. With ≥5 labels in a horizontal axis, `textposition="top center"` produces a stacked unreadable blob. Session 10 proved that even a simple 2-lane top/bottom alternation is insufficient for a dense 22-marker window. **Current convention:** use annotations + stems + multi-lane placement + label suppression when needed; never allow bordered label boxes to overlap just to show more text.
- **Shapes do NOT reliably pin autorange.** Once the old baseline scatter trace was replaced with a `fig.add_shape(type="line", ...)` baseline, the event axis could collapse to the marker span unless `xaxis.range=[pd.Timestamp(window_start), pd.Timestamp(window_end)]` was set explicitly. If a future figure uses only shapes to imply extent, pin the axis range yourself.
- **`fig.add_vline(x=...)` accepts ISO date strings, but `fig.add_shape(type="line", x0=..., x1=...)` needs `pd.Timestamp(...)`.** Mixing the two APIs across the same figure is fine but watch the type contract per call.
- **Plotly hover templates use `<br>` for line breaks (HTML), not `\n`.** `hoverinfo="text"` + `hovertext=[...]` accepts HTML in each text item.

### `streamlit-plotly-events==0.0.6` (Plan 3.6 Task 1, Session 10)

- **Re-added and landed in `52a269a` after Plan 3.5 wrongly dropped it.** Reverses Plan 3.5's spec deviation #1. The package is a legacy Streamlit-component wrapper (last updated 2022) but pip-resolves cleanly with `streamlit==1.39.0`.
- **`plotly_events(fig, click_event=True, select_event=False, hover_event=False)` returns a list of `{x, y, curveNumber, pointIndex, pointNumber}` dicts on click.** No `customdata` propagation — to recover the date from a marker click, look up `moves[pointIndex]["date"]` in the original moves list. Helper: `_click_event_to_iso(events, moves)` in `ui/price_chart.py`.
- **Curve number convention in the current Viz-1 figure:** `curveNumber=0` is the line trace, `curveNumber=1` is the markers trace. The constant `_MARKERS_CURVE_INDEX = 1` in `ui/price_chart.py` documents this. If you ever add a third trace BEFORE the markers, update the index or the click helper will silently mis-map dates.

### `python-dotenv==1.0.1` — Claude-Desktop-shadows-env-var quirk (Session 6)

- **Claude Desktop exports `ANTHROPIC_API_KEY=` (empty string) into child processes.** `load_dotenv()` without `override=True` treats an empty string as "already set" and does NOT replace it from `.env`. Symptom: `os.environ.get("ANTHROPIC_API_KEY")` returns `""` (falsy) even though `.env` has a real key populated. Session 6 discovered this on Task 1 Step 4. Fix is module-specific:
  - **`llm.py` calls `load_dotenv(override=True)`** (live LLM entrypoint, needs the real key).
  - **`config.py` calls `load_dotenv()` WITHOUT override** (tests `monkeypatch.setenv(...)` before importing config — `override=True` there would fight the monkeypatch).
- **If Plan 3 adds a third live entrypoint** (e.g. `app.py` Streamlit runner), decide per-file: override if it's a user-facing live path that needs the key at import, no override if tests inject the key before import.
- **Symptom identification heuristic:** if `/opt/anaconda3/envs/macro-ripple/bin/python -c "import config, os; print(os.environ.get('ANTHROPIC_API_KEY'))"` prints empty string, AND `awk -F= '/ANTHROPIC_API_KEY/ {print substr($2,1,15)}' .env` prints `sk-ant-api03-...`, AND `env | grep ANTHROPIC_API_KEY` shows `ANTHROPIC_API_KEY=` (empty), you are hitting this quirk. Running via Claude Desktop is the cause; running from a fresh shell (no Claude Desktop parent) works fine.
- **Do NOT "fix" by removing the empty ANTHROPIC_API_KEY from the shell export** — it's part of Claude Desktop's launch environment and can't be changed per-project. Use the per-file `override=True` strategy instead.

## Secrets & Environment

- **`.env` lives at the repo root**, is gitignored (line 7 of `.gitignore`), and holds `NEWSAPI_KEY` and `ANTHROPIC_API_KEY` (both present as of Session 2). Populated file format:
  ```
  NEWSAPI_KEY=<real value, no quotes, no spaces>
  ANTHROPIC_API_KEY=sk-ant-api03-...
  ```
- **`.env.example`** is the committed template — same key names, empty values, with comments pointing to the signup URLs. Keep it in sync whenever we introduce a new env var.
- **Loading is automatic.** `config.py` calls `load_dotenv()` at import time (after the stdlib imports, before any pydantic class definitions). Because virtually every other module eventually imports `config`, just importing `config` somewhere in the process tree is enough to seed `os.environ` with the `.env` values. Tests that need to flip a key pattern-match on this: `monkeypatch.setenv(...)` / `monkeypatch.delenv(..., raising=False)` — never edit `.env` from a test.
- **Do not add fallback constants for missing keys.** If a fetcher needs `NEWSAPI_KEY`, do `os.environ.get("NEWSAPI_KEY")` and short-circuit on `None`. No `API_KEY = os.environ.get(..., "DEFAULT")`.
- **`.env` must never be staged.** Stage explicitly by file (`git add <files>`) — not `git add -A`, not `git add .`. If you ever see `.env` in `git status --short`, stop and confirm before committing.
- **When a subagent needs a key:** the `.env` is already loaded by the time the subagent's first `import config` runs. The subagent does not need to do anything special. However, the subagent's tests MUST monkeypatch the env var rather than rely on the real value, so that CI (if we ever have it) and fresh clones work.
- **Claude Desktop can shadow `.env` with an empty export.** Running under Claude Desktop (macOS app), the parent shell exports `ANTHROPIC_API_KEY=` (empty string) into child processes. `load_dotenv()` without `override` treats that empty value as "already set" and refuses to replace it — so the real key in `.env` never reaches `os.environ`. Only live-run entry points are affected; unit tests use `monkeypatch.setenv` so they bypass `.env` entirely. Asymmetric handling across modules (Session 6, Plan 2):
  - **`llm.py` uses `load_dotenv(override=True)`** — it is the live LLM entrypoint and needs the real key; override is safe because tests flip the env var AFTER import.
  - **`config.py` uses `load_dotenv()` without override** — some test fixtures monkeypatch env vars before importing config, and `override=True` there would fight that.
  - **If a future module adds a third live entry point** (e.g. Plan 3 Streamlit `app.py`), pick per-file: override if it's a user-facing live path, no override if tests inject the key before import.

## Subagent Review Checklist

Green tests from a subagent are *necessary but not sufficient*. Before accepting a subagent's commit, review the diff against all six Acceptance Criteria AND scan for these smells:

1. **Test-shaped production code.** Look for dead lines whose only purpose is to satisfy a test assertion's introspection. Example from Task 5:
   ```python
   filters = Filters(keyword=..., start_date=..., end_date=...)
   filters.keyword = cfg.seed_keywords     # <-- dead; Filters doesn't use this
   filters.start_date = start              # <-- dead
   filters.end_date = end                  # <-- dead
   ```
   If a line exists only so a test can read it back, the test is testing the wrong thing. Fix the test, not the production code.
2. **Silent deviations from plan-declared file scope.** `git diff HEAD~1 --stat` should match the "Files to touch" list verbatim. Extra files (even reasonable ones like a new helper) need a follow-up conversation before being committed.
3. **Hardcoded event data.** Search the subagent's diff for literal `"Iran"`, `"Hormuz"`, `"BZ=F"`, `"2026-02-28"`, `"2026-04-16"` in production code (not tests/fixtures). Everything event-specific should arrive via `EventConfig` fields or function params.
4. **Stripped type hints.** Plan text shows `def fetch(cfg: EventConfig) -> List[Dict]:` — the subagent's implementation must preserve the annotations. If the subagent simplified to `def fetch(cfg):` to get green, that's a regression.
5. **Swallowed errors.** `try: ... except Exception: pass` or `except: return []` on an internal call path is almost always wrong (boundary try/except around third-party APIs is the only allowed use, and only when we have a real fallback strategy).
6. **Test brittleness masquerading as a plan spec.** If a plan's assertion references an attribute of a third-party object (`f.some_attr`), verify at the REPL that the pinned library version exposes it before committing. See the `gdeltdoc.Filters` episode in "Library Quirks".
7. **Plan-file assertions that lock in bugs.** When a plan task's test body asserts a specific output shape and the shape "looks wrong" (e.g. an imperative verb surviving into a field called `event_description`, a user query appearing in a place that should be a noun phrase, a metric defaulting to the wrong sentinel), STOP. The assertion may have been written to match an implementation-author's mental model that was itself buggy — and "satisfying the assertion" will codify the bug. Session 5's Plan 2 Task 10 had `assert out["ripple_tree"]["event"].lower().startswith("show me")`, which passed only because the original implementation naïvely piped `state["query"]` into the ripple tree's event description; a subagent executing the task cold would have reproduced the bug perfectly. **Remedy:** question the assertion shape before writing code to satisfy it. If the assertion describes a bug, rewrite the test to lock in the CORRECT behavior and note the rewrite in `docs/progress.md`. This is the Plan-file analogue of smell #1 (test-shaped production code): here it's bug-shaped test code.
8. **Plan ↔ code drift is silent and must be re-verified per task.** CLAUDE.md's "assert on the library's real surface, not a plan's imagined surface" (Tests section) applies in both directions. Before executing ANY plan task, re-read the source files the task depends on and confirm function signatures, return shapes, and side-effects match what the plan's code snippets assume. Plan 2 drifted from Plan 1 across the Session 4 hardening (breaking-change `available` flag on `get_price_changes`, per-page NewsAPI try/except pattern, chromadb telemetry-suppression approach); Session 5 caught and reconciled this in a dedicated MD-only pass. Future plans (Plan 3) will drift from Plan 2 the same way once Plan 2 lands. Budget 15 minutes of "read-the-code, not-the-plan" per plan task start, same as the pre-task `pytest -v` check.

**Corrective workflow when a smell is found:** do NOT amend the subagent's commit. Write a new `refactor(<scope>): ...` or `fix(<scope>): ...` commit that undoes the smell and updates the affected tests. Note the follow-up commit in `docs/progress.md` under the originating task's row. This leaves the history honest — the subagent's first pass is preserved, the correction is visible as a separate act.

**Plan-maintenance chore (Session 5 lesson):** when editing a plan's tests (adding one, splitting, renaming), `grep -nE "Expected: [0-9]+ passed" docs/superpowers/plans/<plan>.md` after the edit and bump every downstream task's count. Missed counts mean an executing subagent will "fail" a task that's actually passing. Caught twice in Session 5 (Task 8 +1, Task 10 +2, propagated through Tasks 9/11/12/13) only because self-verification explicitly looked for it.

## How to Resume

1. `cd /Users/fangyihe/appliedfinance`
2. Read this file (`CLAUDE.md`) and [`docs/progress.md`](docs/progress.md) for what happened last session. **As of end-of-Session-10, the active plan is still Plan 3.6, but it is MID-EXECUTION, not merely written.** Task 1 is done, Task 2 is done after a user-driven follow-up, and Task 3 has NOT started because the user requested a hard checkpoint after every task and has not yet approved moving past the revised Task-2 UI. Also note the adjacent but out-of-plan diagnostics commit `9c9334e` on the price-detail path. Re-read the **"Course Grading Context & Plan 2.5 Rejection"** subsection under Scope Lock before proposing any data-layer expansion or any output-quality work that would cost >30 minutes of user time — that constraint is still in force.
3. Read the active plan file: [`docs/superpowers/plans/2026-04-26-plan-3.6-ui-interaction-fixes.md`](docs/superpowers/plans/2026-04-26-plan-3.6-ui-interaction-fixes.md). It now includes an Addendum with runtime corrections and **mandatory review gates after every task**. Plan-file end-state is **91 passed + 4 skipped**, but the current repo is **92 passed + 4 skipped** because `9c9334e` added three diagnostics tests outside original Task 3. **Do not start Task 3 until the user has re-reviewed Task 2 and explicitly said `continue`.**
4. Sanity-check the environment:
   - `/opt/anaconda3/envs/macro-ripple/bin/pytest -v` → **92 passed, 4 skipped** (end of Session 10). The 4 skipped are `RUN_LIVE=1`-gated: 2 in `tests/test_smoke_live.py` (Plan 1) and 2 in `tests/test_live_agents.py` (Plan 2).
   - `/opt/anaconda3/envs/macro-ripple/bin/python -c "import config, os; print(bool(os.environ.get('NEWSAPI_KEY')), bool(os.environ.get('ANTHROPIC_API_KEY')))"` — note that under Claude Desktop, this may print `True False` because the parent shell exports `ANTHROPIC_API_KEY=` (empty) which shadows `.env`. That's only a problem for live runs, not unit tests. To verify the real key is present: `awk -F= '/ANTHROPIC_API_KEY/ {print substr($2,1,15)}' .env` should show `sk-ant-api03-...`. See Library Quirks → `python-dotenv` if you hit this.
   - `git status --short` → expect `?? AGENTS.md` in this worktree. That file is local session context and is intentionally untracked; stage explicitly by file and do NOT sweep it into a commit accidentally. If `.env` appears here as untracked, verify it's still ignored by `.gitignore` (line 7) — do NOT stage it.
   - Optional — verify the Plan-1 data is fresh enough for Plan 2/3 to consume: `ls -la data/manifest.json`. If stale or missing, run `/opt/anaconda3/envs/macro-ripple/bin/python setup.py --event iran_war --refresh` (takes ~30–60s, hits live GDELT + NewsAPI + yfinance).
   - Optional live Plan-2 smoke: `/opt/anaconda3/envs/macro-ripple/bin/python run.py --event iran_war --query "How did oil react to Hormuz closure?"`. This hits the Anthropic API; expect a JSON blob with `intent`, `market_data` / `response` / `ripple_tree` / `timeline` depending on classification.
5. Start the next task per the mode mapping in "Working Mode". If dispatching a subagent, paste the plan task text inline in the brief — do not hand it the plan file. Include "Library Quirks" entries relevant to the task in the subagent's brief.
6. Before declaring the task done, walk the six Acceptance Criteria plus the Subagent Review Checklist (if applicable).

### Mid-Plan-3.6 specific notes (Session 10 → Session 11 handoff)

- **Task 1 is done and should not be re-litigated.** `52a269a` already proved that `plotly_events(click_event=True)` is the correct click path for Viz 1 in this environment. Do not revert to `st.plotly_chart(on_select="rerun")`.
- **Task 2's first pass was rejected by the user's live review.** `bc67b5f` was not enough. The current accepted code for continued review is `dcc5850`, which adds event-display-name retrieval, English translation, multi-lane placement, and label suppression. Any future Task-2 changes should start from THAT commit's behavior, not the original 2-lane idea.
- **Task 3 is blocked on a literal user `continue`.** The user requested a hard stop after every task. Even though the repo is green at 92+4, that does NOT authorize starting ripple-click wiring.
- **Task 3 will still require the return-shape break in `tree_to_graph_elements`.** When Task 3 begins, three existing tests in `test_ui_helpers.py` will need the `nodes, edges, _id_map = ...` update because the current code still returns a 2-tuple.
- **Known gap still NOT addressed:** `event_axis.render` calls `significant_moves(prices)` with the module-default `_DEFAULT_THRESHOLD_PCT=3.0`, NOT the user-tuned slider value from `price_chart.render()`. Slider plumbing through `st.session_state` was scoped out to keep Plan 3.6 focused on the observed UX failures. If user wants this, it's a small post-Plan-3.6 task.
- **Price explanation diagnostics improved, but explanation coverage is still corpus-limited.** `9c9334e` makes the UI honest (`no_retrieval`, `no_nearby_news`, `insufficient_evidence`); it does not make every date explainable. Future sessions should not treat remaining fallback cases as proof that the Session-10 fix failed.

### Pre-Plan-3 specific notes (carry-forward; partly satisfied)

- **API contracts Plan 3 must respect** (Session 6 Plan 2 surfaces Plan 3 will consume):
  - `agent_supervisor.run(cfg, query, as_of) -> AgentState` — returns a partial dict whose populated keys DEPEND on the classified intent. Plan 3 UI must branch on `final["intent"]` ("timeline" → `timeline`+`news_results` keys; "market" → `market_data`; "ripple" → `ripple_tree`; "qa" → `response`+`news_results`). Do not assume all keys are present.
  - `agent_supervisor.classify_intent({"query": str}) -> {"intent": ..., "focus": ...}` — Plan 3 eval (§9) may want to call this directly to measure classification accuracy vs the labeled `intent_examples.json` sweep.
  - `agent_ripple.generate_ripple_tree(event_description, cfg, as_of, max_depth=3, news_top_k=3) -> Dict` — produces a tree where every node has `supporting_news: List[Dict]` and `price_change: Optional[float]` + `price_details: List[Dict]`. Empty `supporting_news=[]` means `retrieve()` returned empty hits (setup.py likely not run). Plan 3 UI needs to distinguish this from "no citations worth showing".
  - `llm.get_chat_model(temperature, max_tokens) -> ChatAnthropic` — always use this instead of importing `ChatAnthropic` directly, so the UI inherits the `load_dotenv(override=True)` fix.
  - `llm.strip_fences(s: str) -> str` — reuse for any Plan-3 code that parses LLM JSON output (eval harness, refinement loops). Do not roll a new fence-stripper.
  - `setup.is_setup_in_progress() -> bool` — Plan 3 UI MUST call this before firing any `retrieve()`, to avoid racing a setup.py rebuild. Returns True only while another process holds the `$DATA_DIR/setup.lock` fcntl lock.
- **Plan 3 UX decision #1 (from Session 6 code review):** `run_news_agent` / `run_qa_agent` empty-retrieval responses don't carry a distinct `status` field. UI can't distinguish "setup.py hasn't run" from "LLM couldn't find an answer." Consider adding `status: "no_retrieval" | "answered" | "no_answer"` when drafting UI tabs — or accept the current jointly-distinguishable shape. Noted at bottom of `docs/progress.md`.
- **Plan 3 UX decision #2 (from Session 7 code review):** news snippets (`headline` + `text`) from `retrieve()` are interpolated directly into the system+human prompts in `run_news_agent` / `run_qa_agent` without delimiter escaping or injection-phrase filtering. Acceptable for MVP (trusted sources) but a production deployment needs either (a) delimiter-wrapped snippets that the system prompt instructs the model to treat as data only, (b) a lightweight pre-filter for known injection patterns, or (c) explicit documentation of the risk. Option (c) is currently in the [`README.md`](README.md) "Limitations" section. Decide before any public-facing deployment or before accepting user-provided events (§11.1).
- **Session 7 — LLM consumer hardening guarantees Plan-3 can rely on:**
  - `classify_intent` NEVER raises — even on valid-but-non-dict JSON (list/string/number). Safe to call without a top-level `try/except` around `agent_supervisor.run()`.
  - `run_news_agent` always returns `{"news_results": [...], "timeline": list[dict]}` — never a malformed `timeline`. Plan 3 UI can safely `.iter()` over `timeline` entries expecting them to be dicts.
  - `run_qa_agent` always returns `{"news_results": [...], "response": {"answer": str, "citations": list}}` — the `answer` key is ALWAYS present, even on worst-case LLM output (raw-text fallback populates it with the model's pre-parse string).
  - `run.py` returns exit code 2 with stderr message for unknown `--event` or bad `--as-of`. Plan 3 testing / CI scripts can parse stderr substring without catching SystemExit.
- **Model-ID currency check:** `llm.MODEL_ID = "claude-sonnet-4-6"`. Before running Plan 3 §9 evaluation, confirm this is still the current-generation Sonnet. A model bump is a one-line change but invalidates the quality baselines — re-run eval scripts after any bump.
- **Historical reference corpus (Week-2 add-on, NOT Plan 3 but adjacent):** `events/historical_reference/` for the 1979 + 1990-91 oil shocks. Curated markdown files, loaded by M3 at generation time as few-shot priors. If Plan 3 adds groundwork for this (e.g. a loader stub), flag it explicitly — it's outside MVP scope.
