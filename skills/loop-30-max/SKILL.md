---
name: loop-30-max
description: "\"Loop 30 Max\" / \"لف على الـ 30 ماكس\": the deepest EGX scan on ThndrX - full trade check on every stock, extended news and catalyst search, five independent top-model analyst passes per finalist, and a verifier before the allocation. Very heavy on usage."
---

# Loop 30 Max

Run only when Tarek says "Loop 30 Max" or "لف على الـ 30 ماكس". It is the **loop-30** skill with every depth setting turned to maximum. Load **egx-thndrx-trade-check** and **loop-30** first and obey all their hard rules (never trade, read-only on the account, no private API calls, evidence with dates for every claim, chart + analysis + news mandatory for every verdict, education not advice). Where this skill says more, this skill wins.

## 0. Before starting
- Ask in one message (AskUserQuestion if available): **how much to invest now** (required, never assume), and the trading day it is for.
- Read the trade log **Settings** tab (risk per trade, equity, fees, fixed costs) and the **cash available** in the ThndrX header. If the cash is below the amount, say so first: he must deposit or redeem funds (BWA, BMM, gold) before orders can be placed.
- Warn once, plainly: this mode reads every chart in full, runs many extended web searches and launches about 40 top-model analyst agents; it can use a large part of the 5-hour and weekly Claude limits and take a long time. Offer normal **Loop 30** as the lighter option. Continue only after he confirms.
- Create a task list with the steps below so he can follow progress.

## 1. Universe
- Official EGX30 list with a dated source (WebSearch, mode **extended**); else the top 30 by market cap from the ThndrX heatmap, said clearly.
- Plus every stock found in step 2 with a positive dated catalyst and average daily value traded >= EGP 5 million.

## 2. Market (loop-30 step 2) and catalysts (loop-30 step 2c), at maximum depth
- EGX30 regime, breadth, sector pulse, USD/EGP, exactly as the check skill's step 2b.
- Catalyst scan: use WebSearch mode **extended** for every query, at least 10 queries in Arabic and English over the last 14 days (disclosures, acquisitions, mergers, tender offers, expansions, contracts, licenses, bonus shares, capital increases, buybacks, results, index changes, suspensions). WebFetch the original disclosure or article for every catalyst you keep, and record source, link, publish date, and the price move since that date (% and ATRs).
- Also search the macro calendar for the next 5 trading days (CBE rate decision, inflation print, holidays, results season) and list dated items.

## 3. Full check on every stock (no quick scan)
For **every** stock in the universe, run the complete egx-thndrx-trade-check: price and order book (spread, bid/ask split), time and sales, financial data tab, price band, all chart blocks A-J of step 3 with the chart score, drawings on the ThndrX chart with a saved screenshot, and the news check (at least 2 searches per stock, mode extended when standard returns nothing dated in the last 30 days).
- Also run a **setup history test** in the page with the exported bars (no server calls): over the last 300 bars, find past times price touched the same support zone or made the same setup; count how often the next resistance was reached before the stop within 15 bars. Report hits / tries; under 3 tries = "too few to judge".
- Write each stock's results into a data pack file `loop30max/datapack-YYYY-MM-DD.json` in the working directory: ticker, sector, every number from blocks A-I with its bar dates, plan, chart score, setup history, order book read, financial tab values, news and catalysts with links and dates, red events. Unreadable items are "unknown".
- Keep the browser single-threaded: only the main session uses Chrome. Agents never open the browser.

## 4. Filters
Apply loop-30's drop rules (R:R < 2, thin, stop > 3 ATR, stop < 1 ATR that cannot be widened, target below price, near the limit band, fewer than 60 bars) and list every drop with its one-word reason.

## 5. Five independent analyst passes on the finalists
- Finalists = the best 8 survivors by loop-30's ranking (trend + RS, unpriced catalyst, R:R, distance, chart score).
- Launch **five analyst agents in parallel** in one message, each with the same data pack and a different lens. Use the `egx-portfolio:egx-analyst` agent type if it is available, otherwise `general-purpose`. Set `model: "opus"` and `effort: "max"` on every launch (this skill explicitly asks for it).
  1. **Trend follower**: trend, MAs, relative strength, breakouts.
  2. **Pullback / support trader**: zones, touch counts, candles at support, setup history.
  3. **Catalyst and news analyst**: catalyst quality, whether priced in, red events, macro calendar.
  4. **Fundamentals and valuation**: financial tab values, results trend, valuation vs sector, dividend.
  5. **Risk manager (devil's advocate)**: argue against every pick: stop noise, gap risk before results, liquidity, regime, fees vs expected gain, T+2.
- Each agent gets: the data pack path, its lens, Tarek's rules (risk %, R:R >= 2, caps 30% stock / 50% sector, regime rule), and must return JSON per ticker: verdict (Valid / Wait / Not valid), confidence 1-5, the 2-3 facts it relied on (with dates from the pack), and what would change its mind. Agents judge only from the pack; they must not invent numbers.
- **Consensus**: ✅ only if at least 4 of 5 passes say Valid AND every hard rule in the check skill holds (including the Down-regime relative-strength rule). 3 of 5 Valid = ⏳. Fewer = ❌. Show the vote count per ticker.

## 6. Verifier
Launch one more agent (`general-purpose`, `model: "opus"`, `effort: "max"`) that has not seen the analysts' reasoning. Give it the data pack and the draft allocation. It recomputes R:R, share counts, fees, caps and risk from the pack, checks every cited date and link is in the pack, and returns a list of errors. Fix every error before answering; if a number cannot be confirmed, mark it unknown and downgrade that pick to ⏳.

## 7. Allocation and costs
Exactly as loop-30 steps 5 and 6 (risk % from Settings, caps, EGP 2,500 minimum order, half-deploy suggestion in Correction or Down that Tarek may override, cash with reason, costs to cover and the monthly break-even hurdle). Add a **gap-risk line** for any pick with results or another red event before the order expires.

## 8. Answer (Egyptian Arabic, phone-sized first, details after)
1. One-line market regime with numbers, plus the macro calendar items for the trading day.
2. Top catalysts (3-5) with source, date and priced-in status.
3. Allocation table: ticker, verdict, votes (e.g. 4/5), chart score, shares, EGP, entry, stop, target, R:R, risk EGP.
4. Cash left and why; costs to cover.
5. Per finalist: the short analysis block (check skill block J), the five votes in one line each, the risk manager's main objection, and the chart screenshot (send with SendUserFile).
6. Exact ThndrX order steps for each ✅ and each ⏳ he may place as a limit order (he types them himself).
7. Dropped stocks grouped by reason.
8. Closing line: analysis, not investment advice; the decisions and the orders are Tarek's.

## 9. Log
Append one Recommendations row per finalist (Command = Loop 30 Max) to the trade log as the check skill's Trade log section says; Notes = votes, chart score, allocated shares and amount. Never write formula columns. Save the data pack and the agents' JSON next to it so the run can be audited later.
