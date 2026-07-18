#!/usr/bin/env python3
"""Embed data/canyons.json inline into index.html (the page loads no external files).

Also stamps the build date into the 'Data as of' span so viewers can see how
fresh the data is. The stamp sits between two HTML comment markers so a re-run
overwrites the previous date cleanly.
"""
import json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
html = open(os.path.join(ROOT, "index.html")).read()
data = json.load(open(os.path.join(ROOT, "data", "canyons.json")))
blob = "<script>window.CANYONS=" + json.dumps(data, separators=(",", ":")) + ";</script>"

start = html.find("<script>window.CANYONS=[")
end = html.find("];</script>", start) + len("];</script>")
if start == -1 or end == -1:
    raise SystemExit("Could not find the window.CANYONS script block in index.html")
html = html[:start] + blob + html[end:]

# Stamp the build date. Matches either the initial placeholder or a prior stamp.
today = datetime.date.today().strftime("%b %-d, %Y")
html, n = re.subn(r"Data as of <!--ASOF-->.*?<!--/ASOF-->|Data as of &lt;!--ASOF--&gt;",
                  f"Data as of <!--ASOF-->{today}<!--/ASOF-->", html, count=1)
if not n:
    print("  warning: 'Data as of' marker not found; stamp not updated")

open(os.path.join(ROOT, "index.html"), "w").write(html)
print(f"embedded {len(data)} canyons into index.html (data as of {today})")
