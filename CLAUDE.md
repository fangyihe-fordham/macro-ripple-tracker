# CLAUDE.md — Macro Event Ripple Tracker

> **For the next Claude Code session.** Read this file first. It is the single source of truth for project conventions and active scope.

## Project

Applied Finance course project, v0.2. Agentic RAG that turns a macro/geopolitical event into a grounded ripple analysis: timeline, multi-level industry impact tree, market data, and free-form Q&A — all in one Streamlit app backed by Claude Sonnet + LangGraph.

**Authoritative design spec:** [`MacroRippleTracker_Spec_v0.2.docx`](MacroRippleTracker_Spec_v0.2.docx) in repo root. Translated markdown version is on disk at `/tmp/spec.md` (not committed). If that tmp file is gone, re-run `pandoc --track-changes=all MacroRippleTracker_Spec_v0.2.docx -o /tmp/spec.md`.

## Implementation Plans

All saved in `docs/superpowers/plans/`:

- [`2026-04-16-plan-1-data-foundation.md`](docs/superpowers/plans/2026-04-16-plan-1-data-foundation.md) — **In progress.** 12 tasks. M1 news package (GDELT + NewsAPI + RSS + dedup + ChromaDB) and M2 market data (yfinance), glued by `setup.py`.
- [`2026-04-16-plan-2-agents.md`](docs/superpowers/plans/2026-04-16-plan-2-agents.md) — Not started. 15 tasks. M3 ripple tree generator + M4 LangGraph supervisor.
- [`2026-04-16-plan-3-ui-eval.md`](docs/superpowers/plans/2026-04-16-plan-3-ui-eval.md) — Not started. 12 tasks. M5 Streamlit 4-tab UI + §9 evaluation harness.

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

## Current Directory Structure (real, post-Task 5)

```
/Users/fangyihe/appliedfinance/
├── CLAUDE.md                     # ← this file
├── MacroRippleTracker_Spec_v0.2.docx
├── environment.yml               # conda spec
├── requirements.txt              # pinned deps (python-dotenv, yfinance, gdeltdoc, ...)
├── .gitignore                    # includes `.env` and `data/`
├── .env                          # gitignored — NEWSAPI_KEY, ANTHROPIC_API_KEY (present as of Session 2)
├── .env.example                  # committed template — same keys, empty values
├── config.py                     # EventConfig pydantic + load_event(); calls load_dotenv() at import
├── data_market.py                # M2 (download_prices, get_price_on_date, get_price_changes, get_price_range)
├── data_news/                    # M1 news package
│   ├── __init__.py               # empty; populated in Task 10 (retrieve() public API)
│   └── gdelt.py                  # gdelt.fetch(cfg) — GDELT 2.0 fetcher
├── events/
│   └── iran_war.yaml             # reference event config
├── data/                         # runtime, gitignored (does not exist yet in repo)
├── docs/
│   ├── progress.md               # session log
│   └── superpowers/plans/
│       ├── 2026-04-16-plan-1-data-foundation.md
│       ├── 2026-04-16-plan-2-agents.md
│       └── 2026-04-16-plan-3-ui-eval.md
└── tests/
    ├── __init__.py               # empty
    ├── conftest.py               # fixtures_dir, tmp_data_dir
    ├── test_config.py            # 3 tests, passing
    ├── test_data_market.py       # 5 tests, passing (3 from Task 3 + 2 from Task 4)
    ├── test_gdelt.py             # 2 tests, passing (Task 5)
    └── fixtures/
        ├── yf_brent_sample.csv   # sample OHLCV for M2 tests
        └── gdelt_response.json   # sample GDELT articles for Task 5 tests
```

**Commits on `main` at end of Session 2 (most recent first):** `b15ba33` → `c3e8fc0` → `60df2ee` → `b4e9fbe` → `d6a9519` → `178f0d0` → `1c5d7ed` → `77bfd0b` → `70e5bc9` → `1a4638a`.

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

## Conventions Established in Tasks 1–5

### Python

- **Type hints always** on public function signatures. `Optional[T]` for nullable returns. Use `date` (not `datetime`) for calendar dates.
- **pydantic v2 syntax**: `model_validator(mode="after")` for cross-field validation (example in `config.py`). Do not mix in v1 syntax.
- **No comments** unless the *why* is non-obvious. In Tasks 1–5, the only committed comments explain (a) the weekend gap in a market data test, (b) why `config.py` calls `load_dotenv()` at import time, and (c) why the GDELT test introspects `query_params` instead of named attrs. If you add a comment, it should be in the same "explain a non-obvious invariant" register.
- **`DATA_DIR` env var** isolates the runtime data directory (`data/` by default). Every module that reads/writes files under `data/` **must** resolve via `Path(os.environ.get("DATA_DIR", "data"))` — the `tmp_data_dir` pytest fixture depends on this for isolation.

### Filenames / ticker sanitization

CSVs under `data/prices/` are named via `symbol.replace("=", "_").replace("^", "").replace("/", "_")`. So `BZ=F` → `BZ_F.csv`, `^GSPC` → `GSPC.csv`. Any future code that reads these must use the same sanitization (helper is `data_market._csv_path`).

