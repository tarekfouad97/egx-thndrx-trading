# How it works (and why it is cheap on tokens)

```
 ThndrX tab (Chrome)                      Claude                                   Your computer
 ──────────────────                       ──────                                   ─────────────
 egx_chart.js                             1. egx.py recall / news (memory first)
  • open ticker (receipt)        ───────▶ 2. reads the plan and receipts
  • analyse 300 daily bars                3. news: whitelisted sources only,
    or today's 5-min bars (receipt)          opened and dated from the page
  • draw boxes, lines, events, MAs ◀───── 4. EGX.draw(tk, {events})
  • verifyChart: read every mark back     5. screenshot after the verify
  • cash, order book, band, financials    6. run.json ──────────────────────────▶ egx.py verdict (8 gates + rules + ranking)
  • holdings grid                                                                  egx.py allocate (sizing, caps, fees)
                                                                                   egx.py report: HTML + PDF, shots/,
                                                                                   history / news / runs .jsonl
                                          7. Drive: create / replace / skip ◀──── drive plan (sha256 file refs)
```

## Steps, atomic steps and the ledger
Each command starts with `egx.py step start <command> run.json` and ends with `egx.py step finish`. In between, `egx.py step next` names the next atomic step and the proof it needs:
- **script** steps are proven by `egx.py step sync` from `run.json`, the receipts, the call log (`calls`, exported by the page script) and files on disk;
- **egx.py** steps are recorded when that subcommand runs (`recall`, `verdict`, `report`, ...), and refused if an earlier step is open;
- **stated** steps are recorded by Claude with `egx.py step done ID --proof "<value seen>"`.

The ledger (`run.ledger.jsonl`) is append-only and hash-chained; an edited ledger, an older run file or an empty one proves nothing. A step is retried once (`egx.py step fail`), then the stock is ⏳ naming it. `egx.py check` and `report` refuse to run without an intact ledger. Full design: `docs/DESIGN.md`.

## The 8 gates (7 + the step ledger)
| Gate | Receipt (written by) | Fails if |
|---|---|---|
| open | chart header or title shows the ticker, symbol, resolution, last bar (page script) | wrong stock |
| analyse | script version, bar count, last bar (page script) | old script, under 60 bars |
| news | query log (2+, Arabic and English), items on the whitelist, opened, dated (Claude, checked by egx.py) | missing language, unlisted source, no date |
| draw | marks made = planned, MA50 / MA200, every dated red event drawn (page script) | a mark failed |
| verify | every `EGX·` mark read back at its price, right ticker and resolution, nothing left over (page script) | anything off |
| screenshot | the image file's own time is after the verify and within 30 minutes (egx.py) | taken before, or stale |
| verdict | computed by `egx.py verdict`; overrides may only downgrade | hand-written or upgraded |

`egx.py check` re-runs all of it; the report refuses to build otherwise (there is no `--force`).

## Token savings
| Before | Now |
|---|---|
| Screenshot + click the search box + screenshot per stock | `EGX.scan('COMI')` in-page, 8 stocks per call |
| Claude computes pivots, zones, RSI, ATR, plan in its head | the script computes them and returns one line |
| Claude decides where to draw, hopes it worked | the script draws and then verifies every mark |
| Claude applies the verdict rules in prose | `egx.py verdict` |
| Re-sending the analysis code every session | cached in the tab's localStorage; a one-line loader restores it |
| Opening old reports to answer "what did you say about X" (about 1,800 tokens per report) | `egx.py recall X`: about 120 tokens per past call, with outcomes and news titles |
| Searching the same news again every run | `egx.py news X` lists what was already found |

## Files
- `skills/egx-check/scripts/egx_chart.js`: in-page analysis, drawing, verify, T0 (source). `egx_chart.loader.js`: minified, self-caching build (`python3 build_loader.py`).
- `egx.py`: commands. `egx_gates.py`: gates, verdict rules. `egx_steps.py`: the step ledger. `egx_page.py`: the report page. `egx_memory.py`: memory files. `egx_report.py`: the recap video.
- `references/analysis-rules.md`: every rule the script applies. `references/run-schema.md`: the run file. `references/news-sources.md`: the news whitelist and query templates.
- `skills/egx-scan/references/themes.md`: global-demand themes mapped to EGX sectors.
- `examples/sample-run.json`: a complete run built from synthetic data (used by the tests).

## Reports and memory
- Name: `EGX_<Command>_<YYYY-MM-DD>_<HH-MM>.html` and `.pdf`, e.g. `EGX_Scan_2026-11-08_21-30.pdf`. Screenshots go to `shots/`.
- The page: dark, Apple Stocks / Wallet style; per pick a TradingView-style candle chart with the support zone and entry / stop / target tags, the plan, the order line, the reasons, the news (tier, source, date), the gate checklist and the ThndrX screenshot. Static, so the PDF looks the same.
- The run is embedded as JSON (`script#egx-data`, without pictures or candles) for `egx.py read`.
- Memory (one JSON object per line, rewritten in place):
  - `history.jsonl`: one line per stock per run (verdict, plan, support with its last touch, trend, RS, regime, reasons, news ids, failed gates, shares, outcome);
  - `news.jsonl`: one line per news item, deduplicated by URL;
  - `runs.jsonl`: one line per run.
- `index.csv` is kept for `egx.py search`.
- Drive: `egx.py report` prints a plan; Claude uploads with the Google Drive connector. The connector's `update_file` cannot change content, so a changed memory file is replaced: upload the new copy, trash the old one, `egx.py drive-record` the new id.

## Changing the rules
Edit `egx_chart.js` (bump `VERSION`) or `egx_gates.py`, update `analysis-rules.md`, then:
```bash
python3 skills/egx-check/scripts/build_loader.py
node tests/test_chart.js && node tests/test_chart_draw.js
python3 tests/test_egx.py
```
