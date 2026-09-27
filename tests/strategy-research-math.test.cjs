const test = require('node:test');
const assert = require('node:assert/strict');
const math = require('../assets/strategy-research-math.js');
const rows = [
  {date:'2023-12-31', level:1}, {date:'2024-01-31', level:1.2},
  {date:'2024-02-29', level:0.9}, {date:'2024-03-31', level:1.5}
];
const source = (observations = rows) => ({schema_version:1,frequency:'monthly',series:[
  {id:'INNOVATION_LEADER',name:'Innovation Leader',observations},
  {id:'MARKET_BACKTEST',name:'Market Backtest',observations:observations.map(row=>({...row,level:1}))}
]});
const peer = observations => ({series:[{id:'SPY',name:'SPY',currency:'USD',kind:'etf',is_illustrative:false,status:'ok',observations}]});
const close = (date, market_price, distribution=0) => ({date,market_price,distribution,split:2,adjusted_close:9999});
const near = (actual, expected) => assert.ok(Math.abs(actual-expected)<1e-10,`${actual} != ${expected}`);

test('source levels are normalized directly without treating them as ETF prices or adding dividends',()=>{
  const result=math.compare(source(),null,{ids:['INNOVATION_LEADER','MARKET_BACKTEST']});
  assert.deepEqual(result.series[0].points.map(row=>row.value),[100,120,90,150]);
  near(result.series[0].metrics.change,0.5);
  near(result.series[0].metrics.drawdown,-0.25);
  assert.equal(result.series[0].metrics.cagr,null); // Do not annualize a three-month result.
  assert.equal(result.series[0].kind,'research');
  assert.equal(result.series[0].metrics.volatility,undefined);
});

test('ETF reinvestment happens before month selection, with no split or adjusted-close double counting',()=>{
  const market=peer([close('2023-12-29',100),close('2024-01-15',99,1),close('2024-01-31',99),close('2024-02-29',110),close('2024-03-28',121)]);
  const result=math.compare(source(),market,{ids:['INNOVATION_LEADER','SPY']});
  const spy=result.series.find(row=>row.id==='SPY');
  near(spy.points[1].value,100);
  near(spy.points[2].value,100*110/99);
  near(spy.points[3].value,100*121/99);
  assert.equal(spy.points[0].date,'2023-12-31');
  assert.equal(spy.points[0].observedDate,'2023-12-29');
  assert.equal(spy.points[3].observedDate,'2024-03-28');
});

test('missing closing months are excluded without carrying a price forward',()=>{
  const result=math.compare(source(),peer([close('2023-12-29',100),close('2024-01-24',110),close('2024-02-29',120),close('2024-03-28',130)]),{ids:['INNOVATION_LEADER','SPY']});
  assert.deepEqual(result.dates,['2023-12-31','2024-02-29','2024-03-31']);
  assert.ok(result.warnings.some(text=>text.includes('missing')));
  assert.equal(result.series[0].points.length,3);
});

test('only common months are shown and each compared series starts at 100',()=>{
  const result=math.compare(source(),peer([close('2024-02-29',100),close('2024-03-28',120)]),{ids:['SPY']});
  assert.equal(result.start,'2024-02-29');
  assert.equal(result.series[0].id,'INNOVATION_LEADER');
  result.series.forEach(series=>assert.equal(series.points[0].value,100));
  near(result.series[0].metrics.change,1.5/.9-1);
});

test('periods use the final shared month and clamp leap-year boundaries',()=>{
  assert.equal(math.cutoffDate('2024-02-29','1Y'),'2023-02-28');
  const observations=['2022-12-31','2023-02-28','2023-03-31','2024-02-29','2024-03-31'].map((date,i)=>({date,level:i+1}));
  const result=math.compare(source(observations),peer([close('2022-12-30',100),close('2023-02-28',110),close('2023-03-31',120),close('2024-02-29',130)]),{ids:['INNOVATION_LEADER','SPY'],period:'1Y'});
  assert.equal(result.end,'2024-02-29');
  assert.equal(result.start,'2023-02-28');
  near(result.series[0].metrics.cagr,Math.pow(4/2,365.25/366)-1);
});

test('unavailable peer is disclosed and a nonoverlapping peer cannot produce invented history',()=>{
  let result=math.compare(source(),{series:[]},{ids:['INNOVATION_LEADER','SPY']});
  assert.equal(result.excluded[0].id,'SPY');
  assert.equal(result.series.length,1);
  result=math.compare(source(),peer([close('2025-01-31',100)]),{ids:['INNOVATION_LEADER','SPY']});
  assert.equal(result.series.length,0);
  assert.match(result.reason,/do not share/);
});

test('one shared mark has no invented return or drawdown statistic',()=>{
  const result=math.compare(source([rows[0]]),null,{ids:['INNOVATION_LEADER']});
  assert.deepEqual(result.series[0].metrics,{change:null,cagr:null,drawdown:null});
});

