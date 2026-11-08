#!/usr/bin/env python3
"""
egx.py - helper CLI for the EGX ThndrX trading skills (Python 3.9+, standard library only).

Claude does the browsing; this script does the arithmetic and the paperwork, so it costs
no tokens to "think" about them:

  python3 egx.py fees 5000                      # Thndr fees for one order value (per side, round trip)
  python3 egx.py allocate run.json              # position sizing, caps, fees, costs -> writes run.json
  python3 egx.py report run.json [--video]      # HTML report + index.csv (+ HyperFrames recap project)
  python3 egx.py search --ticker HRHO           # find past reports from index.csv (no file opening)
  python3 egx.py read REPORT.html [--ticker X]  # print the JSON data embedded in a report
  python3 egx.py history HRHO                   # every past verdict/plan for one ticker
  python3 egx.py check run.json                 # validate a run file before building
  python3 egx.py config                         # show the merged configuration

Settings come from config.json next to SKILL.md (copy config.example.json). The run file
format is documented in references/run-schema.md.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import html
import json
import math
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
VERSION = "2.0.2"

DEFAULT_CONFIG = {
    "user_name": "",
    "language": "ar",
    "timezone": "Africa/Cairo",
    "reports_dir": "~/EGX-Reports",
    "reports_repo": "",
    "trade_log_sheet_id": "",
    "risk_pct": 1.0,
    "max_stock_pct": 30.0,
    "max_sector_pct": 50.0,
    "min_order_egp": 2500,
    "half_deploy_in_weak_market": True,
    "fees": {
        "per_order_egp": 2.0,
        "brokerage_custody_pct": 0.100,
        "egx_pct": 0.010,
        "mcdr_pct": 0.010,
        "risk_fund_pct": 0.005,
        "stamp_pct": 0.050,
        "fra_pct": 0.003,
        "fra_min_egp": 1.0,
        "fra_max_egp": 250.0,
    },
    "fixed_costs": {"thndr_plan_egp": 245.0, "claude_usd": 20.0},
    "footer": {
        "author": "Tarek Fouad",
        "email": "tare2fo2ad@gmail.com",
        "repo": "https://github.com/tarekfouad97/egx-thndrx-trading",
    },
}

INDEX_COLUMNS = [
    "file", "created", "trading_day", "command", "regime", "egx30", "amount", "deployed",
    "cash_left", "tickers", "valid", "wait", "not_valid", "holdings", "holding_actions",
    "top_pick", "catalysts", "summary",
]


# ----------------------------------------------------------------- config / io
def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config() -> dict:
    cfg = DEFAULT_CONFIG
    for p in (SKILL_DIR / "config.json", pathlib.Path.home() / ".egx-thndrx" / "config.json"):
        if p.exists():
            cfg = deep_merge(cfg, json.loads(p.read_text(encoding="utf-8")))
    return cfg


def reports_dir(cfg: dict, override: str | None = None) -> pathlib.Path:
    d = pathlib.Path(os.path.expanduser(override or os.environ.get("EGX_REPORTS_DIR") or cfg["reports_dir"]))
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_local(cfg: dict) -> _dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo(cfg.get("timezone") or "Africa/Cairo"))
    except Exception:
        return _dt.datetime.now()


def read_json(p) -> dict:
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def write_json(p, data) -> None:
    pathlib.Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def f(x, d=2):
    """format a number with thousands separators; None -> '—'"""
    if x is None or x == "":
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    s = f"{x:,.{0 if abs(x) >= 100000 else d}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


# ----------------------------------------------------------------- fees / sizing
def fees_side(value: float, cfg: dict) -> float:
    fz = cfg["fees"]
    pct = fz["brokerage_custody_pct"] + fz["egx_pct"] + fz["mcdr_pct"] + fz["risk_fund_pct"] + fz["stamp_pct"]
    fra = min(max(value * fz["fra_pct"] / 100, fz["fra_min_egp"]), fz["fra_max_egp"])
    return round(fz["per_order_egp"] + fra + value * pct / 100, 2)


def fixed_monthly(cfg: dict, usd_egp: float | None) -> float:
    fc = cfg["fixed_costs"]
    return round(fc["thndr_plan_egp"] + fc["claude_usd"] * (usd_egp or 54.0), 0)


def allocate(run: dict, cfg: dict) -> dict:
    meta = run.setdefault("meta", {})
    risk_pct = float(meta.get("risk_pct") or cfg["risk_pct"])
    equity = float(meta.get("equity") or 0)
    amount = float(meta.get("amount") or 0)
    regime = ((run.get("market") or {}).get("egx30") or {}).get("regime") or meta.get("regime") or "unknown"
    weak = regime in ("Down", "Correction")
    half = meta.get("half_deploy")
    if half is None:
        half = bool(cfg.get("half_deploy_in_weak_market")) and weak
    cap_total = amount * (0.5 if half else 1.0)
    risk_budget = equity * risk_pct / 100 if equity else amount * risk_pct / 100
    max_stock = equity * cfg["max_stock_pct"] / 100 if equity else amount
    max_sector = equity * cfg["max_sector_pct"] / 100 if equity else amount

    held_value, sector_value = {}, {}
    for h in run.get("holdings") or []:
        v = float(h.get("value") or 0)
        held_value[h.get("tk")] = held_value.get(h.get("tk"), 0) + v
        sec = h.get("sector") or "unknown"
        if not h.get("is_fund"):
            sector_value[sec] = sector_value.get(sec, 0) + v

    picks = []
    for s in run.get("stocks") or []:
        p = s.get("plan") or {}
        if not p.get("entry") or not p.get("stop") or p["entry"] <= p["stop"]:
            continue
        if (p.get("rr") or 0) < 2:
            continue  # never size a plan under 2:1, whatever the verdict says
        if s.get("verdict") == "valid" or (s.get("verdict") == "wait" and meta.get("include_wait_orders")):
            picks.append(s)
    picks.sort(key=lambda s: (s.get("verdict") != "valid", -(s.get("score") or {}).get("total", 0), -((s.get("plan") or {}).get("rr") or 0)))
    for h in run.get("holdings") or []:  # "add" actions compete for the same money
        if h.get("action") == "add" and (h.get("plan") or {}).get("entry"):
            picks.append({"tk": h["tk"], "sector": h.get("sector"), "verdict": "add", "plan": h["plan"], "score": h.get("score") or {}})

    rows, remaining = [], cap_total
    for i, s in enumerate(picks):
        p, tk = s["plan"], s["tk"]
        entry, stop, target = float(p["entry"]), float(p["stop"]), p.get("target")
        share_budget = remaining / max(1, len(picks) - i) if amount else float("inf")  # Check / Positions: size by risk and caps only
        by_risk = math.floor(risk_budget / (entry - stop))
        by_money = math.floor(share_budget / (entry * 1.002)) if share_budget != float("inf") else 10**9
        by_stock = math.floor(max(0.0, max_stock - held_value.get(tk, 0)) / entry)
        sec = s.get("sector") or "unknown"
        by_sector = math.floor(max(0.0, max_sector - sector_value.get(sec, 0)) / entry)
        shares = max(0, min(by_risk, by_money, by_stock, by_sector))
        limit = min((("risk", by_risk), ("money", by_money), ("stock cap", by_stock), ("sector cap", by_sector)), key=lambda x: x[1])[0]
        value = round(shares * entry, 2)
        note = ""
        if shares and value < cfg["min_order_egp"]:
            note, shares, value = f"below minimum order {cfg['min_order_egp']:,} EGP", 0, 0.0
        buy_fee = fees_side(value, cfg) if shares else 0.0
        row = {"tk": tk, "verdict": s.get("verdict"), "order": "buy now" if s.get("verdict") in ("valid", "add") and (p.get("type") or "").endswith("at-support") else "limit",
               "shares": shares, "value": value, "entry": entry, "stop": stop, "target": target, "rr": p.get("rr"),
               "risk": round(shares * (entry - stop), 2), "limited_by": limit, "note": note, "sector": sec,
               "fees_buy": buy_fee}
        if shares:
            sell_t = shares * float(target) if target else 0
            sell_s = shares * stop
            row["gain_if_target"] = round(sell_t - value - buy_fee - fees_side(sell_t, cfg), 2) if target else None
            row["loss_if_stop"] = round(value - sell_s + buy_fee + fees_side(sell_s, cfg), 2)
            remaining -= value + buy_fee
            held_value[tk] = held_value.get(tk, 0) + value
            sector_value[sec] = sector_value.get(sec, 0) + value
        rows.append(row)

    deployed = round(sum(r["value"] + r["fees_buy"] for r in rows), 2)
    usd = (run.get("market") or {}).get("usd_egp") or meta.get("usd_egp")
    fixed = fixed_monthly(cfg, usd)
    cash = meta.get("cash")
    warnings = []
    if cash is not None and deployed > float(cash):
        warnings.append(f"cash in ThndrX is {f(cash)} EGP but the plan needs {f(deployed)} EGP: deposit or redeem funds first")
    run["allocation"] = {
        "regime": regime, "half_deploy": half, "deploy_cap": round(cap_total, 2), "risk_pct": risk_pct,
        "risk_budget_per_trade": round(risk_budget, 2), "rows": rows, "deployed": deployed,
        "cash_left": round(amount - deployed, 2) if amount else None,
        "total_risk": round(sum(r["risk"] for r in rows), 2),
        "gain_if_all_targets": round(sum(r.get("gain_if_target") or 0 for r in rows), 2),
        "loss_if_all_stops": round(sum(r.get("loss_if_stop") or 0 for r in rows), 2),
        "fixed_monthly": fixed,
        "break_even_monthly_pct": round(fixed / (amount or deployed) * 100, 2) if (amount or deployed) else None,
        "capital_for_1pct_month": round(fixed * 100, 0),
        "warnings": warnings,
    }
    return run


# ----------------------------------------------------------------- validation
def check(run: dict) -> list[str]:
    errs = []
    m = run.get("meta") or {}
    for k in ("command", "amount"):
        if m.get(k) in (None, ""):
            errs.append(f"meta.{k} missing")
    if not (run.get("market") or {}).get("egx30"):
        errs.append("market.egx30 missing (run EGX.market())")
    for s in run.get("stocks") or []:
        tk = s.get("tk", "?")
        if s.get("verdict") not in ("valid", "wait", "not_valid", "dropped", None):
            errs.append(f"{tk}: verdict must be valid / wait / not_valid / dropped")
        if s.get("verdict") == "valid" and (s.get("drop") or ((s.get("plan") or {}).get("rr") or 0) < 2):
            errs.append(f"{tk}: verdict valid but the chart script dropped it ({s.get('drop')}) or R:R < 2")
        if s.get("verdict") in ("valid", "wait", "not_valid") and s.get("full", True):
            if not s.get("news") and not s.get("news_checked"):
                errs.append(f"{tk}: deep-checked stock without news (add news[] or news_checked:true with 'no fresh news')")
            if not s.get("screenshot") and not s.get("drawn"):
                errs.append(f"{tk}: deep-checked stock without drawings/screenshot")
        for n in s.get("news") or []:
            if not n.get("url") or not n.get("date"):
                errs.append(f"{tk}: news item without url or date: {n.get('title', '')[:40]}")
    for c in run.get("catalysts") or []:
        if not c.get("url") or not c.get("date"):
            errs.append(f"catalyst {c.get('tk')}: url and date are required")
    return errs


# ----------------------------------------------------------------- labels
L = {
    "ar": {
        "dir": "rtl", "lang": "ar", "title": "تقرير EGX", "market": "السوق", "regime": "حالة السوق",
        "Up": "صاعد", "Down": "هابط", "Correction": "تصحيح", "unknown": "غير معروف",
        "valid": "✅ صالح", "wait": "⏳ انتظر", "not_valid": "❌ مش صالح", "dropped": "مستبعد", "add": "➕ زيادة",
        "amount": "المبلغ", "cash": "الكاش المتاح", "deployed": "هيتشغل", "cash_left": "يفضل كاش",
        "risk": "المخاطرة", "gain": "لو الأهداف اتحققت", "loss": "لو الوقفات اتضربت", "hurdle": "لازم تكسب شهرياً عشان تغطي التكاليف",
        "allocation": "التوزيع", "ticker": "السهم", "verdict": "القرار", "shares": "العدد", "value": "القيمة",
        "entry": "دخول", "stop": "وقف", "target": "هدف", "rr": "عائد/مخاطرة", "score": "الدرجة",
        "holdings": "مراكزك الحالية", "action": "الإجراء", "hold": "احتفظ", "sell": "بيع", "tighten": "قرّب الوقف", "exit": "خروج",
        "picks": "الأسهم المختارة", "chart_ev": "أدلة التحليل الفني", "news_ev": "الأخبار والمصادر", "book": "دفتر الأوامر",
        "fin": "البيانات المالية", "votes": "أصوات المحللين", "catalysts": "الأخبار المحركة", "scan": "كل الأسهم اللي اتفحصت",
        "drops": "اتشال ليه", "costs": "التكاليف", "disclaimer": "ده تحليل تعليمي مش نصيحة استثمارية، والقرار والأوامر كلها في إيدك.",
        "made": "اتعمل بحب بواسطة", "wait_for": "مستني إيه", "reasons": "الأسباب", "red": "أحداث مهمة", "history": "تاريخ النموذج",
        "recap": "ملخص متحرك", "replay": "إعادة", "no_news": "مفيش أخبار جديدة، القرار فني بس", "macro": "أجندة الأسبوع",
        "warnings": "تنبيهات", "limited": "محدود بـ",
    },
    "en": {
        "dir": "ltr", "lang": "en", "title": "EGX report", "market": "Market", "regime": "Regime",
        "Up": "Up", "Down": "Down", "Correction": "Correction", "unknown": "unknown",
        "valid": "✅ Valid", "wait": "⏳ Wait", "not_valid": "❌ Not valid", "dropped": "Dropped", "add": "➕ Add",
        "amount": "Amount", "cash": "Cash available", "deployed": "To deploy", "cash_left": "Stays cash",
        "risk": "Risk", "gain": "If all targets hit", "loss": "If all stops hit", "hurdle": "Monthly return needed to cover costs",
        "allocation": "Allocation", "ticker": "Ticker", "verdict": "Verdict", "shares": "Shares", "value": "Value",
        "entry": "Entry", "stop": "Stop", "target": "Target", "rr": "R:R", "score": "Score",
        "holdings": "Your positions", "action": "Action", "hold": "Hold", "sell": "Sell", "tighten": "Tighten stop", "exit": "Exit",
        "picks": "Picks", "chart_ev": "Chart evidence", "news_ev": "News and sources", "book": "Order book",
        "fin": "Financials", "votes": "Analyst votes", "catalysts": "Catalysts", "scan": "Everything scanned",
        "drops": "Dropped and why", "costs": "Costs", "disclaimer": "Educational analysis, not investment advice. Every decision and order is yours.",
        "made": "Made with love by", "wait_for": "Waiting for", "reasons": "Reasons", "red": "Red events", "history": "Setup history",
        "recap": "Animated recap", "replay": "Replay", "no_news": "No fresh news; the verdict is technical only", "macro": "Week ahead",
        "warnings": "Warnings", "limited": "limited by",
    },
}

DROP_WORDS = {"rr": "R:R < 2", "thin": "thin", "wide": "stop > 3 ATR", "noise": "stop < 1 ATR", "invalid": "target below price",
              "limit": "near limit band", "new": "new listing", "no-plan": "no support/plan", "unknown": "chart unreadable"}


# ----------------------------------------------------------------- report pieces
def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def svg_chart(s: dict, w=760, h=300) -> str:
    """candles + volume-free price chart with plan levels, drawn from s['candles'] = [[date,o,h,l,c],...]"""
    C = s.get("candles") or []
    if len(C) < 5:
        return ""
    p = s.get("plan") or {}
    z = s.get("zones") or {}
    levels = []
    if z.get("support"):
        levels.append((z["support"]["lo"], z["support"]["hi"], "#ffb340", "S"))
    for r in (z.get("resistance") or [])[:2]:
        levels.append((r["lo"], r["hi"], "#ff453a", "R"))
    lines = [(p.get("entry"), "#0a84ff", "E"), (p.get("stop"), "#ff453a", "SL"), (p.get("target"), "#30d158", "T")]
    vals = [x for c in C for x in c[1:5]] + [v for lv in levels for v in lv[:2]] + [x for x, _, _ in lines if x]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    L_, R_, T_, B_ = 8, 64, 10, 22
    cw = (w - L_ - R_) / len(C)
    y = lambda v: T_ + (hi - v) / (hi - lo) * (h - T_ - B_)
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="{esc(s.get("tk"))} daily chart, last {len(C)} bars">']
    for a, b, col, _ in levels:
        out.append(f'<rect x="{L_}" y="{y(b):.1f}" width="{w-L_-R_}" height="{max(2, y(a)-y(b)):.1f}" fill="{col}" opacity=".12"/>')
    for i, (d, o, hh, ll, c) in enumerate(C):
        x = L_ + i * cw + cw / 2
        col = "#30d158" if c >= o else "#ff453a"
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{y(hh):.1f}" y2="{y(ll):.1f}" stroke="{col}" stroke-width="1"/>')
        top, bot = y(max(o, c)), y(min(o, c))
        out.append(f'<rect x="{x-cw*0.35:.1f}" y="{top:.1f}" width="{max(1, cw*0.7):.1f}" height="{max(1, bot-top):.1f}" fill="{col}"/>')
    for v, col, lab in lines:
        if v:
            out.append(f'<line x1="{L_}" x2="{w-R_}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width="1.4" stroke-dasharray="{"0" if lab != "T" else "5 3"}"/>')
            out.append(f'<text x="{w-R_+4}" y="{y(v)+4:.1f}" fill="{col}" font-size="11">{lab} {esc(v)}</text>')
    for k in (0, len(C) // 2, len(C) - 1):
        out.append(f'<text x="{L_ + k*cw:.1f}" y="{h-6}" fill="#8e8e93" font-size="10">{esc(C[k][0][5:])}</text>')
    out.append("</svg>")
    return "".join(out)


def recap_composition(run: dict, cfg: dict) -> str:
    """A HyperFrames composition (HTML -> MP4 with `npx hyperframes render`). Also plays in any browser."""
    meta, al = run.get("meta") or {}, run.get("allocation") or {}
    eg = ((run.get("market") or {}).get("egx30") or {})
    rows = [r for r in al.get("rows") or [] if r.get("shares")][:4]
    if not rows:
        rows = [{"tk": s["tk"], "entry": (s.get("plan") or {}).get("entry"), "stop": (s.get("plan") or {}).get("stop"),
                 "target": (s.get("plan") or {}).get("target"), "verdict": s.get("verdict"), "shares": 0}
                for s in run.get("stocks") or [] if s.get("verdict") in ("valid", "wait")][:4]
    regime = eg.get("regime", "unknown")
    rc = {"Up": "#30d158", "Down": "#ff453a", "Correction": "#ffb340"}.get(regime, "#8e8e93")
    cards = "".join(
        f'<div class="card" id="c{i}"><div class="tk">{esc(r["tk"])}</div><div class="v {esc(r.get("verdict"))}">{esc((r.get("verdict") or "").replace("_", " ").upper())}</div>'
        f'<div class="row"><span>ENTRY</span><b>{esc(r.get("entry"))}</b></div><div class="row"><span>STOP</span><b class="r">{esc(r.get("stop"))}</b></div>'
        f'<div class="row"><span>TARGET</span><b class="g">{esc(r.get("target"))}</b></div>'
        + (f'<div class="row"><span>SHARES</span><b>{esc(r.get("shares"))}</b></div>' if r.get("shares") else "") + "</div>"
        for i, r in enumerate(rows)) or '<div class="card" id="c0"><div class="tk">CASH</div><div class="row"><span>No valid setups</span></div></div>'
    foot = cfg["footer"]
    title = meta.get("command", "EGX")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
:root{{--ground:#000;--ink:#f5f5f7;--muted:#8e8e93;--g:#30d158;--r:#ff453a;--b:#0a84ff;--a:#ffb340}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1920px;height:1080px;overflow:hidden;background:var(--ground);font-family:Inter,sans-serif;color:var(--ink)}}
#root{{position:relative;width:100%;height:100%}}
.clip{{position:absolute;inset:0}}
.scene{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px;opacity:0}}
.kicker{{font-size:34px;letter-spacing:.32em;color:var(--muted);text-transform:uppercase}}
.big{{font-size:150px;font-weight:900;letter-spacing:-.04em;line-height:1}}
.pill{{font-size:46px;font-weight:700;padding:14px 40px;border-radius:999px;border:3px solid {rc};color:{rc}}}
.sub{{font-size:40px;color:var(--muted)}}
.cards{{display:flex;gap:36px}}
.card{{width:400px;padding:40px;border-radius:36px;background:#141416;border:2px solid #2a2a2e;display:flex;flex-direction:column;gap:18px}}
.tk{{font-size:72px;font-weight:900;letter-spacing:-.03em}}
.v{{font-size:28px;font-weight:700;color:var(--a)}} .v.valid,.v.add{{color:var(--g)}} .v.not_valid{{color:var(--r)}}
.row{{display:flex;justify-content:space-between;font-size:34px;color:var(--muted)}} .row b{{color:var(--ink)}} b.g{{color:var(--g)}} b.r{{color:var(--r)}}
.nums{{display:flex;gap:90px}} .n{{text-align:center}} .n b{{display:block;font-size:96px;font-weight:900;letter-spacing:-.03em}} .n span{{font-size:30px;color:var(--muted);letter-spacing:.2em}}
.heart{{color:var(--r)}}
</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="12" data-width="1920" data-height="1080">
 <div id="s1" class="clip" data-start="0" data-duration="3.2" data-track-index="1"><div class="scene" id="s1i">
  <div class="kicker">EGX · {esc(title)} · {esc(meta.get('trading_day') or meta.get('created', '')[:10])}</div>
  <div class="big">EGX30 {esc(f(eg.get('last'), 0))}</div>
  <div class="pill">{esc(regime.upper())} MARKET</div>
  <div class="sub">MA50 {esc(f(eg.get('ma50'), 0))} · MA200 {esc(f(eg.get('ma200'), 0))} · 20d {esc(eg.get('ch20'))}%</div>
 </div></div>
 <div id="s2" class="clip" data-start="3.2" data-duration="4.6" data-track-index="1"><div class="scene" id="s2i">
  <div class="kicker">Plan</div><div class="cards">{cards}</div>
 </div></div>
 <div id="s3" class="clip" data-start="7.8" data-duration="2.6" data-track-index="1"><div class="scene" id="s3i">
  <div class="nums"><div class="n"><b>{esc(f(al.get('deployed'), 0))}</b><span>DEPLOY EGP</span></div>
  <div class="n"><b>{esc(f(al.get('cash_left'), 0))}</b><span>CASH EGP</span></div>
  <div class="n"><b>{esc(f(al.get('total_risk'), 0))}</b><span>AT RISK EGP</span></div></div>
 </div></div>
 <div id="s4" class="clip" data-start="10.4" data-duration="1.6" data-track-index="1"><div class="scene" id="s4i">
  <div class="sub">Made with <span class="heart">♥</span> by {esc(foot['author'])}</div><div class="kicker">Analysis, not investment advice</div>
 </div></div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
if (!window.gsap) {{ /* offline: show the plan scene still */
  document.querySelectorAll(".scene").forEach((e, i) => (e.style.opacity = i === 1 ? 1 : 0));
}} else {{
const tl = gsap.timeline({{ paused: true }});
const scene = (id, start, dur) => {{
  tl.fromTo(id, {{ opacity: 0, y: 40, filter: "blur(10px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", duration: 0.5, ease: "power3.out" }}, start);
  tl.to(id, {{ opacity: 0, y: -30, duration: 0.35, ease: "power2.in" }}, start + dur - 0.4);
}};
scene("#s1i", 0, 3.2); scene("#s2i", 3.2, 4.6); scene("#s3i", 7.8, 2.6);
tl.fromTo("#s4i", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 10.4);
tl.fromTo(".card", {{ opacity: 0, y: 60, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "back.out(1.4)", stagger: 0.18 }}, 3.5);
tl.fromTo(".n b", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.45, stagger: 0.15, ease: "power3.out" }}, 8.0);
window.__timelines["main"] = tl;
tl.seek(0);
}}
</script>
</body></html>"""


