# ::ILANG
# ::STATE{@SELF, role:核对文章增量计数与生成产物}
# ::BOUNDARY{never:把未读页面算成没有}
from pathlib import Path
from html.parser import HTMLParser
import re
import json

class TextCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.exclusive = False
        self.active = 0
        self.total = 0
        self.unique = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'section':
            self.exclusive = dict(attrs).get('data-exclusive') == 'true'
        if tag in ('p', 'li'):
            self.active += 1
    def handle_endtag(self, tag):
        if tag == 'section':
            self.exclusive = False
        if tag in ('p', 'li'):
            self.active -= 1
    def handle_data(self, text):
        if self.active:
            length = len(re.sub(r'\s+', '', text))
            self.total += length
            if self.exclusive:
                self.unique += length

root = Path(__file__).resolve().parents[1]
parser = TextCounter()
parser.feed((root/'templates/ja-wordpress.html').read_text(encoding='utf-8'))
html = (root/'site/ja/wordpress/index.html').read_text(encoding='utf-8')
assert html.count('rel="canonical"') == 1
assert 'href="https://perkmingle.com/ja/wordpress/"' in html
for fragment in ('id="prices"', 'id="worksheet"', 'id="calculation"', 'id="steps"', '/assets/wordpress-cost-table.html'):
    assert fragment in html
assert parser.unique / parser.total >= .3
result = {'checked_inputs':'2026-10-10','published':'2026-10-11','exclusive_candidate_characters':parser.unique,'body_characters':parser.total,'ratio':parser.unique/parser.total,'scope':'Read SERP bodies only; ranks 1,4,8 remain unverified. No all-web uniqueness claim.'}
(root/'docs/wordpress-count.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
