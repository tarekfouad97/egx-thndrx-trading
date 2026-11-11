"""
egx_memory.py - Claude's memory of every run, kept small so recalling it costs few tokens.

Three files next to the reports (one JSON object per line, rewritten in place, never duplicated):
  history.jsonl  one line per stock per run (verdict, plan, levels with dates, reasons, news ids, outcome)
  news.jsonl     one line per news item, deduplicated by URL (so old stories are not searched again)
  runs.jsonl     one line per run (mode, regime, money, picks)
Claude reads them with `egx.py recall / news / runs`, never the HTML. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

FILES = ("history.jsonl", "news.jsonl", "runs.jsonl")


def _load(p: pathlib.Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _save(p: pathlib.Path, rows: list[dict]) -> None:
    p.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")


def news_id(url: str) -> str:
    return hashlib.sha1((url or "").strip().lower().encode()).hexdigest()[:10]


def _r(x, d=2):
    try:
        return round(float(x), d)
    except (TypeError, ValueError):
        return None


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


def stock_line(s: dict, run: dict, fname: str, row: dict | None) -> dict:
    meta = run.get("meta") or {}
    eg = ((run.get("market") or {}).get("egx30") or {})
    t0 = s.get("mode") == "t0"
    p = ((s.get("t0") or {}).get("plan") if t0 else s.get("plan")) or {}
    z = (s.get("zones") or {})
    sup = z.get("support") or {}
    res = (z.get("resistance") or [{}])[0] or {}
    tr, rs = s.get("trend") or {}, s.get("rs") or {}
    last_touch = (sup.get("touches") or [""])[-1][:10] if sup.get("touches") else None
    why = (s.get("reasons") or [])[:3] or [x for x in (s.get("auto_reasons") or []) if not x.startswith("gate ")][:3]
    line = {
        "run": fname.rsplit(".", 1)[0], "date": (meta.get("created") or "")[:16], "day": meta.get("trading_day"),
        "cmd": meta.get("command"), "cat": s.get("category"), "rank": s.get("rank"), "tk": s.get("tk"),
        "v": s.get("verdict"), "wait_for": s.get("wait_for"), "drop": s.get("drop"),
        "last": s.get("last"), "chg": s.get("chg"),
        "plan": _clean({"type": p.get("type") or p.get("setup"), "e": p.get("entry"), "s": p.get("stop"), "t": p.get("target"),
                        "t2": p.get("target2"), "rr": p.get("rr"), "rr_net": p.get("rr_net"), "stopATR": p.get("stopATR") or p.get("stopATR5"),
                        "dist": p.get("entryDistATR"), "trigger": p.get("trigger"), "exitBy": p.get("exitBy")}),
        "sup": [sup.get("lo"), sup.get("hi"), sup.get("n"), last_touch] if sup else None,
        "res": [res.get("lo"), res.get("hi")] if res else None,
        "trend": f'{tr.get("daily")}/{tr.get("weekly")}' if tr else None,
        "rs": [rs.get("rs20"), rs.get("rs60")] if rs.get("rs20") is not None else None,
        "regime": eg.get("regime"), "score": (s.get("score") or {}).get("total"),
        "why": why, "news": [news_id(n.get("url")) for n in s.get("news") or [] if n.get("url")],
        "red": [f'{e.get("type")}@{e.get("date") or "unknown"}' for e in s.get("red_events") or []],
        "gates_failed": [g["gate"] for g in s.get("gates") or [] if not g.get("ok")],
        "steps_failed": [b["id"] for g in (run.get("steps") or {}).get("groups") or [] if g.get("tk") == s.get("tk") for b in g.get("bad") or []],
        "alloc": _clean({"sh": (row or {}).get("shares"), "egp": (row or {}).get("value"), "order": (row or {}).get("order")}) if row and row.get("shares") else None,
        "shot": s.get("_shot_file"),
        "outcome": None,
    }
    return _clean(line) | {"outcome": None}


def holding_line(h: dict, run: dict, fname: str) -> dict:
    meta = run.get("meta") or {}
    return _clean({"run": fname.rsplit(".", 1)[0], "date": (meta.get("created") or "")[:16], "cmd": meta.get("command"),
                   "tk": h.get("tk"), "pos": h.get("action") or "hold", "qty": h.get("qty"), "avg": h.get("avgPrice"),
                   "last": h.get("price"), "pnlPct": h.get("pnlPct"), "stop": h.get("stop"), "target": h.get("target"),
                   "why": (h.get("reasons") or [])[:2], "news": [news_id(n.get("url")) for n in h.get("news") or [] if n.get("url")]})


def news_lines(run: dict) -> list[dict]:
    created = ((run.get("meta") or {}).get("created") or "")[:10]
    out = []
    def add(n, tks):
        if not n.get("url"):
            return
        out.append(_clean({"id": news_id(n["url"]), "tks": sorted(set(t for t in tks if t)), "date": n.get("date"), "src": n.get("source"),
                           "tier": n.get("tier"), "imp": n.get("impact"), "mat": n.get("material") or None, "title": n.get("title"),
                           "sum": n.get("summary"), "url": n["url"], "seen": created}))
    for s in (run.get("stocks") or []) + (run.get("holdings") or []):
        for n in s.get("news") or []:
            add(n, [s.get("tk")])
        for e in s.get("red_events") or []:
            add({**e, "title": f'{(e.get("type") or "event")} on {e.get("date") or "unknown"}', "impact": "-"}, [s.get("tk")])
    for c in run.get("catalysts") or []:
        for src in c.get("sources") or ([{"url": c.get("url"), "date": c.get("date"), "source": c.get("source")}] if c.get("url") else []):
            add({**src, "title": c.get("summary"), "impact": c.get("direction"), "summary": f'{c.get("type")} · {c.get("status", "confirmed")}'}, [c.get("tk")])
    for n in ((run.get("market") or {}).get("macro") or []):
        add(n, ["MARKET"])
    return out


def run_line(run: dict, fname: str) -> dict:
    meta, al = run.get("meta") or {}, run.get("allocation") or {}
    eg = ((run.get("market") or {}).get("egx30") or {})
    picks = {}
    for s in run.get("stocks") or []:
        if s.get("verdict") in ("valid", "wait", "not_valid"):
            picks.setdefault(s.get("category") or "checked", []).append(f'{s.get("tk")}:{s.get("verdict")}')
    return _clean({"run": fname.rsplit(".", 1)[0], "date": (meta.get("created") or "")[:16], "day": meta.get("trading_day"),
                   "cmd": meta.get("command"), "regime": eg.get("regime"), "egx30": eg.get("last"), "amount": meta.get("amount"),
                   "deployed": al.get("deployed"), "cash_left": al.get("cash_left"), "picks": picks,
                   "positions": [f'{h.get("tk")}:{h.get("action") or "hold"}' for h in run.get("holdings") or [] if not h.get("is_fund")],
                   "summary": (meta.get("summary") or "")[:240], "t0": meta.get("t0_status")})


def save_run(folder: pathlib.Path, run: dict, fname: str) -> dict:
    """write / replace this run's lines in the three files; keeps outcomes already recorded"""
    rid = fname.rsplit(".", 1)[0]
    rows = {r["tk"]: r for r in (run.get("allocation") or {}).get("rows") or []}
    hist_p, news_p, runs_p = (folder / f for f in FILES)
    hist = _load(hist_p)
    old = {(h.get("run"), h.get("tk"), "pos" in h): h for h in hist if h.get("run") == rid}
    hist = [h for h in hist if h.get("run") != rid]
    new = []
    for s in run.get("stocks") or []:
        if s.get("verdict") == "unchecked":
            continue
        ln = stock_line(s, run, fname, rows.get(s.get("tk")))
        prev = old.get((rid, s.get("tk"), False))
        if prev and prev.get("outcome"):
            ln["outcome"] = prev["outcome"]
        new.append(ln)
    for h in run.get("holdings") or []:
        if not h.get("is_fund"):
            new.append(holding_line(h, run, fname))
    hist += new
    hist.sort(key=lambda h: (h.get("date") or "", h.get("tk") or ""))
    _save(hist_p, hist)
    news = {n["id"]: n for n in _load(news_p)}
    nl = news_lines(run)
    for n in nl:
        if n["id"] in news:
            keep = news[n["id"]]
            keep["tks"] = sorted(set(keep.get("tks", [])) | set(n.get("tks", [])))
            for k, v in n.items():
                keep.setdefault(k, v)
        else:
            news[n["id"]] = n
    _save(news_p, sorted(news.values(), key=lambda n: (n.get("date") or "", n["id"])))
    runs = [r for r in _load(runs_p) if r.get("run") != rid] + [run_line(run, fname)]
    runs.sort(key=lambda r: r.get("date") or "")
    _save(runs_p, runs)
    return {"stocks": len([x for x in new if "pos" not in x]), "positions": len([x for x in new if "pos" in x]), "news": len({n["id"] for n in nl})}


