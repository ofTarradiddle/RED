'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const math = require('../assets/comparison-math.js');

function series(id, rows) {
  return {id, name: id, currency: 'USD', status: 'ok', observations: rows.map(([date, market_price, distribution = 0, nav = market_price]) => ({date, market_price, distribution, nav}))};
}
function nearly(actual, expected) { assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} should equal ${expected}`); }
function dates(count) {
  const result = [], date = new Date('2025-01-02T00:00:00Z');
  while (result.length < count) {
    if (date.getUTCDay() > 0 && date.getUTCDay() < 6) result.push(date.toISOString().slice(0, 10));
    date.setUTCDate(date.getUTCDate() + 1);
  }
  return result;
}

test('a cash distribution offsets the ex-date price decline only in reinvested mode', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', 98, 2], ['2025-01-06', 101]]);
  const price = math.compare({series: [fund], mode: 'price', period: 'ALL'});
  const reinvested = math.compare({series: [fund], mode: 'reinvested', period: 'ALL'});
  nearly(price.series[0].points[1].value, 98);
  nearly(reinvested.series[0].points[1].value, 100);
  nearly(reinvested.series[0].metrics.change, 101 / 98 - 1);
});

test('distribution reinvestment precedes matching calendars and retains missing common ex-dates', () => {
  const redi = series('REDI', [['2025-01-02', 100], ['2025-01-03', 98, 2], ['2025-01-06', 100]]);
  const peer = series('SPY', [['2025-01-02', 50], ['2025-01-06', 51]]);
  const result = math.compare({series: [redi, peer], mode: 'reinvested', period: 'ALL'});
  assert.deepEqual(result.dates, ['2025-01-02', '2025-01-06']);
  nearly(result.series[0].points[1].value, 10000 / 98);
  nearly(result.series[1].points[1].value, 102);
});

test('adjusted close and splits are never applied on top of already split-adjusted prices', () => {
  const fund = series('REDI', [['2025-01-02', 50], ['2025-01-03', 51, 1]]);
  fund.observations[0].adjusted_close = 48;
  fund.observations[1].adjusted_close = 51;
  fund.observations[1].split = 2;
  nearly(math.buildWealth(fund, 'market_price', 'price').points[1].wealth, 1.02);
  nearly(math.buildWealth(fund, 'market_price', 'reinvested').points[1].wealth, 1.04);
});

test('REDI NAV is selectable while peers always use market price', () => {
  const redi = series('REDI', [['2025-01-02', 100, 0, 99], ['2025-01-03', 103, 0, 101]]);
  const spy = series('SPY', [['2025-01-02', 50, 0, 49], ['2025-01-03', 51, 0, 52]]);
  const result = math.compare({series: [redi, spy], basis: 'nav', period: 'ALL'});
  nearly(result.series[0].metrics.change, 101 / 99 - 1);
  nearly(result.series[1].metrics.change, 0.02);
});

test('every series shares the same horizon and starts at 100 without forward filling', () => {
  const redi = series('REDI', [['2025-01-02', 99], ['2025-01-03', 100], ['2025-01-06', 101], ['2025-01-07', 102]]);
  const spy = series('SPY', [['2025-01-03', 50], ['2025-01-06', 55], ['2025-01-08', 57]]);
  const result = math.compare({series: [redi, spy], period: 'ALL'});
  assert.deepEqual(result.dates, ['2025-01-03', '2025-01-06']);
  assert.equal(result.start, '2025-01-03');
  assert.equal(result.end, '2025-01-06');
  result.series.forEach(fund => nearly(fund.points[0].value, 100));
  nearly(result.series[1].metrics.change, 0.1);
});

test('period filtering is anchored to the common closing date, not today or a newer peer', () => {
  const redi = series('REDI', [['2025-01-02', 90], ['2025-02-03', 100], ['2025-02-28', 110]]);
  const spy = series('SPY', [['2025-01-02', 50], ['2025-02-03', 60], ['2025-02-28', 63], ['2026-02-27', 70]]);
  const result = math.compare({series: [redi, spy], period: '1M'});
  assert.equal(result.end, '2025-02-28');
  assert.equal(result.start, '2025-02-03');
  nearly(result.series[0].metrics.change, 0.1);
});

test('month cutoffs clamp correctly across month ends and leap years', () => {
  assert.equal(math.cutoffDate('2025-03-31', '1M'), '2025-02-28');
  assert.equal(math.cutoffDate('2024-03-31', '1M'), '2024-02-29');
  assert.equal(math.cutoffDate('2024-02-29', '1Y'), '2023-02-28');
  assert.equal(math.cutoffDate('2025-03-31', 'YTD'), '2025-01-01');
});

test('YTD includes the first session return by using the previous year final shared close', () => {
  const fund = series('REDI', [['2024-12-30', 99], ['2024-12-31', 100], ['2025-01-02', 102], ['2025-01-03', 105]]);
  const result = math.compare({series: [fund], period: 'YTD'});
  assert.equal(result.start, '2024-12-31');
  nearly(result.series[0].metrics.change, 0.05);
});

test('drawdown measures the worst decline from a prior observed peak', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', 120], ['2025-01-06', 90], ['2025-01-07', 110]]);
  const result = math.compare({series: [fund], period: 'ALL'});
  nearly(result.series[0].metrics.drawdown, -0.25);
  assert.equal(result.series[0].metrics.volatility, null);
});

test('volatility uses sample daily-return dispersion and correlation has a 20-return minimum', () => {
  const calendar = dates(24);
  let price = 100;
  const rows = calendar.map((date, i) => [date, (price *= i % 2 ? 1.01 : 0.995)]);
  const result = math.compare({series: [series('REDI', rows), series('SPY', rows)], period: 'ALL'});
  assert.equal(result.riskAvailable, true);
  assert.ok(result.series[0].metrics.volatility > 0);
  nearly(result.series[1].metrics.correlation, 1);
  assert.equal(math.correlation([1, 2], [1, 2]), null);
});

test('constant return series has zero volatility and undefined correlation', () => {
  const rows = dates(24).map(date => [date, 100]);
  const result = math.compare({series: [series('REDI', rows), series('SPY', rows)], period: 'ALL'});
  nearly(result.series[0].metrics.volatility, 0);
  assert.equal(result.series[0].metrics.correlation, null);
  assert.equal(result.series[1].metrics.correlation, null);
});

test('missing observed peer sessions suppress daily risk rather than annualizing multiday returns', () => {
  const rows = dates(25).map((date, i) => [date, 100 + i]);
  const rediRows = rows.filter((_, i) => i !== 12);
  const result = math.compare({series: [series('REDI', rediRows), series('SPY', rows)], period: 'ALL'});
  assert.equal(result.riskAvailable, false);
  assert.match(result.riskReason, /gaps/);
  assert.equal(result.series[0].metrics.volatility, null);
  nearly(result.series[0].metrics.change, 0.24);
});

test('a workbook-only weekend does not falsely flag missing exchange sessions', () => {
  const rows = dates(24).map((date, i) => [date, 100 + i]);
  const rediRows = [...rows, ['2025-01-04', 101]];
  const result = math.compare({series: [series('REDI', rediRows), series('SPY', rows)], period: 'ALL'});
  assert.equal(result.riskAvailable, true);
});

test('no fabricated REDI history is produced when only peers are available', () => {
  const result = math.compare({series: [series('REDI', []), series('SPY', [['2025-01-02', 100], ['2025-01-03', 102]])], period: 'ALL'});
  assert.equal(result.series.length, 0);
  assert.match(result.reason, /REDI history is not available/);
});

test('a distribution with no usable ex-date price cannot silently become a reinvested result', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', null, 2], ['2025-01-06', 101]]);
  const result = math.compare({series: [fund], mode: 'reinvested', period: 'ALL'});
  assert.equal(result.series.length, 0);
  assert.match(result.warnings[0], /ex-date price is missing/);
});

test('duplicate dates are rejected instead of silently choosing one price', () => {
  assert.throws(() => math.buildWealth(series('REDI', [['2025-01-02', 100], ['2025-01-02', 101]]), 'market_price', 'price'), /duplicate/);
  assert.equal(math.validDate('2025-02-30'), false);
});

test('long-year presets use calendar horizons anchored to the last shared close', () => {
  const rows = Array.from({length: 26}, (_, i) => [`${2000 + i}-08-31`, 100 + i]);
  const peerRows = [...rows, ['2026-08-31', 127]];
  for (const years of [3, 5, 10, 12, 15, 18, 20]) {
    const result = math.compare({series: [series('REDI', rows), series('SPY', peerRows)], period: years + 'Y'});
    assert.equal(result.start, `${2025 - years}-08-31`);
    assert.equal(result.end, '2025-08-31');
    assert.equal(result.coverageNote, null);
    nearly(result.series[0].metrics.change, 125 / (125 - years) - 1);
  }
  assert.equal(math.cutoffDate('2024-02-29', '3Y'), '2021-02-28');
  assert.equal(math.cutoffDate('2024-02-29', '20Y'), '2004-02-29');
});

test('a requested long horizon explicitly discloses shorter shared history', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', 110]]);
  const result = math.compare({series: [fund], period: '20Y'});
  assert.equal(result.start, '2025-01-02');
  assert.equal(result.requestedStart, '2005-01-03');
  assert.match(result.coverageNote, /less than 20 years/);
  nearly(result.series[0].metrics.change, .1);
});

test('custom ranges use actual common sessions inside inclusive bounds and rebase there', () => {
  const redi = series('REDI', [['2025-01-02', 100], ['2025-01-03', 110], ['2025-01-06', 121], ['2025-01-07', 130]]);
  const spy = series('SPY', [['2025-01-02', 50], ['2025-01-06', 55], ['2025-01-07', 60]]);
  const result = math.compare({series: [redi, spy], period: 'CUSTOM', startDate: '2025-01-04', endDate: '2025-01-08'});
  assert.deepEqual(result.dates, ['2025-01-06', '2025-01-07']);
  assert.equal(result.availableStart, '2025-01-02');
  assert.equal(result.availableEnd, '2025-01-07');
  assert.equal(result.requestedStart, '2025-01-04');
  assert.equal(result.requestedEnd, '2025-01-08');
  nearly(result.series[0].points[0].value, 100);
  nearly(result.series[0].metrics.change, 130 / 121 - 1);
  assert.match(result.coverageNote, /only shared observed closes/);
});

test('custom bounds can contain the whole record without fabricating endpoints', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', 110]]);
  const result = math.compare({series: [fund], period: 'CUSTOM', startDate: '2000-01-01', endDate: '2030-01-01'});
  assert.equal(result.start, '2025-01-02');
  assert.equal(result.end, '2025-01-03');
  nearly(result.series[0].metrics.change, .1);
});

test('custom dates reject invalid calendars and reversed ranges, while empty windows show no metrics', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', 110]]);
  for (const [startDate, endDate] of [['2025-02-30', '2025-03-01'], ['', '2025-01-03'], ['2025-01-03', '2025-01-02'], ['01/02/2025', '2025-01-03']]) {
    assert.throws(() => math.compare({series: [fund], period: 'CUSTOM', startDate, endDate}), /date/);
  }
  const result = math.compare({series: [fund], period: 'CUSTOM', startDate: '2025-01-04', endDate: '2025-01-05'});
  assert.deepEqual(result.dates, []);
  assert.deepEqual(result.series, []);
  assert.match(result.reason, /No shared observations/);
  assert.equal(result.availableEnd, '2025-01-03');
});

test('distributions within a custom range are included exactly once after rebasing', () => {
  const fund = series('REDI', [['2025-01-02', 100], ['2025-01-03', 110], ['2025-01-06', 108, 2], ['2025-01-07', 110]]);
  const result = math.compare({series: [fund], mode: 'reinvested', period: 'CUSTOM', startDate: '2025-01-03', endDate: '2025-01-07'});
  assert.equal(result.start, '2025-01-03');
  nearly(result.series[0].points[1].value, 100);
  nearly(result.series[0].metrics.change, 110 / 108 - 1);
});
