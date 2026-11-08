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
VERSION = "2.0.4"

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
            ar = (meta.get("language") or cfg.get("language") or "ar").startswith("ar")
            note, shares, value = (f"أقل من الحد الأدنى للأمر {cfg['min_order_egp']:,} جنيه" if ar else f"below minimum order {cfg['min_order_egp']:,} EGP"), 0, 0.0
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
        if (meta.get("language") or cfg.get("language") or "ar").startswith("ar"):
            warnings.append(f"الكاش في ThndrX {f(cash)} جنيه والخطة محتاجة {f(deployed)} جنيه: حوّل فلوس أو استرد من الصناديق الأول")
        else:
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
            if not s.get("screenshot") and not s.get("screenshot_b64"):
                errs.append(f"{tk}: deep-checked stock without a screenshot of the drawn ThndrX chart (mandatory evidence)")
            elif s.get("screenshot") and not pathlib.Path(s["screenshot"]).exists():
                errs.append(f"{tk}: screenshot file not found: {s['screenshot']}")
        for n in s.get("news") or []:
            if not n.get("url") or not n.get("date"):
                errs.append(f"{tk}: news item without url or date: {n.get('title', '')[:40]}")
    for c in run.get("catalysts") or []:
        if not c.get("url") or not c.get("date"):
            errs.append(f"catalyst {c.get('tk')}: url and date are required")
    return errs


# ----------------------------------------------------------------- report (HTML lives in egx_report.py)
sys.path.insert(0, str(HERE))
import egx_report  # noqa: E402


def build_html(run: dict, cfg: dict, fname: str) -> str:
    return egx_report.build_html(run, cfg, fname, egx_report.recap_composition(run, cfg), VERSION, index_row(run, fname))


def recap_composition(run: dict, cfg: dict) -> str:
    return egx_report.recap_composition(run, cfg)


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
    emb(run.setdefault("market", {}))


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
        mp4 = folder / name.replace(".html", ".mp4")
        res["render"] = f'cd "{vd}" && npx hyperframes render --output "{mp4}"'
        if a.render:
            import shutil, subprocess
            env = dict(os.environ)
            for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome",
                      r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
                if os.path.exists(c) and "HYPERFRAMES_BROWSER_PATH" not in env:
                    env["HYPERFRAMES_BROWSER_PATH"] = c
            if shutil.which("npx"):
                r = subprocess.run(["npx", "-y", "hyperframes@latest", "render", "--output", str(mp4)], cwd=vd, env=env,
                                   capture_output=True, text=True, shell=(os.name == "nt"))
                res["mp4"] = str(mp4) if mp4.exists() else None
                if not mp4.exists():
                    res["render_error"] = (r.stderr or r.stdout)[-600:]
            else:
                res["render_error"] = "Node.js (npx) not found"
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
    p = sp.add_parser("report"); p.add_argument("run"); p.add_argument("--out"); p.add_argument("--video", action="store_true"); p.add_argument("--render", action="store_true", help="with --video: render the MP4 now (needs Node + Chrome)")
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
