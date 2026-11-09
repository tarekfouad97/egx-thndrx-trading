#!/usr/bin/env python3
"""Dev only: give the synthetic sample run the v3 receipts, whitelisted news and query logs, so
`egx.py verdict/check/report` run on it in the strict mode. Re-run after changing the sample.
Times are refreshed by the tests (receipts must be just before the screenshot file's mtime)."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "examples" / "sample-run.json"
run = json.loads(P.read_text(encoding="utf-8"))
run["meta"]["command"] = "Scan"
T = 1762630000000  # placeholder epoch ms; tests call refresh_times()
for s in run["stocks"]:
    tk = s["tk"]
    s.pop("verdict", None); s.pop("wait_for", None)
    n_events = len([e for e in s.get("red_events") or [] if e.get("date")])
    kinds = ["support", "entry", "stop", "target"] + ["event"] * n_events
    s["receipts"] = {
        "open": {"at": T, "tk": tk, "title": tk, "headerMatch": True, "symbol": "uuid-" + tk, "resolution": "1D", "bars": 300, "lastBar": s.get("asOf")},
        "analyse": {"at": T + 1000, "version": "3.0.0", "bars": 300, "lastBar": s.get("asOf"), "titleMatch": True},
        "draw": {"at": T + 2000, "made": len(kinds), "planned": len(kinds), "kinds": kinds, "failed": [], "studies": {"ma50": "present", "ma200": "present"}},
        "verify": {"at": T + 3000, "ok": True, "resolution": "1D", "expected": len(kinds), "found": len(kinds), "kinds": kinds, "problems": []},
    }
    s["news_queries"] = [{"query": f'"{tk}" OR "Sample Co" site:arabfinance.com', "results": 3},
                         {"query": f'"شركة العينة" البورصة site:mubasher.info', "results": 2}]
    for i, n in enumerate(s.get("news") or []):
        n.update({"url": f"https://www.arabfinance.com/en/news/sample-{tk.lower()}-{i}", "source": "Arab Finance", "tier": 2, "opened": True})
    for e in s.get("red_events") or []:
        e.update({"url": f"https://www.egx.com.eg/en/sample-{tk.lower()}", "source": "EGX"})
    if not s.get("news"):
        s["news"] = []
        s["news_checked"] = True
for c in run.get("catalysts") or []:
    c["sources"] = [{"url": "https://www.arabfinance.com/en/news/sample-expansion", "date": c["date"], "source": "Arab Finance", "tier": 2, "opened": True}]
    c.pop("url", None); c.pop("source", None)
P.write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
print("sample run upgraded to v3 receipts")
