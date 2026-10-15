# ::ILANG
# ::STATE{@SELF, role:prepare sourced monitoring guide and original comparison assets}
# ::BOUNDARY{never:invent observations or operate user servers}
from pathlib import Path
from html import escape
import json,re
from PIL import Image,ImageDraw,ImageFont
root=Path.cwd(); media=root/'work-vps-monitor-media';media.mkdir(exist_ok=True)
code=Path('docs/prepare-vps-backup.py').read_text(encoding='utf-8-sig')
exec(code[code.index('font='):code.index("graphic('vps-backup-evidence'")])
graphic('vps-monitor-scope','表示と機能応答を分ける',[('管理画面','対象と表示内容を記録'),('利用する機能','入口・期待・実際の応答'),('未確認の範囲','観測していない時間は別')],'編集上の観測設計｜公式確認 2026-10-15')
graphic('vps-monitor-record','観測の空白を埋めない',[('観測する前','対象・経路・期待を固定'),('観測した時点','表示と機能応答を別欄へ'),('未実施なら未確認','成功率や稼働率に変えない')],'編集上の記録方法｜サーバー操作なし')
graphic('vps-monitor-cost','観測時間と本体単価',[('現行メモリ1GB','税込 1.9円／時'),('仮定：12時間','1.9 × 12 ＝ 22.8円'),('監視料金ではない','本体単価の参考積算のみ')],'vps.conoha.jp/pricing/｜確認 2026-10-15')
graphic('vps-monitor-version-review','表示の確認にも対象がある',[('画面の種類','VPSとWINGを区別'),('本人の対象','契約と表示先を照合'),('別の確認','利用する機能の応答')],'support.conoha.jp/v/dashboard/｜2026-10-15')
rows=[('管理画面','サーバー状況・支払金額・ConoHaチャージ残額の一覧','https://support.conoha.jp/v/dashboard/'),('サービス表示','上部のVPS・WINGで表示を切替','https://support.conoha.jp/v/dashboard/'),('利用機能','本人の入口と期待する応答を先に記入（編集欄）','https://support.conoha.jp/v/dashboard/'),('観測の空白','未実施や結果不明は未確認のまま記録（編集欄）','https://support.conoha.jp/v/dashboard/')]
heads=['比較対象','公式説明／編集欄の区別','公式参照','公式説明の確認日','本人の観測日時・時間帯','確認する入口・経路','期待する応答','実際の表示・応答','未確認の理由・次の担当']
s='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPSの表示と機能応答・保存用観測比較表</title><style>body{font:16px/1.7 sans-serif;margin:20px;color:#17483d}main{max-width:100%;overflow-x:auto}table{border-collapse:collapse}th,td{border:1px solid #abb;padding:14px;min-width:160px}td[contenteditable]{background:#fff9df}</style><h1>VPSの表示と機能応答・保存用観測比較表</h1><p>独立ファイルとして保存できます。本人の観測結果は空欄です。未記入を成功・障害・稼働率のどれにも読み替えません。秘密情報や個人情報を入力しないでください。</p><a href="/ja/vps-monitor/">記事へ戻る</a><main><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in heads)+'</tr></thead><tbody>'
for a,b,u in rows:s+='<tr><td>'+a+'</td><td>'+b+'</td><td><a href="'+u+'">公式</a></td><td>2026-10-15</td>'+('<td contenteditable="true" aria-label="本人の観測欄"></td>'*5)+'</tr>'
s+='</tbody></table></main><p>公式を読んだ日と、本人が対象を観測した日時は別です。この表は監視ソフトではなく記録用です。</p></html>'
(root/'assets/vps-monitor-checklist.html').write_text(s,encoding='utf-8')

