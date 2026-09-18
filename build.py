# ::ILANG
# ::STATE{@SELF, role:从I-Lang和真实数据生成静态站}
# ::RULE{过期或陈旧数据下架 缺字段不编造 HTML转义}
# ::BOUNDARY{never:捏造价格日期排名或已部署状态}
import json
import hashlib
import re
import shutil
from datetime import datetime, timezone, timedelta
from html import escape
from string import Template
from xml.etree.ElementTree import Element, SubElement, ElementTree
from config import ROOT, load_config, safe_url

def active(o, cfg, now):
    try:
        fetched = datetime.fromisoformat(o['fetched_at'])
        if fetched.tzinfo is None or not timedelta(0) <= now-fetched <= timedelta(hours=cfg['max_age_hours']):
            return False
        if o.get('valid_until') and o['valid_until'] < now.date().isoformat():
            return False
        if o.get('availability') == 'https://schema.org/OutOfStock':
            return False
        safe_url(o['offer_url'])
        safe_url(o['source_url'])
        return True
    except (KeyError,ValueError,TypeError):
        return False

def offer_schema(o):
    result = {'@type':'Offer','name':o['title'],'url':o['offer_url']}
    if 'price' in o and 'currency' in o:
        result.update(price=o['price'],priceCurrency=o['currency'])
    if o.get('valid_until'):
        result['priceValidUntil'] = o['valid_until']
    if o.get('availability'):
        result['availability'] = o['availability']
    return result

