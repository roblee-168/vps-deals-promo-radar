# ::ILANG
# ::STATE{@SELF, role:从I-Lang和真实数据生成静态站}
# ::RULE{过期或陈旧数据下架 缺字段不编造 HTML转义}
# ::BOUNDARY{never:捏造价格日期排名或已部署状态}
import json
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

def build():
    cfg = load_config()
    data = json.loads((ROOT/'data/offers.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    providers = {p['id']:p for p in cfg['providers']}
    offers = [o for o in data['offers'] if o['provider_id'] in providers and active(o,cfg,now)]
    base = cfg['domain'].rstrip('/')
    dest = ROOT/'site'
    # Fixed generated directory only; clear stale detail pages after a provider is removed.
    if dest.is_symlink():
        raise ValueError('Refusing symlink output')
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    shutil.copytree(ROOT/'assets',dest/'assets')
    pages = []
    month = now.strftime('%B %Y')
    def render(template_name, **values):
        template_name = cfg.get('template_'+template_name.removesuffix('.html'),template_name)
        if '/' in template_name or '\\' in template_name or not template_name.endswith('.html'):
            raise ValueError('Template must be a local HTML filename')
        return Template((ROOT/'templates'/template_name).read_text(encoding='utf-8')).substitute(values)
    def write(path,title,description,content,schemas=(),lastmod=None,noindex=False):
        canonical = base+path
        html = render('base.html', brand=escape(cfg['brand']),title=escape(title), description=escape(description), canonical=escape(canonical,quote=True), content=content, locale=escape(cfg['locale']), robots='noindex,follow' if noindex else 'index,follow', schema=json.dumps({'@context':'https://schema.org','@graph':list(schemas)},ensure_ascii=False).replace('<','\\u003c'))
        if not path.startswith('/deals/'):
            social = f'<meta property="og:image" content="{escape(base,quote=True)}/assets/og.png"><meta name="twitter:image" content="{escape(base,quote=True)}/assets/og.png">'
            html = html.replace('</head>',social+'</head>').replace('content="summary"','content="summary_large_image"')
        output = dest / ('index.html' if path=='/' else path.lstrip('/')+'index.html')
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(html,encoding='utf-8')
        if not noindex:
            pages.append((canonical,lastmod))
    def detail_path(o):
        return '/deals/'+o['id']+'/'
    def cards(items):
        result = ''
        for o in items:
            p = providers[o['provider_id']]
            price = escape(o['currency']+' '+str(o['price'])) if 'price' in o else 'See official terms'
            result += f'<article class="deal"><div class="eyebrow">{escape(p["name"])} <span>{escape(o["kind"])}</span></div><h3><a href="{detail_path(o)}">{escape(o["title"])}</a></h3><p class="price">{price}</p><p class="muted">Source checked {escape(o["fetched_at"].replace("T"," ")[:16])} UTC</p><a class="arrow" href="{detail_path(o)}">View offer details <span aria-hidden="true">↗</span></a></article>'
        return result or '<div class="empty">No freshly verified promotions right now. Check the official provider pages below.</div>'
    def itemlist(items):
        return {'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i+1,'url':base+detail_path(o)} for i,o in enumerate(items)]}
    def crumbs(name,path):
        return {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':base+'/'},{'@type':'ListItem','position':2,'name':name,'item':base+path}]}
    statuses = {s['provider_id']:s for s in data['sources']}
    rows = ''
    for p in cfg['providers']:
        s = statuses.get(p['id'],{})
        count = sum(o['provider_id']==p['id'] for o in offers)
        label = f'{count} official promotion'+('s' if count!=1 else '') if count else 'No fresh offer verified'
        rows += f'<tr><td><a href="/providers/{p["id"]}/">{escape(p["name"])}</a></td><td>{label}</td><td>{escape(s.get("checked_at",s.get("attempted_at","Not checked"))[:16].replace("T"," "))}</td><td><a href="{escape(p["source"],quote=True)}" rel="noopener">Official source ↗</a></td></tr>'
    lastmod = max((o['fetched_at'] for o in offers),default=None)
    home = render('index.html',count=len(offers),provider_count=len(providers),cards=cards(offers),source_rows=rows,update_hours=cfg['update_hours'])
    write('/',f'VPS deals & trials — {month} | {cfg["brand"]}',f'Compare {len(offers)} freshly checked official VPS promotions from {len(providers)} providers. Source links and transparent terms.',home,[itemlist(offers)],lastmod)
    for p in cfg['providers']:
        items = [o for o in offers if o['provider_id']==p['id']]
        schema = {'@type':'Service','name':p['name']+' VPS hosting','provider':{'@type':'Organization','name':p['name'],'url':p['home']},'offers':[offer_schema(o) for o in items]}
        # Only aggregate comparable actual prices in the same currency, never trial credits.
        priced = [o for o in items if 'price' in o and 'currency' in o]
        if len(priced)>1 and len({o['currency'] for o in priced})==1:
            schema['offers'] = {'@type':'AggregateOffer','lowPrice':min(float(o['price']) for o in priced),'highPrice':max(float(o['price']) for o in priced),'priceCurrency':priced[0]['currency'],'offerCount':len(priced),'offers':[offer_schema(o) for o in priced]}
        path = '/providers/'+p['id']+'/'
        content = render('provider.html',name=escape(p['name']),cards=cards(items),source=escape(p['source'],quote=True))
        write(path,f'{p["name"]} VPS promotions — {month}',f'{len(items)} freshly checked {p["name"]} promotions. Review eligibility and official terms.',content,[schema,crumbs(p['name'],path)],max((o['fetched_at'] for o in items),default=None),not items)
    for o in offers:
        p = providers[o['provider_id']]
        target = p['affiliate'] or o['offer_url']
        relation = 'sponsored noopener' if p['affiliate'] else 'noopener'
        disclosure = 'This is an affiliate link. We may earn a commission if you purchase through it.' if p['affiliate'] else 'This is a direct official link. No affiliate tracking link is configured for this offer.'
        price = escape(o['currency']+' '+str(o['price'])) if 'price' in o else 'Not independently extracted — confirm with provider'
        content = render('deal.html',name=escape(p['name']),provider_id=p['id'],title=escape(o['title']),kind=escape(o['kind']),price=price,valid_until=escape(o.get('valid_until','Not published in the extracted data')),fetched=escape(o['fetched_at']),source=escape(o['source_url'],quote=True),target=escape(target,quote=True),rel=relation,disclosure=disclosure)
        write(detail_path(o),f'{p["name"]}: {o["title"]} — {month}',f'{o["title"]}. Official source checked {o["fetched_at"][:10]}. Review terms and eligibility before purchase.',content,[offer_schema(o),crumbs(o['title'],detail_path(o))],o['fetched_at'])
    compare_rows = ''.join(f'<tr><td>{escape(providers[o["provider_id"]]["name"])}</td><td><a href="{detail_path(o)}">{escape(o["title"])}</a></td><td>{escape(o["kind"])}</td><td>{escape(o.get("currency","")+" "+str(o["price"])) if "price" in o else "Not extracted"}</td><td>{escape(o.get("valid_until","Not specified"))}</td></tr>' for o in offers)
    write('/compare/',f'Compare VPS promotions — {month}',f'Compare {len(offers)} official VPS promotions, offer types and published expiry dates.',render('compare.html',rows=compare_rows),[itemlist(offers),crumbs('Compare','/compare/')],lastmod)
    write('/about/',f'How we verify offers | {cfg["brand"]}','Our sources, verification limits and affiliate disclosure.',render('about.html',hours=cfg['update_hours'],age=cfg['max_age_hours']),[crumbs('About','/about/')])
    sitemap = Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url,modified in pages:
        el = SubElement(sitemap,'url')
        SubElement(el,'loc').text = url
        if modified:
            SubElement(el,'lastmod').text = modified
    ElementTree(sitemap).write(dest/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    (dest/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n',encoding='utf-8')
    (dest/'404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Offer unavailable</title><h1>This offer is no longer listed</h1><p>It may have expired or could not be verified.</p><a href="/">See current offers</a></html>',encoding='utf-8')
    (dest/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Cache-Control: public, max-age=300\n',encoding='utf-8')
    print(f'Built {len(pages)} indexable pages; {len(offers)} fresh offers; {len(providers)} configured providers')

if __name__ == '__main__':
    build()
