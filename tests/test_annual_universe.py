"""Historical identity, sampling, and missing-data safeguards."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.annual_universe import (
    DATA, read, write, load_sources, choose_metadata, yahoo_mapping,
    filing_ciks, historical_price_bounds, historical_label, needs_price_refresh, attach_prices, archive_identity_matches, archive_symbol_at,
)


class AnnualUniverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history,cls.metadata,cls.current,_=load_sources()
        cls.dataset=read(DATA/'universe.json')

    def test_actual_historical_members_are_retained(self):
        by_id={a['id']:a for a in self.dataset['assets']}
        first=self.dataset['rounds'][0]
        symbols={by_id[i]['sourceTicker'] for i in first['eligibleAssetIds']}
        self.assertEqual(first['cutoff'],'2010-12-31')
        self.assertEqual(first['executionDate'],'2011-01-03')
        self.assertIn('AABA',symbols) # historical Yahoo alias, now delisted
        self.assertIn('RSHCQ',symbols) # historical RadioShack, not silently lost
        self.assertNotIn('TSLA',symbols) # only added to the index in 2020
        snapshot=max((r for r in self.history if r['date']<=first['cutoff']),key=lambda r:r['date'])
        self.assertEqual(symbols,set(snapshot['tickers'].split(',')))

    def test_old_and_new_chubb_are_different_issuers(self):
        old=choose_metadata('CB','2010-12-31',self.metadata)
        new=choose_metadata('CB','2020-12-31',self.metadata)
        self.assertEqual(old['cik'],'0000020171')
        self.assertEqual(new['cik'],'0000896159')
        symbol,_=yahoo_mapping('CB',old['cik'],self.current)
        self.assertIsNone(symbol)
        self.assertEqual(historical_price_bounds('CB',old)['end'],'2016-01-13')

    def test_future_allergan_alias_cannot_replace_old_allergan(self):
        old=choose_metadata('AGN','2010-12-31',self.metadata)
        new=choose_metadata('AGN','2016-12-31',self.metadata)
        self.assertEqual(old['cik'],'0000850693')
        self.assertEqual(new['cik'],'0001578845')
        self.assertFalse(archive_identity_matches({'sourceTicker':'AGN','cik':850693},'2020-04-01',self.metadata))

    def test_original_johnson_controls_is_not_acquiring_tyco(self):
        old=choose_metadata('JCI','2010-12-31',self.metadata)
        new=choose_metadata('JCI','2020-12-31',self.metadata)
        self.assertEqual(old['cik'],'0000053669')
        self.assertNotEqual(old['cik'],new['cik'])
        self.assertIsNone(yahoo_mapping('JCI',old['cik'],self.current)[0])
        self.assertEqual(historical_price_bounds('JCI',old)['end'],'2016-09-01')

    def test_cliffs_typo_and_pre_spinoff_fox_identity_are_corrected(self):
        self.assertEqual(choose_metadata('CLF','2010-12-31',self.metadata)['cik'],'0000764065')
        self.assertEqual(choose_metadata('FOXA','2010-12-31',self.metadata)['cik'],'0001308161')
        self.assertEqual(choose_metadata('FOXA','2020-12-31',self.metadata)['cik'],'0001754301')

    def test_google_original_class_a_and_new_class_c_are_not_backcast(self):
        a=next(a for a in self.dataset['assets'] if a.get('sourceTicker')=='GOOGL')
        c=next(a for a in self.dataset['assets'] if a.get('sourceTicker')=='GOOG')
        self.assertEqual(a['yahooSymbol'],'GOOGL')
        self.assertIn(2010,a['membershipYears'])
        self.assertEqual(a['historicalLabels']['2010']['ticker'],'GOOG')
        self.assertIn('Class A',a['historicalLabels']['2010']['name'])
        self.assertEqual(min(c['membershipYears']),2014)
        self.assertEqual(c['securityStartDate'],'2014-04-03')
        self.assertTrue(all(p['date']>='2014-04-03' for p in c['points']))
        self.assertTrue(all(p['date']>='2014-04-03' for p in c['splits']))

    def test_archive_alias_uses_symbol_at_archive_date_and_verified_issuer(self):
        coterra={'sourceTicker':'CTRA','cik':858470}
        self.assertEqual(archive_symbol_at(coterra,'2020-04-01'),'COG')
        self.assertEqual(archive_symbol_at(coterra,'2022-04-14'),'CTRA')
        # CTRA in the 2020 archive denotes Contura, not Coterra; changing
        # only the string without checking the issuer would corrupt returns.
        self.assertEqual(archive_symbol_at({'sourceTicker':'CTRA','cik':1704715},'2020-04-01'),'CTRA')
        self.assertEqual(archive_symbol_at({'sourceTicker':'CBS','cik':813828},'2022-04-14'),'PARA')
        self.assertEqual(archive_symbol_at({'sourceTicker':'DAY','cik':1725057},'2023-09-21'),'CDAY')

    def test_names_and_tickers_do_not_reveal_later_rebrands(self):
        cases=[('GE','2010-12-31','GE','General Electric Company'),
               ('FB','2013-12-31','FB','Facebook, Inc.'),
               ('FB','2021-12-31','FB','Meta Platforms, Inc.'),
               ('SPGI','2010-12-31','MHP','The McGraw-Hill Companies, Inc.'),
               ('SPGI','2014-12-31','MHFI','McGraw Hill Financial, Inc.'),
               ('ANTM','2010-12-31','WLP','WellPoint, Inc.'),
               ('WBA','2010-12-31','WAG','Walgreen Co.'),
               ('BKNG','2010-12-31','PCLN','priceline.com Incorporated'),
               ('DXC','2010-12-31','CSC','Computer Sciences Corporation'),
               ('BHGE','2010-12-31','BHI','Baker Hughes Incorporated'),
               ('MYL','2010-12-31','MYL','Mylan Inc.'),
               ('ESRX','2010-12-31','ESRX','Express Scripts, Inc.'),
               ('AVGO','2015-12-31','AVGO','Avago Technologies Limited')]
        for symbol,cutoff,ticker,name in cases:
            label=historical_label(symbol,cutoff,choose_metadata(symbol,cutoff,self.metadata))
            self.assertEqual((label['ticker'],label['name']),(ticker,name))
            self.assertEqual(label['status'],'dated-source-verified')

    def test_stale_successful_cache_refreshes_and_current_cache_does_not(self):
        source={'status':'ok','points':[{'date':'2026-09-24'}]}
        self.assertTrue(needs_price_refresh(source,'2026-09-25'))
        self.assertFalse(needs_price_refresh(source,'2026-09-24'))
        self.assertTrue(needs_price_refresh({},'2026-09-25'))

    def test_cold_cache_retains_reviewed_archive_paths_and_quote_provenance(self):
        old=next(a for a in self.dataset['assets'] if a.get('returnSource')=='Quandl WIKI archived adjusted close' and 2010 in a['membershipYears'] and a['points'])
        previous={**self.dataset,'assets':[deepcopy(old)]}
        fresh=deepcopy(previous)
        fresh['assets'][0]['points']=[]
        fresh['rounds']=[{**r,'eligibleAssetIds':[old['id']]} for r in fresh['rounds'] if r['year'] in old['membershipYears']]
        with TemporaryDirectory() as folder,patch('scripts.annual_universe.DATA',Path(folder)):
            result=attach_prices(fresh,{},previous)
        recovered=result['assets'][0]
        self.assertEqual(recovered['points'],old['points'])
        for field in ('returnSource','sourceUrl','priceBasis','splits','splitsStatus','splitsAsOf','archiveProvenance'):
            self.assertEqual(recovered.get(field),old.get(field))
        self.assertEqual(recovered['priceRetainedFromVersion'],previous['version'])
        self.assertEqual(result['retainedSourceEditions'][0]['sources'],previous['sources'])

    def test_future_provider_split_basis_survives_older_game_calendar(self):
        old=next(a for a in self.dataset['assets'] if a.get('sourceTicker')=='MSFT')
        fresh={**deepcopy(self.dataset),'assets':[deepcopy(old)]}
        fresh['rounds']=[{**r,'eligibleAssetIds':[old['id']]} for r in fresh['rounds'] if r['year'] in old['membershipYears']]
        source={'status':'ok','points':old['points']+[{'date':'2026-09-28','close':100,'adjustedClose':100}],
                'splits':[{'date':'2026-09-28','ratio':2}],'splitsStatus':'complete','splitsFrom':'1986-03-13',
                'splitsAsOf':'2026-09-28','priceBasisAsOf':'2026-09-28'}
        with TemporaryDirectory() as folder,patch('scripts.annual_universe.DATA',Path(folder)):
            result=attach_prices(fresh,{'MSFT':source})
        asset=result['assets'][0]
        self.assertNotIn('2026-09-28',[p['date'] for p in asset['points']])
        self.assertEqual(asset['splits'][0]['date'],'2026-09-28')
        self.assertEqual(asset['priceBasisAsOf'],'2026-09-28')
        self.assertEqual(asset['splitsAsOf'],'2026-09-28')

    def test_archive_split_window_does_not_inherit_discarded_yahoo_window(self):
        old=next(a for a in self.dataset['assets'] if a.get('returnSource')=='Quandl WIKI archived adjusted close' and 2010 in a['membershipYears'])
        fresh={**deepcopy(self.dataset),'assets':[deepcopy(old)]}
        fresh['assets'][0]['yahooSymbol']='TEST'
        fresh['assets'][0]['archiveIdentityBounds']={}
        fresh['rounds']=[{**r,'eligibleAssetIds':[old['id']]} for r in fresh['rounds'] if r['year'] in old['membershipYears']]
        archive={'sourceUrl':'https://example.com/archive','archiveSha256':'a'*64,'archiveLastDate':'2018-03-27',
                 'series':{old['archiveSymbol']:{'points':old['points'],'firstDate':'1962-01-02',
                    'splits':[],'splitsStatus':'complete-through-archive-end'}}}
        with TemporaryDirectory() as folder,patch('scripts.annual_universe.DATA',Path(folder)):
            write(Path(folder)/'wiki-prices.json.gz',archive)
            result=attach_prices(fresh,{'TEST':{'points':[],'splitsFrom':'2016-11-01','splitsAsOf':'2026-09-25','splitsStatus':'complete'}})
        asset=result['assets'][0]
        self.assertEqual(asset['priceBasis'],'contemporaneous-unadjusted-close')
        self.assertEqual(asset['splitsFrom'],'1962-01-02')
        self.assertEqual(asset['splitsAsOf'],'2018-03-27')
        self.assertIsNone(asset['priceBasisAsOf'])

    def test_same_ticker_with_a_different_modern_cik_is_not_price_identity(self):
        current={'0':{'ticker':'LIFE','cik_str':999,'title':'Different modern issuer'}}
        symbol,reason=yahoo_mapping('LIFE','0001073431',current)
        self.assertIsNone(symbol)
        self.assertIn('another issuer',reason)

    def test_bankrupt_common_shares_do_not_become_reissued_peabody(self):
        symbol,reason=yahoo_mapping('BTUUQ','0001064728',self.current)
        self.assertIsNone(symbol)
        self.assertIn('post-bankruptcy',reason)

    def test_discovery_class_c_never_reuses_class_a_back_history(self):
        symbol,reason=yahoo_mapping('DISCK','0001437107',self.current)
        self.assertIsNone(symbol)
        self.assertIn('Class C',reason)
        asset=next(a for a in self.dataset['assets'] if a.get('sourceTicker')=='DISCK')
        self.assertNotEqual(asset['returnSource'],'Yahoo Finance adjusted close')

    def test_known_adjustment_disagreements_are_excluded_and_attributable(self):
        flags=read(DATA/'quality_flags.json')['flags'];by_id={a['id']:a for a in self.dataset['assets']}
        self.assertEqual(len(flags),7)
        for flag in flags:
            asset=by_id[flag['assetId']]
            self.assertNotIn(flag['excludedDate'],[p['date'] for p in asset['points']])
            self.assertIn(flag['excludedDate'],[p['date'] for p in asset['excludedObservations']])
            self.assertGreaterEqual(len(flag['sourceReturns']),2)
            self.assertTrue(all(p['sourceUrl'].startswith('https://') for p in flag['sourceReturns']))
            affected=[r for r in self.dataset['rounds'] if asset['id'] in r['eligibleAssetIds'] and flag['excludedDate'] in r['valuationDates']]
            self.assertTrue(affected)
            for rnd in affected:
                available={p['date'] for p in asset['points']}
                self.assertFalse(set(rnd['valuationDates'])<=available)

    def test_cold_cache_preserves_quarantined_observation_provenance(self):
        old=next(a for a in self.dataset['assets'] if a.get('sourceTicker')=='DHR')
        previous={**self.dataset,'assets':[deepcopy(old)]};fresh=deepcopy(previous)
        for field in ('points','excludedObservations','qualityFlags'):fresh['assets'][0].pop(field,None)
        fresh['rounds']=[{**r,'eligibleAssetIds':[old['id']]} for r in fresh['rounds']]
        flags=read(DATA/'quality_flags.json')
        with TemporaryDirectory() as folder,patch('scripts.annual_universe.DATA',Path(folder)):
            write(Path(folder)/'quality_flags.json',flags)
            result=attach_prices(fresh,{},previous)
        recovered=result['assets'][0]
        self.assertEqual(recovered['excludedObservations'],old['excludedObservations'])
        self.assertEqual(result['qualityAudit']['quarantinedObservations'],1)

    def test_filing_cik_eras_are_dated_and_do_not_backcast_alphabet(self):
        google=filing_ciks('GOOGL',1652044)
        self.assertEqual(google[0]['cik'],1288776)
        self.assertEqual(google[0]['end'],'2015-10-01')
        self.assertEqual(google[1]['start'],'2015-10-02')
        self.assertEqual(filing_ciks('XOM',2115436)[0]['cik'],34088)
        self.assertEqual(filing_ciks('CI',1739940)[0]['cik'],701221)
        self.assertEqual(filing_ciks('XRX',1770450)[0]['cik'],108772)
        for symbol,cik,predecessor,transition in [('BHGE',1701605,808362,'2017-07-03'),
                    ('DXC',1688568,23082,'2017-04-01'),('MYL',1623613,69499,'2015-02-27'),
                    ('ESRX',1532063,885721,'2012-04-02')]:
            history=filing_ciks(symbol,cik)
            self.assertEqual(history[0]['cik'],predecessor)
            self.assertEqual(history[1]['start'],transition)
        self.assertEqual(filing_ciks('MYL',1623613)[0]['evidenceThrough'],'2015-03-02')
        self.assertEqual([r['cik'] for r in filing_ciks('AVGO',1730168)],[1441634,1649338,1730168])

    def test_round_grids_are_actual_ordered_sessions_with_contiguous_annual_boundaries(self):
        rounds=self.dataset['rounds']
        for index,rnd in enumerate(rounds):
            dates=rnd['valuationDates']
            self.assertEqual(dates,sorted(set(dates)))
            self.assertEqual(dates[0],rnd['executionDate'])
            self.assertEqual(dates[-1],rnd['endDate'])
            self.assertGreater(rnd['executionDate'],rnd['cutoff'])
            self.assertLessEqual(len(dates),14)
            if index<len(rounds)-1:self.assertEqual(rnd['endDate'],rounds[index+1]['executionDate'])
        self.assertEqual(rounds[-1]['endDate'],self.dataset['asOf'])

    def test_sampled_quotes_never_extend_beyond_observed_market_date(self):
        sample=set(self.dataset['sampleDates'])
        for asset in self.dataset['assets']:
            dates=[p['date'] for p in asset['points']]
            self.assertEqual(dates,sorted(set(dates)))
            for point in asset['points']:
                self.assertIn(point['date'],sample)
                self.assertLessEqual(point['date'],self.dataset['asOf'])
                self.assertGreater(point['adjustedClose'],0)
            if asset.get('returnSource')=='Quandl WIKI archived adjusted close':
                self.assertEqual(asset['priceBasis'],'contemporaneous-unadjusted-close')
                bounds=asset['archiveIdentityBounds']
                if bounds.get('start'):self.assertTrue(all(d>=bounds['start'] for d in dates))
                if bounds.get('end'):self.assertTrue(all(d<=bounds['end'] for d in dates))
            if asset.get('priceBasis')=='contemporaneous-unadjusted-close' and asset.get('returnSource')!='Quandl WIKI archived adjusted close':
                # Missing raw closes remain unavailable: adjusted return units
                # cannot masquerade as historical dollars per share for P/E.
                for point in asset['points']:
                    if point['date']>'2018-03-27':self.assertIsNone(point['close'])

    def test_coverage_counts_missing_members_instead_of_removing_them(self):
        for rnd in self.dataset['rounds']:
            counts=rnd['coverage']
            self.assertEqual(counts['members'],len(rnd['eligibleAssetIds']))
            self.assertEqual(counts['members'],counts['priced']+counts['unavailable'])


if __name__=='__main__':unittest.main()
