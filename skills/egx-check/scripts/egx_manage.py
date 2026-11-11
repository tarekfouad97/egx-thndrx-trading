"""Position management for the EGX skills (standard library only).

`egx.py manage run.json` decides the action of every stock held from numbers, never from prose:
exit, time stop, partial exit at +1R, trailing stop, hold. Claude supplies the facts it read
(entry date, first stop, current stop, whether half was already sold) and never the action.

Fields read from each holding (run.json `holdings[]`):
  price, avgPrice, qty                      EGX.holdings()
  entry_date (YYYY-MM-DD), first_stop       Trades tab (the stop of the original plan)
  stop                                      the stop order seen in ThndrX, else the Trades tab
  partial_done (true / false)               half already sold at +1R
  analysis {atr, zones, candles, last}      EGX.get(tk) after the holding's deep check
  news[]                                    the holding's news step
"""
from __future__ import annotations

import math

PARTIAL_AT_R = 1.0        # sell half when the price is this many R above the entry
TRAIL_ATR = 2.5           # trailing stop = highest close since entry - this many ATR
TIME_STOP_SESSIONS = 10   # sessions held ...
TIME_STOP_MIN_R = 0.5     # ... without reaching this many R = exit
SUPPORT_BREAK_ATR = 0.5


def _n(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def decide(h: dict) -> dict:
    """-> {action, rule, why[], missing[], new_stop, sell_shares, numbers{}}; first rule that applies"""
    a = h.get("analysis") or {}
    price = _n(h.get("price")) or _n(a.get("last"))
    entry, qty = _n(h.get("avgPrice")), _n(h.get("qty"))
    stop, first = _n(h.get("stop")), _n(h.get("first_stop"))
    atr = _n(a.get("atr"))
    sup = (a.get("zones") or {}).get("support") or {}
    sup_lo = _n(sup.get("lo"))
    swing = (a.get("zones") or {}).get("lastSwingLow") or []
    swing_lo = _n(swing[1]) if len(swing) > 1 else None
    since = [c for c in (a.get("candles") or h.get("candles") or []) if len(c) >= 5 and h.get("entry_date") and str(c[0]) > str(h["entry_date"])]
    held = len(since) if h.get("entry_date") else None
    hi_close = max((_n(c[4]) or 0 for c in since), default=None)
    last_close = _n(since[-1][4]) if since else price
    out = {"action": "hold", "rule": "hold", "why": [], "missing": [], "new_stop": None, "sell_shares": None,
           "numbers": {"price": price, "entry": entry, "stop": stop, "first_stop": first, "atr": atr, "sessions_held": held, "highest_close": hi_close}}
    need = {"price": price, "avgPrice": entry, "qty": qty, "analysis.atr": atr, "stop": stop, "first_stop": first, "entry_date": h.get("entry_date")}
    out["missing"] = [k for k, v in need.items() if not v]

    def done(action, rule, why, new_stop=None, sell=None):
        out.update(action=action, rule=rule, new_stop=round(new_stop, 2) if new_stop else None, sell_shares=sell)
        out["why"].append(why)
        return out

    # 1. exit: these need no trade history
    bad = [n for n in h.get("news") or [] if n.get("impact") == "-" and n.get("material")]
    if bad:
        return done("exit", "material-news", f"negative material news {bad[0].get('date')}: {(bad[0].get('title') or '')[:80]}", sell=int(qty or 0) or None)
    if stop and last_close is not None and last_close < stop:
        return done("exit", "stop", f"close {last_close} is under the stop {stop}", sell=int(qty or 0) or None)
    if sup_lo and atr and last_close is not None and last_close < sup_lo - SUPPORT_BREAK_ATR * atr:
        return done("exit", "support-break", f"close {last_close} is under support low {sup_lo} - {SUPPORT_BREAK_ATR} ATR ({round(sup_lo - SUPPORT_BREAK_ATR * atr, 2)})", sell=int(qty or 0) or None)
    if out["missing"]:
        if not stop and sup_lo and atr:
            out["new_stop"] = round(sup_lo - SUPPORT_BREAK_ATR * atr, 2)
            out["why"].append(f"no stop known: place one at support low - {SUPPORT_BREAK_ATR} ATR = {out['new_stop']}")
        out["rule"] = "incomplete"
        out["why"].append("cannot manage this position fully, missing: " + ", ".join(out["missing"]))
        return out
    r1 = entry - first
    if r1 <= 0:
        out["rule"] = "incomplete"; out["missing"].append("first_stop below avgPrice")
        out["why"].append(f"first stop {first} is not under the entry {entry}: R cannot be measured")
        return out
    r_now = (price - entry) / r1
    out["numbers"].update(R=round(r1, 3), r_now=round(r_now, 2))
    # 2. time stop
    if held is not None and held >= TIME_STOP_SESSIONS and r_now < TIME_STOP_MIN_R and not h.get("partial_done"):
        return done("exit", "time-stop", f"{held} sessions held and only {round(r_now, 2)}R (needs {TIME_STOP_MIN_R}R by session {TIME_STOP_SESSIONS})", sell=int(qty))
    # 3. partial exit at +1R, stop to breakeven
    if not h.get("partial_done") and r_now >= PARTIAL_AT_R:
        half = int(qty // 2)
        return done("partial", "partial-1R", f"price {price} is {round(r_now, 2)}R above the entry {entry}: sell {half} of {int(qty)} and move the stop to breakeven {entry}",
                    new_stop=max(stop, entry), sell=half or None)
    # 4. trailing stop after the partial: only ever up
    if h.get("partial_done"):
        cands = [stop] + [x for x in ((hi_close - TRAIL_ATR * atr) if hi_close else None, (swing_lo - SUPPORT_BREAK_ATR * atr) if swing_lo else None) if x and x < price]
        new = round(max(cands), 2)
        if new > stop:
            return done("tighten", "trail", f"trail the stop from {stop} to {new} (highest close {hi_close} - {TRAIL_ATR} ATR, or last swing low {swing_lo} - {SUPPORT_BREAK_ATR} ATR; never down)", new_stop=new)
        out["why"].append(f"trailing stop stays at {stop} (candidates are not higher)")
        return out
    # 5. an add asked for by the check stays an add (egx_steps checks the holding's own check is complete); otherwise hold
    if h.get("want_add") and (h.get("plan") or {}).get("entry"):
        return done("add", "add", f"add asked for and no exit rule fires; position is {round(r_now, 2)}R")
    out["why"].append(f"hold: {round(r_now, 2)}R, stop {stop}, session {held} of {TIME_STOP_SESSIONS} before the time stop, partial at {round(entry + PARTIAL_AT_R * r1, 2)}")
    return out


def manage(run: dict, version: str) -> list[str]:
    lines = []
    for h in run.get("holdings") or []:
        if h.get("is_fund"):
            continue
        d = decide(h)
        h["action"], h["action_by"], h["manage"] = d["action"], "egx.py " + version, d
        if not [r for r in h.get("reasons") or [] if isinstance(r, str) and r.strip()]:
            h["reasons"] = list(d["why"])
        extra = (f" · sell {d['sell_shares']}" if d["sell_shares"] else "") + (f" · stop -> {d['new_stop']}" if d["new_stop"] else "")
        lines.append(f"{h.get('tk'):7} {d['action'].upper():8} [{d['rule']}]{extra}  {'; '.join(d['why'])}")
    return lines


def problem(h: dict):
    """the action in run.json must be the one the rules give (egx_steps.c_actions_set)"""
    if not str(h.get("action_by", "")).startswith("egx.py"):
        return "action not set by egx.py (run: egx.py manage run.json; never type an action)"
    want = decide(h)["action"]
    if want != h.get("action"):
        return f"action {h.get('action')} does not match the rules ({want}); run egx.py manage again"
    return None
