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

# How MUCH off-trail? "off trail" appearing at all used to floor a canyon at 3.
# Dingford is ~1mi of trail then "70 yrd" of flagged drop to the creek -- Scott
# calls that a 2, and he's descended it. A short flagged drop-in is not a bushwhack.
SHORT_OFFTRAIL = re.compile(r"\b(\d{1,3})\s*(?:yrds?|yards?|yds?|feet|ft|')\b", re.I)
FLAGGED = re.compile(r"\b(flagging|flagged|flags|cairn\w*|ribbon\w*|marked with|"
                     r"pink tape|survey tape)\b", re.I)


def _offtrail_extent(txt):
    """-> 'brief' | 'sustained'. Brief = a short, often flagged drop-in at the end
    of a trail hike. Sustained = you are actually bushwhacking."""
    # an explicit short distance attached to the off-trail move
    m = OFFTRAIL.search(txt)
    if m:
        window = txt[max(0, m.start() - 160): m.end() + 160]
        yd = SHORT_OFFTRAIL.search(window)
        if yd and float(yd.group(1)) <= 300:      # <=300yd/ft of off-trail
            return "brief"
        if FLAGGED.search(window) and not re.search(r"\b(mile|mi\b)", window, re.I):
            return "brief"                        # flagged route, no mileage = a drop-in
    # sustained language
    if re.search(r"\b(long|sustained|miles? of|continuous|endless|relentless)\s+"
                 r"(?:\w+\s+){0,2}(bushwhack|thrash|brush)", txt, re.I):
        return "sustained"
    return "sustained"
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

    # 1. Trail quality -> the band. But HOW MUCH off-trail matters: a 70yd flagged
    #    drop to the creek at the end of a trail hike is not a bushwhack (Dingford).
    if OFFTRAIL.search(clean):
        if _offtrail_extent(clean) == "brief":
            band, lo, hi = "trail + short off-trail drop", 1.5, 3.0
        else:
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


# ---------------------------------------------------------------------------
# Wasp exposure -- a TERRAIN PREDICTION grounded in wasp nesting research.
#
# Why this is NOT just Access wearing a hat (the old proxy correlated 0.64 with
# Access because both counted the same general-effort words):
#   * it scores GROUND-NEST HABITAT specifically -- burrows, deadfall, rotten
#     logs, dirt/creek banks, duff -- not "steep" or "loose", which are effort.
#   * distance multiplies OFF-TRAIL travel only. 2mi of maintained trail is
#     exposure 1; 200ft of deadfall outranks it.
#
# Research basis: Vespula and relatives nest in ground burrows, rodent holes,
# cavities in soil/logs, and creek banks (typically 10-15cm down), and are set
# off by ground vibration -- so off-trail travel over forest floor and deadfall
# puts you over more buried nests than a maintained trail does.
#   https://ropewiki.com/ACA_rating is unrelated; sources for this:
#   Penn State Extension (Eastern Yellowjacket), UC Riverside Entomology,
#   OSU Solve Pest Problems, American Trails.
#
# What this is NOT: it is not derived from trip reports. Across 2,199 reports in
# WA/OR/UT/AZ/CA only 39 mention wasps, and most of those nests were AT ANCHORS
# (where people stop and write things down), not on approaches. That is a
# reporting-visibility pattern, not evidence about where wasps are. The log
# column carries that real evidence separately; it never lowers this score.
# ---------------------------------------------------------------------------
NEST_HABITAT = {
    r"\bdeadfall\b": 1.6, r"\bdowned (?:trees|logs)\b": 1.6, r"\bblowdown\b": 1.6,
    r"\brotten (?:logs?|wood|stumps?)\b": 1.8, r"\bstumps?\b": 1.0,
    r"\bduff\b": 1.2, r"\bleaf litter\b": 1.2, r"\bforest floor\b": 1.2,
    r"\bburrow\w*\b": 1.8, r"\brodent\b": 1.5, r"\bhollow\b": 1.0,
    r"\bcreek bank\w*\b": 1.4, r"\bdirt bank\w*\b": 1.4, r"\bembankment\b": 1.2,
    r"\bloamy?\b": 1.0, r"\bsandy soil\b": 1.0, r"\bdry slope\b": 1.0,
    r"\bbrush(y|ing)?\b": 1.1, r"\bovergrown\b": 1.1, r"\bslide alder\b": 1.2,
    r"\bdevils?.?club\b": 1.0, r"\bthick\b": 0.8, r"\bdense\b": 0.8,
    r"\bblackberr\w*\b": 1.1, r"\bvine maple\b": 0.9,
}


