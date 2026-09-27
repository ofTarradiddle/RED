/*
 * Hetzerk's historical investing exercise. No dependencies; browser and Node.
 *
 * const state = InnovationGame.createGame(data);
 * const card = InnovationGame.currentDecision(data, state);
 * const next = InnovationGame.decide(data, state, {amount: 25}); // or amount: 0
 * const book = InnovationGame.portfolio(data, next);
 *
 * A position is a fractional adjusted-price RETURN-INDEX unit, not a brokerage
 * share. Adjusted close already incorporates the provider's distributions and
 * splits; neither is credited a second time. Trading requires an actual quote
 * on the decision date. A cached prior quote is a valuation, never an order fill.
 */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.InnovationGame = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = 1;
  const DAY = 86400000;
  const EPSILON = 1e-10;
  const MAX_ACTIONS = 10000;
  const compiled = new WeakMap();
  const forbiddenIDs = new Set([...Object.getOwnPropertyNames(Object.prototype), 'prototype']);
  const DECISION_KEYS = ['marketOpportunity', 'investmentThesis', 'valuation', 'investment', 'competitivePosition', 'risks', 'context', 'sources', 'knownAt', 'availableAt', 'question', 'revenue', 'researchAndDevelopment', 'editorialPrompt'];
  const DISCLOSURE = 'A curated, hindsight-selected historical exercise, not an unbiased backtest. Fractional adjusted-price return-index units assume the data provider’s reinvested distributions, zero fees and taxes, and 0% cash interest. Some innovations predate investable price coverage. A replay verifies arithmetic, not whether a player knew future outcomes.';

  function fail(message) { throw new Error(message); }
  function validDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const time = Date.parse(value + 'T00:00:00Z');
    return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value;
  }
  function daysBetween(a, b) { return (Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / DAY; }
  function finite(value) { return typeof value === 'number' && Number.isFinite(value); }
  function identifier(value) { return typeof value === 'string' && value.length > 0 && value.length <= 160 && !forbiddenIDs.has(value); }
  function plain(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
  function copy(value) { return value === undefined ? null : JSON.parse(JSON.stringify(value)); }
  function fingerprint(value) {
    // A stable dataset/replay identifier, deliberately not an anti-cheat signature.
    let hash = 2166136261;
    const text = typeof value === 'string' ? value : JSON.stringify(value, (_key, item) => {
      if (!plain(item)) return item;
      const ordered = Object.create(null);
      Object.keys(item).sort().forEach(key => { ordered[key] = item[key]; });
      return ordered;
    });
    for (let i = 0; i < text.length; i++) { hash ^= text.charCodeAt(i); hash = Math.imul(hash, 16777619); }
    return (hash >>> 0).toString(16).padStart(8, '0');
  }

  function prepare(data) {
    if (!plain(data)) fail('The innovation dataset is missing.');
    if (compiled.has(data)) return compiled.get(data);
    if (!validDate(data.asOf) || !Array.isArray(data.assets) || !Array.isArray(data.opportunities)) fail('The dataset needs an asOf date, assets and opportunities.');
    const assets = new Map();
    // Build/retrieval times are operational metadata, not a new game edition.
    // The broader archive's `version` also hashes fetched-at stamps and catalog
    // entries, so it cannot identify economically equivalent saved games. Use
    // gameVersion only for an intentional edition change beyond the rules,
    // prices, decision information and dates already fingerprinted below.
    const identity = [VERSION, data.schemaVersion ?? 1, data.id || '', data.gameVersion ?? null, data.asOf];
    data.assets.forEach(asset => {
      if (!plain(asset) || !identifier(asset.id) || assets.has(asset.id) || !Array.isArray(asset.points)) fail('Asset IDs must be unique and each asset must have a price history.');
      if (asset.currency && asset.currency !== 'USD') fail('All game assets must use USD; currency conversion cannot be inferred.');
      const points = asset.points.map(row => {
        const value = row && (row.adjustedClose === undefined ? row.totalReturnIndex : row.adjustedClose);
        if (!row || !validDate(row.date) || row.date > data.asOf || !finite(value) || value < 0) fail('A return history contains an invalid date or adjusted price.');
        if (row.close !== undefined && row.close !== null && (!finite(row.close) || row.close < 0)) fail('A return history contains an invalid unadjusted closing price.');
        return {date: row.date, value, close: row.close ?? null};
      }).sort((a, b) => a.date.localeCompare(b.date));
      points.forEach((row, i) => {
        if (i && row.date === points[i - 1].date) fail('Duplicate price dates cannot be used in the game.');
        if (i && points[i - 1].value === 0 && row.value > 0) fail('A zero return index cannot recover without a separately modeled capital event.');
      });
      const normalized = {id: asset.id, name: String(asset.name || asset.id), ticker: String(asset.ticker || asset.id), points};
      assets.set(asset.id, normalized);
      identity.push([asset.id, asset.currency || 'USD', points]);
    });
    const ids = new Set();
    const opportunities = data.opportunities.map((event, order) => {
      if (!plain(event) || !identifier(event.id) || ids.has(event.id) || !validDate(event.date) || event.date > data.asOf || !assets.has(event.assetId)) fail('Every opportunity needs a unique ID, valid date and known asset.');
      ids.add(event.id);
      if (event.eventDate && (!validDate(event.eventDate) || event.eventDate > event.date)) fail('A decision cannot precede its innovation event.');
      if (event.decision && event.decision.availableAt && (!validDate(event.decision.availableAt) || event.decision.availableAt > event.date)) fail('Decision information was not available on the decision date.');
      return {event, order};
    }).sort((a, b) => a.event.date.localeCompare(b.event.date) || a.order - b.order).map(row => row.event);
    identity.push(opportunities, data.benchmarkAssetId || null);
    if (data.benchmarkAssetId && !assets.has(data.benchmarkAssetId)) fail('The benchmark is not present in the dataset.');
    const result = {asOf: data.asOf, assets, opportunities, benchmarkAssetId: data.benchmarkAssetId || null, id: 'innovation-v1-' + fingerprint(identity)};
    compiled.set(data, result);
    return result;
  }

  function findQuote(asset, date) {
    let low = 0, high = asset.points.length - 1, found = null;
    while (low <= high) {
      const middle = Math.floor((low + high) / 2), point = asset.points[middle];
      if (point.date <= date) { found = point; low = middle + 1; } else high = middle - 1;
    }
    return found && {date: found.date, value: found.value, ageDays: daysBetween(found.date, date)};
  }

  function quoteAt(data, assetId, date) {
    const catalog = prepare(data);
    if (!validDate(date) || date > catalog.asOf) fail('Quotes require a valid date within the published history.');
    const asset = catalog.assets.get(assetId);
    if (!asset) fail('Unknown asset.');
    return findQuote(asset, date);
  }

  function checkState(catalog, state) {
    if (!plain(state) || state.schemaVersion !== VERSION || state.datasetId !== catalog.id) fail('This game belongs to a different dataset. Start again or load its original data.');
    if (!finite(state.cash) || state.cash < 0 || !finite(state.initialCapital) || state.initialCapital <= 0 || !plain(state.positions) || !Array.isArray(state.actions) || !Array.isArray(state.trades) || !validDate(state.date)) fail('The saved portfolio is invalid.');
    if (!Number.isInteger(state.index) || state.index < 0 || state.index > catalog.opportunities.length || state.actions.length !== state.index) fail('The game decision sequence is invalid.');
    if (!['active', 'complete', 'bankrupt'].includes(state.status)) fail('The game status is invalid.');
    if (state.date > catalog.asOf || (state.status === 'active' && (!catalog.opportunities[state.index] || state.date !== catalog.opportunities[state.index].date))) fail('The portfolio date does not match its next decision.');
    Object.entries(state.positions).forEach(([id, units]) => {
      if (!catalog.assets.has(id) || !finite(units) || units < 0) fail('The portfolio contains invalid return-index units.');
    });
  }

  function benchmark(catalog, state, date) {
    if (!catalog.benchmarkAssetId) return null;
    const asset = catalog.assets.get(catalog.benchmarkAssetId);
    // Buying at a previous close with later knowledge is prohibited here too.
    const first = asset.points.find(point => point.date >= state.startDate && point.value > 0);
    if (!first || first.date > date) return {assetId: asset.id, name: asset.name, value: state.initialCapital, change: 0, from: null, quoteDate: null, status: 'waiting-for-history', cashBeforeInception: true};
    const last = findQuote(asset, date);
    return {assetId: asset.id, name: asset.name, value: state.initialCapital * last.value / first.value, change: last.value / first.value - 1, from: first.date, quoteDate: last.date, ageDays: last.ageDays, status: last.ageDays > state.maxQuoteAgeDays ? 'stale' : 'available', cashBeforeInception: first.date > state.startDate};
  }

  function valuePortfolio(catalog, state, date) {
    const warnings = [], positions = [];
    let value = state.cash;
    Object.entries(state.positions).forEach(([id, units]) => {
      if (units === 0) return;
      const asset = catalog.assets.get(id), quote = findQuote(asset, date);
      if (!quote) fail('A held asset has no valuation at this date.');
      const positionValue = units * quote.value;
      if (!finite(positionValue)) fail('The portfolio exceeds the supported numeric range.');
      const stale = quote.ageDays > state.maxQuoteAgeDays;
      if (stale) warnings.push(asset.ticker + ' is valued at its last observed quote (' + quote.date + '), not a current quote. A missing delisting payoff cannot be inferred.');
      positions.push({assetId: id, name: asset.name, ticker: asset.ticker, units, value: positionValue, adjustedClose: quote.value, quoteDate: quote.date, ageDays: quote.ageDays, stale, canSell: quote.date === date && quote.value > 0});
      value += positionValue;
    });
    if (!finite(value)) fail('The portfolio exceeds the supported numeric range.');
    const comparison = benchmark(catalog, state, date);
    if (comparison && comparison.status === 'stale') warnings.push('The benchmark is valued at its last observed quote (' + comparison.quoteDate + ').');
    return {date, cash: state.cash, investedValue: value - state.cash, value, change: value / state.initialCapital - 1, positions, benchmark: comparison, warnings, comparable: !positions.some(position => position.stale) && (!comparison || comparison.status === 'available')};
  }

  function portfolio(data, state, date) {
    const catalog = prepare(data);
    checkState(catalog, state);
    const asOf = date || state.date;
    if (!validDate(asOf) || asOf > state.date || asOf < state.startDate) fail('The active portfolio cannot be valued using a future or pre-game date.');
    // Current holdings cannot be projected backwards through transactions.
    if (asOf !== state.date && state.trades.some(trade => trade.date > asOf)) fail('Use the saved equity history to inspect dates before a transaction.');
    return valuePortfolio(catalog, state, asOf);
  }

  function historyPoint(catalog, state) {
    const book = valuePortfolio(catalog, state, state.date);
    return {date: state.date, value: book.value, cash: book.cash, benchmarkValue: book.benchmark ? book.benchmark.value : null};
  }

  function createGame(data, options) {
    const catalog = prepare(data), config = options || {};
    const initialCapital = config.initialCapital === undefined ? 100 : config.initialCapital;
    if (!finite(initialCapital) || initialCapital <= 0 || initialCapital > 1000000000) fail('Starting capital must be a positive amount no greater than one billion dollars.');
    const maxQuoteAgeDays = config.maxQuoteAgeDays === undefined ? 45 : config.maxQuoteAgeDays;
    if (!Number.isInteger(maxQuoteAgeDays) || maxQuoteAgeDays < 0 || maxQuoteAgeDays > 365) fail('Quote age tolerance must be between 0 and 365 days.');
    const date = catalog.opportunities.length ? catalog.opportunities[0].date : catalog.asOf;
    const state = {schemaVersion: VERSION, datasetId: catalog.id, initialCapital, maxQuoteAgeDays, startDate: date, date, index: 0, cash: initialCapital, positions: {}, trades: [], actions: [], history: [], status: catalog.opportunities.length ? 'active' : 'complete'};
    state.history.push(historyPoint(catalog, state));
    return state;
  }

  function knownInformation(value, date) {
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
    if (typeof value === 'number') return finite(value) ? value : null;
    if (Array.isArray(value)) return value.map(item => knownInformation(item, date)).filter(item => item !== undefined);
    if (!plain(value)) return undefined;
    const availability = value.availableAt || value.knownAt || value.filedAt;
    if (availability && (!validDate(availability) || availability > date)) return undefined;
    const result = {};
    Object.keys(value).forEach(key => {
      if (forbiddenIDs.has(key) || ['outcome', 'futureReturn', 'realizedReturn', 'futureNarrative'].includes(key)) return;
      const item = knownInformation(value[key], date);
      if (item !== undefined) result[key] = item;
    });
    return result;
  }

  function currentDecision(data, state) {
    const catalog = prepare(data);
    checkState(catalog, state);
    if (state.status !== 'active') return null;
    const event = catalog.opportunities[state.index], asset = catalog.assets.get(event.assetId), quote = findQuote(asset, state.date);
    const decision = {};
    DECISION_KEYS.forEach(key => {
      if (!event.decision || event.decision[key] === undefined) return;
      const item = knownInformation(event.decision[key], state.date);
      if (item !== undefined) decision[key] = item;
    });
    const canInvest = Boolean(event.canTrade !== false && quote && quote.date === state.date && quote.value > 0);
    let unavailableReason = null;
    if (event.canTrade === false) unavailableReason = 'This historical opportunity is not enabled for trading in the published dataset.';
    else if (!quote) unavailableReason = 'No public return history is available on or before this decision date.';
    else if (quote.date !== state.date) unavailableReason = 'There is no execution quote on this decision date. Earlier prices cannot be used to fill an order.';
    else if (quote.value === 0) unavailableReason = 'This return index has reached zero and cannot accept new investment.';
    return {id: event.id, date: event.date, eventDate: event.eventDate || event.date, title: String(event.title || ''), assetId: asset.id, firm: {id: asset.id, name: asset.name, ticker: asset.ticker}, decision, quote, canInvest, unavailableReason, cashAvailable: state.cash, number: state.index + 1, total: catalog.opportunities.length, remaining: catalog.opportunities.length - state.index};
  }

  function normalizeAction(action) {
    if (!plain(action)) fail('Choose an investment amount or pass with amount zero.');
    const amount = action.amount === undefined ? 0 : action.amount;
    if (!finite(amount) || amount < 0) fail('Investment amounts must be finite and nonnegative.');
    if (action.sells !== undefined && !Array.isArray(action.sells)) fail('Sales must be a list of dollar amounts.');
    const ids = new Set();
    const sells = (action.sells || []).map(sale => {
      if (!plain(sale) || !identifier(sale.assetId) || ids.has(sale.assetId) || !finite(sale.amount) || sale.amount <= 0) fail('Each sale must name a different asset and a positive finite amount.');
      ids.add(sale.assetId);
      return {assetId: sale.assetId, amount: sale.amount};
    }).sort((a, b) => a.assetId.localeCompare(b.assetId));
    return {amount, sells};
  }

  function decide(data, state, action) {
    const catalog = prepare(data);
    checkState(catalog, state);
    if (state.status !== 'active') fail('This game has ended. Start another game to make new decisions.');
    const next = copy(state), instruction = normalizeAction(action), event = catalog.opportunities[state.index];
    instruction.sells.forEach(sale => {
      const asset = catalog.assets.get(sale.assetId), units = next.positions[sale.assetId] || 0;
      if (!asset || units <= 0) fail('You cannot sell an asset you do not own.');
      const quote = findQuote(asset, next.date);
      if (!quote || quote.date !== next.date || quote.value <= 0) fail('A sale requires a positive execution quote on the decision date.');
      const holdingValue = units * quote.value;
      if (sale.amount > holdingValue + EPSILON * Math.max(1, holdingValue)) fail('A sale cannot exceed the value of the held position.');
      const proceeds = Math.min(sale.amount, holdingValue), soldUnits = proceeds / quote.value;
      next.positions[sale.assetId] = Math.max(0, units - soldUnits);
      next.cash += proceeds;
      next.trades.push({opportunityId: event.id, date: next.date, assetId: sale.assetId, side: 'sell', amount: proceeds, units: soldUnits, adjustedClose: quote.value, quoteDate: quote.date});
    });
    if (instruction.amount > next.cash + EPSILON * Math.max(1, next.cash)) fail('Investment exceeds available cash. Borrowing is not permitted.');
    if (instruction.amount > 0) {
      const asset = catalog.assets.get(event.assetId), quote = findQuote(asset, next.date);
      if (event.canTrade === false || !quote || quote.date !== next.date || quote.value <= 0) fail('An investment requires an eligible asset and a positive execution quote on the decision date.');
      const amount = Math.min(instruction.amount, next.cash), units = amount / quote.value;
      if (!finite(units)) fail('This investment exceeds the supported numeric range.');
      next.positions[asset.id] = (next.positions[asset.id] || 0) + units;
      next.cash = Math.max(0, next.cash - amount);
      next.trades.push({opportunityId: event.id, date: next.date, assetId: asset.id, side: 'buy', amount, units, adjustedClose: quote.value, quoteDate: quote.date});
    }
    next.actions.push({opportunityId: event.id, amount: instruction.amount, sells: instruction.sells});
    next.index += 1;
    next.date = next.index < catalog.opportunities.length ? catalog.opportunities[next.index].date : catalog.asOf;
    next.status = next.index < catalog.opportunities.length ? 'active' : 'complete';
    const book = valuePortfolio(catalog, next, next.date);
    if (book.value <= 0) next.status = 'bankrupt';
    next.history.push(historyPoint(catalog, next));
    return next;
  }

  function outcomes(data, state) {
    const catalog = prepare(data);
    checkState(catalog, state);
    return catalog.opportunities.slice(0, state.index).flatMap(event => {
      const availableAt = (plain(event.outcome) && event.outcome.availableAt) || event.outcomeDate || catalog.asOf;
      if (!validDate(availableAt) || availableAt > state.date || !event.outcome) return [];
      return [{opportunityId: event.id, availableAt, outcome: copy(event.outcome)}];
    });
  }

  function replay(data, actions, options) {
    if (!Array.isArray(actions) || actions.length > MAX_ACTIONS) fail('The replay has an invalid number of decisions.');
    let state = createGame(data, options);
    for (const action of actions) {
      const card = currentDecision(data, state);
      if (!plain(action) || !card || (action.opportunityId !== undefined && action.opportunityId !== card.id)) fail('The replay decision order does not match this dataset.');
      state = decide(data, state, action);
    }
    return state;
  }

  function serialize(state) {
    if (!plain(state) || !Array.isArray(state.actions)) fail('There is no game to save.');
    return JSON.stringify({schemaVersion: VERSION, datasetId: state.datasetId, settings: {initialCapital: state.initialCapital, maxQuoteAgeDays: state.maxQuoteAgeDays}, actions: state.actions});
  }

  function restore(data, saved) {
    if (typeof saved === 'string' && saved.length > 5000000) fail('The saved game is too large.');
    let payload;
    try { payload = typeof saved === 'string' ? JSON.parse(saved) : saved; } catch (_) { fail('The saved game is not valid JSON.'); }
    const catalog = prepare(data);
    if (!plain(payload) || payload.schemaVersion !== VERSION || payload.datasetId !== catalog.id || !plain(payload.settings)) fail('This save uses different data or unsupported rules.');
    // Balances, positions and claimed scores in a save are never trusted.
    return replay(data, payload.actions, payload.settings);
  }

  function score(data, state) {
    // Recompute from actions so an edited cash balance cannot become a score.
    const verified = restore(data, serialize(state)), book = portfolio(data, verified);
    const canonical = JSON.parse(serialize(verified));
    const complete = verified.status === 'complete' || verified.status === 'bankrupt';
    const defaultRules = verified.initialCapital === 100 && verified.maxQuoteAgeDays === 45;
    return {schemaVersion: VERSION, datasetId: verified.datasetId, replayId: fingerprint(canonical), initialCapital: verified.initialCapital, startDate: verified.startDate, endDate: verified.date, endValue: book.value, change: book.change, benchmarkValue: book.benchmark ? book.benchmark.value : null, benchmark: book.benchmark, status: verified.status, complete, decisions: verified.actions.length, investments: verified.actions.filter(action => action.amount > 0).length, comparable: complete && defaultRules && book.comparable, defaultRules, warnings: book.warnings, replay: canonical, disclosure: DISCLOSURE};
  }

  function verifyScore(data, record) {
    if (!plain(record) || !record.replay) fail('A leaderboard entry requires its full replay.');
    const result = score(data, restore(data, record.replay));
    if (record.replayId && record.replayId !== result.replayId) fail('The replay identifier does not match its decisions.');
    if (record.endValue !== undefined && (!finite(record.endValue) || Math.abs(record.endValue - result.endValue) > EPSILON * Math.max(1, result.endValue))) fail('The claimed score does not match the replay.');
    return result;
  }

  return Object.freeze({VERSION, DISCLOSURE, validDate, createGame, currentDecision, portfolio, quoteAt, decide, outcomes, replay, serialize, restore, score, verifyScore, datasetId: data => prepare(data).id});
});
