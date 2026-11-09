# Design (v0.3)

Two skills. Both are strict: every step leaves a receipt made by a script, and the next step
refuses to run without it. Claude never says a step is done unless its receipt says so.

## Skill 1: `egx-check` (one stock and the account)

| Command | What it does |
|---|---|
| **check TICKER** | Swing check on daily bars |
| **check TICKER T0** | Same-session check on 5-minute bars (session only, 10:15-13:30 Cairo) |
| market · my positions · log · monthly · history | Account and history commands |

### The check: 7 gates (swing and T0)

| Gate | Receipt (made by a script) | Fails if |
|---|---|---|
| 1. Open | chart header symbol = TICKER, resolution, last bar date | wrong stock, stale data |
| 2. Analyse | script version, bar count, the result object | under 60 bars, UNKNOWN |
| 3. News | each query's text, each item's URL, tier, date, impact | fewer than 2 queries, an item with no tier or date |
| 4. Draw | `EGX.draw(tk, {events})`: marks drawn by kind (event and catalyst dates come from gate 3), MA50/MA200 | 0 marks, a mark failed |
| 5. Verify chart | `EGX.verifyChart(tk)` reads every `EGX·` mark back and matches it with the plan | a mark missing, a wrong price, a mark from another stock, wrong resolution |
| 6. Screenshot | the image file's modification time is after the verify time; image size | taken before the verify, file missing |
| 7. Verdict | `egx.py verdict` computes it from the receipts; Claude may only downgrade, with a written reason | Claude upgraded it |

Then `egx.py check` (no `--force` in the skills) and the report. The answer ends with the
checklist `egx.py` prints, e.g. `✔ opened ✔ analysed ✔ drawn 9 ✔ verified ✔ screenshot ✔ news 3 ✔ verdict`.
A failed or unknown gate makes the stock ⏳ and the answer names the gate.

## Skill 2: `egx-scan` (one mode, three categories)

1. Ask the amount and the trading day (risk % from Settings).
2. Positions first (skill 1, my positions); they count toward the caps.
3. Three lists:
   - **Top 30**: official EGX30 with a dated source, else the top 30 by market cap.
   - **Hot**: corporate events (merger, acquisition, tender offer, capital increase, big contract), global demand (themes in `references/themes.md` mapped to EGX sectors), urgent industry (government decisions, tariffs, export bans, sector pulse). Each with its reason, source, tier and date; last 14 days; moved > 2 ATR since the news = priced in. A top-30 stock with a hot reason is listed under Hot with an "EGX30" tag.
   - **T0**: T+0-eligible stocks, average value >= EGP 20M. Only in session (10:15-13:30); otherwise "skipped" with the reason.
4. Quick filter of every stock with the script and the safety drops.
5. Skill 1 in full (all 7 gates) on the best 3-5 of each category.
6. Rank inside each category; top 3 each. Only ✅ and ⏳ are ranked; ✅ first, then net R:R x chart score / 10, ties by an unpriced hot reason.
7. Money: the strongest picks across all categories are funded first; T0 money is free again by 14:20.
8. One report: a section per category, the allocation, dropped stocks by reason.

Removed: Scan Max, Scan Spec, the analyst agents and the verifier.

## On the ThndrX chart

All marks are labelled `EGX·` (T0: `EGX·T0`), only these are ever cleared, and they stay on the
chart after the screenshot. The user's own drawings and the order ticket are never touched.

**Daily**
| # | Mark | Shape |
|---|---|---|
| 1 | Support zone with touch dates | orange shaded box |
| 2 | Up to 2 resistance zones | red shaded boxes |
| 3 | Broken support, now resistance | red hatched box |
| 4 | Entry | blue solid line |
| 5 | Stop | red solid line |
| 6 | Target | green solid line |
| 7 | Target 2 | green dashed line |
| 8 | Trendline (rising lows / falling highs) | orange line |
| 9 | Results / ex-date ahead | red vertical line |
| 10 | Catalyst date (Hot only) | purple vertical line |
| + | MA50 and MA200 | indicators, added once, never duplicated |

