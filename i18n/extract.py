# -*- coding: utf-8 -*-
"""日本語原本から翻訳対象文字列を抽出し i18n/strings/ja.json を作る。

置換はマスク済みテキストへのリテラル置換で行うため、抽出もマスク済み
テキストから行う。こうすることで「抽出できたのに置換できない」文字列が
原理的に発生しない。
"""
import io, json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, htmlmask, build
from bs4 import BeautifulSoup

JA = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")
TEXT_ATTRS = ("alt", "title", "placeholder", "aria-label")
META_OK = re.compile(r"^(description|keywords|og:(title|description|site_name)|twitter:(title|description))$", re.I)
# JSON-LD 内で翻訳してよいキー（url/telephone等の機械可読値は除外）
LD_KEYS = {"name", "alternateName", "description", "streetAddress", "addressLocality",
           "addressRegion", "jobTitle", "headline", "articleBody", "itemListElement"}


def find_raw(hay, decoded):
    """bs4がデコードした文字列に対応する「生の」部分文字列を返す。

    ソース側が &copy; のような実体参照を使っていると、デコード済み文字列は
    そのままでは生HTMLに現れない。置換キーには生の形が要るので引き当てる。
    記号だけ実体参照を許容すればよく、仮名漢字は isalnum() が真になるため
    パターンは短いまま済む。
    """
    if decoded in hay:
        return decoded
    pat = "".join(
        re.escape(c) if (c.isalnum() or c.isspace()) else r"(?:%s|&[#\w]+;)" % re.escape(c)
        for c in decoded)
    m = re.search(pat, hay)
    return m.group(0) if m else None


def ld_strings(node, key=None, out=None):
    """JSON-LD から翻訳対象の文字列を集める。"""
    if out is None:
        out = []
    if isinstance(node, dict):
        for k, v in node.items():
            ld_strings(v, k, out)
    elif isinstance(node, list):
        for v in node:
            ld_strings(v, key, out)
    elif isinstance(node, str):
        if key in LD_KEYS and JA.search(node):
            out.append(node)
    return out


TOKEN = re.compile(r"\x00[A-Z]\d+\x00")


def split_tokens(s):
    """マスクトークンを跨いだ文字列を、翻訳可能な断片に割る。

    テキストノードの途中にHTMLコメント等があると、退避トークンごと
    1つの文字列として拾えてしまう。そのまま訳文に置き換えると
    退避した中身が復元できず、コメントが消える。
    """
    for part in TOKEN.split(s):
        part = part.strip()
        if part and JA.search(part):
            yield part


def page_strings(masked):
    """(文字列, 種別) のリストを出現順で返す。"""
    found = []
    soup = BeautifulSoup(masked.text, "html.parser")
    for t in soup.find_all(string=True):
        kind = "title" if (t.parent and t.parent.name == "title") else "text"
        for part in split_tokens(str(t)):
            found.append((part, kind))
    for el in soup.find_all(True):
        for a in TEXT_ATTRS:
            v = el.get(a)
            if isinstance(v, str):
                for part in split_tokens(v):
                    found.append((part, "attr:" + a))
        if el.name == "meta":
            n = el.get("name") or el.get("property") or ""
            v = el.get("content")
            if isinstance(v, str) and META_OK.match(n) and JA.search(v):
                found.append((v.strip(), "meta:" + n))
    for _, (_, body) in masked.jsonld.items():
        try:
            data = json.loads(body)
        except Exception:
            continue
        for s in ld_strings(data):
            found.append((s, "jsonld"))
    return found


def main():
    order = []
    meta = collections.OrderedDict()
    unmatched = []

    for rel in config.PAGES:
        raw = io.open(config.src_path(rel), encoding="utf-8").read()
        # 生成時に差し込んだ言語バー等は原文ではないので抽出対象から外す
        m = htmlmask.Masked(build.strip_blocks(raw))
        for s, kind in page_strings(m):
            if kind != "jsonld":
                r = find_raw(m.text, s)
                if r is None:
                    unmatched.append((rel, kind, s[:60]))
                    continue
                s = r
            if s not in meta:
                meta[s] = {"ja": s, "kind": kind, "pages": [], "n": 0}
                order.append(s)
            e = meta[s]
            if rel not in e["pages"]:
                e["pages"].append(rel)
            if kind == "jsonld" and e["kind"] != "jsonld":
                pass  # 本文にも出るものは本文側の種別を優先
            e["n"] += 1

    out = {
        "note": "翻訳元。キーは日本語原文そのもの。en.json 等は同じキーで訳文を持つ。",
        "pages": len(config.PAGES),
        "count": len(order),
        "chars": sum(len(s) for s in order),
        "entries": [meta[s] for s in order],
    }
    dst = os.path.join(config.STRINGS, "ja.json")
    io.open(dst, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))

    print("unique strings:", out["count"], " chars:", out["chars"])
    print("wrote:", dst)
    if unmatched:
        print("!! マスク済みテキストで見つからない文字列:", len(unmatched))
        for u in unmatched[:10]:
            print("   ", u)
    else:
        print("all extracted strings are literally replaceable: OK")


if __name__ == "__main__":
    main()
