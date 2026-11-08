#!/usr/bin/env python3
"""Build egx_chart.loader.js: minified egx_chart.js wrapped so one paste both runs it and
caches it in the ThndrX tab's localStorage (key EGX_JS). Later sessions only run
  (0,eval)(localStorage.getItem('EGX_JS'))
Run after editing egx_chart.js:  python3 build_loader.py   (needs Node for npx terser; falls back to unminified)."""
import json, pathlib, re, shutil, subprocess, sys
here = pathlib.Path(__file__).resolve().parent
src = (here / "egx_chart.js").read_text(encoding="utf-8")
version = re.search(r"const VERSION = '([^']+)'", src).group(1)
code = src
if shutil.which("npx"):
    try:
        code = subprocess.run(["npx", "-y", "terser@5", str(here / "egx_chart.js"), "-c", "-m", "--comments", "false"],
                              check=True, capture_output=True, text=True).stdout
    except Exception as e:  # keep working without Node
        print("terser failed, using unminified source:", e, file=sys.stderr)
# function wrapper: no string escaping, and f.toString() gives the exact text to cache
loader = ("(()=>{const f=function(){" + code.strip().rstrip(";") + "};"
          "try{localStorage.setItem('EGX_JS','('+f.toString()+')()')}catch(e){};f();"
          "return 'EGX '+window.EGX.version+' loaded and cached'})()\n")
(here / "egx_chart.loader.js").write_text(loader, encoding="utf-8")
print(f"egx_chart.loader.js written: version {version}, {len(loader):,} bytes")
