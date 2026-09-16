import unittest
from config import load_config
from scraper import extract

class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()
    def run_source(self,provider,body):
        p=next(p for p in self.cfg['providers'] if p['id']==provider)
        return extract(body,p['source'],p,self.cfg,'2026-09-16T12:39:00+00:00')
    def test_dreamhost_requires_same_card_sale_and_renewal(self):
        body='<span>Stack 4</span><p>On Sale First 3 months at $8.99 /mo Auto-renews at $15.99 /mo after 3 months. 2 vCPU AMD EPYC 4 GB RAM 75 GB NVMe SSD Unmetered Bandwidth</p>Other VPS hosts meter'
        result=self.run_source('dreamhost',body)
        self.assertEqual(result[0]['price'],'8.99')
        self.assertEqual(result[0]['renewal_price'],'USD 15.99/month after 3 months')
        self.assertEqual(self.run_source('dreamhost',body.replace('On Sale','Regular pricing')),[])
        self.assertEqual(self.run_source('dreamhost',body.replace('after 3 months','after 6 months')),[])
    def test_inmotion_uses_only_selected_consistent_term(self):
        body='<h3>VPS 4 vCPU</h3><div class="imh-switcher">You Save 41% $9.99 /mo For 24 month term Renews at $16.99 /mo<a data-term="36">Select</a></div><div class=" active imh-switcher">You Save 48% $13.99 /mo For 24 month term Renews at $26.99 /mo<a data-term="24">Select</a></div><ul class="imh-rostrum-details-list"><li>4 vCPU Cores</li></ul>Included In All Plans:'
        result=self.run_source('inmotion-hosting',body)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['price'],'13.99')
        self.assertEqual(self.run_source('inmotion-hosting',body.replace('data-term="24"','data-term="12"')),[])
    def test_ramnode_bonus_is_not_price_and_requires_scope(self):
        body='<div class="whmcspage">Get an extra 25% Cloud Credit! Promo code CLOUD25. Sign up, add at least $5 in Cloud Credit. Only for Cloud (KVM, VDS) service.</div>'
        result=self.run_source('ramnode',body)
        self.assertEqual(result[0]['kind'],'cloud credit bonus')
        self.assertNotIn('price',result[0])
        self.assertEqual(self.run_source('ramnode',body.replace('Only for Cloud (KVM, VDS) service.','')),[])
