#!/usr/bin/env python3
"""
egx.py - helper CLI for the EGX ThndrX trading skills (Python 3.9+, standard library only).

Claude does the browsing; this script does the arithmetic and the paperwork, so it costs
no tokens to "think" about them:

  python3 egx.py fees 5000                      # Thndr fees for one order value (per side, round trip)
  python3 egx.py allocate run.json              # position sizing, caps, fees, costs -> writes run.json
  python3 egx.py report run.json [--video]      # HTML report + index.csv (+ HyperFrames recap project)
  python3 egx.py recall HRHO [--last 5]        # MEMORY: past verdicts, plans, outcomes, news of one stock (cheap)
  python3 egx.py news HRHO [--since DATE]       # MEMORY: news already found (do not search it again)
  python3 egx.py runs [--command Scan]          # MEMORY: what each run decided
  python3 egx.py outcome RUN TK target|stop|expired|time DATE   # record what happened to a call
  python3 egx.py open                           # calls still waiting for an outcome
  python3 egx.py drive-record NAME FILE_ID      # remember the Drive id of an uploaded file
  python3 egx.py search --ticker HRHO           # find past reports from index.csv
  python3 egx.py read REPORT.html [--ticker X]  # full detail of one report (rarely needed)
  python3 egx.py verdict run.json               # gates + verdict per stock (the only way a verdict is set)
  python3 egx.py check run.json                 # strict validation; the report refuses to build otherwise
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
VERSION = "3.0.0"

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
    "drive_folder_id": "",
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
    plan_of = lambda s: (((s.get("t0") or {}).get("plan")) if s.get("mode") == "t0" else s.get("plan")) or {}
    for s in run.get("stocks") or []:
        p = plan_of(s)
        if not p.get("entry") or not p.get("stop") or p["entry"] <= p["stop"]:
            continue
        if (p.get("rr") or 0) < 2:
            continue  # never size a plan under 2:1, whatever the verdict says
        if s.get("verdict") == "valid" or (s.get("verdict") == "wait" and meta.get("include_wait_orders")):
            picks.append(s)
    picks.sort(key=lambda s: (s.get("verdict") != "valid", -(s.get("score") or {}).get("total", 0), -(plan_of(s).get("rr") or 0)))
    for h in run.get("holdings") or []:  # "add" actions compete for the same money
        if h.get("action") == "add" and (h.get("plan") or {}).get("entry"):
            picks.append({"tk": h["tk"], "sector": h.get("sector"), "verdict": "add", "plan": h["plan"], "score": h.get("score") or {}})

    # T0 picks are sold by 14:20, so they reuse the run amount (one T0 trade at a time) and never use up swing money
    picks = [s for s in picks if s.get("mode") != "t0"] + [s for s in picks if s.get("mode") == "t0"]
    n_swing = len([s for s in picks if s.get("mode") != "t0"])
    rows, remaining = [], cap_total
    for i, s in enumerate(picks):
        p, tk = plan_of(s) or s["plan"], s["tk"]
        is_t0 = s.get("mode") == "t0"
        entry, stop, target = float(p["entry"]), float(p["stop"]), p.get("target")
        if is_t0:
            share_budget = amount if amount else float("inf")
        else:
            share_budget = remaining / max(1, n_swing - i) if amount else float("inf")  # Check / Positions: size by risk and caps only
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
        order = "T0 limit, exit by 14:20" if is_t0 else "buy now" if s.get("verdict") in ("valid", "add") and (p.get("type") or "").endswith("at-support") else "limit"
        row = {"tk": tk, "verdict": s.get("verdict"), "order": order, "t0": is_t0 or None,
               "shares": shares, "value": value, "entry": entry, "stop": stop, "target": target, "rr": p.get("rr"),
               "risk": round(shares * (entry - stop), 2), "limited_by": limit, "note": note, "sector": sec,
               "fees_buy": buy_fee}
        if shares:
            sell_t = shares * float(target) if target else 0
            sell_s = shares * stop
            row["gain_if_target"] = round(sell_t - value - buy_fee - fees_side(sell_t, cfg), 2) if target else None
            row["loss_if_stop"] = round(value - sell_s + buy_fee + fees_side(sell_s, cfg), 2)
            if not is_t0:
                remaining -= value + buy_fee
                held_value[tk] = held_value.get(tk, 0) + value
                sector_value[sec] = sector_value.get(sec, 0) + value
        rows.append(row)

    deployed = round(sum(r["value"] + r["fees_buy"] for r in rows if not r.get("t0")), 2)
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


# ----------------------------------------------------------------- gates, verdicts, validation
sys.path.insert(0, str(HERE))
import egx_gates as G  # noqa: E402  (same folder)


def verdicts(run: dict, cfg: dict) -> tuple[list[str], list[str]]:
    """Compute every stock's verdict from its receipts. Returns (checklist lines, errors)."""
    wl = G.whitelist(SKILL_DIR)
    lines, errs = [], []
    for s in run.get("stocks") or []:
        res, e = G.compute(s, run, wl, cfg, fees_side)
        errs += e
        s["verdict"] = res["verdict"]
        s["verdict_by"] = "egx.py " + VERSION
        s["auto_reasons"] = res.get("reasons") or []
        s["gates"] = [{"gate": g, "ok": ok, "note": n} for g, ok, n in res.get("gates") or []]
        if res.get("wait_for"):
            s["wait_for"] = res["wait_for"]
        else:
            s.pop("wait_for", None)
        lines.append(G.checklist_line(s.get("tk", "?"), res))
    ranked = rank_categories(run, cfg)
    if ranked:
        lines.append("ranking: " + " | ".join(f"{c}: " + ", ".join(f"#{i} {tk}" for i, tk in enumerate(v, 1)) for c, v in ranked.items()))
    return lines, errs


