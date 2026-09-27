from copy import deepcopy
import pytest
from scripts.annual_filings import metric_at, select_report, build_cards, investment_evidence
from scripts.refresh_annual_game import combine_financials, validate_dataset


def fact(value,filed='2010-02-01',end='2009-12-31',start='2009-01-01',acc='0000000001-10-000001'):
    return {'val':value,'filed':filed,'end':end,'start':start,'form':'10-K','accn':acc}


def facts(tag,rows,unit='USD'):
    return {'facts':{'us-gaap':{tag:{'units':{unit:rows}}}}}


def test_future_comparative_restatement_cannot_replace_known_annual_fact():
    raw=facts('ResearchAndDevelopmentExpense',[fact(12),fact(90,filed='2012-02-01',acc='0000000001-12-000001')])
    value,source=metric_at(raw,'rd','2010-12-31',1)
    assert value==12 and source['filed']=='2010-02-01'
    assert '000000000110000001' in source['sourceUrl']


def test_component_revenue_and_generic_investing_cash_are_not_mislabeled():
    raw=facts('SalesRevenueGoodsNet',[fact(50)])
    raw['facts']['us-gaap']['PaymentsForProceedsFromOtherInvestingActivities']={'units':{'USD':[fact(99)]}}
    assert metric_at(raw,'revenue','2010-12-31',1)==(None,None)
    assert metric_at(raw,'capex','2010-12-31',1)==(None,None)


def test_missing_short_period_and_old_fact_are_not_filled_or_zero():
    raw=facts('ResearchAndDevelopmentExpense',[fact(3,start='2009-10-01'),fact(20,end='2008-12-31',start='2008-01-01')])
    assert metric_at(raw,'rd','2010-12-31',1)==(None,None)


def test_filing_selection_uses_available_original_annual_report():
    rows=[{'form':'10-K','filingDate':'2010-02-01','reportDate':'2009-12-31','accessionNumber':'0000000001-10-000001'},
          {'form':'10-K','filingDate':'2011-02-01','reportDate':'2010-12-31','accessionNumber':'0000000001-11-000001'},
          {'form':'10-K/A','filingDate':'2010-09-01','reportDate':'2009-12-31','accessionNumber':'0000000001-10-000002'}]
    assert select_report(rows,'2010-12-31')['filingDate']=='2010-02-01'
    assert select_report(rows,'2013-12-31') is None


def test_excerpt_budget_and_specific_focus_are_derived_only_from_filing():
    html='<html><body><p>Our research and development activities focus on semiconductor design and manufacturing capacity, including new processors for mobile devices.</p><p>We invest in data centers and cloud computing infrastructure to develop software platforms for our customers throughout the world.</p><p>Capital expenditures include investment in new facilities and manufacturing capacity for our existing products and customer requirements.</p></body></html>'
    themes,focus=investment_evidence(html)
    assert themes and sum(len(t['excerpt'].split()) for t in themes)<=25
    assert 'Semiconductors' in focus and 'Cloud services' in focus
    assert 'New medicines' not in focus
    assert all(t['excerpt'] in html for t in themes)


def test_card_uses_actual_fact_availability_and_preserves_missing_metrics():
    raw=facts('ResearchAndDevelopmentExpense',[fact(12)])
    card=build_cards(1,['2010-12-31'],[],raw,{})[0]
    assert card['availableAt']=='2010-02-01'
    assert card['metrics']['rd']==12 and card['metrics']['capex'] is None
    assert card['filings']==[] and card['status']=='partial'


def test_predecessor_report_still_available_after_legal_reorganization():
    old=build_cards(1,['2010-12-31'],[],facts('ResearchAndDevelopmentExpense',[fact(12)]),{})[0]
    new=build_cards(2,['2010-12-31'],[],{}, {})[0]
    asset={'points':[],'filingCiks':[{'cik':1,'start':'2000-01-01','end':'2010-10-01'},{'cik':2,'start':'2010-10-02','end':None}]}
    card=combine_financials(asset,'2010-12-31',{'1':{'cards':[old]},'2':{'cards':[new]}})
    assert card['metrics']['rd']==12 and card['availableAt']=='2010-02-01'


def test_yahoo_quote_and_raw_archive_quote_require_different_split_basis():
    source=build_cards(1,['2010-12-31'],[],facts('EarningsPerShareDiluted',[fact(2)],unit='USD/shares'),{})[0]
    asset={'cik':1,'points':[{'date':'2010-12-31','close':10,'adjustedClose':8}], 'splits':[{'date':'2012-01-03','ratio':2}],'priceBasis':'yahoo-split-adjusted-close','splitsStatus':'complete','splitsFrom':'2009-01-01','splitsAsOf':'2026-09-25'}
    asset['priceBasisAsOf']='2026-09-25'
    yahoo=combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})
    assert yahoo['valuation']['pe']==10
    asset.update(priceBasis='contemporaneous-unadjusted-close',splitsStatus='complete')
    archive=combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})
    assert archive['valuation']['pe']==5
    asset.pop('splitsStatus')
    assert combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})['valuation'] is None
    asset['priceBasis']='yahoo-split-adjusted-close'
    assert combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})['valuation'] is None
    asset.update(splitsStatus='complete',splitsAsOf='2009-12-31')
    assert combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})['valuation'] is None
    asset.update(splitsStatus='complete',splitsFrom='2010-01-01',splitsAsOf='2026-09-25')
    assert combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})['valuation'] is None


