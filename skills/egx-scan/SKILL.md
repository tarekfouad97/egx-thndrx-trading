---
name: egx-scan
description: "EGX many-stock scan on ThndrX: \"Scan\" / \"لف على الـ 30\" / \"اعمل سكان\". Reviews positions, builds three lists (Top 30, Hot stocks moved by mergers, global demand or urgent industry news, and Same-day T0 during the session), runs the full egx-check gates on the best of each, ranks the top 3 per list, splits the user's amount and saves one report (HTML + PDF) locally and to Google Drive. The old names Loop 30, Scan Max, Scan Spec, Loop T0 all run this one Scan."
---

# EGX Scan

One mode, three lists. Load **egx-check** first and obey all its hard rules (never trade, read-only, no login work, no private API calls, proof not words, evidence, any failed gate = ⏳, education not advice). Every stock that gets a verdict goes through egx-check's 7 gates; this skill only chooses the stocks, ranks them and splits the money. `$S` = `../egx-check/scripts`.

Old command names (Loop 30, Loop 30 Max, Scan Max, Scan Spec, Loop T0, Scan T0 Max) run this Scan; say once that the Max / Spec modes were retired.

## 0. Before starting (one message, AskUserQuestion if available)
- **The amount for this run** (required, never assume) and the trading day (default: the next EGX session, Sunday-Thursday). Read `EGX.page().cash`; if it is lower than the amount, say so first (deposit or redeem BWA / BMM).
- Whether ⏳ picks may be placed as limit orders at their entry (`meta.include_wait_orders`, default yes).
- Risk per trade, fees and fixed costs come from the Settings tab (egx-check §0); never from memory.
- Warn once: a scan reads 30+ charts and runs many searches; it takes a while.
- Create a task list with the steps below.

## 1. Setup, memory, outcomes
1. egx-check §0 (config, Settings, page script 3.0.0, `EGX.market()`).
2. `python3 $S/egx.py runs --last 3` (what the last scans decided) and outcome tracking (egx-check §4: `egx.py open`, then `egx.py outcome ...`).
3. For every stock that reaches the deep check: `egx.py recall TK` and `egx.py news TK` first (egx-check §1).

## 2. Positions first
egx-check **my positions** on every held stock (all 6 gates each). Their value counts toward the 30% stock and 50% sector caps.

## 3. Market
`EGX.marketPage()` on the market page (breadth, sector pulse, USD/EGP, heatmap order) and `await EGX.market()`. Macro items for the next 5 trading days (CBE decision, inflation print, holidays, results season) from Tier-3 sources go to `market.macro`.

## 4. The three lists
**Top 30** (`category: "top30"`): the official EGX30 constituents with a dated source from the whitelist (search EGX first). None found: the 30 largest by market cap from the ThndrX heatmap, said clearly as "top 30 by market cap".

**Hot** (`category: "hot"`), last 14 days, every candidate with `hot: {reason, type, date, sources, priced_in}`:
- *Corporate events*: merger, acquisition, tender offer, capital increase, big contract, license, expansion, bonus shares, buyback. Queries: the Hot templates in `../egx-check/references/news-sources.md`. A confirmed corporate event needs an EGX disclosure or two independent Tier-2 sources; otherwise it is a rumour and cannot make a stock Hot.
- *Global demand*: the themes in `references/themes.md`; a theme is live only with a dated Tier-3 trigger; its tickers join the list.
- *Urgent industry*: government decisions, tariffs, export bans, subsidies (urgent-industry templates); map them to the sector and its tickers. The sector pulse is a hint, never a reason alone.
- Only stocks with average value traded >= EGP 5M a day. A Top-30 stock with a hot reason is listed under Hot (note "EGX30" in its reasons), never twice.
- Every hot reason also goes to `catalysts` (`tk, type, summary, direction, status, sources[], date`, later `moved_pct`, `moved_atr`, `priced_in`: moved > 2 ATR since the date = priced in; a tender offer caps the upside near the offer price).

