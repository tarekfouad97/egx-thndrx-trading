---
name: "egx-thndrx-trade-check"
description: "EGX trading helper on ThndrX in Tarek's Chrome: \"check TICKER\" (analyse, draw, news, verdict, exact ThndrX order steps), \"market\", \"my positions\", trade logging (\"I bought / I sold\") and \"monthly\" results from his EGX Trade Log sheet."
---

# EGX trade check on ThndrX (temporary, until the EGX Trading Desk is finished)

Commands:
- **check TICKER** ("افحص COMI"): analyse one stock on ThndrX in Tarek's Chrome, draw the analysis on the ThndrX chart, check the market (EGX30) and fresh news, and answer: is it valid to trade now? Then tell him exactly what to type in ThndrX.
- **market** ("السوق النهارده"): only step 2b, as a short market report.
- **my positions** ("راجع مراكزي"): see "My positions" at the end.
- **Loop 30** is a separate skill (loop-30) that runs this skill's steps on the top 30 stocks.
- **log** ("اشتريت JUFO 350 بـ 22.90", "بعت EGAL", "log my trade"): record a trade in the trade log. See "Trade log" at the end.
- **monthly** ("النتيجة الشهرية", "how am I doing"): read the Monthly tab and report this month and the running average.

**Trade log**: Google Sheet "EGX Trade Log (ThndrX)", id `1Z4zxmSYzA29X-UmHr8NGMcFeR7KWWWemKPbKpgjFN68` (https://docs.google.com/spreadsheets/d/1Z4zxmSYzA29X-UmHr8NGMcFeR7KWWWemKPbKpgjFN68/edit). Tabs: Trades, Monthly, Recommendations, Settings. Use the Google Sheets connector (get_values, update_values). If it is not connected, give Tarek the row to paste instead and say the connector is off.

## Hard rules (never break)

1. **Never trade.** Never click Buy, Sell, شراء, بيع, order confirm, modify, cancel, or the order ticket's submit button. Never type in the order ticket. Never touch the open-orders list (the ✎ and ✕ icons). Tarek places every order himself.
2. **Read-only on the account**, except chart drawings and indicators on the chart. Before the first drawing in a session, tell Tarek once that drawings are saved to his ThndrX chart layout and he can delete them with the trash icon.
3. **No login work.** If ThndrX shows the 2FA screen, ask Tarek to approve the number in the Thndr app, then continue. Never enter passwords or codes.
4. **No private API calls.** Read what the page shows; never call prod.thndr.app endpoints from scripts.
5. **Evidence for every claim.** Every level, trend or pattern names the bars (date and price) it comes from. Every news item has a source, a link and a date. If something cannot be seen or found, say "unknown" - never guess.
6. **Education, not advice.** End with one line: this is analysis, not investment advice; the decision is Tarek's.
7. **Chart, analysis and news are mandatory for every verdict**, whether it is ✅, ⏳ or ❌, and for every deep-checked Loop 30 pick. A verdict is not finished until all three exist: (a) the step 3 numbers with dated pivots, (b) the lines drawn on the ThndrX chart plus a saved screenshot sent to Tarek, (c) the step 4 news search with dated sources. Never skip one because the verdict is ⏳ or ❌. If one of them fails (the chart will not load, the drawing API errors, the search returns nothing dated), say exactly which one failed and make the verdict ⏳ for that reason.

## Steps

### 1. Open the stock
- Load the Claude in Chrome tools in one ToolSearch call (tabs_context_mcp, tabs_create_mcp, navigate, computer, read_page, get_page_text, find, javascript_tool).
- New tab -> https://x.thndr.app/workspaces/default/trade. Use the watchlist search to open the ticker. Confirm the header shows the right ticker and name.
- Note whether the market is open ("السوق مفتوح/مغلق").

### 2. Read everything ThndrX offers (read-only)
- **Price**: last, change, day high/low/open.
- **Order book** (العرض/الطلب): best bid/ask, spread in %, bid vs ask volume split (the % bar).
- **Time & sales**: size of the last trades; are they large or small.
- **Financial data tab** (البيانات المالية): P/E, EPS, market cap, dividend, anything shown. Copy only what is visible.
- **Price band** from the order ticket hint ("من X الي Y") = today's allowed range; read it, do not type.
- If Tarek holds the stock: his quantity and average cost from الاستثمارات الحالية.
- **Cash available to buy**: the EGP amount in the ThndrX header next to السوق مفتوح/مغلق. Money in funds (BWA, BMM, gold) is not cash. If the plan costs more than this cash, say so and tell Tarek he must deposit or redeem first, or ThndrX will cap the share count (e.g. 250 EGP cash only buys 11 shares at 22).

### 2b. Market context (EGX30) - always, once per session
- ThndrX market page (https://x.thndr.app/workspaces/default/market): read the indices (EGX 30, EGX 70, EGX 100), breadth (gainers / losers counts and %), sector pulse (نبض القطاعات: sector % moves) and the USD/EGP rate in the header.
- Click the **EGX 30** card in المؤشرات, then open the trade workspace: the chart now holds EGX30. Read its daily bars with the chart's own export (`iframe.contentWindow.tradingViewApi.activeChart().exportData({includeTime:true,includeSeries:true})` - page data, not a server call). Compute: last, MA20, MA50 and its slope (now vs 20 bars ago), MA200, change over 20 and 60 bars, distance from the 300-bar high.
- **Regime**: Up = above a rising MA50 and above MA200. Correction = below MA50 or MA50 falling. Down = below a falling MA50 and below MA200.
- **Relative strength** of the stock: its 20- and 60-bar % change minus EGX30's. Positive = stronger than the market.
- **Sector**: the stock's sector move today from نبض القطاعات.
- Effect on the verdict: in **Down**, a ✅ needs positive relative strength on both 20 and 60 bars, else it becomes ⏳. In **Correction**, say so in the reasons and prefer pullback entries over breakouts. Never let the market alone make a ✅.
- Reopen the stock afterwards (watchlist or search) before reading its chart.

### 3. Chart analysis
- Prefer exact numbers: read the stock's daily bars with the same chart export (open, high, low, close, and the volume study) and compute pivots, MAs, RSI 14 and ATR 14 from them; use the legend and zoom screenshots to cross-check.
- Set the chart to **Daily (1D)**, roughly the last 6-9 months visible. Add from the indicators menu (مؤشرات): **MA 20**, **MA 50**, **RSI 14**, **Volume** (if not already on).
- Read values from the chart legend (crosshair on the last bar) and the scale. Use `zoom` screenshots to read numbers exactly.
- **Data check**: use the last 300 daily bars. Fewer than 60 bars = new listing: verdict ❌ "no history". Confirm the chart header ticker and name before reading.
- Apply **every block below to every chart** and write each result with the bars it comes from (date and price). A block that cannot be computed is written "unknown", never guessed.

**A. Trend structure**
  - **Pivots**: swing highs and lows of the last 130 bars, a pivot = higher/lower than the 3 bars on each side. List the last 2 highs and last 2 lows.
  - **Daily trend**: higher highs + higher lows = up; lower highs + lower lows = down; else sideways.
  - **Weekly trend**: build weekly bars from the daily ones; price vs 10-week and 30-week MA and the 30-week MA slope. A daily setup against a falling weekly trend is noted as counter-trend.
  - **Moving averages**: MA20, MA50, MA200 values; order (MA20 > MA50 > MA200 = bullish stack); MA50 slope (now vs 20 bars ago, %).
  - **Stretch**: distance of the close from MA20 and MA50 in ATRs. More than 2 ATR above MA20 = stretched, do not chase; wait for a pullback.

**B. Support and resistance**
  - **Zones**: cluster all pivots within max(1.5% of price, 0.5 x ATR); a zone needs 2+ touches. Give each zone its range and touch dates.
  - **Still valid?** A support zone is broken if any close in the last 15 bars is below its low minus 0.5 x ATR; a broken support becomes resistance (role reversal).
  - Also mark the 300-bar high and low, the last swing low, and any round number (e.g. 20.00, 100.00) within 1 ATR of price.
  - **Trendline / channel**: a line through 2+ real lows (or highs) that no close broke in between; a parallel line through the opposite pivot.

**C. Momentum**
  - **RSI 14** value and zone (<30 oversold, 30-70, >70 overbought).
  - **RSI divergence**: price makes a lower low but RSI a higher low at the last 2 swing lows = bullish divergence; the mirror at highs = bearish.
  - **MACD (12, 26, 9)**: histogram sign, and any signal-line cross in the last 5 bars.

**D. Volatility**
  - **ATR 14** in EGP and as % of price.
  - **Bollinger (20, 2) squeeze**: band width in the lowest 20% of the last 120 bars = squeeze; a breakout from a squeeze is a stronger signal.

**E. Volume and liquidity**
  - Last bar volume vs 20-day average (ratio).
  - Up-day volume vs down-day volume over the last 20 bars (accumulation if up > down).
  - A breakout counts only if its close is above resistance on volume >= 1.5 x average.
  - Average daily value traded (close x volume, 20 days); under EGP 5 million = too thin.

**F. Patterns and candles** (only when they clearly fit; name the bars)
  - Pullback to support, breakout and retest, range bottom, flag, double bottom / double top, higher low at support.
  - Reversal candles in the last 3 bars at a support zone: hammer, bullish engulfing, inside-bar break. At resistance: shooting star, bearish engulfing.

**G. Relative strength**
  - Stock's 20- and 60-bar % change minus EGX30's (step 2b), and today's move vs its sector (نبض القطاعات).

**H. Plan quality checks** (on top of step 5)
  - Setup type: pullback, breakout-retest or range bottom; say which.
  - Stop distance between 1 x ATR and 3 x ATR: under 1 ATR is daily noise (widen the stop under the next zone or skip), over 3 ATR is too wide.
  - Target must be above the current price and below the next resistance zone; if the next resistance is under the current price, the plan is invalid. Give a second target at the following zone if there is one.
  - Entry more than 2 x ATR from the last close = limit order unlikely to fill soon; say so.

**I. Chart score (0-10)**, shown with its parts:
  - Trend 0-2 (up daily and weekly = 2, one of them = 1).
  - Relative strength 0-2 (RS20 and RS60 positive = 2, one = 1).
  - Reward:risk 0-2 (>= 3 = 2, 2-3 = 1).
  - Volume 0-1 (accumulation or breakout volume).
  - Momentum 0-1 (RSI 40-65 rising, bullish divergence or MACD bull cross).
  - Catalyst 0-1 (positive, dated, not yet priced in; step 4).
  - Market regime 0-1 (EGX30 Up = 1).
  The score ranks candidates; it never overrides the rules for ✅ (valid entry, stop under support, R:R >= 2, regime rule in step 2b).

**J. Per-stock analysis block in the answer** (short): trend (daily / weekly), key zones with touches, RSI / MACD, volume, RS, pattern, plan, score, and what would cancel the idea.
- **Draw on the ThndrX chart (mandatory, see hard rule 7)** with its left toolbar, or with the chart widget's own drawing calls (`createMultipointShape` for trend lines, `createShape` with `horizontal_line` for levels, each with a short Arabic label): trend line tool for the support line and channel ceiling, horizontal line for each support/resistance zone, and horizontal lines for the proposed entry, stop and target (label them if the tool allows). Colours: entry blue, stop red, target green, support orange dashed, resistance red dashed, trendline orange. Label each zone with its touch dates. Set the visible range to about the last 200 days. Draw only lines that match the pivots you listed. Before drawing, check that the chart header shows the right ticker (watchlist search may list other stocks first, e.g. ORAS can be the third result). Take a screenshot with `save_to_disk: true` and send it to Tarek with SendUserFile.

### 4. News check (mandatory, see hard rule 7)
- At least two searches per stock: one English, one Arabic. WebSearch (standard) in English and Arabic, e.g. "<TICKER> EGX", "<company name> news", "<الاسم بالعربي> البورصة". Prefer: EGX disclosures, Mubasher (english.mubasher.info / mubasher.info), Alborsa News, Amwal Al Ghad, Enterprise, Zawya, company IR site.
- Keep only items with a clear publish date. **Fresh = 48 hours or less.** List fresh items with source, date, one-line summary, and whether it is positive, negative or neutral for the stock. Older items: at most 2 lines of context, marked old.
- Flag red events: earnings release in the next days, trading suspension, capital increase, dividend ex-date, regulatory action. No fresh news -> say "no fresh news; verdict is technical only".
- Flag **catalysts** from the last 30 days (with source and date): expansion or new capacity, merger / acquisition / tender offer (استحواذ، اندماج، عرض شراء), large contract, new license or market entry, bonus shares (أسهم مجانية), dividend, buyback, strong results, index inclusion. Say whether the price already moved on it (change since the news date in % and in ATRs). A catalyst can support a verdict, but it never replaces the chart rules: no ✅ without a valid entry, stop under support and reward:risk >= 2.

### 5. Trade plan and checks (Tarek's rules)
- Risk per trade **1% of equity** (allowed 1-2%). Ask equity once per session if unknown; never assume it.
- Entry near support (pullback) or on a confirmed breakout close with above-average volume. Stop just below the support zone / trendline (a little under, not on it). Target at the next resistance.
- **Reward : risk must be >= 2 : 1**, computed from entry, stop and target.
- **Position size** = (equity x 1%) / (entry - stop), rounded down to whole shares (lot = 1 share), and its value must keep the stock <= **30%** of the portfolio and its sector <= **50%**.
- **Thndr fees per side** (from his e-invoices): EGP 2 per order + 0.1% brokerage/custody + 0.01% EGX + 0.01% MCDR + FRA (min EGP 1) + 0.005% risk fund + 0.05% stamp duty. Round trip on small orders is about 0.5%; say if fees eat a big part of the expected gain.
- Entry, stop and target must sit inside today's price band and use valid ticks (0.01 above EGP 1).
- Settlement is T+2: shares bought can only be sold from T+2 - say so if the plan needs a quick exit.
- **Costs to cover before any profit** (show every time):
  - Per trade: the Thndr fees above, buy + sell, in EGP.
  - Per month, fixed: **Thndr Trader plan EGP 245** (seen on his transactions) + **Claude subscription USD 20** converted at the USD/EGP rate in the ThndrX header (about EGP 1,080 at 54). Total about **EGP 1,325 / month**.
  - State the **monthly return needed just to break even** on the money he trades: fixed monthly costs / invested amount (e.g. EGP 15,000 needs about 8.8% a month). Say plainly when that hurdle is unrealistic for the capital and what capital would make it reasonable (e.g. 1% a month needs about EGP 132,500).
  - Net expected gain of the plan = (target - entry) x shares - round-trip fees. Show it next to the monthly cost.

### 6. Verdict
Reply in plain Egyptian Arabic (numbers and tickers in Latin digits), short enough for a phone screen:

- **القرار**: one of ✅ صالح للتداول دلوقتي / ⏳ انتظر (and exactly what must happen first) / ❌ مش صالح.
- Why, in 3-5 bullets, each citing its evidence (bars, indicator values, order book, news with source and date).
- **Plan** (if valid or wait): entry, stop, target(s), reward:risk, shares and EGP value at 1% risk, estimated fees.
- **Exactly what to type in ThndrX** (Tarek types and presses the button himself). First read the order ticket on the left (labels only, never type), then give the steps with the real labels you saw. The ticket as seen on 8 Nov 2026:
  1. Open the stock, panel تداول on the left, tab **شراء**.
  2. **نوع الطلب**: أمر بسعر محدد (limit).
  3. **سعر**: the entry price. **العدد**: the share count. Check **السعر الكامل** shows about shares x price.
  4. **الانتهاء**: صالح لتاريخ معين and **تاريخ انتهاء الصلاحية** = a date about one trading week ahead (or the until-cancelled option if offered). **نوع التنفيذ**: افتراضي.
  5. Tick **امر ايقاف** and enter the stop price. Tick **جني الارباح** and enter the target price.
  6. The green button must read **شراء TICKER · shares أسهم @ entry**. If anything differs, stop and recheck.
  If a label on the ticket differs from this list, use the label you actually saw and say what changed.
- **What would cancel the idea** (invalidation level or event).
- The screenshot of the drawn chart.
- One closing line: analysis, not investment advice; the decision and the order are Tarek's.

If anything important could not be read (chart not loading, 2FA not approved, no data), say what is missing and give the verdict as ⏳ with the reason, never a confident call on partial data.

## Trade log

Always read Settings first (fees, fixed costs, equity, risk) and use those values instead of the numbers written in this skill when they differ.

**After every verdict** (check, and each deep-checked Loop 30 pick): append one row to **Recommendations** at the first empty row (read `Recommendations!A:A` to find it): Date (yyyy-mm-dd), Command (Check / Loop 30), Ticker, Verdict (Valid / Wait / Not valid), Entry, Stop, Target, leave H empty (formula), EGX30 regime (Up / Correction / Down), Taken? = No, Outcome = Open, Outcome date empty, Notes (one line: the key reason). Write with `update_values`; never overwrite column H.

**When Tarek says he bought**: append a row to **Trades** at the first empty row: Trade ID (next T###), Opened date, Ticker, Sector, Source (Check / Loop 30 / Manual), AI verdict (from the matching Recommendations row, if any), Plan entry / stop / target (from that row), Shares, Buy price, Buy fees. Fees: from the Thndr e-invoice email of that day if he has Gmail connected (subject "فاتورتك الإلكترونية من ثاندر (YYYY-MM-DD)", total line اجمالي المصاريف); otherwise estimate from Settings and write "fees estimated" in Notes. Set the matching Recommendations row's Taken? to Yes. Columns M, Q, R, S, T, U, V, W are formulas: never write there.

**When Tarek says he sold**: find his open row for that ticker (Closed empty), fill Closed date, Sell price, Sell fees (invoice or estimate as above), Exit reason (Target / Stop / Manual / Time). Update the matching Recommendations row's Outcome and Outcome date. Then report the trade's Net P/L, Return % and R multiple from the sheet.

**Outcome tracking**: whenever any command runs, for Recommendations rows still Open and older than 1 day, compare the stock's daily bars since the recommendation date with its entry, stop and target (entry touched first, then stop or target first) and set Outcome to Target hit / Stop hit, or Expired after 15 trading days without entry. This measures the AI's accuracy whether Tarek traded or not.

**monthly**: read `Monthly!A1:L16` and `Monthly!N2:O7`. Report in Egyptian Arabic: this month's closed trades, wins, net P/L, fixed costs, net after costs; the average month so far; win rate; and the Recommendations hit rate (Target hit vs Stop hit among closed outcomes). If "Capital at start of month" is empty for the current month, ask Tarek for it once and write it (column I). Say plainly whether trading is covering its fixed costs yet.

## My positions
Read الاستثمارات الحالية (stocks only; skip funds such as BWA, BMM and gold). For each stock: quantity, average cost, last price, P/L %, and whether an open stop or take-profit order exists in الأوامر (read only). Run steps 3 and 2b on it and say per position: keep / tighten the stop to X / exit idea, with evidence. Any position without a stop gets a suggested stop (below the nearest support) and the exact ThndrX steps to place a sell stop - which Tarek enters himself. Also flag any pending order (قيد المعالجة) older than 2 days.