def neutral_metadata(text):
    # Only metadata is rewritten; source evidence and visible body stay intact.
    text = re.sub(r"(?i)\b(\d+(?:\.\d+)?)\s*%\s*off\b", r"price reduction of \1 percent", text)
    for pattern, replacement in [
        (r"\bdiscounts?\b", "price reductions"),
        (r"\bcoupons?\b", "codes"),
        (r"\b(?:offers?|promotions?|promos?)\b", "plans and terms"),
        (r"\bcashback\b", "rebates"),
        (r"\bdeals\b", "plans"),
        (r"\bdeal\b", "plan"),
        (r"%\s*off\b", "percent price reduction"),
    ]:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def build():
    cfg = load_config()
    data = json.loads((ROOT/'data/offers.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    providers = {p['id']:p for p in cfg['providers']}
    offers = [o for o in data['offers'] if o['provider_id'] in providers and active(o,cfg,now)]
    base = cfg['domain'].rstrip('/')
    # Manually transcribed official affiliate-center cards, separate from scraped evidence.
    racknerd_plans = json.loads(cfg.get('racknerd_plans', '[]'))
    racknerd_urls = {safe_url(plan['url']) for plan in racknerd_plans}
    def origin_links(html):
        return re.sub(r'(\b(?:href|src)=["\'])/(?!/)', lambda m: m[1]+escape(base,quote=True)+'/', html)
    dest = ROOT/'site'
    preserved_pages = {}
    preserve_file = ROOT/'data/coverage-preserve.json'
    if preserve_file.exists():
        baseline = json.loads(preserve_file.read_text(encoding='utf-8'))
        unchanged = {p['provider_id'] for p in baseline['providers']
                     if p['offers']==[o for o in offers if o['provider_id']==p['provider_id']]}
        for path,item in baseline['pages'].items():
            provider = next((o['provider_id'] for o in offers if path=='/plans/'+o['id']+'/'),None)
            if path.startswith('/providers/'):
                provider=path.split('/')[2]
            cached=dest/item['path']
            if provider in unchanged and cached.is_file():
                raw=cached.read_bytes()
                if hashlib.sha256(raw).hexdigest()==item['sha256']:
                    preserved_pages[path]=raw
    # Fixed generated directory only; clear stale detail pages after a provider is removed.
    if dest.is_symlink():
        raise ValueError('Refusing symlink output')
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    shutil.copytree(ROOT/'assets',dest/'assets')
    # The legacy social card carries the retired brand; do not publish it.
    (dest/'assets/og.png').unlink(missing_ok=True)
    pages = []
    style_version = hashlib.sha256((ROOT/'assets/style.css').read_bytes()).hexdigest()[:12]
    month = now.strftime('%B %Y')
    def render(template_name, **values):
        template_name = cfg.get('template_'+template_name.removesuffix('.html'),template_name)
        if '/' in template_name or '\\' in template_name or not template_name.endswith('.html'):
            raise ValueError('Template must be a local HTML filename')
        return Template((ROOT/'templates'/template_name).read_text(encoding='utf-8')).substitute(values)
    def write(path,title,description,content,schemas=(),lastmod=None,noindex=False,keep_metadata=False):
        if not keep_metadata:
            title, description = neutral_metadata(title), neutral_metadata(description)
        canonical = base+path
        html = render('base.html', brand=escape(cfg['brand']),title=escape(title), description=escape(description), canonical=escape(canonical,quote=True), content=content, locale=escape(cfg['locale']), robots='noindex,follow' if noindex else 'index,follow', schema=json.dumps({'@context':'https://schema.org','@graph':list(schemas)},ensure_ascii=False).replace('<','\\u003c'))
        html = html.replace('/assets/style.css"',f'/assets/style.css?v={style_version}"')
        # Replace configured provider exits only; preserve source evidence and copy.
        from urllib.parse import urlsplit
        def affiliate_exit(match):
            attrs = match[0]
            href = re.search(r'href="([^"]+)"', attrs)
            if not href:
                return attrs
            from html import unescape
            if unescape(href[1]) in {'https://my.racknerd.com/aff.php?aff=21233', 'https://www.racknerd.com/privacy-policy', 'https://www.racknerd.com/affiliates-terms-of-service'} or unescape(href[1]) in racknerd_urls:
                return attrs
            host = urlsplit(href[1]).hostname or ''
            for provider in cfg['providers']:
                domain = urlsplit(provider['home']).hostname.removeprefix('www.')
                if provider['affiliate'] and (host == domain or host.endswith('.'+domain)):
                    attrs = attrs.replace(href[0], 'href="'+escape(provider['affiliate'],quote=True)+'"')
                    rel = re.search(r'rel="([^"]*)"', attrs)
                    if rel:
                        tokens = list(dict.fromkeys(rel[1].split()+['sponsored','noopener']))
                        attrs = attrs.replace(rel[0], 'rel="'+' '.join(tokens)+'"')
                    else:
                        attrs = attrs[:-1]+' rel="sponsored noopener">'
                    break
            return attrs
        if path not in {'/hostinger-coupon-code/', '/namecheap-promo-code/', '/godaddy-promo-code/', '/bluehost-promo-code/', '/hostgator-promo-code/'}:
            html = re.sub(r'<a\b[^>]*>', affiliate_exit, html)

        output = dest / ('index.html' if path=='/' else path.lstrip('/')+'index.html')
        output.parent.mkdir(parents=True,exist_ok=True)
        if path in preserved_pages:
            output.write_bytes(preserved_pages[path])
        else:
            output.write_text(origin_links(html),encoding='utf-8')
        if not noindex:
            pages.append((canonical,lastmod))
    def detail_path(o):
        return '/plans/'+o['id']+'/'
    def cards(items):
        result = ''
        for o in items:
            p = providers[o['provider_id']]
            price = escape(o['currency']+' '+str(o['price'])+o.get('price_unit','')) if 'price' in o else 'See official terms'
            result += f'<article class="deal"><div class="eyebrow">{escape(p["name"])} <span>{escape(o["kind"])}</span></div><h3><a href="{detail_path(o)}">{escape(o["title"])}</a></h3><p class="price">{price}</p><p class="muted">Source checked {escape(o["fetched_at"].replace("T"," ")[:16])} UTC</p><a class="arrow" href="{detail_path(o)}">View offer details <span aria-hidden="true">↗</span></a></article>'
        return result or '<div class="empty">No freshly verified promotions right now. Check the official provider pages below.</div>'
    def itemlist(items):
        return {'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i+1,'url':base+detail_path(o)} for i,o in enumerate(items)]}
    def crumbs(name,path):
        return {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':base+'/'},{'@type':'ListItem','position':2,'name':name,'item':base+path}]}
    statuses = {s['provider_id']:s for s in data['sources']}
    def coverage(provider_id):
        status = statuses.get(provider_id,{})
        if status.get('status') == 'unavailable':
            error = status.get('error','')
            reason = 'Source could not be fetched'
            if 'Disallowed by robots.txt' in error:
                reason = 'Explicitly disallowed by robots.txt'
            elif 'robots' in error.lower():
                reason = 'robots.txt could not be retrieved; crawling stopped'
            elif 'HTTP' in error:
                reason = 'Official source returned an HTTP error'
            return 'Not verified: '+reason+'.'
        if status.get('status') == 'no_match':
            return 'Not verified: no qualifying VPS promotion found on the official source.'
        if status.get('status') == 'ok':
            return 'Official source checked; only fresh qualifying promotions are listed.'
        return 'Not verified: source has not been checked.'
    rows = ''
    for p in cfg['providers']:
        s = statuses.get(p['id'],{})
        count = sum(o['provider_id']==p['id'] for o in offers)
        label = f'{count} official promotion'+('s' if count!=1 else '') if count else 'No fresh offer verified'
        label += '<br><small>'+escape(coverage(p['id']))+'</small>'
        provider_link = f'<a href="/providers/{p["id"]}/">{escape(p["name"])}</a>' if count else escape(p['name'])
        source_target, source_label = p['source'], 'Official source ↗'
        if p['id'] == 'racknerd' and racknerd_plans and count:
            source_target = detail_path(next(o for o in offers if o['provider_id']=='racknerd'))
            source_label = 'View five plans and terms ↗'
        rows += f'<tr><td>{provider_link}</td><td>{label}</td><td>{escape(s.get("checked_at",s.get("attempted_at","Not checked"))[:16].replace("T"," "))}</td><td><a href="{escape(source_target,quote=True)}" rel="noopener">{source_label}</a></td></tr>'
    lastmod = max((o['fetched_at'] for o in offers),default=None)
    home = render('index.html',count=len(offers),provider_count=len(providers),cards=cards(offers),source_rows=rows,update_hours=cfg['update_hours'])
    if 'hostinger' in providers:
        home += '<section><h2>Buying guides</h2><p><a href="/hostinger-coupon-code/">Hostinger coupon code: official evidence and VPS terms</a></p></section>'
    if 'namecheap' in providers and (ROOT/'data/namecheap-guide.json').exists():
        home += '<section><h2>Namecheap buying guide</h2><p><a href="/namecheap-promo-code/">Namecheap promo code: official evidence and VPS terms</a></p></section>'
    if (ROOT/'data/godaddy-guide.json').exists():
        home += '<section><h2>GoDaddy buying guide</h2><p><a href="/godaddy-promo-code/">GoDaddy promo code: official evidence and VPS terms</a></p></section>'
    if (ROOT/'data/bluehost-guide.json').exists():
        home += '<section><h2>Bluehost buying guide</h2><p><a href="/bluehost-promo-code/">Bluehost promo code: official evidence and VPS terms</a></p></section>'
    if (ROOT/'data/hostgator-guide.json').exists():
        home += '<section><h2>HostGator buying guide</h2><p><a href="/hostgator-promo-code/">HostGator promo code: official evidence and VPS terms</a></p></section>'
    write('/',f'VPS plans & trials — {month} | {cfg["brand"]}',f'Compare {len(offers)} freshly checked official VPS plans and terms from {len(providers)} providers. Source links and transparent terms.',home,[itemlist(offers)],lastmod)
    for p in cfg['providers']:
        items = [o for o in offers if o['provider_id']==p['id']]
        if not items:
            continue
        schema = {'@type':'Service','name':p['name']+' VPS hosting','provider':{'@type':'Organization','name':p['name'],'url':p['home']},'offers':[offer_schema(o) for o in items]}
        # Only aggregate comparable actual prices in the same currency, never trial credits.
        priced = [o for o in items if 'price' in o and 'currency' in o]
        if len(priced)>1 and len({o['currency'] for o in priced})==1:
            schema['offers'] = {'@type':'AggregateOffer','lowPrice':min(float(o['price']) for o in priced),'highPrice':max(float(o['price']) for o in priced),'priceCurrency':priced[0]['currency'],'offerCount':len(priced),'offers':[offer_schema(o) for o in priced]}
        path = '/providers/'+p['id']+'/'
        content = render('provider.html',name=escape(p['name']),cards=cards(items),source=escape(p['source'],quote=True))
        if p['id'] == 'racknerd' and racknerd_plans:
            content = content.replace(escape(p['source'],quote=True),detail_path(items[0])).replace('Check the source ↗','View five plans and terms ↗')
        content += '<p class="note">'+escape(coverage(p['id']))+'</p>'
        write(path,f'{p["name"]} VPS plans and terms — {month}',f'{len(items)} freshly checked {p["name"]} plans and terms. Review eligibility and official terms.',content,[schema,crumbs(p['name'],path)],max((o['fetched_at'] for o in items),default=None),not items)
    for o in offers:
        p = providers[o['provider_id']]
        target = p['affiliate'] or o['offer_url']
        relation = 'sponsored noopener' if p['affiliate'] else 'noopener'
        disclosure = 'This is an affiliate link. We may earn a commission if you purchase through it.' if p['affiliate'] else 'This is a direct official link. No affiliate tracking link is configured for this offer.'
        price = escape(o['currency']+' '+str(o['price'])+o.get('price_unit','')) if 'price' in o else 'Not independently extracted — confirm with provider'
        content = render('deal.html',name=escape(p['name']),provider_id=p['id'],title=escape(o['title']),kind=escape(o['kind']),price=price,valid_until=escape(o.get('valid_until','Not published in the extracted data')),fetched=escape(o['fetched_at']),source=escape(o['source_url'],quote=True),target=escape(target,quote=True),rel=relation,disclosure=disclosure)
        if 'initial_term' in o:
            content=content.replace('<dt>Price</dt>','<dt>Initial price</dt>')
            detail_fields=''.join('<dt>'+label+'</dt><dd>'+escape(o.get(key,'Not specified'))+'</dd>' for label,key in [('Initial period','initial_term'),('Renewal price','renewal_price'),('Specifications','specifications'),('Terms','terms')])
            content=content.replace('<dt>Published expiry</dt>',detail_fields+'<dt>Published expiry</dt>')
            if o['kind']=='cloud credit bonus':
                content=content.replace(price,'Not specified — this is a credit bonus, not a hosting price')
        if p['id'] == 'racknerd' and racknerd_plans:
            content = content.replace(escape(o['source_url'],quote=True),'#racknerd-plans').replace(escape(target,quote=True),'#racknerd-plans')
            content = content.replace('View the original source ↗','View five plans and terms ↓').replace('View official offer ↗','Choose a plan below ↓').replace(price,'See annual prices below')
            plan_rows = ''.join('<tr><td>'+escape(plan['memory'])+'</td><td>'+escape(plan['annual'])+'</td><td>'+escape(plan['pid'])+'</td><td>'+escape(plan['specs'])+'</td><td><a class="button" href="'+escape(plan['url'],quote=True)+'" rel="sponsored noopener">View '+escape(plan['memory'])+' plan ↗</a></td></tr>' for plan in racknerd_plans)
            content += '<section id="racknerd-plans"><h2>Five KVM VPS plans and terms</h2><p>Annual prices and specifications listed in RackNerd’s affiliate center. Renewal prices and billing cycles are subject to the official product page.</p><div class="table-wrap"><table><thead><tr><th>Memory</th><th>Annual price</th><th>Product ID</th><th>Configuration</th><th>Plan link</th></tr></thead><tbody>'+plan_rows+'</tbody></table></div><p class="small">This is an affiliate link. We may earn a commission if you purchase through it.</p></section>'
        write(detail_path(o),f'{p["name"]}: {o["title"]} — {month}',f'{o["title"]}. Official source checked {o["fetched_at"][:10]}. Review terms and eligibility before purchase.',content,[offer_schema(o),crumbs(o['title'],detail_path(o))],o['fetched_at'])
    compare_rows = ''.join(f'<tr><td>{escape(providers[o["provider_id"]]["name"])}</td><td><a href="{detail_path(o)}">{escape(o["title"])}</a></td><td>{escape(o["kind"])}</td><td>{escape(o.get("currency","")+" "+str(o["price"])+o.get("price_unit","")) if "price" in o else "Not extracted"}</td><td>{escape(o.get("valid_until","Not specified"))}</td></tr>' for o in offers)
    write('/compare/',f'Compare VPS plans and terms — {month}',f'Compare {len(offers)} official VPS plans, plan types and published expiry dates.',render('compare.html',rows=compare_rows),[itemlist(offers),crumbs('Compare','/compare/')],lastmod)
    write('/about/',f'How we verify plan information | {cfg["brand"]}','Our sources, verification limits and affiliate disclosure.',render('about.html',hours=cfg['update_hours'],age=cfg['max_age_hours']),[crumbs('About','/about/')])
    write('/privacy/',f'Privacy policy | {cfg["brand"]}','Privacy, hosting information and planned third-party advertising.',render('privacy.html'),[crumbs('Privacy policy','/privacy/')])
    write('/contact/',f'Contact | {cfg["brand"]}','Contact PerkMingle, operated by Jiawei Li, for corrections and privacy questions.',render('contact.html'),[crumbs('Contact','/contact/')])
    if 'hostinger' in providers:
        guide = json.loads((ROOT/'data/hostinger-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/hostinger-coupon-code/','Hostinger coupon code: official evidence and VPS terms | '+cfg['brand'],'Is there an official Hostinger coupon code? Check the published code, VPS pricing and refund conditions with dated official sources.',render('hostinger-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if 'namecheap' in providers and (ROOT/'data/namecheap-guide.json').exists():
        guide = json.loads((ROOT/'data/namecheap-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/namecheap-promo-code/','Namecheap promo code: official evidence and VPS terms | '+cfg['brand'],'Is there an official Namecheap promo code? Check the published code, VPS pricing and refund conditions with dated official sources.',render('namecheap-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/godaddy-guide.json').exists():
        guide = json.loads((ROOT/'data/godaddy-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/godaddy-promo-code/','GoDaddy promo code: official evidence and VPS terms | '+cfg['brand'],'Is there an official GoDaddy promo code? Review verification limits, VPS pricing and refund conditions with dated official sources.',render('godaddy-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/bluehost-guide.json').exists():
        guide = json.loads((ROOT/'data/bluehost-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/bluehost-promo-code/','Bluehost promo code: official evidence and VPS terms | '+cfg['brand'],'Is there an official Bluehost promo code? Review verification limits, VPS pricing and refund conditions with dated official sources.',render('bluehost-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/hostgator-guide.json').exists():
        guide = json.loads((ROOT/'data/hostgator-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/hostgator-promo-code/','HostGator promo code: official evidence and VPS terms | '+cfg['brand'],'Is there an official HostGator promo code? Review verification limits, VPS pricing and refund conditions with dated official sources.',render('hostgator-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    sitemap = Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url,modified in pages:
        el = SubElement(sitemap,'url')
        SubElement(el,'loc').text = url
        if modified:
            SubElement(el,'lastmod').text = modified
    ElementTree(sitemap).write(dest/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    (dest/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n',encoding='utf-8')
    # Retired empty provider pages lead to the current source table, not cached shells.
    retired = [p for p in cfg['providers'] if not any(o['provider_id']==p['id'] for o in offers)]
    (dest/'_redirects').write_text('/deals/:id/ /plans/:id/ 301\n/deals/:id /plans/:id/ 301\n'+''.join(f'/providers/{p["id"]}/ / 302\n/providers/{p["id"]} / 302\n' for p in retired),encoding='utf-8')
    (dest/'404.html').write_text(origin_links('<!doctype html><html lang="en"><meta charset="utf-8"><title>Plan unavailable</title><meta name="description" content="This plan is no longer listed or could not be verified."><h1>This offer is no longer listed</h1><p>It may have expired or could not be verified.</p><a href="/">See current offers</a></html>'),encoding='utf-8')
    (dest/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Cache-Control: public, max-age=300\n',encoding='utf-8')
    print(f'Built {len(pages)} indexable pages; {len(offers)} fresh offers; {len(providers)} configured providers')

if __name__ == '__main__':
    build()
