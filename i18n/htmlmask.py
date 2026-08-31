# -*- coding: utf-8 -*-
"""生HTMLを壊さずに本文だけを置換するためのマスキング。

bs4で再シリアライズすると属性順やインデントが変わり差分が爆発するため、
ソース文字列をそのまま扱う。翻訳してはいけない領域（script / style /
コメント / URL属性値）を一時的にトークンへ退避し、本文置換のあとで戻す。
"""
import re

# JSON-LD は本文と同じく翻訳対象なので、通常のscriptとは区別して退避する
_RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_STYLE   = re.compile(r"<style\b[^>]*>.*?</style>", re.S | re.I)
_RE_SCRIPT  = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
_RE_LD      = re.compile(r"type\s*=\s*[\"']application/ld\+json[\"']", re.I)
# <base> の href は相対URL解決の基準そのもの。言語版に向けてしまうと
# 書き換え対象外のURL（script内など）が全部ずれるので触らない。
_RE_BASE    = re.compile(r"<base(?=[\s/>])[^>]*>", re.I)
# 置換してはいけない属性値。URL系は値に日本語パスが入るとリンクが壊れるため、
# value はフォーム送信値（表示ラベルは翻訳しつつ社内に届く中身は日本語で保つ）ため。
_RE_URLATTR = re.compile(
    r"""(\b(?:href|src|srcset|action|poster|data-src|data-href|formaction|value)\s*=\s*)("[^"]*"|'[^']*')""",
    re.I,
)

TOK = "\x00%s%d\x00"


class Masked:
    """マスク済みテキストと退避した断片を保持する。"""

    def __init__(self, text):
        self.parts = {}      # token -> 元の文字列
        self.jsonld = {}     # token -> (open_tag, 中身)
        self.urls = {}       # token -> (属性名+=, クォート, 生の値)
        self._n = 0
        self.text = self._mask(text)

    def _tok(self, kind):
        self._n += 1
        return TOK % (kind, self._n)

    def _mask(self, t):
        def keep(m):
            k = self._tok("K")
            self.parts[k] = m.group(0)
            return k

        def script(m):
            attrs, body = m.group(1), m.group(2)
            if _RE_LD.search(attrs or ""):
                k = self._tok("L")
                self.jsonld[k] = ("<script%s>" % attrs, body)
                return k
            k = self._tok("K")
            self.parts[k] = m.group(0)
            return k

        def urlattr(m):
            head, q = m.group(1), m.group(2)
            k = self._tok("U")
            self.urls[k] = (head, q[0], q[1:-1])
            return k

        t = _RE_COMMENT.sub(keep, t)
        t = _RE_BASE.sub(keep, t)
        t = _RE_STYLE.sub(keep, t)
        t = _RE_SCRIPT.sub(script, t)
        t = _RE_URLATTR.sub(urlattr, t)
        return t

    def unmask(self, text=None):
        t = self.text if text is None else text
        # トークンは入れ子になり得る（scriptの中のhref等）ので収束するまで回す
        for _ in range(10):
            if "\x00" not in t:
                break
            for k, v in self.urls.items():
                if k in t:
                    head, q, val = v
                    t = t.replace(k, "%s%s%s%s" % (head, q, val, q))
            for k, v in self.jsonld.items():
                if k in t:
                    t = t.replace(k, "%s%s</script>" % (v[0], v[1]))
            for k, v in self.parts.items():
                if k in t:
                    t = t.replace(k, v)
        return t
