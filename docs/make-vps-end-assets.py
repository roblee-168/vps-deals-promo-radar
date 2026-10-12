# ::ILANG
# ::STATE{@SELF, role:build original static diagrams and a savable official-condition table}
# ::BOUNDARY{never:invent contract conditions or interact with accounts}
from pathlib import Path
from html import escape
root = Path(__file__).resolve().parents[1]
assets = root / 'assets'
rows = [
 ['ConoHa VPS・時間課金','停止では料金不変。削除まで利用時間を課金','削除後は復旧不可','https://support.conoha.jp/v/deletevps/','2026-10-13'],
 ['ConoHa VPS・まとめトク','途中の即時削除不可。自動更新OFFを確認','自動更新ONでは満了日の7日前に更新・決済（確認日：2026-10-13）','https://support.conoha.jp/v/v3-longterm-update/','2026-10-13'],
 ['XServer VPS','解約申請後、利用期限日で停止','支払済み料金の返金なし','https://vps.xserver.ne.jp/support/faq/contract_cancel_what.php','2026-10-13'],
 ['さくらのVPS','支払方法・状況で終了日が変わる','支払済み料金の返金なし。決済後の解約は更新後期限','https://help.sakura.ad.jp/purpose_beginner/2566/','2026-10-13']
]
thead = ['契約','公式の終了条件','注意点','公式出典','確認日','本人の契約方式','次の更新・決済','利用終了日','操作完了の表示','未確認の条件']
table = '<table><thead><tr>'+''.join('<th>'+escape(x)+'</th>' for x in thead)+'</tr></thead><tbody>'
for row in rows:
    table += '<tr>'+''.join('<td>'+('<a href="'+escape(x)+'">公式案内</a>' if x.startswith('https://') else escape(x))+'</td>' for x in row)+''.join('<td contenteditable="true" aria-label="本人記入欄"></td>' for _ in range(5))+'</tr>'
table += '</tbody></table>'
page = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VPS終了条件の保存用比較表</title><style>body{font:16px/1.7 sans-serif;margin:24px;color:#173f37}table{border-collapse:collapse;min-width:1000px}th,td{border:1px solid #a4b9b1;padding:12px;min-width:120px}th{background:#edf3ef}td[contenteditable]{background:#fff9df}a{color:#126752}.wrap{overflow:auto}button{padding:12px}</style><h1>VPS終了条件の保存用比較表</h1><p>公式条件の確認日：2026-10-13。本人欄は編集できます。記入後に保存ボタンで別ファイルに保存してください。パスワード・カード情報・秘密鍵は記入しないでください。</p><button id="save">記入済み表を保存</button><div class="wrap">'+table+'</div><p>ConoHaの停止中料金は<a href="https://support.conoha.jp/common/faq/payment-q/billing-q/">公式料金FAQ</a>も参照（確認日：2026-10-13）。個別契約の終了日は本人が確認してください。</p><script>document.getElementById("save").addEventListener("click",()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob(["<!doctype html>"+document.documentElement.outerHTML],{type:"text/html;charset=utf-8"}));a.download="vps-end-billing-filled.html";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});</script></html>'
(assets/'vps-end-billing-table.html').write_text(page,encoding='utf-8')
slides = [
 ('deadline','先に、契約方式を確かめる','停止・削除・更新停止は別の操作', [('時間課金','削除までの利用時間を確認'),('前払い','自動更新と満了条件を確認'),('解約申請','利用期限・支払状況を確認')],'公式条件を、自分の契約表示と照合する'),
 ('proof','申請完了 ≠ 契約の終了','手続きの表示と利用終了日を分ける',[('XServer VPS','申請後も利用期限日まで利用'),('さくらのVPS','完了通知の対象と終了日を確認'),('ConoHa・まとめトク','更新OFFでも途中終了ではない')],'終了日が未来なら、終了予定として残す'),
 ('rate','単価の換算 ≠ 終了日の確認','比較値と契約条件を混同しない',[('時間単価','公式料金表の単位を確認'),('換算','比較用の期間を決めて計算'),('終了条件','削除・満了・解約条件を別に確認')],'単価だけで、課金が終わったとは判断しない')
]
for slug,title,sub,cards,foot in slides:
    body=''
    for i,(label,txt) in enumerate(cards):
        y=300+i*125
        body+=f'<rect x="72" y="{y}" width="1136" height="100" rx="18" fill="#fff"/><text x="104" y="{y+40}" font-size="25" font-weight="700">{escape(label)}</text><text x="400" y="{y+59}" font-size="28">{escape(txt)}</text>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="840" viewBox="0 0 1280 840"><rect width="1280" height="840" fill="#edf4ee"/><g font-family="Yu Gothic,Meiryo,sans-serif" fill="#173f37"><text x="72" y="94" font-size="22" letter-spacing="4">PERKMINGLE / VPS</text><text x="72" y="176" font-size="43" font-weight="700">{escape(title)}</text><text x="72" y="232" font-size="27">{escape(sub)}</text>{body}<text x="72" y="746" font-size="27">{escape(foot)}</text><text x="72" y="797" font-size="20">記事の公式条件・確認日：2026-10-13</text></g></svg>'
    (assets/f'vps-end-{slug}.svg').write_text(svg,encoding='utf-8')
print('Saved downloadable table and three original SVG diagrams.')
