/* Monthly source-level research comparisons. Never a NAV or live ETF series. */
(function (root, factory) {
  'use strict';
  const dependency = typeof module === 'object' && module.exports
    ? require('./comparison-math.js') : root.HetzerkComparisonMath;
  const api = factory(dependency);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HetzerkResearchMath = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (marketMath) {
  'use strict';
  const DAY = 86400000;
  const RESEARCH_IDS = ['INNOVATION_LEADER', 'LAGGARD', 'MARKET_BACKTEST', 'MARKET_EQUAL_WEIGHT', 'NON_RD'];
  const ETF_IDS = ['SPY', 'VOO', 'QQQ', 'ITAN', 'SYLD'];
  const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
  const stamp = date => Date.parse(date + 'T00:00:00Z');

  function monthEnd(date) {
    if (!marketMath.validDate(date)) throw new Error('Invalid observation date.');
    const time = new Date(stamp(date));
    return new Date(Date.UTC(time.getUTCFullYear(), time.getUTCMonth() + 1, 0)).toISOString().slice(0, 10);
  }

  function cutoffDate(end, period) {
    if (!marketMath.validDate(end)) throw new Error('Invalid closing month.');
    if (period === 'ALL') return null;
    const months = {'1Y': 12, '5Y': 60, '10Y': 120}[period];
    if (!months) throw new Error('Unsupported research period.');
    const time = new Date(stamp(end)), day = time.getUTCDate();
    time.setUTCDate(1);
    time.setUTCMonth(time.getUTCMonth() - months);
    const last = new Date(Date.UTC(time.getUTCFullYear(), time.getUTCMonth() + 1, 0)).getUTCDate();
    time.setUTCDate(Math.min(day, last));
    return time.toISOString().slice(0, 10);
  }

  function researchSeries(payload) {
    if (!payload || payload.schema_version !== 1 || payload.frequency !== 'monthly' || !Array.isArray(payload.series)) {
      throw new Error('A supported monthly research dataset is required.');
    }
    const seen = new Set();
    const output = payload.series.map(series => {
      if (!RESEARCH_IDS.includes(series.id) || seen.has(series.id)) throw new Error('Unknown or repeated research series.');
      seen.add(series.id);
      let previous = '';
      if (!Array.isArray(series.observations) || !series.observations.length) throw new Error('Research history is empty.');
      const points = series.observations.map(row => {
        if (!row || !marketMath.validDate(row.date) || monthEnd(row.date) !== row.date || row.date <= previous || !positive(row.level)) {
          throw new Error('Research observations must be positive, unique and ordered calendar-month-end levels.');
        }
        previous = row.date;
        return {date: row.date, observedDate: row.date, wealth: row.level};
      });
      return {id: series.id, name: series.name, kind: 'research', points};
    });
    return output;
  }

  function monthlyETF(series, completedThrough = new Date().toISOString().slice(0, 10)) {
    if (!marketMath.validDate(completedThrough)) throw new Error('Invalid ETF snapshot publication date.');
    if (!ETF_IDS.includes(series.id) || series.currency !== 'USD' || series.kind !== 'etf' || series.is_illustrative !== false) {
      throw new Error('Research peers must be actual USD ETF observations.');
    }
    let previous = '';
    for (const row of series.observations || []) {
      if (!row || !marketMath.validDate(row.date) || row.date <= previous || !positive(row.market_price)
          || typeof row.distribution !== 'number' || !Number.isFinite(row.distribution) || row.distribution < 0) {
        throw new Error(series.id + ' has invalid or unordered market observations.');
      }
      previous = row.date;
    }
    // Apply every supplied ex-date distribution before selecting monthly marks.
    // Yahoo Close is already split-adjusted; Adj Close and split ratios are not
    // applied again. No distributions are added to the source research levels.
    const wealth = marketMath.buildWealth(series, 'market_price', 'reinvested');
    const lastInMonth = new Map();
    for (const point of wealth.points) {
      if (!positive(point.wealth)) throw new Error('ETF wealth is not finite and positive.');
      lastInMonth.set(monthEnd(point.date), point);
    }
    const points = [];
    for (const [date, point] of lastInMonth) {
      const distance = (stamp(date) - stamp(point.date)) / DAY;
      if (date <= completedThrough && distance <= 4) points.push({date, observedDate: point.date, wealth: point.wealth});
    }
    return {id: series.id, name: series.id, kind: 'etf', points, warnings: wealth.warnings};
  }

  function compare(research, market, options = {}) {
    if (!marketMath) throw new Error('Comparison calculations are unavailable.');
    const period = options.period || 'ALL';
    if (!['ALL', '1Y', '5Y', '10Y'].includes(period)) throw new Error('Unsupported research period.');
    const ids = options.ids || ['INNOVATION_LEADER', 'LAGGARD', 'MARKET_BACKTEST'];
    if (!Array.isArray(ids) || new Set(ids).size !== ids.length || ids.some(id => ![...RESEARCH_IDS, ...ETF_IDS].includes(id))) {
      throw new Error('Unknown or repeated comparison selection.');
    }
    const requested = ids.includes('INNOVATION_LEADER') ? ids : ['INNOVATION_LEADER', ...ids];
    const sources = researchSeries(research), warnings = [], excluded = [], prepared = [];
    const peers = market && Array.isArray(market.series) ? market.series : [];
    const publishedDay = market && typeof market.generated_at === 'string' ? market.generated_at.slice(0, 10) : '';
    const completedThrough = marketMath.validDate(publishedDay) ? publishedDay : new Date().toISOString().slice(0, 10);
    for (const id of requested) {
      let series;
      if (RESEARCH_IDS.includes(id)) series = sources.find(item => item.id === id);
      else {
        const peer = peers.find(item => item.id === id);
        if (peer && peer.status !== 'unavailable') {
          series = monthlyETF(peer, completedThrough);
          if (peer.status === 'stale') warnings.push(id + ': latest refresh failed; retained observations are shown.');
          warnings.push(...series.warnings.map(message => id + ': ' + message));
        }
      }
      if (!series || !series.points.length) excluded.push({id, reason: 'No usable month-end observations are available.'});
      else prepared.push({...series, index: new Map(series.points.map(point => [point.date, point]))});
    }
    const empty = {series: [], dates: [], start: null, end: null, period, warnings, excluded, reason: null};
    const reference = prepared.find(series => series.id === 'INNOVATION_LEADER');
    if (!reference) return {...empty, reason: 'Innovation Leader research is unavailable.'};
    let dates = reference.points.map(point => point.date).filter(date => prepared.every(series => series.index.has(date)));
    if (!dates.length) return {...empty, reason: 'The selected series do not share an observed closing month.'};
    const cutoff = cutoffDate(dates[dates.length - 1], period);
    dates = dates.filter(date => !cutoff || date >= cutoff);
    const start = dates[0], end = dates[dates.length - 1];
    const expected = (Number(end.slice(0, 4)) - Number(start.slice(0, 4))) * 12 + Number(end.slice(5, 7)) - Number(start.slice(5, 7)) + 1;
    if (expected !== dates.length) warnings.push('Some closing months are missing. No values are filled; month-end drawdown uses only matched observations.');
    if (prepared.some(series => series.kind === 'etf')) {
      warnings.push('ETF comparisons use the last observed session within four days of each calendar month-end, with cash distributions reinvested. Source backtest fees and distribution conventions are not verified.');
    }
    const years = (stamp(end) - stamp(start)) / DAY / 365.25;
    const output = prepared.map(series => {
      const base = series.index.get(start).wealth;
      const points = dates.map(date => {
        const mark = series.index.get(date);
        return {date, observedDate: mark.observedDate, value: mark.wealth / base * 100};
      });
      let peak = 100, drawdown = 0;
      for (const point of points) { peak = Math.max(peak, point.value); drawdown = Math.min(drawdown, point.value / peak - 1); }
      const ratio = points[points.length - 1].value / 100;
      return {id: series.id, name: series.name, kind: series.kind, points, metrics: {
        change: points.length > 1 ? ratio - 1 : null,
        cagr: years > 0 && start <= cutoffDate(end, '1Y') ? Math.pow(ratio, 1 / years) - 1 : null,
        drawdown: points.length > 1 ? drawdown : null
      }};
    });
    return {...empty, series: output, dates, start, end, reason: dates.length < 2 ? 'At least two shared months are needed to calculate returns.' : null};
  }
  return {compare, monthlyETF, monthEnd, cutoffDate, researchSeries};
}));
