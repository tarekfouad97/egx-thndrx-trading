"""Gates and verdicts for the EGX skills (standard library only).

Every deep-checked stock passes 8 gates, each proven by a receipt the page script or a tool
wrote, never by Claude's word:
  open -> analyse -> news -> draw -> verify -> screenshot -> steps -> verdict
"steps" is the atomic-step ledger (egx_steps.py): every atomic step of the check is recorded.
The verdict is computed here from the receipts and the data. Claude may only downgrade it
(stock.override = {"verdict": "wait"|"not_valid", "reason": "..."}), never upgrade it.
"""
from __future__ import annotations

import datetime as _dt
import math
import pathlib
import re
from urllib.parse import urlparse

GATES = ["open", "analyse", "news", "draw", "verify", "screenshot", "steps", "verdict"]
RANK = {"valid": 0, "wait": 1, "not_valid": 2, "dropped": 3, "unchecked": 4}
ICON = {"valid": "✅", "wait": "⏳", "not_valid": "❌", "dropped": "❌", "unchecked": "·"}
SWING_SETUPS = ("pullback-at-support", "breakout-retest")
CORPORATE = ("merger", "acquisition", "tender offer", "capital increase", "contract")
ARABIC = re.compile(r"[؀-ۿ]")
SHOT_MAX_AFTER_VERIFY_S = 30 * 60


# ----------------------------------------------------------------- news whitelist
def whitelist(skill_dir: pathlib.Path) -> dict:
    """{domain: (source, tier)} parsed from references/news-sources.md (single source of truth)."""
    out, tier = {}, None
    p = skill_dir / "references" / "news-sources.md"
    for line in p.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not cells[0] or cells[0].startswith("-") or cells[0] == "Tier":
            continue
        m = re.match(r"(\d)", cells[0])
        if m:
            tier = int(m.group(1))
        if tier is None:
            continue
        for d in re.split(r"[,\s]+", cells[2]):
            if "." in d:
                out[d.lower()] = (cells[1], tier)
    return out


def source_of(url: str, wl: dict):
    host = (urlparse(url or "").hostname or "").lower()
    for d, v in wl.items():
        if host == d or host.endswith("." + d):
            return d, v[0], v[1]
    return None, None, None


def _date(s):
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------- export checksum
def _fx(x) -> str:
    if x is None:
        return "-"
    if x is True:
        return "1"
    if x is False:
        return "0"
    return f"{x:.4f}" if isinstance(x, (int, float)) else str(x)


def sig_of(s: dict) -> str:
    """the same checksum egx_chart.js (sigOf) puts on every exported stock: the numbers that decide money and the
    receipt times. If run.json was retyped with a different price, the two no longer match."""
    p, rc, T = s.get("plan") or {}, s.get("receipts") or {}, s.get("t0") or {}
    tp, tr = T.get("plan") or {}, T.get("receipts") or {}
    g = lambda d, k: (d.get(k) or {})
    a = "|".join(_fx(x) for x in [
        s.get("tk"), s.get("last"), p.get("entry"), p.get("stop"), p.get("target"), p.get("target2"), p.get("rr"), p.get("maxEntry"), s.get("drop"),
        (s.get("score") or {}).get("total"), g(rc, "open").get("at"), g(rc, "analyse").get("at"), g(rc, "draw").get("at"), g(rc, "draw").get("made"),
        g(rc, "verify").get("at"), g(rc, "verify").get("ok"), tp.get("entry"), tp.get("stop"), tp.get("target"), T.get("drop"),
        g(tr, "analyse").get("at"), g(tr, "draw").get("at"), g(tr, "verify").get("at"), g(tr, "verify").get("ok")])
    h1, h2 = 0x811C9DC5, 0x01000193
    for ch in a:
        c = ord(ch)
        h1 = ((h1 ^ c) * 16777619) & 0xFFFFFFFF
        h2 = ((((h2 + c) & 0xFFFFFFFF) ^ (h2 >> 13)) * 2246822519) & 0xFFFFFFFF
    return f"{h1:08x}{h2:08x}"


