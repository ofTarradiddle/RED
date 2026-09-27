'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const arcade = require('../assets/innovation-arcade-engine.js');

function near(actual, expected) { assert.ok(Math.abs(actual - expected) < 1e-7 * Math.max(1, Math.abs(expected)), `${actual} should equal ${expected}`); }
function fixture(count = 12) {
  const dates = Array.from({length: count + 1}, (_, index) => new Date(Date.UTC(2020, index + 1, 0)).toISOString().slice(0, 10));
  return {
    schemaVersion: 1, id: 'arcade-fixture', asOf: dates[count], benchmarkAssetId: 'MARKET',
    assets: [
      {id: 'A', name: 'Alpha', ticker: 'A', points: dates.map((date, index) => ({date, adjustedClose: 10 * Math.pow(1.2, index), close: 100 * Math.pow(1.1, index), distribution: 2, split: 2}))},
      {id: 'B', name: 'Beta', ticker: 'B', points: dates.map((date, index) => ({date, adjustedClose: 10 * Math.pow(0.5, index)}))},
      {id: 'MARKET', name: 'Market', ticker: 'MKT', points: dates.map((date, index) => ({date, adjustedClose: 100 * Math.pow(1.02, index)}))}
    ],
    opportunities: dates.slice(0, count).map((date, index) => ({
      id: 'event-' + String(index).padStart(2, '0'), assetId: index % 2 ? 'B' : 'A', date, title: 'Idea ' + index,
      decision: {marketOpportunity: 'A new opportunity.', investmentThesis: 'Investing in a new product.', risks: 'Adoption remains uncertain.',
        valuation: {pe: 20, availableAt: date}, investment: {rd: 100, availableAt: dates[count]}},
      outcome: {spillovers: 'A later outcome that must stay hidden.'}
    }))
  };
}
function finish(data, settings, fraction) {
  let run = arcade.create(data, settings);
  while (run.status === 'active') run = arcade.choose(data, run, fraction);
  return run;
}

test('Classic is exactly twelve strictly chronological decisions followed by the published endpoint', () => {
  const data = fixture(24), selected = arcade.selection(data, {mode: 'classic'});
  assert.equal(selected.rounds, 12); assert.equal(selected.ids.length, 12);
  assert.equal(new Set(selected.ids).size, 12);
  selected.dates.slice(1).forEach((date, index) => assert.ok(date > selected.dates[index]));
  const run = finish(data, {mode: 'classic'}, 0);
  assert.equal(run.round, 12); assert.equal(run.status, 'complete');
  assert.equal(run.lastResult.to, data.asOf); assert.equal(arcade.current(data, run), null);
  assert.equal(arcade.score(data, run).endValue, 100);
});

test('the allocation is a fraction of total capital after liquidation, not just leftover cash', () => {
  const data = fixture();
  const first = arcade.create(data);
  const second = arcade.choose(data, first, 0.5);
  near(second.lastResult.before, 100); near(second.lastResult.after, 110); near(second.lastResult.change, 0.1);
  assert.equal(second.lastResult.company, 'Alpha'); assert.equal(second.lastResult.allocation, 0.5);
  near(arcade.current(data, second).capital, 110);
  const third = arcade.choose(data, second, 0.5);
  near(third.lastResult.invested, 55); near(third.lastResult.cashHeld, 55);
  near(third.lastResult.before, 110); near(third.lastResult.after, 82.5);
  near(third.lastResult.change, -0.25);
  assert.deepEqual(third.state.trades.map(trade => trade.side), ['buy', 'sell', 'buy']);
  assert.equal(first.choices.length, 0, 'choosing does not mutate the previous run');
});

test('choosing zero exits the previous investment and preserves the resulting cash', () => {
  const data = fixture();
  const invested = arcade.choose(data, arcade.create(data), 1);
  const passed = arcade.choose(data, invested, 0);
  near(passed.lastResult.before, 120); near(passed.lastResult.after, 120);
  near(arcade.portfolio(data, passed).cash, 120);
  assert.equal(passed.lastResult.allocation, 0);
  assert.equal(passed.state.trades.at(-1).side, 'sell');
});