def wasp_exposure(appr, exit_, nests_found=0):
    """1-5. -> (score float | None, why dict)

    Two inputs, same question ("does this canyon hold nest habitat?"), answered
    two ways:

      terrain  -- a PREDICTION. Nesting habitat (deadfall, burrows, banks, duff)
                  is the heavy term; off-trail travel modifies it, and distance
                  multiplies off-trail only. Habitat leads because off-trail
                  alone is what Access already measures -- leaning on it just
                  reprints the Access column.
      nests    -- an OBSERVATION. Someone logged a nest here. A confirmed nest
                  outweighs a guess about the same canyon, and compounds when
                  multiple parties found one. Colonies die each winter but the
                  SITES recur (Davis Creek: same nest logged Jul and Oct), so
                  this never decays to zero.

    Whether anyone was STUNG is deliberately ignored. Hager's reporter wrote "we
    were fortunate" -- same nest, same risk, different luck. The nest is the
    signal; the sting is downstream noise.

    Silence never lowers the score: most WA canyons have no wasp report at
    all, and that is nobody writing it down, not evidence of absence.

    NOT folded into the Adventure Score.
    """
    why = {"offtrail": False, "extent": None, "habitat": 0.0,
           "offtrail_mi": None, "nests": nests_found, "terrain_only": None}
    both = " ".join(t for t in (appr, exit_) if t)
    if not both.strip() or len(both.strip()) < 40:
        # No beta to read -- but a logged nest is still hard evidence on its own.
        if nests_found:
            s = min(5.0, 3.0 + 0.7 * (nests_found - 1))
            why["terrain_only"] = None
            return s, why
        return None, why

    clean = _strip_negated(both)
    habitat = _severity(clean, NEST_HABITAT)
    why["habitat"] = round(habitat, 2)

    offtrail = bool(OFFTRAIL.search(clean))
    faint = bool(FAINT.search(clean))
    why["offtrail"] = offtrail
    extent = _offtrail_extent(clean) if offtrail else None
    why["extent"] = extent

    # HABITAT leads. This is the term Access does not have.
    terrain = 1.0 + min(habitat * 0.62, 2.6)

    # Off-trail modifies: it is how you come into contact with the habitat.
    # Kept modest on purpose -- it is the term Access already owns.
    if offtrail:
        terrain += 0.9 if extent == "sustained" else 0.35
    elif faint:
        terrain += 0.3

    # Distance multiplies OFF-TRAIL travel only -- 2mi of trail is not exposure,
    # 2mi of deadfall is. (Scott's 2-mile-vs-20-foot rule.)
    d = _dist_mi(both)
    why["offtrail_mi"] = d
    if d is not None and offtrail and extent == "sustained":
        terrain += 0.0 if d < 0.5 else 0.3 if d < 1.5 else 0.6 if d < 3 else 0.9

    terrain = max(1.0, min(5.0, terrain))
    why["terrain_only"] = round(terrain, 2)

    # A found nest is confirmation, and outweighs the prediction for this canyon.
    if nests_found:
        confirmed = min(5.0, 3.4 + 0.6 * (nests_found - 1))
        return max(terrain, confirmed), why
    return terrain, why


def access_total(appr, exit_):
    """Worse end dominates -- one brutal end defines the day. Floats in, float out,
    so this actually differs from max() instead of collapsing onto it."""
    segs = [s for s in (appr, exit_) if s is not None]
    if not segs:
        return None
    if len(segs) == 1:
        return segs[0]
    return max(segs) * 0.65 + (sum(segs) / len(segs)) * 0.35
