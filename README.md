<div align="center">

# EGX ThndrX Trading

**Claude skills that analyse Egyptian Exchange (EGX) stocks inside ThndrX, draw the plan on your chart, check the news, review your positions and hand you a beautiful, evidence-packed HTML report.**

You place every order yourself. The skills only read and draw.

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![No dependencies](https://img.shields.io/badge/dependencies-none-30d158)
![macOS | Windows](https://img.shields.io/badge/install-macOS%20%7C%20Windows-0a84ff)
![Claude](https://img.shields.io/badge/Claude-skills-d97757)
![License: MIT](https://img.shields.io/badge/license-MIT-8e8e93)

<img src="docs/images/report-desktop.png" alt="Report on desktop" width="68%"> <img src="docs/images/report-mobile.png" alt="Report on a phone" width="24%">

</div>

---

## What you get

| Command | What it does |
|---|---|
| **`check COMI`** · `افحص COMI` | Scripted chart analysis (trend daily + weekly, zones with touch dates, RSI + divergence, MACD, ATR, Bollinger squeeze, volume, patterns, relative strength vs EGX30), a plan with entry / stop / target, lines drawn on your ThndrX chart, order book, financials, dated news, a ✅ / ⏳ / ❌ verdict and the exact order-ticket steps. |
| **`my positions`** · `راجع مراكزي` | Every stock you hold gets **hold / tighten stop / sell / add**, with evidence. |
| **`Scan`** | Positions review, a market-wide **news & catalyst scan** (mergers, acquisitions, tender offers, expansions, contracts, bonus shares), a scan of the top 30 stocks, deep checks on the best 5, and a split of the amount you want to invest with risk, caps and fees. |
| **`Scan Max`** | Full technical, fundamental and chart analysis of **every** top-30 stock, **five independent analyst scores** on the best 8 and a verifier, then **always the best 3 ranked** by expected gain vs risk with an A/B/C grade. Heavy on usage. |
| **`Scan Spec`** | Looser speculation rules on top of Scan or Scan Max (`Scan Max Spec`): relaxed grades, entries up to 1.5 ATR above support, R:R 2.0 gross / 1.6 net, a 10-trading-day time stop, and risk as a % of the amount you give for the run. |
| **`Scan T0`** · **`Scan T0 Max`** | Same-session (T+0) scan on T+0-eligible stocks: 5-minute opening-range breakout, VWAP pullback or daily-support bounce, no entries after 13:30, forced exit at 14:20, max 2 trades a day and a daily loss brake. Max adds five analyst scores, a verifier and a price re-check under a 25-minute budget. |
| **`market`**, **`monthly`**, **`اشتريت … / بعت …`**, **`قلت ايه عن HRHO؟`** | Market regime, monthly results vs your fixed costs, trade logging to Google Sheets, and instant search of past reports. |

Every run saves **one self-contained HTML report** styled like ThndrX:
- a dark, RTL Arabic (or English) layout with Apple-style typography and a translucent header;
- an **animated recap** made with [HyperFrames](https://github.com/heygen-com/hyperframes), which can also be rendered to an MP4 you can share;
- KPI cards, an allocation table, a card per stock with a candlestick chart and the plan levels, plus the ThndrX screenshot;
- **collapsible evidence**: chart evidence with bar dates, news with links and dates, order book, financials, analyst votes;
- the full run embedded as JSON, so Claude can answer "what did you say about HRHO last week?" without re-analysing.

Reports are named `EGX_<Command>_<YYYY-MM-DD>_<HH-MM>.html`. An `index.csv` next to them (tickers, verdicts, holdings actions, catalysts, regime …) lets Claude find the right file without opening any.

## Quick start

```bash
git clone https://github.com/tarekfouad97/egx-thndrx-trading.git
cd egx-thndrx-trading
```
- **macOS**: double-click `Install-Mac.command` (or `bash install.sh`)
- **Windows**: double-click `Install-Windows.bat`

The installer installs Python if needed, asks a few settings, creates your reports folder and builds `dist/egx-thndrx-trading.plugin`. Drag that file into the Claude app, install [Claude in Chrome](https://claude.ai/chrome), sign in to [ThndrX](https://x.thndr.app) in Chrome, and say **`check COMI`**.

Full guide: **[docs/SETUP.md](docs/SETUP.md)** · Phone: **[docs/PHONE.md](docs/PHONE.md)** · Internals: **[docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)**

## Why it is fast and cheap on tokens

Claude does not eyeball charts or work out levels in its head:

- **`egx_chart.js`** runs inside the ThndrX tab. It opens tickers through the search box, reads 300 daily bars from the chart's own `exportData()`, computes every indicator and the plan, and draws the lines. It returns **one line per stock** and scans 8 stocks per call (6 stocks in about 9 seconds in testing). It is cached in the tab, so later sessions load it with one line.
- **`egx.py`** (Python standard library only) does the sizing, caps, Thndr fees, monthly break-even, the HTML report, `index.csv` and report search.

The rules are written down in [`analysis-rules.md`](skills/egx-check/references/analysis-rules.md), so every verdict can be explained.

## Safety

- **Never trades**: no buy / sell / confirm / modify / cancel clicks, nothing typed in the order ticket.
- **Read-only** on your account; draws only its own `EGX·` chart lines.
- **No login work** and **no private API calls**, only what ThndrX shows.
- **Evidence or "unknown"**: levels carry bar dates, news carries source, link and date.
- **Education, not investment advice.** Your money, your decisions.

## Repository layout

```
.claude-plugin/plugin.json          plugin manifest
skills/
  egx-check/                        check, market, positions, log, monthly, history
    SKILL.md
    config.example.json             copied to config.json by the installer (git-ignored)
    scripts/egx_chart.js            in-page analysis + drawing (source)
    scripts/egx_chart.loader.js     minified, self-caching build
    scripts/build_loader.py
    scripts/egx.py                  fees, allocate, report, index, search, read, history, check
    references/                     analysis rules, run-file schema, ThndrX UI notes
  egx-scan/SKILL.md                 Scan, Scan Max, Scan Spec, Scan T0 (modes combine)
templates/EGX_Trade_Log_template.xlsx   blank trade log for Google Sheets
examples/sample-run.json            synthetic run used by the tests and screenshots
tests/                              node + python tests
install.py · install.sh · install.ps1 · Install-Mac.command · Install-Windows.bat
docs/                               setup, phone, how it works
```

## Development

```bash
node tests/test_chart.js                 # chart script on synthetic series
python3 tests/test_egx.py                # sizing, report, index, search, read
python3 skills/egx-check/scripts/build_loader.py   # after editing egx_chart.js (bump VERSION)
python3 install.py --build-only          # rebuild dist/
```

---

<div align="center">

Made with ❤️ by **Tarek Fouad** · [tare2fo2ad@gmail.com](mailto:tare2fo2ad@gmail.com) · [github.com/tarekfouad97/egx-thndrx-trading](https://github.com/tarekfouad97/egx-thndrx-trading)

<sub>Not affiliated with Thndr, EGX or Anthropic. Analysis, not investment advice.</sub>

</div>
