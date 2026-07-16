#!/usr/bin/env python3
"""
Canyon Experience Matrix — data pipeline.

Pulls every Washington canyon from RopeWiki, plus all dated condition reports,
scores each canyon on Access (approach/exit effort), Difficulty (ACA grade),
and seasonal Wasp exposure, and writes data/canyons.json for the web matrix.

RopeWiki data is CC BY-NC-SA 3.0 (https://creativecommons.org/licenses/by-nc-sa/3.0/).
This is a non-commercial derivative. Be polite: the script rate-limits itself.

Usage:  python3 scripts/pull_and_score.py
Output: data/canyons.json, data/condition_reports_raw.json, data/wasp_reports.json
"""
import json, re, time, os, urllib.parse, urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "canyon-experience-matrix/1.0 (personal trip planning; +https://github.com/BOOMCHOPALAKA)"}
API = "https://ropewiki.com/api.php"

def api(params, retries=3):
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))

# ---------------------------------------------------------------------------
# 1. Roster: every canyon located in Washington
# ---------------------------------------------------------------------------
def get_roster():
    d = api({"action": "ask",
             "query": "[[Category:Canyons]][[Located in region.Located in region::Washington]]|limit=500"})
    return list(d.get("query", {}).get("results", {}).keys())

# ---------------------------------------------------------------------------
# 2. Structured fields per canyon (browsebysubject returns real property IDs)
# ---------------------------------------------------------------------------
WANT = {"Has_rating", "Has_star_rating", "Has_best_season", "Has_number_of_rappels",
        "Has_longest_rappel", "Has_ACA_rating", "Has_info_major_region",
        "Has_condition_date", "Has_url", "Requires_permits"}

def get_structured(name):
    d = api({"action": "browsebysubject", "subject": name})
    rec = {}
    for item in d.get("query", {}).get("data", []):
        p = item.get("property", "")
        if p in WANT:
            vals = item.get("dataitem", [])
            rec[p] = vals[0].get("item", "") if vals else ""
    return rec

# ---------------------------------------------------------------------------
# 3. Approach / Exit prose (for access + wasp-terrain scoring)
# ---------------------------------------------------------------------------
def section(wt, names):
    for nm in names:
        m = re.search(r"==+\s*" + nm + r"\s*==+(.*?)(?=\n==[^=]|\Z)", wt, re.I | re.S)
        if m:
            txt = re.sub(r"\[\[|\]\]|\{\{[^}]*\}\}|<[^>]+>|\[https?://\S+", "", m.group(1))
            return re.sub(r"\s+", " ", txt).strip()
    return ""

def get_approach_exit(name):
    d = api({"action": "parse", "page": name, "prop": "wikitext"})
    wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
    return section(wt, ["Approach"]), section(wt, ["Exit", "Exits"])

# ---------------------------------------------------------------------------
# 4. Condition reports (dated trip logs — the wasp evidence layer)
# ---------------------------------------------------------------------------
def get_all_condition_titles():
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
        batch = titles[i:i + 50]
        d = api({"action": "query", "prop": "revisions", "rvprop": "content",
                 "rvslots": "main", "titles": "|".join(batch)})
        for pg in d.get("query", {}).get("pages", {}).values():
            revs = pg.get("revisions", [])
            if not revs:
                continue
            wt = revs[0].get("slots", {}).get("main", {}).get("*", "") or revs[0].get("*", "")
            title = pg.get("title", "")
            reports.append({
                "canyon": re.sub(r"-\d{14}$", "", title.replace("Conditions:", "")),
                "date": field(wt, "Date"), "by": field(wt, "ReportedBy"),
                "comment": re.sub(r"\s+", " ", field(wt, "Comments")),
            })
        time.sleep(0.2)
    return reports

# ---------------------------------------------------------------------------
# 5. Scoring
# ---------------------------------------------------------------------------
HARD = re.compile(r"\b(bushwhack|bush-whack|thrash|brushy?|overgrown|off.?trail|scramble|"
                  r"deadfall|downed (?:trees|logs)|talus|nettles?|devils?.?club|blackberr|"
                  r"slide alder|vine maple|thick|dense|steep(?:ly)?|thorny|loose|faint)\b", re.I)
EASY = re.compile(r"\b(road|trail|obvious|maintained|use trail|game trail|well.?marked|"
                  r"pavement|parking|walk up|walk down|short)\b", re.I)
INSECT = re.compile(r"\b(wasps?|hornets?|yellow[\s-]?jackets?|ground\s+wasps?|"
                    r"bees?\b(?![\s-]*line)|stinging|stung|sting)\b", re.I)
GAUGE = re.compile(r"yellowjacket creek", re.I)   # RopeWiki gauge name — not a bug sighting

def _dist(txt):
    ds = [float(m.group(1)) for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:mi\b|mile)", txt, re.I)]
    hike = [d for d in ds if d <= 6]
    return max(hike) if hike else None

def _access_seg(txt):
    """1 = trivial on-trail  →  5 = long/arduous. 50% effort (dist), 50% terrain."""
    if not txt or len(txt) < 40:
        return None
    d = _dist(txt)
    if d is None:      eff = 2
    elif d >= 4:       eff = 5
    elif d >= 2.5:     eff = 4
    elif d >= 1.5:     eff = 3
    elif d >= 0.75:    eff = 2
    else:              eff = 1
    hard, easy = len(HARD.findall(txt)), len(EASY.findall(txt))
    raw = hard * 1.3 - easy * 0.7
    ter = 1 if raw <= -1 else 2 if raw <= 0.8 else 3 if raw <= 2.5 else 4 if raw <= 4.5 else 5
    return max(1, min(5, round((eff + ter) / 2)))

