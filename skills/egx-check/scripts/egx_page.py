"""
egx_page.py - responsive research brief with static charts and expandable evidence.

The page is for the user; it is static (no script needed), so the PDF made from it looks the same.
Claude never reads this HTML: it reads history.jsonl / news.jsonl / runs.jsonl (egx_memory.py).
English labels, the reasoning text as written (Arabic), numbers and tickers in Latin digits.
Standard library only.
"""
from __future__ import annotations

import base64
import datetime as _dt
import html
import json
import pathlib
from urllib.parse import urlparse

DROP_WORDS = {"rr": "R:R below 2", "thin": "Too thin (< 5M EGP/day)", "wide": "Stop over 3 ATR", "noise": "Stop under 1 ATR",
              "invalid": "Resistance right above", "limit": "Near the daily limit", "new": "New listing",
              "no-plan": "No support / no plan", "unknown": "Chart unreadable", "early": "Opening range not complete",
              "no-setup": "No intraday setup", "spread": "Spread over 0.3%"}
VERDICT = {"valid": ("ok", "Valid"), "wait": ("wt", "Wait"), "not_valid": ("no", "Not valid")}
ACTION = {"hold": ("ok", "Hold"), "add": ("ok", "Add"), "tighten": ("wt", "Tighten stop"), "partial": ("wt", "Sell half"), "sell": ("no", "Sell"), "exit": ("no", "Exit")}
CATS = [("top30", "Top 30"), ("hot", "Hot"), ("t0", "Same day")]


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def safe_url(value):
    value = str(value or "")
    parsed = urlparse(value)
    return esc(value) if parsed.scheme in ("https", "http") and parsed.netloc else "#"


def num(x, d=2):
    if x is None or x == "":
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    return f"{x:,.{d}f}"


def money(x):
    return "—" if x is None else f"{float(x):,.0f}"


def signed(x, d=2):
    if x is None:
        return "—"
    x = float(x)
    return ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x):,.{d}f}%"


def nice_date(s):
    try:
        d = _dt.date.fromisoformat(str(s)[:10])
        return f"{d:%b} {d.day}"
    except (ValueError, TypeError):
        return str(s or "")


def nice_dt(s):
    try:
        d = _dt.datetime.fromisoformat(str(s)[:16])
        return f"{d:%a}, {d:%b} {d.day} · {d:%H:%M}"
    except (ValueError, TypeError):
        return str(s or "")


# ----------------------------------------------------------------- charts (static SVG)
def spark(vals, w=96, h=34):
    v = [x for x in (vals or []) if x is not None]
    if len(v) < 3:
        return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1
    y = lambda a: 3 + (hi - a) / rng * (h - 6)
    x = lambda i: i / (len(v) - 1) * w
    col = "var(--red)" if v[-1] < v[0] else "var(--green)"
    d = " ".join(("L" if i else "M") + f"{x(i):.1f} {y(a):.1f}" for i, a in enumerate(v))
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true">'
            f'<line x1="0" x2="{w}" y1="{y(v[0]):.1f}" y2="{y(v[0]):.1f}" stroke="var(--fg3)" stroke-dasharray="1 3"/>'
            f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" stroke-linejoin="round"/></svg>')


def candle_chart(bars, levels, zone=None, W=360, H=190, label=""):
    """bars: [[date,o,h,l,c], ...]; levels: [(price, colour, tag, dashed)]; zone: (lo, hi)"""
    bars = [b for b in (bars or []) if len(b) >= 5][-60:]
    if len(bars) < 5:
        return ""
    R, T, B = 62, 8, 10
    vals = [b[2] for b in bars] + [b[3] for b in bars] + [p for p, *_ in levels if p]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * .06 or 1
    lo, hi = lo - pad, hi + pad
    y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    cw = (W - R - 8) / len(bars)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">']
    for g in range(4):
        gy = T + g * (H - T - B) / 3
        o.append(f'<line x1="0" x2="{W - R}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="var(--grid)" stroke-width=".5"/>')
    if zone and zone[0] and zone[1]:
        top, bot = y(max(zone)), y(min(zone))
        o.append(f'<rect x="0" width="{W - R}" y="{top - 3:.1f}" height="{max(6, bot - top + 6):.1f}" fill="var(--zonefill)"/>')
    for i, bar in enumerate(bars):
        _, op, h, l, c = bar[:5]
        cx = 4 + i * cw + cw / 2
        col = "var(--green)" if c >= op else "var(--red)"
        o.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(h):.1f}" y2="{y(l):.1f}" stroke="{col}" stroke-width="1"/>')
        o.append(f'<rect x="{cx - cw * .32:.1f}" width="{cw * .64:.1f}" y="{y(max(op, c)):.1f}" height="{max(1, abs(y(op) - y(c))):.1f}" fill="{col}" rx=".6"/>')
    for p, colr, tag, dashed in levels:
        if not p:
            continue
        ly = y(p)
        o.append(f'<line x1="0" x2="{W - R}" y1="{ly:.1f}" y2="{ly:.1f}" stroke="{colr}" stroke-width="1.2" stroke-dasharray="{"4 3" if dashed else "none"}"/>' )
        o.append(f'<rect x="{W - R + 4}" y="{ly - 9:.1f}" width="{R - 6}" height="18" rx="4" fill="{colr}"/>')
        o.append(f'<text x="{W - R + 4 + (R - 6) / 2:.1f}" y="{ly + 4.2:.1f}" text-anchor="middle" fill="#fff" font-size="11" font-weight="600">{esc(tag)} {p:.2f}</text>')
    o.append("</svg>")
    return "".join(o)


def img_uri(path):
    p = pathlib.Path(path or "")
    if not path or not p.is_file():
        return None
    mime = "image/png" if p.read_bytes()[:4] == b"\x89PNG" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


# ----------------------------------------------------------------- blocks
def tier_tag(n):
    t = n.get("tier")
    return f'<span class="tier t{esc(t)}">T{esc(t)}</span>' if t else ""


