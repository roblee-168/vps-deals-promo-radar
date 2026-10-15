# ::ILANG
# ::STATE{@SELF, role:assemble rule inventory and original page-based media}
# ::BOUNDARY{never:apply firewall rules or infer required ports}
from pathlib import Path
from html import escape
from PIL import Image,ImageDraw,ImageFont
import json
root=Path.cwd();media=root/'work-vps-port-media';media.mkdir(exist_ok=True)
code=Path('docs/prepare-vps-backup.py').read_text(encoding='utf-8-sig')
exec(code[code.index('font='):code.index("graphic('vps-backup-evidence'")])
graphic('vps-port-purpose','ルールから用途へ戻る',[('何の通信か','サービスと利用者を先に記録'),('どこまで許可するか','方向・種類・範囲を照合'),('どこへ適用したか','対象サーバーを別に確認')],'公式設定項目＋編集上の棚卸し方法｜2026-10-15')
graphic('vps-port-decisions','用途不明を全許可にしない',[('用途が確認できる','必要な範囲の根拠を残す'),('用途や対象が不明','所有者と次の確認先を記録'),('削除したくなったら','依存関係と戻し方を先に確認')],'編集上の判断例｜実設定の変更なし｜2026-10-15')
graphic('vps-port-cost','調査時間は仮定で積算',[('公式の基本料金','メモリ1GB：税込1.9円／時'),('本稿の仮定：2時間','1.9 × 2 ＝ 3.8円'),('ルールの追加料金ではない','本体単価だけの参考計算')],'vps.conoha.jp/pricing/｜入力確認 2026-10-15')
graphic('vps-port-ip-stage','割当と利用を分ける',[('対象への割当','IPのリスト表示とは別'),('NICとOSの設定','本人の環境との適合を確認'),('使うサービスの結果','別IPの成功から推定しない')],'追加IP記事にある確認方法｜2026-10-15')
rows=[('用途と担当','本人が必要なサービス・担当・根拠を記入する（編集欄）'),('方向とIP種類','IN/OUTとIPv4/IPv6を区別する'),('プロトコルとポート','画面の選択とサービスの要件を照合する'),('IP/CIDR','接続元・接続先の適用範囲を照合する'),('グループの適用先','対象サーバーのネットワーク情報で確認する'),('OS内と再確認','別のファイアウォールの条件、確認者・次回確認の根拠を記入する')]
s='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPS許可ルールの保存用棚卸し表</title><style>body{font:16px/1.7 sans-serif;margin:20px;color:#17483d}main{max-width:100%;overflow-x:auto}table{border-collapse:collapse}th,td{border:1px solid #abb;padding:14px;min-width:160px}td[contenteditable]{background:#fff9df}</style><h1>VPS許可ルールの保存用棚卸し表</h1><p>独立ファイルとして保存できます。本人のルールやIP、用途、担当、判断は空欄です。編集上の照合記録であり、適切な設定を自動判定する表ではありません。認証情報や秘密鍵は記入しないでください。</p><a href="/ja/vps-port-rules/">許可ルールの確認へ</a><main><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['確認項目','照合方法','公式参照','確認日','本人の用途・担当','現行値・対象','根拠・依存先','判断・次の確認'])+'</tr></thead><tbody>'
for a,b in rows:s+='<tr><td>'+a+'</td><td>'+b+'</td><td><a href="https://support.conoha.jp/v/v3-security-securitygroup/">公式設定項目</a></td><td>2026-10-15</td>'+('<td contenteditable="true" aria-label="本人の未確認欄"></td>'*4)+'</tr>'
s+='</tbody></table></main><p>用途不明は不要の証明ではありません。変更や削除の実施は、この表で依存関係と本人の判断を確認してから別の作業として扱います。</p></html>'
Path('assets/vps-port-inventory.html').write_text(s,encoding='utf-8')
p=Path('build.py');s=p.read_text(encoding='utf-8');needle="    english_home = dest/'index.html'";assert s.count(needle)==1
new="    port_content = (ROOT/'templates/ja-vps-port-rules.html').read_text(encoding='utf-8')\n    render('/ja/vps-port-rules/', 'VPSの許可ルールを棚卸しする：用途と適用先の確認表 | PerkMingle',\n           '許可ルールの用途、方向、IP種類、範囲と対象サーバーを照合。保存用の棚卸し表と、用途不明を全許可や即削除にしない判断順序を掲載します。',\n           port_content, [{'@type':'Article','headline':'VPSの許可ルールを棚卸しする：用途と適用先の確認表','inLanguage':'ja-JP','datePublished':'2026-10-15','citation':['https://support.conoha.jp/v/v3-security-securitygroup/','https://support.conoha.jp/v/port/','https://vps.conoha.jp/pricing/']}],\n           [{'lang':'ja-JP','path':'/ja/vps-port-rules/'}])\n    pages[-1] = (base+'/ja/vps-port-rules/', '2026-10-15')\n\n"
s=s.replace(needle,new+needle)
needle='VPS：追加IPの料金と割当後の確認 →</a></p></div>';assert s.count(needle)==1
s=s.replace(needle,'VPS：追加IPの料金と割当後の確認 →</a></p><p style="margin:0;padding:1.25rem;border:1px solid #cddcd7;border-radius:1rem;background:#f5f8f6"><a class="ja-card-link" href="/ja/vps-port-rules/">VPS：許可ルールの用途と適用先を棚卸し →</a></p></div>');p.write_text(s,encoding='utf-8')
p=Path('templates/ja-vps-additional-ip.html');s=p.read_text(encoding='utf-8');needle='<p class="ja-back">';assert s.count(needle)==1
s=s.replace(needle,'<figure class="ja-section"><img src="/assets/vps-port-ip-stage.svg" alt="追加IPの割当、NICとOS、サービスの結果を分ける図" loading="lazy" style="width:100%;height:auto"><figcaption>割当から利用まで、段階ごとの根拠を分けて残します。</figcaption></figure>'+needle);p.write_text(s,encoding='utf-8')
(media/'narration.txt').write_text('A rule inventory asks why a permission exists and where it applies. It is different from diagnosing an SSH login failure. The ConoHa security group guide separates traffic direction, IP type, protocol, port, and address range. It also separates creating rules from applying a group to a server. Operating system firewall settings are a separate layer. Our saveable inventory connects each current value with a service purpose, a responsible person, an applied target, and the evidence still needed. An unknown purpose does not prove that a rule is unnecessary. Do not solve that uncertainty by allowing everything or deleting the rule immediately. Record dependencies and a way to restore the previous state before a separately approved change. If the application requirements are not known, leave the required port and scope unconfirmed. The article does not supply a universal port list or execute any firewall changes. Its cost example is only an assumed period at a published VPS base rate, not a rule creation fee.',encoding='utf-8')
video=Path('work-vps-ip-media/video.py').read_text(encoding='utf-8-sig').replace("['vps-ip-states','vps-ip-boundary','vps-ip-cost']","['vps-port-purpose','vps-port-decisions','vps-port-cost']").replace('vps-ip-cost.png','vps-port-cost.png').replace('PerkMingle-VPS-additional-IP.mp4','PerkMingle-VPS-port-rules.mp4');(media/'video.py').write_text(video,encoding='utf-8')