def rank_score(s: dict, run: dict, cfg: dict) -> float:
    """net R:R after fees (on the run amount, or EGP 10,000) x chart score / 10"""
    p = ((s.get("t0") or {}).get("plan") if s.get("mode") == "t0" else s.get("plan")) or {}
    e, st, tg = p.get("entry"), p.get("stop"), p.get("target")
    if not (e and st and tg) or e <= st:
        return 0.0
    q = max(1, math.floor(float((run.get("meta") or {}).get("amount") or 10000) / e))
    fb = fees_side(e * q, cfg)
    net = ((tg - e) * q - fb - fees_side(tg * q, cfg)) / ((e - st) * q + fb + fees_side(st * q, cfg))
    return round(net * ((s.get("score") or {}).get("total") or 0) / 10, 3)


def rank_categories(run: dict, cfg: dict) -> dict:
    """egx-scan: rank valid and wait picks inside each category (valid first, then rank score, ties: unpriced hot reason)"""
    cats = {}
    for s in run.get("stocks") or []:
        s.pop("rank", None)
        if s.get("category") and s.get("verdict") in ("valid", "wait"):
            s["rank_score"] = rank_score(s, run, cfg)
            cats.setdefault(s["category"], []).append(s)
    out = {}
    for c, items in cats.items():
        items.sort(key=lambda s: (s["verdict"] != "valid", -s["rank_score"], bool((s.get("hot") or {}).get("priced_in", True))))
        for i, s in enumerate(items, 1):
            s["rank"] = i
        out[c] = [s["tk"] for s in items[:3]]
    return out


