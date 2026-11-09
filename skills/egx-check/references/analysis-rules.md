# Analysis rules (what `scripts/egx_chart.js` computes)

Claude does not re-derive any of this by hand. The script reads the ThndrX chart's own
`exportData()` (300 daily bars) and returns the numbers below, each level with the bar
dates it came from. This file is the human-readable spec; if you change a rule, change
`egx_chart.js` too, bump its `VERSION`, and run `python3 scripts/build_loader.py`.

## Data
- 300 daily bars (OHLC + volume) of the stock open on the chart.
- Fewer than 60 bars = new listing -> `drop: "new"`.

## A. Trend
- **Pivots**: a swing high/low is higher/lower than the 3 bars on each side, searched in the last 130 bars. The last 2 highs and 2 lows are reported with dates.
- **Daily trend**: higher highs + higher lows = `up`, lower highs + lower lows = `down`, else `side`.
- **Weekly trend**: weekly bars built from the daily ones (EGX week starts Sunday). `up` = close > 10-week MA > 30-week MA and the 30-week MA rising over 4 weeks; mirror for `down`; else `side`; under 34 weeks = `unknown`.
- **MAs**: MA20, MA50, MA200; `stack` bull / bear / mixed; MA50 slope = % change vs 20 bars ago.
- **Stretch**: (close - MA20) / ATR. Above 2 = "stretched, do not chase" flag.

## B. Support and resistance
- **Zones**: all pivots sorted by price; a pivot joins the current zone when it is within `2 x max(1.5% of price, 0.5 x ATR)` of the zone's low. A zone needs 2+ touches.
- **Support** = the highest zone with 2+ touches, top <= 1% above the close, and not broken. **Broken** = any close in the last 15 bars below zone low - 0.5 x ATR (it is then listed as "broken support now resistance"). If no zone qualifies, the last swing low below the price is used and marked weak (1 touch).
- **Resistance** = zones starting more than 0.5% above the close (nearest first).
- Also reported: 300-bar high/low, last swing low, round numbers within 1 ATR.
- **Trendline**: through the last 2 swing lows if rising and no close broke it by more than 0.25 ATR; otherwise through the last 2 swing highs if falling (`falling-highs`).

## C. Momentum
- RSI 14 (Wilder): value, zone (<30 oversold, >70 overbought), rising vs 3 bars ago.
- Divergence: bullish = lower price low with higher RSI low at the last 2 swing lows; bearish = mirror at highs.
- MACD (12, 26, 9): histogram value and any signal cross in the last 5 bars (with date).

## D. Volatility
- ATR 14 (Wilder) in EGP and % of price.
- Bollinger (20, 2) width; **squeeze** = width in the lowest 20% of the last 120 bars.

## E. Volume and liquidity
- Last bar volume / 20-day average.
- Up-day vs down-day volume over 20 bars (accumulation when up > down).
- Average daily value traded (close x volume, 20 days). Under EGP 5M = `thin`.

## F. Patterns and candles
- Candles in the last 3 bars: at support (low within 1 ATR of the zone top) hammer, bullish engulfing, inside-bar break; near resistance shooting star, bearish engulfing.
- Breakout: a close crossing above a 2+ touch zone in the last 5 bars on >= 1.5x average volume, price still above it.
- Double bottom: last 2 swing lows within 0.5 ATR. Higher low at support.

## G. Relative strength
- Stock % change over 20 and 60 bars minus EGX30's (EGX30 is read once per session by `EGX.market()`).

## H. Plan
| Setup | Entry | Stop |
|---|---|---|
| breakout-retest (a breakout exists) | top of the broken zone | min(zone low - 0.5 ATR, entry - 1 ATR) |
| pullback-at-support (close within 1.5 ATR of support top) | last close | min(support low - 0.5 ATR, entry - 1 ATR) |
| pullback-limit (further away) | support top + 0.2 ATR | same |

- **Target** = 0.995 x the low of the FIRST resistance zone more than 1% above the entry (a zone is never skipped); with no resistance zone above at all, 0.995 x the 300-bar high; else none. The target must be more than 1% above the last close, otherwise the plan is `invalid` (the next resistance is in the way). **Target 2** = the next zone.
- Prices are rounded to ticks (0.01, or 0.001 under EGP 1).
- `rr` = (target - entry) / (entry - stop); `stopATR`; `entryDistATR` = (close - entry) / ATR; `fillSoon` = within 2 ATR.

