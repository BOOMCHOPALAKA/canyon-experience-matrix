# Canyon Experience Matrix

An interactive, sortable matrix of every technical canyon in Washington State, scored to help you pick the right objective at a glance — especially as a newer canyoneer.

**[▶ Live version](https://boomchopalaka.github.io/canyon-experience-matrix/)** &nbsp;·&nbsp; single self-contained HTML page, no build step.

## Why

Canyon rating systems tell you how hard the *technical* descent is, but say nothing about **getting in and out** — the approach and exit hikes, which are often what actually make or break a day. This scores those explicitly.

It also stops throwing away two thirds of the official rating. The ACA rating is three independent parts, and most tools show only the first:

| Part | What it means | Example |
|---|---|---|
| **Technical** (1–4) | Rope work. 3 = "ropes and rappels required" — which is **79% of Washington canyons**, so it separates less than you'd think. | `3`C III |
| **Water** (A/B/C + severity) | Often the part that matters. `C1` is light current; `C3` is "very strong current, dangerous water hazards, experts only." | 3`C`III |
| **Time** (I–VI) | Descent commitment. `I` is 1–3 hrs; `IV` is 13–18 hrs, headlamp and possible bivy. | 3C `III` |

A `3C1 I` and a `3C3 IV` are wildly different days. Most matrices render both as "class 3."

## What it scores

| Column | Source | What it means |
|---|---|---|
| **Technical / Water / Time** | ACA, verbatim | The official rating, broken into its three real parts, labelled with the ACA's own published wording. We add no judgment here. |
| **Approach / Exit** | ours | Effort car-to-water and back, 1–5. Trail quality sets the band; distance and vert move you inside it. A trail caps around 2 no matter how long; off-trail floors at 3 no matter how short. |
| **Access** | ours | Approach + exit in one number, weighted toward the worse end. The thing canyon ratings leave out. |
| **Wasp** | ours | Terrain prediction from wasp-nesting research, plus any nests people have actually logged. Seasonal. |
| **Adventure** | ours | ACA technical + Access, evenly weighted. Wasp is deliberately excluded. |

### The Access scale

| | |
|---|---|
| **1** | Defined trail, under a mile, minimal vert |
| **2** | Trail, but it's work — longer, or real vertical |
| **3** | Off-trail enters the picture: fading use trail, short bushwhack, or a real scramble |
| **4** | Sustained bushwhacking — a bad section |
| **5** | Long bushwhack — a bad day. In the sick of it. |

### A note on the wasp layer

Wasps (yellowjackets, paper wasps, hornets) nest in ground burrows, deadfall, rotten logs and creek banks, and are set off by ground vibration — so off-trail travel over forest floor puts you over more buried nests than a maintained trail does. **Off-trail miles matter more than total miles:** 2mi of maintained trail scores 1; 200ft of deadfall doesn't.

Two inputs, same question, answered two ways:

- **Terrain** — a prediction, from the nesting research. Not from trip reports.
- **Nest log** — an observation. Someone found a nest here. A logged nest overrides the prediction for that canyon and compounds when multiple parties found one. Colonies die each winter but the *sites* recur (Davis Creek's nest was logged in July and again in October).

Honest caveats, because this layer is thin:

- **Only 7 of 119 Washington canyons have a logged nest.** A blank means nobody wrote it down. It never means safe.
- Reports only ever push the score **up**. Silence is not evidence of absence.
- **It correlates with Access (r≈0.76), and that's the mechanism, not a coincidence** — brushy off-trail terrain is genuinely both harder to walk and better for nesting.
- We count nests found, not stings taken. Hager's reporter found an active nest on the exit and wrote *"we were fortunate."* Same nest, same risk, different luck.
- It is **not** in the Adventure Score. A signal this thin shouldn't move a ranking.

## Data pipeline

```bash
python3 scripts/pull_beta.py     # once — caches RopeWiki beta to data/wa_beta.json
python3 scripts/build_data.py    # re-score, offline, no network
python3 scripts/embed_data.py    # inline into index.html
```

The pull is rate-limited and polite, and the raw beta is **cached** — re-scoring never re-crawls RopeWiki. Delete `data/wa_beta.json` to refresh from the wiki.

`scripts/scoring.py` holds the whole model and documents why each rule exists. `scripts/wasp_multiregion_scan.py` is the research script behind the wasp layer's caveats (2,199 trip reports across WA/OR/UT/AZ/CA).

## Data source & license

All canyon data comes from **[RopeWiki](https://ropewiki.com)**, the community canyoneering wiki, licensed under
**[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/)**.

This project is a **non-commercial derivative work** and is shared under the **same license (CC BY-NC-SA 3.0)**.
It is not affiliated with or endorsed by RopeWiki. Ratings here are convenience heuristics — always verify a canyon's beta on RopeWiki and use your own judgment before you go.

## Disclaimer

Canyoneering is inherently dangerous. This tool is a planning aid, not a substitute for training, current conditions, proper gear, and sound judgment. The scores are automated heuristics derived from wiki text and can be wrong.
