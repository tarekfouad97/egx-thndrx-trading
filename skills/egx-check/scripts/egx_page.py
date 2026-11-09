"""
egx_page.py - the EGX report page (v3 design: dark, Apple Stocks / Wallet look, TradingView-style charts).

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

DROP_WORDS = {"rr": "R:R below 2", "thin": "Too thin (< 5M EGP/day)", "wide": "Stop over 3 ATR", "noise": "Stop under 1 ATR",
              "invalid": "Resistance right above", "limit": "Near the daily limit", "new": "New listing",
              "no-plan": "No support / no plan", "unknown": "Chart unreadable", "early": "Opening range not complete",
              "no-setup": "No intraday setup", "spread": "Spread over 0.3%"}
VERDICT = {"valid": ("ok", "Valid"), "wait": ("wt", "Wait"), "not_valid": ("no", "Not valid")}
ACTION = {"hold": ("ok", "Hold"), "add": ("ok", "Add"), "tighten": ("wt", "Tighten stop"), "sell": ("no", "Sell"), "exit": ("no", "Exit")}
CATS = [("top30", "Top 30"), ("hot", "Hot"), ("t0", "Same day")]


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


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
    for i, (_, op, h, l, c) in enumerate(bars):
        cx = 4 + i * cw + cw / 2
        col = "var(--green)" if c >= op else "var(--red)"
        o.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(h):.1f}" y2="{y(l):.1f}" stroke="{col}" stroke-width="1"/>')
        o.append(f'<rect x="{cx - cw * .32:.1f}" width="{cw * .64:.1f}" y="{y(max(op, c)):.1f}" height="{max(1, abs(y(op) - y(c))):.1f}" fill="{col}" rx=".6"/>')
    for p, colr, tag, dashed in levels:
        if not p:
            continue
        ly = y(p)
        o.append(f'<line x1="0" x2="{W - R}" y1="{ly:.1f}" y2="{ly:.1f}" stroke="{colr}" stroke-width="1.2"{" stroke-dasharray=&quot;4 3&quot;" if dashed else ""}/>')
        o.append(f'<rect x="{W - R + 4}" y="{ly - 9:.1f}" width="{R - 6}" height="18" rx="4" fill="{colr}"/>')
        o.append(f'<text x="{W - R + 4 + (R - 6) / 2:.1f}" y="{ly + 4.2:.1f}" text-anchor="middle" fill="#fff" font-size="11" font-weight="600">{esc(tag)} {p:.2f}</text>')
    o.append("</svg>")
    return "".join(o).replace("&quot;", '"')


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
        link = f'<a href="{esc(n.get("url"))}" target="_blank" rel="noopener">{esc(n.get("source") or "source")}</a>'
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
        f'<div class="m">{tier_tag(e)}<a href="{esc(e.get("url"))}" target="_blank" rel="noopener">{esc(e.get("source") or "source")}</a></div></div></div>'
        for e in reds)
    body = news_items(items, None if reds else "No dated news in the last 14 days. The verdict is technical only.")
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


def pass_card(s, row, cat_label, rank):
    t0 = s.get("mode") == "t0"
    p = ((s.get("t0") or {}).get("plan") if t0 else s.get("plan")) or {}
    v = s.get("verdict") or "wait"
    cls, word = VERDICT.get(v, ("wt", v))
    order_word = ""
    if row and row.get("shares"):
        order_word = " · Buy now" if row.get("order") == "buy now" else " · Limit"
    tint = {"ok": "pass", "wt": "pass wait", "no": "pass no"}[cls]
    sub = " · ".join(x for x in [s.get("title"), s.get("sector"), f"#{rank} in {cat_label}" if rank else cat_label] if x)
    chg = s.get("chg")
    out = [f'<article class="{tint}" id="stock-{esc(s.get("tk"))}">',
           f'<div class="top"><div><div class="tk">{esc(s.get("tk"))}</div><div class="co">{esc(sub)}</div></div>'
           f'<span class="badge {cls}"><i></i>{esc(word + order_word)}</span></div>',
           f'<div class="price"><b class="n">{esc(num(s.get("last")))}</b>'
           f'<span class="n {"up" if (chg or 0) >= 0 else "dn"}">{esc(signed(chg))}</span></div>']
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
    if v == "wait" and s.get("wait_for"):
        out.append(f'<div class="wf">Waiting for: {esc(s["wait_for"])}</div>')
    rr = p.get("rr")
    fields = [("Entry", num(p.get("entry")), "var(--blue)"), ("Stop", num(p.get("stop")), "var(--red)"), ("Target", num(p.get("target")), "var(--green)")]
    if row and row.get("shares"):
        fields += [("Shares", f'{row["shares"]:,}', None), ("Value", money(row.get("value")), None), ("R:R", rr, None)]
    else:
        fields += [("R:R", rr, None), ("Stop ATR", p.get("stopATR") or p.get("stopATR5"), None), ("Setup", (p.get("type") or p.get("setup") or "—").replace("-", " "), None)]
    out.append('<div class="fields">' + "".join(
        f'<div><span>{esc(a)}</span><b class="n"{f" style=&quot;color:{c}&quot;" if c else ""}>{esc(b)}</b></div>' for a, b, c in fields).replace("&quot;", '"') + "</div>")
    if row and row.get("shares"):
        when = "Limit · stop & target from T+2" if not t0 else "Limit today · exit by 14:20 (T0)"
        out.append(f'<div class="order"><b class="n">Buy {row["shares"]:,} @ {esc(num(row.get("entry")))}</b><span>{esc(when)}</span></div>')
    elif row and row.get("note"):
        out.append(f'<div class="order"><b>Not funded</b><span>{esc(row["note"])}</span></div>')
    reasons = s.get("reasons") or []
    if reasons:
        out.append('<div class="why">' + "".join(f'<p dir="auto">{esc(r)}</p>' for r in reasons[:5]) + "</div>")
    out.append(news_block(s, None))
    out.append(gates_bar(s))
    shot = s.get("_shot_uri")
    if shot:
        when = s.get("_shot_time") or ""
        out.append(f'<div class="shot"><figure><img src="{shot}" alt="{esc(s.get("tk"))} on ThndrX with the drawn levels" loading="lazy">'
                   f'<figcaption>ThndrX chart · drawn and verified {esc(when)}</figcaption></figure></div>')
    out.append("</article>")
    return "".join(out)


# ----------------------------------------------------------------- page
def build_html(run: dict, cfg: dict, fname: str, version: str, memory_counts: dict | None = None) -> str:
    meta, mk, al = run.get("meta") or {}, run.get("market") or {}, run.get("allocation") or {}
    eg = mk.get("egx30") or {}
    stocks = run.get("stocks") or []
    rows = {r["tk"]: r for r in al.get("rows") or []}
    cmd = meta.get("command") or "EGX"
    o = []
    o.append(f'<header class="hdr"><span class="eyebrow n">For {esc(nice_date(meta.get("trading_day")))} · built {esc(nice_dt(meta.get("created")))}</span>'
             f'<h1>{esc(cmd)}</h1></header>')
    if eg:
        ch = eg.get("chgToday") if eg.get("chgToday") is not None else eg.get("ch20")
        lab = "today" if eg.get("chgToday") is not None else "20d"
        o.append(f'<div class="row"><div><div class="sym">EGX30</div><div class="sub">{esc(eg.get("regime") or "unknown")}</div></div>'
                 f'{spark((eg.get("spark") or [])[-21:] if lab == "20d" else eg.get("spark"))}<div class="px"><b class="n">{esc(money(eg.get("last")))}</b>'
                 f'<span class="chip {"dn" if (ch or 0) < 0 else "up"} n">{esc(signed(ch))} <small>{lab}</small></span></div></div>')
    # summary
    orders = [r for r in al.get("rows") or [] if r.get("shares")]
    deep = [s for s in stocks if s.get("verdict") in ("valid", "wait", "not_valid")]
    if al:
        o.append('<section class="sum"><div class="k">Deploying</div>'
                 f'<div class="big n">{esc(money(al.get("deployed")))}<small>EGP</small></div>'
                 '<div class="stats">'
                 f'<div><span>Orders</span><b class="n">{len(orders)}</b></div>'
                 f'<div><span>Cash kept</span><b class="n">{esc(money(al.get("cash_left")))}</b></div>'
                 f'<div><span>Total risk</span><b class="n">{esc(money(al.get("total_risk")))}</b></div></div>'
                 + (f'<p class="note" dir="auto">{esc(meta.get("summary"))}</p>' if meta.get("summary") else "")
                 + "".join(f'<p class="warn" dir="auto">{esc(w)}</p>' for w in al.get("warnings") or [])
                 + "</section>")
    elif meta.get("summary"):
        o.append(f'<section class="sum"><p class="note" dir="auto">{esc(meta.get("summary"))}</p></section>')
    # positions
    hs = [h for h in run.get("holdings") or [] if not h.get("is_fund")]
    if hs:
        lst = []
        for h in hs:
            cls, word = ACTION.get(h.get("action") or "hold", ("ok", "Hold"))
            pl = h.get("pnlPct")
            lst.append(f'<div class="li"><div><b>{esc(h.get("tk"))}</b><div class="sub" dir="auto">{esc((h.get("reasons") or [""])[0])}</div></div>'
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
                         f'<div class="m">{tier_tag(src)}<a href="{esc(src.get("url"))}" target="_blank" rel="noopener">{esc(src.get("source") or "source")}</a>'
                         f'<span class="n">· {esc(nice_date(c.get("date") or src.get("date")))}</span>{flag}{rumour}</div></div></div>')
        o.append(f'<section class="card"><h3>Market news &amp; catalysts</h3>{"".join(items)}{news_items(macro)}</section>')
    # categories
    has_cat = any(s.get("category") for s in stocks)
    groups = [(k, lab, [s for s in deep if s.get("category") == k]) for k, lab in CATS] if has_cat else [(None, "Checked", deep)]
    for key, lab, items in groups:
        if key == "t0" and not items and meta.get("t0_status"):
            o.append(f'<div class="sect">{esc(lab)}</div><div class="list"><div class="li"><span class="sub">{esc(meta["t0_status"])}</span></div></div>')
            continue
        if not items:
            continue
        o.append(f'<div class="sect">{esc(lab)} <em class="n">{len(items)}</em></div>')
        items = sorted(items, key=lambda s: (s.get("rank") or 99))
        for i, s in enumerate(items, 1):
            o.append(pass_card(s, rows.get(s.get("tk")), lab if key else cmd, s.get("rank") or (i if key else None)))
    # dropped
    drops = {}
    for s in stocks:
        if s.get("verdict") == "dropped":
            why = DROP_WORDS.get(s.get("drop"), (s.get("auto_reasons") or [s.get("drop") or "dropped"])[0])
            drops.setdefault(why, []).append(s.get("tk"))
    if drops:
        o.append('<div class="sect">Dropped</div><div class="list">' + "".join(
            f'<div class="li"><b>{esc(" · ".join(v))}</b><span class="sub">{esc(k)}</span></div>' for k, v in drops.items()) + "</div>")
    # costs
    if al:
        o.append('<section class="card costs"><h3>Costs</h3><div class="stats">'
                 f'<div><span>Fixed / month</span><b class="n">{esc(money(al.get("fixed_monthly")))}</b></div>'
                 f'<div><span>Break-even / month</span><b class="n">{esc(al.get("break_even_monthly_pct"))}%</b></div>'
                 f'<div><span>Risk / trade</span><b class="n">{esc(money(al.get("risk_budget_per_trade")))}</b></div></div></section>')
    mc = memory_counts or {}
    o.append(f'<div class="mem"><span>Saved to history: {mc.get("stocks", 0)} stocks · {mc.get("news", 0)} news</span><code>{esc(fname.rsplit(".", 1)[0])}</code></div>')
    foot = cfg.get("footer") or {}
    o.append(f'<p class="foot" dir="rtl">تحليل تعليمي مش نصيحة استثمارية؛ القرار والأوامر ليك.</p>'
             f'<p class="foot">egx-thndrx-trading v{esc(version)} · {esc(foot.get("author", ""))}</p>')
    title = f"{cmd} · {(meta.get('created') or '')[:16].replace('T', ' ')}"
    return (f'<!doctype html><html lang="en" dir="ltr"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="color-scheme" content="dark">'
            f'<meta name="theme-color" content="#000000"><title>{esc(title)}</title>'
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
:root{color-scheme:dark;--bg:#000;--card:#1c1c1e;--card2:#2c2c2e;--sep:rgba(84,84,88,.55);--grid:rgba(84,84,88,.35);
--fg:#fff;--fg2:rgba(235,235,245,.62);--fg3:rgba(235,235,245,.32);--green:#30d158;--red:#ff453a;--orange:#ff9f0a;--blue:#0a84ff;--purple:#bf5af2;--zonefill:rgba(255,159,10,.16);
--sys:-apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Segoe UI",Roboto,"Noto Sans Arabic","Geeza Pro",Tahoma,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg)}
body{font-family:var(--sys);-webkit-font-smoothing:antialiased;font-size:15px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
a{color:inherit;text-decoration:none;border-bottom:.5px solid var(--fg3)}
.page{max-width:520px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-right,0px)) 48px max(16px,env(safe-area-inset-left,0px));display:grid;gap:20px}
.n{font-variant-numeric:tabular-nums}[dir=auto],[dir=rtl]{unicode-bidi:plaintext}
svg{display:block;max-width:100%;height:auto}
.hdr{display:grid;gap:2px}.hdr .eyebrow{font-size:13px;color:var(--fg2);font-weight:500}.hdr h1{margin:0;font-size:34px;line-height:1.1;font-weight:700;letter-spacing:-.02em}
.row{display:grid;grid-template-columns:1fr 96px auto;gap:14px;align-items:center;padding:12px 0;border-block:.5px solid var(--sep)}
.row .sym{font-weight:600;font-size:17px}.sub{font-size:13px;color:var(--fg2)}
.row .px{text-align:right;display:grid;gap:4px;justify-items:end}.row .px b{font-weight:500;font-size:17px}
.chip{display:inline-block;min-width:74px;text-align:right;padding:3px 7px;border-radius:6px;font-weight:600;font-size:14px;color:#fff}
.chip small{font-weight:500;opacity:.8;font-size:11px}.chip.dn,.chip.up{color:#fff}.chip.dn{background:var(--red)}.chip.up{background:var(--green)}
.sum,.card{background:var(--card);border-radius:16px;padding:18px;display:grid;gap:14px}
.sum .k{font-size:13px;color:var(--fg2);font-weight:500}
.sum .big{font-size:40px;font-weight:700;letter-spacing:-.02em;line-height:1}.sum .big small{font-size:17px;color:var(--fg2);font-weight:500;margin-left:4px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);border-top:.5px solid var(--sep);padding-top:12px}.card .stats{border:0;padding:0}
.stats div,.fields div{display:grid;gap:3px;min-width:0}
.stats span,.fields span{font-size:11px;color:var(--fg2);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.stats b{font-size:17px;font-weight:600}
.note{font-size:15px;line-height:1.7;color:var(--fg2);margin:0}.warn{margin:0;font-size:14px;color:var(--orange)}
.sect{font-size:13px;color:var(--fg2);font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin:6px 2px -8px}.sect em{font-style:normal;color:var(--fg3);margin-left:4px}
.list{background:var(--card);border-radius:14px;overflow:hidden}
.li{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 16px;font-size:15px}.li+.li{border-top:.5px solid var(--sep)}
.li .r{display:grid;justify-items:end;gap:4px}
.pass{background:linear-gradient(180deg,#1f2a22 0%,var(--card) 220px);border-radius:20px;overflow:hidden;display:grid}
.pass.wait{background:linear-gradient(180deg,#2c2416 0%,var(--card) 220px)}.pass.no{background:linear-gradient(180deg,#2c1818 0%,var(--card) 220px)}
.pass .top{padding:16px 18px 6px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.pass .tk{font-size:28px;font-weight:700;letter-spacing:-.02em;line-height:1}.pass .co{font-size:13px;color:var(--fg2);margin-top:4px}
.badge{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap}
.badge i{width:7px;height:7px;border-radius:50%;background:currentColor}
.badge.ok{background:rgba(48,209,88,.16);color:var(--green)}.badge.wt{background:rgba(255,159,10,.16);color:var(--orange)}.badge.no{background:rgba(255,69,58,.16);color:var(--red)}
.pass .price{padding:0 18px;display:flex;align-items:baseline;gap:10px}.pass .price b{font-size:22px;font-weight:600}.pass .price span{font-size:15px;font-weight:600}
.up{color:var(--green)}.dn{color:var(--red)}
.chart{padding:10px 0 4px}.chart svg text{font-family:var(--sys)}
.wf{padding:4px 18px 14px;font-size:15px;color:var(--orange);line-height:1.5}
.fields{display:grid;grid-template-columns:repeat(3,1fr);gap:14px 8px;padding:14px 18px 16px;border-top:.5px solid var(--sep)}
.fields b{font-size:19px;font-weight:600;overflow-wrap:anywhere}
.order{margin:0 18px 16px;background:var(--card2);border-radius:12px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.order b{font-size:15px;font-weight:600}.order span{font-size:13px;color:var(--fg2)}
.why,.news{padding:14px 18px;border-top:.5px solid var(--sep);display:grid;gap:10px}
.why p{margin:0;font-size:15px;line-height:1.75;color:rgba(235,235,245,.85)}
.news h3,.card h3{margin:0;font-size:11px;color:var(--fg2);text-transform:uppercase;letter-spacing:.06em;font-weight:600;display:flex;justify-content:space-between;gap:8px}
.news h3 em{font-style:normal;text-transform:none;letter-spacing:0;font-weight:500;color:var(--fg3)}
.item{display:grid;grid-template-columns:8px 1fr;gap:10px;align-items:start}.item .dot{width:8px;height:8px;border-radius:50%;margin-top:7px}
.dot.pos{background:var(--green)}.dot.neg{background:var(--red)}.dot.neu{background:var(--fg3)}
.item .t{font-size:15px;line-height:1.45}.item .s{font-size:13px;color:var(--fg2);margin-top:3px;line-height:1.5}
.item .m{font-size:12px;color:var(--fg2);margin-top:3px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.tier{font-size:10px;font-weight:700;letter-spacing:.04em;padding:1px 5px;border-radius:4px;background:var(--card2);color:var(--fg2)}.tier.t1{background:rgba(10,132,255,.2);color:#64a8ff}
.flag{font-size:12px;padding:2px 7px;border-radius:5px;background:rgba(48,209,88,.14);color:var(--green);font-weight:600}.flag.muted{background:var(--card2);color:var(--fg2)}.flag.no{background:rgba(255,69,58,.16);color:var(--red)}
.empty{font-size:14px;color:var(--fg2)}
.ver{padding:12px 18px;border-top:.5px solid var(--sep);display:flex;justify-content:space-between;align-items:center;gap:10px}
.ver .dots{display:flex;gap:4px}.ver .dots i{width:16px;height:4px;border-radius:2px;background:var(--green)}.ver .dots i.bad{background:var(--red)}
.ver span{font-size:13px;color:var(--fg2)}.gfail{padding:0 18px 8px;font-size:13px;color:var(--red)}
.shot{padding:0 18px 18px}.shot figure{margin:0;border-radius:12px;overflow:hidden;border:.5px solid var(--sep)}.shot img{display:block;width:100%}
.shot figcaption{font-size:12px;color:var(--fg3);padding:8px 2px 0}
.mem{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--fg3);border-top:.5px solid var(--sep);padding-top:14px}
.mem code{font-family:ui-monospace,"SF Mono",Menlo,monospace;color:var(--fg2)}
.foot{font-size:12px;color:var(--fg3);text-align:center;line-height:1.6;margin:0}
@page{size:150mm 330mm;margin:0}
@media print{.page{padding-top:14px}.card,.sum,.list,.chart,.fields,.order,.item,.shot,.top,.ver{break-inside:avoid}}
"""