## Drop reasons (first that applies)
`no-plan` (no support) · `limit` (|day change| >= 18%, inside the last 2% of the +/-20% band) · `thin` · `invalid` (no target above the price) · `rr` (< 2) · `wide` (stop > 3 ATR) · `noise` (stop < 1 ATR, cannot happen after the 1 ATR floor) · `new`.

## I. Chart score 0-10
trend 0-2 (daily up, weekly up) · RS 0-2 (RS20 > 0, RS60 > 0) · R:R 0-2 (>=3 -> 2, >=2 -> 1) · volume 0-1 (accumulation or breakout) · momentum 0-1 (RSI 40-65 rising, bullish divergence or MACD bull cross) · catalyst 0-1 (passed in by Claude after the news check) · regime 0-1 (EGX30 Up).
The score ranks; it never makes a verdict by itself.

## Setup history (deep checks)
Over the 300 bars: every time the low came within 0.25 ATR of today's support top and the close held above its low, simulate an entry at that close, a stop at support low - 0.5 ATR and a target at the same distance as today's plan. Count which came first within 15 bars (next try at least 5 bars later). Under 3 tries = "too few to judge".

## Market regime (EGX30)
Up = close above a rising MA50 and above MA200. Down = close below a falling MA50 and below MA200. Anything else = Correction.

## Drawing and verify (gates 4-5, `EGX.draw` / `EGX.verifyChart`)
- Run only after the news gate, so event dates can be drawn. Chart must show the ticker on 1D.
- Clears every mark labelled `EGX·` (only those), then draws, each labelled `EGX·TICKER ...`:
  support box (orange, from the first touch, extended right; zones thinner than 0.2 ATR are padded 0.1 ATR each side), up to 2 resistance boxes (red), the first broken-support box (red, dashed border), entry (blue), stop (red), target (green), target 2 (green dashed), trendline (orange), red-event vertical lines (red dashed) and catalyst lines (purple) from `events`.
- Adds MA50 and MA200 indicators only if no Moving Average with that length is already on the chart.
- Every mark's id is stored per ticker. `verifyChart` reads each one back and fails on: wrong ticker or symbol changed, wrong resolution, a mark missing, a price off by more than max(1 tick, 0.1%), an event line not on its date, an `EGX·` mark that is not from this check, MA50/MA200 missing. Its receipt time is the earliest moment a valid screenshot can be taken.

## T0 (`EGX.intraday`, `EGX.drawT0`)
- Runs the daily analysis on 1D first (daily support / resistance, liquidity), then switches the chart to 5 minutes. Call `EGX.daily()` after the screenshot.
- Today's session = 5-minute bars on the last bar's Cairo date. Fewer than 6 bars = `drop: "early"` (opening range not complete).
- VWAP (typical price x volume, cumulative from the open), opening range = first 6 bars (30 min), ATR5(14) and RSI5(14) on 5-minute bars, relative volume = today's volume so far vs the same number of bars in earlier sessions (needs 3 sessions, else unknown), day change vs EGX30 (`EGX.market()` today), share of bars closing above VWAP.
- Setups, first that fits: **opening-range breakout** (a 5-min close above the range high on volume above the previous 6 bars, price above VWAP and the range high; entry = range high; stop = the tighter of range high - 0.3 ATR5 and VWAP, at least 1 ATR5 below entry) · **VWAP pullback** (above VWAP on >= 70% of bars, last bar low within 0.25 ATR5 of VWAP and closing above it; entry = VWAP; stop = VWAP - 1.25 ATR5) · **daily-support bounce** (last bar low within 0.25 ATR5 of the daily support top, green bar closing above the previous high; entry = last close; stop = support low - 0.25 ATR5, at least 1 ATR5).
- Target = the nearer of the day's high and the next daily resistance (above the entry); entry + 2R only when neither is above the entry. R:R must still be >= 2. Drops: `limit` (|day change| >= 17%), `thin` (daily average value < EGP 20M), `spread` (> 0.3%), `rr` (< 2), `no-setup`, `early`.
- Marks (`EGX·T0 TICKER ...`): opening-range box, VWAP, entry, stop, target, nearest daily support and resistance. Exit by 14:20, no new entry after 13:30.