CSS = r"""
:root{--bg:#000;--s1:#0f0f10;--s2:#161618;--s3:#1d1d20;--line:#2a2a2e;--ink:#f5f5f7;--muted:#8e8e93;
--g:#30d158;--r:#ff453a;--b:#0a84ff;--a:#ffb340;--radius:18px;
--font:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Arabic","Segoe UI","Noto Sans Arabic",Tahoma,system-ui,sans-serif}
*{box-sizing:border-box}
html{font:100%/1.5 var(--font);background:var(--bg);color:var(--ink);-webkit-text-size-adjust:100%}
body{margin:0}
a{color:var(--b);text-decoration:none} a:hover{text-decoration:underline}
.top{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px max(16px,4vw);
 background:rgba(10,10,12,.72);backdrop-filter:blur(20px) saturate(180%);-webkit-backdrop-filter:blur(20px) saturate(180%);
 border-bottom:1px solid rgba(255,255,255,.08)}
.top h1{font-size:1.05rem;margin:0;letter-spacing:-.01em;font-weight:700}
.top .meta{color:var(--muted);font-size:.85rem}
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 12px;border-radius:999px;font-size:.8rem;font-weight:600;border:1px solid currentColor}
.Up{color:var(--g)} .Down{color:var(--r)} .Correction{color:var(--a)} .unknown{color:var(--muted)}
main{max-width:1180px;margin:0 auto;padding:20px max(16px,4vw) 60px}
section{margin:28px 0}
h2{font-size:1.35rem;line-height:1.15;letter-spacing:-.02em;margin:0 0 12px}
h3{font-size:1.05rem;margin:0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.kpi{background:var(--s1);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}
.kpi span{display:block;color:var(--muted);font-size:.8rem}
.kpi b{font-size:1.45rem;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.card{background:var(--s1);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin:12px 0}
.card .head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.tk{font-weight:800;font-size:1.3rem;letter-spacing:-.02em}
.name{color:var(--muted);font-size:.9rem}
.badge{padding:3px 10px;border-radius:999px;font-size:.8rem;font-weight:700;background:var(--s3)}
.badge.valid,.badge.add,.badge.hold{color:var(--g)} .badge.wait,.badge.tighten{color:var(--a)} .badge.not_valid,.badge.sell,.badge.exit{color:var(--r)}
.plan{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin:12px 0}
.plan div{background:var(--s2);border-radius:12px;padding:8px 10px} .plan span{display:block;color:var(--muted);font-size:.75rem} .plan b{font-variant-numeric:tabular-nums}
.e{color:var(--b)} .s{color:var(--r)} .t{color:var(--g)}
.scorebar{height:6px;border-radius:6px;background:var(--s3);overflow:hidden;margin-top:6px} .scorebar i{display:block;height:100%;background:linear-gradient(90deg,var(--a),var(--g))}
ul.reasons{margin:8px 0;padding-inline-start:20px} ul.reasons li{margin:3px 0}
details{background:var(--s2);border:1px solid var(--line);border-radius:14px;margin:8px 0;overflow:hidden}
summary{cursor:pointer;padding:11px 14px;font-weight:600;list-style:none;display:flex;justify-content:space-between;align-items:center;user-select:none}
summary::-webkit-details-marker{display:none}
summary::after{content:"›";transition:transform .25s cubic-bezier(.2,.8,.2,1);color:var(--muted);font-size:1.2rem}
html[dir=rtl] summary::after{content:"‹"}
details[open]>summary::after{transform:rotate(90deg)} html[dir=rtl] details[open]>summary::after{transform:rotate(-90deg)}
summary:active{transform:scale(.99)}
details>.body{padding:4px 14px 14px;color:#d1d1d6;font-size:.92rem}
.ev{margin:0;padding-inline-start:18px} .ev li{margin:4px 0;font-variant-numeric:tabular-nums}
.tbl{overflow-x:auto;border-radius:14px;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:start;white-space:nowrap}
th{color:var(--muted);font-weight:600;background:var(--s1);position:sticky;top:0}
tr:last-child td{border-bottom:none}
.chart{direction:ltr;width:100%;height:auto;background:var(--s2);border-radius:12px;margin-top:10px}
.shot{width:100%;border-radius:12px;margin-top:10px;border:1px solid var(--line)}
.news li{margin:6px 0} .imp{font-weight:700} .imp.pos{color:var(--g)} .imp.neg{color:var(--r)} .imp.neu{color:var(--muted)}
.fresh{color:var(--a);font-size:.75rem;font-weight:700}
.warn{background:rgba(255,179,64,.1);border:1px solid rgba(255,179,64,.4);color:var(--a);border-radius:14px;padding:10px 14px}
.recap{position:relative;width:100%;aspect-ratio:16/9;border-radius:22px;overflow:hidden;border:1px solid var(--line);background:#000}
.recap iframe{position:absolute;top:0;left:0;width:1920px;height:1080px;border:0;transform-origin:0 0}
.btn{appearance:none;border:1px solid var(--line);background:rgba(30,30,32,.8);color:var(--ink);border-radius:999px;padding:7px 14px;font:inherit;font-size:.85rem;cursor:pointer;backdrop-filter:blur(12px)}
.btn:active{transform:scale(.97);transition:transform .1s ease-out}
.recap .btn{position:absolute;bottom:12px;inset-inline-end:12px}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);color:var(--muted);font-size:.85rem;text-align:center;line-height:1.9}
footer .heart{color:var(--r)}
.muted{color:var(--muted)} .num{font-variant-numeric:tabular-nums}
@media (prefers-reduced-motion:reduce){summary::after{transition:none}}
@media (prefers-reduced-transparency:reduce){.top{background:#0a0a0c;backdrop-filter:none}}
@media (prefers-contrast:more){.card,.kpi,details{border-color:#8e8e93}}
@media print{.top{position:static}.recap{display:none}details{break-inside:avoid}details>.body{display:block}}
"""