View: about the last 200 days. Then verify, move the mouse off the chart, cropped screenshot.

**T0 (5 minutes)**: VWAP, opening-range box, entry, stop, target, nearest daily support and
resistance; verify, screenshot, back to 1D.

## News

Whitelist and tiers in `skills/egx-check/references/news-sources.md`. Every item kept is opened
and its date read from the page. A corporate event counts only with EGX official or two
independent Tier-2 sources; anything else is "rumour".

## Report
- Minimal, stylish, responsive (phone first). Shows the verdict, the plan, the chart picture and the gate checklist.
- Name: `EGX_<Command>_<YYYY-MM-DD>_<HH-MM>` (Check includes the ticker, e.g. `EGX_Check-COMI_2026-11-10_14-05`).
- Saved locally (`reports_dir`, with `index.csv` for history search) **and** uploaded to the user's Google Drive folder (`drive_folder_id` in config.json) as **HTML + PDF**: Drive cannot display HTML, the PDF opens in Drive on any device.
- Drive connector off: say the report was saved locally only; never claim an upload without the file id the connector returns.

## Memory (the report's second reader is future Claude)

The HTML is for the user. Claude never reads HTML or embedded base64: it reads three small
files next to the reports, written by `egx.py report`, each line self-contained.

| File | One line per | About | Holds |
|---|---|---|---|
| `history.jsonl` | stock per run | 150-250 tokens | date, run, command, category, rank, verdict, wait_for, last, plan (type, E/S/T, R:R gross/net, stop ATR), support zone + touch dates, trend d/w, RS20/60, regime, top 3 reasons, news ids, red events, gates (failed only), shares/value, outcome (filled later) |
| `news.jsonl` | news item (deduped by URL) | 60-100 tokens | id, tickers, date, source, tier, impact, material, title, url, one-line summary, first seen |
| `runs.jsonl` | run | 80-120 tokens | file, command, created, trading day, regime + EGX30, amount, deployed, cash left, picks by category, summary |

Commands (Claude's first stop, never the HTML):
- `egx.py recall TICKER [--last 5]`: that stock's last verdicts, plans, outcomes and news titles; about 1-2k tokens for 10 runs instead of ~18k.
- `egx.py news TICKER [--since DATE]`: news already found, so old stories are not searched or paid for again.
- `egx.py runs [--command Scan] [--since DATE]`: what each run decided.
- `egx.py read FILE --ticker X`: full detail of one stock in one run (rarely needed).

Rules: the embedded report data drops screenshots (kept as image files next to the report) and
candles; outcome tracking writes the outcome back into `history.jsonl`; the three files are
uploaded to Drive with each report so the memory survives a new computer.

## Build order
1. ✔ Chart script v3.0.0: boxes, new marks, MAs, `verifyChart`, receipts, `intraday` (tests: `tests/test_chart_draw.js`).
2. ✔ `egx.py` 3.0.0: `verdict` (the only way a verdict is set), strict `check`, printed checklist, no `--force` (gates in `egx_gates.py`; tests: `tests/test_egx.py`).
3. ✔ Report v3 (`egx_page.py`: dark, Apple Stocks / Wallet + TradingView-style SVG charts, news per pick, static so the PDF matches) + memory (`egx_memory.py`: `history.jsonl`, `news.jsonl`, `runs.jsonl`; `recall` / `news` / `runs` / `outcome` / `open`) + PDF (headless Chrome) + Drive plan (`drive-record`). Drive tested live 2026-11-10: create, and replace = upload new + trash old (the connector's update_file cannot change content).
4. Skill 1 rewrite.
5. `themes.md` (the user corrects the sector mapping).
6. Skill 2 rewrite.
7. Tests, a sample run, one live check on ThndrX.
