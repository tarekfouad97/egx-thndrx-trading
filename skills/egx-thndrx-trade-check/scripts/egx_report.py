"""
egx_report.py - builds the EGX HTML report (design spec: "EGX Report - HTML Design Requirements").

One self-contained file: palette tokens, Liquid Glass only on the floating top bar and dock,
the decision first, positions, stock cards that open with the drawn ThndrX chart screenshot,
folded evidence, market, scan, costs, footer; a HyperFrames recap (1080x1920) in a sheet.
Used by egx.py (`report`), standard library only.
"""
from __future__ import annotations

import html
import json

# ----------------------------------------------------------------- labels
L = {
    "ar": {
        "dir": "rtl", "lang": "ar", "brand": "تقرير EGX",
        "Up": "سوق صاعد", "Down": "سوق هابط", "Correction": "سوق في تصحيح", "unknown": "حالة السوق غير معروفة",
        "valid": "صالح", "wait": "انتظر", "not_valid": "مش صالح", "dropped": "مستبعد", "add": "زيادة",
        "hold": "احتفظ", "tighten": "قرّب الوقف", "sell": "بيع", "exit": "اخرج",
        "decision": "القرار", "orders": "أوامر", "order1": "أمر واحد", "ch2060": "تغير 20 / 60 جلسة", "from_high": "بعيد عن القمة", "no_orders": "مفيش أوامر النهارده، الفلوس تفضل كاش",
        "order_now": "شراء دلوقتي", "order_limit": "أمر محدد", "shares": "سهم", "entry": "دخول", "stop": "وقف", "target": "هدف",
        "rr": "عائد/مخاطرة", "risk": "مخاطرة", "value": "القيمة", "cash_left": "يفضل كاش", "total_risk": "إجمالي المخاطرة",
        "gain": "لو الأهداف اتحققت", "loss": "لو الوقفات اتضربت", "hurdle": "عشان تغطي التكاليف شهرياً", "cash": "الكاش في ThndrX",
        "positions": "مراكزك", "picks": "الأسهم اللي اتفحصت", "market": "السوق", "catalysts": "الأخبار المحركة",
        "scan": "كل الأسهم اللي اتمسحت", "drops": "اتشالت ليه", "costs": "التكاليف", "recap": "ملخص 12 ثانية",
        "chart_ev": "أدلة التحليل الفني", "news_ev": "الأخبار والمصادر", "book": "دفتر الأوامر", "fin": "البيانات المالية",
        "votes": "أصوات المحللين", "reasons": "ليه", "wait_for": "مستني إيه", "no_news": "مفيش أخبار جديدة، القرار فني بس",
        "red": "أحداث مهمة", "shot_caption": "شارت ThndrX بعد الرسم", "no_shot": "مفيش صورة للشارت، القرار لا يعتمد عليه",
        "legend": ["دعم", "مقاومة", "دخول", "وقف", "هدف", "اتجاه"], "score": "الدرجة", "regime": "حالة السوق",
        "breadth": "الرابحين / الخاسرين", "sectors": "القطاعات", "macro": "أجندة الأسبوع", "priced_in": "اتسعّر", "open": "لسه",
        "disclaimer": "تحليل تعليمي مش نصيحة استثمارية. القرار والأوامر في إيدك.", "made": "اتعمل بحب بواسطة",
        "dock": ["القرار", "مراكزك", "الأسهم", "السوق"], "close": "قفل", "replay": "إعادة", "fees": "عمولات", "fixed": "تكاليف ثابتة / شهر",
        "cap1": "رأس مال يخلي التكاليف 1% في الشهر", "per_trade": "مخاطرة الصفقة", "limited": "محدود بـ", "funds": "صناديق (مش بتتحلل)",
        "warn": "تنبيه", "last": "آخر سعر", "status": "الحالة", "trend": "الاتجاه",
    },
    "en": {
        "dir": "ltr", "lang": "en", "brand": "EGX report",
        "Up": "Market up", "Down": "Market down", "Correction": "Market in correction", "unknown": "Regime unknown",
        "valid": "Valid", "wait": "Wait", "not_valid": "Not valid", "dropped": "Dropped", "add": "Add",
        "hold": "Hold", "tighten": "Tighten stop", "sell": "Sell", "exit": "Exit",
        "decision": "Decision", "orders": "Orders", "order1": "1 order", "ch2060": "20d / 60d", "from_high": "From high", "no_orders": "No orders today, the money stays in cash",
        "order_now": "Buy now", "order_limit": "Limit order", "shares": "shares", "entry": "Entry", "stop": "Stop", "target": "Target",
        "rr": "R:R", "risk": "Risk", "value": "Value", "cash_left": "Stays cash", "total_risk": "Total risk",
        "gain": "If all targets hit", "loss": "If all stops hit", "hurdle": "Monthly return to cover costs", "cash": "Cash in ThndrX",
        "positions": "Your positions", "picks": "Deep-checked stocks", "market": "Market", "catalysts": "Catalysts",
        "scan": "Everything scanned", "drops": "Dropped and why", "costs": "Costs", "recap": "12-second recap",
        "chart_ev": "Chart evidence", "news_ev": "News and sources", "book": "Order book", "fin": "Financials",
        "votes": "Analyst votes", "reasons": "Why", "wait_for": "Waiting for", "no_news": "No fresh news; the verdict is technical only",
        "red": "Red events", "shot_caption": "ThndrX chart after drawing", "no_shot": "No chart screenshot; do not rely on this verdict",
        "legend": ["Support", "Resistance", "Entry", "Stop", "Target", "Trend"], "score": "Score", "regime": "Regime",
        "breadth": "Gainers / losers", "sectors": "Sectors", "macro": "Week ahead", "priced_in": "priced in", "open": "open",
        "disclaimer": "Educational analysis, not investment advice. Every decision and order is yours.", "made": "Made with love by",
        "dock": ["Decision", "Positions", "Stocks", "Market"], "close": "Close", "replay": "Replay", "fees": "Fees", "fixed": "Fixed costs / month",
        "cap1": "Capital that makes costs 1% a month", "per_trade": "Risk per trade", "limited": "limited by", "funds": "Funds (not analysed)",
        "warn": "Warning", "last": "Last", "status": "Status", "trend": "Trend",
    },
}

DROP_WORDS = {"rr": "R:R < 2", "thin": "thin (< 5M EGP/day)", "wide": "stop > 3 ATR", "noise": "stop < 1 ATR",
              "invalid": "resistance right above", "limit": "near the daily limit", "new": "new listing",
              "no-plan": "no support / plan", "unknown": "chart unreadable"}

# line colours drawn by egx_chart.js (legend must match the screenshot)
LEGEND_COLORS = ["#f5a623", "#e74c3c", "#3498db", "#e74c3c", "#2ecc71", "#f5a623"]
LEGEND_DASH = [True, True, False, False, False, False]

