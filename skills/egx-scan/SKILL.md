---
name: egx-scan
description: "EGX many-stock scan on ThndrX, one skill with modes: Scan / \"لف على الـ 30\" (strict: positions, catalysts, top 30, best 5, allocation), Scan Max / \"لف على الـ 30 ماكس\" (full analysis, best 3 ranked A/B/C), Scan Spec / \"مضاربة\" (looser speculation rules) and Scan T0 / \"لف T0\" (same-session); modes combine. The old names Loop 30, Loop 30 Max, Loop 30 Spec, Loop T0 and Loop T0 Max map to these modes."
---

# EGX Scan

One skill for every multi-stock scan. Load **egx-check** first and obey all its hard rules (never trade or touch the order ticket/orders, read-only on the account except chart drawings, no login work, no private API calls, evidence with dates for every claim, chart + analysis + news for every verdict, education not advice). Use its setup (§0: config, Settings, the `EGX` page script, `EGX.market()`), its per-stock check (§1), positions (§3), trade log (§4) and report/run-file rules. `$S` = `../egx-check/scripts`.

**Scripts first:** levels, plans, drops and chart scores come from `EGX.scan(tk)` / `EGX.deep(tk)` (rules in `egx-check/references/analysis-rules.md`); sizing, fees and the HTML report come from `python3 $S/egx.py allocate|check|report run.json`. Claude adds news, fundamentals, grades and judgement, and never re-derives levels by hand.

## Commands and modes

| the user says | Mode |
|---|---|
| **Scan** | Normal swing scan: top 30 + catalysts, quick scan, deep check on the best 5, strict verdicts, allocation. |
| **Scan Max** | Same universe at full depth: every stock gets the full check (technical, fundamental, chart drawing), five analyst passes score the best 8, a verifier checks the numbers, and the answer is **always the best 3 ranked** with A/B/C grades. |
| **Scan Spec** | Speculation rules on top of Scan (or Scan Max if both words are used): relaxed grades, entries near price, risk % of the run amount, 10-trading-day time stop. |
| **Scan T0** | Same-session (T+0) intraday scan. Add **Max** for the five-pass version. Spec does not apply to T0 (T0 is already speculation). |

- Old names still work: Loop 30 = Scan, Loop 30 Max = Scan Max, Loop 30 Spec = Scan Max Spec, Loop T0 = Scan T0, Loop T0 Max = Scan T0 Max.
- Modes combine: "Scan Max Spec" = Max depth with Spec rules; "Scan T0 Max" = intraday at Max depth.
- Title every answer with the exact mode used and log it as the Command / Source (e.g. `Scan Max Spec`), so the monthly report can compare modes. Spec answers carry "مضاربة" in the title so they are never mistaken for a strict result.
- When a section below is marked **[Max]**, **[Spec]** or **[T0]**, it applies only in that mode.

## Shared rules (all modes)

### Before starting (one message, AskUserQuestion if available)
- **The amount for this run** (required, never assume) and the trading day (default: the next EGX session, Sunday-Thursday). If the user says to ignore the wallet cash, use the amount he gives; otherwise read `EGX.page().cash` and say first if it is lower (deposit or redeem funds such as BWA / BMM).
- Warn once (all swing modes): a scan reads 30+ charts and takes a while.
- **Risk per trade:**
  - Scan / Scan Max: risk % from the Settings tab, as a % of total equity (Settings: Equity, Risk per trade).
  - **[Spec]** and **[T0]**: ask the risk % for this run (Spec suggests 3%, T0 suggests 2%; allowed 1-10%). It is a **% of the run amount, not of equity**: risk budget = amount x risk%, fees included. If he picks more than 5%, show once what 5 losses in a row do to the amount: amount x (1 - risk)^5 (10% -> -41%, e.g. 3,710 -> 2,191).
