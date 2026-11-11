"""Atomic-step ledger for the EGX skills (standard library only).

Every command is a list of steps, every step a list of atomic steps (references/steps.json).
This module keeps one append-only, hash-chained ledger per run (<run>.ledger.jsonl) and decides
what counts as done:
  auto   -> proven here from run.json, the page-script receipts, the call log and files on disk
  cmd    -> recorded by egx.py itself when that subcommand runs
  attest -> recorded by Claude with a written proof (shown in the report as stated, not proven)
Claude never writes or edits the ledger file; only egx.py does.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import time

import egx_gates as G

HERE = pathlib.Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
FINAL = ("done", "skipped", "failed")
AUTO_SKIP = ("dropped", "no-sheet", "no-drive-folder", "no-open-calls")
NEEDS_PROOF = ("sheets-off", "drive-off")
CHART_CHAIN = ("K2", "K4", "K5", "T2", "T4", "T5")   # a failure here makes the later chart steps of that ticker impossible
GENERIC = {"done", "ok", "okay", "yes", "completed", "complete", "checked", "true", "n/a", "na", "none", "تم", "تمام"}
SCRIPT_MM = "3.3"          # page script major.minor the receipts must come from
FRESH_SLACK_MS = 2000
MARKET_MAX_AGE_MS = 8 * 3600 * 1000
ACTIONS = ("exit", "sell", "partial", "tighten", "add", "hold")
REGIMES = ("Up", "Down", "Mixed")


# ----------------------------------------------------------------- manifest
_M = None


def manifest() -> dict:
    global _M
    if _M is None:
        m = json.loads((SKILL_DIR / "references" / "steps.json").read_text(encoding="utf-8"))
        in_block = {sid for b in m["blocks"].values() for sid in b}
        m["atom"] = {}
        for sid, st in m["steps"].items():
            for a in st["atoms"]:
                a["step"], a["scope"] = sid, "stock" if sid in in_block else "run"
                m["atom"][a["id"]] = a
        _M = m
    return _M


def state_dir() -> pathlib.Path:
    d = pathlib.Path(os.environ.get("EGX_STATE_DIR") or (pathlib.Path.home() / ".egx-thndrx"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def ledger_path(run_path) -> pathlib.Path:
    return pathlib.Path(run_path).with_suffix(".ledger.jsonl")


def base(tk) -> str:
    """ledger key -> ticker (holdings are keyed H:TICKER)"""
    return str(tk).upper().split(":")[-1]


def _hash(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()[:24]


# ----------------------------------------------------------------- ledger
class Ledger:
    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
        self.lines, self.chain_error = [], None
        prev = ""
        for i, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                self.chain_error = f"ledger line {i} is not JSON (the ledger was edited by hand)"
                break
            body = {k: v for k, v in rec.items() if k != "hash"}
            if rec.get("prev") != prev or rec.get("hash") != _hash(prev, body):
                self.chain_error = f"ledger line {i} breaks the hash chain (the ledger was edited by hand)"
                break
            prev = rec["hash"]
            self.lines.append(rec)
        if not self.lines and not self.chain_error:
            self.chain_error = "ledger is empty"

    # -- creation / lookup
    @classmethod
    def start(cls, command: str, run_path, tks: list[str]) -> "Ledger":
        M = manifest()
        if command not in M["commands"]:
            raise SystemExit(f"unknown command {command}; one of: {', '.join(M['commands'])}")
        cdef = M["commands"][command]
        if cdef.get("needs_tk") and not tks:
            raise SystemExit(f"{command} needs --tk TICKER")
        if run_path:
            path = ledger_path(run_path)
        else:
            (state_dir() / "ledgers").mkdir(exist_ok=True)
            path = state_dir() / "ledgers" / f"{command}-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.ledger.jsonl"
        if path.exists():
            path.replace(path.with_suffix(".prev.jsonl"))
        path.write_text("", encoding="utf-8")
        led = cls.__new__(cls)
        led.path, led.lines, led.chain_error = path, [], None
        led._append({"type": "start", "command": command, "run": str(pathlib.Path(run_path).resolve()) if run_path else None, "manifest": M["version"]})
        for tk in tks:
            led.add_tk(tk, cdef["needs_tk"])
        (state_dir() / "active.json").write_text(json.dumps({"ledger": str(path.resolve())}), encoding="utf-8")
        return led

    @classmethod
    def for_run(cls, run_path) -> "Ledger | None":
        p = ledger_path(run_path)
        return cls(p) if p.exists() else None

    @classmethod
    def active(cls) -> "Ledger | None":
        ptr = state_dir() / "active.json"
        if not ptr.exists():
            return None
        try:
            p = pathlib.Path(json.loads(ptr.read_text(encoding="utf-8"))["ledger"])
        except (ValueError, KeyError):
            return None
        return cls(p) if p.exists() else None

    def _append(self, rec: dict) -> dict:
        if self.chain_error:
            raise SystemExit(self.chain_error + ": start again with egx.py step start")
        prev = self.lines[-1]["hash"] if self.lines else ""
        body = {**rec, "at": int(time.time() * 1000), "prev": prev}
        body["hash"] = _hash(prev, {k: v for k, v in body.items() if k != "hash"})
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(body, ensure_ascii=False) + "\n")
        self.lines.append(body)
        return body

    # -- facts
    @property
    def command(self) -> str:
        return self.lines[0]["command"]

    @property
    def start_ms(self) -> int:
        return self.lines[0]["at"]

    @property
    def run_path(self):
        return self.lines[0].get("run")

    def tks(self) -> list[tuple]:
        seen, out = set(), []
        for r in self.lines:
            if r["type"] == "tk" and r["tk"] not in seen:
                seen.add(r["tk"])
                out.append((r["tk"], r["block"]))
        return out

    def block_of(self, tk):
        return dict(self.tks()).get(tk)

    def add_tk(self, tk: str, block: str) -> str:
        if block not in manifest()["blocks"]:
            raise SystemExit(f"unknown block {block}; one of: {', '.join(manifest()['blocks'])}")
        tk = ("H:" if block == "holding" else "") + base(tk)   # a held stock that is also a scan candidate has two entries
        have = self.block_of(tk)
        if have:
            return f"{tk} already in the ledger ({have})"
        self._append({"type": "tk", "tk": tk, "block": block})
        return f"{tk} added ({block}: {' '.join(manifest()['blocks'][block])})"

    def sequence(self) -> list[tuple]:
        """[(atom, tk|None)] in the order the command must run"""
        M, out = manifest(), []
        for item in M["commands"][self.command]["seq"]:
            if item.startswith("@"):
                want = ("holding",) if item == "@holding" else ("swing", "t0")
                for tk, block in self.tks():
                    if block in want:
                        for sid in M["blocks"][block]:
                            out += [(a, tk) for a in M["steps"][sid]["atoms"]]
            else:
                out += [(a, None) for a in M["steps"][item]["atoms"]]
        return out

    def state(self) -> dict:
        st = {}
        for r in self.lines:
            if r["type"] != "atom":
                continue
            cur = st.setdefault((r["id"], r.get("tk")), {"status": "open", "attempts": 0})
            if r["status"] == "retry":
                cur["attempts"] += 1
                cur["reason"] = r.get("proof")
            else:
                cur.update(status=r["status"], proof=r.get("proof"), at=r["at"], reason=r.get("reason"))
        return st

    def status(self, aid, tk=None) -> str:
        return self.state().get((aid, tk), {}).get("status", "open")

    def mark(self, atom: dict, tk, status: str, proof: str = "", reason: str | None = None) -> None:
        rec = {"type": "atom", "id": atom["id"], "tk": tk, "status": status, "proof": (proof or "")[:400], "kind": atom["proof"]}
        if reason:
            rec["reason"] = reason
        self._append(rec)

    def open_before(self, atom: dict, tk) -> list[tuple]:
        """earlier attest / cmd atoms of the run or of the same ticker that are not closed yet"""
        st, out = self.state(), []
        for a, t in self.sequence():
            if a["id"] == atom["id"] and t == tk:
                break
            if a["proof"] == "auto" or (t is not None and t != tk):
                continue
            if st.get((a["id"], t), {}).get("status", "open") not in FINAL:
                out.append((a, t))
        return out


# ----------------------------------------------------------------- context
class Ctx:
    def __init__(self, led: Ledger, run: dict, cfg: dict, open_lines=None, drive_known=None):
        self.led, self.run, self.cfg = led, run or {}, cfg
        self.wl = G.whitelist(SKILL_DIR)
        self.start_ms = led.start_ms
        self.now_ms = int(time.time() * 1000)
        self.open_lines = open_lines      # () -> str, the text of `egx.py open`
        self.drive_known = drive_known    # () -> dict, the reports folder's drive.json

    def calls(self, fn, after=0, tk=None) -> list[dict]:
        out = []
        for c in self.run.get("calls") or []:
            if isinstance(c, (list, tuple)):
                c = dict(zip(("fn", "tk", "at", "ok"), c))
            if c.get("fn") == fn and c.get("ok", True) not in (False, 0) and (c.get("at") or 0) >= after and (tk is None or c.get("tk") == tk):
                out.append(c)
        return out

    def fresh(self, rc) -> bool:
        return bool(rc) and (rc.get("at") or 0) >= self.start_ms - FRESH_SLACK_MS

    def subject(self, tk: str):
        if self.led.block_of(tk) == "holding":
            h = next((h for h in self.run.get("holdings") or [] if h.get("tk") == base(tk)), None)
            if h is None:
                return None
            s = dict(h.get("analysis") or {})
            s.update({k: v for k, v in h.items() if k != "analysis"})
            return s
        if not self.led.block_of(tk):
            return None
        return next((s for s in self.run.get("stocks") or [] if s.get("tk") == tk), None)


def _rc(s, k, t0=False):
    r = ((s.get("t0") or {}).get("receipts") if t0 else s.get("receipts")) or {}
    return r.get(k)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _queries(s) -> list[str]:
    return [q for q in ((x.get("query") if isinstance(x, dict) else x) for x in s.get("news_queries") or []) if q]


def _mtime_ms(path) -> int:
    try:
        return int(pathlib.Path(path).stat().st_mtime * 1000)
    except (OSError, TypeError):
        return 0


# ----------------------------------------------------------------- checks: stock scope  (ctx, s) -> (ok, note)
def c_open_receipt(ctx, s):
    o = _rc(s, "open")
    if not o:
        return False, "no open receipt (EGX.deep / EGX.intraday)"
    if o.get("tk") != s.get("tk"):
        return False, f"the chart opened {o.get('tk')}, not {s.get('tk')}"
    if not ctx.fresh(o):
        return False, "the open receipt is older than this run: open and analyse the stock again"
    return True, f"opened {o.get('iso', '')[:16]}"


def c_open_header(ctx, s):
    o = _rc(s, "open") or {}
    ok = bool(o.get("headerMatch") or str(o.get("title") or "").upper() == s.get("tk"))
    return ok, "" if ok else f"neither the chart header nor its title shows {s.get('tk')} (title: {o.get('title')})"


def c_analyse_receipt(ctx, s):
    a, o = _rc(s, "analyse"), _rc(s, "open") or {}
    if not a:
        return False, "no analysis receipt"
    if not str(a.get("version", "")).startswith(SCRIPT_MM):
        return False, f"analysis made by page script {a.get('version')}, needs {SCRIPT_MM}.x (run the loader)"
    if (a.get("bars") or 0) < 60 and s.get("drop") != "new":
        return False, f"only {a.get('bars')} daily bars"
    if a.get("titleMatch") is False:
        return False, "the analysed chart title does not match the ticker"
    if (a.get("at") or 0) < (o.get("at") or 0) or not ctx.fresh(a):
        return False, "the analysis receipt is older than the open receipt or than this run"
    return True, f"{a.get('bars')} bars, last {a.get('lastBar')}"


def c_plan_or_drop(ctx, s):
    p = s.get("plan") or {}
    if s.get("drop"):
        return True, f"drop: {s['drop']}"
    ok = _num(p.get("entry")) and _num(p.get("stop"))
    return ok, f"plan {p.get('type')}" if ok else "neither a plan (entry, stop) nor a drop reason from the script"


def c_page_read(ctx, s):
    pg = s.get("page")
    if not isinstance(pg, dict):
        return False, "no page object from EGX.deep (cash, order book, price band)"
    return True, "band " + ("-".join(str(x) for x in pg["band"]) if pg.get("band") else "unknown")


def c_news_query_ar(ctx, s):
    ok = any(G.ARABIC.search(q) for q in _queries(s))
    return ok, "" if ok else "no Arabic search logged in news_queries"


def c_news_query_en(ctx, s):
    ok = any(not G.ARABIC.search(q) for q in _queries(s))
    return ok, "" if ok else "no English search logged in news_queries"


def c_news_whitelist(ctx, s):
    if not isinstance(s.get("news"), list):
        return False, "news missing (no dated item = news: [] with news_checked: true)"
    for n in s.get("news") or []:
        dom, _, tier = G.source_of(n.get("url"), ctx.wl)
        if not dom:
            return False, f"news source not on the whitelist: {n.get('url')}"
        if n.get("tier") not in (None, tier):
            return False, f"tier {n.get('tier')} is wrong for {dom} (tier {tier})"
    return True, f"{len(s.get('news') or [])} items"


def c_news_opened(ctx, s):
    if not isinstance(s.get("news"), list):
        return False, "news missing"
    for n in s.get("news") or []:
        dom, _, _ = G.source_of(n.get("url"), ctx.wl)
        t = (n.get("title") or n.get("url") or "")[:40]
        if not G._date(n.get("date")):
            return False, f"no YYYY-MM-DD date read from the page: {t}"
        if not n.get("opened") and not (dom == "bloomberg.com" and n.get("paywalled")):
            return False, f"item not opened with WebFetch: {t}"
    return True, ""


def c_news_fields(ctx, s):
    items = s.get("news") or []
    if not items:
        ok = s.get("news_checked") is True
        return ok, "no dated news" if ok else "news is empty: set news_checked: true only after both searches found nothing dated"
    for n in items:
        t = (n.get("title") or n.get("url") or "")[:40]
        if n.get("impact") not in ("+", "0", "-"):
            return False, f"impact (+ / 0 / -) missing: {t}"
        if not isinstance(n.get("material"), bool) or not isinstance(n.get("fresh"), bool):
            return False, f"material / fresh (true or false) missing: {t}"
        if not str(n.get("summary") or "").strip():
            return False, f"one-line summary missing: {t}"
    return True, ""


def c_red_events_checked(ctx, s):
    rc = s.get("red_events_checked")
    if not isinstance(rc, dict) or "egx.com.eg" not in str(rc.get("query") or ""):
        return False, "red_events_checked {query, found, url} missing: search EGX first (a query with site:egx.com.eg)"
    if rc.get("found") and G.source_of(rc.get("url"), ctx.wl)[2] is None:
        return False, "red_events_checked.url is not a whitelist page"
    for e in s.get("red_events") or []:
        if not e.get("type") or not e.get("source"):
            return False, "a red event has no type or source"
        if str(e.get("date")) != "unknown" and not G._date(e.get("date")):
            return False, f"red event {e.get('type')}: date must be YYYY-MM-DD or \"unknown\""
        if G._date(e.get("date")) and not G.source_of(e.get("url"), ctx.wl)[0]:
            return False, f"red event {e.get('type')} {e.get('date')}: url not on the whitelist"
    return True, f"{len(s.get('red_events') or [])} red events"


def c_catalysts_classified(ctx, s):
    for c in ctx.run.get("catalysts") or []:
        if c.get("tk") == s.get("tk"):
            errs = G.catalyst_problems(c, ctx.wl)
            if errs:
                return False, errs[0]
    return True, ""


def _draw(ctx, s, t0=False):
    d, a = _rc(s, "draw", t0), _rc(s, "analyse", t0) or {}
    if not d:
        return False, "nothing drawn (no draw receipt)"
    if not d.get("made") or d.get("made") != d.get("planned") or d.get("failed"):
        return False, f"drew {d.get('made')}/{d.get('planned')} {d.get('failed') or ''}".strip()
    if (d.get("at") or 0) < (a.get("at") or 0) or not ctx.fresh(d):
        return False, "the drawing is older than the analysis or than this run"
    return True, f"{d.get('made')} marks"


def c_draw_complete(ctx, s):
    return _draw(ctx, s)


def c_draw_events(ctx, s):
    d = _rc(s, "draw")
    if not d:
        return False, "nothing drawn (no draw receipt)"
    need = len([e for e in s.get("red_events") or [] if G._date(e.get("date"))])
    have = sum(1 for k in d.get("kinds") or [] if k == "event")
    return have >= need, f"{have} event lines" if have >= need else f"{need - have} dated red event(s) not drawn: pass them in events"


def c_draw_mas(ctx, s):
    st = (_rc(s, "draw") or {}).get("studies") or {}
    ok = bool(st.get("skipped") or (st.get("ma50") and st.get("ma200")))
    return ok, "" if ok else "MA50 / MA200 not on the chart"


def _verify(ctx, s, t0=False):
    v, d = _rc(s, "verify", t0), _rc(s, "draw", t0) or {}
    if not v:
        return False, "EGX.verifyChart not run"
    if not v.get("ok"):
        return False, "; ".join(v.get("problems") or ["verify not ok"])[:160]
    if (v.get("at") or 0) < (d.get("at") or 0):
        return False, "verified before the last draw"
    return True, ""


def c_verify_ok(ctx, s):
    return _verify(ctx, s)


def _chartrect(ctx, s, t0=False):
    v = _rc(s, "verify", t0) or {}
    if not v.get("ok"):
        return False, "chart not verified"
    ok = bool(ctx.calls("chartRect", after=v.get("at") or 0))
    return ok, "" if ok else "EGX.chartRect(4) was not called after the verify"


def c_chartrect_after_verify(ctx, s):
    return _chartrect(ctx, s)


def _shot(ctx, path, v):
    ok, note = G._shot_ok(path, v)
    if ok and _mtime_ms(path) < ctx.start_ms - FRESH_SLACK_MS:
        return False, "the screenshot file is older than this run"
    return ok, note


def c_screenshot_file(ctx, s):
    return _shot(ctx, s.get("screenshot"), _rc(s, "verify"))


def c_reasons_ok(ctx, s):
    rs = [r for r in s.get("reasons") or [] if isinstance(r, str) and len(r.strip()) >= 12]
    if not str(s.get("sector") or "").strip():
        return False, "sector missing"
    lo = 1 if s.get("drop") or (s.get("t0") or {}).get("drop") else 3
    if not (lo <= len(rs) <= 5) or len(rs) != len(s.get("reasons") or []):
        return False, f"needs {lo}-5 written reasons (has {len(s.get('reasons') or [])})"
    with_num = sum(1 for r in rs if re.search(r"[0-9٠-٩]", r))
    if with_num * 2 < len(rs):
        return False, "reasons need their evidence (dates, numbers, sources)"
    return True, f"{len(rs)} reasons"


def c_t0_eligibility(ctx, s):
    e = s.get("t0_eligibility")
    if not isinstance(e, dict) or e.get("status") not in ("confirmed", "unknown") or not str(e.get("how") or "").strip():
        return False, "t0_eligibility {status: confirmed|unknown, how} missing"
    if s.get("t0_eligible") and e["status"] != "confirmed":
        return False, "t0_eligible is true but the eligibility is not confirmed"
    return True, e["status"]


def c_market_today(ctx, s):
    ok = bool(ctx.calls("market", after=ctx.start_ms - FRESH_SLACK_MS))
    return ok, "" if ok else "EGX.market() was not called in this run (today's EGX30 change)"


def c_t0_analyse(ctx, s):
    a = _rc(s, "analyse", True)
    if not a:
        return False, "no 5-minute analysis receipt (EGX.intraday)"
    if not str(a.get("version", "")).startswith(SCRIPT_MM):
        return False, f"page script {a.get('version')}, needs {SCRIPT_MM}.x"
    if not ctx.fresh(a):
        return False, "the 5-minute analysis is older than this run"
    return True, f"last 5-min bar {a.get('lastBar')}"


def cairo(ms) -> _dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.fromtimestamp(ms / 1000, ZoneInfo("Africa/Cairo"))
    except Exception:
        return _dt.datetime.fromtimestamp(ms / 1000)


def c_t0_window(ctx, s):
    a = _rc(s, "analyse", True) or {}
    if not a.get("at"):
        return False, "no 5-minute analysis receipt"
    t = cairo(a["at"])
    if t.weekday() in (4, 5):
        return False, f"{t:%A} is not an EGX session day"
    ok = "10:15" <= f"{t:%H:%M}" <= "13:30"
    return ok, f"read at {t:%H:%M} Cairo" + ("" if ok else ", outside 10:15-13:30")


def c_t0_plan_or_drop(ctx, s):
    T = s.get("t0") or {}
    p = T.get("plan") or {}
    if T.get("drop") or s.get("drop"):
        return True, f"drop: {T.get('drop') or s.get('drop')}"
    ok = all(_num(p.get(k)) for k in ("entry", "stop", "target"))
    return ok, f"setup {p.get('setup')}" if ok else "neither a T0 plan nor a drop reason from the script"


def c_t0_draw_complete(ctx, s):
    return _draw(ctx, s, True)


def c_t0_verify_ok(ctx, s):
    return _verify(ctx, s, True)


def c_t0_chartrect(ctx, s):
    return _chartrect(ctx, s, True)


def c_t0_screenshot(ctx, s):
    return _shot(ctx, (s.get("t0") or {}).get("screenshot"), _rc(s, "verify", True))


def c_back_to_daily(ctx, s):
    after = max((_rc(s, k, True) or {}).get("at") or 0 for k in ("analyse", "draw", "verify"))
    ok = bool(after and ctx.calls("daily", after=after))
    return ok, "" if ok else "EGX.daily() not called after the 5-minute work (the chart may still be on 5 minutes)"


# ----------------------------------------------------------------- checks: run scope  (ctx, None) -> (ok, note)
def c_market_regime(ctx, _):
    idx = (ctx.run.get("market") or {}).get("egx30") or {}
    if idx.get("regime") not in REGIMES:
        return False, "market.egx30.regime missing (paste the export's index after EGX.market())"
    ok = bool(ctx.calls("market", after=ctx.start_ms - MARKET_MAX_AGE_MS))
    return ok, f"{idx['regime']} ({idx.get('date')})" if ok else "no EGX.market() call in the 8 hours before this run in the export's call log"


def c_export_meta(ctx, _):
    v = str((ctx.run.get("meta") or {}).get("egxjs") or "")
    if not v.startswith(SCRIPT_MM):
        return False, f"meta.egxjs is '{v}': paste the export's egxjs (needs {SCRIPT_MM}.x)"
    ok = bool(ctx.calls("exportToPage", after=ctx.start_ms - FRESH_SLACK_MS))
    return ok, f"page script {v}" if ok else "calls (from the export) has no exportToPage in this run"


def c_meta_complete(ctx, _):
    m = ctx.run.get("meta") or {}
    miss = [k for k in ("command", "trading_day") if not m.get(k)] + [k for k in ("amount", "equity", "cash", "risk_pct") if not _num(m.get(k))]
    if not miss and not G._date(m.get("trading_day")):
        miss = ["trading_day (YYYY-MM-DD)"]
    return not miss, "" if not miss else "meta is missing: " + ", ".join(miss)


def _deep_missing(ctx):
    have = {s.get("tk") for s in ctx.run.get("stocks") or []}
    return [tk for tk, b in ctx.led.tks() if b in ("swing", "t0") and tk not in have]


def _verdict_ran(ctx):
    return ctx.led.status("C8.1") == "done"


def c_overrides_ok(ctx, _):
    if not _verdict_ran(ctx):
        return False, "egx.py verdict has not run"
    if _deep_missing(ctx):
        return False, "not in run.json: " + ", ".join(_deep_missing(ctx))
    for s in ctx.run.get("stocks") or []:
        if not str(s.get("verdict_by", "")).startswith("egx.py"):
            return False, f"{s.get('tk')}: verdict not computed by egx.py"
        ov = s.get("override")
        if ov and (ov.get("verdict") not in ("wait", "not_valid") or not str(ov.get("reason") or "").strip() or G.RANK[ov["verdict"]] < G.RANK.get(s.get("verdict"), 9)):
            return False, f"{s.get('tk')}: override must downgrade and carry a reason"
    return True, ""


def c_vs_last(ctx, _):
    if not _verdict_ran(ctx):
        return False, "egx.py verdict has not run"
    miss = _deep_missing(ctx) + [s.get("tk") for s in ctx.run.get("stocks") or [] if not s.get("quick") and ctx.led.block_of(s.get("tk")) and not str(s.get("vs_last") or "").strip()]
    return not miss, "" if not miss else "vs_last missing on: " + ", ".join(miss)


def c_pdf_built(ctx, _):
    rf = ctx.run.get("report_files") or {}
    if rf.get("pdf") and pathlib.Path(rf["pdf"]).is_file():
        return True, pathlib.Path(rf["pdf"]).name
    if rf.get("pdf_error"):
        return True, "no PDF: " + str(rf["pdf_error"])[:80]
    return False, "no PDF and no pdf_error from egx.py report (run it without --no-pdf)"


def c_drive_recorded(ctx, _):
    plan = (ctx.run.get("report_files") or {}).get("drive")
    if not plan:
        return False, "the report printed no Drive plan"
    known = ctx.drive_known() if ctx.drive_known else {}
    for f_ in plan.get("files") or []:
        sha = str(f_.get("file_ref") or "").split(":")[1:2]
        if (known.get(f_["name"]) or {}).get("sha256") != (sha[0] if sha else None):
            return False, f"{f_['name']}: not uploaded and recorded (create_file, then egx.py drive-record {f_['name']} NEW_FILE_ID)"
    return True, f"{len(plan.get('files') or [])} files in Drive"


def c_holdings_read(ctx, _):
    hs = ctx.run.get("holdings")
    if not isinstance(hs, list):
        return False, "holdings missing in run.json (paste EGX.holdings() items; none held = [])"
    if not ctx.calls("holdings", after=ctx.start_ms - FRESH_SLACK_MS):
        return False, "EGX.holdings() was not called in this run"
    miss = [h.get("tk") for h in hs if not h.get("is_fund") and not ctx.led.block_of(f"H:{h.get('tk')}")]
    return not miss, f"{len(hs)} holdings" if not miss else "not in the ledger (egx.py step add --block holding): " + ", ".join(map(str, miss))


def c_actions_set(ctx, _):
    if not isinstance(ctx.run.get("holdings"), list):
        return False, "holdings missing in run.json"
    for h in ctx.run.get("holdings") or []:
        if h.get("is_fund"):
            continue
        if h.get("action") not in ACTIONS:
            return False, f"{h.get('tk')}: action must be one of {', '.join(ACTIONS)}"
        import egx_manage
        mp = egx_manage.problem(h)
        if mp:
            return False, f"{h.get('tk')}: {mp}"
        if not [r for r in h.get("reasons") or [] if isinstance(r, str) and r.strip()]:
            return False, f"{h.get('tk')}: reasons missing"
        if h["action"] == "add" and stock_problems(ctx, f"H:{h.get('tk')}"):
            return False, f"{h.get('tk')}: add needs a complete check ({stock_problems(ctx, 'H:' + str(h.get('tk')))[0]})"
    return True, ""


def c_market_page(ctx, _):
    if not isinstance((ctx.run.get("market") or {}).get("page"), dict):
        return False, "market.page missing (paste EGX.marketPage())"
    ok = bool(ctx.calls("marketPage", after=ctx.start_ms - FRESH_SLACK_MS))
    return ok, "" if ok else "EGX.marketPage() was not called in this run"


def c_cash_read(ctx, _):
    if not _num((ctx.run.get("meta") or {}).get("cash")):
        return False, "meta.cash missing"
    ok = bool(ctx.calls("page", after=ctx.start_ms - FRESH_SLACK_MS))
    return ok, "" if ok else "EGX.page() was not called in this run"


def c_macro_recorded(ctx, _):
    mk = ctx.run.get("market") or {}
    items = mk.get("macro")
    if not isinstance(items, list) or (not items and mk.get("macro_checked") is not True):
        return False, "market.macro missing (none found = [] and market.macro_checked: true)"
    for n in items:
        if not G.source_of(n.get("url"), ctx.wl)[0] or not G._date(n.get("date")):
            return False, f"macro item needs a whitelist url and a date: {(n.get('title') or '')[:40]}"
    return True, f"{len(items)} macro items"


def _lists(ctx):
    L = ctx.run.get("lists") or {}
    return {k: [str(t).upper() for t in (L.get(k) or [])] for k in ("top30", "hot", "t0")}


def c_list_top30(ctx, _):
    L, src = _lists(ctx)["top30"], ((ctx.run.get("lists_source") or {}).get("top30") or {})
    if len(L) < 20:
        return False, f"lists.top30 has {len(L)} tickers"
    if src.get("kind") == "official":
        ok = bool(G.source_of(src.get("url"), ctx.wl)[0] and G._date(src.get("date")))
        return ok, "official EGX30" if ok else "lists_source.top30: official needs a whitelist url and a date"
    ok = src.get("kind") == "market-cap"
    return ok, "top 30 by market cap" if ok else "lists_source.top30.kind must be official or market-cap"


def c_list_hot(ctx, _):
    if not isinstance((ctx.run.get("lists") or {}).get("hot"), list):
        return False, "lists.hot missing (no hot stock = [])"
    kinds = {q.get("kind") for q in ((ctx.run.get("lists_source") or {}).get("hot_queries") or []) if isinstance(q, dict) and q.get("query")}
    miss = [k for k in ("corporate", "global", "industry") if k not in kinds]
    if miss:
        return False, "lists_source.hot_queries {kind, query} missing for: " + ", ".join(miss)
    for tk in _lists(ctx)["hot"]:
        cs = [c for c in ctx.run.get("catalysts") or [] if c.get("tk") == tk and c.get("status", "confirmed") != "rumour"]
        if not cs:
            return False, f"{tk} is on the Hot list without a confirmed catalyst entry"
        errs = [e for c in cs for e in G.catalyst_problems(c, ctx.wl)]
        if errs:
            return False, errs[0]
    return True, f"{len(_lists(ctx)['hot'])} hot"


def c_list_t0(ctx, _):
    ok = bool(_lists(ctx)["t0"] or str((ctx.run.get("meta") or {}).get("t0_status") or "").strip())
    return ok, "" if ok else "lists.t0 is empty and meta.t0_status does not say why"


def c_quick_covered(ctx, _):
    L = _lists(ctx)
    if len(L["top30"]) < 20:
        return False, "lists.top30 is not built yet"
    have = {s.get("tk") for s in ctx.run.get("stocks") or []}
    unknown = {str(t).upper() for t in ctx.run.get("unknown") or []}
    gone = [t for t in dict.fromkeys(L["top30"] + L["hot"]) if t not in have and t not in unknown]
    if gone:
        return False, "listed but neither in stocks nor in unknown: " + ", ".join(gone[:8])
    seen = {c.get("tk") for fn in ("scan", "deep", "intraday") for c in ctx.calls(fn, after=ctx.start_ms - FRESH_SLACK_MS)}
    not_run = [t for t in dict.fromkeys(L["top30"] + L["hot"]) if t in have and t not in seen]
    return not not_run, f"{len(have)} scanned, {len(unknown)} unknown" if not not_run else "no EGX.scan call in this run for: " + ", ".join(not_run[:8])


def c_quick_marked(ctx, _):
    if not ctx.run.get("stocks"):
        return False, "no scanned stocks in run.json yet"
    bad = [s.get("tk") for s in ctx.run.get("stocks") or [] if not ctx.led.block_of(s.get("tk")) and not s.get("quick") and not s.get("drop")]
    return not bad, "" if not bad else "neither deep-checked (step add) nor quick: true nor dropped: " + ", ".join(map(str, bad[:8]))


def c_deep_selected(ctx, _):
    L = _lists(ctx)
    if len(L["top30"]) < 20 or not ctx.run.get("stocks"):
        return False, "the lists and the quick filter come first"
    by = {s.get("tk"): s for s in ctx.run.get("stocks") or []}
    deep = [tk for tk, b in ctx.led.tks() if b in ("swing", "t0")]
    nocat = [tk for tk in deep if (by.get(tk) or {}).get("category") not in ("top30", "hot", "t0")]
    if nocat:
        return False, "category missing on: " + ", ".join(nocat)
    for cat in ("top30", "hot", "t0"):
        pool = [t for t in L[cat] if t in by and not by[t].get("drop") and not (cat == "top30" and t in L["hot"])]
        got = [t for t in deep if by[t].get("category") == cat]
        if len(got) < min(3, len(pool)):
            return False, f"{cat}: {len(got)} deep-checked, {min(3, len(pool))} needed ({len(pool)} survived the quick filter)"
    return True, f"{len(deep)} deep-checked"


def c_ranked(ctx, _):
    if not _verdict_ran(ctx):
        return False, "egx.py verdict has not run"
    cats = {}
    for s in ctx.run.get("stocks") or []:
        if s.get("category") and s.get("verdict") in ("valid", "wait"):
            cats.setdefault(s["category"], []).append(s.get("rank"))
    bad = [c for c, r in cats.items() if 1 not in r]
    return not bad, "" if not bad else "no rank written for: " + ", ".join(bad) + " (run egx.py verdict)"


CHECKS = {k[2:]: v for k, v in list(globals().items()) if k.startswith("c_") and callable(v)}


# ----------------------------------------------------------------- engine
def run_check(ctx: Ctx, atom: dict, tk):
    fn = CHECKS.get(atom.get("check"))
    if fn is None:
        return False, f"no checker named {atom.get('check')}"
    if tk is None:
        return fn(ctx, None)
    s = ctx.subject(tk)
    if s is None:
        return False, f"{tk} is not in run.json yet"
    try:
        return fn(ctx, s)
    except (TypeError, KeyError, AttributeError, ValueError) as e:
        return False, f"run.json has a malformed value here ({e})"


def skip_valid(ctx: Ctx, atom: dict, tk, reason: str, proof: str = ""):
    if reason not in (atom.get("skip_if") or []):
        return False, f"{atom['id']} cannot be skipped for '{reason}'" + (f" (allowed: {', '.join(atom['skip_if'])})" if atom.get("skip_if") else " (it can never be skipped)")
    if reason == "dropped":
        s = ctx.subject(tk) if tk else None
        ok = bool(s and (s.get("drop") or (ctx.led.block_of(tk) == "t0" and (s.get("t0") or {}).get("drop"))))
        return ok, "" if ok else "the script did not drop this stock"
    if reason == "failed-upstream":
        st = ctx.led.state()
        ok = any(st.get((a["id"], t), {}).get("status") == "failed" and a["step"] in CHART_CHAIN for a, t in ctx.led.sequence() if t == tk)
        return ok, "" if ok else "no earlier open / analyse / draw / verify step of this ticker has failed"
    if reason == "no-sheet":
        ok = not ctx.cfg.get("trade_log_sheet_id")
        return ok, "" if ok else "trade_log_sheet_id is set"
    if reason == "no-drive-folder":
        ok = not ctx.cfg.get("drive_folder_id")
        return ok, "" if ok else "drive_folder_id is set"
    if reason == "no-open-calls":
        ok = bool(ctx.open_lines) and ctx.open_lines().strip() == "nothing open"
        return ok, "" if ok else "egx.py open lists open calls"
    if reason in NEEDS_PROOF:
        ok = len((proof or "").strip()) >= 8
        return ok, "" if ok else f"'{reason}' needs --proof with the tool's error text"
    return False, f"unknown skip reason {reason}"


def sync(ctx: Ctx) -> list[tuple]:
    """Tick every auto step that is provable now and every script-checkable skip.
    Returns [(atom, tk, note)] = the auto steps that are not proven yet, with the reason."""
    if ctx.led.chain_error:
        return []
    led, st, out = ctx.led, ctx.led.state(), []
    for atom, tk in led.sequence():
        if st.get((atom["id"], tk), {}).get("status", "open") in FINAL:
            continue
        r = next((r for r in atom.get("skip_if") or [] if r in AUTO_SKIP and skip_valid(ctx, atom, tk, r)[0]), None)
        if r:
            led.mark(atom, tk, "skipped", reason=r)
            continue
        if atom["proof"] == "attest" and "failed-upstream" in (atom.get("skip_if") or []) and skip_valid(ctx, atom, tk, "failed-upstream")[0]:
            led.mark(atom, tk, "skipped", reason="failed-upstream")
            continue
        if atom["proof"] != "auto":
            # a held stock that is also a scan candidate is one chart check: its recorded steps count for both entries
            twin = next((x for (i, k), x in st.items() if i == atom["id"] and k and tk and k != tk and base(k) == base(tk) and x.get("status") == "done"), None)
            if twin and not led.open_before(atom, tk):
                led.mark(atom, tk, "done", f"{twin.get('proof')} (same check as the other {base(tk)} entry)")
                st = led.state()
            continue
        blockers = led.open_before(atom, tk)
        if blockers:   # never proven ahead of an earlier step that is still open
            out.append((atom, tk, f"waits for {blockers[0][0]['id']}{' ' + blockers[0][1] if blockers[0][1] else ''}"))
            continue
        ok, note = run_check(ctx, atom, tk)
        if ok:
            led.mark(atom, tk, "done", note or "proven")
        elif "failed-upstream" in (atom.get("skip_if") or []) and skip_valid(ctx, atom, tk, "failed-upstream")[0]:
            led.mark(atom, tk, "skipped", note, reason="failed-upstream")   # e.g. no valid screenshot after a failed verify
        else:
            out.append((atom, tk, note))
    return out


def proof_problem(atom: dict, proof: str):
    p = (proof or "").strip()
    if len(p) < 4 or p.lower().strip(" .!") in GENERIC:
        return f"--proof must say what you saw ({atom.get('proof_hint') or 'the value or result'})"
    if atom.get("proof_re") and not re.search(atom["proof_re"], p):
        return f"--proof does not contain the expected value ({atom.get('proof_hint')})"
    return None


def do_done(ctx: Ctx, aid: str, tk, proof: str) -> tuple[bool, str]:
    atom, led = manifest()["atom"].get(aid), ctx.led
    if not atom or (atom, tk) not in [(a, t) for a, t in led.sequence()]:
        return False, f"{aid}{' ' + tk if tk else ''} is not a step of this run (stock steps need --tk)"
    if led.status(aid, tk) in FINAL:
        return False, f"{aid} is already {led.status(aid, tk)}"
    if atom["proof"] == "cmd":
        return False, f"{aid} is recorded by egx.py itself when you run: {atom['do']}"
    blockers = led.open_before(atom, tk)
    if blockers:
        b, bt = blockers[0]
        return False, f"REFUSED: {b['id']}{' ' + bt if bt else ''} comes first and is still open ({b['do'][:90]})"
    if atom["proof"] == "auto":
        ok, note = run_check(ctx, atom, tk)
        if ok:
            led.mark(atom, tk, "done", note or "proven")
        return ok, f"{aid} proven by the script" if ok else f"{aid} NOT proven: {note}"
    err = proof_problem(atom, proof)
    if err:
        return False, err
    led.mark(atom, tk, "done", proof.strip())
    return True, f"{aid}{' ' + tk if tk else ''} recorded"


def do_skip(ctx: Ctx, aid: str, tk, reason: str, proof: str) -> tuple[bool, str]:
    atom, led = manifest()["atom"].get(aid), ctx.led
    if not atom or (atom, tk) not in led.sequence():
        return False, f"{aid}{' ' + tk if tk else ''} is not a step of this run"
    if led.status(aid, tk) in FINAL:
        return False, f"{aid} is already {led.status(aid, tk)}"
    ok, why = skip_valid(ctx, atom, tk, reason, proof)
    if not ok:
        return False, "REFUSED: " + why
    led.mark(atom, tk, "skipped", proof, reason=reason)
    return True, f"{aid}{' ' + tk if tk else ''} skipped ({reason})"


def do_fail(ctx: Ctx, aid: str, tk, reason: str) -> tuple[bool, str]:
    atom, led = manifest()["atom"].get(aid), ctx.led
    if not atom or (atom, tk) not in led.sequence():
        return False, f"{aid}{' ' + tk if tk else ''} is not a step of this run"
    if led.status(aid, tk) in FINAL:
        return False, f"{aid} is already {led.status(aid, tk)}"
    if len((reason or "").strip()) < 8:
        return False, "--reason must say what went wrong"
    tries = led.state().get((aid, tk), {}).get("attempts", 0)
    if tries == 0 and atom.get("retry", True):
        led.mark(atom, tk, "retry", reason)
        return True, f"{aid}: first failure recorded. RETRY ONCE now ({atom['do'][:100]}), then step sync / step done; if it fails again, run step fail again."
    led.mark(atom, tk, "failed", reason, reason=reason)
    what = f"{tk} will be ⏳ naming {aid}; go on with its remaining steps (the ones this makes impossible are closed by the script)" if tk else \
        ("the run cannot produce a report: stop and tell the user" if atom.get("blocks") == "report" else "it will show as ✘ in the summary")
    return True, f"{aid} FAILED after the retry: {what}"


def log_cmd(ctx: Ctx, name: str, tk=None) -> str | None:
    """egx.py calls this after a subcommand succeeded. Returns a warning when the step could not be recorded."""
    led, st = ctx.led, ctx.led.state()
    tk, marked, warn = (base(tk) if tk else None), 0, None
    for atom, t in led.sequence():
        if atom.get("cmd") != name or st.get((atom["id"], t), {}).get("status", "open") in FINAL:
            continue
        if t is not None and base(t) != tk:
            continue
        blockers = led.open_before(atom, t)
        if blockers:
            b, bt = blockers[0]
            warn = warn or f"STEP {atom['id']} NOT RECORDED: {b['id']}{' ' + bt if bt else ''} comes first and is still open ({b['do'][:80]}). Do it, then run this command again."
            continue
        led.mark(atom, t, "done", f"egx.py {name}" + (f" {tk}" if tk and t else ""))
        marked += 1
        if t is None:
            break   # run steps: one per run of the command; ticker steps: the holding and the candidate entry together
    return None if marked else warn


# ----------------------------------------------------------------- views
def stock_problems(ctx: Ctx, tk: str, blocks=("verdict",)) -> list[str]:
    """why this ticker's check is not complete (open, failed or no-longer-true atomic steps)"""
    led, block = ctx.led, ctx.led.block_of(tk)
    if not block:
        return [f"{tk} is not in the step ledger (egx.py step add {tk})"]
    st, out, M = led.state(), [], manifest()
    for sid in M["blocks"][block]:
        for a in M["steps"][sid]["atoms"]:
            if a.get("blocks") not in blocks:
                continue
            cur = st.get((a["id"], tk), {})
            status = cur.get("status", "open")
            if status == "failed":
                out.append(f"{a['id']} failed: {cur.get('reason')}")
            elif status == "open":
                why = run_check(ctx, a, tk)[1] if a["proof"] == "auto" else "not recorded"
                out.append(f"{a['id']} {M['steps'][sid]['title']}: {why}")
            elif status == "done" and a["proof"] == "auto":
                ok, note = run_check(ctx, a, tk)
                if not ok:
                    out.append(f"{a['id']} no longer holds (run.json changed after it was proven): {note}")
    return out


