# ::ILANG
# ::STATE{@SELF, role:读取并验证唯一I-Lang配置}
# ::BOUNDARY{never:执行配置内代码 静默替换厂商}
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent

def slug(value):
    result = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    if not result:
        raise ValueError('Provider requires an ASCII slug-compatible name')
    return result

def safe_url(value):
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password:
        raise ValueError('Only public HTTPS URLs without credentials are allowed')
    return value

def load_config(path=None):
    text = Path(path or ROOT / '.ilang/site.ilang').read_text(encoding='utf-8-sig')
    if text.splitlines()[0] != '::ILANG':
        raise ValueError('Missing ::ILANG header')
    state = re.search(r'::STATE\{@SITE,\s*(.*?)\}', text)
    if not state:
        raise ValueError('Missing SITE state')
    cfg = dict(part.strip().split(':', 1) for part in state[1].split(','))
    cfg = {k: v.strip() for k, v in cfg.items()}
    cfg['providers'] = []
    section = ''
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('::MODULE{'):
            section = line.split('{', 1)[1].split('|', 1)[0].split('}', 1)[0]
        elif line.startswith('::'):
            section = ''
        elif section == 'PROVIDERS' and line:
            name, home, source, affiliate = [x.strip() for x in line.split('|')]
            cfg['providers'].append(dict(id=slug(name), name=name, home=safe_url(home), source=safe_url(source), affiliate=safe_url(affiliate) if affiliate else ''))
        elif section == 'FIELDS' and line:
            cfg['fields'] = line.split()
        elif section == 'RUNTIME' and ':' in line:
            key, value = line.split(':', 1)
            cfg[key.strip()] = value.strip()
    safe_url(cfg['domain'])
    if cfg['locale'] != 'en-US':
        raise ValueError('v1 implements en-US only; add localized sources and templates before another locale')
    ids = [p['id'] for p in cfg['providers']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate provider slug')
    for key in ('update_hours','max_age_hours','timeout_seconds','max_bytes','max_pages_per_provider'):
        cfg[key] = int(cfg[key])
        if cfg[key] <= 0:
            raise ValueError(key)
    re.compile(cfg['promotion_pattern'])
    if cfg['cron'] != f"17 */{cfg['update_hours']} * * *":
        raise ValueError('cron and update_hours disagree')
    return cfg