test('full allocation compounds only the adjusted-price return without double-crediting distributions or splits', () => {
  const data = fixture(), run = finish(data, {mode: 'classic'}, 1);
  near(arcade.score(data, run).endValue, 100 * Math.pow(1.2 * 0.5, 6));
  assert.equal(run.round, 12);
  assert.ok(run.state.cash <= 1e-10);
});

test('Daily selections are reproducible for the same day and separate from other days and Classic', () => {
  const data = fixture(36), day = '2026-09-27';
  const one = arcade.selection(data, {mode: 'daily', day});
  const freshCopy = JSON.parse(JSON.stringify(data));
  assert.deepEqual(arcade.selection(freshCopy, {mode: 'daily', day}), one);
  const two = arcade.selection(data, {mode: 'daily', day: '2026-09-28'});
  assert.notEqual(one.editionId, two.editionId); assert.notDeepEqual(one.ids, two.ids);
  assert.notEqual(one.editionId, arcade.selection(data, {mode: 'classic'}).editionId);
  assert.throws(() => arcade.create(data, {mode: 'daily'}), /YYYY-MM-DD/);
  assert.throws(() => arcade.create(data, {mode: 'daily', day: '2026-02-30'}), /YYYY-MM-DD/);
});

test('allocations cannot borrow, short, inject cash or use fractions outside the four controls', () => {
  const data = fixture(), run = arcade.create(data);
  for (const fraction of [-1, 1.1, 25, 0.1, Infinity, NaN, '0.5', null]) assert.throws(() => arcade.choose(data, run, fraction), /allocation/);
  const zero = arcade.choose(data, run, 0);
  assert.equal(zero.lastResult.before, 100); assert.equal(zero.lastResult.after, 100);
});

test('a current card exposes only dated information and the capital for this turn', () => {
  const data = fixture(), card = arcade.current(data, arcade.create(data));
  assert.equal(card.round, 1); assert.equal(card.rounds, 12); assert.equal(card.capital, 100);
  assert.equal(card.decision.valuation.pe, 20);
  assert.equal(card.decision.investment, undefined);
  assert.equal(card.outcome, undefined);
  assert.equal(JSON.stringify(card).includes('later outcome'), false);
});

test('save and restore replays canonical choices and ignores forged balances, rounds and outcomes', () => {
  const data = fixture();
  const run = arcade.choose(data, arcade.choose(data, arcade.create(data), 0.5), 1);
  assert.deepEqual(arcade.restore(data, arcade.serialize(run)), run);
  const saved = JSON.parse(arcade.serialize(run));
  saved.state = {cash: 1e12}; saved.round = 12; saved.lastResult = {after: 1e12};
  assert.deepEqual(arcade.restore(data, JSON.stringify(saved)), run);
  const corrupted = JSON.parse(JSON.stringify(run)); corrupted.state.cash = 1e12;
  near(arcade.portfolio(data, corrupted).value, arcade.portfolio(data, run).value);
  near(arcade.score(data, corrupted).endValue, arcade.score(data, run).endValue);
});

test('saved choices cannot silently move to a different day or revised price history', () => {
  const data = fixture(24), run = arcade.choose(data, arcade.create(data, {mode: 'daily', day: '2026-09-27'}), 0.25);
  const saved = JSON.parse(arcade.serialize(run)); saved.day = '2026-09-28';
  assert.throws(() => arcade.restore(data, JSON.stringify(saved)), /different/);
  const changed = JSON.parse(JSON.stringify(data)); changed.assets[0].points[0].adjustedClose += 1;
  assert.throws(() => arcade.restore(changed, arcade.serialize(run)), /different/);
  assert.throws(() => arcade.restore(data, '{broken'), /valid JSON/);
  assert.throws(() => arcade.restore(data, ' '.repeat(65537)), /bounded/);
});

test('timestamp-only rebuilds retain the Classic and Daily challenge editions', () => {
  const data = fixture(24), run = arcade.choose(data, arcade.create(data, {mode: 'daily', day: '2026-09-27'}), 0.5);
  const changed = JSON.parse(JSON.stringify(data)); changed.generatedAt = '2027-01-01T00:00:00Z'; changed.version = 'new-archive-retrieval';
  assert.deepEqual(arcade.restore(changed, arcade.serialize(run)), run);
});

