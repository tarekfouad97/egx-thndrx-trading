---
name: "loop-30"
description: "\"Loop 30\": scans the top 30 EGX stocks on ThndrX with the egx-thndrx-trade-check method plus a market-wide news and catalyst scan (expansion, mergers, tender offers, contracts), asks how much Tarek wants to invest, then ranks the valid setups and splits the amount across them."
---

# Loop 30

Run when Tarek says "Loop 30" (or "لف على الـ 30"). It applies the **egx-thndrx-trade-check** skill to many stocks and turns the result into an allocation. Load that skill first and obey all its hard rules (never trade, read-only, no private API calls, evidence for every claim, education not advice).

## 0. Ask first (one message, AskUserQuestion if available)
- **How much do you want to invest now?** (e.g. 15,000 EGP). Required; never assume.
- His total equity if not known this session (for 1% risk sizing); default: the account value ThndrX shows on the home page, said out loud.
- Warn once: a full loop reads 30 charts and uses a lot of Claude usage (the 5-hour and weekly limits); it takes a while.
- Read the trade log Settings tab first and use its Risk per trade and Equity (Tarek can set high risk = 2%). Also read the cash available in the ThndrX header: if it is less than the amount he wants to invest, say so at the start (he must deposit or redeem funds such as BWA/BMM first).

## 1. The list
- Official EGX30 constituents: WebSearch for the current list (EGX, Mubasher index page, or a dated news item on the latest index review). Use it only with a source and a date.
- If no dated official list is found: use the 30 largest stocks by market cap from the ThndrX market page heatmap (الحرارة السوقية, size = القيمة السوقية) and say clearly it is "top 30 by market cap", not the official index.

## 2. Market once
Run step 2b of egx-thndrx-trade-check once (EGX30 regime, breadth, sectors, USD/EGP rate). Keep the EGX30 bars for relative strength.

## 2c. News and catalyst scan (mandatory, whole market)
Look for stocks with a trigger for a quick move, not only the 30 on the list.
- WebSearch (standard), several queries in English and Arabic, covering the **last 7 days**, e.g. "EGX disclosure acquisition", "EGX merger", "tender offer EGX", "عرض شراء إجباري البورصة المصرية", "استحواذ البورصة المصرية", "اندماج شركة مقيدة", "توسعات مصنع جديد البورصة", "توزيع أسهم مجانية", "عقد جديد شركة مقيدة", "إفصاح البورصة المصرية اليوم". Prefer EGX disclosures, Mubasher, Alborsa News, Amwal Al Ghad, Arab Finance, Enterprise, Zawya.
- Catalyst types: merger / acquisition / tender offer, expansion or new capacity, large contract, new license or market entry, bonus shares or capital increase, dividend, buyback, strong results, index inclusion. Also note negative triggers (losses, suspension, legal action).
- Keep a catalyst table: ticker, company, catalyst type, one-line summary, source + link + publish date, positive / negative, price change since the news date (% and in ATRs).
- Every positive-catalyst stock with average daily value traded >= EGP 5 million joins the quick scan in step 3, even if it is not in the top 30. Mark it "catalyst" in its row.
- Quick-profit cautions to state with each catalyst: if the price already moved more than 2 x ATR since the news, it is probably priced in (do not chase); for a tender offer, the upside is capped near the offer price and depends on the offer completing; rumours without a disclosure count as unconfirmed.
- A catalyst never makes a ✅ by itself: the chart plan still needs a valid entry, a stop under support and reward:risk >= 2.