### Error handling

- **Trust internal contracts.** No try/except wrappers around calls to our own modules.
- **Validate at config boundaries.** `EventConfig` raises `ValueError` with specific messages; `load_event()` raises `FileNotFoundError`. Tests assert on the exception type AND message substring.
- **Fail loud on missing data files** only where it matters (e.g., `get_price_on_date()` returns `None` for a missing CSV or missing date — it's a *query*, not a pipeline step).
- **Silent-skip on missing external credentials** where a fetcher is opt-in. Convention: `data_news.newsapi_fetcher.fetch(cfg)` returns `[]` if `NEWSAPI_KEY` is unset. This keeps the `setup.py` orchestrator resilient when the free-tier quota is exhausted or a user is running without a key.

### Tests

- File: `tests/test_<module>.py`, mirroring source filename.
- **Mock external APIs** at the module boundary via `monkeypatch.setattr(module.yf, "download", fake_download)` — never patch the library globally. Pattern also applied in Task 5: `monkeypatch.setattr(gdelt, "GdeltDoc", lambda: FakeGdeltDoc())`.
- **One fact per test.** Test names read like the assertion: `test_baseline_before_start`, not `test_config`.
- **Assert on the library's real surface, not a plan's imagined surface.** If the plan's test text asserts `f.keyword`, verify at the REPL that the pinned library version actually exposes `.keyword` before writing that assertion. When it doesn't, rewrite the test to use what's real (see `Filters.query_params` case in Task 5). Do NOT decorate the production object with phantom attrs to make the plan's assertion pass.
- Live integration tests live in `tests/test_*_live.py` and are gated via `pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", ...)`.

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

### `newsapi-python==0.2.7` (not yet integrated; Task 6)

- `NewsApiClient(api_key=str)`. `.get_everything(...)` returns a **plain dict** `{"status", "totalResults", "articles"}`. Safe to introspect — no opaque wrapper objects.
- Free tier: 100 requests/day, no historical access beyond ~30 days. If Plan 1 runs a live smoke past the quota, `get_everything` raises `NewsAPIException` with HTTP 429. Wrap the live call (not the mocked unit tests) accordingly.
- Convention: `fetch(cfg)` returns `[]` if `NEWSAPI_KEY` unset (don't raise). Unit tests `monkeypatch.delenv("NEWSAPI_KEY", raising=False)` to exercise this path.

### `pydantic==2.9.2`

- `model_validator(mode="after")` is the v2 idiom; `@root_validator` is v1 and will break. Cross-field validation goes in a post-init method, not in individual field validators.
- `@field_validator` is also v2 but not currently used; prefer `model_validator` when you need multiple fields' final values.

### `chromadb==0.5.18` (not yet integrated; Task 10)

- Use `chromadb.PersistentClient(path=str(dir))`. Do NOT use the deprecated `chromadb.Client(Settings(persist_directory=...))`.
- First-run embedding model download (~80 MB for `all-MiniLM-L6-v2`) happens silently; expect a delay on the first `index_articles()` call of a fresh clone.
- `collection.query()` returns a dict with `{documents, metadatas, distances}` each wrapped in a one-element outer list (because the API accepts batch queries). Unpack with `res["documents"][0]`, etc.
- `distance` is cosine distance in `[0, 2]` by default; convert to similarity via `1.0 - distance`.

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

**Corrective workflow when a smell is found:** do NOT amend the subagent's commit. Write a new `refactor(<scope>): ...` or `fix(<scope>): ...` commit that undoes the smell and updates the affected tests. Note the follow-up commit in `docs/progress.md` under the originating task's row. This leaves the history honest — the subagent's first pass is preserved, the correction is visible as a separate act.

## How to Resume

1. `cd /Users/fangyihe/appliedfinance`
2. Read this file (`CLAUDE.md`) and [`docs/progress.md`](docs/progress.md) for what happened last session.
3. Read the active plan file. Next task is listed in `progress.md` under "Next session — exact next step".
4. Sanity-check the environment:
   - `/opt/anaconda3/envs/macro-ripple/bin/pytest -v` → all existing tests passing (10 at end of Session 2).
   - `/opt/anaconda3/envs/macro-ripple/bin/python -c "import config, os; print(bool(os.environ.get('NEWSAPI_KEY')), bool(os.environ.get('ANTHROPIC_API_KEY')))"` → `True True`. If either is `False`, check that `.env` at the repo root has both keys populated (no quotes, no spaces around `=`).
   - `git status --short` → clean. If `.env` appears here as untracked, verify it's still ignored by `.gitignore` (line 7) — do NOT stage it.
5. Start the next task per the mode mapping in "Working Mode". If dispatching a subagent, paste the plan task text inline in the brief — do not hand it the plan file. Include "Library Quirks" entries relevant to the task in the subagent's brief.
6. Before declaring the task done, walk the six Acceptance Criteria plus the Subagent Review Checklist (if applicable).
