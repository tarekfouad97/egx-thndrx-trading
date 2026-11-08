#!/usr/bin/env python3
"""Dev only: render ThndrX-like chart images (candles + the EGX· lines) for the synthetic sample run,
so the sample report has chart screenshots. Needs playwright + chromium. Real runs use real ThndrX screenshots."""
import asyncio, json, pathlib, sys
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
run = json.loads((ROOT / "examples" / "sample-run.json").read_text())
out = ROOT / "examples" / "shots"; out.mkdir(exist_ok=True)

def svg(s):
    C = s.get("candles") or []
    lines = (s.get("draw") or {}).get("lines") or []
    vals = [x for c in C for x in c[1:5]] + [l["price"] for l in lines]
    lo, hi = min(vals), max(vals); pad = (hi - lo) * .08; lo -= pad; hi += pad
    W, H, R = 1200, 750, 90
    cw = (W - R - 20) / len(C); y = lambda v: 30 + (hi - v) / (hi - lo) * (H - 80)
    g = [f'<rect width="{W}" height="{H}" fill="#0b0b0c"/>']
    for k in range(6):
        yy = 30 + k * (H - 80) / 5; g.append(f'<line x1="0" x2="{W-R}" y1="{yy}" y2="{yy}" stroke="#1c1c1f"/>')
        g.append(f'<text x="{W-R+8}" y="{yy+4}" fill="#8e8e93" font-size="13" font-family="Arial">{hi - k*(hi-lo)/5:.2f}</text>')
    for i, (d, o, h, l, c) in enumerate(C):
        x = 10 + i * cw + cw / 2; col = "#22ab94" if c >= o else "#f23645"
        g.append(f'<line x1="{x}" x2="{x}" y1="{y(h)}" y2="{y(l)}" stroke="{col}"/>')
        g.append(f'<rect x="{x-cw*.35}" y="{y(max(o,c))}" width="{cw*.7}" height="{max(1,y(min(o,c))-y(max(o,c)))}" fill="{col}"/>')
    for ln in lines:
        dash = ' stroke-dasharray="6 5"' if ln.get("style") == 2 else ""
        g.append(f'<line x1="0" x2="{W-R}" y1="{y(ln["price"])}" y2="{y(ln["price"])}" stroke="{ln["color"]}" stroke-width="2"{dash}/>')
        g.append(f'<text x="{W-R-8}" y="{y(ln["price"])-6}" text-anchor="end" direction="rtl" fill="{ln["color"]}" font-size="14" font-family="Arial">{ln["text"]}</text>')
    g.append(f'<text x="16" y="22" fill="#e5e5ea" font-size="15" font-family="Arial">{s["tk"]} · 1D · EGX (sample data)</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(g)}</svg>'

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=sys.argv[1] if len(sys.argv) > 1 else None)
        pg = await b.new_page(viewport={"width": 1200, "height": 750})
        for s in run["stocks"]:
            if s.get("candles"):
                await pg.set_content(f'<body style="margin:0">{svg(s)}</body>')
                path = out / f'{s["tk"]}.jpg'
                await pg.screenshot(path=str(path), type="jpeg", quality=80)
                s["screenshot"] = f"examples/shots/{s['tk']}.jpg"; s["shot_at"] = "2026-11-08 21:28"
        await b.close()
    for h in run.get("holdings") or []:
        if h.get("tk") in [s["tk"] for s in run["stocks"] if s.get("screenshot")]:
            h["screenshot"] = f"examples/shots/{h['tk']}.jpg"; h["shot_at"] = "2026-11-08 21:28"
    (ROOT / "examples" / "sample-run.json").write_text(json.dumps(run, ensure_ascii=False, indent=1))
    print("shots written to", out)
asyncio.run(main())
