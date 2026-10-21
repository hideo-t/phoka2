# 問い合わせの送信とスプレッドシート記録

サイトの問い合わせは、すべて `assets/js/inquiry.js` を通して送られる。

| ページ | フォーム | 件名 |
|---|---|---|
| `contact/index.html` | お問い合わせ（`data-inquiry` 属性） | 【サイトお問い合わせ】 |
| `pages/estimate.html` | 見積書画面の「この内容で見積もり依頼を送る」 | 【見積もり依頼】 |
| `pages/transport-office.html` | 運送業LPの資料請求 | 【運送業の営業所】 |
| `pages/islands-lp.html` | 離島LPの資料請求 | 【離島向け住宅】 |

## メール（FormSubmit）

- 宛先: `kinjyo@parkhomes-okinawa.com`（FormSubmit の有効化済み）
- CC: `sakata@parkhomes-okinawa.com`, `parkhomes.okinawa@gmail.com`
  - 2026-10 に sakata@ がメールボックス容量オーバーで受信できなくなった。
    1つの受信箱が止まっても取りこぼさないよう、容量の大きい Gmail を CC に加えている。
- お客様への自動返信: `_autoresponse`。お客様がメールアドレスを入力したときだけ送られる。
- 送信後は `contact/thanks.html` に移動する。

宛先・CC・自動返信の文面を変えるときは `inquiry.js` 冒頭の定数だけを直す。

### 翻訳ページ（/en/ /zh-Hant/ /zh-Hans/ /ko/）

- 翻訳ページは `i18n/build.py` が日本語原本から生成する。フォームを直すときは日本語原本だけを編集し、`extract.py → _tr に訳を追加 → merge.py → build.py → verify.py` の順に流す。
- `inquiry.js` は `<html lang>` を見て、自動返信の文面と送信後の完了ページをその言語に切り替える。
- 社内に届くメールの件名・項目名は日本語のまま。件名の末尾に「［英語ページ］」などが付く。

## スプレッドシートへの記録（任意・推奨）

メールが全部届かなくても、問い合わせが一覧で残るようにする。

### 設定手順（parkhomes.okinawa@gmail.com でログインして行う）

1. Google スプレッドシートを新規作成し、名前を「サイト問い合わせ記録」にする。
2. メニュー「拡張機能」→「Apps Script」を開き、`コード.gs` の中身を下記のコードに置き換えて保存する。
3. 右上の「デプロイ」→「新しいデプロイ」を開き、種類は「ウェブアプリ」を選んで次のように設定する。
   - 次のユーザーとして実行: **自分**
   - アクセスできるユーザー: **全員**
4. 承認画面で許可したら、表示された「ウェブアプリの URL」（`https://script.google.com/macros/s/…/exec`）をコピーする。
5. `assets/js/inquiry.js` の `SHEET_URL = ''` にその URL を入れて push する。

```javascript
// サイト問い合わせ → スプレッドシート記録（parkhomes-okinawa.com）
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(['受信日時', '件名', 'ページ', '内容', '対応者', '対応状況']);
      sheet.setFrozenRows(1);
    }
    var fields = data.fields || {};
    var body = Object.keys(fields)
      .filter(function (k) { return fields[k] !== ''; })
      .map(function (k) { return k + '：' + fields[k]; })
      .join('\n');
    sheet.appendRow([new Date(), data.subject || '', data.page || '', body, '', '未対応']);
    return ContentService.createTextOutput('ok');
  } finally {
    lock.releaseLock();
  }
}
```

- 「対応者」「対応状況」列は、担当者が手で書き込む欄。
- コードを書き換えたら「デプロイを管理」から**同じデプロイの新しいバージョン**として更新する。新規デプロイにすると URL が変わってしまう。
- 記録はメール送信とは別に動く。記録に失敗してもメールは送られる。
