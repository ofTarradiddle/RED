'use strict';
(() => {
  const dataLink = document.getElementById('comparison-data-link');
  const math = window.HetzerkComparisonMath;
  if (!dataLink || !math) return;
  const $ = id => document.getElementById(id);
  const peers = Array.from(document.querySelectorAll('input[name="peer"]'));
  const basis = $('redi-basis'), mode = $('return-mode');
  const svg = $('comparison-chart'), cursor = $('chart-cursor');
  const storageKey = 'hetzerk-comparison-preferences-v1';
  const colors = {REDI: '#a31d32', SPY: '#425968', VOO: '#857047', QQQ: '#477b72', ITAN: '#8972a6', SYLD: '#a07137'};
  const ns = 'http://www.w3.org/2000/svg';
  const percent = new Intl.NumberFormat('en-US', {style: 'percent', maximumFractionDigits: 2, minimumFractionDigits: 2});
  const dollar = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 2});
  const number = new Intl.NumberFormat('en-US', {maximumFractionDigits: 2, minimumFractionDigits: 2});
  const dateFormat = new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'});
  let payload = null, result = null, period = '1Y', fetching = false, cached = false, chartGeometry = null;
  let focusLine = null, focusDots = [], resizeFrame = null;

  function write(id, text) { const node = $(id); if (node) node.textContent = text; }
  function dateText(value) { return math.validDate(value) ? dateFormat.format(new Date(value + 'T00:00:00Z')) : 'Not available'; }
  function setError(message) {
    const node = $('comparison-error');
    if (!node) return;
    node.textContent = message || '';
    node.hidden = !message;
  }
  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify({peers: peers.filter(input => input.checked).map(input => input.value), basis: basis.value, mode: mode.value, period: period})); } catch (_) {}
  }
  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
      if (!saved || typeof saved !== 'object') return;
      if (Array.isArray(saved.peers)) {
        const ids = saved.peers.filter(id => peers.some(input => input.value === id)).slice(0, 3);
        peers.forEach(input => { input.checked = ids.includes(input.value); });
      }
      if (['nav', 'market_price'].includes(saved.basis)) basis.value = saved.basis;
      if (['price', 'reinvested'].includes(saved.mode)) mode.value = saved.mode;
      if (['1M', '3M', '6M', 'YTD', '1Y', 'ALL'].includes(saved.period)) period = saved.period;
    } catch (_) {}
  }

  function validate(data) {
    if (!data || data.schema_version !== 1 || !Array.isArray(data.series)) throw new Error('The published comparison snapshot has an unsupported format.');
    const ids = new Set();
    data.series.forEach(series => {
      if (!series || typeof series.id !== 'string' || ids.has(series.id) || !Array.isArray(series.observations)) throw new Error('The published snapshot contains an invalid fund history.');
      if (series.currency !== 'USD') throw new Error('The comparison snapshot must use USD for every fund.');
      const dates = new Set();
      series.observations.forEach(row => {
        if (!row || !math.validDate(row.date) || dates.has(row.date)) throw new Error('The published snapshot contains an invalid or repeated closing date.');
        dates.add(row.date);
      });
      ids.add(series.id);
    });
    if (!ids.has('REDI')) throw new Error('The published snapshot does not include REDI.');
    return data;
  }

  function updateQuotes() {
    const redi = payload.series.find(series => series.id === 'REDI');
    const observations = redi.observations.filter(row => row && math.validDate(row.date)).sort((a, b) => a.date.localeCompare(b.date));
    const latest = observations[observations.length - 1];
    const nav = latest && typeof latest.nav === 'number' && Number.isFinite(latest.nav) && latest.nav > 0 ? latest.nav : null;
    const price = latest && typeof latest.market_price === 'number' && Number.isFinite(latest.market_price) && latest.market_price > 0 ? latest.market_price : null;
    write('fund-nav', nav === null ? '—' : dollar.format(nav));
    write('fund-price', price === null ? '—' : dollar.format(price));
    write('fund-premium', nav === null || price === null ? '—' : percent.format(price / nav - 1));
    write('fund-asof', latest ? 'As of ' + dateText(latest.date) : 'Awaiting REDI history');
  }

  function updateSources(selected) {
    const list = $('comparison-sources');
    if (!list) return;
    list.replaceChildren();
    selected.forEach(series => {
      const item = document.createElement('li');
      const title = document.createElement('strong');
      title.textContent = series.id + (series.is_illustrative ? ' *' : '');
      item.append(title);
      const detail = document.createElement('small');
      const status = series.status === 'unavailable' ? 'Unavailable' : series.status === 'stale' ? 'Retained snapshot' : 'Published snapshot';
      detail.textContent = (series.source || 'Published fund data') + ' · ' + status + ' · ' + (math.validDate(series.as_of) ? 'closing data ' + dateText(series.as_of) : 'No closing date');
      item.append(detail);
      if (series.source_url) {
        try {
          const url = new URL(series.source_url, location.href);
          if (url.protocol === 'https:' || (url.protocol === 'http:' && url.origin === location.origin)) {
            const link = document.createElement('a');
            link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
            link.textContent = 'Source'; link.setAttribute('aria-label', series.id + ' data source (opens a new tab)');
            item.append(link);
          }
        } catch (_) {}
      }
      list.append(item);
    });
  }

  function renderTable() {
    const body = document.querySelector('#risk-table tbody');
    if (!body) return;
    body.replaceChildren();
    if (!result.series.length) {
      const row = document.createElement('tr'), cell = document.createElement('td');
      cell.colSpan = 5; cell.textContent = 'No comparable observations are available.';
      row.append(cell); body.append(row); return;
    }
    result.series.forEach(series => {
      const row = document.createElement('tr');
      const heading = document.createElement('th');
      heading.scope = 'row'; heading.textContent = series.id + (series.isIllustrative ? ' *' : '');
      row.append(heading);
      ['change', 'drawdown', 'volatility', 'correlation'].forEach(key => {
        const cell = document.createElement('td');
        const value = series.metrics[key];
        cell.textContent = value === null ? '—' : key === 'correlation' ? number.format(value) : percent.format(value);
        if (value === null) cell.title = key === 'correlation' && result.riskAvailable ? 'Correlation is undefined for a constant return series.' : result.riskReason || 'Not enough shared closing dates.';
        if (key === 'change' && value !== null) cell.classList.add(value >= 0 ? 'metric-positive' : 'metric-negative');
        row.append(cell);
      });
      body.append(row);
    });
  }

  function element(tag, attributes, text) {
    const node = document.createElementNS(ns, tag);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function renderLegend() {
    const list = $('chart-legend');
    if (!list) return;
    list.replaceChildren();
    result.series.forEach(series => {
      const li = document.createElement('li'), swatch = document.createElement('span'), label = document.createElement('span');
      swatch.className = 'legend-swatch'; swatch.style.backgroundColor = colors[series.id] || '#425968'; swatch.setAttribute('aria-hidden', 'true');
      label.textContent = series.id + (series.id === 'REDI' ? (basis.value === 'nav' ? ' · NAV' : ' · Market Price') : '') + (series.isIllustrative ? ' *' : '');
      li.append(swatch, label); list.append(li);
    });
  }
  function inspect(index) {
    if (!result || !result.dates.length || !chartGeometry) return;
    const selected = Math.min(Math.max(0, index), result.dates.length - 1);
    cursor.value = String(selected);
    const date = result.dates[selected];
    cursor.setAttribute('aria-valuetext', dateText(date));
    const text = dateText(date) + ' · ' + result.series.map(series => series.id + ' ' + number.format(series.points[selected].value)).join(' · ');
    write('chart-readout', text);
    const x = chartGeometry.x(selected);
    if (focusLine) { focusLine.setAttribute('x1', x); focusLine.setAttribute('x2', x); }
    focusDots.forEach((dot, i) => {
      dot.setAttribute('cx', x);
      dot.setAttribute('cy', chartGeometry.y(result.series[i].points[selected].value));
    });
  }
  function renderChart() {
    if (!svg || !result) return;
    svg.replaceChildren(); focusDots = []; focusLine = null; chartGeometry = null;
    const empty = $('chart-empty');
    if (!result.series.length || result.dates.length < 2) {
      if (empty) { empty.hidden = false; empty.textContent = result.reason || 'A comparison needs at least two shared closing dates.'; }
      svg.setAttribute('hidden', ''); cursor.disabled = true; cursor.hidden = true;
      write('chart-readout', ''); return;
    }
    if (empty) empty.hidden = true;
    svg.removeAttribute('hidden'); cursor.disabled = false; cursor.hidden = false;
    const width = Math.max(320, Math.min(960, svg.getBoundingClientRect().width || 960));
    const height = width < 580 ? 300 : 400;
    const left = 52, right = 22, top = 28, bottom = 42;
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.setAttribute('aria-label', (mode.value === 'reinvested' ? 'Growth with distributions reinvested' : 'Price growth') + ', indexed to 100, ' + dateText(result.start) + ' through ' + dateText(result.end) + '. Use the date slider for exact values.');
    const values = result.series.flatMap(series => series.points.map(point => point.value));
    let min = Math.min(...values), max = Math.max(...values);
    const pad = Math.max(1, (max - min) * 0.12);
    min -= pad; max += pad;
    const x = index => left + index / (result.dates.length - 1) * (width - left - right);
    const y = value => top + (max - value) / (max - min) * (height - top - bottom);
    chartGeometry = {x: x, y: y, width: width, left: left, right: right};
    for (let i = 0; i <= 4; i += 1) {
      const value = min + (max - min) * i / 4, pos = y(value);
      svg.append(element('line', {x1: left, y1: pos, x2: width - right, y2: pos, class: 'chart-grid'}));
      svg.append(element('text', {x: left - 9, y: pos + 4, 'text-anchor': 'end', class: 'chart-axis-label'}, value.toFixed(max - min < 10 ? 1 : 0)));
    }
    const ticks = width < 580 ? 3 : 5;
    for (let i = 0; i < ticks; i += 1) {
      const index = Math.round(i / (ticks - 1) * (result.dates.length - 1));
      const date = new Date(result.dates[index] + 'T00:00:00Z');
      const label = new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'}).format(date);
      svg.append(element('text', {x: x(index), y: height - 14, 'text-anchor': i === 0 ? 'start' : i === ticks - 1 ? 'end' : 'middle', class: 'chart-axis-label'}, label));
    }
    result.series.slice().reverse().forEach(series => {
      const path = series.points.map((point, index) => (index ? 'L' : 'M') + x(index).toFixed(2) + ',' + y(point.value).toFixed(2)).join(' ');
      svg.append(element('path', {d: path, fill: 'none', stroke: colors[series.id] || '#425968', 'stroke-width': series.id === 'REDI' ? 3 : 2, class: 'chart-line', 'vector-effect': 'non-scaling-stroke'}));
    });
    focusLine = element('line', {x1: left, y1: top, x2: left, y2: height - bottom, class: 'chart-focus-line', 'aria-hidden': 'true'});
    svg.append(focusLine);
    result.series.forEach(series => {
      const dot = element('circle', {cx: left, cy: y(100), r: series.id === 'REDI' ? 4.5 : 3.5, fill: colors[series.id] || '#425968', class: 'chart-focus-point', 'aria-hidden': 'true'});
      focusDots.push(dot); svg.append(dot);
    });
    cursor.min = '0'; cursor.max = String(result.dates.length - 1); cursor.step = '1';
    inspect(result.dates.length - 1);
  }

  function render() {
    document.querySelectorAll('[data-period]').forEach(button => {
      const active = button.dataset.period === period;
      button.setAttribute('aria-pressed', String(active)); button.classList.toggle('is-active', active);
    });
    if (!payload) return;
    const peerIds = peers.filter(input => input.checked).map(input => input.value);
    const selected = ['REDI', ...peerIds].map(id => payload.series.find(series => series.id === id) || {id: id, name: id, currency: 'USD', status: 'unavailable', observations: [], error: 'No published history.'});
    try { result = math.compare({series: selected, basis: basis.value, mode: mode.value, period: period}); }
    catch (error) { setError(error.message); return; }
    updateQuotes(); updateSources(selected); renderLegend(); renderTable(); renderChart();
    write('comparison-range', result.start ? dateText(result.start) + ' — ' + dateText(result.end) : 'No shared history');
    write('comparison-summary', (mode.value === 'reinvested' ? 'Distributions reinvested' : 'Price change') + ' · Each series starts at 100.');
    write('risk-status', result.riskReason || '');
    if ($('risk-status')) $('risk-status').hidden = !result.riskReason;
    const unavailable = result.excluded.map(item => item.id + ': ' + item.reason);
    const missing = selected.filter(series => series.status === 'stale').map(series => series.id + ' uses a retained snapshot.');
    setError([...unavailable, ...missing, ...result.warnings].join(' '));
    const peerDates = selected.filter(series => series.id !== 'REDI' && math.validDate(series.as_of)).map(series => series.as_of);
    const status = [];
    if (cached) status.push('Saved snapshot');
    else status.push('Daily closing data');
    if (result.end && peerDates.some(date => date > result.end)) status.push('Comparison ends at the latest shared REDI date');
    write('comparison-status', status.join(' · '));
    const timestamp = payload.generated_at;
    const parsed = timestamp && new Date(timestamp);
    write('comparison-updated', parsed && Number.isFinite(parsed.getTime())
      ? (cached ? 'Saved snapshot published ' : 'Snapshot published ') + parsed.toLocaleString('en-US', {month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short'})
      : 'Published snapshot · See each fund’s closing date below');
  }

  async function refresh() {
    if (fetching) return;
    fetching = true;
    const buttons = Array.from(document.querySelectorAll('[data-refresh]'));
    buttons.forEach(button => { button.disabled = true; button.setAttribute('aria-busy', 'true'); });
    write('comparison-status', 'Checking the published snapshot…');
    try {
      const response = await fetch(dataLink.href, {cache: 'no-cache', credentials: 'same-origin'});
      if (!response.ok) throw new Error('The published data is not available (HTTP ' + response.status + ').');
      const next = validate(await response.json());
      payload = next; cached = response.headers.get('X-Hetzerk-Cache') === 'offline';
      render();
    } catch (error) {
      if (payload) { render(); setError('Could not check for updates. The last loaded snapshot remains on screen. ' + error.message); }
      else {
        setError('The comparison snapshot could not be loaded. Connect to the internet and check for updates.');
        write('comparison-status', 'Data unavailable');
        const empty = $('chart-empty');
        if (empty) { empty.hidden = false; empty.textContent = 'No published snapshot is available. No prices or performance have been estimated.'; }
        svg.setAttribute('hidden', ''); cursor.disabled = true; cursor.hidden = true;
        const body = document.querySelector('#risk-table tbody');
        if (body) {
          const row = document.createElement('tr'), cell = document.createElement('td');
          cell.colSpan = 5; cell.textContent = 'Metrics are unavailable until the snapshot loads.';
          row.append(cell); body.replaceChildren(row);
        }
      }
    } finally {
      fetching = false;
      buttons.forEach(button => { button.disabled = false; button.removeAttribute('aria-busy'); });
    }
  }

  peers.forEach(input => input.addEventListener('change', () => {
    if (peers.filter(peer => peer.checked).length > 3) {
      input.checked = false; setError('Choose up to three ETFs alongside REDI.'); return;
    }
    save(); render();
  }));
  [basis, mode].forEach(select => select.addEventListener('change', () => { save(); render(); }));
  document.querySelectorAll('[data-period]').forEach(button => button.addEventListener('click', () => { period = button.dataset.period; save(); render(); }));
  document.querySelectorAll('[data-refresh]').forEach(button => button.addEventListener('click', refresh));
  cursor.addEventListener('input', () => inspect(Number(cursor.value)));
  function inspectPointer(event) {
    if (!chartGeometry || !result) return;
    const box = svg.getBoundingClientRect();
    const position = (event.clientX - box.left) / box.width * chartGeometry.width;
    const index = Math.round((position - chartGeometry.left) / (chartGeometry.width - chartGeometry.left - chartGeometry.right) * (result.dates.length - 1));
    inspect(index);
  }
  svg.addEventListener('pointermove', inspectPointer);
  svg.addEventListener('pointerdown', inspectPointer);
  document.querySelectorAll('a[href="#methodology"]').forEach(link => link.addEventListener('click', () => {
    const details = $('methodology');
    if (details) details.open = true;
  }));
  if (typeof ResizeObserver === 'function') {
    let lastWidth = 0;
    new ResizeObserver(entries => {
      const width = Math.round(entries[0].contentRect.width);
      if (width === lastWidth) return;
      lastWidth = width;
      if (resizeFrame !== null) cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => { resizeFrame = null; renderChart(); });
    }).observe(svg.parentElement);
  }
  restore(); render(); refresh();
})();
