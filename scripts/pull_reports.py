#!/usr/bin/env python3
"""
Refresh the trip-report index only. Cheap enough to run daily.

This is the ONLY thing that changes day to day: new condition reports land on
RopeWiki regularly, especially in canyoning season. The canyon roster and beta
(approach/exit prose, ACA ratings) change rarely, so re-crawling all 314 canyons
daily would hammer a volunteer wiki for data that's almost always identical.

This script pulls just the Conditions: namespace titles (batched, ~one call per
500) and rewrites data/all_condition_titles.json. build_data.py then derives the
"Latest report" column from that file offline. Unlike pull_beta.py, this always
refreshes -- no cache guard -- because freshness is the whole point.

Usage: python3 scripts/pull_reports.py
"""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "canyon-experience-matrix/1.0 (personal trip planning; +https://github.com/BOOMCHOPALAKA)"}
API = "https://ropewiki.com/api.php"


def api(params, retries=6):
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # exponential backoff: 1,2,4,8,16s


def all_condition_titles():
    """Every page in RopeWiki's Conditions: namespace (190), batched 500 at a time.
    Titles look like 'Conditions:<Canyon Name>-YYYYMMDDHHMMSS'."""
    titles, cont = [], None
    while True:
        params = {"action": "query", "list": "allpages", "apnamespace": 190, "aplimit": 500}
        if cont:
            params["apcontinue"] = cont
        d = api(params)
        titles += [p["title"] for p in d["query"]["allpages"]]
        cont = d.get("continue", {}).get("apcontinue")
        if not cont:
            break
        time.sleep(0.15)
    return titles


def main():
    titles = all_condition_titles()
    p = os.path.join(DATA, "all_condition_titles.json")
    json.dump(titles, open(p, "w"))
    print(f"-> {len(titles)} condition-report titles cached to {p}")


if __name__ == "__main__":
    main()
