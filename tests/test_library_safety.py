"""Offline regression cases for confirmed legacy accounting/control failures."""
from datetime import date, timedelta
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from lib.etf.adapters.fmp_adapter import FMPDataSourceAdapter
from lib.etf.functions.core.accounting import Accounting
from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.core.shadow_accounting import ShadowAccounting
from lib.etf.functions.tax.tax_lot import TaxLotManager
from lib.etf.shared import NAVCalculation
from lib.etf.functions.operations.performance import PerformanceCalculator

D = Decimal
DAY = date(2026, 9, 21)


def test_simple_sale_tax_is_applied_to_gain_not_entire_wealth(tmp_path):
    source=tmp_path/'nav.csv'
    source.write_text('date,nav\n2024-01-02,100\n2025-01-03,120\n')
    result=PerformanceCalculator(str(tmp_path)).compute_performance(str(source),None,None,{'lt_capital_gains_tax_rate':.2})
    assert result['pre_tax_total_return']==pytest.approx(.2)
    assert result['after_tax_total_return']==pytest.approx(.16)
    assert 'Not standardized' in result['after_tax_methodology']


def test_reinvested_distributions_increase_tax_basis(tmp_path):
    nav=tmp_path/'nav.csv';div=tmp_path/'div.csv'
    nav.write_text('date,nav\n2024-01-02,100\n2024-06-03,100\n2025-01-03,110\n')
    div.write_text('date,distribution_per_share\n2024-06-03,10\n')
    result=PerformanceCalculator(str(tmp_path)).compute_performance(str(nav),str(div),None,{'dividend_tax_rate':.1,'lt_capital_gains_tax_rate':.2})
    # 1.09 shares, $109 basis, $119.90 value, $10.90 gain, $2.18 sale tax.
    assert result['after_tax_total_return']==pytest.approx(.1772)


def test_same_ex_date_components_are_reinvested_once(tmp_path):
    nav=tmp_path/'nav.csv';dist=tmp_path/'distributions.csv'
    nav.write_text('date,nav\n2024-01-02,100\n2024-01-03,80\n')
    dist.write_text('date,distribution_per_share\n2024-01-03,10\n2024-01-03,10\n')
    calc=PerformanceCalculator(str(tmp_path))
    result=calc.compute_performance(str(nav),str(dist),None,{'dividend_tax_rate':0,'lt_capital_gains_tax_rate':0})
    assert result['pre_tax_total_return']==0
    assert result['after_tax_total_return']==0


@pytest.mark.parametrize('case',['missing','nan','negative','date','no_nav'])
def test_distribution_errors_are_not_silently_omitted(tmp_path,case):
    nav=tmp_path/'nav.csv';dist=tmp_path/'distributions.csv'
    nav.write_text('date,nav\n2024-01-02,100\n2024-01-04,80\n')
    rows={'nan':'2024-01-04,NaN','negative':'2024-01-04,-1','date':'not-a-date,20','no_nav':'2024-01-03,20'}
    if case!='missing':dist.write_text('date,distribution_per_share\n'+rows[case]+'\n')
    with pytest.raises((ValueError,FileNotFoundError)):
        PerformanceCalculator(str(tmp_path)).compute_performance(str(nav),str(dist),None,{})


def snapshot(value='100', valid=True, exceptions=None):
    return NAVCalculation(DAY, D(value) * 100, D('0'), D(value) * 100,
                          D('100'), D(value), exceptions or [], valid)


def shadow(tmp_path, value='100', valid=True, exceptions=None):
    calculator = ShadowAccounting(SimpleNamespace(), str(tmp_path / 'shadow'))
    calculator.admin = SimpleNamespace(
        calculate_nav=lambda _: snapshot(value, valid, exceptions))
    return calculator


def test_shadow_requires_independent_official_nav(tmp_path):
    calculator = shadow(tmp_path)
    result = calculator.calculate_shadow_nav(DAY)
    assert result.status == 'unavailable'
    assert not result.validation_passed
    assert result.official_nav_per_share is None
    assert result.difference is None
    record = json.loads((calculator.storage_path / f'shadow_nav_{DAY}.json').read_text())
    assert record['official_nav_per_share'] is None
    assert record['difference_percentage'] is None


@pytest.mark.parametrize(('value', 'expected'), [('100.005', 'match'),
                                                ('100.01', 'warning'),
                                                ('100.1', 'error')])
