#!/usr/bin/env python3
"""
Multi-region wasp-evidence scan (research, not part of the site build).

Question: do canyoneers report wasps from brushy approach/exit terrain, or from
in-canyon features (anchors, downclimbs)? Washington alone gave 8 mentions in 625
reports -- too thin. This widens the corpus across regions with different terrain
character, using the desert canyons as a natural control: if bushwhack exposure
drives wasp encounters, brushy PNW should light up and slickrock should not.

Caches every network pull to data/. Re-runs read the cache; delete it to refresh.
Polite: same rate limits as pull_and_score.py.

Usage: python3 scripts/wasp_multiregion_scan.py
"""
import json, re, os, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "canyon-experience-matrix/1.0 (personal trip planning; +https://github.com/BOOMCHOPALAKA)"}
API = "https://ropewiki.com/api.php"

REGIONS = {
    "PNW-wet":   ["Washington", "Oregon"],
    "Desert":    ["Utah", "Arizona"],
    "Sierra":    ["California"],
}

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

def cached(name, fn):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        print(f"  [cache] {name}")
        return json.load(open(p))
    print(f"  [pull ] {name} ...")
    v = fn()
    json.dump(v, open(p, "w"), indent=0)
    return v

# --- rosters: canyon -> region -------------------------------------------------
def roster_for(region):
    d = api({"action": "ask",
             "query": f"[[Category:Canyons]][[Located in region.Located in region::{region}]]|limit=500"})
    return list(d.get("query", {}).get("results", {}).keys())

def build_rosters():
    out = {}
    for bucket, regions in REGIONS.items():
        for reg in regions:
            names = roster_for(reg)
            print(f"     {reg:12} {len(names):4} canyons")
            for n in names:
                out.setdefault(n, bucket)
            time.sleep(0.4)
    return out

# --- condition reports (site-wide, batched, cheap) -----------------------------
def all_condition_titles():
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

def field(wt, name):
    m = re.search(name + r"=(.*?)(?:\n?\||\}\})", wt, re.S)
    return m.group(1).strip() if m else ""

def fetch_reports(titles):
    reports = []
    for i in range(0, len(titles), 50):
        d = api({"action": "query", "prop": "revisions", "rvprop": "content",
                 "rvslots": "main", "titles": "|".join(titles[i:i + 50])})
        for pg in d.get("query", {}).get("pages", {}).values():
            revs = pg.get("revisions", [])
            if not revs:
                continue
            wt = revs[0].get("slots", {}).get("main", {}).get("*", "") or revs[0].get("*", "")
            reports.append({
                "canyon": re.sub(r"-\d{14}$", "", pg.get("title", "").replace("Conditions:", "")),
                "date": field(wt, "Date"), "by": field(wt, "ReportedBy"),
                "comment": re.sub(r"\s+", " ", field(wt, "Comments")),
            })
        if i % 500 == 0:
            print(f"     {i}/{len(titles)} reports")
        time.sleep(0.2)
    return reports

# --- classification ------------------------------------------------------------
NOUN = re.compile(r"\b(wasps?|hornets?|yellow[\s-]?jackets?|yellowjackets?|bees?|beehive|"
                  r"bald[\s-]?faced|paper wasp)\b", re.I)
EVENT = re.compile(r"\b(stung|stings?|stinging|swarm\w*|nests?|hive|buzzing|attacked)\b", re.I)
NOTBUG = re.compile(r"\b(bird|eagle|osprey|hawk|rat|wood\s?rat|mouse|ants?|nettles?|"
                    r"devil.?s\s+club|spider|yellowjacket creek)\b", re.I)

# where was it? approach/exit terrain vs. in-canyon feature
APPROACH_CTX = re.compile(r"\b(approach|hike\s?in|bushwhack\w*|brush|trail|hike\s?out|exit|"
                          r"scramble|ridge|slope|hillside|road|thrash\w*)\b", re.I)
CANYON_CTX = re.compile(r"\b(rappel|rap\b|r\d+|anchor|downclimb|down\s?climb|bolt|pothole|"
                        r"pool|drop|slide|chute|falls?|webbing|log rappel|dcl|dcr)\b", re.I)

def classify_location(comment):
    """Look at the words near the wasp mention, not the whole report."""
    m = NOUN.search(comment) or EVENT.search(comment)
    if not m:
        return "unknown"
    ctx = comment[max(0, m.start() - 130): m.end() + 130]
    a, c = len(APPROACH_CTX.findall(ctx)), len(CANYON_CTX.findall(ctx))
    if a > c: return "approach/exit"
    if c > a: return "in-canyon"
    return "ambiguous" if (a or c) else "unknown"

def main():
    os.makedirs(DATA, exist_ok=True)
    print("1. Rosters by region")
    rosters = cached("multiregion_rosters.json", build_rosters)
    print(f"   -> {len(rosters)} canyons across {len(REGIONS)} buckets")
    print(Counter(rosters.values()))

    print("\n2. Condition report titles (site-wide)")
    titles = cached("all_condition_titles.json", all_condition_titles)
    print(f"   -> {len(titles)} total reports on RopeWiki")

    # only fetch reports for canyons in our sampled regions
    want = {t: re.sub(r"-\d{14}$", "", t.replace("Conditions:", "")) for t in titles}
    keep = [t for t, c in want.items() if c in rosters]
    print(f"   -> {len(keep)} belong to sampled regions (fetching those only)")

    print("\n3. Fetching reports")
    reports = cached("multiregion_reports.json", lambda: fetch_reports(keep))
    print(f"   -> {len(reports)} reports cached")

    print("\n4. Scanning for wasp evidence")
    hits = []
    for r in reports:
        c = r.get("comment") or ""
        if not c:
            continue
        n, e = NOUN.search(c), EVENT.search(c)
        if not n:                      # require an actual insect noun
            continue
        if NOTBUG.search(c) and not n: # other critters' nests
            continue
        r = {**r, "region": rosters.get(r["canyon"], "?"),
             "where": classify_location(c), "has_event": bool(e)}
        hits.append(r)

    json.dump(hits, open(os.path.join(DATA, "multiregion_wasp_hits.json"), "w"), indent=1)

    # ---- report ----
    per_region_reports = Counter(rosters.get(r["canyon"], "?") for r in reports)
    per_region_hits = Counter(h["region"] for h in hits)
    print("\n" + "=" * 64)
    print("RATE BY REGION  (the bushwhack hypothesis's real test)")
    print("=" * 64)
    print(f"{'region':12} {'reports':>8} {'wasp':>6} {'rate':>7}")
    for reg in list(REGIONS) + ["?"]:
        n, h = per_region_reports.get(reg, 0), per_region_hits.get(reg, 0)
        if n:
            print(f"{reg:12} {n:8} {h:6} {100*h/n:6.2f}%")

    print("\n" + "=" * 64)
    print("WHERE WAS THE WASP?  (in-canyon vs. approach/exit terrain)")
    print("=" * 64)
    for w, n in Counter(h["where"] for h in hits).most_common():
        print(f"  {w:16} {n:3}")

    print("\n  cross-tab: region x location")
    ct = defaultdict(Counter)
    for h in hits:
        ct[h["region"]][h["where"]] += 1
    for reg, c in ct.items():
        print(f"  {reg:12} {dict(c)}")

    print("\n" + "=" * 64)
    print("ALL HITS")
    print("=" * 64)
    for h in sorted(hits, key=lambda x: (x["region"], x["canyon"])):
        print(f"\n[{h['region']} | {h['where']}] {h['canyon']} — {h['date']}")
        print(f"   {h['comment'][:230]}")

if __name__ == "__main__":
    main()