def check(run: dict, cfg: dict | None = None) -> list[str]:
    cfg = cfg or load_config()
    errs = []
    m = run.get("meta") or {}
    for k in ("command", "amount"):
        if m.get(k) in (None, ""):
            errs.append(f"meta.{k} missing")
    if not (run.get("market") or {}).get("egx30"):
        errs.append("market.egx30 missing (run EGX.market())")
    wl = G.whitelist(SKILL_DIR)
    for s in run.get("stocks") or []:
        tk = s.get("tk", "?")
        if not str(s.get("verdict_by", "")).startswith("egx.py"):
            errs.append(f"{tk}: verdict not computed by egx.py (run: egx.py verdict run.json)")
            continue
        res, e = G.compute(dict(s), run, wl, cfg, fees_side)
        errs += e
        if res["verdict"] != s.get("verdict"):
            errs.append(f"{tk}: verdict {s.get('verdict')} does not match the rules ({res['verdict']}); re-run egx.py verdict")
        if s.get("verdict") == "valid" and (s.get("drop") or (s.get("mode") != "t0" and ((s.get("plan") or {}).get("rr") or 0) < 2)):
            errs.append(f"{tk}: verdict valid but the chart script dropped it ({s.get('drop')}) or R:R < 2")
        if s.get("verdict") not in ("dropped", "unchecked"):
            errs += [f"{tk}: {x}" for x in G.news_problems(s.get("news"), wl)]
    for c in run.get("catalysts") or []:
        errs += G.catalyst_problems(c, wl)
    for h in run.get("holdings") or []:
        errs += [f"holding {h.get('tk')}: {x}" for x in G.news_problems(h.get("news"), wl)]
    return errs


# ----------------------------------------------------------------- report (page: egx_page.py, recap video: egx_report.py)
import egx_report  # noqa: E402  (video recap only)
import egx_page  # noqa: E402
import egx_memory  # noqa: E402


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


def attach_screenshots(run: dict, folder: pathlib.Path, rid: str) -> None:
    """copy each chart screenshot next to the report (shots/) and give the page its picture"""
    import shutil
    shots = folder / "shots"
    for s in (run.get("stocks") or []) + (run.get("holdings") or []):
        for holder, key in ((s, "screenshot"), (s.get("t0") or {}, "screenshot")):
            src = holder.get(key)
            if not src or not pathlib.Path(src).is_file():
                continue
            shots.mkdir(exist_ok=True)
            ext = pathlib.Path(src).suffix.lower() or ".jpg"
            dst = shots / f"{rid}_{s.get('tk')}{'_T0' if holder is not s else ''}{ext}"
            if pathlib.Path(src).resolve() != dst.resolve():
                shutil.copy2(src, dst)
            s["_shot_file"] = f"shots/{dst.name}"
            s["_shot_uri"] = egx_page.img_uri(dst)
            s["_shot_time"] = _dt.datetime.fromtimestamp(pathlib.Path(src).stat().st_mtime).strftime("%H:%M")


def make_pdf(html_path: pathlib.Path) -> tuple[str | None, str | None]:
    import shutil, subprocess
    cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
             shutil.which("google-chrome") or "", shutil.which("chromium") or "", shutil.which("chrome") or "",
             r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
    chrome = next((c for c in cands if c and os.path.exists(c)), None)
    if not chrome:
        return None, "Chrome not found: PDF not made"
    pdf = html_path.with_suffix(".pdf")
    r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                        f"--print-to-pdf={pdf}", "--virtual-time-budget=4000", html_path.resolve().as_uri()],
                       capture_output=True, text=True, timeout=120)
    return (str(pdf), None) if pdf.exists() and pdf.stat().st_size > 1000 else (None, (r.stderr or "PDF failed")[-300:])