# ----------------------------------------------------------------- reading (compact text, not JSON, to save tokens)
def fmt_hist(h: dict, news_by_id: dict) -> str:
    if "pos" in h:
        return (f'{h.get("date", "")[:10]} {h.get("cmd")} POSITION {h["tk"]} {h["pos"]} qty {h.get("qty")} avg {h.get("avg")} last {h.get("last")}'
                f' P/L {h.get("pnlPct")}% stop {h.get("stop")}' + (f'\n   why: {" | ".join(h["why"])}' if h.get("why") else ""))
    p = h.get("plan") or {}
    head = (f'{h.get("date", "")[:10]} {h.get("cmd")}{" " + h["cat"] if h.get("cat") else ""}{" #" + str(h["rank"]) if h.get("rank") else ""}'
            f' {h["tk"]} {(h.get("v") or "").upper()}{" (" + h["drop"] + ")" if h.get("drop") else ""} last {h.get("last")}')
    if h.get("v") == "dropped":
        return head
    parts = [head]
    if p:
        parts.append(f'   plan {p.get("type")} E {p.get("e")} S {p.get("s")} T {p.get("t")} RR {p.get("rr")}'
                     + (f'/{p["rr_net"]} net' if p.get("rr_net") else "") + (f' trigger: {p["trigger"]}' if p.get("trigger") else ""))
    ctx = []
    if h.get("sup"):
        lo, hi, n, lt = (h["sup"] + [None] * 4)[:4]
        ctx.append(f"sup {lo}-{hi} x{n}" + (f" last {lt}" if lt else ""))
    if h.get("trend"):
        ctx.append(f'trend {h["trend"]}')
    if h.get("rs"):
        ctx.append(f'RS {h["rs"][0]}/{h["rs"][1]}')
    if h.get("regime"):
        ctx.append(h["regime"])
    if h.get("alloc"):
        ctx.append(f'{h["alloc"].get("sh")} sh {h["alloc"].get("egp")} EGP')
    if ctx:
        parts.append("   " + " | ".join(ctx))
    if h.get("wait_for"):
        parts.append(f'   waiting: {h["wait_for"]}')
    if h.get("why"):
        parts.append(f'   why: {" | ".join(h["why"])}')
    if h.get("red"):
        parts.append(f'   red: {", ".join(h["red"])}')
    if h.get("gates_failed"):
        parts.append(f'   failed gates: {", ".join(h["gates_failed"])}')
    if h.get("steps_failed"):
        parts.append(f'   atomic steps not done: {", ".join(h["steps_failed"])}')
    for i in h.get("news") or []:
        n = news_by_id.get(i)
        if n:
            parts.append(f'   news {n.get("date")} {n.get("src")}{" T" + str(n["tier"]) if n.get("tier") else ""} {n.get("imp") or ""} {n.get("title")}')
    parts.append(f'   outcome: {h.get("outcome") or "open"}')
    return "\n".join(parts)