- **[Max]** Warn once: this mode reads every chart in full, runs many extended searches and launches six top-model agents; it can use a large part of the 5-hour and weekly Claude limits. Offer the mode without Max. Continue only after he confirms.
- **[Spec] Monthly brake:** if this month's net P/L (Monthly tab) is at or below -15% of the month's starting capital, say so, give analysis only (no funded picks) until he says otherwise in chat. Monthly tab unreadable = say the brake could not be checked.
- Read Settings for fees, fixed costs, equity and risk; use them over any number written here.
- Create a task list when the run has more than a few steps.

### Safety drops (every mode, never relaxed)
R:R under 2 gross (Spec: also under 1.6 net of fees; T0: under 1.5 net; net R:R = `gain_if_target` / `loss_if_stop` from `egx.py allocate`, never by hand), average daily value traded too thin (swing: < EGP 5M; T0: < EGP 20M), stop more than 3 ATR away, stop under 1 ATR that cannot be widened, target below price, price inside the last 2% (T0: 3%) of the daily limit band, fewer than 60 daily bars (new listing), trading suspension. List every drop with a one-word reason.

### Sizing
Done by `egx.py allocate` only. Shares = floor( risk budget / (entry - stop) ), then capped by the run amount (and cash after buy fees, unless told to ignore it), 30% of total equity per stock, 50% per sector, and the EGP 2,500 minimum order (swing). The fees are added afterwards in `loss_if_stop`; if that is above the risk budget, reduce the shares by one until it is not and say so.
- **`meta.risk_pct` for [Spec] and [T0]:** `allocate` always takes the risk budget from equity when `meta.equity` is set. So write `meta.risk_pct` = run amount x chosen risk% / equity (e.g. amount 3,710, 3%, equity 50,858 -> 0.2188) and put the chosen % in `meta.notes`; check that `allocation.risk_budget_per_trade` = amount x risk%. Say which limit set the share count; if the loss at stop is already under the risk budget at the cash-capped size, say plainly that the risk % did not change anything.

### Costs to cover
Round-trip Thndr fees for the plan, fixed monthly costs (Settings), the monthly return needed on the run amount just to break even, and net gain at target vs net loss at stop. Say plainly when the hurdle is unrealistic for the amount.

### Answer basics
Egyptian Arabic, phone-sized first, details after; numbers and tickers in Latin digits. Exact ThndrX steps for every pick he may place (he types them himself). Every pick gets its drawn chart screenshot (SendUserFile). Closing line: analysis, not investment advice; the decisions and the orders are the user's.

## A. Swing modes (Scan, Scan Max, Scan Spec)

### A1. Universe
- Official EGX30 list with a dated source (WebSearch); if none, the 30 largest by market cap from the ThndrX heatmap, said clearly as "top 30 by market cap".
- Plus every stock with a positive dated catalyst in the last 7 days (**[Max]** 14 days) and average daily value >= EGP 5M, marked "catalyst".

### A2. Market and catalysts
- egx-check §2 (market) once: `EGX.market()` (EGX30 regime and the relative-strength base) and `EGX.marketPage()` on the market page (breadth, sector pulse, USD/EGP, heatmap order).
- Catalyst scan (mandatory): WebSearch standard (extended only if standard returns nothing dated) over the last 7 days, English and Arabic, e.g. "EGX disclosure acquisition", "EGX merger", "tender offer EGX", "عرض شراء إجباري البورصة المصرية", "استحواذ البورصة المصرية", "اندماج شركة مقيدة", "توسعات مصنع جديد البورصة", "توزيع أسهم مجانية", "عقد جديد شركة مقيدة", "إفصاح البورصة المصرية اليوم" (also capital increases, buybacks, results, index changes, suspensions). Prefer EGX disclosures, Mubasher, Alborsa News, Amwal Al Ghad, Arab Finance, Enterprise, Zawya. Table: ticker, type, one line, source + link + date, positive/negative, move since the news in % and ATRs (> 2 ATR = priced in; tender offers cap the upside near the offer; rumours are unconfirmed). A catalyst never replaces the chart rules.
- **[Max]** WebSearch mode extended for every query, at least 10 queries over 14 days, WebFetch the original for every catalyst kept, and the macro calendar for the next 5 trading days (CBE decision, inflation prints, holidays, results season).

