# Presentation Speaker Script — Plain English

> **Total budget:** ~4-5 min slides + 3-4 min demo = ~7-9 min.
> **How to use this:** Read it out loud once. Time yourself. Adjust pacing on the bits that feel slow or fast.

---

## Slide 1 — Title (5 seconds)

> "Hi, I'm [your name]. My project is the **Macro Event Ripple Tracker**. It's an AI system that takes one big news event and shows you, in seconds, all the ways it ripples through markets."

*(click to next slide)*

---

## Slide 2 — Problem (30 seconds)

> "Here's the problem. When something big happens — like Iran closing the Strait of Hormuz this past March — an analyst needs to figure out, very fast, which industries get hit and which prices move.
>
> But the information is everywhere. Hundreds of news articles. Dozens of related stocks and commodities. A moving timeline of sub-events. Doing this by hand takes days, and you can still miss a ripple.
>
> So I built a system that does it in seconds."

*(click)*

---

## Slide 3 — Architecture (45 seconds)

> "Here's how the system is built.
>
> A user types a question into the chat. The **supervisor** — this is built on LangGraph — figures out what kind of question it is: a fact lookup, a market check, a timeline request, or a full ripple analysis. Then it routes to the right specialized agent.
>
> The data layer behind it: news from **GDELT and NewsAPI free tier**, embedded into ChromaDB using a local sentence-transformer. Market data from yfinance. **Everything is free, everything runs locally**, except for the Claude Sonnet model itself.
>
> One design choice I'll flag: the ripple tree is built in **three phases**. First, Claude generates the structure. Then we attach news citations to each node from the vector index. Then we attach actual market data. So every claim in the tree is grounded — not invented."

*(click — switch to Streamlit app for demo)*

---

## Slide 4 — LIVE DEMO (3 to 3.5 minutes)

**Setup:** Have `streamlit run` already open in another window. Cache should be cleared so the demo runs cleanly.

### 0:00 – 0:15 — orient the audience

> "OK, this is the dashboard. Sidebar on the left lets you pick the event. The main area is split into a **price chart**, an **event timeline**, and the **ripple tree** at the bottom. Let me walk you through how an analyst would use this."

### 0:15 – 0:50 — click a price marker

*(click a red dot on the Brent chart, e.g. early March)*

> "Each red dot on this Brent crude chart is a day where price moved more than 3%. I'll click this one — March 1st.
>
> The panel on the right just kicked off an AI agent. It pulled up news from a few days around March 1st and asked Claude to explain why Brent jumped. We get back the direction — up — a one-line summary, the key drivers, and three news articles linked to the original source. So I can verify every claim."

### 0:50 – 1:20 — point at the event axis

> "Below the price chart is the **event timeline**. Each marker is a day with a significant move. We automatically translate non-English headlines into English and place them on different lanes so the labels don't overlap. So an analyst can scan the entire window in one glance."

### 1:20 – 2:10 — click a ripple tree node

*(scroll to ripple tree, click 'Defense / Aerospace')*

> "Now this is the **ripple tree**. Claude generated this from the event description — three levels deep, color-coded by severity. Red is critical, orange is significant, yellow is moderate.
>
> Watch what happens when I click 'Defense / Aerospace.' The timeline above just **refiltered** — now it's showing only the news related to the defense ripple. So I can see exactly which days had defense-relevant news driving that branch of the tree."

### 2:10 – 2:25 — show node details

*(hover, expand a sub-branch)*

> "Each node also shows the causal mechanism on hover, and the supporting article citations underneath."

### 2:25 – 2:55 — chat: QA query

*(in sidebar chat, type: "Why did fertilizer prices rise after Hormuz closed?")*

> "Now let me try the chat. I'll ask: *Why did fertilizer prices rise after Hormuz closed?*
>
> The supervisor classifies this as a Q&A query, routes it to the grounded QA agent — and we get an answer **with citation links to the actual source articles**. So nothing the model says is unverifiable."

### 2:55 – 3:15 — chat: market query (different intent)

*(type: "How did Brent compare to S&P this week?")*

