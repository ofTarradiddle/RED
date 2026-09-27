import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash, webcrypto} from 'node:crypto';
import {createHandler} from './worker.mjs';
import game from '../../assets/innovation-game-engine.js';

const origin = 'https://oftarradiddle.github.io';
function fixture() {
  return {
    asOf: '2020-03-31',
    assets: [{id: 'A', name: 'A', points: [
      {date: '2020-01-31', adjustedClose: 10},
      {date: '2020-02-28', adjustedClose: 12},
      {date: '2020-03-31', adjustedClose: 15}
    ]}],
    opportunities: [
      {id: 'first', date: '2020-01-31', assetId: 'A', title: 'First', decision: {}},
      {id: 'second', date: '2020-02-28', assetId: 'A', title: 'Second', decision: {}}
    ]
  };
}

class FakeD1 {
  constructor() { this.rows = new Map(); this.queries = []; }
  prepare(sql) {
    const db = this;
    return {bind(...args) {
      db.queries.push({sql, args});
      return {
        async all() {
          return {success: true, results: [...db.rows.values()].filter(row => row.dataset_id === args[0])
            .sort((a, b) => b.score_value - a.score_value || a.submitted_at.localeCompare(b.submitted_at) || a.run_hash.localeCompare(b.run_hash)).slice(0, 20)};
        },
        async first() { return db.rows.get(args[0] + ':' + args[1]) || null; },
        async run() {
          assert.match(sql, /ON CONFLICT\(dataset_id, run_hash\) DO NOTHING/);
          const fields = ['dataset_id', 'run_hash', 'replay_id', 'display_name', 'score_value', 'score_change', 'decisions', 'benchmark_value', 'start_date', 'end_date', 'actions_json', 'submitted_at'];
          const row = Object.fromEntries(fields.map((field, i) => [field, args[i]]));
          const key = row.dataset_id + ':' + row.run_hash;
          const exists = db.rows.has(key);
          if (!exists) db.rows.set(key, row);
          return {success: true, meta: {changes: exists ? 0 : 1}};
        }
      };
    }};
  }
}

function setup(data = fixture()) {
  const bytes = JSON.stringify(data), fetches = [];
  const handler = createHandler({
    crypto: webcrypto, now: () => new Date('2026-09-26T00:00:00Z'),
    fetch: async url => { fetches.push(url); return new Response(bytes, {headers: {'Content-Type': 'application/json'}}); }
  });
  const env = {
    DATASET_URL: 'https://raw.githubusercontent.com/ofTarradiddle/RED/' + 'a'.repeat(40) + '/data/innovation/dataset.json',
    DATASET_SHA256: createHash('sha256').update(bytes).digest('hex'),
    ALLOWED_ORIGINS: origin, DB: new FakeD1(), RATE_LIMITER: {limit: async () => ({success: true})}
  };
  const datasetId = game.datasetId(data);
  const payload = {name: 'Ada', datasetId, actions: [{opportunityId: 'first', amount: 100}, {opportunityId: 'second', amount: 0}]};
  const send = (value = payload, headers = {}) => handler.fetch(new Request('https://leaderboard.example/scores', {
    method: 'POST', headers: {Origin: origin, 'Content-Type': 'application/json', ...headers}, body: typeof value === 'string' ? value : JSON.stringify(value)
  }), env);
  const get = () => handler.fetch(new Request('https://leaderboard.example/scores?datasetId=' + datasetId, {headers: {Origin: origin}}), env);
  return {handler, env, datasetId, payload, send, get, fetches};
}

test('a completed replay is computed server-side, persisted and ranked without seeded players', async () => {
  const service = setup();
  assert.deepEqual((await (await service.get()).json()).scores, []);
  const saved = await service.send();
  assert.equal(saved.status, 201);
  const body = await saved.json();
  assert.equal(body.score.endValue, 150); assert.equal(body.score.change, 0.5);
  assert.equal(body.verification, 'replayed-arithmetic');
  assert.equal(body.score.submittedAt, '2026-09-26T00:00:00.000Z');
  const list = await (await service.get()).json();
  assert.equal(list.scores[0].name, 'Ada'); assert.equal(list.scores[0].endValue, 150);
  assert.equal(list.scores[0].actions, undefined); assert.equal(list.scores[0].actions_json, undefined);
  assert.equal(service.fetches.length, 1, 'the immutable dataset is reused within the worker');
});

