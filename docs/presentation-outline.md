# Presentation Outline — Macro Event Ripple Tracker

**Time budget per professor's guidance:** 4-5 min presentation + 3-4 min demo = ~7-9 min total.

---

## Slide-by-slide

### 1. Title (5s)
- Macro Event Ripple Tracker
- Applied Finance v0.2 · [your name] · 2026-04-29

### 2. Problem (30s)
**Visual:** one-paragraph statement + a small montage / list of headline shrapnel
**Say:**
> "When a major macro event hits — sanctions, a strait closure, an OPEC surprise — analysts need to map second-order ripples across industries within hours, not days. The inputs are scattered: hundreds of news articles, dozens of correlated tickers, a moving sub-event timeline. Doing this by hand is slow and miss-prone. We built an agentic RAG system that turns one event description into a grounded ripple analysis with citations."

### 3. Architecture (45s)
**Visual:** the ASCII diagram from `docs/writeup.md` §2 (or redraw as Mermaid / Excalidraw)
**Say (call out three things):**
- LangGraph supervisor classifies intent → routes to one of four worker agents
- Free-tier corpus only — GDELT (metadata) + NewsAPI (free 100/query); ChromaDB + MiniLM for dense retrieval; everything local & free
- Three-phase ripple generation: structure first, then attach news per node, then attach prices — each phase auditable

### 4. 🎬 LIVE / RECORDED DEMO (3:00-3:30) — see Demo Runbook below

### 5. Evaluation — the iteration story (60s)
**Visual:** the v1 → v6 table from `docs/writeup.md` §4
**Say:**
> "We didn't just measure once. Per Lecture 9 Slide 10's iterative quality-testing emphasis, we ran the eval six times. §9.2 ripple precision climbed from 21.2% to 58.6% — that came entirely from honest fixes: an N:1 scoring bug in the matcher, then a token-overlap fallback for paraphrases. Recall went 58.3% to 75.0%. §9.3 faithfulness 0.55 to 0.60 — the only thing that moved it was refreshing the corpus, which proves it's a corpus-coverage ceiling. §9.1 retrieval precision stayed at 0.76 across all six versions; we proved that's a structural plateau, not a corpus-size or query-phrasing problem."

### 6. Limitations + Next Steps (30s)
**Visual:** two columns, 2-3 bullets each. Lead with the data-layer limitation; everything else is downstream.

**Limitations:**
- **Free-tier APIs only → corpus is headline + ~200 chars, not full articles.** GDELT returns metadata only; NewsAPI free returns 200-char preview capped at 100 results. This is what caps §9.3 faithfulness near 0.60. Lifting it requires either full-text scraping (paywall- and ToS-blocked on major outlets) or a paid API — both excluded by the course rule.
- **Single-event scope.** Wired for the 2026 Iran War; architecture is event-agnostic but only one event is fully populated.

**Say:** "The biggest constraint is structural, not algorithmic — we work over headlines and 200-char previews because GDELT and NewsAPI free don't give us article bodies. Every other limitation in the report is downstream of this one."

**Next Steps (top 3, anchored to spec §11):**
- **More events** — populate 2-3 more `events/*.yaml`, including a historical reference (1979 Iranian Revolution / 1990-91 Gulf War) loaded as few-shot priors at ripple-tree generation time.
- **Multi-event comparison dashboards** — once 2+ events exist, side-by-side comparison shows how sector mechanics shift across crisis types.
- **Full-text article access** (paid API or curated scraping) — the single biggest unblocker for the §9.3 faithfulness ceiling.

**Say:** "The next step is breadth, not retrieval-tuning — the architecture is already event-agnostic, so adding the 1979 and 1990-91 oil shocks as a reference corpus is a YAML-copy plus an ingestion run."

### 7. Q&A (5s + as long as questions take)
**Visual:** repo URL + final eval report path
- `github.com/fangyihe-fordham/macro-ripple-tracker`
- `eval/results/eval-iran_war-20260428-003229.md`

---

## Demo Runbook (target ~3:30)