JS = r"""
(function(){
 const box=document.querySelector('.recap'); if(!box) return;
 const fr=box.querySelector('iframe');
 const fit=()=>{fr.style.transform='scale('+(box.clientWidth/1920)+')'};
 addEventListener('resize',fit); fit();
 const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const play=()=>{try{const t=fr.contentWindow.__timelines.main; if(reduce){t.seek(9)} else {t.restart()}}catch(e){}};
 fr.addEventListener('load',()=>setTimeout(play,250));
 box.querySelector('.btn').addEventListener('click',play);
})();
"""


def news_html(items, t) -> str:
    if not items:
        return f'<p class="muted">{esc(t["no_news"])}</p>'
    li = []
    for n in items:
        imp = {"+": "pos", "positive": "pos", "-": "neg", "negative": "neg"}.get(str(n.get("impact", "")).lower(), "neu")
        mark = {"pos": "▲", "neg": "▼", "neu": "•"}[imp]
        li.append(f'<li><span class="imp {imp}">{mark}</span> <a href="{esc(n.get("url"))}" target="_blank" rel="noopener">{esc(n.get("title"))}</a>'
                  f' <span class="muted">— {esc(n.get("source"))}, {esc(n.get("date"))}</span>'
                  + (' <span class="fresh">48h</span>' if n.get("fresh") else "")
                  + (f'<br><span class="muted">{esc(n.get("summary"))}</span>' if n.get("summary") else "") + "</li>")
    return '<ul class="news ev">' + "".join(li) + "</ul>"


