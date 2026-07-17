#!/usr/bin/env python3
"""
Scoring for the Canyon Experience Matrix.

Two ideas, kept separate on purpose:

  ACA rating  -- not ours. Parsed into its three real parts (technical / water /
                 time) and labelled with the ACA's OWN published wording. We add
                 no judgment here; we just stop throwing two thirds of it away.
                 Source: https://ropewiki.com/ACA_rating

  Access      -- ours. Approach + exit effort, on Scott's 1-5 bands:
                   1  defined trail, <1mi, minimal vert
                   2  trail but it's work (longer / some vert), or a few hundred ft of easy brush
                   3  off-trail enters: fading use trail, short bushwhack, or a real scramble
                   4  sustained bushwhacking -- a bad section
                   5  long bushwhack ("in the sick of it") -- a bad day

Design rules learned the hard way:
  * trail quality sets the BAND (a trail caps ~2 no matter how long; off-trail
    floors at 3 no matter how short). Distance/vert move you WITHIN the band and
    can bump up, rarely down. This is why "0.2mi of devils club" != "5mi of trail".
  * distance x terrain is MULTIPLICATIVE, not averaged. Terrain says how bad each
    mile is; distance says how many.
  * negation/avoidance is stripped BEFORE counting words, or "avoid the brushy
    scramble by staying on the trail" reads as hard.
  * floats end to end; round once at display.
  * severity-weighted terms: devils club != "steep".
"""
import re

# ---------------------------------------------------------------------------
# ACA rating -- their system, their words. No invention.
# ---------------------------------------------------------------------------
ACA_TECH = {
    1: ("canyon hiking",  "A hike through a canyon. No special physical obstacles."),
    2: ("non-technical",  "Scrambling, up/down-climbing or stemming. No ropes required."),
    3: ("technical",      "Ropes and rappels are required."),
    4: ("advanced",       "Advanced anchors, long drops, rebelays. Extra challenges beyond most class 3."),
}
ACA_WATER = {
    "A":  ("normally dry",     "Dry or very little water. No wetsuit required."),
    "B":  ("still water",      "Water with no current or very light current."),
    "C":  ("has current",      "Water with current. Waterfalls."),
    "C1": ("light current",    "Light to moderate current. Easy water hazards."),
    "C2": ("strong current",   "Strong current. Hydraulics and siphons."),
    "C3": ("very strong current", "Very strong current. Dangerous water hazards. Experts only."),
    "C4": ("extreme water",    "Extreme problems and hazards, difficult to overcome."),
}
ACA_TIME = {
    1: ("short day",  "1-3 hours",   1),
    2: ("half day",   "4-6 hours",   2),
    3: ("full day",   "7-12 hours",  3),
    4: ("long day",   "13-18 hours. Headlamp, possible bivy.", 4),
    5: ("overnight",  "1-2 days",    5),
    6: ("multi-day",  "2+ days",     6),
}
ACA_RISK = {
    "R":  "One or more extraordinary risk factors present.",
    "X":  "Multiple and/or life-threatening risk factors present.",
    "XX": "Multiple and/or life-threatening risk factors present.",
}
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


def parse_aca(raw):
    """'3C III (v3a4 II)' -> the three ACA parts. Returns dict; None fields when absent.

    The parenthetical is the European v-grade equivalent -- noise for a US audience,
    and it contains its own roman numeral, so it MUST be stripped before we look
    for the commitment grade or we'd read the wrong one.
    """
    out = {"tech": None, "tech_word": None, "tech_def": None,
           "water": None, "water_word": None, "water_def": None,
           "time": None, "time_word": None, "time_hours": None,
           "risk": None, "risk_def": None, "clean": None}
    if not raw:
        return out
    s = re.sub(r"<[^>]+>", "", raw)                  # stray <i> tags in the wiki data
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"\([^)]*\)", "", s)                  # drop the (v3a4 II) euro grade
    s = re.sub(r"\s+", " ", s).strip()
    if not s or s.upper() in ("POI", "?"):
        return out
    out["clean"] = s

    m = re.match(r"\s*([1-4])", s)
    if m:
        out["tech"] = int(m.group(1))
        out["tech_word"], out["tech_def"] = ACA_TECH[out["tech"]]

    # water: C3 / C1 / C / B / A  -- longest match first so C3 doesn't read as C
    m = re.search(r"\b[1-4]\s*(C[1-4]|C|B|A)\b", s)
    if m:
        w = m.group(1)
        out["water"] = w
        out["water_word"], out["water_def"] = ACA_WATER[w]

    # commitment roman numeral (euro grade already stripped)
    m = re.search(r"\b(VI|IV|V|III|II|I)\b", s)
    if m:
        n = _ROMAN[m.group(1)]
        out["time"] = n
        out["time_word"], out["time_hours"], _ = ACA_TIME[n]

    m = re.search(r"\b(XX|X|R)\b", s)
    if m:
        out["risk"] = m.group(1)
        out["risk_def"] = ACA_RISK[m.group(1)]
    return out