ICON = {"valid": "✓", "add": "+", "hold": "•", "wait": "◷", "tighten": "↑", "not_valid": "✕", "sell": "↓", "exit": "↓", "dropped": "–"}
TONE = {"valid": "gain", "add": "gain", "hold": "gain", "wait": "copper", "tighten": "copper", "not_valid": "loss", "sell": "loss", "exit": "loss", "dropped": "muted"}


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def num(x, d=2):
    if x is None or x == "":
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    s = f"{x:,.{0 if abs(x) >= 100000 else d}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def signed(x, d=2, unit="%"):
    if x is None:
        return "—"
    return ("+" if float(x) > 0 else "") + num(x, d) + unit


def badge(kind, t) -> str:
    return f'<span class="badge {TONE.get(kind, "muted")}"><i aria-hidden="true">{ICON.get(kind, "•")}</i>{esc(t.get(kind, kind))}</span>'


def spark_svg(vals, w=96, h=28) -> str:
    vals = [v for v in (vals or []) if v is not None]
    if len(vals) < 3:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{i * w / (len(vals) - 1):.1f},{h - 3 - (v - lo) / rng * (h - 6):.1f}" for i, v in enumerate(vals))
    tone = "var(--gain)" if vals[-1] >= vals[0] else "var(--loss)"
    return f'<svg class="spark" viewBox="0 0 {w} {h}" aria-hidden="true"><polyline points="{pts}" fill="none" stroke="{tone}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg>'


def score_ring(score) -> str:
    if score is None:
        return ""
    c = 2 * 3.14159 * 15
    off = c * (1 - max(0, min(10, score)) / 10)
    return (f'<span class="ring" title="score {score}/10"><svg viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15" class="ring-bg"/>'
            f'<circle cx="18" cy="18" r="15" class="ring-fg" stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}"/></svg><b>{esc(score)}</b></span>')


def legend(t) -> str:
    items = []
    for name, col, dash in zip(t["legend"], LEGEND_COLORS, LEGEND_DASH):
        dash_attr = ' stroke-dasharray="4 3"' if dash else ""
        items.append(f'<span><svg viewBox="0 0 18 4" aria-hidden="true"><line x1="0" y1="2" x2="18" y2="2" stroke="{col}" stroke-width="2.5"'
                     f'{dash_attr}/></svg>{esc(name)}</span>')
    return '<div class="legend">' + "".join(items) + "</div>"


def figure(s, t, kind="stock") -> str:
    b64 = s.get("screenshot_b64")
    if not b64:
        return f'<div class="noshot">⚠︎ {esc(t["no_shot"])}</div>'
    mime = "image/png" if b64.startswith("iVBOR") else "image/jpeg"
    cap = f'{esc(s.get("tk"))} · {esc(s.get("shot_at") or s.get("date") or "")} · {esc(t["shot_caption"])} · egx_chart.js v{esc(s.get("v") or "")}'
    return (f'<figure class="shot"><button class="shot-btn" type="button" data-lightbox aria-label="{esc(s.get("tk"))} chart, open full screen">'
            f'<img alt="{esc(s.get("tk"))} ThndrX daily chart with the analysis lines drawn" src="data:{mime};base64,{b64}"/></button>'
            f'<figcaption>{cap}</figcaption>{legend(t) if kind == "stock" else ""}</figure>')


def plan_grid(p, t, row=None) -> str:
    if not p:
        return ""
    cells = [(t["entry"], p.get("entry"), "teal"), (t["stop"], p.get("stop"), "loss"), (t["target"], p.get("target"), "gain"), (t["rr"], p.get("rr"), "")]
    if row and row.get("shares"):
        cells += [(t["shares"], row["shares"], ""), (t["value"], num(row["value"], 0), "")]
    return '<dl class="plan">' + "".join(f'<div><dt>{esc(a)}</dt><dd class="{c}">{esc(num(b) if isinstance(b, (int, float)) else b)}</dd></div>' for a, b, c in cells if b not in (None, "")) + "</dl>"


def news_list(items, t) -> str:
    if not items:
        return f'<p class="muted">{esc(t["no_news"])}</p>'
    out = []
    for n in items:
        imp = {"+": "gain", "positive": "gain", "-": "loss", "negative": "loss"}.get(str(n.get("impact", "")).lower(), "muted")
        mark = {"gain": "▲", "loss": "▼", "muted": "•"}[imp]
        out.append(f'<li><span class="{imp}">{mark}</span><div><a href="{esc(n.get("url"))}" target="_blank" rel="noopener">{esc(n.get("title"))}</a>'
                   f'<small>{esc(n.get("source"))} · {esc(n.get("date"))}{" · <b class=copper>48h</b>" if n.get("fresh") else ""}</small>'
                   + (f'<p>{esc(n.get("summary"))}</p>' if n.get("summary") else "") + "</div></li>")
    return '<ul class="news">' + "".join(out) + "</ul>"


def kv(d) -> str:
    if not d:
        return '<p class="muted">—</p>'
    return '<dl class="kv">' + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in d.items()) + "</dl>"


def fold(title, body, open_=False) -> str:
    return f'<details{" open" if open_ else ""}><summary><span>{esc(title)}</span><i aria-hidden="true"></i></summary><div class="fold">{body}</div></details>'


def evidence_body(s, t) -> str:
    ev = list(s.get("evidence") or [])
    z = s.get("zones") or {}
    if z.get("trendline"):
        tl = z["trendline"]
        ev.append(f"Trendline {tl['kind']}: {tl['from'][0]} {tl['from'][1]} → {tl['to'][0]} {tl['to'][1]} (now {tl.get('now')})")
    if z.get("brokenSupportNowResistance"):
        ev.append("Broken supports now resistance: " + ", ".join(f"{b['lo']}-{b['hi']}" for b in z["brokenSupportNowResistance"]))
    if z.get("hi300") is not None:
        ev.append(f"300-bar high {z.get('hi300')} · low {z.get('lo300')} · round numbers {', '.join(map(str, z.get('roundNumbers') or [])) or '—'}")
    pat = s.get("patterns") or {}
    if pat.get("doubleBottom"):
        ev.append("Double bottom: " + " & ".join(pat["doubleBottom"]))
    h = s.get("history")
    if h:
        ev.append(f"Setup history: {h.get('hits')}/{h.get('tries')} reached the target before the stop within 15 bars ({h.get('judge')})")
    for fl in s.get("flags") or []:
        ev.append("Flag: " + fl)
    body = '<ol class="ev">' + "".join(f"<li>{esc(e)}</li>" for e in ev) + "</ol>"
    sc = s.get("score") or {}
    if sc.get("parts"):
        body += '<p class="parts">' + " · ".join(f"{esc(k)} <b>{esc(v)}</b>" for k, v in sc["parts"].items()) + f" = <b>{esc(sc.get('total'))}/10</b></p>"
    return body