def stock_gate(ctx: Ctx):
    """the 8th gate for egx_gates.compute: (stock) -> (ok, note)"""
    def gate(s):
        tk = s.get("tk")
        if ctx.led.chain_error:
            return False, ctx.led.chain_error
        block = ctx.led.block_of(tk)
        if block and (block == "t0") != (s.get("mode") == "t0"):
            return False, f"ledger block is {block} but the stock's mode is {s.get('mode') or 'swing'}"
        probs = stock_problems(ctx, tk)
        return (not probs), ("; ".join(probs[:2]) + (f" (+{len(probs) - 2} more)" if len(probs) > 2 else ""))[:300]
    return gate


def report_problems(ctx: Ctx) -> list[str]:
    """run-level reasons the report may not be built"""
    led = ctx.led
    if led.chain_error:
        return [led.chain_error]
    st, out = led.state(), []
    for atom, tk in led.sequence():
        if tk is not None or atom.get("blocks") != "report":
            continue
        status = st.get((atom["id"], None), {}).get("status", "open")
        if status == "failed":
            out.append(f"step {atom['id']} failed: {st[(atom['id'], None)].get('reason')}")
        elif status == "open":
            why = run_check(ctx, atom, None)[1] if atom["proof"] == "auto" else "not recorded yet"
            out.append(f"step {atom['id']} open ({why}): {atom['do'][:110]}")
        elif status == "done" and atom["proof"] == "auto":
            ok, note = run_check(ctx, atom, None)
            if not ok:
                out.append(f"step {atom['id']} no longer holds (run.json changed after it was proven): {note}")
    return out


