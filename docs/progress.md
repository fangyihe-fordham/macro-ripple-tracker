# Progress Log

## Session 2 — 2026-04-20 → 2026-04-22

**Model:** Claude Opus 4.7 (1M context) via Claude Code CLI.
**Scope:** Plan 1 Task 4 (inline, TDD), Plan 1 Task 5 (subagent + review/refactor), Acceptance Criteria doc, `.env` infrastructure.
**Outcome:** Tasks 4 & 5 complete and committed on `main`. Project-wide Acceptance Criteria checklist codified. Secrets pipeline wired via `python-dotenv`. 10 tests passing. Both API keys now in place on disk; Plans 1 Task 6+ and Plan 2 are unblocked for credentials purposes.

### Commits landed this session (chronological)

| # | Commit | Type | Summary |
|---|---|---|---|
| 1 | `178f0d0` | feat(M2) | Plan 1 Task 4 — `get_price_changes(cfg, as_of)` + `get_price_range(symbol, start, end)` in `data_market.py`, 2 new tests in `tests/test_data_market.py` |
| 2 | `d6a9519` | feat(M1) | Plan 1 Task 5 — GDELT fetcher (`data_news/__init__.py`, `data_news/gdelt.py`, `tests/test_gdelt.py`, `tests/fixtures/gdelt_response.json`) via subagent |
| 3 | `b4e9fbe` | refactor(M1) | Post-subagent cleanup: removed decorative `filters.keyword=` / `.start_date=` / `.end_date=` assignments in `data_news/gdelt.py`; test now asserts on `Filters.query_params` (the library's real surface) |
| 4 | `60df2ee` | docs | Session 2 handoff first pass (this file) |
| 5 | `c3e8fc0` | docs | Added **Acceptance Criteria (every task)** six-item gate to `CLAUDE.md` — full pytest green, plan-only file scope, spec-matching signatures, no hardcoded event data, conventional commit + trailer, full pytest tail in report |
| 6 | `b15ba33` | chore | `.env` loader via `python-dotenv` + `.env.example` committed template; `config.py` now calls `load_dotenv()` at import time; added `python-dotenv==1.0.1` to `requirements.txt` |

### Tasks completed (plan mapping)

| Task | Commit(s) | Files touched |
|---|---|---|
| Plan 1 Task 4 — M2 % change + range (inline) | `178f0d0` | `data_market.py`, `tests/test_data_market.py` |
| Plan 1 Task 5 — GDELT fetcher (subagent + cleanup) | `d6a9519`, `b4e9fbe` | `data_news/__init__.py` (empty), `data_news/gdelt.py`, `tests/test_gdelt.py`, `tests/fixtures/gdelt_response.json` |

### Deviations from plan text

1. **Plan 1 Task 5 — `gdeltdoc.Filters` API shape.** The plan specified:
   - `Filters(keyword=..., start_date=..., end_date=..., language="english")`
   - Test assertions `f.keyword`, `f.start_date`, `f.end_date`

   Neither works against `gdeltdoc==1.6.0` (the pinned version):
   - `Filters.__init__` does not accept `language=` — raises `TypeError: __init__() got an unexpected keyword argument 'language'`. Its signature only accepts `start_date`, `end_date`, `timespan`, `num_records`, `keyword`, `domain`, `domain_exact`, `near`, `repeat`, `country`, `theme`.
   - `Filters` discards the named kwargs immediately and stores the compiled query as `query_params: list[str]` (a list of URL fragments like `['(Iran OR Hormuz OR oil) ', '&startdatetime=20260228000000', '&enddatetime=20260416000000', '&maxrecords=250']`). The instance has no `.keyword`, `.start_date`, `.end_date` attributes after construction — `vars(f).keys()` returns `['query_params', '_valid_countries', '_valid_themes']`.

   **Fix applied:** dropped the `language=` kwarg from the `Filters(...)` call; rewrote the Task 5 test to assert on `query_params` content — `"Hormuz" in " ".join(f.query_params)`, `"startdatetime=20260228" in ...`, `"enddatetime=20260416" in ...`. English-only filtering, if needed later, is a separate change (either via `near`/custom query string or a post-filter on the returned DataFrame).

2. **Plan 1 Task 5 — subagent produced test-shaped production code.** The first subagent pass (commit `d6a9519`) discovered the `Filters` issue mid-implementation and chose to decorate the `Filters` instance with post-hoc attribute assignments purely to satisfy the plan's test assertions:

   ```python
   filters = Filters(keyword=..., start_date=..., end_date=...)
   filters.keyword = cfg.seed_keywords     # dead code — not read by article_search
   filters.start_date = start              # dead code
   filters.end_date = end                  # dead code
   ```

   Behavior was correct (yfinance-style: kwargs drive `query_params`), but those three lines existed solely to make the test's `f.keyword` / `f.start_date` / `f.end_date` introspection pass. That inverts TDD: production code was shaped by the test assertion mechanics rather than by the real library surface. Caught in review and refactored in commit `b4e9fbe` — removed the decorative lines and rewrote the test to assert on `query_params` directly.

   **Generalized lesson (now in `CLAUDE.md` under Acceptance Criteria):** a subagent returning green is *necessary but not sufficient*. Review the diff for (a) test-shaped decoration in production code, (b) files outside the plan's declared scope, (c) hardcoded event data, (d) silent downgrades like removed type hints or `except: pass`. Followup commit is the corrective action — do not amend.

3. **Not a deviation, but newly documented:** added the **Acceptance Criteria (every task)** section to `CLAUDE.md` (commit `c3e8fc0`) codifying the six-item gate every task must clear. This was an ad-hoc check I applied in this session; future sessions should treat it as mandatory.

4. **New infrastructure dependency — `python-dotenv==1.0.1`.** Not in the original plan. Added in commit `b15ba33` because the user chose `.env`-based secret management over shell `export`. `config.py` now calls `load_dotenv()` at import time, so any entry point that transitively imports config (every test, every future CLI / Streamlit run) gets `NEWSAPI_KEY` and `ANTHROPIC_API_KEY` in `os.environ` automatically. Listed under a new "Config" heading in `requirements.txt`, pinned at 1.0.1.

### Current state

- **Pytest:** `/opt/anaconda3/envs/macro-ripple/bin/pytest -v` → **10 passed**.
  - `tests/test_config.py`: 3 passed
  - `tests/test_data_market.py`: 5 passed (Tasks 3 + 4)
  - `tests/test_gdelt.py`: 2 passed (Task 5)
- **Public APIs available:**
  - `config.load_event(name) -> EventConfig` — pydantic v2 model with `name`, `display_name`, `start_date`, `end_date`, `baseline_date`, `seed_keywords: List[str]`, `tickers: List[Ticker]`, `rss_feeds: List[str]`.
  - `config.Ticker` — pydantic v2 model with `category`, `name`, `symbol`.
  - `data_market.download_prices(cfg) -> None` — writes one OHLCV CSV per ticker under `$DATA_DIR/prices/`, filename via `_csv_path()` sanitization.
  - `data_market.get_price_on_date(symbol, d) -> Optional[float]` — close on a trading day; `None` for weekends / missing CSVs.
  - `data_market.get_price_changes(cfg, as_of) -> dict[symbol -> {baseline, latest, pct_change}]` — baseline is `cfg.baseline_date` close, latest is `as_of` close, pct_change is signed percent.
  - `data_market.get_price_range(symbol, start, end) -> pd.Series` — inclusive on both ends, Date-indexed Series of Close prices; trading days only.
  - `data_news.gdelt.fetch(cfg) -> List[Dict]` — each dict has `{url, headline, source, date, snippet, full_text, source_kind}`; `source_kind="gdelt"`; `snippet` and `full_text` always empty for GDELT (API doesn't return bodies).
- **Files on disk at end of session:**
  - New this session: `data_news/__init__.py`, `data_news/gdelt.py`, `tests/test_gdelt.py`, `tests/fixtures/gdelt_response.json`, `.env` (gitignored, user-edited with real keys), `.env.example` (committed template).
  - Modified this session: `config.py` (added `load_dotenv()` import + call), `requirements.txt` (added `python-dotenv==1.0.1`), `CLAUDE.md` (Acceptance Criteria section), `docs/progress.md`.
- **Environment:** conda env `macro-ripple` at `/opt/anaconda3/envs/macro-ripple/bin/python`; `python-dotenv==1.0.1` installed via pip (had been at 1.2.2 automatically pulled as a transitive dep; pinned down).
- **Secrets:** `NEWSAPI_KEY` and `ANTHROPIC_API_KEY` both populated in `/Users/fangyihe/appliedfinance/.env` (gitignored, never committed). Verify with `/opt/anaconda3/envs/macro-ripple/bin/python -c "import config, os; print(bool(os.environ.get('NEWSAPI_KEY')), bool(os.environ.get('ANTHROPIC_API_KEY')))"` → should print `True True`.

### Next session — exact next step

**Plan 1 Task 6 (subagent): NewsAPI fetcher.** Source of truth: `docs/superpowers/plans/2026-04-16-plan-1-data-foundation.md` → Task 6. Unit tests mock `NewsApiClient` so no live API calls happen during pytest — but `NEWSAPI_KEY` is now in `.env` for any live smoke run the session wants to do afterward.

**Subagent brief must include** (do not let it read the plan file — paste the task text inline):
- Which commits have already landed on `main` (`b15ba33` head; Task 5 + its cleanup are in). Pytest baseline is 10 passed.
- Public APIs it can import (`config.load_event`, etc. — see "Public APIs available" above).
- `python-dotenv` auto-loads `.env`; tests should monkeypatch `NEWSAPI_KEY` via `monkeypatch.setenv` / `monkeypatch.delenv` anyway, so they don't depend on the real key.
- Reminder of the six Acceptance Criteria in `CLAUDE.md`.
- The `gdeltdoc.Filters` lesson generalizes: when a plan's test assertions reference attributes of a third-party object, verify those attributes actually exist in the pinned library version before accepting the plan text verbatim. For `newsapi-python==0.2.7`, `NewsApiClient.get_everything(...)` returns a plain dict — safe, no special attrs.

After Task 6, remaining Plan 1 tasks per the mode mapping in `CLAUDE.md`:
- Task 7 — RSS fetcher (subagent)
- Task 8 — URL + MinHash dedup (subagent)
- Task 9 — articles.json store (subagent)
- Task 10 — ChromaDB vector store + `retrieve()` (subagent; first run downloads ~80 MB MiniLM model)
- Task 11 — `setup.py` orchestrator (inline; remember to add `from dotenv import load_dotenv; load_dotenv()` at the top — or just `import config` which does the same thing — before any fetcher that reads env keys)
- Task 12 — live smoke test (inline, gated by `RUN_LIVE=1`)

### Blockers

**All Session 1 blockers resolved.** Status as of end of Session 2:

1. ~~`ANTHROPIC_API_KEY` missing~~ — **resolved.** Populated in `.env`; will be picked up by `langchain-anthropic` via `os.environ` in Plan 2. Budget is user's pay-as-you-go account.
2. ~~`NEWSAPI_KEY` missing~~ — **resolved.** Populated in `.env`. Free tier (100 req/day); if Plan 1 Task 6 live smoke hits the limit, either wait 24h or remove NewsAPI from the active source set (its `fetch()` returns `[]` when the key is unset, so degradation is graceful).
3. **Plan 2 ready to start** whenever Plan 1 lands. No new blockers anticipated.
4. **New operational concern (not a blocker but worth flagging):** ChromaDB persistent store lives at `$DATA_DIR/chroma_db/`. Task 10 will build it; Task 11 (`setup.py`) will populate it. Size estimate: ~10–50 MB depending on article count. Already gitignored via `data/` rule. No action needed.

---

## Session 1 — 2026-04-16

**Model:** Claude Opus 4.7 (1M context) via Claude Code CLI.
**Scope:** Read spec, write 3 implementation plans, start Plan 1 execution.
**Outcome:** 3 plans written; Plan 1 Tasks 1–3 complete and committed on `main`.

---

### Tasks completed

| Task | Commit | Summary |
|---|---|---|
| Plan 1 Task 1 — scaffolding | `1a4638a` | Repo init, `environment.yml`, `requirements.txt`, `.gitignore`, `events/iran_war.yaml`, `tests/conftest.py`, fixtures dir |
| Plan 1 Task 2 — config loader | `70e5bc9` | `config.py` (pydantic v2 `EventConfig` + `Ticker` + `load_event`), `tests/test_config.py` (3 tests green) |
| Plan 1 Task 3 — market data, part 1 | `77bfd0b` | `data_market.py` (`download_prices`, `get_price_on_date`), `tests/test_data_market.py` (3 tests green), `tests/fixtures/yf_brent_sample.csv` |

All 6 tests currently pass under `/opt/anaconda3/envs/macro-ripple/bin/pytest -v`.

---

### Files created/modified this session

**Plans (not yet committed as code, live in repo):**
- `docs/superpowers/plans/2026-04-16-plan-1-data-foundation.md` — 12-task TDD plan for M1 (news) + M2 (market) + `setup.py` orchestrator.
- `docs/superpowers/plans/2026-04-16-plan-2-agents.md` — 15-task plan for M3 (ripple tree generator) + M4 (LangGraph supervisor with 4 sub-agents).
- `docs/superpowers/plans/2026-04-16-plan-3-ui-eval.md` — 12-task plan for M5 (Streamlit 4-tab UI) + §9 eval harness.

**Repo scaffolding (Task 1):**
- `environment.yml` — conda env `macro-ripple`, Python 3.11, references `requirements.txt` via pip.
- `requirements.txt` — pinned deps (yfinance 0.2.51, pandas 2.2.3, pydantic 2.9.2, gdeltdoc 1.6.0, newsapi-python 0.2.7, feedparser 6.0.11, datasketch 1.6.5, chromadb 0.5.18, sentence-transformers 3.2.1, langchain-anthropic 0.2.4, langgraph 0.2.50, streamlit 1.40.2, plotly 5.24.1, streamlit-agraph 0.0.45, pytest 8.3.3, pytest-mock 3.14.0, responses 0.25.3).
- `.gitignore` — stdlib Python + `data/` (with `.gitkeep` exception) + `.env` + `.claude/`.
- `events/iran_war.yaml` — 11 tickers (BZ=F, CL=F, NG=F, TTF=F, ^DJT, GSL, URA, MOS, LIN, APD, ^GSPC), start 2026-02-28, end 2026-04-16, baseline 2026-02-27, seed_keywords + Reuters/AP RSS feeds.
- `tests/conftest.py` — `fixtures_dir` and `tmp_data_dir` (sets `DATA_DIR` env var for test isolation).
- `tests/fixtures/.gitkeep` — placeholder.
- `data/.gitkeep` — placeholder.

**Task 2:**
- `config.py` — `Ticker` (category/name/symbol), `EventConfig` (with `@model_validator(mode="after")` enforcing `baseline_date < start_date` and `end_date >= start_date`), `load_event(name, events_dir=None)` reading `events/<name>.yaml`.
- `tests/test_config.py` — `test_load_iran_war_event`, `test_load_event_missing_raises`, `test_baseline_before_start`.

**Task 3:**
- `data_market.py` — `_data_dir()` honoring `DATA_DIR` env var, `_prices_dir()`, `_csv_path(symbol)` sanitizing `=`/`^`/`/` → `_`, `download_prices(cfg)` (loop over `cfg.tickers`, yfinance with `start=baseline-7d` and `end=end_date+1d`, reset_index, write CSV per ticker), `_load(symbol)`, `get_price_on_date(symbol, d)` returning `Optional[float]`.
- `tests/test_data_market.py` — 3 tests using `fake_yf` fixture that monkeypatches `data_market.yf.download` to return fixture DataFrame.
- `tests/fixtures/yf_brent_sample.csv` — 8-row OHLCV sample spanning Feb 23 – Mar 4, 2026. Baseline Feb 27 close = 74.20, Mar 4 close = 111.00 (used for Task 4 pct_change assertions).

**Handoff docs (this commit):**
- `CLAUDE.md` — project map, tech stack, plan status, scope lock, conventions.
- `docs/progress.md` — this file.

---

### Decisions made

**Architecture / tooling:**
- **Claude model access:** chose **Option A** — pay-as-you-go API key (`ANTHROPIC_API_KEY`) via console.anthropic.com, using `langchain-anthropic.ChatAnthropic(model="claude-sonnet-4-6")`. Rejected Option B (custom wrapper around `claude-agent-sdk` + Max subscription) as too much glue code for a weekend project. **Key not yet obtained — blocker for Plan 2 Task 1.**
- **Python environment:** dedicated conda env `macro-ripple` on Python **3.11** (not user's base 3.13.9) at `/opt/anaconda3/envs/macro-ripple/bin/python`. Reason: `chromadb` + `sentence-transformers` wheels are unreliable on 3.13.
- **Git workflow:** direct commits on `main` (no PRs, no worktrees). One commit per plan-task. Format: `<type>(<scope>): <summary>` with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
- **Execution mode:** hybrid per Plan 1 task — inline for simple/glue (Tasks 1, 2, 3, 4, 8, 10, 12), subagent for independent M1 submodules (Tasks 5 GDELT, 6 NewsAPI, 7 RSS, 9 dedup, 11 embed/index). Plan 2 & 3 modes TBD after Plan 1 finishes.
- **UI stack:** Streamlit local web app (http://localhost:8501). No deployment. streamlit-agraph for ripple tree, Plotly for market charts.
- **Ripple visualization:** chose the tree/graph widget (streamlit-agraph) over plain text tree.

**Code conventions:**
- **Pydantic v2 syntax:** `model_validator(mode="after")` on the instance (not `@root_validator`).
- **Test isolation:** `tmp_data_dir` fixture sets `DATA_DIR` env var so production code writes under `tmp_path`, not the real `data/` dir.
- **External API boundary:** tests mock at the **module attribute** (`monkeypatch.setattr(data_market.yf, "download", fake)`), not at the library itself. This pattern will repeat for GDELT/NewsAPI/RSS.
- **yfinance end date trick:** pass `end=cfg.end_date + timedelta(days=1)` because yfinance treats `end` as exclusive.
- **CSV filename sanitization:** `BZ=F` → `BZ_F.csv`, `^GSPC` → `GSPC.csv`, stripping `=`, `^`, `/`.
- **Live tests:** none yet; when added (M1), gate with `pytest.mark.skipif(not os.getenv("RUN_LIVE"), ...)` so CI and default local runs stay offline.
- **Comments:** none added unless a non-obvious invariant needs documenting. So far, only one such comment in tests (weekend gap explanation).
- **No try/except around internal calls.** Boundary try/except only around external APIs when we add retry/fallback logic (not yet).

**Scope:**
- **MVP = Iran War 2026 only.** No user-input events, no multi-event comparison, no real-time updates, no full-text scraping, no cloud deploy, no KG-RAG, no formal event-study stats, no TruLens.
- **Week 2 addendum:** historical reference corpus of 2–5 markdown files each for the 1979 Iranian Revolution and the 1990–91 Gulf War, to live in `events/historical_reference/`. These are **analytical material feeding M3** (ripple generator prompts/context), not standalone events tracked in the UI.

---

### Current state

**Runs end-to-end:**
- Pytest: `/opt/anaconda3/envs/macro-ripple/bin/pytest -v` → 6 passed.
- `load_event("iran_war")` returns valid `EventConfig`.
- `data_market.download_prices(cfg)` writes one CSV per ticker into `$DATA_DIR/prices/`.
- `data_market.get_price_on_date(symbol, date)` returns close or `None`.

**Stubbed / partial:**
- `data_market.py` has `get_price_on_date` but **not** `get_price_changes` or `get_price_range` yet (Task 4).
- `events/historical_reference/` directory — not yet created; Week 2 work.

**Not started:**
- Plan 1 Tasks 4–12 (M2 finish + M1 news ingest + M1 embed/index + setup.py orchestrator).
- Plan 2 (15 tasks, M3 ripple + M4 LangGraph supervisor).
- Plan 3 (12 tasks, M5 Streamlit UI + §9 eval harness).
- `.env` file with `ANTHROPIC_API_KEY`, `NEWSAPI_KEY`.

---

### Blockers / ambiguities

1. **`ANTHROPIC_API_KEY` not yet obtained** — required before Plan 2 Task 1. User chose Option A (pay-as-you-go, ~$5–20 budget). Get from https://console.anthropic.com and add to `.env` as `ANTHROPIC_API_KEY=sk-ant-...`.
2. **`NEWSAPI_KEY` not yet obtained** — required before Plan 1 Task 6. Free tier from https://newsapi.org/register.
3. **GDELT has no API key** — zero-setup, but Plan 1 Task 5 should include a live smoke test gated by `RUN_LIVE=1`.
4. **No blockers on Plan 3 yet.**

---

### Next session — exact next step

**Start with Plan 1 Task 4 (inline): "M2 % change vs baseline + price range query".**

Source of truth: `docs/superpowers/plans/2026-04-16-plan-1-data-foundation.md` → Task 4.

Files touched:
- Modify `tests/test_data_market.py` — append `test_get_price_changes_vs_baseline` and `test_get_price_range` (exact code in the plan).
- Modify `data_market.py` — append `get_price_changes(cfg, as_of)` returning `dict[symbol -> {baseline, latest, pct_change}]` and `get_price_range(symbol, start, end)` returning `pd.Series` indexed by date (inclusive both ends, trading days only).

Expected commit: `feat(M2): % change vs baseline + price range query`

After Task 4, continue with Task 5 (GDELT client, subagent) per the plan's mode mapping.