def kv_table(d: dict) -> str:
    if not d:
        return '<p class="muted">—</p>'
    return '<div class="tbl"><table>' + "".join(f"<tr><td>{esc(k)}</td><td class='num'>{esc(v)}</td></tr>" for k, v in d.items()) + "</table></div>"


def plan_block(p: dict, t: dict, extra=None) -> str:
    if not p:
        return ""
    cells = [(t["entry"], p.get("entry"), "e"), (t["stop"], p.get("stop"), "s"), (t["target"], p.get("target"), "t"),
             (t["rr"], p.get("rr"), ""), ("ATR (stop)", p.get("stopATR"), ""), ("type", p.get("type"), "")]
    cells += extra or []
    return '<div class="plan">' + "".join(f'<div><span>{esc(a)}</span><b class="{c}">{esc(b)}</b></div>' for a, b, c in cells) + "</div>"


def stock_card(s: dict, t: dict, alloc_row=None, head_html=None) -> str:
    p, z = s.get("plan") or {}, s.get("zones") or {}
    v = s.get("verdict") or "dropped"
    score = (s.get("score") or {}).get("total")
    head = (f'<div class="head"><span class="tk">{esc(s.get("tk"))}</span><span class="name">{esc(s.get("title"))}</span>'
            f'<span class="badge {esc(v)}">{esc(t.get(v, v))}</span><span class="muted num">{esc(s.get("last"))} ({esc(s.get("chg"))}%)</span>'
            + (f'<span class="muted">{esc(t["score"])} {score}/10</span>' if score is not None else "") + "</div>")
    if score is not None:
        head += f'<div class="scorebar"><i style="width:{score*10}%"></i></div>'
    if head_html is not None:
        head = head_html
    extra = [(t["shares"], alloc_row["shares"], ""), (t["value"], f(alloc_row["value"]), "")] if alloc_row and alloc_row.get("shares") else None
    body = head + plan_block(p, t, extra)
    if s.get("reasons"):
        body += '<ul class="reasons">' + "".join(f"<li>{esc(r)}</li>" for r in s["reasons"]) + "</ul>"
    if s.get("wait_for"):
        body += f'<p><b>{esc(t["wait_for"])}:</b> {esc(s["wait_for"])}</p>'
    body += svg_chart(s)
    if s.get("screenshot_b64"):
        body += f'<img class="shot" alt="ThndrX chart {esc(s.get("tk"))}" src="data:image/jpeg;base64,{s["screenshot_b64"]}"/>'
    ev = list(s.get("evidence") or [])
    if z:
        if z.get("trendline"):
            tl = z["trendline"]
            ev.append(f"Trendline {tl['kind']}: {tl['from'][0]} {tl['from'][1]} → {tl['to'][0]} {tl['to'][1]} (now {tl.get('now')})")
        if z.get("brokenSupportNowResistance"):
            ev.append("Broken supports now resistance: " + ", ".join(f"{b['lo']}-{b['hi']}" for b in z["brokenSupportNowResistance"]))
        ev.append(f"300-bar high {z.get('hi300')} / low {z.get('lo300')}; round numbers {z.get('roundNumbers')}")
    pat = s.get("patterns") or {}
    if pat.get("doubleBottom"):
        ev.append("Double bottom: " + " & ".join(pat["doubleBottom"]))
    if s.get("history"):
        hst = s["history"]
        ev.append(f"Setup history: {hst.get('hits')}/{hst.get('tries')} reached target before stop in 15 bars ({hst.get('judge')})")
    if s.get("flags"):
        ev.append("Flags: " + "; ".join(s["flags"]))
    body += f'<details><summary>{esc(t["chart_ev"])}</summary><div class="body"><ul class="ev">' + "".join(f"<li>{esc(e)}</li>" for e in ev) + "</ul>"
    if s.get("score"):
        body += f'<p class="muted">{esc(t["score"])}: ' + ", ".join(f"{k} {v}" for k, v in s["score"].get("parts", {}).items()) + "</p>"
    body += "</div></details>"
    body += f'<details><summary>{esc(t["news_ev"])}</summary><div class="body">{news_html(s.get("news"), t)}'
    if s.get("red_events"):
        body += f'<p><b>{esc(t["red"])}:</b></p><ul class="ev">' + "".join(
            f'<li>{esc(r.get("type"))} {esc(r.get("date"))} — <a href="{esc(r.get("url"))}" target="_blank" rel="noopener">{esc(r.get("source"))}</a></li>' for r in s["red_events"]) + "</ul>"
    body += "</div></details>"
    pg = (s.get("page") or {})
    if pg.get("book") or pg.get("band"):
        b = pg.get("book") or {}
        body += (f'<details><summary>{esc(t["book"])}</summary><div class="body">' +
                 kv_table({"bid %": b.get("bidPct"), "ask %": b.get("askPct"), "best bid": b.get("bestBid"), "best ask": b.get("bestAsk"),
                           "spread %": b.get("spreadPct"), "side": b.get("side"), "price band": pg.get("band")}) + "</div></details>")
    fin = s.get("financials") or {}
    if fin.get("metrics") or fin.get("scores"):
        body += f'<details><summary>{esc(t["fin"])}</summary><div class="body">{kv_table({**fin.get("scores", {}), **fin.get("metrics", {})})}</div></details>'
    if s.get("votes"):
        rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v.get('verdict'))}</td><td>{esc(v.get('confidence'))}</td><td style='white-space:normal'>{esc('; '.join(v.get('facts') or []))}</td></tr>" for k, v in s["votes"].items())
        body += f'<details><summary>{esc(t["votes"])}</summary><div class="body"><div class="tbl"><table>{rows}</table></div></div></details>'
    return f'<article class="card" id="stock-{esc(s.get("tk"))}">{body}</article>'


