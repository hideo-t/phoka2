# アクセス解析（GA4 / Microsoft Clarity）

最終更新: 2026-08-29

## 1. 構成

計測タグは **`assets/js/analytics.js` 1本** にまとまっており、全 67 ページの HTML から読み込まれています。
タグの追加・変更（広告タグなど）は、このファイルだけを直せば全ページに反映されます。

```js
var GA4_ID     = 'G-RHS863EHBQ';   // Google アナリティクス 4
var CLARITY_ID = 'y9lqd0er98';     // Microsoft Clarity
```

ID を空文字にすると、そのツールは一切読み込まれません（無効化したいときは空にするだけ）。

### 本番ドメイン以外では計測しない

`analytics.js` は `parkhomes-okinawa.com` 以外のホストでは何も送信しません。
ローカルでの表示確認（`file://` や `localhost`）がデータに混ざらないようにするためです。
除外された場合はブラウザのコンソールに `[analytics] 本番ドメイン外のため計測しません` と出ます。

## 2. 計測しているイベント

GA4 の自動計測（拡張計測機能）に加えて、`analytics.js` が独自に送っているイベントです。
GA4 の自動計測は `tel:` / `mailto:` のクリックを拾わないため、自前で送っています。

| イベント名 | 発火タイミング | 主なパラメータ | サイト内の該当箇所 |
|---|---|---|---|
| `contact_tel` | `tel:` リンクのクリック | `tel_number`, `link_text` | 電話番号リンク（76 箇所） |
| `contact_mail` | `mailto:` リンクのクリック | `link_text` | メールリンク（58 箇所） |
| `contact_line` | `lin.ee` / `line.me` へのリンククリック | `link_text` | LINE 相談ボタン（38 箇所） |
| `download_pdf` | `.pdf` へのリンククリック | `file_name`, `link_text` | 見積り資料など（6 箇所） |
| `contact_form_submit` | `<form>` の送信 | `form_action` | `/contact/` の問い合わせフォーム |

全イベントに `page_path`（発火したページのパス）が付きます。

## 3. GA4 側に残っている設定作業

タグは動いていますが、以下は GA4 の管理画面での操作が必要です（このリポジトリの変更では対応できません）。

### 3-1. キーイベント（旧コンバージョン）の登録

**管理 → データの表示 → イベント** を開き、上の表のイベント名を「キーイベントとしてマークを付ける」で ON にします。
※ イベントは一度発火してからでないと一覧に出ません。出てこない場合は
**管理 → データの表示 → キーイベント → 「新しいキーイベント」** でイベント名を直接入力しても登録できます。

推奨: `contact_tel` / `contact_line` / `contact_form_submit` の 3 つ。
`contact_mail`・`download_pdf` は検討度の指標として、必要に応じて追加。

### 3-2. 社内アクセスの除外

**管理 → データの収集と修正 → データ ストリーム → （ストリームを選択）→ タグ設定を行う → 内部トラフィックの定義** で
事務所のグローバル IP を登録し、**データフィルタ** で「内部トラフィック」を *有効* にします。
（作成直後のフィルタは「テスト」状態で、除外が効きません。必ず「有効」に切り替えてください。）

### 3-3. Google Search Console との連携

`sitemap.xml` と `robots.txt` は設置済みです。

- Search Console にプロパティ `parkhomes-okinawa.com` を登録
- サイトマップとして `https://parkhomes-okinawa.com/sitemap.xml` を送信
- GA4 側で **管理 → サービス間のリンク設定 → Search Console のリンク** を設定すると、
  検索キーワードのレポートが GA4 内で見られるようになります

### 3-4. データ保持期間

**管理 → データの収集と修正 → データの保持** を **14 か月** に変更（初期値は 2 か月）。
探索レポートで前年比を見るために必要です。

## 4. Microsoft Clarity

プロジェクト ID: `y9lqd0er98` / ダッシュボード: https://clarity.microsoft.com/

ヒートマップとセッション録画が自動で溜まります。追加設定は不要ですが、
Clarity の **Settings → Google Analytics integration** で GA4 と連携しておくと、
GA4 のセグメントから該当セッションの録画に飛べるようになります。

## 5. 動作確認の方法

ブラウザで https://parkhomes-okinawa.com/ を開き、DevTools のコンソールで:

```js
window.GA4_ID       // 'G-RHS863EHBQ'
window.CLARITY_ID   // 'y9lqd0er98'
typeof window.gtag  // 'function'
typeof window.clarity // 'function'
```

Network タブで `google-analytics.com/g/collect`（`tid=G-RHS863EHBQ` 付き）と
`clarity.ms/collect` が飛んでいれば計測できています。

> **注意**: `g/collect` のステータスが `503` と表示されることがありますが、これは
> レスポンスが CORS で読み取れないことによる表示上の誤りです。同じ回線から
> `curl` で叩くと `204`（正常）が返ります。実際の着弾は GA4 のリアルタイムレポートで確認してください。

## 6. 既知の課題

- **問い合わせフォームの送信先が仮のまま**
  `contact/index.html:140` の `<form action="https://formspree.io/f/parkhomes">` は
  Formspree の実 ID（ランダムな英数字）ではなくプレースホルダーです。
  このままではフォーム送信が届かない可能性が高いため、Formspree でフォームを作成し、
  発行された ID に差し替える必要があります。
- **サイトマップの網羅率**
  サイト内の HTML は 67 ページありますが、`sitemap.xml` に載っているのは 34 URL です。
  意図的な除外でなければ、追加を検討してください。
