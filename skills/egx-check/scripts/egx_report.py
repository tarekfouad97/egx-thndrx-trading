"""
egx_report.py - the 12-second HyperFrames recap of a run (1080x1920), written by `egx.py report --video`
and rendered to MP4 with `npx hyperframes render`. The report page itself is egx_page.py.
Standard library only.
"""
from __future__ import annotations

import html
import json


TONE = {"valid": "gain", "add": "gain", "hold": "gain", "wait": "copper", "tighten": "copper", "not_valid": "loss", "sell": "loss", "exit": "loss", "dropped": "muted"}


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def num(x, d=2):
    if x is None or x == "":
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    s = f"{x:,.{0 if abs(x) >= 100000 else d}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def signed(x, d=2, unit="%"):
    if x is None:
        return "—"
    return ("+" if float(x) > 0 else "") + num(x, d) + unit


def recap_composition(run: dict, cfg: dict) -> str:
    """1080x1920 HyperFrames composition in the report palette; also plays in a browser (`npx hyperframes render` -> MP4)."""
    meta, al = run.get("meta") or {}, run.get("allocation") or {}
    eg = ((run.get("market") or {}).get("egx30") or {})
    regime = eg.get("regime", "unknown")
    rcol = {"Up": "#6CC4A1", "Down": "#E8766A", "Correction": "#D9894A"}.get(regime, "#D6B9B9")
    orders = [r for r in al.get("rows") or [] if r.get("shares")][:3]
    holds = [h for h in run.get("holdings") or [] if not h.get("is_fund")][:4]
    sp = [v for v in (eg.get("spark") or []) if v is not None]
    path = ""
    if len(sp) > 2:
        lo, hi = min(sp), max(sp)
        rng = (hi - lo) or 1
        path = "M" + " L".join(f"{i * 880 / (len(sp) - 1):.1f} {300 - (v - lo) / rng * 280:.1f}" for i, v in enumerate(sp))
    cards = "".join(
        f'<div class="ord" id="o{i}"><div class="otk">{esc(r["tk"])}</div><div class="orow"><span>SHARES</span><b>{esc(r["shares"])}</b></div>'
        f'<div class="orow"><span>ENTRY</span><b class="te">{esc(r["entry"])}</b></div><div class="orow"><span>STOP</span><b class="lo">{esc(r["stop"])}</b></div>'
        f'<div class="orow"><span>TARGET</span><b class="ga">{esc(r["target"])}</b></div></div>' for i, r in enumerate(orders)
    ) or '<div class="ord" id="o0"><div class="otk">CASH</div><div class="orow"><span>No valid setup today</span></div></div>'
    hrows = "".join(f'<div class="hrow"><b>{esc(h.get("tk"))}</b><span class="act {esc(TONE.get(h.get("action") or "hold"))}">{esc((h.get("action") or "hold").upper())}</span>'
                    f'<em>{esc(signed(h.get("pnlPct")))}</em></div>' for h in holds) or '<div class="hrow"><b>No stock positions</b></div>'
    foot = cfg["footer"]
    deployed, cash_left, risk = al.get("deployed") or 0, al.get("cash_left") or 0, al.get("total_risk") or 0
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1080, height=1920"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
:root{{--bg:#0F171B;--s1:#122D39;--teal:#2C697F;--tt:#6FB3C8;--rose:#D6B9B9;--copper:#8A4C1C;--ct:#D9894A;--ink:#F4EEEA;--gain:#6CC4A1;--loss:#E8766A}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:var(--bg);font-family:Inter,sans-serif;color:var(--ink)}}
#root{{position:relative;width:100%;height:100%}}
.ground{{position:absolute;inset:0;background:radial-gradient(120% 60% at 50% -10%,rgba(138,76,28,.55),transparent 60%),linear-gradient(180deg,#0F171B 0%,#122D39 55%,#0F171B 100%)}}
.clip{{position:absolute;inset:0}}
.scene{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 90px;gap:36px;opacity:0}}
.k{{font-size:34px;letter-spacing:.3em;color:var(--rose);text-transform:uppercase}}
.h{{font-size:120px;font-weight:900;letter-spacing:-.04em;line-height:1}}
.pill{{align-self:flex-start;font-size:44px;font-weight:700;padding:16px 40px;border-radius:999px;color:{rcol};border:3px solid {rcol};background:rgba(18,45,57,.6)}}
.chart{{width:900px;height:320px}}
.sub{{font-size:38px;color:var(--rose)}}
.ord{{padding:44px 52px;border-radius:44px;background:rgba(18,45,57,.72);border:2px solid rgba(214,185,185,.18);box-shadow:inset 0 2px 0 rgba(255,255,255,.12),0 30px 80px rgba(0,0,0,.45);display:flex;flex-direction:column;gap:14px}}
.otk{{font-size:84px;font-weight:900;letter-spacing:-.03em}}
.orow{{display:flex;justify-content:space-between;font-size:40px;color:var(--rose)}} .orow b{{color:var(--ink)}}
.te{{color:var(--tt)!important}} .lo{{color:var(--loss)!important}} .ga{{color:var(--gain)!important}}
.hrow{{display:flex;align-items:center;gap:30px;font-size:52px;padding:26px 0;border-bottom:2px solid rgba(214,185,185,.14)}} .hrow em{{margin-inline-start:auto;font-style:normal;color:var(--rose)}}
.act{{font-size:32px;font-weight:700;padding:8px 22px;border-radius:999px;background:rgba(18,45,57,.8)}} .act.gain{{color:var(--gain)}} .act.loss{{color:var(--loss)}} .act.copper{{color:var(--ct)}}
.n{{display:flex;flex-direction:column;gap:6px}} .n b{{font-size:150px;font-weight:900;letter-spacing:-.04em;line-height:1}} .n span{{font-size:34px;letter-spacing:.24em;color:var(--rose)}}
.heart{{color:var(--loss)}}
</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="12" data-width="1080" data-height="1920">
 <div class="ground"></div>
 <div id="s1" class="clip" data-start="0" data-duration="3" data-track-index="1"><div class="scene" id="s1i">
  <div class="k">EGX · {esc(meta.get("command", ""))} · {esc(meta.get("trading_day") or (meta.get("created") or "")[:10])}</div>
  <div class="h">EGX30<br/>{esc(num(eg.get("last"), 0))}</div>
  <div class="pill">{esc(regime.upper())}</div>
  <svg class="chart" viewBox="0 0 880 320"><path id="line" d="{path}" fill="none" stroke="{rcol}" stroke-width="6" stroke-linecap="butt" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>
  <div class="sub">MA50 {esc(num(eg.get("ma50"), 0))} · MA200 {esc(num(eg.get("ma200"), 0))} · 20d {esc(signed(eg.get("ch20")))}</div>
 </div></div>
 <div id="s2" class="clip" data-start="3" data-duration="3.6" data-track-index="1"><div class="scene" id="s2i">
  <div class="k">Orders</div>{cards}
 </div></div>
 <div id="s3" class="clip" data-start="6.6" data-duration="2.6" data-track-index="1"><div class="scene" id="s3i">
  <div class="k">Your positions</div>{hrows}
 </div></div>
 <div id="s4" class="clip" data-start="9.2" data-duration="2.8" data-track-index="1"><div class="scene" id="s4i">
  <div class="n"><b id="n1">0</b><span>DEPLOY EGP</span></div><div class="n"><b id="n2">0</b><span>STAYS CASH EGP</span></div>
  <div class="n"><b id="n3">0</b><span>AT RISK EGP</span></div>
  <div class="sub">Made with <span class="heart">♥</span> by {esc(foot["author"])} · not investment advice</div>
 </div></div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
if (!window.gsap) {{
  document.querySelectorAll(".scene").forEach((e, i) => (e.style.opacity = i === 1 ? 1 : 0));
}} else {{
  const tl = gsap.timeline({{ paused: true }});
  const scene = (id, start, dur, last) => {{
    tl.fromTo(id, {{ opacity: 0, y: 60, filter: "blur(14px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", duration: 0.55, ease: "power3.out" }}, start);
    if (!last) tl.to(id, {{ opacity: 0, y: -40, filter: "blur(10px)", duration: 0.35, ease: "power2.in" }}, start + dur - 0.4);
  }};
  tl.set("#s1i", {{ opacity: 1 }}, 0); tl.to("#s1i", {{ opacity: 0, y: -40, filter: "blur(10px)", duration: 0.35, ease: "power2.in" }}, 2.6);
  scene("#s2i", 3, 3.6); scene("#s3i", 6.6, 2.6); scene("#s4i", 9.2, 2.8, true);
  tl.fromTo("#line", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 1.6, ease: "power2.inOut" }}, 0.4);
  tl.fromTo(".ord", {{ opacity: 0, y: 80, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "back.out(1.3)", stagger: 0.2 }}, 3.3);
  tl.fromTo(".hrow", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.4, stagger: 0.12, ease: "power3.out" }}, 6.9);
  const count = (id, to, at) => {{ const o = {{ v: 0 }}; tl.to(o, {{ v: to, duration: 1.2, ease: "power2.out", onUpdate: () => {{ document.querySelector(id).textContent = Math.round(o.v).toLocaleString("en-US"); }} }}, at); }};
  count("#n1", {deployed:.0f}, 9.4); count("#n2", {cash_left:.0f}, 9.6); count("#n3", {risk:.0f}, 9.8);
  window.__timelines["main"] = tl;
  tl.seek(0);
}}
</script>
</body></html>"""

