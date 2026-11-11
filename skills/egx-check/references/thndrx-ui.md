# ThndrX UI notes (checked 8 Nov 2026)

- Trade workspace: https://x.thndr.app/workspaces/default/trade · Market page: https://x.thndr.app/workspaces/default/market
- Chart: TradingView widget inside an iframe; `iframe.contentWindow.tradingViewApi.activeChart()`. Symbols are UUIDs, so open stocks through the watchlist search (`EGX.open(tk)`), never `setSymbol`.
- Watchlist search: `input[placeholder="ابحث عن سهم"]`; each result is a `<button>` holding the ticker text. The first result is not always the ticker (ORAS lists OFH and OIH first) - `EGX.open` clicks the exact ticker.
- EGX30 opens the same way (search "EGX30").
- Header: market status "السوق مفتوح / مغلق" and the **cash available** next to it ("250.24 ج.م"). Funds (BWA, BMM, gold) are not cash.
- Order book: first total (green, الطلب) = bids, second (red, العرض) = asks; e.g. "396.95 ألف (23%)" / "1.35 مليون (77%)" = 23% bids, 77% asks = sellers heavier.
- Price band: read the displayed order ticket hint "من X الي Y". Limits vary by segment; never assume ±20% for every ticker.
- Financial data: tab "البيانات المالية" -> quality scores (الصحة المالية, الكفاءة, النمو, الربحية, التقييم) and "تفاصيل المؤشرات" (P/E = مضاعف الربحية, EPS = ربحية السهم, ROE, margins, growth).
- Current investments: bottom tab "الاستثمارات الحالية" (ARIA grid): price, daily change, average entry, quantity, cost, market value, weight, P/L EGP, P/L %.

## Order ticket (Tarek or his friend types it; Claude never does)
1. Open the stock, panel تداول on the left, tab **شراء** (or **بيع** for a sell).
2. **نوع الطلب**: أمر بسعر محدد (limit).
3. **سعر**: the entry price. **العدد**: the share count. Check **السعر الكامل** ≈ shares × price.
4. **الانتهاء**: صالح لتاريخ معين, **تاريخ انتهاء الصلاحية** about one trading week ahead. **نوع التنفيذ**: افتراضي.
5. Explain the stop and target as planned exit levels. Only describe an attached stop/target control if it is actually visible and its behavior is confirmed. Do not assume bracket orders or that a stop is active before sell eligibility.
6. The green button must read **شراء TICKER · N أسهم @ PRICE**. If anything differs, stop and recheck.
If the ticket shows only a few shares, the cash is too low (e.g. 250 EGP buys 11 shares at 22).

## Broker documentation cross-check — 11 November 2026

[Thndr order types](https://support.thndr.app/en/articles/640388-egx-stock-order-types-market-limit-stop-sell-advanced) states that market orders are not accepted from the pre-close phase beginning at 14:15. This strategy therefore plans its T0 exit by **14:10**, allowing a small buffer; a halt or illiquid book can still prevent execution. Verify shortened sessions and holidays each run. Same-day sell eligibility depends on the available settlement bucket.

[Thndr wallet balances](https://support.thndr.app/en/articles/640608-how-to-read-your-thndr-wallet-activities-balances-transfer-statuses) distinguishes available investing balances from pending funds reserved for orders. Use available buying power; do not count pending cash or prospective future sales. These documentation checks do not establish that the current ThndrX UI controls were tested live.