def stock_card(s, t, row=None, head=None, plan=None) -> str:
    v = s.get("verdict") or "dropped"
    p = plan if plan is not None else (s.get("plan") or {})
    top = head if head is not None else (f'<header class="card-head"><div><h3>{esc(s.get("tk"))}</h3><small>{esc(s.get("title"))}</small></div>'
                   f'<div class="card-meta">{badge(v, t)}<span class="px">{esc(num(s.get("last")))} <em class="{"gain" if (s.get("chg") or 0) >= 0 else "loss"}">{esc(signed(s.get("chg")))}</em></span>'
                   f'{score_ring((s.get("score") or {}).get("total"))}</div></header>')
    body = top + figure(s, t) + plan_grid(p, t, row)
    if s.get("reasons"):
        body += '<ul class="reasons">' + "".join(f"<li>{esc(r)}</li>" for r in s["reasons"]) + "</ul>"
    if s.get("wait_for"):
        body += f'<p class="waitfor"><b>{esc(t["wait_for"])}:</b> {esc(s["wait_for"])}</p>'
    folds = [fold(t["chart_ev"], evidence_body(s, t))]
    nb = news_list(s.get("news"), t)
    if s.get("red_events"):
        nb += f'<h4>{esc(t["red"])}</h4><ul class="news">' + "".join(
            f'<li><span class="copper">!</span><div>{esc(r.get("type"))} · {esc(r.get("date"))} · <a href="{esc(r.get("url"))}" target="_blank" rel="noopener">{esc(r.get("source"))}</a></div></li>'
            for r in s["red_events"]) + "</ul>"
    folds.append(fold(t["news_ev"], nb))
    pg = s.get("page") or {}
    if pg.get("book"):
        b = pg["book"]
        bid, ask = b.get("bidPct") or 0, b.get("askPct") or 0
        bar = (f'<div class="bookbar" role="img" aria-label="bids {bid}% asks {ask}%"><span class="gainbg" style="flex:{bid or 1}">{esc(bid)}%</span>'
               f'<span class="lossbg" style="flex:{ask or 1}">{esc(ask)}%</span></div>')
        folds.append(fold(t["book"], bar + kv({"best bid / ask": f'{b.get("bestBid")} / {b.get("bestAsk")}', "spread": f'{b.get("spreadPct")}%',
                                                "side": b.get("side"), "price band": " – ".join(map(str, pg.get("band") or [])) or "—"})))
    fin = s.get("financials") or {}
    if fin.get("metrics") or fin.get("scores"):
        folds.append(fold(t["fin"], kv({**fin.get("scores", {}), **fin.get("metrics", {})})))
    if s.get("votes"):
        rows = "".join(f'<tr><th>{esc(k)}</th><td>{esc(x.get("verdict"))}</td><td>{esc(x.get("confidence"))}/5</td><td>{esc("; ".join(x.get("facts") or []))}</td></tr>'
                       for k, x in s["votes"].items())
        folds.append(fold(t["votes"], f'<div class="tbl"><table>{rows}</table></div>'))
    body += '<div class="folds">' + "".join(folds) + "</div>"
    return body