> "Same chat box, different question. *How did Brent compare to S&P this week?*
>
> This time the supervisor routes to the market agent. Pure numbers, no LLM hallucination — it just reads the price CSVs and summarizes."

### 3:15 – 3:30 — surface the honest fallback

*(click a date with no nearby news coverage)*

> "And finally — let me click on a date with very thin news coverage. See? Instead of making something up, the system honestly surfaces *'no nearby news.'* **This is the limitation surface, not a bug.** The system tells you when it can't help, instead of inventing an explanation."

*(switch back to slides)*

---

## Slide 5 — Evaluation (60 seconds)

> "I didn't just measure quality once. I ran the evaluation **six times** — call them version 1 through version 6 — and each iteration is a separate commit in the repo.
>
> Version 1 had ripple sector precision at **21 percent**. I found a scoring bug in the matcher, fixed it, jumped to 37 percent. Then I noticed the matcher was missing obvious paraphrases — like 'Industrial Metals & Materials' should match 'Aluminum / energy-intensive metals.' I added a token-overlap fallback, and precision jumped to **48 percent**. Then I refreshed the news corpus from 1000 articles to 1400 articles. That's what pushed QA faithfulness from 0.55 to **0.60** — the first real movement on faithfulness across all six versions.
>
> Final version 6: ripple precision 58.6 percent, recall 75 percent, faithfulness 0.60, market checks 5 out of 5.
>
> One number didn't move: **retrieval precision stayed at 0.76 across all six versions.** I tried query rewriting — didn't help. That told me the bottleneck isn't retrieval, it's how strict our LLM judge is. So I documented that as a structural plateau in the limitations section."

*(click)*

---

## Slide 6 — Limitations + Next Steps (30 seconds)

> "The biggest limitation isn't algorithmic — it's **structural**.
>
> The free APIs we're allowed to use — GDELT and NewsAPI's free tier — only give us **headlines and 200-character previews**, not full article text. That's what caps QA faithfulness around 0.60. Every other limitation is downstream of this one.
>
> For next steps: the architecture is already event-agnostic, so the natural next move is **breadth, not retrieval-tuning**. Adding more events is a YAML copy plus an ingestion run. The 1979 Iranian Revolution and the 1990-91 Gulf War are obvious historical references — same kind of oil shock, very different geopolitical setup. Comparing across them is the v0.3 deliverable."

*(click)*

---

## Slide 7 — Q&A (5 seconds + however long)

> "That's it. Code is at github.com/fangyihe-fordham/macro-ripple-tracker. Final eval report and writeup are in the docs folder. Happy to take questions."

---

## If you only have 30 seconds for Q&A — three highest-likelihood questions

**"Why didn't you use TruLens / a framework like RAGAS?"**
> "TruLens is a production monitoring tool for systems with live users. We're a v0.2 demo with no live traffic. Plus, two of our four eval dimensions — ripple sector matching and market price spot-checks — are domain-specific. No framework has built-in support for those, so we'd be writing custom feedback functions either way. The LLM-as-judge pattern we use is the same one TruLens uses internally."

**"Why is the corpus only headlines?"**
> "Course constraint — free data sources only. GDELT returns metadata, NewsAPI free returns 200-character previews. Full-text scraping hits paywalls and ToS issues on major outlets. We documented this as the primary limitation."

**"Could this generalize to other events?"**
> "Yes. Every event-specific knob — keywords, tickers, date windows — lives in a YAML file. New event is `cp events/iran_war.yaml events/<new>.yaml`, edit, run setup. The UI auto-discovers events from the directory. Multi-event support is the v0.3 next step."

---

## Pacing tips

- The demo is the **biggest single block** of your time. If you go over on demo, **cut something from the demo, not from slides 5-6**. Slide 5 is the evaluation story which is the highest-grading-weight content.
- If the live demo flakes (Streamlit cache, API timeout), **switch to the pre-recorded backup video immediately** — don't try to debug live.
- If you finish under 4 minutes on slides, **don't fill** — just open Q&A early. A short, tight presentation is better than padded.
- Practice the **transition between demo and slide 5** specifically. That's where most students lose 5-10 seconds fumbling with screen sharing.