def sig_problem(s: dict):
    if not s.get("sig"):
        return "no export checksum (sig): paste the stock exactly as EGX.exportToPage wrote it (page script 3.2)"
    if s["sig"] != sig_of(s):
        return "export checksum mismatch: a price, the drop or a receipt in run.json differs from what the page script exported (export again, paste unchanged)"
    return None


def plan_problem(p):
    values = [p.get(k) for k in ("stop", "entry", "target")]
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
        return "plan needs finite numeric stop, entry and target"
    if not 0 < values[0] < values[1] < values[2]:
        return "plan must satisfy 0 < stop < entry < target"
    return None


def net_rr(p: dict, run: dict, cfg: dict, fees_side):
    """R:R after fees on the run amount (or EGP 10,000)"""
    e, st, tg = p.get("entry"), p.get("stop"), p.get("target")
    if not (e and st and tg and fees_side) or e <= st:
        return None
    q = max(1, math.floor(float((run.get("meta") or {}).get("amount") or 10000) / e))
    fb = fees_side(e * q, cfg)
    return round(((tg - e) * q - fb - fees_side(tg * q, cfg)) / ((e - st) * q + fb + fees_side(st * q, cfg)), 2)


# ----------------------------------------------------------------- gates
def _r(s: dict, t0: bool) -> dict:
    if t0:
        return ((s.get("t0") or {}).get("receipts")) or {}
    return s.get("receipts") or {}


def news_problems(items, wl) -> list[str]:
    errs = []
    for n in items or []:
        title = (n.get("title") or n.get("url") or "")[:40]
        dom, src, tier = source_of(n.get("url"), wl)
        if not n.get("url") or not _date(n.get("date")):
            errs.append(f"news item without url or YYYY-MM-DD date: {title}")
        elif not dom:
            errs.append(f"news source not on the whitelist: {n.get('url')}")
        elif n.get("tier") not in (None, tier):
            errs.append(f"news tier {n.get('tier')} wrong for {dom} (tier {tier}): {title}")
        if dom and not n.get("opened") and not (dom == "bloomberg.com" and n.get("paywalled")):
            errs.append(f"news item not opened (WebFetch) and dated from the page: {title}")
    return errs


def gates(s: dict, run: dict, wl: dict, t0: bool = False) -> list[tuple]:
    """[(gate, ok, note)] for gates 1-6. Gate 7 (verdict) is added by compute_verdict."""
    tk, r, out = s.get("tk"), _r(s, t0), []
    o = (s.get("receipts") or {}).get("open") if t0 else r.get("open")
    if not o:
        out.append(("open", False, "no open receipt (EGX.open / EGX.deep)"))
    elif o.get("tk") != tk:
        out.append(("open", False, f"chart opened {o.get('tk')}, not {tk}"))
    elif not (o.get("headerMatch") or str(o.get("title") or "").upper() == tk):
        out.append(("open", False, f"neither the chart header nor the chart title shows {tk} (title: {o.get('title')})"))
    else:
        out.append(("open", True, ""))
    a = r.get("analyse")
    ok_a = bool(a and str(a.get("version", "")).startswith("3.") and (t0 or (a.get("bars") or 0) >= 60) and a.get("titleMatch", True))
    sp = sig_problem(s) if ok_a else None
    out.append(("analyse", ok_a and not sp, "" if ok_a and not sp else sp or ("no analysis receipt from page script v3" if not a else "analysis receipt incomplete")))
    q = [x for x in s.get("news_queries") or [] if (x.get("query") if isinstance(x, dict) else x)]
    qs = [(x.get("query") if isinstance(x, dict) else x) for x in q]
    nerr = news_problems(s.get("news"), wl)
    ok_n = len(qs) >= 2 and any(ARABIC.search(x) for x in qs) and any(not ARABIC.search(x) for x in qs) and not nerr
    note = f"{len(qs)} queries, {len(s.get('news') or [])} items"
    if len(qs) < 2 or not any(ARABIC.search(x) for x in qs) or all(ARABIC.search(x) for x in qs):
        note = f"needs 2+ searches incl. one Arabic and one English (has {len(qs)})"
    elif nerr:
        note = nerr[0]
    out.append(("news", ok_n, note))
    d = r.get("draw")
    ok_d = bool(d and d.get("made") and d.get("made") == d.get("planned") and not d.get("failed"))
    if ok_d and not t0:
        st = d.get("studies") or {}
        if not st.get("skipped") and not (st.get("ma50") and st.get("ma200")):
            ok_d, dnote = False, "MA50/MA200 not added"
        else:
            need = len([e for e in s.get("red_events") or [] if _date(e.get("date"))])
            have = sum(1 for k in d.get("kinds") or [] if k == "event")
            dnote = "" if have >= need else f"{need - have} red-event date(s) not drawn"
            ok_d = have >= need
    else:
        dnote = "nothing drawn" if not d else f"drew {d.get('made')}/{d.get('planned')} {d.get('failed') or ''}".strip()
    out.append(("draw", ok_d, f"{d.get('made')} marks" if ok_d else dnote))
    v = r.get("verify")
    ok_v = bool(v and v.get("ok") and d and v.get("at", 0) >= d.get("at", 0))
    out.append(("verify", ok_v, "" if ok_v else "not verified after the last draw" if v and v.get("ok") else
                "; ".join((v or {}).get("problems") or ["EGX.verifyChart not run"])[:160]))
    shot = (s.get("t0") or {}).get("screenshot") if t0 else s.get("screenshot")
    out.append(("screenshot",) + _shot_ok(shot, v))
    return out


