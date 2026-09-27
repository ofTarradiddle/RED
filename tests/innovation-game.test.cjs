'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const game = require('../assets/innovation-game-engine.js');

function near(actual, expected) { assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} should equal ${expected}`); }
function fixture() {
  return {
    asOf: '2020-04-30', benchmarkAssetId: 'MARKET',
    assets: [
      {id: 'A', name: 'Early Innovator', ticker: 'AAA', points: [
        {date: '2020-01-31', adjustedClose: 10, close: 20},
        {date: '2020-02-28', adjustedClose: 8, close: 15, distribution: 1, split: 2},
        {date: '2020-03-31', adjustedClose: 20, close: 20},
        {date: '2020-04-30', adjustedClose: 30, close: 30}
      ]},
      {id: 'B', name: 'New Entrant', ticker: 'BBB', points: [
        {date: '2020-02-28', adjustedClose: 4},
        {date: '2020-03-31', adjustedClose: 8},
        {date: '2020-04-30', adjustedClose: 6}
      ]},
      {id: 'MARKET', name: 'Market', points: [
        {date: '2020-01-31', adjustedClose: 100},
        {date: '2020-02-28', adjustedClose: 110},
        {date: '2020-03-31', adjustedClose: 105},
        {date: '2020-04-30', adjustedClose: 120}
      ]}
    ],
    opportunities: [
      {id: 'a-launch', date: '2020-01-31', assetId: 'A', title: 'A new platform', decision: {
        marketOpportunity: 'A public opportunity known today.',
        valuation: {value: 25, ratio: 'P/E', availableAt: '2020-01-30'},
        investment: {value: 100000000, availableAt: '2020-04-01'},
        outcome: 'Forbidden future story.'
      }, outcome: 'It eventually grew.'},
      {id: 'b-launch', date: '2020-02-28', assetId: 'B', title: 'A competing platform', decision: {marketOpportunity: 'A new competitor.'}},
      {id: 'a-expands', date: '2020-03-31', assetId: 'A', title: 'Expansion', decision: {marketOpportunity: 'A larger addressable market.'}}
    ]
  };
}

test('fractional adjusted-price units compound returns without double-counting splits or dividends', () => {
  const data = fixture(), first = game.createGame(data), next = game.decide(data, first, {amount: 25});
  near(next.positions.A, 2.5);
  near(next.cash, 75);
  near(game.portfolio(data, next).value, 95);
  assert.equal(first.cash, 100, 'decisions do not mutate their input state');
  assert.equal(first.trades.length, 0);
  const end = game.decide(data, game.decide(data, next, {amount: 0}), {amount: 0});
  near(game.portfolio(data, end).value, 150);
  near(game.score(data, end).change, 0.5);
  near(game.portfolio(data, end).benchmark.value, 120);
  assert.equal(end.trades[0].units, 2.5);
  assert.equal(end.trades[0].quoteDate, '2020-01-31');
});

test('a sale recycles cash into another firm at the current decision close', () => {
  const data = fixture();
  let state = game.decide(data, game.createGame(data), {amount: 100});
  state = game.decide(data, state, {sells: [{assetId: 'A', amount: 40}], amount: 40});
  near(state.positions.A, 5); near(state.positions.B, 10); near(state.cash, 0);
  near(game.portfolio(data, state).value, 180);
  state = game.decide(data, state, {amount: 0});
  near(game.portfolio(data, state).value, 210);
  assert.deepEqual(state.trades.map(trade => trade.side), ['buy', 'sell', 'buy']);
});

test('cash stays at zero interest, and a pass never buys an asset', () => {
  const data = fixture();
  const state = game.replay(data, [{amount: 0}, {amount: 0}, {amount: 0}]);
  assert.equal(state.status, 'complete'); assert.equal(state.cash, 100);
  assert.equal(state.trades.length, 0); assert.equal(game.score(data, state).endValue, 100);
});

test('no borrowing, short positions, overselling, negative amounts or nonfinite orders', () => {
  const data = fixture(), first = game.createGame(data);
  for (const amount of [101, -1, Infinity, NaN, '10']) assert.throws(() => game.decide(data, first, {amount}));
  assert.throws(() => game.decide(data, first, {sells: [{assetId: 'A', amount: 1}]}), /do not own/);
  const owned = game.decide(data, first, {amount: 50});
  assert.throws(() => game.decide(data, owned, {sells: [{assetId: 'A', amount: 41}]}), /exceed/);
  assert.throws(() => game.decide(data, owned, {sells: [{assetId: 'A', amount: 5}, {assetId: 'A', amount: 5}]}), /different/);
});

test('pre-IPO opportunities cannot invent a quote, but players can continue in cash', () => {
  const data = fixture(); data.opportunities[0].assetId = 'B';
  const state = game.createGame(data), card = game.currentDecision(data, state);
  assert.equal(card.quote, null); assert.equal(card.canInvest, false);
  assert.throws(() => game.decide(data, state, {amount: 1}), /execution quote/);
  assert.equal(game.decide(data, state, {amount: 0}).cash, 100);
});

test('earlier quotes can value a holding but cannot fill a later information-date trade', () => {
  const data = fixture(); data.opportunities[0].date = '2020-02-01';
  const state = game.createGame(data), card = game.currentDecision(data, state);
  assert.equal(card.quote.date, '2020-01-31'); assert.equal(card.canInvest, false);
  assert.throws(() => game.decide(data, state, {amount: 1}), /execution quote/);
  assert.equal(game.quoteAt(data, 'A', '2020-02-15').value, 10);
});

test('future financial filings and retrospective narratives are absent from decision cards', () => {
  const data = fixture(), state = game.createGame(data), card = game.currentDecision(data, state);
  assert.equal(card.decision.valuation.value, 25);
  assert.equal(card.decision.investment, undefined);
  assert.equal(card.decision.outcome, undefined); assert.equal(card.outcome, undefined);
  assert.equal(JSON.stringify(card).includes('eventually'), false);
  const next = game.decide(data, state, {amount: 0});
  assert.deepEqual(game.outcomes(data, next), []);
  const end = game.decide(data, game.decide(data, next, {amount: 0}), {amount: 0});
  assert.equal(game.outcomes(data, end)[0].outcome, 'It eventually grew.');
});

test('no future quote or future portfolio date is exposed through the public lookup', () => {
  const data = fixture(), state = game.createGame(data);
  assert.equal(game.quoteAt(data, 'A', '2020-02-27').value, 10);
  assert.throws(() => game.portfolio(data, state, '2020-04-30'), /future/);
  assert.throws(() => game.quoteAt(data, 'A', '2021-01-01'), /published history/);
});

test('missing post-delisting coverage is flagged instead of invented as a total loss', () => {
  const data = fixture(); data.assets[0].points = data.assets[0].points.slice(0, 1);
  const state = game.replay(data, [{amount: 100}, {amount: 0}, {amount: 0}]);
  assert.equal(game.portfolio(data, state).value, 100);
  assert.equal(game.portfolio(data, state).positions[0].stale, true);
  assert.equal(game.score(data, state).comparable, false);
  assert.match(game.score(data, state).warnings.join(' '), /delisting payoff/);
});

test('a documented zero index causes bankruptcy only when the investor has no cash left', () => {
  const data = fixture(); data.assets[0].points.slice(1).forEach(point => { point.adjustedClose = 0; });
  const allIn = game.decide(data, game.createGame(data), {amount: 100});
  assert.equal(allIn.status, 'bankrupt'); assert.equal(game.portfolio(data, allIn).value, 0);
  assert.throws(() => game.decide(data, allIn, {amount: 0}), /ended/);
  const cashLeft = game.decide(data, game.createGame(data), {amount: 99.99});
  assert.equal(cashLeft.status, 'active'); near(game.portfolio(data, cashLeft).value, 0.01);
});

test('positive but tiny capital does not trigger an invented bankruptcy threshold', () => {
  const data = fixture(); data.assets[0].points.slice(1).forEach(point => { point.adjustedClose = 0.0000001; });
  const state = game.decide(data, game.createGame(data), {amount: 100});
  assert.equal(state.status, 'active'); assert.ok(game.portfolio(data, state).value > 0);
});

test('a newer benchmark starts at its real first quote, with its earlier cash period disclosed', () => {
  const data = fixture(); data.assets[2].points.shift();
  const initial = game.createGame(data), waiting = game.portfolio(data, initial).benchmark;
  assert.equal(waiting.status, 'waiting-for-history'); assert.equal(waiting.value, 100);
  const end = game.replay(data, [{amount: 0}, {amount: 0}, {amount: 0}]);
  const mark = game.portfolio(data, end).benchmark;
  near(mark.value, 100 * 120 / 110); assert.equal(mark.from, '2020-02-28'); assert.equal(mark.cashBeforeInception, true);
});

test('saved games are rebuilt from decisions and never trust saved balances', () => {
  const data = fixture(), state = game.decide(data, game.createGame(data), {amount: 37.50});
  const save = JSON.parse(game.serialize(state)); save.cash = 100000000; save.positions = {A: 100000};
  assert.deepEqual(game.restore(data, save), state);
  state.cash = 99999999;
  near(game.score(data, state).endValue, 92.5);
});

test('a save cannot silently migrate onto revised prices or a different decision sequence', () => {
  const data = fixture(), state = game.decide(data, game.createGame(data), {amount: 10});
  const changed = fixture(); changed.assets[0].points[0].adjustedClose = 11;
  assert.throws(() => game.restore(changed, game.serialize(state)), /different data/);
  assert.throws(() => game.replay(data, [{opportunityId: 'b-launch', amount: 0}]), /decision order/);
  assert.throws(() => game.restore(data, '{broken'), /valid JSON/);
});

test('unchanged economic history keeps saved games across rebuild and retrieval timestamp changes', () => {
  const original = fixture();
  original.id = 'history'; original.version = 'archive-hash-before';
  original.generatedAt = '2026-09-26T00:00:00Z';
  original.assets[0].retrievedAt = '2026-09-26T00:00:00Z';
  const state = game.decide(original, game.createGame(original), {amount: 25});
  const rebuilt = JSON.parse(JSON.stringify(original));
  rebuilt.version = 'archive-hash-after';
  rebuilt.generatedAt = '2026-09-27T12:00:00Z';
  rebuilt.assets[0].retrievedAt = '2026-09-27T12:00:00Z';
  // JSON object key order has no economic meaning either.
  rebuilt.opportunities[0].decision.valuation = Object.fromEntries(Object.entries(rebuilt.opportunities[0].decision.valuation).reverse());
  assert.equal(game.datasetId(rebuilt), game.datasetId(original));
  assert.deepEqual(game.restore(rebuilt, game.serialize(state)), state);
});

test('game edition fingerprints cover adjusted and raw prices, financial evidence, dates and explicit rule editions', () => {
  const original = fixture(); original.id = 'history'; original.gameVersion = 1;
  const state = game.decide(original, game.createGame(original), {amount: 25});
  for (const mutate of [
    data => { data.assets[0].points[0].adjustedClose = 11; },
    data => { data.assets[0].points[0].close = 21; },
    data => { data.opportunities[0].decision.valuation.value = 30; },
    data => { data.opportunities[0].decision.valuation.availableAt = '2020-01-31'; },
    data => { data.opportunities[0].decision.marketOpportunity = 'A materially different brief.'; },
    data => { data.opportunities[1].date = '2020-02-29'; },
    data => { data.opportunities[0].canTrade = false; },
    data => { data.asOf = '2020-05-01'; },
    data => { data.gameVersion = 2; },
    data => { data.schemaVersion = 2; }
  ]) {
    const changed = JSON.parse(JSON.stringify(original)); mutate(changed);
    assert.notEqual(game.datasetId(changed), game.datasetId(original));
    assert.throws(() => game.restore(changed, game.serialize(state)), /different data/);
  }
});

test('score replay rejects inflated leaderboard claims and records the actual horizon', () => {
  const data = fixture(), state = game.replay(data, [{amount: 100}, {amount: 0}, {amount: 0}]);
  const score = game.score(data, state);
  assert.equal(score.complete, true); assert.equal(score.comparable, true);
  assert.equal(score.startDate, '2020-01-31'); assert.equal(score.endDate, '2020-04-30');
  near(game.verifyScore(data, score).endValue, 300);
  assert.throws(() => game.verifyScore(data, {...score, endValue: 99999}), /claimed score/);
  assert.throws(() => game.verifyScore(data, {...score, replayId: 'fake'}), /identifier/);
  assert.match(score.disclosure, /hindsight/);
});

test('unfinished games and custom capital cannot rank with standard completed $100 games', () => {
  const data = fixture(); assert.equal(game.score(data, game.createGame(data)).comparable, false);
  const custom = game.replay(data, [{amount: 0}, {amount: 0}, {amount: 0}], {initialCapital: 1000});
  assert.equal(game.score(data, custom).defaultRules, false); assert.equal(game.score(data, custom).comparable, false);
});

test('equity history preserves each decision mark and benchmark without mutating prior entries', () => {
  const data = fixture(), state = game.replay(data, [{amount: 100}, {amount: 0}, {amount: 0}]);
  assert.deepEqual(state.history.map(point => point.value), [100, 80, 200, 300]);
  assert.deepEqual(state.history.map(point => point.benchmarkValue), [100, 110, 105, 120]);
  const subsequentTrades = game.replay(data, [{amount: 50}, {amount: 25}, {amount: 0}]);
  assert.throws(() => game.portfolio(data, subsequentTrades, '2020-01-31'), /saved equity history/);
});

test('invalid histories, impossible dates, future events and foreign currency are rejected', () => {
  for (const mutate of [
    data => { data.assets[0].points[0].date = '2020-02-30'; },
    data => { data.assets[0].points[0].adjustedClose = -1; },
    data => { data.assets[0].points[0].adjustedClose = Infinity; },
    data => { data.assets[0].points.push({...data.assets[0].points[0]}); },
    data => { data.assets[0].currency = 'JPY'; },
    data => { data.opportunities[0].eventDate = '2020-02-01'; },
    data => { data.opportunities[0].decision.availableAt = '2020-02-01'; },
    data => { data.assets[0].points[0].adjustedClose = 0; },
    data => { data.assets[0].id = 'toString'; data.opportunities[0].assetId = 'toString'; }
  ]) { const data = fixture(); mutate(data); assert.throws(() => game.createGame(data)); }
  assert.equal(game.validDate('2000-02-29'), true); assert.equal(game.validDate('1900-02-29'), false);
});

test('multiple decisions on the same date preserve order and cannot manufacture a return', () => {
  const data = fixture(); data.opportunities[1].date = '2020-01-31'; data.opportunities[1].assetId = 'A';
  let state = game.decide(data, game.createGame(data), {amount: 20});
  near(game.portfolio(data, state).value, 100);
  state = game.decide(data, state, {amount: 30, sells: [{assetId: 'A', amount: 20}]});
  near(state.cash, 70); near(state.positions.A, 3);
});
