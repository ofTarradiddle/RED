"""Reprice a filed SPY balance sheet without deriving prices from its NAV."""
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

D=Decimal
ASSETS={'cash','dividends_receivable','foreign_tax_receivable'}
LIABILITIES={'units_redeemed_payable','trustee_expense_payable','marketing_expense_payable','distribution_payable','other_expenses_liabilities'}


def verify(source):
    statement=source['statement'];balances=statement['balances'];date=source['as_of']
    if set(balances)!=ASSETS|LIABILITIES:raise ValueError('Unrecognized balance-sheet accounts')
    securities=D(0);seen=set()
    for p in source['positions']:
        if p['yahoo_symbol'] in seen or p['valuation_date']!=date or p['currency']!='USD':raise ValueError('Historical security identity/date mismatch')
        seen.add(p['yahoo_symbol'])
        price=D(p['independent_price']);quantity=D(p['quantity'])
        if not price.is_finite() or not quantity.is_finite() or min(price,quantity)<=0:raise ValueError('Invalid historical valuation')
        securities+=price*quantity
    assets=sum((D(balances[k]) for k in ASSETS),D(0));liabilities=sum((D(balances[k]) for k in LIABILITIES),D(0))
    shares=D(statement['shares_outstanding']);net=securities+assets-liabilities
    nav=net/shares;book=D(statement['reported_net_assets'])/shares
    return dict(securities=str(securities),other_assets=str(assets),liabilities=str(liabilities),net_assets=str(net),
                nav=str(nav),book_nav=str(book),difference_dollars=str(net-D(statement['reported_net_assets'])),
                same_cent=nav.quantize(D('.01'),rounding=ROUND_HALF_UP)==book.quantize(D('.01'),rounding=ROUND_HALF_UP),
                position_count=len(seen))


def load(folder):
    folder=Path(folder);path=folder/'historical-integration.json'
    if not path.exists():return None
    source=json.loads(path.read_text());source['calculation']=verify(source)
    return source
