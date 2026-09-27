/* Annual, point-in-time portfolio exercise. Browser, Node and JavaScriptCore.
 * Adjusted-close units include the provider's split/dividend adjustments. They
 * are economic return units, not executable brokerage shares. No extra cash
 * dividend or split factor is applied. Every displayed mark must be observed.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AnnualPortfolio = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const VERSION = 1, CAPITAL = 100, EPSILON = 1e-10, DAY = 86400000;
  const cache = new WeakMap(), trustedRuns = new WeakSet();
  const prohibited = new Set([...Object.getOwnPropertyNames(Object.prototype), 'prototype']);
  const METRICS = ['revenue', 'netIncome', 'operatingCashFlow', 'capex', 'rd', 'acquisitions', 'assets', 'equity', 'epsDiluted'];
  const DISCLOSURE = 'Historical annual portfolio exercise using point-in-time constituent lists and dated filings. Membership eligibility does not guarantee complete return coverage; unsupported positions are explicitly blocked, never assigned invented returns. This coverage constraint can introduce selection bias. Provider-adjusted return units include its dividend and split adjustments. Cash earns 0%; fees, taxes, spreads and inflation are excluded. Replays verify accounting, not whether a player knew future outcomes.';

  function fail(message, code, details) {
    const error = new Error(message);
    error.code = code || 'INVALID_DATA';
    if (details) error.details = details;
    throw error;
  }
  function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
  function number(value) { return typeof value === 'number' && Number.isFinite(value); }
  function id(value) { return typeof value === 'string' && value.length > 0 && value.length <= 160 && !prohibited.has(value); }
  function date(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const time = Date.parse(value + 'T00:00:00Z');
    return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value;
  }
  function copy(value) { return value === undefined ? null : JSON.parse(JSON.stringify(value)); }
  function freeze(value) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      Object.keys(value).forEach(key => freeze(value[key]));
      Object.freeze(value);
    }
    return value;
  }
  function seal(run) { freeze(run); trustedRuns.add(run); return run; }
  function provenance(value) {
    if (Array.isArray(value)) return value.map(provenance);
    if (!object(value)) return value;
    const result = {};
    Object.keys(value).filter(key => !['retrievedAt', 'generatedAt', 'fetchedAt', 'lastAttemptAt'].includes(key)).forEach(key => { result[key] = provenance(value[key]); });
    return result;
  }
  function fingerprint(value) {
    // Two streaming 32-bit fingerprints identify an economic edition. This is
    // not a cryptographic signature or a claim of anti-cheat protection.
    let a = 2166136261, b = 2246822507;
    function write(text) {
      for (let i = 0; i < text.length; i++) {
        a = Math.imul(a ^ text.charCodeAt(i), 16777619);
        b = Math.imul(b ^ text.charCodeAt(i), 3266489909);
      }
    }
    function walk(item) {
      if (Array.isArray(item)) { write('['); item.forEach(child => { walk(child); write(','); }); write(']'); }
      else if (object(item)) {
        write('{'); Object.keys(item).sort().forEach(key => { write(JSON.stringify(key)); write(':'); walk(item[key]); write(','); }); write('}');
      } else write(JSON.stringify(item === undefined ? null : item));
    }
    walk(value);
    return (a >>> 0).toString(16).padStart(8, '0') + (b >>> 0).toString(16).padStart(8, '0');
  }

  function prepare(data, verifiedDatasetId) {
    if (!object(data)) fail('The annual portfolio dataset is unavailable.');
    if (verifiedDatasetId !== undefined && (typeof verifiedDatasetId !== 'string' || !/^annual-v1-[a-f0-9]{16}$/.test(verifiedDatasetId))) fail('Invalid verified annual edition identifier.', 'INVALID_VERIFIED_EDITION');
    if (cache.has(data)) {
      const prepared = cache.get(data);
      if (verifiedDatasetId !== undefined && verifiedDatasetId !== prepared.datasetId) fail('The verified edition conflicts with the prepared source.', 'INVALID_VERIFIED_EDITION');
      return prepared;
    }
    if ((data.schema_version ?? data.schemaVersion) !== 1 || !date(data.asOf) || !Array.isArray(data.assets) || !Array.isArray(data.rounds) || !data.rounds.length) fail('A supported dated annual portfolio dataset is required.');
    if (data.rounds.length > 100 || data.assets.length > 5000) fail('This dataset exceeds the supported annual exercise size.');
    const assets = new Map();
    data.assets.forEach(raw => {
      if (!object(raw) || !id(raw.id) || assets.has(raw.id) || !Array.isArray(raw.points) || (raw.currency && raw.currency !== 'USD')) fail('Each security needs a unique stable identifier and USD return history.');
      const excludedObservations = copy(raw.excludedObservations || []), qualityFlags = copy(raw.qualityFlags || []);
      if (!Array.isArray(excludedObservations) || !Array.isArray(qualityFlags)) fail(raw.id + ': quality-review metadata must be arrays.');
      const excludedDates = new Set();
      excludedObservations.forEach(row => {
        if (!object(row) || !date(row.date) || row.date > data.asOf || excludedDates.has(row.date)) fail(raw.id + ': excluded observations require unique valid dates.');
        excludedDates.add(row.date);
      });
      let previous = '';
      const points = raw.points.map(row => {
        if (!object(row) || !date(row.date) || row.date <= previous || row.date > data.asOf || !number(row.adjustedClose) || row.adjustedClose <= 0) fail(raw.id + ': return indices must be positive, ordered and observed. Missing terminal payoffs cannot be inferred.');
        if (row.close != null && (!number(row.close) || row.close <= 0)) fail(raw.id + ': invalid closing price.');
        previous = row.date;
        return {date: row.date, adjustedClose: row.adjustedClose, close: row.close ?? null};
      });
      const asset = {
        id: raw.id, name: String(raw.name || raw.ticker || raw.id), ticker: raw.ticker == null ? null : String(raw.ticker),
        cik: raw.cik == null ? null : String(raw.cik), sector: raw.sector == null ? null : String(raw.sector), sectorAsOf: raw.sectorAsOf || null,
        priceStatus: raw.priceStatus || null, priceReason: raw.priceReason || null,
        membership: copy(raw.membership || []), financials: copy(raw.financials || []),
        identityHistory: copy(raw.identityHistory || []), historicalLabels: copy(raw.historicalLabels || {}), points,
        excludedObservations, qualityFlags,
        // The compiler removes these observations. Keep an independent engine
        // guard so an accidental reintroduction cannot price a position.
        quotes: new Map(points.filter(row => !excludedDates.has(row.date)).map(row => [row.date, row]))
      };
      if (!Array.isArray(asset.financials) || !Array.isArray(asset.identityHistory)) fail(raw.id + ': financial and identity histories must be dated arrays.');
      assets.set(asset.id, asset);
    });
    let prior = null;
    const rounds = data.rounds.map(raw => {
      if (!object(raw) || !Number.isInteger(raw.year) || raw.cutoff !== raw.year + '-12-31' || !date(raw.cutoff) || !date(raw.executionDate) || !date(raw.endDate) || raw.cutoff >= raw.executionDate || raw.executionDate >= raw.endDate || raw.endDate > data.asOf) fail('Annual decisions require a year-end information cutoff and later observed execution and ending dates.');
      if (prior && (raw.year !== prior.year + 1 || prior.endDate !== raw.executionDate)) fail('Annual periods must be chronological and meet at the next rebalance close.');
      if (!Array.isArray(raw.eligibleAssetIds) || new Set(raw.eligibleAssetIds).size !== raw.eligibleAssetIds.length || raw.eligibleAssetIds.some(value => !assets.has(value))) fail('An annual constituent list contains an unknown or repeated security.');
      if (!Array.isArray(raw.valuationDates) || raw.valuationDates.length < 2 || raw.valuationDates[0] !== raw.executionDate || raw.valuationDates[raw.valuationDates.length - 1] !== raw.endDate) fail('Each annual period needs an explicit observed valuation calendar including both execution dates.');
      let previous = '';
      raw.valuationDates.forEach(value => {
        if (!date(value) || value <= previous || value < raw.executionDate || value > raw.endDate) fail('Annual valuation dates must be unique and chronological.');
        previous = value;
      });
      const round = {year: raw.year, cutoff: raw.cutoff, executionDate: raw.executionDate, endDate: raw.endDate,
        eligibleAssetIds: raw.eligibleAssetIds.slice(), valuationDates: raw.valuationDates.slice()};
      prior = round;
      return round;
    });
    if (rounds[rounds.length - 1].endDate !== data.asOf) fail('The final annual period must end at the dataset as-of date.');
    const benchmarkAssetId = data.benchmarkAssetId || null;
    if (benchmarkAssetId && !assets.has(benchmarkAssetId)) fail('The benchmark security is missing.');
    const identity = {
      rules: VERSION, id: data.id || '', version: data.version ?? null, asOf: data.asOf,
      frequency: data.frequency || 'monthly', rounds, benchmarkAssetId,
      assets: Array.from(assets.values(), asset => ({...asset, quotes: undefined})).sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
      source: provenance(data.source || null), sources: provenance(data.sources || [])
    };
    const catalog = {assets, rounds, asOf: data.asOf, frequency: data.frequency || 'monthly', benchmarkAssetId,
      datasetId: verifiedDatasetId === undefined ? 'annual-v1-' + fingerprint(identity) : verifiedDatasetId, coverage: new Map()};
    cache.set(data, catalog);
    return catalog;
  }

  function assetCoverage(catalog, round, assetId) {
    const key = round.year + ':' + assetId;
    if (catalog.coverage.has(key)) return catalog.coverage.get(key);
    const asset = catalog.assets.get(assetId);
    const missingDates = round.valuationDates.filter(day => !asset.quotes.has(day));
    const qualityExcluded = asset.excludedObservations.some(row => round.valuationDates.includes(row.date));
    const result = freeze({complete: !missingDates.length, required: round.valuationDates.length,
      observed: round.valuationDates.length - missingDates.length, missingDates,
      reason: qualityExcluded ? 'Excluded after provider-quality review; incomplete reliable return path.'
        : missingDates.length ? 'Missing observed return indices in this period; no fill or terminal payout is assumed.' : null});
    catalog.coverage.set(key, result);
    return result;
  }
  function knownFinancials(asset, cutoff) {
    const eligible = asset.financials.filter(card => object(card) && (!card.decisionCutoff || card.decisionCutoff === cutoff)
      && date(card.availableAt) && card.availableAt <= cutoff && date(card.fiscalPeriodEnd) && card.fiscalPeriodEnd <= cutoff)
      .sort((a, b) => b.availableAt.localeCompare(a.availableAt));
    if (!eligible.length) return null;
    const card = eligible[0], metrics = {}, metricSources = {};
    METRICS.forEach(key => {
      const value = card.metrics && card.metrics[key], source = card.metricSources && card.metricSources[key];
      const usable = value != null && number(value) && object(source) && date(source.filed) && source.filed <= cutoff
        && date(source.fiscalPeriodEnd) && source.fiscalPeriodEnd <= cutoff
        && (!source.periodStart || (date(source.periodStart) && source.periodStart <= source.fiscalPeriodEnd));
      metrics[key] = usable ? value : null;
      if (usable) metricSources[key] = copy(source);
    });
    const filings = (Array.isArray(card.filings) ? card.filings : []).filter(filing => object(filing)
      && date(filing.filed) && filing.filed <= cutoff
      && (!filing.reportDate || (date(filing.reportDate) && filing.reportDate <= cutoff))).map(filing => ({
        form: filing.form || null, filed: filing.filed, reportDate: filing.reportDate || null,
        accession: filing.accession || null, url: filing.url || null, status: filing.status || null,
        investmentThemes: copy(Array.isArray(filing.investmentThemes) ? filing.investmentThemes : []),
        focusAreas: copy(Array.isArray(filing.focusAreas) ? filing.focusAreas : []), focusNote: filing.focusNote || null
      }));
    const valuation = object(card.valuation) && date(card.valuation.asOf) && card.valuation.asOf <= cutoff
      && (card.valuation.pe == null || number(card.valuation.pe)) ? copy(card.valuation) : null;
    return {decisionCutoff: cutoff, availableAt: card.availableAt, fiscalPeriodEnd: card.fiscalPeriodEnd,
      metrics, metricSources, filings, valuation, status: card.status || 'partial', reason: card.reason || null};
  }
  function identityAt(asset, cutoff) {
    const knownSector = date(asset.sectorAsOf) && asset.sectorAsOf <= cutoff ? asset.sector : null;
    const historical = asset.historicalLabels[cutoff.slice(0, 4)];
    if (object(historical)) return {id: asset.id, name: String(historical.name || historical.ticker || asset.name),
      ticker: historical.ticker == null ? asset.ticker : String(historical.ticker), cik: asset.cik, sector: historical.sector || knownSector,
      identityNote: historical.note || null};
    const row = asset.identityHistory.filter(item => object(item) && date(item.availableAt) && item.availableAt <= cutoff)
      .sort((a, b) => b.availableAt.localeCompare(a.availableAt))[0];
    return {id: asset.id, name: row && row.name ? String(row.name) : asset.name,
      ticker: row && row.ticker ? String(row.ticker) : asset.ticker, cik: asset.cik, sector: row?.sector || knownSector};
  }
  function initial(catalog) {
    const startDate = catalog.rounds[0].executionDate;
    return {schemaVersion: VERSION, datasetId: catalog.datasetId, index: 0, rounds: catalog.rounds.length, status: 'active',
      initialCapital: CAPITAL, startDate, date: startDate, cash: CAPITAL, positions: [], lots: [], actions: [],
      history: [{date: startDate, value: CAPITAL, cash: CAPITAL, investedValue: 0}], lastResult: null};
  }
  function canonicalWeights(input, round) {
    if (!object(input)) fail('Enter portfolio weights as fractions by security identifier.', 'INVALID_ALLOCATION');
    const weights = {}, allowed = new Set(round.eligibleAssetIds);
    let sum = 0;
    Object.keys(input).sort().forEach(key => {
      const weight = input[key];
      if (!allowed.has(key)) fail(key + ' is not an eligible constituent at this information cutoff.', 'INVALID_ALLOCATION');
      if (!number(weight) || weight < 0 || weight > 1) fail('Each weight must be a finite fraction between 0 and 1.', 'INVALID_ALLOCATION');
      if (weight > 0) { weights[key] = weight; sum += weight; }
    });
    if (sum > 1 + EPSILON) fail('Portfolio weights exceed 100%. Borrowing and leverage are not allowed.', 'INVALID_ALLOCATION');
    // Reserve the finite capital budget in canonical ID order. Clipping only
    // binary roundoff at the final allocations is idempotent: unlike dividing
    // every weight by a rounded sum, saving and replaying cannot renormalize the
    // entire portfolio a second time and drift its canonical action values.
    let remaining = 1;
    Object.keys(weights).forEach(key => {
      const reserved = Math.min(weights[key], remaining);
      remaining = Math.max(0, remaining - reserved);
      if (reserved > 0) weights[key] = reserved; else delete weights[key];
    });
    return {weights, totalWeight: 1 - remaining, cashWeight: remaining};
  }
  function action(catalog, state, input) {
    if (state.status !== 'active') fail('This annual exercise is finished.', 'COMPLETE');
    const round = catalog.rounds[state.index], allocation = canonicalWeights(input, round);
    const blockedAssets = Object.keys(allocation.weights).filter(key => !assetCoverage(catalog, round, key).complete)
      .map(key => ({id: key, ticker: catalog.assets.get(key).ticker, coverage: copy(assetCoverage(catalog, round, key))}));
    if (blockedAssets.length) fail('The chosen portfolio cannot be calculated because observed return coverage is incomplete.', 'COVERAGE_GAP', {blockedAssets});
    const before = state.history[state.history.length - 1].value;
    const next = copy(state);
    next.lots.filter(lot => lot.closedAt === null).forEach(lot => {
      const quote = catalog.assets.get(lot.assetId).quotes.get(round.executionDate);
      if (!quote) fail('A prior holding cannot be liquidated without an exact observed close.', 'COVERAGE_GAP', {assetId: lot.assetId, date: round.executionDate});
      lot.closedAt = round.executionDate; lot.exitIndex = quote.adjustedClose;
      lot.proceeds = lot.units * quote.adjustedClose; lot.realizedProfit = lot.proceeds - lot.invested;
      lot.unrealizedProfit = 0; lot.currentValue = 0;
    });
    const cash = before * allocation.cashWeight;
    const positions = Object.keys(allocation.weights).map(assetId => {
      const asset = catalog.assets.get(assetId), entry = asset.quotes.get(round.executionDate), end = asset.quotes.get(round.endDate);
      const invested = before * allocation.weights[assetId], units = invested / entry.adjustedClose;
      const value = units * end.adjustedClose;
      if (!number(value) || !number(units) || value <= 0 || units <= 0 || invested <= 0) fail('A position exceeds the supported numeric range.');
      const named = identityAt(asset, round.cutoff);
      next.lots.push({id: round.year + ':' + assetId, assetId, year: round.year, name: named.name, ticker: named.ticker,
        openedAt: round.executionDate, closedAt: null, valuedAt: round.endDate, invested, units,
        entryIndex: entry.adjustedClose, exitIndex: null, proceeds: null, realizedProfit: 0,
        currentValue: value, unrealizedProfit: value - invested});
      return {assetId, name: named.name, ticker: named.ticker, weight: allocation.weights[assetId], invested, units,
        entryIndex: entry.adjustedClose, entryDate: round.executionDate, quoteDate: round.endDate,
        adjustedClose: end.adjustedClose, value};
    });
    const path = round.valuationDates.map(day => {
      const investedValue = positions.reduce((sum, position) => sum + position.units * catalog.assets.get(position.assetId).quotes.get(day).adjustedClose, 0);
      const value = cash + investedValue;
      if (!number(value) || value < 0) fail('Portfolio value exceeds the supported numeric range.');
      return {date: day, value, cash, investedValue};
    });
    const after = path[path.length - 1].value;
    const companies = positions.map(position => {
      const endingValue = position.value, profit = endingValue - position.invested;
      const lots = next.lots.filter(lot => lot.assetId === position.assetId);
      return {id: position.assetId, name: position.name, ticker: position.ticker, weight: position.weight,
        invested: position.invested, endingValue, profit, return: endingValue / position.invested - 1,
        contribution: profit / before, cumulativeInvested: lots.reduce((sum, lot) => sum + lot.invested, 0),
        cumulativeProfit: lots.reduce((sum, lot) => sum + lot.realizedProfit + lot.unrealizedProfit, 0)};
    });
    next.cash = cash; next.positions = positions; next.date = round.endDate; next.index++;
    next.status = after <= 0 ? 'bankrupt' : next.index === catalog.rounds.length ? 'complete' : 'active';
    next.actions.push({year: round.year, weights: allocation.weights});
    // Replace the rebalance-date cash/exposure composition, while its equity
    // remains unchanged. Do not duplicate shared annual boundary dates.
    next.history[next.history.length - 1] = path[0];
    next.history.push(...path.slice(1));
    next.lastResult = {year: round.year, cutoff: round.cutoff, from: round.executionDate, to: round.endDate,
      before, after, change: after / before - 1, profit: after - before, cashWeight: allocation.cashWeight,
      companies, path, frequency: catalog.frequency, partial: round.endDate.slice(0, 4) === round.executionDate.slice(0, 4),
      coverage: {complete: true, observations: path.length}};
    return next;
  }
  function replayInternal(catalog, actions) {
    if (!Array.isArray(actions) || actions.length > catalog.rounds.length) fail('Invalid saved annual decision sequence.', 'INVALID_SAVE');
    let state = initial(catalog);
    actions.forEach(item => {
      if (!object(item) || Object.keys(item).some(key => !['year', 'weights'].includes(key)) || item.year !== catalog.rounds[state.index]?.year) fail('Annual decisions are out of order.', 'INVALID_SAVE');
      state = action(catalog, state, item.weights);
    });
    return state;
  }
  function checked(catalog, run) {
    if (!object(run) || run.schemaVersion !== VERSION || run.datasetId !== catalog.datasetId) fail('This run belongs to a different source edition.', 'EDITION_MISMATCH');
    if (trustedRuns.has(run)) return run;
    const rebuilt = replayInternal(catalog, run.actions);
    if (fingerprint(rebuilt) !== fingerprint(run)) fail('Saved portfolio balances or history do not match the canonical decisions.', 'INVALID_SAVE');
    return seal(rebuilt);
  }
  function create(data) { return seal(initial(prepare(data))); }
  // Native bundles may skip only the expensive edition hash after their host
  // verifies a build-generated manifest against SHA-256 of BOTH exact source
  // and engine bytes. This is not a validation API for user-submitted IDs.
  // All source/price/calendar validation and canonical replay remain enabled.
  function createWithVerifiedEdition(data, verifiedDatasetId) {
    if (verifiedDatasetId === undefined) fail('A host-verified edition is required.', 'INVALID_VERIFIED_EDITION');
    return seal(initial(prepare(data, verifiedDatasetId)));
  }
  function current(data, run) {
    const catalog = prepare(data), state = checked(catalog, run);
    if (state.status !== 'active') return null;
    const round = catalog.rounds[state.index], capital = state.history[state.history.length - 1].value;
    const companies = round.eligibleAssetIds.map(assetId => {
      const asset = catalog.assets.get(assetId), coverage = assetCoverage(catalog, round, assetId);
      const position = state.positions.find(item => item.assetId === assetId);
      return {...identityAt(asset, round.cutoff), financials: knownFinancials(asset, round.cutoff), canInvest: coverage.complete,
        coverage: copy(coverage), currentWeight: position ? position.value / capital : 0};
    });
    return {year: round.year, cutoff: round.cutoff, executionDate: round.executionDate, endDate: round.endDate,
      round: state.index + 1, rounds: catalog.rounds.length, capital, companies, disclosure: DISCLOSURE,
      coverage: {eligible: companies.length, supported: companies.filter(item => item.canInvest).length}};
  }
  function validateAllocation(data, run, weights) {
    const catalog = prepare(data), state = checked(catalog, run);
    if (state.status !== 'active') return {valid: false, totalWeight: null, cashWeight: null, errors: ['This exercise is finished.'], blockedAssets: []};
    const round = catalog.rounds[state.index];
    let allocation;
    try { allocation = canonicalWeights(weights, round); }
    catch (error) { return {valid: false, totalWeight: null, cashWeight: null, errors: [error.message], blockedAssets: []}; }
    const blockedAssets = Object.keys(allocation.weights).filter(key => !assetCoverage(catalog, round, key).complete)
      .map(key => ({id: key, ticker: catalog.assets.get(key).ticker, coverage: copy(assetCoverage(catalog, round, key))}));
    return {valid: !blockedAssets.length, totalWeight: allocation.totalWeight, cashWeight: allocation.cashWeight,
      errors: blockedAssets.length ? ['The selected portfolio has unresolved return coverage.'] : [], blockedAssets};
  }
  function allocate(data, run, weights) {
    const catalog = prepare(data);
    return seal(action(catalog, checked(catalog, run), weights));
  }
  function attribution(state) {
    const firms = new Map();
    state.lots.forEach(lot => {
      if (!firms.has(lot.assetId)) firms.set(lot.assetId, {id: lot.assetId, name: lot.name, ticker: lot.ticker,
        totalInvested: 0, realizedProfit: 0, unrealizedProfit: 0, currentValue: 0, periods: 0});
      const item = firms.get(lot.assetId);
      item.totalInvested += lot.invested; item.realizedProfit += lot.realizedProfit;
      item.unrealizedProfit += lot.unrealizedProfit; item.currentValue += lot.currentValue; item.periods++;
      item.name = lot.name; item.ticker = lot.ticker;
    });
    return Array.from(firms.values(), item => ({...item, profit: item.realizedProfit + item.unrealizedProfit,
      contribution: (item.realizedProfit + item.unrealizedProfit) / CAPITAL,
      returnOnAllocatedCapital: item.totalInvested ? (item.realizedProfit + item.unrealizedProfit) / item.totalInvested : null}));
  }
  function benchmark(catalog, state) {
    if (!catalog.benchmarkAssetId) return null;
    const asset = catalog.assets.get(catalog.benchmarkAssetId), entry = asset.quotes.get(state.startDate);
    if (!entry || state.history.some(point => !asset.quotes.has(point.date))) return {id: asset.id, status: 'unavailable', reason: 'Exact benchmark observations do not cover this shared window.', value: null, change: null, path: []};
    const path = state.history.map(point => ({date: point.date, value: CAPITAL * asset.quotes.get(point.date).adjustedClose / entry.adjustedClose}));
    const value = path[path.length - 1].value;
    return {id: asset.id, name: asset.name, status: 'available', value, change: value / CAPITAL - 1, path};
  }
  function portfolio(data, run) {
    const catalog = prepare(data), state = checked(catalog, run), value = state.history[state.history.length - 1].value;
    return {date: state.date, value, cash: state.cash, investedValue: value - state.cash, change: value / CAPITAL - 1,
      profit: value - CAPITAL, positions: copy(state.positions), companies: attribution(state), history: copy(state.history),
      benchmark: benchmark(catalog, state)};
  }
  function companyHistory(data, run, assetId) {
    const catalog = prepare(data), state = checked(catalog, run), asset = catalog.assets.get(assetId);
    if (!asset) fail('Unknown security.');
    const lots = state.lots.filter(lot => lot.assetId === assetId);
    const periods = lots.map(lot => {
      const end = lot.closedAt || lot.valuedAt, endingValue = lot.closedAt ? lot.proceeds : lot.currentValue;
      return {year: lot.year, from: lot.openedAt, to: end, invested: lot.invested, endingValue,
        profit: endingValue - lot.invested, return: endingValue / lot.invested - 1, closed: lot.closedAt !== null};
    });
    const ownedReturnPath = [];
    const path = state.history.map(point => {
      let profit = 0, value = 0, capitalAllocated = 0, ownedLevel = CAPITAL;
      lots.forEach(lot => {
        if (point.date < lot.openedAt) return;
        capitalAllocated += lot.invested;
        const end = lot.closedAt || lot.valuedAt;
        const markDate = point.date < end ? point.date : end;
        const quote = asset.quotes.get(markDate);
        if (!quote) fail('An invested period has an unresolved valuation.', 'COVERAGE_GAP');
        const mark = lot.units * quote.adjustedClose;
        ownedLevel *= quote.adjustedClose / asset.quotes.get(lot.openedAt).adjustedClose;
        profit += mark - lot.invested;
        if (!lot.closedAt || point.date < lot.closedAt) value += mark;
      });
      if (lots.length) ownedReturnPath.push({date: point.date, value: ownedLevel, invested: value > 0});
      return {date: point.date, profit, contribution: profit / CAPITAL, value, capitalAllocated, invested: value > 0};
    });
    // A completed round can be inspected even when no position was taken.
    // Never inspect the unresolved current round or jump to a future period
    // merely because it has more complete prices.
    const recentRound = catalog.rounds.slice(0, state.index).reverse().find(round => round.eligibleAssetIds.includes(assetId));
    let mostRecentPeriod = null;
    if (recentRound) {
      const coverage = assetCoverage(catalog, recentRound, assetId);
      const normalizedPath = security => recentRound.valuationDates.map(day => ({date: day,
        value: CAPITAL * security.quotes.get(day).adjustedClose / security.quotes.get(recentRound.executionDate).adjustedClose}));
      const stockPath = coverage.complete ? normalizedPath(asset) : [];
      let comparator = null;
      if (catalog.benchmarkAssetId) {
        const security = catalog.assets.get(catalog.benchmarkAssetId), benchmarkCoverage = assetCoverage(catalog, recentRound, security.id);
        const marks = benchmarkCoverage.complete ? normalizedPath(security) : [];
        comparator = {id: security.id, status: benchmarkCoverage.complete ? 'available' : 'unavailable',
          reason: benchmarkCoverage.complete ? null : 'Exact benchmark observations do not cover this completed interval.',
          return: marks.length ? marks[marks.length - 1].value / CAPITAL - 1 : null, path: marks};
      }
      const identity = identityAt(asset, recentRound.cutoff);
      mostRecentPeriod = {year: recentRound.year, cutoff: recentRound.cutoff, from: recentRound.executionDate, to: recentRound.endDate,
        name: identity.name, ticker: identity.ticker, coverage: copy(coverage),
        return: stockPath.length ? stockPath[stockPath.length - 1].value / CAPITAL - 1 : null,
        path: stockPath, benchmark: comparator};
    }
    const lastLot = lots[lots.length - 1], knownIdentity = identityAt(asset, catalog.rounds[Math.max(0, state.index - 1)].cutoff);
    return {id: assetId, name: lastLot ? lastLot.name : knownIdentity.name, ticker: lastLot ? lastLot.ticker : knownIdentity.ticker, periods, path,
      ownedReturn: ownedReturnPath.length ? ownedReturnPath[ownedReturnPath.length - 1].value / CAPITAL - 1 : null,
      ownedReturnPath, mostRecentPeriod,
      summary: attribution(state).find(item => item.id === assetId) || null};
  }
  function outcomes(data, run, year) {
    const catalog = prepare(data), state = checked(catalog, run);
    const chosenYear = year === undefined ? state.actions[state.actions.length - 1]?.year : year;
    const index = catalog.rounds.findIndex(round => round.year === chosenYear);
    if (index < 0 || index >= state.index) fail('Firm outcomes are available only after that annual allocation is committed.', 'FUTURE_INFORMATION');
    const round = catalog.rounds[index];
    return {year: round.year, from: round.executionDate, to: round.endDate,
      companies: round.eligibleAssetIds.map(assetId => {
        const asset = catalog.assets.get(assetId), coverage = assetCoverage(catalog, round, assetId);
        return {...identityAt(asset, round.cutoff), coverage: copy(coverage),
          return: coverage.complete ? asset.quotes.get(round.endDate).adjustedClose / asset.quotes.get(round.executionDate).adjustedClose - 1 : null};
      })};
  }
  function score(data, run) {
    const catalog = prepare(data), state = checked(catalog, run);
    if (state.status === 'active') fail('Finish the annual exercise before recording a score.', 'INCOMPLETE');
    const book = portfolio(data, state);
    let peak = CAPITAL, drawdown = 0;
    state.history.forEach(point => { peak = Math.max(peak, point.value); drawdown = Math.min(drawdown, point.value / peak - 1); });
    return {datasetId: catalog.datasetId, runId: 'annual-run-' + fingerprint([catalog.datasetId, state.actions]),
      status: state.status, startDate: state.startDate, endDate: state.date, periods: state.index,
      initialCapital: CAPITAL, finalValue: book.value, profit: book.profit, change: book.change,
      maxDrawdown: drawdown, observationFrequency: catalog.frequency,
      benchmarkValue: book.benchmark?.value ?? null, benchmarkChange: book.benchmark?.change ?? null,
      disclosure: DISCLOSURE};
  }
  function serialize(run) {
    if (!trustedRuns.has(run)) fail('Only a replay-verified run can be saved.', 'INVALID_SAVE');
    return JSON.stringify({schemaVersion: VERSION, datasetId: run.datasetId, actions: run.actions});
  }
  function restore(data, text) {
    if (typeof text !== 'string' || text.length > 2000000) fail('Invalid annual portfolio save.', 'INVALID_SAVE');
    let saved;
    try { saved = JSON.parse(text); } catch (_) { fail('The saved portfolio is not valid JSON.', 'INVALID_SAVE'); }
    const catalog = prepare(data);
    if (!object(saved) || Object.keys(saved).some(key => !['schemaVersion', 'datasetId', 'actions'].includes(key)) || saved.schemaVersion !== VERSION) fail('Unsupported saved annual portfolio.', 'INVALID_SAVE');
    if (saved.datasetId !== catalog.datasetId) fail('This save belongs to a different economic data edition.', 'EDITION_MISMATCH');
    return seal(replayInternal(catalog, saved.actions));
  }
  function replay(data, actions) { return seal(replayInternal(prepare(data), actions)); }

  return Object.freeze({VERSION, DISCLOSURE, create, createWithVerifiedEdition, current, validateAllocation, allocate, portfolio, companyHistory, outcomes,
    score, serialize, restore, replay, validDate: date, datasetId: data => prepare(data).datasetId});
});
