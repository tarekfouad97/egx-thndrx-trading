"""Regression tests for capital/risk invariants and report trust boundaries."""
import copy
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'skills/egx-check/scripts'))
import egx
import egx_gates as G
import egx_page as P

class RiskTests(unittest.TestCase):
    def setUp(self):
        self.cfg = copy.deepcopy(egx.DEFAULT_CONFIG)
        self.cfg.update(min_order_egp=1, stop_slippage_atr=0.5)
        self.stock = {'tk':'TEST', 'verdict':'valid', 'sector':'Banks', 'atr':1,
                      'plan':{'entry':100, 'stop':98, 'target':112, 'rr':6}, 'score':{'total':7}}
        self.run = {'meta':{'amount':20000, 'cash':20000, 'equity':100000, 'risk_pct':1},
                    'market':{'egx30':{'regime':'Up'}}, 'stocks':[self.stock]}
    def allocate(self):
        return egx.allocate(self.run, self.cfg)['allocation']
    def test_wait_never_funded(self):
        self.stock['verdict']='wait'
        self.run['meta']['include_wait_orders']=True
        self.assertEqual(self.allocate()['deployed'],0)
    def test_zero_risk_preserved(self):
        self.run['meta']['risk_pct']=0
        self.assertEqual(self.allocate()['deployed'],0)
    def test_cash_unknown_or_zero_blocks(self):
        self.run['meta']['cash']=0
        self.assertEqual(self.allocate()['deployed'],0)
        del self.run['meta']['cash']
        self.assertEqual(self.allocate()['deployed'],0)
    def test_cash_and_stressed_risk_limits(self):
        self.run['meta'].update(cash=5000,risk_pct=0.1)
        a=self.allocate()
        self.assertGreater(a['deployed'],0)
        self.assertLessEqual(a['deployed'],5000)
        self.assertLessEqual(a['total_risk'],100)
        self.assertGreater(a['rows'][0]['loss_if_stop'],a['rows'][0]['shares']*2)
    def test_t0_shares_cash_and_concentration(self):
        intraday=copy.deepcopy(self.stock)
        intraday.update(tk='DAY',mode='t0',t0={'plan':self.stock['plan'].copy(),'atr5':1})
        self.run['stocks'].append(intraday)
        self.run['meta']['cash']=10000
        a=self.allocate()
        self.assertEqual(len(a['rows']),2)
        self.assertTrue(all(r['shares']>0 for r in a['rows']))
        self.assertLessEqual(sum(r['value']+r['fees_buy'] for r in a['rows']),10000)
        self.assertAlmostEqual(a['deployed'],sum(r['value']+r['fees_buy'] for r in a['rows']))
    def test_existing_unknown_stop_blocks(self):
        self.run['holdings']=[{'tk':'HELD','value':1000}]
        self.assertEqual(self.allocate()['deployed'],0)
    def test_net_rr_recomputed_at_actual_size(self):
        self.stock['plan'].update(target=104,rr=20)
        self.assertEqual(self.allocate()['deployed'],0)
    def test_invalid_price_geometry(self):
        for price in (None,0,-1,float('nan'),float('inf'),True):
            self.stock['plan']['stop']=price
            self.assertEqual(self.allocate()['deployed'],0)
    def test_negative_slippage_rejected(self):
        self.cfg['stop_slippage_atr']=-1
        with self.assertRaises(ValueError): self.allocate()
    def test_invalid_plan_cannot_crash_ranking(self):
        self.stock['plan']['entry']=float('nan')
        self.assertEqual(egx.rank_score(self.stock,self.run,self.cfg),0)
    def test_report_escaping_and_url_schemes(self):
        chart=P.candle_chart([['date',1,2,0.5,1.5]]*5,[],label='" onload="alert(1)')
        self.assertNotIn('aria-label="" onload=',chart)
        self.assertIn('&quot;',chart)
        self.assertEqual(P.safe_url('javascript:alert(1)'),'#')
        self.assertEqual(P.safe_url('https://example.com'),'https://example.com')
    def test_intraday_card_uses_intraday_quote(self):
        stock=copy.deepcopy(self.stock)
        stock.update(mode='t0',last=100,chg=-2,t0={'last':105.55,'dayChg':3.5,'plan':self.stock['plan'],'session':{'day':'2026-11-11'}})
        card=P.pass_card(stock,None,'Same day',1)
        self.assertIn('105.55',card)
        self.assertIn('+3.50%',card)
        self.assertIn('2026-11-11',card)
    def test_ledger_counts_only_completed_proofs(self):
        P._STEPS={'groups':[{'tk':None,'n':10,'done':2,'skipped':3,'attested':['X'],'typed':[], 'bad':[], 'step':'C0','title':'Setup'}]}
        self.assertIn('1 script-checked',P.steps_bar(None))

if __name__=='__main__': unittest.main()