def _shot_ok(path, v):
    if not path:
        return False, "no screenshot"
    p = pathlib.Path(path)
    if not p.exists():
        return False, f"screenshot file not found: {path}"
    head = p.read_bytes()[:8]
    if not (head.startswith(b"\xff\xd8") or head.startswith(b"\x89PNG")):
        return False, "screenshot is not a JPEG/PNG"
    if p.stat().st_size < 8000:
        return False, "screenshot too small to be the chart"
    if not v or not v.get("ok"):
        return False, "chart not verified, so the screenshot proves nothing"
    dt = p.stat().st_mtime - v["at"] / 1000
    if dt < -1:
        return False, "screenshot taken BEFORE the chart was verified"
    if dt > SHOT_MAX_AFTER_VERIFY_S:
        return False, f"screenshot taken {int(dt // 60)} min after the verify (chart may have changed)"
    return True, ""


# ----------------------------------------------------------------- verdicts
def _expiry(run: dict) -> _dt.date:
    td = _date((run.get("meta") or {}).get("trading_day")) or _date((run.get("meta") or {}).get("created")) or _dt.date.today()
    return td + _dt.timedelta(days=7)  # the order is valid about one trading week


def _today(run):
    return _date((run.get("meta") or {}).get("created")) or _date((run.get("meta") or {}).get("trading_day")) or _dt.date.today()


