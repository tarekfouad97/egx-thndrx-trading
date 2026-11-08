# EGX ThndrX Trading

Three skills for analysing Egyptian Exchange (EGX) stocks on ThndrX in Chrome. They read the account and chart only; Tarek places every order himself.

| Skill | Say | What it does |
|---|---|---|
| egx-thndrx-trade-check | "check COMI", "market", "my positions", "I bought ...", "monthly" | Full analysis of one stock (chart blocks A-J, chart score, drawings + screenshot, news and catalysts), market regime, position review, trade logging in the "EGX Trade Log (ThndrX)" Google Sheet |
| loop-30 | "Loop 30" / "لف على الـ 30" | Market-wide news and catalyst scan, scan of the top 30 stocks, full check on the best 5, allocation of the amount with fees and break-even cost |
| loop-30-max | "Loop 30 Max" / "لف على الـ 30 ماكس" | Deepest scan: full check on every stock, extended searches, five independent top-model analyst passes per finalist, a verifier, then the allocation. Very heavy on usage |

Needs: Claude in Chrome signed in to x.thndr.app, and the Google Sheets connector for the trade log (risk, equity and fees are read from its Settings tab).

All output is analysis, not investment advice.
