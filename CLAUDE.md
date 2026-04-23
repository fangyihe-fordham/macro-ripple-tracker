# CLAUDE.md — Macro Event Ripple Tracker

> **For the next Claude Code session.** Read this file first. It is the single source of truth for project conventions and active scope.

## Project

Applied Finance course project, v0.2. Agentic RAG that turns a macro/geopolitical event into a grounded ripple analysis: timeline, multi-level industry impact tree, market data, and free-form Q&A — all in one Streamlit app backed by Claude Sonnet + LangGraph.

**Authoritative design spec:** [`MacroRippleTracker_Spec_v0.2.docx`](MacroRippleTracker_Spec_v0.2.docx) in repo root. Translated markdown version is on disk at `/tmp/spec.md` (not committed). If that tmp file is gone, re-run `pandoc --track-changes=all MacroRippleTracker_Spec_v0.2.docx -o /tmp/spec.md`.

## Implementation Plans

All saved in `docs/superpowers/plans/`:

- [`2026-04-16-plan-1-data-foundation.md`](docs/superpowers/plans/2026-04-16-plan-1-data-foundation.md) — **DONE + HARDENED (end of Session 4).** 12 tasks + 2 Session-3 infra follow-ups + 15 Session-4 hardening/cleanup commits (8 code-review-driven in Round 1, 6 user-directed in Round 2, 1 regression fix). All Plan 1 verification checklist items still green; live run delivers richer data (1,387 unique articles vs 1,217 in Session 3; retrieval top hit 0.533 vs 0.39).
- [`2026-04-16-plan-2-agents.md`](docs/superpowers/plans/2026-04-16-plan-2-agents.md) — Not started but **reconciled** (Session 4, commit `35f46e2`) to match Plan 1's new `get_price_changes` `available` flag contract + `classify_intent` now returns `{intent, focus}` JSON with extracted event focus. 15 tasks.
- [`2026-04-16-plan-3-ui-eval.md`](docs/superpowers/plans/2026-04-16-plan-3-ui-eval.md) — Not started. 12 tasks. M5 Streamlit 4-tab UI + §9 evaluation harness. **Plan 3 UI should call `setup.is_setup_in_progress()` before triggering `retrieve()` against ChromaDB** — see `vector_store.py` docstring and C4 lock commit `e5a84ad`.

Execute plans task-by-task. Each task = TDD cycle + a single `git commit`. Do not batch tasks into one commit.

## Tech Stack

