# Stay305 task board

Load the `stay305-build` skill first. Claim a task by writing your session label and the time on its line. Only edit what your component owns.

Feature freeze 2:45 PM · build ends 3:30 PM · submit by 3:45 PM

## Components
- [x] DONE **A - Data pipeline** (`data/`): `fetch_data.py` -> occupations.json (BLS OEWS, Miami MSA, ~50 SOCs), neighborhoods.json (Census ACS by ZIP; the 2023 ZCTA query came back empty, so check year/geo syntax), communities.json (verified real orgs). Claimed by: session-main 12:21 -- verify: `python data/fetch_data.py` regenerates occupations+neighborhoods; communities.json is hand-verified
- [ ] **B - AI + API server** (`server/`): Express app, Gemma 4 client (find the exact model id via ListModels), `/api/plan` per contract, server-side number math + validation. Claimed by: session-main 12:15
- [ ] **C - Web UI** (`web/`): resume paste/photo upload -> Stay Plan view (roles + wages, neighborhood affordability, 90-day plan, communities). Mobile friendly, loading + error states. Claimed by: _
- [ ] **D - Submission** (`README.md`, `LICENSE`, `docs/demo.md`): README per checklist (track, data sources, models + license link, how to run, team), MIT license, 2-min demo script with a sample resume of a FIU senior. Claimed by: _

## Requests
(format: `from X to Y: what you need`)

## Contract changes
(note any edit to the skill's Contracts section here)
- 12:30 A: neighborhoods.json now comes from Zillow ZORI (fields: zip, name, median_rent, month, source). No household income field. Real occupations.json + neighborhoods.json are committed.
