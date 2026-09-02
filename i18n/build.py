# -*- coding: utf-8 -*-
"""日本語原本から各言語の静的ページを生成する。

  python i18n/build.py            # 全言語を生成し、日本語原本にも言語バーを差し込む
  python i18n/build.py --check    # 書き込まずに未訳件数だけ表示

bs4での再シリアライズは行わない。マスク済みテキストへの一括置換のみを使い、
属性順・インデント・実体参照を原本のまま保つ。
"""
import io, json, os, re, sys, argparse
from urllib.parse import urljoin, urlparse, quote, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, htmlmask

HOSTS = {"parkhomes-okinawa.com", "www.parkhomes-okinawa.com"}
SKIP_SCHEME = ("#", "mailto:", "tel:", "javascript:", "data:", "sms:", "line:")

BEG_HEAD, END_HEAD = "<!--i18n:alt:start-->", "<!--i18n:alt:end-->"
BEG_BAR, END_BAR = "<!--i18n:bar:start-->", "<!--i18n:bar:end-->"
# 「外す形」と「差し込む形」を1文字単位で一致させる。ずれていると
# ビルドのたびに空行が増減し、無関係なページまで差分になってしまう。
#   head: 直前に改行を足し、末尾にも改行を足して </head> の前に置く
#   bar : 直前に改行を足すだけで <body> の直後に置く
_RE_HEAD_BLOCK = re.compile(r"\n?" + re.escape(BEG_HEAD) + ".*?" + re.escape(END_HEAD) + r"\n", re.S)
_RE_BAR_BLOCK = re.compile(r"\n?" + re.escape(BEG_BAR) + ".*?" + re.escape(END_BAR), re.S)

LD_KEYS = {"name", "alternateName", "description", "streetAddress", "addressLocality",
           "addressRegion", "jobTitle", "headline", "articleBody"}

BAR_CSS = (
    ".pkw-langbar{background:#0d2d5e;font-size:13px;line-height:1;"
    "font-family:system-ui,-apple-system,'Hiragino Kaku Gothic ProN','Meiryo',sans-serif}"
    ".pkw-langbar ul{max-width:1100px;margin:0 auto;padding:7px 24px;display:flex;"
    "gap:6px;justify-content:flex-end;align-items:center;list-style:none;flex-wrap:wrap}"
    ".pkw-langbar li{margin:0}"
    ".pkw-langbar a{color:#cfe0f5;text-decoration:none;padding:5px 9px;border-radius:6px;display:block}"
    ".pkw-langbar a:hover{background:rgba(255,255,255,.14);color:#fff}"
    ".pkw-langbar [aria-current=true]{background:#fff;color:#0d2d5e;font-weight:700}"
    ".pkw-langbar .pkw-lb-label{color:#8fb3dd;letter-spacing:.08em;padding:5px 0}"
    "@media(max-width:600px){.pkw-langbar ul{justify-content:center;padding:6px 12px}}"
)


# ---------------------------------------------------------------- URL 書き換え

def page_base(rel, raw):
    """そのページで相対URLの基準になるURL。<base href> があればそれに従う。"""
    m = re.search(r"<base\b[^>]*\bhref\s*=\s*[\"']([^\"']+)", raw, re.I)
    return m.group(1) if m else config.SITE + config.url_of(rel)


def path_to_rel(path):
    p = unquote(path).lstrip("/")
    if p == "" or p.endswith("/"):
        p += "index.html"
    return p


def map_url(val, base, lang):
    """1本のURLを言語版に向け直す。対象外はサイト内絶対パスに正規化する。

    生成先はソースと階層が変わるので、相対URLをそのまま残すと壊れる。
    サイト内は必ずルート絶対パスへ正規化し、翻訳対象ページだけ言語接頭辞を付ける。
    """
    v = val.strip()
    if not v or v.startswith(SKIP_SCHEME):
        return val
    u = urljoin(base, v)
    p = urlparse(u)
    if p.scheme and p.scheme not in ("http", "https"):
        return val
    if p.netloc and p.netloc.lower() not in HOSTS:
        return val                      # 外部サイトは触らない
    rel = path_to_rel(p.path)
    tail = ("?" + p.query if p.query else "") + ("#" + p.fragment if p.fragment else "")
    if rel in config.PAGESET and lang != "ja":
        return "/" + lang + config.url_of(rel) + tail
    return quote(p.path, safe="/%:@&=+$,~") + tail