def holding_card(h: dict, t: dict) -> str:
    a = h.get("action") or "hold"
    s = dict(h.get("analysis") or {})
    s.update({k: v for k, v in h.items() if k in ("news", "reasons", "red_events", "screenshot_b64", "wait_for")})
    s["tk"] = h.get("tk")
    head = (f'<div class="head"><span class="tk">{esc(h.get("tk"))}</span><span class="name">{esc(s.get("title"))}</span>'
            f'<span class="badge {esc(a)}">{esc(t.get(a, a))}</span>'
            f'<span class="muted num">{esc(h.get("qty"))} × {esc(h.get("avgPrice"))} → {esc(h.get("price"))} '
            f'({esc(h.get("pnlPct"))}%, {esc(f(h.get("pnl")))} EGP)</span></div>')
    if h.get("plan"):
        s["plan"] = h["plan"]
    else:
        s["plan"] = {"entry": h.get("price"), "stop": h.get("stop"), "target": h.get("target"), "type": a}
    return stock_card(s, t, None, head_html=head).replace('<article class="card" id="stock-', '<article class="card" id="hold-', 1)


def build_html(run: dict, cfg: dict, fname: str) -> str:
    t = L.get(cfg.get("language", "ar"), L["ar"])
    meta, mk, al = run.get("meta") or {}, run.get("market") or {}, run.get("allocation") or {}
    eg = mk.get("egx30") or {}
    regime = eg.get("regime", "unknown")
    stocks = run.get("stocks") or []
    deep = [s for s in stocks if s.get("verdict") in ("valid", "wait", "not_valid")]
    rows = al.get("rows") or []
    by_tk = {r["tk"]: r for r in rows}
    title = f'{meta.get("command", "EGX")} · {meta.get("created", "")[:16].replace("T", " ")}'
    parts = [f'<header class="top"><h1>{esc(t["title"])} · {esc(meta.get("command"))}</h1>'
             f'<span class="pill {esc(regime)}">EGX30 {esc(f(eg.get("last"), 0))} · {esc(t.get(regime, regime))}</span>'
             f'<span class="meta">{esc(meta.get("created", "")[:16].replace("T", " "))} · {esc(t["market"])} {esc(meta.get("trading_day", ""))}</span></header><main>']
    # recap (HyperFrames composition, plays in place)
    parts.append(f'<section><div class="recap" aria-label="{esc(t["recap"])}"><iframe title="recap" sandbox="allow-scripts allow-same-origin" '
                 f'srcdoc="{esc(recap_composition(run, cfg))}"></iframe><button class="btn" type="button">↻ {esc(t["replay"])}</button></div></section>')
    # market line
    ms = mk.get("summary") or (f"EGX30 {f(eg.get('last'), 0)}: MA50 {f(eg.get('ma50'), 0)} (slope {eg.get('ma50Slope')}%), "
                               f"MA200 {f(eg.get('ma200'), 0)}, 20d {eg.get('ch20')}%, 60d {eg.get('ch60')}%, {eg.get('fromHigh')}% from high")
    parts.append(f'<section><h2>{esc(t["market"])}</h2><p>{esc(ms)}</p>')
    pg = mk.get("page") or {}
    if pg.get("sectors"):
        parts.append(f'<details><summary>Sectors · breadth {esc(pg.get("gainers"))}▲ / {esc(pg.get("losers"))}▼ · USD/EGP {esc(pg.get("usdEgp"))}</summary><div class="body">'
                     + kv_table({a: f"{b}%" for a, b in pg["sectors"]}) + "</div></details>")
    if mk.get("macro"):
        parts.append(f'<details><summary>{esc(t["macro"])}</summary><div class="body">{news_html(mk["macro"], t)}</div></details>')
    parts.append("</section>")
    # KPIs
    k = [(t["amount"], meta.get("amount")), (t["cash"], meta.get("cash")), (t["deployed"], al.get("deployed")), (t["cash_left"], al.get("cash_left")),
         (t["risk"], al.get("total_risk")), (t["gain"], al.get("gain_if_all_targets")), (t["loss"], al.get("loss_if_all_stops")),
         (t["hurdle"], f'{al.get("break_even_monthly_pct")}%' if al.get("break_even_monthly_pct") is not None else None)]
    parts.append('<section><div class="grid">' + "".join(f'<div class="kpi"><span>{esc(a)}</span><b>{esc(f(b) if not isinstance(b, str) else b)}</b></div>' for a, b in k) + "</div>")
    if al.get("warnings"):
        parts.append(f'<p class="warn">⚠️ {esc(" · ".join(al["warnings"]))}</p>')
    parts.append("</section>")
    # allocation
    if rows:
        tr = "".join(
            f'<tr><td><a href="#stock-{esc(r["tk"])}">{esc(r["tk"])}</a></td><td><span class="badge {esc(r["verdict"])}">{esc(t.get(r["verdict"], r["verdict"]))}</span></td>'
            f'<td>{esc(r["order"])}</td><td>{esc(r["shares"])}</td><td>{esc(f(r["value"]))}</td><td class="e">{esc(r["entry"])}</td><td class="s">{esc(r["stop"])}</td>'
            f'<td class="t">{esc(r["target"])}</td><td>{esc(r["rr"])}</td><td>{esc(f(r["risk"]))}</td><td class="muted">{esc(t["limited"])} {esc(r["limited_by"])} {esc(r["note"])}</td></tr>'
            for r in rows)
        parts.append(f'<section><h2>{esc(t["allocation"])}</h2><div class="tbl"><table><tr><th>{t["ticker"]}</th><th>{t["verdict"]}</th><th>order</th><th>{t["shares"]}</th>'
                     f'<th>{t["value"]}</th><th>{t["entry"]}</th><th>{t["stop"]}</th><th>{t["target"]}</th><th>{t["rr"]}</th><th>{t["risk"]}</th><th></th></tr>{tr}</table></div></section>')
    # holdings
    hs = run.get("holdings") or []
    if hs:
        parts.append(f'<section><h2>{esc(t["holdings"])}</h2>' + "".join(holding_card(h, t) for h in hs if not h.get("is_fund")))
        funds = [h for h in hs if h.get("is_fund")]
        if funds:
            parts.append('<p class="muted">Funds (not analysed): ' + ", ".join(f'{esc(h["tk"])} {esc(f(h.get("value")))} EGP' for h in funds) + "</p>")
        parts.append("</section>")
    # catalysts
    cats = run.get("catalysts") or []
    if cats:
        tr = "".join(f'<tr><td>{esc(c.get("tk"))}</td><td>{esc(c.get("type"))}</td><td style="white-space:normal">{esc(c.get("summary"))}</td>'
                     f'<td><a href="{esc(c.get("url"))}" target="_blank" rel="noopener">{esc(c.get("source"))}</a></td><td>{esc(c.get("date"))}</td>'
                     f'<td>{esc(c.get("moved_pct"))}% / {esc(c.get("moved_atr"))} ATR</td><td>{"priced in" if c.get("priced_in") else "open"}</td></tr>' for c in cats)
        parts.append(f'<section><h2>{esc(t["catalysts"])}</h2><div class="tbl"><table>{tr}</table></div></section>')
    # deep picks
    if deep:
        parts.append(f'<section><h2>{esc(t["picks"])}</h2>' + "".join(stock_card(s, t, by_tk.get(s["tk"])) for s in deep) + "</section>")
    # scan table + drops
    if stocks:
        tr = "".join(
            f'<tr><td>{esc(s.get("tk"))}</td><td>{esc(s.get("last"))}</td><td>{esc((s.get("trend") or {}).get("daily"))}/{esc((s.get("trend") or {}).get("weekly"))}</td>'
            f'<td>{esc((s.get("rs") or {}).get("rs20"))}/{esc((s.get("rs") or {}).get("rs60"))}</td><td>{esc((s.get("plan") or {}).get("entry"))}</td>'
            f'<td>{esc((s.get("plan") or {}).get("stop"))}</td><td>{esc((s.get("plan") or {}).get("target"))}</td><td>{esc((s.get("plan") or {}).get("rr"))}</td>'
            f'<td>{esc((s.get("score") or {}).get("total"))}</td><td>{esc(DROP_WORDS.get(s.get("drop"), s.get("drop") or s.get("verdict") or ""))}</td></tr>'
            for s in stocks)
        parts.append(f'<section><details><summary>{esc(t["scan"])} ({len(stocks)})</summary><div class="body"><div class="tbl"><table>'
                     f'<tr><th>{t["ticker"]}</th><th>last</th><th>trend d/w</th><th>RS 20/60</th><th>{t["entry"]}</th><th>{t["stop"]}</th><th>{t["target"]}</th><th>{t["rr"]}</th><th>{t["score"]}</th><th>status</th></tr>{tr}</table></div></div></details>')
        drops = {}
        for s in stocks:
            if s.get("drop"):
                drops.setdefault(DROP_WORDS.get(s["drop"], s["drop"]), []).append(s["tk"])
        if drops:
            parts.append(f'<details><summary>{esc(t["drops"])}</summary><div class="body"><ul class="ev">' + "".join(f"<li><b>{esc(k)}:</b> {esc(', '.join(v))}</li>" for k, v in drops.items()) + "</ul></div></details>")
        parts.append("</section>")
    # costs
    if al:
        parts.append(f'<section><h2>{esc(t["costs"])}</h2><div class="grid">'
                     f'<div class="kpi"><span>fixed / month</span><b>{esc(f(al.get("fixed_monthly"), 0))}</b></div>'
                     f'<div class="kpi"><span>{esc(t["hurdle"])}</span><b>{esc(al.get("break_even_monthly_pct"))}%</b></div>'
                     f'<div class="kpi"><span>capital for 1%/month</span><b>{esc(f(al.get("capital_for_1pct_month"), 0))}</b></div>'
                     f'<div class="kpi"><span>risk / trade</span><b>{esc(al.get("risk_pct"))}% = {esc(f(al.get("risk_budget_per_trade")))}</b></div></div></section>')
    if meta.get("notes"):
        parts.append(f'<section><p class="muted">{esc(meta["notes"])}</p></section>')
    foot = cfg["footer"]
    parts.append(f'<footer><div>{esc(t["disclaimer"])}</div><div>{esc(t["made"])} <span class="heart">♥</span> <b>{esc(foot["author"])}</b> · '
                 f'<a href="mailto:{esc(foot["email"])}">{esc(foot["email"])}</a> · <a href="{esc(foot["repo"])}" target="_blank" rel="noopener">GitHub</a></div>'
                 f'<div class="muted">egx-thndrx-trading v{VERSION} · {esc(fname)}</div></footer></main>')
    data = json.dumps({k: v for k, v in run.items()}, ensure_ascii=False).replace("</", "<\\/")
    idx = index_row(run, fname)
    return (f'<!doctype html><html lang="{t["lang"]}" dir="{t["dir"]}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="color-scheme" content="dark"><title>{esc(title)}</title>'
            f'<meta name="egx-report" content="{esc(json.dumps(idx, ensure_ascii=False))}">'
            f'<!-- FOR CLAUDE: all data of this report is the JSON in script#egx-data at the end of the body. '
            f'Read it with: python3 egx.py read {esc(fname)} [--ticker TK]. Search reports with index.csv in this folder. -->'
            f'<style>{CSS}</style></head><body>{"".join(parts)}'
            f'<script id="egx-data" type="application/json">{data}</script><script>{JS}</script></body></html>')


