#!/usr/bin/env python3
"""
EGX ThndrX Trading - installer (macOS and Windows, also Linux).

    python3 install.py            # interactive
    python3 install.py --yes      # accept defaults (no questions)

What it does:
  1. checks Python (3.9+) and, optionally, Node.js (only needed for the MP4 recap and extra design skills)
  2. asks a few settings and writes skills/egx-thndrx-trade-check/config.json
  3. creates your reports folder with an empty index.csv
  4. builds dist/egx-thndrx-trading.plugin  -> drag into Claude (desktop / claude.ai) to install all 3 skills
     and dist/claude-ai-skills/*.zip         -> or upload each skill in Settings > Capabilities > Skills
  5. if Claude Code is on this computer, copies the skills into ~/.claude/skills
  6. optional extras with Node: Apple-design skill and the HyperFrames skills / renderer

Python itself: use install.sh (macOS / Linux) or install.ps1 / Install-Windows.bat (Windows);
they install Python first when it is missing, then run this file.
Only the Python standard library is used - nothing to pip install.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
SKILLS = ["egx-thndrx-trade-check", "loop-30", "loop-30-max"]
CHECK = ROOT / "skills" / "egx-thndrx-trade-check"
GREEN, RED, DIM, BOLD, END = ("\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m") if sys.stdout.isatty() and os.name != "nt" else ("",) * 5


def say(msg, color=""):
    print(f"{color}{msg}{END}")


def ask(q, default="", yes=False):
    if yes:
        return default
    try:
        a = input(f"{q} [{default}]: ").strip()
    except EOFError:
        a = ""
    return a or default


def step_python():
    v = sys.version_info
    if v < (3, 9):
        say(f"Python {v.major}.{v.minor} found; 3.9 or newer is needed. Run install.sh (macOS) or install.ps1 (Windows).", RED)
        sys.exit(1)
    say(f"✓ Python {v.major}.{v.minor}.{v.micro} ({platform.system()} {platform.machine()})", GREEN)


def step_node():
    node, npx = shutil.which("node"), shutil.which("npx")
    if not node or not npx:
        say("• Node.js not found - optional (MP4 recap + extra design skills). Mac: brew install node · Windows: winget install OpenJS.NodeJS.LTS", DIM)
        return False
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        say(f"✓ Node {out}", GREEN)
    except Exception:
        return False
    return True


def step_config(yes: bool) -> dict:
    ex = json.loads((CHECK / "config.example.json").read_text(encoding="utf-8"))
    cur_p = CHECK / "config.json"
    cur = json.loads(cur_p.read_text(encoding="utf-8")) if cur_p.exists() else {}
    cfg = {**ex, **cur}
    say(f"\n{BOLD}Settings{END} (Enter keeps the value in brackets)")
    cfg["user_name"] = ask("Your name", cfg.get("user_name") if cfg.get("user_name") != "Your name" else "", yes)
    cfg["language"] = ask("Report language ar / en", cfg.get("language", "ar"), yes)
    cfg["reports_dir"] = ask("Reports folder", cfg.get("reports_dir", "~/EGX-Reports"), yes)
    cfg["risk_pct"] = float(ask("Risk per trade % (1 = normal, 2 = high)", str(cfg.get("risk_pct", 1.0)), yes))
    cfg["trade_log_sheet_id"] = ask("Google Sheet id of your trade log (optional, see docs/SETUP.md)", cfg.get("trade_log_sheet_id", ""), yes)
    cfg["reports_repo"] = ask("Private GitHub repo for reports, e.g. you/egx-reports (optional)", cfg.get("reports_repo", ""), yes)
    cfg["footer"] = ex["footer"]  # credits stay with the author
    cur_p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"✓ config written: {cur_p.relative_to(ROOT)}", GREEN)
    return cfg


def step_reports(cfg):
    d = pathlib.Path(os.path.expanduser(cfg["reports_dir"]))
    d.mkdir(parents=True, exist_ok=True)
    idx = d / "index.csv"
    if not idx.exists():
        sys.path.insert(0, str(CHECK / "scripts"))
        from egx import INDEX_COLUMNS  # noqa: E402
        idx.write_text(",".join(INDEX_COLUMNS) + "\n", encoding="utf-8")
    say(f"✓ reports folder: {d}", GREEN)


def _zip_dir(src: pathlib.Path, zf: zipfile.ZipFile, prefix: str):
    for p in sorted(src.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store":
            zf.write(p, f"{prefix}{p.relative_to(src).as_posix()}")


def step_build():
    dist = ROOT / "dist"
    (dist / "claude-ai-skills").mkdir(parents=True, exist_ok=True)
    plugin = dist / "egx-thndrx-trading.plugin"
    with zipfile.ZipFile(plugin, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(ROOT / ".claude-plugin" / "plugin.json", ".claude-plugin/plugin.json")
        zf.write(ROOT / "README.md", "README.md")
        for s in SKILLS:
            _zip_dir(ROOT / "skills" / s, zf, f"skills/{s}/")
    for s in SKILLS:
        with zipfile.ZipFile(dist / "claude-ai-skills" / f"{s}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            _zip_dir(ROOT / "skills" / s, zf, f"{s}/")
    say(f"✓ built {plugin.relative_to(ROOT)} and dist/claude-ai-skills/*.zip", GREEN)
    return plugin


def step_claude_code(yes):
    home = pathlib.Path.home() / ".claude"
    if not home.exists() and not shutil.which("claude"):
        say("• Claude Code not found on this computer - skipped (use the .plugin file in the Claude app).", DIM)
        return
    if ask("Copy the skills into ~/.claude/skills for Claude Code? y/n", "y", yes).lower() != "y":
        return
    dst_root = home / "skills"
    dst_root.mkdir(parents=True, exist_ok=True)
    for s in SKILLS:
        dst = dst_root / s
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(ROOT / "skills" / s, dst, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    say(f"✓ Claude Code skills installed in {dst_root}", GREEN)


def step_extras(has_node, yes):
    if not has_node:
        return
    if ask("Install optional Node extras (Apple-design skill, HyperFrames skills for the MP4 recap)? y/n", "n", yes).lower() != "y":
        return
    for cmd in (["npx", "-y", "skills", "add", "emilkowalski/skills", "--skill", "apple-design", "-y"],
                ["npx", "-y", "hyperframes", "skills", "update"]):
        say("$ " + " ".join(cmd), DIM)
        try:
            subprocess.run(cmd, check=False, shell=(os.name == "nt"))
        except Exception as e:
            say(f"  skipped: {e}", DIM)


def main():
    ap = argparse.ArgumentParser(description="Install the EGX ThndrX trading skills")
    ap.add_argument("--yes", action="store_true", help="accept all defaults")
    ap.add_argument("--build-only", action="store_true", help="only build dist/ (no questions)")
    a = ap.parse_args()
    say(f"{BOLD}EGX ThndrX Trading - installer{END}  ({ROOT})")
    step_python()
    if a.build_only:
        step_build()
        return
    has_node = step_node()
    cfg = step_config(a.yes)
    step_reports(cfg)
    plugin = step_build()
    step_claude_code(a.yes)
    step_extras(has_node, a.yes)
    say(f"""
{BOLD}Next steps{END}
 1. Claude app (desktop or claude.ai): open a chat and drag in {plugin.relative_to(ROOT)}
    (or Settings > Capabilities > Skills > upload each zip in dist/claude-ai-skills).
 2. Install Claude in Chrome (https://claude.ai/chrome) and sign in to https://x.thndr.app in Chrome.
 3. Optional: import templates/EGX_Trade_Log_template.xlsx into Google Sheets, put its id in config
    (python3 install.py again) and connect Google Sheets in Claude.
 4. In Claude say: "check COMI", "my positions" or "Loop 30".
 Docs: docs/SETUP.md · Phone: docs/PHONE.md
""")


if __name__ == "__main__":
    main()
