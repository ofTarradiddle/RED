"""Local review calculator. Imported only by serve.py, never the static publisher."""
from copy import deepcopy
from publishing.branding import apply_branding
from decimal import Decimal, ROUND_HALF_UP
from html import escape

from lib.etf.shadow import ASSETS, LIABILITIES, compare, value_shadow
from publishing.site import money, pct

D = Decimal
PRIVATE_ROUTE = '/perspective-7f3c9e/'


def parameter(query, key, default, minimum, maximum):
    raw = query.get(key, [str(default)])
    if len(raw) != 1: raise ValueError(f'One {key} value is required')
    try: value = D(raw[0])
    except Exception as exc: raise ValueError(f'Invalid {key}') from exc
    if not value.is_finite() or not D(str(minimum)) <= value <= D(str(maximum)):
        raise ValueError(f'{key} must be between {minimum} and {maximum}')
    return value


def calculate(fund, query=None):
    query = query or {}
    equities = [h for h in fund['holdings'] if h['security_type']=='equity']
    last = fund['daily'][-1]
    selected = next((h for h in equities if h['ticker']=='ABT'), equities[0])
    price_bps = parameter(query,'price_bps',0,-5000,5000)
    fee = parameter(query,'fee',0,0,1000000)
    tolerance = parameter(query,'tolerance',1,0,1000)
    positions = [dict(security_id=h['identifier'],symbol=h['ticker'],currency=h['currency'],security_type='equity',quantity=str(h['quantity'])) for h in equities]
    balances = dict.fromkeys(ASSETS+LIABILITIES,'0')
    balances['cash'] = str(sum((D(str(h['market_value'])) for h in fund['holdings'] if h['security_type']=='cash'),D(0)))
    snapshot = dict(fund_id=fund['fund_id'],as_of=fund['as_of'],base_currency='USD',shares_outstanding=str(last['shares_outstanding']),corporate_actions_reviewed=True,
                    positions_source='Constructed workbook scenario',balances_source='Workbook cash; explicit zero opening accruals in scenario',positions=positions,balances=balances)
    quotes = dict(as_of=fund['as_of'],source='Constructed workbook prices, not Yahoo observations',fetched_at=fund['as_of']+'T21:00:00Z',prices={
        h['ticker']:dict(date=fund['as_of'],currency=h['currency'],close=str(h['price']),fx_to_usd=str(h['fx_rate']),price_basis='as_of_share_units') for h in equities})
    # Arithmetic scenario only: this is not an independent provider observation.
    baseline = value_shadow(snapshot,quotes)
    provider = deepcopy(snapshot)
    provider.update(provider_name='Provider comparison scenario',net_assets=str(baseline['net_assets']),official_nav=str(baseline['nav'].quantize(D('.01'),rounding=ROUND_HALF_UP)),official_nav_decimals=2)
    for p,h in zip(provider['positions'],equities):
        p.update(price=str(h['price']),fx_to_usd=str(h['fx_rate']))
    quotes['prices'][selected['ticker']]['close'] = str(D(str(selected['price']))*(1+price_bps/10000))
    snapshot['balances']['accrued_fees'] = str(fee)
    report = compare(snapshot,quotes,provider,str(tolerance))
    fee_estimate = (D(str(last['net_assets']))*D(str(fund['expense_ratio']))/365).quantize(D('.01'),rounding=ROUND_HALF_UP)
    return dict(report=report,baseline=baseline,provider_input=provider,snapshot=snapshot,quotes=quotes,
                selected=selected,price_bps=price_bps,fee=fee,tolerance=tolerance,fee_estimate=fee_estimate)


