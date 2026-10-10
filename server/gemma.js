// Gemma 4 via the Gemini API (@google/genai).
import { GoogleGenAI } from '@google/genai';

const TIMEOUT_MS = 60_000;
let ai = null;
let modelId = process.env.GEMMA_MODEL || null;

function client() {
  if (!process.env.GEMINI_API_KEY) throw new Error('GEMINI_API_KEY is not set (put it in server/.env)');
  if (!ai) ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  return ai;
}

// Resolve the Gemma 4 model id from ListModels unless GEMMA_MODEL pins one.
export async function resolveModel() {
  if (modelId) return modelId;
  const names = [];
  const pager = await client().models.list();
  for await (const m of pager) names.push(m.name.replace(/^models\//, ''));
  const gemma4 = names.filter((n) => n.startsWith('gemma-4'));
  if (!gemma4.length) throw new Error(`No gemma-4 model available. Gemma models seen: ${names.filter((n) => n.startsWith('gemma')).join(', ') || 'none'}`);
  // Prefer the largest instruction-tuned variant (best reasoning for the demo).
  const size = (n) => Number((n.match(/(\d+)b/) || [0, 0])[1]);
  gemma4.sort((a, b) => size(b) - size(a));
  modelId = gemma4[0];
  console.log(`Gemma 4 models available: ${gemma4.join(', ')} -> using ${modelId}`);
  return modelId;
}

export function currentModel() {
  return modelId;
}

function parseDataUrl(dataUrl) {
  const m = /^data:([^;]+);base64,(.+)$/s.exec(dataUrl || '');
  if (!m) throw new Error('resumeImage must be a base64 data URL');
  return { mimeType: m[1], data: m[2] };
}

// Pull the first JSON object out of a model reply (Gemma may wrap it in ``` fences).
function extractJson(text) {
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start < 0 || end <= start) throw new Error('Gemma did not return JSON');
  return JSON.parse(text.slice(start, end + 1));
}

function buildPrompt({ resumeText, goals, major, occupations, communities }) {
  const occList = occupations.map((o) => `${o.soc} | ${o.title} | median $${o.median_annual}`).join('\n');
  const comList = communities.map((c) => `${c.name} | ${c.type} | ${(c.fields || []).join(', ')} | ${c.description || ''}`).join('\n');
  return `You are Stay305, a career coach helping a graduating college senior in Miami build a career here instead of leaving.

STUDENT
Major: ${major || 'not given'}
Goals: ${goals || 'not given'}
Resume: ${resumeText ? '\n' + resumeText : '(see attached image)'}

MIAMI OCCUPATIONS (SOC | title | Miami metro median annual wage, BLS):
${occList}

MIAMI COMMUNITIES (name | type | fields | description):
${comList}

TASK
1. Summarize the student in one sentence and list their concrete skills (max 10).
2. Choose the 4 occupations from the list above that best fit them, considering wage and realistic fit for a new grad. Use ONLY SOC codes from the list.
3. For each, give a fit_score from 0 to 1, a one-sentence "why" that cites their resume, and 2-4 specific skill_gaps.
4. Write a 90-day plan (5-6 steps, each tied to weeks like "1-2") with concrete actions in Miami toward the top match.
5. Choose 3-5 communities from the list above (exact names only) and say why each helps this student.

Reply with ONLY this JSON, no prose:
{"profile":{"summary":"","skills":[]},"matches":[{"soc":"","fit_score":0.0,"why":"","skill_gaps":[]}],"plan_90_day":[{"weeks":"","action":""}],"communities":[{"name":"","why":""}]}`;
}

export async function generatePlan(input) {
  const model = await resolveModel();
  const parts = [{ text: buildPrompt(input) }];
  if (input.resumeImage) parts.push({ inlineData: parseDataUrl(input.resumeImage) });

  const call = client().models.generateContent({
    model,
    contents: [{ role: 'user', parts }],
    config: { temperature: 0.4 },
  });
  const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error(`Gemma timed out after ${TIMEOUT_MS / 1000}s`)), TIMEOUT_MS));
  const res = await Promise.race([call, timeout]);
  return extractJson(res.text || '');
}
