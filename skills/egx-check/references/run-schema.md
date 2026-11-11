# Run file (`run.json`) -> HTML report

Every command ends by writing one run file and calling
`python3 scripts/egx.py report run.json`. Most of the file is pasted straight from the
browser (`EGX.exportToPage(...)` read with get_page_text, or `EGX.exportRun(...)` for short output); Claude only adds verdicts, reasons and news.
See `examples/sample-run.json` in the repo for a complete example.

```jsonc
{
  "meta": {
    "command": "Scan",               // Check | Check T0 | Market | Positions | Scan
    "created": "2026-11-08T21:30",   // local time to the minute (egx.py fills it if missing)
    "trading_day": "2026-11-09",
    "amount": 15287,                 // money to invest now (0 for Check / Positions)
    "equity": 50858.16,              // account value (Settings tab or ThndrX)
    "cash": 250.24,                  // EGX.page().cash
    "risk_pct": 2,                   // from Settings
    "include_wait_orders": false,    // deprecated; wait picks are never funded
    "half_deploy": null,             // null = automatic (half in Down/Correction); true/false to override
    "summary": "one line for index.csv",
    "notes": "anything else"
  },
  "market": {
    "egx30": { /* EGX.market() */ },
    "page":  { /* EGX.marketPage(): breadth, sectors, usdEgp */ },
    "usd_egp": 54.12,
    "summary": "optional one-line market sentence",
    "macro": [{ "title": "", "source": "", "url": "", "date": "" }]
  },
  "catalysts": [{ "tk": "", "company": "", "type": "merger|acquisition|tender offer|expansion|contract|license|bonus shares|dividend|buyback|results|index",
                  "summary": "", "source": "", "url": "", "date": "", "direction": "+|-",
                  "moved_pct": 0, "moved_atr": 0, "priced_in": false, "status": "confirmed|rumour" }],
  "stocks": [
    { /* EGX.exportRun() object: tk, title, last, chg, trend, zones, momentum, volume, rs, plan, score, drop, evidence, draw, candles, page, financials, history ... */
      "sector": "Banks",
      "verdict": "valid | wait | not_valid | dropped",
      "reasons": ["3-5 short lines, each with its evidence"],
      "wait_for": "what must happen first (⏳ only)",
      "news": [{ "title": "", "source": "", "url": "", "date": "YYYY-MM-DD", "impact": "+|0|-", "fresh": true, "summary": "" }],
      "news_checked": true,          // set when the search found nothing dated
      "red_events": [{ "type": "results|ex-date|suspension|capital increase", "date": "", "source": "", "url": "" }],
      "screenshot": "/path/to/chart.jpg",   // REQUIRED: cropped ThndrX chart with the EGX· lines, saved with zoom + save_to_disk; embedded in the report
      "shot_at": "2026-11-09 00:05",        // when the screenshot was taken
      "spark": [ /* last 30 closes, from the export */ ],
    }
  ],
  "holdings": [
    { "tk": "EGAL", "qty": 11, "avgPrice": 328.015, "price": 317, "value": 3487, "pnl": -121.17, "pnlPct": -3.36,
      "sector": "Basic Resources", "is_fund": false,
      "action": "hold | tighten | sell | exit | add", "stop": 0, "target": 0,
      "plan": { /* only for add */ }, "reasons": [], "news": [], "analysis": { /* EGX.get(tk) */ } }
  ]
}
```

## v3.1 fields (atomic-step ledger)
The ledger itself is `run.ledger.jsonl` next to `run.json` (written only by `egx.py step ...`, hash-chained, never edited). `egx.py step start` moves an old `run.json` to `run.prev.json`. The step checks read these fields:
```jsonc
{ "meta": { "egxjs": "3.3.1" },                 // the export's egxjs
  "calls": [["market", null, 1762800000000, 1]], // the export's call log, pasted as is: [fn, ticker, time ms, ok]
  "stocks": [{
    "red_events_checked": { "query": "\"Company\" disclosure site:egx.com.eg", "found": false, "url": null },
    "news": [{ "material": false, "fresh": true, "summary": "one line" }],   // all three required on every item
    "vs_last": "first check",                    // what changed since the last call in memory, and why
    "t0_eligibility": { "status": "confirmed|unknown", "how": "EGX list dated 2026-11-01 / T0 option seen in ThndrX" }
  }],
  "holdings": [{ "news_queries": [], "news": [], "red_events_checked": {}, "screenshot": "", "analysis": { /* EGX.get(tk), with receipts */ } }],
  "market": { "macro": [], "macro_checked": true },
  // egx-scan
  "lists": { "top30": ["COMI", "..."], "hot": ["..."], "t0": [] },
  "lists_source": { "top30": { "kind": "official|market-cap", "url": "", "date": "" },
                    "hot_queries": [{ "kind": "corporate|global|industry", "query": "" }] },
  "unknown": ["tickers EGX.scan could not read"] }
```
Written by `egx.py report`, never typed: `steps` (the ledger summary shown in the report and kept in memory), `report_files` (html, pdf, pdf_error, the Drive plan), `check_incomplete` on a holding whose steps are not all proven.