test('invalid source levels, ambiguous dates and duplicated selections fail visibly',()=>{
  for (const observations of [[{date:'2024-02-30',level:1}],[{date:'2024-02-28',level:1}],[{date:'2024-02-29',level:NaN}], [rows[0],rows[0]],rows.slice().reverse()]) {
    assert.throws(()=>math.compare(source(observations),null));
  }
  assert.throws(()=>math.compare(source(),null,{ids:['INNOVATION_LEADER','INNOVATION_LEADER']}));
  assert.throws(()=>math.compare(source(),null,{ids:['REDI']}));
  assert.throws(()=>math.compare(source(),null,{period:'YTD'}));
});

test('invalid ETF distribution evidence or source identity cannot silently become research',()=>{
  const market=peer([close('2024-02-29',100),close('2024-03-28',100,-1)]);
  assert.throws(()=>math.compare(source(),market,{ids:['INNOVATION_LEADER','SPY']}));
  market.series[0].observations[1].distribution=0;
  market.series[0].is_illustrative=true;
  assert.throws(()=>math.compare(source(),market,{ids:['INNOVATION_LEADER','SPY']}));
});

test('a near-month-end quote cannot create a closing month that had not completed at publication',()=>{
  const market=peer([close('2024-08-30',100),close('2024-09-27',110)]);
  market.generated_at='2024-09-29T12:00:00Z';
  const research=source([{date:'2024-08-31',level:1},{date:'2024-09-30',level:1.2}]);
  const result=math.compare(research,market,{ids:['INNOVATION_LEADER','SPY']});
  assert.deepEqual(result.dates,['2024-08-31']);
  assert.equal(result.series[0].metrics.change,null);
});

const suppliedIds = ['MARKET','MARKET_CAP','NON_RD','RD_OTHER','INNOVATION','PREDICTED_INNOVATION',
  'INNOVATION_150_75','INNOVATION_200_100','INNOVATION_250_125'];
const uploaded = () => ({id:'hetzerk-comparison-research',schema_version:1,frequency:'monthly',
  reference_series_id:'PREDICTED_INNOVATION',series:suppliedIds.map((id,index)=>({id,name:id,
    observations:rows.map((row,i)=>({...row,level:i === 0 ? .99 : row.level*(index+1)}))}))});

test('uploaded comparison defaults to Predicted innovation and retains its non-unit starting level',()=>{
  const data=uploaded();
  const result=math.compare(data,null);
  assert.deepEqual(result.series.map(series=>series.id),['PREDICTED_INNOVATION','INNOVATION','MARKET']);
  assert.equal(result.referenceId,'PREDICTED_INNOVATION');
  near(result.series[0].points[0].value,100);
  near(result.series[0].metrics.change,9/.99-1);
  assert.throws(()=>math.compare({...data,reference_series_id:'INNOVATION_LEADER'},null),/reference/);
  assert.throws(()=>math.compare(data,null,{ids:['LAGGARD']}),/Unknown/);
});

test('all nine supplied series and all five ETFs can share one comparison without a peer cap',()=>{
  const data=uploaded(), etfs=['SPY','VOO','QQQ','ITAN','SYLD'];
  const market={generated_at:'2024-04-01T00:00:00Z',series:etfs.map(id=>({...peer([
    close('2023-12-29',100),close('2024-01-31',110),close('2024-02-29',120),close('2024-03-28',130)
  ]).series[0],id}))};
  const result=math.compare(data,market,{ids:[...suppliedIds,...etfs]});
  assert.equal(result.series.length,14);
  assert.equal(result.dates.length,4);
  assert.equal(result.referenceId,'PREDICTED_INNOVATION');
  result.series.forEach(series=>near(series.points[0].value,100));
  const onlyETF=math.compare(data,market,{ids:['SPY']});
  assert.deepEqual(onlyETF.series.map(series=>series.id),['SPY']);
  near(onlyETF.series[0].metrics.change,.3);
  assert.equal(onlyETF.referenceId,'SPY');
  assert.match(math.compare(data,market,{ids:[]}).reason,/Select at least one/);
  assert.deepEqual(math.compare(data,null,{ids:['INNOVATION_250_125']}).series.map(series=>series.id),['INNOVATION_250_125']);
});

test('the supplied file remains a distinct path from the PDF chart and is rebased rather than re-compounded',()=>{
  const data=require('../data/comparison_research.json');
  const result=math.compare(data,null,{ids:['PREDICTED_INNOVATION']});
  assert.equal(result.dates.length,289);
  assert.equal(result.start,'2002-08-31');
  assert.equal(result.end,'2026-08-31');
  near(result.series[0].metrics.change,65.75/.99-1);
  const legacy=math.compare(require('../data/strategy_research.json'),null,{ids:[]});
  assert.equal(legacy.series[0].id,'INNOVATION_LEADER');
  assert.equal(legacy.start,'2003-04-30');
  near(legacy.series[0].metrics.change,48.08-1);
});
