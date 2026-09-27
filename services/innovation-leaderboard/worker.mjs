import InnovationGame from '../../assets/innovation-game-engine.js';

const MAX_BODY_BYTES = 65536;
const MAX_DATASET_BYTES = 32 * 1024 * 1024;
const MAX_ACTIONS = 2000;
const DATASET_ID = /^innovation-v1-[0-9a-f]{8}$/;
const VERIFICATION = 'replayed-arithmetic';
const PUBLIC_COLUMNS = 'display_name, score_value, score_change, decisions, submitted_at, replay_id, benchmark_value, start_date, end_date';

class HTTPError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
function reject(status, message) { throw new HTTPError(status, message); }
function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function knownKeys(value, keys) { return Object.keys(value).every(key => keys.includes(key)); }
function json(body, status, origin, extraHeaders = {}) {
  const headers = new Headers({
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Vary': 'Origin',
    ...extraHeaders
  });
  if (origin) headers.set('Access-Control-Allow-Origin', origin);
  return new Response(body === null ? null : JSON.stringify(body), {status, headers});
}

async function limitedBytes(message, maximum) {
  const announced = Number(message.headers.get('Content-Length'));
  if (Number.isFinite(announced) && announced > maximum) reject(413, 'The request or data file is too large.');
  if (!message.body) return new Uint8Array();
  const reader = message.body.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > maximum) {
        await reader.cancel();
        reject(413, 'The request or data file is too large.');
      }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let position = 0;
  for (const chunk of chunks) { bytes.set(chunk, position); position += chunk.byteLength; }
  return bytes;
}

function parseJSON(bytes) {
  try { return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)); }
  catch (_) { reject(400, 'The body must contain valid UTF-8 JSON.'); }
}