def test_shadow_thresholds_are_percent(tmp_path, value, expected):
    result = shadow(tmp_path, value).calculate_shadow_nav(DAY, D('100'))
    assert result.status == expected


@pytest.mark.parametrize('official', ['0', '-1', 'NaN', 'Infinity'])
def test_shadow_rejects_invalid_official_nav(tmp_path, official):
    result = shadow(tmp_path).calculate_shadow_nav(DAY, D(official))
    assert result.status == 'error'
    assert not result.validation_passed
    assert result.difference_percentage is None


def test_shadow_pricing_exception_cannot_downgrade_error(tmp_path):
    result = shadow(tmp_path, '50', False, ['missing price']).calculate_shadow_nav(DAY, D('100'))
    assert result.status == 'error'
    assert not result.validation_passed


def test_shadow_trends_exclude_unavailable_comparisons(tmp_path):
    report = shadow(tmp_path).monitor_nav_trends(DAY, DAY + timedelta(days=1))
    assert report['compared_days'] == 0
    assert report['unavailable_days'] == 2
    assert report['match_days'] == 0
    assert report['statistics']['average_difference_percentage'] is None


def test_nav_snapshots_never_accumulate_in_general_ledger(tmp_path):
    accounting = Accounting(SimpleNamespace(), str(tmp_path))
    nav = {'total_assets': '1000', 'total_liabilities': '100', 'net_assets': '900'}
    for day in (DAY, DAY, DAY + timedelta(days=1)):
        assert accounting.record_nav_entries(day, nav) == []
    assert accounting.general_ledger['1100'].balance == 0
    assert accounting.journal_entries == []
    record = json.loads((tmp_path / f'nav_snapshot_{DAY}.json').read_text())
    assert record['net_assets'] == '900'
    assert record['posted_to_ledger'] is False


def test_invalid_snapshot_does_not_overwrite_prior_snapshot(tmp_path):
    accounting = Accounting(SimpleNamespace(), str(tmp_path))
    nav = {'total_assets': '1000', 'total_liabilities': '100', 'net_assets': '900'}
    accounting.record_nav_entries(DAY, nav)
    path = tmp_path / f'nav_snapshot_{DAY}.json'
    before = path.read_bytes()
    with pytest.raises(ValueError):
        accounting.record_nav_entries(DAY, {**nav, 'net_assets': '950'})
    assert path.read_bytes() == before


def test_failed_journal_validates_all_accounts_before_mutation(tmp_path):
    accounting = Accounting(SimpleNamespace(), str(tmp_path))
    with pytest.raises(ValueError):
        accounting.create_journal_entry(DAY, [{'account': '1000', 'debit': '10'},
                                             {'account': 'unknown', 'credit': '10'}], 'invalid')
    assert accounting.general_ledger['1000'].balance == 0
    assert accounting.general_ledger['1000'].entries == []
    assert accounting.journal_entries == []


@pytest.mark.parametrize('amount', ['-1', 'NaN', 'Infinity'])
def test_journal_rejects_nonfinite_or_negative_amounts(tmp_path, amount):
    accounting = Accounting(SimpleNamespace(), str(tmp_path))
    with pytest.raises(ValueError):
        accounting.create_journal_entry(DAY, [{'account': '1000', 'debit': amount},
                                             {'account': '3000', 'credit': amount}], 'invalid')
    assert accounting.journal_entries == []


def test_ledger_reload_restores_types_and_unique_journal_ids(tmp_path):
    accounting = Accounting(SimpleNamespace(), str(tmp_path))
    entries = [{'account': '1000', 'debit': '10'}, {'account': '3000', 'credit': '10'}]
    first = accounting.create_journal_entry(DAY, entries, 'capital')
    reloaded = Accounting(SimpleNamespace(), str(tmp_path))
    assert len(reloaded.journal_entries) == 2
    assert reloaded.general_ledger['1000'].entries[0].date == DAY
    assert reloaded.general_ledger['1000'].entries[0].debit == D('10')
    second = reloaded.create_journal_entry(DAY, entries, 'more capital')
    assert {e.entry_id for e in first}.isdisjoint(e.entry_id for e in second)
    assert reloaded.general_ledger['1000'].balance == D('20')


def test_corrupt_ledger_is_not_silently_reset(tmp_path):
    (tmp_path / 'general_ledger.json').write_text('{bad json')
    with pytest.raises(ValueError, match='refusing to reset'):
        Accounting(SimpleNamespace(), str(tmp_path))


