---
name: "loop-t0-max"
description: "\"Loop T0 Max\" / \"لف T0 ماكس\": the deepest intraday (T+0) EGX scan — Loop T0 plus five parallel analyst passes and a verifier, under a 25-minute time budget. Very heavy on usage. Use only when the user names it."
---

# Loop T0 Max (intraday, maximum depth)

Run only when the user says "Loop T0 Max" or "لف T0 ماكس". It is **loop-t0** at maximum depth. Load **egx-thndrx-trade-check** and **loop-t0** first and follow every step and hard rule of theirs (never trade, read-only on the account, no private API calls, no login work, evidence with times, education not advice, longs only, exit by 14:20, no new entries after 13:30, daily brake). Where this skill says more, this skill wins.

## 0. Before starting
- Same questions as loop-t0 (amount, risk % of the amount).
- Warn once: this mode launches six top-model agents and uses a large part of the 5-hour and weekly Claude limits; intraday prices move while it runs, so it has a **25-minute time budget** from start to answer. Offer normal **Loop T0** as the faster option. Continue only after he confirms.
- If the clock is after **13:00**, say there is not enough time for Max before the 13:30 entry cut-off and offer Loop T0 instead.
- Create a task list so he can follow progress.

## 1. Universe and scan at full depth
- Every T+0-eligible stock with average daily value >= EGP 20 million (not capped at 20 names), plus any stock with a dated disclosure today (results, contract, acquisition, buyback) that is T+0-eligible.
- Run loop-t0 step 3 on all of them, plus: 15-minute bars as a second timeframe, today's relative volume by time of day, and a **setup history test** on the last 20 sessions of 5-minute bars (how often the same setup reached 2R before the stop within the same session; under 5 tries = "too few to judge").
- Write a data pack `loopt0max/datapack-YYYY-MM-DD-HHMM.json` with every number, its bar times, the plan, order-book and time & sales reads, news with links and times, and the clock time of each read.

## 2. Five analyst passes on the best 5
Launch five agents **in parallel in one message** (`egx-portfolio:egx-analyst` if available, else `general-purpose`; `model: "opus"`, `effort: "max"`), each with the same data pack and one lens, judging only from the pack:
1. **Momentum / VWAP:** opening range, VWAP position, 5- and 15-minute trend, relative strength vs EGX30 today.
2. **Order flow:** order-book split and depth, spread, time & sales (size and side of recent prints), whether the entry level has real bids.
3. **News and catalysts today:** dated disclosures, whether the move is already priced in (move since the news in ATR5), red events today.
4. **Market and sector context:** EGX30 intraday vs VWAP, sector move today (نبض القطاعات), breadth.
5. **Risk manager (devil's advocate):** stop vs 5-minute noise, fees vs expected move, slippage, time left in the session, no-stop risk on T0 shares, the daily brake.
Each returns JSON per ticker: verdict (Valid / Wait / Not valid), confidence 1-5, 2-3 facts with clock times from the pack, the trigger that would make it Valid, what would change its mind. Agents cannot write files: collect their JSON from their final messages and save it next to the pack.
- **Consensus:** ✅ only if at least 4 of 5 say Valid AND every loop-t0 hard rule holds. 3 of 5 = ⏳ with the trigger. Fewer = ❌. Show the vote count.

## 3. Verifier
One more agent (`general-purpose`, `model: "opus"`, `effort: "max"`) that has not seen the analysts' reasoning recomputes R:R gross/net, shares, fees, loss at stop, the 14:20 time exit and the 13:30 cut-off from the pack, and checks every cited time and link. Fix every error before answering.

## 4. Price re-check before answering
Re-read the last price and order book of every ✅/⏳ pick right before writing the answer. If the price moved more than 0.5 x ATR5 past the entry, or the trigger already fired and ran more than 1R, mark the plan stale (⏳ "re-plan") rather than chasing.

## 5. Answer and log
- Same layout as loop-t0 step 6, title "T0 ماكس نفس الجلسة", plus the vote count per ticker, the risk manager's main objection, and the clock time of the last price check.
- Log as loop-t0 step 7 with Command = **Loop T0 Max**. Save the data pack, agent JSON and verifier output under `loopt0max/`.
- Closing line: analysis, not investment advice; the decisions and the orders are the user's.