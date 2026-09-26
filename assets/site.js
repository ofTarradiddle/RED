'use strict';
(() => {
  const menu = document.querySelector('.menu-button');
  const nav = document.querySelector('#main-navigation');
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') {
      menu.setAttribute('aria-expanded', 'false'); nav.classList.remove('is-open'); menu.focus();
    }
  });
  for (const status of document.querySelectorAll('[data-as-of]')) {
    const age = Math.floor((Date.now() - Date.parse(status.dataset.asOf + 'T23:59:59Z')) / 86400000);
    if (age > 7) status.textContent = `Data is ${age} days old. Refer to the displayed as-of date.`;
  }
  const data = document.querySelector('#page-data');
  if (!data) return;
  let fund;
  try { fund = JSON.parse(data.textContent); } catch { return; }
  const NS = 'http://www.w3.org/2000/svg';
  const svgElement = (tag, attrs, text) => {
    const el = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    if (text !== undefined) el.textContent = text;
    return el;
  };
  function chart(container, rows, series, mode, title) {
    if (!container) return;
    container.replaceChildren();
    if (rows.length < 2) { container.textContent = 'Chart unavailable: insufficient observations.'; return; }
    const width = 1000, height = 295, left = mode === 'premium' ? 62 : 54, right = 12, top = 15, bottom = 42;
    const values = series.map(s => rows.map(r => mode === 'indexed' ? r[s.key] / rows[0][s.key] * 100 : mode === 'price' ? r[s.key] : r[s.key] * 100));
    const all = values.flat();
    const min = Math.min(...all), max = Math.max(...all), span = Math.max(max-min, .01);
    // Premium/discount data is a decimal fraction, displayed as a percentage.
    // A symmetric domain keeps NAV (zero) visible even in an all-premium period.
    const extent = Math.max(Math.abs(min), Math.abs(max), .02) * 1.12;
    const lo = mode === 'premium' ? -extent : min - span*.12;
    const hi = mode === 'premium' ? extent : max + span*.12;
    const x = i => left+i/(rows.length-1)*(width-left-right);
    const y = v => top+(hi-v)/(hi-lo)*(height-top-bottom);
    const svg = svgElement('svg', {viewBox:`0 0 ${width} ${height}`, role:'img', 'aria-label':title});
    svg.append(svgElement('title', {}, title));
    for(let i=0;i<5;i++) {
      const v = lo+(hi-lo)*i/4;
      svg.append(svgElement('line',{x1:left,x2:width-right,y1:y(v),y2:y(v),stroke:'#e3e4db','stroke-width':1}));
      svg.append(svgElement('text',{x:left-9,y:y(v)+4,'text-anchor':'end'},mode === 'indexed' ? v.toFixed(1) : mode === 'price' ? '$'+v.toFixed(2) : v.toFixed(2)+'%'));
    }
    values.forEach((list,i)=>svg.append(svgElement('path',{d:list.map((v,j)=>(j?'L':'M')+x(j).toFixed(2)+','+y(v).toFixed(2)).join(' '),fill:'none',stroke:series[i].color,'stroke-width':i===0?2.7:1.7,'stroke-dasharray':i===1?'4 3':'none','vector-effect':'non-scaling-stroke'})));
    if (mode === 'premium') {
      svg.append(svgElement('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),stroke:'#6b7280','stroke-width':1.2,'stroke-dasharray':'4 4','data-zero-baseline':''}));
      svg.append(svgElement('rect',{x:width-right-34,y:y(0)-22,width:34,height:18,fill:'#fff','fill-opacity':.95}));
      svg.append(svgElement('text',{x:width-right,y:y(0)-7,'text-anchor':'end'},'NAV'));
    }
    for(const i of [0,Math.floor((rows.length-1)/2),rows.length-1]) svg.append(svgElement('text',{x:x(i),y:height-10,'text-anchor':i===0?'start':i===rows.length-1?'end':'middle'},rows[i].date));
    container.append(svg);
  }
  const accent=getComputedStyle(document.body).getPropertyValue('--fund-accent').trim() || '#8b0000';
  const series = [{key:'nav',color:accent},{key:'market_price',color:'#2563eb'},{key:'benchmark_index',color:'#6b7280'}];
  function selectPeriod(period) {
    const end = new Date(fund.as_of+'T12:00:00Z');
    const start = new Date(end);
    const months = {'1M':1,'3M':3,'6M':6,'1Y':12}[period];
    if(months) {
      const day=end.getUTCDate(); start.setUTCDate(1); start.setUTCMonth(start.getUTCMonth()-months);
      const last=new Date(Date.UTC(start.getUTCFullYear(),start.getUTCMonth()+1,0)).getUTCDate(); start.setUTCDate(Math.min(day,last));
    } else if(period==='YTD') {start.setUTCFullYear(end.getUTCFullYear()-1,11,31);}
    else {start.setTime(Date.parse(fund.daily[0].date+'T12:00:00Z'));}
    const cutoff=start.toISOString().slice(0,10);
    const before=fund.daily.filter(r=>r.date<=cutoff).at(-1);
    const rows=fund.daily.filter(r=>r.date>cutoff);
    if(before) rows.unshift(before);
    chart(document.querySelector('#performance-chart'),rows,series,'indexed',`NAV, Market Price and ${fund.benchmark_label} · indexed to 100`);
    const summary=document.querySelector('#chart-summary');
    if(summary) {
      const format=d=>new Date(d+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
      summary.textContent=rows.length?`${format(rows[0].date)} – ${format(rows.at(-1).date)} · Each series starts at 100 for the selected period.`:'No observations available.';
    }
    document.querySelectorAll('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===period)));
  }
  selectPeriod('ALL');
  document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>selectPeriod(b.dataset.period)));
  const minPeriod = fund.disclosure_periods[0]?.start || fund.daily[0].date;
  const premiumRows = fund.daily.filter(r=>r.date>=minPeriod);
  chart(document.getElementById('premium-chart'),premiumRows,[{key:'premium_discount',color:accent}],'premium','Daily closing premium and discount history');
  const tbody=document.querySelector('#holdings-table tbody');
  if(!tbody) return;
  let sortKey='weight', sortDirection=-1;
  const currency=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'});
  function filterHoldings() {
    const query=(document.querySelector('#holding-search')?.value||'').trim().toLowerCase();
    const sector=document.querySelector('#sector-filter')?.value||'';
    const rows=fund.holdings.filter(h=>(!sector||h.sector===sector)&&`${h.ticker} ${h.identifier} ${h.name}`.toLowerCase().includes(query));
    rows.sort((a,b)=>sortDirection*(typeof a[sortKey]==='number'?a[sortKey]-b[sortKey]:String(a[sortKey]).localeCompare(String(b[sortKey]))));
    tbody.replaceChildren();
    for(const h of rows) {
      const tr=document.createElement('tr');
      const cells=[h.ticker,h.identifier.replace(/^DEMO:/,''),h.name,h.sector,(h.weight*100).toFixed(2)+'%',h.quantity.toLocaleString('en-US',{minimumFractionDigits:4,maximumFractionDigits:4}),h.price.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}),h.currency,currency.format(h.market_value)];
      for(const value of cells){const td=document.createElement('td');td.textContent=value;tr.append(td);} tbody.append(tr);
    }
    document.querySelector('#holding-count').textContent=`${rows.length} of ${fund.holdings.length} positions`;
    document.querySelector('#holdings-empty').hidden=rows.length>0;
    document.querySelectorAll('[data-sort]').forEach(b=>b.parentElement.setAttribute('aria-sort',b.dataset.sort===sortKey?(sortDirection===1?'ascending':'descending'):'none'));
  }
  document.querySelector('#holding-search')?.addEventListener('input',filterHoldings);
  document.querySelector('#sector-filter')?.addEventListener('change',filterHoldings);
  document.querySelectorAll('[data-sort]').forEach(b=>b.addEventListener('click',()=>{sortDirection=sortKey===b.dataset.sort?-sortDirection:1;sortKey=b.dataset.sort;filterHoldings();}));
  filterHoldings();
})();
