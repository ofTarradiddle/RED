/* Innovation Atlas: sourced history, native browser interaction, fictional capital. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const cash = value => Number.isFinite(value) ? value.toLocaleString('en-US', {style:'currency',currency:'USD',maximumFractionDigits:2}) : '—';
const compactCash = value => Number.isFinite(value) ? value.toLocaleString('en-US', {style:'currency',currency:'USD',notation:Math.abs(value)>=10000?'compact':'standard',maximumFractionDigits:Math.abs(value)>=10000?1:2}) : '—';
const percent = value => Number.isFinite(value) ? `${value>0?'+':''}${(value*100).toLocaleString('en-US',{maximumFractionDigits:2,minimumFractionDigits:2})}%` : '—';
const count = value => Number(value || 0).toLocaleString('en-US');
const dateText = (date, precision) => { if (!date) return 'Date unavailable'; if (precision==='year'||date.length===4) return date.slice(0,4); const parsed=new Date((date.length===7?date+'-01':date.slice(0,10))+'T12:00:00Z'); return Number.isNaN(+parsed)?date:parsed.toLocaleDateString('en-US',{year:'numeric',month:'short',...(precision==='month'||date.length===7?{}:{day:'numeric'}),timeZone:'UTC'}); };
const storage = {get(key){try{return localStorage.getItem(key);}catch{return null;}},set(key,value){try{localStorage.setItem(key,value);return true;}catch{return false;}}};
const KEYS = {save:'hetzerk-innovation-game-v1',scores:'hetzerk-innovation-scores-v1',motion:'hetzerk-innovation-motion-v1'};
const eras = {
  all:['1960—','The compounding of ideas.','Pivotal moments, followed by the companies and products they helped make possible.'],
  1960:['1960s','The architecture of possibility.','Compatible computers, integrated circuits and new interfaces lay foundations that will outlive their inventors.'],
  1970:['1970s','A computer on a chip.','Processing power begins its migration from the institution to the individual. Smaller circuits open larger markets.'],
  1980:['1980s','The personal becomes powerful.','The computer reaches the desk. Software, interfaces and networks become businesses in their own right.'],
  1990:['1990s','Everything starts to connect.','The browser, the network and the mobile phone redraw the boundaries of distribution—and investor expectations.'],
  2000:['2000s','From products to platforms.','Search, cloud computing and the smartphone turn individual tools into connected systems. Scale changes the economics.'],
  2010:['2010s','Intelligence, at the edge.','Accelerated computing, new architectures and connected devices expand what software can do in the physical world.'],
  2020:['2020s','A new kind of machine.','Models, accelerators and new computing platforms create another contest between technical possibility and economic value.']
};
let data, config={}, records=[], firms=new Map(), view='atlas', era='all', shown=24, game=null, gameBusy=false, pendingSales=new Set(), selectedAmount=0, scoreScope='local', detailRecord=null, detailPeriod='all';
let paused=storage.get(KEYS.motion)==='paused'||matchMedia('(prefers-reduced-motion: reduce)').matches;
let setSceneEra=()=>{}, sceneVisibility=()=>{};
const core=()=>window.InnovationGame;

function sourceURL(value){try{const url=new URL(value);return url.protocol==='https:'?url.href:null;}catch{return null;}}
function sourcesHTML(sources){const seen=new Set();return (sources||[]).flatMap(source=>{const raw=typeof source==='string'?source:source.url||source.sourceUrl;const url=sourceURL(raw);if(!url||seen.has(url))return[];seen.add(url);const label=typeof source==='string'?new URL(url).hostname.replace(/^www\./,''):source.title||source.label||new URL(url).hostname;return `<li><a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(label)} <span aria-hidden="true">↗</span></a></li>`;}).join('');}
function preciseDay(record){const raw=record.eventDate||record.date||String(record.year||'');if(/^\d{4}$/.test(raw))return raw+'-12-31';if(/^\d{4}-\d{2}$/.test(raw)){const [year,month]=raw.split('-').map(Number);return new Date(Date.UTC(year,month,0)).toISOString().slice(0,10);}return raw.slice(0,10);}
function yearOf(record){return Number(String(record.originalDate||record.eventDate||record.date||record.year||'1960').slice(0,4));}
function recordDate(record){return dateText(record.originalDate||record.eventDate||record.date,record.datePrecision);}
function readable(value){if(typeof value==='string')return value;if(Array.isArray(value))return value.map(readable).filter(Boolean).join(' ');if(value&&typeof value==='object')return value.text||value.summary||value.description||value.thesis||'';return '';}
function firmFor(record){return firms.get(record.assetId)||{name:record.company||record.assetId||'Company attribution unavailable',ticker:record.assetId||'',points:[]};}
function latestPath(record,period='all'){
  const asset=firmFor(record),after=preciseDay(record);
  const eligible=(asset.points||[]).filter(point=>(record._landmark?point.date>=record.date:point.date>after)&&Number.isFinite(point.adjustedClose)&&point.adjustedClose>=0);
  const firstPositive=eligible.findIndex(point=>point.adjustedClose>0),usable=firstPositive<0?[]:eligible.slice(firstPositive);
  if(!usable.length)return {points:[],asset,after};
  let limit=data.asOf;if(period!=='all'){const end=new Date(usable[0].date+'T12:00:00Z');end.setUTCFullYear(end.getUTCFullYear()+Number(period));limit=end.toISOString().slice(0,10);}
  const points=usable.filter(point=>point.date<=limit).map(point=>({date:point.date,value:100*point.adjustedClose/usable[0].adjustedClose}));
  return {points,asset,after,first:points[0],last:points.at(-1),change:points.length>1?points.at(-1).value/100-1:null};
}

function glyph(record){
  const text=(record.category+' '+record.title).toLowerCase();
  let type=/typewriter/.test(text)?'typewriter':/747|aircraft/.test(text)?'aircraft':/chip|semiconductor|processor|silicon|computing|micro|gpu|architecture/.test(text)?'chip':/network|web|internet|cloud|connect|search|browser/.test(text)?'network':/software|operating|code|windows|database|platform/.test(text)?'code':/phone|mobile|display|interface|ipod|tablet|ipad|watch/.test(text)?'device':/bio|health|drug|medicine|science/.test(text)?'molecule':'orbit';
  const frame='<svg viewBox="0 0 180 150" fill="none" aria-hidden="true"><g stroke="currentColor" stroke-width="1.2" stroke-linejoin="round">';
  const chip=`<path d="M39 54 90 26l52 28v44l-52 29-51-29Z" fill="#e6d8c3"/><path d="M39 54 90 83l52-29M90 83v44"/><path d="M60 55 90 38l30 17-30 17Z" fill="currentColor" opacity=".78"/>${Array.from({length:6},(_,i)=>`<path d="M${42+i*8} ${65+i*4.5}l-10 6M${97+i*8} ${110-i*4.5}l10 6M${43+i*8} ${47-i*4.5}l-11-6M${96+i*8} ${28+i*4.5}l11-6"/>`).join('')}<path d="m68 56 22 12 21-12" stroke="#ede5d5"/>`;
  const network=`<ellipse cx="90" cy="77" rx="54" ry="49" stroke-opacity=".25"/><ellipse cx="90" cy="77" rx="24" ry="49"/><path d="M36 77h108M47 48c25 14 61 14 86 0M47 107c25-14 61-14 86 0M53 37l73 77M37 100l105-49" stroke-opacity=".5"/>${[[90,28],[36,77],[142,61],[78,123],[122,104],[91,76]].map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="${i===5?9:5}" fill="${i===5?'currentColor':'#ede5d5'}"/>`).join('')}`;
  const code='<path d="m35 45 60-18 52 28-61 19Z" fill="#e8dcc7"/><path d="m35 45 0 51 52 29V74m60-19v51l-60 19"/><path d="m35 60 52 29 60-19M35 77l52 30 60-19" stroke-opacity=".3"/><path d="m72 45-9 3 9 5m34-12 10 4-10 4m-17-10-4 16" stroke-width="2"/>';
  const device='<path d="m64 23 52 17c5 2 7 7 6 12l-13 70c-1 6-5 9-10 7l-49-17c-5-2-7-6-6-11l13-72c1-5 3-7 7-6Z" fill="#e7d9c3"/><path d="m62 34 49 16-11 63-48-16Z" fill="currentColor" opacity=".8"/><path d="m73 56 24 8m-27 5 24 8m-27 5 16 6" stroke="#ede5d5" stroke-opacity=".6"/><circle cx="77" cy="113" r="3"/>';
  const molecule='<path d="m44 76 32-44 46 23 16 42-51 27-43-48 78-21-35 69-11-92 62 65-94-21" stroke-opacity=".55"/><circle cx="44" cy="76" r="13" fill="#e7d9c3"/><circle cx="76" cy="32" r="8" fill="currentColor"/><circle cx="122" cy="55" r="15" fill="#e7d9c3"/><circle cx="138" cy="97" r="9" fill="currentColor"/><circle cx="87" cy="124" r="12" fill="#e7d9c3"/>';
  const orbit='<ellipse cx="90" cy="77" rx="65" ry="27" transform="rotate(-28 90 77)"/><ellipse cx="90" cy="77" rx="65" ry="27" transform="rotate(35 90 77)" stroke-opacity=".4"/><ellipse cx="90" cy="77" rx="65" ry="27" transform="rotate(92 90 77)" stroke-opacity=".6"/><path d="m90 53 21 12v25l-21 13-22-13V65Z" fill="#e6d8c3"/><path d="m68 65 22 13 21-13M90 78v25"/><circle cx="33" cy="105" r="4" fill="currentColor"/><circle cx="128" cy="29" r="4" fill="currentColor"/>';
  const typewriter='<path d="M36 81h108l10 35H26Z" fill="#e7d9c3"/><path d="M48 81V54h83v27" fill="#e6d8c3"/><path d="M58 58V29h64v29Z" fill="#f7f3e9"/><path d="M68 38h41M68 45h31" stroke-opacity=".5"/><path d="M43 60h95v16H43Z" fill="currentColor" opacity=".8"/><path d="M47 104h87M40 110h101" stroke-width="3"/><path d="M32 118v7h119v-7"/> <circle cx="92" cy="68" r="6" fill="#e7d9c3"/>'+Array.from({length:9},(_,i)=>`<circle cx="${47+i*11}" cy="91" r="2" fill="currentColor"/><circle cx="${44+i*11}" cy="99" r="2" fill="currentColor"/>`).join('');
  const aircraft='<path d="m84 28 7-8 7 8 3 36 57 40v7l-57-20-1 28 16 12v5l-25-7-25 7v-5l16-12-1-28-57 20v-7l57-40Z" fill="#e7d9c3"/><path d="M91 37v77M44 99l37-20m20 0 37 20" stroke-opacity=".45"/><path d="m64 89-1 14m55-14 1 14" stroke-width="5"/>';
  return frame+({chip,network,code,device,molecule,orbit,typewriter,aircraft}[type])+'</g></svg>';
}

function chart(container,series,{label='Observed portfolio value',log=false}={}){
  const active=series.filter(item=>item.points?.length);
  if(!active.length){container.innerHTML='<p class="ia-chart-empty">No verified observations are available for this window.</p>';return;}
  const width=880,height=310,left=68,right=18,top=22,bottom=46;
  const rows=active.flatMap(item=>item.points).filter(p=>Number.isFinite(p.value)&&p.value>=0);
  if(!rows.length)return;
  const dates=rows.map(p=>Date.parse(p.date+'T00:00:00Z')),start=Math.min(...dates),end=Math.max(...dates);
  let low=Math.min(...rows.map(p=>p.value)),high=Math.max(...rows.map(p=>p.value));
  log=log&&low>0&&high/low>3;
  if(log){low=Math.log10(low);high=Math.log10(high);}
  const span=high-low||Math.max(high*.1,1);low-=span*.1;high+=span*.14;if(!log)low=Math.max(0,low);
  const x=date=>left+(Date.parse(date+'T00:00:00Z')-start)/Math.max(end-start,1)*(width-left-right);
  const y=value=>top+(high-(log?Math.log10(value):value))/(high-low)*(height-top-bottom);
  const grid=Array.from({length:4},(_,i)=>{const value=low+(high-low)*i/3,yy=top+(1-i/3)*(height-top-bottom);return `<path d="M${left} ${yy}H${width-right}" stroke="#b79b721b"/><text x="${left-12}" y="${yy+4}" text-anchor="end">${escape(compactCash(log?10**value:value))}</text>`;}).join('');
  const ticks=[.18,.5,.82].map(ratio=>{const value=new Date(start+(end-start)*ratio);return `<text x="${left+(width-left-right)*ratio}" y="${height-12}" text-anchor="middle">${escape(value.toLocaleDateString('en-US',{month:'short',year:'2-digit',timeZone:'UTC'}))}</text>`;}).join('');
  const lines=active.map((item,index)=>{const path=item.points.map((p,i)=>`${i?'L':'M'}${x(p.date).toFixed(2)} ${y(p.value).toFixed(2)}`).join(' ');return `${index===0?`<path d="${path}L${x(item.points.at(-1).date)} ${height-bottom}H${x(item.points[0].date)}Z" fill="url(#ia-fill-${container.id})"/>`:''}<path class="ia-plot-line" d="${path}" fill="none" stroke="${item.color||'#c4a476'}" stroke-width="${index===0?2.7:1.6}" stroke-linecap="round" ${index?'stroke-dasharray="5 5"':''}/>${item.points.length===1?`<circle cx="${x(item.points[0].date)}" cy="${y(item.points[0].value)}" r="4" fill="${item.color||'#c4a476'}"/>`:''}`;}).join('');
  container.innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(label)}"><title>${escape(label)}${log?' (logarithmic value scale)':''}</title><defs><linearGradient id="ia-fill-${container.id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bf986c" stop-opacity=".13"/><stop offset="1" stop-color="#bf986c" stop-opacity="0"/></linearGradient></defs>${grid}${ticks}${lines}</svg><div class="ia-chart-legend">${active.map(item=>`<span style="--series-color:${item.color||'#c4a476'}">${escape(item.name)}</span>`).join('')}${log?'<span>Logarithmic value scale</span>':''}</div>`;
  $$('path.ia-plot-line',container).forEach(path=>{try{path.style.setProperty('--path-length',String(path.getTotalLength()));}catch{}});
  container.tabIndex=0;container.setAttribute('role','figure');container.setAttribute('aria-label',label+'. Use left and right arrow keys to inspect observations.');
  const tooltip=document.createElement('div');tooltip.className='ia-chart-tooltip';tooltip.hidden=true;container.append(tooltip);
  let inspected=active[0].points.length-1;
  const inspect=index=>{
    inspected=Math.max(0,Math.min(active[0].points.length-1,index));const point=active[0].points[inspected];
    tooltip.innerHTML=`<strong>${escape(dateText(point.date))}</strong>`+active.map(item=>{const observed=item.points.findLast(p=>p.date<=point.date);return observed?`<span>${escape(item.name)}<b>${escape(cash(observed.value))}</b></span>`:'';}).join('');
    tooltip.hidden=false;const rect=container.getBoundingClientRect();tooltip.style.left=Math.max(8,Math.min(rect.width-260,x(point.date)/width*rect.width-125))+'px';
  };
  container.onpointermove=event=>{const rect=$('svg',container).getBoundingClientRect(),target=start+((event.clientX-rect.left)/rect.width*width-left)/(width-left-right)*(end-start);let nearest=0,best=Infinity;active[0].points.forEach((point,i)=>{const distance=Math.abs(Date.parse(point.date+'T00:00:00Z')-target);if(distance<best){nearest=i;best=distance;}});inspect(nearest);};
  container.onpointerleave=()=>{tooltip.hidden=true;};container.onfocus=()=>inspect(inspected);container.onblur=()=>{tooltip.hidden=true;};
  container.onkeydown=event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();inspect(inspected+(event.key==='ArrowLeft'?-1:1));}else if(event.key==='Escape'&&!tooltip.hidden){event.preventDefault();event.stopPropagation();tooltip.hidden=true;}};
}

function filteredRecords(){
  const term=$('#atlas-search').value.trim().toLowerCase(),company=$('#atlas-company').value,collection=$('#atlas-collection').value;
  return records.filter(record=>(era==='all'||Math.floor(yearOf(record)/10)*10===Number(era))&&(company==='all'||record.assetId===company)&&(collection==='all'||(collection==='landmarks'?record._landmark:!record._landmark))&&(!term||`${record.title} ${record.summary||record.description||''} ${firmFor(record).name} ${record.assetId} ${record.category||''}`.toLowerCase().includes(term)));
}
function renderCards(reset=true){
  if(!data)return;if(reset)shown=24;
  const filtered=filteredRecords(),display=filtered.slice(0,shown);
  $('#result-count').textContent=`${count(filtered.length)} records · ${count(display.length)} shown`;
  $('#innovation-cards').innerHTML=display.map((record,index)=>{
    const asset=firmFor(record),path=record._landmark?latestPath(record):null;
    const summary=record.summary||record.description||(record._landmark?'A sourced moment in this company’s history.':'A company-linked product or software record from the structured archive.');
    return `<button type="button" class="ia-card ${record._landmark?'kind-landmark':'kind-catalog'}" data-record="${escape(record.id)}" style="--order:${Math.min(index%24,10)}"><span class="ia-card-top"><span class="ia-card-date">${escape(recordDate(record))}</span><span>${record._landmark?'LANDMARK':'ARCHIVE'}</span></span><span class="ia-card-art">${glyph(record)}<span class="glyph-ticker">${escape(asset.ticker||'')}</span></span><span class="ia-card-body"><span class="ia-eyebrow">${escape(asset.name)}</span><h3>${escape(record.title)}</h3><span class="ia-card-summary">${escape(summary)}</span><span class="ia-card-bottom"><span>${record._landmark?'$100 / available history':'OPEN THE RECORD'}</span><strong>${path?.last?escape(compactCash(path.last.value)):'↗'}</strong></span></span></button>`;
  }).join('');
  $('#load-more').hidden=display.length>=filtered.length;$('#archive-empty').hidden=filtered.length!==0;
  $$('[data-record]',$('#innovation-cards')).forEach(button=>button.addEventListener('click',()=>openRecord(button.dataset.record)));
}
function chooseEra(value){era=value;const copy=eras[value]||eras.all;$('#era-number').textContent=copy[0];$('#era-title').textContent=copy[1];$('#era-copy').textContent=copy[2];$('#hero-year').textContent=value==='all'?'1960':value;$$('[data-era]').forEach(button=>{const active=button.dataset.era===value;button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});setSceneEra(value==='all'?1960:Number(value));renderCards();}

function openRecord(id){
  const record=records.find(item=>item.id===id);if(!record)return;
  detailRecord=record;detailPeriod='all';const asset=firmFor(record);
  const links=[...(record.sourceUrls||record.source_urls||[]),...(record.sourceUrl?[record.sourceUrl]:[]),...(asset.sourceUrl?[asset.sourceUrl]:[])];
  const outline=record._landmark?readable(record.decision?.investmentThesis)||record.summary:record.description||record.summary||'This item is attributed to the company in the structured discovery archive. A separately researched commercialization history has not yet been attached to this individual record.';
  const spillovers=readable(record.outcome?.spillovers)||readable(record.spillovers);
  $('#detail-content').innerHTML=`<div class="ia-detail-hero"><div><p class="ia-eyebrow">${escape(asset.name)} / ${escape(recordDate(record))}</p><h2 id="detail-title">${escape(record.title)}</h2><p class="ia-detail-attribution">${escape(record.attributionRole||record.relationship||'Company-linked manufacturer / developer record')} · ${record._landmark?'Researched landmark':'Structured discovery record'}</p></div><div class="ia-card-art">${glyph(record)}</div></div><div class="ia-detail-body"><section class="ia-lifecycle"><div class="ia-lifecycle-head"><div><p class="ia-eyebrow">THE SHAREHOLDER’S PATH</p><h3>If $100 followed the company.</h3><p id="detail-return-dates"></p></div><div class="ia-lifecycle-number"><strong id="detail-return-value">—</strong><span id="detail-return-percent"></span></div></div><div id="detail-chart" class="ia-return-chart"></div><div class="ia-periods" role="group" aria-label="Investment window after innovation"><button data-life-period="1" aria-pressed="false">First year</button><button data-life-period="3" aria-pressed="false">3 years</button><button data-life-period="10" aria-pressed="false">10 years</button><button data-life-period="all" class="is-active" aria-pressed="true">Through latest</button></div><p class="ia-small" id="detail-history-note"></p></section><div class="ia-detail-copy"><article><h3>The firm behind the idea.</h3><p>${escape(asset.story||'A longer independently sourced company profile has not yet been added.')}</p></article><article><h3>Bringing it to market.</h3><p>${escape(outline)}</p></article><article><h3>What it made possible.</h3><p>${escape(spillovers||'Individual spillover effects have not been independently established for this catalog item. Explore the linked record and the company’s researched landmarks for context.')}</p></article><article><h3>What investors received.</h3><p>These are whole-company, provider-adjusted returns over the available period. Other products, valuation, the economic cycle and later decisions also shaped the outcome. This is not a causal estimate of the value created by this one innovation.</p></article><article class="ia-full"><h3>Follow the evidence.</h3><ul>${sourcesHTML(links)||'<li>No primary link is attached to this archive record.</li>'}</ul></article></div><p class="ia-record-note">${record._landmark?'The landmark narrative has been separately researched.':'Archive attribution follows manufacturer/developer links; ownership at the historical event date has not been independently reconstructed. A product release is not necessarily a new invention.'} ${record.datePrecision==='year'?'Only the year is established. Return calculations begin conservatively at the first available quote after year end.':record.datePrecision==='month'?'Only the month is established. Return calculations begin after that month ends.':''}</p></div>`;
  $$('[data-life-period]',$('#detail-content')).forEach(button=>button.addEventListener('click',()=>{detailPeriod=button.dataset.lifePeriod;renderDetailReturn();}));
  renderDetailReturn();$('#innovation-detail').showModal();document.body.style.overflow='hidden';history.replaceState(null,'',`#innovation=${encodeURIComponent(id)}`);
}
function renderDetailReturn(){
  const path=latestPath(detailRecord,detailPeriod);$$('[data-life-period]').forEach(button=>{const active=button.dataset.lifePeriod===detailPeriod;button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});
  $('#detail-return-value').textContent=path.last?compactCash(path.last.value):'Unavailable';$('#detail-return-percent').textContent=path.change===null||path.change===undefined?'':percent(path.change);
  $('#detail-return-dates').textContent=path.first?`${dateText(path.first.date)} — ${dateText(path.last.date)}`:'No verified public price history for this selection.';
  const gap=path.first?(Date.parse(path.first.date)-Date.parse(path.after))/86400000:0;
  $('#detail-history-note').textContent=path.first?`${gap>35?'Price coverage begins later than this milestone; the return starts at the first available observation. ':''}Nominal USD · dividends and splits incorporated by the provider. ${path.points.length===1?'One observation does not establish a return. ':''}The window is limited to observed history through ${dateText(path.last.date)}.`:'Unavailable history is not a zero return. Private periods and missing or delisted share histories are not fabricated.';
  chart($('#detail-chart'),[{name:`${path.asset.ticker||path.asset.name} · $100 starting value`,points:path.points,color:'#c4a476'}],{label:`${path.asset.name} provider-adjusted value of $100 after ${detailRecord.title}`,log:true});
}
function closeDetail(){if($('#innovation-detail').open)$('#innovation-detail').close();document.body.style.overflow='';if(location.hash.startsWith('#innovation='))history.replaceState(null,'','#chronicle');}

function showView(next){
  if(!['atlas','game','scores'].includes(next))return;view=next;
  ['atlas','game','scores'].forEach(name=>{$(`#${name}-view`).hidden=name!==next;});
  $$('.ia-header [data-view]').forEach(button=>{const active=button.dataset.view===next;button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});
  sceneVisibility(next==='atlas');if(next==='scores')renderLeaderboard();
  if(next==='game'&&game)renderGame();window.scrollTo({top:0,behavior:paused?'instant':'smooth'});
}
function saveProgress(){if(!game)return;const saved=storage.set(KEYS.save,core().serialize(game));if(!saved)$('#saved-status').textContent='This browser cannot save progress. Keep this page open to continue your journey.';}
function availableCash(){if(!game)return 0;const book=core().portfolio(data,game);return book.cash+book.positions.filter(position=>pendingSales.has(position.assetId)&&position.canSell).reduce((sum,position)=>sum+position.value,0);}
function setAllocation(value,mode='percent'){
  const available=availableCash();selectedAmount=mode==='percent'?available*Math.max(0,Math.min(100,Number(value)||0))/100:Math.max(0,Number(value)||0);
  if(mode==='percent'&&Number(value)!==100)selectedAmount=Math.floor(selectedAmount*100)/100;
  $('#allocation-amount').value=Number.isFinite(selectedAmount)?selectedAmount.toFixed(2):'0.00';$('#allocation-amount').max=available.toFixed(2);
  const pct=available>0?Math.min(100,selectedAmount/available*100):0;$('#allocation-slider').value=String(pct);$('#allocation-percent').textContent=`${Math.round(pct)}% of available cash`;
  $('#allocation-help').textContent=`${cash(available)} available${pendingSales.size?' after selected sales':''}. Fractional return-index positions; no borrowing.`;
}
function startGame(){
  if(!data)return;try{game=core().createGame(data);pendingSales.clear();saveProgress();$('#game-error').hidden=true;$('#game-intro').hidden=true;showView('game');renderGame();}catch(error){$('#saved-status').textContent=error.message;}
}
function renderGame(){
  if(!game)return;$('#game-intro').hidden=true;$('#game-active').hidden=game.status!=='active';$('#game-finish').hidden=game.status==='active';
  if(game.status!=='active'){renderFinish();return;}
  const card=core().currentDecision(data,game),book=core().portfolio(data,game),event=data.opportunities.find(item=>item.id===card.id);
  $('#game-counter').textContent=`/ ${card.number} OF ${card.total}`;$('#game-year').textContent=card.date.slice(0,4);$('#game-date-label').textContent=dateText(card.date);$('#game-progress-fill').style.width=`${game.index/card.total*100}%`;
  $('#portfolio-value').textContent=cash(book.value);$('#portfolio-cash').textContent=cash(book.cash);$('#portfolio-change').textContent=percent(book.change);$('#portfolio-benchmark').textContent=book.benchmark?cash(book.benchmark.value):'Unavailable';
  const benchmarkAsset=firms.get(data.benchmarkAssetId);$('#benchmark-title').textContent=book.benchmark?.from?`${benchmarkAsset?.ticker||'Market'} · from ${book.benchmark.from.slice(0,4)}`:`${benchmarkAsset?.ticker||'Market'} · cash before history`;
  $('#decision-company').textContent=card.firm.name;$('#decision-ticker').textContent=firms.get(card.assetId)?.ticker||'History only';$('#decision-title').textContent=card.title;$('#decision-art').innerHTML=glyph(event||card);
  $('#decision-known-at').textContent=`Decision: ${dateText(card.date)} · ${event?.datePrecision==='year'?'Event year '+event.originalDate:'After '+dateText(event?.eventDate||card.eventDate)} · Reconstructed decision brief`;
  $('#decision-opportunity').textContent=readable(card.decision.marketOpportunity)||'The opportunity must be weighed against competition, execution costs and the price investors are being asked to pay.';
  $('#decision-investment').textContent=readable(card.decision.investmentThesis)||readable(card.decision.investment)||'Company-wide spending is shown below when a dated filing is available. Product-specific investment has not been established.';
  $('#decision-risk').textContent=readable(card.decision.risks)||'Commercial adoption is uncertain. Rivals can imitate, costs can exceed expectations, and even a successful product can disappoint investors who pay too much.';
  const val=card.decision.valuation,invest=card.decision.investment;
  const metrics=[['Price / filed annual EPS',Number.isFinite(val?.pe)?`${val.pe.toFixed(1)}×`:null],['Annual R&D expense',Number.isFinite(invest?.rd)?compactCash(invest.rd):null],['R&D / annual revenue',Number.isFinite(invest?.rdToSales)?`${(invest.rdToSales*100).toFixed(1)}%`:null],['Annual revenue',Number.isFinite(invest?.revenue)?compactCash(invest.revenue):null]];
  $('#decision-financials').innerHTML=metrics.map(([label,value])=>`<div><dt>${escape(label)}</dt><dd${value?'':' class="is-missing"'}>${escape(value||'Not verified for this date')}</dd></div>`).join('');
  $('#decision-financial-note').textContent=invest?`Fiscal year ended ${dateText(invest.fiscalPeriodEnd)}; filing available ${dateText(invest.availableAt)}. Company-wide annual figures, not spending on this product. ${val?'P/E uses the latest filed positive full-year EPS; it is not forward or necessarily trailing-twelve-month P/E.':''}`:'Historical filing evidence is not available in this edition for these ratios. No current valuation or invented spending is substituted.';
  $('#decision-sources').innerHTML=sourcesHTML([...(event?.sourceUrls||[]),...(val?.sourceUrl?[val.sourceUrl]:[]),...(invest?.sourceUrl?[invest.sourceUrl]:[])]);
  $('#game-invest').disabled=!card.canInvest||gameBusy;$('#game-pass').disabled=gameBusy;
  $('#game-error').hidden=card.canInvest;if(!card.canInvest)$('#game-error').textContent=card.unavailableReason+' You can continue without investing.';
  renderHoldings(book);setAllocation(0);renderGameChart(book);renderTrades();
  $('#game-warnings').textContent=book.warnings.join(' ');
}
function renderHoldings(book){
  $('#holdings-count').textContent=`${book.positions.length} position${book.positions.length===1?'':'s'}`;
  $('#game-holdings').innerHTML=book.positions.length?book.positions.map(position=>`<div class="ia-holding"><div><strong>${escape(position.ticker)}</strong><span>${escape(cash(position.value))}</span><small>${position.stale?'Last quote ':''}${escape(dateText(position.quoteDate))}${!position.canSell?' · no trade quote today':''}</small></div><button type="button" data-sell="${escape(position.assetId)}" ${position.canSell?'':'disabled'} class="${pendingSales.has(position.assetId)?'is-selling':''}">${pendingSales.has(position.assetId)?'Undo sale':'Sell position'}</button></div>`).join(''):'<p class="ia-small">Your capital is in cash. Your first investment will appear here.</p>';
  $$('[data-sell]').forEach(button=>button.addEventListener('click',()=>{const id=button.dataset.sell;if(pendingSales.has(id))pendingSales.delete(id);else pendingSales.add(id);renderHoldings(core().portfolio(data,game));setAllocation(0);}));
  $('#sale-note').textContent=pendingSales.size?`${pendingSales.size} position${pendingSales.size===1?'':'s'} will be sold when you advance. Proceeds are included in available cash.`:'';
  $('#game-pass').textContent=pendingSales.size?'Sell selected & advance':'Keep my cash & advance';
}
function renderGameChart(book){
  chart($('#game-equity-chart'),[{name:'Your portfolio',color:'#c4a476',points:game.history.map(point=>({date:point.date,value:point.value}))},{name:firms.get(data.benchmarkAssetId)?.ticker||'Market reference',color:'#8eaaa3',points:game.history.filter(point=>point.benchmarkValue!==null).map(point=>({date:point.date,value:point.benchmarkValue}))}],{label:`Your portfolio from ${game.startDate} through ${game.date}`,log:true});
  $('#game-chart-note').textContent=`${dateText(game.startDate)} — ${dateText(game.date)} · ${cash(book.value)}`;
}
function renderTrades(){
  $('#game-trades').innerHTML=game.trades.length?game.trades.slice().reverse().map(trade=>`<div class="ia-trade-row"><span>${escape(dateText(trade.date))}</span><span>${escape(trade.side.toUpperCase())}</span><span>${escape(firms.get(trade.assetId)?.ticker||trade.assetId)}</span><span>${escape(cash(trade.amount))}</span></div>`).join(''):'<p class="ia-small">No trades yet. Passing preserves cash.</p>';
}
async function advance(invest){
  if(!game||gameBusy)return;gameBusy=true;
  try{
    const book=core().portfolio(data,game),amount=invest?selectedAmount:0;
    const sells=book.positions.filter(position=>pendingSales.has(position.assetId)).map(position=>({assetId:position.assetId,amount:position.value}));
    const previous=game;game=core().decide(data,game,{amount,sells});pendingSales.clear();saveProgress();renderGame();
    const value=core().portfolio(data,game).value;$('#ia-live').textContent=`Advanced to ${dateText(game.date)}. Portfolio value ${cash(value)}.`;
    const card=$('.ia-decision-card');card.classList.remove('ia-transition');void card.offsetWidth;card.classList.add('ia-transition');
    $('#game-error').hidden=true;if(game.status==='active'&&!core().currentDecision(data,game).canInvest){$('#game-error').hidden=false;$('#game-error').textContent=core().currentDecision(data,game).unavailableReason;}
    if(previous.date!==game.date)window.scrollTo({top:0,behavior:paused?'instant':'smooth'});
  }catch(error){$('#game-error').hidden=false;$('#game-error').textContent=error.message;}
  finally{setTimeout(()=>{gameBusy=false;if(game?.status==='active'){$('#game-invest').disabled=!core().currentDecision(data,game).canInvest;$('#game-pass').disabled=false;}},paused?0:400);}
}
function renderFinish(){
  const result=core().score(data,game),book=core().portfolio(data,game);
  $('#finish-title').innerHTML=game.status==='bankrupt'?'The capital is gone.<br><em>The lesson remains.</em>':'Time has<br><em>had its say.</em>';
  $('#finish-value').textContent=cash(result.endValue);$('#finish-description').textContent=`Your $100 became ${cash(result.endValue)} across ${result.decisions} decisions, ending ${dateText(result.endDate)}.`;
  chart($('#finish-chart'),[{name:'Your portfolio',color:'#c4a476',points:game.history.map(point=>({date:point.date,value:point.value}))},{name:firms.get(data.benchmarkAssetId)?.ticker||'Market reference',color:'#8eaaa3',points:game.history.filter(point=>point.benchmarkValue!==null).map(point=>({date:point.date,value:point.benchmarkValue}))}],{label:'Your completed historical investment journey',log:true});
  $('#finish-stats').innerHTML=[['Return on starting capital',percent(result.change)],['Investment decisions',count(result.investments)],['Market reference',cash(result.benchmarkValue)]].map(([label,value])=>`<div><strong>${escape(value)}</strong><span>${escape(label)}</span></div>`).join('');
  $('#score-status').textContent=result.comparable?'Save a verified replay to this device. A public submission is optional.':`This result cannot be ranked with standard completed games. ${result.warnings.join(' ')}`;
  $('#score-form button').disabled=!result.comparable;
  $('#finish-outcomes').innerHTML=core().outcomes(data,game).slice(-8).map(item=>{const event=data.opportunities.find(entry=>entry.id===item.opportunityId);return `<article><p class="ia-eyebrow">${escape(event?.assetId||'')}</p><h3>${escape(event?.title||'The outcome')}</h3><p>${escape(readable(item.outcome.spillovers)||readable(item.outcome))}</p></article>`;}).join('');
}

function localScores(){let saved;try{saved=JSON.parse(storage.get(KEYS.scores)||'[]');}catch{return[];}if(!Array.isArray(saved))return[];return saved.slice(0,100).flatMap(record=>{try{if(record.replay?.datasetId!==core().datasetId(data))return[];const verified=core().verifyScore(data,record);return verified.comparable?[{...verified,name:String(record.name||'Anonymous').slice(0,20),submittedAt:record.submittedAt}]:[];}catch{return[];}}).sort((a,b)=>b.endValue-a.endValue);}
async function saveScore(event){
  event.preventDefault();if(!game)return;
  const name=$('#player-name').value.normalize('NFKC').trim().replace(/\s+/g,' ').slice(0,20);if(!name||!/^[\p{L}\p{N} ._'-]+$/u.test(name)){$('#score-status').textContent='Use 1–20 letters, numbers, spaces or simple punctuation for your display name.';return;}
  try{const result=core().score(data,game);if(!result.comparable)throw new Error('This run is not eligible for the standard leaderboard.');let entries;try{entries=JSON.parse(storage.get(KEYS.scores)||'[]');}catch{entries=[];}if(!Array.isArray(entries))entries=[];
    const record={name,replay:result.replay,replayId:result.replayId,endValue:result.endValue,submittedAt:new Date().toISOString()};
    entries=entries.filter(item=>!(item.replayId===result.replayId&&item.replay?.datasetId===result.datasetId));entries.unshift(record);if(!storage.set(KEYS.scores,JSON.stringify(entries.slice(0,50))))throw new Error('This browser could not save the result. Download your decisions to keep a copy.');
    $('#score-status').textContent='Saved to this device. Your score was recalculated from your decisions.';
    if(config.leaderboardUrl){let button=$('#publish-score');if(!button){button=document.createElement('button');button.id='publish-score';button.type='button';button.className='ia-secondary';button.textContent='Publish this name and score across players ↗';button.style.marginTop='16px';$('#score-form').append(button);}button.hidden=false;button.disabled=false;button.onclick=()=>publishScore(name,result,button);}
  }catch(error){$('#score-status').textContent=error.message;}
}
async function publishScore(name,result,button){
  button.disabled=true;try{const response=await fetch(config.leaderboardUrl.replace(/\/$/,'')+'/scores',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,datasetId:result.datasetId,actions:result.replay.actions})});const payload=await response.json();if(!response.ok)throw new Error(payload.error||'The shared leaderboard is unavailable.');$('#score-status').textContent='Published. The server independently replayed your decisions.';button.hidden=true;}catch(error){$('#score-status').textContent=`Your device score is saved. ${error.message}`;button.disabled=false;}
}
async function renderLeaderboard(){
  if(!data)return;$$('[data-score-scope]').forEach(button=>{const active=button.dataset.scoreScope===scoreScope;button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});
  let rows=[];
  if(scoreScope==='local'){rows=localScores();$('#leaderboard-status').textContent=`This device · same data edition through ${dateText(data.asOf)} · scores verified from saved decisions.`;}
  else if(!config.leaderboardUrl){$('#leaderboard-status').textContent='Shared rankings are not connected yet. Your completed journeys can be saved on this device.';}
  else{try{$('#leaderboard-status').textContent='Loading verified player results…';const response=await fetch(config.leaderboardUrl.replace(/\/$/,'')+'/scores?datasetId='+encodeURIComponent(core().datasetId(data)));const payload=await response.json();if(!response.ok)throw new Error(payload.error||'Shared rankings could not be loaded.');rows=Array.isArray(payload.scores)?payload.scores:[];$('#leaderboard-status').textContent=`Across players · same data edition through ${dateText(payload.asOf||data.asOf)} · arithmetic verified by replay.`;}catch(error){$('#leaderboard-status').textContent=error.message;}}
  $('#leaderboard-body').innerHTML=rows.length?rows.slice(0,20).map((record,index)=>`<tr><td>${String(index+1).padStart(2,'0')}</td><td>${escape(record.name)}</td><td>${escape(cash(record.endValue))}</td><td>${escape(percent(record.change))}</td><td>${escape(count(record.decisions))}</td></tr>`).join(''):`<tr><td colspan="5" class="ia-leaderboard-empty">${scoreScope==='global'&&!config.leaderboardUrl?'Global rankings will appear when the public board opens.':'No completed journeys in this edition yet. Make the first one.'}</td></tr>`;
}
function downloadReplay(){if(!game)return;const blob=new Blob([core().serialize(game)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`hetzerk-innovation-decisions-${game.date}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

function setupEvents(){
  $$('[data-view]').forEach(button=>button.addEventListener('click',()=>showView(button.dataset.view)));
  $$('[data-era]').forEach(button=>button.addEventListener('click',()=>chooseEra(button.dataset.era)));
  $('#atlas-search').addEventListener('input',()=>renderCards());$('#atlas-company').addEventListener('change',()=>renderCards());$('#atlas-collection').addEventListener('change',()=>renderCards());
  $('#load-more').addEventListener('click',()=>{shown+=24;renderCards(false);});
  $('#detail-close').addEventListener('click',closeDetail);$('#innovation-detail').addEventListener('close',()=>{document.body.style.overflow='';if(location.hash.startsWith('#innovation='))history.replaceState(null,'','#chronicle');});
  $('#innovation-detail').addEventListener('click',event=>{if(event.target===$('#innovation-detail')){const rect=event.target.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeDetail();}});
  $('#game-start').addEventListener('click',startGame);$('#game-resume').addEventListener('click',()=>{try{game=core().restore(data,storage.get(KEYS.save));showView('game');renderGame();}catch(error){$('#saved-status').textContent=error.message;}});
  $('#game-restart').addEventListener('click',()=>$('#restart-dialog').showModal());$('#game-again').addEventListener('click',()=>$('#restart-dialog').showModal());$('#restart-confirm').addEventListener('click',()=>{$('#restart-dialog').close();startGame();});$('#restart-cancel').addEventListener('click',()=>$('#restart-dialog').close());
  $('#allocation-slider').addEventListener('input',event=>setAllocation(event.target.value));$('#allocation-amount').addEventListener('input',event=>{selectedAmount=Math.max(0,Number(event.target.value)||0);const available=availableCash(),pct=available?selectedAmount/available*100:0;$('#allocation-slider').value=String(Math.min(100,pct));$('#allocation-percent').textContent=`${Math.round(pct)}% of available cash`;});
  $$('[data-allocation]').forEach(button=>button.addEventListener('click',()=>setAllocation(button.dataset.allocation)));
  $('#game-invest').addEventListener('click',()=>advance(true));$('#game-pass').addEventListener('click',()=>advance(false));$('#score-form').addEventListener('submit',saveScore);$('#download-replay').addEventListener('click',downloadReplay);
  $$('[data-score-scope]').forEach(button=>button.addEventListener('click',()=>{scoreScope=button.dataset.scoreScope;renderLeaderboard();}));
  $('#motion-toggle').addEventListener('click',()=>{paused=!paused;storage.set(KEYS.motion,paused?'paused':'playing');applyMotion();});applyMotion();
}
function applyMotion(){document.body.classList.toggle('ia-motion-paused',paused);const button=$('#motion-toggle');button.innerHTML=paused?'Play motion <span aria-hidden="true">▷</span>':'Pause motion <span aria-hidden="true">Ⅱ</span>';button.setAttribute('aria-pressed',String(paused));button.setAttribute('aria-label',paused?'Resume decorative animation':'Pause decorative animation');sceneVisibility(view==='atlas');document.dispatchEvent(new Event('hetzerk:motion-change'));}

async function startScene(){
  const host=$('#innovation-scene');
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  let THREE,renderer;
  try{THREE=await import('./vendor/three/three.module.js');renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});}catch{return;}
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.setClearColor(0x171617,0);host.append(renderer.domElement);host.classList.add('has-webgl');
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(37,1,.1,80);camera.position.set(0,0,14);
  const group=new THREE.Group();scene.add(group);group.position.set(2.6,.1,0);
  scene.add(new THREE.AmbientLight(0xd8b594,1.7));const warm=new THREE.PointLight(0xffc481,65,24);warm.position.set(4,5,7);scene.add(warm);const red=new THREE.PointLight(0xb92b20,38,18);red.position.set(-3,-3,3);scene.add(red);
  const metal=new THREE.MeshStandardMaterial({color:0x241719,roughness:.24,metalness:.8});
  const heart=new THREE.Mesh(new THREE.TorusKnotGeometry(1.04,.31,180,16,2,3),metal);heart.rotation.set(.6,.15,.3);group.add(heart);
  const edge=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(1.6,1)),new THREE.LineBasicMaterial({color:0x97714d,transparent:true,opacity:.23}));group.add(edge);
  const paths=[];
  for(let j=0;j<7;j++){
    const points=[];for(let i=0;i<=180;i++){const t=i/180*Math.PI*2,radius=2.05+j*.09;points.push(new THREE.Vector3(Math.cos(t)*radius,Math.sin(t)*radius*.66,Math.sin(t*2+j*.5)*.45));}
    const curve=new THREE.CatmullRomCurve3(points),ribbon=new THREE.Mesh(new THREE.TubeGeometry(curve,180,j===3?.014:.005,5,false),new THREE.MeshBasicMaterial({color:j===3?0xa83226:0xbd9b6c,transparent:true,opacity:j===3?.85:.2+j*.045}));
    ribbon.rotation.set(j*.36,.35+j*.13,j*.17);group.add(ribbon);paths.push({curve,ribbon});
  }
  const nodes=new THREE.InstancedMesh(new THREE.SphereGeometry(.027,6,6),new THREE.MeshBasicMaterial({color:0xdcc3a0}),Math.min(records.length||600,1000));
  const dummy=new THREE.Object3D();for(let i=0;i<nodes.count;i++){const phase=i*2.399963,radius=2.8+(i%17)*.083;dummy.position.set(Math.cos(phase)*radius,Math.sin(phase)*radius*.8,Math.sin(i*1.73)*2.2);dummy.updateMatrix();nodes.setMatrixAt(i,dummy.matrix);}group.add(nodes);
  const sparks=new THREE.Group();for(let i=0;i<12;i++){const spark=new THREE.Mesh(new THREE.SphereGeometry(i%3===0?.055:.025,8,8),new THREE.MeshBasicMaterial({color:i%3===0?0xd44631:0xe3c7a2}));sparks.add(spark);}group.add(sparks);
  let targetX=0,targetY=0,eraTarget=0,frame=0,visible=true,last=0,time=0;
  const resize=()=>{const rect=host.getBoundingClientRect();if(!rect.width||!rect.height)return;renderer.setSize(rect.width,rect.height,false);camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();group.position.x=rect.width<800?1.1:2.5;renderer.render(scene,camera);};
  const observer=new ResizeObserver(resize);observer.observe(host);resize();
  host.parentElement.addEventListener('pointermove',event=>{const rect=host.getBoundingClientRect();targetY=(event.clientX-rect.left)/rect.width-.5;targetX=(event.clientY-rect.top)/rect.height-.5;},{passive:true});
  setSceneEra=year=>{eraTarget=(year-1960)/10*.24;};
  function tick(now){frame=0;if(!visible||document.hidden||paused){renderer.render(scene,camera);return;}const delta=last?Math.min((now-last)/1000,.06):0;last=now;time+=delta;group.rotation.y+=(targetY*.25+eraTarget+time*.055-group.rotation.y)*.025;group.rotation.x+=(targetX*.13-.2-group.rotation.x)*.025;heart.rotation.z=time*.12;edge.rotation.y=-time*.09;nodes.rotation.z=time*.008;sparks.children.forEach((spark,i)=>{const entry=paths[i%paths.length],pos=entry.curve.getPoint((time*.02+i/12)%1);spark.position.copy(pos.applyEuler(entry.ribbon.rotation));});renderer.render(scene,camera);frame=requestAnimationFrame(tick);}
  sceneVisibility=flag=>{visible=flag;if(frame){cancelAnimationFrame(frame);frame=0;}last=0;if(visible&&!document.hidden){renderer.render(scene,camera);if(!paused)frame=requestAnimationFrame(tick);}};
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting&&view==='atlas';sceneVisibility(visible);},{rootMargin:'100px'}).observe(host.parentElement);
  document.addEventListener('visibilitychange',()=>sceneVisibility(view==='atlas'&&host.getBoundingClientRect().bottom>0));
  renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();host.classList.remove('has-webgl');if(frame)cancelAnimationFrame(frame);});
  window.addEventListener('pagehide',()=>{if(frame)cancelAnimationFrame(frame);observer.disconnect();renderer.dispose();},{once:true});sceneVisibility(view==='atlas');
}

async function load(){
  setupEvents();
  try{
    const [response,settings]=await Promise.all([fetch(new URL('../innovation/data.json',import.meta.url)),fetch(new URL('../innovation/config.json',import.meta.url)).then(response=>response.ok?response.json():{}).catch(()=>({}))]);
    if(!response.ok)throw new Error('The dated archive is not available. Please try again after the next publication.');data=await response.json();
    if(!Array.isArray(data.assets)||!Array.isArray(data.opportunities)||!Array.isArray(data.catalog))throw new Error('This archive edition is not in a supported format.');
    core().createGame(data);config=typeof settings==='object'&&settings?settings:{};config.leaderboardUrl=sourceURL(config.leaderboardUrl)||null;
    firms=new Map(data.assets.map(asset=>[asset.id,asset]));records=[...data.opportunities.map(record=>({...record,_landmark:true})),...data.catalog.map(record=>({...record,_landmark:false}))].filter(record=>yearOf(record)>=1960&&yearOf(record)<=Number(data.asOf.slice(0,4))).sort((a,b)=>preciseDay(a).localeCompare(preciseDay(b))||a.title.localeCompare(b.title));
    $('#count-innovations').textContent=count(records.length);$('#count-landmarks').textContent=count(data.opportunities.length);$('#count-firms').textContent=count(data.assets.filter(asset=>asset.id!==data.benchmarkAssetId).length);$('#count-prices').textContent=count(data.assets.reduce((sum,asset)=>sum+(asset.points?.length||0),0));
    $$('[data-latest-year]').forEach(node=>node.textContent=data.asOf.slice(0,4));
    $('#atlas-status').textContent=`Published archive · observations through ${dateText(data.asOf)} · researched landmarks and structured discovery records are identified separately.`;
    $('#atlas-company').insertAdjacentHTML('beforeend',data.assets.filter(asset=>asset.id!==data.benchmarkAssetId).sort((a,b)=>a.name.localeCompare(b.name)).map(asset=>`<option value="${escape(asset.id)}">${escape(asset.name)}</option>`).join(''));
    const coverage=data.coverage||{};$('#coverage-notes').innerHTML=`<p>${count(coverage.curatedMilestones||data.opportunities.length)} researched milestones, ${count(data.catalog.length)} company-linked discovery records, and ${count(coverage.priceObservations)} sampled price observations. Source history ends ${escape(dateText(data.asOf))}.</p><p>${count(coverage.opportunitiesWithValuation)} decision cards include verified, dated filing metrics. Missing prices and ratios remain unavailable. The collection is selective, not a complete history of invention.</p>`;
    renderCards();$('#game-start').disabled=false;
    const saved=storage.get(KEYS.save);if(saved){try{const restored=core().restore(data,saved);$('#game-resume').hidden=false;$('#saved-status').textContent=`Saved journey: ${dateText(restored.date)} · ${cash(core().portfolio(data,restored).value)}.`;}catch{$('#saved-status').textContent='A journey from another data edition is stored here. Start a new journey to use this edition.';}}
    const hash=new URLSearchParams(location.hash.slice(1));if(hash.has('innovation'))openRecord(hash.get('innovation'));
    (window.requestIdleCallback||((fn)=>setTimeout(fn,80)))(()=>startScene());
  }catch(error){$('#atlas-status').textContent=error.message;$('#saved-status').textContent='The game will be available once its dated dataset can be loaded.';$('#innovation-cards').innerHTML='<p class="ia-empty">The archive could not be loaded. The site’s research remains available from the footer.</p>';}
}
load();