def swing_verdict(s: dict, run: dict, wl: dict, cfg: dict | None = None, fees_side=None) -> dict:
    p, rs, tr = s.get("plan") or {}, s.get("rs") or {}, s.get("trend") or {}
    regime = (((run.get("market") or {}).get("egx30") or {}).get("regime")) or "unknown"
    if s.get("drop"):
        return {"verdict": "dropped", "reasons": [f"chart script drop: {s['drop']}"], "gates": []}
    if s.get("quick"):
        return {"verdict": "unchecked", "reasons": ["quick scan only (not deep-checked)"], "gates": []}
    if plan_problem(p):
        return {"verdict": "wait", "reasons": [plan_problem(p)], "wait_for": "recompute a valid price plan", "gates": gates(s, run, wl)}
    G = gates(s, run, wl)
    failed = [g for g in G if not g[1]]
    reasons, waits = [], []
    if failed:
        return {"verdict": "wait", "reasons": [f"gate {g[0]} failed: {g[2]}" for g in failed],
                "wait_for": "fix gate " + ", ".join(g[0] for g in failed) + " and re-check", "gates": G}
    today, exp = _today(run), _expiry(run)
    news = s.get("news") or []
    material = [n for n in news if n.get("impact") == "-" and n.get("material")]
    if material:
        return {"verdict": "not_valid", "reasons": [f"negative material news {n.get('date')}: {n.get('title', '')[:80]}" for n in material], "gates": G}
    if tr.get("daily") == "down" and tr.get("weekly") == "down" and (rs.get("rs20") or 0) < 0 and (rs.get("rs60") or 0) < 0:
        return {"verdict": "not_valid", "reasons": ["daily and weekly trend down, RS20 and RS60 negative"], "gates": G}
    if p.get("type") not in SWING_SETUPS:
        waits.append(f"price reaches the entry {p.get('entry')} ({p.get('type')}, {p.get('entryDistATR')} ATR away)")
    if p.get("type") == "breakout-retest" and (p.get("entryDistATR") or 0) > 1:
        waits.append(f"price comes back within 1 ATR of the entry {p.get('entry')} (now {p.get('entryDistATR')} ATR above it)")
    lp = s.get("livePrice")
    if p.get("type") == "pullback-at-support" and lp and p.get("maxEntry") and lp > p["maxEntry"]:
        waits.append(f"price is at or under the max entry {p['maxEntry']} (now {lp})")
    # a valid swing buy is with the trend and not weaker than the index, in every regime
    if tr.get("daily") == "down":
        waits.append("the daily trend stops being down (a higher high and a higher low)")
    if rs.get("rs20") is None:
        waits.append("relative strength vs EGX30 is known (EGX.market() before the analysis)")
    elif rs["rs20"] < 0:
        waits.append(f"RS20 vs EGX30 is not negative (now {rs['rs20']})")
    nr = net_rr(p, run, cfg or {}, fees_side) if cfg else None
    if nr is not None:
        p["rr_net"] = nr
        need = float((cfg or {}).get("min_net_rr") or 2.0)
        if nr < need:
            waits.append(f"R:R after fees is at least {need:g} (now {nr}; gross {p.get('rr')})")
    for e in s.get("red_events") or []:
        d = _date(e.get("date"))
        if d is None:
            waits.append(f"the {e.get('type')} date is confirmed (unknown now: gap risk)")
        elif today <= d <= exp:
            waits.append(f"{e.get('type')} on {d} passes")
    fresh_neg = [n for n in news if n.get("impact") == "-" and _date(n.get("date")) and 0 <= (today - _date(n["date"])).days <= 2]
    if fresh_neg:
        waits.append("fresh negative news is digested: " + (fresh_neg[0].get("title") or "")[:60])
    band = (s.get("page") or {}).get("band")
    if band and len(band) == 2:
        out = [k for k in ("entry", "stop", "target") if p.get(k) is not None and not (band[0] <= p[k] <= band[1])]
        if "entry" in out:
            waits.append(f"entry {p.get('entry')} inside today's price band {band[0]}-{band[1]}")
        elif out:
            reasons.append(f"{', '.join(out)} outside today's band {band[0]}-{band[1]} (place later)")
    else:
        waits.append("today's price band is confirmed")
    if regime == "Down" and not ((rs.get("rs20") or 0) > 0 and (rs.get("rs60") or 0) > 0):
        waits.append("EGX30 leaves Down or RS20 and RS60 turn positive")
    if regime == "unknown":
        waits.append("EGX30 regime is read (EGX.market())")
    if waits:
        return {"verdict": "wait", "reasons": reasons + [f"waiting: {w}" for w in waits], "wait_for": "; ".join(waits), "gates": G}
    return {"verdict": "valid", "reasons": reasons + [f"{p.get('type')} R:R {p.get('rr')}, all rules pass"], "gates": G}


T0_SIGNAL_MAX_AGE_S = 5 * 60   # a 5-minute read older than this is not a signal any more


def t0_signal(s: dict, run: dict, wl: dict, cfg: dict, fees_side, now_ms: int) -> dict:
    """The fast T0 answer (egx.py t0-signal): every T0 rule and gate except the screenshot, which is paperwork made after
    the answer, on a 5-minute read that is at most 5 minutes old. Returns the verdict dict plus age_s and valid_until_ms."""
    at = (((s.get("t0") or {}).get("receipts") or {}).get("analyse") or {}).get("at") or 0
    res = t0_verdict(s, run, wl, cfg, fees_side, signal=True)
    age = (now_ms - at) / 1000 if at else None
    res["age_s"], res["valid_until_ms"] = age, (at + T0_SIGNAL_MAX_AGE_S * 1000 if at else None)
    if res["verdict"] == "valid" and (age is None or age > T0_SIGNAL_MAX_AGE_S or age < -60):
        res["verdict"] = "wait"
        res["wait_for"] = f"a fresh 5-minute read (this one is {'of unknown age' if age is None else str(int(age // 60)) + ' min old'}; limit {T0_SIGNAL_MAX_AGE_S // 60}): run EGX.intraday again"
        res["reasons"] = ["stale: " + res["wait_for"]]
    return res


