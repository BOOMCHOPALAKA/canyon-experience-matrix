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


def _ask_names(query):
    d = api({"action": "ask", "query": query + "|limit=2000"})
    r = d.get("query", {}).get("results", {})
    return set(r.keys()) if isinstance(r, dict) else set()


def _region_chain(name):
    """Authoritative full-depth region list for a canyon, e.g.
    'North America;Pacific Northwest/United States;Washington;North Cascades;...'."""
    d = api({"action": "browsebysubject", "subject": name})
    for item in d.get("query", {}).get("data", []):
        if item.get("property") == "Has_info_regions":
            vals = item.get("dataitem", [])
            return vals[0].get("item", "") if vals else ""
    return ""


def roster():
    # RopeWiki's region tree is deeper than one hop under Washington. The old query
    # ([[Located in region.Located in region::Washington]]) only caught canyons whose
    # region sat DIRECTLY under Washington, dropping anything two levels deep
    # (e.g. Wallace River Canyon: Darrington Ranger District -> North Cascades -> Washington).
    # That undercounted WA to 119 of ~314. Fix: take the 1-hop OR 2-hop candidate pool,
    # then keep only canyons whose authoritative region chain actually contains "Washington".
    cand = (_ask_names("[[Category:Canyons]][[Located in region.Located in region::Washington]]")
            | _ask_names("[[Category:Canyons]][[Located in region.Located in region.Located in region::Washington]]"))
    wa = []
    for nm in sorted(cand):
        toks = [t.strip() for t in _region_chain(nm).replace("/", ";").split(";")]
        if "Washington" in toks:
            wa.append(nm)
        time.sleep(0.15)
    return wa


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

    # Cache the roster so a network blip mid-pull doesn't force re-running the
    # ~314 region-check calls. Delete roster.json to re-derive the WA canyon list.
    rp = os.path.join(DATA, "roster.json")
    if os.path.exists(rp):
        names = json.load(open(rp))
        print(f"[cache] roster.json -> {len(names)} WA canyons")
    else:
        names = roster()
        json.dump(names, open(rp, "w"))
        print(f"{len(names)} WA canyons (cached to roster.json)")

    # Resume support: keep partial progress in wa_beta.partial.json so a failure
    # after N canyons only re-pulls the remainder, not all 314.
    part = os.path.join(DATA, "wa_beta.partial.json")
    out = json.load(open(part)) if os.path.exists(part) else []
    done = {r["canyon"] for r in out}
    if done:
        print(f"[resume] {len(done)} already pulled; continuing")
    print("Pulling beta (polite, ~0.5s each)...")
    for i, n in enumerate(names, 1):
        if n in done:
            continue
        st = structured(n)
        time.sleep(0.25)
        ap, ex = beta(n)
        time.sleep(0.25)
        out.append({"canyon": n, "structured": st, "approach": ap, "exit": ex})
        if i % 20 == 0:
            json.dump(out, open(part, "w"), indent=0)  # checkpoint
            print(f"  {i}/{len(names)}")
    json.dump(out, open(p, "w"), indent=0)
    if os.path.exists(part):
        os.remove(part)
    print(f"-> cached {len(out)} canyons to {p}")


if __name__ == "__main__":
    main()
