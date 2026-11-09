# News sources (whitelist)

Only these sources count as evidence. Anything else (other sites, social media, forums,
Telegram / WhatsApp groups, tip sites) may point to a story but is never cited; find the story
on a listed source or drop it.

| Tier | Source | Domains | Language | Used for |
|---|---|---|---|---|
| 1 Official | Egyptian Exchange (EGX) | egx.com.eg | AR / EN | disclosures, suspensions, segment (T+0) lists, results and ex-dates |
| 2 EGX news | Arab Finance | arabfinance.com | EN / AR | stock news, results, events |
| 2 | Mubasher Egypt | mubasher.info, english.mubasher.info | AR / EN | stock news, disclosures quoted |
| 2 | Amwal Al Ghad | amwalalghad.com, en.amwalalghad.com | AR / EN | stock and sector news |
| 2 | Enterprise Egypt | enterprise.press | EN | deals, policy, sector news |
| 3 Economy / global | Ahram Online | english.ahram.org.eg | EN | government decisions, economy |
| 3 | Egypt Today | egypttoday.com | EN | government decisions, economy |
| 3 | Daily News Egypt | dailynewsegypt.com | EN | economy, sectors |
| 3 | Reuters (Egypt) | reuters.com | EN | macro, global demand, commodities |
| 3 | Bloomberg | bloomberg.com | EN | global demand, commodity prices |

## Rules
1. **Open every item kept** (WebFetch) and read its date from the page, not from the search snippet. Cannot open = does not count. **Bloomberg** (paywall): counts when the headline and date are readable on the page; note "paywalled, headline only".
2. **Corporate events** (merger, acquisition, tender offer, capital increase, big contract) count only with an EGX disclosure **or** two independent Tier-2 sources. Otherwise `status: "rumour"`; a rumour never makes a stock Hot or upgrades anything.
3. **Red events** (results date, ex-date, suspension) are checked on EGX first. Not found = `"unknown"`, shown as a risk, never assumed safe.
4. **Fresh** = published within 48 hours. Hot window = 14 days. Older items: at most 2 lines of context, marked old.
5. Every news receipt stores: the query text, URL, source, tier, published date (from the page), impact (+ / 0 / -), one-line summary.

## Query templates (at least 2 per stock: one Arabic, one English)
- English: `"<TICKER>" OR "<company name>" site:arabfinance.com OR site:english.mubasher.info OR site:enterprise.press`
- Arabic: `"<الاسم العربي>" البورصة site:mubasher.info OR site:amwalalghad.com`
- Official: `"<company name>" disclosure site:egx.com.eg` / `"<الاسم العربي>" إفصاح site:egx.com.eg`
- Hot, corporate: `استحواذ OR اندماج OR "عرض شراء" البورصة المصرية site:mubasher.info OR site:amwalalghad.com`, `EGX acquisition OR merger OR "tender offer" site:arabfinance.com OR site:enterprise.press`
- Hot, urgent industry: `Egypt decision tariff OR "export ban" OR subsidy site:english.ahram.org.eg OR site:egypttoday.com OR site:dailynewsegypt.com`
- Hot, global demand: `<commodity> prices site:reuters.com OR site:bloomberg.com`

If `site:` returns nothing dated, search again without it and keep only results on listed domains.
