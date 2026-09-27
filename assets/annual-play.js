/* Annual portfolio UI. Accounting and point-in-time filtering live in AnnualPortfolio. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const engine = window.AnnualPortfolio;
  const STORAGE = 'hetzerk.annual-portfolio.v1';
  const SCORE_STORAGE = 'hetzerk.annual-records.v1';
  const PAGE_SIZE = 12;
  let data, run, decision, draft = {}, reveal = false, page = 0, busy = false, storageOK = true;
  let currentCompanies = [], companyMap = new Map(), filterQuery = '', sector = '', sort = 'name', availableOnly = false;
  let outcomeCompanies = [], outcomePage = 0, outcomeQuery = '';
  let investedPage = 0, investedQuery = '';
  const moneyFormat = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2});
  const compactMoney = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2});
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const money = value => finite(value) ? moneyFormat.format(value) : 'Unavailable';
  const compact = value => finite(value) ? Math.abs(value) >= 1000000 ? compactMoney.format(value) : money(value) : 'Unavailable';
  const percent = (value, signed = false, digits = 2) => finite(value) ? (signed && value > 0 ? '+' : '') + (value * 100).toFixed(digits) + '%' : 'Unavailable';
  const weightText = value => Number((value * 100).toFixed(4)).toLocaleString('en-US', {maximumFractionDigits: 4});
  const signedMoney = value => finite(value) ? (value > 0 ? '+' : '') + money(value) : 'Unavailable';
  const dateText = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? new Date(value + 'T12:00:00Z').toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'}) : String(value || 'Unavailable');
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }
  function link(url, label) {
    try {
      if (typeof url !== 'string' || !url.trim()) throw new Error('Missing source URL');
      const parsed = new URL(url, location.href);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Unsupported source URL');
      const node = element('a', '', label);
      node.href = parsed.href; node.target = '_blank'; node.rel = 'noopener noreferrer';
      return node;
    } catch (_) { return element('span', '', label + ' — source link unavailable'); }
  }
  function announce(text) { $('ap-live').textContent = text; }
  function error(message) { $('ap-error').textContent = message; $('ap-error').hidden = !message; }
  function save() {
    if (!run) return;
    try {
      localStorage.setItem(STORAGE, JSON.stringify({version: 1, run: engine.serialize(run), draft, reveal}));
      storageOK = true;
    } catch (_) { storageOK = false; }
    $('ap-save-status').textContent = storageOK ? 'Saved on this device' : 'Storage unavailable · keep this tab open';
  }
  function defaultDraft() {
    const next = {};
    currentCompanies.forEach(company => {
      if (company.canInvest && finite(company.currentWeight) && company.currentWeight > 0) next[company.id] = company.currentWeight;
    });
    return next;
  }
  function refreshDecision() {
    decision = engine.current(data, run);
    currentCompanies = decision ? decision.companies : [];
    companyMap = new Map(currentCompanies.map(company => [company.id, company]));
  }
  function safeDraft(value) {
    const next = {};
    if (value && typeof value === 'object' && !Array.isArray(value)) Object.entries(value).forEach(([id, fraction]) => {
      if (companyMap.get(id)?.canInvest && finite(fraction) && fraction >= 0 && fraction <= 1) next[id] = fraction;
    });
    return next;
  }
  function setDesk(panel) {
    document.querySelector('.ap-desk').dataset.mobilePanel = panel;
    $('ap-universe-tab').setAttribute('aria-selected', String(panel === 'universe'));
    $('ap-basket-tab').setAttribute('aria-selected', String(panel === 'basket'));
  }
  function updateSectors() {
    const select = $('ap-sector'), sectors = [...new Set(currentCompanies.map(company => company.sector).filter(Boolean))].sort();
    select.replaceChildren(new Option('All sectors', ''));
    sectors.forEach(value => select.add(new Option(value, value)));
    select.closest('label').hidden = sectors.length === 0;
    select.disabled = sectors.length === 0;
    if (!sectors.includes(sector)) sector = '';
    select.value = sector;
  }
  function filteredCompanies() {
    const query = filterQuery.trim().toLowerCase();
    return currentCompanies.filter(company => (!query || [company.name, company.ticker, company.id].some(value => String(value || '').toLowerCase().includes(query))) && (!sector || company.sector === sector) && (!availableOnly || company.canInvest)).sort((a, b) => {
      if (sort === 'allocated') { const difference = (draft[b.id] || 0) - (draft[a.id] || 0); if (difference) return difference; }
      if (['rd', 'rd_intensity', 'revenue'].includes(sort)) {
        const metric = company => {
          const facts = company.financials?.metrics;
          if (sort === 'rd_intensity') {
            const rdSource = company.financials?.metricSources?.rd, revenueSource = company.financials?.metricSources?.revenue;
            const matchedPeriod = rdSource?.periodStart && rdSource.periodStart === revenueSource?.periodStart && rdSource.fiscalPeriodEnd === revenueSource.fiscalPeriodEnd;
            return matchedPeriod && finite(facts?.rd) && finite(facts?.revenue) && facts.revenue > 0 ? facts.rd / facts.revenue : null;
          }
          return finite(facts?.[sort]) ? facts[sort] : null;
        };
        const first = metric(a), second = metric(b);
        if (first !== null && second !== null && first !== second) return second - first;
        if (first !== null && second === null) return -1;
        if (first === null && second !== null) return 1;
      }
      return String(sort === 'ticker' ? a.ticker || a.id : a.name).localeCompare(String(sort === 'ticker' ? b.ticker || b.id : b.name));
    });
  }
  function renderCompanies() {
    const companies = filteredCompanies(), pages = Math.max(1, Math.ceil(companies.length / PAGE_SIZE));
    page = Math.max(0, Math.min(page, pages - 1));
    $('ap-company-list').replaceChildren();
    $('ap-company-count').textContent = companies.length.toLocaleString() + (companies.length === 1 ? ' COMPANY' : ' COMPANIES');
    $('ap-page-label').textContent = companies.length ? (page * PAGE_SIZE + 1) + '–' + Math.min((page + 1) * PAGE_SIZE, companies.length) + ' of ' + companies.length : 'No matching companies';
    $('ap-page-prev').disabled = page === 0; $('ap-page-next').disabled = page >= pages - 1;
    if (!companies.length) $('ap-company-list').append(element('p', 'ap-list-empty', 'No companies match these filters. Try a different name or sector.'));
    companies.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).forEach(company => {
      const row = element('article', 'ap-company' + (Object.hasOwn(draft, company.id) ? ' is-allocated' : ''));
      row.dataset.company = company.id;
      const icon = element('span', 'ap-company-icon', String(company.ticker || company.name).slice(0, 2)); icon.setAttribute('aria-hidden', 'true');
      const title = element('div', 'ap-company-title');
      title.append(element('h4', '', company.name));
      const meta = element('p'); meta.append(element('span', 'ap-ticker', company.ticker || company.id));
      if (company.sector) meta.append(element('span', '', company.sector));
      title.append(meta);
      const financials = company.financials, rd = financials?.metrics?.rd;
      if (finite(rd)) title.append(element('span', 'ap-filed-hint', 'As filed · R&D ' + compact(rd) + ' · FY ' + String(financials.metricSources?.rd?.fiscalPeriodEnd || financials.fiscalPeriodEnd).slice(0, 4)));
      else title.append(element('span', 'ap-filed-hint' + (!financials ? ' is-missing' : ''), financials ? 'Dated company file available' : 'Dated filing evidence unavailable'));
      if (!company.canInvest) title.append(element('span', 'ap-unavailable', 'Incomplete price coverage · allocation unavailable'));
      const actions = element('div', 'ap-company-actions'), brief = element('button', 'ap-brief-button', 'File ↗');
      brief.type = 'button'; brief.setAttribute('aria-label', 'Read ' + company.name + ' company file'); brief.addEventListener('click', () => openBrief(company.id));
      const selected = Object.hasOwn(draft, company.id), add = element('button', 'ap-add' + (selected ? ' is-allocated' : ''), selected ? weightText(draft[company.id]) + '%' : '+');
      add.type = 'button'; add.disabled = !company.canInvest;
      add.setAttribute('aria-label', selected ? 'Edit ' + company.name + ' allocation' : 'Add ' + company.name + ' to your allocation');
      add.addEventListener('click', () => addCompany(company.id));
      actions.append(brief, add); row.append(icon, title, actions); $('ap-company-list').append(row);
    });
  }
  function totalWeight() { return Object.values(draft).reduce((sum, value) => sum + (finite(value) ? value : 0), 0); }
  function updateAllocation() {
    const total = totalWeight(), capital = decision?.capital || 0, entries = Object.entries(draft);
    $('ap-invested').textContent = weightText(total) + '%';
    $('ap-cash').textContent = weightText(Math.max(0, 1 - total)) + '%';
    $('ap-basket-tab-count').textContent = String(entries.length);
    $('ap-basket-empty').hidden = entries.length > 0;
    $('ap-equal').disabled = !entries.length; $('ap-clear').disabled = !entries.length;
    const available = currentCompanies.filter(company => company.canInvest);
    $('ap-equal-universe').disabled = busy || !available.length;
    const entireUniverse = available.length > 0 && entries.length === available.length && available.every(company => finite(draft[company.id]) && Math.abs(draft[company.id] - 1 / available.length) < 1e-10);
    $('ap-universe-allocation-status').textContent = entireUniverse ? '100% across all ' + available.length + ' available companies at ' + weightText(1 / available.length) + '% each. ' + (currentCompanies.length - available.length) + ' companies have incomplete price coverage.' : 'Use every company with verified price coverage in the full annual roster.';
    const validation = decision ? engine.validateAllocation(data, run, draft) : {valid: false, errors: []};
    const invalid = total > 1 + 1e-9;
    const invalidField = document.querySelector('.ap-weight-input input[aria-invalid="true"]');
    const message = invalid ? 'Reduce allocations by ' + weightText(total - 1) + '% to stay within 100%.' : !validation.valid && validation.errors?.length ? String(validation.errors[0].message || validation.errors[0]) : '';
    $('ap-allocation-error').textContent = invalidField ? 'Each company allocation must be between 0% and 100%.' : message;
    $('ap-commit').disabled = busy || !decision || !validation.valid || !!invalidField;
    $('ap-commit').firstChild.textContent = entries.some(([, weight]) => weight > 0) ? 'Lock & run the year ' : 'Hold cash & run the year ';
    $('ap-allocation-bar').replaceChildren();
    entries.forEach(([id, weight]) => {
      if (weight <= 0) return;
      const segment = element('span'); segment.style.width = (weight * 100 / Math.max(total, 1)) + '%';
      segment.title = (companyMap.get(id)?.name || id) + ': ' + weightText(weight) + '%';
      $('ap-allocation-bar').append(segment);
      const amount = $('ap-amount-' + id); if (amount) amount.textContent = money(capital * weight);
    });
    $('ap-allocation-bar').setAttribute('aria-label', weightText(total) + '% invested; ' + weightText(Math.max(0, 1 - total)) + '% cash');
    document.querySelectorAll('.ap-company').forEach(row => {
      const selected = Object.hasOwn(draft, row.dataset.company), add = row.querySelector('.ap-add');
      row.classList.toggle('is-allocated', selected); add.classList.toggle('is-allocated', selected);
      add.textContent = selected ? weightText(draft[row.dataset.company]) + '%' : '+';
    });
  }
  function renderBasket() {
    $('ap-basket-list').replaceChildren();
    Object.entries(draft).forEach(([id, weight]) => {
      const company = companyMap.get(id); if (!company) return;
      const row = element('div', 'ap-position'), name = element('div', 'ap-position-name');
      name.append(element('strong', '', company.ticker || company.name));
      const amount = element('small', '', money(decision.capital * weight)); amount.id = 'ap-amount-' + id; name.append(amount);
      const wrap = element('label', 'ap-weight-input'), input = element('input');
      input.type = 'number'; input.min = '0'; input.max = '100'; input.step = '0.01'; input.inputMode = 'decimal'; input.value = String(Number((weight * 100).toFixed(6)));
      input.id = 'ap-weight-' + id; input.setAttribute('aria-label', company.name + ' allocation percentage');
      input.addEventListener('input', () => {
        const number = Number(input.value);
        if (!finite(number) || number < 0 || number > 100) {
          input.setAttribute('aria-invalid', 'true'); $('ap-allocation-error').textContent = 'Each company allocation must be between 0% and 100%.'; $('ap-commit').disabled = true; return;
        }
        input.removeAttribute('aria-invalid'); draft[id] = number / 100; updateAllocation(); save();
      });
      input.addEventListener('change', () => { if (input.getAttribute('aria-invalid') === 'true') { input.value = weightText(draft[id]); input.removeAttribute('aria-invalid'); updateAllocation(); } });
      wrap.append(input, element('span', '', '%'));
      const remove = element('button', 'ap-remove', '×'); remove.type = 'button'; remove.setAttribute('aria-label', 'Remove ' + company.name);
      remove.addEventListener('click', () => { delete draft[id]; renderBasket(); renderCompanies(); save(); });
      row.append(name, wrap, remove); $('ap-basket-list').append(row);
    });
    updateAllocation();
  }
  function addCompany(id) {
    const company = companyMap.get(id); if (!company?.canInvest || !decision || reveal) return;
    if (!Object.hasOwn(draft, id)) draft[id] = Math.max(0, Math.min(0.1, 1 - totalWeight()));
    renderBasket(); renderCompanies(); save(); setDesk('basket');
    $('ap-weight-' + id)?.focus(); announce(company.name + ' added. Set its share of your portfolio.');
  }
  function benchmarkInfo(book) {
    const benchmark = book?.benchmark;
    return {value: finite(benchmark?.value) ? benchmark.value : finite(book?.benchmarkValue) ? book.benchmarkValue : null, change: finite(benchmark?.change) ? benchmark.change : null, history: benchmark?.path || benchmark?.history || book?.benchmarkHistory || []};
  }
  function renderLedger() {
    const book = engine.portfolio(data, run), benchmark = benchmarkInfo(book), result = reveal ? run.lastResult : null;
    $('ap-stage-label').textContent = result ? 'YEAR COMPLETED' : decision ? 'YOUR DECISION CUTOFF' : 'YOUR RUN, RECORDED';
    $('ap-year').textContent = String(result ? Number(result.year) + 1 : decision?.year || String(run.date || '').slice(0, 4));
    $('ap-cutoff').textContent = result ? dateText(result.to) : decision ? dateText(decision.cutoff) : dateText(run.date);
    const value = finite(book.value) ? book.value : run.initialCapital;
    $('ap-capital').textContent = compact(value); $('ap-capital').title = money(value);
    $('ap-growth').textContent = run.actions.length ? percent(value / run.initialCapital - 1, true) + ' since your start' : 'Fictional starting capital';
    $('ap-benchmark').textContent = benchmark.value !== null ? compact(benchmark.value) : run.actions.length ? 'Unavailable' : '$100.00';
    $('ap-benchmark').title = benchmark.value !== null ? money(benchmark.value) : '';
    $('ap-benchmark-growth').textContent = benchmark.value !== null ? percent(benchmark.value / run.initialCapital - 1, true) + ' · S&P 500 proxy' : 'S&P 500 proxy (SPY)';
    $('ap-round-label').textContent = run.status !== 'active' ? 'THE FULL RECORD' : String(run.actions.length).padStart(2, '0') + ' / ' + String(run.rounds).padStart(2, '0') + ' YEARS COMMITTED';
    $('ap-progress').replaceChildren();
    for (let index = 0; index < run.rounds; index++) { const dot = element('span', index < run.actions.length ? 'is-complete' : index === run.actions.length ? 'is-current' : ''); dot.setAttribute('aria-hidden', 'true'); $('ap-progress').append(dot); }
    $('ap-progress').setAttribute('aria-label', run.actions.length + ' of ' + run.rounds + ' annual allocations completed');
    $('ap-save-status').textContent = storageOK ? 'Saved on this device' : 'Storage unavailable · keep this tab open';
    $('ap-history').hidden = run.actions.length === 0;
    if (run.actions.length) drawHistory(book);
  }
  function svgNode(tag, attributes, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function pathString(points, x, y) { return points.map((point, index) => (index ? 'L' : 'M') + x(point).toFixed(2) + ',' + y(point).toFixed(2)).join(' '); }
  function drawHistory(book) {
    const svg = $('ap-history-chart'), history = book?.history || run.history || [], benchmark = benchmarkInfo(book);
    const player = history.filter(point => finite(point.value) && point.date), comparison = benchmark.history.filter(point => finite(point.value) && point.date);
    svg.replaceChildren();
    if (!player.length) return;
    const width = Math.max(260, Math.round(svg.getBoundingClientRect().width || 900)), height = innerWidth <= 650 ? 205 : 245;
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    const all = player.concat(comparison), start = Date.parse(player[0].date), end = Date.parse(player[player.length - 1].date);
    let low = Math.min(...all.map(point => point.value)), high = Math.max(...all.map(point => point.value));
    const pad = Math.max((high - low) * 0.12, high * 0.035, 1); low = Math.max(0, low - pad); high += pad;
    const margin = {left: 51, right: 13, top: 13, bottom: 26}, plotWidth = width - margin.left - margin.right, plotHeight = height - margin.top - margin.bottom;
    const x = point => margin.left + (Date.parse(point.date) - start) / Math.max(1, end - start) * plotWidth;
    const y = point => margin.top + (high - point.value) / (high - low) * plotHeight;
    for (let index = 0; index < 4; index++) {
      const value = low + (high - low) * index / 3, yy = y({value});
      svg.append(svgNode('line', {x1: margin.left, x2: width - margin.right, y1: yy, y2: yy, class: 'ap-chart-grid'}));
      const label = value >= 1000 ? compactMoney.format(value) : '$' + Math.round(value);
      svg.append(svgNode('text', {x: margin.left - 10, y: yy + 3, 'text-anchor': 'end'}, label));
    }
    if (comparison.length) svg.append(svgNode('path', {d: pathString(comparison, x, y), class: 'ap-chart-benchmark'}));
    svg.append(svgNode('path', {d: pathString(player, x, y), class: 'ap-chart-player'}));
    const last = player[player.length - 1]; svg.append(svgNode('circle', {cx: x(last), cy: y(last), r: 4, class: 'ap-chart-dot'}));
    const dates = width > 550 ? [player[0], player[Math.floor((player.length - 1) / 2)], last] : [player[0], last];
    dates.forEach((point, index) => svg.append(svgNode('text', {x: x(point), y: height - 5, 'text-anchor': index === 0 ? 'start' : index === dates.length - 1 ? 'end' : 'middle'}, dateText(point.date))));
    svg.setAttribute('aria-label', 'From ' + dateText(player[0].date) + ' to ' + dateText(last.date) + ', your portfolio moved from ' + money(player[0].value) + ' to ' + money(last.value) + (benchmark.value !== null ? '. SPY ended at ' + money(benchmark.value) : '. SPY comparison unavailable'));
    document.querySelector('.ap-chart-legend span:last-child').hidden = !comparison.length;
  }
  function resultRows(companies) {
    $('ap-result-rows').replaceChildren();
    companies.slice().sort((a, b) => b.profit - a.profit).forEach(company => {
      const row = element('tr'), nameCell = element('td'), button = element('button', '', company.name || company.id);
      button.type = 'button'; button.addEventListener('click', () => openBrief(company.id));
      nameCell.append(button, element('small', '', company.ticker || company.id)); row.append(nameCell);
      [percent(company.weight, false, 2), percent(company.return, true), signedMoney(company.profit), money(company.endingValue)].forEach((value, index) => {
        const cell = element('td', (index === 1 && company.return < 0 || index === 2 && company.profit < 0) ? 'is-negative' : '', value); row.append(cell);
      });
      $('ap-result-rows').append(row);
    });
    if (!companies.length) { const row = element('tr'), cell = element('td', '', 'The portfolio stayed entirely in cash.'); cell.colSpan = 5; row.append(cell); $('ap-result-rows').append(row); }
  }
  function renderResults() {
    const result = run.lastResult;
    if (!result) return;
    const title = $('ap-results-title'); title.replaceChildren(document.createTextNode(result.partial ? String(Number(result.year) + 1) + ',' : 'The year,'), document.createElement('br'), element('em', '', result.partial ? 'so far.' : 'in perspective.'));
    $('ap-result-dates').textContent = dateText(result.from) + ' — ' + dateText(result.to);
    $('ap-result-capital').textContent = compact(result.after); $('ap-result-capital').title = money(result.after);
    $('ap-result-return').textContent = percent(result.change, true) + ' for the period';
    const benchmarkPath = benchmarkInfo(engine.portfolio(data, run)).history;
    const benchmarkStart = benchmarkPath.find(point => point.date === result.from), benchmarkEnd = benchmarkPath.find(point => point.date === result.to);
    const benchmarkReturn = finite(benchmarkStart?.value) && finite(benchmarkEnd?.value) && benchmarkStart.value > 0 ? benchmarkEnd.value / benchmarkStart.value - 1 : null;
    $('ap-result-benchmark').textContent = percent(benchmarkReturn, true);
    $('ap-result-excess').textContent = benchmarkReturn !== null ? ((result.change - benchmarkReturn) > 0 ? '+' : '') + ((result.change - benchmarkReturn) * 100).toFixed(2) + ' percentage points' : 'Comparison data unavailable';
    const firms = result.companies || [];
    $('ap-result-summary').textContent = firms.length ? firms.length + (firms.length === 1 ? ' company. ' : ' companies. ') + money(result.before) + ' became ' + money(result.after) + '.' : 'You held cash through the period. Your ' + money(result.before) + ' remained available.';
    $('ap-result-cash').textContent = percent(result.cashWeight, false, 1) + ' held in cash';
    $('ap-result-method').textContent = 'Period returns use the observed holding interval, with provider-adjusted distributions and splits. Your P&L reflects your allocation. No fees, taxes or cash interest.';
    resultRows(firms);
    const next = engine.current(data, run), done = !next;
    $('ap-next').firstChild.textContent = done ? 'Start another portfolio ' : 'Rebalance for ' + (Number(next.year) + 1) + ' ';
    $('ap-next-note').textContent = done ? 'Your complete holding record is below. The final period may cover only part of the calendar year.' : 'The next decision uses evidence filed by ' + dateText(next.cutoff) + '. Reallocate your ' + money(next.capital) + ' across the next universe.';
    outcomeCompanies = engine.outcomes(data, run, result.year).companies;
    renderOutcomes();
    $('ap-finish-save').hidden = !done;
    if (done) {
      const score = engine.score(data, run);
      $('ap-final-recap').textContent = score.periods + ' annual decisions. ' + money(score.initialCapital) + ' became ' + money(score.finalValue) + '. ' + (finite(score.benchmarkValue) ? 'SPY ended at ' + money(score.benchmarkValue) + '.' : 'SPY comparison unavailable.');
    }
  }
  function renderOutcomes() {
    const query = outcomeQuery.trim().toLowerCase();
    const firms = outcomeCompanies.filter(company => !query || [company.name, company.ticker, company.id].some(value => String(value || '').toLowerCase().includes(query))).slice().sort((a, b) => {
      if (finite(a.return) && finite(b.return)) return b.return - a.return;
      if (finite(a.return)) return -1; if (finite(b.return)) return 1; return a.name.localeCompare(b.name);
    });
    const pages = Math.max(1, Math.ceil(firms.length / PAGE_SIZE)); outcomePage = Math.max(0, Math.min(outcomePage, pages - 1));
    $('ap-outcome-rows').replaceChildren();
    firms.slice(outcomePage * PAGE_SIZE, (outcomePage + 1) * PAGE_SIZE).forEach(company => {
      const row = element('tr'), name = element('td'), button = element('button', '', company.name);
      button.type = 'button'; button.addEventListener('click', () => openBrief(company.id));
      name.append(button, element('small', '', company.ticker || company.id)); row.append(name, element('td', '', company.sector || 'Unavailable'), element('td', company.return < 0 ? 'is-negative' : '', percent(company.return, true)));
      $('ap-outcome-rows').append(row);
    });
    if (!firms.length) { const row = element('tr'), cell = element('td', '', 'No matching companies.'); cell.colSpan = 3; row.append(cell); $('ap-outcome-rows').append(row); }
    $('ap-outcome-page').textContent = firms.length ? (outcomePage * PAGE_SIZE + 1) + '–' + Math.min((outcomePage + 1) * PAGE_SIZE, firms.length) + ' of ' + firms.length : 'No matches';
    $('ap-outcome-prev').disabled = outcomePage === 0; $('ap-outcome-next').disabled = outcomePage >= pages - 1;
  }
  function miniChart(points) {
    const svg = svgNode('svg', {class: 'ap-mini-chart', viewBox: '0 0 220 48', 'aria-hidden': 'true'});
    const values = points.map(point => finite(point.profit) ? point.profit : finite(point.cumulativeProfit) ? point.cumulativeProfit : finite(point.value) ? point.value : 0);
    if (!values.length) return svg;
    const items = [0, ...values], low = Math.min(0, ...items), high = Math.max(0, ...items), range = high - low || 1;
    const y = value => 42 - (value - low) / range * 36;
    svg.append(svgNode('line', {x1: 0, x2: 220, y1: y(0), y2: y(0)}));
    svg.append(svgNode('path', {d: items.map((value, index) => (index ? 'L' : 'M') + (index / Math.max(1, items.length - 1) * 220).toFixed(1) + ',' + y(value).toFixed(1)).join(' ')}));
    return svg;
  }
  function recordPeriods(record) { return record.periods || record.lots || []; }
  function recordProfit(record) { return finite(record.profit) ? record.profit : finite(record.cumulativeProfit) ? record.cumulativeProfit : recordPeriods(record).reduce((sum, period) => sum + (period.profit || 0), 0); }
  function renderInvestedHistory() {
    const query = investedQuery.trim().toLowerCase(), companies = engine.portfolio(data, run).companies || [];
    $('ap-invested-history').hidden = !companies.length;
    const matching = companies.filter(company => !query || [company.name, company.ticker, company.id].some(value => String(value || '').toLowerCase().includes(query))).slice().sort((a, b) => b.profit - a.profit);
    const pages = Math.max(1, Math.ceil(matching.length / PAGE_SIZE)); investedPage = Math.max(0, Math.min(investedPage, pages - 1));
    const records = matching.slice(investedPage * PAGE_SIZE, (investedPage + 1) * PAGE_SIZE).map(company => engine.companyHistory(data, run, company.id));
    $('ap-invested-cards').replaceChildren();
    records.sort((a, b) => recordProfit(b) - recordProfit(a)).forEach(record => {
      const periods = recordPeriods(record), id = record.id || record.assetId;
      const card = element('article', 'ap-invested-card'), top = element('div', 'ap-invested-card-top'), button = element('button', '', record.name || id);
      button.type = 'button'; button.addEventListener('click', () => openBrief(id));
      top.append(button, element('span', '', record.ticker || id)); card.append(top);
      card.append(element('p', '', periods.length + (periods.length === 1 ? ' invested period' : ' invested periods')), element('strong', '', signedMoney(recordProfit(record))), element('small', '', 'CUMULATIVE CONTRIBUTION / DOLLARS'));
      card.append(miniChart(record.path || []));
      const details = element('details'), summary = element('summary', '', 'See your invested periods'), list = element('ol');
      periods.forEach(period => list.append(element('li', '', String(period.year !== undefined ? Number(period.year) + 1 : String(period.from || '').slice(0, 4)) + ': ' + percent(period.return, true) + ' · ' + signedMoney(period.profit))));
      details.append(summary, list); card.append(details); $('ap-invested-cards').append(card);
    });
    if (!matching.length) $('ap-invested-cards').append(element('p', 'ap-list-empty', 'No invested companies match this search.'));
    $('ap-invested-page').textContent = matching.length ? (investedPage * PAGE_SIZE + 1) + '–' + Math.min((investedPage + 1) * PAGE_SIZE, matching.length) + ' of ' + matching.length + ' invested companies' : 'No matches';
    $('ap-invested-prev').disabled = investedPage === 0; $('ap-invested-next').disabled = investedPage >= pages - 1;
  }
  function render() {
    refreshDecision();
    $('ap-game').hidden = false; $('ap-load-status').hidden = true;
    $('ap-plan').hidden = reveal || !decision; $('ap-results').hidden = !reveal && !!decision;
    if (decision) {
      $('ap-basket-year').textContent = decision.year;
      $('ap-desk-eyebrow').textContent = 'YEAR-END ' + decision.year + ' / BEFORE THE NEXT YEAR UNFOLDS';
      const available = currentCompanies.filter(company => company.canInvest).length;
      $('ap-universe-context').textContent = available + ' / ' + currentCompanies.length + ' companies available. First trade: ' + dateText(decision.executionDate) + '.';
      $('ap-universe-tab-count').textContent = currentCompanies.length;
      $('ap-coverage').textContent = available + ' of ' + currentCompanies.length + ' companies have verifiable price coverage for this investment interval. Missing coverage blocks allocation; missing filings remain explicitly unavailable.';
      updateSectors(); renderCompanies(); renderBasket();
    }
    renderLedger();
    if (reveal || !decision) renderResults();
    renderInvestedHistory();
  }
  function openDialog(dialog) { if (!dialog.open) dialog.showModal(); }
  function closeDialogs() { document.querySelectorAll('.ap-dialog[open]').forEach(dialog => dialog.close()); }
  function knownCompany(id) {
    if (!reveal && companyMap.has(id)) return {...companyMap.get(id), decisionCutoff: decision?.cutoff};
    if (run.actions.length) {
      try {
        for (let index = run.actions.length - 1; index >= 0; index--) {
          if (index !== run.actions.length - 1 && !(run.actions[index].weights[id] > 0)) continue;
          const before = engine.replay(data, run.actions.slice(0, index));
          const previousDecision = engine.current(data, before);
          const company = previousDecision?.companies.find(item => item.id === id);
          if (company) return {...company, decisionCutoff: previousDecision.cutoff};
        }
        return null;
      } catch (_) { return null; }
    }
    return null;
  }
  function formatFact(value, unit) {
    if (!finite(value)) return 'Unavailable';
    if (unit === 'USD/shares' || unit === 'USD / shares') return money(value);
    if (unit === 'ratio') return value.toFixed(2) + '×';
    if (Math.abs(value) >= 1000000) return compactMoney.format(value);
    return money(value);
  }
  function appendCompanyChart(section, points, benchmark, label) {
    const series = (points || []).filter(point => point.date && finite(point.value));
    const comparison = (benchmark || []).filter(point => point.date && finite(point.value));
    if (!series.length) return;
    const width = Math.max(230, Math.min(650, innerWidth - 78)), height = innerWidth <= 650 ? 185 : 210;
    const svg = svgNode('svg', {viewBox: '0 0 ' + width + ' ' + height, class: 'ap-company-chart', role: 'img'});
    const first = series[0], last = series[series.length - 1], start = Date.parse(first.date), end = Date.parse(last.date);
    const values = series.concat(comparison).map(point => point.value);
    const pad = Math.max(2, (Math.max(...values) - Math.min(...values)) * 0.12);
    const low = Math.max(0, Math.min(...values) - pad), high = Math.max(...values) + pad;
    const left = 37, right = width - 8, top = 13, bottom = height - 23;
    const x = point => left + (Date.parse(point.date) - start) / Math.max(1, end - start) * (right - left);
    const y = point => top + (high - point.value) / Math.max(1, high - low) * (bottom - top);
    for (let index = 0; index < 4; index++) {
      const value = low + (high - low) * index / 3, yy = y({value});
      svg.append(svgNode('line', {x1: left, x2: right, y1: yy, y2: yy, class: 'ap-chart-grid'}));
      svg.append(svgNode('text', {x: left - 8, y: yy + 3, 'text-anchor': 'end'}, value >= 10000 ? new Intl.NumberFormat('en-US', {notation: 'compact', maximumFractionDigits: 1}).format(value) : Math.round(value)));
    }
    if (comparison.length) svg.append(svgNode('path', {d: pathString(comparison, x, y), class: 'ap-chart-benchmark'}));
    svg.append(svgNode('path', {d: pathString(series, x, y), class: 'ap-chart-player'}));
    svg.append(svgNode('text', {x: left, y: height - 3, 'text-anchor': 'start'}, String(first.date).slice(0, 7)));
    svg.append(svgNode('text', {x: right, y: height - 3, 'text-anchor': 'end'}, String(last.date).slice(0, 7)));
    svg.setAttribute('aria-label', label + ', growth of 100 from ' + dateText(first.date) + ' to ' + dateText(last.date) + ', ending at ' + last.value.toFixed(2) + '.');
    const focus = svgNode('g'), guide = svgNode('line', {y1: top, y2: bottom, class: 'ap-company-chart-guide'}), dot = svgNode('circle', {r: 3.5, class: 'ap-chart-dot'});
    focus.append(guide, dot); svg.append(focus); section.append(svg);
    const inspection = element('p', 'ap-company-chart-readout'); inspection.setAttribute('role', 'status');
    const slider = element('input', 'ap-company-chart-cursor'); slider.type = 'range'; slider.min = '0'; slider.max = String(series.length - 1); slider.step = '1'; slider.value = slider.max;
    slider.setAttribute('aria-label', 'Inspect observed dates for ' + label);
    function inspect() {
      const point = series[Number(slider.value)], peer = comparison.find(item => item.date === point.date);
      guide.setAttribute('x1', x(point)); guide.setAttribute('x2', x(point)); dot.setAttribute('cx', x(point)); dot.setAttribute('cy', y(point));
      const text = dateText(point.date) + ' · ' + label + ' ' + point.value.toFixed(2) + (peer ? ' · SPY ' + peer.value.toFixed(2) : '');
      inspection.textContent = text; slider.setAttribute('aria-valuetext', text);
    }
    slider.addEventListener('input', inspect); inspect(); section.append(inspection, slider);
  }
  function openBrief(id) {
    const company = knownCompany(id), content = $('ap-brief-content');
    content.replaceChildren();
    let record = null; try { record = engine.companyHistory(data, run, id); } catch (_) { /* Not yet invested. */ }
    const heading = element('h2', '', company?.name || record?.name || id); heading.id = 'ap-brief-title'; content.append(heading);
    const meta = element('div', 'ap-brief-meta'); meta.append(element('span', 'ap-brief-tag', company?.ticker || record?.ticker || id));
    if (company?.sector) meta.append(element('span', 'ap-brief-tag', company.sector)); content.append(meta);
    if (company?.identityNote) {
      const identity = element('details', 'ap-identity-note');
      identity.append(element('summary', '', 'Historical identity'), element('p', '', company.identityNote));
      if (company.identitySourceUrl) identity.append(link(company.identitySourceUrl, 'Dated identity source ↗'));
      content.append(identity);
    }
    const financials = company?.financials, cutoff = financials?.decisionCutoff || company?.decisionCutoff || decision?.cutoff;
    content.append(element('p', 'ap-brief-cutoff', 'AS FILED · Evidence available by ' + dateText(cutoff) + '. Subsequent operating results are not used in this decision file.'));
    if (company?.canInvest === false) content.append(element('p', 'ap-brief-warning', 'Allocation unavailable. ' + (company.coverage?.reason || 'Complete verifiable price coverage is unavailable for this investment interval.')));
    const observed = record?.mostRecentPeriod;
    if (observed) {
      const section = element('section', 'ap-company-period'); section.append(element('h3', '', 'The last completed interval.'));
      section.append(element('p', 'ap-chart-note', dateText(observed.from) + ' — ' + dateText(observed.to) + '. Outcomes appear only after the annual allocation is committed.'));
      const metrics = element('dl', 'ap-company-return-stats');
      [[observed.ticker || company?.ticker || 'Company', percent(observed.return, true)], ['S&P 500 proxy / SPY', percent(observed.benchmark?.return, true)]].forEach(([name, value]) => { const cell = element('div'); cell.append(element('dt', '', name), element('dd', '', value)); metrics.append(cell); });
      section.append(metrics);
      if (observed.path?.length) {
        const legend = element('div', 'ap-chart-legend');
        const own = element('span'); own.append(element('i'), document.createTextNode(observed.ticker || 'Company')); legend.append(own);
        if (observed.benchmark?.path?.length) { const peer = element('span'); peer.append(element('i'), document.createTextNode('SPY')); legend.append(peer); }
        section.append(legend);
        appendCompanyChart(section, observed.path, observed.benchmark?.path, observed.ticker || 'Company');
        section.append(element('p', 'ap-chart-note', 'Growth of 100 over this observed interval. Provider adjustments reflect distributions and splits.'));
      } else section.append(element('p', 'ap-brief-warning', 'Complete observed price coverage is unavailable for this completed interval. No return has been filled or inferred.'));
      content.append(section);
    }
    const metrics = financials?.metrics || {}, metricSources = financials?.metricSources || {};
    const facts = element('dl', 'ap-brief-facts');
    [['rd', 'ANNUAL R&D'], ['capex', 'CAPITAL EXPENDITURES'], ['acquisitions', 'ACQUISITION SPENDING'], ['revenue', 'ANNUAL REVENUE'], ['operatingCashFlow', 'OPERATING CASH FLOW'], ['epsDiluted', 'DILUTED EPS']].forEach(([key, label]) => {
      const cell = element('div'), source = metricSources[key], raw = metrics[key], value = finite(raw) ? raw : raw?.value;
      cell.append(element('dt', '', label));
      const dd = element('dd', finite(value) ? '' : 'is-unavailable', formatFact(value, source?.unit || (key === 'epsDiluted' ? 'USD/shares' : 'USD'))); cell.append(dd);
      const note = element('small', '', finite(value) ? 'FY ended ' + dateText(source?.fiscalPeriodEnd || financials?.fiscalPeriodEnd) + ' · filed ' + dateText(source?.filed || financials?.availableAt) : 'No eligible filed value in this edition.');
      if (finite(value) && source?.sourceUrl) { note.append(document.createTextNode(' · '), link(source.sourceUrl, 'SEC source ↗')); }
      cell.append(note); facts.append(cell);
    }); content.append(facts);
    content.append(element('p', 'ap-chart-note', 'R&D, capital expenditures and acquisitions are separate reported measures. They can overlap and are not added into a single investment total.'));
    if (financials?.valuation && finite(financials.valuation.pe)) {
      content.append(element('h3', '', 'Valuation at the cutoff'));
      content.append(element('p', '', 'Price / filed earnings: ' + financials.valuation.pe.toFixed(2) + '×. ' + (financials.valuation.note || '')));
      if (financials.valuation.sourceUrl) content.append(link(financials.valuation.sourceUrl, 'Valuation evidence ↗'));
    }
    const filings = financials?.filings || [];
    content.append(element('h3', '', 'The investment brief.'));
    const themes = filings.flatMap(filing => (filing.investmentThemes || []).map(theme => ({...theme, filing})));
    if (!themes.length) content.append(element('p', 'ap-brief-warning', 'A verified, dated operating-investment excerpt is not available in this data edition. No investment thesis has been inferred from later results. Review any linked eligible filing for the company’s own discussion.'));
    themes.forEach(theme => {
      content.append(element('h3', '', theme.label || 'As filed'));
      if (theme.excerpt) content.append(element('p', 'ap-brief-section-copy', theme.excerpt));
      if (theme.note) content.append(element('p', 'ap-chart-note', theme.note));
      if (theme.filing.url) content.append(link(theme.filing.url, theme.filing.form + ' · filed ' + dateText(theme.filing.filed) + ' ↗'));
    });
    filings.forEach(filing => {
      if (!filing.focusAreas?.length) return;
      content.append(element('p', 'ap-chart-note', 'Filing topic pointers: ' + filing.focusAreas.join(' · ') + '. ' + (filing.focusNote || 'These are navigation labels, not a reconstruction of the company’s strategy or spending.')));
    });
    if (filings.length) {
      content.append(element('h3', '', 'Dated source filings'));
      filings.forEach(filing => {
        const row = element('div', 'ap-filing');
        row.append(link(filing.url, (filing.form || 'SEC filing') + ' · filed ' + dateText(filing.filed) + ' ↗'));
        row.append(element('p', '', 'Period ended ' + dateText(filing.reportDate) + (filing.accession ? ' · ' + filing.accession : '')));
        content.append(row);
      });
    } else content.append(element('p', 'ap-chart-note', 'No eligible SEC filing is attached to this company at the decision cutoff.'));
    if (record && recordPeriods(record).length) {
      const section = element('section', 'ap-brief-history'); section.append(element('h3', '', 'Your invested periods'));
      section.append(element('p', '', signedMoney(recordProfit(record)) + ' in total contribution to your portfolio. Only periods in which you allocated capital are included.'));
      if (finite(record.ownedReturn)) {
        const stats = element('dl', 'ap-company-return-stats'), linked = element('div'), profit = element('div');
        linked.append(element('dt', '', 'LINKED RETURN WHILE OWNED'), element('dd', '', percent(record.ownedReturn, true)));
        profit.append(element('dt', '', 'YOUR DOLLAR P&L'), element('dd', '', signedMoney(recordProfit(record)))); stats.append(linked, profit); section.append(stats);
        appendCompanyChart(section, record.ownedReturnPath, [], 'Owned periods');
        section.append(element('p', 'ap-chart-note', 'Compounds the company’s returns only across periods you held it; flat sections include unowned periods. Allocation sizes do not affect this linked return. Your dollar P&L reflects your actual weights.'));
      }
      recordPeriods(record).forEach(period => {
        const row = element('div', 'ap-brief-period'); row.append(element('span', '', dateText(period.from) + ' — ' + dateText(period.to)), element('strong', '', percent(period.return, true) + ' / ' + signedMoney(period.profit))); section.append(row);
      }); section.append(miniChart(record.path || [])); content.append(section);
    }
    if (decision && !reveal && companyMap.has(id)) {
      const controls = element('div', 'ap-brief-allocation');
      controls.append(element('p', '', company.canInvest ? 'Set the share of your full portfolio to hold for the next period. No purchase occurs until you lock the allocation.' : 'This company’s next investment interval lacks complete verifiable price coverage. Allocation is unavailable.'));
      const button = element('button', 'ap-primary', Object.hasOwn(draft, id) ? 'Edit allocation ↗' : 'Add to portfolio +'); button.type = 'button'; button.disabled = !company.canInvest;
      button.addEventListener('click', () => { closeDialogs(); addCompany(id); }); controls.append(button); content.append(controls);
    }
    openDialog($('ap-brief')); $('ap-brief').scrollTop = 0;
  }
  async function commit() {
    if (busy || !decision) return;
    busy = true; updateAllocation(); error('');
    try {
      const next = engine.allocate(data, run, draft);
      run = next; reveal = true; outcomePage = 0; outcomeQuery = ''; investedPage = 0; investedQuery = ''; $('ap-invested-search').value = ''; $('ap-outcome-search').value = ''; refreshDecision(); draft = defaultDraft(); save(); render();
      $('ap-history').classList.remove('is-revealing'); void $('ap-history').offsetWidth; $('ap-history').classList.add('is-revealing');
      $('ap-history').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
      announce('Period completed. Your portfolio is now ' + money(run.lastResult.after) + '. Results are available.');
    } catch (failure) { error(failure.message || 'This allocation could not be verified. Review the coverage details.'); }
    finally { busy = false; if (!reveal && decision) updateAllocation(); }
  }
  function nextYear() {
    if (!engine.current(data, run)) { openDialog($('ap-reset-dialog')); return; }
    reveal = false; page = 0; filterQuery = ''; sector = ''; $('ap-search').value = ''; save(); render(); setDesk('universe');
    $('ap-plan').scrollIntoView({behavior: 'smooth', block: 'start'}); announce('New annual decision. ' + dateText(decision.cutoff) + '.');
  }
  function reset() { run = engine.create(data); refreshDecision(); draft = {}; reveal = false; page = 0; filterQuery = ''; sector = ''; $('ap-search').value = ''; closeDialogs(); error(''); save(); render(); setDesk('universe'); $('ap-plan').scrollIntoView({behavior: 'smooth', block: 'start'}); }
  function readScores() {
    try { const result = JSON.parse(localStorage.getItem(SCORE_STORAGE) || '[]'); return Array.isArray(result) ? result.slice(0, 100) : []; } catch (_) { return []; }
  }
  function verifiedScores() {
    return readScores().filter(entry => entry?.datasetId === run.datasetId).map(entry => {
      try { const savedRun = engine.restore(data, entry.run), score = engine.score(data, savedRun); return {...entry, score}; } catch (_) { return null; }
    }).filter(Boolean).sort((a, b) => b.score.finalValue - a.score.finalValue);
  }
  function showScores() {
    if (!run) return;
    $('ap-scores-edition').textContent = 'Current annual edition · ' + run.rounds + ' decisions · starts with $100';
    const entries = verifiedScores(); $('ap-scores-list').replaceChildren();
    if (!entries.length) $('ap-scores-list').append(element('li', 'ap-no-score', 'Finish the annual exercise to record your first portfolio.'));
    entries.forEach(entry => {
      const row = element('li'), description = element('div'), value = element('div');
      description.append(element('strong', '', String(entry.name || 'You').slice(0, 24)), element('small', '', entry.score.periods + ' decisions · ' + dateText(entry.score.endDate)));
      value.append(element('strong', '', compact(entry.score.finalValue)), element('small', '', percent(entry.score.change, true) + ' from $100')); row.append(description, value); $('ap-scores-list').append(row);
    });
    openDialog($('ap-scores'));
  }
  function saveScore(event) {
    event.preventDefault();
    try {
      const score = engine.score(data, run), entries = verifiedScores().filter(entry => entry.score.runId !== score.runId);
      const entry = {datasetId: run.datasetId, name: $('ap-score-name').value.trim().slice(0, 24) || 'You', run: engine.serialize(run), recordedAt: new Date().toISOString(), score};
      entries.push(entry); entries.sort((a, b) => b.score.finalValue - a.score.finalValue);
      const best = entries.slice(0, 20).map(item => ({datasetId: item.datasetId, name: item.name, run: item.run, recordedAt: item.recordedAt}));
      const older = readScores().filter(item => item?.datasetId !== run.datasetId).slice(0, 40);
      let constrained = false;
      while (true) {
        try { localStorage.setItem(SCORE_STORAGE, JSON.stringify(best.concat(older))); break; }
        catch (failure) {
          if (!['QuotaExceededError', 'NS_ERROR_DOM_QUOTA_REACHED'].includes(failure.name)) throw failure;
          constrained = true;
          if (older.length) older.pop(); else if (best.length > 1) best.pop(); else throw failure;
        }
      }
      const retained = best.some(item => item.run === entry.run);
      $('ap-score-status').textContent = (retained ? 'Saved to your device’s annual record. Replay verified.' : 'Run verified. This device retained the higher-value portfolios.') + (constrained ? ' Storage is limited; ' + best.length + ' current-edition records fit.' : '');
      announce($('ap-score-status').textContent);
    } catch (failure) { $('ap-score-status').textContent = 'Could not save this record. ' + (failure.message || 'Device storage may be unavailable.'); }
  }
  function bind() {
    $('ap-search').addEventListener('input', event => { filterQuery = event.target.value; page = 0; renderCompanies(); });
    $('ap-sector').addEventListener('change', event => { sector = event.target.value; page = 0; renderCompanies(); });
    $('ap-sort').addEventListener('change', event => { sort = event.target.value; page = 0; renderCompanies(); });
    $('ap-available-only').addEventListener('change', event => { availableOnly = event.target.checked; page = 0; renderCompanies(); });
    $('ap-page-prev').addEventListener('click', () => { page--; renderCompanies(); }); $('ap-page-next').addEventListener('click', () => { page++; renderCompanies(); });
    $('ap-outcome-search').addEventListener('input', event => { outcomeQuery = event.target.value; outcomePage = 0; renderOutcomes(); });
    $('ap-outcome-prev').addEventListener('click', () => { outcomePage--; renderOutcomes(); }); $('ap-outcome-next').addEventListener('click', () => { outcomePage++; renderOutcomes(); });
    $('ap-invested-search').addEventListener('input', event => { investedQuery = event.target.value; investedPage = 0; renderInvestedHistory(); });
    $('ap-invested-prev').addEventListener('click', () => { investedPage--; renderInvestedHistory(); }); $('ap-invested-next').addEventListener('click', () => { investedPage++; renderInvestedHistory(); });
    $('ap-universe-tab').addEventListener('click', () => setDesk('universe')); $('ap-basket-tab').addEventListener('click', () => setDesk('basket'));
    [$('ap-universe-tab'), $('ap-basket-tab')].forEach(tab => tab.addEventListener('keydown', event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); const panel = event.key === 'Home' ? 'universe' : event.key === 'End' ? 'basket' : tab.id === 'ap-universe-tab' ? 'basket' : 'universe'; setDesk(panel); $(panel === 'universe' ? 'ap-universe-tab' : 'ap-basket-tab').focus(); } }));
    $('ap-equal').addEventListener('click', () => { const ids = Object.keys(draft); if (!ids.length) return; ids.forEach(id => { draft[id] = 1 / ids.length; }); renderBasket(); renderCompanies(); save(); });
    $('ap-equal-universe').addEventListener('click', () => {
      const companies = currentCompanies.filter(company => company.canInvest); if (!companies.length) return;
      draft = Object.fromEntries(companies.map(company => [company.id, 1 / companies.length]));
      renderBasket(); renderCompanies(); save(); setDesk('basket');
      announce('Allocated 100% equally across all ' + companies.length + ' available companies in the full ' + currentCompanies.length + '-company roster. The portfolio is ready to review.');
    });
    $('ap-clear').addEventListener('click', () => { draft = {}; renderBasket(); renderCompanies(); save(); });
    $('ap-commit').addEventListener('click', commit); $('ap-next').addEventListener('click', nextYear);
    $('ap-restart').addEventListener('click', () => { if (run) openDialog($('ap-reset-dialog')); }); $('ap-reset-confirm').addEventListener('click', reset);
    $('ap-scores-open').addEventListener('click', showScores); $('ap-score-form').addEventListener('submit', saveScore);
    document.querySelectorAll('[data-ap-rules]').forEach(button => button.addEventListener('click', () => openDialog($('ap-rules'))));
    document.querySelectorAll('[data-ap-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
    document.querySelectorAll('.ap-dialog').forEach(dialog => dialog.addEventListener('click', event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } }));
    let resizeTimer; window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (run?.actions.length) drawHistory(engine.portfolio(data, run)); }, 120); });
  }
  async function load() {
    bind();
    try {
      if (!engine) throw new Error('The portfolio engine did not load. Refresh the page to try again.');
      const response = await fetch($('ap-data-link').href, {cache: 'no-cache'});
      if (!response.ok) throw new Error('The historical edition could not be loaded (' + response.status + '). Try refreshing when connected.');
      data = await response.json(); run = engine.create(data); refreshDecision();
      let saved = null;
      try { const text = localStorage.getItem(STORAGE); if (text) saved = JSON.parse(text); } catch (_) { storageOK = false; }
      if (saved?.run) {
        try { run = engine.restore(data, saved.run); refreshDecision(); draft = safeDraft(saved.draft); reveal = !!saved.reveal && !!run.lastResult; }
        catch (_) { error('The previous save belongs to a different or unverifiable data edition. This run starts from $100 with the current data.'); }
      }
      if (!decision) reveal = true;
      $('ap-edition-note').textContent = 'Historical roster reconstruction. Coverage gaps are visible. ' + (data.asOf ? 'Data through ' + dateText(data.asOf) + '.' : '');
      const notes = Array.isArray(data.disclosures) ? data.disclosures : Array.isArray(data.methodology) ? data.methodology : Array.isArray(data.limitations) ? data.limitations : [];
      notes.forEach(note => $('ap-data-notes').append(element('p', '', typeof note === 'string' ? note : note.text || '')));
      if (data.membershipSourceUrl) $('ap-data-notes').append(link(data.membershipSourceUrl, 'Archived historical membership source ↗'));
      render(); save();
    } catch (failure) { $('ap-load-status').textContent = 'The historical record is unavailable.'; error(failure.message || 'The game could not load. Please refresh to try again.'); }
  }
  load();
})();