def build_html(run: dict, cfg: dict, fname: str, recap_html: str, version: str, index_meta: dict) -> str:
    t = L.get(cfg.get("language", "ar"), L["ar"])
    meta, mk, al = run.get("meta") or {}, run.get("market") or {}, run.get("allocation") or {}
    eg = mk.get("egx30") or {}
    regime = eg.get("regime", "unknown")
    rtone = {"Up": "gain", "Down": "loss", "Correction": "copper"}.get(regime, "muted")
    stocks = run.get("stocks") or []
    deep = [s for s in stocks if s.get("verdict") in ("valid", "wait", "not_valid")]
    rows = al.get("rows") or []
    by_tk = {r["tk"]: r for r in rows}
    orders = [r for r in rows if r.get("shares")]
    created = (meta.get("created") or "")[:16].replace("T", " ")
    cmd = meta.get("command") or "EGX"
    out = []

    # ---------- top bar (glass)
    out.append(f'<header class="glass topbar"><div class="brand"><b>{esc(cmd)}</b><small>{esc(created)}</small></div>'
               f'<span class="pill {rtone}">EGX30 {esc(num(eg.get("last"), 0))} · {esc(t.get(regime, regime))}</span>'
               f'<button class="pill recap-btn" type="button" data-recap>▶ {esc(t["recap"])}</button></header>')
    out.append("<main>")

    # ---------- decision
    headline = meta.get("summary") or ""
    out.append(f'<section id="decision" class="hero" aria-labelledby="h-decision"><p class="eyebrow">{esc(t["decision"])} · {esc(meta.get("trading_day") or created[:10])}</p>')
    if orders:
        total = sum(r["value"] for r in orders)
        out.append(f'<h1 id="h-decision">{esc(t["order1"]) if len(orders) == 1 else str(len(orders)) + " " + esc(t["orders"])} · {esc(num(total, 0))} EGP</h1>')
    else:
        out.append(f'<h1 id="h-decision">{esc(t["no_orders"])}</h1>')
    if headline:
        out.append(f'<p class="lede">{esc(headline)}</p>')
    if orders:
        out.append('<div class="orders">')
        for r in orders:
            kind = r.get("verdict") or "valid"
            out.append(f'<a class="order" href="#stock-{esc(r["tk"])}"><div class="order-top"><b class="tk">{esc(r["tk"])}</b>{badge(kind, t)}'
                       f'<span class="otype">{esc(t["order_now"] if r.get("order") == "buy now" else t["order_limit"])}</span></div>'
                       f'<div class="big">{esc(r["shares"])} <small>{esc(t["shares"])} ×</small> {esc(num(r["entry"]))}</div>'
                       f'<dl class="mini"><div><dt>{esc(t["stop"])}</dt><dd class="loss">{esc(num(r["stop"]))}</dd></div>'
                       f'<div><dt>{esc(t["target"])}</dt><dd class="gain">{esc(num(r["target"]))}</dd></div>'
                       f'<div><dt>{esc(t["rr"])}</dt><dd>{esc(r.get("rr"))}</dd></div><div><dt>{esc(t["risk"])}</dt><dd>{esc(num(r["risk"], 0))}</dd></div></dl></a>')
        out.append("</div>")
    k = [(t["cash_left"], al.get("cash_left")), (t["total_risk"], al.get("total_risk")), (t["gain"], al.get("gain_if_all_targets")),
         (t["loss"], al.get("loss_if_all_stops")), (t["hurdle"], f'{al.get("break_even_monthly_pct")}%' if al.get("break_even_monthly_pct") is not None else None),
         (t["cash"], meta.get("cash"))]
    out.append('<dl class="kpis">' + "".join(f'<div><dt>{esc(a)}</dt><dd>{esc(b if isinstance(b, str) else num(b, 0))}</dd></div>' for a, b in k if b not in (None, "")) + "</dl>")
    for w in al.get("warnings") or []:
        out.append(f'<p class="warn" role="note"><b>{esc(t["warn"])}:</b> {esc(w)}</p>')
    out.append("</section>")

    # ---------- positions
    hs = run.get("holdings") or []
    stocks_held = [h for h in hs if not h.get("is_fund")]
    funds = [h for h in hs if h.get("is_fund")]
    if hs:
        out.append(f'<section id="positions" aria-labelledby="h-pos"><h2 id="h-pos">{esc(t["positions"])}</h2>')
        for h in stocks_held:
            a = h.get("action") or "hold"
            s = dict(h.get("analysis") or {})
            s.update({kk: vv for kk, vv in h.items() if kk in ("news", "reasons", "red_events", "screenshot_b64", "wait_for", "shot_at")})
            s["tk"] = h.get("tk")
            plan = h.get("plan") or {"entry": h.get("price"), "stop": h.get("stop"), "target": h.get("target"), "rr": None}
            reason = (h.get("reasons") or [""])[0]
            head = (f'<summary class="pos-row"><b class="tk">{esc(h.get("tk"))}</b>{badge(a, t)}'
                    f'<em dir="ltr" class="{"gain" if (h.get("pnlPct") or 0) >= 0 else "loss"}">{esc(signed(h.get("pnlPct")))} · {esc(signed(h.get("pnl"), 0, " EGP"))}</em>'
                    f'<span class="px" dir="ltr">{esc(num(h.get("qty"), 0))} × {esc(num(h.get("avgPrice")))} → {esc(num(h.get("price")))}</span>'
                    f'<span class="why">{esc(reason)}</span><i aria-hidden="true"></i></summary>')
            out.append(f'<details class="card pos" id="hold-{esc(h.get("tk"))}">{head}<div class="fold">{stock_card(s, t, head="", plan=plan)}</div></details>')
        if funds:
            out.append(f'<p class="muted small">{esc(t["funds"])}: ' + " · ".join(f'{esc(h["tk"])} {esc(num(h.get("value"), 0))} EGP' for h in funds) + "</p>")
        out.append("</section>")

    # ---------- picks
    if deep:
        out.append(f'<section id="stocks" aria-labelledby="h-st"><h2 id="h-st">{esc(t["picks"])}</h2><div class="cards">')
        for s in deep:
            out.append(f'<article class="card" id="stock-{esc(s.get("tk"))}">{stock_card(s, t, by_tk.get(s["tk"]))}</article>')
        out.append("</div></section>")

    # ---------- market
    out.append(f'<section id="market" aria-labelledby="h-mk"><h2 id="h-mk">{esc(t["market"])}</h2><article class="card">')
    if mk.get("screenshot_b64"):
        out.append(figure({"tk": "EGX30", "screenshot_b64": mk["screenshot_b64"], "shot_at": mk.get("shot_at") or eg.get("date")}, t, kind="market"))
    pg = mk.get("page") or {}
    stats = {t["regime"]: t.get(regime, regime), "MA50": f'{num(eg.get("ma50"), 0)} ({signed(eg.get("ma50Slope"))})', "MA200": num(eg.get("ma200"), 0),
             t["ch2060"]: f'{signed(eg.get("ch20"))} / {signed(eg.get("ch60"))}', t["from_high"]: signed(eg.get("fromHigh"))}
    if pg.get("gainers") is not None:
        stats[t["breadth"]] = f'{pg.get("gainers")} / {pg.get("losers")}'
    if pg.get("usdEgp"):
        stats["USD/EGP"] = pg["usdEgp"]
    out.append(kv(stats))
    if mk.get("summary"):
        out.append(f'<p class="lede">{esc(mk["summary"])}</p>')
    if pg.get("sectors"):
        sec = "".join(f'<li><span>{esc(a)}</span><b class="{"gain" if (b or 0) >= 0 else "loss"}">{esc(signed(b))}</b></li>' for a, b in pg["sectors"])
        out.append(fold(t["sectors"], f'<ul class="sectors">{sec}</ul>'))
    if mk.get("macro"):
        out.append(fold(t["macro"], news_list(mk["macro"], t)))
    out.append("</article>")
    cats = run.get("catalysts") or []
    if cats:
        out.append(f'<h3 class="sub">{esc(t["catalysts"])}</h3><ul class="cats">')
        for c in cats:
            tone = "gain" if c.get("direction") == "+" else "loss" if c.get("direction") == "-" else "muted"
            out.append(f'<li class="card"><div class="cat-top"><b class="tk">{esc(c.get("tk"))}</b><span class="badge {tone}">{esc(c.get("type"))}</span>'
                       f'<span class="badge {"muted" if c.get("priced_in") else "copper"}">{esc(t["priced_in"] if c.get("priced_in") else t["open"])}</span></div>'
                       f'<p>{esc(c.get("summary"))}</p><small><a href="{esc(c.get("url"))}" target="_blank" rel="noopener">{esc(c.get("source"))}</a> · {esc(c.get("date"))}'
                       f' · {esc(signed(c.get("moved_pct")))} / {esc(c.get("moved_atr"))} ATR</small></li>')
        out.append("</ul>")
    out.append("</section>")

    # ---------- scan
    if stocks:
        tr = []
        for s in stocks:
            p = s.get("plan") or {}
            status = s.get("verdict") if s.get("verdict") in ("valid", "wait", "not_valid") else (DROP_WORDS.get(s.get("drop"), s.get("drop") or "—"))
            tr.append(f'<tr><th>{esc(s.get("tk"))}</th><td>{spark_svg(s.get("spark") or [c[4] for c in (s.get("candles") or [])][-30:])}</td>'
                      f'<td>{esc(num(s.get("last")))}</td><td>{esc((s.get("trend") or {}).get("daily"))}/{esc((s.get("trend") or {}).get("weekly"))}</td>'
                      f'<td>{esc(p.get("entry"))}</td><td>{esc(p.get("stop"))}</td><td>{esc(p.get("target"))}</td><td>{esc(p.get("rr"))}</td>'
                      f'<td>{esc((s.get("score") or {}).get("total"))}</td><td>{esc(t.get(status, status))}</td></tr>')
        head = (f'<tr><th>{esc(t["last"])}</th><th></th><th>{esc(t["last"])}</th><th>{esc(t["trend"])}</th><th>{esc(t["entry"])}</th><th>{esc(t["stop"])}</th>'
                f'<th>{esc(t["target"])}</th><th>{esc(t["rr"])}</th><th>{esc(t["score"])}</th><th>{esc(t["status"])}</th></tr>').replace(f'<th>{esc(t["last"])}</th><th></th>', '<th>Ticker</th><th>30d</th>', 1)
        table_html = '<div class="tbl"><table>' + head + "".join(tr) + "</table></div>"
        out.append('<section id="scan">' + fold(t["scan"] + " (" + str(len(stocks)) + ")", table_html))
        drops = {}
        for s in stocks:
            if s.get("drop") and s.get("verdict") not in ("valid", "wait", "not_valid"):
                drops.setdefault(DROP_WORDS.get(s["drop"], s["drop"]), []).append(s["tk"])
        if drops:
            drop_items = "".join("<li><b>" + esc(k_) + "</b> " + esc(" · ".join(v_)) + "</li>" for k_, v_ in drops.items())
            out.append(fold(t["drops"], '<ul class="drops">' + drop_items + "</ul>"))
        out.append("</section>")

    # ---------- costs
    if al:
        out.append(f'<section id="costs" aria-labelledby="h-c"><h2 id="h-c">{esc(t["costs"])}</h2><dl class="kpis small">'
                   f'<div><dt>{esc(t["fixed"])}</dt><dd>{esc(num(al.get("fixed_monthly"), 0))}</dd></div>'
                   f'<div><dt>{esc(t["hurdle"])}</dt><dd>{esc(al.get("break_even_monthly_pct"))}%</dd></div>'
                   f'<div><dt>{esc(t["cap1"])}</dt><dd>{esc(num(al.get("capital_for_1pct_month"), 0))}</dd></div>'
                   f'<div><dt>{esc(t["per_trade"])}</dt><dd>{esc(al.get("risk_pct"))}% · {esc(num(al.get("risk_budget_per_trade"), 0))}</dd></div></dl></section>')

    foot = cfg["footer"]
    out.append(f'<footer><p>{esc(t["disclaimer"])}</p><p>{esc(t["made"])} <span class="heart">♥</span> <b>{esc(foot["author"])}</b> · '
               f'<a href="mailto:{esc(foot["email"])}">{esc(foot["email"])}</a> · <a href="{esc(foot["repo"])}" target="_blank" rel="noopener">GitHub</a></p>'
               f'<p class="muted small">egx-thndrx-trading v{esc(version)} · {esc(fname)}</p></footer></main>')

    # ---------- dock (glass) + dialogs
    targets = ["decision", "positions" if hs else "stocks", "stocks", "market"]
    out.append('<nav class="glass dock" aria-label="sections">' + "".join(f'<a href="#{a}">{esc(b)}</a>' for a, b in zip(targets, t["dock"])) + "</nav>")
    out.append(f'<dialog id="lightbox" aria-label="chart"><button class="pill close" type="button" data-close>{esc(t["close"])} ✕</button><img alt=""/></dialog>')
    out.append(f'<dialog id="recap" aria-label="{esc(t["recap"])}"><div class="recap-frame"><iframe title="recap" sandbox="allow-scripts allow-same-origin" srcdoc="{esc(recap_html)}"></iframe></div>'
               f'<div class="recap-bar"><button class="pill" type="button" data-replay>↻ {esc(t["replay"])}</button><button class="pill" type="button" data-close>{esc(t["close"])} ✕</button></div></dialog>')

    data = json.dumps(run, ensure_ascii=False).replace("</", "<\\/")
    title = f"{cmd} · {created}"
    return (f'<!doctype html><html lang="{t["lang"]}" dir="{t["dir"]}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="color-scheme" content="dark">'
            f'<meta name="theme-color" content="#0F171B"><title>{esc(title)}</title>'
            f'<meta name="egx-report" content="{esc(json.dumps(index_meta, ensure_ascii=False))}">'
            f'<!-- FOR CLAUDE: the whole run is the JSON in script#egx-data at the end of the body. Read it with: python3 egx.py read {esc(fname)} [--ticker TK]. Search with index.csv in this folder. -->'
            f'<style>{CSS}</style></head><body><div class="bg" aria-hidden="true"></div>{SVG_DEFS}{"".join(out)}'
            f'<script id="egx-data" type="application/json">{data}</script><script>{JS}</script></body></html>')


