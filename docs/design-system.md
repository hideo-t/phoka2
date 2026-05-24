# パークホームズオキナワ デザインシステム v1.0

最終更新: 2026-05-13 / PR #6 マージ時点

## 目的
hideo-t.github.io/phoka2/ 全ページのデザインを統一するための基準書。
新しいページや既存ページの修正時は本ドキュメントに準拠すること。
本ドキュメントの内容と差異が出る場合は本ドキュメントが正。

## 1. CIカラー（CSS変数）

| 変数 | 値 | 用途 |
|---|---|---|
| `--blue` | `#1560a8` | プライマリ（リンク、ボタン背景、ブランド） |
| `--navy` | `#0d2d5e` | 見出し、強調、フッター背景 |
| `--blue-light` | `#4fa3e0` | アクセント、サブテキストリンク |
| `--coral` | `#e8614a` | CTA（コンバージョン誘導） |
| `--coral-dark` | `#c44a35` | CTA ホバー |
| `--coral-light` | `#f08070` | CTA バリアント |
| `--black` | `#1a1a1a` | 通常テキスト最濃 |
| `--white` | `#ffffff` | 白背景 |
| `--bg` | `#f8fafc` | セクションのうす背景 |
| `--text` | `#1a2332` | 本文 |
| `--muted` | `#64748b` | サブテキスト |
| `--border` | `#d1e3f8` | 罫線、薄ボーダー |
| `--radius` | `12px` | 角丸の基本値 |

**禁止**: `--primary` / `--accent` / `--rl` / `--primary-dark` / `--primary-light` /
`--hero-from` / `--hero-to` / `--sky` / `--bg-alt` は今後新規コードで使用禁止。

## 2. タイポグラフィ
- フォントスタック: `'Hiragino Kaku Gothic ProN','Meiryo',sans-serif`
- 基準サイズ: 16px / line-height 1.75
- 見出し line-height: 1.4
- `Noto Sans JP` / `Zen Kaku Gothic New` などWebフォント追加は禁止

## 3. レイアウト
- `.container { max-width:1100px; padding:0 24px }`
- `.section { padding:80px 0 }`（モバイル 56px）
- 768px ブレークポイントでモバイル対応

## 4. NAV（ナビゲーション）
- 高さ: PC 108px / モバイル 同じ
- ロゴ: `logopkw.jpg` を `height:96px`
- 装飾: シーサー（`images/hero-sisa.jpg`）と守礼門（`images/hero-syuri.jpg`）をモバイル時のみ表示（`.nav-deco`）
- 5 ドロップダウン項目:
  1. **3つの理由** → 他社・自社比較（ABC比較）/ 暮らしのイメージ（#appeal1）/ 沖縄仕様の根拠（#appeal2）
  2. **商品** → ラインナップ / カタログDL / 設置事例集 / 価格表
  3. **AI見積** → 標準見積DL（PDF）
  4. **会社情報** → アクセス・会社概要 / トレーラーハウス協会 / 理事プロフィール
  5. **問い合わせ** → LINE / メール
- 右端CTA: `<a class="nav-cta" href="pages/estimate.html">無料見積もり</a>`（コーラル色）
- 商品比較（`pages/product-compare.html`）は提供していないため NAV から除外

## 5. フッター
- `.footer-grid` 3 カラム（PC）/ 1 カラム（モバイル）
  - 左: `.footer-brand`（ロゴ + 住所・電話・メール）
  - 中: サービス系リンク
  - 右: 会社・お問い合わせ系リンク
- 背景: `var(--navy)`
- 著作権: `© 2026 株式会社パークホームズオキナワ All Rights Reserved.`

## 6. 共通UIコンポーネント
- **モバイルCTAバー** (`.mobile-cta-bar`): モバイル時のみ下端固定。AI相談 / LINE / 見積もりの3ボタン
- **パクオ君フローティング** (`.pakuo-float`): 右下固定。`QAparkhome/` を別タブで開く
- **パクオ君バブル** (`.pakuo-bubble`): ページロード後 3 秒で表示、5 秒で自動消滅

### 例外
- `pages/estimate.html` ではパクオ君系（float + bubble + mobile-cta-bar）は表示しない
  （フォーム集中環境のため）

## 7. ボタン
- `.btn` 基本骨格、`.btn-primary`（青）、`.btn-coral`（橙）、`.btn-outline-blue`、`.btn-outline-white`、`.btn-lg`（大）
- 最小高さ 48px（タップ可能領域）

## 8. ファイル構造
```
phoka2/
├── index.html                  ← トップ（基準）
├── assets/
│   └── css/
│       └── common.css          ← 共通スタイル（PR #6 で新設）
├── images/
│   ├── hero-sisa.jpg
│   ├── hero-syuri.jpg
│   ├── cases/                  ← 事例画像 (-01/-02/-03.webp + @600w)
│   └── ...
├── cases/index.html
├── lineup/index.html
├── lineup/{slug}/index.html    ← 8 製品詳細
├── company/index.html
├── contact/index.html
├── faq/index.html
├── about/index.html
├── use-cases/index.html
├── sitemap/index.html
├── pages/                      ← Web フォーム / 比較 / カタログ
│   ├── abc-compare.html
│   ├── durability.html
│   ├── estimate.html           ← パクオ系UI除外
│   ├── price.html
│   ├── lineup.html             ← 旧 Catalog 2026 (今後リファクタ予定)
│   ├── catalog.pdf
│   └── estimate.pdf
└── docs/
    └── design-system.md        ← 本書
```

## 9. ページ固有 CSS の扱い
共通 CSS で吸収できないもの（フォーム、フィルタ、テーブル、details など）は
そのページの `<style>` ブロックに残してよい。ただし以下は守ること:
- CSS 変数は `--blue/--navy/--coral/--radius/...` を使う（旧変数禁止）
- 共通クラス名と被らない命名（例: `.case-card`, `.form-group` などはOK、`.btn` の再定義はNG）

## 10. 移行ロードマップ
- **PR #5 (済)**: トップ #cases 修正
- **PR #6 (本書同梱)**: Phase 1 — cases / lineup / company / contact / faq + common.css 新設
- **PR #7 予定**: Phase 2 — about / use-cases / sitemap / lineup/{8 製品}/
- **PR #8 予定**: Phase 3 — pages/abc-compare.html / durability.html / price.html / estimate.html
- **PR #9 予定**: Phase 4 — pages/lineup.html (Canva Catalog 2026) のリファクタ判断

## 11. 検証チェックリスト
新規 / 修正ページをマージする前に:
1. `<base href="https://hideo-t.github.io/phoka2/">` が `<head>` 先頭付近にある
2. `<link rel="stylesheet" href="assets/css/common.css">` がある
3. NAV / Footer / paku-float / mobile-cta-bar が本書 §4-6 と一致
4. 旧変数 `--primary` `--accent` `--rl` を `grep -r` で0件
5. `Noto Sans JP` `Zen Kaku Gothic` の参照が0件
6. og:url が正しい URL（タイポなし）
7. JSON-LD があれば url が `hideo-t.github.io/phoka2/...`

## 変更履歴
- 2026-05-13 v1.0 PR #6 で新規作成。Phase 1 5 ページ統一。
