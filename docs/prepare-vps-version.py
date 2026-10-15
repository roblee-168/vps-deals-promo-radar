# ::ILANG
# ::STATE{@SELF, role:prepare original applicability diagrams and independent worksheet}
# ::BOUNDARY{never:operate a contract or invent version compatibility}
from pathlib import Path
from html import escape
from PIL import Image,ImageDraw,ImageFont
root=Path.cwd();media=root/'work-vps-version-media';media.mkdir(exist_ok=True)
code=Path('docs/prepare-vps-backup.py').read_text(encoding='utf-8-sig')
exec(code[code.index('font='):code.index("graphic('vps-backup-evidence'")])
graphic('vps-version-scope','手順の適用先をそろえる',[('ガイドの対象者','注意書きと本人の利用状況'),('選択中の版','表示を本人が確認する'),('機能の制約','対象版と対象外条件を照合')],'公式手順＋編集上の確認方法｜2026-10-15')
graphic('vps-version-decision','似た画面だけでは進めない',[('対象一致','該当機能の残る条件を確認'),('対象外','使わない理由と出典を残す'),('未確認','足りない根拠を明示して保留')],'編集上の判断方法｜契約画面の操作なし')
graphic('vps-version-cost','旧契約へ単価を転記しない',[('現行時間単価','メモリ1GB：1.9円／時'),('仮定：10時間','1.9 × 10 ＝ 19円'),('本人の旧契約とは別','単価未確認なら見積もらない')],'vps.conoha.jp/pricing/｜確認 2026-10-15')
graphic('vps-version-restart-review','再起動の手順も適用先を確認',[('読む手順','対象者と注意書き'),('見る画面','本人の選択中の版と対象'),('実施する操作','機能の条件まで照合')],'編集上の確認方法｜サーバー操作なし')
rows=[('切替ガイド','2023年11月15日以前の利用者向け','https://support.conoha.jp/v/changeversion/'),('画面の版','ガイド対象者はダッシュボード左下の表示を確認','https://support.conoha.jp/v/changeversion/'),('帯域拡張','VPS3.0向け・VPS2.0は利用不可','https://support.conoha.jp/v/networkupgrade/'),('バックアップ','復元先などが版で異なるため該当区分を照合','https://support.conoha.jp/vps/faq/autobackup-q/'),('料金の対象','現行と旧版の料金資料を分けて照合','https://vps.conoha.jp/pricing/'),('手順の採用','対象一致・対象外・未確認と理由を残す（編集欄）','https://support.conoha.jp/v/changeversion/')]
heads=['比較項目','公開条件','公式出典','公開条件の確認日','本人の対象・観測時点','実際に見た版・条件','採用／保留の手順URL','判断理由・残る確認']
s='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPSの版と手順の適用先・保存用比較表</title><style>body{font:16px/1.7 sans-serif;margin:20px;color:#17483d}main{max-width:100%;overflow-x:auto}table{border-collapse:collapse}th,td{border:1px solid #abb;padding:14px;min-width:160px}td[contenteditable]{background:#fff9df}</style><h1>VPSの版と手順の適用先・保存用比較表</h1><p>独立ファイルとして保存できます。本人の対象と画面は未確認のため空欄です。編集上の照合表で、移行や機能の利用完了を判定しません。秘密情報は記入しないでください。</p><a href="/ja/vps-version/">記事へ戻る</a><main><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in heads)+'</tr></thead><tbody>'
for a,b,u in rows:s+='<tr><td>'+a+'</td><td>'+b+'</td><td><a href="'+u+'">公式</a></td><td>2026-10-15</td>'+('<td contenteditable="true" aria-label="本人の未確認欄"></td>'*4)+'</tr>'
s+='</tbody></table></main><p>公式条件の確認日と、本人が画面を見た時点は別欄です。</p></html>'
(root/'assets/vps-version-checklist.html').write_text(s,encoding='utf-8')
