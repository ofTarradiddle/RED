"""Local-only SPY valuation and inspectable accounting; excluded from Pages."""
from publishing.branding import apply_branding
from decimal import Decimal
from html import escape as esc
import json
from pathlib import Path
from dataclasses import dataclass

from lib.etf.ledger import replay
from publishing.private_nav import PRIVATE_ROUTE

ROOT=Path(__file__).resolve().parents[1]
ACTIONS='https://github.com/ofTarradiddle/RED/actions/workflows/refresh-spy.yml'
D=Decimal


@dataclass
class Link:
    label: str
    url: str


def cell(value):
    if isinstance(value,Link) and value.url.startswith('https://'):
        return f'<a href="{esc(value.url,quote=True)}">{esc(value.label)} ↗</a>'
    return esc(str(value))


def cash(value, places=2):
    return 'Unavailable' if value is None else f'${D(str(value)):,.{places}f}'


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+cell(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def panel(title, body, anchor=''):
    return f'<section id="{esc(anchor)}" class="cambria-card p-6 my-8"><h2 class="text-xl font-semibold mb-5">{esc(title)}</h2>{body}</section>'


def journals(state):
    rows=[]
    for entry in state['journal']:
        for p in entry['postings']:
            value=D(p['amount'])
            rows.append([entry['date'],entry['id'],entry['type'],p['account'].replace('_',' '),
                         cash(max(value,0)),cash(max(-value,0)),entry['description']])
    return table(['Date','Event','Type','Account','Debit','Credit','Source / explanation'],rows)


def render(report=None, refresh_state=None):
    status=refresh_state or dict(running=False,message='Ready')
    controls=f'''<div class="nav-actions"><form method="post" action="{PRIVATE_ROUTE}refresh"><button class="cambria-button" type="submit" {'disabled' if status['running'] else ''}>Refresh holdings, prices &amp; daily accruals</button></form><a class="cambria-button-secondary" href="{ACTIONS}">Open GitHub refresh workflow ↗</a><a class="cambria-button-secondary" href="{PRIVATE_ROUTE}">Reload results</a></div><p class="metric-note" role="status">{esc(status['message'])}</p>'''
    body=controls
    if report and report.get('daily_accruals'):
        from publishing.accrual_view import render as render_accruals
        body+=render_accruals(report['daily_accruals'],panel,table,cash,journals)
    body+='<details class="cambria-card p-6 my-8"><summary>SPY source research and valuation comparison</summary><p>Reference evidence for the starting basket. The forward operating book above uses its own dividend and unitary expense accruals.</p>'
    if report and report.get('dividend_receivables'):
        from publishing.dividend_view import render as render_dividends
        body+=render_dividends(report['dividend_receivables'],panel,table,cash,Link)
    if not report:
        body+=panel('No dated SPY report yet','<p>Run the refresh to download the issuer files and date-matched Yahoo closes. The last complete public build stays available if a refresh fails.</p>')
    else:
        r=report;o=r['official'];v=r.get('reconciliation')
        if v:
            complete=not v['missing_security_ids']
            metrics=[('NAV with reported net cash',cash(v['calculated_nav'],8) if complete else 'Incomplete'),
                     ('Official SPY NAV',cash(o['nav'],8)),('Net-assets difference',cash(v['difference_dollars'],2)),
                     ('Reconciliation',v['status'])]
            body+='<div class="nav-metrics">'+''.join(f'<div class="nav-metric"><span>{esc(k)}</span><strong>{esc(val)}</strong></div>' for k,val in metrics)+'</div>'
            body+=f'<p class="metric-note">Valuation: {esc(r["as_of"])} · Inventory file: {esc(v["holdings_as_of"])} · Fetched {esc(r["fetched_at"])} · SPY shares: {D(v["shares"]):,.0f}</p>'
            body+='<nav class="nav-actions"><a href="#calculation">Calculation</a><a href="#positions">Positions</a><a href="#blotter">Blotter &amp; journal</a><a href="#actions">Dividend calendar</a></nav>'
            equation=table(['Component','USD'],[
                ['Common stocks × independently sourced Yahoo closing prices',cash(v['priced_equities'])],
                ['Hologic contingent value right × published peer-fund mark',cash(v['priced_rights'])],
                ['Issuer aggregate Net Cash Amount — included once',cash(v['net_cash']['amount'])],
                ['Calculated net assets',cash(v['known_net_assets'])],['Official net assets',cash(o['net_assets'])],
                ['Difference — no balancing entry',cash(v['difference_dollars'])],
                ['Difference / share',cash(v['difference_per_share'],10)],
                ['Difference in basis points',f"{D(v['difference_bps']):,.8f}"],
                ['Calculated NAV',cash(v['calculated_nav'],10)],['Official net assets ÷ shares',cash(v['official_nav'],10)]])
            body+=panel('NAV calculation','<p class="nav-equation">(Stocks + other securities + net cash) ÷ ETF shares</p>'+equation+
                '<p>Stock quantities are not normalized. The issuer’s aggregate Net Cash Amount is used once; the separate USD holdings row is excluded. Dividends, settlement balances and expense accruals must not be added on top of this aggregate. This reconciles security valuation and aggregate net cash; it does not independently replay today’s detailed cash ledger.</p>'+
                f'<p class="metric-note">SPY market price: {cash(r.get("market_price"),4)}. Missing security valuations: {len(v["missing_security_ids"])}.</p>','calculation')
            counter=r.get('same_date_inventory_countercheck')
            body+=panel('Inventory timing and fair-value evidence',
                '<p>The fixed rule uses the previous NAV session’s holdings file with valuation-day prices, shares and net cash. The feed alignment is observed; the issuer’s timing contract still needs confirmation. The script does not select whichever date produces the closest NAV.</p>'+
                (f'<p>Countercheck using the {esc(r["as_of"])} inventory: {cash(counter["difference_dollars"])} difference ({D(counter["difference_bps"]):,.4f} bps); {len(counter["missing_security_ids"])} unpriced securities.</p>' if counter else '')+
                ''.join(f'<p>436CVR021 · {esc(m["security_name"])} · {cash(m["price"],4)} per right on {esc(m["date"])}. <a href="{esc(m["source_url"])}">State Street SPY5 valuation file ↗</a> · <a href="{esc(m["identity_source_url"])}">Security identity evidence ↗</a>. This is a separately managed fund’s published mark, not a Yahoo common-stock quote or SPY’s own security-level valuation.</p>' for m in r.get('valuation_marks',{}).values()))
            position_rows=[[h['ticker'],h['identifier'],f"{D(h['quantity']):,.4f}",cash(h.get('price'),6),cash(h.get('value')),Link(h.get('source_field') or 'Source',h['price_source']) if h.get('price_source') else 'Unavailable'] for h in v['positions']]
            body+=panel('Position import and closing prices',table(['Security','Identifier','Quantity','Price / share','Market value','Source field'],position_rows),'positions')
            if r.get('closing_price_corroboration'):
                body+=panel('Closing-price precision', '<p>These Yahoo closing quotes retain fractional cents while the daily bar rounds to cents. The same-date identified holdings below independently corroborate the exact quote. Uncorroborated conflicts remain exceptions.</p>'+table(['Security','Identifier','Date','Exact price','Primary corroboration'],[
                    [symbol,m['identifier'],m['date'],cash(m['price'],6),Link('State Street SPY5 holdings',m['source_url'])] for symbol,m in r['closing_price_corroboration'].items()]))
            if r.get('valuation_source_issues'):
                body+=panel('Valuation evidence requires review',''.join('<p>'+esc(issue)+'</p>' for issue in r['valuation_source_issues']))
        else:
            body+=panel('Incomplete archived report','<p>This known-assets subtotal is not a completed NAV. Refresh to run the dated net-cash reconciliation.</p><p>'+esc(r.get('warmup_note',''))+'</p>')
        body+=panel('Execution blotter and operating journal','<p>No SPY execution confirmations or opening operating books have been supplied. Holdings imports are not purchases or sales. Actual blotter entries will appear here when you supply the documented accounting input.</p><p class="metric-note">Input: data/shadow_spy/accounting-input.json. Include opening balances, dated events and dated closing prices. The replay rejects duplicate events, unsupported corporate actions and missing balances.</p>','blotter')
        accounting=ROOT/'data/shadow_spy/accounting-input.json'
        if accounting.exists():
            try:
                inp=json.loads(accounting.read_text());actual=replay(inp['opening'],inp['events'],inp['cutoff'],inp['prices'])
                body+=panel('Supplied accounting records',f'<p>Accounting date: {actual["as_of"]} · NAV {cash(actual["nav"],8)}</p>'+table(['Trade','Date','Security','Side','Quantity','Execution price','Net settlement'],[
                    [e['id'],e['date'],e['symbol'],e['side'],e['quantity'],cash(e['price']),cash(e['net_settlement'])] for e in actual['blotter']])+journals(actual))
            except (ValueError,KeyError,TypeError) as exc:
                body+=panel('Accounting input needs attention','<p>'+esc(str(exc))+'</p>')
        calendar=r.get('dividend_calendar',[]);coverage=r.get('dividend_source_coverage',{})
        rows=[[a['symbol'],a['ex_date'],a['payable_date'],cash(a.get('per_share'),6),a['declaration_status'],
               cash(a.get('cashflow_at_current_quantity')),a['status'],a['crosscheck'],Link(a['source'],a['source_url'])] for a in sorted(calendar,key=lambda x:(x['payable_date'],x['symbol']),reverse=True)]
        body+=panel('Underlying dividend calendar',
            '<p>Ordinary dividend accrual = shares entitled immediately before ex-date × declared amount per share. Debit dividend receivable; credit dividend income. On confirmed payment, debit cash and credit the receivable. The payment does not create income again.</p>'+
            f'<p class="metric-note">Schedules retrieved for {coverage.get("with_schedule",0)} of {coverage.get("requested",0)} securities. Checked {esc(r.get("dividend_calendar_fetched_at","Not fetched"))}. A missing schedule is not evidence of zero dividends. Expected cash uses current shares only for current/future ex-dates; historical entitlements require historical holdings. Estimated schedules remain unbooked. A scheduled payment date does not confirm cash receipt.</p>'+
            '<p><a href="https://www.nasdaq.com/market-activity/stocks/aapl/dividend-history">Nasdaq dividend history ↗</a> · <a href="https://dividendhistory.org/">DividendHistory.org ↗</a> · Yahoo Finance calendar. Source dates and declared amounts are retained; incomplete and conflicting evidence stays unconfirmed.</p>'+
            table(['Security','Ex-date','Payable date','Amount / share','Declaration','Expected cash at current shares','Status','Cross-check','Source'],rows),'actions')
        actionrows=[[a['symbol'],a['date'],a['type'],a['amount']] for a in sorted(r['actions'],key=lambda a:(a['date'],a['symbol']),reverse=True)]
        body+=panel('Corporate-action observations','<p>Yahoo dividend and split observations are references, not booked transactions. The short quote window is not a complete action history. Merger consideration, spin-offs, tender offers, special distributions, return of capital and cash in lieu require explicit source records and supported journal events. Splits change quantity and per-share basis while preserving total cost.</p>'+table(['Security','Ex / effective date','Action','Per share / ratio'],actionrows))
        body+=panel('SPY distributions to its shareholders','<p>Separate from dividends earned on the underlying stocks. A fund distribution reduces NAV through a distribution payable; its later cash payment clears the liability.</p>'+table(['Ex-date','Record date','Payable date','Income / share','Capital gains / share','Total / share'],[
            [d['ex_date'],d['record_date'],d['payable_date'],cash(d['income'],6),cash(D(d['short_term_gain'])+D(d['long_term_gain']),6),cash(d['per_share'],6)] for d in reversed(r['distributions'])]))
        files=r['manifest']['files']
        body+=panel('Source evidence','<p>'+esc(r['accounting_note'])+'</p>'+table(['Input','URL / source','SHA-256'],[[k,f.get('url',f.get('source','')),f['sha256']] for k,f in files.items()])+f'<p class="metric-note">Engine SHA-256: {esc(r["manifest"]["engine_sha256"])}</p>')
    body+='</details>'
    return apply_branding(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Shadow NAV | Hetzerk Asset Management</title><link rel="stylesheet" href="/assets/fonts.css"><link rel="stylesheet" href="/assets/original-utilities.css"><link rel="stylesheet" href="/assets/restored.css"><link rel="icon" href="/assets/favicon.svg?v=wing-h-1"></head><body class="restored-site shadow-spy"><header class="cambria-header"><div class="max-w-7xl mx-auto px-4 py-6 flex justify-between items-center"><a href="/">Hetzerk Asset Management</a><a href="/etfs/redi/">Back to REDI →</a></div></header><main class="max-w-7xl mx-auto px-4 py-12 restored-data"><p class="text-red-800 font-semibold mb-4">FUND OPERATIONS · LOCAL REVIEW</p><h1 class="text-4xl elegant-heading font-bold mb-4">Shadow NAV</h1><p class="mb-8">Hetzerk Innovation Factor ETF · daily operating book · SPY starting basket</p>{body}</main></body></html>''')
