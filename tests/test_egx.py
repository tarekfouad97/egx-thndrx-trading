#!/usr/bin/env python3
"""Tests for egx.py: step ledger, verdicts, allocate, check, report, index, search, read. Run: python3 tests/test_egx.py"""
import copy, json, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "egx-check" / "scripts"
EGX = SCRIPTS / "egx.py"
SAMPLE = ROOT / "examples" / "sample-run.json"
sys.path.insert(0, str(SCRIPTS))
import egx_gates as G  # noqa: E402
import egx_gates as G


def run(*args, env=None):
    return subprocess.run([sys.executable, str(EGX), *args], capture_output=True, text=True, env=env, cwd=ROOT)


def fresh(d, tmp, scan=True):
    """the sample as a run made right now: receipts, call log and screenshots dated after the ledger start"""
    t = int(time.time() * 1000)
    (tmp / "shots").mkdir(exist_ok=True)
    for s in d["stocks"]:
        src = ROOT / s.get("screenshot", "")
        if s.get("receipts"):
            for i, k in enumerate(("open", "analyse", "draw", "verify")):
                s["receipts"][k]["at"] = t + i * 100
        if src.is_file():
            dst = tmp / "shots" / src.name
            shutil.copy(src, dst); os.utime(dst, ((t + 1500) / 1000, (t + 1500) / 1000))
            s["screenshot"] = str(dst)
    d["calls"] = [[fn, None, t, 1] for fn in ("market", "page", "holdings", "marketPage")] + [["scan", s["tk"], t, 1] for s in d["stocks"]] \
        + [["chartRect", None, t + 400, 1], ["exportToPage", None, t + 2000, 1]]
    if scan:
        for s in d["stocks"]:
            if s.get("drop"):
                s.pop("category", None)
        st = copy.deepcopy(next(s for s in d["stocks"] if s["tk"] == "DEMO2"))
        h = next(h for h in d["holdings"] if h["tk"] == "DEMO2")
        h["analysis"] = {k: v for k, v in st.items() if k in ("tk", "title", "receipts", "plan", "page", "drop", "zones", "trend", "rs")}
        h.update({k: st[k] for k in ("news_queries", "news", "news_checked", "red_events_checked", "screenshot") if k in st})
        unknown = [f"U{i:02d}" for i in range(17)]
        d["lists"] = {"top30": ["DEMO2", "DEMO3", "DEMO4"] + unknown, "hot": ["DEMO1"], "t0": []}
        d["unknown"] = unknown
        d["lists_source"] = {"top30": {"kind": "market-cap"}, "hot_queries": [{"kind": k, "query": k + " query"} for k in ("corporate", "global", "industry")]}
        d["meta"]["t0_status"] = "Skipped: market closed"
    return sign(d)


def sign(d):
    """what EGX.exportToPage does: the checksum of every stock as exported"""
    for s in d["stocks"]:
        s["sig"] = G.sig_of(s)
    return d


SCAN_WALK = [("step", "done", "N0.1", "--proof", "15287 EGP for 2026-11-09"), ("step", "done", "N0.2", "--proof", "limit orders yes, no T0"),
             ("config",), ("step", "done", "C0.3", "--proof", "tab 7, chart visible, no login screen"), ("step", "done", "C0.4", "--proof", "EGX.version 3.3.1"),
             ("runs", "--last", "3"), ("open",), ("step", "add", "--block", "holding", "DEMO2"), ("recall", "DEMO2"), ("news", "DEMO2"),
             ("step", "done", "K6.1", "--tk", "H:DEMO2", "--proof", "moved to 120,400"), ("step", "done", "H2.1", "--proof", "no open orders"),
             ("step", "add", "DEMO1", "DEMO2"), ("recall", "DEMO1"), ("news", "DEMO1"), ("recall", "DEMO2"), ("news", "DEMO2"),
             ("step", "done", "K6.1", "--tk", "DEMO1", "--proof", "moved to 120,400"), ("step", "done", "C7.2", "--proof", "cleared")]


class EgxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.cfg_file = self.tmp / "config.json"; self.cfg_file.write_text("{}")   # never the user's own config
        self.env = {**os.environ, "EGX_REPORTS_DIR": str(self.tmp / "reports"), "EGX_STATE_DIR": str(self.tmp / "state"), "EGX_CONFIG": str(self.cfg_file)}
        self.run_file = self.tmp / "run.json"
        self.walk(self.tmp)

    def walk(self, folder, steps=SCAN_WALK):
        """a whole Scan through the ledger, up to the money step"""
        rf = folder / "run.json"
        self.assertEqual(self.go("step", "start", "scan", str(rf)).returncode, 0)
        rf.write_text(json.dumps(fresh(json.loads(SAMPLE.read_text(encoding="utf-8")), folder)), encoding="utf-8")
        for cmd in steps:
            r = self.go(*cmd)
            self.assertEqual((r.returncode, r.stderr), (0, ""), f"{cmd}: {r.stdout}{r.stderr}")
        r = self.go("manage", str(rf)); self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout)
        r = self.go("verdict", str(rf)); self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout)
        r = self.go("allocate", str(rf)); self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout)
        return rf

    def go(self, *args, env=None):
        return run(*args, env=env or self.env)

    def stocks(self):
        return {s["tk"]: s for s in json.loads(self.run_file.read_text())["stocks"]}

    def edit(self, fn, resign=True):
        d = json.loads(self.run_file.read_text()); fn(d); self.run_file.write_text(json.dumps(sign(d) if resign else d))

    # ---------------------------------------------------------------- step ledger
    def test_ledger_complete_run(self):
        self.assertEqual(self.go("check", str(self.run_file)).returncode, 0)
        r = self.go("step", "finish"); self.assertNotEqual(r.returncode, 0)        # report, files not done yet
        self.assertIn("✘ C9.2", r.stdout); self.assertIn("NOT COMPLETE", r.stdout)
        self.assertEqual(self.go("report", str(self.run_file), "--no-pdf").returncode, 0)
        self.assertEqual(self.go("step", "done", "C9.5", "--proof", "paths given in the answer").returncode, 0)
        r = self.go("step", "finish"); self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("COMPLETE: every atomic step is recorded", r.stdout); self.assertIn("0 failed, 0 open", r.stdout)
        self.assertIn("the answer must include", r.stdout)
        d = json.loads(self.run_file.read_text())
        self.assertEqual((d["steps"]["open"], d["steps"]["failed"]), (0, 0))        # the report carries the ledger
        self.assertFalse(d["holdings"][1].get("check_incomplete"))

    def test_drive_step_needs_every_file_recorded(self):
        self.cfg_file.write_text(json.dumps({"drive_folder_id": "FOLDER"}))
        tmp2 = self.tmp / "h"; tmp2.mkdir(); rf = self.walk(tmp2)
        self.assertEqual(self.go("check", str(rf)).returncode, 0)
        res = json.loads(self.go("report", str(rf), "--no-pdf").stdout)
        self.go("step", "done", "C9.5", "--proof", "paths given in the answer")
        r = self.go("step", "finish"); self.assertNotEqual(r.returncode, 0); self.assertIn("✘ C9.4", r.stdout)
        self.assertIn("REFUSED", self.go("step", "skip", "C9.4", "--reason", "no-drive-folder").stdout)
        for f in res["drive"]["files"]:
            self.go("drive-record", f["name"], "ID-" + f["name"])
        r = self.go("step", "finish"); self.assertEqual(r.returncode, 0, r.stdout)

    def test_t0_ledger(self):
        import egx_steps
        tmp2 = self.tmp / "t"; tmp2.mkdir(); rf = tmp2 / "run.json"
        self.go("step", "start", "check_t0", str(rf), "--tk", "DEMO1")
        d = fresh(json.loads(SAMPLE.read_text(encoding="utf-8")), tmp2, scan=False)
        s = next(s for s in d["stocks"] if s["tk"] == "DEMO1"); s["mode"] = "t0"; s["t0_eligible"] = True
        s["t0_eligibility"] = {"status": "confirmed", "how": "T0 option seen in ThndrX by the user"}
        r = s["receipts"]
        s["t0"] = {"plan": {"setup": "vwap-pullback", "entry": 35.5, "stop": 35.2, "target": 36.4, "rr": 3, "movePct": 2.5, "entryDistATR5": 0.2}, "screenshot": s["screenshot"],
                   "receipts": {"analyse": dict(r["analyse"]), "draw": dict(r["draw"], studies={"skipped": True}), "verify": dict(r["verify"])}}
        d["stocks"], d["holdings"], d["meta"]["command"] = [s], [], "Check T0"
        rf.write_text(json.dumps(sign(d)))
        for cmd in [("config",), ("step", "done", "C0.3", "--proof", "tab 7, chart visible"), ("step", "done", "C0.4", "--proof", "3.3.1"), ("open",),
                    ("recall", "DEMO1"), ("news", "DEMO1"), ("step", "done", "T6.1", "--tk", "DEMO1", "--proof", "moved to 100,300")]:
            self.assertEqual(self.go(*cmd).returncode, 0, cmd)
        out = self.go("step", "status").stdout
        self.assertIn("T6.4 DEMO1 open: EGX.daily() not called", out)                # the chart must go back to 1D
        at = r["analyse"]["at"]; now = egx_steps.cairo(at)
        in_window = now.weekday() not in (4, 5) and "10:15" <= now.strftime("%H:%M") <= "13:30"
        self.assertEqual("T2.4 DEMO1 open" in out, not in_window)                    # the clock is checked by the script, not by Claude
        d["calls"].append(["daily", None, at + 5000, 1]); rf.write_text(json.dumps(d))
        self.assertNotIn("T6.4", self.go("step", "status").stdout)

    def test_nothing_is_proven_on_an_empty_run(self):
        for i, (cmd, tk) in enumerate([("scan", []), ("check", ["--tk", "COMI"]), ("check_t0", ["--tk", "COMI"]), ("positions", []), ("market", [])]):
            tmp2 = self.tmp / f"z{i}"; tmp2.mkdir()
            self.go("step", "start", cmd, str(tmp2 / "run.json"), *tk)
            (tmp2 / "run.json").write_text(json.dumps({"stocks": [{"tk": "COMI"}], "holdings": [], "lists": {}, "market": {}, "meta": {}}))
            self.go("step", "sync")
            done = [json.loads(x) for x in (tmp2 / "run.ledger.jsonl").read_text().splitlines() if '"status": "done"' in x]
            self.assertEqual(done, [], cmd)                                         # an empty run proves nothing

    def test_order_is_enforced(self):
        tmp2 = self.tmp / "b"; tmp2.mkdir()
        self.go("step", "start", "check", str(tmp2 / "run.json"), "--tk", "COMI")
        r = self.go("step", "done", "C0.4", "--proof", "EGX.version 3.3.1")       # C0.1 config and C0.3 come first
        self.assertNotEqual(r.returncode, 0); self.assertIn("REFUSED: C0.1", r.stdout)
        r = self.go("recall", "COMI"); self.assertIn("K1.1 NOT RECORDED", r.stderr)  # a cmd step out of order is not counted
        self.go("config")
        self.assertNotEqual(self.go("step", "done", "C0.3", "--proof", "ok").returncode, 0)       # empty proof
        self.assertNotEqual(self.go("step", "done", "C0.3", "--proof", "done").returncode, 0)
        self.assertEqual(self.go("step", "done", "C0.3", "--proof", "tab 3, chart visible").returncode, 0)
        r = self.go("step", "done", "C0.4", "--proof", "version is fine")        # proof must carry the version
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.go("step", "done", "C0.4", "--proof", "3.3.1").returncode, 0)
        self.assertNotEqual(self.go("step", "done", "C0.4", "--proof", "3.3.1").returncode, 0)    # only once
        self.assertNotEqual(self.go("step", "done", "K2.1", "--tk", "COMI").returncode, 0)        # auto: needs the receipt

    def test_skip_only_for_listed_true_reasons(self):
        r = self.go("step", "skip", "K5.1", "--tk", "DEMO1", "--reason", "dropped")
        self.assertNotEqual(r.returncode, 0)                                          # already proven
        tmp2 = self.tmp / "c"; tmp2.mkdir()
        self.cfg_file.write_text(json.dumps({"drive_folder_id": "FOLDER"}))
        self.go("step", "start", "check", str(tmp2 / "run.json"), "--tk", "DEMO1")
        (tmp2 / "run.json").write_text(json.dumps({"stocks": [{"tk": "DEMO1", "plan": {"entry": 1, "stop": 0.9}}]}))
        r = self.go("step", "skip", "K5.1", "--tk", "DEMO1", "--reason", "dropped"); self.assertIn("did not drop", r.stdout)
        r = self.go("step", "skip", "K3.1", "--tk", "DEMO1", "--reason", "dropped"); self.assertIn("can never be skipped", r.stdout)
        r = self.go("step", "skip", "K5.1", "--tk", "DEMO1", "--reason", "failed-upstream"); self.assertIn("REFUSED", r.stdout)
        r = self.go("step", "skip", "C9.4", "--reason", "drive-off"); self.assertIn("needs --proof", r.stdout)

    def test_retry_once_then_wait(self):
        tmp2 = self.tmp / "d"; tmp2.mkdir(); rf = tmp2 / "run.json"
        self.go("step", "start", "check", str(rf), "--tk", "DEMO1")
        d = fresh(json.loads(SAMPLE.read_text(encoding="utf-8")), tmp2, scan=False)
        d["stocks"] = [s for s in d["stocks"] if s["tk"] == "DEMO1"]; d["holdings"] = []; d["meta"]["command"] = "Check"
        d["stocks"][0]["receipts"]["verify"].update(ok=False, problems=["stop missing"])
        rf.write_text(json.dumps(sign(d)))
        for cmd in [("config",), ("step", "done", "C0.3", "--proof", "tab 7, chart visible"), ("step", "done", "C0.4", "--proof", "3.3.1"), ("open",),
                    ("recall", "DEMO1"), ("news", "DEMO1")]:
            self.assertEqual(self.go(*cmd).returncode, 0, cmd)
        r = self.go("step", "fail", "K5.1", "--tk", "DEMO1", "--reason", "verify says stop missing"); self.assertIn("RETRY ONCE", r.stdout)
        r = self.go("step", "skip", "K6.1", "--tk", "DEMO1", "--reason", "failed-upstream"); self.assertIn("REFUSED", r.stdout)   # not failed yet
        r = self.go("step", "fail", "K5.1", "--tk", "DEMO1", "--reason", "still missing after the redraw"); self.assertIn("FAILED after the retry", r.stdout)
        st = self.go("step", "status").stdout                                           # the screenshot steps are closed by the script
        self.assertIn("K6 Screenshot ✔ 3/3", st); self.assertNotIn("✘ K6", st); self.assertIn("K7 Write-up ✔", st)
        self.go("step", "done", "C7.2", "--proof", "cleared")
        out = self.go("verdict", str(rf)).stdout
        s = json.loads(rf.read_text())["stocks"][0]
        self.assertEqual(s["verdict"], "wait"); self.assertIn("K5.1 failed", out)       # the answer names the atomic step
        self.go("check", str(rf)); self.go("report", str(rf), "--no-pdf"); self.go("step", "done", "C9.5", "--proof", "paths in the answer")
        r = self.go("step", "finish"); self.assertEqual(r.returncode, 0, r.stdout)       # a run with an honest failure can finish
        self.assertIn("FINISHED WITH 1 FAILED STEP", r.stdout); self.assertIn("✘ K5.1 DEMO1 failed", r.stdout)

    def test_missing_step_makes_wait(self):
        tmp2 = self.tmp / "e"; tmp2.mkdir(); rf = tmp2 / "run.json"
        self.go("step", "start", "check", str(rf), "--tk", "DEMO1")
        d = fresh(json.loads(SAMPLE.read_text(encoding="utf-8")), tmp2, scan=False)
        d["stocks"] = [s for s in d["stocks"] if s["tk"] == "DEMO1"]; d["holdings"] = []; d["meta"]["command"] = "Check"
        rf.write_text(json.dumps(sign(d)))
        for cmd in [("config",), ("step", "done", "C0.3", "--proof", "tab 7, chart visible"), ("step", "done", "C0.4", "--proof", "3.3.1"), ("open",),
                    ("recall", "DEMO1"), ("news", "DEMO1"), ("step", "done", "C7.2", "--proof", "cleared")]:
            self.assertEqual(self.go(*cmd).returncode, 0, cmd)
        out = self.go("verdict", str(rf)).stdout                                       # K6.1 (mouse off the chart) never recorded
        s = json.loads(rf.read_text())["stocks"][0]
        self.assertEqual(s["verdict"], "wait"); self.assertIn("K6.1", out)
        self.assertEqual(self.go("step", "done", "K6.1", "--tk", "DEMO1", "--proof", "moved to 100,300").returncode, 0)
        self.go("verdict", str(rf)); self.assertEqual(json.loads(rf.read_text())["stocks"][0]["verdict"], "valid")

    def test_stale_receipts_are_not_proof(self):
        def old(d):
            for k in ("open", "analyse", "draw", "verify"):
                d["stocks"][0]["receipts"][k]["at"] -= 3600 * 1000
        self.edit(old); out = self.go("verdict", str(self.run_file)).stdout
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait"); self.assertIn("no longer holds", out)

    def test_edited_ledger_is_rejected(self):
        led = self.tmp / "run.ledger.jsonl"
        lines = led.read_text().splitlines()
        rec = json.loads(lines[3]); rec["proof"] = "typed by hand"; lines[3] = json.dumps(rec)
        led.write_text("\n".join(lines) + "\n")
        r = self.go("check", str(self.run_file)); self.assertNotEqual(r.returncode, 0); self.assertIn("edited by hand", r.stdout)
        self.assertNotEqual(self.go("report", str(self.run_file), "--no-pdf").returncode, 0)
        self.assertNotEqual(self.go("step", "status").returncode, 0)

    def test_no_ledger_no_report(self):
        (self.tmp / "run.ledger.jsonl").unlink()
        r = self.go("report", str(self.run_file), "--no-pdf"); self.assertNotEqual(r.returncode, 0); self.assertIn("no step ledger", r.stderr)

    def test_open_run_step_blocks_report(self):
        tmp2 = self.tmp / "f"; tmp2.mkdir(); rf = tmp2 / "run.json"
        self.go("step", "start", "scan", str(rf))
        rf.write_text(json.dumps(fresh(json.loads(SAMPLE.read_text(encoding="utf-8")), tmp2)))
        for cmd in SCAN_WALK[:-1]:                                                    # C7.2 (clearExport) left open
            self.go(*cmd)
        self.go("verdict", str(rf)); self.go("allocate", str(rf))
        r = self.go("report", str(rf), "--no-pdf"); self.assertNotEqual(r.returncode, 0); self.assertIn("step C7.2 open", r.stderr)

    def test_scan_lists_cannot_lose_a_ticker(self):
        self.edit(lambda d: d["lists"]["top30"].append("GONE1"))
        r = self.go("check", str(self.run_file)); self.assertNotEqual(r.returncode, 0)   # changed after it was proven
        self.assertIn("N5.1 no longer holds", r.stdout)
        tmp2 = self.tmp / "g"; tmp2.mkdir(); rf = tmp2 / "run.json"
        self.go("step", "start", "scan", str(rf))
        d = fresh(json.loads(SAMPLE.read_text(encoding="utf-8")), tmp2); d["lists"]["top30"].append("GONE1"); rf.write_text(json.dumps(d))
        for cmd in SCAN_WALK:
            self.go(*cmd)
        r = self.go("step", "status"); self.assertIn("N5.1", r.stdout); self.assertIn("GONE1", r.stdout)

    def test_skill_ids_match_manifest(self):
        import re
        M = json.loads((ROOT / "skills" / "egx-check" / "references" / "steps.json").read_text(encoding="utf-8"))
        ids = {a["id"] for st in M["steps"].values() for a in st["atoms"]}
        text = (ROOT / "skills" / "egx-check" / "SKILL.md").read_text(encoding="utf-8") + (ROOT / "skills" / "egx-scan" / "SKILL.md").read_text(encoding="utf-8")
        in_skill = set(re.findall(r"\b([A-Z]\d{1,2}\.\d)\b", text))
        self.assertEqual(ids - in_skill, set(), "atomic steps missing from the SKILL.md files")
        self.assertEqual(in_skill - ids, set(), "SKILL.md names atomic steps that are not in steps.json")
        import egx_steps, egx
        js = (SCRIPTS / 'egx_chart.js').read_text()
        self.assertIn("const VERSION = '" + egx.VERSION + "'", js)
        self.assertTrue(egx.VERSION.startswith(egx_steps.SCRIPT_MM + '.'))
        version_step = next(a for st in M['steps'].values() for a in st['atoms'] if a['id']=='C0.4')
        self.assertRegex(egx.VERSION, version_step['proof_re'])
        for a in (a for st in M["steps"].values() for a in st["atoms"]):
            self.assertIn(a["proof"], ("auto", "cmd", "attest"), a["id"])
            self.assertIn(a["blocks"], ("verdict", "report", "finish"), a["id"])
            if a["proof"] == "auto":
                self.assertIn(a["check"], egx_steps.CHECKS, a["id"])
            for r in a.get("skip_if", []):
                self.assertIn(r, M["skip_reasons"], a["id"])

    # ---------------------------------------------------------------- existing behaviour
    def test_fees(self):
        out = json.loads(self.go("fees", "4981").stdout)
        self.assertAlmostEqual(out["fees_per_side"], 11.72, places=2)

    def test_check_sample(self):
        self.assertEqual(self.go("check", str(self.run_file)).returncode, 0)

    def test_allocate_rules(self):
        r = self.go("allocate", str(self.run_file))
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
        self.edit(cat); out = self.go("verdict", str(self.run_file)).stdout
        st = self.stocks()
        self.assertEqual((st["DEMO1"]["rank"], st["DEMO2"]["rank"]), (1, 2))  # valid before wait
        self.assertIn("top30: #1 DEMO1, #2 DEMO2", out)

    def test_hand_verdict_rejected(self):
        self.edit(lambda d: d["stocks"][2].update(verdict="valid"))  # DEMO3 R:R < 2
        self.assertNotEqual(self.go("check", str(self.run_file)).returncode, 0)

    def test_upgrade_override_rejected(self):
        self.edit(lambda d: d["stocks"][1].update(override={"verdict": "wait", "reason": "x"}))
        self.assertEqual(self.go("verdict", str(self.run_file)).returncode, 0)  # wait -> wait is fine
        self.edit(lambda d: d["stocks"][0].update(override={"verdict": "not_valid", "reason": "results rumour"}))
        self.go("verdict", str(self.run_file)); self.assertEqual(self.stocks()["DEMO1"]["verdict"], "not_valid")

    def test_screenshot_before_verify_fails_gate(self):
        def late(d):
            d["stocks"][0]["receipts"]["verify"]["at"] += 3600 * 1000
        self.edit(late); self.go("verdict", str(self.run_file))
        s = self.stocks()["DEMO1"]
        self.assertEqual(s["verdict"], "wait")
        self.assertFalse(next(g for g in s["gates"] if g["gate"] == "screenshot")["ok"])

    def test_missing_draw_fails_gate(self):
        self.edit(lambda d: d["stocks"][0]["receipts"].pop("verify")); self.go("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")

    def test_news_whitelist_and_languages(self):
        self.edit(lambda d: d["stocks"][0]["news"][0].update(url="https://randomblog.example/x")); self.go("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")
        self.assertNotEqual(self.go("check", str(self.run_file)).returncode, 0)

    def test_one_language_queries_fail(self):
        self.edit(lambda d: d["stocks"][0].update(news_queries=[{"query": "a"}, {"query": "b"}])); self.go("verdict", str(self.run_file))
        self.assertEqual(self.stocks()["DEMO1"]["verdict"], "wait")

    def test_rumour_catalyst(self):
        self.edit(lambda d: d["catalysts"][0].update(type="acquisition"))  # one Tier-2 source only
        self.assertNotEqual(self.go("check", str(self.run_file)).returncode, 0)

    def test_t0_verdicts(self):
        import datetime as dt
        import egx, egx_gates
        cairo = lambda hh, mm: int(dt.datetime(2026, 11, 8, hh - 2, mm, tzinfo=dt.timezone.utc).timestamp() * 1000)  # Cairo = UTC+2 in Nov
        d = json.loads(self.run_file.read_text())
        s = json.loads(json.dumps(d["stocks"][0])); s["mode"] = "t0"; s["t0_eligible"] = True
        r = s["receipts"]
        s["t0"] = {"session": {"day": "2026-11-08"}, "last": 35.6, "vwap": 35.4, "vsEGX30": 0.5, "screenshot": s["screenshot"],
                   "plan": {"setup": "vwap-pullback", "entry": 35.5, "stop": 35.2, "target": 36.4, "rr": 3, "movePct": 2.5, "entryDistATR5": 0.2, "trigger": "x"},
                   "receipts": {"analyse": dict(r["analyse"], at=cairo(11, 5)), "draw": dict(r["draw"], studies={"skipped": True}), "verify": r["verify"]}}
        d["stocks"] = [s]  # Sunday 2026-11-08
        cfg, wl = egx.DEFAULT_CONFIG, egx_gates.whitelist(SCRIPTS.parent)
        def verdict():
            sign(d)
            return egx_gates.compute(s, d, wl, cfg, egx.fees_side, lambda _s: (True, ""))[0]
        res = verdict(); self.assertEqual(res["verdict"], "valid", res["reasons"])
        self.assertEqual(egx_gates.compute(s, d, wl, cfg, egx.fees_side)[0]["verdict"], "wait")  # no ledger: never valid
        s['t0']['session']['day']='2026-11-05'
        self.assertEqual(verdict()['verdict'],'wait')
        s['t0']['session']['day']='2026-11-08'
        s["t0"]["receipts"]["analyse"]["at"] = cairo(13, 45); self.assertEqual(verdict()["verdict"], "wait")  # read after the 13:30 cut-off
        s["t0"]["receipts"]["analyse"]["at"] = cairo(11, 5); s["t0_eligible"] = False
        self.assertEqual(verdict()["verdict"], "wait")  # eligibility not confirmed
        s["t0_eligible"] = True; s["t0"]["plan"].update(target=35.55, movePct=0.14)
        self.assertEqual(verdict()["verdict"], "dropped")  # fees eat the move
        s["t0"]["plan"].update(target=36.4, movePct=2.5); s["verdict"] = verdict()["verdict"]
        row = egx.allocate(d, cfg)["allocation"]["rows"][0]
        self.assertEqual((row["entry"], row["stop"]), (35.5, 35.2))  # sized from the 5-minute plan, not the daily one
        # fast signal: no screenshot needed, but the 5-minute read must be at most 5 minutes old
        s["t0"].pop("screenshot"); sign(d); at = cairo(11, 5)
        sig = lambda age_s: egx_gates.t0_signal(s, d, wl, cfg, egx.fees_side, at + age_s * 1000)
        self.assertEqual(verdict()["verdict"], "wait")                    # the full verdict still needs the screenshot
        self.assertEqual(sig(120)["verdict"], "valid")
        self.assertEqual(sig(301)["verdict"], "wait"); self.assertIn("fresh 5-minute read", sig(301)["wait_for"])
        s["t0_eligible"] = False; self.assertEqual(sig(60)["verdict"], "wait")   # every other rule still applies

    def test_memory_files(self):
        r = self.go("report", str(self.run_file), "--no-pdf")
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = self.tmp / "reports"
        for f in ("history.jsonl", "news.jsonl", "runs.jsonl"):
            self.assertTrue((rep / f).exists(), f)
        self.go("report", str(self.run_file), "--no-pdf")  # same run again: no duplicates
        hist = [json.loads(x) for x in (rep / "history.jsonl").read_text().splitlines()]
        self.assertEqual(len([h for h in hist if h["tk"] == "DEMO1" and "pos" not in h]), 1)
        rec = self.go("recall", "DEMO1").stdout
        self.assertIn("VALID", rec); self.assertIn("E 35.56", rec); self.assertIn("Arab Finance", rec)
        self.assertLess(len(rec), 1500)  # cheap to read
        rid = json.loads(r.stdout)["report"].rsplit("/", 1)[1].rsplit(".", 1)[0]
        self.assertIn("target", self.go("outcome", rid, "DEMO1", "target", "2026-11-12").stdout)
        self.go("report", str(self.run_file), "--no-pdf")  # outcome survives a rebuild
        self.assertIn("outcome: target 2026-11-12", self.go("recall", "DEMO1").stdout)
        self.assertIn("DEMO1", self.go("news", "DEMO1").stdout)
        self.assertIn("Scan", self.go("runs").stdout)
        html = pathlib.Path(json.loads(r.stdout)["report"]).read_text()
        self.assertNotIn("screenshot_b64", html.split('id="egx-data"')[1])  # data block has no pictures

    def test_drive_plan(self):
        self.cfg_file.write_text(json.dumps({"drive_folder_id": "FOLDER"}))
        env = self.env
        res = json.loads(self.go("report", str(self.run_file), "--no-pdf", env=env).stdout)
        names = {f["name"]: f for f in res["drive"]["files"]}
        self.assertEqual(res["drive"]["folder_id"], "FOLDER")
        self.assertTrue(names["history.jsonl"]["file_ref"].startswith("sha256:"))
        self.assertEqual(names["history.jsonl"]["action"], "create")
        self.go("drive-record", "history.jsonl", "ID123", env=env)
        res = json.loads(self.go("report", str(self.run_file), "--no-pdf", env=env).stdout)
        h = {f["name"]: f for f in res["drive"]["files"]}["history.jsonl"]
        self.assertEqual((h["action"], h["old_file_id"]), ("skip", "ID123"))  # same content: nothing to upload
        self.go("outcome", res["drive"]["files"][0]["name"].rsplit(".", 1)[0], "DEMO1", "stop", "2026-11-12", env=env)
        res = json.loads(self.go("report", str(self.run_file), "--no-pdf", env=env).stdout)
        h = {f["name"]: f for f in res["drive"]["files"]}["history.jsonl"]
        self.assertEqual((h["action"], h["old_file_id"]), ("replace", "ID123"))  # new copy, then trash the old one

    def test_report_recomputes_cached_allocation(self):
        d=json.loads(self.run_file.read_text())
        d['allocation']={'deployed':999999,'rows':[]}
        self.run_file.write_text(json.dumps(d))
        r=self.go('report',str(self.run_file),'--no-pdf')
        self.assertEqual(r.returncode,0,r.stderr)
        updated=json.loads(self.run_file.read_text())
        self.assertLessEqual(updated['allocation']['deployed'],updated['meta']['cash'])

    def test_no_force(self):
        self.edit(lambda d: d["stocks"][2].update(verdict="valid"))
        r = self.go("report", str(self.run_file), "--force")
        self.assertNotEqual(r.returncode, 0)

    def test_report_index_search_read(self):
        r = self.go("report", str(self.run_file), "--no-pdf")
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        html = pathlib.Path(res["report"]).read_text(encoding="utf-8")
        self.assertIn('id="egx-data"', html)
        self.assertIn("Tarek Fouad", html)
        self.assertRegex(pathlib.Path(res["report"]).name, r"^EGX_Scan_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.html$")
        self.assertIn("DEMO1", self.go("search", "--ticker", "DEMO1").stdout)
        one = json.loads(self.go("read", pathlib.Path(res["report"]).name, "--ticker", "DEMO1", "--compact").stdout)
        self.assertEqual(one["stock"]["tk"], "DEMO1")
        self.assertNotIn("candles", one["stock"])

    # ---------------------------------------------------------------- v3.2 rules
    def reverdict(self, fn, resign=True):
        self.edit(fn, resign); r = self.go("verdict", str(self.run_file)); return self.stocks()["DEMO1"], r

    def test_retyped_price_is_rejected(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0]["plan"].update(stop=34.0), resign=False)   # a stop typed differently from the export
        self.assertEqual(s["verdict"], "wait")
        self.assertIn("checksum mismatch", " ".join(s["auto_reasons"]))
        self.assertNotEqual(self.go("check", str(self.run_file)).returncode, 0)

    def test_missing_checksum_is_rejected(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0].pop("sig"), resign=False)
        self.assertEqual(s["verdict"], "wait")

    def test_checksum_matches_the_page_script(self):
        if not shutil.which("node"):
            self.skipTest("node not installed")
        out = subprocess.run(["node", str(ROOT / "tests" / "test_chart_rules.js")], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        st = json.loads(next(l for l in out.stdout.splitlines() if l.startswith("SIG "))[4:])
        self.assertEqual(G.sig_of(st), st["sig"])

    def test_down_trend_is_not_valid(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0]["trend"].update(daily="down"))
        self.assertEqual(s["verdict"], "wait"); self.assertIn("daily trend", s["wait_for"])

    def test_negative_or_unknown_rs_is_not_valid(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0]["rs"].update(rs20=-0.5))
        self.assertEqual(s["verdict"], "wait"); self.assertIn("RS20", s["wait_for"])
        s, _ = self.reverdict(lambda d: d["stocks"][0]["rs"].pop("rs20"))
        self.assertEqual(s["verdict"], "wait"); self.assertIn("relative strength", s["wait_for"])

    def test_unknown_event_date_waits(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0].update(red_events=[{"type": "results", "date": "unknown"}]))
        self.assertEqual(s["verdict"], "wait"); self.assertIn("results date is confirmed", s["wait_for"])

    def test_net_rr_after_fees_gate(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0]["plan"].update(target=37.77, rr=2.3))   # gross 2.3, net under 2
        self.assertEqual(s["verdict"], "wait"); self.assertIn("after fees", s["wait_for"]); self.assertLess(s["plan"]["rr_net"], 2)

    def test_price_above_max_entry_waits(self):
        s, _ = self.reverdict(lambda d: d["stocks"][0].update(livePrice=36.4))
        self.assertEqual(s["verdict"], "wait"); self.assertIn("max entry", s["wait_for"])

    def test_no_equity_sizes_nothing(self):
        self.edit(lambda d: d["meta"].update(equity=0)); self.go("allocate", str(self.run_file))
        al = json.loads(self.run_file.read_text())["allocation"]
        self.assertTrue(al["rows"]); self.assertTrue(all(r["shares"] == 0 for r in al["rows"])); self.assertTrue(al["warnings"])

    def test_open_risk_cap_and_slippage(self):
        def roomy(d):   # the sample has almost no cash, and its target is too near once stop slippage is counted
            d["meta"].update(cash=20000); d["stocks"][0]["plan"].update(target=40.0, rr=4.62)
        self.edit(roomy); self.go("verdict", str(self.run_file)); self.go("allocate", str(self.run_file))
        al = json.loads(self.run_file.read_text())["allocation"]
        self.assertLessEqual(al["open_risk_after"], al["open_risk_cap"] + 0.01)
        row = next(r for r in al["rows"] if r["shares"])
        self.assertGreater(row["slippage_if_stop"], 0)
        self.edit(lambda d: d["holdings"][1].update(price=30.0, stop=20.0, qty=1000))   # a holding already risks 10,000 > 4% of equity
        self.go("allocate", str(self.run_file))
        self.assertTrue(all(r["shares"] == 0 for r in json.loads(self.run_file.read_text())["allocation"]["rows"]))

    def test_unknown_sector_is_an_error(self):
        self.edit(lambda d: d["stocks"][0].update(sector="Banking"))
        r = self.go("check", str(self.run_file)); self.assertNotEqual(r.returncode, 0); self.assertIn("sector", r.stdout)

    # ---------------------------------------------------------------- exits in code (egx.py manage)
    def held(self, **kw):
        import egx_manage
        bars = [[f"2026-10-{d:02d}", 30, 30.5, 29.5, c] for d, c in zip(range(1, 31), kw.pop("closes", [30.0] * 30))]
        h = {"tk": "X", "price": 30.0, "avgPrice": 30.0, "qty": 101, "stop": 28.0, "first_stop": 28.0, "entry_date": "2026-10-20",
             "analysis": {"atr": 1.0, "zones": {"support": {"lo": 27.5, "hi": 28.2}, "lastSwingLow": ["2026-10-18", 28.4]}, "candles": bars}}
        h.update(kw)
        return egx_manage.decide(h)

    def test_manage_exit_rules(self):
        self.assertEqual(self.held(closes=[30.0] * 29 + [27.9])["rule"], "stop")
        self.assertEqual(self.held(stop=26.0, first_stop=26.0, closes=[30.0] * 29 + [26.9])["rule"], "support-break")
        self.assertEqual(self.held(news=[{"impact": "-", "material": True, "date": "2026-10-30", "title": "suspension"}])["action"], "exit")

    def test_manage_partial_then_trail_never_down(self):
        d = self.held(price=32.1)                                  # +1.05R
        self.assertEqual((d["action"], d["sell_shares"], d["new_stop"]), ("partial", 50, 30.0))
        d = self.held(price=34.0, partial_done=True, stop=30.0, closes=[30.0] * 25 + [31, 32, 33, 34.5, 34.0])
        self.assertEqual((d["action"], d["new_stop"]), ("tighten", 32.0))      # 34.5 - 2.5 ATR
        d = self.held(price=33.0, partial_done=True, stop=32.5, closes=[30.0] * 25 + [31, 32, 33, 34.5, 33.0])
        self.assertEqual((d["action"], d["new_stop"]), ("hold", None))         # candidates are below the stop: it stays

    def test_manage_time_stop(self):
        d = self.held(entry_date="2026-10-10", price=30.4)        # 20 sessions, +0.2R
        self.assertEqual((d["action"], d["rule"]), ("exit", "time-stop"))
        self.assertEqual(self.held(entry_date="2026-10-25", price=30.4)["action"], "hold")   # 5 sessions

    def test_manage_missing_facts_are_named(self):
        d = self.held(first_stop=None, stop=None, entry_date=None)
        self.assertEqual(d["rule"], "incomplete"); self.assertIn("first_stop", d["missing"]); self.assertEqual(d["new_stop"], 27.0)

    def test_hand_typed_action_is_rejected(self):
        self.edit(lambda d: d["holdings"][1].update(action="add"))
        r = self.go("check", str(self.run_file)); self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not match the rules", r.stdout)
        self.edit(lambda d: d["holdings"][1].pop("action_by"))
        self.assertIn("not set by egx.py", self.go("check", str(self.run_file)).stdout)

    def test_typed_steps_are_counted_apart(self):
        self.assertIn("typed by Claude", self.go("step", "status").stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
