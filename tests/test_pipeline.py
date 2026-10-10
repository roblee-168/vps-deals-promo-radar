# ::ILANG
# ::STATE{@SELF, role:验证真实数据边界和配置生效}
# ::BOUNDARY{never:把测试合成数据混入生产}
import json
import tempfile
import unittest
from urllib.parse import urlsplit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import build
from config import ROOT, load_config
from scraper import extract, Fetcher
from sync_workflow import workflow

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()
        self.now = datetime.now(timezone.utc)
        self.p = self.cfg['providers'][0]
    def record(self,**kw):
        return dict(dict(id='test',provider_id=self.p['id'],title='Test offer',kind='promotion',offer_url=self.p['source'],source_url=self.p['source'],fetched_at=self.now.isoformat()),**kw)
    def test_credit_is_not_price(self):
        result = extract('<h1>Free $100 credit trial</h1><p>$9 a month</p>',self.p['source'],self.p,self.cfg,self.now.isoformat())
        self.assertNotIn('price',result[0])
        self.assertNotIn('price',build.offer_schema(result[0]))
    def test_scoped_price_and_expiry(self):
        body = '<h1>Test sale</h1><script type="application/ld+json">'+json.dumps({'@type':'Offer','name':'Test sale','price':'4.99','priceCurrency':'USD','priceValidUntil':'2020-01-01'})+'</script>'
        record = extract(body,self.p['source'],self.p,self.cfg,self.now.isoformat())[0]
        self.assertEqual(record['price'],'4.99')
        self.assertFalse(build.active(record,self.cfg,self.now))
    def test_stale_and_future(self):
        for delta in (-30,2):
            o = self.record()
            o['fetched_at'] = (self.now+timedelta(hours=delta)).isoformat()
            self.assertFalse(build.active(o,self.cfg,self.now))
    def test_english_hreflang_helper_changes_only_the_two_links(self):
        before = '<!doctype html><html><head><title>English home</title></head><body><h1>Unchanged</h1></body></html>'
        expected = before.replace('</head>', '<link rel="alternate" hreflang="ja-JP" href="https://perkmingle.com/ja/"><link rel="alternate" hreflang="x-default" href="https://perkmingle.com/"></head>')
        self.assertEqual(build.add_english_hreflang(before,'https://perkmingle.com/ja/','https://perkmingle.com/'),expected)
        with self.assertRaisesRegex(ValueError,'already contains'):
            build.add_english_hreflang(expected,'https://perkmingle.com/ja/','https://perkmingle.com/')
    def test_japanese_locale_configuration(self):
        self.assertEqual(self.cfg['localized']['locale'],'ja-JP')
        self.assertEqual(self.cfg['localized']['prefix'],'/ja/')
        ja = json.loads((ROOT/'data/ja-site.json').read_text(encoding='utf-8'))
        self.assertEqual(ja['currency'],'JPY')
        self.assertEqual(ja['checked'],'2026-10-10')
        self.assertEqual(len(ja['pages']),3)
        official_hosts={'vps.sakura.ad.jp','vps.conoha.jp','vpscloud.xserver.ne.jp'}
        for page in ja['pages']:
            for fact in page['facts']:
                self.assertTrue(fact['source'].startswith('https://'))
                self.assertIn(urlsplit(fact['source']).hostname,official_hosts)
    def test_no_arbitrary_page_price(self):
        body = '<h1>VPS sale</h1><script type="application/ld+json">{"@type":"Offer","name":"Unrelated domain","price":1,"priceCurrency":"USD"}</script>'
        self.assertNotIn('price',extract(body,self.p['source'],self.p,self.cfg,self.now.isoformat())[0])
    def test_robots_denial(self):
        f = Fetcher(self.cfg)
        with patch.object(f,'raw',return_value='User-agent: *\nDisallow: /'):
            with self.assertRaisesRegex(ValueError,'Disallowed'):
                f.get(self.p['source'])
    def test_trial_not_relabelled_by_upgrade_guarantee(self):
        body = '<h1>Free trial</h1><p>Test cloud servers.</p><h2>Upgrading</h2><p>First payment has a money-back guarantee.</p>'
        result = extract(body,'https://example.com/free-trial/',self.p,self.cfg,self.now.isoformat())
        self.assertEqual(result[0]['kind'],'trial / credit')
    def test_non_offer_and_mixed_catalog_are_not_vps_deals(self):
        for body,url in [('<h1>Save Time While We Do the Heavy Lifting</h1>',self.p['source']),
                         ('<h1>Domain sale</h1><h2>VPS Hosting</h2>','https://example.com/promos/'),
                         ('<h1>VPS sale ended</h1>',self.p['source']),
                         ('<h1>Managed VPS deals</h1><p>Black Friday hosting deals ended on December 5, 2025.</p>',self.p['source']),
                         ('<h1>Do you offer VPS discounts?</h1>',self.p['source'])]:
            self.assertEqual(extract(body,url,self.p,self.cfg,self.now.isoformat()),[])
    def test_config_removes_provider_from_built_site(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            import shutil
            shutil.copytree(ROOT/'templates',root/'templates')
            shutil.copytree(ROOT/'assets',root/'assets')
            (root/'data').mkdir()
            import shutil
            shutil.copy(ROOT/'data/ja-site.json',root/'data/ja-site.json')
            shutil.copy(ROOT/'data/ja-provider-batch.json',root/'data/ja-provider-batch.json')
            (root/'data/offers.json').write_text(json.dumps({'offers':[self.record()],'sources':[]}),encoding='utf-8')
            config_file = root/'site.ilang'
            original = (ROOT/'.ilang/site.ilang').read_text(encoding='utf-8')
            config_file.write_text('\n'.join(line for line in original.splitlines() if not line.startswith(self.p['name']+' |')),encoding='utf-8')
            changed = load_config(config_file)
            with patch.object(build,'ROOT',root),patch.object(build,'load_config',return_value=changed):
                build.build()
            self.assertFalse((root/'site/providers'/self.p['id']).exists())
            self.assertNotIn(self.p['name'],(root/'site/index.html').read_text(encoding='utf-8'))
            ja_home=(root/'site/ja/index.html').read_text(encoding='utf-8')
            self.assertIn('<html lang="ja-JP">',ja_home)
            self.assertIn('hreflang="en" href="https://perkmingle.com/"',ja_home)
            self.assertIn('canonical" href="https://perkmingle.com/ja/"',ja_home)
            ja_detail=(root/'site/ja/providers/sakura-vps/index.html').read_text(encoding='utf-8')
            self.assertIn('643円/月',ja_detail)
            self.assertIn('vps.sakura.ad.jp/specification/',ja_detail)
            self.assertEqual(ja_detail.count('rel="canonical"'),1)
            batch=json.loads((ROOT/'data/ja-provider-batch.json').read_text(encoding='utf-8'))
            for page in batch['pages']:
                detail=(root/'site/ja/providers'/page['slug']/'index.html').read_text(encoding='utf-8')
                self.assertIn(page['answer'],detail)
                self.assertEqual(detail.count('rel="canonical"'),1)
                self.assertIn(page['name'],detail.split('<footer',1)[1])
            saved_home=(root/'site/ja/index.html').read_bytes()
            saved_detail=(root/'site/ja/providers/sakura-vps/index.html').read_bytes()
            without_batch=dict(changed,localized=dict(changed['localized']))
            without_batch['localized'].pop('additional_data')
            with patch.object(build,'ROOT',root),patch.object(build,'load_config',return_value=without_batch):
                build.build()
            self.assertEqual(saved_home,(root/'site/ja/index.html').read_bytes())
            self.assertEqual(saved_detail,(root/'site/ja/providers/sakura-vps/index.html').read_bytes())
            en_home=(root/'site/index.html').read_text(encoding='utf-8')
            self.assertEqual(en_home.count('hreflang="ja-JP"'),1)
            self.assertEqual(en_home.count('hreflang="x-default"'),1)
    def test_failed_source_keeps_historical_urls_without_active_offer(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT/'templates',root/'templates')
            shutil.copytree(ROOT/'assets',root/'assets')
            (root/'data').mkdir()
            shutil.copy(ROOT/'data/ja-site.json',root/'data/ja-site.json')
            shutil.copy(ROOT/'data/ja-provider-batch.json',root/'data/ja-provider-batch.json')
            provider = next(p for p in self.cfg['providers'] if p['id']=='upcloud')
            record = self.record(provider_id='upcloud', evidence='Previously verified trial')
            cfg = dict(self.cfg, providers=[provider])
            (root/'data/offers.json').write_text(json.dumps({'offers':[], 'historical_offers':[record], 'sources':[{'provider_id':'upcloud','status':'unavailable','error':'robots unavailable'}]}),encoding='utf-8')
            with patch.object(build,'ROOT',root),patch.object(build,'load_config',return_value=cfg):
                build.build()
            plan = (root/'site/plans/test/index.html').read_text(encoding='utf-8')
            self.assertIn('Current availability could not be verified',plan)
            self.assertIn(record['fetched_at'],plan)
            self.assertNotIn('"@type": "Offer"',plan)
            sitemap = (root/'site/sitemap.xml').read_text(encoding='utf-8')
            self.assertIn('/plans/test/',sitemap)
            self.assertIn('/providers/upcloud/',sitemap)
            self.assertNotIn('/providers/upcloud/',(root/'site/_redirects').read_text(encoding='utf-8'))

    def test_schedule_matches_config(self):
        self.assertIn(self.cfg['cron'],workflow())

if __name__ == '__main__':
    unittest.main()