# ----------------------------------------------------------------- recap (HyperFrames composition)
def recap_composition(run: dict, cfg: dict) -> str:
    """1080x1920 HyperFrames composition in the report palette; also plays in a browser (`npx hyperframes render` -> MP4)."""
    meta, al = run.get("meta") or {}, run.get("allocation") or {}
    eg = ((run.get("market") or {}).get("egx30") or {})
    regime = eg.get("regime", "unknown")
    rcol = {"Up": "#6CC4A1", "Down": "#E8766A", "Correction": "#D9894A"}.get(regime, "#D6B9B9")
    orders = [r for r in al.get("rows") or [] if r.get("shares")][:3]
    holds = [h for h in run.get("holdings") or [] if not h.get("is_fund")][:4]
    sp = [v for v in (eg.get("spark") or []) if v is not None]
    path = ""
    if len(sp) > 2:
        lo, hi = min(sp), max(sp)
        rng = (hi - lo) or 1
        path = "M" + " L".join(f"{i * 880 / (len(sp) - 1):.1f} {300 - (v - lo) / rng * 280:.1f}" for i, v in enumerate(sp))
    cards = "".join(
        f'<div class="ord" id="o{i}"><div class="otk">{esc(r["tk"])}</div><div class="orow"><span>SHARES</span><b>{esc(r["shares"])}</b></div>'
        f'<div class="orow"><span>ENTRY</span><b class="te">{esc(r["entry"])}</b></div><div class="orow"><span>STOP</span><b class="lo">{esc(r["stop"])}</b></div>'
        f'<div class="orow"><span>TARGET</span><b class="ga">{esc(r["target"])}</b></div></div>' for i, r in enumerate(orders)
    ) or '<div class="ord" id="o0"><div class="otk">CASH</div><div class="orow"><span>No valid setup today</span></div></div>'
    hrows = "".join(f'<div class="hrow"><b>{esc(h.get("tk"))}</b><span class="act {esc(TONE.get(h.get("action") or "hold"))}">{esc((h.get("action") or "hold").upper())}</span>'
                    f'<em>{esc(signed(h.get("pnlPct")))}</em></div>' for h in holds) or '<div class="hrow"><b>No stock positions</b></div>'
    foot = cfg["footer"]
    deployed, cash_left, risk = al.get("deployed") or 0, al.get("cash_left") or 0, al.get("total_risk") or 0
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1080, height=1920"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
:root{{--bg:#0F171B;--s1:#122D39;--teal:#2C697F;--tt:#6FB3C8;--rose:#D6B9B9;--copper:#8A4C1C;--ct:#D9894A;--ink:#F4EEEA;--gain:#6CC4A1;--loss:#E8766A}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:var(--bg);font-family:Inter,sans-serif;color:var(--ink)}}
#root{{position:relative;width:100%;height:100%}}
.ground{{position:absolute;inset:0;background:radial-gradient(120% 60% at 50% -10%,rgba(138,76,28,.55),transparent 60%),linear-gradient(180deg,#0F171B 0%,#122D39 55%,#0F171B 100%)}}
.clip{{position:absolute;inset:0}}
.scene{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 90px;gap:36px;opacity:0}}
.k{{font-size:34px;letter-spacing:.3em;color:var(--rose);text-transform:uppercase}}
.h{{font-size:120px;font-weight:900;letter-spacing:-.04em;line-height:1}}
.pill{{align-self:flex-start;font-size:44px;font-weight:700;padding:16px 40px;border-radius:999px;color:{rcol};border:3px solid {rcol};background:rgba(18,45,57,.6)}}
.chart{{width:900px;height:320px}}
.sub{{font-size:38px;color:var(--rose)}}
.ord{{padding:44px 52px;border-radius:44px;background:rgba(18,45,57,.72);border:2px solid rgba(214,185,185,.18);box-shadow:inset 0 2px 0 rgba(255,255,255,.12),0 30px 80px rgba(0,0,0,.45);display:flex;flex-direction:column;gap:14px}}
.otk{{font-size:84px;font-weight:900;letter-spacing:-.03em}}
.orow{{display:flex;justify-content:space-between;font-size:40px;color:var(--rose)}} .orow b{{color:var(--ink)}}
.te{{color:var(--tt)!important}} .lo{{color:var(--loss)!important}} .ga{{color:var(--gain)!important}}
.hrow{{display:flex;align-items:center;gap:30px;font-size:52px;padding:26px 0;border-bottom:2px solid rgba(214,185,185,.14)}} .hrow em{{margin-inline-start:auto;font-style:normal;color:var(--rose)}}
.act{{font-size:32px;font-weight:700;padding:8px 22px;border-radius:999px;background:rgba(18,45,57,.8)}} .act.gain{{color:var(--gain)}} .act.loss{{color:var(--loss)}} .act.copper{{color:var(--ct)}}
.n{{display:flex;flex-direction:column;gap:6px}} .n b{{font-size:150px;font-weight:900;letter-spacing:-.04em;line-height:1}} .n span{{font-size:34px;letter-spacing:.24em;color:var(--rose)}}
.heart{{color:var(--loss)}}
</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="12" data-width="1080" data-height="1920">
 <div class="ground"></div>
 <div id="s1" class="clip" data-start="0" data-duration="3" data-track-index="1"><div class="scene" id="s1i">
  <div class="k">EGX · {esc(meta.get("command", ""))} · {esc(meta.get("trading_day") or (meta.get("created") or "")[:10])}</div>
  <div class="h">EGX30<br/>{esc(num(eg.get("last"), 0))}</div>
  <div class="pill">{esc(regime.upper())}</div>
  <svg class="chart" viewBox="0 0 880 320"><path id="line" d="{path}" fill="none" stroke="{rcol}" stroke-width="6" stroke-linecap="butt" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>
  <div class="sub">MA50 {esc(num(eg.get("ma50"), 0))} · MA200 {esc(num(eg.get("ma200"), 0))} · 20d {esc(signed(eg.get("ch20")))}</div>
 </div></div>
 <div id="s2" class="clip" data-start="3" data-duration="3.6" data-track-index="1"><div class="scene" id="s2i">
  <div class="k">Orders</div>{cards}
 </div></div>
 <div id="s3" class="clip" data-start="6.6" data-duration="2.6" data-track-index="1"><div class="scene" id="s3i">
  <div class="k">Your positions</div>{hrows}
 </div></div>
 <div id="s4" class="clip" data-start="9.2" data-duration="2.8" data-track-index="1"><div class="scene" id="s4i">
  <div class="n"><b id="n1">0</b><span>DEPLOY EGP</span></div><div class="n"><b id="n2">0</b><span>STAYS CASH EGP</span></div>
  <div class="n"><b id="n3">0</b><span>AT RISK EGP</span></div>
  <div class="sub">Made with <span class="heart">♥</span> by {esc(foot["author"])} · not investment advice</div>
 </div></div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
if (!window.gsap) {{
  document.querySelectorAll(".scene").forEach((e, i) => (e.style.opacity = i === 1 ? 1 : 0));
}} else {{
  const tl = gsap.timeline({{ paused: true }});
  const scene = (id, start, dur, last) => {{
    tl.fromTo(id, {{ opacity: 0, y: 60, filter: "blur(14px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", duration: 0.55, ease: "power3.out" }}, start);
    if (!last) tl.to(id, {{ opacity: 0, y: -40, filter: "blur(10px)", duration: 0.35, ease: "power2.in" }}, start + dur - 0.4);
  }};
  tl.set("#s1i", {{ opacity: 1 }}, 0); tl.to("#s1i", {{ opacity: 0, y: -40, filter: "blur(10px)", duration: 0.35, ease: "power2.in" }}, 2.6);
  scene("#s2i", 3, 3.6); scene("#s3i", 6.6, 2.6); scene("#s4i", 9.2, 2.8, true);
  tl.fromTo("#line", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 1.6, ease: "power2.inOut" }}, 0.4);
  tl.fromTo(".ord", {{ opacity: 0, y: 80, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "back.out(1.3)", stagger: 0.2 }}, 3.3);
  tl.fromTo(".hrow", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.4, stagger: 0.12, ease: "power3.out" }}, 6.9);
  const count = (id, to, at) => {{ const o = {{ v: 0 }}; tl.to(o, {{ v: to, duration: 1.2, ease: "power2.out", onUpdate: () => {{ document.querySelector(id).textContent = Math.round(o.v).toLocaleString("en-US"); }} }}, at); }};
  count("#n1", {deployed:.0f}, 9.4); count("#n2", {cash_left:.0f}, 9.6); count("#n3", {risk:.0f}, 9.8);
  window.__timelines["main"] = tl;
  tl.seek(0);
}}
</script>
</body></html>"""


SVG_DEFS = """<svg width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="lg" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency="0.012 0.03" numOctaves="1" seed="7" result="n"/><feGaussianBlur in="n" stdDeviation="2.4" result="nb"/>
<feDisplacementMap in="SourceGraphic" in2="nb" scale="14" xChannelSelector="R" yChannelSelector="G"/></filter></svg>"""

CSS = r"""
:root{--bg:#0F171B;--surface-1:#122D39;--surface-warm:#311F15;--teal:#2C697F;--teal-text:#6FB3C8;--rose:#D6B9B9;--copper:#8A4C1C;--copper-text:#D9894A;
--ink:#F4EEEA;--gain:#6CC4A1;--loss:#E8766A;--hair:rgba(214,185,185,.16);--card:rgba(18,45,57,.78);--r:20px;
--font:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Arabic","IBM Plex Sans Arabic","Segoe UI","Noto Sans Arabic",system-ui,sans-serif;
--spring:cubic-bezier(.22,1,.36,1)}
*{box-sizing:border-box}
html{font:100%/1.5 var(--font);color:var(--ink);background:var(--bg);-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0;min-height:100vh}
.bg{position:fixed;inset:0;z-index:-1;background:radial-gradient(110% 55% at 50% -12%,rgba(138,76,28,.55),transparent 62%),radial-gradient(80% 40% at 100% 40%,rgba(44,105,127,.28),transparent 70%),linear-gradient(180deg,#0F171B 0%,#122D39 60%,#0F171B 100%)}
a{color:var(--teal-text);text-decoration:none} a:hover{text-decoration:underline}
.gain{color:var(--gain)} .loss{color:var(--loss)} .copper{color:var(--copper-text)} .teal{color:var(--teal-text)} .muted{color:var(--rose);opacity:.85} .small{font-size:.82rem}
main{max-width:760px;margin:0 auto;padding:96px 16px 120px}
section{margin:0 0 36px}
h1,h2,h3,h4{margin:0;font-weight:700}
h1{font-size:2.1rem;line-height:1.08;letter-spacing:-.02em}
h2{font-size:1.4rem;line-height:1.15;letter-spacing:-.015em;margin-bottom:14px}
h3{font-size:1.25rem;letter-spacing:-.01em} h3.sub{margin:22px 0 10px;font-size:1.05rem;color:var(--rose)}
h4{font-size:.85rem;color:var(--rose);margin:14px 0 6px;text-transform:uppercase;letter-spacing:.06em}
dl{margin:0} dd{margin:0}
/* Liquid Glass: floating controls only */
.glass{position:fixed;z-index:20;background:rgba(18,45,57,.55);-webkit-backdrop-filter:blur(22px) saturate(160%);backdrop-filter:blur(22px) saturate(160%);
 border:1px solid rgba(214,185,185,.18);border-top-color:rgba(255,255,255,.28);
 box-shadow:inset 0 1px 0 rgba(255,255,255,.18),inset 0 -1px 0 rgba(0,0,0,.35),0 12px 40px rgba(0,0,0,.45)}
.glass::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;background:linear-gradient(180deg,rgba(255,255,255,.10),transparent 42%)}
html.refract .glass{-webkit-backdrop-filter:url(#lg) blur(18px) saturate(170%);backdrop-filter:url(#lg) blur(18px) saturate(170%)}
.topbar{top:max(10px,env(safe-area-inset-top));left:50%;transform:translateX(-50%);width:min(740px,calc(100% - 20px));border-radius:22px;padding:8px 10px 8px 16px;display:flex;align-items:center;gap:8px}
.brand{display:flex;flex-direction:column;line-height:1.15;margin-inline-end:auto;min-width:0} .brand b{font-size:1rem;letter-spacing:-.01em} .brand small{color:var(--rose);font-size:.75rem}
.dock{bottom:max(12px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);border-radius:999px;padding:6px;display:flex;gap:2px}
.dock a{color:var(--ink);font-size:.84rem;font-weight:600;padding:10px 14px;border-radius:999px;min-height:44px;display:flex;align-items:center;transition:background .25s var(--spring)}
.dock a:hover,.dock a:focus-visible{background:rgba(214,185,185,.12);text-decoration:none}
.pill{appearance:none;font:inherit;font-size:.8rem;font-weight:600;color:var(--ink);background:rgba(15,23,27,.55);border:1px solid var(--hair);border-radius:999px;padding:8px 12px;min-height:36px;white-space:nowrap;cursor:pointer;transition:transform .1s ease-out}
.pill.gain{color:var(--gain);border-color:rgba(108,196,161,.4)} .pill.loss{color:var(--loss);border-color:rgba(232,118,106,.45)} .pill.copper{color:var(--copper-text);border-color:rgba(217,137,74,.45)}
.pill:active,.order:active,summary:active,.shot-btn:active{transform:scale(.97)}
.topbar .pill:active{transform:scale(.97)}
/* decision */
.hero{padding-top:6px}
.eyebrow{color:var(--rose);font-size:.82rem;letter-spacing:.08em;text-transform:uppercase;margin:0 0 8px}
.lede{color:var(--rose);margin:10px 0 0;font-size:1rem}
.orders{display:grid;gap:12px;margin:18px 0 16px}
.order{display:block;color:var(--ink);background:var(--card);border:1px solid var(--hair);border-radius:var(--r);padding:16px 18px;transition:transform .35s var(--spring),border-color .25s}
.order:hover{text-decoration:none;border-color:rgba(108,196,161,.45)}
.order-top{display:flex;align-items:center;gap:8px} .order-top .otype{margin-inline-start:auto;color:var(--rose);font-size:.8rem}
.tk{font-size:1.25rem;font-weight:800;letter-spacing:-.02em}
.big{font-size:2.1rem;font-weight:700;letter-spacing:-.02em;line-height:1.05;margin:10px 0 12px;font-variant-numeric:tabular-nums} .big small{font-size:1rem;color:var(--rose);font-weight:500}
.mini{display:grid;grid-template-columns:repeat(4,1fr);gap:8px} .mini dt{color:var(--rose);font-size:.75rem} .mini dd{font-weight:600;font-variant-numeric:tabular-nums}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:6px}
.kpis div{background:rgba(18,45,57,.55);border:1px solid var(--hair);border-radius:16px;padding:12px 14px} .kpis dt{color:var(--rose);font-size:.78rem;line-height:1.3}
.kpis dd{font-size:1.35rem;font-weight:700;letter-spacing:-.015em;font-variant-numeric:tabular-nums} .kpis.small dd{font-size:1.1rem}
.warn{unicode-bidi:plaintext;margin:14px 0 0;background:rgba(49,31,21,.85);border:1px solid rgba(217,137,74,.45);color:#F1D3BC;border-radius:16px;padding:12px 14px} .warn b{color:var(--copper-text)}
/* badges */
.badge{display:inline-flex;align-items:center;gap:5px;font-size:.78rem;font-weight:700;padding:4px 10px;border-radius:999px;background:rgba(15,23,27,.6);border:1px solid var(--hair);white-space:nowrap}
.badge i{font-style:normal} .badge.gain{color:var(--gain);border-color:rgba(108,196,161,.4)} .badge.loss{color:var(--loss);border-color:rgba(232,118,106,.45)}
.badge.copper{color:var(--copper-text);border-color:rgba(217,137,74,.45)} .badge.muted{color:var(--rose)}
/* cards */
.card{background:var(--card);border:1px solid var(--hair);border-radius:var(--r);padding:16px;margin:0 0 14px}
.cards{display:grid;gap:14px} .cards .card{margin:0}
.card-head{display:flex;align-items:flex-start;gap:10px;margin-bottom:12px} .card-head small{display:block;color:var(--rose);font-size:.82rem}
.card-meta{margin-inline-start:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.px{font-variant-numeric:tabular-nums;font-weight:600} .px em{font-style:normal;font-weight:600;font-size:.85rem}
.ring{position:relative;width:36px;height:36px;display:inline-grid;place-items:center} .ring svg{position:absolute;inset:0;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:rgba(214,185,185,.16);stroke-width:3.5} .ring-fg{fill:none;stroke:var(--teal-text);stroke-width:3.5;stroke-linecap:round} .ring b{font-size:.8rem}
.shot{margin:0 0 12px} .shot-btn{display:block;width:100%;padding:0;border:0;background:none;cursor:zoom-in;border-radius:16px;overflow:hidden;transition:transform .35s var(--spring)}
.shot img{display:block;width:100%;height:auto;background:#0b1114;border:1px solid var(--hair);border-radius:16px}
.shot figcaption{color:var(--rose);font-size:.78rem;margin-top:6px}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:6px;font-size:.78rem;color:var(--rose)} .legend span{display:inline-flex;align-items:center;gap:6px} .legend svg{width:18px;height:4px}
.noshot{border:1px dashed rgba(232,118,106,.6);color:var(--loss);border-radius:16px;padding:18px;text-align:center;margin-bottom:12px}
.plan{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:8px;margin:0 0 12px}
.plan div{background:rgba(15,23,27,.55);border-radius:14px;padding:9px 12px} .plan dt{color:var(--rose);font-size:.74rem} .plan dd{font-weight:700;font-size:1.05rem;font-variant-numeric:tabular-nums}
.reasons{margin:0 0 10px;padding-inline-start:18px} .reasons li{margin:4px 0}
.waitfor{background:rgba(49,31,21,.7);border-radius:14px;padding:10px 12px;margin:0 0 10px} .waitfor b{color:var(--copper-text)}
/* folds */
details{border-top:1px solid var(--hair)} .folds details:first-child{margin-top:4px}
summary{list-style:none;display:flex;align-items:center;gap:10px;padding:12px 2px;min-height:44px;cursor:pointer;font-weight:600;user-select:none;transition:transform .1s ease-out}
summary::-webkit-details-marker{display:none}
summary>i{margin-inline-start:auto;width:9px;height:9px;border-inline-end:2px solid var(--rose);border-bottom:2px solid var(--rose);transform:rotate(45deg);transition:transform .35s var(--spring)}
details[open]>summary>i{transform:rotate(225deg)}
.fold{padding:0 2px 14px;color:#E6DCD8;font-size:.94rem;animation:in .35s var(--spring)}
@keyframes in{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.ev{margin:0;padding-inline-start:20px} .ev li{margin:5px 0;font-variant-numeric:tabular-nums}
.parts{color:var(--rose);font-size:.85rem}
.news{list-style:none;margin:0;padding:0} .news li{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--hair)} .news li:last-child{border:0}
.news small{display:block;color:var(--rose)} .news p{margin:4px 0 0;color:#E6DCD8}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px} .kv div{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid var(--hair);padding:6px 0}
.kv dt{color:var(--rose)} .kv dd{font-weight:600;font-variant-numeric:tabular-nums;text-align:end}
.bookbar{display:flex;height:30px;border-radius:999px;overflow:hidden;margin:4px 0 12px;font-size:.78rem;font-weight:700}
.bookbar span{display:flex;align-items:center;padding:0 10px;color:#0F171B} .gainbg{background:var(--gain)} .lossbg{background:var(--loss);justify-content:flex-end}
/* positions */
.pos{padding:0} .pos>summary{padding:14px 16px;border:0} .pos>.fold{padding:0 16px 16px}
.pos-row{display:grid;grid-template-columns:auto auto 1fr auto;align-items:center;gap:4px 10px}
.pos-row .px{grid-row:2;grid-column:1/-1;justify-self:start;font-size:.86rem;color:var(--rose);font-weight:500} .pos-row em{font-style:normal;font-weight:700;justify-self:end}
.pos-row .why{grid-row:3;grid-column:1/-1;color:#E6DCD8;font-weight:400;font-size:.88rem}
.pos-row>i{grid-row:1;grid-column:4}
/* market */
.sectors{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:4px 16px} .sectors li{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--hair)}
.cats{list-style:none;margin:0;padding:0} .cats p{margin:8px 0} .cats small{color:var(--rose)} .cat-top{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
/* scan */
.tbl{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums}
th,td{padding:8px 10px;border-bottom:1px solid var(--hair);text-align:start;white-space:nowrap} tr:first-child th{color:var(--rose);font-weight:600}
.spark{width:96px;height:28px;display:block}
.drops{list-style:none;margin:0;padding:0} .drops li{padding:6px 0;border-bottom:1px solid var(--hair)} .drops b{color:var(--rose);margin-inline-end:8px}
/* footer */
footer{margin-top:40px;padding-top:18px;border-top:1px solid var(--hair);text-align:center;color:var(--rose);font-size:.86rem} footer p{margin:6px 0} .heart{color:var(--loss)}
/* dialogs */
dialog{border:0;padding:0;background:transparent;color:var(--ink);max-width:none;max-height:none}
dialog::backdrop{background:rgba(5,9,11,.72);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
#lightbox{width:100vw;height:100vh;display:none;place-items:center} #lightbox[open]{display:grid;animation:grow .35s var(--spring)}
#lightbox img{max-width:96vw;max-height:88vh;border-radius:16px;touch-action:pinch-zoom}
#lightbox .close,#recap .recap-bar{position:fixed;top:max(14px,env(safe-area-inset-top));inset-inline-end:14px}
#recap{width:100vw;height:100vh;display:none;place-items:center} #recap[open]{display:grid;animation:grow .35s var(--spring)}
.recap-frame{position:relative;width:min(92vw,calc(84vh * 9 / 16));aspect-ratio:9/16;border-radius:28px;overflow:hidden;border:1px solid var(--hair);box-shadow:0 30px 90px rgba(0,0,0,.6)}
.recap-frame iframe{position:absolute;top:0;left:0;width:1080px;height:1920px;border:0;transform-origin:0 0}
.recap-bar{display:flex;gap:8px}
@keyframes grow{from{opacity:0;transform:scale(.96)}to{opacity:1;transform:none}}
@media (min-width:900px){main{max-width:1120px}.cards{grid-template-columns:repeat(auto-fit,minmax(480px,1fr))}#decision .orders{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}}
@media (max-width:420px){h1{font-size:1.7rem}.big{font-size:1.75rem}.mini{grid-template-columns:repeat(2,1fr)}.kv,.sectors{grid-template-columns:1fr}.recap-btn{font-size:0;padding:8px 11px}.recap-btn::first-letter{font-size:.8rem}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:opacity .2s!important;scroll-behavior:auto!important}}
@media (prefers-reduced-transparency:reduce){.glass{background:#122D39;-webkit-backdrop-filter:none;backdrop-filter:none}.glass::before{display:none}}
@media (prefers-contrast:more){.card,.kpis div,.order,.glass{border-color:rgba(214,185,185,.6)} .card,.order{background:#122D39}}
@media print{.glass,.bg,dialog,.recap-btn{display:none!important}html,body{background:#fff;color:#111}main{padding:0;max-width:none}
 .card,.order,.kpis div{background:#fff;border-color:#ccc;break-inside:avoid}.card{page-break-inside:avoid}details>.fold{display:block}a{color:#0b5}}
"""

JS = r"""
(function(){
 var d=document,h=d.documentElement;
 try{var b=navigator.userAgentData&&navigator.userAgentData.brands||[];if(b.some(function(x){return /Chromium|Google Chrome|Microsoft Edge/.test(x.brand)}))h.classList.add('refract')}catch(e){}
 var lb=d.getElementById('lightbox'),lbi=lb&&lb.querySelector('img');
 d.addEventListener('click',function(e){
  var t=e.target.closest('[data-lightbox]');
  if(t&&lb){lbi.src=t.querySelector('img').src;lbi.alt=t.querySelector('img').alt;lb.showModal();return}
  if(e.target.closest('[data-close]')){var dl=e.target.closest('dialog');dl&&dl.close();return}
  if(e.target===lb){lb.close();return}
  if(e.target.closest('[data-recap]')){openRecap();return}
  if(e.target.closest('[data-replay]')){play();return}
 });
 var rc=d.getElementById('recap'),fr=rc&&rc.querySelector('iframe'),box=rc&&rc.querySelector('.recap-frame');
 var reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
 function fit(){if(box&&fr)fr.style.transform='scale('+(box.clientWidth/1080)+')'}
 function play(){try{var t=fr.contentWindow.__timelines.main;reduce?t.seek(10):t.restart()}catch(e){}}
 function openRecap(){if(!rc)return;rc.showModal();fit();setTimeout(play,120)}
 addEventListener('resize',fit);
 var y0=0;lb&&lb.addEventListener('touchstart',function(e){y0=e.touches[0].clientY},{passive:true});
 lb&&lb.addEventListener('touchend',function(e){if(e.changedTouches[0].clientY-y0>90)lb.close()},{passive:true});
})();
"""