def _wasp_terrain(ap, ex):
    """Terrain proxy for wasp habitat (NOT the dated log). 1-5."""
    both = ap + " " + ex
    if not both.strip():
        return None
    hard, easy = len(HARD.findall(both)), len(EASY.findall(both))
    raw = hard * 1.5 - easy * 0.7
    d = _dist(ap)
    if d:
        raw += min(d, 4) * 0.5
    return 1 if raw <= -1 else 2 if raw <= 1 else 3 if raw <= 3 else 4 if raw <= 5 else 5

def _difficulty(raw):
    """ACA technical grade → 1-4 + layman word. 1 beginner … 4 expert."""
    if not raw or raw in ("POI", "?", ""):
        return None, "not rated", raw or "?"
    s = raw.strip()
    m = re.match(r"\s*([1-4])", s)
    if not m:
        return None, "not rated", s
    tech = int(m.group(1))
    risk = "XX" if re.search(r"\bXX\b", s) else "X" if re.search(r"\bX\b", s) else "R" if re.search(r"\bR\b", s) else ""
    words = {1: "beginner-friendly", 2: "novice/intermediate", 3: "advanced", 4: "EXPERT ONLY"}
    word, d = words[tech], tech
    if risk in ("X", "XX"):
        word = word.split(" (")[0] + " ⚠ DANGER (X)"
        d = min(4, d + 1)
    elif risk == "R":
        word += " + some risk (R)"
    return d, word, s

def _has_wasp(comment):
    return bool(comment) and bool(INSECT.search(GAUGE.sub("", comment)))

def _year(date):
    m = re.match(r"(\d{4})", date or "")
    return int(m.group(1)) if m else None

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print("1/5  roster…")
    roster = get_roster()
    print(f"     {len(roster)} WA canyons")

    print("2/5  structured fields + approach/exit prose…")
    struct, prose = {}, {}
    for i, name in enumerate(roster):
        struct[name] = get_structured(name)
        try:
            prose[name] = get_approach_exit(name)
        except Exception:
            prose[name] = ("", "")
        if (i + 1) % 25 == 0:
            print(f"     {i+1}/{len(roster)}")
        time.sleep(0.15)

    print("3/5  condition reports…")
    all_titles = get_all_condition_titles()
    wa = set(roster)
    wa_titles = [t for t in all_titles
                 if re.sub(r"-\d{14}$", "", t.replace("Conditions:", "")) in wa]
    print(f"     {len(wa_titles)} WA condition reports")
    reports = fetch_reports(wa_titles)
    json.dump(reports, open(os.path.join(DATA, "condition_reports_raw.json"), "w"))

    print("4/5  wasp scan…")
    wasp_by = defaultdict(list)
    wasp_reports = []
    for r in reports:
        if _has_wasp(r["comment"]):
            wasp_reports.append(r)
            wasp_by[r["canyon"]].append(r["date"])
    json.dump(wasp_reports, open(os.path.join(DATA, "wasp_reports.json"), "w"))
    print(f"     {len(wasp_reports)} dated wasp reports across {len(wasp_by)} canyons")

    print("5/5  scoring…")
    W_DIFF, W_ACC = 0.6, 0.4   # default Adventure blend (Difficulty-led)
    out = []
    for name in roster:
        st, (ap, ex) = struct[name], prose[name]
        a_appr, a_exit = _access_seg(ap), _access_seg(ex)
        segs = [x for x in (a_appr, a_exit) if x is not None]
        a_total = round(max(segs) * 0.6 + (sum(segs) / len(segs)) * 0.4) if segs else None
        diff, diff_word, rating_raw = _difficulty(st.get("Has_rating", ""))
        wasp_exp = _wasp_terrain(ap, ex)
        thin = (a_appr is None and a_exit is None) or (len(ap) + len(ex) < 100)

        # Adventure = Difficulty + Access (wasp is a seasonal toggle in the UI, not baked in here)
        parts, wsum = [], 0
        if diff is not None:
            parts.append((diff / 4 * 5) * W_DIFF); wsum += W_DIFF
        if a_total is not None:
            parts.append(a_total * W_ACC); wsum += W_ACC
        adventure = round(sum(parts) / wsum, 1) if wsum else None

        wl = sorted(wasp_by.get(name, []), reverse=True)
        try:
            stars = float(st.get("Has_star_rating") or 0)
        except ValueError:
            stars = None

        out.append({
            "canyon": name, "url": st.get("Has_url", ""),
            "stars": stars, "season": st.get("Has_best_season", "") or "",
            "difficulty": diff, "diff_word": diff_word, "rating_raw": rating_raw,
            "acc_appr": a_appr, "acc_exit": a_exit, "acc_total": a_total,
            "appr_stat": _dist(ap) and f"{_dist(ap)}mi" or "short",
            "exit_stat": _dist(ex) and f"{_dist(ex)}mi" or "short",
            "wasp_exp": wasp_exp, "adventure": adventure,
            "wasp": len(wl), "wasp_note": wl[0] if wl else "",
            "thin": thin,
            "note": f"{'thin beta; ' if thin else ''}approach {a_appr or '?'}, exit {a_exit or '?'}"
                    + (f"; ⚠ wasp {wl[0]}" if wl else ""),
        })

    json.dump(out, open(os.path.join(DATA, "canyons.json"), "w"), indent=0)
    print(f"done — wrote data/canyons.json ({len(out)} canyons)")
    print("Note: index.html embeds this data inline; run scripts/embed_data.py to refresh the page.")

if __name__ == "__main__":
    main()