def map_srcset(val, base, lang):
    out = []
    for part in val.split(","):
        s = part.strip()
        if not s:
            continue
        bits = s.split(None, 1)
        bits[0] = map_url(bits[0], base, lang)
        out.append(" ".join(bits))
    return ", ".join(out)


def rewrite_urls(masked, base, lang):
    for k, (head, q, val) in list(masked.urls.items()):
        attr = head.split("=")[0].strip().lower()
        if attr == "value":
            continue                    # フォーム送信値は日本語のまま保つ
        if attr == "srcset":
            masked.urls[k] = (head, q, map_srcset(val, base, lang))
        else:
            masked.urls[k] = (head, q, map_url(val, base, lang))


# ---------------------------------------------------------------- 本文置換

def make_pattern(table):
    """長い文字列を優先する単一パス置換用の正規表現。

    一度の走査で置換するので、挿入済みの訳文が別のキーに再ヒットして
    二重に翻訳されることがない（繁体字訳に日本語キーが埋まる等）。
    """
    keys = sorted((k for k in table if table[k]), key=len, reverse=True)
    if not keys:
        return None
    return re.compile("|".join(re.escape(k) for k in keys))


def translate_text(text, pat, table):
    if pat is None:
        return text
    return pat.sub(lambda m: table.get(m.group(0), m.group(0)), text)