function displayName(value) {
  if (typeof value !== 'string') reject(400, 'Choose a display name.');
  const cleaned = value.normalize('NFKC').trim().replace(/\s+/gu, ' ');
  const characters = Array.from(cleaned);
  if (characters.length < 1 || characters.length > 20 || !/^[\p{L}\p{N} ._'-]+$/u.test(cleaned)) reject(400, 'Use 1–20 letters, numbers, spaces or simple punctuation for your display name.');
  return cleaned;
}

function submission(value) {
  if (!object(value) || !knownKeys(value, ['name', 'datasetId', 'actions']) || !DATASET_ID.test(value.datasetId || '') || !Array.isArray(value.actions) || value.actions.length > MAX_ACTIONS) reject(400, 'Send only a display name, datasetId and a bounded list of decisions.');
  value.actions.forEach(action => {
    if (!object(action) || !knownKeys(action, ['opportunityId', 'amount', 'sells'])) reject(400, 'The decision format is invalid.');
    if (action.sells !== undefined && (!Array.isArray(action.sells) || action.sells.length > 200 || action.sells.some(sale => !object(sale) || !knownKeys(sale, ['assetId', 'amount'])))) reject(400, 'The sale format is invalid.');
  });
  return {name: displayName(value.name), datasetId: value.datasetId, actions: value.actions};
}

function publicRow(row) {
  return {
    name: row.display_name, endValue: row.score_value, change: row.score_change,
    decisions: row.decisions, submittedAt: row.submitted_at, replayId: row.replay_id,
    benchmarkValue: row.benchmark_value, startDate: row.start_date, endDate: row.end_date
  };
}

export function createHandler(dependencies = {}) {
  const fetchData = dependencies.fetch || globalThis.fetch;
  const cryptography = dependencies.crypto || globalThis.crypto;
  const now = dependencies.now || (() => new Date());
  const datasets = new Map();

  async function sha256(bytes) {
    const digest = await cryptography.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  }

  async function trustedDataset(env) {
    let url;
    try { url = new URL(env.DATASET_URL); } catch (_) { reject(503, 'The leaderboard dataset is not configured.'); }
    if (url.protocol !== 'https:' || url.username || url.password || !/^[0-9a-f]{64}$/.test(env.DATASET_SHA256 || '')) reject(503, 'The leaderboard requires a trusted HTTPS dataset and its SHA-256 digest.');
    const key = url.href + '|' + env.DATASET_SHA256;
    if (!datasets.has(key)) {
      if (datasets.size >= 4) datasets.delete(datasets.keys().next().value);
      const pending = (async () => {
        const response = await fetchData(url.href, {redirect: 'error', signal: AbortSignal.timeout(20000), cf: {cacheTtl: 3600, cacheEverything: true}});
        if (!response.ok) reject(503, 'The pinned dataset is temporarily unavailable.');
        const bytes = await limitedBytes(response, MAX_DATASET_BYTES);
        if (await sha256(bytes) !== env.DATASET_SHA256) reject(503, 'The published dataset does not match the configured digest.');
        const data = parseJSON(bytes);
        const id = InnovationGame.datasetId(data);
        if (data.opportunities.length > MAX_ACTIONS || data.assets.length > 5000) reject(503, 'The configured dataset exceeds this leaderboard’s bounds.');
        return {data, id};
      })();
      datasets.set(key, pending);
      pending.catch(() => { if (datasets.get(key) === pending) datasets.delete(key); });
    }
    try { return await datasets.get(key); }
    catch (error) {
      if (error instanceof HTTPError && error.status === 503) throw error;
      reject(503, 'The trusted dataset could not be loaded and validated.');
    }
  }

  return {
    async fetch(request, env) {
      let responseOrigin = null;
      try {
        const url = new URL(request.url), origin = request.headers.get('Origin');
        const allowed = new Set(String(env.ALLOWED_ORIGINS || '').split(',').map(value => value.trim()).filter(Boolean));
        if (origin && !allowed.has(origin)) reject(403, 'This origin is not allowed.');
        responseOrigin = origin;
        if (url.pathname !== '/scores') reject(404, 'The leaderboard endpoint is /scores.');
        if (request.method === 'OPTIONS') {
          if (!origin) reject(400, 'A preflight request requires an origin.');
          return json(null, 204, responseOrigin, {'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '86400'});
        }
        if (!['GET', 'POST'].includes(request.method)) return json({error: 'Use GET or POST.'}, 405, responseOrigin, {Allow: 'GET, POST, OPTIONS'});
        if (!env.DB || !env.RATE_LIMITER || typeof env.RATE_LIMITER.limit !== 'function') reject(503, 'The leaderboard database and rate limiter must be configured.');
        if (request.method === 'POST' && !origin) reject(403, 'Score submissions require an allowed website origin.');
        // CF-Connecting-IP is supplied by Cloudflare. It is only an ephemeral
        // rate-limit key; IP addresses are not written to the score database.
        const key = request.method + ':' + (request.headers.get('CF-Connecting-IP') || 'local-development');
        const limit = await env.RATE_LIMITER.limit({key});
        if (!limit.success) return json({error: 'Too many requests. Try again shortly.'}, 429, responseOrigin, {'Retry-After': '60'});

        let entry = null;
        if (request.method === 'POST') {
          if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get('Content-Type') || '')) reject(415, 'Submit application/json.');
          entry = submission(parseJSON(await limitedBytes(request, MAX_BODY_BYTES)));
        }
        const trusted = await trustedDataset(env);
        const requestedID = entry ? entry.datasetId : url.searchParams.get('datasetId');
        if (!DATASET_ID.test(requestedID || '')) reject(400, 'A canonical datasetId is required.');
        if (requestedID !== trusted.id) reject(409, 'This leaderboard uses a different dataset. Reload the game or use the matching archived leaderboard.');

        if (request.method === 'GET') {
          const result = await env.DB.prepare('SELECT ' + PUBLIC_COLUMNS + ' FROM innovation_scores WHERE dataset_id = ? ORDER BY score_value DESC, submitted_at ASC, run_hash ASC LIMIT 20').bind(trusted.id).all();
          return json({datasetId: trusted.id, asOf: trusted.data.asOf, verification: VERIFICATION, scores: (result.results || []).map(publicRow)}, 200, responseOrigin);
        }

        let verified;
        try { verified = InnovationGame.score(trusted.data, InnovationGame.replay(trusted.data, entry.actions)); }
        catch (error) { reject(400, 'The submitted decisions do not form a valid game: ' + error.message); }
        if (!verified.complete || !verified.comparable || !Number.isFinite(verified.endValue)) reject(422, 'Only completed games under the standard $100 rules with sufficiently current valuations can enter this board.');
        const actionsJSON = JSON.stringify(verified.replay.actions);
        const runHash = await sha256(new TextEncoder().encode(JSON.stringify(verified.replay)));
        const submittedAt = now().toISOString();
        const inserted = await env.DB.prepare(
          'INSERT INTO innovation_scores (dataset_id, run_hash, replay_id, display_name, score_value, score_change, decisions, benchmark_value, start_date, end_date, actions_json, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(dataset_id, run_hash) DO NOTHING'
        ).bind(trusted.id, runHash, verified.replayId, entry.name, verified.endValue, verified.change, verified.decisions, verified.benchmarkValue, verified.startDate, verified.endDate, actionsJSON, submittedAt).run();
        const row = await env.DB.prepare('SELECT ' + PUBLIC_COLUMNS + ' FROM innovation_scores WHERE dataset_id = ? AND run_hash = ?').bind(trusted.id, runHash).first();
        if (!row) reject(503, 'The score could not be confirmed after saving.');
        const duplicate = inserted.meta?.changes === 0;
        return json({datasetId: trusted.id, asOf: trusted.data.asOf, verification: VERIFICATION, duplicate, score: publicRow(row)}, duplicate ? 200 : 201, responseOrigin);
      } catch (error) {
        const status = error instanceof HTTPError ? error.status : 503;
        return json({error: error instanceof HTTPError ? error.message : 'The leaderboard is temporarily unavailable.'}, status, responseOrigin);
      }
    }
  };
}

export default createHandler();