def test_split_between_fiscal_end_and_filing_withholds_ambiguous_pe():
    source=build_cards(1,['2010-12-31'],[],facts('EarningsPerShareDiluted',[fact(2)],unit='USD/shares'),{})[0]
    asset={'cik':1,'points':[{'date':'2010-12-31','close':10,'adjustedClose':8}],'splits':[{'date':'2010-01-15','ratio':2}],'priceBasis':'yahoo-split-adjusted-close','splitsStatus':'complete','splitsFrom':'2009-01-01','splitsAsOf':'2026-09-25'}
    asset['priceBasisAsOf']='2026-09-25'
    assert combine_financials(asset,'2010-12-31',{'1':{'cards':[source]}})['valuation'] is None


def test_later_predecessor_filing_cannot_override_successor_issuer_evidence():
    old=build_cards(1,['2011-12-31'],[],facts('ResearchAndDevelopmentExpense',[fact(999,filed='2011-03-01',end='2010-12-31',start='2010-01-01')]),{})[0]
    new=build_cards(2,['2011-12-31'],[],facts('ResearchAndDevelopmentExpense',[fact(12,filed='2011-02-01',end='2010-12-31',start='2010-01-01')]),{})[0]
    asset={'points':[],'filingCiks':[{'cik':1,'start':'2000-01-01','end':'2010-10-01'},{'cik':2,'start':'2010-10-02','end':None}]}
    card=combine_financials(asset,'2011-12-31',{'1':{'cards':[old]},'2':{'cards':[new]}})
    assert card['metrics']['rd']==12


def test_failed_metadata_refresh_preserves_prior_dated_evidence(tmp_path,monkeypatch):
    from scripts import annual_filings
    path=tmp_path/'facts.json.gz';old={'cik':1,'facts':{'us-gaap':{}}}
    annual_filings.save(path,old)
    def unavailable(url):raise OSError('network unavailable')
    monkeypatch.setattr(annual_filings,'request',unavailable)
    annual_filings._local.refresh_warnings=[]
    assert annual_filings.cached_json(path,'https://data.sec.gov/test',refresh=True)==old
    assert annual_filings._local.refresh_warnings
    assert annual_filings.load(path)==old


def test_transition_cutoff_retains_original_fact_before_later_amendment():
    raw=facts('ResearchAndDevelopmentExpense',[fact(12),fact(99,filed='2010-11-01',acc='0000000001-10-000002')])
    cards=build_cards(1,['2010-10-01','2010-12-31'],[],raw,{})
    asset={'points':[],'filingCiks':[{'cik':1,'start':'2000-01-01','end':'2010-10-01'},{'cik':2,'start':'2010-10-02'}]}
    card=combine_financials(asset,'2010-12-31',{'1':{'cards':cards}})
    assert card['metrics']['rd']==12
    assert card['metricSources']['rd']['filed']=='2010-02-01'


def test_older_sgml_wrapped_html_report_without_outer_html_tag(tmp_path,monkeypatch):
    from scripts import annual_filings
    from types import SimpleNamespace
    paragraph='<p>Our research and development activities focus on new products and manufacturing capacity for our customers.</p>'
    raw=('<DOCUMENT>\n<TYPE>10-K\n<TEXT>\n<head></head><body>'+paragraph*40+'</body>\n</TEXT></DOCUMENT>').encode()
    monkeypatch.setattr(annual_filings,'CACHE',tmp_path)
    monkeypatch.setattr(annual_filings,'request',lambda url:SimpleNamespace(content=raw))
    row={'accessionNumber':'0000000001-12-000001','form':'10-K','filingDate':'2012-02-29','reportDate':'2011-12-31','primaryDocument':'d10k.htm'}
    report=annual_filings.get_report(1,row)
    assert report['status']=='ok'
    assert report['investmentThemes']
    assert (tmp_path/'1/raw/0000000001-12-000001.html.gz').exists()


def test_verified_predecessor_extension_admits_only_pretransition_period():
    raw=facts('ResearchAndDevelopmentExpense',[
        fact(12,filed='2015-03-02',end='2014-12-31',start='2014-01-01'),
        fact(99,filed='2015-03-03',end='2014-12-31',start='2014-01-01',acc='0000000001-15-000002'),
    ])
    cards=build_cards(1,['2015-03-02','2015-12-31'],[],raw,{})
    asset={'points':[],'filingCiks':[{'cik':1,'end':'2015-02-27','evidenceThrough':'2015-03-02'}]}
    card=combine_financials(asset,'2015-12-31',{'1':{'cards':cards}})
    assert card['metrics']['rd']==12
    assert card['metricSources']['rd']['filed']=='2015-03-02'
    assert combine_financials(asset,'2015-03-01',{'1':{'cards':cards}})['metrics']['rd'] is None
    cards[0]['metricSources']['rd']['fiscalPeriodEnd']='2015-03-01'
    assert combine_financials(asset,'2015-12-31',{'1':{'cards':cards}})['metrics']['rd'] is None
