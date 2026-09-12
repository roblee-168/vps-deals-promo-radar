# ::ILANG
# ::STATE{@SELF, role:让工作流明确报告抓取退化}
# ::BOUNDARY{never:把全部失败显示为健康}
import json
from config import ROOT

if __name__ == '__main__':
    data = json.loads((ROOT/'data/offers.json').read_text(encoding='utf-8'))
    errors = [s for s in data['sources'] if s['status'] != 'ok']
    for s in errors:
        print('::warning::'+s['provider_id']+': '+s.get('error',s['status']))
    if not data['offers']:
        raise SystemExit('All sources empty: inspect the source report; honest empty site has been built')
