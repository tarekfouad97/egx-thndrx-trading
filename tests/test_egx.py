#!/usr/bin/env python3
"""Smoke tests for egx.py: allocate, check, report, index, search, read. Run: python3 tests/test_egx.py"""
import json, os, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EGX = ROOT / "skills" / "egx-thndrx-trade-check" / "scripts" / "egx.py"
SAMPLE = ROOT / "examples" / "sample-run.json"


def run(*args, env=None):
    return subprocess.run([sys.executable, str(EGX), *args], capture_output=True, text=True, env=env)


class EgxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.env = {**os.environ, "EGX_REPORTS_DIR": str(self.tmp / "reports")}
        self.run_file = self.tmp / "run.json"
        self.run_file.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

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

    def test_valid_needs_rr(self):
        d = json.loads(self.run_file.read_text())
        d["stocks"][2]["verdict"] = "valid"  # DEMO3 has R:R < 2
        self.run_file.write_text(json.dumps(d))
        self.assertNotEqual(run("check", str(self.run_file)).returncode, 0)

    def test_report_index_search_read(self):
        r = run("report", str(self.run_file), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        html = pathlib.Path(res["report"]).read_text(encoding="utf-8")
        self.assertIn('id="egx-data"', html)
        self.assertIn("Tarek Fouad", html)
        self.assertRegex(pathlib.Path(res["report"]).name, r"^EGX_Loop30_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.html$")
        self.assertIn("DEMO1", run("search", "--ticker", "DEMO1", env=self.env).stdout)
        one = json.loads(run("read", pathlib.Path(res["report"]).name, "--ticker", "DEMO1", "--compact", env=self.env).stdout)
        self.assertEqual(one["stock"]["tk"], "DEMO1")
        self.assertNotIn("candles", one["stock"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