test('an opportunity with no current or no final quote cannot enter the playable selection', () => {
  const data = fixture(24);
  data.assets.push({id: 'NEW', name: 'New company', points: [{date: data.asOf, adjustedClose: 10}]});
  data.opportunities[0].assetId = 'NEW';
  const selected = arcade.selection(data, {mode: 'classic'});
  assert.equal(selected.ids.includes(data.opportunities[0].id), false);
  const missingFinal = fixture(24); missingFinal.assets[1].points.pop();
  const onlyCovered = arcade.selection(missingFinal, {mode: 'classic'});
  assert.ok(onlyCovered.ids.every(id => missingFinal.opportunities.find(event => event.id === id).assetId === 'A'));
});

test('selection skips a date when the preceding investment has no exact liquidation quote', () => {
  const data = fixture(24);
  // Enough fully covered A-only gates remain after removing every intervening
  // B gate's quote for A. A previous close cannot be used to sell A at B's gate.
  data.assets[0].points = data.assets[0].points.filter((point, index) => index % 2 === 0);
  const chosen = arcade.selection(data, {mode: 'classic'});
  assert.equal(chosen.ids.length, 12);
  const run = finish(data, {mode: 'classic'}, 1);
  assert.equal(run.status, 'complete');
  run.state.trades.forEach(trade => assert.equal(trade.date, trade.quoteDate));
});

test('a dataset with too few valid rounds fails visibly instead of adding fictional events', () => {
  assert.throws(() => arcade.create(fixture(11)), /twelve/);
  const sameDate = fixture(12); sameDate.opportunities.forEach(event => { event.date = sameDate.opportunities[0].date; });
  assert.throws(() => arcade.create(sameDate), /chronological/);
});

test('a documented total loss ends an all-in run, while uninvested cash remains playable', () => {
  const data = fixture(24);
  data.assets[0].points.slice(1).forEach(point => { point.adjustedClose = 0; });
  const allIn = arcade.choose(data, arcade.create(data), 1);
  assert.equal(allIn.status, 'bankrupt'); assert.equal(arcade.current(data, allIn), null);
  assert.equal(arcade.score(data, allIn).endValue, 0);
  assert.throws(() => arcade.choose(data, allIn, 0), /ended/);
  const half = arcade.choose(data, arcade.create(data), 0.5);
  assert.equal(half.status, 'active'); near(arcade.portfolio(data, half).value, 50);
});

test('finished runs reject extra decisions and carry edition-specific replay metadata', () => {
  const data = fixture(24), run = finish(data, {mode: 'daily', day: '2026-09-27'}, 0.25), score = arcade.score(data, run);
  assert.equal(score.complete, true); assert.equal(score.comparable, true); assert.equal(score.decisions, 12);
  assert.equal(score.mode, 'daily'); assert.equal(score.day, '2026-09-27');
  assert.equal(score.editionId, run.editionId); assert.match(score.disclosure, /hindsight/);
  assert.deepEqual(arcade.restore(data, JSON.stringify(score.replay)), run);
  assert.throws(() => arcade.choose(data, run, 0), /ended/);
  assert.throws(() => arcade.replay(data, {mode: 'classic', choices: Array(13).fill(0)}), /twelve/);
});

test('both engines load as plain JavaScript globals without Node, browser DOM or network APIs', () => {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(require.resolve('../assets/innovation-game-engine.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(require.resolve('../assets/innovation-arcade-engine.js'), 'utf8'), context);
  context.dataJSON = JSON.stringify(fixture());
  const snapshot = vm.runInContext("const data=JSON.parse(dataJSON); let run=InnovationArcade.create(data); run=InnovationArcade.choose(data,run,.5); JSON.stringify({card:InnovationArcade.current(data,run),book:InnovationArcade.portfolio(data,run),result:run.lastResult,save:InnovationArcade.serialize(run)})", context);
  const result = JSON.parse(snapshot);
  near(result.book.value, 110); assert.equal(result.card.round, 2); assert.equal(result.result.company, 'Alpha');
  assert.ok(result.save.includes('choices'));
});