def t0_verdict(s: dict, run: dict, wl: dict, cfg: dict, fees_side, signal: bool = False) -> dict:
    T, meta = s.get("t0") or {}, run.get("meta") or {}
    p = T.get("plan") or {}
    if T.get("drop"):
        return {"verdict": "dropped", "reasons": [f"T0 drop: {T['drop']}"], "gates": []}
    if plan_problem(p):
        return {"verdict": "wait", "reasons": [plan_problem(p)], "wait_for": "recompute a valid intraday plan", "gates": gates(s, run, wl, t0=True)}
    G = gates(s, run, wl, t0=True)
    failed = [g for g in G if not g[1] and not (signal and g[0] == "screenshot")]
    if failed:
        return {"verdict": "wait", "reasons": [f"gate {g[0]} failed: {g[2]}" for g in failed],
                "wait_for": "fix gate " + ", ".join(g[0] for g in failed), "gates": G}
    day = _date((T.get("session") or {}).get("day")) or _today(run)
    for e in s.get("red_events") or []:
        if _date(e.get("date")) == day:
            return {"verdict": "not_valid", "reasons": [f"{e.get('type')} today ({day})"], "gates": G}
    if [n for n in s.get("news") or [] if n.get("impact") == "-" and n.get("material")]:
        return {"verdict": "not_valid", "reasons": ["negative material news"], "gates": G}
    reasons, waits = [], []
    hm = str(meta.get("created") or "")[11:16]
    at = ((T.get("receipts") or {}).get("analyse") or {}).get("at")
    if at:  # the browser's own time of the 5-minute read, in Cairo
        try:
            from zoneinfo import ZoneInfo
            observed = _dt.datetime.fromtimestamp(at / 1000, ZoneInfo("Africa/Cairo"))
            hm = observed.strftime("%H:%M")
            if day != observed.date():
                waits.append("intraday bars belong to the current Cairo session")
        except Exception:
            pass
    wd = day.weekday()  # Mon=0 ... Sun=6; EGX trades Sun-Thu
    if wd in (4, 5):
        waits.append("an EGX session (Sunday-Thursday)")
    if not hm or not ("10:15" <= hm <= "13:30"):
        waits.append(f"the entry window 10:15-13:30 (data time {hm or 'unknown'})")
    if not s.get("t0_eligible"):
        waits.append("T0 eligibility confirmed (EGX segment list or the T0 option in ThndrX)")
    idx = ((run.get("market") or {}).get("egx30") or {})
    if (idx.get("chgToday") or 0) < 0 and not ((T.get("vsEGX30") or 0) > 0 and (T.get("last") or 0) > (T.get("vwap") or 0)):
        waits.append("the stock is above its VWAP and stronger than EGX30 today (EGX30 is down)")
    e, st, tg = p.get("entry"), p.get("stop"), p.get("target")
    if e and st and tg:
        q = max(1, math.floor(float(meta.get("amount") or 10000) / e))
        fb = fees_side(e * q, cfg)
        net_gain = (tg - e) * q - fb - fees_side(tg * q, cfg)
        net_loss = (e - st) * q + fb + fees_side(st * q, cfg)
        net_rr = round(net_gain / net_loss, 2) if net_loss > 0 else 0
        rt_pct = 100 * (fb + fees_side(tg * q, cfg)) / (e * q)
        p["rr_net"], p["fees_rt_pct"] = net_rr, round(rt_pct, 3)
        if net_rr < 1.5:
            return {"verdict": "dropped", "reasons": [f"net R:R {net_rr} < 1.5 after fees"], "gates": G}
        if (p.get("movePct") or 0) < 3 * rt_pct:
            return {"verdict": "dropped", "reasons": [f"move to target {p.get('movePct')}% < 3x round-trip fees {round(rt_pct, 2)}%"], "gates": G}
    if abs(p.get("entryDistATR5") or 0) > 0.5:
        waits.append(f"trigger: {p.get('trigger')}")
    if waits:
        return {"verdict": "wait", "reasons": reasons + [f"waiting: {w}" for w in waits], "wait_for": "; ".join(waits), "gates": G}
    return {"verdict": "valid", "reasons": [f"{p.get('setup')} R:R {p.get('rr')} gross / {p.get('rr_net')} net, exit by 14:10"], "gates": G}