## v3 fields (strict mode)
```jsonc
{ "stocks": [{
    "receipts": { "open": {}, "analyse": {}, "draw": {}, "verify": {} },   // pasted from the export, never typed
    "news_queries": [{ "query": "\"COMI\" site:arabfinance.com", "results": 4 }, { "query": "التجاري الدولي البورصة", "results": 3 }],
    "news": [{ "title": "", "url": "", "source": "Arab Finance", "tier": 2, "date": "YYYY-MM-DD", "opened": true,
               "paywalled": false, "impact": "+|0|-", "material": false, "summary": "" }],
    "category": "top30|hot|t0",         // egx-scan: which list it was ranked in (report section + memory)
    "rank": 1,                          // place inside its category (1-3)
    "quick": true,                      // quick-scan row only -> verdict "unchecked", never funded
    "mode": "t0", "t0_eligible": true,  // check TICKER T0; eligibility confirmed with a source or the ThndrX T0 option
    "t0": { "plan": {}, "receipts": {}, "screenshot": "/path/5min.jpg" },
    "override": { "verdict": "wait|not_valid", "reason": "", "wait_for": "" }   // Claude may only downgrade
}],
  "catalysts": [{ "tk": "", "type": "", "status": "confirmed|rumour", "sources": [{ "url": "", "date": "", "source": "", "tier": 1, "opened": true }] }] }
```
`meta.t0_status` (egx-scan) says why the Same-day list is empty, e.g. "Skipped: market closed".
`verdict`, `verdict_by`, `auto_reasons`, `gates` and `wait_for` are written by `egx.py verdict`; never type them.
`egx.py report` also writes the memory files (`history.jsonl`, `news.jsonl`, `runs.jsonl`), copies screenshots to `shots/`, makes the PDF and prints the Drive upload plan.

Rules enforced by `egx.py check` (the report refuses to build otherwise; there is no `--force`):
- the run has a step ledger with an intact hash chain, and every run-level atomic step that blocks the report is recorded and still true;
- every verdict was computed by `egx.py verdict` and still matches the rules; overrides only downgrade, with a reason;
- every stock that is not dropped / unchecked passes the 8 gates (the 8th, `steps`, is the atomic-step ledger of that ticker), or it is ⏳ with the failed gate named:
  open (header shows the ticker) · analyse (page script v3, 60+ bars) · news (2+ searches, one Arabic and one English, every item on the whitelist in `news-sources.md`, opened and dated from the page) · draw (every planned mark made, MA50/MA200 present, every dated red event drawn) · verify (`EGX.verifyChart` ok after the last draw) · screenshot (JPEG/PNG of the chart whose file time is after the verify and within 30 minutes) · verdict;
- a confirmed corporate catalyst (merger, acquisition, tender offer, capital increase, contract) has an EGX source or two Tier-2 sources; otherwise `status: "rumour"`;
- `valid` is impossible when the chart script dropped the stock or R:R < 2 (T0: also net R:R < 1.5 or a move under 3x the round-trip fees).

`egx.py allocate` adds `allocation` (shares, values, risk, fees, gain/loss, break-even) and
never sizes a plan under 2:1. The report embeds the whole run file as JSON, so later
`egx.py read FILE --ticker TK` returns exactly what was decided and why.

Allocation v3.3 uses `meta.cash` as currently available buying power (exclude pending/reserved funds). Missing cash prevents sizing. `allocation.deployed` includes swing and T0 entry values and buy fees. `risk`, `total_risk` and `open_risk_after` include modeled fees/slippage; they are estimates, not worst-case loss guarantees. Each funded row carries `rr_net_sized`.
