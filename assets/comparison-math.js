/* Shared, dependency-free comparison calculations. Prices are already split
 * adjusted by the publisher. Adjusted close is deliberately never used here. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HetzerkComparisonMath = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const DAY = 86400000;
  const PERIODS = ['1M', '3M', '6M', 'YTD', '1Y', '3Y', '5Y', '10Y', '12Y', '15Y', '18Y', '20Y', 'ALL', 'CUSTOM'];
  const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
  const validDate = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(value + 'T00:00:00Z'))
    && new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;

  function cutoffDate(end, period) {
    if (!validDate(end)) throw new Error('A valid closing date is required.');
    const date = new Date(end + 'T00:00:00Z');
    if (period === 'ALL') return null;
    if (period === 'YTD') return String(date.getUTCFullYear()) + '-01-01';
    const months = {'1M': 1, '3M': 3, '6M': 6, '1Y': 12, '3Y': 36, '5Y': 60, '10Y': 120,
      '12Y': 144, '15Y': 180, '18Y': 216, '20Y': 240}[period];
    if (!months) throw new Error('Unsupported comparison period.');
    const day = date.getUTCDate();
    date.setUTCDate(1);
    date.setUTCMonth(date.getUTCMonth() - months);
    const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
    date.setUTCDate(Math.min(day, lastDay));
    return date.toISOString().slice(0, 10);
  }

  function customRange(start, end) {
    if (!validDate(start) || !validDate(end)) throw new Error('Choose valid start and end dates.');
    if (start > end) throw new Error('The start date must be on or before the end date.');
    return {start, end};
  }

  function buildWealth(series, basis, mode) {
    const field = series.id === 'REDI' && basis === 'nav' ? 'nav' : 'market_price';
    const warnings = [];
    const byDate = new Map();
    let unusableDistribution = false;
    for (const row of Array.isArray(series.observations) ? series.observations : []) {
      if (!row || !validDate(row.date)) continue;
      const dividend = row.distribution === undefined || row.distribution === null ? 0 : row.distribution;
      if (mode === 'reinvested' && (typeof dividend !== 'number' || !Number.isFinite(dividend) || dividend < 0)) {
        unusableDistribution = true;
      }
      if (!positive(row[field])) {
        if (mode === 'reinvested' && dividend > 0) unusableDistribution = true;
        warnings.push('A date without a valid ' + (field === 'nav' ? 'NAV' : 'market price') + ' was omitted.');
        continue;
      }
      if (byDate.has(row.date)) throw new Error(series.id + ' has duplicate observation dates.');
      byDate.set(row.date, {date: row.date, price: row[field], distribution: dividend});
    }
    if (unusableDistribution) {
      return {id: series.id, points: [], warnings: ['Reinvested performance is unavailable because a distribution or its ex-date price is missing.']};
    }
    const rows = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
    let wealth = 1;
    const points = rows.map((row, index) => {
      if (index) {
        // Apply each ex-date distribution before matching calendars. Reinvesting
        // at the closing price gives exactly (P_t + D_t) / P_(t-1).
        const dividend = mode === 'reinvested' ? row.distribution : 0;
        wealth *= (row.price + dividend) / rows[index - 1].price;
      }
      return {date: row.date, price: row.price, wealth: wealth};
    });
    return {id: series.id, points: points, warnings: Array.from(new Set(warnings))};
  }

  function sampleVariance(values) {
    if (values.length < 2) return null;
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    return values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1);
  }

  function correlation(left, right) {
    if (left.length !== right.length || left.length < 20) return null;
    const leftMean = left.reduce((sum, value) => sum + value, 0) / left.length;
    const rightMean = right.reduce((sum, value) => sum + value, 0) / right.length;
    let numerator = 0, leftSquares = 0, rightSquares = 0;
    for (let i = 0; i < left.length; i += 1) {
      const l = left[i] - leftMean, r = right[i] - rightMean;
      numerator += l * r;
      leftSquares += l * l;
      rightSquares += r * r;
    }
    if (leftSquares < 1e-24 || rightSquares < 1e-24) return null;
    return Math.max(-1, Math.min(1, numerator / Math.sqrt(leftSquares * rightSquares)));
  }

  function compare(options) {
    const mode = options.mode === 'reinvested' ? 'reinvested' : 'price';
    const basis = options.basis === 'nav' ? 'nav' : 'market_price';
    const period = PERIODS.includes(options.period) ? options.period : '1Y';
    const custom = period === 'CUSTOM' ? customRange(options.startDate, options.endDate) : null;
    const requested = Array.isArray(options.series) ? options.series : [];
    const excluded = [], warnings = [];
    const prepared = [];
    for (const series of requested) {
      if (!series || typeof series.id !== 'string') continue;
      const result = buildWealth(series, basis, mode);
      warnings.push(...result.warnings.map(message => series.id + ': ' + message));
      if (!result.points.length) {
        excluded.push({id: series.id, reason: series.error || 'No usable observations for this selection.'});
      } else prepared.push({source: series, points: result.points, index: new Map(result.points.map(point => [point.date, point]))});
    }
    const redi = prepared.find(item => item.source.id === 'REDI');
    const empty = {series: [], dates: [], excluded: excluded, warnings: warnings, start: null, end: null,
      mode: mode, basis: basis, period: period, riskAvailable: false, riskReason: null,
      availableStart: null, availableEnd: null, requestedStart: custom && custom.start, requestedEnd: custom && custom.end,
      coverageNote: null};
    if (!redi) return {...empty, reason: 'REDI history is not available for this selection.'};
    // No forward fills: every value in a displayed comparison uses the same date.
    let dates = redi.points.map(point => point.date).filter(date => prepared.every(item => item.index.has(date)));
    if (!dates.length) return {...empty, reason: 'The selected funds do not yet share a closing date.'};
    const availableStart = dates[0], availableEnd = dates[dates.length - 1];
    const cutoff = custom ? custom.start : cutoffDate(availableEnd, period);
    const requestedEnd = custom ? custom.end : availableEnd;
    const coverage = {availableStart, availableEnd, requestedStart: cutoff, requestedEnd};
    // YTD includes the move on the first session of the year, measured from
    // the final shared close of the prior year when that close is available.
    const yearBase = period === 'YTD' ? dates.filter(date => date < cutoff).pop() : null;
    dates = dates.filter(date => (!cutoff || date >= cutoff || date === yearBase) && date <= requestedEnd);
    if (!dates.length) return {...empty, ...coverage, reason: 'No shared observations fall within the selected date range.'};
    const start = dates[0], end = dates[dates.length - 1];
    const coverageNote = custom ? 'Custom range uses only shared observed closes; actual dates are shown.'
      : period !== 'YTD' && cutoff && availableStart > cutoff ? 'The selected funds have less than ' + period.replace('Y', ' year').replace('M', ' month') + (period === '1Y' || period === '1M' ? '' : 's') + ' of shared history. Showing the available period.' : null;
    // Peer calendars establish the observed exchange sessions. An extra REDI
    // workbook holiday is not an exchange session. Missing peer sessions suppress
    // annualized daily risk, rather than treating multiday changes as daily ones.
    const peers = prepared.filter(item => item.source.id !== 'REDI');
    const calendars = peers.length ? peers : prepared;
    const calendar = new Set(calendars.flatMap(item => item.points.map(point => point.date)).filter(date => date >= start && date <= end));
    const hasMissingSession = calendar.size > dates.length;
    const hasLongGap = dates.some((date, index) => index > 0 && (Date.parse(date) - Date.parse(dates[index - 1])) / DAY > 5);
    const riskAvailable = dates.length >= 21 && !hasMissingSession && !hasLongGap;
    const riskReason = dates.length < 21 ? 'At least 20 matched daily returns are needed for volatility and correlation.'
      : (hasMissingSession || hasLongGap) ? 'Volatility and correlation are withheld because the matched daily history has gaps.' : null;
    const compared = prepared.map(item => {
      const base = item.index.get(start).wealth;
      const points = dates.map(date => ({date: date, value: item.index.get(date).wealth / base * 100}));
      const returns = points.slice(1).map((point, index) => point.value / points[index].value - 1);
      let peak = 100, drawdown = 0;
      for (const point of points) {
        peak = Math.max(peak, point.value);
        drawdown = Math.min(drawdown, point.value / peak - 1);
      }
      const variance = sampleVariance(returns);
      return {id: item.source.id, name: item.source.name, isIllustrative: item.source.is_illustrative === true,
        points: points, returns: returns, metrics: {
          change: points.length > 1 ? points[points.length - 1].value / 100 - 1 : null,
          drawdown: points.length > 1 ? drawdown : null,
          volatility: riskAvailable && variance !== null ? Math.sqrt(variance * 252) : null,
          correlation: null
        }};
    });
    const rediReturns = compared.find(item => item.id === 'REDI').returns;
    if (riskAvailable) compared.forEach(item => { item.metrics.correlation = correlation(item.returns, rediReturns); });
    return {series: compared, dates: dates, start: start, end: end, excluded: excluded, warnings: warnings,
      mode: mode, basis: basis, period: period, riskAvailable: riskAvailable, riskReason: riskReason,
      ...coverage, coverageNote,
      reason: dates.length < 2 ? 'Only one shared closing date is available; performance needs at least two.' : null};
  }
  return {buildWealth: buildWealth, compare: compare, cutoffDate: cutoffDate, correlation: correlation, validDate: validDate,
    customRange: customRange, periods: PERIODS};
}));