def news_items(items, empty_text=None):
    out = []
    for n in items or []:
        dot = {"+": "pos", "-": "neg"}.get(n.get("impact"), "neu")
        extra = []
        if n.get("fresh"):
            extra.append("fresh")
        if n.get("material"):
            extra.append("material")
        if n.get("paywalled"):
            extra.append("headline only")
        link = f'<a href="{safe_url(n.get("url"))}" target="_blank" rel="noopener">{esc(n.get("source") or "source")}</a>'
        out.append(f'<div class="item"><i class="dot {dot}"></i><div><div class="t" dir="auto">{esc(n.get("title"))}</div>'
                   f'<div class="m">{tier_tag(n)}{link}<span class="n">· {esc(nice_date(n.get("date")))}</span>'
                   + "".join(f"<span>· {esc(x)}</span>" for x in extra) + "</div>"
                   + (f'<div class="s" dir="auto">{esc(n.get("summary"))}</div>' if n.get("summary") else "") + "</div></div>")
    if not out and empty_text:
        out.append(f'<div class="empty">{esc(empty_text)}</div>')
    return "".join(out)


def news_block(s, created):
    q = s.get("news_queries") or []
    langs = []
    for x in q:
        txt = x.get("query") if isinstance(x, dict) else str(x)
        langs.append("AR" if any("؀" <= ch <= "ۿ" for ch in txt or "") else "EN")
    meta = f'{len(q)} searches · {" + ".join(sorted(set(langs), reverse=True))}' if q else "no searches logged"
    items = list(s.get("news") or [])
    reds = s.get("red_events") or []
    red_html = "".join(
        f'<div class="item"><i class="dot neg"></i><div><div class="t">{esc((e.get("type") or "event").capitalize())} on {esc(e.get("date") or "unknown date")}</div>'
        f'<div class="m">{tier_tag(e)}<a href="{safe_url(e.get("url"))}" target="_blank" rel="noopener">{esc(e.get("source") or "source")}</a></div></div></div>'
        for e in reds)
    body = news_items(items, None if reds else "No dated news retained. This does not confirm the absence of material news.")
    return f'<div class="news"><h3>News <em>{esc(meta)}</em></h3>{body}{red_html}</div>'


def gates_bar(s):
    G = s.get("gates") or []
    if not G:
        return ""
    ok = sum(1 for g in G if g.get("ok"))
    dots = "".join(f'<i class="{"" if g.get("ok") else "bad"}"></i>' for g in G)
    fails = [g for g in G if not g.get("ok")]
    txt = f"{ok} of {len(G)} checks verified" if not fails else "Failed: " + ", ".join(g["gate"] for g in fails)
    note = "".join(f'<div class="gfail">✘ {esc(g["gate"])}: {esc(g.get("note"))}</div>' for g in fails)
    return f'<div class="ver"><div class="dots" aria-hidden="true">{dots}</div><span>{esc(txt)}</span></div>{note}'


_STEPS = {}   # run["steps"] of the report being built (set by build_html)


def steps_bar(key, label="steps"):
    """the atomic-step ledger of one ticker (key) or of the run (key None): one dot per step, every open / failed atomic step spelled out"""
    G = [g for g in (_STEPS.get("groups") or []) if g.get("tk") == key]
    if not G:
        return ""
    n, done = sum(g["n"] for g in G), sum(g["done"] + g["skipped"] for g in G)
    att = sum(len(g.get("attested") or []) for g in G)
    dots = "".join(f'<i class="{"bad" if g.get("bad") else ""}" title="{esc(g["step"] + " " + g["title"])}"></i>' for g in G)
    typed = sum(len(g.get("typed") or []) for g in G)
    parts = [f"{sum(g['done'] for g in G) - att - typed} script-checked"] + ([f"{typed} typed by Claude (shape checked only)"] if typed else []) + ([f"{att} stated by Claude"] if att else [])
    txt = f"{done} of {n} atomic {label} recorded · " + " · ".join(parts)
    note = "".join(f'<div class="gfail">✘ {esc(b["id"])} {esc(g["title"])}: {esc(b.get("why") or b.get("status"))}</div>' for g in G for b in g.get("bad") or [])
    return f'<div class="ver"><div class="dots" aria-hidden="true">{dots}</div><span>{esc(txt)}</span></div>{note}'


