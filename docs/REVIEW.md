# Technical and trading-method review

Reviewed 11 November 2026 against the working tree, including pre-existing uncommitted v0.4 changes. This revision is plugin v0.5.0 / script v3.3.0. No live account, orders, Drive uploads or Sheet writes were used in this review.

## Assessment

The strongest part of this project is the separation between browser observations, deterministic calculations and a recorded workflow. The principal weakness was that completion of the workflow could look like permission to trade: `wait` records could receive money, and reported risk understated the costs used in the loss scenario. Those are corrected below.

The project remains a rule-based research assistant. There is no evidence here establishing profitable expectancy. More indicators or stricter paperwork do not establish an edge. Keep the Claude workflow, but require a current, complete signal and affordable risk before presenting a funded plan.

## Findings and implemented changes

| Priority | Finding | Change |
|---|---|---|
| High | `include_wait_orders` allowed allocations to signals waiting for evidence, news, eligibility or trend checks. | Only `valid` stock signals are funded. Wait is watchlist only; the old flag is ignored with an explanation. Holding additions require a valid underlying analysis and no incomplete check. |
| High | Shares were limited by entry-minus-stop, while fees and slippage were added only after sizing. | Binary search limits shares using exact entry fees and estimated stop-fill loss, including exit fees and configured slippage. Per-trade and aggregate risk budgets use that modeled loss. |
| High | Each T0 idea could reuse the full amount already reserved for swing ideas. T0 exposure did not consume stock/sector caps. | All proposed allocations reserve the same cash, stock, sector and open-risk budgets. This is deliberately conservative; sequential reuse requires a new observation of available cash. |
| High | Cash shortages produced warnings rather than constraining the plan. Missing holding stops counted as zero risk. | Available cash constrains allocation; missing cash blocks sizing. A non-fund holding with value but no quantifiable stop risk blocks additional allocation. |
| High | `risk_pct: 0` silently fell back to the configured nonzero default. | Zero is preserved. Non-finite/negative sizing inputs and fee assumptions are rejected. |
| High | Report generation could reuse a previously stored allocation after rules or inputs changed. | The report recalculates allocation every time. |
| High | Net R:R was assessed using the run amount rather than the final quantity. | Actual-size net reward/risk, including modeled stop slippage, is required before funding. Gross R:R may pass while the position remains unfunded. |
| High | Version instruction required 3.1, receipts expected 3.2, and test fixtures mixed versions. | Skill, ledger manifest, receipt checks, fixtures and built loader aligned to 3.3.0. |
| High | Tests crashed before exercising the workflow; the analysis harness printed errors without failing. | Fixed missing import and stale fixture checksums. Added assertion-based JS tests and dedicated risk/report regression tests. |
| High | T0 exit at 14:20 crossed the broker's documented 14:15 market-order cutoff. | Strategy exit moved to 14:10 across code and instructions. This is a planned exit time, not an execution guarantee. |
| Medium | Swing stock returns could be compared with a partial or differently dated benchmark. JS subtraction also coerced null returns. | EGX30 excludes the current daily bar during an observed open session. Relative strength requires matching start/end dates and known values. Failed index opening clears cached benchmark state. |
| Medium | Target selection could skip the nearest resistance when it failed a distance filter. | Select the first qualifying resistance above entry, then let the reward/risk and target checks reject inadequate upside. |
| Medium | Weekly anchor calculation used Saturday; flat-price RSI returned 100. | Sunday anchor and neutral RSI 50 for a flat series. The week anchor correction usually leaves Sun–Thu membership unchanged but fixes its date convention. |
| Medium | Malformed OHLCV and duplicate timestamps reached indicator calculations. | Reject invalid prices/ranges, negative volume, non-finite values and non-increasing timestamps. |
| Medium | A recent T0 receipt could describe a previous session. Missing/invalid plan geometry could reach verdict/ranking code. | Compare session date with the receipt's Cairo date; require finite `0 < stop < entry < target`; invalid plans cannot crash ranking. |
| Medium | Setup history displayed a hit percentage from today's support and target applied to past bars. | Mark it explicitly retrospective and non-predictive; remove the implied hit-rate judgment. |
| Medium | Global HTML entity decoding could undo escaping; source links accepted active URL schemes. | Preserve escaping and allow only HTTP(S) links. Regression tests cover both. |
| Medium | Report proof counts counted skipped/open steps as script-proven. | Count only completed script checks; Claude entries and attestations remain separate. |
| Medium | Report presentation obscured allocation, risk and conditions; T0 cards showed the daily quote. | Responsive research brief, scenario P/L and sized net R:R, watchlist state, expandable evidence, intraday quotes, coverage gaps, Arabic text support, keyboard focus, A4 print styling and explicit synthetic-preview labeling. |

