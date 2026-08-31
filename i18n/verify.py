# -*- coding: utf-8 -*-
"""生成した言語版ページを検証する。

  python i18n/verify.py [--lang en ...]

原本にもとから存在する不備（外部サイト扱いのリンク切れなど）を数えても
意味がないので、リンク到達性は「原本では解決できたのに生成側で解決できない」
回帰だけを報告する。
"""
import io, json, os, re, sys, argparse
from urllib.parse import urljoin, urlparse, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, htmlmask, build

RE_ATTR = re.compile(r"""\b(?:href|src)\s*=\s*("[^"]*"|'[^']*')""", re.I)
RE_LD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)
# 未訳検出はかなの有無で行う（漢字は中国語訳と重なるので使えない）。
# ただし ・ と ー は片仮名ブロックにありながら中国語でも普通に使う約物なので除く。
JA = re.compile(r"[぀-ゟ゠-ヺヽ-ヿ]")


def links(text):
    for m in RE_ATTR.finditer(text):
        yield m.group(1)[1:-1].strip()


def resolvable(val, base):
    """サイト内リンクなら、対応するファイルが存在するかを返す。対象外は None。"""
    if not val or val.startswith(build.SKIP_SCHEME):
        return None
    p = urlparse(urljoin(base, val))
    if p.scheme and p.scheme not in ("http", "https"):
        return None
    if p.netloc and p.netloc.lower() not in build.HOSTS:
        return None
    rel = build.path_to_rel(p.path)
    return os.path.exists(os.path.join(config.ROOT, rel.replace("/", os.sep)))


def check(lang):
    attr = "ja" if lang == "ja" else config.LANGS[lang][0]
    problems = []
    deltas = set()

    for rel in config.PAGES:
        src = io.open(config.src_path(rel), encoding="utf-8").read()
        dst_p = config.src_path(rel) if lang == "ja" else config.out_path(lang, rel)
        if not os.path.exists(dst_p):
            problems.append((rel, "生成物がない"))
            continue
        out = io.open(dst_p, encoding="utf-8").read()

        def bad(msg):
            problems.append((rel, msg))

        if "\x00" in out:
            bad("マスクトークンが残っている")

        m = re.search(r"<html\b[^>]*\blang\s*=\s*[\"']([^\"']*)", out, re.I)
        if not m or m.group(1) != attr:
            bad("html lang が %s でない (%s)" % (attr, m.group(1) if m else "なし"))

        if out.count('rel="canonical"') != 1:
            bad("canonical が1本でない (%d)" % out.count('rel="canonical"'))
        n_alt = len(re.findall(r'rel="alternate"\s+hreflang=', out))
        if n_alt != len(config.LANGS) + 2:      # ja + 各言語 + x-default
            bad("hreflang の本数が %d" % n_alt)

        sb = re.search(r"<base\b[^>]*>", src, re.I)
        ob = re.search(r"<base\b[^>]*>", out, re.I)
        if (sb is None) != (ob is None) or (sb and sb.group(0) != ob.group(0)):
            bad("base タグが原本と違う: %s" % (ob.group(0) if ob else "なし"))

        for body in RE_LD.findall(out):
            try:
                json.loads(body)
            except Exception as e:
                bad("JSON-LD が壊れている: %s" % e)

        # 構造: 差し込みブロックを外せば原本とタグ数が一致するはず（0以外は本文破壊）
        deltas.add(len(re.findall(r"<[a-zA-Z/!]", build.strip_blocks(out)))
                   - len(re.findall(r"<[a-zA-Z/!]", build.strip_blocks(src))))

        # 差し込みブロック（hreflang・言語バー）は他言語を先に指すので本文と分けて扱う
        body = build.strip_blocks(out)

        # リンク到達性。原本から持ち越しの不備は数えず、生成漏れだけを回帰として拾う
        obase = build.page_base(rel, out)
        broken = []
        for v in links(body):
            if resolvable(v, obase) is not False:
                continue
            path = urlparse(urljoin(obase, v)).path
            stripped = re.sub(r"^/(?:%s)/" % "|".join(config.LANGS), "/", path)
            if os.path.exists(os.path.join(
                    config.ROOT, build.path_to_rel(stripped).replace("/", os.sep))):
                broken.append(v)        # 日本語版には在るのに言語版に無い＝生成漏れ
        for v in sorted(set(broken))[:5]:
            bad("リンク先がない: %s" % v)

        if lang != "ja":
            # URLは翻訳対象外。日本語のディレクトリ名がそのまま入るので未訳判定から外す
            scan = re.sub(r"https?://\S+", "", htmlmask.Masked(body).text)
            if JA.search(scan):
                body = scan
                left = sorted(set(re.findall(r"[^\s<>\"'=;:,.()（）]*[぀-ゟ゠-ヿ][^\s<>\"'=;:,.()（）]*", body)))
                bad("かなが残っている(%d種): %s" % (len(left), " / ".join(left[:6])))

    return problems, deltas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", action="append")
    a = ap.parse_args()
    langs = a.lang or (["ja"] + list(config.LANGS))
    rc = 0
    for lang in langs:
        problems, deltas = check(lang)
        print("=" * 60)
        print("%s: pages=%d  タグ増加=%s" % (lang, len(config.PAGES), sorted(deltas)))
        if len(deltas) > 1:
            print("  !! 挿入以外の構造変化が疑われる（増加数がページごとに違う）")
        if not problems:
            print("  問題なし")
        else:
            rc = 1
            shown = {}
            for rel, msg in problems:
                shown.setdefault(rel, []).append(msg)
            for rel, msgs in list(shown.items())[:12]:
                print("  %s" % rel)
                for m in msgs[:4]:
                    print("     - %s" % m)
            print("  合計 %d 件 / %d ページ" % (len(problems), len(shown)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
