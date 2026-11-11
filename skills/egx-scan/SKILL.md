---
name: egx-scan
description: "EGX many-stock scan on ThndrX: \"Scan\" / \"لف على الـ 30\" / \"اعمل سكان\". Reviews positions, builds three lists (Top 30, Hot stocks moved by mergers, global demand or urgent industry news, and Same-day T0 during the session), runs the full egx-check steps on the best of each, ranks the top 3 per list, splits the user's amount and saves one report (HTML + PDF) locally and to Google Drive. Runs as numbered steps split into atomic steps, each recorded with its proof in a script ledger; no ticker and no step can be dropped silently. The old names Loop 30, Scan Max, Scan Spec, Loop T0 all run this one Scan."
---

# EGX Scan

One mode, three lists. Load **egx-check** first and obey all its hard rules (never trade, read-only, no login work, no private API calls, proof not words, evidence, any failed gate or atomic step = ⏳, education not advice, **work only through the ledger**). Every stock that gets a verdict goes through egx-check's per-ticker steps (K1-K7, or the T0 steps); this skill only chooses the stocks, ranks them and splits the money. `$S` = `../egx-check/scripts`.

Old command names (Loop 30, Loop 30 Max, Scan Max, Scan Spec, Loop T0, Scan T0 Max) run this Scan; say once that the Max / Spec modes were retired.

## The ledger
`python3 $S/egx.py step start scan run.json` first; then the steps below in this order, with `step next` / `step done` / `step sync` as in egx-check ("The ledger loop"); `python3 $S/egx.py step finish` is the last tool call. Order of the whole run:

**N0 → C0 → N1 → C1 → H1 → K1-K6 per holding → H2 → M1 → N3 → N4 → N5 → N6 → K1-K7 (or T0 steps) per deep-checked stock → C7 → C8 → N7 → N8 → C9 → C10 → C11**

C, K, T, H and M steps are egx-check's, done exactly as written there. Run `step sync` after every list, batch and stock: it names anything not proven yet.

## Step N0. Before starting (one message, AskUserQuestion if available)
| ID | Do | Proof |
|---|---|---|
| N0.1 | Ask **the amount for this run** (required, never assume) and the trading day (default: the next EGX session, Sunday-Thursday) | you: the user's answer |
| N0.2 | Confirm that ⏳ picks remain watchlist only (`meta.include_wait_orders` is deprecated and ignored) and ask whether to run the Same-day T0 list. Warn once: a scan reads 30+ charts and runs many searches; it takes a while | you: the user's answers |

Risk per trade, fees and fixed costs come from the Settings tab (C0.2); never from memory.

## Step N1. Scan memory and cash (after C0)
| ID | Do | Proof |
|---|---|---|
| N1.1 | `python3 $S/egx.py runs --last 3` (what the last scans decided) | egx.py |
| N1.2 | `EGX.page()` -> `meta.cash`; if it is lower than the amount, say so first (deposit or redeem BWA / BMM) | script |

Then C1 (outcome tracking).

## Positions first
egx-check **my positions**: H1.1, K1-K6 for every held stock (`--tk H:TICKER`), H2.1, H2.2. Their value counts toward the 30% stock and 50% sector caps.

## Market
M1.1 (`EGX.marketPage()` on the market page; `EGX.market()` was C0.5), then:
| ID | Do | Proof |
|---|---|---|
| N3.1 | Macro items for the next 5 trading days (CBE decision, inflation print, holidays, results season) from Tier-3 sources -> `market.macro` (each with `url` and `date`); none found = `market.macro: []` and `market.macro_checked: true` | script |

## Step N4. The three lists
| ID | Do | Proof |
|---|---|---|
| N4.1 | **Top 30** -> `lists.top30`: the official EGX30 constituents with a dated source from the whitelist (search EGX first): `lists_source.top30: {kind: "official", url, date}`. None found: the 30 largest by market cap from the ThndrX heatmap, `kind: "market-cap"`, said clearly as "top 30 by market cap" | script |
| N4.2 | **Hot** -> `lists.hot`, last 14 days. Run all three kinds of search and log them in `lists_source.hot_queries` (`{kind: "corporate"\|"global"\|"industry", query}`); every hot ticker has a confirmed, sourced entry in `catalysts[]` | script |
| N4.3 | **Same day T0** -> `lists.t0`, or `meta.t0_status` with the reason it was skipped (e.g. "Skipped: market closed", "Skipped: after 13:30", "Skipped: user declined") | script |

**Hot** details (every candidate also gets `hot: {reason, type, date, sources, priced_in}`):
- *Corporate events*: merger, acquisition, tender offer, capital increase, big contract, license, expansion, bonus shares, buyback. Queries: the Hot templates in `../egx-check/references/news-sources.md`. A confirmed corporate event needs an EGX disclosure or two independent Tier-2 sources; otherwise it is a rumour and cannot make a stock Hot.
- *Global demand*: the themes in `references/themes.md`; a theme is live only with a dated Tier-3 trigger; its tickers join the list.
- *Urgent industry*: government decisions, tariffs, export bans, subsidies (urgent-industry templates); map them to the sector and its tickers. The sector pulse is a hint, never a reason alone.
- Only stocks with average value traded >= EGP 5M a day. A Top-30 stock with a hot reason is listed under Hot (note "EGX30" in its reasons), never twice.
- Every hot reason goes to `catalysts` (`tk, type, summary, direction, status, sources[], date`, later `moved_pct`, `moved_atr`, `priced_in`: moved > 2 ATR since the date = priced in; a tender offer caps the upside near the offer price).