- **Python 3.11** in dedicated conda env `macro-ripple` at `/opt/anaconda3/envs/macro-ripple/bin/python`. Do **not** use the user's `base` env (Python 3.13, risky for chromadb + sentence-transformers).
- **Config:** `python-dotenv` (loads `.env` at `config.py` import time)
- **Data:** `yfinance`, `pandas`, `pyyaml`, `pydantic` v2
- **News:** `gdeltdoc`, `newsapi-python`, `feedparser`
- **Dedup:** `datasketch` (MinHash LSH)
- **Vector store:** `chromadb` (persistent, local) + `sentence-transformers` (`all-MiniLM-L6-v2`, local, free)
- **Agents:** `langchain-anthropic` + `langgraph` + `claude-sonnet-4-6` via `ANTHROPIC_API_KEY` (provided via `.env` as of Session 2)
- **UI:** `streamlit` + `plotly` + `streamlit-agraph` (local web app at http://localhost:8501; no deployment)
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
5. **Commit message is `<type>(<scope>): <desc>` with the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.** One commit per task.
6. **Show the full `pytest -v` output before declaring done.** No paraphrasing the result — paste the tail that shows `N passed`.

If a subagent returns green but any criterion above is unmet (e.g. extra files touched, hardcoded values, test-shaped decoration in production code), review and fix in a follow-up commit before moving on.

## Current Directory Structure (real, end of Session 4 — Plan 1 hardened)

```
/Users/fangyihe/appliedfinance/
├── CLAUDE.md                     # ← this file
├── README.md                     # data-source strategy + quickstart (added Session 4, R2-T2)
├── MacroRippleTracker_Spec_v0.2.docx
├── environment.yml               # conda spec
├── requirements.txt              # pinned deps (yfinance 0.2.66; LangChain/LangGraph TBD Plan 2)
├── .gitignore                    # includes `.env` and `data/`
├── .env                          # gitignored — NEWSAPI_KEY, ANTHROPIC_API_KEY (both populated)
├── .env.example                  # committed template — same keys, empty values
├── config.py                     # EventConfig pydantic (MUTABLE — tests can set cfg.field=...); load_event() calls load_dotenv() at import
├── data_market.py                # M2: download_prices (returns List[str] missing), get_price_on_date, get_price_changes (now keyed by ALL tickers with `available` flag), get_price_range; _WARNED_MISSING one-shot log cache
├── setup.py                      # orchestrator CLI: fcntl-locked (setup.lock); --refresh wipes prices/+articles.json+chroma_db; exports is_setup_in_progress()
├── data_news/                    # M1 news package
│   ├── __init__.py               # re-exports retrieve, index_articles, reset, read_articles, write_articles
│   ├── gdelt.py                  # 7-day chunk pagination (num_records=250, 2s sleep, per-chunk try/except — load-bearing)
│   ├── newsapi_fetcher.py        # 30-day clamp + per-page try/except + 100-total-cap detection via NewsAPIException code
│   ├── rss.py                    # keyword-filtered on STRIPPED summary; _strip_html removes <script>/<style>/<!--...--> content-and-all before tag strip
│   ├── dedup.py                  # URL dedup → MinHash LSH (threshold 0.95; returns (kept, stats))
│   ├── store.py                  # articles.json read/write via DATA_DIR env var
│   └── vector_store.py           # ChromaDB + MiniLM; telemetry logger silenced at module load; reset() clears SharedSystemClient cache; sha1 stable IDs
├── events/
│   └── iran_war.yaml             # RSS feeds deprecated (empty list) — GDELT covers same publications
├── data/                         # runtime, gitignored; populated by setup.py run
│   ├── articles.json             # ~1,387 unique articles after cross-source dedup (Session 4 baseline)
│   ├── prices/*.csv              # 11 files, one per cfg.tickers entry
│   ├── chroma_db/                # persistent MiniLM vector index
│   ├── manifest.json             # event, snapshot_utc, article_count, source_counts, dedup, ticker_count, missing_tickers
│   └── setup.lock                # fcntl lock file; presence + non-free state = setup.py is running
├── docs/
│   ├── progress.md               # session log (Sessions 1–4)
│   └── superpowers/plans/
│       ├── 2026-04-16-plan-1-data-foundation.md  # DONE + hardened
│       ├── 2026-04-16-plan-2-agents.md           # next — RECONCILED Session 4 to match new contracts
│       └── 2026-04-16-plan-3-ui-eval.md
└── tests/
    ├── __init__.py               # empty
    ├── conftest.py               # fixtures_dir, tmp_data_dir (sets DATA_DIR env)
    ├── test_config.py            # 3 tests
    ├── test_data_market.py       # 8 tests — incl. _WARNED_MISSING log-once, download_prices missing return, get_price_changes available-flag contract
    ├── test_gdelt.py             # 3 tests (incl. chunk-failure resilience; monkeypatches gdelt.time.sleep)
    ├── test_newsapi.py           # 6 tests — +30d-clamp assertions, +far-future short-circuit, +pagination stop-on-short-page, +free-tier 100-cap regression
    ├── test_rss.py               # 3 tests — keyword filter + script/style/comment stripping + case-insensitive newline-spanning
    ├── test_dedup.py             # 2 tests (unpacks new (kept, stats) return + asserts stats shape)
    ├── test_store.py             # 2 tests
    ├── test_vector_store.py      # 4 tests — +C3 surface-errors-not-silent-empty, +I5 stable-IDs-across-runs
    ├── test_setup_cli.py         # 3 tests — end-to-end + --refresh-wipes-stale + fcntl-lock-blocks-concurrent (subprocess-based)
    ├── test_smoke_live.py        # 2 tests, gated by RUN_LIVE=1 (real GDELT + yfinance SPY)
    └── fixtures/
        ├── yf_brent_sample.csv   # sample OHLCV for M2 tests
        ├── gdelt_response.json   # sample GDELT articles
        ├── newsapi_response.json # sample NewsAPI /v2/everything payload
        └── rss_sample.xml        # 3-item RSS 2.0 feed (rss-3 now contains <p><a>...</a></p>&nbsp; to exercise _strip_html)
```

**Test counts:** 36 total → **34 pass + 2 gated-skip** (end of Session 4). 13 more tests than end-of-Session-3's 23.

**Commits on `main` at end of Session 4 (newest first, session-4 additions bold):**
**`35f46e2`** → **`862d263`** → **`33f88f5`** → **`0726337`** → **`90f02db`** → **`db8beb9`** → **`5fb2c8c`** → **`a1138b2`** → **`e5a84ad`** → **`15edf56`** → **`eba54a7`** → **`36a4d3d`** → **`62dbc4c`** → **`45b6157`** → **`c454c8b`** → **`ecd92fc`** → `aa2f3ea` → `fc3704c` → `3beabee` → `deb4650` → `0b69dbe` → `44e2d12` → `24adb51` → `3e25d3f` → `717d6c2` → `1c0793e` → `d1a23f2` → `b15ba33` → `c3e8fc0` → `60df2ee` → `b4e9fbe` → `d6a9519` → `178f0d0` → `1c5d7ed` → `77bfd0b` → `70e5bc9` → `1a4638a`.

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

## Conventions Established in Tasks 1–5 (+ Session 4 hardening)

### Python

- **Type hints always** on public function signatures. `Optional[T]` for nullable returns. Use `date` (not `datetime`) for calendar dates.
- **pydantic v2 syntax**: `model_validator(mode="after")` for cross-field validation (example in `config.py`). Do not mix in v1 syntax.
- **pydantic models are MUTABLE by default** (v2 unless `model_config = ConfigDict(frozen=True)`). `EventConfig` is not frozen → tests can do `cfg = load_event("iran_war"); cfg.rss_feeds = ["..."]` to inject synthetic values instead of constructing a throwaway model. Session 4's `test_rss.py` relies on this after `iran_war.yaml` deprecated its RSS feeds. DO NOT add `frozen=True` to `EventConfig` without checking which tests mutate fields.
- **No comments** unless the *why* is non-obvious. Load-bearing comments in the codebase now explain (a) weekend gaps in market data tests, (b) `config.py` calling `load_dotenv()` at import time, (c) GDELT `query_params` introspection, (d) yfinance `multi_level_index=False` flag, (e) `_WARNED_MISSING` one-shot log cache, (f) `chromadb` posthog-logger suppression, (g) `SharedSystemClient.clear_system_cache()` after `rmtree`, (h) NewsAPI 100-total-cap rationale in the pagination loop. If you add a comment, match that register.
- **`DATA_DIR` env var** isolates the runtime data directory (`data/` by default). Every module that reads/writes files under `data/` **must** resolve via `Path(os.environ.get("DATA_DIR", "data"))` — the `tmp_data_dir` pytest fixture depends on this for isolation. Session-4-added targets under `$DATA_DIR`: `setup.lock` (fcntl lock file) in addition to the existing `articles.json`, `prices/`, `chroma_db/`, `manifest.json`.

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
2. Read this file (`CLAUDE.md`) and [`docs/progress.md`](docs/progress.md) for what happened last session. As of end-of-Session-4, the active plan is Plan 2.
3. Read the active plan file. Next task is listed in `progress.md` under "Next session — exact next step". Session 4's reconciled Plan 2 file is the source of truth — **do not read an older copy**.
4. Sanity-check the environment:
   - `/opt/anaconda3/envs/macro-ripple/bin/pytest -v` → **34 passed, 2 skipped** (end of Session 4). The 2 skipped are the `RUN_LIVE=1`-gated smoke probes in `tests/test_smoke_live.py`.
   - `/opt/anaconda3/envs/macro-ripple/bin/python -c "import config, os; print(bool(os.environ.get('NEWSAPI_KEY')), bool(os.environ.get('ANTHROPIC_API_KEY')))"` → `True True`. If either is `False`, check that `.env` at the repo root has both keys populated (no quotes, no spaces around `=`).
   - `git status --short` → clean. If `.env` appears here as untracked, verify it's still ignored by `.gitignore` (line 7) — do NOT stage it.
   - Optional — verify the Plan-1 data is fresh enough for Plan 2 to consume: `ls -la data/manifest.json`. If stale or missing, run `/opt/anaconda3/envs/macro-ripple/bin/python setup.py --event iran_war --refresh` (takes ~30–60s, hits live GDELT + NewsAPI + yfinance).
5. Start the next task per the mode mapping in "Working Mode". If dispatching a subagent, paste the plan task text inline in the brief — do not hand it the plan file. Include "Library Quirks" entries relevant to the task in the subagent's brief.
6. Before declaring the task done, walk the six Acceptance Criteria plus the Subagent Review Checklist (if applicable).

### Pre-Plan-2 specific notes

- **API contracts Plan 2 must respect** (Session 4 changes — Plan 2 markdown already reconciled, commit `35f46e2`):
  - `data_market.get_price_changes(cfg, as_of)` ALWAYS returns every `cfg.tickers` symbol, each entry is `{"available": bool, "baseline": Optional[float], "latest": Optional[float], "pct_change": Optional[float]}`. No KeyErrors; check `available` before reading `pct_change`.
  - `data_news.dedup.deduplicate(...)` returns `(kept, stats)` — a TUPLE, not a list. Plan 2 probably won't call this but setup.py does.
  - `data_news.retrieve(query, top_k)` unchanged — returns list of `{text, url, headline, metadata, score}`.
  - `setup.is_setup_in_progress() -> bool` — new helper for gating concurrent access.
- **Plan 2 Task 1 has two sub-steps to SKIP**: `.env.example` already exists (Session 2), `.env` already populated. Only append to `requirements.txt` + create `prompts/__init__.py`. Plan 2's reconciled text marks these.
- **Library pins Plan 2 Task 1 will add:** `langchain==0.3.7`, `langchain-core==0.3.15`, `langchain-anthropic==0.3.0`, `langgraph==0.3.0`. The `langchain-anthropic==0.2.4` + `langgraph==0.2.50` in current `requirements.txt` are bumped to 0.3.0 — safe because nothing in Plan 1 imports them, but IS a version change in a working env. Flag to user before `pip install -r requirements.txt`.
