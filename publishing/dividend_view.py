"""Private dividend subledger view; no output is included in static Pages."""
from decimal import Decimal as D
from html import escape as esc


def render(book,panel,table,cash,Link):
    observed=book['source_dated_book'];modeled=book['modeled_book']
    total=book['outstanding_event_count'];count=book['calculated_outstanding_count']
    metrics=[('Gross from dated share snapshots',cash(observed['expected_receivable'])),
             ('Gross model subtotal',cash(book['expected_gross_receivable'])),
             ('Calculated outstanding events',f'{count} / {total}'),
             ('Complete confirmed receivable','Not established')]
    body='<div class="nav-metrics">'+''.join(f'<div class="nav-metric"><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k,v in metrics)+'</div>'
    body+='<p>Each ordinary dividend is calculated as eligible shares on ex-date × the declared amount per share. The entitlement is frozen: later sales, splits and ETF creations/redemptions do not rescale the dollar receivable. Confirmed receipts reduce it; a scheduled payment affects only the expected-payment model.</p>'
    body+=f'<p class="metric-note">As of {esc(book["as_of"])}. {book["outstanding_source_dated_count"]} outstanding events use published pre-ex-date share observations. Other quantities are explicitly estimated from a fixed basket per SPY share and historical fund units, with split adjustments. {len(book["unresolved_outstanding"])} outstanding event(s) remain unresolved. Action histories retrieved for {book["action_history_coverage"]} securities.</p>'
    body+='<p><strong>The gross model is not a fully verified SPY receivable.</strong> Historical trades, index changes, opening unpaid items, withholding and cash receipts remain incomplete. A dated issuer snapshot supports a calculation but does not attest custody timing. No issuer-reported receivable balance or NAV residual is used to create these amounts.</p>'
    if book.get('prior_entitlements_under_review'):
        body+=f'<p><strong>{len(book["prior_entitlements_under_review"])} previously calculated entitlements need review.</strong> Their original quantities and amounts remain archived. They are excluded from current calculated subtotals until the evidence conflict is resolved; this exclusion is not a cancellation or write-off.</p>'
    pending=[r for r in book['rows'] if r['pending']]
    def source(r):
        evidence=r.get('rate_evidence') or {}
        return Link(r['rate_status'],evidence.get('source_url') or evidence.get('url') or r['source_url'])
    def quantity(r):
        methods={'documented_entitlement':'Documented entitlement','dated_holdings_snapshot':'Dated pre-ex snapshot','fund_unit_scaled_estimate':'Estimated; frozen at first calculation'}
        return methods.get(r['quantity_method'],'Unresolved')
    rows=[[r['symbol'],r['ex_date'],r['payable_date'],f"{D(r['eligible_quantity']):,.6f}" if r.get('eligible_quantity') else 'Unavailable',
           quantity(r),cash(r.get('per_share'),6),cash(r.get('gross')),source(r)] for r in pending]
    body+=table(['Stock','Ex-date','Scheduled payment','Eligible shares used','Quantity basis','Dividend / share','Gross receivable','Rate evidence'],rows)
    body+='<details><summary>Calculation, frozen quantities and source corrections</summary>'+table(['Stock','Required pre-ex snapshot','Source amount','Amount used','Quantity evidence','Rate decision'],[
        [r['symbol'],r.get('required_holdings_date','Unavailable'),cash(r.get('scheduled_rate'),6),cash(r.get('per_share'),6),r.get('quantity_source','Unavailable'),r['rate_status']] for r in pending])+'</details>'
    journals=[]
    for e in observed['journal']:
        for account,value in e['postings'].items():
            val=D(value)
            if val:journals.append([e['date'],e['id'],e['type'],account.replace('_',' '),cash(max(val,0)),cash(max(-val,0)),e['source']])
    body+='<details><summary>Source-dated accrual and payment journal</summary><p>Unknown withholding is left as a gross assumption. These are shadow entries from the displayed evidence, not a claim that the custodian has confirmed entitlement or paid cash.</p>'+table(['Date','Action','Entry','Account','Debit','Credit','Evidence'],journals)+'</details>'
    body+=('<details><summary>Payment roll-forward and unresolved opening items</summary>'+table(['Source-dated book','USD'],[
        ['Gross accruals from available dated snapshots',cash(observed['gross_accrued'])],
        ['Confirmed cash receipts supplied',cash(observed['confirmed_receipts'])],
        ['Receivable before assuming scheduled cash receipts',cash(observed['receivable_without_assumed_receipts'])],
        ['Modeled cash receipts on scheduled dates',cash(observed['modeled_receipts'])],
        ['Expected remaining receivable on those items',cash(observed['expected_receivable'])]])+
        f'<p>{esc(book["opening_balance_status"])}. {len(book["missing_payment_schedules"])} historical dividend observations lack usable payment schedules. Their outstanding status is unknown; they are not declared paid or silently included at zero.</p>'+
        '<p>Import documented entitlement quantities, withholding/reclaims and confirmed receipts in data/shadow_spy/dividend-inputs.json. The source-dated subtotal excludes lots whose quantities are estimated. The full model is separate, and scheduled-payment entries never become confirmed receipts.</p></details>')
    check=book.get('component_check')
    if check:
        body+=('<details><summary>NAV components with independently calculated dividends</summary>'+table(['Component','USD'],[
            ['Independently priced securities',cash(check['securities'])],['Standalone USD holdings cash',cash(check['holdings_cash'])],
            ['Calculated gross dividend subtotal — includes estimates',cash(check['calculated_gross_receivable_subtotal'])],
            ['Assets before other balances',cash(check['assets_before_other_balances'])],
            ['Official net assets for comparison',cash(check['official_net_assets'])],
            ['Other net balances / model differences needed — NOT BOOKED',cash(check['other_net_balances_needed_to_reconcile'])]])+
            f'<p>{esc(check["note"])} The separate matched NAV check below uses reported aggregate net cash. This dividend subtotal is never added to that aggregate.</p></details>')
    return panel('Dividend receivable — independent calculation',body,'dividend-book')
