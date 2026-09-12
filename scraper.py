# ::ILANG
# ::STATE{@SELF, role:按I-Lang抓取官方公开优惠并记录证据}
# ::RULE{遵守robots TLS验证 有界请求 失败撤下}
# ::BOUNDARY{never:编价格 编日期 绕反爬 把赠金当价格}
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin
from config import ROOT, load_config, safe_url

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []
        self.headings = []
        self.heading = None
        self.heading_parts = []
        self.ld = []
        self.ld_parts = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script','style','noscript'):
            self.hidden += 1
            if tag == 'script' and attrs.get('type') == 'application/ld+json':
                self.ld_parts = []
        if not self.hidden and tag in ('h1','h2','h3'):
            self.heading, self.heading_parts = tag, []
    def handle_endtag(self, tag):
        if tag == 'script' and self.ld_parts is not None:
            try:
                self.ld.append(json.loads(''.join(self.ld_parts)))
            except ValueError:
                pass
            self.ld_parts = None
        if tag in ('script','style','noscript'):
            self.hidden = max(0, self.hidden - 1)
        if tag == self.heading:
            self.headings.append(' '.join(' '.join(self.heading_parts).split()))
            self.heading = None
        if tag in ('p','div','li','h1','h2','h3'):
            self.parts.append('\n')
    def handle_data(self, data):
        if self.ld_parts is not None:
            self.ld_parts.append(data)
        if not self.hidden:
            self.parts.append(data)
            if self.heading:
                self.heading_parts.append(data)
    @property
    def text(self):
        return ' '.join(' '.join(self.parts).split())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class Fetcher:
    def __init__(self, cfg):
        self.cfg, self.robots, self.last = cfg, {}, {}
        self.opener = urllib.request.build_opener(NoRedirect)
    def raw(self, url):
        safe_url(url)
        host = urlsplit(url).hostname
        if any(not ipaddress.ip_address(a[4][0]).is_global for a in socket.getaddrinfo(host, 443)):
            raise ValueError('Non-public destination refused')
        wait = 1 - (time.monotonic() - self.last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self.last[host] = time.monotonic()
        req = urllib.request.Request(url, headers={'User-Agent':self.cfg['user_agent'],'Accept-Language':'en-US,en;q=0.8'})
        with self.opener.open(req, timeout=self.cfg['timeout_seconds']) as r:
            body = r.read(self.cfg['max_bytes'] + 1)
            if len(body) > self.cfg['max_bytes']:
                raise ValueError('Response exceeds size limit')
            return body.decode(r.headers.get_content_charset() or 'utf-8','replace')
    def allowed(self, url):
        u = urlsplit(url)
        origin = f'{u.scheme}://{u.netloc}'
        if origin not in self.robots:
            try:
                content = self.raw(origin + '/robots.txt')
                if '<html' in content.lower():
                    raise ValueError('robots returned HTML')
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(content.splitlines())
                self.robots[origin] = rp
            except urllib.error.HTTPError as e:
                if e.code in (404,410):
                    self.robots[origin] = True
                else:
                    raise ValueError(f'robots unavailable: HTTP {e.code}') from e
        rp = self.robots[origin]
        if rp is not True and not rp.can_fetch(self.cfg['user_agent'], url):
            raise ValueError('Disallowed by robots.txt')
        if rp is not True:
            delay = rp.crawl_delay(self.cfg['user_agent']) or rp.crawl_delay('*') or 1
            wait = delay - (time.monotonic() - self.last.get(u.hostname,0))
            if wait > 0:
                time.sleep(min(wait, 60))
            if delay > 60:
                raise ValueError('Crawl delay exceeds this bounded job budget')
    def get(self, url):
        for _ in range(5):
            self.allowed(url)
            try:
                return self.raw(url), url
            except urllib.error.HTTPError as e:
                if e.code not in (301,302,303,307,308):
                    raise
                url = urljoin(url,e.headers['Location'])
        raise ValueError('Too many redirects')

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:
            yield from walk(v)

def extract(body, url, provider, cfg, fetched):
    page = Page()
    page.feed(body)
    # A live page can advertise an old campaign. Explicit ended notices override headings.
    if re.search(r'(?i)\b(?:deals?|sale|promotion|offer|campaign)s?\s+(?:(?:has|have)\s+)?(?:ended|expired|is over|are over)\b',page.text):
        return []
    # Accept a short promotional heading, never an arbitrary currency elsewhere in the page.
    vps = r'(?i)\bvps\b|virtual private|cloud[- ]servers?|\bdroplets?\b'
    scoped_page = bool(re.search(vps,urlsplit(url).path))
    trial_page = bool(re.search(r'(?i)free[-/]?(?:trial|credit)',urlsplit(url).path) and re.search(vps,page.text))
    candidates = [h for h in page.headings if 5 <= len(h) <= 160
                  and re.search(cfg['promotion_pattern'],h)
                  and not re.search(r'(?i)\?|\b(?:expired|ended|over|coming soon|contact sales)\b',h)
                  and (scoped_page or re.search(vps,h) or (trial_page and re.search(r'(?i)trial|credit',h)))]
    if not candidates:
        return []
    title = candidates[0]
    record = dict(id=provider['id']+'-'+hashlib.sha256(url.encode()).hexdigest()[:10], provider_id=provider['id'], title=title, offer_url=url, source_url=url, fetched_at=fetched, kind='promotion', evidence=title)
    if re.search(r'(?i)credit|trial|money.back',title):
        record['kind'] = 'trial / credit' if 'money' not in title.lower() else 'money-back guarantee'
    if not trial_page and re.search(r'(?i)trial',title) and re.search(r'(?i)money.back guarantee',page.text):
        record['kind'] = 'money-back guarantee'
    # Price and validity require the SAME named structured Offer; no page-wide price guessing.
    for obj in walk(page.ld):
        types = obj.get('@type',[])
        if isinstance(types,str):
            types = [types]
        if 'Offer' not in types or obj.get('name') != title or record['kind'] != 'promotion':
            continue
        price = str(obj.get('price',''))
        currency = obj.get('priceCurrency','')
        if re.fullmatch(r'\d+(?:\.\d{1,4})?',price) and re.fullmatch(r'[A-Z]{3}',currency):
            record.update(price=price,currency=currency)
        date = obj.get('priceValidUntil')
        if isinstance(date,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):
            datetime.fromisoformat(date)
            record['valid_until'] = date
        if obj.get('availability') in ('https://schema.org/InStock','https://schema.org/OutOfStock'):
            record['availability'] = obj['availability']
    allowed = set(cfg['fields']) | {'id','provider_id','kind','evidence','availability'}
    return [{k:v for k,v in record.items() if k in allowed}]

def run():
    cfg = load_config()
    fetcher = Fetcher(cfg)
    offers, statuses = [], []
    for p in cfg['providers']:
        status = dict(provider_id=p['id'], attempted_at=utcnow())
        try:
            body, final = fetcher.get(p['source'])
            documents = [(body,final)]
            if body.lstrip().startswith('<?xml') or body.lstrip().startswith(('<urlset','<rss','<feed','<sitemapindex')):
                root = ET.fromstring(body)
                links = []
                for el in root.iter():
                    if el.tag.split('}')[-1] in ('loc','link'):
                        link = el.get('href') or el.text or ''
                        if urlsplit(link).hostname == urlsplit(final).hostname and re.search(cfg['promotion_pattern'], link):
                            links.append(link)
                documents = [fetcher.get(link) for link in sorted(set(links))[:cfg['max_pages_per_provider']]]
            found = []
            for html, url in documents:
                found.extend(extract(html,url,p,cfg,utcnow()))
            offers.extend(found)
            status.update(status='ok' if found else 'no_match', count=len(found), checked_at=utcnow())
        except Exception as e:
            status.update(status='unavailable', error=f'{type(e).__name__}: {e}'[:240])
        statuses.append(status)
        print(p['name'],status['status'],status.get('error',''))
    output = dict(generated_at=utcnow(),offers=list({o['id']:o for o in offers}.values()),sources=statuses)
    path = ROOT/'data/offers.json'
    path.parent.mkdir(exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)
    if not offers:
        print('WARNING: no verified promotions; build will show an honest empty state')

if __name__ == '__main__':
    run()
