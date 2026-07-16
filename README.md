# Canyon Experience Matrix

An interactive, sortable matrix of every technical canyon in Washington State, scored to help you pick the right objective at a glance — especially as a newer canyoneer.

**[▶ Live version](https://boomchopalaka.github.io/canyon-experience-matrix/)** &nbsp;·&nbsp; single self-contained HTML page, no build step.

## Why

Canyon rating systems tell you how hard the *technical* descent is (rope work, water) but say little about **getting in and out** — the approach and exit hikes, which are often what actually make or break a day. This tool scores those explicitly, blends them with the official difficulty into one tunable **Adventure Score**, and adds a couple of layers most tools skip.

## What it scores

Every canyon gets these, each on a 1–5 scale (1 = easy, 5 = hard):

| Column | What it means |
|---|---|
| **Difficulty** | The official ACA technical grade (rope work, water, commitment), translated to plain words (1 beginner → 4 expert). |
| **Approach** | Effort to get from the car to the water — a 50/50 blend of distance/time and terrain (trail vs. bushwhack vs. steep). |
| **Exit** | Same scoring, for getting back to the car. |
| **Access** | Approach + Exit combined, weighted toward the worse of the two. |
| **Wasp exposure** | A *terrain proxy* for stinging-insect habitat, from brush/bushwhack language in the approach/exit beta. Seasonal — only folds into the score for Jul–Oct trips. |
| **Wasp log** | Dated, boots-on-ground wasp sightings pulled from RopeWiki condition reports. Real evidence, shown beside the proxy. |
| **Adventure Score** | The tunable all-in blend: Difficulty + Access by default, +wasp exposure when you flip the wasp-season toggle. |

Hover the ⓘ on any column in the live page for the exact calculation. Click a canyon name to open its full RopeWiki page.

### A note on the wasp layer

This started as a personal need (the author is allergic to wasp stings), but it turns out to be a genuinely underrated planning data point: wasps nest in ground burrows, rotten logs, and brush — exactly the terrain you cross on a long or bushwhacky approach/exit, not in the technical canyon itself. So easy, on-trail access also tends to mean lower wasp exposure. The proxy is directional, not a guarantee: **a blank wasp log means nobody logged one, not that a canyon is safe.**

## Data pipeline

```bash
python3 scripts/pull_and_score.py   # pull RopeWiki + condition reports, score → data/canyons.json
python3 scripts/embed_data.py       # inline that data into index.html
```

`pull_and_score.py` is rate-limited and polite. Re-run it to refresh — the wasp log especially picks up new dated reports through the season.

## Data source & license

All canyon data comes from **[RopeWiki](https://ropewiki.com)**, the community canyoneering wiki, licensed under
**[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/)**.

This project is a **non-commercial derivative work** and is shared under the **same license (CC BY-NC-SA 3.0)**.
It is not affiliated with or endorsed by RopeWiki. Ratings here are convenience heuristics — always verify a canyon's beta on RopeWiki and use your own judgment before you go.

## Disclaimer

Canyoneering is inherently dangerous. This tool is a planning aid, not a substitute for training, current conditions, proper gear, and sound judgment. The scores are automated heuristics derived from wiki text and can be wrong.