# ---------------------------------------------------------------------------
# Access -- ours.
# ---------------------------------------------------------------------------

# Negation/avoidance. RopeWiki beta is full of "avoid the brush by...", and a
# bag-of-words counter reads those as HARD. Strip the clause before counting.
NEG = re.compile(
    r"\b(?:avoid(?:s|ing)?|bypass(?:es|ing)?|no need to|instead of|rather than|"
    r"don'?t|do not|not?\b(?=\s+(?:a\s+)?(?:bushwhack|brush|scramble))|"
    r"skip(?:s|ping)?|stay(?:ing)? on|keep(?:ing)? to)\b[^.;]*[.;]?", re.I)

# Trail quality sets the band. Ordered worst -> best; first match wins.
OFFTRAIL = re.compile(r"\b(bushwhack\w*|bush-?whack\w*|thrash\w*|off.?trail|no trail|"
                      r"trailless|cross.?country|whack\w*)\b", re.I)
FAINT    = re.compile(r"\b(use.?trail|game.?trail|climber.?s?.?trail|social trail|"
                      r"faint|fading|unmaintained|overgrown trail|boot path|way.?trail)\b", re.I)
TRAIL    = re.compile(r"\b(maintained trail|well.?marked|obvious trail|good trail|"
                      r"hiking trail|established trail|trailhead|\btrail\b|pavement|sidewalk|"
                      # walking the road back to the car is a trail-grade exit, not "unknown".
                      # Dingford: "a 2 min walk up the road to the right to the parking area."
                      r"walk (?:up|down|along|back)? ?the road|road (?:back |up |down )?to the "
                      r"(?:car|parking|trailhead)|to the parking area|back to the car)\b", re.I)

# Severity-weighted terrain. devils club is not "steep".
VEG = {
    r"\bdevils?.?club\b": 2.2, r"\bslide alder\b": 2.2, r"\bblackberr\w*\b": 1.8,
    r"\bvine maple\b": 1.5, r"\bthorny\b": 1.6, r"\bnettles?\b": 1.2,
    r"\bbrush(y|ing)?\b": 1.2, r"\bovergrown\b": 1.2, r"\bthick\b": 1.0,
    r"\bdense\b": 1.0, r"\bdeadfall\b": 1.3, r"\bdowned (?:trees|logs)\b": 1.3,
    r"\bblowdown\b": 1.3,
}
GROUND = {
    r"\bscrambl\w*\b": 1.2, r"\bexposed?\b": 1.2, r"\btalus\b": 1.1,
    r"\bscree\b": 1.1, r"\bsteep(ly)?\b": 0.9, r"\bloose\b": 0.8,
    r"\bslippery\b": 0.6, r"\bboulder\w*\b": 0.7, r"\bcliff\w*\b": 1.0,
}
# The reporter's own verdict beats any word count.
VERDICT = {
    r"\btype\s*(?:2|two|ii)\s*fun\b": 4.0,
    r"\btype\s*(?:3|three|iii)\s*fun\b": 5.0,
    r"\bmiserable\b": 4.0, r"\bbrutal\b": 4.0, r"\bsuffer\w*\b": 4.0,
    r"\bheinous\b": 4.5, r"\bspicy\b": 3.5, r"\bsporty\b": 3.5,
    r"\bdirty mess\b": 3.5, r"\bstrenuous\b": 3.5, r"\barduous\b": 4.0,
    r"\bgnarly\b": 3.5, r"\bthrash\w*\b": 3.5,
}


def _strip_negated(txt):
    return NEG.sub(" ", txt or "")


# Mileage that belongs to the DRIVE, not the hike. Dingford's beta opens with
# "The final 6mi of road to the trailhead is rough" -- a 6mi cap doesn't catch that,
# and reading it as a 6-mile approach is how a 1.1mi trail hike scored 3.7.
DRIVE_CTX = re.compile(r"\b(driv\w+|drove|road to the trail(?:head)?|forest road|"
                       r"fs road|fr\s?\d|high.?clearance|4wd|awd|washout|"
                       r"from i-?\d|shuttle|mileage from|odometer)\b", re.I)
