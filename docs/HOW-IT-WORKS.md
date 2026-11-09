# How it works (and why it is cheap on tokens)

```
 ThndrX tab (Chrome)                     Claude                                  Your computer / repo
 ──────────────────                      ──────                                  ────────────────────
 egx_chart.js  ── one line per stock ──▶ reads only the summary / plan / zones
  • opens tickers via the search box     • news search (dated sources)
  • exportData() 300 daily bars          • verdict rules (table in SKILL.md)
  • blocks A-I, plan, score, drop        • writes run.json ───────────────────▶ egx.py allocate / report
  • draws EGX· lines on the chart                                                • sizing, caps, fees, costs
  • cash, order book, band, financials                                          • HTML report (+ recap)
  • holdings grid                                                                • index.csv
```

## Token savings
| Before | Now |
|---|---|
| Screenshot + click the search box + screenshot per stock | `EGX.scan('COMI')` in-page, 8 stocks per call (6 stocks in ~9 s) |
| Claude computes pivots, zones, RSI, ATR, plan in its head | the script computes them deterministically and returns one line |
| Claude decides where to draw each line | the script draws entry / stop / target / zones / trendline with labels |
| Re-sending the analysis code every session | cached in the tab's localStorage; a one-line loader restores it |
| Claude does sizing / fee arithmetic in prose | `egx.py allocate` |
| Opening old reports to find a ticker | `egx.py search` / `history` read `index.csv`; `egx.py read FILE --ticker X` prints only that stock |

## Files
- `skills/egx-check/scripts/egx_chart.js` - in-page analysis (source). `egx_chart.loader.js` - minified, self-caching build (`python3 build_loader.py`).
- `skills/egx-check/scripts/egx.py` - fees, allocation, report, index, search, read, history, check.
- `skills/egx-check/references/analysis-rules.md` - every rule the script applies.
- `skills/egx-check/references/run-schema.md` - the run file.
- `examples/sample-run.json` - a complete run built from synthetic data (used by the tests).

## Reports
- Name: `EGX_<Command>_<YYYY-MM-DD>_<HH-MM>.html`, e.g. `EGX_Loop30_2026-11-08_21-30.html`.
- One self-contained file in the palette #0F171B / #122D39 / #2C697F / #D6B9B9 / #8A4C1C / #311F15 with Apple Liquid Glass only on the floating top bar and bottom dock (RTL Arabic or English). Each checked stock shows a **cropped screenshot of the real ThndrX chart with the drawn `EGX·` lines** as evidence (tap to enlarge), the plan grid, the reasons, and folded evidence (chart evidence with bar dates, news with links, order book, financials, analyst votes). A 12-second HyperFrames recap opens from the top bar.
- Big JSON leaves the page through an overlay read with `get_page_text` (`EGX.exportToPage` / `EGX.clearExport`), because `javascript_tool` output is cut at about 1.5 KB.
- Machine-readable: the whole run is embedded as JSON (`script#egx-data`) and a summary in `<meta name="egx-report">`.
- `index.csv` columns: file, created, trading_day, command, regime, egx30, amount, deployed, cash_left, tickers, valid, wait, not_valid, holdings, holding_actions, top_pick, catalysts, summary.

## Changing the rules
Edit `egx_chart.js`, bump `VERSION`, run `python3 skills/egx-check/scripts/build_loader.py`, update `analysis-rules.md`, and run the tests:
```bash
node tests/test_chart.js skills/egx-check/scripts/egx_chart.js
python3 tests/test_egx.py
```