def summary(ctx: Ctx, include_finish=True) -> dict:
    """counts and per-step state, for the terminal, the report and the memory files"""
    led, st, M = ctx.led, ctx.led.state(), manifest()
    groups, order = {}, []
    for atom, tk in led.sequence():
        if not include_finish and atom.get("blocks") == "finish":
            continue
        key = (tk, atom["step"])
        if key not in groups:
            groups[key] = {"tk": tk, "step": atom["step"], "title": M["steps"][atom["step"]]["title"], "n": 0, "done": 0, "skipped": 0, "bad": [], "attested": [], "typed": []}
            order.append(key)
        g, cur = groups[key], st.get((atom["id"], tk), {})
        status = cur.get("status", "open")
        g["n"] += 1
        if status == "done":
            g["done"] += 1
            if atom["proof"] == "attest":
                g["attested"].append(atom["id"])
            elif atom.get("typed"):   # data Claude typed into run.json: the script checks its shape, not that it is true
                g["typed"].append(atom["id"])
        elif status == "skipped":
            g["skipped"] += 1
        else:
            why = cur.get("reason") if status == "failed" else (run_check(ctx, atom, tk)[1] if atom["proof"] == "auto" else "not recorded")
            g["bad"].append({"id": atom["id"], "status": status, "do": atom["do"], "why": why or ""})
    gs = [groups[k] for k in order]
    tot = {k: sum(g[k] for g in gs) for k in ("n", "done", "skipped")}
    bad = [dict(b, tk=g["tk"]) for g in gs for b in g["bad"]]
    return {"command": led.command, "started": cairo(led.start_ms).strftime("%Y-%m-%d %H:%M"), "total": tot["n"], "done": tot["done"], "skipped": tot["skipped"],
            "failed": sum(1 for b in bad if b["status"] == "failed"), "open": sum(1 for b in bad if b["status"] != "failed"),
            "attested": sum(len(g["attested"]) for g in gs), "typed": sum(len(g["typed"]) for g in gs), "groups": gs, "bad": bad, "chain": led.chain_error}