**Same day T0** (`category: "t0"`): only when it is Sunday-Thursday between 10:15 and 13:30 Cairo time **and** the user wants it. Start from the most-active list and the watchlist (about 20 names): T+0-eligible (egx-check §3), average value >= EGP 20M and today's value on pace. Otherwise set `meta.t0_status` to the reason (e.g. "Skipped: market closed", "Skipped: after 13:30") and do not run T0.

## 5. Quick filter (scripted)
- Swing lists, batches of 8 per `javascript_tool` call: `const out=[]; for (const tk of [...]) out.push(await EGX.scan(tk, {catalyst: HOT.includes(tk)})); out.join('\n')`. One line each: trend, RS, entry, stop, target, R:R, stop ATRs, distance, value traded, chart score, `DROP:` reason.
- `UNKNOWN` lines are skipped and listed (never fill their numbers; a themes.md ticker that is UNKNOWN is reported as "not found, fix themes.md").
- In `run.json`, scanned stocks that are not deep-checked get `quick: true` (verdict "unchecked", never funded); drops keep their `drop` (verdict "dropped").
- Order the survivors per list for the deep check: daily trend up and RS20 and RS60 positive first, then an unpriced hot reason, then R:R, then distance to entry, ties by chart score.

## 6. Deep check, best 3-5 per list
- Top 30 and Hot: egx-check §2 in full (gates 1-6, export) on the best 3-5 of each list (fewer if fewer survive).
- T0: egx-check §3 in full on the best 3 (`"mode": "t0"`).
- Set `category` on every deep-checked stock (and `hot` for Hot ones). Keep all of them in one `run.json` (`meta.command: "Scan"`), with `holdings`, `catalysts`, `market`.

## 7. Verdicts and ranking
`python3 $S/egx.py verdict run.json`: gates and verdict for every stock, then the ranking inside each list (✅ first, then net R:R after fees x chart score / 10, ties by an unpriced hot reason). It prints the checklist lines and `ranking: top30: #1 ... | hot: ... | t0: ...`. Downgrades only through `override` (egx-check §2 gate 7). Show the top 3 of each list.

## 8. Money
`python3 $S/egx.py allocate run.json` (never size by hand). It funds ✅ picks first, then ⏳ limit orders if allowed, across all lists, by chart score and R:R; it applies the risk % from Settings, the 30% stock and 50% sector caps (holdings included), the EGP 2,500 minimum order, fees, and half the amount in Correction / Down (the user may override with `meta.half_deploy: false`). T0 picks reuse the run amount (they are sold by 14:20) and never use up swing money. Whatever is not allocated stays cash, with the reason; add a gap-risk line for any pick with a red event before its order expires.

## 9. Report and Drive
egx-check §5: `check`, `report --out <reports folder>`, then the Drive plan (create / replace / skip, `drive-record`). One report for the whole scan; the memory files get one line per stock.

## 10. Answer (Egyptian Arabic, phone-sized, title "Scan")
1. Market line: EGX30 regime with numbers, breadth, macro items.
2. Positions: one line each (action + why).
3. Catalysts and themes found: 3-5 lines with source, tier, date, priced in or not.
4. Per list (Top 30, Hot, Same day): the top 3 with verdict, the checklist line, entry / stop / target, R:R, shares and EGP, and one line why; T0 status when skipped.
5. Cash left and why; costs to cover; the cash warning if any.
6. ThndrX steps for each pick the user may place (egx-check §6); T0 exit steps; the T+2 note.
7. Dropped stocks grouped by reason; UNKNOWN tickers.
8. The report name, where it is saved (local, Drive), and the closing line.

## 11. Log
One Recommendations row per deep-checked pick (egx-check §4), Command = "Scan " + list (e.g. "Scan Hot"), Notes = rank, shares, amount, report name. Never log quick-scan rows.