def render_dashboard(fund, query=None):
    data = calculate(fund,query)
    report=data['report'];shadow=report['shadow'];provider=report['provider']
    label = 'Within tolerance' if report['status']=='within_tolerance' else 'Difference to review'
    numbers = (
        ('Shadow NAV',money(shadow['nav'],6)),('Provider NAV · unrounded',money(provider['unrounded_nav'],6)),
        ('Difference · unrounded',f'{report["unrounded_difference_bps"]:+.4f} bps'),('Reconciliation',label))
    metrics=''.join(f'<div class="nav-metric"><span>{k}</span><strong>{v}</strong></div>' for k,v in numbers)
    amounts=[('Equities',shadow['securities']),('Cash',shadow['balances']['cash']),('Dividends receivable',shadow['balances']['dividends_receivable']),('Trade receivables',shadow['balances']['trade_receivables']),('Other receivables',shadow['balances']['other_receivables']),('Total assets',shadow['assets']),('Accrued fees',-shadow['balances']['accrued_fees']),('Trade payables',-shadow['balances']['trade_payables']),('Other liabilities',-shadow['balances']['other_liabilities']),('Net assets',shadow['net_assets'])]
    bridge=''.join(f'<tr><th>{k}</th><td>{money(v)}</td></tr>' for k,v in amounts)
    positions=[]
    breaks={b['security_id']:b for b in report['breaks']}
    provider_positions={p['security_id']:p for p in data['provider_input']['positions']}
    for sid,p in sorted(shadow['positions'].items(),key=lambda item:-abs(breaks[item[0]]['total'])):
        old=provider_positions[sid];b=breaks[sid]
        values=[escape(p['symbol']),f'{p["quantity"]:,.4f}',money(p['price'],4),money(D(old['price']),4),money(p['value']),money(b['quantity']),money(b['price']),money(b['fx']),money(b['total'])]
        positions.append('<tr>'+''.join(f'<td>{v}</td>' for v in values)+'</tr>')
    attribution=''.join(f'<tr><th>{name.replace("_"," ").title()}</th><td>{money(value,8)}</td></tr>' for name,value in report['nav_attribution'].items())
    other_balances=''.join(f'<tr><th>{key.replace("_"," ").title()}</th><td>{money(value)}</td></tr>' for key,value in report['balance_breaks'].items())
    ticker=escape(data['selected']['ticker'])
    return apply_branding(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Shadow NAV | Hetzerk Asset Management</title><link rel="stylesheet" href="/assets/fonts.css"><link rel="stylesheet" href="/assets/original-utilities.css"><link rel="stylesheet" href="/assets/restored.css"><link rel="icon" href="/assets/favicon.svg"></head><body class="restored-site">
    <div class="demo-strip">Illustrative demo · Portfolio data, performance and comparisons are fictional · Not an investment offering</div>
    <header class="cambria-header"><div class="max-w-7xl mx-auto px-4 py-6 flex justify-between items-center"><a href="/" class="font-semibold">Hetzerk Asset Management</a><a href="/etfs/redi/" class="text-sm">Back to REDI →</a></div></header>
    <main class="max-w-7xl mx-auto px-4 py-12 restored-data"><p class="text-red-800 font-semibold mb-4">FUND OPERATIONS · LOCAL REVIEW</p><h1 class="text-4xl elegant-heading font-bold mb-4">Shadow NAV</h1><p class="mb-8">Hetzerk Innovation Factor ETF · {fund['as_of']} · USD</p>
    <div class="nav-metrics">{metrics}</div>
    <section class="cambria-card p-6 my-8"><h2 class="text-xl font-semibold mb-3">Calculation inputs</h2><p class="metric-note">Pricing: workbook closing prices. Yahoo and administrator feeds are not connected. The provider comparison uses unchanged workbook values.</p>
    <form action="{PRIVATE_ROUTE}" method="get" class="nav-inputs">
      <label>{ticker} price difference (bps)<input type="number" name="price_bps" min="-5000" max="5000" step="0.01" value="{data['price_bps']}" required></label>
      <label>New accrued fee (USD)<input type="number" name="fee" min="0" max="1000000" step="0.01" value="{data['fee']}" required></label>
      <label>Tolerance (bps)<input type="number" name="tolerance" min="0" max="1000" step="0.01" value="{data['tolerance']}" required></label>
      <button class="cambria-button" type="submit">Recalculate</button>
    </form><p class="metric-note">A price difference of 100 bps is +1% for {ticker} only. <a href="{PRIVATE_ROUTE}?price_bps=0&amp;fee=0&amp;tolerance=1" class="text-red-800 underline">Match the baseline</a> · <a href="{PRIVATE_ROUTE}" class="text-red-800 underline">Reset price difference</a></p></section>
    <div class="nav-columns"><section class="cambria-card p-6"><h2 class="text-xl font-semibold mb-5">NAV calculation</h2><p class="nav-equation">(Assets − liabilities) ÷ shares</p><div class="table-scroll"><table><tbody>{bridge}<tr><th>Shares outstanding</th><td>{shadow['shares']:,.0f}</td></tr><tr class="nav-total"><th>Shadow NAV per share</th><td>{money(shadow['nav'],8)}</td></tr></tbody></table></div></section>
    <section class="cambria-card p-6"><h2 class="text-xl font-semibold mb-5">Expense accrual</h2><p class="nav-equation">{pct(fund['expense_ratio'])} per year · 45 bps</p><p>{money(D(str(fund['daily'][-1]['net_assets'])))} × {pct(fund['expense_ratio'])} ÷ 365</p><p class="nav-fee">{money(data['fee_estimate'])}<span>for one calendar day</span></p><p class="metric-note">ACT/365 on the workbook net-asset base. Opening accruals are zero in this scenario. This is a new liability only when applied below; it does not alter the published fund data.</p><a class="cambria-button-secondary" href="{PRIVATE_ROUTE}?price_bps={data['price_bps']}&amp;fee={data['fee_estimate']}&amp;tolerance={data['tolerance']}">Apply one day’s fee</a><p class="metric-note">Paying an accrued fee reduces cash and the liability together; it does not charge NAV a second time.</p></section></div>
    <section class="cambria-card p-6 my-8"><h2 class="text-xl font-semibold mb-5">Position reconciliation</h2><p class="metric-note">{len(positions)} equities · largest differences first · differences are shadow minus provider, in USD.</p><div class="table-scroll"><table><thead><tr><th>Security</th><th>Quantity</th><th>Shadow price</th><th>Provider price</th><th>Shadow value</th><th>Quantity effect</th><th>Price effect</th><th>FX effect</th><th>Total difference</th></tr></thead><tbody>{''.join(positions)}</tbody></table></div></section>
    <div class="nav-columns"><section class="cambria-card p-6"><h2 class="text-xl font-semibold mb-5">Balance differences</h2><div class="table-scroll"><table><tbody>{other_balances}</tbody></table></div></section><section class="cambria-card p-6"><h2 class="text-xl font-semibold mb-5">NAV difference explained</h2><div class="table-scroll"><table><tbody>{attribution}<tr><th>Total vs reported NAV</th><td>{money(report['nav_difference'],8)}</td></tr><tr><th>Unexplained residual</th><td>{money(report['attribution_residual'],8)}</td></tr></tbody></table></div><p class="metric-note">Reported provider NAV: {money(provider['official_nav'])}. Tolerance uses the unrounded provider NAV, so cent rounding does not create a false break.</p></section></div>
    <p class="metric-note mt-8">This calculation stays on the local review server. It does not post accounting entries or publish NAV. Operational records and corporate actions must be reconciled before using external pricing.</p></main></body></html>''')
