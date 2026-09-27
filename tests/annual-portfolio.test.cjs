'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const Engine = require('../assets/annual-portfolio-engine.js');

const dates = ['2011-01-03', '2011-06-30', '2012-01-03', '2012-06-29', '2013-01-02', '2013-06-28', '2014-01-02'];
const clone = value => JSON.parse(JSON.stringify(value));
function fixture() {
  const asset = (id, values) => ({id, name: id + ' Corporation', ticker: id, currency: 'USD',
    points: values.map((adjustedClose, index) => ({date: dates[index], adjustedClose, close: adjustedClose * 2})),
    historicalLabels: {'2010': {name: 'Original ' + id, ticker: id + '.OLD', note: 'Historical constituent label'}}, financials: []});
  const assets = [asset('A', [100, 120, 110, 70, 55, 100, 110]), asset('B', [100, 80, 90, 100, 180, 150, 90]),
    asset('SPY', [100, 105, 110, 120, 125, 130, 140]), asset('MISSING', [100, 50])];
  return {schema_version: 1, id: 'annual-test', version: 'economic-v1', asOf: dates.at(-1), frequency: 'monthly',
    benchmarkAssetId: 'SPY', assets, rounds: [2010, 2011, 2012].map((year, index) => ({
      year, cutoff: year + '-12-31', executionDate: dates[index * 2], endDate: dates[index * 2 + 2],
      eligibleAssetIds: index === 1 ? ['B', 'MISSING'] : ['A', 'B', 'MISSING'],
      valuationDates: dates.slice(index * 2, index * 2 + 3)
    }))};
}
function near(actual, expected, tolerance = 1e-10) { assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`); }

test('a whole portfolio allocates one shared $100, retains cash, and attributes its actual interval return', () => {
  const data = fixture(), start = Engine.create(data);
  const next = Engine.allocate(data, start, {A: 0.5, B: 0.25});
  near(next.lastResult.before, 100); near(next.lastResult.after, 102.5);
  near(next.lastResult.change, 0.025); near(next.cash, 25);
  assert.equal(next.lastResult.path.length, 3);
  near(next.lastResult.path[1].value, 105);
  near(next.lastResult.companies.find(item => item.id === 'A').return, 0.1);
  near(next.lastResult.companies.reduce((sum, item) => sum + item.contribution, 0), 0.025);
  assert.equal(start.cash, 100); assert.equal(start.actions.length, 0);
  assert.ok(Object.isFrozen(next)); assert.ok(Object.isFrozen(next.actions[0].weights));
});

test('weights across all names cannot exceed 100%, borrow, short, coerce strings, or use future constituents', () => {
  const data = fixture(), run = Engine.create(data);
  for (const weights of [{A: 1, B: 1}, {A: 1.01}, {A: -0.01}, {A: NaN}, {A: Infinity}, {A: '0.5'}, {A: null}, {SPY: 0.1}]) {
    assert.equal(Engine.validateAllocation(data, run, weights).valid, false);
    assert.throws(() => Engine.allocate(data, run, weights), error => error.code === 'INVALID_ALLOCATION');
  }
  const second = Engine.allocate(data, run, {A: 1});
  assert.throws(() => Engine.allocate(data, second, {A: 0.5}), /not an eligible constituent/);
  const allocation = Engine.validateAllocation(data, run, {A: 0.1, B: 0.9});
  assert.equal(allocation.valid, true); assert.equal(allocation.cashWeight, 0);
});

test('missing terminal prices block a chosen firm rather than fabricate a zero loss or stale exit', () => {
  const data = fixture(), run = Engine.create(data);
  const missing = Engine.current(data, run).companies.find(item => item.id === 'MISSING');
  assert.equal(missing.canInvest, false);
  assert.deepEqual(missing.coverage.missingDates, ['2012-01-03']);
  const validation = Engine.validateAllocation(data, run, {A: 0.5, MISSING: 0.5});
  assert.equal(validation.valid, false); assert.equal(validation.blockedAssets[0].id, 'MISSING');
  assert.throws(() => Engine.allocate(data, run, {MISSING: 1}), error => error.code === 'COVERAGE_GAP');
  assert.equal(run.index, 0); assert.equal(run.cash, 100);
  // Data unavailable for another constituent must not prevent an all-cash year.
  near(Engine.allocate(data, run, {}).lastResult.after, 100);
});

test('missing intermediate marks block the full valuation path even when both annual endpoints exist', () => {
  const data = fixture(); data.assets[0].points.splice(1, 1);
  const run = Engine.create(data);
  assert.deepEqual(Engine.current(data, run).companies[0].coverage.missingDates, ['2011-06-30']);
  assert.throws(() => Engine.allocate(data, run, {A: 1}), error => error.code === 'COVERAGE_GAP');
});

test('reviewed provider observations block only affected rounds and never price a position or reveal future event details', () => {
  const data = fixture(), asset = data.assets.find(item => item.id === 'B');
  const suspect = {...asset.points[3], adjustedClose: 99999};
  asset.points[3] = suspect; // Even an accidental compiler reintroduction must be excluded.
  asset.excludedObservations = [{...suspect, qualityFlagId: 'review-B', source: 'Provider', sourceUrl: 'https://example.test/provider'}];
  asset.qualityFlags = [{id: 'review-B', excludedDate: suspect.date, reason: 'Future spin-off details must remain hidden', sourceReturns: [{returnFraction: -0.8, source: 'Independent archive'}]}];
  const original = Engine.create(data), first = Engine.current(data, original).companies.find(item => item.id === 'B');
  assert.equal(first.canInvest, true); assert.equal(first.coverage.reason, null);
  let run = Engine.allocate(data, original, {B: 1});
  near(run.lastResult.after, 90);
  const blocked = Engine.current(data, run).companies.find(item => item.id === 'B');
  assert.equal(blocked.canInvest, false);
  assert.deepEqual(blocked.coverage.missingDates, ['2012-06-29']);
  assert.equal(blocked.coverage.reason, 'Excluded after provider-quality review; incomplete reliable return path.');
  assert.equal(JSON.stringify(blocked).includes('spin-off'), false);
  assert.equal(Object.hasOwn(blocked, 'excludedObservations'), false);
  assert.equal(Object.hasOwn(blocked, 'qualityFlags'), false);
  assert.throws(() => Engine.allocate(data, run, {B: 1}), error => error.code === 'COVERAGE_GAP');
  run = Engine.allocate(data, run, {});
  const detail = Engine.companyHistory(data, run, 'B');
  assert.equal(detail.mostRecentPeriod.return, null); assert.deepEqual(detail.mostRecentPeriod.path, []);
  assert.equal(Engine.current(data, run).companies.find(item => item.id === 'B').canInvest, true);
  run = Engine.allocate(data, run, {B: 1});
  near(run.lastResult.after, 45); // 90 cash then B 180→90; suspect mark never enters equity.
  assert.ok(run.history.every(point => point.value <= 100));
  const correctedEvidence = clone(data); correctedEvidence.assets[1].qualityFlags[0].reason = 'Revised source review';
  assert.notEqual(Engine.datasetId(correctedEvidence), Engine.datasetId(data));
  const correctedExcludedSource = clone(data); correctedExcludedSource.assets[1].excludedObservations[0].sourceUrl += '/corrected';
  assert.notEqual(Engine.datasetId(correctedExcludedSource), Engine.datasetId(data));
});

test('rebalancing closes prior lots and later reentry excludes the years a firm was not owned', () => {
  const data = fixture();
  let run = Engine.allocate(data, Engine.create(data), {A: 0.5, B: 0.25});
  run = Engine.allocate(data, run, {B: 1});
  near(run.lastResult.before, 102.5); near(run.lastResult.after, 205);
  assert.equal(run.lots[0].closedAt, '2012-01-03'); near(run.lots[0].realizedProfit, 5);
  run = Engine.allocate(data, run, {A: 0.5});
  const book = Engine.portfolio(data, run), company = Engine.companyHistory(data, run, 'A');
  near(book.value, 307.5); near(book.cash, 102.5);
  near(book.companies.reduce((sum, item) => sum + item.profit, 0), book.profit);
  near(book.companies.reduce((sum, item) => sum + item.contribution, 0), book.change);
  near(company.summary.totalInvested, 152.5); near(company.summary.profit, 107.5);
  near(company.summary.returnOnAllocatedCapital, 107.5 / 152.5);
  assert.equal(company.periods.length, 2);
  near(company.periods[0].return, 0.1); near(company.periods[1].return, 1);
  // A lost 50% between these dates, but the portfolio held no A then.
  near(company.path.find(item => item.date === '2012-06-29').profit, 5);
  assert.equal(company.path.find(item => item.date === '2012-06-29').invested, false);
  near(company.path.at(-1).contribution, 1.075);
  // The owned-period chain earns 10%, then 100%; A's intervening 50% loss
  // was never owned. This is separate from dollar P&L and return on allocations.
  near(company.ownedReturn, 1.2);
  near(company.ownedReturnPath.at(-1).value, 220);
  near(company.ownedReturnPath.find(item => item.date === '2012-06-29').value, 110);
  assert.equal(company.ownedReturnPath.find(item => item.date === '2012-06-29').invested, false);
  near(company.mostRecentPeriod.return, 1);
  assert.deepEqual(company.mostRecentPeriod.path.map(point => point.date), dates.slice(4));
  near(company.mostRecentPeriod.benchmark.return, 140 / 125 - 1);
  assert.equal(new Set(run.history.map(item => item.date)).size, run.history.length);
});

test('company deep dives unlock only the latest completed eligible interval, including unheld firms', () => {
  const data = fixture(), start = Engine.create(data);
  const initial = Engine.companyHistory(data, start, 'A');
  assert.equal(initial.mostRecentPeriod, null); assert.equal(initial.ownedReturn, null);
  assert.deepEqual(initial.ownedReturnPath, []);
  const first = Engine.allocate(data, start, {}), unheld = Engine.companyHistory(data, first, 'A');
  assert.equal(unheld.summary, null); assert.equal(unheld.ownedReturn, null);
  assert.equal(unheld.mostRecentPeriod.year, 2010);
  near(unheld.mostRecentPeriod.return, 0.1);
  assert.deepEqual(unheld.mostRecentPeriod.path.map(point => point.value), [100, 120, 110]);
  assert.deepEqual(unheld.mostRecentPeriod.benchmark.path.map(point => point.value), [100, 105, 110]);
  const second = Engine.allocate(data, first, {}), beforeReentry = Engine.companyHistory(data, second, 'A');
  // A is eligible in the unresolved 2012 round but not the completed 2011
  // round. Its deep dive must remain the completed 2010 result, not future +100%.
  assert.equal(beforeReentry.mostRecentPeriod.year, 2010);
  assert.deepEqual(beforeReentry.mostRecentPeriod, unheld.mostRecentPeriod);
  const firstHeld = Engine.allocate(data, second, {A: 0.01}), held = Engine.companyHistory(data, firstHeld, 'A');
  near(held.ownedReturn, 1);
  near(held.ownedReturnPath.find(point => point.date === '2012-06-29').value, 100);
  near(held.summary.profit, 1);
});

test('deep-dive paths preserve observed coverage gaps instead of fabricating company or benchmark returns', () => {
  const data = fixture(); data.assets.find(item => item.id === 'SPY').points.splice(1, 1);
  const first = Engine.allocate(data, Engine.create(data), {});
  const missing = Engine.companyHistory(data, first, 'MISSING').mostRecentPeriod;
  assert.equal(missing.return, null); assert.deepEqual(missing.path, []);
  assert.deepEqual(missing.coverage.missingDates, ['2012-01-03']);
  const available = Engine.companyHistory(data, first, 'A').mostRecentPeriod;
  near(available.return, 0.1);
  assert.equal(available.benchmark.status, 'unavailable');
  assert.equal(available.benchmark.return, null); assert.deepEqual(available.benchmark.path, []);
});

test('adjusted return indices receive no second dividend, raw-close, or split adjustment', () => {
  const data = fixture();
  data.assets[0].points.forEach((row, index) => { row.close = 10000 + index; row.distribution = 200; row.split = 10; });
  data.assets[0].splits = [{date: '2011-06-30', ratio: 10}];
  const run = Engine.allocate(data, Engine.create(data), {A: 1});
  near(run.lastResult.after, 110); near(run.lastResult.path[1].value, 120);
});

test('current decisions expose only the matching year and filed evidence available by cutoff', () => {
  const data = fixture();
  data.assets[0].financials = [{decisionCutoff: '2010-12-31', availableAt: '2010-11-01', fiscalPeriodEnd: '2010-09-30',
    metrics: {revenue: 1000, rd: 90, acquisitions: 500}, metricSources: {
      revenue: {filed: '2010-11-01', fiscalPeriodEnd: '2010-09-30', sourceUrl: 'https://www.sec.gov/old'},
      rd: {filed: '2011-02-01', fiscalPeriodEnd: '2010-12-31'},
      acquisitions: {filed: '2010-11-01', fiscalPeriodEnd: '2011-09-30'}
    }, filings: [
      {filed: '2010-11-01', reportDate: '2010-09-30', form: '10-Q', focusAreas: ['Research'], focusNote: 'Automated topic label', investmentThemes: [{label: 'Research', excerpt: 'An original dated excerpt.'}]},
      {filed: '2011-02-01', form: '10-K', investmentThemes: [{label: 'Future breakthrough'}]}
    ], valuation: {pe: 12, asOf: '2011-01-03'}, status: 'partial'},
    {decisionCutoff: '2011-12-31', availableAt: '2011-11-01', fiscalPeriodEnd: '2011-09-30', metrics: {revenue: 99999}, metricSources: {}, filings: []}];
  const card = Engine.current(data, Engine.create(data)).companies[0];
  assert.equal(card.name, 'Original A'); assert.equal(card.ticker, 'A.OLD');
  assert.equal(card.financials.metrics.revenue, 1000);
  assert.equal(card.financials.metrics.rd, null); assert.equal(card.financials.metrics.acquisitions, null);
  assert.equal(card.financials.filings.length, 1); assert.equal(card.financials.valuation, null);
  assert.deepEqual(card.financials.filings[0].focusAreas, ['Research']);
  assert.equal(card.financials.filings[0].focusNote, 'Automated topic label');
  assert.equal(Object.hasOwn(card, 'points'), false); assert.equal(Object.hasOwn(card, 'return'), false);
});

test('future or undated financial cards are unavailable, not implicitly known', () => {
  const data = fixture(); data.assets[0].financials = [
    {availableAt: '2011-02-01', fiscalPeriodEnd: '2010-12-31', metrics: {revenue: 999}},
    {fiscalPeriodEnd: '2010-09-30', metrics: {revenue: 777}}
  ];
  assert.equal(Engine.current(data, Engine.create(data)).companies[0].financials, null);
});

test('undated modern sectors do not leak into historical decision cards', () => {
  const data = fixture(); data.assets[0].sector = 'Modern classification';
  assert.equal(Engine.current(data, Engine.create(data)).companies[0].sector, null);
  const dated = clone(data); dated.assets[0].sectorAsOf = '2010-01-01';
  assert.equal(Engine.current(dated, Engine.create(dated)).companies[0].sector, 'Modern classification');
  const future = clone(data); future.assets[0].sectorAsOf = '2025-01-01';
  assert.equal(Engine.current(future, Engine.create(future)).companies[0].sector, null);
});

test('all-firm outcome lookup unlocks only completed annual periods and keeps missing coverage explicit', () => {
  const data = fixture(), run = Engine.create(data);
  assert.throws(() => Engine.outcomes(data, run), error => error.code === 'FUTURE_INFORMATION');
  const first = Engine.allocate(data, run, {}), reveal = Engine.outcomes(data, first);
  near(reveal.companies.find(item => item.id === 'A').return, 0.1);
  assert.equal(reveal.companies.find(item => item.id === 'MISSING').return, null);
  assert.throws(() => Engine.outcomes(data, first, 2011), error => error.code === 'FUTURE_INFORMATION');
});

test('all-cash completion remains $100 and records only a same-horizon observed benchmark', () => {
  const data = fixture(); let run = Engine.create(data);
  assert.throws(() => Engine.score(data, run), error => error.code === 'INCOMPLETE');
  for (let i = 0; i < 3; i++) run = Engine.allocate(data, run, {});
  const score = Engine.score(data, run), book = Engine.portfolio(data, run);
  assert.equal(run.status, 'complete'); assert.equal(Engine.current(data, run), null);
  near(score.finalValue, 100); near(score.change, 0); near(score.maxDrawdown, 0);
  near(book.benchmark.value, 140); near(book.benchmark.change, 0.4);
  assert.deepEqual(book.benchmark.path.map(point => point.date), run.history.map(point => point.date));
  assert.throws(() => Engine.allocate(data, run, {}), error => error.code === 'COMPLETE');
  const incomplete = clone(data); incomplete.assets.find(item => item.id === 'SPY').points.splice(1, 1);
  let cash = Engine.create(incomplete); for (let i = 0; i < 3; i++) cash = Engine.allocate(incomplete, cash, {});
  assert.equal(Engine.portfolio(incomplete, cash).benchmark.status, 'unavailable');
  assert.equal(Engine.score(incomplete, cash).benchmarkValue, null);
});

test('source editions ignore retrieval time but change with prices, dates, membership or filed evidence', () => {
  const data = fixture(); data.sources = [{url: 'https://example.test/source', sha256: 'verified-source-hash', retrievedAt: '2026-01-01'}];
  const base = Engine.datasetId(data);
  const stamped = clone(data); stamped.generatedAt = '2099-01-01'; stamped.retrievedAt = '2099-02-01';
  stamped.sources[0].retrievedAt = '2099-01-01';
  assert.equal(Engine.datasetId(stamped), base);
  const variants = [clone(data), clone(data), clone(data), clone(data), clone(data)];
  variants[0].assets[0].points[1].adjustedClose += 0.01;
  variants[1].rounds[0].eligibleAssetIds = ['A', 'MISSING'];
  variants[2].assets[0].financials = [{availableAt: '2010-01-01', fiscalPeriodEnd: '2009-12-31', metrics: {revenue: 1}}];
  variants[3].assets[0].historicalLabels['2010'].name = 'Corrected historical identity';
  variants[4].sources[0].sha256 = 'a-corrected-source-hash';
  for (const variant of variants) assert.notEqual(Engine.datasetId(variant), base);
});

test('save/load and deterministic replay reproduce every lot, exposure, attribution and score', () => {
  const data = fixture(); let run = Engine.create(data);
  for (const weights of [{A: 0.5, B: 0.25}, {B: 1}, {A: 0.5}]) {
    run = Engine.allocate(data, run, weights);
    const wire = Engine.serialize(run);
    assert.deepEqual(Object.keys(JSON.parse(wire)), ['schemaVersion', 'datasetId', 'actions']);
    assert.deepEqual(Engine.restore(data, wire), run);
    assert.deepEqual(Engine.replay(data, run.actions), run);
  }
  assert.deepEqual(Engine.score(data, Engine.restore(data, Engine.serialize(run))), Engine.score(data, run));
});

test('host-verified edition preparation preserves ordinary IDs, replay, and all source validation', () => {
  const data = fixture(), ordinary = Engine.create(data), identical = clone(data);
  const accelerated = Engine.createWithVerifiedEdition(identical, ordinary.datasetId);
  assert.deepEqual(accelerated, ordinary);
  let normal = ordinary, fast = accelerated;
  for (const weights of [{A: 0.5, B: 0.25}, {B: 1}, {A: 0.5}]) {
    normal = Engine.allocate(data, normal, weights); fast = Engine.allocate(identical, fast, weights);
    assert.deepEqual(fast, normal);
    assert.deepEqual(Engine.restore(identical, Engine.serialize(fast)), normal);
  }
  assert.deepEqual(Engine.score(identical, fast), Engine.score(data, normal));
  for (const value of [undefined, null, '', 'annual-v1-incorrect']) {
    assert.throws(() => Engine.createWithVerifiedEdition(clone(data), value), error => error.code === 'INVALID_VERIFIED_EDITION');
  }
  assert.throws(() => Engine.createWithVerifiedEdition(data, 'annual-v1-0000000000000000'), error => error.code === 'INVALID_VERIFIED_EDITION');
  const invalid = clone(data); invalid.assets[0].points[1].adjustedClose = 0;
  assert.throws(() => Engine.createWithVerifiedEdition(invalid, ordinary.datasetId), /positive/);
  const missing = clone(data); missing.assets[0].points.splice(1, 1);
  const blocked = Engine.createWithVerifiedEdition(missing, 'annual-v1-0000000000000000');
  assert.throws(() => Engine.allocate(missing, blocked, {A: 1}), error => error.code === 'COVERAGE_GAP');
});

test('hundreds of fully allocated names retain exact canonical replay despite floating-point weight sums', () => {
  for (const count of [461, 473, 497, 503]) {
    const data = fixture();
    data.assets = Array.from({length: count}, (_, index) => ({id: 'F' + String(index).padStart(4, '0'),
      ticker: 'F' + index, name: 'Firm ' + index, points: dates.map((date, offset) => ({date, adjustedClose: 100 + offset}))}));
    delete data.benchmarkAssetId;
    data.rounds.forEach(round => { round.eligibleAssetIds = data.assets.map(item => item.id); });
    const weights = Object.fromEntries(data.assets.map(item => [item.id, 1 / count]));
    let run = Engine.create(data);
    for (let i = 0; i < data.rounds.length; i++) {
      run = Engine.allocate(data, run, weights);
      assert.deepEqual(Engine.restore(data, Engine.serialize(run)), run);
      assert.ok(run.cash >= 0);
      near(run.lastResult.companies.reduce((sum, item) => sum + item.invested, 0) + run.cash, run.lastResult.before, 1e-8);
    }
  }
});

test('tampered balances, action order, edition, weight totals and injected save fields are rejected', () => {
  const data = fixture(), run = Engine.allocate(data, Engine.create(data), {A: 1});
  const altered = clone(run); altered.cash = 1e9;
  assert.throws(() => Engine.portfolio(data, altered), error => error.code === 'INVALID_SAVE');
  assert.throws(() => Engine.serialize(altered), error => error.code === 'INVALID_SAVE');
  const saved = JSON.parse(Engine.serialize(run));
  for (const change of [value => { value.cash = 1e9; }, value => { value.actions[0].year = 2011; },
    value => { value.actions[0].weights = {A: 1, B: 1}; }, value => { value.datasetId += '-other'; }]) {
    const bad = clone(saved); change(bad); assert.throws(() => Engine.restore(data, JSON.stringify(bad)));
  }
});

test('duplicate or impossible dates, unsupported prices and discontinuous annual calendars fail validation', () => {
  const variants = [fixture(), fixture(), fixture(), fixture(), fixture(), fixture()];
  variants[0].assets[0].points[0].date = '2011-02-30';
  variants[1].assets[0].points[1].date = variants[1].assets[0].points[0].date;
  variants[2].assets[0].points[0].adjustedClose = 0;
  variants[3].rounds[1].executionDate = '2012-02-01';
  variants[4].rounds[0].cutoff = '2010-06-30';
  variants[5].rounds[0].eligibleAssetIds.push('A');
  for (const data of variants) assert.throws(() => Engine.create(data));
});

test('the dependency-free global build works without Node APIs, like browser and JavaScriptCore', () => {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(require.resolve('../assets/annual-portfolio-engine.js'), 'utf8'), context);
  context.payload = JSON.stringify(fixture());
  const result = vm.runInContext('const data = JSON.parse(payload); let run = AnnualPortfolio.create(data); run = AnnualPortfolio.allocate(data,run,{A:0.5,B:0.25}); JSON.stringify(AnnualPortfolio.portfolio(data,run));', context);
  near(JSON.parse(result).value, 102.5);
});