## 3. Quick scan, every stock (no drawings yet)
For each ticker: open it in ThndrX (heatmap tile or watchlist search), read its daily bars with the chart export, and compute with the same rules as the check skill: trend (pivots, MA20/MA50/MA200, MA50 slope), nearest support and resistance zones with touch counts, RSI 14, ATR 14, volume vs 20-day average, relative strength vs EGX30 (20 and 60 bars), and a candidate plan (entry near support or confirmed breakout, stop under support, target at next resistance) with reward:risk. Apply all chart blocks A-I of the check skill's step 3 to every stock (pivots, weekly trend, zones with the broken-zone test, RSI and divergence, MACD, ATR and squeeze, volume and accumulation, patterns, relative strength, plan quality checks) and give each a chart score 0-10. Also drop stocks whose stop is under 1 x ATR and cannot be widened to the next zone with R:R >= 2 ("noise"), and plans whose target is below the current price ("invalid"). When ranking survivors, break ties with the chart score (higher first).
- Keep a table row per stock: ticker, sector, last, trend, RS20, RS60, entry, stop, target, R:R, ATR %, average daily value traded (close x volume, 20 days), catalyst (from step 2c, or none).
- News is mandatory here too: every stock gets at least one dated news search (Arabic or English, last 7 days). Note any red event (results within 3 trading days, ex-date, suspension) in the row.
- Confirm the chart header shows the right ticker after each search (other stocks may be listed first). Stocks with fewer than 60 daily bars (new listings) are dropped as "new".
- Drop stocks with: R:R under 2, average daily value traded under EGP 5 million (too thin), a stop distance over 3 x ATR (too wide), or price inside the last 2% of the daily limit band. Say why each was dropped (one word).
- If a chart cannot be read, mark the row "unknown" and skip it; never fill numbers.

## 4. Deep check, top candidates only
Rank the survivors: trend up and RS positive first, then a confirmed positive catalyst not yet priced in, then R:R, then distance from entry (closest first). Take the best 5 (fewer if fewer survive) and run the FULL egx-thndrx-trade-check on each: order book, financial tab, fresh news (48 h) plus the catalyst check, red events (results date, ex-date, suspension), drawings on the chart and a screenshot. **Drawings, analysis and news are mandatory for all 5, whatever the verdict** (hard rule 7 of the check skill): never skip them because a pick is ⏳ or ❌. Each gets ✅ / ⏳ / ❌.

## 5. Split the amount
Use only ✅ picks for buying now; ⏳ picks may get a limit order at their entry price if Tarek wants (say so).
- **Shares per pick** = floor( (equity x risk %) / (entry - stop) ), with risk % from Settings (1% normal, 2% high risk). Never above that: the risk rule wins over spending the whole amount.
- **Caps**: each stock at most 30% of the portfolio after the trade; each sector at most 50% (include what he already holds; sectors from the EGX classification with a source).
- **Minimum order**: about EGP 2,500 per stock, so the fixed fees (EGP 2 + FRA min EGP 1 per side) stay small. If the amount cannot fund at least one order at that size, say so.
- **Market regime**: in Correction or Down, suggest deploying at most half of the amount now and keeping the rest as cash for later entries - a suggestion Tarek can override, not his rule.
- Whatever is not allocated stays **cash**, with the reason (no valid setups is a valid answer).
- Order the allocation table by priority.

## 6. Costs to cover
Show, as in the check skill: round-trip Thndr fees for the whole plan, the fixed monthly costs (Thndr Trader EGP 245 + Claude USD 20 at today's rate, about EGP 1,325), the **monthly return needed on the invested amount just to break even**, and the plan's total net expected gain if all targets hit vs total loss if all stops hit. Say plainly if the hurdle is unrealistic for this amount.

## 7. Answer (Egyptian Arabic, phone-sized)
1. Market line: EGX30 regime in one sentence with its numbers.
1b. Catalyst list (step 2c): the strongest 3-5 triggers with source and date, whether each is priced in, and which ones made it into the deep check.
2. Allocation table: ticker, verdict, shares, EGP value, entry, stop, target, R:R, risk EGP.
3. Cash left and why.
4. Costs to cover (step 6).
5. For each deep-checked pick (✅, ⏳ and ❌): its chart screenshot. For each ✅ pick, and each ⏳ pick Tarek may place as a limit order: the exact ThndrX steps from the check skill (Tarek types them himself).
6. A short list of the dropped stocks grouped by reason, and the ⏳ ones with what they wait for.
7. One closing line: analysis, not investment advice; the decisions and the orders are Tarek's.

## 8. Log it
Append one Recommendations row per deep-checked pick (Command = Loop 30) to the trade log, exactly as the egx-thndrx-trade-check "Trade log" section says, with the allocated shares and amount in Notes. Read Settings first for fees, fixed costs, equity and risk. Do not log the quick-scan rows.