def text(sm: dict) -> str:
    def cell(g):
        return f"{g['step']} {g['title']} " + ("✔" if not g["bad"] else "✘") + f" {g['done'] + g['skipped']}/{g['n']}"
    L = [f"STEPS {sm['command']}: {sm['done']} done ({sm['attested']} stated by Claude, {sm.get('typed', 0)} typed by Claude and only shape-checked, the rest proven by scripts), {sm['skipped']} not applicable, {sm['failed']} failed, {sm['open']} open, of {sm['total']}"]
    run = [g for g in sm["groups"] if g["tk"] is None]
    if run:
        L.append("run:  " + " · ".join(cell(g) for g in run))
    for tk in dict.fromkeys(g["tk"] for g in sm["groups"] if g["tk"]):
        L.append(f"{tk}:  " + " · ".join(cell(g) for g in sm["groups"] if g["tk"] == tk))
    for b in sm["bad"]:
        L.append(f"✘ {b['id']}{' ' + b['tk'] if b['tk'] else ''} {b['status']}: {b['why'] or b['do'][:100]}")
    if sm.get("chain"):
        L.append("✘ " + sm["chain"])
    return "\n".join(L)


def next_lines(ctx: Ctx, tk_filter=None, limit=10) -> list[str]:
    led, st, out = ctx.led, ctx.led.state(), []
    for atom, tk in led.sequence():
        if tk_filter and tk not in (None, tk_filter):
            continue
        if st.get((atom["id"], tk), {}).get("status", "open") in FINAL:
            continue
        who = f" {tk}" if tk else ""
        if atom["proof"] == "attest":
            how = f'-> egx.py step done {atom["id"]}{" --tk " + tk if tk else ""} --proof "<{atom.get("proof_hint") or "what you saw"}>"'
        elif atom["proof"] == "cmd":
            how = "-> recorded when the command runs"
        else:
            how = "-> proven by egx.py step sync"
        skip = f"  [skip only if: {', '.join(atom['skip_if'])}]" if atom.get("skip_if") else ""
        out.append(f"{atom['id']}{who} [{atom['proof']}] {atom['do']}  {how}{skip}")
        if len(out) >= limit:
            break
    return out
