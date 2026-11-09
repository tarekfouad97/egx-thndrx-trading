#!/usr/bin/env python3
"""Smoke tests for egx.py: allocate, check, report, index, search, read. Run: python3 tests/test_egx.py"""
import json, os, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EGX = ROOT / "skills" / "egx-check" / "scripts" / "egx.py"
SAMPLE = ROOT / "examples" / "sample-run.json"


def run(*args, env=None):
    return subprocess.run([sys.executable, str(EGX), *args], capture_output=True, text=True, env=env, cwd=ROOT)


def fresh(d):
    """receipts just before each screenshot's mtime, as in a real run"""
    for s in d["stocks"]:
        shot = ROOT / s.get("screenshot", "")
        if s.get("receipts") and shot.is_file():
            t = int(shot.stat().st_mtime * 1000) - 60000
            for i, k in enumerate(("open", "analyse", "draw", "verify")):
                s["receipts"][k]["at"] = t + i * 1000
    return d


class EgxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.env = {**os.environ, "EGX_REPORTS_DIR": str(self.tmp / "reports")}
        self.run_file = self.tmp / "run.json"
        self.run_file.write_text(json.dumps(fresh(json.loads(SAMPLE.read_text(encoding="utf-8")))), encoding="utf-8")
        self.assertEqual(run("verdict", str(self.run_file)).returncode, 0)

    def stocks(self):
        return {s["tk"]: s for s in json.loads(self.run_file.read_text())["stocks"]}

    def edit(self, fn):
        d = json.loads(self.run_file.read_text()); fn(d); self.run_file.write_text(json.dumps(d))

    def test_fees(self):
        out = json.loads(run("fees", "4981").stdout)
        self.assertAlmostEqual(out["fees_per_side"], 11.72, places=2)

    def test_check_sample(self):
        self.assertEqual(run("check", str(self.run_file)).returncode, 0)

    def test_allocate_rules(self):
        r = run("allocate", str(self.run_file), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        al = json.loads(self.run_file.read_text())["allocation"]
        self.assertTrue(al["half_deploy"])  # sample regime is Correction
        self.assertLessEqual(al["deployed"], al["deploy_cap"] + 1)
        for row in al["rows"]:
            self.assertGreaterEqual(row["rr"], 2)
            if row["shares"]:
                self.assertGreaterEqual(row["value"], 2500)

    def test_verdicts_computed(self):
        v = {k: s["verdict"] for k, s in self.stocks().items()}
        self.assertEqual(v, {"DEMO1": "valid", "DEMO2": "wait", "DEMO3": "dropped", "DEMO4": "dropped"})
        self.assertTrue(all(g["ok"] for g in self.stocks()["DEMO1"]["gates"]))

    def test_rank_per_category(self):
        def cat(d):
            d["stocks"][0]["category"] = "top30"; d["stocks"][1]["category"] = "top30"
        self.edit(cat); out = run("verdict", str(self.run_file)).stdout
        st = self.stocks()
        self.assertEqual((st["DEMO1"]["rank"], st["DEMO2"]["rank"]), (1, 2))  # valid before wait
        self.assertIn("top30: #1 DEMO1, #2 DEMO2", out)

    def test_hand_verdict_rejected(self):
        self.edit(lambda d: d["stocks"][2].update(verdict="valid"))  # DEMO3 R:R < 2
        self.assertNotEqual(run("check", str(self.run_file)).returncode, 0)

    def test_upgrade_override_rejected(self):
        self.edit(lambda d: d["stocks"][1].update(override={"verdict": "wait", "reason": "x"}))
        self.assertEqual(run("verdict", str(self.run_file)).returncode, 0)  # wait -> wait is fine
        self.edit(lambda d: d["stocks"][0].update(override={"verdict": "not_valid", "reason": "results rumour"}))
        run("verdict", str(self.run_file)); self.assertEqual(self.stocks()["DEMO1"]["verdict"], "not_valid")

    def test_screenshot_before_verify_fails_gate(self):
        def late(d):
            d["stocks"][0]["receipts"]["verify"]["at"] += 3600 * 1000
        self.edit(late); run("verdict", str(self.run_file))
        s = self.stocks()["DEMO1"]
        self.assertEqual(s["verdict"], "wait")
        self.assertFalse(next(g for g in s["gates"] if g["gate"] == "screenshot")["ok"])

    def test_missing_draw_fails_gate(self):
        self.edit(lambda d: d["stocks"][0]["receipts"].pop("verify")); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")

    def test_news_whitelist_and_languages(self):
        self.edit(lambda d: d["stocks"][0]["news"][0].update(url="https://randomblog.example/x")); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")
        self.assertNotEqual(run("check", str(self.run_file)).returncode, 0)

    def test_one_language_queries_fail(self):
        self.edit(lambda d: d["stocks"][0].update(news_queries=[{"query": "a"}, {"query": "b"}])); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")

    def test_rumour_catalyst(self):
        self.edit(lambda d: d["catalysts"][0].update(type="acquisition"))  # one Tier-2 source only
        self.assertNotEqual(run("check", str(self.run_file)).returncode, 0)

    def test_t0_verdicts(self):
        import datetime as dt
        cairo = lambda hh, mm: int(dt.datetime(2026, 11, 8, hh - 2, mm, tzinfo=dt.timezone.utc).timestamp() * 1000)  # Cairo = UTC+2 in Nov
        def t0(d):
            s = json.loads(json.dumps(d["stocks"][0])); s["mode"] = "t0"; s["t0_eligible"] = True
            r = s["receipts"]
            s["t0"] = {"session": {"day": "2026-11-08"}, "last": 35.6, "vwap": 35.4, "vsEGX30": 0.5, "screenshot": s["screenshot"],
                       "plan": {"setup": "vwap-pullback", "entry": 35.5, "stop": 35.2, "target": 36.4, "rr": 3, "movePct": 2.5, "entryDistATR5": 0.2, "trigger": "x"},
                       "receipts": {"analyse": dict(r["analyse"], at=cairo(11, 5)), "draw": dict(r["draw"], studies={"skipped": True}), "verify": r["verify"]}}
            d["stocks"] = [s]  # Sunday 2026-11-08
        self.edit(t0); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "valid", self.stocks()["DEMO1"]["auto_reasons"])
        self.edit(lambda d: d["stocks"][0]["t0"]["receipts"]["analyse"].update(at=cairo(13, 45))); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")  # read after the 13:30 cut-off
        self.edit(lambda d: d["stocks"][0]["t0"]["receipts"]["analyse"].update(at=cairo(11, 5)) or d["stocks"][0].update(t0_eligible=False)); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")  # eligibility not confirmed
        self.edit(lambda d: d["stocks"][0].update(t0_eligible=True) or d["stocks"][0]["t0"]["plan"].update(target=35.55, movePct=0.14)); run("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "dropped")  # fees eat the move
        self.edit(lambda d: d["stocks"][0]["t0"]["plan"].update(target=36.4, movePct=2.5)); run("verdict", str(self.run_file))
        r = run("allocate", str(self.run_file), env=self.env)
        row = json.loads(self.run_file.read_text())["allocation"]["rows"][0]
        self.assertEqual((row["entry"], row["stop"]), (35.5, 35.2))  # sized from the 5-minute plan, not the daily one

    def test_memory_files(self):
        r = run("report", str(self.run_file), "--no-pdf", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = self.tmp / "reports"
        for f in ("history.jsonl", "news.jsonl", "runs.jsonl"):
            self.assertTrue((rep / f).exists(), f)
        run("report", str(self.run_file), "--no-pdf", env=self.env)  # same run again: no duplicates
        hist = [json.loads(x) for x in (rep / "history.jsonl").read_text().splitlines()]
        self.assertEqual(len([h for h in hist if h["tk"] == "DEMO1" and "pos" not in h]), 1)
        rec = run("recall", "DEMO1", env=self.env).stdout
        self.assertIn("VALID", rec); self.assertIn("E 35.56", rec); self.assertIn("Arab Finance", rec)
        self.assertLess(len(rec), 1500)  # cheap to read
        rid = json.loads(r.stdout)["report"].rsplit("/", 1)[1].rsplit(".", 1)[0]
        self.assertIn("target", run("outcome", rid, "DEMO1", "target", "2026-11-12", env=self.env).stdout)
        run("report", str(self.run_file), "--no-pdf", env=self.env)  # outcome survives a rebuild
        self.assertIn("outcome: target 2026-11-12", run("recall", "DEMO1", env=self.env).stdout)
        self.assertIn("DEMO1", run("news", "DEMO1", env=self.env).stdout)
        self.assertIn("Scan", run("runs", env=self.env).stdout)
        html = pathlib.Path(json.loads(r.stdout)["report"]).read_text()
        self.assertNotIn("screenshot_b64", html.split('id="egx-data"')[1])  # data block has no pictures

    def test_drive_plan(self):
        cfgdir = self.tmp / "home" / ".egx-thndrx"; cfgdir.mkdir(parents=True)
        (cfgdir / "config.json").write_text(json.dumps({"drive_folder_id": "FOLDER"}))
        env = {**self.env, "HOME": str(self.tmp / "home")}
        res = json.loads(run("report", str(self.run_file), "--no-pdf", env=env).stdout)
        names = {f["name"]: f for f in res["drive"]["files"]}
        self.assertEqual(res["drive"]["folder_id"], "FOLDER")
        self.assertTrue(names["history.jsonl"]["file_ref"].startswith("sha256:"))
        self.assertEqual(names["history.jsonl"]["action"], "create")
        run("drive-record", "history.jsonl", "ID123", env=env)
        res = json.loads(run("report", str(self.run_file), "--no-pdf", env=env).stdout)
        h = {f["name"]: f for f in res["drive"]["files"]}["history.jsonl"]
        self.assertEqual((h["action"], h["old_file_id"]), ("skip", "ID123"))  # same content: nothing to upload
        run("outcome", res["drive"]["files"][0]["name"].rsplit(".", 1)[0], "DEMO1", "stop", "2026-11-12", env=env)
        res = json.loads(run("report", str(self.run_file), "--no-pdf", env=env).stdout)
        h = {f["name"]: f for f in res["drive"]["files"]}["history.jsonl"]
        self.assertEqual((h["action"], h["old_file_id"]), ("replace", "ID123"))  # new copy, then trash the old one

    def test_no_force(self):
        self.edit(lambda d: d["stocks"][2].update(verdict="valid"))
        r = run("report", str(self.run_file), "--force", env=self.env)
        self.assertNotEqual(r.returncode, 0)

    def test_report_index_search_read(self):
        r = run("report", str(self.run_file), "--no-pdf", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        html = pathlib.Path(res["report"]).read_text(encoding="utf-8")
        self.assertIn('id="egx-data"', html)
        self.assertIn("Tarek Fouad", html)
        self.assertRegex(pathlib.Path(res["report"]).name, r"^EGX_Scan_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.html$")
        self.assertIn("DEMO1", run("search", "--ticker", "DEMO1", env=self.env).stdout)
        one = json.loads(run("read", pathlib.Path(res["report"]).name, "--ticker", "DEMO1", "--compact", env=self.env).stdout)
        self.assertEqual(one["stock"]["tk"], "DEMO1")
        self.assertNotIn("candles", one["stock"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
