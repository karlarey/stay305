---
name: stay305-build
description: Shared build context for Stay305, our Hack for Humanity Miami (Brain Gain track) project. Load this FIRST in every Claude session working in this repo - it defines the product, the component split, the data/API contracts, the task-claim protocol and the deadline so parallel sessions can build different components without colliding.
---

# Stay305 - parallel build skill

## Deadline (hard)
- Build ends **3:30 PM ET, Sat Oct 10 2026**. Submit in OrganizerHQ by **3:45 PM**.
- **2:45 PM = feature freeze.** After that: only bug fixes, README and demo prep.
- Prefer a working thin slice over a half-built big one. Judges weight: impact 30%, working build 25%, AI+data 20%, craft 15%, demo 10%.

## Product (do not drift)
**Stay305** helps one specific person stay in Miami: a **graduating FIU / Miami Dade College senior** who is weighing leaving after school.
They paste their resume (or upload a photo of it) and get a personal **Stay Plan**:
1. **Miami roles they fit**: matched to real BLS wages and employment for the Miami metro.
2. **Where they can afford to live**: Census median rent by ZIP, compared with the salary for those roles (rent ≤ 30% of gross = affordable).
3. **Skill gaps + 90-day plan**: the shortest path into the best-paying role they fit.
4. **Communities to join**: real Miami orgs and meetups that match their goals, so they have a network.

Track: **03 Brain Gain**. Also entering **Best Use of Gemma 4** and **Best Open-Source AI Project**.
AI model: **Gemma 4 via the Gemini API** (open-weight). Never swap in a closed model.

## Architecture
```
data/            Python pipeline -> committed JSON (Component A)
  fetch_data.py  pulls BLS + Census, writes data/*.json
  occupations.json  neighborhoods.json  communities.json
server/          Node 22 + Express, port 3000 (Component B)
  index.js       serves web/ statically + the API below
  gemma.js       Gemini API client for Gemma 4 + prompts
web/             static HTML/CSS/vanilla JS, no build step (Component C)
  index.html  app.js  styles.css
README.md        submission README (Component D)
```
Run: `cd server && npm install && npm start` -> http://localhost:3000
Env: `GEMINI_API_KEY` (required), `GEMMA_MODEL` (default set in server/gemma.js; verify the exact Gemma 4 model id with the ListModels endpoint before hardcoding).

## Contracts (the interface between components)
Change a contract only by editing this section AND noting it in TASKS.md "Contract changes", so other sessions see it.

### data/occupations.json
```json
[{ "soc": "15-1252", "title": "Software Developers", "median_annual": 132650, "mean_annual": 141000,
   "employment": 18900, "year": 2025, "area": "Miami-Fort Lauderdale-West Palm Beach, FL MSA",
   "source": "BLS OEWS" }]
```
~40-60 occupations relevant to new grads (tech, health, business, finance, hospitality, trades, education, logistics).
BLS series id format: `OEUM0033100000000` + SOC(6 digits, no dash) + datatype (`13` annual median, `04` annual mean, `01` employment).

### data/neighborhoods.json
```json
[{ "zip": "33131", "name": "Brickell", "median_rent": 3831, "month": "2026-08",
   "source": "Zillow Observed Rent Index (ZORI), all homes, smoothed" }]
```
74 Miami-Dade ZIPs, real data (Census API now needs a key, so we switched to Zillow ZORI: keyless and current). Cheapest ZIP is ~$2,060/mo.

### data/communities.json
```json
[{ "name": "Refresh Miami", "url": "https://...", "type": "meetup|nonprofit|career-center|accelerator|professional-assoc",
   "fields": ["tech"], "description": "one line", "free": true }]
```
**Only real orgs with a working URL you verified today.** Don't invent any. 15-25 entries.

### API (server)
- `GET /api/health` -> `{ "ok": true, "model": "<gemma model id>" }`
- `GET /api/occupations` -> occupations.json
- `GET /api/neighborhoods` -> neighborhoods.json
- `POST /api/plan`
  - request: `{ "resumeText": "string (optional)", "resumeImage": "data:image/...;base64,... (optional)", "goals": "string (optional)", "major": "string (optional)" }` (at least one of resumeText/resumeImage)
  - response:
```json
{
  "profile": { "summary": "string", "skills": ["string"] },
  "matches": [{ "soc": "15-1252", "title": "Software Developers", "median_annual": 132650, "employment": 18900,
                "fit_score": 0.82, "why": "string", "skill_gaps": ["string"] }],
  "neighborhoods": [{ "zip": "33131", "name": "Brickell", "median_rent": 2900, "rent_share": 0.26, "affordable": true }],
  "plan_90_day": [{ "weeks": "1-2", "action": "string" }],
  "communities": [{ "name": "string", "url": "string", "why": "string" }],
  "model": "gemma model id"
}
```
  - Rule: **numbers (wages, rents, rent_share) come from data/*.json, computed in server code, never invented by the model.** Gemma picks the matches, gaps, plan and community picks, choosing only from SOC codes and community names it was given. Server validates that and drops anything not found in the data.
  - `rent_share` = median_rent*12 / median_annual of the top match. Return the 8 most relevant neighborhoods, affordable ones first.

## Components & ownership
| ID | Component | Owns (only edit these) |
|----|-----------|------------------------|
| A | Data pipeline | `data/` |
| B | AI + API server | `server/` |
| C | Web UI | `web/` |
| D | README, license, demo script, deploy | `README.md`, `LICENSE`, `docs/demo.md` |

Until the real data lands, B and C build against the sample records in the contracts above (B can put a stub `data/*.json` in place only if none exists yet, and A overwrites it).

## Session protocol
1. Load this skill, then read `TASKS.md`.
2. **Claim** one component by writing your session label + time next to it in TASKS.md before starting. Don't take a claimed component.
3. Only edit files your component owns. If you need something from another component, add a line under "Requests" in TASKS.md.
4. All sessions share ONE working directory. Stage only your own paths (`git add data/`, never `git add -A`), and commit often with small commits prefixed by the component, e.g. `A: add BLS fetch`. Run `git pull --rebase` before you push, if a remote is set. Never force-push.
5. When done, mark it `DONE` in TASKS.md with a one-line "how to verify", then pick up an open Request or the next unclaimed task.

## Quality bar
- Ground every claim in Miami: real ZIPs, real orgs, real BLS/Census numbers. Cite the sources in README.
- The demo flow must work end to end in under 20 seconds: paste resume -> Stay Plan.
- If Gemma fails or times out, show a readable error in the UI (no blank screen).
- Keep secrets out of git: `.env` is gitignored, never commit the API key.