# ----------------------------------------------------------------- index
def index_row(run: dict, fname: str) -> dict:
    meta, al = run.get("meta") or {}, run.get("allocation") or {}
    eg = ((run.get("market") or {}).get("egx30") or {})
    st = run.get("stocks") or []
    pick = lambda v: ";".join(s["tk"] for s in st if s.get("verdict") == v)
    hs = [h for h in run.get("holdings") or [] if not h.get("is_fund")]
    top = next((r["tk"] for r in al.get("rows") or [] if r.get("shares")), "") or pick("valid").split(";")[0] or pick("wait").split(";")[0]
    return {
        "file": fname, "created": meta.get("created", ""), "trading_day": meta.get("trading_day", ""), "command": meta.get("command", ""),
        "regime": eg.get("regime", ""), "egx30": eg.get("last", ""), "amount": meta.get("amount", ""), "deployed": al.get("deployed", ""),
        "cash_left": al.get("cash_left", ""), "tickers": ";".join(s.get("tk", "") for s in st), "valid": pick("valid"), "wait": pick("wait"),
        "not_valid": pick("not_valid"), "holdings": ";".join(h.get("tk", "") for h in hs),
        "holding_actions": ";".join(f'{h.get("tk")}:{h.get("action", "hold")}' for h in hs),
        "top_pick": top, "catalysts": ";".join(f'{c.get("tk")}:{c.get("type")}' for c in run.get("catalysts") or []),
        "summary": (meta.get("summary") or "")[:300],
    }


