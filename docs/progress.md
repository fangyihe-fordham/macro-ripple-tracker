# Progress Log

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
