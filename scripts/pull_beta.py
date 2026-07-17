#!/usr/bin/env python3
"""
Cache the raw approach/exit prose + structured fields for every WA canyon.

The original pull_and_score.py fetched this, scored it, and threw the prose away --
so every scoring change meant re-crawling RopeWiki. This caches the source text to
data/wa_beta.json once; re-scoring is then free and offline.

Usage: python3 scripts/pull_beta.py
"""
import json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "canyon-experience-matrix/1.0 (personal trip planning; +https://github.com/BOOMCHOPALAKA)"}
API = "https://ropewiki.com/api.php"

WANT = {"Has_rating", "Has_star_rating", "Has_best_season", "Has_number_of_rappels",
        "Has_longest_rappel", "Has_ACA_rating", "Has_info_major_region",
        "Has_condition_date", "Has_url", "Requires_permits"}


def api(params, retries=3):
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
            time.sleep(1.5 * (attempt + 1))


def roster():
    d = api({"action": "ask",
             "query": "[[Category:Canyons]][[Located in region.Located in region::Washington]]|limit=500"})
    return list(d.get("query", {}).get("results", {}).keys())


def structured(name):
    d = api({"action": "browsebysubject", "subject": name})
    rec = {}
    for item in d.get("query", {}).get("data", []):
        p = item.get("property", "")
        if p in WANT:
            vals = item.get("dataitem", [])
            rec[p] = vals[0].get("item", "") if vals else ""
    return rec


def section(wt, names):
    for nm in names:
        m = re.search(r"==+\s*" + nm + r"\s*==+(.*?)(?=\n==[^=]|\Z)", wt, re.I | re.S)
        if m:
            txt = re.sub(r"\[\[|\]\]|\{\{[^}]*\}\}|<[^>]+>|\[https?://\S+", "", m.group(1))
            return re.sub(r"\s+", " ", txt).strip()
    return ""


def beta(name):
    d = api({"action": "parse", "page": name, "prop": "wikitext"})
    wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
    return section(wt, ["Approach"]), section(wt, ["Exit", "Exits"])


def main():
    p = os.path.join(DATA, "wa_beta.json")
    if os.path.exists(p):
        print(f"[cache] {p} already exists -- delete it to re-pull.")
        return
    names = roster()
    print(f"{len(names)} WA canyons. Pulling beta (polite, ~0.5s each)...")
    out = []
    for i, n in enumerate(names, 1):
        st = structured(n)
        time.sleep(0.25)
        ap, ex = beta(n)
        time.sleep(0.25)
        out.append({"canyon": n, "structured": st, "approach": ap, "exit": ex})
        if i % 20 == 0:
            print(f"  {i}/{len(names)}")
    json.dump(out, open(p, "w"), indent=0)
    print(f"-> cached {len(out)} canyons to {p}")


if __name__ == "__main__":
    main()