def update_index(folder: pathlib.Path, row: dict) -> pathlib.Path:
    p = folder / "index.csv"
    rows = []
    if p.exists():
        with p.open(newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("file") != row["file"]]
    rows.append(row)
    rows.sort(key=lambda r: r.get("created", ""))
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return p


def report_name(run: dict, cfg: dict) -> str:
    meta = run.setdefault("meta", {})
    created = meta.get("created")
    if not created:
        created = now_local(cfg).strftime("%Y-%m-%dT%H:%M")
        meta["created"] = created
    cmd = re.sub(r"[^A-Za-z0-9]+", "", meta.get("command") or "EGX") or "EGX"
    d = created[:10]
    hm = created[11:16].replace(":", "-") if len(created) >= 16 else now_local(cfg).strftime("%H-%M")
    return f"EGX_{cmd}_{d}_{hm}.html"


def embed_screenshots(run: dict) -> None:
    """screenshot paths -> base64 (kept small); missing files are ignored"""
    import base64
    def emb(s):
        pth = s.get("screenshot")
        if pth and not s.get("screenshot_b64") and pathlib.Path(pth).exists():
            s["screenshot_b64"] = base64.b64encode(pathlib.Path(pth).read_bytes()).decode()
    for s in run.get("stocks") or []:
        emb(s)
    for h in run.get("holdings") or []:
        emb(h)


