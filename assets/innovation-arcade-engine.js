/*
 * Twelve historical decisions, $100 fictional starting capital.
 * Load innovation-game-engine.js first in browsers and JavaScriptCore.
 * Every turn first closes existing positive-value positions at that day's
 * observed prices, then puts 0%, 25%, 50% or 100% into the current company.
 */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./innovation-game-engine.js'));
  else root.InnovationArcade = factory(root.InnovationGame);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (HistoricalGame) {
  'use strict';

  if (!HistoricalGame) throw new Error('Load InnovationGame before InnovationArcade.');
  const VERSION = 1;
  const ROUNDS = 12;
  const FRACTIONS = Object.freeze([0, 0.25, 0.5, 1]);
  const cache = new WeakMap();
  const DISCLOSURE = 'A twelve-round historical learning game using hindsight-selected firms. Each decision liquidates prior positions before the chosen allocation. Provider-adjusted return indices include its dividend and split adjustments; no extra dividends are credited. Cash earns 0%; fees, taxes and inflation are excluded. A valid replay checks arithmetic, not investment skill or whether someone knew the future.';

  function fail(message) { throw new Error(message); }
  function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  function hash(value) {
    const text = typeof value === 'string' ? value : JSON.stringify(value);
    let result = 2166136261;
    for (let i = 0; i < text.length; i++) { result ^= text.charCodeAt(i); result = Math.imul(result, 16777619); }
    return (result >>> 0).toString(16).padStart(8, '0');
  }
  function randomGenerator(seed) {
    let state = parseInt(hash(seed), 16) || 0x6d2b79f5;
    return function () {
      state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
      return (state >>> 0) / 4294967296;
    };
  }
  function settings(options) {
    const input = options || {};
    if (!object(input)) fail('Choose Classic or Daily mode.');
    const mode = input.mode === undefined ? 'classic' : input.mode;
    if (mode !== 'classic' && mode !== 'daily') fail('Choose Classic or Daily mode.');
    const day = mode === 'daily' ? input.day : null;
    if (mode === 'daily' && !HistoricalGame.validDate(day)) fail('Daily mode requires a valid YYYY-MM-DD day shared by all players.');
    return {mode, day};
  }
  function validFraction(value) { return typeof value === 'number' && Number.isFinite(value) && FRACTIONS.includes(value); }

  function prepare(data, options) {
    const config = settings(options), datasetId = HistoricalGame.datasetId(data);
    let editions = cache.get(data);
    if (!editions) { editions = new Map(); cache.set(data, editions); }
    const key = config.mode + ':' + (config.day || 'classic');
    if (editions.has(key)) return editions.get(key);
    const quotes = new Map();
    function exactQuote(assetId, date) {
      const quoteKey = assetId + '|' + date;
      if (!quotes.has(quoteKey)) {
        const mark = HistoricalGame.quoteAt(data, assetId, date);
        quotes.set(quoteKey, mark && mark.date === date ? mark : null);
      }
      return quotes.get(quoteKey);
    }
    const candidates = data.opportunities.filter(event => {
      if (event.canTrade === false) return false;
      const start = exactQuote(event.assetId, event.date), final = exactQuote(event.assetId, data.asOf);
      return start && start.value > 0 && final && final.value >= 0;
    }).slice().sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
    if (candidates.length < ROUNDS) fail('This data edition does not have twelve investable historical opportunities with verified final prices.');
    if (candidates.length > 2000) fail('This arcade edition exceeds the supported opportunity count.');

    function follows(previous, next) {
      return candidates[next].date > candidates[previous].date && exactQuote(candidates[previous].assetId, candidates[next].date) !== null;
    }
    // A path is feasible only when the position bought at one gate can be
    // liquidated at the exact next gate's quote. Missing data is never a fill.
    const lengths = new Uint16Array(candidates.length);
    for (let i = candidates.length - 1; i >= 0; i--) {
      lengths[i] = 1;
      for (let j = i + 1; j < candidates.length; j++) {
        if (lengths[j] + 1 > lengths[i] && follows(i, j)) lengths[i] = Math.min(ROUNDS, lengths[j] + 1);
        if (lengths[i] === ROUNDS) break;
      }
    }
    if (!Array.from(lengths).some(length => length >= ROUNDS)) fail('Twelve chronological rounds cannot be linked with verified liquidation prices in this data edition.');
    const random = randomGenerator(datasetId + '|' + config.mode + '|' + config.day);
    const startTime = Date.parse(candidates[0].date + 'T00:00:00Z');
    const endTime = Date.parse(candidates[candidates.length - 1].date + 'T00:00:00Z');
    const selected = [];
    let previous = -1;
    for (let round = 0; round < ROUNDS; round++) {
      const remaining = ROUNDS - round;
      const target = startTime + (endTime - startTime) * round / (ROUNDS - 1);
      const feasible = [];
      for (let i = previous + 1; i < candidates.length; i++) {
        if (lengths[i] < remaining || (previous >= 0 && !follows(previous, i))) continue;
        feasible.push({index: i, distance: Math.abs(Date.parse(candidates[i].date + 'T00:00:00Z') - target)});
      }
      feasible.sort((a, b) => a.distance - b.distance || a.index - b.index);
      if (!feasible.length) fail('The historical round sequence has no valid continuation.');
      const choice = config.mode === 'daily' ? Math.floor(random() * Math.min(4, feasible.length)) : 0;
      previous = feasible[choice].index;
      selected.push(candidates[previous]);
    }
    const editionId = 'arcade-v1-' + config.mode + '-' + (config.day || 'fixed') + '-' + hash([VERSION, datasetId, config.mode, config.day, selected.map(event => event.id)]);
    const subset = {
      schemaVersion: data.schemaVersion || 1,
      id: (data.id || 'innovation-history') + ':arcade',
      gameVersion: editionId,
      asOf: data.asOf,
      benchmarkAssetId: data.benchmarkAssetId || null,
      assets: data.assets,
      opportunities: selected
    };
    // Validate the actual accounting dataset, not just the selection metadata.
    HistoricalGame.createGame(subset);
    const prepared = {config, datasetId, editionId, subset, selected};
    if (editions.size >= 64) editions.delete(editions.keys().next().value);
    editions.set(key, prepared);
    return prepared;
  }

  function initial(prepared) {
    const state = HistoricalGame.createGame(prepared.subset);
    return {
      schemaVersion: VERSION, mode: prepared.config.mode, day: prepared.config.day,
      datasetId: prepared.datasetId, editionId: prepared.editionId,
      round: 0, rounds: ROUNDS, status: state.status, choices: [], state, lastResult: null
    };
  }

  function step(prepared, run, fraction) {
    if (!validFraction(fraction)) fail('Choose an allocation of 0%, 25%, 50% or 100%.');
    if (run.status !== 'active') fail('This run has ended. Start a new run to make another decision.');
    const book = HistoricalGame.portfolio(prepared.subset, run.state);
    const card = HistoricalGame.currentDecision(prepared.subset, run.state);
    if (!card || !card.canInvest) fail('This round has no verified investment quote.');
    const sells = book.positions.filter(position => position.value > 0).map(position => {
      if (!position.canSell || position.quoteDate !== run.state.date) fail('The previous holding has no exact liquidation quote on this decision date.');
      return {assetId: position.assetId, amount: position.value};
    });
    const amount = book.value * fraction;
    const state = HistoricalGame.decide(prepared.subset, run.state, {amount, sells});
    const after = HistoricalGame.portfolio(prepared.subset, state);
    return {
      schemaVersion: VERSION, mode: run.mode, day: run.day, datasetId: run.datasetId,
      editionId: run.editionId, round: state.index, rounds: ROUNDS, status: state.status,
      choices: run.choices.concat([fraction]), state,
      lastResult: {
        before: book.value, after: after.value, change: after.value / book.value - 1,
        from: card.date, to: state.date, company: card.firm.name, assetId: card.assetId,
        title: card.title, allocation: fraction, invested: amount, cashHeld: book.value - amount
      }
    };
  }

  function replay(data, input) {
    if (!object(input) || !Array.isArray(input.choices) || input.choices.length > ROUNDS) fail('A replay must contain at most twelve allocation choices.');
    const prepared = prepare(data, input);
    let run = initial(prepared);
    input.choices.forEach(fraction => { run = step(prepared, run, fraction); });
    return run;
  }

  function envelope(run) {
    if (!object(run) || run.schemaVersion !== VERSION || !Array.isArray(run.choices) || run.choices.length > ROUNDS || run.choices.some(fraction => !validFraction(fraction))) fail('The saved arcade run has invalid choices or unsupported rules.');
    const config = settings(run);
    return {schemaVersion: VERSION, mode: config.mode, day: config.day, datasetId: run.datasetId, editionId: run.editionId, choices: run.choices.slice()};
  }

  function canonical(data, run) {
    const saved = envelope(run), prepared = prepare(data, saved);
    if (saved.datasetId !== prepared.datasetId || saved.editionId !== prepared.editionId) fail('This run belongs to a different historical data edition or daily challenge.');
    return {prepared, run: replay(data, saved)};
  }

  function create(data, options) { return initial(prepare(data, options)); }

  function current(data, input) {
    const {prepared, run} = canonical(data, input);
    if (run.status !== 'active') return null;
    const card = HistoricalGame.currentDecision(prepared.subset, run.state);
    const book = HistoricalGame.portfolio(prepared.subset, run.state);
    const event = prepared.selected[run.round], sources = [];
    const urls = (event.sourceUrls || []).concat([
      card.decision.valuation && card.decision.valuation.sourceUrl,
      card.decision.investment && card.decision.investment.sourceUrl
    ]).filter(value => typeof value === 'string' && /^https:\/\//i.test(value));
    urls.forEach(url => { if (!sources.some(source => source.url === url)) sources.push({url, label: 'Historical source or dated filing'}); });
    return Object.assign({}, card, {capital: book.value, round: run.round + 1, rounds: ROUNDS, sources});
  }

  function choose(data, input, fraction) {
    const {prepared, run} = canonical(data, input);
    return step(prepared, run, fraction);
  }

  function portfolio(data, input) {
    const {prepared, run} = canonical(data, input);
    return HistoricalGame.portfolio(prepared.subset, run.state);
  }

  function serialize(run) { return JSON.stringify(envelope(run)); }

  function restore(data, value) {
    if (typeof value !== 'string' || value.length > 65536) fail('The saved arcade run must be a bounded JSON string.');
    let saved;
    try { saved = JSON.parse(value); } catch (_) { fail('The saved arcade run is not valid JSON.'); }
    return canonical(data, saved).run;
  }

  function score(data, input) {
    const {prepared, run} = canonical(data, input);
    const result = HistoricalGame.score(prepared.subset, run.state);
    const saved = envelope(run);
    return {
      schemaVersion: VERSION, mode: run.mode, day: run.day, datasetId: run.datasetId,
      editionId: run.editionId, replayId: 'arcade-' + hash(saved), initialCapital: 100,
      endValue: result.endValue, change: result.change, startDate: result.startDate,
      endDate: result.endDate, status: run.status, complete: result.complete,
      comparable: result.comparable, round: run.round, rounds: ROUNDS,
      decisions: run.choices.length, investments: run.choices.filter(value => value > 0).length,
      benchmarkValue: result.benchmarkValue, benchmark: result.benchmark,
      warnings: result.warnings, replay: saved, disclosure: DISCLOSURE
    };
  }

  function selection(data, options) {
    const prepared = prepare(data, options);
    return {
      mode: prepared.config.mode, day: prepared.config.day, datasetId: prepared.datasetId,
      editionId: prepared.editionId, rounds: ROUNDS,
      ids: prepared.selected.map(event => event.id), dates: prepared.selected.map(event => event.date)
    };
  }

  return Object.freeze({VERSION, ROUNDS, FRACTIONS, DISCLOSURE, create, current, choose, portfolio, score, serialize, restore, replay, selection});
});
