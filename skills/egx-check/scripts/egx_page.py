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
        out.append(f'<div class="chart">{chart}</div>')
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
        out.append('<div class="why">' + "".join(f'<p dir="auto">{esc(r)}</p>' for r in reasons[:5]) + "</div>")
    if row and row.get("shares"):
        out.append('<div class="scenario"><div><span>Net at target</span><b class="up n">+' + esc(money(row.get("gain_if_target"))) + ' EGP</b></div><div><span>Estimated stop loss</span><b class="dn n">−' + esc(money(row.get("loss_if_stop"))) + ' EGP</b></div><div><span>Net reward / risk</span><b class="n">' + esc(num(row.get("rr_net_sized"))) + '</b></div></div>')
    out.append("</div></div>")
    out.append('<details class="evidence"><summary>Sources &amp; verification <span>Inspect evidence</span></summary>')
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
    o.append(f'<header class="hdr"><span class="eyebrow n">For {esc(nice_date(meta.get("trading_day")))} · built {esc(nice_dt(meta.get("created")))}</span>'
             f'<div class="heading"><h1>{esc(cmd)}<span>Trading brief</span></h1><div class="edition">EGX / RESEARCH<br><b>Decision before execution</b></div></div><p class="intro">A plan for the session. Evidence, price levels and the risk you are taking.</p></header>' )
    o.append('<nav class="nav" aria-label="Report sections"><a href="#overview">Overview</a><a href="#ideas">Trade plans</a><a href="#costs">Risk &amp; costs</a></nav>')
    if meta.get("demo") or any(str(x.get("tk", "")).startswith("DEMO") for x in stocks):
        o.append('<aside class="demo">SYNTHETIC DEMO · Illustrative prices and evidence. Not a live market report.</aside>')
    if eg:
        sp = [x for x in (eg.get("spark") or []) if x is not None][-21:]
        # the chip and the line always describe the same 20 sessions
        ch = round((sp[-1] / sp[0] - 1) * 100, 2) if len(sp) >= 2 and sp[0] else eg.get("ch20")
        lab = "20d"
        o.append(f'<div class="row"><div><div class="sym">EGX30</div><div class="sub">{esc(eg.get("regime") or "unknown")}</div></div>'
                 f'{spark(sp)}<div class="px"><b class="n">{esc(money(eg.get("last")))}</b>'
                 f'<span class="chip {"dn" if (ch or 0) < 0 else "up"} n">{esc(signed(ch))} <small>{lab}</small></span></div></div>')
    # summary
    orders = [r for r in al.get("rows") or [] if r.get("shares")]
    deep = [s for s in stocks if s.get("verdict") in ("valid", "wait", "not_valid")]
    if al:
        o.append('<section class="sum" id="overview"><div class="k">Planned allocation · including entry fees</div>'
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
    counts = {v: sum(x.get("verdict") == v for x in stocks) for v in ("valid", "wait", "not_valid", "dropped")}
    o.append('<section class="decision-strip" id="ideas" aria-label="Decision overview">' + ''.join(f'<div><b class="n">{counts[v]}</b><span>{label}</span></div>' for v, label in [("valid", "Rules passed"), ("wait", "Watch & wait"), ("not_valid", "Not valid"), ("dropped", "Filtered out")]) + '</section>')
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
        o.append(f'<div class="sect">Your positions</div><div class="list">{"".join(lst)}</div>')
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
        o.append(f'<section class="card"><h3>Market news &amp; catalysts</h3>{"".join(items)}{news_items(macro)}</section>')
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
            f'<meta name="theme-color" content="#0b1118"><title>{esc(title)}</title>'
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
:root{color-scheme:dark;--bg:#0b1118;--card:#131d28;--card2:#1b2938;--sep:#2a3949;--grid:#263342;--fg:#edf3fa;--fg2:#a7b8ca;--fg3:#8195aa;--green:#61d4ac;--red:#ff8b91;--orange:#e8ba72;--blue:#86b8ff;--purple:#c2a6f8;--zonefill:#e8ba7218;--sys:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 var(--sys);-webkit-font-smoothing:antialiased;print-color-adjust:exact;-webkit-print-color-adjust:exact}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,summary:focus-visible{outline:2px solid var(--blue);outline-offset:5px}.page{grid-template-columns:minmax(0,1fr);max-width:1240px;margin:auto;padding:44px 40px 36px;display:grid;gap:24px}.page>*{min-width:0}.n{font-variant-numeric:tabular-nums}[dir=auto],[dir=rtl]{unicode-bidi:plaintext}svg{display:block;max-width:100%;height:auto}.eyebrow{font:11px/1.5 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--fg2)}.heading{display:flex;align-items:center;justify-content:space-between;gap:20px}.hdr h1{font-size:52px;line-height:1.08;letter-spacing:-.055em;margin:14px 0}.hdr h1 span{display:block;font-weight:400;color:var(--fg2);font-size:28px;letter-spacing:-.025em;margin-top:8px}.edition{text-align:right;font-size:10px;letter-spacing:.14em;color:var(--green);line-height:2}.edition b{font-weight:400;letter-spacing:0;color:var(--fg2)}.intro{color:var(--fg2);margin:5px 0 0;max-width:650px}.nav{display:flex;gap:28px;border-bottom:1px solid var(--sep);padding:0 0 16px;font-size:13px}.nav a{color:var(--fg2)}.nav a:first-child{color:var(--fg)}.demo{border:1px solid #e8ba7244;background:#e8ba7209;color:var(--orange);padding:10px 16px;font-size:12px;border-radius:8px}
.row{display:grid;grid-template-columns:1fr 150px auto;align-items:center;gap:24px;padding:16px 22px;border:1px solid var(--sep);border-radius:12px;background:var(--card)}.row svg{width:150px}.sym{font-weight:650;letter-spacing:.04em}.sub,.co{color:var(--fg2);font-size:12px}.px{display:flex;align-items:center;gap:20px}.px b{font-size:23px;font-weight:500}.chip{padding:5px 9px;border-radius:5px;font-size:12px;background:#61d4ac15}.chip.dn{background:#ff8b9115}.chip small{color:var(--fg2)}.sum{border:1px solid #38596b;border-radius:14px;padding:28px 32px;background:linear-gradient(110deg,#1b3140,#14202d);display:grid;grid-template-columns:1fr 1fr;column-gap:44px;row-gap:8px}.sum .k{font-size:12px;color:var(--fg2);grid-column:1/-1}.big{font-size:50px;letter-spacing:-.04em;line-height:1.2}.big small{font-size:16px;margin-left:10px;color:var(--fg2);letter-spacing:0}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;align-items:center}.stats div,.fields div,.scenario div{display:grid;gap:5px;min-width:0}.stats span,.fields span,.scenario span{font-size:10px;letter-spacing:.065em;text-transform:uppercase;color:var(--fg2)}.stats b{font-size:20px;font-weight:500}.sum .note,.sum .warn{grid-column:1/-1}.note{margin:12px 0 0;color:var(--fg2);line-height:1.8}.warn{font-size:12px;color:var(--orange);margin:8px 0 0}.decision-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding:6px 0 20px;border-bottom:1px solid var(--sep)}.decision-strip div{display:flex;align-items:baseline;gap:12px}.decision-strip b{font-size:26px;font-weight:500}.decision-strip span{font-size:12px;color:var(--fg2)}.sect{font-size:13px;text-transform:uppercase;letter-spacing:.13em;font-weight:600;margin:10px 0 -10px}.sect em{font-style:normal;font-size:11px;margin-left:8px;background:var(--card2);padding:3px 7px;border-radius:5px;color:var(--fg2)}.ideas-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;align-items:start}.pass{min-width:0;border:1px solid var(--sep);border-top:3px solid var(--green);border-radius:12px;background:var(--card);overflow:hidden}.pass.wait{border-top-color:var(--orange)}.pass.no{border-top-color:var(--red)}.top{padding:24px 24px 8px;display:flex;justify-content:space-between;gap:12px;align-items:start}.tk{font-size:26px;font-weight:650;letter-spacing:-.03em}.co{margin-top:3px;max-width:280px;overflow-wrap:anywhere}.badge{display:inline-flex;align-items:center;gap:6px;border:1px solid currentColor;border-radius:5px;font-size:10px;font-weight:600;padding:4px 7px;white-space:nowrap}.badge i{width:5px;height:5px;border-radius:50%;background:currentColor}.ok,.up{color:var(--green)}.wt{color:var(--orange)}.no,.dn{color:var(--red)}.price{padding:0 24px;display:flex;flex-wrap:wrap;align-items:baseline;gap:10px}.price b{font-size:25px;font-weight:500}.price span{font-size:12px}.chart{margin:18px 16px 0;padding:10px 0;background:#0e1721;border-radius:8px}.chart svg{width:100%}.chart svg text{font-family:var(--sys);fill:#0b1118}.fields{padding:20px 24px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;border-bottom:1px solid var(--sep)}.fields b{font-size:18px;font-weight:550;overflow-wrap:anywhere}.order{margin:18px 24px 0;padding:12px 14px;background:var(--card2);border-radius:6px;display:grid;gap:4px}.order b{font-size:14px;font-weight:550}.order span{font-size:11px;color:var(--fg2)}.wf{margin:16px 24px 0;padding:10px 12px;border-left:2px solid var(--orange);background:#e8ba7209;color:var(--orange);font-size:13px;line-height:1.7}.why{padding:16px 24px}.why p{margin:0 0 8px;font-size:14px;line-height:1.85;color:#d1dce8}.scenario{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:0 24px 20px}.scenario b{font-size:13px;font-weight:550}.evidence{border-top:1px solid var(--sep)}summary{cursor:pointer;padding:16px 24px;color:var(--fg2);font-size:12px}summary span{float:right;font-size:10px;color:var(--fg3)}.news{padding:6px 24px 20px;display:grid;gap:16px}.news h3,.card h3{margin:0;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--fg2);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.news h3 em{font-style:normal;text-transform:none;font-weight:400;letter-spacing:0}.item{display:grid;grid-template-columns:6px minmax(0,1fr);gap:10px}.dot{width:6px;height:6px;border-radius:50%;margin-top:8px;background:var(--fg3)}.dot.pos{background:var(--green)}.dot.neg{background:var(--red)}.item .t{font-size:13px;line-height:1.65}.item .s{font-size:12px;color:var(--fg2);margin-top:5px;line-height:1.7}.item .m{font-size:11px;color:var(--fg3);display:flex;gap:6px;flex-wrap:wrap;margin-top:5px}.tier,.flag{padding:1px 5px;background:var(--card2);border-radius:3px;font-size:10px;color:var(--fg2)}.tier.t1{color:var(--blue)}.empty{font-size:12px;color:var(--fg2)}.card,.list{border:1px solid var(--sep);border-radius:10px;background:var(--card)}.card{padding:22px 24px;display:grid;gap:18px}.li{padding:16px 22px;display:flex;justify-content:space-between;align-items:center;gap:18px}.li+.li{border-top:1px solid var(--sep)}.li .r{display:flex;align-items:center;gap:14px}.li b{font-size:13px}.ver{padding:12px 24px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-top:1px solid var(--sep)}.ver span{font-size:11px;color:var(--fg2)}.dots{display:flex;gap:3px;flex-wrap:wrap}.dots i{width:12px;height:3px;background:var(--green);border-radius:2px}.dots .bad{background:var(--red)}.gfail{font-size:12px;color:var(--red);padding:6px 24px}.shot{padding:14px 24px 20px}.shot figure{margin:0}.shot img{width:100%;border-radius:6px}.shot figcaption{font-size:10px;color:var(--fg3);margin-top:6px}.costs .sub{margin:0;max-width:850px;line-height:1.8}.mem{border-top:1px solid var(--sep);padding-top:20px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:11px;color:var(--fg3);overflow-wrap:anywhere}.mem code{font-size:10px}.foot{font-size:11px;text-align:center;color:var(--fg3);margin:0}.steps .ver{padding:12px 0}.bad{color:var(--red)}
.plan-layout{display:grid;grid-template-columns:minmax(0,1fr)}.plan-layout>*{min-width:0}@media screen and (min-width:801px){.ideas-grid:has(>.pass:only-child){grid-template-columns:minmax(0,1fr)}.pass:only-child .plan-layout{grid-template-columns:1fr 1fr;align-items:start}.pass:only-child .visual{padding:0 8px 20px}.pass:only-child .plan-content{border-left:1px solid var(--sep)}}
@media(max-width:800px){.page{padding:26px 20px;gap:20px}.hdr h1{font-size:42px}.edition{display:none}.sum{padding:22px;grid-template-columns:1fr}.sum .stats{margin-top:16px;border-top:1px solid var(--sep);padding-top:16px}.ideas-grid{grid-template-columns:1fr}.decision-strip{gap:10px}.decision-strip div{display:grid;gap:0}.decision-strip span{font-size:10px}.row{grid-template-columns:1fr 90px auto;gap:12px;padding:14px}.px{display:grid;gap:3px;text-align:right}.px b{font-size:18px}.big{font-size:44px}.intro{font-size:13px}.nav{gap:24px;font-size:12px}}
@media(max-width:380px){.page{padding:22px 12px}.top{flex-wrap:wrap}.stats{gap:10px}.stats b{font-size:16px}.scenario{grid-template-columns:1fr 1fr}.row{grid-template-columns:1fr auto}.row svg{display:none}.nav{gap:18px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@page{size:A4;margin:12mm}
@media print{.page{max-width:none;padding:0;gap:15px}.nav{display:none}.hdr h1{font-size:32px}.ideas-grid{display:block}.pass{margin-bottom:18px}.chart{max-width:440px;margin:12px auto}.card,.sum,.chart,.fields,.order,.item,.shot,.top,.ver,.scenario{break-inside:avoid}.sect{break-after:avoid}details::details-content{content-visibility:visible!important;display:block!important}details>*{display:block}summary{display:none}.why p{font-size:12px}.shot img{max-height:220px;object-fit:contain}.foot{font-size:10px}}
"""
