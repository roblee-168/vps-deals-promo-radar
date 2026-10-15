# ::ILANG
# ::STATE{@SELF, role:assemble dated network comparison and original diagrams}
# ::BOUNDARY{never:change live servers or claim measured VPS performance}
from pathlib import Path
from html import escape
from PIL import Image,ImageDraw,ImageFont
import json
root=Path.cwd();media=root/'work-vps-network-media';media.mkdir(exist_ok=True)
code=Path('docs/prepare-vps-backup.py').read_text(encoding='utf-8-sig')
exec(code[code.index('font='):code.index("graphic('vps-backup-evidence'")])
graphic('vps-network-layers','転送と速度を分ける',[('転送量の料金','無料の表示を単独で読む'),('回線の条件','共有・制限の原文も残す'),('本人の観測','料金表から結果を推定しない')],'公式料金表の読み方｜確認 2026-10-15')
graphic('vps-network-target','通信する対象をそろえる',[('標準のIP','サーバーのネットワーク情報'),('追加のIP','ネットワークの追加IP画面'),('観測する向きと相手','条件が違えば別の記録にする')],'公式操作の経路＋編集上の記録方法｜2026-10-15')
graphic('vps-network-cost','追加料金だけを積算',[('公式の時間単価','300Mbps：税込8.3円／時'),('本稿の仮定：12時間','8.3 × 12 ＝ 99.6円'),('請求総額ではない','VPS本体の料金とは分ける')],'vps.conoha.jp/pricing/｜入力確認 2026-10-15')
graphic('vps-network-plan-review','変更後の確認を残す',[('変更前の基準','本人が使うサービスの応答'),('変更処理の表示','希望した対象とプラン'),('再開後の観測','表示だけで復旧扱いにしない')],'プラン変更記事にある確認方法｜2026-10-15')
rows=[('転送量の課金','課金無し、無制限。','https://vps.conoha.jp/pricing/'),('インターネットの条件','50Gbps共有(100Mbps制限あり)','https://vps.conoha.jp/pricing/'),('標準IPの設定先','サーバーのネットワーク情報','https://support.conoha.jp/v/networkupgrade/'),('追加IPの設定先','ネットワークの追加IPアドレス','https://support.conoha.jp/v/networkupgrade/'),('帯域拡張の料金','選ぶ帯域・月額欄・時間欄を別記する','https://vps.conoha.jp/pricing/'),('観測を比べる条件','同じ対象IP・方向・相手・時点の条件を照合する（編集方法）','https://support.conoha.jp/v/networkupgrade/')]
s='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPS転送量と帯域の保存用比較表</title><style>body{font:16px/1.7 sans-serif;margin:20px;color:#17483d}main{max-width:100%;overflow-x:auto}table{border-collapse:collapse}th,td{border:1px solid #abb;padding:14px;min-width:160px}td[contenteditable]{background:#fff9df}</style><h1>VPS転送量と帯域の保存用比較表</h1><p>独立ファイルとして保存できます。本人のIP、方向、相手、時点と観測値は空欄です。編集上の照合記録であり、実測値は入っていません。認証情報は記入しないでください。</p><a href="/ja/vps-network/">転送量と帯域の確認へ</a><main><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['確認項目','公式条件・編集上の照合方法','公式出典','確認日','本人の契約・対象IP','方向・通信相手','条件・観測時点','結果・残る未確認'])+'</tr></thead><tbody>'
for a,b,u in rows:s+='<tr><td>'+a+'</td><td>'+b+'</td><td><a href="'+u+'">公式</a></td><td>2026-10-15</td>'+('<td contenteditable="true" aria-label="本人の未確認欄"></td>'*4)+'</tr>'
s+='</tbody></table></main><p>料金欄、設定表示、本人の観測を別々に残します。条件がそろわない結果を、帯域拡張の成否として採点しません。</p></html>'
Path('assets/vps-network-checklist.html').write_text(s,encoding='utf-8')
p=Path('build.py');s=p.read_text(encoding='utf-8');needle="    english_home = dest/'index.html'";assert s.count(needle)==1
new="    network_content = (ROOT/'templates/ja-vps-network.html').read_text(encoding='utf-8')\n    render('/ja/vps-network/', 'VPSの転送量と帯域：無料の転送と回線速度を分けて確認する | PerkMingle',\n           '転送量の課金、共有回線、帯域制限、追加IPの設定先を分けて確認。保存用比較表と追加料金の換算例を掲載します。',\n           network_content, [{'@type':'Article','headline':'VPSの転送量と帯域：無料の転送と回線速度を分けて確認する','inLanguage':'ja-JP','datePublished':'2026-10-15','citation':['https://support.conoha.jp/v/networkupgrade/','https://vps.conoha.jp/pricing/']}],\n           [{'lang':'ja-JP','path':'/ja/vps-network/'}])\n    pages[-1] = (base+'/ja/vps-network/', '2026-10-15')\n\n"
s=s.replace(needle,new+needle)
needle='VPS：プラン変更前の停止条件と再開の確認 →</a></p></div>';assert s.count(needle)==1
s=s.replace(needle,'VPS：プラン変更前の停止条件と再開の確認 →</a></p><p style="margin:0;padding:1.25rem;border:1px solid #cddcd7;border-radius:1rem;background:#f5f8f6"><a class="ja-card-link" href="/ja/vps-network/">VPS：転送量と帯域の条件を分けて確認 →</a></p></div>');p.write_text(s,encoding='utf-8')
p=Path('templates/ja-vps-plan-change.html');s=p.read_text(encoding='utf-8');needle='<p class="ja-back">';assert s.count(needle)==1
s=s.replace(needle,'<figure class="ja-section"><img src="/assets/vps-network-plan-review.svg" alt="変更前の基準、処理表示、再開後の観測を分ける図" loading="lazy" style="width:100%;height:auto"><figcaption>変更後の確認を、希望プランの表示とサービスの応答に分けます。</figcaption></figure>'+needle);p.write_text(s,encoding='utf-8')
(media/'narration.txt').write_text('Free data transfer and connection speed describe different things. The ConoHa pricing page lists unlimited data transfer without a transfer charge, but it lists shared network conditions separately. Keep those qualifiers. Before changing bandwidth, identify the IP address that carries the traffic. The official guide uses the server network information for the default IP, and the additional IP address screen for an optional IP. Our saveable sheet keeps the contract, target IP, traffic direction, remote endpoint, observation time, and result in separate fields. If those conditions differ, keep separate records rather than claim the upgrade succeeded or failed. A setting completion message and an observed service result are different checks. The cost example calculates an additional option only, using an explicitly assumed duration. It is not a total invoice. This guide reports no live server change and no measured connection speed.',encoding='utf-8')
video=Path('work-vps-plan-change-media/video.py').read_text(encoding='utf-8-sig').replace("['vps-plan-change-decision','vps-plan-change-sequence','vps-plan-change-cost']","['vps-network-layers','vps-network-target','vps-network-cost']").replace('vps-plan-change-cost.png','vps-network-cost.png').replace('PerkMingle-VPS-plan-change.mp4','PerkMingle-VPS-network.mp4');(media/'video.py').write_text(video,encoding='utf-8')
