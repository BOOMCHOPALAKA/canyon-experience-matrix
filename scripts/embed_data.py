#!/usr/bin/env python3
"""Embed data/canyons.json inline into index.html (the page loads no external files)."""
import json, os

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
open(os.path.join(ROOT, "index.html"), "w").write(html)
print(f"embedded {len(data)} canyons into index.html")