**Same day T0**: only when it is Sunday-Thursday between 10:15 and 13:30 Cairo time **and** the user wants it. Start from the most-active list and the watchlist (about 20 names): T+0-eligible (egx-check T1.2), average value >= EGP 20M and today's value on pace.

## Step N5. Quick filter (scripted)
Swing lists, batches of 8 per `javascript_tool` call: `const out=[]; for (const tk of [...]) out.push(await EGX.scan(tk, {catalyst: HOT.includes(tk)})); out.join('\n')`. One line each: trend, RS, entry, stop, target, R:R, stop ATRs, distance, value traded, chart score, `DROP:` reason.
| ID | Do | Proof |
|---|---|---|
| N5.1 | Every ticker of `lists.top30` and `lists.hot` was scanned and is in `stocks[]`, or is in `unknown[]` (`UNKNOWN` lines: never fill their numbers; a themes.md ticker that is UNKNOWN is reported as "not found, fix themes.md"). No ticker may vanish | script (lists against stocks, unknown and the call log) |
| N5.2 | Scanned stocks that are not deep-checked carry `quick: true` (verdict "unchecked", never funded); drops keep their `drop` (verdict "dropped") | script |

Order the survivors per list for the deep check: daily trend up and RS20 and RS60 positive first, then an unpriced hot reason, then R:R, then distance to entry, ties by chart score.

## Step N6. Deep check, best 3-5 per list
| ID | Do | Proof |
|---|---|---|
| N6.1 | `python3 $S/egx.py step add <the best 3-5 survivors of Top 30 and of Hot>` and `python3 $S/egx.py step add --block t0 <the best 3 of the T0 list>`; set `category` (`top30` / `hot` / `t0`) on each (and `hot` for Hot ones). Fewer only if fewer survived | script (at least min(3, survivors) per list) |

Then, for each added stock: egx-check K1-K7 in full (T0 stocks: K1, T1, T2, K3, T4-T6, K7 with `"mode": "t0"`). Keep everything in one `run.json` (`meta.command: "Scan"`), with `holdings`, `catalysts`, `market`, `lists`. Then C7 (export, `clearExport`, meta) and `step sync`.

## Verdicts and ranking
C8.1-C8.3 (`python3 $S/egx.py verdict run.json`: gates, atomic steps and verdict for every stock; downgrades only through `override`), then:
| ID | Do | Proof |
|---|---|---|
| N7.1 | The ranking inside each list was written by `verdict` (✅ first, then net R:R after fees x chart score / 10, ties by an unpriced hot reason). It prints `ranking: top30: #1 ... \| hot: ... \| t0: ...`. Show the top 3 of each list | script |

## Step N8. Money
| ID | Do | Proof |
|---|---|---|
| N8.1 | `python3 $S/egx.py allocate run.json` (never size by hand) | egx.py |

It funds only ✅ picks, across all lists, by chart score and R:R; it applies the risk % from Settings, the 30% stock and 50% sector caps (holdings included), the EGP 2,500 minimum order, fees, and half the amount in Correction / Down (the user may override with `meta.half_deploy: false`). T0 picks reserve the same cash, stock, sector and open-risk budgets as swing picks. Never assume future sale proceeds are already available. Unknown cash or unquantified holding risk blocks new allocation. Fees and configured stop slippage count toward risk; actual-size net R:R must pass. Whatever is not allocated stays cash, with the reason; add a gap-risk line for any pick with a red event before its order expires.

## Report, Drive, log, finish
- C9.1-C9.5: `check`, `report --out <reports folder>`, the PDF, the Drive plan (create / replace / skip, `drive-record`), send the files. One report for the whole scan; the memory files get one line per stock.
- C10.1: one Recommendations row per deep-checked pick, Command = "Scan " + list (e.g. "Scan Hot"), Notes = rank, shares, amount, report name. Never log quick-scan rows.
- C11.1: `python3 $S/egx.py step finish`.

## Answer (Egyptian Arabic, phone-sized, title "Scan")
1. Market line: EGX30 regime with numbers, breadth, macro items.
2. Positions: one line each (action + why).
3. Catalysts and themes found: 3-5 lines with source, tier, date, priced in or not.
4. Per list (Top 30, Hot, Same day): the top 3 with verdict, the checklist line, entry / stop / target, R:R, shares and EGP, and one line why; T0 status when skipped.
5. Cash left and why; costs to cover; the cash warning if any.
6. ThndrX steps for each pick the user may place (egx-check answer); T0 exit steps; the T+2 note.
7. Dropped stocks grouped by reason; UNKNOWN tickers.
8. The `step finish` summary lines exactly as printed (steps proven by scripts, steps stated by you, every ✘).
9. The report name, where it is saved (local, Drive), and the closing line.