### A3. Per-stock analysis
- **Swing scans start with positions:** egx-check §3 on every held stock; their value counts toward the caps.
- **Scan / Scan Spec:** quick scan in batches of 8 per `javascript_tool` call: `out.push(await EGX.scan(tk, {catalyst: ...}))` (one line per stock: trend daily/weekly, RS20/60, entry, stop, target, R:R, stop ATRs, distance, value traded, chart score, drop reason). `UNKNOWN` lines are skipped (never fill their numbers); `DROP:` lines are dropped with their reason. News for every scanned stock: one dated search per ticker over the last 7 days (several tickers may share a query) for red events (results within 3 trading days, ex-date, suspension). Rank the survivors as A4, ties by chart score; then egx-check §1 in full on the best 5 (fewer if fewer survive): `EGX.deep(tk)`, cropped chart screenshot, 2+ news searches. Drawings, analysis and news are mandatory for all 5 whatever the verdict. No quick-scan screenshots.
- **[Max]** egx-check §1 in full on **every** stock (`EGX.deep(tk)` with drawings, order book, financial tab and candles; cropped screenshot; 2+ news searches), plus for every stock (news extended when standard finds nothing dated in 30 days):
  - **Fundamental read:** P/E and EPS from the financial tab, valuation vs its sector, latest dated results (growth/decline, one-offs), dividend yield, balance-sheet flags (debt, losses, late filings). Flag page values that contradict dated news.
  - **Plan and expected gain:** entry, stop under real support, target at the next resistance, R:R gross and net, % gain to target, % loss to stop.
  - **Setup history test** on the last 300 bars (same zone or setup: how often the target came before the stop within 15 bars; < 3 tries = too few to judge).
  - Data pack: `EGX.exportToPage([...tickers])` + `get_page_text` + `EGX.clearExport()` -> `scan/datapack-YYYY-MM-DD.json` in the working directory with every number and its bar dates, plan, setup history, order book, financial values, news and catalysts with links and dates, red events. Unreadable = "unknown". Only the main session uses Chrome.
- **[Spec]** Entry may be up to 1.5 ATR above the support zone, using only the script's plans (no hand levels): `pullback-at-support` already enters at the last close within 1.5 ATR of the support top, so it qualifies; a `pullback-limit` plan may be placed at the last price only when `|plan.entryDistATR|` <= 0.5 (then the entry is the last close and R:R must be recomputed by `egx.py allocate` with that entry; say which entry was used). Stop still under the support zone, 1-3 ATR away. Every plan has a **time stop of 10 trading days**.

### A4. Verdicts and ranking
**Scan (no Max, no Spec): strict verdicts** as egx-check: ✅ / ⏳ / ❌. In a Down regime a ✅ needs RS20 and RS60 both positive, else ⏳. Rank the survivors: trend up and RS positive first, then an unpriced positive catalyst, then R:R, then distance to entry.

**Scan Max and any Spec mode: always the best 3, ranked and graded.** Relative strength and the regime never drop a stock here; they set the grade.
- **Quality score (0-10):**
  - **[Max]** the average of the five analyst scores (A5).
  - Otherwise a checklist, 1 point each (trend up counts 2): trend up, price above MA50, RS20 > 0, RS60 > 0, support with 2+ touches, volume confirms the last move, unpriced positive catalyst, fundamentals sound (no losses, reasonable P/E vs sector), no red event before the order expires.