# ----------------------------------------------------------------- commands
def cmd_fees(a, cfg):
    v = float(a.value)
    side = fees_side(v, cfg)
    print(json.dumps({"order_value": v, "fees_per_side": side, "round_trip": round(2 * side, 2), "round_trip_pct": round(200 * side / v, 3)}))


def cmd_allocate(a, cfg):
    run = allocate(read_json(a.run), cfg)
    write_json(a.run, run)
    al = run["allocation"]
    for r in al["rows"]:
        print(f'{r["tk"]:6} {r["verdict"]:9} {r["order"]:8} {r["shares"]:>6} sh  {f(r["value"]):>10} EGP  E {r["entry"]} S {r["stop"]} T {r["target"]}  risk {f(r["risk"])}  [{r["limited_by"]}] {r["note"]}')
    print(json.dumps({k: v for k, v in al.items() if k != "rows"}, ensure_ascii=False))


def cmd_report(a, cfg):
    run = read_json(a.run)
    errs = check(run)
    if errs and not a.force:
        print("run file problems (fix them or pass --force):\n - " + "\n - ".join(errs), file=sys.stderr)
        sys.exit(2)
    if "allocation" not in run or a.reallocate:
        allocate(run, cfg)
    embed_screenshots(run)
    folder = reports_dir(cfg, a.out)
    name = report_name(run, cfg)
    out = folder / name
    out.write_text(build_html(run, cfg, name), encoding="utf-8")
    idx = update_index(folder, index_row(run, name))
    res = {"report": str(out), "index": str(idx), "bytes": out.stat().st_size}
    if a.video:
        vd = folder / "video" / name.replace(".html", "")
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "index.html").write_text(recap_composition(run, cfg), encoding="utf-8")
        res["video_project"] = str(vd)
        res["render"] = f'cd "{vd}" && npx hyperframes render --output "{folder / name.replace(".html", ".mp4")}"'
    write_json(a.run, run)
    print(json.dumps(res, ensure_ascii=False))


def load_index(folder: pathlib.Path):
    p = folder / "index.csv"
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cmd_search(a, cfg):
    rows = load_index(reports_dir(cfg, a.dir))
    def ok(r):
        if a.ticker and a.ticker.upper() not in (r["tickers"] + ";" + r["holdings"]).split(";"):
            return False
        if a.command and a.command.lower().replace(" ", "") not in r["command"].lower().replace(" ", ""):
            return False
        if a.since and r["created"][:10] < a.since:
            return False
        if a.verdict and (a.ticker or "").upper() not in r.get(a.verdict, "").split(";"):
            return False
        return True
    hits = [r for r in rows if ok(r)][-a.limit:]
    for r in hits:
        print(f'{r["created"][:16]}  {r["command"]:12} {r["regime"]:10} valid[{r["valid"]}] wait[{r["wait"]}] hold[{r["holding_actions"]}]  {r["file"]}')
    if not hits:
        print("no matching reports")


def extract_data(path: pathlib.Path) -> dict:
    txt = path.read_text(encoding="utf-8")
    tag = '<script id="egx-data" type="application/json">'
    i = txt.rfind(tag)
    if i < 0:
        raise SystemExit(f"{path}: no embedded egx-data")
    j = txt.index("</script>", i)
    return json.loads(txt[i + len(tag):j].replace("<\\/", "</"))


def cmd_read(a, cfg):
    p = pathlib.Path(a.file)
    if not p.exists():
        p = reports_dir(cfg, a.dir) / a.file
    d = extract_data(p)
    if a.ticker:
        tk = a.ticker.upper()
        d = {"meta": d.get("meta"), "market": (d.get("market") or {}).get("egx30"),
             "stock": next((s for s in d.get("stocks") or [] if s.get("tk") == tk), None),
             "holding": next((h for h in d.get("holdings") or [] if h.get("tk") == tk), None),
             "allocation": next((r for r in (d.get("allocation") or {}).get("rows") or [] if r.get("tk") == tk), None)}
        for k in ("stock", "holding"):
            if d.get(k):
                d[k] = {kk: vv for kk, vv in d[k].items() if kk not in ("candles", "screenshot_b64", "draw")}
    elif a.section:
        d = d.get(a.section)
    print(json.dumps(d, ensure_ascii=False, indent=None if a.compact else 1))


def cmd_history(a, cfg):
    folder = reports_dir(cfg, a.dir)
    tk = a.ticker.upper()
    for r in load_index(folder):
        if tk not in (r["tickers"] + ";" + r["holdings"]).split(";"):
            continue
        try:
            d = extract_data(folder / r["file"])
        except Exception as e:
            print(r["file"], "unreadable:", e)
            continue
        s = next((s for s in d.get("stocks") or [] if s.get("tk") == tk), {}) or {}
        h = next((h for h in d.get("holdings") or [] if h.get("tk") == tk), {}) or {}
        p = s.get("plan") or {}
        print(f'{r["created"][:16]} {r["command"]:11} {s.get("verdict") or h.get("action") or "-":9} last {s.get("last") or h.get("price")} '
              f'E {p.get("entry")} S {p.get("stop")} T {p.get("target")} RR {p.get("rr")} score {(s.get("score") or {}).get("total")}  {r["file"]}')


def cmd_check(a, cfg):
    errs = check(read_json(a.run))
    print("OK" if not errs else "\n".join(errs))
    sys.exit(1 if errs else 0)


def cmd_config(a, cfg):
    print(json.dumps(cfg, ensure_ascii=False, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="egx.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("fees"); p.add_argument("value"); p.set_defaults(fn=cmd_fees)
    p = sp.add_parser("allocate"); p.add_argument("run"); p.set_defaults(fn=cmd_allocate)
    p = sp.add_parser("report"); p.add_argument("run"); p.add_argument("--out"); p.add_argument("--video", action="store_true")
    p.add_argument("--force", action="store_true"); p.add_argument("--reallocate", action="store_true"); p.set_defaults(fn=cmd_report)
    p = sp.add_parser("search"); p.add_argument("--ticker"); p.add_argument("--command"); p.add_argument("--since")
    p.add_argument("--verdict", choices=["valid", "wait", "not_valid"]); p.add_argument("--limit", type=int, default=30); p.add_argument("--dir"); p.set_defaults(fn=cmd_search)
    p = sp.add_parser("read"); p.add_argument("file"); p.add_argument("--ticker"); p.add_argument("--section"); p.add_argument("--dir")
    p.add_argument("--compact", action="store_true"); p.set_defaults(fn=cmd_read)
    p = sp.add_parser("history"); p.add_argument("ticker"); p.add_argument("--dir"); p.set_defaults(fn=cmd_history)
    p = sp.add_parser("check"); p.add_argument("run"); p.set_defaults(fn=cmd_check)
    p = sp.add_parser("config"); p.set_defaults(fn=cmd_config)
    a = ap.parse_args(argv)
    a.fn(a, load_config())


if __name__ == "__main__":
    main()