def apply_override(s: dict, res: dict) -> list[str]:
    """Claude may only downgrade. Returns errors."""
    ov = s.get("override")
    if not ov:
        return []
    want = ov.get("verdict")
    if want not in ("wait", "not_valid"):
        return [f"{s.get('tk')}: override verdict must be wait or not_valid"]
    if not (ov.get("reason") or "").strip():
        return [f"{s.get('tk')}: override needs a reason"]
    if RANK[want] < RANK[res["verdict"]] or res["verdict"] in ("dropped", "unchecked"):
        return [f"{s.get('tk')}: override {want} would UPGRADE {res['verdict']} (not allowed)"]
    res["verdict"] = want
    res["reasons"] = res["reasons"] + [f"downgraded by Claude: {ov['reason']}"]
    if want == "wait":
        res["wait_for"] = ov.get("wait_for") or ov["reason"]
    return []


def compute(s: dict, run: dict, wl: dict, cfg: dict, fees_side, step_gate=None) -> tuple[dict, list[str]]:
    """step_gate(stock) -> (ok, note): the atomic-step ledger (egx_steps.stock_gate). Without a ledger the gate fails."""
    res = t0_verdict(s, run, wl, cfg, fees_side) if s.get("mode") == "t0" else swing_verdict(s, run, wl, cfg, fees_side)
    if res.get("gates"):
        ok, note = step_gate(s) if step_gate else (False, "no step ledger for this run (egx.py step start)")
        res["gates"] = res["gates"] + [("steps", ok, note)]
        if not ok and res["verdict"] in ("valid", "wait"):
            had = res.get("wait_for") if res["verdict"] == "wait" else None
            res["verdict"] = "wait"
            res["reasons"] = [f"gate steps failed: {note}"] + [r for r in res.get("reasons") or [] if "all rules pass" not in r]
            res["wait_for"] = "complete the atomic steps and re-check" + (f"; {had}" if had else "")
    errs = apply_override(s, res)
    if res.get("gates"):
        res["gates"] = res["gates"] + [("verdict", not errs, "computed by egx.py" if not errs else errs[0])]
    return res, errs


def checklist_line(tk: str, res: dict) -> str:
    v = res["verdict"]
    if not res.get("gates"):
        return f"{tk:7} {ICON[v]} {v}  ({'; '.join(res.get('reasons') or [])})"
    marks = " ".join(("✔ " if ok else "✘ ") + g + (f" {note}" if ok and g in ("news", "draw") and note else "") for g, ok, note in res["gates"])
    fails = [f"{g}: {note}" for g, ok, note in res["gates"] if not ok]
    why = res.get("wait_for") if v == "wait" else "; ".join(res.get("reasons") or [])[:200] if v != "valid" else ""
    return f"{tk:7} {marks}  → {ICON[v]} {v}" + (f" ({why})" if why and not fails else "") + (f"\n        ✘ " + "\n        ✘ ".join(fails) if fails else "")


def catalyst_problems(c: dict, wl: dict) -> list[str]:
    tk, errs = c.get("tk"), []
    srcs = c.get("sources") or ([{"url": c.get("url"), "date": c.get("date"), "opened": c.get("opened")}] if c.get("url") else [])
    if not srcs:
        return [f"catalyst {tk}: no sources"]
    errs += [f"catalyst {tk}: {e}" for e in news_problems(srcs, wl)]
    if c.get("status", "confirmed") == "confirmed" and (c.get("type") or "") in CORPORATE:
        tiers = {}
        for x in srcs:
            dom, _, t = source_of(x.get("url"), wl)
            if dom:
                tiers.setdefault(t, set()).add(dom)
        if not tiers.get(1) and len(tiers.get(2, ())) < 2:
            errs.append(f"catalyst {tk}: a confirmed {c.get('type')} needs an EGX disclosure or two Tier-2 sources; else status rumour")
    return errs
