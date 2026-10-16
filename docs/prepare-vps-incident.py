# ::ILANG
# ::STATE{@SELF, role:prepare original notice matching worksheet and diagrams}
# ::BOUNDARY{never:invent an incident or assert user impact}
from pathlib import Path
from html import escape
from PIL import Image,ImageDraw,ImageFont
root=Path.cwd();media=root/'work-vps-incident-media';media.mkdir(exist_ok=True)
code=Path('docs/prepare-vps-backup.py').read_text(encoding='utf-8-sig');exec(code[code.index('font='):code.index("graphic('vps-backup-evidence'")])
graphic('vps-incident-label','ラベルと予定一覧を分ける',[('障害なしの表示条件','直近12時間以内の予定も見る'),('将来の予定は別欄','一覧から詳細を開く'),('本人への影響は別','対象サービスと接続を照合')],'help.sakura.ad.jp/status/｜確認 2026-10-16')
graphic('vps-incident-match','タイトルだけで原因を決めない',[('公式通知','対象・時間・影響・更新内容'),('本人の現象','対象・経路・時点を記録'),('照合の結果','一致・不一致・未確認＋理由')],'編集上の照合方法｜サーバー操作なし')
graphic('vps-incident-cost','年額と月額換算を区別',[('石狩・メモリ1GB','年額9,680円（税込）'),('年額を12ヶ月で割る','9,680 ÷ 12 ≈ 806.67円'),('公式表示は807円／月','月額払い・補償額とは別')],'vps.sakura.ad.jp/｜確認 2026-10-16')
graphic('vps-incident-monitor-review','観測と公式通知を分ける',[('本人の観測','入口・時点・実際の応答'),('公式の通知','影響範囲・作業時間'),('根拠のない原因は保留','近い時間だけでは一致にしない')],'編集上の記録方法｜2026-10-16')
rows=[('ステータス表示','障害未発生・直近12時間以内に予定なし','https://help.sakura.ad.jp/status/'),('通知の作業日程','2026年10月27日19時00分 - 2026年10月27日24時00分。延長の可能性あり','https://support.sakura.ad.jp/mainte/mainteentry.php?id=39689'),('通知の対象例','専用サーバPHY/高火力PHYと接続するサービス間接続の中に、さくらのVPSハイブリッド接続を列挙','https://support.sakura.ad.jp/mainte/mainteentry.php?id=39689'),('本人の照合','実際の契約・接続・現象は未確認。本人が記録する編集欄','https://support.sakura.ad.jp/mainte/mainteentry.php?id=39689')]
heads=['照合項目','公式記載／編集欄','公式出典','公式確認日','本人の対象・接続','本人の現象と時点・時間帯','一致／不一致／未確認','根拠と次に確認すること']
s='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPSの公式通知と本人の現象・保存用照合表</title><style>body{font:16px/1.7 sans-serif;margin:20px;color:#17483d}main{max-width:100%;overflow-x:auto}table{border-collapse:collapse}th,td{border:1px solid #abb;padding:14px;min-width:160px}td[contenteditable]{background:#fff9df}</style><h1>VPSの公式通知と本人の現象・保存用照合表</h1><p>独立ファイルとして保存できます。通知は確認日の公開記録です。本人の契約や障害原因は未確認。秘密情報は記入しないでください。</p><a href="/ja/vps-incident/">記事へ戻る</a><main><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in heads)+'</tr></thead><tbody>'
for a,b,u in rows:s+='<tr><td>'+a+'</td><td>'+b+'</td><td><a href="'+u+'">公式</a></td><td>2026-10-16</td>'+('<td contenteditable="true" aria-label="本人の照合欄"></td>'*4)+'</tr>'
s+='</tbody></table></main><p>通知の確認日と、本人の現象発生時点は別欄です。空欄を原因確定へ読み替えません。</p></html>'
(root/'assets/vps-incident-checklist.html').write_text(s,encoding='utf-8')