class SnapshotAdapter:
    def __init__(self):
        self.custodian = {'cash_balance': '100', 'shares_outstanding': '100'}
        self.expenses = {'accrued_income': '0', 'accrued_expenses': '0', 'payables': '0'}
        self.holdings = []
        self.prices = {}

    def get_portfolio_holdings(self, day):
        return self.holdings

    def get_market_prices(self, day, identifiers):
        return self.prices

    def get_expense_data(self, day):
        return self.expenses

    def get_custodian_statements(self, day):
        return self.custodian


@pytest.mark.parametrize(('source', 'field'), [('custodian', 'cash_balance'),
                                               ('custodian', 'shares_outstanding'),
                                               ('expenses', 'accrued_income'),
                                               ('expenses', 'accrued_expenses'),
                                               ('expenses', 'payables')])
def test_nav_requires_explicit_financial_inputs(tmp_path, source, field):
    adapter = SnapshotAdapter()
    del getattr(adapter, source)[field]
    nav = FundAdministration(adapter, str(tmp_path)).calculate_nav(DAY)
    assert not nav.validation_passed
    assert field in nav.pricing_exceptions[0]


@pytest.mark.parametrize('shares', ['0', '-1', 'NaN', 'Infinity'])
def test_nav_rejects_invalid_shares(tmp_path, shares):
    adapter = SnapshotAdapter()
    adapter.custodian['shares_outstanding'] = shares
    assert not FundAdministration(adapter, str(tmp_path)).calculate_nav(DAY).validation_passed


def test_nav_explicit_zero_accruals_and_cash_only_portfolio_are_valid(tmp_path):
    nav = FundAdministration(SnapshotAdapter(), str(tmp_path)).calculate_nav(DAY)
    assert nav.validation_passed
    assert nav.nav_per_share == D('1')


def test_missing_security_price_is_not_added_to_cash(tmp_path):
    adapter = SnapshotAdapter()
    adapter.holdings = [{'cusip': 'ABC', 'ticker': 'ABC', 'quantity': 10, 'market_value': 1000}]
    nav = FundAdministration(adapter, str(tmp_path)).calculate_nav(DAY)
    assert not nav.validation_passed
    assert nav.total_assets == D('100')
    assert any('Missing price' in error for error in nav.pricing_exceptions)


class FakeFMP:
    def __init__(self, price=None):
        self.price = price if price is not None else {'close': 100, 'adjClose': 90, 'date': DAY.isoformat()}

    def get_historical_price_eod(self, ticker, day):
        return self.price

    def get_dividends_calendar(self, start, end):
        return [{'symbol': 'ABC', 'exDate': '2026-09-01', 'dividend': 1},
                {'symbol': 'ABC', 'exDate': DAY.isoformat(), 'dividend': 2},
                {'symbol': 'ABC', 'exDate': '2026-10-01', 'dividend': 3}]


def fmp_adapter(client):
    return FMPDataSourceAdapter(fmp_client=client,
                               manual_holdings=[{'ticker': 'ABC', 'cusip': 'ABC', 'quantity': 10}])


def test_fmp_valuation_uses_close_not_total_return_adjusted_price():
    assert fmp_adapter(FakeFMP()).get_market_prices(DAY, ['ABC']) == {'ABC': D('100')}


@pytest.mark.parametrize('price', [{'adjClose': 90}, {'close': 'NaN'}, {'close': -10},
                                  {'close': 100, 'date': '2026-09-18'}])
def test_fmp_rejects_missing_invalid_or_stale_close(price):
    assert fmp_adapter(FakeFMP(price)).get_market_prices(DAY, ['ABC']) == {}


def test_fmp_dividends_are_recognized_only_on_ex_date():
    income = fmp_adapter(FakeFMP()).get_accounting_data(DAY)['income']
    assert D(income['dividend_income']) == D('20')


def test_oversell_does_not_consume_lots_or_book_realized_gain(tmp_path):
    manager = TaxLotManager(str(tmp_path))
    manager.add_lot('ABC', D('10'), D('5'), DAY - timedelta(days=1))
    with pytest.raises(ValueError, match='Not enough lots'):
        manager.sell('ABC', D('20'), D('6'), DAY)
    assert len(manager.open_lots) == 1
    assert manager.open_lots[0].quantity == D('10')
    assert manager.closed_lots == []
    assert manager.realized_gains == []
    restored = TaxLotManager(str(tmp_path))
    assert restored.open_lots[0].quantity == D('10')
