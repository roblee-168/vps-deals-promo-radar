# ::ILANG
# ::STATE{@SELF, role:prepare original restart graphics and saveable comparison}
# ::BOUNDARY{never:invent observations or operate a live server}
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont
root=Path.cwd();media=root/'work-vps-restart-media';media.mkdir(exist_ok=True)
code=Path('docs/prepare-vps-backup.py').read_text(encoding='utf-8-sig')
exec(code[code.index('font='):code.index("graphic('vps-backup-evidence'")])
graphic('vps-restart-target','対象と操作を照合する',[('対象サーバー','ネームタグと目的の対象'),('操作の名前','起動・再起動・シャットダウン'),('実行の確認','「はい」が選択操作の実行')],'support.conoha.jp/v/restart/｜確認 2026-10-15')
graphic('vps-restart-accept','押す前に再開条件を決める',[('予定','担当と確認する機能を決める'),('送信','選んだ操作と時点を残す'),('受入','見た結果と未確認を分ける')],'編集上の確認方法｜実サーバー操作なし')
graphic('vps-restart-cost','本体単価の参考積算',[('1.9円／時','公式時間課金・メモリ1GB'),('× 8時間 = 15.2円','時間は編集上の仮定'),('請求額とは別','再起動料金・停止時間の実測ではない')],'vps.conoha.jp/pricing/｜確認 2026-10-15')
graphic('vps-restart-console-review','操作後の確認を分ける',[('管理画面','操作と表示の観測'),('コンソール','その経路の応答'),('利用する機能','本人が再開条件を確認')],'編集上の確認方法｜実サーバー操作なし')
rows=[('対象','目的の対象と選んだネームタグ'),('操作の候補','起動・再起動・シャットダウンを混同しない'),('確認画面','「はい」で選択した操作を実行'),('影響と担当','使われる機能と担当を事前に確認（編集欄）'),('再開の受入','確認予定と実際の機能応答を比較（編集欄）'),('引継ぎ','最後の観測と未確認を残す（編集欄）')]
heads=['比較項目','照合する条件','出典','確認日','本人の対象・担当','予定の操作・受入条件','実際の操作・観測時点','差異・未確認・次の確認']
s='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPS再起動前後の保存用比較表</title><style>body{font:16px/1.7 sans-serif;margin:20px;color:#17483d}main{max-width:100%;overflow-x:auto}table{border-collapse:collapse}th,td{border:1px solid #abb;padding:14px;min-width:160px}td[contenteditable]{background:#fff9df}</style><h1>VPS再起動前後の保存用比較表</h1><p>独立ファイルとして保存できます。本人の対象、操作候補、事前の受入条件と事後の観測は空欄です。編集上の確認方法で、実際の操作結果は入っていません。秘密情報は記入しません。</p><a href="/ja/vps-restart/">記事へ戻る</a><main><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in heads)+'</tr></thead><tbody>'
for a,b in rows:s+='<tr><td>'+a+'</td><td>'+b+'</td><td><a href="https://support.conoha.jp/v/restart/">公式の操作手順</a></td><td>2026-10-15</td>'+('<td contenteditable="true" aria-label="本人の未確認欄"></td>'*4)+'</tr>'
s+='</tbody></table></main><p>操作を送ったことと利用機能を確認したことは別に記録します。</p></html>'
(root/'assets/vps-restart-checklist.html').write_text(s,encoding='utf-8')