| Time | Action | What to say |
|---|---|---|
| **0:00-0:15** | `streamlit run ui_app.py` — show full layout | "Single-page dashboard. Sidebar picks event; main has price chart, detail panel, event axis, ripple tree." |
| **0:15-0:50** | Click a significant-move marker on price chart (e.g. Brent on 2026-03-01) | "Each red dot is a >3% daily move. Click → leaf agent retrieves news ±2 days around that date, asks LLM why the move happened. Notice ▲ direction, headline summary, key drivers, ≤3 cited articles linking to source." |
| **0:50-1:20** | Pan to the event axis | "Multi-lane horizontal timeline. Every significant move with its most relevant English-translated headline. Collision suppression keeps it readable even with 20+ events." |
| **1:20-2:10** | Scroll to ripple tree, click a sector node (e.g. Defense / Aerospace) | "LLM-generated ripple tree, depth 3, color-coded by severity. Click a sector → event axis above filters to that sector's news only. So clicking Defense shows defense-specific events on the timeline." |
| **2:10-2:25** | Expand a sub-branch, hover to show mechanism tooltip | "Each node has causal mechanism on hover and supporting news citations under it." |
| **2:25-2:55** | Sidebar chat: ask `"Why did fertilizer prices rise after Hormuz closed?"` | "Supervisor classifies intent — QA query, routed to grounded QA agent. Answer cites snippet URLs." |
| **2:55-3:15** | Same chat, ask `"How did Brent compare to S&P?"` | "Different intent — supervisor classified as 'market', routed to market agent. Numerical answer, zero LLM hallucination." |
| **3:15-3:30** | Click a date with thin coverage to surface fallback reason | "When retrieval finds no nearby news, we surface `no_nearby_news` honestly instead of hallucinating. The limitation has a UI surface." |

**3:30 wrap.**

---

## Pre-demo prep checklist

- [ ] **Day before:** run `python setup.py --event iran_war --refresh` to ensure corpus is fresh and the demo queries (Brent, Defense, Fertilizer) all return rich results.
- [ ] **Day before:** run `python -m eval.run_eval --event iran_war` once to confirm v6 numbers still match the slides; if they don't, regenerate the slide table from the latest report.
- [ ] **2 hours before:** open `streamlit run ui_app.py`, walk the demo end-to-end once, time it. Adjust pacing.
- [ ] **30 min before:** restart Streamlit fresh so cache is clean. Pre-load the dashboard so the audience sees the data immediately when you switch over.
- [ ] **Backup:** record a 3:30 screen-cap (QuickTime → iMovie trim) the night before. If live demo flakes (Anthropic API timeout, browser hiccup), drop in the recording instead. Per professor's note, recorded demo is acceptable.

---

## Anticipated questions + 1-line answers

| Question | Answer |
|---|---|
| Why headline-only? | Course constraint: free APIs only. GDELT returns metadata; NewsAPI free returns 200-char preview. Paid / scraping excluded. |
| Why didn't query rewriting help §9.1? | Rewriter changed query phrasing materially but precision stayed 0.76. Per-query analysis showed the LLM judge strictly enforces `must_be_about` keywords — articles about general "oil prices" got rejected for not naming "Brent" specifically. The bottleneck is judging, not retrieval. |
| Why 12 ground-truth sectors? | Hand-curated from Wikipedia's "2026 Strait of Hormuz crisis" article. Tree generates ~30 at depth 3, so precision is mathematically capped. Expanding truth would lift the number but is evaluator-side tuning. |
| What does an eval run cost? | About $0.5-1.0 in Anthropic API per full run (~50 LLM calls). 3-5 minutes wall clock. |
| Would this generalize to other events? | Yes — every component is YAML-driven. New event = `cp events/iran_war.yaml events/<new>.yaml`, edit keywords + tickers, run `setup.py`. UI auto-discovers events from the directory. |
| Why LangGraph vs a single big prompt? | Routing per intent lets us test each worker in isolation, mock the LLM in unit tests, and keep prompts short enough to stay accurate. The supervisor is 5 nodes; each <50 lines. |

---

## After the presentation

- [ ] Push the slide deck to the repo (`docs/slides.pdf` or similar) for grading appendix.
- [ ] Update writeup if anything in the demo surfaced a real bug worth reporting.