def drive_plan(folder: pathlib.Path, cfg: dict, files: list[pathlib.Path]) -> dict | None:
    """what Claude uploads to Drive: create new files, update the memory files already there"""
    import hashlib
    fid = cfg.get("drive_folder_id")
    if not fid:
        return None
    known = {}
    dj = folder / "drive.json"
    if dj.exists():
        known = json.loads(dj.read_text(encoding="utf-8"))
    out = []
    for f_ in files:
        if not f_ or not f_.exists():
            continue
        sha = hashlib.sha256(f_.read_bytes()).hexdigest()
        mime = {".html": "text/html", ".pdf": "application/pdf", ".jsonl": "text/plain"}.get(f_.suffix, "application/octet-stream")
        k = known.get(f_.name) or {}
        act = "skip" if k.get("id") and k.get("sha256") == sha else "replace" if k.get("id") else "create"
        out.append({"name": f_.name, "action": act, "old_file_id": k.get("id"), "mime": mime,
                    "file_ref": f"sha256:{sha}:{f_.resolve().as_posix()}"})
    return {"folder_id": fid, "files": out,
            "how": "create / replace: create_file(parentId=folder_id, title=name, base64Content=file_ref, contentMimeType=mime,"
                   " disableConversionToGoogleType=true), then for replace trash_file(old_file_id) (update_file cannot change content);"
                   " then egx.py drive-record NAME NEW_FILE_ID. skip: already up to date."}


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
    errs = check(run, cfg)
    if errs:  # no --force: a report is only built from a run that passes every rule
        print("run file problems (fix them, then run egx.py verdict and report again):\n - " + "\n - ".join(errs), file=sys.stderr)
        sys.exit(2)
    if "allocation" not in run or a.reallocate:
        allocate(run, cfg)
    folder = reports_dir(cfg, a.out)
    name = report_name(run, cfg)
    rid = name.rsplit(".", 1)[0]
    attach_screenshots(run, folder, rid)
    counts = egx_memory.save_run(folder, run, name)
    out = folder / name
    out.write_text(egx_page.build_html(run, cfg, name, VERSION, counts), encoding="utf-8")
    idx = update_index(folder, index_row(run, name))
    res = {"report": str(out), "index": str(idx), "bytes": out.stat().st_size, "memory": counts}
    pdf = None
    if not a.no_pdf:
        pdf, perr = make_pdf(out)
        res["pdf"] = pdf
        if perr:
            res["pdf_error"] = perr
    if a.video:
        vd = folder / "video" / rid
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "index.html").write_text(recap_composition(run, cfg), encoding="utf-8")
        res["video_project"] = str(vd)
        mp4 = folder / (rid + ".mp4")
        res["render"] = f'cd "{vd}" && npx hyperframes render --output "{mp4}"'
    plan = drive_plan(folder, cfg, [out, pathlib.Path(pdf) if pdf else None] + [folder / f_ for f_ in egx_memory.FILES])
    if plan:
        res["drive"] = plan
    for s in (run.get("stocks") or []) + (run.get("holdings") or []):
        for k in ("_shot_uri", "_shot_time", "screenshot_b64"):
            s.pop(k, None)
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


def cmd_recall(a, cfg):
    print(egx_memory.recall(reports_dir(cfg, a.dir), a.ticker, a.last))


def cmd_news(a, cfg):
    print(egx_memory.news(reports_dir(cfg, a.dir), a.ticker, a.since, a.limit))


def cmd_runs(a, cfg):
    print(egx_memory.runs(reports_dir(cfg, a.dir), a.command, a.since, a.last))


def cmd_outcome(a, cfg):
    print(egx_memory.set_outcome(reports_dir(cfg, a.dir), a.run, a.ticker, a.result, a.date, a.note))


def cmd_open(a, cfg):
    print(egx_memory.open_lines(reports_dir(cfg, a.dir)))


def cmd_drive_record(a, cfg):
    import hashlib
    folder = reports_dir(cfg, a.dir)
    dj = folder / "drive.json"
    known = json.loads(dj.read_text(encoding="utf-8")) if dj.exists() else {}
    f_ = folder / a.name
    known[a.name] = {"id": a.file_id, "sha256": hashlib.sha256(f_.read_bytes()).hexdigest() if f_.exists() else None,
                     "at": now_local(cfg).strftime("%Y-%m-%dT%H:%M")}
    dj.write_text(json.dumps(known, indent=1), encoding="utf-8")
    print(f"{a.name} -> Drive {a.file_id}")


