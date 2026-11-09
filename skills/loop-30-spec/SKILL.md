---
name: "loop-30-spec"
description: "\"Loop 30 Spec\" / \"لف على الـ 30 مضاربة\": Loop 30 Max with looser speculation rules (3/5 consensus, one-period RS, entries near price, user-set risk up to 10% of the invested amount). Use only when the user names it."
---

# Loop 30 Spec (speculation mode)

Run only when the user says "Loop 30 Spec" or "لف على الـ 30 مضاربة". It is **loop-30-max** with the looser rules below. Load **egx-thndrx-trade-check**, **loop-30** and **loop-30-max** first and follow every step and hard rule of theirs (never trade, read-only on the account, no private API calls, evidence with dates, chart + analysis + news for every verdict, the five analyst passes and the verifier, education not advice). Where this skill says something different, this skill wins.

## 0. Before starting (adds to loop-30-max step 0)
- Ask in the same message: the amount to invest, the trading day, and the **risk per trade for this run** (suggest 3%; allowed range 1-10%). **The risk % is a percentage of the amount the user gives for this run (the invested amount), not of his total equity.** Example: amount 3,710 at 10% = max loss EGP 371 per trade, including fees.
- If he picks more than 5%, show once what 5 losing trades in a row would do to the invested amount: amount x (1 - risk)^5 (at 10% that is -41%, e.g. 3,710 -> 2,191). Then use the number he chose.
- **Monthly brake:** read the Monthly tab. If this month's net P/L is already at or below -15% of the month's starting capital, say so and give analysis only (all verdicts at most ⏳) until he says otherwise in chat.
- Label everything in the answer "مضاربة" so it is never confused with a Loop 30 Max result.

## 1. Looser rules (replace the matching loop-30-max / check-skill rules)
1. **Consensus:** ✅ when **3 or more of 5** analyst passes say Valid **and** the risk-manager pass does not say Not valid. 2 of 5 = ⏳. Fewer = ❌. Show the vote count.
2. **Down-regime relative strength:** in Down, a ✅ needs RS20 > 0 **or** RS60 > 0, and neither may be below -5. (Up and Correction regimes: no RS requirement, as in the check skill.)
3. **Entry:** the entry may be up to **1.5 ATR above** the support zone (not only at it). A market or at-price limit entry is allowed when the last price is within 0.5 ATR of the planned entry.
4. **Reward:risk:** at least **2.0 gross**, and at least **1.6 after round-trip fees** (show both).
5. **Stop:** still under the support zone; between 1 and 3 ATR from entry (unchanged).
6. **Liquidity, new listings, price band, T+2, caps (30% stock / 50% sector):** unchanged.
7. **Holding time:** each plan states a time stop of **10 trading days**; if neither target nor stop is hit by then, the plan says exit or re-check.
8. **Red events:** results, ex-date or suspension inside the order window or the 10-day hold still make the verdict ⏳ (not loosened).

## 2. Analyst passes
Same five lenses and the verifier as loop-30-max. Tell each analyst pass the looser rules above (consensus, one-period RS, entry within 1.5 ATR of support, R:R 2.0 gross / 1.6 net) so they judge against them, and that this is a speculation run with a 10-trading-day horizon.

## 3. Sizing
Risk budget = invested amount x risk% from step 0 (not equity). Shares = floor( risk budget / ((entry - stop) + round-trip fees per share) ), then capped by the invested amount and cash available (after buy fees), the 30% / 50% caps of total equity, and the minimum order (~EGP 2,500). Show the risk budget in EGP, the loss at stop including fees, and which limit set the share count. If the loss at stop with the cash-capped size is already under the risk budget, say plainly that the risk % did not change the size.

## 4. Answer and log
- Same answer layout as loop-30-max step 8, with "مضاربة" in the title, the risk % used, the time stop, and the vote count per ticker.
- Log each finalist to Recommendations with Command = **Loop 30 Spec**, so its hit rate can be compared with Loop 30 Max in the monthly report. Outcome tracking: also mark **Time exit** when 10 trading days pass after entry without target or stop.
- Save the data pack and agent JSON as `loop30spec/datapack-YYYY-MM-DD.json` next to the votes.
- Closing line: analysis, not investment advice; the decisions and the orders are the user's.