test('identical decisions deduplicate by SHA-256 even if the player changes aliases', async () => {
  const service = setup(); await service.send();
  const duplicate = await service.send({...service.payload, name: 'Other'});
  assert.equal(duplicate.status, 200);
  assert.equal((await duplicate.json()).score.name, 'Ada');
  assert.equal(service.env.DB.rows.size, 1);
  assert.match([...service.env.DB.rows.values()][0].run_hash, /^[a-f0-9]{64}$/);
});

test('client balances, starting capital, unknown fields and overspending are rejected', async () => {
  const service = setup();
  for (const extra of [{endValue: 1e9}, {initialCapital: 1e6}, {dataset: fixture()}]) assert.equal((await service.send({...service.payload, ...extra})).status, 400);
  assert.equal((await service.send({...service.payload, actions: [{amount: 101}]})).status, 400);
  assert.equal(service.env.DB.rows.size, 0);
});

test('partial games cannot enter the board', async () => {
  const service = setup();
  assert.equal((await service.send({...service.payload, actions: []})).status, 422);
  assert.equal((await service.send({...service.payload, actions: [{amount: 20}]})).status, 422);
  assert.equal(service.env.DB.rows.size, 0);
});

test('stale final valuations cannot become a shared leaderboard score', async () => {
  const data = fixture(); data.asOf = '2021-01-01';
  const service = setup(data);
  assert.equal((await service.send()).status, 422);
});

test('the trusted file digest is checked before replay and mismatched versions are separate', async () => {
  const service = setup(); service.env.DATASET_SHA256 = '0'.repeat(64);
  const response = await service.send(); assert.equal(response.status, 503);
  assert.match((await response.json()).error, /digest/);
  const valid = setup();
  assert.equal((await valid.send({...valid.payload, datasetId: 'innovation-v1-deadbeef'})).status, 409);
  assert.equal(valid.env.DB.rows.size, 0);
});

test('CORS preflights only allow configured origins and writes require the website origin', async () => {
  const service = setup();
  const allowed = await service.handler.fetch(new Request('https://leaderboard.example/scores', {method: 'OPTIONS', headers: {Origin: origin}}), service.env);
  assert.equal(allowed.status, 204); assert.equal(allowed.headers.get('Access-Control-Allow-Origin'), origin);
  assert.match(allowed.headers.get('Access-Control-Allow-Methods'), /POST/);
  const rejected = await service.send(service.payload, {Origin: 'https://attacker.example'});
  assert.equal(rejected.status, 403); assert.equal(rejected.headers.has('Access-Control-Allow-Origin'), false);
  const noOrigin = await service.handler.fetch(new Request('https://leaderboard.example/scores', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(service.payload)}), service.env);
  assert.equal(noOrigin.status, 403);
});

test('the actual streamed body is limited even when Content-Length is absent', async () => {
  const service = setup();
  assert.equal((await service.send(' '.repeat(65537))).status, 413);
  assert.equal((await service.send('{')).status, 400);
  assert.equal((await service.send(service.payload, {'Content-Type': 'text/plain'})).status, 415);
});

test('public aliases are bounded, normalized and never interpolated into SQL', async () => {
  const service = setup();
  assert.equal((await service.send({...service.payload, name: '<script>alert(1)</script>'})).status, 400);
  assert.equal((await service.send({...service.payload, name: 'x'.repeat(21)})).status, 400);
  const reply = await service.send({...service.payload, name: "  O'Brien  "});
  assert.equal(reply.status, 201); assert.equal((await reply.json()).score.name, "O'Brien");
  assert.equal(service.env.DB.queries.some(query => query.sql.includes("O'Brien")), false);
  assert.equal(service.env.DB.queries.some(query => query.args.includes("O'Brien")), true);
});

test('rate limiting rejects submissions before data loading or database writes', async () => {
  const service = setup(); service.env.RATE_LIMITER.limit = async () => ({success: false});
  const response = await service.send(); assert.equal(response.status, 429);
  assert.equal(response.headers.get('Retry-After'), '60');
  assert.equal(service.fetches.length, 0); assert.equal(service.env.DB.rows.size, 0);
});

test('missing production bindings fail closed and unsupported routes are explicit', async () => {
  const service = setup(); delete service.env.RATE_LIMITER;
  assert.equal((await service.send()).status, 503);
  assert.equal((await service.handler.fetch(new Request('https://leaderboard.example/other'), service.env)).status, 404);
});