def recall(folder: pathlib.Path, tk: str, last: int = 5) -> str:
    tk = tk.upper()
    hist = [h for h in _load(folder / "history.jsonl") if h.get("tk") == tk]
    if not hist:
        return f"no history for {tk}"
    news = {n["id"]: n for n in _load(folder / "news.jsonl")}
    shown = hist[-last:]
    return (f"{tk}: {len(hist)} records, showing the last {len(shown)}\n" + "\n".join(fmt_hist(h, news) for h in shown))


def news(folder: pathlib.Path, tk: str | None, since: str | None, limit: int = 20) -> str:
    rows = _load(folder / "news.jsonl")
    if tk:
        rows = [n for n in rows if tk.upper() in (n.get("tks") or [])]
    if since:
        rows = [n for n in rows if (n.get("date") or "") >= since]
    rows = rows[-limit:]
    if not rows:
        return "no news saved"
    return "\n".join(f'{n.get("date")} {",".join(n.get("tks") or [])} {n.get("src")}{" T" + str(n["tier"]) if n.get("tier") else ""} {n.get("imp") or "0"} {n.get("title")}'
                     f'{" (" + n["sum"] + ")" if n.get("sum") else ""} {n.get("url")}' for n in rows)


def runs(folder: pathlib.Path, command: str | None, since: str | None, last: int = 10) -> str:
    rows = _load(folder / "runs.jsonl")
    if command:
        rows = [r for r in rows if command.lower().replace(" ", "") in (r.get("cmd") or "").lower().replace(" ", "")]
    if since:
        rows = [r for r in rows if (r.get("date") or "") >= since]
    rows = rows[-last:]
    if not rows:
        return "no runs saved"
    out = []
    for r in rows:
        picks = " ".join(f'{k}[{",".join(v)}]' for k, v in (r.get("picks") or {}).items())
        out.append(f'{r.get("date")} {r.get("cmd")} {r.get("regime")} EGX30 {r.get("egx30")} amount {r.get("amount")} deployed {r.get("deployed")}'
                   f' {picks}' + (f' positions[{",".join(r["positions"])}]' if r.get("positions") else "") + f' {r["run"]}'
                   + (f'\n   {r["summary"]}' if r.get("summary") else ""))
    return "\n".join(out)