def pass_card(s, row, cat_label, rank):
    t0 = s.get("mode") == "t0"
    p = ((s.get("t0") or {}).get("plan") if t0 else s.get("plan")) or {}
    v = s.get("verdict") or "wait"
    cls, word = VERDICT.get(v, ("wt", v))
    order_word = ""
    if row and row.get("shares"):
        order_word = " · Planned limit" if row.get("order") == "buy now" else " · Planned limit"
    tint = {"ok": "pass", "wt": "pass wait", "no": "pass no"}[cls]
    sub = " · ".join(x for x in [s.get("title"), s.get("sector"), f"#{rank} in {cat_label}" if rank else cat_label] if x)
    quote = (s.get("t0") or {}) if t0 else s
    chg = quote.get("dayChg") if t0 else s.get("chg")
    observed = ((quote.get("session") or {}).get("day") if t0 else s.get("asOf")) or "date unknown"
    out = [f'<article class="{tint}" id="stock-{esc(s.get("tk"))}">',
           f'<div class="top"><div><div class="tk">{esc(s.get("tk"))}</div><div class="co">{esc(sub)}</div></div>'
           f'<span class="badge {cls}"><i></i>{esc(word + order_word)}</span></div>',
           f'<div class="price"><b class="n">{esc(num(quote.get("last")))}</b>'
           f'<span class="n {"up" if (chg or 0) >= 0 else "dn"}">{esc(signed(chg))}</span><small class="sub">EGP · {esc(observed)}</small></div>']
    out.append('<div class="plan-layout"><div class="visual">')
    sup = (s.get("zones") or {}).get("support") or {}
    levels = [(p.get("target"), "var(--green)", "T", False), (p.get("entry"), "var(--blue)", "E", True), (p.get("stop"), "var(--red)", "S", False)]
    if t0:
        T = s.get("t0") or {}
        levels.append((T.get("vwap"), "var(--purple)", "VWAP", True))
        rng = T.get("openingRange") or {}
        chart = candle_chart(T.get("candles"), levels, (rng.get("lo"), rng.get("hi")), H=190,
                             label=f'{s.get("tk")} 5-minute candles today with VWAP, opening range, entry, stop and target')
    else:
        chart = candle_chart(s.get("candles"), levels, (sup.get("lo"), sup.get("hi")),
                             H=190 if v == "valid" else 150, label=f'{s.get("tk")} daily candles with entry, stop and target')
    if chart:
        out.append(f'<div class="chart-heading"><span>PRICE STRUCTURE</span><span>{"5 MIN / INTRADAY" if t0 else "DAILY / LAST 60 BARS"}</span></div><div class="chart">{chart}</div><div class="chart-legend"><span><i class="entry-key"></i>Entry</span><span><i class="target-key"></i>Target</span><span><i class="stop-key"></i>Stop</span></div>')
    out.append('</div><div class="plan-content">')
    if v == "wait" and s.get("wait_for"):
        out.append(f'<div class="wf">Waiting for: {esc(s["wait_for"])}</div>')
    rr = p.get("rr")
    fields = [("Entry", num(p.get("entry")), "var(--blue)"), ("Stop", num(p.get("stop")), "var(--red)"), ("Target", num(p.get("target")), "var(--green)")]
    if row and row.get("shares"):
        fields += [("Shares", f'{row["shares"]:,}', None), ("Value", money(row.get("value")), None), ("R:R", rr, None)]
    else:
        fields += [("R:R", rr, None), ("Stop ATR", p.get("stopATR") or p.get("stopATR5"), None), ("Setup", (p.get("type") or p.get("setup") or "—").replace("-", " "), None)]
    if p.get("maxEntry") and p.get("type") == "pullback-at-support":
        fields.append(("Max entry", num(p.get("maxEntry")), "var(--blue)"))
    if p.get("rr_net") is not None:
        fields.append(("R:R after fees", p.get("rr_net"), None))
    out.append('<div class="fields">' + "".join(
        f'<div><span>{esc(a)}</span><b class="n" style="color:{c or "inherit"}">{esc(b)}</b></div>' for a, b, c in fields) + "</div>")
    if row and row.get("shares"):
        when = "Limit plan · confirm settlement and sell eligibility" if not t0 else "Limit today · exit by 14:10 (T0)"
        out.append(f'<div class="order"><b class="n">Plan {row["shares"]:,} @ {esc(num(row.get("entry")))}</b><span>{esc(when)}</span></div>')
    elif row and row.get("note"):
        out.append(f'<div class="order"><b>Not funded</b><span>{esc(row["note"])}</span></div>')
    if not row:
        out.append('<div class="order"><b>Not allocated</b><span>Watchlist only · recheck the signal and risk limits before any order.</span></div>')
    reasons = s.get("reasons") or []
    if reasons:
        out.append('<div class="why"><h3>The rationale</h3>' + "".join(f'<p dir="auto">{esc(r)}</p>' for r in reasons[:5]) + "</div>")
    if row and row.get("shares"):
        out.append('<div class="scenario"><div><span>Net at target</span><b class="up n">+' + esc(money(row.get("gain_if_target"))) + ' EGP</b></div><div><span>Estimated stop loss</span><b class="dn n">−' + esc(money(row.get("loss_if_stop"))) + ' EGP</b></div><div><span>Net reward / risk</span><b class="n">' + esc(num(row.get("rr_net_sized"))) + '</b></div></div>')
    out.append("</div></div>")
    out.append('<details class="evidence"><summary>Behind the analysis <span>Sources &amp; verification ＋</span></summary>')
    out.append(news_block(s, None))
    out.append(gates_bar(s))
    out.append(steps_bar(s.get("tk")))
    shot = s.get("_shot_uri")
    if shot:
        when = s.get("_shot_time") or ""
        out.append(f'<div class="shot"><figure><img src="{shot}" alt="{esc(s.get("tk"))} on ThndrX with the drawn levels" loading="lazy">'
                   f'<figcaption>ThndrX chart · captured evidence {esc(when)}</figcaption></figure></div>')
    out.append("</details></article>")
    return "".join(out)


