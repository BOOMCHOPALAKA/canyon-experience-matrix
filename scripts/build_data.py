#!/usr/bin/env python3
"""
Build data/canyons.json from the cached beta + condition reports. Offline.

  python3 scripts/pull_beta.py    # once -- caches RopeWiki beta to data/wa_beta.json
  python3 scripts/build_data.py   # re-score anytime, no network
  python3 scripts/embed_data.py   # inline into index.html
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.path.join(HERE, "..", "data")

from scoring import access_segment, access_total, wasp_exposure, parse_aca, ACA_TIME


def rd(v, n=1):
    return None if v is None else round(v, n)


def nest_notes():
    """canyon -> [(date, what was found)] from the real wasp reports."""
    out = collections.defaultdict(list)
    p = os.path.join(DATA, "wasp_reports.json")
    if not os.path.exists(p):
        return out
    for r in json.load(open(p)):
        c = r.get("comment") or ""
        # pull the clause naming the nest so the log cell can say WHERE, not "1x"
        m = re.search(r"[^.;]*\b(nest|hive|wasps?|hornets?|yellow[\s-]?jackets?|bees?)\b[^.;]*", c, re.I)
        frag = re.sub(r"\s+", " ", m.group(0)).strip() if m else ""
        if len(frag) > 105:
            frag = frag[:102].rsplit(" ", 1)[0] + "..."
        yr = (re.match(r"(\d{4})", r.get("date") or "") or [None, ""])[1] if re.match(r"(\d{4})", r.get("date") or "") else ""
        out[r["canyon"]].append({"year": yr, "what": frag, "date": r.get("date", "")})
    return out


def latest_reports():
    """canyon -> {date, url, count} from RopeWiki's Conditions: namespace.

    Titles look like 'Conditions:<Canyon Name>-YYYYMMDDHHMMSS'. We match the stem
    EXACTLY against the canyon name -- fuzzy matching cross-attributes reports
    between distinct same-named canyons (Big Creek Sierra NF vs. ours), which is
    worse than showing 'no report'. Date shown is the newest report's date.
    """
    out = {}
    p = os.path.join(DATA, "all_condition_titles.json")
    if not os.path.exists(p):
        return out
    pat = re.compile(r"^Conditions:(.+)-(\d{14})$")
    by_canyon = collections.defaultdict(list)
    for t in json.load(open(p)):
        m = pat.match(t)
        if m:
            by_canyon[m.group(1)].append((m.group(2), t))
    for name, reps in by_canyon.items():
        reps.sort(reverse=True)  # newest first by the YYYYMMDDHHMMSS timestamp
        ts, title = reps[0]
        out[name] = {
            "date": f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}",
            "url": "https://ropewiki.com/" + title.replace(" ", "_"),
            "count": len(reps),
        }
    return out


def approach_stat(txt, seg_why):
    """Never say 'short' when we mean 'we could not tell' -- the old build did."""
    if seg_why is None or seg_why.get("trail") is None:
        return "no beta"
    d, v = seg_why.get("dist_mi"), seg_why.get("vert_ft")
    bits = []
    if d is not None:
        bits.append(f"{d:g}mi")
    if v is not None:
        bits.append(f"{int(v)}ft")
    return " · ".join(bits) if bits else "distance not stated"


def main():
    beta = json.load(open(os.path.join(DATA, "wa_beta.json")))
    notes = nest_notes()
    reports = latest_reports()
    out = []
    for b in beta:
        name, st = b["canyon"], b["structured"]
        a, wa = access_segment(b["approach"])
        e, we = access_segment(b["exit"])
        acc = access_total(a, e)
        nl = notes.get(name, [])
        w, ww = wasp_exposure(b["approach"], b["exit"], len(nl))
        aca = parse_aca(st.get("Has_rating", ""))

        try:
            stars = float(st.get("Has_star_rating") or 0)
        except ValueError:
            stars = None

        thin = a is None and e is None

        # Adventure = ACA technical + Access. Two inputs, fixed weights, no sliders.
        # Wasp is NOT in here on purpose.
        parts, wsum = [], 0.0
        if aca["tech"] is not None:
            parts.append((aca["tech"] / 4 * 5) * 0.5); wsum += 0.5
        if acc is not None:
            parts.append(acc * 0.5); wsum += 0.5
        adventure = rd(sum(parts) / wsum) if wsum else None

        out.append({
            "canyon": name, "url": st.get("Has_url", ""),
            "stars": stars, "season": st.get("Has_best_season", "") or "",
            # ACA -- their system, their words
            "aca_raw": aca["clean"],
            "tech": aca["tech"], "tech_word": aca["tech_word"], "tech_def": aca["tech_def"],
            "water": aca["water"], "water_word": aca["water_word"], "water_def": aca["water_def"],
            "time": aca["time"], "time_word": aca["time_word"], "time_hours": aca["time_hours"],
            "risk": aca["risk"], "risk_def": aca["risk_def"],
            # Access -- ours
            "acc_appr": rd(a), "acc_exit": rd(e), "acc_total": rd(acc),
            "appr_band": (wa or {}).get("trail"), "exit_band": (we or {}).get("trail"),
            "appr_stat": approach_stat(b["approach"], wa),
            "exit_stat": approach_stat(b["exit"], we),
            # Wasp
            "wasp": rd(w), "wasp_terrain": rd(ww.get("terrain_only")),
            "nests": len(nl), "nest_log": nl,
            "adventure": adventure, "thin": thin,
            # Latest RopeWiki trip report (date + link); None if none exist
            "report_date": (reports.get(name) or {}).get("date"),
            "report_url": (reports.get(name) or {}).get("url"),
            "report_count": (reports.get(name) or {}).get("count", 0),
        })

    json.dump(out, open(os.path.join(DATA, "canyons.json"), "w"), indent=0)

    d = lambda k: dict(sorted(collections.Counter(
        None if c[k] is None else round(c[k]) for c in out).items(),
        key=lambda x: (x[0] is None, x[0])))
    print(f"-> {len(out)} canyons")
    print("   access   :", d("acc_total"))
    print("   wasp     :", d("wasp"))
    print("   adventure:", d("adventure"))
    print("   water    :", dict(collections.Counter(c["water"] for c in out)))
    print("   time     :", dict(collections.Counter(c["time_word"] for c in out)))
    print("   nests    :", sum(1 for c in out if c["nests"]), "canyons with a logged nest")
    print("   thin     :", sum(1 for c in out if c["thin"]))


if __name__ == "__main__":
    main()