def set_outcome(folder: pathlib.Path, run_id: str, tk: str, result: str, date: str, note: str | None = None) -> str:
    p = folder / "history.jsonl"
    hist = _load(p)
    hit = 0
    for h in hist:
        if h.get("run") == run_id.rsplit(".", 1)[0] and h.get("tk") == tk.upper() and "pos" not in h:
            h["outcome"] = f"{result} {date}" + (f" ({note})" if note else "")
            hit += 1
    if not hit:
        return f"no history line for {tk} in {run_id}"
    _save(p, hist)
    return f"{tk} {run_id}: outcome = {result} {date}"


def open_lines(folder: pathlib.Path) -> str:
    """history lines still waiting for an outcome (for outcome tracking)"""
    rows = [h for h in _load(folder / "history.jsonl") if "pos" not in h and h.get("v") in ("valid", "wait") and not h.get("outcome")]
    if not rows:
        return "nothing open"
    return "\n".join(f'{h["run"]} {h["tk"]} {h["v"]} {h.get("date", "")[:10]} E {(h.get("plan") or {}).get("e")} S {(h.get("plan") or {}).get("s")} T {(h.get("plan") or {}).get("t")}'
                     f'{" T0" if (h.get("plan") or {}).get("exitBy") else ""}' for h in rows)
