---
name: egx-thndrx-trade-check
description: "EGX trading helper on ThndrX in the user's Chrome: \"check TICKER\" / \"افحص\" (scripted chart analysis, drawings, news, verdict, order steps), \"market\", \"my positions\" / \"راجع مراكزي\" (hold / sell / add), trade logging (\"I bought / I sold\"), \"monthly\" results, and \"what did you say about TICKER\" (report history). Every run saves a ThndrX-style HTML report with evidence."
---

# EGX trade check on ThndrX

Commands: **check TICKER** · **market** · **my positions** · **log** ("اشتريت JUFO 350 بـ 22.90", "بعت EGAL") · **monthly** · **history** ("قلت ايه عن HRHO", "last reports"). **Loop 30** and **Loop 30 Max** are separate skills that reuse everything here.

Scripts live in this skill's `scripts/` folder (call it `$S`; it is the base directory this skill was loaded from + `/scripts`). They do the analysis and the paperwork so Claude does not spend tokens deriving levels by hand:
- `egx_chart.js` (in the ThndrX page) - opens tickers, computes every chart block, draws the lines, reads cash / order book / financials / holdings. Rules: `references/analysis-rules.md`.
- `egx.py` (Python 3, standard library) - fees, sizing, the HTML report, `index.csv`, report search. Run-file format: `references/run-schema.md`.
- UI facts and the order-ticket steps: `references/thndrx-ui.md`.

## Hard rules (never break)
1. **Never trade.** Never click Buy, Sell, شراء, بيع, confirm, modify or cancel; never type in the order ticket; never touch the open-orders list. The user places every order.
2. **Read-only on the account**, except chart drawings (only lines labelled `EGX·`, which the script clears and redraws). Say once per session that drawings are saved to the ThndrX chart layout.
3. **No login work.** On the 2FA screen ask the user to approve it in the Thndr app. Never enter passwords or codes.
4. **No private API calls.** Only what the page shows and the chart's own `exportData()`. Never call prod.thndr.app endpoints.
5. **Evidence for everything.** Levels come from the script with their bar dates; news has source, link and date. Unknown is written "unknown", never guessed.
6. **Chart + analysis + news are mandatory for every verdict** (✅, ⏳ or ❌). If one fails, say which and make the verdict ⏳.
7. **Education, not advice.** End with: analysis, not investment advice; the decision is the user's.

## 0. Setup (each session, silent)
- Read `config.json` in this skill folder (`python3 $S/egx.py config`). If the trade-log sheet id is set and the Google Sheets connector is on, read its **Settings** tab (risk %, equity, fees, fixed costs); Settings wins over config.
- Load the Claude in Chrome tools in one ToolSearch call (tabs_context_mcp, tabs_create_mcp, navigate, computer, javascript_tool, find).
- New tab -> https://x.thndr.app/workspaces/default/trade, wait 3 s, then load the script:
  1. `javascript_tool`: `typeof EGX!=='undefined'?EGX.version:(localStorage.getItem('EGX_JS')?((0,eval)(localStorage.getItem('EGX_JS')),EGX.version):'missing')`
  2. If the answer is not the version in the first lines of `$S/egx_chart.js`, read `$S/egx_chart.loader.js` and run its whole text once with `javascript_tool` (it runs and caches itself; later sessions only need step 1).
- `await EGX.market()` once per session (EGX30 regime + relative-strength base). On the market page, `EGX.marketPage()` adds breadth, sectors and USD/EGP.

## 1. check TICKER
1. `await EGX.deep('TICKER')` -> opens it, runs blocks A-I, draws entry / stop / target / zones / trendline, reads the order book, price band, cash and the financial tab, and stores 120 candles. Read only what you need from the result (`plan`, `zones`, `rs`, `score`, `drop`, `evidence`, `page`, `flags`).
2. Screenshot the chart with `computer` `screenshot` + `save_to_disk: true` (keep the path for the report).
3. News (mandatory): at least 2 WebSearch queries (English + Arabic: ticker, company name, Arabic name + البورصة). Keep only dated items; fresh = 48 h. Flag red events (results date, ex-date, suspension, capital increase, regulatory action) and catalysts (merger / acquisition / tender offer, expansion, contract, license, bonus shares, buyback, strong results), and whether the price already moved on them (% and ATRs since the date).
4. **Verdict** (Claude may only downgrade these, never upgrade):
   - script `drop` set -> ❌ with the drop reason.
   - ✅ **valid** only if: no drop, `plan.type` is `pullback-at-support` or `breakout-retest`, no red event before the order would expire, no negative fresh news, and in a **Down** regime both `rs.rs20` and `rs.rs60` > 0.
   - ❌ **not_valid** if: negative material news (suspension, fraud, big loss) or daily AND weekly trend down with RS20 and RS60 negative.
   - otherwise ⏳ **wait**, with `wait_for` = exactly what must happen (price reaches entry X; EGX30 leaves Down / RS turns positive; results on DATE pass).
5. Write the run file (see §6) and build the report. Answer as in §7.

