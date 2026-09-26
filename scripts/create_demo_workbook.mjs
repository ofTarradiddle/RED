// Run with the bundled @oai/artifact-tool dependency environment. Input: demo_seed.py JSON.
import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile, FileBlob } from '@oai/artifact-tool';

const root = process.env.HETZERK_ROOT;
if (!root) throw new Error('HETZERK_ROOT must point to the project');
const seed = JSON.parse(await fs.readFile('/private/tmp/hetzerk-seed.json','utf8'));
const wb = Workbook.create();
const guide=wb.worksheets.add('Read me');
guide.showGridLines=false;
guide.getRange('B2').values=[['Hetzerk · Demo site workbook']];
guide.getRange('B2').format.font={name:'Arial',size:16,color:'#771F33'};
guide.getRange('B4:C14').values=[
 ['Purpose','Editable illustrative content and data for the local website.'],
 ['Status','Demo only. No actual fund performance, offering or verified registration.'],
 ['Update','Edit the five data sheets. Keep exact headers and stable fund_id values.'],
 ['Build','Save, then run python3 -m publishing.build from the project directory.'],
 ['Dates','Use Excel dates or ISO YYYY-MM-DD. Holdings must match the final daily date.'],
 ['Rates','Decimal fractions: 0.0045 = 0.45%. cash_weight is 0.02 = 2%.'],
 ['Reconcile','Daily NAV × shares = net assets. Equity + cash values = demo net assets.'],
 ['Values','Quantity × local price × FX = USD market value. All prices are synthetic.'],
 ['Distributions','Daily per-share amount must match the distribution ex-date total.'],
 ['Source','Original demo company names; normalized equity weights 98%, cash 2%.'],
 ['History','Synthetic weekday observations. Not an exchange calendar or real track record.'],
];
guide.getRange('B4:C14').format.font={name:'Arial',size:10,color:'#242E2B'};
guide.getRange('B4:B14').format.font.bold=true;
guide.getRange('B:B').format.columnWidth=18;
guide.getRange('C:C').format.columnWidth=102;
guide.getRange('B4:C14').format.rowHeight=27;
guide.tabColor='#771F33';
let tableIndex=0;
for(const [name, raw] of Object.entries(seed)) {
 const sh=wb.worksheets.add(name); sh.showGridLines=false;
 const headers=raw[0];
 const dateCols=headers.map((v,i)=>v==='date'||v.endsWith('_date')?i:-1).filter(i=>i>=0);
 const rows=raw.map((r,i)=>r.map((v,c)=>i&&v&&dateCols.includes(c)?new Date(v+'T12:00:00Z'):v));
 const range=sh.getRangeByIndexes(0,0,rows.length,headers.length);range.values=rows;
 range.format.font={name:'Arial',size:10,color:'#242E2B'};
 range.format.rowHeight=22;
 range.format.columnWidth=18;
 sh.getRangeByIndexes(0,0,1,headers.length).format={fill:'#771F33',font:{name:'Arial',bold:true,color:'#FFFFFF',size:10},rowHeight:28};
 const table=sh.tables.add(`A1:${String.fromCharCode(64+headers.length)}${rows.length}`,true,`DemoTable${++tableIndex}`);
 table.style='TableStyleLight1';
 sh.freezePanes.freezeRows(1);
 for(const col of dateCols) {
   sh.getRangeByIndexes(1,col,rows.length-1,1).setNumberFormat('yyyy-mm-dd');
   sh.getRangeByIndexes(1,col,rows.length-1,1).format.horizontalAlignment='center';
 }
 for(let col=0;col<headers.length;col++) {
   const key=headers[col], body=sh.getRangeByIndexes(1,col,rows.length-1,1);
   if(['name','description','title','strategy','benchmark_label'].includes(key)) sh.getRangeByIndexes(0,col,rows.length,1).format.columnWidth=key==='description'?88:45;
   if(['expense_ratio','cash_weight'].includes(key))body.setNumberFormat('0.00%');
   if(['nav','market_price','benchmark_index','price','income','short_term_gain','long_term_gain','return_of_capital','distribution_per_share'].includes(key))body.setNumberFormat('0.000000');
   if(['market_value','net_assets'].includes(key))body.setNumberFormat('#,##0.00');
   if(['quantity','shares_outstanding'].includes(key))body.setNumberFormat('#,##0.0000');
 }
 if(name==='Funds')sh.getRange(`H2:H${rows.length}`).dataValidation={rule:{type:'list',values:['TRUE']}};
 if(name==='Holdings')sh.getRange(`I2:I${rows.length}`).dataValidation={rule:{type:'list',values:['equity','cash']}};
 if(name==='Documents')sh.getRange(`F2:F${rows.length}`).dataValidation={rule:{type:'list',values:['unavailable','draft']}};
}
wb.recalculate();
await fs.mkdir(root+'/workbooks',{recursive:true});
await (await SpreadsheetFile.exportXlsx(wb)).save(root+'/workbooks/hetzerk-demo.xlsx');
for(const [sheet,range] of [['Read me','B2:C14'],['Funds','A1:F6'],['Daily Data','A1:H12'],['Holdings','A1:F12'],['Distributions','A1:H10'],['Documents','A1:F9']]) {
 const preview=await wb.render({sheetName:sheet,range,scale:1,format:'png'});
 await fs.writeFile(`/private/tmp/hetzerk-workbook/${sheet.replaceAll(' ','-')}.png`,new Uint8Array(await preview.arrayBuffer()));
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
// Preserve the legacy holdings workbook while applying the requested brand change.
const old=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'/red_holdings.xlsx'));
await fs.writeFile('/private/tmp/hetzerk-workbook/legacy-before.png',new Uint8Array(await (await old.render({sheetName:'Fund Details',range:'A1:H2',scale:1,format:'png'})).arrayBuffer()));
const legacySheets=[['Holdings','A1:K60'],['Sector Summary','A1:D11'],['Fund Details','A1:H2']];
for(const [sheet,range] of legacySheets) {
 const target=old.worksheets.getItem(sheet).getRange(range);
 const values=target.values;
 const replaced=values.map(row=>row.map(v=>typeof v==='string'?v.replace(/D\u0069amond Brothers/gi,'Hetzerk').replace(/D\u0069amond/gi,'Hetzerk'):v));
 for(let row=0;row<values.length;row++)for(let col=0;col<values[row].length;col++) if(replaced[row][col]!==values[row][col]) target.getCell(row,col).values=[[replaced[row][col]]];
}
old.recalculate();
await (await SpreadsheetFile.exportXlsx(old)).save(root+'/red_holdings.xlsx');
await fs.writeFile('/private/tmp/hetzerk-workbook/legacy-after.png',new Uint8Array(await (await old.render({sheetName:'Fund Details',range:'A1:H2',scale:1,format:'png'})).arrayBuffer()));
console.log('Saved demo workbook and rebranded legacy workbook.');
