# -*- coding: utf-8 -*-
"""sitemap.xml を多言語対応で作り直す。

既存の日本語URLと lastmod はそのまま残す。翻訳対象ページだけは
言語ごとの <url> に分け、どのURLからも全言語を辿れるよう
xhtml:link の相互参照を全件に付ける（Googleの要件）。

  python i18n/sitemap.py
"""
import io, os, re, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

SITEMAP = os.path.join(config.ROOT, "sitemap.xml")
# 生成済みサイトマップには xhtml:link が入るので、<url> の中身は丸ごと拾ってから
# loc と lastmod を取り出す。要素を決め打ちで並べると再生成時に読み落とす。
RE_URL = re.compile(r"<url>(.*?)</url>", re.S)
RE_LOC = re.compile(r"<loc>([^<]+)</loc>")
RE_MOD = re.compile(r"<lastmod>([^<]+)</lastmod>")


def alternates(path):
    """1ページ分の hreflang 相互参照。全言語版に同じものを載せる。"""
    out = ['    <xhtml:link rel="alternate" hreflang="ja" href="%s%s"/>' % (config.SITE, path)]
    for code in config.LANGS:
        out.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s/%s%s"/>'
                   % (config.LANGS[code][0], config.SITE, code, path))
    out.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s"/>'
               % (config.SITE, path))
    return out


def block(loc, lastmod, path=None):
    lines = ["  <url>", "    <loc>%s</loc>" % loc]
    if lastmod:
        lines.append("    <lastmod>%s</lastmod>" % lastmod)
    if path is not None:
        lines += alternates(path)
    lines.append("  </url>")
    return lines


def main():
    raw = io.open(SITEMAP, encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    # 翻訳対象ページのサイト内パス
    paths = {config.url_of(rel): rel for rel in config.PAGES}

    body, seen, n_multi = [], set(), 0
    for chunk in RE_URL.findall(raw):
        m = RE_LOC.search(chunk)
        if not m:
            continue
        loc = m.group(1)
        mod = RE_MOD.search(chunk)
        lastmod = mod.group(1) if mod else ""
        path = loc[len(config.SITE):] if loc.startswith(config.SITE) else None
        # 前回生成した言語版URLは、日本語版から作り直すのでここでは捨てる
        if path and path.split("/")[1] in config.LANGS:
            continue
        seen.add(path)
        if path in paths:
            n_multi += 1
            body += block(loc, today, path)
            for code in config.LANGS:
                body += block("%s/%s%s" % (config.SITE, code, path), today, path)
        else:
            body += block(loc, lastmod)

    # 既存サイトマップに載っていなかった翻訳対象ページを補う
    added = 0
    for path in paths:
        if path in seen:
            continue
        added += 1
        body += block(config.SITE + path, today, path)
        for code in config.LANGS:
            body += block("%s/%s%s" % (config.SITE, code, path), today, path)

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
           '        xmlns:xhtml="http://www.w3.org/1999/xhtml">'] + body + ["</urlset>", ""]
    io.open(SITEMAP, "w", encoding="utf-8", newline="").write("\n".join(out))

    total = len(re.findall(r"<url>", "\n".join(body)))
    print("sitemap.xml: 全%d URL（多言語化 %d ページ × %d 言語、新規追加 %d ページ）"
          % (total, n_multi + added, len(config.LANGS) + 1, added))


if __name__ == "__main__":
    main()
