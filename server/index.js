import 'dotenv/config';
import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { generatePlan, resolveModel, currentModel } from './gemma.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = process.env.PORT || 3000;

// Placeholder records used only until component A writes data/*.json. Marked SAMPLE so they never pass as real.
const FALLBACK = {
  occupations: [
    { soc: '15-1252', title: 'Software Developers', median_annual: 132650, employment: 18900, year: 2025, source: 'BLS OEWS' },
    { soc: '13-2011', title: 'Accountants and Auditors', median_annual: 80000, employment: 30000, year: 2025, source: 'SAMPLE' },
    { soc: '13-1161', title: 'Market Research Analysts and Marketing Specialists', median_annual: 70000, employment: 15000, year: 2025, source: 'SAMPLE' },
    { soc: '29-1141', title: 'Registered Nurses', median_annual: 85000, employment: 50000, year: 2025, source: 'SAMPLE' },
  ],
  neighborhoods: [
    { zip: '33131', name: 'Brickell', median_rent: 2900, source: 'SAMPLE' },
    { zip: '33135', name: 'Little Havana', median_rent: 1300, source: 'SAMPLE' },
    { zip: '33172', name: 'Doral', median_rent: 2000, source: 'SAMPLE' },
  ],
  communities: [
    { name: 'The LAB Miami', url: 'https://labmiami.com', type: 'meetup', fields: ['tech', 'startups'], description: 'Wynwood coworking and community hub', free: true },
  ],
};

function loadData(name) {
  try {
    const rows = JSON.parse(fs.readFileSync(path.join(root, 'data', `${name}.json`), 'utf8'));
    if (Array.isArray(rows) && rows.length) return rows;
  } catch {}
  return FALLBACK[name];
}

const app = express();
app.use(express.json({ limit: '12mb' }));
app.use(express.static(path.join(root, 'web')));

app.get('/api/health', async (_req, res) => {
  try {
    res.json({ ok: true, model: await resolveModel() });
  } catch (e) {
    res.status(500).json({ ok: false, model: currentModel(), error: e.message });
  }
});
app.get('/api/occupations', (_req, res) => res.json(loadData('occupations')));
app.get('/api/neighborhoods', (_req, res) => res.json(loadData('neighborhoods')));

// Rent share for the top match; affordable (<=30%) first, priciest-you-can-afford on top.
function rankNeighborhoods(neighborhoods, annualWage, n = 8) {
  const rows = neighborhoods
    .filter((h) => h.median_rent > 0)
    .map((h) => {
      const rent_share = Math.round(((h.median_rent * 12) / annualWage) * 100) / 100;
      return { zip: h.zip, name: h.name, median_rent: h.median_rent, rent_share, affordable: rent_share <= 0.3 };
    });
  const ok = rows.filter((r) => r.affordable).sort((a, b) => b.median_rent - a.median_rent);
  const stretch = rows.filter((r) => !r.affordable).sort((a, b) => a.median_rent - b.median_rent);
  return [...ok, ...stretch].slice(0, n);
}

app.post('/api/plan', async (req, res) => {
  const { resumeText, resumeImage, goals, major } = req.body || {};
  if (!resumeText?.trim() && !resumeImage) return res.status(400).json({ error: 'Send resumeText or resumeImage.' });

  const occupations = loadData('occupations');
  const neighborhoods = loadData('neighborhoods');
  const communities = loadData('communities');
  const t0 = Date.now();

  let ai;
  try {
    ai = await generatePlan({ resumeText, resumeImage, goals, major, occupations, communities });
  } catch (e) {
    console.error('plan failed:', e);
    return res.status(502).json({ error: `AI step failed: ${e.message}` });
  }

  // Numbers come from our data, never the model. Drop anything the model invented.
  const occBySoc = new Map(occupations.map((o) => [o.soc, o]));
  const matches = (ai.matches || [])
    .filter((m) => occBySoc.has(m.soc))
    .map((m) => {
      const o = occBySoc.get(m.soc);
      return {
        soc: o.soc,
        title: o.title,
        median_annual: o.median_annual,
        employment: o.employment ?? null,
        fit_score: Math.max(0, Math.min(1, Number(m.fit_score) || 0)),
        why: String(m.why || ''),
        skill_gaps: (m.skill_gaps || []).map(String).slice(0, 4),
      };
    })
    .sort((a, b) => b.fit_score - a.fit_score);

  const comByName = new Map(communities.map((c) => [c.name.toLowerCase(), c]));
  const picked = (ai.communities || [])
    .map((c) => ({ c: comByName.get(String(c.name || '').toLowerCase()), why: String(c.why || '') }))
    .filter((x) => x.c)
    .map(({ c, why }) => ({ name: c.name, url: c.url, why }));

  if (!matches.length) return res.status(502).json({ error: 'AI returned no valid occupation matches. Try again.' });

  console.log(`plan ok in ${Date.now() - t0}ms, ${matches.length} matches`);
  res.json({
    profile: { summary: String(ai.profile?.summary || ''), skills: (ai.profile?.skills || []).map(String).slice(0, 10) },
    matches,
    neighborhoods: rankNeighborhoods(neighborhoods, matches[0].median_annual),
    plan_90_day: (ai.plan_90_day || []).map((p) => ({ weeks: String(p.weeks || ''), action: String(p.action || '') })),
    communities: picked,
    model: currentModel(),
  });
});

app.listen(PORT, () => {
  console.log(`Stay305 on http://localhost:${PORT}`);
  resolveModel().catch((e) => console.warn('Model not resolved yet:', e.message));
});