## Important limits still present

1. **No validated strategy performance.** Setup history contains look-ahead (current zones), overlapping outcomes and no realistic fills. Its new label is a correction to interpretation, not a replacement backtest. Scores are ranking heuristics, not probabilities.
2. **Live integration is unverified in this review.** ThndrX selectors, export schema, symbol matching, holdings parsing, drawing persistence and screenshot timing need a supervised read-only live check. Tests use mocked charts and synthetic fixtures.
3. **Calendar and freshness remain incomplete.** Receipt freshness is not market-data freshness. There is no maintained exchange holiday/short-session calendar. A shared stale stock/index endpoint can still produce RS. Five-minute bars may include an unfinished current candle; opening-range data may be incomplete or interrupted. Do not promote a T0 idea without independently confirming session state and closed-bar timing.
4. **Corporate actions and universe bias.** Adjustment policy is not established by `exportData()`. Splits, dividends, capital increases and missing/delisted stocks can distort levels and historical evaluation. A dated official universe and event adjustment policy are needed.
5. **Local provenance is not authentication.** Checksums cover selected values, and a local hash chain detects changes relative to its own content. Neither prevents a writer from recomputing it. News `opened` flags, classifications and many workflow proofs remain Claude-supplied. The report must not call these independently verified facts.
6. **Execution losses can exceed the model.** ATR slippage is a scenario assumption. Stops can gap, fail to fill, or be unavailable for unsettled holdings. No depth/participation sizing or correlated-sector stress model exists. Existing holding risk uses its supplied stop and ATR when available; missing ATR is not an independently estimated gap allowance.
7. **External settings are not automatically trustworthy.** Fees, subscriptions and settings copied from Sheets require current verification and consistent application to the active config. The fallback USD/EGP assumption is now disclosed when used; it is not a current quote. No fee schedule was certified in this review.
8. **Outcome accounting is simplified.** Bar touches do not prove an order filled, and intrabar entry/stop ordering may be ambiguous. Memory outcomes should remain separate from the broker's executed-trade P/L. Holding additions now require a valid analysis; incomplete legacy holding records may therefore remain unfunded.
9. **The ledger is long and expensive.** Preserve the checks that protect money and provenance, but measure tool calls and latency on actual Claude runs before simplifying it. The current implementation still requires some manual transfers between browser exports, run JSON and connectors. Do not claim that all steps are automated.

## Next validation work, in order

- Run one swing check, one failing-evidence case and one session-eligible T0 check in Claude with read-only access. Confirm that a failed check cannot receive money and that changed inputs regenerate the allocation. Verify the account's available cash and sell eligibility explicitly.
- Add a current exchange-session calendar, bar-completion/freshness policy, and explicit adjustment metadata. Replace placeholder/hand-curated universe assumptions with dated sources.
- Freeze one simple setup and test it chronologically on held-out EGX data. Include spread, fees, queue/fill assumptions, settlement delay, corporate actions, halts and delisted names. Report net expectancy, maximum drawdown, turnover, exposure and sensitivity to slippage, including losing periods. Do not tune on the holdout period.
- Forward paper-log signals and fills separately, then compare predicted and realized slippage and risk. Only claim an edge after enough independent observations and a documented validation method.

## Broker documentation consulted

[Thndr order types](https://support.thndr.app/en/articles/640388-egx-stock-order-types-market-limit-stop-sell-advanced): market orders are not accepted from the pre-close phase beginning at 14:15; price bands and settlement availability vary. This supports the earlier exit policy and checking actual sell eligibility.

[Thndr wallet balances](https://support.thndr.app/en/articles/640608-how-to-read-your-thndr-wallet-activities-balances-transfer-statuses): investing availability differs from withdrawal settlement, and pending funds are reserved. Allocation therefore uses currently available buying power rather than prospective proceeds.

## Validation and preview

- `python3 tests/test_egx.py`: 32 end-to-end synthetic workflow tests.
- `python3 tests/test_risk.py`: 13 focused regression tests.
- `node tests/test_chart.js`: assertions for analysis, malformed data and non-predictive history.
- `node tests/test_chart_draw.js`: mocked drawing, verification, T0 and exported call log.
- Rendered the report in Chrome at 1440px, 390px and 320px; checked horizontal overflow and evidence expansion, and checked evidence visibility under print media. These checks do not test the live broker.
- `python3 tests/render_preview.py` rebuilds [the synthetic HTML preview](../examples/report-preview.html). It writes no trading memory. The preview intentionally changes illustrative prices/cash to show a funded scenario; it is not a real signal or a reproduction of current market conditions.
