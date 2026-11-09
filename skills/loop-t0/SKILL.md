---
name: "loop-t0"
description: "\"Loop T0\" / \"لف T0\": intraday (same-session, T+0) EGX scan on ThndrX — finds buy-and-sell-today setups on T+0-eligible stocks, sizes them from the user's amount, exit by 14:20. Use only when the user names it."
---

# Loop T0 (intraday, same-session trades)

Run only when the user says "Loop T0" or "لف T0". Load **egx-thndrx-trade-check** first and obey all its hard rules (never trade or touch the order ticket/orders, read-only on the account, no private API calls, no login work, evidence with times and dates, education not advice). Where this skill says something different, this skill wins.

## What T+0 means here
- Same-session trading: buy and sell the same stock in the same session. Since 2026-02-01 (EGX market-segment review, Mondo Visione 2026-01-28) securities on the **Most Active** and **Medium Activity** boards (and the SMEs "Tamayuz" list) are eligible for intraday and T+1 trading. The EGX updates the segments periodically, so treat eligibility as **unknown until confirmed** for each stock: a dated EGX segment list, or the user seeing the T0 option in ThndrX for that stock (بيع ← طلب بسعر محدد متقدم ← T0).
- Everything bought in this loop must be sold the same session. No position is carried overnight unless the user says so in chat.

## 0. Before starting (one message, AskUserQuestion if available)
- The amount for this run (required) and the **risk % of that amount** per trade (suggest 2%; allowed 1-10%). Risk budget = amount x risk%, fees included.
- Check the clock (Africa/Cairo). Session 10:00-14:30, Sunday-Thursday. **No new entries after 13:30**; if it is later, give analysis only. If before 10:15, wait for the first 15 minutes of trading (opening noise) and say so.
- Warn once: intraday needs the user watching ThndrX until the trade is closed; a plan older than ~15 minutes is stale.
- **Daily brake:** if a Loop T0 trade already hit its stop today (Trades tab, Source = Loop T0, Closed = today, loss), give analysis only for the rest of the day.

## 1. Universe
- T+0-eligible stocks with average daily value traded >= **EGP 20 million** (20 days) and today's value traded so far on pace for that. Start from the ThndrX heatmap / الأكثر نشاطًا list plus the user's watchlist; at most ~20 names.
- Drop: spread > 0.3%, price in the last 3% of the daily limit band, trading suspension or results/ex-date today, fewer than 60 daily bars.

## 2. Market context (fast)
EGX30 daily regime as in the check skill, plus intraday: EGX30 on 5-minute bars vs its session VWAP. Longs only (no short selling). If EGX30 is below its VWAP and falling, require the stock to be above its own VWAP and stronger than EGX30 today.

## 3. Intraday scan, every stock
Read with the chart's own export (page data, no server calls): today's **5-minute** bars (switch the chart resolution with the chart widget, then switch back to 1D) and the last 60 daily bars. Compute: session VWAP, opening range (first 30 min high/low), 5-min ATR(14), 5-min RSI(14), volume vs the same time of day average if available (else vs 20-day average per minute), today's change vs EGX30, nearest daily support/resistance.
Setups (pick at most one per stock):
- **Opening-range breakout:** a 5-min close above the opening-range high on rising volume, price above VWAP. Entry on a retest of the range high; stop under the range high minus 0.3 x ATR5 or under VWAP, whichever is tighter but >= 1 x ATR5.
- **VWAP pullback:** stock above VWAP most of the session, pulls back to VWAP and holds (5-min close back above). Entry near VWAP; stop 1-1.5 x ATR5 under VWAP.
- **Daily-support bounce:** price at a daily support zone with a 5-min reversal candle and buying in time & sales. Stop under the zone.
Target: the nearer of the day's high / next daily resistance / 2R. Require **R:R >= 2 gross and >= 1.5 after round-trip fees**, and the expected move to target must be at least **3x the round-trip fee %** (fees are about 0.35% + EGP 6 per round trip: compute from Settings). Drop and name the reason otherwise.

## 4. Deep check, top 3
For the best 3: order book (bid/ask split, spread, depth at entry), time & sales (are the last prints buyers or sellers, large or small), one news search each for today (Arabic + English: results, disclosures, suspensions), chart drawings on the 5-min chart (VWAP, range high/low, entry, stop, target) and a saved screenshot sent with SendUserFile. Verdict ✅ / ⏳ (with the exact trigger, e.g. "5-min close above 13.55") / ❌.

## 5. Size and plan
Shares = floor( risk budget / ((entry - stop) + round-trip fees per share) ), capped by the amount and the cash the user says he will use, and by 30% of total equity. One trade at a time; at most 2 trades per day. Every plan has: entry, stop, target, R:R gross/net, shares, EGP, loss at stop with fees, gain at target with fees, and a **time exit: sell at market by 14:20 whatever happens**.

## 6. Answer (Egyptian Arabic, phone-sized, title "T0 نفس الجلسة")
1. Clock time of the data and EGX30 daily regime + intraday vs VWAP.
2. Table: ticker, verdict, setup, entry, stop, target, R:R, shares, EGP, loss at stop.
3. ThndrX steps the user types himself: buy as a limit order (أمر بسعر محدد) valid today; to exit the same day: بيع ← طلب بسعر محدد متقدم ← تسوية T0 ← price ← quantity. If ThndrX does not offer a stop order on T0 shares, say so and tell him to set price alerts at the stop and target and to exit manually; never pretend a stop exists.
4. What cancels the idea (e.g. EGX30 breaks its VWAP, stock closes a 5-min bar under the stop level).
5. Dropped stocks grouped by reason.
6. Closing line: analysis, not investment advice; the decisions and the orders are the user's.

## 7. Log
Recommendations rows (Command = Loop T0) for the deep-checked picks, Notes = setup, time of the data, shares. When the user says he bought/sold, log in Trades with Source = Loop T0 as the check skill says; Exit reason Target / Stop / Time (14:20) / Manual. Outcome tracking for Loop T0 rows uses that day's 5-minute bars only; anything not hit by 14:20 is "Time exit".