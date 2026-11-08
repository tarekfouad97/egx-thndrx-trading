---
name: loop-30
description: "\"Loop 30\" / \"لف على الـ 30\": reviews the user's current EGX positions (hold / sell / add), runs a market-wide news and catalyst scan, scans the top 30 EGX stocks on ThndrX with the scripted egx-thndrx-trade-check method, deep-checks the best 5, splits the amount the user wants to invest, and saves a ThndrX-style HTML report with all evidence."
---

# Loop 30

Run when the user says "Loop 30" or "لف على الـ 30". Load **egx-thndrx-trade-check** first and obey all its hard rules and its setup (§0: config, Settings, the `EGX` page script, `EGX.market()`). `$S` = that skill's `scripts/` folder (sibling of this skill: `../egx-thndrx-trade-check/scripts`).

## 0. Ask first (one message, AskUserQuestion if available)
- **How much to invest now?** Required; never assume.
- The trading day it is for (default: next EGX session, Sunday-Thursday).
- Warn once: a loop reads 30+ charts and uses a lot of Claude usage; it takes a while.
- Risk % and equity come from the Settings tab (else config). Read `EGX.page().cash`: if the cash is below the amount, say so at once (deposit or redeem funds such as BWA / BMM first).

## 1. Current positions
Run the check skill's **my positions** (§3) on every held stock. Their actions (hold / tighten / sell / exit / add) go into the run file `holdings`; their value counts toward the 30% stock and 50% sector caps.

## 2. Market and catalysts
- `EGX.market()` (regime) and, on the market page, `EGX.marketPage()` (breadth, sectors, USD/EGP, and the heatmap order).
- **Catalyst scan (mandatory)**: WebSearch (standard; extended only if standard returns nothing dated) over the last 7 days, English and Arabic, e.g. "EGX disclosure acquisition", "EGX merger", "tender offer EGX", "عرض شراء إجباري البورصة المصرية", "استحواذ البورصة المصرية", "اندماج شركة مقيدة", "توسعات مصنع جديد البورصة", "توزيع أسهم مجانية", "عقد جديد شركة مقيدة", "إفصاح البورصة المصرية اليوم". Prefer EGX disclosures, Mubasher, Alborsa News, Amwal Al Ghad, Arab Finance, Enterprise, Zawya.
- Keep each catalyst with ticker, type, one-line summary, source, link, date, direction, price move since the date (% and ATRs) and `priced_in` (moved > 2 ATR = priced in, do not chase). Tender offer = upside capped near the offer price; rumours without a disclosure are `status: "rumour"`.
- A positive, confirmed catalyst stock with average value traded >= EGP 5M joins the scan even if it is not in the top 30.

## 3. The list
Official EGX30 constituents with a dated source (WebSearch); else the 30 largest by market cap from the ThndrX heatmap (الحرارة السوقية), said clearly as "top 30 by market cap". Add the catalyst stocks.

## 4. Quick scan (scripted, no screenshots)
- Scan in batches of 8 per `javascript_tool` call: `const out=[]; for (const tk of ['COMI','SWDY',...]) out.push(await EGX.scan(tk, {catalyst: CATALYST_TICKERS.includes(tk)})); out.join('\n')`. Each line already holds trend daily/weekly, RS 20/60, entry, stop, target, R:R, stop ATRs, distance, value traded, chart score and the drop reason.
- A line with `UNKNOWN` is skipped (never fill numbers). `DROP:` lines are dropped with their one-word reason (rules in `references/analysis-rules.md`).
- News is mandatory for every scanned stock: one dated search per ticker (Arabic or English, last 7 days) noting red events (results within 3 trading days, ex-date, suspension). Several tickers may share one query.

## 5. Deep check, best 5
Rank the survivors: daily trend up and RS20 & RS60 positive first, then a confirmed catalyst not priced in, then R:R, then distance from entry (closest first), ties by chart score. For each of the best 5 (fewer if fewer survive) run the check skill's §1 fully: `EGX.deep(tk)` (drawings + order book + financials + candles), cropped chart screenshot (check skill §1.2), news (2+ searches), verdict ✅ / ⏳ / ❌ by its rules. Drawings, analysis and news are mandatory for all 5 whatever the verdict.

## 6. Split the amount (no hand arithmetic)
Write the run file (check skill §6) with `meta.amount`, `meta.equity`, `meta.cash`, `meta.risk_pct`, `meta.include_wait_orders` (true if the user wants ⏳ limit orders), then `python3 $S/egx.py allocate run.json`. It applies: shares = floor(equity × risk % / (entry − stop)); 30% per stock and 50% per sector including holdings; EGP 2,500 minimum order; equal split of the money between picks; half the amount in Correction / Down (the user may override with `meta.half_deploy: false`); never a plan under 2:1; fees, gain if all targets, loss if all stops, fixed monthly costs and the break-even monthly return. Whatever is not allocated stays cash, with the reason.

## 7. Report and answer
- `python3 $S/egx.py check run.json`, then `python3 $S/egx.py report run.json --out <reports folder>` (folder rules: check skill §6). Send the HTML with SendUserFile.
- Answer in the user's language (Egyptian Arabic by default), phone-sized:
  1. One market line with its numbers.
  2. Positions: one line each (action + why).
  3. Top catalysts (3-5) with source, date, priced in or not.
  4. Allocation table: ticker, verdict, shares, EGP, entry, stop, target, R:R, risk EGP.
  5. Cash left and why; costs to cover; the cash warning if any.
  6. ThndrX order steps for each ✅ (and ⏳ limit orders if wanted) with each chart screenshot.
  7. Dropped stocks grouped by reason; ⏳ picks with what they wait for.
  8. The report file name; closing line: analysis, not investment advice; the decisions and orders are the user's.

## 8. Log
One Recommendations row per deep-checked pick (Command = Loop 30) as the check skill §4 says, with the allocated shares, amount and report file name in Notes. Do not log quick-scan rows.