def cmd_check(a, cfg):
    run = read_json(a.run)
    errs = check(run, cfg)
    for s in run.get("stocks") or []:
        if s.get("gates"):
            print(G.checklist_line(s.get("tk", "?"), {"verdict": s.get("verdict"), "gates": [(g["gate"], g["ok"], g["note"]) for g in s["gates"]], "reasons": s.get("auto_reasons")}))
    print("OK" if not errs else "\n".join(errs))
    sys.exit(1 if errs else 0)


def cmd_verdict(a, cfg):
    run = read_json(a.run)
    lines, errs = verdicts(run, cfg)
    write_json(a.run, run)
    print("\n".join(lines))
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(1)


def cmd_config(a, cfg):
    print(json.dumps(cfg, ensure_ascii=False, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="egx.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("fees"); p.add_argument("value"); p.set_defaults(fn=cmd_fees)
    p = sp.add_parser("allocate"); p.add_argument("run"); p.set_defaults(fn=cmd_allocate)
    p = sp.add_parser("report"); p.add_argument("run"); p.add_argument("--out"); p.add_argument("--video", action="store_true"); p.add_argument("--render", action="store_true", help="with --video: render the MP4 now (needs Node + Chrome)")
    p.add_argument("--reallocate", action="store_true"); p.add_argument("--no-pdf", action="store_true"); p.set_defaults(fn=cmd_report)
    p = sp.add_parser("recall"); p.add_argument("ticker"); p.add_argument("--last", type=int, default=5); p.add_argument("--dir"); p.set_defaults(fn=cmd_recall)
    p = sp.add_parser("news"); p.add_argument("ticker", nargs="?"); p.add_argument("--since"); p.add_argument("--limit", type=int, default=20); p.add_argument("--dir"); p.set_defaults(fn=cmd_news)
    p = sp.add_parser("runs"); p.add_argument("--command"); p.add_argument("--since"); p.add_argument("--last", type=int, default=10); p.add_argument("--dir"); p.set_defaults(fn=cmd_runs)
    p = sp.add_parser("outcome"); p.add_argument("run"); p.add_argument("ticker"); p.add_argument("result", choices=["target", "stop", "expired", "time", "manual"])
    p.add_argument("date"); p.add_argument("--note"); p.add_argument("--dir"); p.set_defaults(fn=cmd_outcome)
    p = sp.add_parser("open"); p.add_argument("--dir"); p.set_defaults(fn=cmd_open)
    p = sp.add_parser("drive-record"); p.add_argument("name"); p.add_argument("file_id"); p.add_argument("--dir"); p.set_defaults(fn=cmd_drive_record)
    p = sp.add_parser("search"); p.add_argument("--ticker"); p.add_argument("--command"); p.add_argument("--since")
    p.add_argument("--verdict", choices=["valid", "wait", "not_valid"]); p.add_argument("--limit", type=int, default=30); p.add_argument("--dir"); p.set_defaults(fn=cmd_search)
    p = sp.add_parser("read"); p.add_argument("file"); p.add_argument("--ticker"); p.add_argument("--section"); p.add_argument("--dir")
    p.add_argument("--compact", action="store_true"); p.set_defaults(fn=cmd_read)
    p = sp.add_parser("history"); p.add_argument("ticker"); p.add_argument("--last", type=int, default=10); p.add_argument("--dir"); p.set_defaults(fn=cmd_recall)  # old name
    p = sp.add_parser("check"); p.add_argument("run"); p.set_defaults(fn=cmd_check)
    p = sp.add_parser("verdict"); p.add_argument("run"); p.set_defaults(fn=cmd_verdict)
    p = sp.add_parser("config"); p.set_defaults(fn=cmd_config)
    a = ap.parse_args(argv)
    a.fn(a, load_config())


if __name__ == "__main__":
    main()
