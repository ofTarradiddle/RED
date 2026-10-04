'use strict';
(() => {
  const hosts = Array.from(document.querySelectorAll('[data-strategy-research]'));
  if (!hosts.length) return;
  const colors = {INNOVATION_LEADER:'#df7480', LAGGARD:'#d7b47c', MARKET_BACKTEST:'#aeb2b8', MARKET_EQUAL_WEIGHT:'#8fb0a5', NON_RD:'#9b9caa', SPY:'#94b7c9', VOO:'#a4b998', QQQ:'#dfab9b', ITAN:'#b8a0d8', SYLD:'#8fb7a9'};
  const comparisonColors = {MARKET:'#d5b775', MARKET_CAP:'#d6d0ba', NON_RD:'#aeb2c8', RD_OTHER:'#80bca9', INNOVATION:'#e5a279', PREDICTED_INNOVATION:'#f07d8c', INNOVATION_150_75:'#91b9d8', INNOVATION_200_100:'#b99ae2', INNOVATION_250_125:'#d0a0be', SPY:'#85d1d3', VOO:'#bfd088', QQQ:'#e9c088', ITAN:'#c7b7ed', SYLD:'#a4cbb0'};
  const ETF_IDS = ['SPY','VOO','QQQ','ITAN','SYLD'];
  const defaults = ['INNOVATION_LEADER','LAGGARD','MARKET_BACKTEST'];
  const number = new Intl.NumberFormat('en-US', {maximumFractionDigits:2, minimumFractionDigits:2});
  const percentage = new Intl.NumberFormat('en-US', {style:'percent', maximumFractionDigits:2, minimumFractionDigits:2});
  const axisNumber = new Intl.NumberFormat('en-US', {notation:'compact', maximumFractionDigits:1});
  const monthFormat = new Intl.DateTimeFormat('en-US', {month:'short', year:'numeric', timeZone:'UTC'});
  const dateFormat = new Intl.DateTimeFormat('en-US', {month:'short', day:'numeric', year:'numeric', timeZone:'UTC'});
  const ns = 'http://www.w3.org/2000/svg';
  const responses = new Map();
  function fetchJSON(url) {
    if (!responses.has(url)) responses.set(url, fetch(url, {cache:'no-cache', credentials:'same-origin'}).then(response => {
      if (!response.ok) throw new Error('Published data is unavailable (HTTP ' + response.status + ').');
      return response.json();
    }));
    return responses.get(url);
  }
  function month(value) { return monthFormat.format(new Date(value + 'T00:00:00Z')); }
  function date(value) { return dateFormat.format(new Date(value + 'T00:00:00Z')); }
  function element(tag, className, value) {
    const result = document.createElement(tag); if (className) result.className = className;
    if (value !== undefined) result.textContent = value; return result;
  }
  function vector(tag, attributes, value) {
    const result = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, val]) => result.setAttribute(key, String(val)));
    if (value !== undefined) result.textContent = value; return result;
  }
  function savedPreferences(key) {
    try { const value = JSON.parse(localStorage.getItem(key) || 'null'); return value && typeof value === 'object' ? value : null; } catch (_) { return null; }
  }

  hosts.forEach(host => {
    const $ = name => host.querySelector('[data-sr-' + name + ']');
    const all = selector => Array.from(host.querySelectorAll(selector));
    const chart = $('chart'), cursor = $('cursor');
    const customDates = $('custom-dates'), startDate = $('start-date'), endDate = $('end-date');
    const comparisonMode = host.dataset.srMode === 'comparison';
    const palette = comparisonMode ? comparisonColors : colors;
    const storageKey = comparisonMode ? 'hetzerk-comparison-research-v1' : 'hetzerk-strategy-research-v1';
    let referenceId = comparisonMode ? 'PREDICTED_INNOVATION' : 'INNOVATION_LEADER';
    let research = null, market = null, result = null, ids = comparisonMode ? [referenceId, 'INNOVATION', 'MARKET'] : defaults.slice(), period = 'ALL', scale = 'log';
    let geometry = null, focusLine = null, focusDots = [], selectionIndex = null, missingMarket = false;
    let emphasizedId = null;
    let customDatesInitialized = false;
    const saved = savedPreferences(storageKey);
    if (saved) {
      if (Array.isArray(saved.ids)) ids = comparisonMode ? Array.from(new Set(saved.ids.filter(id => typeof id === 'string'))) : [referenceId, ...Array.from(new Set(saved.ids.filter(id => typeof id === 'string' && id !== referenceId))).slice(0,3)];
      if ((window.HetzerkResearchMath ? window.HetzerkResearchMath.periods : ['ALL','1Y','5Y','10Y']).includes(saved.period)) period = saved.period;
      if (startDate && window.HetzerkComparisonMath.validDate(saved.startDate)) startDate.value = saved.startDate;
      if (endDate && window.HetzerkComparisonMath.validDate(saved.endDate)) endDate.value = saved.endDate;
      customDatesInitialized = Boolean(startDate && endDate && startDate.value && endDate.value);
      if (period === 'CUSTOM' && (!startDate || !endDate || !startDate.value || !endDate.value || startDate.value > endDate.value)) period = 'ALL';
      if (['log','linear'].includes(saved.scale)) scale = saved.scale;
    }
    function write(name, value) { const target = $(name); if (target) target.textContent = value; }
    function save() { try { localStorage.setItem(storageKey, JSON.stringify({ids, period, scale, startDate: startDate && startDate.value, endDate: endDate && endDate.value})); } catch (_) {} }
    function warning(value) { write('warning', value); $('warning').hidden = !value; }
    function chip(series, isETF) {
      const label = element('label','sr-chip'), input = document.createElement('input');
      if (comparisonMode && series.id === referenceId) label.classList.add('sr-preferred-chip');
      input.type = 'checkbox'; input.value = series.id; input.checked = ids.includes(series.id);
      input.setAttribute('data-sr-choice','');
      const caption = element('span'), swatch = element('i'); swatch.style.backgroundColor = palette[series.id] || '#b4968e'; swatch.setAttribute('aria-hidden','true');
      caption.append(swatch, document.createTextNode(isETF ? series.id : series.name));
      if (comparisonMode && series.id === referenceId) caption.append(element('small', '', 'REFERENCE'));
      if (comparisonMode && series.source_column) label.title = 'Source column: ' + series.source_column;
      if (isETF && (!series.observations || !series.observations.length || series.status === 'unavailable')) {
        input.disabled = true; label.title = series.id + ' historical data is unavailable.';
      }
      input.addEventListener('change', () => {
        const selection = all('[data-sr-choice]:checked').map(item => item.value);
        if (!comparisonMode && selection.length > 3) { input.checked = false; warning('Choose up to three comparison series alongside Innovation Leader.'); return; }
        ids = comparisonMode ? selection : [referenceId, ...selection]; selectionIndex = null; save(); render();
      });
      label.append(input,caption); return label;
    }
    function choices() {
      const validIDs = new Set([...research.series.map(series => series.id), ...ETF_IDS]);
      ids = ids.filter(id => validIDs.has(id));
      if (!comparisonMode && !ids.includes(referenceId)) ids.unshift(referenceId);
      const group = $('research-chips');
      Array.from(group.children).forEach(child => { if (!child.classList.contains('sr-reference-chip')) child.remove(); });
      const cohorts = research.series.filter(series => comparisonMode || series.id !== referenceId);
      if (comparisonMode) cohorts.sort((a,b) => Number(b.id === referenceId) - Number(a.id === referenceId));
      cohorts.forEach(series => group.append(chip(series,false)));
      const peers = $('etf-chips'); peers.replaceChildren();
      ETF_IDS.forEach(id => {
        const item = market && market.series && market.series.find(series => series.id === id);
        peers.append(chip(item || {id, status:'unavailable', observations:[]},true));
      });
    }
    function source() {
      const provenance = research.source || {};
      const details = [provenance.title, provenance.precision, provenance.provenance].filter(item => typeof item === 'string' && item.trim());
      write('source', details.join('. ').replace(/\.\./g,'.'));
      const notes = $('method-notes'); notes.replaceChildren();
      (Array.isArray(research.methodology) ? research.methodology : []).slice(0,4).forEach(item => {
        if (typeof item === 'string') notes.append(element('li','',item));
      });
      const start = research.period && research.period.start, end = research.period && research.period.end;
      if (start && end) write('coverage', start.slice(0,4) + '—' + end.slice(0,4));
    }
    function inspect(index) {
      if (!result || !geometry || !result.dates.length) return;
      selectionIndex = Math.max(0,Math.min(result.dates.length-1,index));
      cursor.value = String(selectionIndex);
      const day = result.dates[selectionIndex];
      cursor.setAttribute('aria-valuetext', month(day));
      const values = result.series.map(series => {
        const point = series.points[selectionIndex];
        const asOf = series.kind === 'etf' && point.observedDate !== day ? ' (close ' + date(point.observedDate) + ')' : '';
        return series.name + ' ' + number.format(point.value) + asOf;
      });
      if (comparisonMode) {
        const readout = $('readout'); readout.replaceChildren(element('strong', 'sr-readout-date', month(day)));
        result.series.forEach(series => {
          const point = series.points[selectionIndex], item = element('span', 'sr-readout-series'), swatch = element('i');
          swatch.style.backgroundColor = palette[series.id] || '#b4968e'; swatch.setAttribute('aria-hidden', 'true');
          item.append(swatch, element('span', '', series.name), element('strong', '', number.format(point.value)));
          if (series.kind === 'etf' && point.observedDate !== day) item.append(element('small', '', 'Close ' + date(point.observedDate)));
          readout.append(item);
        });
      } else write('readout', month(day) + ' · ' + values.join(' · '));
      const x = geometry.x(selectionIndex);
      focusLine.setAttribute('x1',x); focusLine.setAttribute('x2',x);
      focusDots.forEach((dot,i) => { dot.setAttribute('cx',x); dot.setAttribute('cy',geometry.y(result.series[i].points[selectionIndex].value)); });
    }
    function plot() {
      chart.replaceChildren(); focusDots = []; focusLine = null; geometry = null;
      if (!result || result.dates.length < 2 || !result.series.length) {
        chart.setAttribute('hidden',''); $('empty').hidden = false;
        write('empty', result && result.reason ? result.reason : 'At least two shared monthly observations are needed.');
        cursor.disabled = true; cursor.hidden = true; write('readout',''); return;
      }
      chart.removeAttribute('hidden'); $('empty').hidden = true;
      cursor.disabled = false; cursor.hidden = false;
      const width = Math.max(300,Math.min(1200,chart.getBoundingClientRect().width || 960));
      const height = width < 580 ? 300 : 370;
      const left = 49, right = 19, top = 25, bottom = 39;
      chart.setAttribute('viewBox','0 0 ' + width + ' ' + height);
      chart.setAttribute('aria-label','Historical research comparison, growth of 100 on a ' + (scale === 'log' ? 'logarithmic' : 'linear') + ' scale, ' + date(result.start) + ' to ' + date(result.end) + '. Use the month slider for exact values.');
      const values = result.series.flatMap(series => series.points.map(point => point.value));
      const transform = value => scale === 'log' ? Math.log10(value) : value;
      const inverse = value => scale === 'log' ? 10 ** value : value;
      let min = Math.min(...values.map(transform)), max = Math.max(...values.map(transform));
      const pad = Math.max(scale === 'log' ? .03 : 1, (max-min)*.1);
      min -= pad; max += pad; if (scale === 'linear') min = Math.max(0,min);
      const x = index => left + index/(result.dates.length-1)*(width-left-right);
      const y = value => top + (max-transform(value))/(max-min)*(height-top-bottom);
      geometry = {x,y,width,left,right};
      for (let i=0;i<5;i++) {
        const transformed = min+(max-min)*i/4, value = inverse(transformed), pos = y(value);
        chart.append(vector('line',{x1:left,y1:pos,x2:width-right,y2:pos,class:'sr-grid-line'}));
        chart.append(vector('text',{x:left-9,y:pos+4,'text-anchor':'end'},axisNumber.format(value)));
      }
      const count = width < 580 ? 3 : 5;
      for (let i=0;i<count;i++) {
        const index = Math.round(i/(count-1)*(result.dates.length-1));
        const day = result.dates[index], label = width < 580 && result.dates.length > 36 ? day.slice(0,4) : month(day);
        chart.append(vector('text',{x:x(index),y:height-11,'text-anchor':i===0?'start':i===count-1?'end':'middle'},label));
      }
      result.series.slice().reverse().forEach(series => {
        const path = series.points.map((point,index) => (index?'L':'M')+x(index).toFixed(2)+','+y(point.value).toFixed(2)).join(' ');
        const attributes = {d:path,class:'sr-series-line',stroke:palette[series.id]||'#b4968e','stroke-width':series.id===referenceId?2.8:1.8,'vector-effect':'non-scaling-stroke','data-sr-line':series.id};
        if (comparisonMode && series.kind === 'etf') attributes['stroke-dasharray'] = '5 4';
        chart.append(vector('path', attributes));
      });
      focusLine = vector('line',{x1:left,y1:top,x2:left,y2:height-bottom,class:'sr-focus-line','aria-hidden':'true'}); chart.append(focusLine);
      result.series.forEach(series => {
        const dot = vector('circle',{cx:left,cy:y(100),r:series.id===referenceId?4.5:3.5,fill:palette[series.id]||'#b4968e',class:'sr-focus-point','aria-hidden':'true','data-sr-line':series.id});
        chart.append(dot); focusDots.push(dot);
      });
      cursor.min='0'; cursor.max=String(result.dates.length-1); cursor.step='1';
      inspect(selectionIndex === null ? result.dates.length-1 : selectionIndex);
      emphasize();
    }
    function table() {
      const body = $('table'); body.replaceChildren();
      if (!result.series.length) { const row=element('tr'),cell=element('td','','No shared period is available for this selection.');cell.colSpan=4;row.append(cell);body.append(row);return; }
      result.series.forEach(series => {
        const row=element('tr'),label=element('th','',series.name);label.scope='row';
        label.append(element('small','',series.kind==='research'?(comparisonMode?'RESEARCH SERIES':'RESEARCH BACKTEST'):'ETF · DISTRIBUTIONS REINVESTED'));row.append(label);
        ['change','cagr','drawdown'].forEach(key => {
          const value=series.metrics[key],cell=element('td','',typeof value==='number'&&Number.isFinite(value)?percentage.format(value):'—');
          if (key==='cagr' && (value===null||value===undefined))cell.title='Annualized growth requires at least one year of shared observations.';
          row.append(cell);
        });
        body.append(row);
      });
    }
    function legend() {
      const list=$('legend');list.replaceChildren();
      result.series.forEach(series=>{
        const item=element('li'),swatch=element('span','sr-legend-swatch');swatch.style.backgroundColor=palette[series.id]||'#b4968e';swatch.setAttribute('aria-hidden','true');
        if (comparisonMode) {
          const button=element('button','sr-legend-button');button.type='button';button.dataset.srEmphasize=series.id;button.setAttribute('aria-label','Emphasize '+series.name);button.setAttribute('aria-pressed',String(emphasizedId===series.id));
          if(series.kind==='etf')swatch.classList.add('is-dashed');
          button.append(swatch,document.createTextNode(series.name));button.addEventListener('click',()=>{emphasizedId=emphasizedId===series.id?null:series.id;emphasize();});item.append(button);
        } else item.append(swatch,document.createTextNode(series.name));
        list.append(item);
      });
    }
    function emphasize() {
      if (!comparisonMode) return;
      all('[data-sr-line]').forEach(item=>item.classList.toggle('is-muted',Boolean(emphasizedId && item.dataset.srLine!==emphasizedId)));
      all('[data-sr-emphasize]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.srEmphasize===emphasizedId)));
    }
    function render() {
      if (customDates) customDates.hidden = period !== 'CUSTOM';
      all('[data-sr-period]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.srPeriod===period)));
      all('[data-sr-scale]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.srScale===scale)));
      if (!research) return;
      all('[data-sr-choice]').forEach(input=>{input.checked=ids.includes(input.value);});
      if (comparisonMode) {
        const researchCount=research.series.filter(series=>ids.includes(series.id)).length,etfCount=ids.filter(id=>ETF_IDS.includes(id)).length;
        write('selection-status',researchCount+' research series · '+etfCount+' ETF'+(etfCount===1?'':'s'));
      }
      try {
        if (period === 'CUSTOM' && !customDatesInitialized) {
          const available=window.HetzerkResearchMath.compare(research,market||{series:[]},{ids,period:'ALL'});
          if (!startDate.value && available.start) startDate.value=available.start;
          if (!endDate.value && available.end) endDate.value=available.end;
          customDatesInitialized=true;
        }
        result=window.HetzerkResearchMath.compare(research,market||{series:[]},{ids,period,startDate:startDate&&startDate.value,endDate:endDate&&endDate.value});
        write('date-error','');
        if (startDate) { startDate.removeAttribute('aria-invalid');endDate.removeAttribute('aria-invalid'); }
        if(emphasizedId && !result.series.some(series=>series.id===emphasizedId))emphasizedId=null;
        write('status',result.dates.length+' shared month-end observations');
        write('range',result.start?date(result.start)+' — '+date(result.end)+' · Starting value 100':'No shared monthly history');
        write('coverage-note',result.coverageNote||'');$('coverage-note').hidden=!result.coverageNote;
        const messages=[...(result.warnings||[]),...(result.excluded||[]).map(item=>item.id+': '+item.reason)];
        if(missingMarket)messages.push('ETF observations could not be loaded. The source research record remains available.');
        warning(messages.join(' '));
        write('unit','Growth of 100 · '+(scale==='log'?'logarithmic':'linear')+' scale');
        legend();table();plot();
      } catch(failure){
        warning(period==='CUSTOM'?'':failure.message);write('date-error',period==='CUSTOM'?failure.message:'');
        if (period==='CUSTOM' && startDate) { startDate.setAttribute('aria-invalid','true');endDate.setAttribute('aria-invalid','true'); }
        write('status','Research comparison unavailable');write('range','Choose a valid date range.');write('coverage-note','');$('coverage-note').hidden=true;
        result={series:[],dates:[],reason:failure.message};legend();table();plot();
      }
    }
    all('[data-sr-period]').forEach(button=>button.addEventListener('click',()=>{period=button.dataset.srPeriod;selectionIndex=null;render();save();}));
    if (customDates) {
      [startDate,endDate].forEach(input=>input.addEventListener('change',()=>{customDatesInitialized=true;selectionIndex=null;render();save();}));
      customDates.addEventListener('submit',event=>{event.preventDefault();selectionIndex=null;render();save();});
    }
    all('[data-sr-scale]').forEach(button=>button.addEventListener('click',()=>{scale=button.dataset.srScale;save();render();}));
    all('[data-sr-select]').forEach(button=>button.addEventListener('click',()=>{
      if(!research)return;
      const action=button.dataset.srSelect;
      if(action==='none')ids=[];
      else if(action==='reference')ids=[referenceId];
      else {
        const researchIDs=[referenceId,...research.series.map(series=>series.id).filter(id=>id!==referenceId)];
        const etfIDs=action==='all'?all('[data-sr-choice]').filter(input=>ETF_IDS.includes(input.value)&&!input.disabled).map(input=>input.value):ids.filter(id=>ETF_IDS.includes(id));
        ids=[...researchIDs,...etfIDs];
      }
      selectionIndex=null;emphasizedId=null;save();render();
    }));
    cursor.addEventListener('input',()=>inspect(Number(cursor.value)));
    function pointer(event){if(!geometry||!result)return;const box=chart.getBoundingClientRect(),position=(event.clientX-box.left)/box.width*geometry.width,index=Math.round((position-geometry.left)/(geometry.width-geometry.left-geometry.right)*(result.dates.length-1));inspect(index);}
    chart.addEventListener('pointermove',pointer);chart.addEventListener('pointerdown',pointer);
    if(typeof ResizeObserver==='function'){let lastWidth=0,frame=null;new ResizeObserver(entries=>{const width=Math.round(entries[0].contentRect.width);if(!width||width===lastWidth)return;lastWidth=width;if(frame!==null)cancelAnimationFrame(frame);frame=requestAnimationFrame(plot);}).observe(chart.parentElement);}
    document.addEventListener('hetzerk:research-view',()=>requestAnimationFrame(plot));
    async function load(){
      try {
        if(!window.HetzerkResearchMath)throw new Error('The monthly research calculator did not load.');
        const loaded=await Promise.allSettled([fetchJSON($('research-link').href),fetchJSON($('market-link').href)]);
        if(loaded[0].status!=='fulfilled')throw loaded[0].reason;
        research=loaded[0].value;
        window.HetzerkResearchMath.researchSeries(research);
        if(comparisonMode && typeof research.reference_series_id==='string')referenceId=research.reference_series_id;
        if(loaded[1].status==='fulfilled')market=loaded[1].value;else missingMarket=true;
        choices();source();render();
      }catch(failure){write('status','Source observations unavailable');warning(failure.message+' No research observations have been estimated.');result=null;plot();write('empty','The monthly source record is unavailable. Please reconnect and reload this page.');}
    }
    load();
  });

  const tabs=Array.from(document.querySelectorAll('[data-comparison-view]'));
  if(tabs.length){
    const panels=Array.from(document.querySelectorAll('[data-comparison-view-panel]'));
    function select(view,focus=false){
      if(!['etf','research'].includes(view))view='etf';
      tabs.forEach(tab=>{const active=tab.dataset.comparisonView===view;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;if(active&&focus)tab.focus();});
      panels.forEach(panel=>{panel.hidden=panel.dataset.comparisonViewPanel!==view;});
      const status=document.querySelector('.compare-data-status');if(status)status.hidden=view==='research';
      const error=document.getElementById('comparison-error');if(error)error.style.display=view==='research'?'none':'';
      const dock=document.querySelector('.compare-dock a[href="#comparison-research"]');if(dock)dock.classList.toggle('is-research-active',view==='research');
      try{localStorage.setItem('hetzerk-comparison-view',view);}catch(_){}
      document.dispatchEvent(new Event('hetzerk:research-view'));
    }
    tabs.forEach((tab,index)=>{
      tab.addEventListener('click',()=>select(tab.dataset.comparisonView));
      tab.addEventListener('keydown',event=>{
        let next=null;if(event.key==='ArrowRight')next=(index+1)%tabs.length;else if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;
        if(next!==null){event.preventDefault();select(tabs[next].dataset.comparisonView,true);}
      });
    });
    document.querySelectorAll('.compare-dock a').forEach(link=>link.addEventListener('click',()=>select(link.getAttribute('href')==='#comparison-research'?'research':'etf')));
    const params=new URL(location.href).searchParams;let initial=params.get('view');
    if(!initial&&location.hash==='#comparison-research')initial='research';
    if(!initial){try{initial=localStorage.getItem('hetzerk-comparison-view');}catch(_){}}
    select(initial||'research');
  }
})();
