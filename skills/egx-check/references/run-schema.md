# Run file (`run.json`) -> HTML report

Every command ends by writing one run file and calling
`python3 scripts/egx.py report run.json`. Most of the file is pasted straight from the
browser (`EGX.exportToPage(...)` read with get_page_text, or `EGX.exportRun(...)` for short output); Claude only adds verdicts, reasons and news.
See `examples/sample-run.json` in the repo for a complete example.

```jsonc
{
  "meta": {
    "command": "Loop 30",            // Check | Market | Positions | Scan | Scan Max | Scan Spec | Scan Max Spec | Scan T0 | Scan T0 Max
    "created": "2026-11-08T21:30",   // local time to the minute (egx.py fills it if missing)
    "trading_day": "2026-11-09",
    "amount": 15287,                 // money to invest now (0 for Check / Positions)
    "equity": 50858.16,              // account value (Settings tab or ThndrX)
    "cash": 250.24,                  // EGX.page().cash
    "risk_pct": 2,                   // from Settings
    "include_wait_orders": true,     // also size ⏳ picks as limit orders
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
      "votes": { "trend": { "verdict": "Valid", "confidence": 4, "facts": [] } }   // Scan Max: per-lens "score" 1-10 replaces "verdict"
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

Rules enforced by `egx.py check` (the report refuses to build otherwise, unless `--force`):
- every news item and catalyst has a `url` and a `date`;
- every deep-checked stock (valid / wait / not_valid) has news (or `news_checked: true`) and a `screenshot` of the drawn chart (the file must exist); `market.screenshot` (EGX30) is optional;
- `valid` is impossible when the chart script dropped the stock or R:R < 2.

`egx.py allocate` adds `allocation` (shares, values, risk, fees, gain/loss, break-even) and
never sizes a plan under 2:1. The report embeds the whole run file as JSON, so later
`egx.py read FILE --ticker TK` returns exactly what was decided and why.