# ...but "park at the gate and hike 2 miles up the road" IS a hike. An explicit
# on-foot verb in the same clause wins over the driving context.
HIKE_CTX = re.compile(r"\b(hik\w+|walk\w*|on foot|bushwhack\w*|approach\w*\s+is|"
                      r"trudge|slog|march|travel\w*\s+up)\b", re.I)


def _dist_mi(txt):
    """Hiking miles only. A mileage inside a driving clause is the approach DRIVE,
    not the approach hike -- look at the sentence it lives in, not just its size."""
    if not txt:
        return None
    hike = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:mi\b|mile)", txt, re.I):
        v = float(m.group(1))
        if v > 6:                      # nobody hikes >6mi to a WA canyon
            continue
        # the clause this number sits in (sentence-ish window either side)
        start = max(0, txt.rfind(".", 0, m.start()) + 1)
        end = txt.find(".", m.end())
        clause = txt[start: end if end > 0 else m.end() + 60]
        if DRIVE_CTX.search(clause) and not HIKE_CTX.search(clause):
            continue                   # it's the drive, and nobody's walking it
        hike.append(v)
    return max(hike) if hike else None


def _vert_ft(txt):
    """Elevation gain/loss. Scott's 1 is <~250-500ft."""
    vals = []
    for m in re.finditer(r"(\d[\d,]{1,5})\s*(?:'|ft\b|feet\b|foot\b)", txt or "", re.I):
        v = float(m.group(1).replace(",", ""))
        if 20 <= v <= 6000:          # ignore rope lengths (<20) and elevations ASL
            vals.append(v)
    return max(vals) if vals else None


def _severity(txt, table):
    return sum(w * len(re.findall(p, txt, re.I)) for p, w in table.items())


def access_segment(txt):
    """-> (score float 1-5, why dict) or (None, why) when there's nothing to read."""
    why = {"trail": None, "dist_mi": None, "vert_ft": None,
           "veg": 0.0, "ground": 0.0, "verdict": None, "band": None}
    if not txt or len(txt.strip()) < 40:
        return None, why

    clean = _strip_negated(txt)

    # 1. Trail quality -> the band. Off-trail wins if mentioned at all: a route
    #    that bushwhacks for 200yd and then hits a trail is still a bushwhack.
    if OFFTRAIL.search(clean):
        band, lo, hi = "off-trail", 3.0, 5.0
    elif FAINT.search(clean):
        band, lo, hi = "faint/use trail", 2.0, 4.0
    elif TRAIL.search(clean):
        band, lo, hi = "defined trail", 1.0, 2.5
    else:
        band, lo, hi = "unknown", 1.5, 3.5      # no trail language either way
    why["trail"] = band

    d = _dist_mi(txt)
    v = _vert_ft(txt)
    why["dist_mi"], why["vert_ft"] = d, v

    # 2. Effort within the band, from distance + vert (Scott's 1: <1mi, <500ft)
    eff = 0.0
    if d is not None:
        eff += 0.0 if d < 1 else 0.30 if d < 1.5 else 0.55 if d < 2.5 else 0.80 if d < 4 else 1.0
    if v is not None:
        eff += 0.0 if v < 500 else 0.25 if v < 1000 else 0.45 if v < 2000 else 0.6
    eff = min(eff, 1.0)

    # 3. Terrain severity -> how bad each mile is
    veg = _severity(clean, VEG)
    grd = _severity(clean, GROUND)
    why["veg"], why["ground"] = round(veg, 2), round(grd, 2)
    sev = min((veg * 1.0 + grd * 0.6) / 5.0, 1.0)

    # 4. Multiplicative, not averaged: terrain sets how bad, distance how much.
    #    Severity is weighted heavier so 0.2mi of devils club outranks 5mi of trail.
    mix = min(1.0, sev * 0.65 + eff * 0.35 + sev * eff * 0.25)
    score = lo + (hi - lo) * mix

    # 5. The reporter's verdict overrides the word count -- but only upward.
    vscore = max((w for p, w in VERDICT.items() if re.search(p, clean, re.I)), default=None)
    if vscore:
        why["verdict"] = vscore
        score = max(score, vscore)

    why["band"] = (lo, hi)
    return max(1.0, min(5.0, score)), why


def access_total(appr, exit_):
    """Worse end dominates -- one brutal end defines the day. Floats in, float out,
    so this actually differs from max() instead of collapsing onto it."""
    segs = [s for s in (appr, exit_) if s is not None]
    if not segs:
        return None
    if len(segs) == 1:
        return segs[0]
    return max(segs) * 0.65 + (sum(segs) / len(segs)) * 0.35
