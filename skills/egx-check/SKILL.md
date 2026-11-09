---
name: egx-check
description: "EGX trading helper on ThndrX in the user's Chrome. \"check TICKER\" / \"افحص\" (swing check: chart analysis, drawings, news, verdict, order steps), \"check TICKER T0\" (same-session check on 5-minute bars), \"market\", \"my positions\" / \"راجع مراكزي\" (hold / sell / add), trade logging (\"اشتريت / بعت\"), \"monthly\" results, and \"what did you say about TICKER\" / \"قلت ايه عن\" (memory). Every check passes 7 proven gates and saves a report (HTML + PDF) locally and to Google Drive."
---

# EGX Check on ThndrX

Commands: **check TICKER** · **check TICKER T0** · **market** · **my positions** · **log** ("اشتريت JUFO 350 بـ 22.90", "بعت EGAL") · **monthly** · **memory** ("قلت ايه عن HRHO", "last runs"). Multi-stock scans are the **egx-scan** skill, which runs this skill's check on every stock it picks.

`$S` = this skill's `scripts/` folder (the base directory this skill was loaded from + `/scripts`):
- `egx_chart.js` (runs in the ThndrX page): opens tickers, analyses, draws, verifies the drawings, reads panels. Rules: `references/analysis-rules.md`.
- `egx.py` (Python 3.9+, standard library): `verdict`, `check`, `allocate`, `report`, `fees`, memory (`recall`, `news`, `runs`, `outcome`, `open`), `drive-record`. Run-file format: `references/run-schema.md`.
- News whitelist and query templates: `references/news-sources.md`. UI facts and order-ticket steps: `references/thndrx-ui.md`.

## Hard rules (never break)
1. **Never trade.** Never click Buy, Sell, شراء, بيع, confirm, modify or cancel; never type in the order ticket; never touch the open-orders list. The user places every order.
2. **Read-only on the account**, except chart drawings labelled `EGX·` (the script clears and redraws only those) and the MA50 / MA200 indicators. Say once per session that drawings stay in the ThndrX chart layout.
3. **No login work.** On the 2FA screen ask the user to approve it in the Thndr app. Never enter passwords or codes.
4. **No private API calls.** Only what the page shows and the chart's own `exportData()`. Never call prod.thndr.app endpoints.
5. **Proof, not words.** A step is done only when its receipt says so (the page script or `egx.py` writes receipts; you never type or edit one). Never write a verdict by hand: `egx.py verdict` computes it. You may only downgrade it, with `override` and a reason. Never use or ask for a `--force`; there is none.
6. **Evidence for every claim.** Levels come from the script with their bar dates. News comes only from the whitelist in `references/news-sources.md`, opened and dated from the page. Unknown is written "unknown", never guessed.
7. **Any gate that fails makes the stock ⏳**, and the answer names the gate. Never present a partial check as a full one.
8. **Education, not advice.** End every answer with: تحليل تعليمي مش نصيحة استثمارية؛ القرار والأوامر ليك.

## 0. Setup (each session, silent)
1. `python3 $S/egx.py config` (config.json here, then `~/.egx-thndrx/config.json`). If `trade_log_sheet_id` is set and the Google Sheets connector is on, read the **Settings** tab (risk %, equity, fees, fixed costs); Settings wins over config.
2. Load the Chrome tools in one ToolSearch call: tabs_context_mcp, tabs_create_mcp, navigate, computer, javascript_tool, find, get_page_text.
3. New tab -> https://x.thndr.app/workspaces/default/trade, wait 3 s, then load the page script:
   - `javascript_tool`: `typeof EGX!=='undefined'?EGX.version:(localStorage.getItem('EGX_JS')?((0,eval)(localStorage.getItem('EGX_JS')),EGX.version):'missing')`
   - If it is not the `VERSION` at the top of `$S/egx_chart.js` (now 3.0.0), read `$S/egx_chart.loader.js` and run its whole text once with `javascript_tool`.
