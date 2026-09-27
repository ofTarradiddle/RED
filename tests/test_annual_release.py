from copy import deepcopy
from pathlib import Path
import json
import pytest
from publishing.annual_release import publish_annual_game
from scripts.refresh_annual_game import economic_content, validate_dataset, validate_fact_source


def fixture():
    return {'schema_version':1,'id':'hetzerk-annual-portfolio','version':'test','asOf':'2012-01-03','benchmarkAssetId':'SPY',
      'assets':[{'id':'SPY','points':[{'date':'2011-01-03','adjustedClose':100},{'date':'2012-01-03','adjustedClose':105}]},
                {'id':'A','points':[{'date':'2011-01-03','adjustedClose':10},{'date':'2012-01-03','adjustedClose':12}],'financials':[]}],
      'rounds':[{'year':2010,'cutoff':'2010-12-31','executionDate':'2011-01-03','endDate':'2012-01-03','eligibleAssetIds':['A'],'valuationDates':['2011-01-03','2012-01-03']}]}


def test_publisher_only_writes_public_dataset_not_private_source_cache(tmp_path):
    source=tmp_path/'input.json';source.write_text(json.dumps(fixture()))
    stage=tmp_path/'release';stage.mkdir()
    publish_annual_game(stage,source)
    assert [p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()]==['play/data.json']


def test_future_filing_cannot_enter_the_published_decision_card():
    data=fixture();data['assets'][1]['financials']=[{'decisionCutoff':'2010-12-31','availableAt':'2010-02-01','fiscalPeriodEnd':'2009-12-31','metrics':{},'filings':[{'filed':'2011-02-01','reportDate':'2010-12-31','url':'https://www.sec.gov/Archives/test','investmentThemes':[]}]}]
    with pytest.raises(ValueError,match='Future filing'):validate_dataset(data)


def test_duplicate_or_missing_benchmark_mark_fails_publication():
    data=fixture();data['assets'][0]['points'].pop()
    with pytest.raises(ValueError,match='SPY'):validate_dataset(data)
    data=fixture();data['assets'][1]['points'].append(data['assets'][1]['points'][-1])
    with pytest.raises(ValueError,match='return index'):validate_dataset(data)


def test_retrieval_timestamps_do_not_change_economic_edition():
    a={'retrievedAt':'2026-01-01','assets':[{'id':'A','generatedAt':'one','points':[{'date':'2011-01-03','adjustedClose':10}]}]}
    b=deepcopy(a);b['retrievedAt']='2026-02-01';b['assets'][0]['generatedAt']='two'
    assert economic_content(a)==economic_content(b)
    b['assets'][0]['points'][0]['adjustedClose']=11
    assert economic_content(a)!=economic_content(b)


@pytest.mark.parametrize('changes',[
    {'form':'10-Q'}, {'unit':'shares'}, {'tag':'Assets'}, {'periodStart':'2009-10-01'},
    {'accession':'bad'}, {'sourceUrl':'https://www.sec.gov/about'},
    {'sourceUrl':'https://www.sec.gov/Archives/edgar/data/1/000000000110000099/other.htm'},
])
def test_mislabeled_quarterly_or_unlinked_financial_evidence_cannot_publish(changes):
    source={'form':'10-K','filed':'2010-02-01','periodStart':'2009-01-01','fiscalPeriodEnd':'2009-12-31','tag':'ResearchAndDevelopmentExpense','unit':'USD','accession':'0000000001-10-000001','sourceUrl':'https://www.sec.gov/Archives/edgar/data/1/000000000110000001/0000000001-10-000001-index.html'}
    validate_fact_source('rd',source,'2010-12-31')
    source.update(changes)
    with pytest.raises(ValueError):validate_fact_source('rd',source,'2010-12-31')


def test_public_card_cannot_misstate_when_its_evidence_became_available():
    data=fixture()
    source={'form':'10-K','filed':'2010-02-01','periodStart':'2009-01-01','fiscalPeriodEnd':'2009-12-31','tag':'ResearchAndDevelopmentExpense','unit':'USD','accession':'0000000001-10-000001','sourceUrl':'https://www.sec.gov/Archives/edgar/data/1/000000000110000001/0000000001-10-000001-index.html'}
    card={'decisionCutoff':'2010-12-31','availableAt':'2010-01-01','fiscalPeriodEnd':'2009-12-31','metrics':{'rd':12},'metricSources':{'rd':source},'filings':[]}
    data['assets'][1]['financials']=[card]
    with pytest.raises(ValueError,match='dates do not match'):validate_dataset(data)


def test_reviewed_out_observation_cannot_reenter_published_price_path():
    data=fixture();data['assets'][1]['excludedObservations']=[{'date':'2011-01-03','qualityFlagId':'provider-review'}]
    with pytest.raises(ValueError,match='reviewed-out'):validate_dataset(data)
