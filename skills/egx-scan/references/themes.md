# Hot-stock themes (draft: the user corrects the mapping)

Used by egx-scan to turn world and Egyptian news into EGX candidates. A theme is **live** when a
whitelisted source (Tier 3 for prices and decisions, `../egx-check/references/news-sources.md`)
reports the trigger within the last 14 days. A live theme adds its tickers to the Hot list with the
reason, the source, its tier and date.

Tickers are a starting list, not a fact: every one is opened with `EGX.scan`; a ticker that does not
open (`UNKNOWN`) is removed from the run and reported as "not found, fix themes.md". Never add a
ticker that is not here or in the news itself.

| Theme | Trigger (last 14 days, dated) | Direction | EGX sector | Tickers to check |
|---|---|---|---|---|
| Urea / fertilizer prices | urea or ammonia prices up >= 10%, export demand, gas supply to plants restored | + | Fertilizers / chemicals | ABUK, MFPC, EGCH, KZPC |
| Gas supply cuts to industry | government cuts or rations gas to factories | - | Fertilizers, steel, cement | ABUK, MFPC, ESRS, ARCC |
| Steel and rebar | rebar prices up, import duties on steel, construction push | + | Basic resources | ESRS |
| Cement demand / export quotas | export quota changes, cement price moves, mega-projects | +/- | Building materials | ARCC, SUCE, MCQE |
| Oil and petrochemicals | Brent or polymer prices move >= 10% | +/- | Energy / petrochemicals | SKPC, AMOC |
| Gold price | gold at highs, new mining concessions | + | Mining | ASCM |
| EGP devaluation or FX inflows | EGP moves, IMF tranche, big FDI deal | + exporters, - importers | Exporters with USD revenue | SWDY, ORWE, ABUK, MFPC |
| CBE rate cuts | MPC cuts rates or signals cuts | + | Real estate, consumer, banks | TMGH, PHDC, OCDI, EMFD, HELI, COMI |
| CBE rate hikes / tight money | MPC hikes | + banks' margins, - real estate | Banks | COMI, CIEB, ADIB, HDBK, FAIT |
| Tourism inflows | record arrivals, new flights, Red Sea / Sinai news | + | Tourism / hotels | ORHD, EGTS |
| Suez Canal / Red Sea shipping | canal traffic recovers or drops | +/- | Shipping and ports | ALCN, CSAG |
| Food commodities (wheat, milk, sugar) | input prices fall, price-cap decisions | +/- | Food | EFID, JUFO |
| Drug pricing decisions | EDA approves price increases | + | Pharma | PHAR, ISPH, RMDA |
| Cigarette prices / taxes | price or tax decisions | +/- | Tobacco | EAST |
| Digital payments and fintech rules | CBE licenses, e-payment mandates | + | Fintech / IT | FWRY |
| Telecom tariffs | NTRA approves tariff increases | + | Telecom | ETEL |
| Healthcare demand / insurance law | universal health insurance rollout | + | Healthcare | CLHO |
| Textiles and cotton exports | cotton prices, US / EU export orders | +/- | Textiles | ORWE |

## Urgent industry (no fixed list)
Government decisions, tariffs, export bans, subsidies or sector-wide shocks found by the urgent-industry
queries. Map them to the sector named in the decision; the tickers come from the source itself or from
the table above. The sector pulse (`EGX.marketPage().sectors`) moving more than 2% in a day is a hint,
never a reason on its own: find the dated source or drop it.

## Rules
- Direction "-" themes are risks: they never make a stock Hot, they are red flags for stocks already in the run.
- A theme already moved more than 2 ATR since its date on a stock = priced in for that stock; it may still be checked but ranks below unpriced ones.
- Theme-only candidates still pass every rule of the check (liquidity >= EGP 5M a day, R:R, gates). A theme never replaces the chart.
