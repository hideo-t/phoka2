# -*- coding: utf-8 -*-
"""多言語ビルドの共通設定。

日本語版（リポジトリ直下）を原本とし、言語ごとのディレクトリに
翻訳済み静的HTMLを生成する。
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.join(ROOT, "i18n")
STRINGS = os.path.join(I18N, "strings")

SITE = "https://parkhomes-okinawa.com"

# 出力先ディレクトリ名 -> (html lang属性, og:locale, 言語切替UIの表示名)
LANGS = {
    "en":      ("en",      "en_US", "English"),
    "zh-Hant": ("zh-Hant", "zh_TW", "繁體中文"),
    "zh-Hans": ("zh-Hans", "zh_CN", "简体中文"),
    "ko":      ("ko",      "ko_KR", "한국어"),
}
JA_LABEL = "日本語"

# 翻訳対象の稼働ページ。ここに無いページ（Jimdo移行残骸など）は日本語のまま。
PAGES = [
    "index.html",
    "about/index.html",
    "cases/index.html",
    "company/index.html",
    "company/オフィス紹介-展示場/index.html",
    "company/協力会社一覧/index.html",
    "company/社長挨拶/index.html",
    "company/製作スタッフ/index.html",
    "contact/index.html",
    "faq/index.html",
    "lineup/index.html",
    "lineup/airstream/index.html",
    "lineup/amalfi/index.html",
    "lineup/container/index.html",
    "lineup/food-truck/index.html",
    "lineup/parq/index.html",
    "lineup/round-premier/index.html",
    "lineup/sauna/index.html",
    "lineup/solar-haven/index.html",
    "use-cases/index.html",
    "pages/abc-compare.html",
    "pages/amalfi-gallery.html",
    "pages/catalog.html",
    "pages/durability.html",
    "pages/estimate.html",
    "pages/islands-lp.html",
    "pages/press.html",
    "pages/price.html",
    "pages/tax-saving.html",
    "pages/transport-office.html",
    "sitemap/index.html",
    "j/privacy/index.html",
]

# 翻訳対象ページの集合（URL書き換えの判定に使う）
PAGESET = set(PAGES)

def src_path(rel):
    return os.path.join(ROOT, rel.replace("/", os.sep))

def out_path(lang, rel):
    return os.path.join(ROOT, lang, rel.replace("/", os.sep))

def url_of(rel):
    """リポジトリ相対パス -> サイト内絶対パス（末尾 index.html は落とす）"""
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    if rel == "index.html":
        return "/"
    return "/" + rel