- **Rank score** = net R:R x (quality score / 10). Ties go to the higher quality score.
- **Grades** (Scan Max thresholds; Spec thresholds in brackets):
  - **A**: RS20 and RS60 both positive or regime Up [Spec: RS20 > 0 or RS60 > 0, neither below -5]; no red event before the order expires [Spec: and none in the 10-day hold]; entry within 1.5 ATR of the last price; quality >= 7 [Spec: >= 6.5].
  - **B**: exactly one weakness (one RS period negative, entry 1.5-3 ATR away, or quality 5.5-7 [Spec: 5-6.5]).
  - **C**: everything else, including any red event before the order expires.
- A = ✅, B = ✅ with the weakness named, C = ⚠️ speculative. When all three are C, say plainly that the market is not on his side and cash is a valid choice; the decision is his.

### A5. [Max] Five analyst passes on the best 8, then the verifier
- Finalists: the best 8 survivors by rank score using the checklist quality score.
- Launch **five agents in parallel in one message** with the same data pack and one lens each. Use `general-purpose` (not `egx-portfolio:egx-analyst`: that agent returns the portfolio advisor's verdict format, not these scores); set `model: "opus"` and `effort: "max"`.
  1. **Trend follower:** trend daily/weekly, MAs, relative strength, breakouts.
  2. **Pullback / support trader:** zones, touches, candles at support, setup history, chance of a fill within a week.
  3. **Catalyst and news:** catalyst quality and date, priced in or not, red events, macro calendar.
  4. **Fundamentals and valuation:** financial values, results trend, valuation vs sector, dividend, data inconsistencies.
  5. **Risk manager (devil's advocate):** stop vs noise, gap risk before results, liquidity, regime, fees vs gain, T+2.
- Give each agent: the pack path, its lens, the mode's rules (R:R, caps, Spec thresholds if Spec), and the horizon (swing about 1-3 weeks; Spec 10 trading days). Each returns JSON per ticker: **score 1-10**, 2-3 facts with dates from the pack, the biggest weakness, what would raise or lower the score; the risk manager also gives its **main objection**. No votes, no veto. Agents judge only from the pack and invent no numbers. They cannot write files: collect their JSON from their final messages and save it next to the pack.
- **Verifier:** one more agent (`general-purpose`, `model: "opus"`, `effort: "max"`) that has not seen the analysts' reasoning gets the pack, the analysts' scores and `run.json` after `egx.py allocate`; it recomputes R:R gross/net, shares, fees, caps, risk, quality, rank and grades and checks every cited date and link is in the pack, returning a list of errors. Fix every error; anything unconfirmable becomes "unknown" and costs the pick one grade.

### A6. Allocation
- Write the run file (egx-check §6) and run `python3 $S/egx.py allocate run.json` (caps incl. holdings, EGP 2,500 minimum, fees, break-even). Never size by hand.
- **Scan:** only ✅ picks are funded now; ⏳ picks may get a limit order at their entry if the user wants (`meta.include_wait_orders`).
- **Scan Max / Spec:** `allocate` funds only `verdict: valid` (and `wait` when `meta.include_wait_orders` is true) and orders by verdict then chart score, not by rank. So in `run.json` set A/B picks to `valid`, C picks to `wait` with `include_wait_orders: true`, and put only the picks being funded in that run, best rank first; fund #1 first, then #2 and #3 only while each order can still be >= EGP 2,500. Check that the allocation rows come out in rank order. Size grade C picks normally but label them speculative. For Spec, set `meta.risk_pct` from the run amount (risk budget / amount).
- In Correction or Down, suggest deploying at most half the amount (a suggestion he can override); say so when half is below the minimum order.
- Whatever is not allocated stays cash, with the reason. Add a **gap-risk line** for any pick with results or another red event before the order expires.

### A7. Report and answer
`python3 $S/egx.py check run.json`, fix every line, then `report run.json --out <reports folder>` (Max: `--video`, and tell him the render command it prints); send the HTML with SendUserFile (fallback: egx-check §6) and name the file in the answer.
1. Market line: EGX30 regime with numbers (**[Max]** plus the macro calendar items).
2. Positions: one line each (action + why).
3. Top 3-5 catalysts with source, date and priced-in status.
4. Table:
   - Scan: ticker, verdict, shares, EGP, entry, stop, target, R:R, risk EGP.
   - Scan Max / Spec: rank, ticker, grade, quality score, technical and fundamental one-liners, % gain to target, % loss to stop, R:R gross/net, shares, EGP, entry, stop, target, risk EGP (**[Spec]** plus the risk % used and the time stop).
5. Cash left and why; costs to cover; the cash warning from `allocation.warnings`.
6. Per pick: the short analysis, the fundamental read, **[Max]** the five scores in one line each and the risk manager's main objection; the chart screenshot. **[Max]** one line each for finalists ranked 4-8.
7. ThndrX steps for each pick he may place; remind him that stop and target sell orders usually can only be placed from T+2 and to use alerts until then.
8. Dropped stocks grouped by reason; ⏳ picks with what they wait for.
9. The report file name; closing line.

### A8. Log
One Recommendations row per deep-checked pick (Scan) or per finalist (Max/Spec) as egx-check §4 says, Command = the mode used; never log quick-scan rows. Notes always include shares, amount and the report file name. Max/Spec: Verdict column = Valid for A/B, Wait for C; Notes = rank, grade, quality score, shares and amount. **[Spec]** Outcome tracking also marks **Time exit** after 10 trading days without target or stop. Save the data pack and agent JSON so the run can be audited.

## B. Same-session mode (Scan T0, Scan T0 Max)

### B0. What T+0 is
Buy and sell the same stock in the same session. Since 2026-02-01 (EGX market-segment review, announced 2026-01-28) securities on the **Most Active** and **Medium Activity** boards (and the SMEs "Tamayuz" list) are eligible for intraday and T+1 trading; the segments change periodically, so eligibility is **unknown until confirmed** per stock (a dated EGX list, or the user seeing the T0 option in ThndrX: بيع ← طلب بسعر محدد متقدم ← تسوية T0). Everything bought must be sold the same session unless the user says otherwise. Longs only.

### B1. Clock and brakes
- Session 10:00-14:30, Sunday-Thursday (Africa/Cairo). Before 10:15, say so and wait for the first 15 minutes (opening noise). **No new entries after 13:30**; later = analysis only. **[Max]** has a **25-minute time budget**; after 13:00 offer Scan T0 instead.
- **Forced exit at 14:20** whatever happens. At most 2 trades per day, one at a time. **Daily brake:** if a T0 trade already hit its stop today (Trades tab: Source starts with "Scan T0" or "Loop T0", Closed = today, loss), analysis only for the rest of the day; Trades unreadable = ask him.
- Warn once: T0 needs the user watching ThndrX until the trade is closed; a plan older than ~15 minutes is stale.

### B2. Universe and market
- T+0-eligible stocks with average daily value >= EGP 20M and today's value on pace; start from the most-active list and his watchlist (about 20 names; **[Max]** all of them, plus T+0-eligible stocks with a dated disclosure today).
- Drops: spread > 0.3%, last 3% of the limit band, suspension or results/ex-date today, the safety drops above, expected move to target < 3x the round-trip fee % (`python3 $S/egx.py fees VALUE` for the order value; never a typed-in fee %), eligibility not confirmed = say so on the pick.
- EGX30 daily regime plus EGX30 5-minute bars vs its session VWAP.

### B3. Intraday analysis
The page script has **no intraday functions**, so: switch the chart to 5 minutes with the chart widget, read today's bars with one `javascript_tool` call that computes everything below from the chart's `exportData()` inside the page and returns only the results with bar times, then switch back to 1D (the daily tools need it). Never type intraday numbers by hand. With the last 60 daily bars compute: session VWAP, opening range (first 30 min), ATR5(14), RSI5(14), relative volume (vs the same time of day over recent sessions if available, else vs the 20-day average per minute), change vs EGX30, nearest daily support/resistance. **[Max]** also 15-minute bars, a setup history test on the last 20 sessions of 5-minute bars (how often the same setup reached 2R before the stop within the same session; < 5 tries = too few), a fundamental read (P/E, EPS, latest results, red events today) and a data pack `scan-t0/datapack-YYYY-MM-DD-HHMM.json` with every number and its bar times, the plan, order-book and time & sales reads, news with links and times, and the clock time of each read.
Setups (one per stock):
- **Opening-range breakout:** 5-min close above the range high on rising volume, above VWAP; entry on the retest; stop under the range high - 0.3 x ATR5 or under VWAP, whichever is tighter but >= 1 x ATR5.
- **VWAP pullback:** above VWAP most of the session, pulls back and holds; entry near VWAP; stop 1-1.5 x ATR5 below.
- **Daily-support bounce:** at a daily zone with a 5-min reversal and buyers in time & sales; stop under the zone.
Target: the nearer of the day's high, the next daily resistance, or 2R. R:R >= 2 gross and >= 1.5 net.
Every plan: entry, stop, target, R:R gross/net, shares, EGP, loss at stop with fees, gain at target with fees (from `egx.py allocate`), and the **time exit: sell by 14:20 whatever happens**. Size cap: the run amount (or the cash he says he will use) and 30% of equity; one trade at a time, at most 2 per day.

### B4. Verdicts or ranking
- **Scan T0:** deep check on the best 3 (order book split, spread and depth at the entry, time & sales: side and size of the last prints, one news search for today, drawings on the 5-min chart: VWAP, range, entry, stop, target; screenshot). Verdict ✅ / ⏳ (with the exact trigger, e.g. "5-min close above 13.55") / ❌. If EGX30 is below its VWAP and falling, a ✅ needs the stock above its own VWAP and stronger than EGX30 today.
- **[Max] Scan T0 Max:** five agents on the best 5 (same launch rules as A5) with intraday lenses: momentum/VWAP, order flow, news today, market and sector context, risk manager (stop vs 5-min noise, fees, slippage, time left, no stop available on T0 shares, the daily brake). Each gives a score 1-10, facts with clock times, the entry trigger and the biggest weakness. Same agent choice as A5 (`general-purpose`). Then the verifier (also checks the 13:30 cut-off and 14:20 exit). Rank score = net R:R x (average score / 10). Grades: **A** above VWAP, stronger than EGX30 today, trigger fired or within 0.5 x ATR5, average >= 7; **B** one weakness; **C** the rest. Always present the best 3 with grades; the ranking says which to take first.
- **[Max]** Re-read price and order book of every ranked pick right before answering; if price moved more than 0.5 x ATR5 past the entry or the trigger already ran more than 1R, mark it stale ("re-plan") instead of chasing.

### B5. Answer and log
- Title "T0 نفس الجلسة" (Max: "T0 ماكس نفس الجلسة"), clock time of the data (Max: and of the last price re-check), EGX30 regime + intraday vs VWAP, the table (ticker, verdict or grade, setup, entry, stop, target, R:R gross/net, shares, EGP, loss at stop), what cancels the idea (e.g. EGX30 breaks its VWAP, a 5-min close under the stop), dropped stocks grouped by reason, closing line.
- ThndrX steps: buy as a limit order valid today; exit the same day with بيع ← طلب بسعر محدد متقدم ← تسوية T0 ← price ← quantity. If no stop order is available on T0 shares, say so and tell him to set alerts at the stop and target and exit manually; never pretend a stop exists.
- Log Recommendations rows for the deep-checked picks with Command = the mode used (Notes = setup, time of the data, shares); save the data pack, agent JSON and verifier output under `scan-t0/`; Trades Source = the mode; Exit reason Target / Stop / Time (14:20) / Manual. Outcome tracking uses that day's 5-minute bars only; anything not hit by 14:20 is "Time exit".