4. `await EGX.market()` once per session (EGX30 regime, today's change, relative-strength base).
5. **Stop and tell the user** (never work around it) when: Chrome is not connected; the login / 2FA screen shows (rule 3); `EGX.version` is still wrong after the loader; `EGX.market()` returns no regime. Market closed ("السوق مغلق") is fine for swing checks: say the plan is for the next session.

## 1. Memory first (before any new analysis)
- `python3 $S/egx.py recall TICKER` (past verdicts, plans, outcomes, news titles; about 120 tokens per record) and `python3 $S/egx.py news TICKER --since <30 days ago>` (news already found: do not search or fetch those again; only look for newer items).
- Never open old report HTML files to search. `egx.py read FILE --ticker TK` gives the full detail of one record only when recall is not enough.
- Mention in the answer when the new verdict differs from the last one, and why.

## 2. check TICKER (swing): the 7 gates, in this order
Write each step's result into the stock object of `run.json` (in the working directory) as you go.

**Gates 1-2: open + analyse.** `await EGX.deep('TICKER')`. It opens the stock, switches the chart to 1D, analyses it (blocks A-I, plan, setup history), reads the page (cash, order book, price band) and the financial tab, keeps 120 candles, and writes the `open` and `analyse` receipts. It does **not** draw. If it returns `ok:false`, or `R.drop` is set, there is no draw (a dropped stock still gets the news gate only if the user asked about it specifically).

**Gate 3: news.** At least 2 WebSearch queries, one Arabic and one English, built from the templates in `references/news-sources.md`. Log every query in `news_queries` (`{query, results}`).
- Keep only items on the whitelist. Open each kept item with WebFetch and read its date from the page; set `opened: true` (Bloomberg: headline and date readable = `paywalled: true`). Record `source`, `tier`, `date`, `impact` (+ / 0 / -), `material` (suspension, fraud, big loss), `fresh` (48 h), one-line `summary`.
- Red events (results date, ex-date, suspension, capital increase) are checked on EGX (Tier 1) first: `red_events` with date, source, url. Not found = date "unknown".
- Catalysts from the last 30 days: merger / acquisition / tender offer, expansion, contract, license, bonus shares, dividend, buyback, strong results, index inclusion. A corporate event needs an EGX disclosure or two Tier-2 sources, else `status: "rumour"`.
- No dated item = `news: []`, `news_checked: true`; the answer says "مفيش أخبار جديدة، القرار فني بس".

**Gate 4: draw.** `await EGX.draw('TICKER', {events})` with `events` = every dated red event (`{date, kind:'event', label}`) and, for a catalyst, `{date, kind:'catalyst', label}`. It must return `ok:true` with `made == planned`. It draws the support / resistance / broken-support boxes, entry, stop, target, target 2, trendline, the event lines, and adds MA50 / MA200 once.

**Gate 5: verify.** `await EGX.verifyChart('TICKER')` must return `ok:true`. If not: read `problems`, run gate 4 once more, verify again. Still failing: continue; the verdict will be ⏳ with the gate named.

**Gate 6: screenshot (after the verify, within 30 minutes).** Move the mouse off the chart (`computer` `mouse_move` to the watchlist). `EGX.chartRect(4)` -> `region` (CSS px) and `viewport`. One `computer` `screenshot` to learn the frame width, scale the region by frame width / `viewport[0]`, then `computer` `zoom` with that region and `save_to_disk: true`. Put the saved path in `screenshot`. `egx.py` checks the file's own save time is after the verify.

**Export.** `EGX.exportToPage(['TICKER'])`, read it with `get_page_text` between `EGX-EXPORT-BEGIN` and `EGX-EXPORT-END`, then `EGX.clearExport()` (javascript_tool output is cut at about 1.5 KB). Paste it into `run.json` (it carries the receipts). Add `meta` (`command: "Check"`, `trading_day`, `amount: 0` unless the user gave one, `equity`, `cash`, `risk_pct`), `market.egx30` from the export's `index`, and per stock: `sector`, `reasons` (3-5 short lines in Egyptian Arabic, each with its evidence: dates, numbers, sources), `news_queries`, `news`, `red_events`, `screenshot`.

**Gate 7: verdict.** `python3 $S/egx.py verdict run.json`. It prints the checklist, e.g. `COMI ✔ open ✔ analyse ✔ news 2 queries, 3 items ✔ draw 9 marks ✔ verify ✔ screenshot ✔ verdict → ✅ valid`. The rules it applies (for your understanding; never apply them by hand):
- script drop -> ❌ dropped; any failed gate -> ⏳ naming the gate;
- ❌ not valid: negative material news, or daily and weekly trend down with RS20 and RS60 negative;
- ✅ valid only with plan `pullback-at-support` or `breakout-retest`, no red event before the order expires (about a week), no fresh negative news, entry inside today's price band, and in a Down regime RS20 and RS60 both positive;
- otherwise ⏳ with `wait_for` (price reaches the entry, the event passes, RS turns positive...).
- To downgrade (e.g. news the rules cannot read): add `"override": {"verdict": "wait"|"not_valid", "reason": "...", "wait_for": "..."}` and run `verdict` again.

Then §5 (report, Drive) and §6 (answer).

## 3. check TICKER T0 (same session)
T+0 = buy and sell the same stock in the same session. Only stocks on the EGX Most Active / Medium Activity boards (or the SMEs "Tamayuz" list) are eligible, and the boards change: eligibility is unknown until confirmed with a dated EGX list or the user seeing the T0 option in ThndrX (بيع ← طلب بسعر محدد متقدم ← تسوية T0). Set `t0_eligible: true` only then. Longs only.
- **Clock (Africa/Cairo):** session 10:00-14:30, Sunday-Thursday. Before 10:15, wait and say so. **No new entry after 13:30**; **exit by 14:20** whatever happens. At most 2 T0 trades a day, one at a time. **Daily brake:** if a T0 trade already hit its stop today (Trades tab: Source starts with "Scan T0" or "Check T0", Closed = today, loss), give analysis only.
- **Gates 1-2:** `await EGX.market()` (today's EGX30 change), then `await EGX.intraday('TICKER')`: daily analysis on 1D, then the chart switches to 5 minutes; VWAP, opening range, ATR5, RSI5, relative volume, the setup and its plan, the `t0` receipts. `drop` set -> stop here.
- **Gate 3: news** for today (2 queries, Arabic + English, as §2): results, disclosures, suspensions today.
- **Gates 4-6:** `await EGX.drawT0('TICKER')`, `await EGX.verifyChart('TICKER', {t0:true})`, screenshot as §2 into `t0.screenshot`, then `await EGX.daily()`.
- **Export + verdict:** as §2 with the stock's `"mode": "t0"` and `t0_eligible`. `egx.py verdict` also checks: the 5-minute read was between 10:15 and 13:30 Cairo on a Sunday-Thursday, eligibility, EGX30 down today -> the stock above its VWAP and stronger than EGX30, net R:R >= 1.5 after fees, a move to target of at least 3x the round-trip fees, entry within 0.5 ATR5 of the price (else ⏳ with the trigger).
- A plan older than 15 minutes is stale: run `EGX.intraday` again before answering.
- Order steps: buy as a limit order valid today; exit the same day with بيع ← طلب بسعر محدد متقدم ← تسوية T0 ← price ← quantity. If ThndrX offers no stop order on T0 shares, say so and tell the user to set price alerts at the stop and the target and exit by hand; never pretend a stop exists.

## 4. market · my positions · log · monthly · memory
**market:** `EGX.marketPage()` on https://x.thndr.app/workspaces/default/market + `await EGX.market()`; a run file with `command: "Market"`, no stocks; short answer.

**my positions** (also the first step of every swing scan):
1. Click the bottom tab **الاستثمارات الحالية**, then `EGX.holdings()`. Funds (BWA, BMM, gold, money-market) are `is_fund: true` and not analysed.
2. Each stock: `recall` it, then gates 1-6 exactly as §2 (deep, news, draw, verify, screenshot). Read the open orders tab **الأوامر** (read only) for an existing stop or take-profit.
3. Action (first that applies), each with evidence:
   - **exit / sell:** close below the user's stop or below the support low - 0.5 ATR; a broken support (`zones.brokenSupportNowResistance`) on above-average volume; negative material news.
   - **tighten:** price at least 1.5 x (avgPrice - stop) above avgPrice, or within 0.5 ATR of the target -> new stop = last swing low - 0.5 ATR (or breakeven).
   - **add:** the stock's own `egx.py verdict` would be ✅, R:R >= 2, and the position stays under the caps; give `plan` so `egx.py allocate` sizes the add.
   - **hold:** anything else. No stop order seen -> suggest one (support low - 0.5 ATR) with the sell-stop ticket steps.
4. Put them in `run.json` `holdings` with `action`, `reasons`, `news`, `screenshot`. Flag pending orders (قيد المعالجة) older than 2 days.

**log / monthly** (Google Sheet, only if `trade_log_sheet_id` is set; tabs Trades, Monthly, Recommendations, Settings). Read column A first to find the first empty row; never write formula columns (Trades M, Q-W; Recommendations H). Connector off -> give the row to paste.
- After every verdict: one Recommendations row: Date, Command, Ticker, Verdict (Valid / Wait / Not valid), Entry, Stop, Target, (H empty), EGX30 regime, Taken? = No, Outcome = Open, Outcome date, Notes (key reason + report name).
- "I bought": Trades row (next T###, date, ticker, sector, source = the command, AI verdict and plan from Recommendations, shares, price, buy fees from the Thndr e-invoice email "فاتورتك الإلكترونية من ثاندر" if Gmail is connected, else `egx.py fees VALUE` and "fees estimated"); Taken? = Yes.
- "I sold": Closed, sell price, sell fees, exit reason (Target / Stop / Time / Manual); update the Recommendation's Outcome; report net P/L, return %, R multiple from the sheet.
- **Outcome tracking** (start of any command): `python3 $S/egx.py open` lists calls still open. For each (at most 10, oldest first): bars after the call (`EGX.get(tk).candles` if deep-checked this session, else `await EGX.open(tk)` then `await EGX.candlesNow(120)`; rows `[date, o, h, l, c]`). Entry touched first, then whichever of stop / target comes first (both in one bar = stop). Results: target, stop, expired (15 trading days without entry); T0 calls use that day's 5-minute bars, nothing by 14:20 = time. Record each with `python3 $S/egx.py outcome RUN TICKER RESULT DATE` and in the Sheet.
- **monthly:** `Monthly!A1:L16` and `N2:O7`: this month, running average, win rate, Recommendations hit rate, whether trading covers its fixed costs.

**memory** ("what did you say about X", "last runs"): `egx.py recall X [--last N]`, `egx.py news X`, `egx.py runs [--command Scan] [--since DATE]`. Answer from these; never open report HTML.

## 5. Report, PDF and Drive
1. `python3 $S/egx.py check run.json`: fix every line it prints (re-run `verdict` after changing data). `allocate` runs inside `report`; run `python3 $S/egx.py allocate run.json` first only to show the sizing.
2. `python3 $S/egx.py report run.json --out <reports folder>` (folder: `reports_dir` from config, default `~/EGX-Reports`; a cloud session without the user's computer: the working directory, and say so). It writes the HTML, the PDF (needs Chrome), `shots/`, `index.csv` and the memory files, and prints a `drive` plan.
3. **Drive** (when the plan is printed and the Google Drive connector is on), for each file in `drive.files`:
   - `create`: `create_file(parentId = drive.folder_id, title = name, base64Content = file_ref, contentMimeType = mime, disableConversionToGoogleType = true)`;
   - `replace`: the same `create_file`, then `trash_file(old_file_id)` (Drive's `update_file` cannot change content);
   - `skip`: nothing.
   - After each create, `python3 $S/egx.py drive-record NAME NEW_FILE_ID`. Say the report is in Drive only after the connector returned the file id; connector off = "saved on this computer only".
4. Send the PDF (and the HTML) with SendUserFile when that tool exists; otherwise give the full paths and the Drive link.

## 6. Answer (Egyptian Arabic, phone-sized, numbers and tickers in Latin digits)
- **القرار** ✅ / ⏳ / ❌ and the checklist line from `egx.py verdict`, exactly as printed.
- 3-5 reasons with their evidence (dates, numbers, sources); what changed since the last call (memory).
- **الخطة**: entry, stop, target (and target 2), R:R, whether the entry is likely to fill soon (`plan.fillSoon`; over 2 ATR away = unlikely this week), shares and EGP from `egx.py allocate`, fees, the monthly costs to cover; say plainly when the hurdle is unrealistic for the capital.
- **خطوات ThndrX** for ✅ (and ⏳ the user may place as a limit order): the ticket steps from `references/thndrx-ui.md` with the real numbers. If `page.cash` is below the order value, say the cash must be deposited or redeemed first. Settlement is T+2: stop and target sell orders usually only from T+2, so set price alerts until then.
- What cancels the idea; the report name and where it is saved; the closing line (rule 8).