def translate_jsonld(masked, table, ldlang):
    def walk(node, key=None):
        if isinstance(node, dict):
            return {k: walk(v, k) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v, key) for v in node]
        if isinstance(node, str) and key in LD_KEYS:
            return table.get(node, node)
        return node

    for k, (open_tag, body) in list(masked.jsonld.items()):
        try:
            data = json.loads(body)
        except Exception:
            continue
        data = walk(data)
        if isinstance(data, dict):
            if "inLanguage" in data:
                data["inLanguage"] = ldlang
            cp = data.get("contactPoint")
            if isinstance(cp, dict) and "availableLanguage" in cp:
                cp["availableLanguage"] = [ldlang]
        masked.jsonld[k] = (open_tag, "\n" + json.dumps(data, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 差し込み

def head_block(rel, lang):
    u = config.url_of(rel)
    here = config.SITE + (("/" + lang) if lang != "ja" else "") + u
    lines = [BEG_HEAD, '<link rel="canonical" href="%s">' % here,
             '<link rel="alternate" hreflang="ja" href="%s%s">' % (config.SITE, u)]
    for code in config.LANGS:
        lines.append('<link rel="alternate" hreflang="%s" href="%s/%s%s">'
                     % (config.LANGS[code][0], config.SITE, code, u))
    lines.append('<link rel="alternate" hreflang="x-default" href="%s%s">' % (config.SITE, u))
    lines.append('<meta property="og:locale" content="%s">'
                 % ("ja_JP" if lang == "ja" else config.LANGS[lang][1]))
    for code in ["ja"] + list(config.LANGS):
        if code != lang:
            lines.append('<meta property="og:locale:alternate" content="%s">'
                         % ("ja_JP" if code == "ja" else config.LANGS[code][1]))
    lines.append(END_HEAD)
    return "\n".join(lines)


def bar_block(rel, lang):
    u = config.url_of(rel)
    items = [("ja", "ja", config.JA_LABEL, config.SITE + u)]
    for code, (attr, _loc, label) in config.LANGS.items():
        items.append((code, attr, label, "%s/%s%s" % (config.SITE, code, u)))
    li = []
    for code, attr, label, href in items:
        cur = ' aria-current="true"' if code == lang else ""
        li.append('<li><a href="%s" hreflang="%s" lang="%s"%s>%s</a></li>'
                  % (href, attr, attr, cur, label))
    return "\n".join([
        BEG_BAR,
        "<style>%s</style>" % BAR_CSS,
        '<nav class="pkw-langbar" aria-label="Language">',
        "<ul>",
        '<li class="pkw-lb-label" aria-hidden="true">LANGUAGE</li>',
        "\n".join(li),
        "</ul>",
        "</nav>",
        END_BAR,
    ])


_RE_CANONICAL = re.compile(r"[ \t]*<link\b[^>]*\brel\s*=\s*[\"']canonical[\"'][^>]*>[ \t]*\n?", re.I)


def strip_blocks(raw):
    """既存の差し込みを外す。ビルドを何度流しても同じ結果になるようにするため。

    ページが元から持つ canonical も外す。言語版ごとに正しい自己参照を張り直すので、
    残すと1ページに2本並んで検索エンジンに矛盾したシグナルを送ることになる。
    """
    raw = _RE_HEAD_BLOCK.sub("", raw)
    raw = _RE_BAR_BLOCK.sub("", raw)
    raw = _RE_CANONICAL.sub("", raw)
    return re.sub(r"\n{3,}", "\n\n", raw)


def insert_blocks(raw, rel, lang):
    m = re.search(r"</head\s*>", raw, re.I)
    if m:
        raw = raw[:m.start()] + "\n" + head_block(rel, lang) + "\n" + raw[m.start():]
    m = re.search(r"<body\b[^>]*>", raw, re.I)
    if m:
        raw = raw[:m.end()] + "\n" + bar_block(rel, lang) + raw[m.end():]
    return raw


def set_og_url(raw, rel, lang):
    """og:url は content 属性なのでURL書き換えの対象外。ここで言語版に向ける。"""
    here = config.SITE + (("/" + lang) if lang != "ja" else "") + config.url_of(rel)
    return re.sub(
        r"(<meta\b[^>]*\bproperty\s*=\s*[\"']og:url[\"'][^>]*\bcontent\s*=\s*\")[^\"]*(\")",
        lambda m: m.group(1) + here + m.group(2), raw, flags=re.I)


_RE_NEXT = re.compile(r"(name\s*=\s*[\"']_next[\"'][^>]*\bvalue\s*=\s*\")([^\"]*)(\")", re.I)


def set_form_next(raw, base, lang):
    """フォーム送信後の遷移先を言語版に向ける。

    _next は value 属性なので通常のURL書き換えの対象外（value はフォーム送信値
    として日本語のまま保つ方針）。ただしこれは遷移先URLなので、英語ページから
    送信した人が日本語のサンクスページに飛ばされないよう個別に直す。
    """
    return _RE_NEXT.sub(lambda m: m.group(1) + config.SITE + map_url(m.group(2), base, lang)
                        + m.group(3), raw)


def set_lang(raw, lang):
    attr = "ja" if lang == "ja" else config.LANGS[lang][0]
    return re.sub(r"(<html\b[^>]*?)\slang\s*=\s*[\"'][^\"']*[\"']",
                  lambda m: m.group(1) + ' lang="%s"' % attr, raw, count=1, flags=re.I)


# ---------------------------------------------------------------- 生成

def load_table(lang):
    p = os.path.join(config.STRINGS, lang + ".json")
    if not os.path.exists(p):
        return {}
    d = json.load(io.open(p, encoding="utf-8"))
    return {k: v for k, v in d.items() if isinstance(v, str) and v.strip()}


def build_page(rel, lang, table, pat):
    raw = io.open(config.src_path(rel), encoding="utf-8").read()
    base = page_base(rel, raw)
    m = htmlmask.Masked(strip_blocks(raw))
    m.text = translate_text(m.text, pat, table)
    translate_jsonld(m, table, "ja" if lang == "ja" else config.LANGS[lang][0])
    rewrite_urls(m, base, lang)
    out = set_og_url(set_lang(m.unmask(), lang), rel, lang)
    out = set_form_next(out, base, lang)
    return insert_blocks(out, rel, lang)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="書き込まずに集計のみ")
    ap.add_argument("--lang", action="append", help="対象言語を絞る")
    a = ap.parse_args()

    src = json.load(io.open(os.path.join(config.STRINGS, "ja.json"), encoding="utf-8"))
    all_keys = [e["ja"] for e in src["entries"]]
    langs = a.lang or (["ja"] + list(config.LANGS))

    for lang in langs:
        table = {} if lang == "ja" else load_table(lang)
        pat = make_pattern(table)
        missing = 0 if lang == "ja" else sum(1 for k in all_keys if k not in table)
        for rel in config.PAGES:
            out = build_page(rel, lang, table, pat)
            dst = config.src_path(rel) if lang == "ja" else config.out_path(lang, rel)
            if not a.check:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                io.open(dst, "w", encoding="utf-8", newline="").write(out)
        print("%-8s pages=%-3d translated=%-5d missing=%d"
              % (lang, len(config.PAGES), len(all_keys) - missing, missing))

    if not a.check and not a.lang:
        import sitemap
        sitemap.main()


if __name__ == "__main__":
    main()
