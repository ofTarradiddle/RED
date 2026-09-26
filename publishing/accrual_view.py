"""Private daily operating book; rendered only by the localhost server."""
from decimal import Decimal as D
from html import escape as esc


def render(book, panel, table, cash, journals):
    rows = book.get('daily', [])
    if not rows:
        previous=book.get('last_complete_day')
        prior=(f'<p>Last calculated day: {esc(previous["date"])} · model NAV {cash(previous["nav"],8)} · unitary fee payable {cash(previous["fee_payable"])}. These are prior-date results.</p>' if previous else '')
        return panel('Daily dividend and expense accruals',
            '<p><strong>'+esc(book['status'])+'</strong></p><p>'+esc(book.get('error', 'No valued day available'))+
            '</p>'+prior+'<p>The saved opening and source history are retained. A missing trading-session close is not carried forward.</p>', 'daily-accruals')
    latest = rows[-1]; policy = book['policy']; rate = D(latest['annual_rate'])
    metrics = [('Portfolio model NAV', cash(latest['nav'], 8)),
               ('Dividend receivable', cash(latest['dividend_receivable'])),
               ('Unitary fee accrued today', cash(latest['fee_accrual'])),
               ('Unitary fee payable', cash(latest['fee_payable']))]
    body = '<div class="nav-metrics">'+''.join(f'<div class="nav-metric"><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k,v in metrics)+'</div>'
    body += f'<p>Through <strong>{esc(book["as_of"])}</strong> · {esc(book["mode"])} · Hetzerk Innovation Factor ETF expense assumption: <strong>{(rate*10000).normalize():f} bps per year</strong>.</p>'
    body += '<p>Dividends accrue once, in full, on the ex-date. Receivables carry forward each day. Payments move receivables into cash without adding income again. One unitary fee accrues every calendar day, including weekends and holidays.</p>'
    body += '<p class="nav-equation">NAV = (securities + cash + receivables − payables) ÷ portfolio shares</p>'
    body += f'<p>Fee = pre-fee net assets × annual rate ÷ (year days + annual rate). This implements a fee based on closing net assets after today’s expense. Day count: {esc(policy["day_count"])}. Prior unpaid fees are already deducted from the base. Fractional cents carry forward; the journal posts the change in rounded cumulative expense.</p>'
    mode = 'Scheduled dividend payments are modeled cash, not confirmed bank receipts.' if policy['payment_mode']=='scheduled' else 'Dividends clear only against supplied cash receipts; overdue items stay receivable.'
    body += '<p class="metric-note">'+mode+' Fee payments require a supplied event and reduce cash and the payable together.</p>'
    body += table(['Date','Prices dated','Dividend income','Dividend cash · confirmed','Dividend cash · scheduled','Dividends receivable','Fee / day','Fee paid','Fee payable','Model NAV'],[
        [r['date'],r['price_date'],cash(r['dividend_income']),cash(r['confirmed_dividend_cash']),cash(r['scheduled_dividend_cash']),
         cash(r['dividend_receivable']),cash(r['fee_accrual']),cash(r['fee_payment']),cash(r['fee_payable']),cash(r['nav'],8)] for r in rows])
    if book.get('assumptions'):
        body += '<details open><summary>Opening assumptions and portfolio scope</summary><p>Opening books: '+esc(book['opening_date'])+'. Routine refreshes preserve these balances.</p><ul>'+''.join('<li>'+esc(x)+'</li>' for x in book['assumptions'])+'</ul></details>'
    body += '<details><summary>Daily fee bases and precision</summary>'+table(['Date','Pre-fee base','Annual rate','Year days','Exact daily expense','Posted expense','Cumulative expense'],[
        [r['date'],cash(r['fee_base'],6),f'{D(r["annual_rate"])*100:g}%',str(r['year_days']),cash(r['exact_fee'],10),cash(r['fee_accrual']),cash(r['cumulative_fee'])] for r in rows])+'</details>'
    body += '<details><summary>Operating journal · dividends, cash and unitary expense</summary>'+journals(book['state'])+'</details>'
    state = book['state']
    body += '<details><summary>Forward portfolio holdings and prices</summary><p>Quantities change only through supplied executions or supported corporate actions. Later SPY constituent snapshots do not rebalance this book.</p>'+table(['Security','Quantity','Closing price','Market value'],[
        [symbol,f'{D(p["quantity"]):,.6f}',cash(p.get('price'),6),cash(p.get('market_value'))] for symbol,p in state['positions'].items() if D(p['quantity'])])+'</details>'
    body += '<details><summary>Supply operating records</summary><p>Use data/shadow_spy/daily-accounting-input.json with fund_id REDI, opening books, events, dated price_history and the unitary fee policy. Set payment_mode to confirmed to require receipts. Trades, settlement, splits, cash creations/redemptions and fund distributions use the existing accounting replay. Other fee accruals are rejected while the unitary policy is active.</p></details>'
    return panel('Daily dividend and expense accruals',body,'daily-accruals')