# ----------------------------------------------------------------- page
def build_html(run: dict, cfg: dict, fname: str, version: str, memory_counts: dict | None = None) -> str:
    global _STEPS
    _STEPS = run.get("steps") or {}
    meta, mk, al = run.get("meta") or {}, run.get("market") or {}, run.get("allocation") or {}
    eg = mk.get("egx30") or {}
    stocks = run.get("stocks") or []
    rows = {r["tk"]: r for r in al.get("rows") or []}
    cmd = meta.get("command") or "EGX"
    o = []
    o.append('<div class="masthead"><a class="brand" href="#top"><span class="brand-mark">E</span><span>EGX<span class="brand-sub">THE MARKET DESK</span></span></a><span class="mast-note">Read the market.<br>Define the risk.</span></div>')
    o.append(f'<header class="hdr" id="top"><div><span class="eyebrow">SESSION RESEARCH / {esc(cmd)}</span><h1>Market focus.<br><em>Risk defined.</em></h1></div><div class="edition"><span class="eyebrow">YOUR SESSION BRIEF</span><b>{esc(nice_date(meta.get("trading_day")))}</b><p>The signal. The levels. The risk.<br>Your plan for the session.</p><small>Prepared {esc(nice_dt(meta.get("created")))}</small></div></header>')
    o.append('<nav class="nav" aria-label="Report sections"><a href="#overview"><span>01</span> The overview</a><a href="#ideas"><span>02</span> Trade plans</a><a href="#costs"><span>03</span> Risk &amp; costs</a><span class="nav-end">EGYPTIAN EXCHANGE / EGP</span></nav>')
    if meta.get("demo") or any(str(x.get("tk", "")).startswith("DEMO") for x in stocks):
        o.append('<aside class="demo">SYNTHETIC DEMO · Illustrative prices and evidence. Not a live market report.</aside>')
    o.append('<div class="hero" id="overview">')
    if eg:
        sp = [x for x in (eg.get("spark") or []) if x is not None][-21:]
        # the chip and the line always describe the same 20 sessions
        ch = round((sp[-1] / sp[0] - 1) * 100, 2) if len(sp) >= 2 and sp[0] else eg.get("ch20")
        lab = "20d"
        o.append(f'<div class="row"><div><div class="eyebrow">THE BENCHMARK</div><div class="sym">EGX30</div><div class="sub">{esc(eg.get("regime") or "unknown")}</div></div>'
                 f'{spark(sp)}<div class="px"><b class="n">{esc(money(eg.get("last")))}</b>'
                 f'<span class="chip {"dn" if (ch or 0) < 0 else "up"} n">{esc(signed(ch))} <small>{lab}</small></span></div></div>')
    # summary
    orders = [r for r in al.get("rows") or [] if r.get("shares")]
    deep = [s for s in stocks if s.get("verdict") in ("valid", "wait", "not_valid")]
    if al:
        o.append('<section class="sum"><div class="k"><span class="live-dot"></span> THE CAPITAL PLAN</div><div class="allocation-label">Planned allocation</div>'
                 f'<div class="big n">{esc(money(al.get("deployed")))}<small>EGP</small></div>'
                 '<div class="stats">'
                 f'<div><span>Orders</span><b class="n">{len(orders)}</b></div>'
                 f'<div><span>Cash kept</span><b class="n">{esc(money(al.get("cash_left")))}</b></div>'
                 f'<div><span>Est. stop loss</span><b class="n">{esc(money(al.get("total_risk")))}</b></div></div>'
                 + (f'<p class="note" dir="auto">{esc(meta.get("summary"))}</p>' if meta.get("summary") else "")
                 + "".join(f'<p class="warn" dir="auto">{esc(w)}</p>' for w in al.get("warnings") or [])
                 + "</section>")
    elif meta.get("summary"):
        o.append(f'<section class="sum"><p class="note" dir="auto">{esc(meta.get("summary"))}</p></section>')
    if al and meta.get("amount") and float(meta["amount"]) > 0:
        portion = max(0, min(100, float(al.get("deployed") or 0) / float(meta["amount"]) * 100))
        o[-1] = o[-1].replace('</section>', f'<div class="allocation-foot"><div class="allocation-track" role="img" aria-label="{portion:.0f}% of the run budget allocated"><span style="width:{portion:.2f}%"></span></div><div><span>{portion:.0f}% allocated · entry fees included</span><span>{100-portion:.0f}% held in reserve</span></div></div></section>')
    o.append('</div>')
    counts = {v: sum(x.get("verdict") == v for x in stocks) for v in ("valid", "wait", "not_valid", "dropped")}
    o.append('<section class="decision-strip" id="ideas" aria-label="Decision overview">' + ''.join(f'<div><b class="n">{counts[v]}</b><span>{label}</span></div>' for v, label in [("valid", "Rules passed"), ("wait", "Watch & wait"), ("not_valid", "Not valid"), ("dropped", "Filtered out")]) + '</section>')
    o.append('<div class="context-grid">')
    # positions
    hs = [h for h in run.get("holdings") or [] if not h.get("is_fund")]
    if hs:
        lst = []
        for h in hs:
            cls, word = ACTION.get(h.get("action") or "hold", ("ok", "Hold"))
            pl = h.get("pnlPct")
            inc = "".join(f'<div class="sub bad">✘ incomplete check: {esc(x)}</div>' for x in (h.get("check_incomplete") or [])[:3])
            mg = h.get("manage") or {}
            if mg:   # the action comes from egx.py manage: show its rule and numbers, not only the label
                bits = [f"rule {mg.get('rule')}"] + ([f"sell {mg['sell_shares']:,} shares"] if mg.get("sell_shares") else []) + ([f"stop to {num(mg['new_stop'])}"] if mg.get("new_stop") else [])
                nb = mg.get("numbers") or {}
                bits += [f"{k} {nb[k]}" for k in ("r_now", "sessions_held") if nb.get(k) is not None]
                inc += f'<div class="sub n">{esc(" · ".join(bits))}</div>' + "".join(f'<div class="sub" dir="auto">{esc(w)}</div>' for w in (mg.get("why") or [])[:2])
                if mg.get("missing"):
                    inc += f'<div class="sub bad">✘ missing for full management: {esc(", ".join(mg["missing"]))}</div>'
            lst.append(f'<div class="li"><div><b>{esc(h.get("tk"))}</b><div class="sub" dir="auto">{esc((h.get("reasons") or [""])[0])}</div>{inc}</div>'
                       f'<div class="r"><span class="badge {cls}"><i></i>{esc(word)}</span><span class="n {"up" if (pl or 0) >= 0 else "dn"}">{esc(signed(pl))}</span></div></div>')
        o.append(f'<section class="context-card"><h2>Portfolio notes<span>YOUR POSITIONS</span></h2><div class="list">{"".join(lst)}</div></section>')
    # market news and catalysts
    cats = run.get("catalysts") or []
    macro = mk.get("macro") or []
    if cats or macro:
        items = []
        for c in cats:
            src = (c.get("sources") or [{}])[0]
            flag = (f'<span class="flag {"muted" if c.get("priced_in") else ""}">{"Priced in" if c.get("priced_in") else "Not priced in"}'
                    f' · {esc(signed(c.get("moved_pct")))} ({esc(c.get("moved_atr"))} ATR)</span>') if c.get("moved_pct") is not None else ""
            rumour = '<span class="flag no">Rumour</span>' if c.get("status") == "rumour" else ""
            items.append(f'<div class="item"><i class="dot {"pos" if c.get("direction") == "+" else "neg" if c.get("direction") == "-" else "neu"}"></i><div>'
                         f'<div class="t" dir="auto"><b>{esc(c.get("tk"))}</b> · {esc(c.get("summary"))}</div>'
                         f'<div class="m">{tier_tag(src)}<a href="{safe_url(src.get("url"))}" target="_blank" rel="noopener">{esc(src.get("source") or "source")}</a>'
                         f'<span class="n">· {esc(nice_date(c.get("date") or src.get("date")))}</span>{flag}{rumour}</div></div></div>')
        o.append(f'<section class="card intelligence"><h2>The wider picture<span>NEWS &amp; CATALYSTS</span></h2>{"".join(items)}{news_items(macro)}</section>')
    o.append("</div>")
    # categories
    has_cat = any(s.get("category") for s in stocks)
    groups = [(k, lab, [s for s in deep if s.get("category") == k]) for k, lab in CATS] if has_cat else [(None, "Checked", deep)]
    if has_cat:
        other = [s for s in deep if s.get("category") not in {k for k, _ in CATS}]
        if other:
            groups.append((None, "Other checks", other))
    for key, lab, items in groups:
        if key == "t0" and not items and meta.get("t0_status"):
            o.append(f'<div class="sect">{esc(lab)}</div><div class="list"><div class="li"><span class="sub">{esc(meta["t0_status"])}</span></div></div>')
            continue
        if not items:
            continue
        o.append(f'<div class="sect">{esc(lab)} <em class="n">{len(items)}</em></div>')
        items = sorted(items, key=lambda s: (s.get("rank") or 99))
        o.append('<div class="ideas-grid">')
        for i, s in enumerate(items, 1):
            o.append(pass_card(s, rows.get(s.get("tk")), lab if key else cmd, s.get("rank") or (i if key else None)))
        o.append("</div>")
    # dropped
    drops = {}
    for s in stocks:
        if s.get("verdict") == "dropped":
            why = DROP_WORDS.get(s.get("drop"), (s.get("auto_reasons") or [s.get("drop") or "dropped"])[0])
            drops.setdefault(why, []).append(s.get("tk"))
    if drops:
        o.append('<div class="sect">Dropped</div><div class="list">' + "".join(
            f'<div class="li"><b>{esc(" · ".join(v))}</b><span class="sub">{esc(k)}</span></div>' for k, v in drops.items()) + "</div>")
    unchecked = [s.get("tk") for s in stocks if s.get("verdict") == "unchecked"]
    unknown = [x.get("tk", "unknown") if isinstance(x, dict) else str(x) for x in run.get("unknown") or []]
    if unchecked or unknown:
        o.append('<section class="card"><h3>Coverage gaps · no allocation</h3>' + (f'<p class="sub">Quick scan only: {esc(", ".join(unchecked))}</p>' if unchecked else '') + (f'<p class="warn">Unavailable: {esc(", ".join(unknown))}</p>' if unknown else '') + '</section>')
    # costs
    if al:
        if al.get("usd_egp_estimated"):
            o.append('<p class="warn">Monthly cost estimate uses an unverified USD/EGP assumption of ' + esc(al.get("usd_egp_used")) + '; update the exchange rate before relying on the hurdle.</p>')
        o.append('<section class="card costs" id="costs"><h3>Risk &amp; cost assumptions</h3><p class="sub">Stop loss includes configured fees and slippage; gaps or trading halts can produce larger losses. Reward/risk is a scenario, not a probability.</p><div class="stats">'
                 f'<div><span>Fixed / month</span><b class="n">{esc(money(al.get("fixed_monthly")))}</b></div>'
                 f'<div><span>Break-even / month</span><b class="n">{esc(al.get("break_even_monthly_pct"))}%</b></div>'
                 f'<div><span>Risk / trade</span><b class="n">{esc(money(al.get("risk_budget_per_trade")))}</b></div></div></section>')
    run_steps = steps_bar(None, "run steps")
    if run_steps:
        o.append(f'<section class="card steps"><h3>Step ledger <em>{esc(_STEPS.get("command"))} · started {esc(_STEPS.get("started"))}</em></h3>{run_steps}</section>')
    mc = memory_counts or {}
    o.append(f'<div class="mem"><span>Saved to history: {mc.get("stocks", 0)} stocks · {mc.get("news", 0)} news</span><code>{esc(fname.rsplit(".", 1)[0])}</code></div>')
    foot = cfg.get("footer") or {}
    o.append(f'<p class="foot" dir="rtl">تحليل تعليمي مش نصيحة استثمارية؛ القرار والأوامر ليك.</p>'
             f'<p class="foot">egx-thndrx-trading v{esc(version)} · {esc(foot.get("author", ""))}</p>')
    title = f"{cmd} · {(meta.get('created') or '')[:16].replace('T', ' ')}"
    return (f'<!doctype html><html lang="en" dir="ltr"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="color-scheme" content="dark">'
            f'<meta name="theme-color" content="#090d0c"><title>{esc(title)}</title>'
            f'<!-- FOR CLAUDE: do not read this page. Use: egx.py recall TICKER / egx.py news TICKER / egx.py runs (history.jsonl, news.jsonl, runs.jsonl in this folder). Full detail: egx.py read {esc(fname)} --ticker TK -->'
            f'<style>{CSS}</style></head><body><main class="page">{"".join(o)}</main>'
            f'<script id="egx-data" type="application/json">{slim_json(run)}</script></body></html>')


