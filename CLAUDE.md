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
- **Data:** `yfinance`, `pandas`, `pyyaml`, `pydantic` v2
- **News:** `gdeltdoc`, `newsapi-python`, `feedparser`
- **Dedup:** `datasketch` (MinHash LSH)
- **Vector store:** `chromadb` (persistent, local) + `sentence-transformers` (`all-MiniLM-L6-v2`, local, free)
- **Agents:** `langchain-anthropic` + `langgraph` + `claude-sonnet-4-6` via `ANTHROPIC_API_KEY` (not yet obtained; required before Plan 2 Task 1)
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

## Current Directory Structure (real, post-Task 3)

```
/Users/fangyihe/appliedfinance/
├── CLAUDE.md                     # ← this file
├── MacroRippleTracker_Spec_v0.2.docx
├── environment.yml               # conda spec
├── requirements.txt              # pinned deps
├── .gitignore
├── config.py                     # EventConfig pydantic + load_event()
├── data_market.py                # M2 (download_prices, get_price_on_date)
├── events/
│   └── iran_war.yaml             # reference event config
├── data/                         # runtime, gitignored (does not exist yet)
├── docs/
│   ├── progress.md               # session log (see below)
│   └── superpowers/plans/
│       ├── 2026-04-16-plan-1-data-foundation.md
│       ├── 2026-04-16-plan-2-agents.md
│       └── 2026-04-16-plan-3-ui-eval.md
└── tests/
    ├── __init__.py               # empty
    ├── conftest.py               # fixtures_dir, tmp_data_dir
    ├── test_config.py            # 3 tests, passing
    ├── test_data_market.py       # 3 tests, passing (Task 4 will add 2 more)
    └── fixtures/
        └── yf_brent_sample.csv   # sample OHLCV for M2 tests
```

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

## Conventions Established in Tasks 1–3

### Python

- **Type hints always** on public function signatures. `Optional[T]` for nullable returns. Use `date` (not `datetime`) for calendar dates.
- **pydantic v2 syntax**: `model_validator(mode="after")` for cross-field validation (example in `config.py`). Do not mix in v1 syntax.
- **No comments** unless the *why* is non-obvious. In Tasks 1–3, none of the committed files have docstrings beyond a single module-level string. Follow this.
- **`DATA_DIR` env var** isolates the runtime data directory (`data/` by default). Every module that reads/writes files under `data/` **must** resolve via `Path(os.environ.get("DATA_DIR", "data"))` — the `tmp_data_dir` pytest fixture depends on this for isolation.

### Filenames / ticker sanitization

CSVs under `data/prices/` are named via `symbol.replace("=", "_").replace("^", "").replace("/", "_")`. So `BZ=F` → `BZ_F.csv`, `^GSPC` → `GSPC.csv`. Any future code that reads these must use the same sanitization (helper is `data_market._csv_path`).

### Error handling

- **Trust internal contracts.** No try/except wrappers around calls to our own modules.
- **Validate at config boundaries.** `EventConfig` raises `ValueError` with specific messages; `load_event()` raises `FileNotFoundError`. Tests assert on the exception type AND message substring.
- **Fail loud on missing data files** only where it matters (e.g., `get_price_on_date()` returns `None` for a missing CSV or missing date — it's a *query*, not a pipeline step).

### Tests

- File: `tests/test_<module>.py`, mirroring source filename.
- **Mock external APIs** at the module boundary via `monkeypatch.setattr(module.yf, "download", fake_download)` — never patch the library globally.
- **One fact per test.** Test names read like the assertion: `test_baseline_before_start`, not `test_config`.
- Live integration tests live in `tests/test_*_live.py` and are gated via `pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", ...)`.

### yfinance specifics

- `start` is inclusive, `end` is exclusive — always pass `end_date + timedelta(days=1)` when we want end-date data.
- Fetch window: `baseline_date - 7 days` through `end_date + 1` (pre-event buffer for chart context).

### Running commands

- Use `/opt/anaconda3/envs/macro-ripple/bin/python` and `.../bin/pytest` directly. Shell state does not persist between Bash tool calls, so `conda activate` does not carry.

## How to Resume

1. `cd /Users/fangyihe/appliedfinance`
2. Read this file (`CLAUDE.md`) and [`docs/progress.md`](docs/progress.md) for what happened last session.
3. Read the active plan file. Next task is listed in `progress.md`.
4. Verify env: `/opt/anaconda3/envs/macro-ripple/bin/pytest -v` → should show all existing tests passing.
5. Start the next task per the mode mapping above.
