---
name: loop-30-max
description: "\"Loop 30 Max\" / \"لف على الـ 30 ماكس\": the deepest EGX scan on ThndrX - positions review, extended news and catalyst search, full scripted check with drawings on every stock, five independent top-model analyst passes per finalist and a verifier, then the allocation and a ThndrX-style HTML report. Very heavy on usage."
---

# Loop 30 Max

Run only when the user says "Loop 30 Max" or "لف على الـ 30 ماكس". It is **loop-30** with every depth setting at maximum. Load **egx-thndrx-trade-check** and **loop-30** first and obey all their rules; where this skill says more, it wins. `$S` = `../egx-thndrx-trade-check/scripts`.

## 0. Before starting
- Ask in one message: **how much to invest now** (required) and the trading day.
- Read Settings (risk %, equity, fees, fixed costs) and `EGX.page().cash`; warn first if the cash is below the amount.
- Warn plainly: this mode deep-checks every stock, runs many extended searches and launches about 40 top-model agents; it can use a large part of the 5-hour and weekly Claude limits. Offer normal **Loop 30**. Continue only after the user confirms.
- Create a task list with the steps below.

## 1. Positions
loop-30 §1 (the check skill's my positions), at full depth for every held stock.

## 2. Market, macro and catalysts
- loop-30 §2 with WebSearch mode **extended** for every query, at least 10 queries over the last 14 days. WebFetch the original disclosure or article for every catalyst kept.
- Macro calendar for the next 5 trading days (CBE rate decision, inflation print, holidays, results season) into `market.macro`.

## 3. Full check on every stock (no quick scan)
For every stock in the universe (official EGX30 with a dated source, else top 30 by market cap, plus catalyst stocks): `await EGX.deep(tk)` (it also runs the **setup history test**), screenshot with `save_to_disk`, news with 2+ searches (extended when standard finds nothing dated in 30 days). Only the main session uses Chrome; agents never open the browser.
Then `EGX.exportRun([...all tickers])` -> `loop30max/datapack-YYYY-MM-DD.json` in the working directory, adding news, catalysts, red events and screenshots per stock.

## 4. Filters
The script's drop reasons (`references/analysis-rules.md`); list every drop.

## 5. Five independent analyst passes on the best 8
- Finalists: loop-30 §5 ranking, best 8.
- Launch **five agents in parallel in one message**, same data pack, different lens. Use `egx-portfolio:egx-analyst` if available, else `general-purpose`. Set `model: "opus"` and `effort: "max"` on every launch (this skill asks for it explicitly).
  1. Trend follower (trend daily/weekly, MAs, RS, breakouts).
  2. Pullback / support trader (zones, touches, candles at support, setup history).
  3. Catalyst and news analyst (catalyst quality, priced in, red events, macro).
  4. Fundamentals and valuation (financial tab values, results trend, valuation, dividend).
  5. Risk manager / devil's advocate (stop noise, gap risk before results, liquidity, regime, fees vs gain, T+2).
- Each returns JSON per ticker: `verdict` (Valid / Wait / Not valid), `confidence` 1-5, 2-3 `facts` with dates from the pack, `change_mind`. Agents judge only from the pack and invent no numbers.
- **Consensus**: ✅ only with at least 4 of 5 Valid AND every ✅ rule of the check skill (including the Down-regime RS rule). 3 of 5 = ⏳. Fewer = ❌. Store the votes in each stock's `votes`.

## 6. Verifier
One more agent (`general-purpose`, `model: "opus"`, `effort: "max"`) that has not seen the analysts' reasoning gets the data pack and `run.json` after `egx.py allocate`. It re-checks R:R, shares, fees, caps and risk against the pack, and that every cited date and link is in the pack, and returns a list of errors. Fix every error; anything that cannot be confirmed becomes unknown and the pick ⏳.

## 7. Allocation, report, answer, log
- `python3 $S/egx.py allocate run.json`, `check`, then `report run.json --out <reports folder> --video` (the HyperFrames recap project; tell the user the render command it prints).
- Answer as loop-30 §7 plus: votes (e.g. 4/5) and chart score per finalist, the risk manager's main objection, the macro items, and a gap-risk line for any pick with results or another red event before the order expires.
- Log one Recommendations row per finalist (Command = Loop 30 Max; Notes = votes, score, shares, amount, report file). Keep the data pack and the agents' JSON next to the report.
