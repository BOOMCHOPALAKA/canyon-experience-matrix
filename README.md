# Canyon Experience Matrix

An interactive, sortable matrix of every technical canyon in Washington State, scored to help you pick the right objective at a glance — especially as a newer canyoneer.

**[▶ Live version](https://boomchopalaka.github.io/canyon-experience-matrix/)** &nbsp;·&nbsp; single self-contained HTML page, no build step.

## Why

RopeWiki describes the approach and exit for every canyon. But it's **prose** — you read it one canyon at a time, and there's no number to compare or sort by. The two things you *can* sort by, the ACA rating and the star rating, are both about the descent.

So the hike in and the climb out — often what actually makes or breaks the day — never show up as a score. This reads that beta and quantifies it: a number for the approach, a number for the exit, and one **Access** score combining them.

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

| | | |
|---|---|---|
| **1** | Walking | Trail to the water, under a mile |
| **2** | Hiking | Still a trail, but longer or steeper |
| **3** | Off-trail | The trail runs out partway |
| **4** | Bushwhacking | Sustained — a bad section |
| **5** | Suffering | Long bushwhack, in the thick of it |

Trail quality sets the band; distance and vertical move you inside it. A trail caps around 2 no matter how long, and off-trail floors at 3 no matter how short — a short flagged drop-in to the creek is not a bushwhack.

## Data source & license

All canyon data comes from **[RopeWiki](https://ropewiki.com)**, the community canyoneering wiki, licensed under
**[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/)**.

This project is a **non-commercial derivative work** and is shared under the **same license (CC BY-NC-SA 3.0)**.
It is not affiliated with or endorsed by RopeWiki. Ratings here are convenience heuristics — always verify a canyon's beta on RopeWiki and use your own judgment before you go.

## Disclaimer

Canyoneering is inherently dangerous. This tool is a planning aid, not a substitute for training, current conditions, proper gear, and sound judgment. The scores are automated heuristics derived from wiki text and can be wrong.
