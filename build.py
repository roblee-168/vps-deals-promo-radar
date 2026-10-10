# ::ILANG
# ::STATE{@SELF, role:从I-Lang和真实数据生成静态站}
# ::RULE{过期或陈旧数据退出最新列表 历史页面保留 缺字段不编造 HTML转义}
# ::BOUNDARY{never:捏造价格日期排名或已部署状态}
import json
import hashlib
import re
import shutil
from datetime import datetime, timezone, timedelta
from html import escape
from html.parser import HTMLParser
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


def add_english_hreflang(markup, japanese_url, english_url):
    """Add only the two approved alternate links to the English home head."""
    head_end = markup.find('</head>')
    if head_end < 0:
        raise ValueError('English homepage is missing its head close tag')
    head = markup[:head_end]
    if re.search(r'<link\s+rel="alternate"\s+hreflang="(?:ja-JP|x-default)"', head):
        raise ValueError('English homepage already contains a localized alternate link')
    tags = (
        f'<link rel="alternate" hreflang="ja-JP" href="{escape(japanese_url, quote=True)}">'
        f'<link rel="alternate" hreflang="x-default" href="{escape(english_url, quote=True)}">'
    )
    return markup[:head_end] + tags + markup[head_end:]


def build_localized_pages(cfg, base, dest, pages, stylesheet_asset, analytics_tag):
    """Render separately sourced Japanese pages and append their sitemap entries."""
    localized = cfg.get('localized', {})
    if not localized:
        return
    data = json.loads((ROOT/'data'/localized['data']).read_text(encoding='utf-8'))
    if data.get('locale') != localized['locale'] or data.get('currency') != 'JPY':
        raise ValueError('Japanese data must use ja-JP and JPY')
    checked = data['checked']
    extra_pages = []
    if localized.get('additional_data'):
        extra = json.loads((ROOT/'data'/localized['additional_data']).read_text(encoding='utf-8'))
        if extra.get('locale') != localized['locale'] or extra.get('currency') != 'JPY':
            raise ValueError('Additional Japanese data must use ja-JP and JPY')
        extra_pages = extra['pages']
        all_slugs = [p['slug'] for p in data['pages'] + extra_pages]
        if len(all_slugs) != len(set(all_slugs)) or any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', s) for s in all_slugs):
            raise ValueError('Duplicate or invalid Japanese provider slug')
    datetime.strptime(checked, '%Y-%m-%d')
    prefix = localized['prefix']
    template = Template((ROOT/'templates'/localized['template']).read_text(encoding='utf-8'))
    stylesheet = (ROOT/'assets'/localized['stylesheet']).read_bytes()
    style_hash = hashlib.sha256(stylesheet.replace(b'\r\n', b'\n')).hexdigest()[:12]
    stylesheet_name = f'ja.{style_hash}.css'
    (dest/'assets'/stylesheet_name).write_bytes(stylesheet)
    checked_ja = f'{checked[:4]}年{int(checked[5:7])}月{int(checked[8:10])}日'

    def fact_table(facts):
        rows = []
        for fact in facts:
            source = safe_url(fact['source'])
            rows.append(
                '<tr>'
                f'<td data-label="確認できた内容">{escape(fact["offer"])}</td>'
                f'<td data-label="利用条件">{escape(fact["conditions"])}</td>'
                f'<td data-label="公式情報"><a rel="noopener" href="{escape(source, quote=True)}">{escape(fact["source_label"])} ↗</a></td>'
                f'<td data-label="確認日">{escape(checked_ja)}</td>'
                '</tr>'
            )
        return ('<div class="ja-table-wrap"><table class="ja-facts"><thead><tr>'
                '<th>確認できた内容</th><th>利用条件</th><th>公式情報</th><th>確認日</th>'
                '</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')

    def render(path, title, description, content, schema, alternates, provider_name=None):
        canonical = base + path
        alternate_tags = ''.join(
            f'<link rel="alternate" hreflang="{escape(item["lang"], quote=True)}" href="{escape(base+item["path"], quote=True)}">'
            for item in alternates
        )
        html = template.substitute(
            locale=escape(localized['locale']), brand=escape(cfg['brand']),
            title=escape(title), description=escape(description), canonical=escape(canonical, quote=True),
            analytics_tag=analytics_tag, stylesheet='/assets/'+stylesheet_asset,
            localized_stylesheet='/assets/'+stylesheet_name, alternate_links=alternate_tags,
            content=content, schema=json.dumps({'@context':'https://schema.org','@graph':schema}, ensure_ascii=False).replace('<','\\u003c'),
        )
        if path == prefix:
            html = html.replace('>VPSを比較</a>', '>サーバーを比較</a>')
        output = dest / (path.lstrip('/')+'index.html')
        if provider_name:
            html = html.replace('日本向けの公式情報を確認し、条件と確認日を掲載しています。', escape(provider_name)+'の公式情報を確認し、条件と確認日を掲載しています。')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding='utf-8')
        pages.append((canonical, checked))

    home = data['home']
    all_pages = data['pages'] + extra_pages
    groups = home.get('groups', {})
    entries, list_items = {}, []
    for position, page in enumerate(all_pages, 1):
        category = next((label for label, slugs in groups.items() if page['slug'] in slugs), '分類未確認')
        entries.setdefault(category, [])
        path = prefix + 'providers/' + page['slug'] + '/'
        source = safe_url(page['facts'][0]['source'])
        page_checked = page.get('checked', data['checked'])
        page_checked_ja = f'{page_checked[:4]}年{int(page_checked[5:7])}月{int(page_checked[8:10])}日'
        entries[category].append(
            '<article class="ja-provider-card"><p class="ja-eyebrow">'+escape(category)+' · 公式情報</p>'
            f'<h2>{escape(page["name"])}</h2>'
            f'<p>{escape(page["summary"])}</p>'
            f'<p class="ja-source-line"><a rel="noopener" href="{escape(source, quote=True)}">{escape(page["facts"][0]["source_label"])} ↗</a>・確認日 {escape(page_checked_ja)}</p>'
            f'<a class="ja-card-link" href="{escape(path, quote=True)}">条件と料金を見る →</a></article>'
        )
        list_items.append({'@type':'ListItem','position':position,'name':page['name'],'url':base+path})
    home_content = (
        '<main id="main" class="ja-main"><section class="ja-hero">'
        '<p class="ja-eyebrow">日本向け VPS・レンタルサーバー比較</p>'
        f'<h1>{escape(home["title"])}</h1><p class="ja-lead">{escape(home["lead"].format(count=len(all_pages)))}</p>'
        '<div class="ja-answer"><strong>クーポンコード・特典の確認結果は各社の条件ページに掲載</strong>'
        '<span>特典・料金は、適用条件、公式リンク、確認日とあわせて掲載しています。</span></div>'
        '<a class="ja-primary" href="#providers">公式情報を比較する ↓</a></section>'
        '<section id="providers" class="ja-section"><div class="ja-section-heading">'
        '<p class="ja-eyebrow">確認済みの公式情報</p><h2>特典と料金を条件ごとに比較</h2></div>'
        + ''.join('<section class="ja-section"><h3>'+escape(category)+'</h3>'+''.join('<p><a class="ja-card-link" href="'+prefix+c['slug']+'/">'+escape(c['title'])+' →</a></p>' for c in data.get('comparisons',[]) if c['category']==category)+'<div class="ja-provider-grid">'+''.join(cards)+'</div></section>' for category, cards in entries.items()) +
        '<p class="ja-note">キャンペーンの期限や条件は変更されることがあります。申込前にリンク先の公式情報をご確認ください。</p></section>'
        '<section class="ja-section ja-method"><h2>このページの見方</h2>'
        '<p>日本向けの公式ページで確認した価格・特典を掲載し、確認日を記しています。クーポンコードは、確認対象の公式ページに記載が見当たらない場合、その範囲を明示しています。</p></section></main>'
    )
    home_schema = [
        {'@type':'WebSite','name':'PerkMingle','url':base+prefix,'inLanguage':'ja-JP'},
        {'@type':'ItemList','name':home['title'],'itemListElement':list_items},
    ]
    render(prefix, home['title']+' | PerkMingle', home['description'], home_content, home_schema,
           [{'lang':'ja-JP','path':prefix},{'lang':'en','path':'/'},{'lang':'x-default','path':'/'}])

    for page in data['pages'] + extra_pages:
        checked = page.get('checked', data['checked'])
        datetime.strptime(checked, '%Y-%m-%d')
        checked_ja = f'{checked[:4]}年{int(checked[5:7])}月{int(checked[8:10])}日'
        path = prefix + 'providers/' + page['slug'] + '/'
        facts = fact_table(page['facts'])
        faq_html = ''.join(
            '<article class="ja-faq-item"><h3>'+escape(item['question'])+'</h3>'
            '<p>'+escape(item['answer'])+' <a rel="noopener" href="'+escape(safe_url(item['source']), quote=True)+'">公式情報 ↗</a>・確認日 '+escape(checked_ja)+'</p></article>'
            for item in page['faq']
        )
        content = (
            '<main id="main" class="ja-main"><nav class="ja-breadcrumb" aria-label="パンくず">'
            f'<a href="{escape(prefix, quote=True)}">日本語トップ</a><span aria-hidden="true"> / </span><span>{escape(page["name"])}</span></nav>'
            '<article><section class="ja-hero ja-detail-hero"><p class="ja-eyebrow">公式ページ確認 · '+escape(checked_ja)+'</p>'
            f'<h1>{escape(page["title"])}</h1><p class="ja-lead">{escape(page["answer"])}</p>'
            f'<div class="ja-answer"><strong>{escape(page["code_status"])}</strong><span>{escape(page["summary"])}</span></div></section>'
            '<section class="ja-section" id="facts"><div class="ja-section-heading">'
            '<p class="ja-eyebrow">公式情報と利用条件</p><h2>確認できた特典・料金</h2></div>'+facts+'</section>'
            '<section class="ja-section ja-faq"><p class="ja-eyebrow">よくある質問</p>'
            '<h2>申し込む前に確認したいこと</h2>'+faq_html+'</section>'
            f'<p class="ja-back"><a href="{escape(prefix, quote=True)}">← 日本語トップへ戻る</a></p></article></main>'
        )
        faq_schema = {'@type':'FAQPage','mainEntity':[
            {'@type':'Question','name':item['question'],'acceptedAnswer':{'@type':'Answer','text':item['answer']}}
            for item in page['faq']
        ]}
        breadcrumb = {'@type':'BreadcrumbList','itemListElement':[
            {'@type':'ListItem','position':1,'name':'日本語トップ','item':base+prefix},
            {'@type':'ListItem','position':2,'name':page['name'],'item':base+path},
        ]}
        render(path, page['title']+' | PerkMingle', page['description'], content, [faq_schema,breadcrumb],
               [{'lang':'ja-JP','path':path}], page['name'] if page in extra_pages else None)

    for comparison in data.get('comparisons', []):
        checked = comparison['checked']
        path = prefix + comparison['slug'] + '/'
        headers = ['提供会社', '最低料金（掲載済み確認範囲）', 'お試し・特典', '条件の要点', '公式出典', '確認日']
        lookup = {p['slug']: p for p in all_pages}
        table_rows, items = [], []
        for position, row in enumerate((r for r in comparison['rows'] if r['slug'] in lookup), 1):
            provider = lookup[row['slug']]
            prices = [provider['facts'][i] for i in row['price']]
            benefits = [provider['facts'][i] for i in row['benefit']]
            selected = list({json.dumps(f, ensure_ascii=False): f for f in prices + benefits}.values())
            detail = prefix + 'providers/' + provider['slug'] + '/'
            cells = [f'<a href="{escape(detail, quote=True)}">{escape(provider["name"])}</a>',
                     '<br>'.join(escape(f['offer']) for f in prices),
                     '<br>'.join(escape(f['offer']) for f in benefits),
                     '<br>'.join(escape(f['conditions']) for f in selected),
                     '<br>'.join(f'<a rel="noopener" href="{escape(safe_url(f["source"]), quote=True)}">{escape(f["source_label"])} ↗</a>' for f in selected),
                     escape(provider.get('checked', data['checked']))]
            table_rows.append('<tr>'+''.join(f'<td data-label="{escape(label, quote=True)}">{cell}</td>' for label,cell in zip(headers,cells))+'</tr>')
            items.append({'@type':'ListItem','position':position,'name':provider['name'],'url':base+detail})
        table = '<div class="ja-table-wrap"><table class="ja-facts"><thead><tr>'+''.join('<th scope="col">'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(table_rows)+'</tbody></table></div>'
        lead = '掲載済みの確認範囲を比較します。全プランの最安値や同じ構成の比較を意味するものではありません。'
        content = '<main id="main" class="ja-main"><h1 style="font-size:clamp(24px,4vw,36px);margin:0 0 12px">'+escape(comparison['title'])+'</h1>'+table+'<section class="ja-section ja-method"><h2>各欄の読み方</h2><p class="ja-lead">'+lead+'</p><p>月払い、長期契約の月額換算、起点価格、時間課金の月額上限は別の料金方式です。前払い・更新料金・初期費用・対象プランは条件欄で確認してください。税込と記載されていない金額の税区分は推定していません。確認日は元の提供会社ページの確認日であり、この比較ページの作成による新しい公式確認日ではありません。</p></section><section class="ja-section ja-faq"><h2>よくある質問</h2><article class="ja-faq-item"><h3>掲載順はおすすめ順ですか？</h3><p>いいえ。提供会社の掲載順です。構成・用途・契約期間の異なる料金を同一条件の順位にしていません。</p></article><article class="ja-faq-item"><h3>未確認の条件は補っていますか？</h3><p>補っていません。未確認の税区分、追加費用、返金条件は各提供会社ページの確認範囲に従います。</p></article></section><p class="ja-back"><a href="/ja/">日本語トップへ戻る</a></p></main>'
        render(path, comparison['title']+' | PerkMingle', '掲載済みの公式料金と特典を、適用条件・公式出典・確認日付きで比較します。', content,
               [{'@type':'ItemList','name':comparison['title'],'itemListElement':items}], [{'lang':'ja-JP','path':path}])

    english_home = dest/'index.html'
    english_markup = english_home.read_text(encoding='utf-8')
    english_home.write_text(add_english_hreflang(english_markup, base+prefix, base+'/'), encoding='utf-8')



def guide_library(markup):
    """Present existing guide links as an editorial feature and grouped directory."""
    class GuideParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.groups = []
            self.tag = None
            self.text = []
            self.href = ''
        def handle_starttag(self, tag, attrs):
            if tag in ('h2', 'a'):
                self.tag, self.text = tag, []
                if tag == 'a':
                    self.href = dict(attrs).get('href', '')
        def handle_data(self, text):
            if self.tag:
                self.text.append(text)
        def handle_endtag(self, tag):
            if tag != self.tag:
                return
            text = ''.join(self.text)
            if tag == 'h2':
                self.groups.append([text, []])
            elif self.groups:
                self.groups[-1][1].append((self.href, text))
            self.tag = None
    parser = GuideParser()
    parser.feed(markup)
    featured = {
        '/vps-vs-shared-hosting/': ('HOSTING DECISIONS', 'Permissions, CPU allocation and the upgrade checklist.'),
        '/racknerd-black-friday/': ('LISTING CHECK', 'Campaign year, availability and price terms.'),
        '/vps-deals-shortlist/': ('SHORTLIST METHOD', 'Workload fit, exact-plan evidence and explicit unknowns.'),
    }
    links = dict(link for _, group in parser.groups for link in group)
    features = []
    for href, (label, description) in featured.items():
        if href not in links:
            continue
        rail = '<span class="reading-rail" aria-label="Shortlist sequence"><span>Workload</span><span>Evidence</span><span>Verdict</span></span>' if href == '/vps-deals-shortlist/' else ''
        features.append('<a class="reading-feature" href="'+escape(href, quote=True)+'"><span class="eyebrow">'+label+'</span><h3>'+escape(links[href])+'</h3><p>'+description+'</p>'+rail+'<span class="reading-action">Read the guide <span aria-hidden="true">↗</span></span></a>')
    cards = []
    for heading, group in parser.groups:
        group = [(href, title) for href, title in group if href not in featured]
        if not group:
            continue
        groups = [(re.split(r' (?:coupon|promo) code', title.split(':')[0])[0], [(href, title)]) for href, title in group] if heading == 'More stores' else [(heading, group)]
        for label, items in groups:
            label = label.replace(' buying guide', '').replace('Buying guides', 'Hostinger').replace('RackNerd buyer worksheet', 'RackNerd worksheet')
            body = ''.join('<a href="'+escape(href, quote=True)+'"><span>'+escape(title)+'</span><span aria-hidden="true">↗</span></a>' for href, title in items)
            cards.append('<article class="guide-group"><h3>'+escape(label)+'</h3>'+body+'</article>')
    return '<section class="reading-room" aria-labelledby="reading-title"><div class="reading-heading"><div><p class="eyebrow">THE PERKMINGLE LIBRARY</p><h2 id="reading-title">A little reading.<br><em>A clearer decision.</em></h2></div><p>Plan comparisons, buying guides and the terms worth checking before you choose.</p></div><div class="reading-features">'+''.join(features)+'</div><div class="guide-directory-heading" id="more-stores"><h3>Browse the guide library</h3><span>Find your provider. Read the details.</span></div><div class="guide-directory">'+''.join(cards)+'</div></section>'

def build():
    cfg = load_config()
    ga4_id = cfg.get('ga4_measurement_id', '')
    if not re.fullmatch(r'G-[A-Z0-9]+', ga4_id):
        raise ValueError('Invalid GA4 measurement ID')
    analytics_tag = (
        '<!-- Google tag (gtag.js) -->'
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga4_id}"></script>'
        '<script>window.dataLayer = window.dataLayer || [];'
        'function gtag(){dataLayer.push(arguments);}'
        "gtag('js', new Date());"
        f"gtag('config', '{ga4_id}');</script>"
    )
    def with_analytics(page):
        if analytics_tag in page:
            return page
        if 'googletagmanager.com/gtag/js?id=' in page:
            raise ValueError('Conflicting Google tag in preserved page')
        if '<head>' not in page:
            raise ValueError('Cannot add analytics to HTML without head')
        return page.replace('<head>', '<head>'+analytics_tag, 1)
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
                baseline_raw = raw.replace(analytics_tag.encode('utf-8'), b'', 1)
                if hashlib.sha256(baseline_raw).hexdigest()==item['sha256']:
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
    style_bytes = (ROOT/'assets/style.css').read_bytes()
    style_version = hashlib.sha256(style_bytes.replace(b'\r\n', b'\n')).hexdigest()[:12]
    style_asset = f'style.{style_version}.css'
    # Cloudflare may keep the stable asset URL cached across deployments. A
    # content-addressed filename guarantees that updated HTML fetches updated CSS.
    (dest/'assets'/style_asset).write_bytes(style_bytes)
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
        html = render('base.html', brand=escape(cfg['brand']),title=escape(title), description=escape(description), canonical=escape(canonical,quote=True), content=content, locale=escape(cfg['locale']), robots='noindex,follow' if noindex else 'index,follow', schema=json.dumps({'@context':'https://schema.org','@graph':list(schemas)},ensure_ascii=False).replace('<','\\u003c'), analytics_tag=analytics_tag)
        html = html.replace('/assets/style.css"',f'/assets/{style_asset}"')
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
        if path not in store_paths and path not in {'/hostinger-domain-coupon-code/', '/namecheap-renewal-promo-code/', '/godaddy-renewal-promo-code/', '/hostinger-coupon-code/', '/namecheap-promo-code/', '/godaddy-promo-code/', '/bluehost-promo-code/', '/hostgator-promo-code/', '/ovhcloud-promo-code/', '/digitalocean-promo-code/', '/ionos-promo-code/', '/contabo-promo-code/', '/liquid-web-promo-code/', '/vultr-promo-code/', '/racknerd-vps-plans/', '/racknerd-checkout-worksheet/', '/racknerd-black-friday/', '/hetzner-promo-code/', '/vps-deals-shortlist/'}:
            html = re.sub(r'<a\b[^>]*>', affiliate_exit, html)

        output = dest / ('index.html' if path=='/' else path.lstrip('/')+'index.html')
        output.parent.mkdir(parents=True,exist_ok=True)
        if path in preserved_pages:
            output.write_text(with_analytics(preserved_pages[path].decode('utf-8')),encoding='utf-8')
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
    guide_sections = ''
    if (ROOT/'data/vultr-guide.json').exists():
        guide_sections += '<section><h2>Vultr buying guide</h2><p><a href="/vultr-promo-code/">Vultr promo code: official redemption and terms</a></p></section>'
    if (ROOT/'data/hetzner-guide.json').exists():
        guide_sections += '<section><h2>Hetzner buying guide</h2><p><a href="/hetzner-promo-code/">Hetzner promo code and Cloud billing terms</a></p></section>'
    if (ROOT/'data/racknerd-guide.json').exists():
        guide_sections += '<section><h2>RackNerd buying guide</h2><p><a href="/racknerd-vps-plans/">RackNerd VPS plans and pricing terms</a></p></section>'
        guide_sections += '<section><h2>RackNerd buyer worksheet</h2><p><a href="/racknerd-checkout-worksheet/">Check product eligibility and checkout terms</a></p></section>'
    if (ROOT/'data/liquid-web-guide.json').exists():
        guide_sections += '<section><h2>Liquid Web buying guide</h2><p><a href="/liquid-web-promo-code/">Liquid Web promo code: official redemption and terms</a></p></section>'
    if (ROOT/'data/contabo-guide.json').exists():
        guide_sections += '<section><h2>Contabo buying guide</h2><p><a href="/contabo-promo-code/">Contabo promo code: verification status and refund terms</a></p></section>'
    if (ROOT/'data/ionos-guide.json').exists():
        guide_sections += '<section><h2>IONOS buying guide</h2><p><a href="/ionos-promo-code/">IONOS promo code: official VPS prices and terms</a></p></section>'
    if (ROOT/'data/digitalocean-guide.json').exists():
        guide_sections += '<section><h2>DigitalOcean buying guide</h2><p><a href="/digitalocean-promo-code/">DigitalOcean promo code: official verification and credit terms</a></p></section>'
    if (ROOT/'data/ovhcloud-guide.json').exists():
        guide_sections += '<section><h2>OVHcloud buying guide</h2><p><a href="/ovhcloud-promo-code/">OVHcloud promo code: official US offers and terms</a></p></section>'
    if 'hostinger' in providers:
        guide_sections += '<section><h2>Buying guides</h2><p><a href="/hostinger-coupon-code/">Hostinger coupon code: official evidence and VPS terms</a> · <a href="/hostinger-domain-coupon-code/">Hostinger domain coupon code: eligibility and terms</a></p></section>'
    if 'namecheap' in providers and (ROOT/'data/namecheap-guide.json').exists():
        guide_sections += '<section><h2>Namecheap buying guide</h2><p><a href="/namecheap-promo-code/">Namecheap promo code: official evidence and VPS terms</a> · <a href="/namecheap-renewal-promo-code/">Namecheap renewal promo code: community claims and verification</a></p></section>'
    store_guides = json.loads((ROOT/'data/store-guides.json').read_text(encoding='utf-8')) if (ROOT/'data/store-guides.json').exists() else []
    store_paths = {'/'+guide['slug']+'/' for guide in store_guides}
    domain_faq = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':'Is COUPONSPAGE a verified domain coupon?','acceptedAnswer':{'@type':'Answer','text':'No. We observed it on hosting cards, not as proof of standalone domain eligibility.'}},{'@type':'Question','name':'Is the included domain free forever?','acceptedAnswer':{'@type':'Answer','text':'No. The included registration is for one year; standard renewal pricing follows.'}}]}
    write('/hostinger-domain-coupon-code/', 'Hostinger domain coupon code: eligibility and terms | '+cfg['brand'], 'Check whether a standalone Hostinger domain code is verified, with official free-domain conditions, renewal limits and refund sources.', render('hostinger-domain-guide.html', checked='2026-09-28'), [domain_faq], '2026-09-28', keep_metadata=True)
    namecheap_renewal_faq = {'@type':'FAQPage','mainEntity':[
        {'@type':'Question','name':'Does absence from the official coupon page mean COUPONFCNC does not exist?','acceptedAnswer':{'@type':'Answer','text':'No. It establishes only that we did not find it on the reviewed page, not that it is unavailable everywhere.'}},
        {'@type':'Question','name':'Is there a verified Namecheap promo code for renewal on this page?','acceptedAnswer':{'@type':'Answer','text':'No. COUPONFCNC is included only as a reader-supplied community report; we have no current renewal-cart result.'}}
    ]}
    write('/namecheap-renewal-promo-code/', 'Namecheap renewal promo code: is COUPONFCNC verified? | '+cfg['brand'], 'Separate community COUPONFCNC reports from official renewal evidence, understand cart claims, and check unexpected renewal notices safely.', render('namecheap-renewal-guide.html', checked='2026-09-27'), [namecheap_renewal_faq], '2026-09-27', keep_metadata=True)
    if (ROOT/'data/godaddy-guide.json').exists():
        guide_sections += '<section><h2>GoDaddy buying guide</h2><p><a href="/godaddy-promo-code/">GoDaddy promo code: official evidence and VPS terms</a> · <a href="/godaddy-renewal-promo-code/">GoDaddy renewal promo code: eligibility and cost worksheet</a></p></section>'
    if (ROOT/'data/bluehost-guide.json').exists():
        guide_sections += '<section><h2>Bluehost buying guide</h2><p><a href="/bluehost-promo-code/">Bluehost promo code: official evidence and VPS terms</a></p></section>'
    if (ROOT/'data/hostgator-guide.json').exists():
        guide_sections += '<section><h2>HostGator buying guide</h2><p><a href="/hostgator-promo-code/">HostGator promo code: official evidence and VPS terms</a></p></section>'
    if store_guides:
        guide_sections += '<section id="more-stores"><h2>More stores</h2><ul>'+''.join('<li><a href="/'+escape(g['slug'],quote=True)+'/">'+escape(g['title'])+'</a></li>' for g in store_guides)+'</ul></section>'
    for guide in store_guides:
        guide_rows = ''
        for row in guide['rows']:
            quote = '<br><q>'+escape(row['quote'])+'</q>' if row.get('quote') else ''
            guide_rows += '<tr><td>'+escape(row['offer'])+quote+'</td><td>'+escape(row['conditions'])+'</td><td><a href="'+escape(safe_url(row['source']),quote=True)+'" rel="noopener">Official source</a></td><td>'+escape(guide['checked'])+'</td></tr>'
        faq_html = ''.join('<h3>'+escape(f['question'])+'</h3><p>'+escape(f['answer'])+' <a href="'+escape(safe_url(f['source']),quote=True)+'">Official source</a> · Reviewed '+escape(guide['checked'])+'.</p>' for f in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':f['question'],'acceptedAnswer':{'@type':'Answer','text':f['answer']}} for f in guide['faq']]}
        lead = escape(guide['lead'])+' <a href="'+escape(safe_url(guide['rows'][0]['source']),quote=True)+'">Official evidence</a>'
        variant = '<p>'+escape(guide['variant'])+'</p>' if guide['variant'] else ''
        content = render('store-guide.html',heading=escape(guide['title']),lead=lead,checked=escape(guide['checked']),variant=variant,rows=guide_rows,faq=faq_html,advice=escape(guide['advice']))
        write('/'+guide['slug']+'/',guide['title']+' | '+cfg['brand'],guide['lead'],content,[faq_schema],guide['checked'],keep_metadata=True)
    hosting_faq = {'@type':'FAQPage','mainEntity':[
        {'@type':'Question','name':'Does VPS always mean root access?','acceptedAnswer':{'@type':'Answer','text':"No. DreamHost's Managed VPS is a documented counterexample. Check the particular product instead of generalizing from the label."}},
        {'@type':'Question','name':'Does VPS always mean dedicated CPU?','acceptedAnswer':{'@type':'Answer','text':'No. DigitalOcean documents shared-CPU and dedicated-CPU Droplets. Check the allocation model of the selected plan.'}},
        {'@type':'Question','name':'What traffic number means I must upgrade?','acceptedAnswer':{'@type':'Answer','text':'This page does not set one. Our worksheet asks you to identify a specific limitation and an acceptance check; it does not turn visitor count into a universal hosting requirement.'}}
    ]}
    write('/vps-vs-shared-hosting/', 'VPS vs shared hosting: check what an upgrade actually changes | '+cfg['brand'], 'Compare shared hosting and VPS using documented permissions, CPU allocation and a requirement-by-requirement upgrade worksheet.', render('vps-vs-shared-hosting.html'), [hosting_faq], '2026-09-29', keep_metadata=True)
    guide_sections += '<section><h2>Hosting decisions</h2><p><a href="/vps-vs-shared-hosting/">VPS vs shared hosting: check what an upgrade actually changes</a></p></section>'
    write('/vps-price/', 'VPS Price: Calculate the First Usable Cycle, Not the Smallest Number | '+cfg['brand'], 'Calculate a VPS first usable-cycle cost from the invoice, required extras, migration overlap, residual resources and recovery work.', render('vps-price.html'), [], '2026-09-29', keep_metadata=True)
    shortlist_faq = {'@type':'FAQPage','mainEntity':[
        {'@type':'Question','name':'Should I choose the lowest displayed monthly price?','acceptedAnswer':{'@type':'Answer','text':'Not before the candidate passes the hard requirements. Record the actual plan, billing term, amount due, required extras and renewal terms first.'}},
        {'@type':'Question','name':'Does a VPS label tell me whether CPU time is dedicated?','acceptedAnswer':{'@type':'Answer','text':'No universal conclusion follows from the VPS label. Check the allocation model documented for the exact product.'}},
        {'@type':'Question','name':'If the documentation does not mention a requirement, should I assume it passes?','acceptedAnswer':{'@type':'Answer','text':'No. Keep the row Unconfirmed and ask the provider about the exact product.'}},
        {'@type':'Question','name':'Does stopping a Vultr server stop its charges?','acceptedAnswer':{'@type':'Answer','text':'Vultr says stopped servers continue to incur hourly charges until they are destroyed. Check another provider’s own billing terms separately.'}},
        {'@type':'Question','name':'Does a 200 OK response prove that a VPS plan is in stock?','acceptedAnswer':{'@type':'Answer','text':'No. RFC 9110 says 200 OK means the request succeeded; for GET, the response represents the requested resource. A successful homepage response does not establish a separate plan’s current inventory or orderability. Check the exact provider product and order flow.'}}
    ]}
    write('/vps-deals-shortlist/', 'VPS Deals: Turn a Plan List into a Workload Shortlist | '+cfg['brand'], 'Screen VPS deals against workload requirements, official plan evidence, billing behavior and explicit unknowns before comparing price.', render('vps-deals-shortlist.html'), [shortlist_faq,crumbs('VPS deals shortlist','/vps-deals-shortlist/')], '2026-10-02', keep_metadata=True)
    guide_sections += '<section><h2>VPS comparison method</h2><p><a href="/vps-deals-shortlist/">Turn a VPS plan list into a workload shortlist</a></p></section>'
    black_friday_faq = {'@type':'FAQPage','mainEntity':[
        {'@type':'Question','name':'Is a 2026 heading enough to prove the 2026 VPS Black Friday campaign is live?','acceptedAnswer':{'@type':'Answer','text':'No. The reviewed Hostinger page had a 2026 heading but retained 2025 availability dates in its FAQ, so the 2026 campaign window remained unconfirmed.'}},
        {'@type':'Question','name':'Is a separate Hostinger coupon code required on the reviewed page?','acceptedAnswer':{'@type':'Answer','text':'The official FAQ says the reduction is automatically included and no additional coupon code is needed.'}},
        {'@type':'Question','name':'Does the displayed monthly figure establish cash due today?','acceptedAnswer':{'@type':'Answer','text':'No. The official page says plans are paid upfront and the monthly rate is the term total divided by its number of months.'}}
    ]}
    write('/vps-black-friday/', 'VPS Black Friday: verify the campaign year before buying | '+cfg['brand'], 'Check a VPS Black Friday page by separating its campaign year, availability window, checkout state and renewal evidence.', render('vps-black-friday.html'), [black_friday_faq], '2026-09-30', keep_metadata=True)
    guide_sections += '<section><h2>Seasonal VPS verification</h2><p><a href="/vps-black-friday/">VPS Black Friday: verify the campaign year before buying</a></p></section>'
    racknerd_season_faq = {'@type':'FAQPage','mainEntity':[
        {'@type':'Question','name':'Is there a verified RackNerd Black Friday VPS code?','acceptedAnswer':{'@type':'Answer','text':'No VPS code was verified on the official Black Friday 2025 listing reviewed on 2026-09-30. This does not establish that no code exists elsewhere.'}},
        {'@type':'Question','name':'Are these Black Friday 2026 prices?','acceptedAnswer':{'@type':'Answer','text':'No. The reviewed page names Black Friday 2025. A 2026 campaign remains Unconfirmed.'}},
        {'@type':'Question','name':'Can I buy one of the five listed VPS plans now?','acceptedAnswer':{'@type':'Answer','text':'All five cards showed 0 Available on 2026-09-30. Checkout and fulfillment were not tested.'}}
    ]}
    write('/racknerd-black-friday/', 'RackNerd Black Friday: listed plans and availability | '+cfg['brand'], 'Review the official RackNerd seasonal listing, its 2025 heading, VPS stock, annual billing and dedicated-server code scope.', render('racknerd-black-friday.html'), [racknerd_season_faq], '2026-09-30', keep_metadata=True)
    guide_sections += '<section><h2>RackNerd seasonal listing</h2><p><a href="/racknerd-black-friday/">RackNerd Black Friday: listed plans and availability</a></p></section>'
    home += guide_library(guide_sections)
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
    renewal_faq = {'@type':'FAQPage','mainEntity':[
        {'@type':'Question','name':'Does no public code mean no renewal offers exist?','acceptedAnswer':{'@type':'Answer','text':'No. The official explanation describes occasional customer-specific offers.'}},
        {'@type':'Question','name':'Can I assume a first-order code works on a renewal?','acceptedAnswer':{'@type':'Answer','text':'No. The general offer policy requires the email offer to specifically include renewals.'}}
    ]}
    write('/godaddy-renewal-promo-code/', 'GoDaddy renewal promo code: eligibility and cost checks | '+cfg['brand'], 'No public renewal code verified. Check official account eligibility and compare matching renewal totals with a practical worksheet.', render('godaddy-renewal-guide.html', checked='2026-09-27'), [renewal_faq], '2026-09-27', keep_metadata=True)
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
    if (ROOT/'data/ovhcloud-guide.json').exists():
        guide = json.loads((ROOT/'data/ovhcloud-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/ovhcloud-promo-code/','OVHcloud promo code: official US offers and terms | '+cfg['brand'],'Check official OVHcloud US credits, eligibility, commitment pricing and refund terms with dated sources.',render('ovhcloud-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/digitalocean-guide.json').exists():
        guide = json.loads((ROOT/'data/digitalocean-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/digitalocean-promo-code/','DigitalOcean promo code: official verification and credit terms | '+cfg['brand'],'Check whether a DigitalOcean promo code was verified, with official credit conditions, refund rules and dated sources.',render('digitalocean-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/ionos-guide.json').exists():
        guide = json.loads((ROOT/'data/ionos-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/ionos-promo-code/','IONOS promo code: official verification and VPS terms | '+cfg['brand'],'Check whether a IONOS promo code was verified, with official VPS conditions, refund rules and dated sources.',render('ionos-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/contabo-guide.json').exists():
        guide = json.loads((ROOT/'data/contabo-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/contabo-promo-code/','Contabo promo code: official verification and VPS terms | '+cfg['brand'],'Check whether a Contabo promo code was verified, with official VPS conditions, refund rules and dated sources.',render('contabo-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/liquid-web-guide.json').exists():
        guide = json.loads((ROOT/'data/liquid-web-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/liquid-web-promo-code/','Liquid Web promo code: official verification and VPS terms | '+cfg['brand'],'Check whether a Liquid Web promo code was verified, with official VPS conditions, refund rules and dated sources.',render('liquid-web-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/vultr-guide.json').exists():
        guide = json.loads((ROOT/'data/vultr-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/vultr-promo-code/','Vultr promo code: official verification and VPS terms | '+cfg['brand'],'Check whether a Vultr promo code was verified, with official VPS conditions, refund rules and dated sources.',render('vultr-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/hetzner-guide.json').exists():
        guide = json.loads((ROOT/'data/hetzner-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/hetzner-promo-code/','Hetzner promo code: official status and Cloud billing terms | '+cfg['brand'],'Check whether a Hetzner promo code was verified, with official referral status, billing conditions, cancellation terms and dated sources.',render('hetzner-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
    if (ROOT/'data/racknerd-guide.json').exists():
        guide = json.loads((ROOT/'data/racknerd-guide.json').read_text(encoding='utf-8'))
        guide_rows = ''.join('<tr><td>'+escape(row['offer'])+'</td><td>'+escape(row['conditions'])+'</td><td><a rel="noopener" href="'+escape(row['source'],quote=True)+'">'+escape(row['label'])+'</a></td><td>'+escape(guide['checked'])+'</td></tr>' for row in guide['facts'])
        faq_html = ''.join('<h3>'+escape(q['question'])+'</h3><p>'+escape(q['answer'])+' <a href="'+escape(q['source'],quote=True)+'" rel="noopener">Official source</a> · Checked '+escape(guide['checked'])+'</p>' for q in guide['faq'])
        faq_schema = {'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in guide['faq']]}
        write('/racknerd-vps-plans/','RackNerd VPS plans and pricing terms | '+cfg['brand'],'Review RackNerd VPS annual prices and dedicated-server terms, with official sources, review dates and refund guidance.',render('racknerd-guide.html',rows=guide_rows,faq=faq_html,checked=guide['checked']),[faq_schema],guide['checked'],keep_metadata=True)
        worksheet_faq = {'@type':'FAQPage','mainEntity':[
            {'@type':'Question','name':'Does the public code apply to the annual VPS specials?','acceptedAnswer':{'@type':'Answer','text':'The official banner describes 15OFFDEDI for dedicated servers. The VPS list does not state that it applies to the annual specials.'}},
            {'@type':'Question','name':'Does a visible code box mean my VPS qualifies?','acceptedAnswer':{'@type':'Answer','text':'No eligibility claim follows from the box alone. Check the actual response and final total for the product you selected.'}},
            {'@type':'Question','name':'Can I get a refund if the plan is unsuitable?','acceptedAnswer':{'@type':'Answer','text':'RackNerd says it does not offer refunds or a money-back guarantee.'}},
        ]}
        write('/racknerd-checkout-worksheet/','RackNerd VPS checkout worksheet | '+cfg['brand'],'Check RackNerd VPS product eligibility, billing cycle, final total and refund terms against official sources before paying.',render('racknerd-checkout-worksheet.html'),[worksheet_faq],'2026-09-27',keep_metadata=True)
    # Keep established URLs when verification fails; never count history as fresh.
    known = {o['id']:o for o in data.get('historical_offers',[]) + data['offers'] if o['provider_id'] in providers}
    archived = [o for oid,o in known.items() if oid not in {x['id'] for x in offers}]
    for pid in {o['provider_id'] for o in archived}:
        p = providers[pid]
        items = [o for o in archived if o['provider_id']==pid]
        if not any(o['provider_id']==pid for o in offers):
            content = '<article class="prose"><h1>'+escape(p['name'])+' VPS plans and terms</h1><p>Current availability could not be verified. Historical records remain available below; they are not current verified offers.</p>'+''.join('<p><a href="'+detail_path(o)+'">'+escape(o['title'])+'</a></p>' for o in items)+'<p><a href="'+escape(p['source'],quote=True)+'">Official source</a></p></article>'
            write('/providers/'+pid+'/',p['name']+' VPS plans and terms','Historical source records and current verification limits.',content)
    for o in archived:
        content = '<article class="prose"><h1>'+escape(providers[o['provider_id']]['name']+': '+o['title'])+'</h1><p>Current availability could not be verified. This historical record is not a current verified offer.</p><p>Last successful source check: '+escape(o['fetched_at'])+'</p><p>Previously recorded: '+escape(o['evidence'])+'</p><p><a href="'+escape(o['source_url'],quote=True)+'">Official source</a></p><p><a href="/providers/'+o['provider_id']+'/">Provider details</a></p></article>'
        write(detail_path(o),providers[o['provider_id']]['name']+': '+o['title'],'Historical source record; current availability unverified.',content,lastmod=o['fetched_at'])
    build_localized_pages(cfg, base, dest, pages, style_asset, analytics_tag)
    sitemap = Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url,modified in pages:
        el = SubElement(sitemap,'url')
        SubElement(el,'loc').text = url
        if modified:
            SubElement(el,'lastmod').text = modified
    ElementTree(sitemap).write(dest/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    (dest/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n',encoding='utf-8')
    # Retired empty provider pages lead to the current source table, not cached shells.
    retired = [p for p in cfg['providers'] if not any(o['provider_id']==p['id'] for o in known.values())]
    (dest/'_redirects').write_text('/racknerd-promo-code/ /racknerd-vps-plans/ 301\n/racknerd-promo-code /racknerd-vps-plans/ 301\n/deals/:id/ /plans/:id/ 301\n/deals/:id /plans/:id/ 301\n'+''.join(f'/providers/{p["id"]}/ / 302\n/providers/{p["id"]} / 302\n' for p in retired),encoding='utf-8')
    not_found = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Plan unavailable</title><meta name="description" content="This plan is no longer listed or could not be verified."></head><body><h1>This offer is no longer listed</h1><p>It may have expired or could not be verified.</p><a href="/">See current offers</a></body></html>'
    (dest/'404.html').write_text(origin_links(with_analytics(not_found)),encoding='utf-8')
    (dest/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Cache-Control: public, max-age=300\n',encoding='utf-8')
    print(f'Built {len(pages)} indexable pages; {len(offers)} fresh offers; {len(providers)} configured providers')

if __name__ == '__main__':
    build()
