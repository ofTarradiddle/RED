'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const all = selector => Array.from(document.querySelectorAll(selector));
  if (!$('play-start')) return;
  const engine = () => window.InnovationArcade;
  const prefix = 'hetzerk-redi-play-v1:';
  const money = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 2});
  const compact = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1});
  const capitalFormat = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2});
  const percent = new Intl.NumberFormat('en-US', {style: 'percent', maximumFractionDigits: 1, signDisplay: 'exceptZero'});
  const dateFormat = new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'});
  const ns = 'http://www.w3.org/2000/svg';
  const storage = {
    get(key) { try { return localStorage.getItem(prefix + key); } catch (_) { return null; } },
    set(key, value) { try { localStorage.setItem(prefix + key, value); return true; } catch (_) { return false; } }
  };
  const utcDay = () => new Date().toISOString().slice(0, 10);
  const queryMode = new URL(location.href).searchParams.get('mode');
  let mode = ['classic', 'daily'].includes(queryMode) ? queryMode : storage.get('mode') === 'daily' ? 'daily' : 'classic';
  let data = null, run = null, preparedRun = null, card = null, pendingReveal = false, busy = false, revealTimer = null;
  let paused = matchMedia('(prefers-reduced-motion: reduce)').matches || storage.get('motion') === 'paused';
  let storageWarningShown = false, pendingStartMode = null;

  function text(id, value) { const node = $(id); if (node) node.textContent = value; }
  function capital(id, value) {
    const target = $(id);
    target.textContent = value >= 10000 ? capitalFormat.format(value) : money.format(value);
    target.title = money.format(value);
    target.setAttribute('aria-label', money.format(value));
  }
  function date(value) {
    const time = new Date(String(value) + 'T00:00:00Z');
    return Number.isFinite(time.getTime()) ? dateFormat.format(time) : 'Date unavailable';
  }
  function plain(value) {
    if (typeof value === 'string') return value;
    if (value && typeof value === 'object') return typeof value.text === 'string' ? value.text : typeof value.summary === 'string' ? value.summary : '';
    return '';
  }
  function short(value, length = 188) {
    const copy = plain(value).trim();
    if (copy.length <= length) return copy;
    const sentence = copy.slice(0, length).lastIndexOf('. ');
    if (sentence > 70) return copy.slice(0, sentence + 1);
    return copy.slice(0, length).replace(/\s+\S*$/, '') + '…';
  }
  function node(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  }
  function error(message) { text('play-error', message || ''); $('play-error').hidden = !message; }
  function config(selectedMode = mode) { return selectedMode === 'daily' ? {mode: 'daily', day: utcDay()} : {mode: 'classic'}; }
  function saveKey(subject) { return 'run:' + subject.editionId; }
  function activeEdition() { return run || preparedRun; }
  function safeSave() {
    if (!run) return;
    const envelope = JSON.stringify({replay: engine().serialize(run), reveal: pendingReveal});
    const saved = storage.set(saveKey(run), envelope);
    if (run.mode === 'daily') {
      if (run.status === 'active' || pendingReveal) storage.set('last-daily-run', envelope);
      else {
        const previous = readSaved(storage.get('last-daily-run'));
        if (previous && previous.run.editionId === run.editionId) storage.set('last-daily-run', 'null');
      }
    }
    if (!saved && !storageWarningShown) {
      storageWarningShown = true;
      error('Your browser cannot save progress right now. You can still finish this run in the open page.');
    }
  }
  function readSaved(value) {
    try {
      const saved = JSON.parse(value || 'null');
      if (!saved || typeof saved.replay !== 'string') return null;
      const restored = engine().restore(data, saved.replay);
      return {run: restored, reveal: Boolean(saved.reveal && restored.lastResult)};
    } catch (_) { return null; }
  }
  function savedRun(subject) {
    const exact = readSaved(storage.get(saveKey(subject)));
    if (exact && exact.run.editionId === subject.editionId && (exact.run.status === 'active' || exact.reveal)) return exact;
    if (subject.mode === 'daily') {
      const older = readSaved(storage.get('last-daily-run'));
      if (older && older.run.mode === 'daily' && (older.run.status === 'active' || older.reveal)) return older;
    }
    return exact && exact.run.editionId === subject.editionId ? exact : null;
  }
  function displayMode() {
    all('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    const selectedDay = run && run.mode === 'daily' ? run.day : preparedRun && preparedRun.mode === 'daily' ? preparedRun.day : utcDay();
    text('play-edition', (mode === 'daily' ? date(selectedDay) + ' · UTC daily' : 'Classic · 12 moments') + (data ? ' · History through ' + data.asOf.slice(0, 4) : ''));
    const url = new URL(location.href);
    url.searchParams.set('mode', mode);
    history.replaceState(null, '', url);
    storage.set('mode', mode);
  }
  function welcome(selectedMode = mode) {
    if (busy) return;
    safeSave();
    mode = selectedMode; run = null; card = null; pendingReveal = false;
    preparedRun = engine().create(data, config());
    displayMode();
    $('play-welcome').hidden = false; $('play-idle').hidden = false;
    $('play-decision').hidden = true; $('play-finish').hidden = true; $('play-reveal').hidden = true; $('play-restart').hidden = true;
    document.querySelector('.play-cabinet').classList.remove('is-running', 'is-resolving');
    $('play-start').disabled = false; text('play-start', mode === 'daily' ? 'Play today’s flight  →' : 'Start with $100  →');
    const saved = savedRun(preparedRun);
    $('play-resume').hidden = !saved;
    text('play-resume', saved && saved.run.day && saved.run.day !== utcDay() ? 'Resume ' + date(saved.run.day) + ' ↗' : saved && saved.run.status !== 'active' && !saved.reveal ? 'Review your last run ↗' : 'Resume your run ↗');
    updateStage(preparedRun, true);
  }
  function begin(force = false) {
    if (!data || busy) return;
    if (!force && savedRun(preparedRun || engine().create(data, config()))) {
      pendingStartMode = mode; $('play-restart-dialog').showModal(); return;
    }
    error(''); run = engine().create(data, config()); pendingReveal = false; displayMode();
    safeSave(); render();
    text('play-live', 'Your run begins with one hundred fictional dollars. Choose how much capital to allocate.');
  }
  function resume() {
    const saved = savedRun(preparedRun);
    if (!saved) { error('That saved run cannot be restored in this data edition. You can start a new run.'); return; }
    run = saved.run; pendingReveal = saved.reveal; error(''); displayMode(); render();
    if (pendingReveal) reveal(false);
  }
  function eraLabel(year) {
    if (year < 1980) return 'THE AGE OF MACHINES';
    if (year < 1990) return 'COMPUTING BECOMES PERSONAL';
    if (year < 2000) return 'THE WORLD CONNECTS';
    if (year < 2010) return 'THE NETWORK BECOMES A MARKET';
    if (year < 2020) return 'SOFTWARE, EVERYWHERE';
    return 'THE INTELLIGENCE FRONTIER';
  }
  function updateStage(subject, idle = false) {
    const book = engine().portfolio(data, subject);
    const current = engine().current(data, subject);
    const value = book.value;
    const shownDate = subject.state.date;
    const year = Number(shownDate.slice(0, 4));
    const sky = $('play-sky'), flyer = $('play-flyer');
    capital('play-capital', value);
    text('play-era-year', shownDate.slice(0, 4));
    text('play-era-name', idle ? 'THE NEXT IDEA IS AHEAD' : eraLabel(year));
    text('play-scene-date', idle ? 'NO TIMER. YOUR CALL.' : date(shownDate).toUpperCase());
    text('play-round-label', idle ? 'THE BEGINNING' : subject.status === 'active' ? 'DECISIONS MADE' : 'THE FLIGHT COMPLETE');
    $('play-round').replaceChildren(document.createTextNode(String(subject.round).padStart(2, '0') + ' '), node('small', '', '/ ' + subject.rounds));
    sky.style.setProperty('--scene-shift', (-subject.round * 10) + 'px');
    const historyPoints = subject.state.history || [{value: 100}];
    const points = historyPoints.map((point, index) => ({
      x: 90 + index / subject.rounds * 810,
      y: 358 - Math.max(-44, Math.min(192, Math.log2(Math.max(point.value, 0.001) / 100) * 28))
    }));
    const last = points[points.length - 1];
    if (idle) {
      flyer.style.removeProperty('--flyer-x'); flyer.style.removeProperty('--flyer-y');
      $('play-flight-path').setAttribute('d', 'M20 356C85 354 143 345 200 335');
    } else {
      flyer.style.setProperty('--flyer-x', (last.x / 10) + '%'); flyer.style.setProperty('--flyer-y', (last.y / 5) + '%');
      $('play-flight-path').setAttribute('d', points.map((point, index) => (index ? 'L' : 'M') + point.x.toFixed(2) + ' ' + point.y.toFixed(2)).join(' '));
    }
    const dots = $('play-path-dots'); dots.replaceChildren();
    if (!idle) points.forEach(point => {
      const dot = document.createElementNS(ns, 'circle');
      dot.setAttribute('cx', point.x); dot.setAttribute('cy', point.y); dot.setAttribute('r', '3'); dot.setAttribute('fill', '#e6ba7e'); dot.setAttribute('opacity', '.75'); dots.append(dot);
    });
    const progress = $('play-progress'), gates = $('play-gates'); progress.replaceChildren(); gates.replaceChildren();
    for (let i = 0; i < subject.rounds; i += 1) {
      const status = i < subject.round ? 'is-complete' : i === subject.round ? 'is-current' : '';
      const step = node('span', status); step.setAttribute('aria-hidden', 'true'); progress.append(step);
      gates.append(node('span', 'play-gate ' + (i < subject.round ? 'is-passed' : i === subject.round ? 'is-current' : '')));
    }
    progress.setAttribute('aria-label', subject.round + ' of ' + subject.rounds + ' decisions completed');
  }
  function decisionCard(subject) {
    if (pendingReveal && subject.choices.length) {
      const previous = engine().replay(data, {...config(subject.mode), day: subject.day, choices: subject.choices.slice(0, -1)});
      return engine().current(data, previous);
    }
    return engine().current(data, subject);
  }
  function renderCard(current) {
    card = current;
    if (!card) return;
    const brief = card.decision || {}, valuation = brief.valuation, investment = brief.investment;
    text('play-company', card.firm.name.toUpperCase()); text('play-ticker', card.firm.ticker || card.assetId);
    text('play-decision-title', card.title); text('play-decision-date', date(card.date) + ' · The information available then');
    text('play-opportunity', short(brief.marketOpportunity || brief.investmentThesis) || 'A new idea meets an uncertain market. Weigh its possible adoption against competition, execution and the price of owning the company.');
    const hasValuation = Number.isFinite(valuation && valuation.pe), hasRD = Number.isFinite(investment && investment.rd);
    text('play-valuation', hasValuation ? valuation.pe.toFixed(1) + '×' : 'Not verified for this date');
    text('play-rd', hasRD ? compact.format(investment.rd) : 'Not verified for this date');
    $('play-valuation').classList.toggle('is-unavailable', !hasValuation); $('play-rd').classList.toggle('is-unavailable', !hasRD);
    const capital = pendingReveal && run.lastResult ? run.lastResult.before : engine().portfolio(data, run).value;
    text('play-available', money.format(capital));
    all('[data-fraction]').forEach(button => {
      button.disabled = busy || pendingReveal || !card.canInvest;
      button.classList.toggle('is-selected', pendingReveal && Number(button.dataset.fraction) === run.lastResult.allocation);
      const fraction = Number(button.dataset.fraction);
      button.setAttribute('aria-label', fraction === 0 ? 'Pass: hold all ' + money.format(capital) + ' in cash until the next round' : 'Invest ' + (fraction * 100) + '% of capital, ' + money.format(capital * fraction) + ', in ' + card.firm.name);
    });
    text('play-choice-note', pendingReveal ? 'The decision is made. Continue above to the next moment.' : 'Each round rebalances. Uninvested capital stays in cash.');
  }
  function render() {
    if (!run) return;
    document.querySelector('.play-cabinet').classList.add('is-running');
    document.querySelector('.play-cabinet').classList.toggle('is-resolving', pendingReveal);
    $('play-welcome').hidden = true; $('play-idle').hidden = true; $('play-restart').hidden = false;
    const finished = run.status !== 'active' && !pendingReveal;
    $('play-finish').hidden = !finished; $('play-decision').hidden = finished;
    if (!pendingReveal) $('play-reveal').hidden = true;
    updateStage(run);
    if (finished) finish(); else renderCard(decisionCard(run));
  }
  function choose(fraction) {
    if (!run || busy || pendingReveal || run.status !== 'active') return;
    busy = true; error('');
    try {
      run = engine().choose(data, run, fraction); pendingReveal = true;
      safeSave(); render(); $('play-sky').classList.add('is-flying');
      const duration = paused ? 0 : 730;
      revealTimer = setTimeout(() => {
        $('play-sky').classList.remove('is-flying'); busy = false; revealTimer = null; reveal(true);
      }, duration);
    } catch (failure) { busy = false; error(failure.message); render(); }
  }
  function reveal(announce) {
    if (!run || !run.lastResult) return;
    const result = run.lastResult;
    text('play-reveal-date', date(result.from) + ' → ' + date(result.to));
    text('play-reveal-title', result.change < -0.05 ? 'Conviction met reality.' : result.change > 0.05 ? 'The idea took flight.' : 'The years moved.');
    capital('play-reveal-capital', result.after);
    text('play-reveal-change', percent.format(result.change) + ' this round');
    $('play-reveal-change').classList.toggle('is-negative', result.change < 0);
    text('play-reveal-allocation', result.allocation === 0 ? 'You kept ' + money.format(result.before) + ' in cash.' : (result.allocation * 100) + '% in ' + result.company + ' · ' + ((1 - result.allocation) * 100) + '% in cash');
    text('play-continue', run.status === 'active' ? 'Next idea  →' : 'See your flight  →');
    $('play-reveal').hidden = false;
    if (announce) {
      text('play-live', 'Round ' + run.round + ' complete. Capital ' + money.format(result.after) + ', ' + percent.format(result.change) + ' this round. Continue when you are ready.');
      $('play-continue').focus({preventScroll: true});
    }
  }
  function advance() {
    if (!pendingReveal || busy) return;
    pendingReveal = false; safeSave(); render();
    if (run.status === 'active') {
      text('play-live', 'Round ' + (run.round + 1) + '. ' + card.firm.name + '. ' + card.title + '. ' + date(card.date));
      $('play-decision-title').setAttribute('tabindex', '-1'); $('play-decision-title').focus({preventScroll: true});
    } else { $('play-finish-title').setAttribute('tabindex', '-1'); $('play-finish-title').focus({preventScroll: true}); }
  }
  function finish() {
    const result = engine().score(data, run);
    capital('play-final-value', result.endValue); text('play-final-change', percent.format(result.change));
    text('play-finish-summary', 'Your $100 became ' + money.format(result.endValue) + ' across ' + run.round + ' decisions. A record of this route—not a prediction of the next.');
    $('play-score-form').hidden = !result.complete || !result.comparable;
    text('play-score-status', result.complete && result.comparable ? 'Your result is ready to save on this device.' : 'This run is not eligible for a completed-game ranking.');
  }
  function appendBriefPart(parent, title, value) {
    const copy = plain(value);
    if (!copy) return;
    parent.append(node('h3', '', title), node('p', '', copy));
  }
  function brief() {
    if (!card) return;
    const decision = card.decision || {}, copy = $('play-brief-copy'), sources = $('play-brief-sources');
    text('play-brief-heading', card.title); text('play-brief-date', card.firm.name + ' · Decision date ' + date(card.date) + ' · Reconstructed brief');
    copy.replaceChildren(); sources.replaceChildren();
    appendBriefPart(copy, 'The opportunity', decision.marketOpportunity);
    appendBriefPart(copy, 'The company’s investment', decision.investmentThesis || decision.investment);
    appendBriefPart(copy, 'The risk', decision.risks);
    const investment = decision.investment, valuation = decision.valuation;
    if (investment && typeof investment === 'object') {
      const figures = [];
      if (Number.isFinite(investment.revenue)) figures.push('Annual revenue: ' + compact.format(investment.revenue) + '.');
      if (Number.isFinite(investment.rd)) figures.push('Annual R&D: ' + compact.format(investment.rd) + '.');
      if (Number.isFinite(investment.rdToSales)) figures.push('R&D / revenue: ' + (investment.rdToSales * 100).toFixed(1) + '%.');
      if (investment.fiscalPeriodEnd) figures.push('Fiscal year ended ' + date(investment.fiscalPeriodEnd) + '.');
      if (investment.availableAt) figures.push('Filing available ' + date(investment.availableAt) + '.');
      figures.push('Company-wide figures, not spending on this invention.');
      appendBriefPart(copy, 'Dated financial evidence', figures.join(' '));
    } else appendBriefPart(copy, 'Dated financial evidence', 'Verified financial figures are unavailable for this decision date. Current ratios and estimates are not substituted.');
    if (valuation && Number.isFinite(valuation.pe)) appendBriefPart(copy, 'What the valuation means', 'Price / filed annual EPS: ' + valuation.pe.toFixed(1) + '×. This uses the latest available positive full-year EPS; it is not forward P/E or necessarily a trailing-twelve-month ratio.');
    sources.append(node('h3', '', 'Sources behind the historical record'));
    const list = node('ul');
    const candidates = [...(Array.isArray(card.sources) ? card.sources : []), ...(investment && investment.sourceUrl ? [{url: investment.sourceUrl, label: 'Dated company filing'}] : []), ...(valuation && valuation.sourceUrl ? [{url: valuation.sourceUrl, label: 'Valuation evidence'}] : [])];
    const seen = new Set();
    candidates.forEach(item => {
      try {
        const href = typeof item === 'string' ? item : item.url;
        const url = new URL(href);
        if (url.protocol !== 'https:' || seen.has(url.href)) return;
        seen.add(url.href); const li = node('li'), link = node('a', '', (item.label || url.hostname.replace(/^www\./, '')) + ' ↗');
        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; li.append(link); list.append(li);
      } catch (_) {}
    });
    if (list.children.length) sources.append(list);
    const atlasLink = node('a', '', 'Explore this event in the Atlas ↗');
    const dataURL = new URL($('play-data-link').href); atlasLink.href = new URL('./', dataURL).href + '#innovation=' + encodeURIComponent(card.id);
    sources.append(atlasLink, node('p', 'play-dialog-footnote', 'Historical sources may be retrospective. The decision date controls the financial information presented in this game. Following source links can reveal subsequent outcomes.'));
    $('play-brief-dialog').showModal();
  }
  function records() {
    try { const items = JSON.parse(storage.get('scores') || '[]'); return Array.isArray(items) ? items.slice(0, 80) : []; } catch (_) { return []; }
  }
  function verifiedScores() {
    const edition = activeEdition();
    if (!edition) return [];
    return records().flatMap(record => {
      try {
        if (!record || record.editionId !== edition.editionId || typeof record.replay !== 'string') return [];
        const restored = engine().restore(data, record.replay), result = engine().score(data, restored);
        if (!result.complete || !result.comparable || result.editionId !== edition.editionId || result.mode !== mode || result.day !== edition.day) return [];
        return [{name: String(record.name || 'You').slice(0, 20), savedAt: record.savedAt, result}];
      } catch (_) { return []; }
    }).sort((a, b) => b.result.endValue - a.result.endValue);
  }
  function scores() {
    if (!data) return;
    const edition = activeEdition();
    text('play-scores-edition', (mode === 'daily' ? 'Daily · ' + date(edition.day) + ' UTC' : 'Classic route') + ' · History through ' + date(data.asOf));
    const list = $('play-scores-list'); list.replaceChildren();
    const entries = verifiedScores();
    if (!entries.length) list.append(node('li', 'play-score-empty', 'The record is open. Complete a flight and make the first entry in this edition.'));
    entries.slice(0, 12).forEach(entry => {
      const item = node('li'), player = node('span');
      player.append(node('strong', '', entry.name), node('small', '', entry.result.decisions + ' decisions · ' + percent.format(entry.result.change)));
      const amount = node('span', '', entry.result.endValue >= 10000 ? capitalFormat.format(entry.result.endValue) : money.format(entry.result.endValue));
      amount.title = money.format(entry.result.endValue); amount.setAttribute('aria-label', money.format(entry.result.endValue));
      item.append(player, amount); list.append(item);
    });
    if (!$('play-scores-dialog').open) $('play-scores-dialog').showModal();
  }
  function saveScore(event) {
    event.preventDefault();
    if (!run) return;
    try {
      const result = engine().score(data, run);
      if (!result.complete || !result.comparable) throw new Error('Only completed, comparable flights can be ranked.');
      const name = $('play-name').value.normalize('NFKC').trim().replace(/\s+/g, ' ').slice(0, 20);
      if (!name) throw new Error('Give this run a short name.');
      const entries = records().filter(entry => entry.replayId !== result.replayId || entry.editionId !== result.editionId);
      entries.unshift({name, editionId: result.editionId, replayId: result.replayId, replay: engine().serialize(run), savedAt: new Date().toISOString()});
      const currentBest = entries.filter(entry => entry.editionId === result.editionId).flatMap(entry => {
        try { return [{entry, value: engine().score(data, engine().restore(data, entry.replay)).endValue}]; } catch (_) { return []; }
      }).sort((a, b) => b.value - a.value).slice(0, 20).map(item => item.entry);
      const retained = currentBest.concat(entries.filter(entry => entry.editionId !== result.editionId).slice(0, 60));
      if (!storage.set('scores', JSON.stringify(retained))) throw new Error('This browser could not save the score. Your completed result is still on this page.');
      text('play-score-status', 'Saved on this device. Your decisions were replayed to verify the result.');
    } catch (failure) { text('play-score-status', failure.message); }
  }
  function applyMotion() {
    document.body.classList.toggle('play-motion-paused', paused);
    document.body.classList.toggle('ia-motion-paused', paused);
    $('play-motion').setAttribute('aria-pressed', String(paused));
    $('play-motion').setAttribute('aria-label', paused ? 'Resume decorative motion' : 'Pause decorative motion');
    storage.set('motion', paused ? 'paused' : 'playing');
    document.dispatchEvent(new Event('hetzerk:motion-change'));
  }
  all('[data-fraction]').forEach(button => button.addEventListener('click', () => choose(Number(button.dataset.fraction))));
  all('[data-mode]').forEach(button => button.addEventListener('click', () => {
    if (!data || busy || button.dataset.mode === mode) return;
    error(''); welcome(button.dataset.mode);
  }));
  all('[data-open-scores]').forEach(button => button.addEventListener('click', scores));
  all('[data-close-dialog]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  all('.play-dialog').forEach(dialog => dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }));
  $('play-start').addEventListener('click', () => begin());
  $('play-resume').addEventListener('click', resume);
  $('play-continue').addEventListener('click', advance);
  $('play-more').addEventListener('click', brief);
  $('play-rules-open').addEventListener('click', () => $('play-rules-dialog').showModal());
  $('play-score-form').addEventListener('submit', saveScore);
  $('play-restart').addEventListener('click', () => { if (!busy) { pendingStartMode = mode; $('play-restart-dialog').showModal(); } });
  $('play-again').addEventListener('click', () => begin(true));
  $('play-restart-confirm').addEventListener('click', () => { $('play-restart-dialog').close(); if (pendingStartMode) mode = pendingStartMode; pendingStartMode = null; begin(true); });
  $('play-motion').addEventListener('click', () => { paused = !paused; applyMotion(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) safeSave(); });
  applyMotion();
  async function load() {
    try {
      if (!engine()) throw new Error('The game engine did not load. Refresh this page to try again.');
      const response = await fetch($('play-data-link').href, {cache: 'no-cache', credentials: 'same-origin'});
      if (!response.ok) throw new Error('The historical dataset is unavailable (HTTP ' + response.status + ').');
      data = await response.json();
      if (!data || !Array.isArray(data.assets) || !Array.isArray(data.opportunities)) throw new Error('The published historical dataset has an unsupported format.');
      welcome();
      if (location.hash === '#resume' && savedRun(preparedRun)) resume();
    } catch (failure) {
      error(failure.message + ' No invented price history has been substituted.');
      text('play-start', 'History unavailable'); $('play-start').disabled = true; text('play-edition', 'Waiting for published history');
    }
  }
  load();
})();