def slim_json(run: dict) -> str:
    """the run without pictures and candles (they live in the image files and the chart)"""
    def strip(d):
        return {k: v for k, v in d.items() if k not in ("screenshot_b64", "candles", "_shot_uri", "_shot_time", "draw")}
    r = dict(run)
    r["stocks"] = [strip(s) for s in run.get("stocks") or []]
    r["holdings"] = [strip(h) for h in run.get("holdings") or []]
    r["market"] = strip(run.get("market") or {})
    return json.dumps(r, ensure_ascii=False).replace("</", "<\\/")


CSS = r"""
:root{color-scheme:dark;--bg:#090d0c;--card:#111815;--card2:#1c2822;--fg:#eef4e8;--fg2:#a4b2a8;--fg3:#95a598;--sep:#2b3a31;--grid:#26372e;--green:#c2f853;--red:#ff786a;--orange:#f6bb58;--blue:#79bcff;--purple:#c6a1ff;--zonefill:#c2f8530d;--serif:Georgia,'Times New Roman',serif;--sys:-apple-system,BlinkMacSystemFont,'Segoe UI',Tahoma,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 var(--sys);-webkit-font-smoothing:antialiased;print-color-adjust:exact;-webkit-print-color-adjust:exact}a{color:inherit;text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,summary:focus-visible{outline:2px solid var(--green);outline-offset:5px}.page{max-width:1280px;padding:0 56px 36px;margin:auto;display:grid;grid-template-columns:minmax(0,1fr);gap:28px}.page>*{min-width:0}.n{font-variant-numeric:tabular-nums}[dir=auto],[dir=rtl]{unicode-bidi:plaintext}svg{display:block;max-width:100%;height:auto}.masthead{display:flex;align-items:center;justify-content:space-between;padding:28px 0 22px;border-bottom:1px solid var(--fg)}.brand{display:flex;align-items:center;gap:12px;font-size:22px;font-weight:650;line-height:1.25;letter-spacing:.02em}.brand-mark{display:grid;place-items:center;width:42px;height:46px;background:var(--fg);color:var(--bg);font:italic 34px var(--serif);border-radius:22px 22px 3px 3px}.brand-sub{display:block;font-size:8px;font-weight:500;letter-spacing:.19em;margin-top:5px}.mast-note{text-align:right;font:italic 13px/1.5 var(--serif);color:var(--fg2)}.hdr{display:flex;justify-content:space-between;align-items:center;gap:40px;padding:24px 0 16px}.eyebrow{font-size:9px;letter-spacing:.17em;font-weight:600;color:var(--fg2)}.hdr h1{font:normal clamp(48px,5.5vw,78px)/1.04 var(--serif);letter-spacing:-.045em;margin:20px 0 0}.hdr h1 em{font-weight:400;color:var(--green)}.edition{border-left:1px solid var(--sep);padding-left:36px;width:270px;flex-shrink:0}.edition b{display:block;font:40px/1.3 var(--serif);margin-top:12px}.edition p{font-size:12px;color:var(--fg2);margin:10px 0 20px}.edition small{font-size:10px;color:var(--fg2)}.nav{display:flex;align-items:center;gap:34px;padding:18px 0;border-block:1px solid var(--sep);font-size:11px}.nav a{white-space:nowrap}.nav a span{font:italic 12px var(--serif);color:var(--fg2);margin-right:8px}.nav-end{margin-left:auto;font-size:8px;letter-spacing:.14em;color:var(--fg2)}.demo{font-size:10px;color:var(--orange);padding:10px 14px;background:#f6bb580a;border-left:2px solid var(--orange);margin-top:-8px}.hero{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:20px;align-items:stretch}.hero:has(>:only-child){grid-template-columns:1fr}.sum{order:0;background:linear-gradient(120deg,#1c3021,#111c16);color:var(--fg);padding:30px 34px;border-radius:3px;position:relative;overflow:hidden;display:grid;gap:12px;align-content:start}.sum .k{font-size:9px;letter-spacing:.16em;color:#b4c5ad;display:flex;gap:8px;align-items:center}.live-dot{height:5px;width:5px;background:var(--green);border-radius:50%}.allocation-label{font:20px var(--serif);margin-top:8px;color:#dce8d0}.big{font:54px/1.15 var(--serif);letter-spacing:-.035em}.big small{font:11px var(--sys);letter-spacing:.06em;color:#b4c5ad;margin-left:12px}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.sum .stats{padding-top:18px;margin-top:8px;border-top:1px solid #ffffff22}.stats div,.fields div,.scenario div{display:grid;gap:6px;min-width:0}.stats span,.fields span,.scenario span{font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:var(--fg2)}.sum .stats span{color:#b4c5ad}.stats b{font-size:20px;font-weight:500}.note{color:var(--fg2);margin:6px 0 0;font-size:12px;line-height:1.8}.sum .note{color:#bdcbb5}.warn{color:var(--orange);font-size:12px;margin:0}.sum .warn{color:#f0d19b}.allocation-foot{margin-top:8px}.allocation-track{height:4px;background:#ffffff20;border-radius:5px;overflow:hidden}.allocation-track span{display:block;height:100%;background:var(--green)}.allocation-foot>div:last-child{display:flex;justify-content:space-between;gap:12px;font-size:9px;color:#b4c5ad;margin-top:9px}.row{order:1;background:#121b16;border:1px solid var(--sep);border-radius:3px;padding:28px;display:flex;flex-direction:column;align-items:stretch;gap:12px;justify-content:space-between;position:relative}.row .sym{font:42px/1.2 var(--serif);margin-top:12px}.row .sub{font-size:11px;margin-top:5px}.row>svg{width:100%;height:72px;order:2;margin:10px 0}.px{display:flex;flex-wrap:wrap;gap:12px;align-items:center;order:1}.px b{font-size:25px;font-weight:400}.chip{font-size:11px;padding:4px 7px;border-radius:3px;background:#ffffff08}.chip small{color:var(--fg2);font-size:9px;margin-left:3px}.decision-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));padding:22px 0;border-bottom:1px solid var(--sep);gap:20px;margin-top:-8px}.decision-strip>div{display:flex;align-items:center;gap:12px;border-right:1px solid var(--sep)}.decision-strip>div:last-child{border:0}.decision-strip b{font:36px/1 var(--serif);font-weight:400}.decision-strip span{font-size:10px;color:var(--fg2)}.context-grid{display:grid;grid-template-columns:1fr 1.2fr;gap:34px;align-items:start}.context-grid:has(>:only-child){grid-template-columns:1fr}.context-grid:empty{display:none}.context-card h2,.intelligence h2{margin:0 0 18px;font:25px var(--serif)}h2 span{display:block;font:8px var(--sys);letter-spacing:.16em;color:var(--fg2);margin-top:8px}.context-grid .card{background:none;border:0;padding:0}.list{border-top:1px solid var(--sep);border-bottom:1px solid var(--sep)}.li{padding:17px 0;display:flex;justify-content:space-between;align-items:start;gap:18px}.li+.li{border-top:1px solid var(--sep)}.li b{font-size:13px;letter-spacing:.04em}.li .r{display:grid;justify-items:end;gap:8px;font-size:12px}.sub,.co{font-size:12px;color:var(--fg2)}.sub.bad,.bad{color:var(--red)}.card{padding:24px;background:var(--card);border:1px solid var(--sep);border-radius:3px;display:grid;gap:16px}.card h3,.news h3{font-size:9px;letter-spacing:.12em;text-transform:uppercase;margin:0;color:var(--fg2);display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}.card h3 em,.news h3 em{font-style:normal;font-weight:400;letter-spacing:0;text-transform:none}.sect{display:flex;align-items:center;gap:14px;font:31px var(--serif);margin:18px 0 -10px}.sect:after{content:'';height:1px;background:var(--sep);flex:1;margin-left:6px}.sect em{font:10px var(--sys);border:1px solid var(--sep);border-radius:50%;width:24px;height:24px;display:grid;place-items:center;color:var(--fg2)}.ideas-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:24px}.pass{background:var(--card);border:1px solid var(--sep);border-radius:4px;box-shadow:0 5px 18px #243b3304;overflow:hidden;min-width:0}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;padding:25px 30px 12px}.tk{font:35px/1.2 var(--serif);letter-spacing:-.03em}.co{font-size:10px;margin-top:5px}.badge{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border-radius:3px;padding:6px 9px;background:#c2f85312;font-size:10px;font-weight:500;color:var(--green)}.badge i{width:4px;height:4px;background:currentColor;border-radius:50%}.badge.wt{background:#f6bb5812;color:var(--orange)}.badge.no{background:#ff786a12;color:var(--red)}.up,.ok{color:var(--green)}.dn,.no{color:var(--red)}.wt{color:var(--orange)}.price{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;padding:0 30px 22px}.price b{font-size:23px;font-weight:400}.price span{font-size:11px}.price small{font-size:9px;color:var(--fg3);margin-left:auto}.plan-layout{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);border-top:1px solid var(--sep)}.plan-layout>*{min-width:0}.visual{padding:26px 24px 24px;background:#0d1410}.chart-heading{font-size:8px;letter-spacing:.08em;color:var(--fg2);display:flex;justify-content:space-between;gap:12px;padding:0 2px 20px}.chart svg{width:100%}.chart svg text{font-family:var(--sys);font-weight:500;fill:#09110c}.chart-legend{display:flex;justify-content:center;gap:22px;font-size:9px;color:var(--fg2);margin-top:20px}.chart-legend span{display:flex;align-items:center;gap:6px}.chart-legend i{height:2px;width:12px;background:var(--blue)}.chart-legend .target-key{background:var(--green)}.chart-legend .stop-key{background:var(--red)}.plan-content{border-left:1px solid var(--sep);padding:24px 26px;display:grid;align-content:start;gap:18px}.fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px 12px}.fields b{font-size:20px;font-weight:500;line-height:1.3;overflow-wrap:anywhere}.fields div:nth-child(n+4) b{font-size:15px}.order{padding:12px 15px;border:1px solid var(--sep);border-radius:3px;display:grid;gap:4px;background:#19241d}.order b{font-size:12px;font-weight:600}.order span{font-size:10px;color:var(--fg2)}.wf{font-size:12px;line-height:1.75;color:var(--orange);background:#f6bb5809;border-left:2px solid var(--orange);padding:12px 14px}.why h3{font:italic 18px var(--serif);margin:0 0 12px}.why p{font-size:12px;line-height:1.85;color:#b5c1b7;margin:0 0 8px}.why p:last-child{margin-bottom:0}.scenario{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding-top:16px;border-top:1px solid var(--sep)}.scenario span{font-size:8px}.scenario b{font-size:13px;font-weight:600}.evidence{border-top:1px solid var(--sep)}summary{cursor:pointer;list-style:none;padding:15px 30px;font:italic 16px var(--serif);display:flex;justify-content:space-between;gap:12px;align-items:center}summary::-webkit-details-marker{display:none}summary span{font:9px var(--sys);color:var(--fg2)}details[open] summary{border-bottom:1px solid var(--sep)}.news{padding:24px 30px;display:grid;gap:16px}.item{display:grid;grid-template-columns:5px minmax(0,1fr);gap:10px}.dot{height:5px;width:5px;border-radius:50%;background:var(--fg3);margin-top:8px}.dot.pos{background:var(--green)}.dot.neg{background:var(--red)}.item .t{font-size:12px;line-height:1.65}.item .s{font-size:11px;color:var(--fg2);line-height:1.7;margin-top:5px}.item .m{font-size:9px;color:var(--fg2);display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin-top:6px}.item a{border-bottom:1px solid var(--sep)}.tier,.flag{font-size:8px;padding:1px 4px;border-radius:2px;background:#253127;color:var(--fg2)}.tier.t1{color:var(--blue)}.empty{font-size:12px;color:var(--fg2)}.ver{padding:12px 30px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;border-top:1px solid var(--sep)}.ver span{font-size:10px;color:var(--fg2)}.dots{display:flex;gap:3px;flex-wrap:wrap}.dots i{width:12px;height:3px;background:var(--green);border-radius:2px}.dots i.bad{background:var(--red)}.gfail{padding:6px 30px;font-size:11px;color:var(--red)}.shot{padding:15px 30px 25px}.shot figure{margin:0}.shot img{display:block;width:100%;border-radius:3px}.shot figcaption{font-size:10px;color:var(--fg2);margin-top:8px}.costs{margin-top:12px;padding:28px 30px;border:0;border-block:1px solid var(--sep);background:#152019;border-radius:0;grid-template-columns:1fr 1fr;gap:20px 36px}.costs h3{grid-column:1/-1;color:var(--fg);font:25px var(--serif);letter-spacing:0;text-transform:none}.costs .sub{margin:0;font-size:11px;line-height:1.8}.costs .stats{border-left:1px solid var(--sep);padding-left:28px}.costs .stats b{font:24px var(--serif)}.steps .ver{padding:12px 0}.mem{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:9px;color:var(--fg2);border-top:1px solid var(--sep);padding-top:22px;overflow-wrap:anywhere}.mem code{font-size:9px}.foot{font-size:10px;color:var(--fg2);text-align:center;margin:0}.foot:last-child{font-size:9px;margin-top:-18px}
.masthead{border-bottom:2px solid var(--green)}.brand-mark{background:var(--green);color:#0a110b;border-radius:0;clip-path:polygon(0 0,100% 0,100% 78%,78% 100%,0 100%);font-style:normal;font-weight:700}.mast-note{font-family:var(--sys);font-style:normal;text-transform:uppercase;letter-spacing:.1em;font-size:9px}.hdr h1{font-weight:700;letter-spacing:-.055em}.hdr h1 em{font-style:italic}.edition{border-left:2px solid var(--green)}.nav a:hover{color:var(--green)}.sum{border:1px solid #527238;border-top:3px solid var(--green);border-radius:0}.row{border-radius:0}.big{font-family:var(--sys);font-weight:650;letter-spacing:-.06em}.decision-strip b{font-family:var(--sys);font-size:32px;font-weight:600}.decision-strip>div:first-child b{color:var(--green)}.decision-strip>div:nth-child(2) b{color:var(--orange)}.sect{font-family:var(--sys);font-size:25px;font-weight:650;letter-spacing:-.03em}.sect:after{background:linear-gradient(90deg,#638a3c,var(--sep))}.pass{border-radius:0;border-top:2px solid var(--green);box-shadow:0 14px 35px #0003}.pass.wait{border-top-color:var(--orange)}.pass.no{border-top-color:var(--red)}.tk{font-family:var(--sys);font-weight:650;font-size:32px;letter-spacing:-.04em}.badge{border-radius:0;border:1px solid #c2f85338;text-transform:uppercase;font-size:9px;letter-spacing:.04em}.badge.wt{border-color:#f6bb5838}.badge.no{border-color:#ff786a38}.fields b{font-weight:650}.order{border-radius:0;border-left:2px solid var(--green)}.wait .order{border-left-color:var(--orange)}.evidence summary:hover{background:#c2f85305}.costs{border-left:3px solid var(--orange)}.brand:focus-visible{outline-offset:8px}
@media(min-width:1400px){.page{padding-inline:48px}.hdr{padding-block:30px 22px}}
@media(max-width:900px){.page{padding-inline:28px;gap:24px}.hero{grid-template-columns:1.7fr 1fr}.sum{padding:24px}.row{padding:22px}.edition{width:220px;padding-left:24px}.plan-layout{grid-template-columns:1fr}.plan-content{border-left:0;border-top:1px solid var(--sep)}.visual{padding:24px 30px}.chart{max-width:620px;margin:auto}.costs{grid-template-columns:1fr}.costs .stats{border-left:0;padding:14px 0 0;border-top:1px solid var(--sep)}.nav-end{display:none}}
@media(max-width:600px){.page{padding:0 20px 28px;gap:22px}.masthead{padding:21px 0 17px}.brand{font-size:19px}.brand-mark{width:34px;height:38px;font-size:28px}.brand-sub{font-size:7px}.mast-note{font-size:11px}.hdr{display:block;padding:13px 0 0}.hdr h1{font-size:52px;margin-top:14px}.edition{border:0;border-top:1px solid var(--sep);width:auto;padding:16px 0 0;margin-top:24px;display:flex;align-items:center;flex-wrap:wrap;gap:8px 16px}.edition .eyebrow{font-size:8px}.edition b{font-size:25px;margin:0}.edition p{display:none}.edition small{width:100%;font-size:9px}.nav{gap:0;justify-content:space-between;font-size:10px;padding:14px 0}.nav a span{font-size:10px;margin-right:5px}.demo{font-size:9px;line-height:1.7;margin-top:-6px}.hero{grid-template-columns:minmax(0,1fr);gap:14px}.sum{padding:24px}.big{font-size:52px}.sum .stats b{font-size:18px}.sum .stats span{font-size:8px}.allocation-label{font-size:19px}.allocation-foot>div:last-child{font-size:8px}.row{display:grid;grid-template-columns:1fr auto;padding:19px 22px;gap:10px}.row .sym{font-size:29px;margin-top:5px}.row .eyebrow{font-size:8px}.row>svg{grid-column:1/-1;height:45px;margin:0}.px{display:grid;justify-items:end;gap:2px}.px b{font-size:23px}.decision-strip{gap:8px;padding:4px 0 20px;margin-top:0}.decision-strip>div{display:grid;gap:8px;align-content:start}.decision-strip b{font-size:29px}.decision-strip span{font-size:9px;line-height:1.4}.context-grid{grid-template-columns:minmax(0,1fr);gap:24px}.context-card h2,.intelligence h2{font-size:25px}.sect{font-size:28px;margin-top:8px}.top{padding:20px 20px 10px;align-items:start}.tk{font-size:29px}.co{font-size:9px;max-width:210px}.badge{font-size:9px;padding:5px 7px}.price{padding:0 20px 18px;gap:8px}.price small{width:100%;margin-left:0}.price b{font-size:23px}.visual{padding:20px 14px}.chart-heading{font-size:7px;letter-spacing:.06em;padding:0 6px 17px}.plan-content{padding:22px 20px;gap:18px}.fields b{font-size:20px}.fields span{font-size:10px}.why p{font-size:13px}.scenario{gap:8px}.scenario span{font-size:9px}.scenario b{font-size:12px}summary{padding:15px 20px;font-size:16px}summary span{font-size:8px}.news{padding:20px}.ver{padding:12px 20px}.shot{padding:12px 20px 20px}.card{padding:20px}.costs{padding:23px 20px}.costs .stats{gap:10px}.costs .stats b{font-size:22px}.costs .stats span{font-size:8px}.mem{font-size:8px}.foot{font-size:9px}}
@media(max-width:360px){.page{padding-inline:14px}.hdr h1{font-size:45px}.top{flex-wrap:wrap}.nav{font-size:9px}.sum{padding:21px}.fields{gap:17px 8px}.allocation-foot>div:last-child{flex-wrap:wrap;gap:3px}.edition small{font-size:8px}.scenario{grid-template-columns:1fr 1fr}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@page{size:A4;margin:12mm}
@media print{body{background:var(--bg)}.page{max-width:none;padding:0;gap:16px}.masthead{padding-top:0}.hdr{padding:10px 0}.hdr h1{font-size:44px}.edition{display:block;width:200px}.nav{display:none}.hero{grid-template-columns:1.7fr 1fr}.sum{padding:20px}.big{font-size:38px}.row .sym{font-size:30px}.context-grid{grid-template-columns:1fr 1fr}.plan-layout{grid-template-columns:1fr 1fr}.plan-content{padding:18px;border-top:0;border-left:1px solid var(--sep)}.visual{padding:20px 12px}.fields{gap:12px}.fields b{font-size:16px}.why p{font-size:10px}.card,.sum,.chart,.fields,.order,.item,.shot,.top,.ver,.scenario{break-inside:avoid}.sect,.top{break-after:avoid}.pass{box-shadow:none}.news{padding:15px 20px}details::details-content{content-visibility:visible!important;display:block!important}details>*{display:block}summary{display:none}.shot img{max-height:200px;object-fit:contain}.costs{grid-template-columns:1fr}.mem{font-size:8px}}

"""