## 2. market
`EGX.marketPage()` on the market page + `await EGX.market()`; a short answer and a run file with `command: "Market"` (no stocks).

## 3. my positions (also step 1 of every Loop)
1. Click the bottom tab **الاستثمارات الحالية**, then `EGX.holdings()`. Funds (BWA, BMM, gold, money-market) are `is_fund: true` and not analysed.
2. For each stock: `await EGX.deep(tk)`, screenshot, news check (as §1.3). Read the open orders tab **الأوامر** (read only) for an existing stop or take-profit.
3. Action per stock (first that applies), each with evidence:
   - **exit / sell**: close below the user's stop or below the support zone low - 0.5 ATR, a broken support (`zones.brokenSupportNowResistance`) on above-average volume, or negative material news.
   - **tighten**: price at least 1.5 x (avgPrice - stop) above avgPrice, or within 0.5 ATR of the target -> new stop = last swing low - 0.5 ATR (or breakeven).
   - **add**: the script plan passes all ✅ rules, R:R >= 2 and the position stays under the caps; give `plan` so `egx.py allocate` sizes the add.
   - **hold**: anything else. No stop order seen -> suggest one (support low - 0.5 ATR) with the sell-stop ticket steps.
4. Flag pending orders (قيد المعالجة) older than 2 days.

## 4. log / monthly (trade log sheet, only if `trade_log_sheet_id` is set)
Google Sheet tabs: Trades, Monthly, Recommendations, Settings. Use `get_values` / `update_values`; never write formula columns (Trades M, Q-W; Recommendations H). If the connector is off, give the row to paste.
- **After every verdict**: append to Recommendations: Date, Command, Ticker, Verdict (Valid / Wait / Not valid), Entry, Stop, Target, (H empty), EGX30 regime, Taken? = No, Outcome = Open, Outcome date, Notes (key reason + report file name).
- **"I bought"**: append to Trades (next T###, date, ticker, sector, source, AI verdict and plan from Recommendations, shares, price, buy fees from the Thndr e-invoice email "فاتورتك الإلكترونية من ثاندر" if Gmail is connected, else `egx.py fees VALUE` and "fees estimated"); set Taken? = Yes.
- **"I sold"**: fill Closed, Sell price, Sell fees, Exit reason; update the Recommendation's Outcome; report Net P/L, Return %, R multiple from the sheet.
- **Outcome tracking** (any command): Recommendations still Open and older than 1 day -> compare the stock's bars since that date with entry / stop / target (entry first, then whichever of stop / target is hit first) -> Target hit / Stop hit, or Expired after 15 trading days without entry.
- **monthly**: read `Monthly!A1:L16` and `N2:O7`; report this month, the running average, win rate, Recommendations hit rate, and whether trading covers its fixed costs.

## 5. history ("what did you say about X", "show my last reports")
Never open report files to search. `python3 $S/egx.py search --ticker X` (or `--command`, `--since`) reads `index.csv`; `egx.py history X` lists every past verdict and plan; `egx.py read FILE --ticker X` prints only that stock's saved data. Reports live in the reports folder (§6).

## 6. Run file, report and where it is saved
- Build the run file in the working directory: `EGX.exportRun(['TK',...])` in the page returns JSON (full detail for the listed tickers, summary rows for the rest); paste it into `run.json`, add `meta`, `market`, `holdings`, `catalysts` and per stock `verdict`, `reasons`, `wait_for`, `news`, `red_events`, `screenshot`, `sector`. Format: `references/run-schema.md`.
- `python3 $S/egx.py check run.json`, fix every line it prints, then `python3 $S/egx.py report run.json --out <reports folder>` (add `--video` to also write a HyperFrames recap project the user can render to MP4 with the command it prints).
- Reports folder, first that works:
  1. Claude Code / desktop with the folder reachable: `reports_dir` from config (default `~/EGX-Reports`).
  2. Cloud session with the user's computer linked: stage the folder's `index.csv` (if any) into a local folder, run `report --out` there, then write the HTML and `index.csv` back with the device bridge.
  3. `reports_repo` set in config (a private GitHub repo): clone / pull it, run `report --out` into it, commit and push.
  4. Otherwise build in the working directory and say it was not saved to the user's folder.
- Always send the HTML with SendUserFile (it opens on the phone too).

## 7. Answer (the user's language; Egyptian Arabic by default, phone-sized)
- **القرار** ✅ / ⏳ / ❌ and 3-5 reasons, each with its evidence (dates, numbers, sources).
- **Plan**: entry, stop, target, R:R, shares and EGP value from `egx.py allocate` (risk % from Settings), fees and the monthly costs to cover (`allocation.fixed_monthly`, `break_even_monthly_pct`). Say plainly when the hurdle is unrealistic for the capital.
- **Order steps** for ✅ (and ⏳ the user may place as a limit order): the ticket steps from `references/thndrx-ui.md` with the real numbers. If `page.cash` is below the order value, say the cash must be deposited or redeemed first.
- What cancels the idea; the report file; the closing line from rule 7.
